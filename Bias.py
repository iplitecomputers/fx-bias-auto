import requests
import datetime
import json
import os

# --- SETTINGS ---
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
TIMEFRAMES = ["1h", "4h", "1d"]
HISTORY_FILE = "history.json"

def get_base_score(raw_val):
    # Scale 0-100 to -5 to +5
    return int(round((float(raw_val) - 50) / 10))

def get_peak_logic(h1, h4, d1):
    # Rule: 1H, 4H, and 1D must all have the same sign (confluence)
    scores = [h1, h4, d1]
    is_pos = all(x >= 0 for x in scores)
    is_neg = all(x <= 0 for x in scores)
    if not (is_pos or is_neg): return "INVALID"
    return max(scores) if is_pos else min(scores)

def fetch_data():
    raw_data = {tf: {} for tf in TIMEFRAMES}
    for tf in TIMEFRAMES:
        url = f"https://marketmilk.babypips.com/api/currency-strength?period={tf}"
        try:
            resp = requests.get(url, timeout=10).json()
            for item in resp:
                if item['symbol'] in CURRENCIES:
                    raw_data[tf][item['symbol']] = get_base_score(item['strength'])
        except:
            pass
    
    peaks = {}
    for c in CURRENCIES:
        h1 = raw_data['1h'].get(c, 0)
        h4 = raw_data['4h'].get(c, 0)
        d1 = raw_data['1d'].get(c, 0)
        peaks[c] = get_peak_logic(h1, h4, d1)
    return peaks

def generate_dashboard(peaks):
    # 1. Load History (Memory)
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except:
            history = {}

    current_signals = {}
    strong = [c for c, s in peaks.items() if s != "INVALID" and s >= 3]
    weak = [c for c, s in peaks.items() if s != "INVALID" and s <= -3]
    
    table_rows = ""
    processed_pairs = []

    # 2. Logic: Create Pairings (+4/+3 vs -4/-3)
    for s in strong:
        for w in weak:
            # BUY if base is strong, quote is weak
            processed_pairs.append((f"{s}{w}", "BUY"))
            # SELL if base is weak, quote is strong
            processed_pairs.append((f"{w}{s}", "SELL"))

    # 3. Process Duration and Stability
    for pair, side in processed_pairs:
        prev_data = history.get(pair, {"side": "None", "duration": 0})
        
        if side == prev_data["side"]:
            new_duration = prev_data["duration"] + 1
            trend_label = f"✅ Stable ({new_duration}h)"
        else:
            new_duration = 1
            trend_label = "🆕 New Signal"

        current_signals[pair] = {"side": side, "duration": new_duration}
        
        color = "#22c55e" if side == "BUY" else "#ef4444"
        table_rows += f"""
        <tr style="border-bottom: 1px solid #1e293b;">
            <td style="padding:15px;"><b>{pair}</b></td>
            <td style="padding:15px; color:{color}; font-weight:bold;">{side}</td>
            <td style="padding:15px; color:#94a3b8;">{prev_data['side']}</td>
            <td style="padding:15px;">{trend_label}</td>
        </tr>
        """

    # 4. Save history for the next run
    with open(HISTORY_FILE, "w") as f:
        json.dump(current_signals, f)

    # 5. Build HTML with Pro Design
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fx Bias Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background:#020617; color:white; font-family:sans-serif; text-align:center; padding:20px; }}
            .container {{ max-width:900px; margin:auto; background:#0f172a; padding:30px; border-radius:15px; border:1px solid #1e293b; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            h1 {{ margin-bottom:5px; letter-spacing:-1px; color: #f8fafc; }}
            .subtitle {{ color:#64748b; margin-bottom:30px; font-size: 14px; }}
            table {{ width:100%; border-collapse:collapse; text-align:left; }}
            th {{ color:#94a3b8; border-bottom: 2px solid #1e293b; text-transform:uppercase; font-size:12px; padding:12px; }}
            .currency-box {{ margin-top:40px; padding:15px; background:#020617; border-radius:8px; font-size:11px; color:#475569; display:flex; flex-wrap:wrap; justify-content:center; gap:10px; }}
            .currency-item {{ border: 1px solid #1e293b; padding: 5px 10px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Fx Confluence Dashboard</h1>
            <p class="subtitle">Last Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            
            <table>
                <tr>
                    <th>Pair</th>
                    <th>Current Signal</th>
                    <th>Last Hour</th>
                    <th>Trend & Duration</th>
                </tr>
                {table_rows if table_rows else "<tr><td colspan='4' style='padding:40px; text-align:center; color:#475569;'>No Confluence Detected. Waiting for Market Alignment...</td></tr>"}
            </table>

            <div class="currency-box">
                {"".join([f"<span class='currency-item'><b>{k}:</b> {v}</span>" for k,v in peaks.items()])}
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w") as f:
        f.write(html)

if __name__ == "__main__":
    peaks = fetch_data()
    generate_dashboard(peaks)
