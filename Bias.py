import requests
import datetime
import json
import os

# --- SETTINGS ---
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
TIMEFRAMES = ["1d", "4h", "1h"] 
HISTORY_FILE = "fx_history.json"

def get_base_score(raw_val):
    """Maps BabyPips 0-100 scale to -6 to +6 scale"""
    try:
        # Scale: 0=-6, 50=0, 100=+6
        val = float(raw_val)
        score = int(round((val - 50) / 8.33))
        return max(min(score, 6), -6)
    except:
        return 0

def get_verdict(scores):
    """
    Implements your specific Logic:
    1. Check for Conflict (Strong and Weak in same set)
    2. Determine if Strong, Weak, or Neutral
    """
    s_max = max(scores)
    s_min = min(scores)
    
    # RULE: Conflict Check (e.g., +4 and -4 in the same set)
    is_strong_present = any(x >= 4 for x in scores)
    is_weak_present = any(x <= -4 for x in scores)
    
    if is_strong_present and is_weak_present:
        return "INVALID", 0

    # Determine status and final score
    if is_strong_present:
        return "STRONG", s_max
    elif is_weak_present:
        return "WEAK", s_min
    else:
        # Neutral logic: get the value with highest absolute magnitude as representative
        # Or simply the max/min depending on bias
        final_neutral = s_max if abs(s_max) >= abs(s_min) else s_min
        return "NEUTRAL", final_neutral

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
    
    results = {}
    for c in CURRENCIES:
        # Order: 1D, 4H, 1H
        scores = [raw_data['1d'][c], raw_data['4h'][c], raw_data['1h'][c]]
        status, final_val = get_verdict(scores)
        results[c] = {
            "1d": scores[0], "4h": scores[1], "1h": scores[2],
            "status": status, "final": final_val
        }
    return results

def generate_dashboard(current_results):
    # Load History for "Last Hour" Verdict
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: pass

    # 1. GROUP CURRENCIES
    strongs = [c for c, d in current_results.items() if d['status'] == "STRONG"]
    weaks = [c for c, d in current_results.items() if d['status'] == "WEAK"]
    neutrals = [c for c, d in current_results.items() if d['status'] == "NEUTRAL"]

    # 2. GENERATE TRADE LIST BIAS
    trade_list = []
    # All combinations for 8 currencies
    import itertools
    for base, quote in itertools.permutations(CURRENCIES, 2):
        b_stat = current_results[base]['status']
        q_stat = current_results[quote]['status']
        
        pair = f"{base}/{quote}"
        bias = None
        
        # LOGIC: Weak vs Strong | Strong vs Neutral | Weak vs Neutral
        if b_stat == "STRONG" and q_stat == "WEAK": bias = "BUY (Strong vs Weak)"
        elif b_stat == "WEAK" and q_stat == "STRONG": bias = "SELL (Weak vs Strong)"
        elif b_stat == "STRONG" and q_stat == "NEUTRAL": bias = "BUY (Strong vs Neutral)"
        elif b_stat == "NEUTRAL" and q_stat == "STRONG": bias = "SELL (Neutral vs Strong)"
        elif b_stat == "NEUTRAL" and q_stat == "WEAK": bias = "BUY (Neutral vs Weak)"
        elif b_stat == "WEAK" and q_stat == "NEUTRAL": bias = "SELL (Weak vs Neutral)"
        elif b_stat == "WEAK" and q_stat == "WEAK": bias = "AVOID (Weak vs Weak)"
        elif b_stat == "STRONG" and q_stat == "STRONG": bias = "AVOID (Strong vs Strong)"
        elif b_stat == "NEUTRAL" and q_stat == "NEUTRAL": bias = "AVOID (Neutral vs Neutral)"
        else: bias = "AVOID (Invalid data)"

        trade_list.append((pair, bias))

    # 3. CONSTRUCT STRINGS FOR DASHBOARD
    currency_rows = ""
    for c in CURRENCIES:
        d = current_results[c]
        last_stat = history.get(c, {}).get('status', 'N/A')
        # Display format: USD (1d)+3 (4H)-1 (1H)+5 USD= +5 strong
        display_str = f"{c} (1d){d['1d']:+d} (4h){d['4h']:+d} (1h){d['1h']:+d} = {d['final']:+d} {d['status']}"
        
        color = "#22c55e" if d['status'] == "STRONG" else "#ef4444" if d['status'] == "WEAK" else "#94a3b8"
        if d['status'] == "INVALID": color = "#f97316"

        currency_rows += f"""
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:10px; color:{color}; font-family:monospace;">{display_str}</td>
            <td style="padding:10px; font-size: 0.8em; color:#64748b;">Prev: {last_stat}</td>
        </tr>"""

    trade_rows = ""
    for pair, bias in trade_list:
        color = "#22c55e" if "BUY" in bias else "#ef4444" if "SELL" in bias else "#475569"
        trade_rows += f"<tr><td style='padding:5px;'><b>{pair}</b></td><td style='color:{color};'>{bias}</td></tr>"

    # 4. HTML TEMPLATE
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FX Strength Dashboard</title>
        <style>
            body {{ background:#020617; color:white; font-family:sans-serif; padding:20px; }}
            .container {{ max-width:1000px; margin:auto; }}
            .card {{ background:#0f172a; padding:20px; border-radius:10px; border:1px solid #1e293b; margin-bottom:20px; }}
            table {{ width:100%; border-collapse:collapse; }}
            h2 {{ color:#3b82f6; border-bottom:1px solid #3b82f6; padding-bottom:10px; }}
            .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Currency Strength Command Center</h1>
            
            <div class="card">
                <h2>Currency Strength Breakdown</h2>
                <table>{currency_rows}</table>
            </div>

            <div class="grid">
                <div class="card">
                    <h2>Summary</h2>
                    <p><b style="color:#22c55e;">Strongest:</b> {", ".join(strongs) if strongs else "None"}</p>
                    <p><b style="color:#ef4444;">Weakest:</b> {", ".join(weaks) if weaks else "None"}</p>
                    <p><b style="color:#94a3b8;">Neutral:</b> {", ".join(neutrals) if neutrals else "None"}</p>
                </div>
                
                <div class="card" style="height: 400px; overflow-y: scroll;">
                    <h2>Forex Trade List Bias</h2>
                    <table>{trade_rows}</table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w") as f: f.write(html)
    with open(HISTORY_FILE, "w") as f: json.dump(current_results, f)
    print("Dashboard Updated Successfully.")

if __name__ == "__main__":
    data = fetch_data()
    generate_dashboard(data)
