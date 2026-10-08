# Bullseye chart markers

Draws the local bot's paper buys/sells on pump.fun, GMGN, Axiom, Padre and Dexscreener charts.

1. Start the Telegram process (`bullseye telegram`). It serves fills on
   `http://127.0.0.1:8765/fills` (set `BULLSEYE_CHART_MARKERS_PORT=0` to disable).
2. Chrome → `chrome://extensions` → Developer mode → **Load unpacked** → this folder.
3. Open a token the bot traded. Markers refresh every few seconds:
   - `B $49.61` green ▲ at each buy fill
   - `S +23.4% TP` / `S -39.0% stop` ▼ at each sell fill (change vs. the buy fill)
   - a dashed `Bullseye entry · P&L` line while a position is open

The extension hooks each site's embedded TradingView chart. That is not a public
API, so a site redesign can break it until `inject.js` is adjusted.
