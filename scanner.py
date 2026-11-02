import os, urllib.request, json

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'QuantPulse/1.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def run_scanner():
    # 1. Ambil Top 100-500 Coin dari CoinGecko Free API & Fear/Greed
    coins = fetch_json('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1')
    fng = fetch_json('https://api.alternative.me/fng/?limit=1')['data'][0]
    
    scored = []
    for c in coins:
        sym = c['symbol'].upper()
        if sym in ('USDT','USDC','FDUSD','DAI','USDE'): continue
        chg24 = c.get('price_change_percentage_24h') or 0.0
        vol = c.get('total_volume') or 0
        mcap = c.get('market_cap') or 1
        fdv = c.get('fully_diluted_valuation') or mcap
        mc_fdv = min(1.0, mcap / max(1, fdv))
        vol_ratio = min(100, (vol / max(1, mcap)) * 450)
        
        # Skor Kuantitatif Gabungan (Teknikal + Likuiditas + Tokenomics MC/FDV)
        buy_score = 55 + (chg24 * 1.6) + (vol_ratio * 0.18) + (mc_fdv * 20)
        sell_score = 55 - (chg24 * 1.5) + ((1 - mc_fdv) * 28)
        scored.append((sym, c['current_price'], chg24, buy_score, sell_score, mc_fdv))
    
    top3_buy = sorted(scored, key=lambda x: x[3], reverse=True)[:3]
    top3_sell = sorted(scored, key=lambda x: x[4], reverse=True)[:3]
    
    msg = f"⚡ *QUANTPULSE 24/7 AUTO-ALERT*\nF&G Index: {fng['value']} ({fng['value_classification']})\n\n"
    msg += "🟢 *TOP 3 KONDISI TERBAIK DIBELI (LONG):*\n"
    for i, x in enumerate(top3_buy, 1):
        msg += f"{i}. *{x[0]}* (${x[1]:,.4g} | {x[2]:+.2f}%) — Skor Beli: {x[3]:.1f}/100 (MC/FDV {x[5]:.2f})\n"
    msg += "\n🔴 *TOP 3 KONDISI TERBAIK DIJUAL (SHORT/REDUCE):*\n"
    for i, x in enumerate(top3_sell, 1):
        msg += f"{i}. *{x[0]}* (${x[1]:,.4g} | {x[2]:+.2f}%) — Skor Jual: {x[4]:.1f}/100 (MC/FDV {x[5]:.2f})\n"
        
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat_id:
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data)

if __name__ == '__main__':
    run_scanner()
