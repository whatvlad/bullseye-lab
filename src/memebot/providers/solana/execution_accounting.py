"""Exact packet-local movements; canonical ownership/config still require an atomic bank."""

from __future__ import annotations

from typing import Any

from memebot.providers.solana.canonical import FEE_PROGRAM
from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.idl_schema import decode_record, schema
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
)
from memebot.providers.solana.trade_alignment import account_keys, trade_invocations

ATA_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
COMPUTE_PROGRAM = "ComputeBudget111111111111111111111111111111"
MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


def execution_accounting(tx: dict[str, Any], mint: str) -> dict[str, Any]:
    """Explain every lamport/token delta without inferring an unnamed transfer.

    External programs cannot debit/change canonically foreign-owned market data.
    Every CPI that could do so is inspected; bank ownership and fee/config checks
    remain mandatory before this packet-local result can authorize any execution.
    """
    meta = tx["meta"]
    if meta.get("err") is not None or any("Log truncated" in s for s in meta["logMessages"]):
        raise ValueError("MISSING_PACKET: failed or truncated execution")
    calls = trade_invocations(tx, mint)
    if len(calls) != 1:
        raise ValueError("EVENT_INSTRUCTION_ALIGNMENT: single native invocation required")
    call = calls[0]
    event, mapping = call["event"], call["mapping"]
    keys = account_keys(tx)
    message = tx["transaction"]["message"]
    header = message.get("header")
    writable: set[str] = set(keys)
    if header is not None:
        static_count = len(message["accountKeys"])
        signed = header["numRequiredSignatures"]
        writable = {
            key
            for i, key in enumerate(keys[:static_count])
            if (i < signed - header["numReadonlySignedAccounts"])
            or signed <= i < static_count - header["numReadonlyUnsignedAccounts"]
        }
        writable.update(meta.get("loadedAddresses", {}).get("writable", []))
    if len(keys) != len(meta["preBalances"]) or len(keys) != len(meta["postBalances"]):
        raise ValueError("ACCOUNT_ORDERING_AMBIGUITY: balance/key lengths disagree")
    curve = mapping.get("bonding_curve")
    vault = mapping.get("associated_bonding_curve", mapping.get("associated_base_bonding_curve"))
    if not curve or not vault or mapping.get("user") != event.user:
        raise ValueError("EVENT_INSTRUCTION_ALIGNMENT: market/user mapping absent")
    protected = {
        mapping[name]
        for name in (
            "global",
            "mint",
            "base_mint",
            "bonding_curve",
            "associated_bonding_curve",
            "associated_base_bonding_curve",
            "associated_quote_bonding_curve",
            "fee_config",
            "sharing_config",
            "creator_vault",
            "associated_creator_vault",
            "fee_recipient",
            "buyback_fee_recipient",
            "associated_quote_fee_recipient",
            "associated_quote_buyback_fee_recipient",
        )
        if name in mapping
    }
    _, fields = decode_record(
        PUMP_PROGRAM_ID,
        decode_base58(dict(call["descendants"])[call["event_inner_index"]]["data"])[8:],
        collection="events",
    )
    balances = {key: int(meta["preBalances"][i]) for i, key in enumerate(keys)}
    balances[keys[0]] -= int(meta["fee"])
    pre_tokens = {r["accountIndex"]: r for r in meta["preTokenBalances"]}
    post_tokens = {r["accountIndex"]: r for r in meta["postTokenBalances"]}
    token_rows = {**post_tokens, **pre_tokens}
    tokens = {keys[i]: int(r["uiTokenAmount"]["amount"]) for i, r in pre_tokens.items()}
    trace: list[dict[str, Any]] = []
    ancillary: list[dict[str, Any]] = []
    groups = {g["index"]: g["instructions"] for g in meta["innerInstructions"]}
    selected = {(call["top_index"], call["inner_index"])}
    selected.update((call["top_index"], i) for i, _ in call["descendants"])
    market_transfers = 0

    def move(
        source: str, destination: str, amount: int, kind: str, coordinate: list[int | None]
    ) -> None:
        if source not in balances or destination not in balances or amount < 0:
            raise ValueError("ACCOUNT_ORDERING_AMBIGUITY: movement account absent")
        balances[source] -= amount
        balances[destination] += amount
        trace.append(
            {
                "source": source,
                "destination": destination,
                "amount": amount,
                "asset": "SOL",
                "kind": kind,
                "coordinate": coordinate,
            }
        )

    for top, outer in enumerate(tx["transaction"]["message"]["instructions"]):
        for pos, ix in [(None, outer), *enumerate(groups.get(top, []))]:
            coordinate = [top, pos]
            inside = (top, pos) in selected
            program = keys[ix["programIdIndex"]]
            accounts = [keys[a] for a in ix["accounts"]]
            raw = decode_base58(ix["data"])
            if (top, pos) == (call["top_index"], call["inner_index"]):
                if not event.is_buy:
                    fee_amount, creator_amount = int(fields["fee"]), int(fields["creator_fee"])
                    buyback = int(fields["buyback_fee"])
                    # Legacy suffix is the documented curve-v2/buyback pair;
                    # destination authorization is independently checked against Global.
                    recipient = mapping.get("buyback_fee_recipient", accounts[-1])
                    protected.add(recipient)
                    move(
                        curve,
                        event.user,
                        event.quote_amount - fee_amount - creator_amount,
                        "TRADE_PROCEEDS",
                        coordinate,
                    )
                    move(
                        curve,
                        fields["fee_recipient"],
                        fee_amount - buyback,
                        "PROTOCOL_FEE",
                        coordinate,
                    )
                    move(curve, recipient, buyback, "BUYBACK_FEE", coordinate)
                    move(curve, mapping["creator_vault"], creator_amount, "CREATOR_FEE", coordinate)
                continue
            if program == NATIVE_SOL_MINT:
                tag = int.from_bytes(raw[:4], "little")
                if tag == 2 and len(raw) == 12 and len(accounts) >= 2:
                    kind = "TRADE_SYSTEM_TRANSFER" if inside else "UNRELATED_SYSTEM_TRANSFER"
                    if not inside and protected.intersection(accounts):
                        raise ValueError(
                            "UNEXPLAINED_OUTER_MUTATION: ancillary transfer touches "
                            "protected account"
                        )
                    move(
                        accounts[0],
                        accounts[1],
                        int.from_bytes(raw[4:], "little"),
                        kind,
                        coordinate,
                    )
                elif tag == 0 and len(raw) == 52 and len(accounts) == 2:
                    if not inside and accounts[1] in protected:
                        raise ValueError(
                            "UNEXPLAINED_OUTER_MUTATION: protected account created outside trade"
                        )
                    move(
                        accounts[0],
                        accounts[1],
                        int.from_bytes(raw[4:12], "little"),
                        "ACCOUNT_RENT",
                        coordinate,
                    )
                elif tag == 3 and len(raw) >= 92 and len(accounts) in {2, 3}:
                    from solders.pubkey import Pubkey

                    seed_size = int.from_bytes(raw[36:44], "little")
                    end = 44 + seed_size
                    if len(raw) != end + 48 or accounts[1] in protected:
                        raise ValueError(
                            "UNEXPLAINED_OUTER_MUTATION: CreateWithSeed layout/protected account"
                        )
                    derived = Pubkey.create_with_seed(
                        Pubkey.from_bytes(raw[4:36]),
                        raw[44:end].decode(),
                        Pubkey.from_bytes(raw[end + 16 : end + 48]),
                    )
                    if str(derived) != accounts[1]:
                        raise ValueError(
                            "ACCOUNT_ORDERING_AMBIGUITY: CreateWithSeed address mismatch"
                        )
                    move(
                        accounts[0],
                        accounts[1],
                        int.from_bytes(raw[end : end + 8], "little"),
                        "ACCOUNT_RENT",
                        coordinate,
                    )
                elif tag == 4 and len(raw) == 4 and len(accounts) >= 3:
                    if accounts[0] in protected:
                        raise ValueError("UNEXPLAINED_OUTER_MUTATION: protected nonce account")
                    ancillary.append(
                        {
                            "coordinate": coordinate,
                            "program": program,
                            "effect": "AdvanceNonceAccount; no SOL/token movement",
                        }
                    )
                else:
                    raise ValueError("UNSUPPORTED_INSTRUCTION_VARIANT: system mutation")
            elif program in {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}:
                tag = raw[0] if raw else -1
                if tag in {3, 12} and len(raw) == (9 if tag == 3 else 10):
                    source, destination = accounts[0], accounts[1 if tag == 3 else 2]
                    amount = int.from_bytes(raw[1:9], "little")
                    metadata = token_rows.get(
                        keys.index(source), token_rows.get(keys.index(destination))
                    )
                    if metadata is None or metadata.get("programId", program) != program:
                        raise ValueError("MISSING_PACKET: transfer token metadata absent")
                    token_mint = metadata["mint"]
                    for address in (source, destination):
                        row = token_rows.get(keys.index(address))
                        if row is not None and (
                            row["mint"] != token_mint or row.get("programId", program) != program
                        ):
                            raise ValueError(
                                "PHYSICAL_BALANCE_MISMATCH: transfer metadata disagrees"
                            )
                    if not inside and protected.intersection({source, destination}):
                        raise ValueError("UNEXPLAINED_OUTER_MUTATION: protected token movement")
                    if tag == 12 and accounts[1] != token_mint:
                        raise ValueError("PHYSICAL_BALANCE_MISMATCH: checked mint mismatch")
                    if vault in {source, destination}:
                        if not inside or amount != event.token_amount or token_mint != mint:
                            raise ValueError("UNEXPLAINED_INNER_MUTATION: unrelated vault movement")
                        expected = source == vault if event.is_buy else destination == vault
                        if not expected:
                            raise ValueError("PHYSICAL_BALANCE_MISMATCH: vault direction mismatch")
                        market_transfers += 1
                    tokens[source] = tokens.get(source, 0) - amount
                    tokens[destination] = tokens.get(destination, 0) + amount
                    trace.append(
                        {
                            "source": source,
                            "destination": destination,
                            "amount": amount,
                            "asset": token_mint,
                            "kind": "TOKEN_TRANSFER",
                            "coordinate": coordinate,
                        }
                    )
                    if token_mint == WRAPPED_SOL_MINT:
                        move(source, destination, amount, "WRAPPED_SOL_TRANSFER", coordinate)
                elif tag == 9 and raw == b"\x09" and len(accounts) == 3:
                    source, destination, authority = accounts
                    row = token_rows.get(keys.index(source))
                    if (
                        source in protected
                        or row is None
                        or row.get("owner") != authority
                        or meta["postBalances"][keys.index(source)] != 0
                        or row.get("programId", program) != program
                        or (row["mint"] != WRAPPED_SOL_MINT and tokens.get(source, 0) != 0)
                    ):
                        raise ValueError(
                            "UNEXPLAINED_OUTER_MUTATION: token close provenance incomplete"
                        )
                    move(
                        source,
                        destination,
                        balances[source],
                        "TOKEN_ACCOUNT_CLOSE_REFUND",
                        coordinate,
                    )
                    tokens[source] = 0
                elif tag in {1, 16, 18, 22, 21}:
                    # InitializeAccount[2/3], InitializeImmutableOwner and
                    # GetAccountDataSize: user account only; mint is read-only.
                    if tag != 21 and accounts[0] in protected:
                        raise ValueError(
                            "UNEXPLAINED_INNER_MUTATION: protected token initialization"
                        )
                elif tag == 17 and raw == b"\x11" and len(accounts) == 1:
                    row = token_rows.get(keys.index(accounts[0]))
                    if row is None or row["mint"] != WRAPPED_SOL_MINT:
                        raise ValueError("MISSING_PACKET: SyncNative rent metadata absent")
                    initial = int(meta["preBalances"][keys.index(accounts[0])])
                    initial_tokens = int(
                        pre_tokens.get(keys.index(accounts[0]), {})
                        .get("uiTokenAmount", {})
                        .get("amount", 0)
                    )
                    if initial == 0:
                        raise ValueError(
                            "MISSING_PACKET: initialized WSOL rent boundary unavailable"
                        )
                    tokens[accounts[0]] = balances[accounts[0]] - (initial - initial_tokens)
                else:
                    raise ValueError("UNSUPPORTED_INSTRUCTION_VARIANT: token mutation")
            elif program == PUMP_PROGRAM_ID:
                if not raw.startswith(bytes.fromhex("e445a52e51cb9a1d")):
                    raise ValueError("UNSUPPORTED_INSTRUCTION_VARIANT: additional Pump mutation")
            elif program == ATA_PROGRAM:
                if (
                    raw not in {b"", b"\x00", b"\x01"}
                    or len(accounts) < 6
                    or accounts[1] in protected
                ):
                    raise ValueError(
                        "UNEXPLAINED_OUTER_MUTATION: protected/unsupported ATA creation"
                    )
                ancillary.append(
                    {
                        "coordinate": coordinate,
                        "program": program,
                        "effect": "user ATA creation; mint read-only; rent accounted by System CPI",
                    }
                )
            elif program == FEE_PROGRAM:
                definition = next(
                    (
                        i
                        for i in schema(FEE_PROGRAM)["instructions"]
                        if bytes(i["discriminator"]) == raw[:8]
                    ),
                    None,
                )
                if (
                    definition is None
                    or definition["name"] not in {"get_fees", "get_fees_with_quote_mint"}
                    or any(a.get("writable", False) for a in definition["accounts"])
                ):
                    raise ValueError("UNEXPLAINED_INNER_MUTATION: fee program mutation")
            elif program not in {COMPUTE_PROGRAM, MEMO_PROGRAM}:
                # Only a wrapper containing the selected Pump invocation may
                # have protected accounts. Its nested calls and all balance
                # movements are still checked; no arbitrary wrapper allowlist.
                if protected.intersection(accounts).intersection(writable) and not (
                    pos is None and top == call["top_index"]
                ):
                    raise ValueError(
                        "UNEXPLAINED_INNER_MUTATION: unknown program has protected accounts"
                    )
                ancillary.append(
                    {
                        "coordinate": coordinate,
                        "program": program,
                        "effect": "foreign-owner boundary requires canonical bank; CPIs inspected",
                    }
                )
    residuals = {
        key: int(meta["postBalances"][i]) - balances[key]
        for i, key in enumerate(keys)
        if int(meta["postBalances"][i]) != balances[key]
    }
    token_residuals = {
        keys[i]: int(post_tokens.get(i, {}).get("uiTokenAmount", {}).get("amount", 0))
        - tokens.get(keys[i], 0)
        for i in set(pre_tokens) | set(post_tokens)
        if int(post_tokens.get(i, {}).get("uiTokenAmount", {}).get("amount", 0))
        != tokens.get(keys[i], 0)
    }
    if market_transfers != 1:
        raise ValueError("EVENT_INSTRUCTION_ALIGNMENT: expected one exact canonical vault transfer")
    if residuals or token_residuals:
        raise ValueError(
            "PHYSICAL_BALANCE_MISMATCH: " + str({"SOL": residuals, "tokens": token_residuals})
        )
    return {
        "status": "PACKET_TRANSFERS_EXACT",
        "movements": trace,
        "lamport_residuals": residuals,
        "token_residuals": token_residuals,
        "ancillary": ancillary,
        "canonical_ownership_bank_required": True,
    }
