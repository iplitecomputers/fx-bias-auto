import requests
import datetime

# --- CONFIGURATION ---
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
TIMEFRAMES = ["1h", "4h", "1d"]

def get_base_score(raw_val):
    # Scale 0-100 to -5 to +5
    return int(round((float(raw_val) - 50) / 10))

def get_peak_logic(h1, h4, d1):
    # Rule: All signs must be the same
    scores = [h1, h4, d1]
    if all(x >= 0 for x in scores):
        return max(scores)
    elif all(x <= 0 for x in scores):
        return min(scores)
    return "INVALID"

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
    
    final_peaks = {}
    for c in CURRENCIES:
        h1, h4, d1 = raw_data['1h'].get(c,0), raw_data['4h'].get(c,0), raw_data['1d'].get(c,0)
        final_peaks[c] = get_peak_logic(h1, h4, d1)
    return final_peaks

def generate_html(peaks):
    # Categorize
    strong = [c for c, s in peaks.items() if s != "INVALID" and s >= 3]
    weak = [c for c, s in peaks.items() if s != "INVALID" and s <= -3]
    neutral = [c for c, s in peaks.items() if s != "INVALID" and -1 <= s <= 1]
    
    # Pairing Logic
    alerts = []
    # Strong vs Weak
    for s in strong:
        for w in weak:
            alerts.append(f"🟢 <b>{s}/{w}</b>: Strong vs Weak (Score: {peaks[s]}/{peaks[w]})")
    # Strong vs Neutral
    for s in strong:
        for n in neutral:
            alerts.append(f"🔵 <b>{s}/{n}</b>: Strong vs Neutral (Score: {peaks[s]}/{peaks[n]})")
            
    # Generate index.html (Simplified for brevity)
    html = f"""
    <html><body style="background:#0f172a; color:white; font-family:sans-serif; text-align:center;">
        <h1>Confluence Bias Dashboard</h1>
        <p>Updated: {datetime.datetime.now()}</p>
        <div style="background:#1e293b; padding:20px; border-radius:10px; display:inline-block;">
            <h3>Active Pairings</h3>
            {"<br>".join(alerts) if alerts else "No Confluence Found"}
        </div>
        <h3>Currency Status</h3>
        {"".join([f"<p>{k}: {v}</p>" for k,v in peaks.items()])}
    </body></html>
    """
    with open("index.html", "w") as f:
        f.write(html)

if __name__ == "__main__":
    peaks = fetch_data()
    generate_html(peaks)