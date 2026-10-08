# Versioned strategies

Status: Phase 4 implemented

The runner evaluates four independent immutable configurations on every risk
assessment:

| Preset | Entry / watch | Risk limit | Window | Minimum trades | Minimum age |
| --- | --- | ---: | ---: | ---: | ---: |
| Conservative | 80 / 70 | 30 | 60s | 8 | 30s |
| Balanced | 70 / 60 | 50 | 30s | 5 | 10s |
| Aggressive | 60 / 50 | 70 | 10s | 2 | 0s |

Aggressive is marked active by default, as required, but “active” currently means
the primary decision stream only. The possible actions are `enter_candidate`,
`watch`, and `skip`; none can create an order or alter a portfolio in Phase 4.

Before an entry candidate is emitted, the strategy requires:

- Phase 3 `allowed=true` and no hard reject;
- risk score within the preset limit;
- a permitted deterministic market regime;
- minimum token age and trade count;
- sufficient score-component completeness;
- final score at or above the preset threshold.

Regimes include new launch, early momentum, bonding curve, final stretch,
graduation, post-graduation, mature momentum, dead/illiquid, and unknown. Early
momentum requires a bonding-curve token no older than 120 seconds plus a momentum
score of at least 65; this classifier consumes only the current decision snapshot.

Configuration UUIDs derive from canonical serialized parameters. Decisions derive
from the risk-event ID plus configuration-version ID, making replay idempotent and
comparable across strategies.

Commands:

```powershell
bullseye strategies
bullseye decisions <mint> --limit 10
bullseye decisions <mint> --strategy aggressive --limit 10
```

Changing strategy parameters must create a new version rather than rewriting
historical parameters. Phase 6 selection changes only which existing version is
active for new paper entries; it does not rewrite historical configuration.

## Integrated graduation velocity

This Phase 9A component is a research hypothesis, not a calibrated win
probability. Conservative, Balanced, and Aggressive now all give it 25% configured
weight whenever decision-time bonding-curve evidence is available. It combines
curve progress, net real-SOL reserve velocity, buy/sell flow, buyer volume
concentration (HHI), and largest-buyer share. Outside the curve, the unavailable
component is explicitly omitted and the remaining weights are renormalized.

Open paper positions also have a strategy-independent `dump_hazard` overlay. A
close requires a current sell plus both an outlier/drop condition and confirming
sell pressure, drawdown, or reserve outflow. It does not react to a single small
sell in isolation.
