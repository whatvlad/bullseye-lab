# Supported standard fee-route coverage

Only the already-supported simple standard SOL route can authorize a candidate proof. Cashback, holder rewards and shared-creator routes remain excluded. The ordinary config-bound protocol buyback split remains part of the previously validated simple route.

Routing is classified after canonical current account validation. Serious candidates that fail before the route is decoded remain NOT_DETERMINED. They are not assumed to be simple or complex. The report shows both the simple fraction of all serious attempts and the fraction among route-determined attempts. The latter is censored by availability and evidence failures and is not a population estimate.

Observed coverage: 23/74 (31.08%) supported simple routes, 14/74 (18.92%) excluded complex routes and 37/74 (50%) undetermined. Among the 37 route-determined candidates, the simple fraction was 23/37 (62.16%). Complex exclusions were seven SHARED_CREATOR and seven HOLDER_REWARD cases. None of the 23 simple-route candidates completed a PASS; routing compatibility alone did not establish execution eligibility.

`analysis/supported_route_coverage.json` records SUPPORTED_SIMPLE_ROUTE, UNSUPPORTED_COMPLEX_ROUTE and unknown counts, exact denominators, observed complex branches and candidate-level classifications. A simple route classification is a prerequisite; it does not bypass a failed transaction, transfer, continuity, config, freshness or provider check.

No Mayhem, PumpSwap, migrated, ambiguous multi-event or unsupported-quote market was added to the cohort. Excluded markets are not sent through candidate proof or wallet enrichment. No permanent threshold or disagreement band was inferred from this sample.
