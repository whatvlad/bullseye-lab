// Page world: draw Bullseye fills on the site's own TradingView chart.
(() => {
  const GREEN = "#2fbf71";
  const RED = "#ef4b4b";
  const drawn = new WeakMap(); // chart holder (iframe or window) -> { key, ids }
  let latest = null;

  const REASONS = {
    stop_loss: "stop",
    take_profit: "TP",
    partial_take_profit: "partial TP",
    trailing_stop: "trail",
    maximum_holding_time: "max hold",
    dump_hazard: "dump",
    stagnation: "stale",
  };

  function charts() {
    // activeChart() returns a fresh wrapper per call, so track by the holder.
    const found = [];
    const add = (holder, api) => {
      try {
        if (api && typeof api.activeChart === "function") {
          found.push({ holder, chart: api.activeChart() });
        }
      } catch {}
    };
    add(window, window.tvWidget);
    for (const frame of document.querySelectorAll("iframe")) {
      try {
        add(frame, frame.contentWindow.tradingViewApi);
      } catch {} // cross-origin frames are not charts we can reach
    }
    return found;
  }

  const FIELDS = ["mcap_usd", "mcap_sol", "price_usd", "price_sol"];
  const units = new WeakMap(); // chart holder -> { symbol, field }

  function visibleRange(chart) {
    try {
      const range = chart.getPanes()[0].getMainSourcePriceScale().getVisiblePriceRange();
      return range && range.from > 0 && range.to > 0 ? range : null;
    } catch {
      return null;
    }
  }

  function unit(holder, chart, symbol) {
    // Labels are unreliable (Dexscreener says "X/SOL (Market Cap)" while showing USD),
    // so the unit is picked from the price scale. It is then locked per chart: zooming
    // or resizing changes the visible range and must not move the markers. It is only
    // re-detected for a new symbol or when the locked unit is >10x outside the view
    // (the user switched USD/SOL or price/market cap).
    const sample = latest?.open || latest?.fills?.[latest.fills.length - 1];
    const range = visibleRange(chart);
    const locked = units.get(holder);
    if (locked && locked.symbol === symbol) {
      const value = sample?.[locked.field];
      if (!range || !value || (value > range.from / 10 && value < range.to * 10)) {
        return locked.field;
      }
    }
    let field = null;
    if (sample && range) {
      const middle = Math.log10(Math.sqrt(range.from * range.to));
      field = FIELDS.reduce((best, item) =>
        Math.abs(Math.log10(sample[item]) - middle) < Math.abs(Math.log10(sample[best]) - middle)
          ? item
          : best
      );
    } else {
      let label = "";
      try {
        label = `${symbol} ${chart.symbolExt?.()?.description || ""}`;
      } catch {}
      const mcap = /MCAP|MARKET ?CAP|\bMC\b/i.test(label);
      const usd = /USD/i.test(label) || !/SOL/i.test(label);
      field = `${mcap ? "mcap" : "price"}_${usd ? "usd" : "sol"}`;
    }
    if (sample && range) units.set(holder, { symbol, field });
    return field;
  }

  function money(value) {
    return `$${Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2)}`;
  }

  function labels(data, field) {
    const out = [];
    let entry = null;
    for (const fill of data.fills) {
      if (fill.side === "buy") {
        entry = fill[field];
        out.push({ fill, text: `B ${money(fill.amount)}`, shape: "arrow_up", color: GREEN });
      } else {
        const change = entry ? ((fill[field] / entry - 1) * 100).toFixed(1) : null;
        const reason = REASONS[fill.reason] || fill.reason || "sell";
        const text = `S ${change !== null ? (change > 0 ? "+" : "") + change + "% " : ""}${reason}`;
        out.push({ fill, text, shape: "arrow_down", color: change > 0 ? GREEN : RED });
      }
    }
    return out;
  }

  async function redraw({ holder, chart }) {
    let symbol = "";
    try {
      symbol = chart.symbol();
    } catch {}
    const field = unit(holder, chart, symbol);
    const key = JSON.stringify([field, symbol, latest]);
    const previous = drawn.get(holder);
    if (previous?.key === key) return;
    for (const id of previous?.ids || []) {
      try {
        chart.removeEntity(id);
      } catch {}
    }
    const ids = [];
    drawn.set(holder, { key, ids });
    if (!latest) return;
    const common = { lock: true, disableSelection: true, disableSave: true, disableUndo: true };
    for (const item of labels(latest, field)) {
      try {
        ids.push(
          await chart.createShape(
            { time: item.fill.time, price: item.fill[field] },
            { ...common, shape: item.shape, text: item.text, overrides: { color: item.color, fontsize: 12 } }
          )
        );
      } catch {}
    }
    const open = latest.open;
    if (open) {
      const pnl = open.pnl_percent === null ? "P&L n/a" : `P&L ${open.pnl_percent > 0 ? "+" : ""}${open.pnl_percent.toFixed(1)}%`;
      try {
        ids.push(
          await chart.createShape(
            { price: open[field] },
            {
              ...common,
              shape: "horizontal_line",
              text: `Bullseye entry · ${pnl}`,
              overrides: {
                linecolor: open.pnl_percent > 0 ? GREEN : RED,
                linestyle: 2,
                linewidth: 1,
                showLabel: true,
                textcolor: "#e8edf4",
                horzLabelsAlign: "left",
              },
            }
          )
        );
      } catch {}
    }
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window || !event.data?.__bullseye) return;
    latest = event.data.data && event.data.data.fills.length ? event.data.data : null;
    charts().forEach(redraw);
  });
  // Charts load late and are rebuilt on navigation or unit toggles.
  setInterval(() => charts().forEach(redraw), 2000);
})();
