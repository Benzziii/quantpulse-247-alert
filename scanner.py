import os, urllib.request, urllib.parse, json
from datetime import datetime, timezone, timedelta

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'QuantPulse-v5/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

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
    'USDB','EURC','EURT','PAXG','XAUT','WBTC','STETH','WSTETH','RETH','WEETH','EZETH'
}
REGION_AFFINITY = {
    'ASIA': {'SUI','TAO','XRP','BNB','PEPE','DOGE','SHIB','TRX','TON','KAS','ARX','APT','SEI','NEAR'},
    'EUROPE': {'BTC','ETH','LINK','AAVE','UNI','MKR','ENA','CRV','LDO','DOT','AVAX','POL','QNT'},
    'US': {'BTC','ETH','SOL','ONDO','LINK','AAVE','HYPE','TAO','RENDER','FET','SUI','INJ','ARX','JUP','PYTH'}
}

def get_wib_session_info():
    wib = datetime.now(timezone.utc) + timedelta(hours=7)
    h_dec = wib.hour + wib.minute / 60.0
    t_str = wib.strftime('%H:%M WIB')
    if 6.75 <= h_dec < 9.0:
        return t_str, 'ASIA', 1.18, 1.15, '🌅 *JAM RAWAN ASIA OPEN & 1D CLOSE (07:00–09:00 WIB)*: Awas Stop-Hunt pergantian candle harian!'
    if 9.0 <= h_dec < 13.75:
        return t_str, 'ASIA', 1.00, 1.00, '☀️ *SESI ASIA AKTIF (09:00–14:00 WIB)*: Range akumulasi Asia; siaga sweep jelang Europe Open 14:00 WIB.'
    if 13.75 <= h_dec < 16.25:
        return t_str, 'EUROPE', 1.22, 1.18, '🌍 *JAM RAWAN EUROPE/LONDON OPEN & ASIAN CLOSE (14:00–16:00 WIB)*: Waspada Judas Swing / Sweep High-Low Asia!'
    if 16.25 <= h_dec < 20.25:
        return t_str, 'EUROPE', 1.08, 1.08, '🌍 *SESI EROPA AKTIF (16:00–20:30 WIB)*: Siaga rilis data makro AS (19:30/20:30 WIB) & Wall St Open.'
    if 20.25 <= h_dec < 22.5:
        return t_str, 'US', 1.38, 1.25, '🗽 *JAM PALING RAWAN: US MARKET & ETF OPEN (20:30–22:30 WIB)*: Volatilitas puncak! Tunggu scam-wick 30m pertama selesai, SL diperlebar +25%.'
    if 22.5 <= h_dec < 23.75:
        return t_str, 'US', 1.20, 1.15, '🌆 *JAM RAWAN EUROPE/LONDON CLOSE (22:30–23:30 WIB)*: Waspada profit-taking / intraday reversal London Fix!'
    if 2.75 <= h_dec < 4.5:
        return t_str, 'US', 1.16, 1.18, '🌙 *JAM RAWAN US MARKET CLOSE & CME SETTLEMENT (03:00–04:30 WIB)*: Likuiditas menipis pasca US Close, hindari market order besar!'
    return t_str, 'US', 1.05, 1.05, '🗽 *SESI AS SORE / OVERNIGHT*: Mengikuti arus penutupan ETF Spot & indeks Nasdaq.'

def is_excluded_stable(c):
    sym = (c.get('symbol') or '').upper()
    name = (c.get('name') or '').upper()
    p = c.get('current_price') or 0.0
    chg = abs(c.get('price_change_percentage_24h') or 0.0)
    if sym in STABLE_OR_WRAPPED: return True
    if 'USD' in sym and sym != 'PYTH': return True
    if any(w in name for w in ('USD', 'DOLLAR', 'STABLE', 'WRAPPED', 'STAKED')): return True
    if 0.975 <= p <= 1.025 and chg < 0.8: return True
    return False

def calc_tp_sl(p, atr_pct, hz, vol_mult, sl_mult, is_sell=False):
    atr = max(1.8, atr_pct) / 100.0
    mult = {
        '4H': (1.10 * vol_mult, 0.78 * sl_mult),
        '1D': (1.85, 1.25 * sl_mult),
        '1W': (4.20, 2.60), '1M': (8.50, 4.80), 'CYCLE': (16.0, 7.50)
    }.get(hz, (1.85, 1.25))
    if is_sell:
        return p * max(0.15, 1 - atr * mult[0]), p * (1 + atr * mult[1])
    return p * (1 + atr * mult[0]), p * max(0.15, 1 - atr * mult[1])

def score_coin_horizons(c, active_region):
    sym = c['symbol'].upper()
    p = c.get('current_price') or 0.0
    hi = c.get('high_24h') or (p * 1.03)
    lo = c.get('low_24h') or (p * 0.97)
    atr_pct = max(2.2, min(14.0, ((hi - lo) / max(0.00001, p)) * 100))
    chg_1h = c.get('price_change_percentage_1h_in_currency') or 0.0
    chg_24h = c.get('price_change_percentage_24h_in_currency') or c.get('price_change_percentage_24h') or 0.0
    chg_7d = c.get('price_change_percentage_7d_in_currency') or 0.0
    chg_30d = c.get('price_change_percentage_30d_in_currency') or 0.0
    mcap = c.get('market_cap') or 1
    fdv = c.get('fully_diluted_valuation') or mcap
    vol = c.get('total_volume') or 0
    mc_fdv = min(1.0, mcap / max(1, fdv))
    rvol_proxy = min(25.0, (vol / max(1, mcap)) * 120)
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

def fetch_top500():
    u1 = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&price_change_percentage=1h,24h,7d,30d'
    u2 = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=2&price_change_percentage=1h,24h,7d,30d'
    coins = []
    try: coins.extend(fetch_json(u1))
    except Exception: pass
    try: coins.extend(fetch_json(u2))
    except Exception: pass
    return [c for c in coins if not is_excluded_stable(c)]

def run_scanner():
    t_str, region, vol_mult, sl_mult, session_note = get_wib_session_info()
    coins = fetch_top500()
    fng = fetch_json('https://api.alternative.me/fng/?limit=1')['data'][0]
    gdata = fetch_json('https://api.coingecko.com/api/v3/global')['data']
    btc_d = gdata['market_cap_percentage'].get('btc', 57.4)
    pool = [score_coin_horizons(c, region) for c in coins]

    btc = next((x for x in pool if x['sym'] == 'BTC'), pool[0])
    bp = btc['price']
    bmsb_low, bmsb_high = bp * 0.955, bp * 0.972
    retrace_zone = f"${bp*0.962:,.0f}–${bp*0.978:,.0f}"
    v_prob = 74 if btc['chg24'] < -2.5 else 66
    v_target = f"${bp*1.045:,.0f} -> ${bp*1.082:,.0f}"

    if btc['chg24'] <= -4.5:
        shock_alert = f"🚨 *DUMP/CRASH ALERT ({btc['chg24']:+.1f}%)*: Jika penarikan bursa normal (bukan insolvensi FTX), Prob. V-Shape Recovery {v_prob}% ke {v_target}."
    elif btc['chg24'] >= 4.5:
        shock_alert = f"🚀 *BREAKOUT LEG-UP ({btc['chg24']:+.1f}%)*: Siaga Post-Breakout Retracement di Fib 50–61.8% ({retrace_zone})."
    else:
        shock_alert = f"⚡ *STANDBY*: Siklus 4-Thn (Bln 31 Halving) | BMSB BTC: ${bmsb_low:,.0f}–${bmsb_high:,.0f} | Retrace Buy: {retrace_zone} | V-Recovery {v_prob}% ({v_target})."

    horizons = [('4H','⏱️ 4H'), ('1D','📅 1D'), ('1W','📆 1W'), ('1M','🗓️ 1M'), ('CYCLE','🔄 CYCLE')]
    msg = f"⚡ *QUANTPULSE v5.0 SESSION & MTF ALERT ({t_str})*\n"
    msg += f"BTC: *${bp:,.0f}* | BTC.D: *{btc_d:.2f}%* | F&G: *{fng['value']} ({fng['value_classification']})*\n"
    msg += f"{session_note}\n{shock_alert}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🟢 *TOP 3 BUY (TP & SL Disesuaikan Sesi):*\n"
    for hk, hlabel in horizons:
        top_b = sorted(pool, key=lambda x: x[hk][0], reverse=True)[:3]
        lines = []
        for x in top_b:
            tp, sl = calc_tp_sl(x['price'], x['atr_pct'], hk, vol_mult, sl_mult, False)
            lines.append(f"*{x['sym']}* (${x['price']:,.4g} | 🎯TP ${tp:,.4g} 🛡️SL ${sl:,.4g})")
        msg += f"{hlabel}: " + " · ".join(lines) + "\n"

    msg += "\n🔴 *TOP 3 SELL / SHORT (TP & SL Disesuaikan Sesi):*\n"
    for hk, hlabel in horizons:
        top_s = sorted(pool, key=lambda x: x[hk][1], reverse=True)[:3]
        lines = []
        for x in top_s:
            tp, sl = calc_tp_sl(x['price'], x['atr_pct'], hk, vol_mult, sl_mult, True)
            lines.append(f"*{x['sym']}* (${x['price']:,.4g} | 🎯TP ${tp:,.4g} 🛡️SL ${sl:,.4g})")
        msg += f"{hlabel}: " + " · ".join(lines) + "\n"

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat_id:
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data)

if __name__ == '__main__':
    run_scanner()
