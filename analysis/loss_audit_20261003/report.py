"""Build the audit document from the fixed, retained read-only snapshots."""
from collections import Counter
from datetime import datetime
from decimal import Decimal as D
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT.parents[1] / 'docs' / 'PAPER_LOSS_AUDIT_20261003.md'


def n(value):
    return f'{D(str(value)):.2f}'


def main():
    findings = json.loads((ROOT/'findings.json').read_text(encoding='utf-8'))
    prior, current = findings['cohorts']
    timelines = json.loads((ROOT/'timeline_findings.json').read_text(encoding='utf-8'))['positions']
    raw_timelines = json.loads((ROOT/'retained_timelines.json').read_text(encoding='utf-8'))['timelines']
    snapshot = json.loads((ROOT/'current_1250/snapshot.json').read_text(encoding='utf-8'))
    cases = []
    for cohort, folder in [(prior, 'current_1248'), (current, 'current_1250')]:
        source = json.loads((ROOT/folder/'snapshot.json').read_text(encoding='utf-8'))
        for trade in cohort['trades']:
            if D(trade['pnl_percent']) > -40:
                continue
            sell = next(row['fill_json'] for row in reversed(source['filled_orders'])
                        if row['mint'] == trade['mint'] and row['side'] == 'sell')
            timeline = next(row for row in raw_timelines if row['cohort'] == trade['cohort'] and row['mint'] == trade['mint'])
            native = [row for row in timeline['retained_events']
                      if row['source_slot'] < sell['execution_state']['slot'] and row['normalized_state']]
            last = max(native, key=lambda row: (row['source_slot'], row['provider_received_at'] or row['ingested_at']))
            state = last['normalized_state']
            tokens = state['virtual_token'] if state['virtual_token'] is not None else state['token_reserve']
            quotes = state['virtual_quote'] if state['virtual_quote'] is not None else (state['quote_reserve'] or 0) + (state['virtual_offset'] or 0)
            native_price = D(quotes)/D(tokens) if quotes and tokens else None
            comparison = {'cohort': trade['cohort'], 'symbol': trade['symbol'], 'mint': trade['mint'],
                'recorded_pnl_percent': trade['pnl_percent'], 'native_slot': last['source_slot'],
                'native_source_at': last['source_event_at'], 'native_received_at': last['provider_received_at'],
                'native_ingested_at': last['ingested_at'], 'native_continuity_status': state['continuity_status'],
                'native_reserve_ratio_diagnostic': native_price, 'exit_atomic_slot': sell['execution_state']['slot'],
                'exit_atomic_received_at': sell['market_observed_at'], 'exit_fill_at': sell['filled_at'],
                'exit_reference_price': sell['reference_price'],
                'exit_vs_earlier_native_ratio_percent': (D(sell['reference_price'])/native_price-1)*100 if native_price else None,
                'comparison_is_synchronized': False}
            if trade['symbol'] == 'Lath':
                reserve = sell['execution_state']['reserves']
                comparison.update(native_post_quote_raw=state['quote_reserve'], native_post_base_raw=state['token_reserve'],
                                  native_offset_raw=state['virtual_offset'], exit_pool_reserves=reserve,
                                  k_change_percent=(D(reserve['base'])*D(reserve['quote']+reserve['offset']) /
                                                    (D(tokens)*D(quotes))-1)*100,
                                  interpretation='Large constant-product reserve move is plausible; the intervening full transaction and synchronized account bytes are not retained here, so exact cause is not proven.')
            cases.append(comparison)
    (ROOT/'evidence_cases.json').write_text(json.dumps({'cases': cases}, indent=2, default=str), encoding='utf-8')
    p, c = prior['summary'], current['summary']
    decomp = c['decomposition']
    delay = {row['mint']:row for row in timelines if row['cohort'] == 'current'}
    all_decision_evidence = []
    for folder in ('current_1248', 'current_1250'):
        source = json.loads((ROOT/folder/'snapshot.json').read_text(encoding='utf-8'))
        events = {row['event_id']:row['payload'] for row in source['evidence']}
        all_decision_evidence.extend(events[row['entry_decision_event_id']]['price_evidence'] for row in source['outcomes'])
    invalidations = Counter(row.get('invalidation_reason') for row in all_decision_evidence)
    current_rows = '\n'.join(f"| {row['symbol']} | {row['entry_at_dublin'][11:19]} | {n(row['entry_cost_usdt'])} | {n(row['net_pnl_usdt'])} | {n(row['pnl_percent'])}% | {n(row['holding_seconds'])} | {n(row['executable_statistics']['mfe_percent'])}% | {row['exit_reason']} |" for row in current['trades'])
    current_contracts = '\n'.join(f"- {row['symbol']}: `{row['mint']}`" for row in current['trades'])
    lath = next(row for row in cases if row['symbol'] == 'Lath')
    doc = f"""# Почему PAPER-портфели убыточны: аудит 3 октября 2026

Аудит выполнен только чтением PostgreSQL и сохранённых данных. Production-код, настройки, торговые пороги, пауза, балансы и записи сделок не менялись. LIVE и `runner-edge-prospective-v1` не запускались. В документе речь о текущей operational PAPER-стратегии; существующий `paper_runner_enabled=true` управляет её выходами и не означает запуск заблокированного эксперимента.

Снимки: 12:49 UTC / 13:49 Dublin, 3 октября. Два последних портфеля анализируются отдельно. Сброс PAPER-портфеля создаёт новую виртуальную кассу и не исправляет причины убытков.

## 1. Результат и проверка учёта

| Портфель | Начальная касса | Остаток USDT | Закрытых позиций | Прибыльных / убыточных | PnL USDT |
|---|---:|---:|---:|---:|---:|
| Предыдущий, `{p['portfolio_id']}` | 1000 | {n(p['cash_usdt'])} | 12 | 1 / 11 | {n(p['net_pnl_usdt'])} |
| Текущий Telegram, `{c['portfolio_id']}` | 1000 | {n(c['cash_usdt'])} | 8 | 1 / 7 | {n(c['net_pnl_usdt'])} |

На снимке открытых позиций нет. Текущий портфель создан в 13:26:54 Dublin. Его восемь позиций закрылись к 13:35:43. Убыток текущей кассы — 26,69%. Всего в двух сериях 20 позиций / 42 исполнения; суммарный виртуальный PnL −485,90 USDT. Это сумма двух отдельных касс, не процент потерь одного текущего баланса.

Независимый пересчёт каждого BUY и всех связанных SELL совпадает с PnL позиции с допуском 0,00000002 USDT; суммы округлённых позиций точно совпадают с PnL портфелей. Проданное количество совпадает с купленным. Касса = начальная касса + реализованный PnL. Двойного списания BUY venue fee не обнаружено: эта комиссия уже включена в gross input; отдельно при входе добавляются provider/network fees.

Это проверка внутренней согласованности PAPER-модели. Она не доказывает реальные исполнимые цены, полноту потока или правильность всех исходных RPC-банков.

## 2. Что съедает текущий результат

Пересчёт использует те же сохранённые exit-банки, моменты выходов и пропорции частичных продаж, снимая только записанную дополнительную friction. Это бухгалтерское разложение, не бэктест альтернативной стратегии.

| Компонент | USDT |
|---|---:|
| Изменение marginal reserve prices и SOL/USDT до impact/friction/fees | {n(decomp['spot_reserve_move_and_sol_fx_pnl'])} |
| Дополнительный расход из-за constant-product price impact | −{n(decomp['curve_price_impact_cost'])} |
| Итого результат по кривым до дополнительных friction/fees | {n(decomp['curve_price_pnl_before_fees_friction'])} |
| Настроенная дополнительная friction | −{n(decomp['configured_friction_cost'])} |
| Venue fees из сохранённых on-chain rates | −{n(decomp['venue_fees'])} |
| Моделируемая provider fee | −{n(decomp['modeled_provider_fees'])} |
| Моделируемые network/priority fees | −{n(decomp['modeled_network_fees'])} |
| Итог | {n(c['net_pnl_usdt'])} |

Примерно 84% записанного убытка приходится на компонент по кривым до дополнительных friction/fees. Для предыдущей серии аналогично: −164,78 USDT по кривым, −23,44 friction, −30,77 fees = −219,00. Удаление дополнительной friction и всех fees не превращает эти сохранённые выходы в прибыльные. При этом часть reserve-price падений, особенно Lath, требует проверки причин; называть весь этот компонент доказанным рыночным движением нельзя.

В симуляции каждая сторона получает 50 bps latency penalty + 50 bps additional slippage + 50 bps adverse fill = 1,5%. Дополнительно действует provider fee 0,5% на сторону, записанная как предположение PumpPortal Local API, даже при native discovery. Discovery-провайдер сам по себе не определяет маршрут будущего исполнения. Нужно проверить применимость этой fee к конкретному execution route; аудит не отключал её ради улучшения результата.

## 3. Подтверждённый пробел входного сигнала

У **20 из 20** исполненных входов:

- `decision_price=null`;
- `price_change_percent=null` в 10-секундном окне;
- исходная observational continuity `UNKNOWN`, качество `INCOMPLETE`;
- momentum-компонент считается AVAILABLE, полнота скоринга `100%`.

Причины инвалидирования: `{dict(invalidations)}`. `NormalizedMarketState.observational_price` корректно возвращает None при неподтверждённой continuity; feature engine не подменяет её необоснованной ценой. Но momentum scorer усредняет оставшиеся flow/acceleration признаки, пропуская отсутствующую цену. Полнота считается по доступности целых компонентов, не по обязательным входам внутри них. `maximum_price_change_percent` проверяется только при наличии price change. Для aggressive sell absorption не обязателен.

В результате ранний поток покупок и резервная активность могут давать высокий score без подтверждённого движения цены и без работающей проверки extension. Final atomic RPC проверяет текущую canonical identity/config/executable quote и позволяет fill, но не восстанавливает пропущенную историю за окно сигнала. Все BUY имели качество `canonical_atomic_bank_verified`; это не эквивалент полноты исторического сигнала.

Риск всё ещё является hard gate. Нулевой вес risk в score не отключает проверки risk. Wallet/social не участвуют в данном скоринге, Ollama выключена. По этой выборке нельзя доказать, что включение Ollama или wallet alpha исправило бы результат.

Источники кода: [observational price](C:/Bullseye/src/memebot/market_state.py:95), [feature price provenance](C:/Bullseye/src/memebot/intelligence/features/engine.py:132), [очистка неподтверждённой цены](C:/Bullseye/src/memebot/intelligence/features/engine.py:249), [полнота компонентов](C:/Bullseye/src/memebot/strategies/scoring.py:62), [пропуск отсутствующего price change](C:/Bullseye/src/memebot/strategies/scoring.py:127), [extension gate](C:/Bullseye/src/memebot/strategies/runner.py:172), [fallback decision reference](C:/Bullseye/src/memebot/paper/engine.py:208).

## 4. Стоимость входа и смысл стопа

Моделируемый немедленный BUY→SELL на одном entry-банке теряет в текущей серии {n(c['round_trip_cost_percent_min'])}–{n(c['round_trip_cost_percent_max'])}% **net** даже без движения рынка. В предыдущей серии: 8,50–8,96%. В эту величину уже включены impact, venue/provider/network fees и обе friction-поправки. Guard aggressive допускает до 900 bps / 9%, поэтому почти вся эта стоимость проходит установленный контроль.

Этот cost probe делает две quantity-specific quotes по одному наблюдаемому банку; он не накладывает смоделированную покупку на его резервы перед обратной продажей. Поэтому это hurdle существующей модели, не измеренная стоимость реального немедленного round trip с учётом собственного влияния на pool. Independent-bank подход может добавлять пессимизм impact; его нельзя смешивать с эмпирически подтверждёнными live expenses.

Стоп `12%` проверяется **по gross executable sell price относительно gross buy fill price**, а не по net PnL кассы. Немедленный gross price loss текущих входов уже {n(c['immediate_gross_price_loss_percent_min'])}–{n(c['immediate_gross_price_loss_percent_max'])}%; до стопа остаётся примерно 5–6 процентных пунктов по этой шкале. Даже точное срабатывание gross −12% при неизменном SOL/USDT даёт около net −14% после оставшихся fees. Пример SENTI: reference price −6,13%, gross fill price −12,38%, net PnL −14,33%.

Стоп также не гарантирует продажу ровно на пороге. Timer ждёт 5 секунд **после** обработки всех позиций; позиции проверяются последовательно под общим monitor lock, timer пропускает проверку при занятом lock. Trade-triggered мониторинг помогает, но тоже проходит этот lock и RPC. После сигнала выхода добавляются 800 ms модельной задержки и ещё один atomic refresh; резкое движение между проверками или между trigger/refresh даёт более плохой выход. В сохранённых данных final mark→fill занимает примерно 0,9–1,1 s; полная история каждого RPC-probe/lock-wait не сохранена, поэтому точную задержку обнаружения всех стопов вычислить нельзя.

Суммарная signal→fill задержка в текущей серии: медиана {c['median_signal_to_fill_seconds']:.2f} s; decision wall-clock→fill: {c['median_decision_to_fill_seconds']:.2f} s. В предыдущей: {p['median_signal_to_fill_seconds']:.2f} s и {p['median_decision_to_fill_seconds']:.2f} s. Фиксированные `simulated_latency_ms=800` не равны полной задержке от исходного события. Часть старых сигналов жили почти 25 секунд.

В `price_safety.entry_data_block` ветка с verified atomic execution state возвращает допуск до проверки `feed_age_ms`: там проверяется свежесть самого RPC-банка. Поэтому настроенный feed age limit5 s не обеспечивает свежесть rolling-сигнала в этой ветке; для его возраста остаётся отдельный limit25 s. Fresh execution quote не означает fresh price history. Это объясняет, почему большая signal→fill задержка может пройти текущие safety checks.

В новой серии received→ingested достигает {max(row['received_to_ingested_max_seconds'] for row in delay.values()):.2f} s. Это подтверждённая задержка обработки **после receipt**, отдельная от возраста chain timestamp; DB commit time этим полем не измеряется. Независимый websocket receiver сохраняет соединение, но сам по себе не гарантирует, что обработчик успевает за потоком.

## 5. Выходы и отдача прибыли

Текущие параметры: stop gross −12%; partial take profit +100% с продажей 50%; `paper_runner_enabled=true`; activation trailing +50%, ширина min18% / max30% в зависимости от пика. Обычная activation +12% здесь не используется. Это существующие параметры, не изменения аудита.

Поэтому AWW #1 с записанным **net executable** пиком +32,21%, KaiCenat +17,11%, UP +13,29%, Lath +44,06% и LORIAN +45,48% могут оставаться без фиксации: даже с отличием gross/net эти пики ниже gross activation +50%. Политика ждёт большой продолженный рост; наблюдаемые небольшие всплески и быстрые возвраты часто заканчиваются стопом. Это объяснение поведения, не доказательство, что новый меньший take profit даст прибыль.

ORDERS достиг записанного net peak +62,16%, но закрылся −44,22%. Здесь trailing уже мог быть активен. Без истории промежуточных executable probes нельзя доказать, пропустил ли монитор доступную продажу раньше обвала. В этой серии ormine получил partial TP и trailing exit, итог +104,12% / +35,03 USDT.

`trade_outcomes.mfe_percent/mae_percent` у всех 20 равны нулю из-за отсутствия подтверждённой observational price history; они не доказывают отсутствие роста/падения. В таблице ниже используются отдельные retained executable statistics. После partial SELL их база — оставшаяся позиция/оставшаяся стоимость: пик ormine +141,12% и старого AWW #2 +296,05% нельзя читать как доходность всей изначальной позиции. Gross exit thresholds и net executable MFE тоже не равнозначны.

## 6. Восемь сделок текущего портфеля

Время входа — Dublin, 3 октября; PnL — за всю позицию, включая partial SELL.

| Монета | Вход | Cost USDT | PnL USDT | PnL % | Hold s | Recorded executable MFE* | Финальный выход |
|---|---|---:|---:|---:|---:|---:|---|
{current_rows}

*Статистика сохраняет только проверенные монитором точки, не непрерывный максимум рынка. Для ormine применяется оговорка о partial basis выше.

Lath составляет 44,81% net убытка текущей серии. Даже без него остальные позиции дают −147,31 USDT. Текущая серия: один winner +35,03 против семи losses суммарно −301,94. Выборка слишком мала и неоднородна для доказательства устойчивого edge или подбора прибыльных порогов.

Адреса для независимой проверки:

{current_contracts}

## 7. Lath: самое тяжёлое исключение требует осторожной трактовки

Entry reference price из атомарного банка: `0.0002902729811557527266778065919` lamports/raw token. Финальная migration-exit reference price: `{lath['exit_reference_price']}`. Записанный net результат −93,43% / −119,59 USDT.

Последний сохранённый native pool event перед exit-bank: slot {lath['native_slot']}, source {lath['native_source_at']}; receipt {lath['native_received_at']}; ingested {lath['native_ingested_at']}. Его диагностическое reserve ratio `{lath['native_reserve_ratio_diagnostic']}`, continuity UNKNOWN. Exit RPC bank: slot {lath['exit_atomic_slot']}, observed {lath['exit_atomic_received_at']}, fill {lath['exit_fill_at']}. Exit ratio ниже этого более раннего raw feed ratio на {n(-lath['exit_vs_earlier_native_ratio_percent'])}%.

Это **не synchronized source disagreement**: снимки разделены девятью слотами, а feed state неполный. Из native post-state к RPC-bank base balance вырос примерно с 237,07 млн до 921,79 млн токенов, real SOL balance упал с 56,69 до 1,52 SOL при одинаковом virtual offset 17,58 SOL. Произведение base × (quote + offset) отличается всего на {n(lath['k_change_percent'])}%. Такой переход математически совместим с очень большим sell на constant-product pool. Это усиливает гипотезу резкого market sell-off, но не доказывает конкретную транзакцию, rug, действия creator, полноту потока или отсутствие ошибки исходного account state. Полный intervening executed packet / synchronized raw account evidence для этого перехода в данном аудите отсутствует.

В текущей серии нет `market_snapshot_stale` отказов. Два `atomic_current_execution_state_required` относятся к переходу Lath после completion/migration. Старые 394 stale отказа относятся к **другому AWW #2**, который в итоге принёс +14,59 USDT. Это не общая причина семи текущих losses. AWW #1 и AWW #2 имеют разные mint.

## 8. Почему entries paused и почему потери больше дневного лимита

На снимке pause=true, последняя запись system safety в 13:33:17 Dublin. Настроенный daily loss limit — 10% от initial1000 = 100 USDT; governor учитывает realized + unrealized текущего portfolio. Последняя закрытая позиция Lath вышла позже, в 13:35:43. Pause блокирует новые входы, монитор продолжает закрывать уже открытые позиции; она не гарантирует максимальную итоговую просадку ровно 100 USDT.

На момент открытия крупной позиции tail loss порядка 90% не резервируется: отдельный open-risk budget15% использует reserve loss fraction30%, total exposure limit40%. Фактические текущие входы до 137,69 USDT. Один Lath потерял больше всего дневного лимита. Это сочетание tail risk и размера уже открытой позиции, а не основание отключать circuit breaker. Повторный Start trading до восстановления дневного допуска закономерно возвращает pause. Создание новой кассы сбрасывает счётчик текущего портфеля, но не устраняет отрицательные результаты.

## 9. Дополнительные ограничения достоверности

- 5163 retained trade records проанализированы по индексированным token/time диапазонам вокруг 20 позиций, без усечения. Тишина в записях не доказывает outage и не сертифицирует completeness. В текущей серии max source gaps с краями позиции 1–5 s, в старой есть длинные gaps и legacy provider задержки; отсутствие большого gap не предотвратило новые большие losses.
- Все текущие entry decisions имели UNKNOWN history, а fills — verified current bank. Нужны разные статусы полноты сигнала и исполнимости текущего state. Нельзя relabel неподтверждённые ticks историческими RPC prices.
- Активный experiment record всё ещё привязан к старому portfolio `{p['portfolio_id']}`, тогда как исполнение идёт в Telegram portfolio `{c['portfolio_id']}`. Experiment reports могут исключать текущие восемь сделок; текущие `experiment_matches=true` проверяют код/settings/control, но не эту связь. Это дефект атрибуции исследований, отдельный от cash accounting.
- Severe unsynchronized price transitions нельзя выдавать за доказанный source bug или калибровочный disagreement sample. Disagreement bands не настраивались.
- Материал содержит только конечные банки, retained marks/peaks и события, но не непрерывную историю каждого RPC read, lock wait и всех executable windows. Counterfactual stop/TP backtest по этой истории не будет надёжным.

## 10. Порядок дальнейших исправлений

1. Исправить entry input integrity и score completeness: отсутствие требуемой исторической цены должно явно отличаться от полной цены/сигнала. Не ослаблять canonical identity/execution guards и не возвращать неподтверждённые reserve ticks как достоверную цену.
2. Записывать exit probe start/end, atomic slots, queue/lock wait, trigger time, actual fill time, gross и net stop metrics; устранить выявляемые задержки open-position protection. Разобрать Lath synchronized evidence при следующем подобном переходе, сохраняя малый watch cohort.
3. Согласовать отображаемые stop/TP/MFE units; проверить фактический execution route и применимость modeled provider fee, не удаляя расходы ради красивого PAPER PnL.
4. Исправить связывание experiment ↔ активный Telegram portfolio и маркировку MFE/MAE unavailable. Сохранять прошлые кассы и их реальные результаты.
5. Только затем проводить отдельную ограниченную оценку entry/exit edge на данных с корректной provenance. Не выбирать новые пороги по этим двадцати позициям и не запускать заблокированный runner.

Аудит выполнил изучение; перечисленные production-изменения не внесены. Пауза сохраняется. Подтверждённые проблемы сигнала/измерений и cost hurdle объясняют риск текущего поведения, но прибыльность исправленной стратегии ещё не доказана.

Артефакты: `analysis/loss_audit_20261003/findings.json`, `trades.csv`, `timeline_findings.json`, `evidence_cases.json`, два read-only snapshots; воспроизводимый пересчёт `analyze.py`, `timeline_analysis.py`, `report.py`.
"""
    REPORT.write_text(doc, encoding='utf-8')
    print(json.dumps({'report': str(REPORT), 'audited_positions': 20, 'filled_orders': 42,
                      'all_fill_ledgers_reconciled': True, 'lath_case': lath}, default=str))


if __name__ == '__main__':
    main()
