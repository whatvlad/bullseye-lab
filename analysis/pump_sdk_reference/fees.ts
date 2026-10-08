import { NATIVE_MINT, NATIVE_MINT_2022 } from "@solana/spl-token";
import { PublicKey } from "@solana/web3.js";
import BN from "bn.js";

import { bondingCurveMarketCap } from "./bondingCurve";
import { FeeConfig, Global, Fees, BondingCurve, FeeTier } from "./state";

export const ONE_BILLION_SUPPLY = new BN(1_000_000_000_000_000);

/**
 * Quote mints pump-fees charges `feeTiers` for on a canonical pump pool or
 * curve: the zero key legacy bonding curves store for SOL, legacy WSOL and the
 * Token-2022 native mint. Mirrors `pump_fees::state::is_sol_like_quote_mint`.
 *
 * Deliberately wider than `isLegacyQuoteMint` (pda.ts): `create_v2` rejects
 * the Token-2022 native mint as a quote, so builders only ever treat WSOL and
 * the zero key as SOL, but the fee program classifies all three as SOL-like.
 */
export const SOL_LIKE_QUOTE_MINTS: readonly PublicKey[] = Object.freeze([
  PublicKey.default,
  NATIVE_MINT,
  NATIVE_MINT_2022,
]);

/**
 * Quote mints pump-fees charges `stableFeeTiers` for on a canonical pump pool
 * or curve. Hardcoded on-chain (`pump_fees::state::STABLE_QUOTE_MINTS`), so
 * hardcoded here: widening it is a program upgrade. Devnet USDC
 * (`4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU`) is not listed on-chain and
 * is therefore not listed here — devnet USDC curves pay the exotic schedule.
 */
export const STABLE_QUOTE_MINTS: readonly PublicKey[] = Object.freeze([
  new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
]);

export function isSolLikeQuoteMint(quoteMint: PublicKey): boolean {
  return SOL_LIKE_QUOTE_MINTS.some((mint) => mint.equals(quoteMint));
}

export function isStableQuoteMint(quoteMint: PublicKey): boolean {
  return STABLE_QUOTE_MINTS.some((mint) => mint.equals(quoteMint));
}

/**
 * A quote mint that is neither SOL-like nor a listed stable, which pump-fees
 * charges `exoticFlatFees` for (or `flatFees` while that schedule is unset).
 */
export function isExoticQuoteMint(quoteMint: PublicKey): boolean {
  return !isSolLikeQuoteMint(quoteMint) && !isStableQuoteMint(quoteMint);
}

export interface CalculatedFeesBps {
  protocolFeeBps: BN;
  creatorFeeBps: BN;
}

export function getFee({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  isNewBondingCurve,
}: {
  global: Global;
  feeConfig: FeeConfig | null;
  mintSupply: BN;
  bondingCurve: BondingCurve;
  amount: BN;
  isNewBondingCurve: boolean;
}) {
  const { virtualQuoteReserves, virtualTokenReserves, isMayhemMode } =
    bondingCurve;
  const { protocolFeeBps, creatorFeeBps } = computeFeesBps({
    global,
    feeConfig,
    mintSupply: isMayhemMode ? mintSupply : ONE_BILLION_SUPPLY,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint: bondingCurve.quoteMint,
    creatorFeeBps: bondingCurve.creatorFeeBps,
  });

  return fee(amount, protocolFeeBps).add(
    isNewBondingCurve || !PublicKey.default.equals(bondingCurve.creator)
      ? fee(amount, creatorFeeBps)
      : new BN(0),
  );
}

/**
 * The fee rates a bonding-curve trade pays.
 *
 * @param params.quoteMint - The curve's quote mint as stored on chain
 * (`bondingCurve.quoteMint`, `PublicKey.default` for SOL curves). Selects the
 * fee schedule the way pump-fees does; omitted (or a runtime `null`) means
 * SOL.
 * @param params.creatorFeeBps - The curve's own creator rate
 * (`bondingCurve.creatorFeeBps`). While `global.creatorFeeConfigurable` is on,
 * a nonzero value replaces the schedule's creator rate, as pump's
 * `compute_fees` does after the pump-fees CPI; zero, omitted (or a runtime
 * `null`) means the schedule rate. The protocol rate is never affected.
 */
export function computeFeesBps({
  global,
  feeConfig,
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
  quoteMint,
  creatorFeeBps,
}: {
  global: Global;
  feeConfig: FeeConfig | null;
  mintSupply: BN;
  virtualQuoteReserves: BN;
  virtualTokenReserves: BN;
  quoteMint?: PublicKey;
  creatorFeeBps?: BN;
}): CalculatedFeesBps {
  const schedule = scheduleFeesBps({
    global,
    feeConfig,
    mintSupply,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint,
  });

  // A `Global` decoded from the live 1045-byte account reads the gate as
  // `false`; a curve hand-built before the field existed carries `undefined`.
  if (
    !global.creatorFeeConfigurable ||
    creatorFeeBps == null ||
    creatorFeeBps.isZero()
  ) {
    return schedule;
  }

  return { protocolFeeBps: schedule.protocolFeeBps, creatorFeeBps };
}

/** `computeFeesBps` before the per-coin creator rate: the schedule's rates. */
function scheduleFeesBps({
  global,
  feeConfig,
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
  quoteMint,
}: {
  global: Global;
  feeConfig: FeeConfig | null;
  mintSupply: BN;
  virtualQuoteReserves: BN;
  virtualTokenReserves: BN;
  quoteMint?: PublicKey;
}): CalculatedFeesBps {
  if (feeConfig != null) {
    const marketCap = bondingCurveMarketCap({
      mintSupply,
      virtualQuoteReserves,
      virtualTokenReserves,
    });

    // A decoded curve always carries a key, but curves hand-built before the
    // field existed carry `undefined` or `null`; both mean SOL, as in
    // `normalizeQuoteMint`.
    return selectCurveFeeSchedule({
      feeConfig,
      quoteMint: quoteMint ?? PublicKey.default,
      marketCap,
    });
  }

  return {
    protocolFeeBps: global.feeBasisPoints,
    creatorFeeBps: global.creatorFeeBasisPoints,
  };
}

/**
 * The fee schedule a canonical pump bonding curve (or its canonical pool) pays,
 * selected by quote mint the way `FeeConfig::fees_for_quote_mint` does with
 * `is_pump_pool = true`: SOL-like quotes pay the market-cap tier from
 * `feeTiers`, listed stables the tier from `stableFeeTiers`, everything else
 * `exoticFlatFees` — or `flatFees` while that schedule is unset (all-zero).
 *
 * @param params.marketCap - Market cap in the quote mint's base units (lamports
 * for SOL curves), as `bondingCurveMarketCap` computes it.
 */
export function selectCurveFeeSchedule({
  feeConfig,
  quoteMint,
  marketCap,
}: {
  feeConfig: FeeConfig;
  quoteMint: PublicKey;
  marketCap: BN;
}): Fees {
  if (isSolLikeQuoteMint(quoteMint)) {
    return calculateFeeTier({ feeTiers: feeConfig.feeTiers, marketCap });
  }

  if (isStableQuoteMint(quoteMint)) {
    // A FeeConfig written before `stable_fee_tiers` existed decodes to an empty
    // list. On chain an empty schedule is an invariant violation, so mirror
    // what such an account charged: the SOL tiers.
    return calculateFeeTier({
      feeTiers:
        feeConfig.stableFeeTiers.length > 0
          ? feeConfig.stableFeeTiers
          : feeConfig.feeTiers,
      marketCap,
    });
  }

  return isZeroFees(feeConfig.exoticFlatFees)
    ? feeConfig.flatFees
    : feeConfig.exoticFlatFees;
}

function isZeroFees({ lpFeeBps, protocolFeeBps, creatorFeeBps }: Fees) {
  return lpFeeBps.isZero() && protocolFeeBps.isZero() && creatorFeeBps.isZero();
}

/// rust reference: pump-fees-math::calculate_fee_tier()
export function calculateFeeTier({
  feeTiers,
  marketCap,
}: {
  feeTiers: FeeTier[];
  marketCap: BN;
}): Fees {
  if (feeTiers.length === 0) {
    throw new Error("Fee tiers cannot be empty");
  }

  const firstTier = feeTiers[0];

  if (marketCap.lt(firstTier.marketCapLamportsThreshold)) {
    return firstTier.fees;
  }

  for (const tier of feeTiers.slice().reverse()) {
    if (marketCap.gte(tier.marketCapLamportsThreshold)) {
      return tier.fees;
    }
  }

  return firstTier.fees;
}

function fee(amount: BN, feeBasisPoints: BN): BN {
  return ceilDiv(amount.mul(feeBasisPoints), new BN(10_000));
}

function ceilDiv(a: BN, b: BN): BN {
  return a.add(b.subn(1)).div(b);
}

export function getFeeRecipient(
  global: Global,
  mayhemMode: boolean,
): PublicKey {
  if (mayhemMode) {
    const feeRecipients = [
      global.reservedFeeRecipient,
      ...global.reservedFeeRecipients,
    ];
    return feeRecipients[Math.floor(Math.random() * feeRecipients.length)];
  }
  const feeRecipients = [global.feeRecipient, ...global.feeRecipients];
  return feeRecipients[Math.floor(Math.random() * feeRecipients.length)];
}
