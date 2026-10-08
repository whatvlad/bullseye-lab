from __future__ import annotations

import base64
import binascii
from collections import Counter, deque
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from itertools import count
from time import monotonic, perf_counter
from typing import Any, cast

import httpx

from memebot.core.clock import utc_now
from memebot.core.logging import get_logger
from memebot.models.common import SolanaAddress
from memebot.providers.solana.base import (
    Commitment,
    RpcAccount,
    RpcHealth,
    RpcTokenBalance,
    RpcTokenBalances,
    SolanaRpcProvider,
)


class SolanaRpcError(RuntimeError):
    def __init__(self, code: str, *, rate_limited: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.rate_limited = rate_limited


class JsonRpcSolanaClient:
    """Minimal vendor-neutral, read-only Solana JSON-RPC client."""

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._endpoint = endpoint
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={"content-type": "application/json"},
            transport=transport,
        )
        self._request_ids = count(1)
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._failures = 0
        self._blocked_until = 0.0
        self._probe_in_flight = False
        self._requests: Counter[str] = Counter()
        self._errors: Counter[str] = Counter()
        self._latencies: deque[float] = deque(maxlen=2048)
        self._logger = get_logger("memebot.rpc")

    @property
    def available(self) -> bool:
        return self._clock() >= self._blocked_until and not self._probe_in_flight

    def metrics(self) -> dict[str, object]:
        return {
            "requests_by_method": dict(self._requests),
            "errors_by_code": dict(self._errors),
            "consecutive_failures": self._failures,
            "circuit_open": not self.available,
            "cooldown_remaining_seconds": max(0.0, self._blocked_until - self._clock()),
            "latency_ms_recent": list(self._latencies),
        }

    async def _call(self, method: str, params: list[object] | None = None) -> object:
        if not self.available:
            self._errors["circuit_open"] += 1
            raise SolanaRpcError("circuit_open")
        probing = self._blocked_until > 0
        if probing:
            self._probe_in_flight = True
        request_id = next(self._request_ids)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or [],
        }
        started = perf_counter()
        self._requests[method] += 1
        response: httpx.Response | None = None
        error_code: str | None = None
        try:
            try:
                response = await self._client.post(self._endpoint, json=payload)
                response.raise_for_status()
                body = response.json()
            except httpx.HTTPStatusError as error:
                status = error.response.status_code
                raise SolanaRpcError(f"http_{status}", rate_limited=status == 429) from None
            except (httpx.HTTPError, ValueError):
                raise SolanaRpcError("transport_error") from None
            if not isinstance(body, dict):
                raise SolanaRpcError("malformed_response")
            if body.get("id") != request_id or body.get("jsonrpc") != "2.0":
                raise SolanaRpcError("mismatched_rpc_response")
            rpc_error = body.get("error")
            if isinstance(rpc_error, dict):
                code = rpc_error.get("code", "unknown")
                raise SolanaRpcError(f"rpc_{code}", rate_limited=code == 429)
            if "result" not in body or rpc_error is not None:
                raise SolanaRpcError("malformed_response")
            self._failures = 0
            if probing:
                self._blocked_until = 0.0
            return body["result"]
        except SolanaRpcError as error:
            error_code = error.code
            self._errors[error.code] += 1
            self._failures += 1
            if (
                error.rate_limited
                or error.code in {"http_401", "http_403"}
                or self._failures >= self._failure_threshold
                or probing
            ):
                delay = self._cooldown_seconds
                if error.code in {"http_401", "http_403"}:
                    delay = max(delay, 900)
                if response is not None:
                    delay = max(delay, _retry_after_seconds(response.headers.get("retry-after")))
                self._blocked_until = self._clock() + delay
            raise
        finally:
            self._probe_in_flight = False
            latency = (perf_counter() - started) * 1000
            self._latencies.append(latency)
            log_request = self._logger.warning if error_code is not None else self._logger.debug
            log_request(
                "rpc_request",
                method=method,
                latency_ms=latency,
                error_code=error_code,
                circuit_open=not self.available,
            )

    async def health(self) -> RpcHealth:
        started_at = perf_counter()
        try:
            result = await self._call("getHealth")
            healthy = result == "ok"
            error = None if healthy else "unhealthy_result"
        except SolanaRpcError as rpc_error:
            healthy = False
            error = rpc_error.code
        return RpcHealth(
            healthy=healthy,
            checked_at=utc_now(),
            latency_ms=(perf_counter() - started_at) * 1000,
            error=error,
        )

    async def get_account(
        self,
        address: SolanaAddress,
        commitment: Commitment,
    ) -> RpcAccount | None:
        result = await self._call(
            "getAccountInfo",
            [address, {"commitment": commitment, "encoding": "base64"}],
        )
        if not isinstance(result, dict):
            raise SolanaRpcError("malformed_account_response")
        value = result.get("value")
        if value is None:
            return None
        context = result.get("context")
        if not isinstance(value, dict) or not isinstance(context, dict):
            raise SolanaRpcError("malformed_account_response")
        encoded_data = value.get("data")
        if not (
            isinstance(encoded_data, list)
            and len(encoded_data) >= 2
            and isinstance(encoded_data[0], str)
            and encoded_data[1] == "base64"
        ):
            raise SolanaRpcError("unsupported_account_encoding")
        try:
            base64.b64decode(encoded_data[0], validate=True)
        except (binascii.Error, ValueError) as error:
            raise SolanaRpcError("invalid_account_base64") from error
        return RpcAccount(
            address=address,
            slot=int(context["slot"]),
            owner=str(value["owner"]),
            lamports=int(value["lamports"]),
            executable=bool(value["executable"]),
            data_base64=encoded_data[0],
        )

    async def get_transaction(
        self,
        signature: str,
        commitment: Commitment,
    ) -> dict[str, object] | None:
        result = await self._call(
            "getTransaction",
            [
                signature,
                {
                    "commitment": commitment,
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )
        if result is None:
            return None
        if not isinstance(result, dict):
            raise SolanaRpcError("malformed_transaction_response")
        return cast(dict[str, object], result)

    async def get_multiple_accounts(
        self,
        addresses: list[SolanaAddress],
        commitment: Commitment,
    ) -> tuple[RpcAccount | None, ...]:
        if not addresses:
            return ()
        result = await self._call(
            "getMultipleAccounts",
            [addresses, {"commitment": commitment, "encoding": "base64"}],
        )
        if not isinstance(result, dict):
            raise SolanaRpcError("malformed_multiple_accounts_response")
        context = result.get("context")
        values = result.get("value")
        if not isinstance(context, dict) or not isinstance(values, list):
            raise SolanaRpcError("malformed_multiple_accounts_response")
        if len(values) != len(addresses):
            raise SolanaRpcError("multiple_accounts_length_mismatch")
        slot = int(context["slot"])
        accounts: list[RpcAccount | None] = []
        for address, value in zip(addresses, values, strict=True):
            if value is None:
                accounts.append(None)
                continue
            if not isinstance(value, dict):
                raise SolanaRpcError("malformed_multiple_accounts_response")
            encoded_data = value.get("data")
            if not (
                isinstance(encoded_data, list)
                and len(encoded_data) >= 2
                and isinstance(encoded_data[0], str)
                and encoded_data[1] == "base64"
            ):
                raise SolanaRpcError("unsupported_account_encoding")
            try:
                base64.b64decode(encoded_data[0], validate=True)
            except (binascii.Error, ValueError) as error:
                raise SolanaRpcError("invalid_account_base64") from error
            accounts.append(
                RpcAccount(
                    address=address,
                    slot=slot,
                    owner=str(value["owner"]),
                    lamports=int(value["lamports"]),
                    executable=bool(value["executable"]),
                    data_base64=encoded_data[0],
                )
            )
        return tuple(accounts)

    async def get_token_largest_accounts(
        self,
        mint: SolanaAddress,
        commitment: Commitment,
    ) -> RpcTokenBalances:
        result = await self._call(
            "getTokenLargestAccounts",
            [mint, {"commitment": commitment}],
        )
        return self._parse_token_balances(result, address_key="address")

    async def get_token_accounts_by_owner(
        self,
        owner: SolanaAddress,
        mint: SolanaAddress,
        commitment: Commitment,
    ) -> RpcTokenBalances:
        result = await self._call(
            "getTokenAccountsByOwner",
            [owner, {"mint": mint}, {"commitment": commitment, "encoding": "jsonParsed"}],
        )
        if not isinstance(result, dict):
            raise SolanaRpcError("malformed_owner_token_accounts_response")
        context = result.get("context")
        values = result.get("value")
        if not isinstance(context, dict) or not isinstance(values, list):
            raise SolanaRpcError("malformed_owner_token_accounts_response")
        balances: list[RpcTokenBalance] = []
        for value in values:
            try:
                account = cast(dict[str, Any], value)["account"]
                data = cast(dict[str, Any], account)["data"]
                parsed = cast(dict[str, Any], data)["parsed"]
                info = cast(dict[str, Any], parsed)["info"]
                token_amount = cast(dict[str, Any], info)["tokenAmount"]
                amount = cast(dict[str, Any], token_amount)["amount"]
                address = cast(dict[str, Any], value)["pubkey"]
            except (KeyError, TypeError):
                raise SolanaRpcError("malformed_owner_token_accounts_response") from None
            balances.append(RpcTokenBalance(address=str(address), amount_raw=int(amount)))
        return RpcTokenBalances(slot=int(context["slot"]), balances=tuple(balances))

    @staticmethod
    def _parse_token_balances(result: object, *, address_key: str) -> RpcTokenBalances:
        if not isinstance(result, dict):
            raise SolanaRpcError("malformed_token_balances_response")
        context = result.get("context")
        values = result.get("value")
        if not isinstance(context, dict) or not isinstance(values, list):
            raise SolanaRpcError("malformed_token_balances_response")
        balances: list[RpcTokenBalance] = []
        for value in values:
            if not isinstance(value, dict):
                raise SolanaRpcError("malformed_token_balances_response")
            try:
                balances.append(
                    RpcTokenBalance(
                        address=str(value[address_key]),
                        amount_raw=int(value["amount"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                raise SolanaRpcError("malformed_token_balances_response") from None
        return RpcTokenBalances(slot=int(context["slot"]), balances=tuple(balances))

    async def close(self) -> None:
        await self._client.aclose()


def _retry_after_seconds(value: str | None) -> float:
    if value is None:
        return 0
    try:
        seconds = float(value)
        return min(86400, max(0, seconds))
    except ValueError:
        try:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=UTC)
            return min(86400, max(0, (stamp - datetime.now(UTC)).total_seconds()))
        except (ValueError, TypeError, OverflowError):
            return 0


class FallbackSolanaRpcProvider:
    """Read-only primary/fallback RPC without taking ownership of either client."""

    def __init__(self, primary: SolanaRpcProvider, fallback: SolanaRpcProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    async def health(self) -> RpcHealth:
        primary = await self._primary.health()
        return primary if primary.healthy else await self._fallback.health()

    async def get_account(
        self, address: SolanaAddress, commitment: Commitment
    ) -> RpcAccount | None:
        try:
            result = await self._primary.get_account(address, commitment)
        except Exception:
            result = None
        return (
            result if result is not None else await self._fallback.get_account(address, commitment)
        )

    async def get_transaction(
        self, signature: str, commitment: Commitment
    ) -> dict[str, object] | None:
        try:
            result = await self._primary.get_transaction(signature, commitment)
        except Exception:
            result = None
        return (
            result
            if result is not None
            else await self._fallback.get_transaction(signature, commitment)
        )

    async def get_multiple_accounts(
        self, addresses: list[SolanaAddress], commitment: Commitment
    ) -> tuple[RpcAccount | None, ...]:
        try:
            return await self._primary.get_multiple_accounts(addresses, commitment)
        except Exception:
            return await self._fallback.get_multiple_accounts(addresses, commitment)

    async def get_token_largest_accounts(
        self, mint: SolanaAddress, commitment: Commitment
    ) -> RpcTokenBalances:
        try:
            return await self._primary.get_token_largest_accounts(mint, commitment)
        except Exception:
            return await self._fallback.get_token_largest_accounts(mint, commitment)

    async def get_token_accounts_by_owner(
        self, owner: SolanaAddress, mint: SolanaAddress, commitment: Commitment
    ) -> RpcTokenBalances:
        try:
            return await self._primary.get_token_accounts_by_owner(owner, mint, commitment)
        except Exception:
            return await self._fallback.get_token_accounts_by_owner(owner, mint, commitment)

    async def close(self) -> None:
        """The worker owns and closes the underlying clients."""
