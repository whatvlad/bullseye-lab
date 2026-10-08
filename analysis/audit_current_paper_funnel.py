"""Read-only attribution of the current PAPER experiment's entry funnel."""
import asyncio
import json
from collections import Counter, defaultdict
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy import select, func
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    ExperimentRunRecord, StrategyDecisionRecord, DomainEventRecord, TokenRecord,
    PaperOrderRecord, PaperPositionRecord, TradingControlRecord,
)


def category(reason):
    if reason.startswith('risk:') or reason in {'risk_gate_not_approved','risk_score_unknown','risk_score_above_strategy_limit'}:
        return 'risk'
    groups = {
        'insufficient_observation_span':'observation_span',
        'insufficient_trades_in_scoring_window':'trade_count',
        'insufficient_unique_buyers_in_scoring_window':'buyer_count',
        'insufficient_sustained_buy_flow':'buy_flow',
        'buyer_flow_concentrated':'buyer_concentration',
        'buyer_attribution_incomplete':'buyer_attribution',
        'score_component_completeness_below_minimum':'score_completeness',
        'score_below_watch_threshold':'score',
        'token_younger_than_strategy_minimum':'token_age',
        'token_age_unknown':'token_age',
        'regime_not_allowed':'regime',
        'price_extension_above_entry_limit':'price_extension',
        'feature_snapshot_unavailable':'missing_features',
    }
    return groups.get(reason, reason.split(':')[0])


async def main():
    run=json.loads(Path('analysis/paper_run_state.json').read_text(encoding='utf-8'))
    end=datetime.now(UTC)
    db=Database(create_database_engine(Settings().database_url))
    try:
        async with db.sessions() as session:
            exp=await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.name==run['experiment_name']))
            start=exp.started_at
            decisions=list(await session.execute(select(StrategyDecisionRecord,DomainEventRecord.provider,TokenRecord.mint)
                .join(DomainEventRecord,DomainEventRecord.event_id==StrategyDecisionRecord.event_id)
                .join(TokenRecord,TokenRecord.id==StrategyDecisionRecord.token_id)
                .where(StrategyDecisionRecord.active_strategy.is_(True),
                       StrategyDecisionRecord.strategy_key==exp.strategy_key,
                       StrategyDecisionRecord.decided_at>=start,StrategyDecisionRecord.decided_at<=end)))
            orders=list(await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id==exp.portfolio_id,
                                                                           PaperOrderRecord.created_at<=end)))
            positions=list(await session.scalars(select(PaperPositionRecord).where(PaperPositionRecord.portfolio_id==exp.portfolio_id)))
            events=list(await session.execute(select(DomainEventRecord.event_type,func.count()).where(
                DomainEventRecord.ingested_at>=start,DomainEventRecord.ingested_at<=end,
                DomainEventRecord.provider=='solana_rpc_pump').group_by(DomainEventRecord.event_type)))
            latest=await session.scalar(select(func.max(DomainEventRecord.ingested_at)).where(DomainEventRecord.provider=='solana_rpc_pump'))
            control=await session.get(TradingControlRecord,1)
        actions=Counter(); providers=Counter(); reason_counts=Counter(); group_counts=Counter(); exclusive=Counter()
        mints=defaultdict(set); policy=[]; policy_failures=[]; entries=[]
        for d,provider,mint in decisions:
            actions[d.action]+=1; providers[provider]+=1
            mints['all'].add(mint)
            if provider=='bullseye_ollama_policy':
                if 'ollama_unavailable_no_entry' in d.reasons:
                    policy_failures.append(d)
                else:
                    policy.append(d)
                    mints['policy'].add(mint)
                    if d.action=='skip': mints['vetoed'].add(mint)
            if d.action=='enter_candidate': entries.append(d); mints['approved'].add(mint)
            if provider!='bullseye_ollama_policy' and d.action=='skip':
                groups={category(r) for r in d.reasons}
                group_counts.update(groups)
                if len(groups)==1: exclusive.update(groups)
                reason_counts.update(d.reasons)
        refusals=Counter(o.rejection_reason for o in orders if o.status=='rejected')
        buy_refusals=Counter(o.rejection_reason for o in orders if o.status=='rejected' and o.side=='buy')
        filled_buys=[o for o in orders if o.status=='filled' and o.side=='buy']
        samples=[{'at':d.decided_at,'action':d.action,'confidence':d.final_score,'reasons':d.reasons}
                 for d in sorted(policy,key=lambda x:x.decided_at)[-12:]]
        settings=exp.configuration_snapshot_json['settings']['execution_parameters']
        result={
            'experiment':exp.name,'status':exp.status,'portfolio_id':str(exp.portfolio_id),
            'started_at':start,'snapshot_end':end,'hours':(end-start).total_seconds()/3600,
            'latest_native_event_at':latest,'entries_paused':control.entries_paused,
            'active_strategy_now':control.active_strategy_key,
            'native_event_counts':dict(events),'active_decisions':len(decisions),
            'distinct_candidate_coins':len(mints['all']),'decision_actions':dict(actions),
            'decision_providers':dict(providers),'deterministic_skip_reasons':dict(reason_counts.most_common()),
            'deterministic_skip_categories':dict(group_counts.most_common()),
            'exclusive_skip_categories':dict(exclusive.most_common()),
            'deterministic_entry_qualified_decisions':len(policy)+len(policy_failures)+sum(d.action=='enter_candidate' and p!='bullseye_ollama_policy' for d,p,m in decisions),
            'policy_evaluations_successful':len(policy),'policy_failures':len(policy_failures),
            'policy_vetoes':sum(d.action=='skip' for d in policy),
            'policy_buy_approvals':sum(d.action=='enter_candidate' for d in policy),
            'policy_distinct_coins':len(mints['policy']),'policy_vetoed_distinct_coins':len(mints['vetoed']),
            'final_entry_decisions':len(entries),'final_entry_distinct_coins':len(mints['approved']),
            'buy_execution_rejections':dict(buy_refusals.most_common()),'all_order_rejections':dict(refusals.most_common()),
            'filled_buys':len(filled_buys),'filled_sells':sum(o.status=='filled' and o.side=='sell' for o in orders),
            'open_positions':sum(p.status=='open' for p in positions),'closed_positions':sum(p.status=='closed' for p in positions),
            'positions':[{'mint':p.mint,'status':p.status,'opened_at':p.opened_at,'closed_at':p.closed_at,'realized_pnl':p.realized_pnl} for p in positions],
            'policy_samples':samples,'policy_failure_samples':[{'at':d.decided_at,'reasons':d.reasons} for d in policy_failures[-5:]],
            'entry_order_samples':[{'at':o.created_at,'mint':o.mint,'side':o.side,'status':o.status,'reason':o.rejection_reason,
                                    'decision_id':o.decision_event_id} for o in orders if o.side=='buy'][-20:],
            'risk_prefilter':{k:v for k,v in settings.items() if k.startswith('risk_prefilter_')},
            'strategy':exp.configuration_snapshot_json['strategy'],
            'configured_model':settings.get('ollama_model'),
        }
        Path('analysis/current_paper_funnel_audit.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
        print(json.dumps(result,indent=2,default=str))
    finally:
        await db.dispose()

asyncio.run(main())
