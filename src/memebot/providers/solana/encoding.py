from __future__ import annotations

from dataclasses import dataclass

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class BorshDecodeError(ValueError):
    """Raised when untrusted on-chain bytes do not match the pinned schema."""


def decode_base58(value: str) -> bytes:
    number = 0
    for character in value:
        number = number * 58 + BASE58_ALPHABET.index(character)
    body = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\0" * (len(value) - len(value.lstrip("1"))) + body


def encode_base58(data: bytes) -> str:
    """Encode bytes using Solana's Bitcoin-style base58 alphabet."""
    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    number = int.from_bytes(data, byteorder="big", signed=False)
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    return (BASE58_ALPHABET[0] * leading_zeroes) + encoded


@dataclass(slots=True)
class BorshReader:
    data: bytes
    offset: int = 0

    def _read(self, size: int) -> bytes:
        end = self.offset + size
        if size < 0 or end > len(self.data):
            raise BorshDecodeError("truncated Borsh payload")
        value = self.data[self.offset : end]
        self.offset = end
        return value

    def u8(self) -> int:
        return int.from_bytes(self._read(1), "little")

    def u16(self) -> int:
        return int.from_bytes(self._read(2), "little")

    def u32(self) -> int:
        return int.from_bytes(self._read(4), "little")

    def u64(self) -> int:
        return int.from_bytes(self._read(8), "little")

    def i64(self) -> int:
        return int.from_bytes(self._read(8), "little", signed=True)

    def i128(self) -> int:
        return int.from_bytes(self._read(16), "little", signed=True)

    def boolean(self) -> bool:
        value = self.u8()
        if value not in {0, 1}:
            raise BorshDecodeError("invalid Borsh boolean")
        return bool(value)

    def pubkey(self) -> str:
        return encode_base58(self._read(32))

    def string(self, *, maximum_bytes: int = 4096) -> str:
        size = self.u32()
        if size > maximum_bytes:
            raise BorshDecodeError("Borsh string exceeds safety limit")
        try:
            return self._read(size).decode("utf-8")
        except UnicodeDecodeError as error:
            raise BorshDecodeError("invalid UTF-8 in Borsh string") from error
