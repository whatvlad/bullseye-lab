import { NATIVE_MINT_2022 } from "@solana/spl-token";
import { PublicKey } from "@solana/web3.js";
import BN from "bn.js";

import { UnsupportedQuoteMintError } from "./errors";
import { computeFeesBps, getFee } from "./fees";
import { isLegacyQuoteMint } from "./pda";
import { BondingCurve, FeeConfig, Global, QuoteControl } from "./state";

/**
 * The `virtualQuoteReserves` a new curve quoted in `quoteMint` starts from,
 * the way `create_v2` seeds it: SOL (WSOL or the zero key) from
 * `Global.initialVirtualSolReserves`, a mint whitelisted on `Global` from
 * `Global.initialVirtualQuoteReserves` (even when quote control lists it too),
 * and a mint admitted through quote control from its entry. The Token-2022
 * native mint always throws `UnsupportedQuoteMintError`: `create_v2` rejects
 * it before consulting either list.
 *
 * @param quoteControl - The decoded `QuoteControl` PDA, or `null` when the
 * account does not exist yet (an empty list). Pass it whenever the mint may
 * be a quote-control mint: a mint in neither list then throws
 * `UnsupportedQuoteMintError`, as `create_v2` would reject it. When omitted,
 * an unlisted mint falls back to `Global.initialVirtualQuoteReserves` — what
 * callers that predate quote control always got — and quote-control mints
 * are seeded wrong.
 */
export function initialVirtualQuoteReservesFor(
  global: Global,
  quoteMint: PublicKey,
  quoteControl?: QuoteControl | null,
): BN {
  if (isLegacyQuoteMint(quoteMint)) {
    return global.initialVirtualSolReserves;
  }

  // Checked before either list, as `create_v2` does: pump-fees treats this
  // key as SOL, but it cannot quote a curve whichever list admits it.
  if (quoteMint.equals(NATIVE_MINT_2022)) {
    throw new UnsupportedQuoteMintError(quoteMint);
  }

  // `quoteMint` is non-zero here, so an empty (zero-key) whitelist slot can
  // never match.
  if (global.whitelistedQuoteMints.some((mint) => mint.equals(quoteMint))) {
    return global.initialVirtualQuoteReserves;
  }

  const entry = quoteControl?.mints.find((candidate) =>
    candidate.mint.equals(quoteMint),
  );
  if (entry) {
    return entry.initialVirtualQuoteReserves;
  }

  if (quoteControl !== undefined) {
    throw new UnsupportedQuoteMintError(quoteMint);
  }

  return global.initialVirtualQuoteReserves;
}

/**
 * The curve `create_v2` would initialize for `quoteMint`.
 *
 * @param quoteControl - See `initialVirtualQuoteReservesFor`; required for a
 * quote-control mint to be seeded correctly.
 * @param creatorFeeBps - The `creator_fee_bps` the create is sent with
 * (`createV2Instruction`'s `creatorFeeBps`); omitted or zero means the
 * schedule rate. `create_v2` always stores `canEditCreatorFee = false`.
 * @param isHolderReward - Whether the create is sent with `holderReward`
 * (`createV2Instruction`'s `holderReward`): the curve's creator is then the
 * coin's `holderRewardsPda(mint)`, which this function cannot derive without
 * the mint, so `creator` stays the zero key either way.
 */
export function newBondingCurve(
  global: Global,
  quoteMint: PublicKey = PublicKey.default,
  quoteControl?: QuoteControl | null,
  creatorFeeBps?: BN,
  isHolderReward = false,
): BondingCurve {
  // The type never admitted `null`, but the pre-quote-control code treated any
  // falsy quote as SOL at runtime and untyped callers rely on it.
  const quote = quoteMint ?? PublicKey.default;

  return {
    virtualTokenReserves: global.initialVirtualTokenReserves,
    virtualQuoteReserves: initialVirtualQuoteReservesFor(
      global,
      quote,
      quoteControl,
    ),
    realTokenReserves: global.initialRealTokenReserves,
    realQuoteReserves: new BN(0),
    tokenTotalSupply: global.tokenTotalSupply,
    complete: false,
    creator: PublicKey.default,
    isMayhemMode: global.mayhemModeEnabled,
    isCashbackCoin: false,
    // Stored the way the program stores it: the zero key for SOL curves.
    quoteMint: isLegacyQuoteMint(quote) ? PublicKey.default : quote,
    creatorFeeBps: creatorFeeBps ?? new BN(0),
    canEditCreatorFee: false,
    isHolderReward,
  };
}

function getBuySolAmountFromTokenAmountQuote({
  minAmount,
  virtualTokenReserves,
  virtualQuoteReserves,
}: {
  minAmount: BN;
  virtualTokenReserves: BN;
  virtualQuoteReserves: BN;
}): BN {
  return minAmount
    .mul(virtualQuoteReserves)
    .div(virtualTokenReserves.sub(minAmount))
    .add(new BN(1));
}

function getBuyTokenAmountFromSolAmountQuote({
  inputAmount,
  virtualTokenReserves,
  virtualQuoteReserves,
}: {
  inputAmount: BN;
  virtualTokenReserves: BN;
  virtualQuoteReserves: BN;
}): BN {
  return inputAmount
    .mul(virtualTokenReserves)
    .div(virtualQuoteReserves.add(inputAmount));
}

function getSellSolAmountFromTokenAmountQuote({
  inputAmount,
  virtualTokenReserves,
  virtualQuoteReserves,
}: {
  inputAmount: BN;
  virtualTokenReserves: BN;
  virtualQuoteReserves: BN;
}): BN {
  return inputAmount
    .mul(virtualQuoteReserves)
    .div(virtualTokenReserves.add(inputAmount));
}

/**
 * @param params.quoteMint - Selects the quote when `bondingCurve` is `null`
 * (a curve about to be created); an existing curve's own `quoteMint` is
 * authoritative for fee selection.
 * @param params.quoteControl - The decoded `QuoteControl` PDA (or `null` when
 * it does not exist), needed to seed a new curve quoted in a quote-control
 * mint; see `initialVirtualQuoteReservesFor`.
 * @param params.creatorFeeBps - Used only when `bondingCurve` is `null`: the
 * `creator_fee_bps` the create is sent with, so the first buy is quoted at
 * the rate the program will charge. An existing curve's own `creatorFeeBps`
 * is authoritative.
 */
export function getBuyTokenAmountFromSolAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  quoteMint,
  quoteControl,
  creatorFeeBps,
}: {
  global: Global;
  feeConfig: FeeConfig | null;
  mintSupply: BN | null;
  bondingCurve: BondingCurve | null;
  amount: BN;
  quoteMint: PublicKey;
  quoteControl?: QuoteControl | null;
  creatorFeeBps?: BN;
}): BN {
  if (amount.eq(new BN(0))) {
    return new BN(0);
  }

  let isNewBondingCurve = false;

  if (bondingCurve === null || mintSupply === null) {
    bondingCurve = newBondingCurve(
      global,
      quoteMint,
      quoteControl,
      creatorFeeBps,
    );
    mintSupply = global.tokenTotalSupply;
    isNewBondingCurve = true;
  }

  // migrated bonding curve
  if (bondingCurve.virtualTokenReserves.eq(new BN(0))) {
    return new BN(0);
  }

  const { virtualQuoteReserves, virtualTokenReserves } = bondingCurve;
  const { protocolFeeBps, creatorFeeBps: chargedCreatorFeeBps } =
    computeFeesBps({
      global,
      feeConfig,
      mintSupply,
      virtualQuoteReserves,
      virtualTokenReserves,
      quoteMint: bondingCurve.quoteMint,
      creatorFeeBps: bondingCurve.creatorFeeBps,
    });

  const totalFeeBasisPoints = protocolFeeBps.add(
    isNewBondingCurve || !PublicKey.default.equals(bondingCurve.creator)
      ? chargedCreatorFeeBps
      : new BN(0),
  );

  const inputAmount = amount
    .subn(1)
    .muln(10_000)
    .div(totalFeeBasisPoints.addn(10_000));

  const tokensReceived = getBuyTokenAmountFromSolAmountQuote({
    inputAmount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves,
  });

  return BN.min(tokensReceived, bondingCurve.realTokenReserves);
}

/**
 * @param params.quoteMint - Selects the quote when `bondingCurve` is `null`
 * (a curve about to be created); an existing curve's own `quoteMint` is
 * authoritative for fee selection.
 * @param params.quoteControl - The decoded `QuoteControl` PDA (or `null` when
 * it does not exist), needed to seed a new curve quoted in a quote-control
 * mint; see `initialVirtualQuoteReservesFor`.
 * @param params.creatorFeeBps - Used only when `bondingCurve` is `null`; see
 * `getBuyTokenAmountFromSolAmount`.
 */
export function getBuySolAmountFromTokenAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  quoteMint,
  quoteControl,
  creatorFeeBps,
}: {
  global: Global;
  feeConfig: FeeConfig | null;
  mintSupply: BN | null;
  bondingCurve: BondingCurve | null;
  amount: BN;
  quoteMint: PublicKey;
  quoteControl?: QuoteControl | null;
  creatorFeeBps?: BN;
}): BN {
  if (amount.eq(new BN(0))) {
    return new BN(0);
  }

  let isNewBondingCurve = false;

  if (bondingCurve === null || mintSupply === null) {
    bondingCurve = newBondingCurve(
      global,
      quoteMint,
      quoteControl,
      creatorFeeBps,
    );
    mintSupply = global.tokenTotalSupply;
    isNewBondingCurve = true;
  }

  // migrated bonding curve
  if (bondingCurve.virtualTokenReserves.eq(new BN(0))) {
    return new BN(0);
  }

  const minAmount = BN.min(amount, bondingCurve.realTokenReserves);

  const solCost = getBuySolAmountFromTokenAmountQuote({
    minAmount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves,
  });

  return solCost.add(
    getFee({
      global,
      feeConfig,
      mintSupply,
      bondingCurve,
      amount: solCost,
      isNewBondingCurve,
    }),
  );
}

export function getSellSolAmountFromTokenAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
}: {
  global: Global;
  feeConfig: FeeConfig | null;
  mintSupply: BN;
  bondingCurve: BondingCurve;
  amount: BN;
}): BN {
  if (amount.eq(new BN(0))) {
    return new BN(0);
  }

  // migrated bonding curve
  if (bondingCurve.virtualTokenReserves.eq(new BN(0))) {
    return new BN(0);
  }

  const solCost = getSellSolAmountFromTokenAmountQuote({
    inputAmount: amount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves,
  });

  return solCost.sub(
    getFee({
      global,
      feeConfig,
      mintSupply,
      bondingCurve,
      amount: solCost,
      isNewBondingCurve: false,
    }),
  );
}

export function getStaticRandomFeeRecipient(): PublicKey {
  const randomIndex = Math.floor(Math.random() * CURRENT_FEE_RECIPIENTS.length);
  return new PublicKey(CURRENT_FEE_RECIPIENTS[randomIndex]);
}

const CURRENT_FEE_RECIPIENTS = [
  "62qc2CNXwrYqQScmEdiZFFAnJR262PxWEuNQtxfafNgV",
  "7VtfL8fvgNfhz17qKRMjzQEXgbdpnHHHQRh54R9jP2RJ",
  "7hTckgnGnLQR6sdH7YkqFTAA7VwTfYFaZ6EhEsU3saCX",
  "9rPYyANsfQZw3DnDmKE3YCQF5E8oD89UXoHn9JFEhJUz",
  "AVmoTthdrX6tKt4nDjco2D775W2YK3sDhxPcMmzUAmTY",
  "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM",
  "FWsW1xNtWscwNmKv6wVsU1iTzRN6wmmk3MjxRP5tT7hz",
  "G5UZAVbAf46s7cKWoyKu8kYTip9DGTpbLZ2qa9Aq69dP",
];

export function getStaticRandomFeeRecipientForBuyback(): PublicKey {
  const randomIndex = Math.floor(
    Math.random() * CURRENT_FEE_RECIPIENTS_FOR_BUYBACK.length,
  );
  return new PublicKey(CURRENT_FEE_RECIPIENTS_FOR_BUYBACK[randomIndex]);
}

const CURRENT_FEE_RECIPIENTS_FOR_BUYBACK = [
  "5YxQFdt3Tr9zJLvkFccqXVUwhdTWJQc1fFg2YPbxvxeD",
  "9M4giFFMxmFGXtc3feFzRai56WbBqehoSeRE5GK7gf7",
  "GXPFM2caqTtQYC2cJ5yJRi9VDkpsYZXzYdwYpGnLmtDL",
  "3BpXnfJaUTiwXnJNe7Ej1rcbzqTTQUvLShZaWazebsVR",
  "5cjcW9wExnJJiqgLjq7DEG75Pm6JBgE1hNv4B2vHXUW6",
  "EHAAiTxcdDwQ3U4bU6YcMsQGaekdzLS3B5SmYo46kJtL",
  "5eHhjP8JaYkz83CWwvGU2uMUXefd3AazWGx4gpcuEEYD",
  "A7hAgCzFw14fejgCp387JUJRMNyz4j89JKnhtKU8piqW",
];

export function bondingCurveMarketCap({
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
}: {
  mintSupply: BN;
  virtualQuoteReserves: BN;
  virtualTokenReserves: BN;
}): BN {
  if (virtualTokenReserves.isZero()) {
    throw new Error("Division by zero: virtual token reserves cannot be zero");
  }
  return virtualQuoteReserves.mul(mintSupply).div(virtualTokenReserves);
}
