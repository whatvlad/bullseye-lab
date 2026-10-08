
class BN {
 constructor(v){this.v=BigInt(v instanceof BN?v.v:v)}
 add(v){return new BN(this.v+v.v)} sub(v){return new BN(this.v-v.v)}
 mul(v){return new BN(this.v*v.v)} div(v){return new BN(this.v/v.v)}
 addn(v){return new BN(this.v+BigInt(v))} subn(v){return new BN(this.v-BigInt(v))}
 muln(v){return new BN(this.v*BigInt(v))} isZero(){return this.v===0n}
 eq(v){return this.v===v.v} lt(v){return this.v<v.v} gte(v){return this.v>=v.v}
 toString(){return this.v.toString()} static min(a,b){return a.lt(b)?a:b}
}
class Key {constructor(v){this.v=v} equals(other){return this.v===other.v}}
Key.default=new Key("zero");
const import_bn={default:BN}, import_bn5={default:BN};
const import_web3={PublicKey:Key}, import_web35={PublicKey:Key};
const ONE_BILLION_SUPPLY=new BN("1000000000000000");
const SOL_LIKE_QUOTE_MINTS=[Key.default,new Key("wsol")];
const STABLE_QUOTE_MINTS=[];
function isSolLikeQuoteMint(quoteMint) {
  return SOL_LIKE_QUOTE_MINTS.some((mint) => mint.equals(quoteMint));
}
function isStableQuoteMint(quoteMint) {
  return STABLE_QUOTE_MINTS.some((mint) => mint.equals(quoteMint));
}
function selectCurveFeeSchedule({
  feeConfig,
  quoteMint,
  marketCap
}) {
  if (isSolLikeQuoteMint(quoteMint)) {
    return calculateFeeTier({ feeTiers: feeConfig.feeTiers, marketCap });
  }
  if (isStableQuoteMint(quoteMint)) {
    return calculateFeeTier({
      feeTiers: feeConfig.stableFeeTiers.length > 0 ? feeConfig.stableFeeTiers : feeConfig.feeTiers,
      marketCap
    });
  }
  return isZeroFees(feeConfig.exoticFlatFees) ? feeConfig.flatFees : feeConfig.exoticFlatFees;
}
function isZeroFees({ lpFeeBps, protocolFeeBps, creatorFeeBps }) {
  return lpFeeBps.isZero() && protocolFeeBps.isZero() && creatorFeeBps.isZero();
}
function calculateFeeTier({
  feeTiers,
  marketCap
}) {
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
function scheduleFeesBps({
  global,
  feeConfig,
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
  quoteMint
}) {
  if (feeConfig != null) {
    const marketCap = bondingCurveMarketCap({
      mintSupply,
      virtualQuoteReserves,
      virtualTokenReserves
    });
    return selectCurveFeeSchedule({
      feeConfig,
      quoteMint: quoteMint ?? import_web3.PublicKey.default,
      marketCap
    });
  }
  return {
    protocolFeeBps: global.feeBasisPoints,
    creatorFeeBps: global.creatorFeeBasisPoints
  };
}
function computeFeesBps({
  global,
  feeConfig,
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
  quoteMint,
  creatorFeeBps
}) {
  const schedule = scheduleFeesBps({
    global,
    feeConfig,
    mintSupply,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint
  });
  if (!global.creatorFeeConfigurable || creatorFeeBps == null || creatorFeeBps.isZero()) {
    return schedule;
  }
  return { protocolFeeBps: schedule.protocolFeeBps, creatorFeeBps };
}
function getFee({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  isNewBondingCurve
}) {
  const { virtualQuoteReserves, virtualTokenReserves, isMayhemMode } = bondingCurve;
  const { protocolFeeBps, creatorFeeBps } = computeFeesBps({
    global,
    feeConfig,
    mintSupply: isMayhemMode ? mintSupply : ONE_BILLION_SUPPLY,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint: bondingCurve.quoteMint,
    creatorFeeBps: bondingCurve.creatorFeeBps
  });
  return fee(amount, protocolFeeBps).add(
    isNewBondingCurve || !import_web3.PublicKey.default.equals(bondingCurve.creator) ? fee(amount, creatorFeeBps) : new import_bn.default(0)
  );
}
function fee(amount, feeBasisPoints) {
  return ceilDiv(amount.mul(feeBasisPoints), new import_bn.default(1e4));
}
function ceilDiv(a, b) {
  return a.add(b.subn(1)).div(b);
}
function bondingCurveMarketCap({
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves
}) {
  if (virtualTokenReserves.isZero()) {
    throw new Error("Division by zero: virtual token reserves cannot be zero");
  }
  return virtualQuoteReserves.mul(mintSupply).div(virtualTokenReserves);
}
function getBuySolAmountFromTokenAmountQuote({
  minAmount,
  virtualTokenReserves,
  virtualQuoteReserves
}) {
  return minAmount.mul(virtualQuoteReserves).div(virtualTokenReserves.sub(minAmount)).add(new import_bn5.default(1));
}
function getBuyTokenAmountFromSolAmountQuote({
  inputAmount,
  virtualTokenReserves,
  virtualQuoteReserves
}) {
  return inputAmount.mul(virtualTokenReserves).div(virtualQuoteReserves.add(inputAmount));
}
function getSellSolAmountFromTokenAmountQuote({
  inputAmount,
  virtualTokenReserves,
  virtualQuoteReserves
}) {
  return inputAmount.mul(virtualQuoteReserves).div(virtualTokenReserves.add(inputAmount));
}
function getBuyTokenAmountFromSolAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  quoteMint,
  quoteControl,
  creatorFeeBps
}) {
  if (amount.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  let isNewBondingCurve = false;
  if (bondingCurve === null || mintSupply === null) {
    bondingCurve = newBondingCurve(
      global,
      quoteMint,
      quoteControl,
      creatorFeeBps
    );
    mintSupply = global.tokenTotalSupply;
    isNewBondingCurve = true;
  }
  if (bondingCurve.virtualTokenReserves.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  const { virtualQuoteReserves, virtualTokenReserves } = bondingCurve;
  const { protocolFeeBps, creatorFeeBps: chargedCreatorFeeBps } = computeFeesBps({
    global,
    feeConfig,
    mintSupply,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint: bondingCurve.quoteMint,
    creatorFeeBps: bondingCurve.creatorFeeBps
  });
  const totalFeeBasisPoints = protocolFeeBps.add(
    isNewBondingCurve || !import_web35.PublicKey.default.equals(bondingCurve.creator) ? chargedCreatorFeeBps : new import_bn5.default(0)
  );
  const inputAmount = amount.subn(1).muln(1e4).div(totalFeeBasisPoints.addn(1e4));
  const tokensReceived = getBuyTokenAmountFromSolAmountQuote({
    inputAmount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves
  });
  return import_bn5.default.min(tokensReceived, bondingCurve.realTokenReserves);
}
function getBuySolAmountFromTokenAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  quoteMint,
  quoteControl,
  creatorFeeBps
}) {
  if (amount.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  let isNewBondingCurve = false;
  if (bondingCurve === null || mintSupply === null) {
    bondingCurve = newBondingCurve(
      global,
      quoteMint,
      quoteControl,
      creatorFeeBps
    );
    mintSupply = global.tokenTotalSupply;
    isNewBondingCurve = true;
  }
  if (bondingCurve.virtualTokenReserves.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  const minAmount = import_bn5.default.min(amount, bondingCurve.realTokenReserves);
  const solCost = getBuySolAmountFromTokenAmountQuote({
    minAmount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves
  });
  return solCost.add(
    getFee({
      global,
      feeConfig,
      mintSupply,
      bondingCurve,
      amount: solCost,
      isNewBondingCurve
    })
  );
}
function getSellSolAmountFromTokenAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount
}) {
  if (amount.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  if (bondingCurve.virtualTokenReserves.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  const solCost = getSellSolAmountFromTokenAmountQuote({
    inputAmount: amount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves
  });
  return solCost.sub(
    getFee({
      global,
      feeConfig,
      mintSupply,
      bondingCurve,
      amount: solCost,
      isNewBondingCurve: false
    })
  );
}
const fs=require("fs"); const input=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const results=input.cases.map(c=>{
 const b=n=>new BN(String(n));
 const global={creatorFeeConfigurable:true};
 const feeConfig={feeTiers:input.config.fee_tiers.map(t=>({marketCapLamportsThreshold:b(t.market_cap_lamports_threshold),
  fees:{lpFeeBps:b(0),protocolFeeBps:b(t.fees.protocol_fee_bps),creatorFeeBps:b(t.fees.creator_fee_bps)}}))};
 const x=c.curve;
 const bondingCurve={virtualQuoteReserves:b(x.virtual_quote_reserves),virtualTokenReserves:b(x.virtual_token_reserves),
  realTokenReserves:b(x.real_token_reserves),creator:x.creator.startsWith("1111")?Key.default:new Key("creator"),
  quoteMint:Key.default,creatorFeeBps:b(x.creator_fee_bps),isMayhemMode:false};
 const params={global,feeConfig,mintSupply:ONE_BILLION_SUPPLY,bondingCurve};
 const tokens=getBuyTokenAmountFromSolAmount({...params,amount:b(c.budget)});
 const gross=getBuySolAmountFromTokenAmount({...params,amount:tokens});
 const net=getSellSolAmountFromTokenAmount({...params,amount:b(c.sell_tokens)});
 return {token_output:tokens.toString(),gross_buy:gross.toString(),net_sell:net.toString()};
}); process.stdout.write(JSON.stringify(results));
