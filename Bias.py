import requests
import datetime
import json
import os

# --- SETTINGS ---
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
TIMEFRAMES = ["1h", "4h", "1d"]
HISTORY_FILE = "history.json"

def get_base_score(raw_val):
    try:
        return int(round((float(raw_val) - 50) / 10))
    except:
        return 0

def get_peak_logic(h1, h4, d1):
    scores = [h1, h4, d1]
    is_pos = all(x >= 0 for x in scores)
    is_neg = all(x <= 0 for x in scores)
    if not (is_pos or is_neg): return "INVALID"
    return max(scores) if is_pos else min(scores)

def fetch_data():
    raw_data = {tf: {c: 0 for c in CURRENCIES} for tf in TIMEFRAMES}
    for tf in TIMEFRAMES:
        url = f"https://marketmilk.babypips.com/api/currency-strength?period={tf}"
        try:
            resp = requests.get(url, timeout=10).json()
            for item in resp:
                if item['symbol'] in CURRENCIES:
                    raw_data[tf][item['symbol']] = get_base_score(item['strength'])
        except Exception as e:
            print(f"Error fetching {tf}: {e}")
    
    peaks = {}
    for c in CURRENCIES:
        h1, h4, d1 = raw_data['1h'].get(c,0), raw_data['4h'].get(c,0), raw_data['1d'].get(c,0)
        peaks[c] = get_peak_logic(h1, h4, d1)
    return peaks

def generate_dashboard(peaks):
    # Load History Safely - If file is old or broken, start fresh
    data_store = {"signals": {}, "log": []}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                loaded = json.load(f)
                # If the loaded data is the old format (just signals), merge it
                if "signals" in loaded:
                    data_store["signals"] = loaded["signals"]
                if "log" in loaded:
                    data_store["log"] = loaded["log"]
                # If it was REALLY old (just a flat dict), assume those are signals
                if "signals" not in loaded and "log" not in loaded:
                    data_store["signals"] = loaded
        except:
            pass

    current_signals = {}
    strong = [c for c, s in peaks.items() if s != "INVALID" and s >= 3]
    weak = [c for c, s in peaks.items() if s != "INVALID" and s <= -3]
    
    table_rows = ""
    timestamp = datetime.datetime.now().strftime('%H:%M')
    active_pairs = []

    for s in strong:
        for w in weak:
            active_pairs.append((f"{s}{w}", "BUY"))
            active_pairs.append((f"{w}{s}", "SELL"))

    for pair, side in active_pairs:
        # Safe get for signals
        prev_data = data_store["signals"].get(pair, {"side": "None", "duration": 0})
        
        if side == prev_data.get("side"):
            new_duration = prev_data.get("duration", 0) + 1
            trend_label = f"✅ Stable ({new_duration}h)"
        else:
            new_duration = 1
            trend_label = "🆕 New Signal"
            log_entry = f"[{timestamp}] {side} {pair}"
            if log_entry not in data_store["log"]:
                data_store["log"].insert(0, log_entry)

    # Update and trim the store
    data_store["log"] = data_store["log"][:5]
    data_store["signals"] = {pair: {"side": side, "duration": 1 if pair not in data_store["signals"] or side != data_store["signals"][pair].get("side") else data_store["signals"][pair].get("duration", 0) + 1} for pair, side in active_pairs}

    # Generate the table HTML
    for pair, info in data_store["signals"].items():
        color = "#22c55e" if info["side"] == "BUY" else "#ef4444"
        dur = info["duration"]
        table_rows += f"<tr style='border-bottom:1px solid #1e293b;'><td style='padding:12px;'><b>{pair}</b></td><td style='color:{color}; font-weight:bold;'>{info['side']}</td><td>{dur}h</td></tr>"

    with open(HISTORY_FILE, "w") as f:
        json.dump(data_store, f)

    log_html = "".join([f"<p style='margin:5px 0;'>{entry}</p>" for entry in data_store["log"]])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fx Command Center</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background:#020617; color:white; font-family:sans-serif; text-align:center; padding:20px; }}
            .container {{ max-width:1100px; margin:auto; background:#0f172a; padding:30px; border-radius:15px; border:1px solid #1e293b; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .grid-layout {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 25px; }}
            table {{ width:100%; border-collapse:collapse; text-align:left; margin-bottom: 20px; }}
            th {{ color:#94a3b8; border-bottom: 2px solid #1e293b; padding:12px; font-size:12px; text-transform: uppercase; }}
            td {{ padding: 12px; border-bottom: 1px solid #1e293b; }}
            .widget-card {{ background:#131722; border-radius:10px; border:1px solid #1e293b; padding:5px; height: 450px; overflow: hidden; }}
            h3 {{ font-size:12px; color:#3b82f6; text-align:left; margin: 10px; text-transform: uppercase; letter-spacing: 1px; }}
            @media (max-width: 850px) {{ .grid-layout {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="margin:0; letter-spacing: -1px;">Fx Command Center</h1>
            <p style="color:#64748b; margin-top: 5px;">Confluence Bias & Macro Data</p>

            <div style="background:#020617; padding:15px; border-radius:10px; border:1px solid #1e293b; margin-top:20px;">
                <table>
                    <thead>
                        <tr><th>Pair</th><th>Signal</th><th>Duration</th></tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else "<tr><td colspan='3' style='padding:40px; text-align:center; color:#475569;'>No confluence detected. Standing by...</td></tr>"}
                    </tbody>
                </table>
            </div>

            <div class="grid-layout">
                <div class="widget-card">
                    <h3>📅 Economic Calendar</h3>
                    <iframe src="https://www.tradingview.com/embed-widget/events/?locale=en#%7B%22colorTheme%22%3A%22dark%22%2C%22isMaximized%22%3Atrue%2C%22width%22%3A%22100%25%22%2C%22height%22%3A%22100%25%22%7D" width="100%" height="400" frameborder="0"></iframe>
                </div>
                
                <div class="widget-card">
                    <h3>🔥 Live News Feed</h3>
                    <iframe src="https://www.tradingview.com/embed-widget/timeline/?locale=en#%7B%22colorTheme%22%3A%22dark%22%2C%22isMaximized%22%3Atrue%2C%22width%22%3A%22100%25%22%2C%22height%22%3A%22100%25%22%7D" width="100%" height="400" frameborder="0"></iframe>
                </div>
            </div>

            <div style="margin-top:30px; padding:15px; background:#020617; border-radius:8px; font-size:11px; color:#475569; border: 1px solid #1e293b;">
                RAW STRENGTH: {" | ".join([f"<b>{k}:</b> {v}" for k,v in peaks.items()])}
            </div>
            <p style="font-size:10px; color:#334155; margin-top:10px;">Updated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w") as f:
        f.write(html)

if __name__ == "__main__":
    peaks = fetch_data()
    generate_dashboard(peaks)


