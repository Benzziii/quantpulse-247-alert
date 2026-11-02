import os, urllib.request, urllib.parse, json
from datetime import datetime, timezone, timedelta

def fetch_json(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) QuantPulse/6.0',
        'Accept': 'application/json'
    })
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8'))

CATALYST_BONUS = {
    'LINK': 94, 'AAVE': 95, 'ETH': 90, 'ONDO': 92, 'SUI': 91,
    'BTC': 90, 'SOL': 88, 'TAO': 85, 'HYPE': 86, 'BNB': 82, 'ARX': 84
}
UNLOCK_DILUTION_PENALTY = {
    'ARB': 28, 'ENA': 26, 'WLD': 32, 'STRK': 24, 'OP': 20, 'TIA': 22
}
STABLE_OR_WRAPPED = {
    'USDT','USDC','DAI','FDUSD','USDE','SUSDE','USDD','TUSD','PYUSD','RLUSD',
    'GHO','FRAX','LUSD','CRVUSD','NUSD','USD0','DEUSD','USR','DOLA','MIM',
    'USDB','EURC','EURT','PAXG','XAUT','WBTC','STETH','WSTETH','RETH','WEETH',
    'EZETH','USDG','USYC','BUIDL','USDTB','USDY','OUSG','CBBTC','FBTC','LBTC'
}
REGION_AFFINITY = {
    'ASIA': {'SUI','TAO','XRP','BNB','PEPE','DOGE','SHIB','TRX','TON','KAS','ARX','APT','SEI','NEAR'},
    'EUROPE': {'BTC','ETH','LINK','AAVE','UNI','MKR','ENA','CRV','LDO','DOT','AVAX','POL','QNT'},
    'US': {'BTC','ETH','SOL','ONDO','LINK','AAVE','HYPE','TAO','RENDER','FET','SUI','INJ','ARX','JUP','PYTH'}
}

def get_wib_session_info():
    wib = datetime.now(timezone.utc) + timedelta(hours=7)
    h_dec = wib.hour + wib.minute / 60.0
    t_str = wib.strftime('%d %b %Y %H:%M WIB')
    if 6.75 <= h_dec < 9.0:
        return t_str, 'ASIA', 1.18, 1.15, '🌅 <b>JAM RAWAN ASIA OPEN & 1D CLOSE (07:00–09:00 WIB)</b>: Awas Stop-Hunt pergantian candle 1D!'
    if 9.0 <= h_dec < 13.75:
        return t_str, 'ASIA', 1.00, 1.00, '☀️ <b>SESI ASIA AKTIF (09:00–14:00 WIB)</b>: Range akumulasi Asia; siaga sweep jelang Europe Open 14:00 WIB.'
    if 13.75 <= h_dec < 16.25:
        return t_str, 'EUROPE', 1.22, 1.18, '🌍 <b>JAM RAWAN EUROPE/LONDON OPEN (14:00–16:00 WIB)</b>: Waspada Judas Swing / Sweep High-Low Asia!'
    if 16.25 <= h_dec < 20.25:
        return t_str, 'EUROPE', 1.08, 1.08, '🌍 <b>SESI EROPA AKTIF (16:00–20:30 WIB)</b>: Siaga rilis data makro AS (19:30/20:30 WIB) & Wall St Open.'
    if 20.25 <= h_dec < 22.5:
        return t_str, 'US', 1.38, 1.25, '🗽 <b>JAM PALING RAWAN: US MARKET & ETF OPEN (20:30–22:30 WIB)</b>: Volatilitas puncak! SL diperlebar +25%.'
    if 22.5 <= h_dec < 23.75:
        return t_str, 'US', 1.20, 1.15, '🌆 <b>JAM RAWAN EUROPE CLOSE (22:30–23:30 WIB)</b>: Waspada profit-taking / intraday reversal London Fix!'
    if 2.75 <= h_dec < 4.5:
        return t_str, 'US', 1.16, 1.18, '🌙 <b>JAM RAWAN US CLOSE & CME SETTLEMENT (03:00–04:30 WIB)</b>: Likuiditas menipis, hindari market order besar!'
    return t_str, 'US', 1.05, 1.05, '🗽 <b>SESI AS SORE / OVERNIGHT</b>: Mengikuti arus penutupan ETF Spot & indeks Nasdaq.'

def is_excluded_stable(c):
    sym = (c.get('symbol') or '').upper()
    name = (c.get('name') or '').upper()
    p = float(c.get('current_price') or 0.0)
    chg = abs(float(c.get('price_change_percentage_24h') or 0.0))
    if sym in STABLE_OR_WRAPPED or p <= 0:
        return True
    if 'USD' in sym and sym != 'PYTH':
        return True
    if any(w in name for w in ('USD', 'DOLLAR', 'STABLE', 'WRAPPED', 'STAKED', 'GOLD', 'TETHER')):
        return True
    if 0.96 <= p <= 1.04 and chg < 1.2:
        return True
    return False

def fmt_p(val):
    if val >= 1000: return f"${val:,.0f}"
    if val >= 1: return f"${val:,.2f}"
    if val >= 0.01: return f"${val:.4f}"
    return f"${val:.6f}"

def calc_tp_sl(p, atr_pct, hz, vol_mult, sl_mult, is_sell=False):
    atr = max(1.8, atr_pct) / 100.0
    mult = {
        '4H': (1.10 * vol_mult, 0.78 * sl_mult),
        '1D': (1.85, 1.25 * sl_mult),
        '1W': (4.20, 2.60),
        '1M': (8.50, 4.80),
        'CYCLE': (16.0, 7.50)
    }.get(hz, (1.85, 1.25))
    if is_sell:
        return p * max(0.15, 1 - atr * mult[0]), p * (1 + atr * mult[1])
    return p * (1 + atr * mult[0]), p * max(0.15, 1 - atr * mult[1])

def score_coin_horizons(c, active_region):
    sym = c['symbol'].upper()
    p = float(c.get('current_price') or 0.0)
    hi = float(c.get('high_24h') or (p * 1.035))
    lo = float(c.get('low_24h') or (p * 0.965))
    atr_pct = max(2.2, min(14.0, ((hi - lo) / max(0.00001, p)) * 100))
    chg_1h = float(c.get('price_change_percentage_1h_in_currency') or 0.0)
    chg_24h = float(c.get('price_change_percentage_24h_in_currency') or c.get('price_change_percentage_24h') or 0.0)
    chg_7d = float(c.get('price_change_percentage_7d_in_currency') or 0.0)
    chg_30d = float(c.get('price_change_percentage_30d_in_currency') or 0.0)
    mcap = float(c.get('market_cap') or 1.0)
    fdv = float(c.get('fully_diluted_valuation') or mcap)
    vol = float(c.get('total_volume') or 0.0)
    mc_fdv = min(1.0, mcap / max(1.0, fdv))
    rvol_proxy = min(25.0, (vol / max(1.0, mcap)) * 120.0)
    cat_base = CATALYST_BONUS.get(sym, 68)
    unlock_pen = UNLOCK_DILUTION_PENALTY.get(sym, int((1.0 - mc_fdv) * 25))
    ses_bonus = 2.6 if sym in REGION_AFFINITY.get(active_region, set()) else -0.5

    buy_4h = min(98, max(15, 58 + chg_1h * 2.5 + chg_24h * 1.1 + rvol_proxy * 0.6 + (cat_base - 68) * 0.4 - unlock_pen * 0.4 + ses_bonus))
    sell_4h = min(96, max(15, 52 - chg_1h * 2.2 - chg_24h * 1.0 + unlock_pen * 0.8))
    buy_1d = min(98, max(15, 56 + chg_24h * 1.2 + chg_7d * 0.45 + rvol_proxy * 0.5 + (cat_base - 65) * 0.65 - unlock_pen * 0.6 + ses_bonus))
    sell_1d = min(96, max(15, 50 - chg_24h * 1.1 - chg_7d * 0.35 + unlock_pen * 1.05))
    buy_1w = min(98, max(15, 55 + chg_7d * 0.65 + chg_30d * 0.25 + (cat_base - 65) * 0.8 + mc_fdv * 14 - unlock_pen * 0.75))
    sell_1w = min(96, max(15, 50 - chg_7d * 0.55 - chg_30d * 0.20 + unlock_pen * 1.15))
    buy_1m = min(98, max(15, 54 + chg_30d * 0.35 + (cat_base - 65) * 0.9 + mc_fdv * 18 - unlock_pen * 0.85))
    sell_1m = min(96, max(15, 52 - chg_30d * 0.30 + (1.0 - mc_fdv) * 28 + unlock_pen * 0.9))
    buy_cycle = min(98, max(15, 50 + (cat_base - 60) * 1.05 + mc_fdv * 26 - unlock_pen * 1.1))
    sell_cycle = min(96, max(15, 48 + (1.0 - mc_fdv) * 35 + unlock_pen * 1.1 - (cat_base - 68) * 0.5))

    return {
        'sym': sym, 'price': p, 'atr_pct': atr_pct, 'chg24': chg_24h, 'mc_fdv': mc_fdv,
        '4H': (buy_4h, sell_4h), '1D': (buy_1d, sell_1d),
        '1W': (buy_1w, sell_1w), '1M': (buy_1m, sell_1m),
        'CYCLE': (buy_cycle, sell_cycle)
    }

def fetch_top500_bulletproof():
    coins = []
    # Lapis 1: CoinMarketCap Public Top 500 API (1 Request untuk 500 koin, Bebas Rate-Limit GitHub Actions!)
    try:
        cmc_url = 'https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=500&sortBy=market_cap&sortType=desc&convert=USD'
        cmc_list = fetch_json(cmc_url).get('data', {}).get('cryptoCurrencyList', [])
        for item in cmc_list:
            sym = item.get('symbol', '').upper()
            q = (item.get('quotes') or [{}])[0]
            p = float(q.get('price') or 0.0)
            chg24 = float(q.get('percentChange24h') or 0.0)
            sw = max(0.025, abs(chg24) / 100.0 * 1.35)
            coins.append({
                'symbol': sym,
                'name': item.get('name', sym),
                'current_price': p,
                'high_24h': p * (1.0 + sw * 0.6),
                'low_24h': p * (1.0 - sw * 0.6),
                'price_change_percentage_1h_in_currency': float(q.get('percentChange1h') or 0.0),
                'price_change_percentage_24h_in_currency': chg24,
                'price_change_percentage_24h': chg24,
                'price_change_percentage_7d_in_currency': float(q.get('percentChange7d') or 0.0),
                'price_change_percentage_30d_in_currency': float(q.get('percentChange30d') or 0.0),
                'market_cap': float(q.get('marketCap') or 1.0),
                'fully_diluted_valuation': float(q.get('fullyDilutedMarketCap') or q.get('marketCap') or 1.0),
                'total_volume': float(q.get('volume24h') or 0.0)
            })
    except Exception as e:
        print('CMC fallback notice:', e)

    # Lapis 2: CoinGecko Top 250 jika CMC kosong
    if len(coins) < 30:
        try:
            u1 = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&price_change_percentage=1h,24h,7d,30d'
            coins.extend(fetch_json(u1))
        except Exception as e:
            print('CG fallback notice:', e)

    return [c for c in coins if not is_excluded_stable(c)]

def send_telegram_message(token, chat_id, text_html):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text_html, 'parse_mode': 'HTML'}).encode('utf-8')
        urllib.request.urlopen(url, data=data, timeout=20)
        print('Telegram HTML alert sent successfully!')
    except Exception as e:
        print('HTML parse fallback to plain text:', e)
        plain = text_html.replace('<b>', '').replace('</b>', '')
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': plain}).encode('utf-8')
        urllib.request.urlopen(url, data=data, timeout=20)

def run_scanner():
    t_str, region, vol_mult, sl_mult, session_note = get_wib_session_info()
    coins = fetch_top500_bulletproof()
    try:
        fng = fetch_json('https://api.alternative.me/fng/?limit=1')['data'][0]
        fng_str = f"{fng['value']} ({fng['value_classification']})"
    except Exception:
        fng_str = "37 (Fear)"

    pool = [score_coin_horizons(c, region) for c in coins]
    btc = next((x for x in pool if x['sym'] == 'BTC'), pool[0])
    bp = btc['price']
    bmsb_low, bmsb_high = bp * 0.955, bp * 0.972
    retrace_zone = f"${bp*0.962:,.0f}–${bp*0.978:,.0f}"
    v_prob = 74 if btc['chg24'] < -2.5 else 66
    v_target = f"${bp*1.045:,.0f} -> ${bp*1.082:,.0f}"

    if btc['chg24'] <= -4.5:
        shock_alert = f"🚨 <b>DUMP/CRASH ALERT ({btc['chg24']:+.1f}%)</b>: Jika withdrawal bursa normal (bukan insolvensi FTX), Prob. V-Shape Recovery {v_prob}% ke {v_target}."
    elif btc['chg24'] >= 4.5:
        shock_alert = f"🚀 <b>BREAKOUT LEG-UP ({btc['chg24']:+.1f}%)</b>: Siaga Post-Breakout Retracement di Fib 50–61.8% ({retrace_zone})."
    else:
        shock_alert = f"⚡ <b>STANDBY RADAR</b>: Siklus 4-Thn (Bln 31 Halving) | BMSB BTC: ${bmsb_low:,.0f}–${bmsb_high:,.0f} | Retrace Buy: {retrace_zone} | V-Recovery {v_prob}% ({v_target})."

    horizons = [
        ('4H', '⏱️ TF 4H (Intraday 1–3H)'),
        ('1D', '📅 TF 1D (Daily Swing)'),
        ('1W', '📆 TF 1W (Weekly Trend)'),
        ('1M', '🗓️ TF 1M (Monthly Macro)'),
        ('CYCLE', '🔄 LONG-TERM (Cycle)')
    ]

    lines = [
        f"⚡ <b>QUANTPULSE v6.0 MULTI-TIMEFRAME & SESSION ALERT</b>",
        f"🕒 Waktu: <b>{t_str}</b> | BTC: <b>{fmt_p(bp)} ({btc['chg24']:+.2f}%)</b> | F&G: <b>{fng_str}</b>",
        session_note,
        shock_alert,
        "━━━━━━━━━━━━━━━━━━━━",
        "🟢 <b>TOP 3 BUY PER TIMEFRAME (Beserta TP & SL):</b>"
    ]
    for hk, hlabel in horizons:
        top_b = sorted(pool, key=lambda x: x[hk][0], reverse=True)[:3]
        lines.append(f"<b>{hlabel}:</b>")
        for i, x in enumerate(top_b, 1):
            tp, sl = calc_tp_sl(x['price'], x['atr_pct'], hk, vol_mult, sl_mult, False)
            lines.append(f"  {i}. <b>{x['sym']}</b> ({fmt_p(x['price'])}) 🎯TP: <b>{fmt_p(tp)}</b> | 🛡️SL: <b>{fmt_p(sl)}</b> (Skor {x[hk][0]:.0f})")

    lines.append("")
    lines.append("🔴 <b>TOP 3 SELL / SHORT PER TIMEFRAME (Beserta TP & SL):</b>")
    for hk, hlabel in horizons:
        top_s = sorted(pool, key=lambda x: x[hk][1], reverse=True)[:3]
        lines.append(f"<b>{hlabel}:</b>")
        for i, x in enumerate(top_s, 1):
            tp, sl = calc_tp_sl(x['price'], x['atr_pct'], hk, vol_mult, sl_mult, True)
            lines.append(f"  {i}. <b>{x['sym']}</b> ({fmt_p(x['price'])}) 🎯TP: <b>{fmt_p(tp)}</b> | 🛡️SL: <b>{fmt_p(sl)}</b> (Skor {x[hk][1]:.0f})")

    msg = "\n".join(lines)
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat_id:
        send_telegram_message(token, chat_id, msg)

if __name__ == '__main__':
    run_scanner()
