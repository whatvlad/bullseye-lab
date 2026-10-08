"""Canonical addresses using the Solana SDK and pinned official PDA seeds."""

from solders.pubkey import Pubkey

from .pump_idl import PUMP_AMM_PROGRAM_ID, PUMP_PROGRAM_ID

ASSOCIATED_TOKEN_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
FEE_PROGRAM = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"


def pda(program: str, seeds: list[bytes]) -> str:
    return str(Pubkey.find_program_address(seeds, Pubkey.from_string(program))[0])


def curve_address(mint: str) -> str:
    return pda(PUMP_PROGRAM_ID, [b"bonding-curve", bytes(Pubkey.from_string(mint))])


def associated_address(owner: str, mint: str, token_program: str) -> str:
    return pda(
        ASSOCIATED_TOKEN_PROGRAM,
        [
            bytes(Pubkey.from_string(owner)),
            bytes(Pubkey.from_string(token_program)),
            bytes(Pubkey.from_string(mint)),
        ],
    )


def pool_authority(mint: str) -> str:
    return pda(PUMP_PROGRAM_ID, [b"pool-authority", bytes(Pubkey.from_string(mint))])


def pool_address(index: int, creator: str, base_mint: str, quote_mint: str) -> str:
    return pool_address_and_bump(index, creator, base_mint, quote_mint)[0]


def pool_address_and_bump(
    index: int, creator: str, base_mint: str, quote_mint: str
) -> tuple[str, int]:
    address, bump = Pubkey.find_program_address(
        [
            b"pool",
            index.to_bytes(2, "little"),
            bytes(Pubkey.from_string(creator)),
            bytes(Pubkey.from_string(base_mint)),
            bytes(Pubkey.from_string(quote_mint)),
        ],
        Pubkey.from_string(PUMP_AMM_PROGRAM_ID),
    )
    return str(address), bump


def config_addresses() -> dict[str, tuple[str, str, str]]:
    return {
        "pump_global": (pda(PUMP_PROGRAM_ID, [b"global"]), PUMP_PROGRAM_ID, "Global"),
        "swap_global": (
            pda(PUMP_AMM_PROGRAM_ID, [b"global_config"]),
            PUMP_AMM_PROGRAM_ID,
            "GlobalConfig",
        ),
        "pump_fee": (
            pda(FEE_PROGRAM, [b"fee_config", bytes(Pubkey.from_string(PUMP_PROGRAM_ID))]),
            FEE_PROGRAM,
            "FeeConfig",
        ),
        "swap_fee": (
            pda(FEE_PROGRAM, [b"fee_config", bytes(Pubkey.from_string(PUMP_AMM_PROGRAM_ID))]),
            FEE_PROGRAM,
            "FeeConfig",
        ),
    }
