# Research data quality and reproducibility

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

Export: repeatable-read, READ ONLY PostgreSQL; 2026-10-01 07:27:25.853291+00:00. No current market APIs or trading process was used. Per-file counts and SHA256 are in `analysis/source_manifest.json`; source data stays under ignored `research_sessions/`.

| Universe | N total | N usable for indicated purpose | N HIGH |
|---|---|---|---|
| Discoveries | 171676 | 8245 | 0 |
| Closed positions | 225 | 215 | 0 |
| Tick excursions | 225 | 198 | 0 |
| All-offset entry comparisons | 225 | 0 | 0 |
| Tokens at first anchor, 300s bounded label | 8245 | 3 | 0 |

Position quality: {'LOW': 160, 'MEDIUM': 65}. Token anchor quality: {'LOW': 7909, 'MEDIUM': 336}. Every position and trade-covered token has a row in `data_quality.json/csv`. Feature/decision-only and launch-only tokens lack price follow-up; their unusable count is shown rather than silently labelled zero.

MEDIUM: two-sided observed timestamps and gaps ≤2s in the evaluated interval. LOW: missing baseline/end/extrema, larger gaps, unknown reserves or conflicting evidence. HIGH would require independently validated source timestamps and complete stream coverage; none meet that standard. PumpPortal's historical source stamps were receipt times even when an older schema said estimated=false. Native events may have slots but receipt of all events is not established. Gap thresholds score observed coverage only; quiet trading and dropped events cannot be distinguished.

Holder coverage is a risk snapshot, not holder growth. Wallet coverage is observed addresses, not independently verified smart-wallet PnL. Funding graphs/insider attribution are unknown. Provider health transitions were exported; a provider error overlapping a position does not prove its price history is corrupt or causally explain a loss. No assumed zero is substituted for absent evidence.

Cappuccinu's RPC exit mark was 73.33% below its nearby feed tick; FLETCH's was 21.77% below. Recorded RPC extrema do not have a complete matching tick chronology. Those positions are excluded from net timing/avoided-loss reconstruction. Stored market marks and integer execution formulas alone cannot certify executable profit.

Reproduce into a NEW raw directory, then derive outputs:

```powershell
.venv\Scripts\python.exe -m memebot.research.strategy_capture --output research_sessions/strategy-new
.venv\Scripts\python.exe -m memebot.research.runner_study --source research_sessions/strategy-new --output analysis
.venv\Scripts\python.exe -m memebot.research.runner_reports --source research_sessions/strategy-new --analysis analysis --docs docs
```

The exporter refuses an existing destination. Reports are descriptive mixed-history statistics, not holdout evaluation. Common timing panels, rejected simulation reasons, unknown MAE times and conditional-only results are explicit. A new dataset will require reviewing narrative case conclusions rather than automatically trusting old statements.