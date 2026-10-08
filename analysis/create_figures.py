"""Standalone ReportLab scientific plots; run with the bundled Python runtime."""
import json
from pathlib import Path

from reportlab.graphics import renderSVG
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors

root = Path(__file__).resolve().parent
timeline = json.loads((root / "worst_trade_timeline.json").read_text())
summary = json.loads((root / "summary.json").read_text())
for trade in summary["worst_positions"]:
    observations = [(r["T_plus_seconds"], r["price_raw"]) for r in timeline
                    if r["mint"] == trade["mint"] and r["kind"] == "observation"
                    and r.get("price_raw") and r["T_plus_seconds"] >= 0]
    fills = [(r["T_plus_seconds"], float(r["fill"]["actual_fill_price_raw"]))
             for r in timeline if r["mint"] == trade["mint"]
             and r["kind"].endswith("filled_at") and r.get("status") == "filled"]
    drawing = Drawing(1000, 440)
    chart = LinePlot()
    chart.x, chart.y, chart.width, chart.height = 105, 80, 845, 290
    chart.data = [observations, fills]
    chart.xValueAxis.valueMin = 0
    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.labelTextFormat = "%.5f"
    for index, color in enumerate((colors.HexColor("#2563eb"), colors.HexColor("#dc2626"))):
        chart.lines[index].lineStyle = None
        chart.lines[index].strokeColor = color
        chart.lines[index].symbol = makeMarker("FilledCircle")
        chart.lines[index].symbol.size = 3 if index == 0 else 8
    drawing.add(chart)
    drawing.add(String(105, 410, f"{trade['symbol']}: recorded prices and actual paper fills",
                       fontName="Helvetica-Bold", fontSize=18))
    drawing.add(String(105, 390, "Blue: recorded observations; red: paper fills. Gaps are not interpolated.",
                       fontSize=11))
    drawing.add(String(105, 45, "Seconds since discovery (receipt clock)", fontSize=12))
    drawing.add(String(105, 20, "Y: lamports / raw token unit. Marks do not establish executable liquidation value.",
                       fontSize=10))
    renderSVG.drawToFile(drawing, str(root / f"{trade['symbol']}-trajectory.svg"))
print("Saved two ReportLab forensic figures")
