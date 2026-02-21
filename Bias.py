import requests
import datetime
import json
import os

# --- SETTINGS ---
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
TIMEFRAMES = ["1d", "4h", "1h"] 
HISTORY_FILE = "history.json"

def get_base_score(raw_val):
    """Maps 0-100 BabyPips scale to -5 to +5 scale"""
    try:
        # (raw - 50) / 10: 100 becomes +5, 0 becomes -5, 50 becomes 0
        score = int(round((float(raw_val) - 50) / 10))
        return max(min(score, 5), -5) 
    except:
        return 0

def get_peak_logic(scores):
    """
    Implements your dominance and lane validity logic:
    1. Conflict Check: Invalid if contains both Strong (>=3) and Weak (<=-3).
    2. Threshold Check: Valid Strong must hit at least +4. Valid Weak must hit -4.
    3. Neutral Check: If no extremes, check if it fits the 0/1/-1 neutral zone.
    """
    s_max = max(scores)
    s_min = min(scores)
    
    # RULE: Conflict Check (e.g., +3 and -5 in the same set)
    has_strong_pos = any(x >= 3 for x in scores)
    has_strong_neg = any(x <= -3 for x in scores)
    
    if has_strong_pos and has_strong_neg:
        return "INVALID"

    # RULE: Valid Strong (Must have a 4 or 5 and NO strong negatives)
    if s_max >= 4:
        return s_max
    
    # RULE: Valid Weak (Must have a -4 or -5 and NO strong positives)
    if s_min <= -4:
        return s_min
    
    # RULE: Neutral Logic (If only 0, 1, or -1 are present)
    if all(-1 <= x <= 1 for x in scores):
        return "NEUTRAL"

    # Everything else (like a max of +3 without a +4, or mixed small numbers)
    return "INVALID"

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
        # Order: 1D, 4H, 1H
        scores = [raw_data['1d'].get(c,0), raw_data['4h'].get(c,0), raw_data['1h'].get(c,0)]
        peaks[c] = get_peak_logic(scores)
    return peaks

def generate_dashboard(peaks):
    data_store = {"signals": {}, "log": []}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data_store = json.load(f)
        except: pass

    # Filter currencies based on your trading rules
    # We trade Strong (+4, +5) against Weak (-4, -5) OR Neutral
    strong_side = [c for c, s in peaks.items() if s in [4, 5]]
    weak_side = [c for c, s in peaks.items() if s in [-4, -5]]
    neutrals = [c for c, s in peaks.items() if s == "NEUTRAL"]

    active_pairs = []
    # Strong vs Weak
    for s in strong_side:
        for w in weak_side:
            active_pairs.append((f"{s}{w}", "BUY"))
            active_pairs.append((f"{w}{s}", "SELL"))
    # Strong vs Neutral
    for s in strong_side:
        for n in neutrals:
            active_pairs.append((f"{s}{n}", "BUY"))
    # Neutral vs Weak
    for n in neutrals:
        for w in weak_side:
            active_pairs.append((f"{n}{w}", "BUY"))

    timestamp = datetime.datetime.now().strftime('%H:%M')
    new_signals_dict = {}

    for pair, side in active_pairs:
        prev = data_store.get("signals", {}).get(pair, {})
        if side == prev.get("side"):
            duration = prev.get("duration", 0) + 1
        else:
            duration = 1
            data_store["log"].insert(0, f"[{timestamp}] {side} {pair}")
        
        new_signals_dict[pair] = {"side": side, "duration": duration}

    data_store["signals"] = new_signals_dict
    data_store["log"] = data_store["log"][:5]

    # --- HTML GENERATION ---
    table_rows = ""
    for pair, info in data_store["signals"].items():
        color = "#22c55e" if info["side"] == "BUY" else "#ef4444"
        table_rows += f"<tr style='border-bottom:1px solid #1e293b;'><td style='padding:12px;'><b>{pair}</b></td><td style='color:{color}; font-weight:bold;'>{info['side']}</td><td>{info['duration']}h</td></tr>"

    # Create the RAW STRENGTH string for the footer
    raw_strings = []
    for k, v in peaks.items():
        color = "#94a3b8"
        if v == "INVALID": color = "#475569"
        elif v == "NEUTRAL": color = "#fbbf24"
        elif isinstance(v, int) and v > 0: color = "#22c55e"
        elif isinstance(v, int) and v < 0: color = "#ef4444"
        raw_strings.append(f"<span style='color:{color}'><b>{k}:</b> {v}</span>")

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
            <div style="background:#020617; padding:15px; border-radius:10px; border:1px solid #1e293b; margin-top:20px;">
                <table>
                    <thead><tr><th>Pair</th><th>Signal</th><th>Duration</th></tr></thead>
                    <tbody>{table_rows if table_rows else "<tr><td colspan='3' style='padding:40px; text-align:center; color:#475569;'>No confluence detected.</td></tr>"}</tbody>
                </table>
            </div>
            <div class="grid-layout">
                <div class="widget-card">
                    <h3>📅 Economic Calendar</h3>
                    <iframe src="https://www.tradingview.com/embed-widget/events/?locale=en#%7B%22colorTheme%22%3A%22dark%22%2C%22width%22%3A%22100%25%22%2C%22height%22%3A%22100%25%22%7D" width="100%" height="400" frameborder="0"></iframe>
                </div>
                <div class="widget-card">
                    <h3>🔥 Recent Alerts</h3>
                    <div style="text-align:left; padding:15px; font-family:monospace; color:#22c55e;">
                        {"".join([f"<p style='margin:5px 0;'>{log}</p>" for log in data_store['log']])}
                    </div>
                </div>
            </div>
            <div style="margin-top:30px; padding:15px; background:#020617; border-radius:8px; font-size:11px; border: 1px solid #1e293b;">
                {" | ".join(raw_strings)}
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w") as f: f.write(html)
    with open(HISTORY_FILE, "w") as f: json.dump(data_store, f)

if __name__ == "__main__":
    peaks = fetch_data()
    generate_dashboard(peaks)
