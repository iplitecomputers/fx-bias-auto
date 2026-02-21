import requests
import datetime
import json
import os

# --- SETTINGS ---
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
TIMEFRAMES = ["1h", "4h", "1d"]
HISTORY_FILE = "history.json"

def get_base_score(raw_val):
    return int(round((float(raw_val) - 50) / 10))

def get_peak_logic(h1, h4, d1):
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
        except: pass
    
    peaks = {}
    for c in CURRENCIES:
        h1, h4, d1 = raw_data['1h'].get(c,0), raw_data['4h'].get(c,0), raw_data['1d'].get(c,0)
        peaks[c] = get_peak_logic(h1, h4, d1)
    return peaks

def generate_dashboard(peaks):
    # 1. Load History
    data_store = {"signals": {}, "log": []}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data_store = json.load(f)
        except: pass

    current_signals = {}
    strong = [c for c, s in peaks.items() if s != "INVALID" and s >= 3]
    weak = [c for c, s in peaks.items() if s != "INVALID" and s <= -3]
    
    table_rows = ""
    timestamp = datetime.datetime.now().strftime('%H:%M')
    
    # 2. Process Pairings
    active_pairs = []
    for s in strong:
        for w in weak:
            active_pairs.append((f"{s}{w}", "BUY"))
            active_pairs.append((f"{w}{s}", "SELL"))

    for pair, side in active_pairs:
        prev_data = data_store["signals"].get(pair, {"side": "None", "duration": 0})
        
        if side == prev_data["side"]:
            new_duration = prev_data["duration"] + 1
            trend_label = f"✅ Stable ({new_duration}h)"
        else:
            new_duration = 1
            trend_label = "🆕 New Signal"
            # Add to Recent Log if it's a new signal
            log_entry = f"[{timestamp}] {side} {pair} detected"
            if log_entry not in data_store["log"]:
                data_store["log"].insert(0, log_entry)

        current_signals[pair] = {"side": side, "duration": new_duration}
        color = "#22c55e" if side == "BUY" else "#ef4444"
        table_rows += f"""<tr style='border-bottom:1px solid #1e293b;'><td style='padding:12px;'><b>{pair}</b></td><td style='color:{color}; font-weight:bold;'>{side}</td><td style='color:#94a3b8;'>{prev_data['side']}</td><td>{trend_label}</td></tr>"""

    # Keep only last 5 log entries
    data_store["log"] = data_store["log"][:5]
    data_store["signals"] = current_signals

    # 3. Save History
    with open(HISTORY_FILE, "w") as f:
        json.dump(data_store, f)

    # 4. Build HTML
    log_html = "".join([f"<p style='margin:5px 0;'>{entry}</p>" for entry in data_store["log"]])
    
    html = f"""
    <html>
    <body style="background:#020617; color:white; font-family:sans-serif; text-align:center; padding:20px;">
        <div style="max-width:800px; margin:auto; background:#0f172a; padding:30px; border-radius:15px; border:1px solid #1e293b;">
            <h1 style="margin-bottom:0;">Confluence Dashboard Pro</h1>
            <p style="color:#64748b; margin-bottom:25px;">Last Update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            
            <table style="width:100%; border-collapse:collapse; text-align:left; margin-bottom:30px;">
                <tr style="color:#94a3b8; border-bottom: 2px solid #1e293b;"><th>Pair</th><th>Signal</th><th>Prev</th><th>Trend</th></tr>
                {table_rows if table_rows else "<tr><td colspan='4' style='padding:20px; color:#475569;'>No Signals Detected</td></tr>"}
            </table>

            <div style="background:#020617; padding:20px; border-radius:10px; text-align:left; border:1px solid #1e293b;">
                <h3 style="margin-top:0; color:#3b82f6; font-size:14px; text-transform:uppercase;">Recent Activity Log</h3>
                <div style="font-family:monospace; font-size:13px; color:#94a3b8;">{log_html if log_html else "Waiting for new activity..."}</div>
            </div>
            
            <div style="margin-top:20px; font-size:11px; color:#475569;">
                {" | ".join([f"{k}: {v}" for k,v in peaks.items()])}
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
