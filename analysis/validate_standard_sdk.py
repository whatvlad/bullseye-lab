"""Compare Python quotes with unmodified official SDK compiled pure functions.

Only a BigInt/BN and public-key equality adapter is supplied; package initialization,
RPC, wallet code and third-party package scripts are never executed.
"""
import hashlib
import json
import subprocess
from pathlib import Path

from memebot.paper.standard_math import buy_exact_tokens, buy_quote, select_fees, sell_quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
raw = (OUT / "pump_sdk_reference/index.js").read_text()
names = ["isSolLikeQuoteMint", "isStableQuoteMint", "selectCurveFeeSchedule", "isZeroFees",
         "calculateFeeTier", "scheduleFeesBps", "computeFeesBps", "getFee", "fee", "ceilDiv",
         "bondingCurveMarketCap", "getBuySolAmountFromTokenAmountQuote",
         "getBuyTokenAmountFromSolAmountQuote", "getSellSolAmountFromTokenAmountQuote",
         "getBuyTokenAmountFromSolAmount", "getBuySolAmountFromTokenAmount",
         "getSellSolAmountFromTokenAmount"]
functions = []
for name in names:
    start = raw.index("function " + name + "(")
    # The first brace may belong to the destructured parameter. Find the body
    # only after balanced parentheses, then retain its exact original bytes.
    paren = raw.index("(", start); depth = 1; cursor = paren + 1
    while depth:
        depth += (raw[cursor] == "(") - (raw[cursor] == ")"); cursor += 1
    body = raw.index("{", cursor); depth = 1; cursor = body + 1
    while depth:
        depth += (raw[cursor] == "{") - (raw[cursor] == "}"); cursor += 1
    functions.append(raw[start:cursor])
adapter = '''
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
'''
config = {"fee_tiers": [
    {"market_cap_lamports_threshold": 0, "fees": {"lp_fee_bps": 0, "protocol_fee_bps": 95, "creator_fee_bps": 30}},
    {"market_cap_lamports_threshold": 30_000_000_000, "fees": {"lp_fee_bps": 0, "protocol_fee_bps": 90, "creator_fee_bps": 20}},
]}
global_state = {"creator_fee_configurable": True, "max_configurable_creator_fee_bps": 300}
cases = []
for vq in (29_999_999_999, 30_000_000_000, 30_000_000_001):
    for override in (0, 77):
        for creator in ("11111111111111111111111111111111", "creator"):
            for budget in (10000, 1_000_000, 100_000_000):
                curve = dict(virtual_quote_reserves=vq, virtual_token_reserves=10**15,
                    real_token_reserves=793_100_000_000_000, real_quote_reserves=10_000_000_000,
                    quote_mint="11111111111111111111111111111111", creator=creator, creator_fee_bps=override)
                rates = select_fees(global_state, config, curve, 10**15)
                buy = buy_quote(curve, budget, rates)
                tokens = 1_000_000_000
                sell = sell_quote(curve, tokens, rates)
                exact = buy_exact_tokens(curve, buy["token_output"], rates)
                cases.append(dict(curve=curve, rates=rates, budget=budget, sell_tokens=tokens,
                    expected=dict(token_output=buy["token_output"], gross_buy=exact["gross_input"],
                                  net_sell=sell["net_output"])))
javascript = adapter + "\n".join(functions) + '''
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
'''
(OUT / "pump_sdk_reference/parity.js").write_text(javascript)
(OUT / "pump_sdk_reference/parity_inputs.json").write_text(json.dumps(dict(config=config, cases=cases)))
result = subprocess.run(["node", str(OUT / "pump_sdk_reference/parity.js"),
                         str(OUT / "pump_sdk_reference/parity_inputs.json")],
                         check=True, capture_output=True, text=True)
actual = json.loads(result.stdout)
assert len(actual) == len(cases)
mismatches = [{"case": index, "expected": c["expected"], "sdk": a}
              for index, (c, a) in enumerate(zip(cases, actual, strict=True))
              if {key: str(value) for key, value in c["expected"].items()} != a]
report = dict(sdk_version="2.0.0", cases=len(cases), integer_quote_comparisons=3*len(cases),
    mismatches=mismatches, sdk_source_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    reference_function_hashes={name:hashlib.sha256(code.encode()).hexdigest()
                               for name,code in zip(names,functions,strict=True)},
    tested=["tier boundary below/equal/above", "creator override", "creator zero", "buy budget floor",
            "buy exact-token ceil+1", "sell floor", "independent fee ceiling"],
    native_live_parity_validated=False,
    fee_components={"protocol":"VERIFIED_AT_CANDIDATE_STATE when bound; otherwise UNKNOWN",
                    "creator":"VERIFIED_AT_CANDIDATE_STATE for supported routing; otherwise UNKNOWN",
                    "external_costs":"ESTIMATED"})
(OUT / "standard_fee_validation.json").write_text(json.dumps(report,indent=2)+"\n")
assert not mismatches, mismatches[:3]
print(json.dumps({key:report[key] for key in ["sdk_version","cases","integer_quote_comparisons","mismatches"]}))
