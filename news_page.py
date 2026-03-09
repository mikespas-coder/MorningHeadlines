import requests
import feedparser
import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
NYT_KEY     = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')

if not NYT_KEY:
    raise EnvironmentError("NYT_KEY environment variable is not set.")
if not FINNHUB_KEY:
    raise EnvironmentError("FINNHUB_KEY environment variable is not set.")

# ── Sports ────────────────────────────────────────────────────────────────────
TRACKED_TEAMS = {
    "knicks":  {"nba_id": "1610612752", "display": "NY Knicks",       "league": "nba"},
    "sabres":  {"nhl_id": "7",          "display": "Buffalo Sabres",  "league": "nhl"},
    "nuggets": {"nba_id": "1610612743", "display": "Denver Nuggets",  "league": "nba"},
    "bulls":   {"nba_id": "1610612741", "display": "Chicago Bulls",   "league": "nba"},
}
TEAM_KEYWORDS = [
    "knicks", "new york knicks",
    "sabres", "buffalo sabres",
    "nuggets", "denver nuggets",
    "bulls", "chicago bulls",
]

# ── Stocks ────────────────────────────────────────────────────────────────────
# AI & tech watchlist (curated)
AI_WATCHLIST = [
    ("NVDA",  "Nvidia"),
    ("MSFT",  "Microsoft"),
    ("GOOGL", "Alphabet"),
    ("META",  "Meta"),
    ("AMZN",  "Amazon"),
    ("AAPL",  "Apple"),
    ("TSM",   "TSMC"),
    ("AMD",   "AMD"),
    ("ORCL",  "Oracle"),
    ("PLTR",  "Palantir"),
    ("ARM",   "Arm Holdings"),
    ("SOUN",  "SoundHound"),
]

# High-volume proxy pool for "most active" (Finnhub free tier has no screener)
ACTIVE_PROXY = [
    "SPY","QQQ","AAPL","TSLA","NVDA","AMZN","MSFT",
    "AMD","META","GOOGL","BAC","F","PLTR","INTC","XOM",
]


# ─────────────────────────────────────────────
#  DATA FETCHING
# ─────────────────────────────────────────────

def fetch_nyt_section(section: str) -> list[dict]:
    url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json().get('results', [])[:3]
    except Exception as e:
        logger.error(f"[NYT/{section}] {e}")
        return []


def fetch_nyt_data() -> dict[str, list[dict]]:
    sections = ["home", "nyregion", "opinion", "food", "style"]
    return {s: fetch_nyt_section(s) for s in sections}


def fetch_nyt_sports() -> list[dict]:
    url = f"https://api.nytimes.com/svc/topstories/v2/sports.json?api-key={NYT_KEY}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return [
            a for a in r.json().get('results', [])
            if any(kw in (a.get('title','') + ' ' + a.get('abstract','')).lower()
                   for kw in TEAM_KEYWORDS)
        ][:5]
    except Exception as e:
        logger.error(f"[NYT/sports] {e}")
        return []


def fetch_buffalo_news() -> list[dict]:
    try:
        feed = feedparser.parse(
            "https://www.wivb.com/news/local-news/buffalo/feed/",
            agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        )
        return [{"title": e.title, "link": e.link} for e in feed.entries[:6]]
    except Exception as e:
        logger.error(f"[WIVB] {e}")
        return []


def fetch_bbc_middle_east() -> list[dict]:
    try:
        feed = feedparser.parse(
            "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
            agent='Mozilla/5.0'
        )
        return [
            {"title": e.title, "link": e.link,
             "summary": e.get('summary', e.get('description', ''))}
            for e in feed.entries[:6]
        ]
    except Exception as e:
        logger.error(f"[BBC] {e}")
        return []


def fetch_cnbc_business() -> list[dict]:
    """
    CNBC public RSS feeds — tries multiple in order and returns first that works.
    Finance/Wall St → Market Insider → World Top News
    """
    feeds = [
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",   # Finance / Wall St
        "https://www.cnbc.com/id/20409666/device/rss/rss.html",   # Market Insider
        "https://www.cnbc.com/id/100727362/device/rss/rss.html",  # World Top News
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url, agent='Mozilla/5.0')
            if feed.entries:
                return [
                    {
                        "title":   e.title,
                        "link":    e.link,
                        "summary": e.get('summary', e.get('description', '')),
                    }
                    for e in feed.entries[:6]
                ]
        except Exception as e:
            logger.warning(f"[CNBC] {url} failed: {e}")
    logger.error("[CNBC] All feeds failed.")
    return []


def fetch_weather() -> Optional[dict]:
    try:
        r = requests.get(
            "https://api.weather.gov/gridpoints/BUF/78,43/forecast", timeout=5
        )
        r.raise_for_status()
        p = r.json()['properties']['periods'][0]
        return {"temp": p['temperature'], "unit": p['temperatureUnit'],
                "forecast": p['shortForecast']}
    except Exception as e:
        logger.error(f"[Weather] {e}")
        return None


# ─────────────────────────────────────────────
#  STOCKS  (Finnhub)
# ─────────────────────────────────────────────

def _finnhub_quote(symbol: str) -> Optional[dict]:
    """Single Finnhub /quote call."""
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": FINNHUB_KEY},
            timeout=5,
        )
        r.raise_for_status()
        d = r.json()
        if d.get('c', 0) == 0:
            return None
        return {
            "symbol":     symbol,
            "price":      d['c'],
            "change_abs": d.get('d',  0.0),
            "change_pct": d.get('dp', 0.0),
        }
    except Exception as e:
        logger.error(f"[Finnhub] {symbol}: {e}")
        return None


def fetch_stock_data() -> dict:
    """
    Returns:
      most_active  — top 10 from ACTIVE_PROXY, sorted by |% change| (biggest movers)
      ai_watchlist — AI_WATCHLIST quotes with display names
    """
    logger.info("Fetching stock quotes...")

    # Most active / top movers
    proxy_quotes = []
    for sym in ACTIVE_PROXY:
        q = _finnhub_quote(sym)
        if q:
            proxy_quotes.append(q)
    proxy_quotes.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    most_active = proxy_quotes[:10]

    # AI watchlist
    ai_stocks = []
    for symbol, display in AI_WATCHLIST:
        q = _finnhub_quote(symbol)
        if q:
            q["display"] = display
            ai_stocks.append(q)

    return {"most_active": most_active, "ai_watchlist": ai_stocks}


# ─────────────────────────────────────────────
#  SPORTS  (NBA / NHL public APIs)
# ─────────────────────────────────────────────

def nba_team_games(team_id: str, date_str: str) -> list[dict]:
    url = (f"https://stats.nba.com/stats/scoreboardV2"
           f"?DayOffset=0&LeagueID=00&gameDate={date_str}")
    headers = {"User-Agent": "Mozilla/5.0",
               "Referer": "https://www.nba.com/", "Accept": "application/json"}
    try:
        res = requests.get(url, headers=headers, timeout=8)
        res.raise_for_status()
        data = res.json()
        gh  = next(r for r in data['resultSets'] if r['name'] == 'GameHeader')
        ls  = next(r for r in data['resultSets'] if r['name'] == 'LineScore')
        ghi = {h: i for i, h in enumerate(gh['headers'])}
        lsi = {h: i for i, h in enumerate(ls['headers'])}
        games = []
        for row in gh['rowSet']:
            gid  = row[ghi['GAME_ID']]
            hid  = str(row[ghi['HOME_TEAM_ID']])
            vid  = str(row[ghi['VISITOR_TEAM_ID']])
            status = row[ghi['GAME_STATUS_TEXT']]
            if team_id not in (hid, vid):
                continue
            scores = {}
            for lr in ls['rowSet']:
                if lr[lsi['GAME_ID']] == gid:
                    tid = str(lr[lsi['TEAM_ID']])
                    scores[tid] = {"abbr": lr[lsi['TEAM_ABBREVIATION']],
                                   "pts": lr[lsi['PTS']]}
            games.append({
                "home": scores.get(hid, {}).get("abbr", "?"),
                "home_pts": scores.get(hid, {}).get("pts"),
                "visitor": scores.get(vid, {}).get("abbr", "?"),
                "visitor_pts": scores.get(vid, {}).get("pts"),
                "status": status.strip(), "date": date_str,
            })
        return games
    except Exception as e:
        logger.error(f"[NBA] {team_id} on {date_str}: {e}")
        return []


def nhl_team_games(team_id: str, date_str: str) -> list[dict]:
    try:
        res = requests.get(
            f"https://api-web.nhle.com/v1/score/{date_str}", timeout=8
        )
        res.raise_for_status()
        games = []
        for g in res.json().get("games", []):
            hid = str(g.get("homeTeam", {}).get("id", ""))
            aid = str(g.get("awayTeam", {}).get("id", ""))
            if team_id not in (hid, aid):
                continue
            state = g.get("gameState", "")
            if state in ("OFF", "FINAL"):
                status = "Final"
            elif state in ("LIVE", "CRIT"):
                status = f"Live – P{g.get('period','')}"
            else:
                try:
                    dt = datetime.strptime(
                        g.get("startTimeUTC",""), "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=ZoneInfo("UTC"))
                    status = dt.astimezone(
                        ZoneInfo("America/New_York")
                    ).strftime("%-I:%M %p ET")
                except Exception:
                    status = "Scheduled"
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            games.append({
                "home": home.get("abbrev","?"), "home_pts": home.get("score"),
                "visitor": away.get("abbrev","?"), "visitor_pts": away.get("score"),
                "status": status, "date": date_str,
            })
        return games
    except Exception as e:
        logger.error(f"[NHL] {team_id} on {date_str}: {e}")
        return []


def fetch_all_sports_data() -> list[dict]:
    now       = datetime.now(ZoneInfo("America/New_York"))
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today     = now.strftime("%Y-%m-%d")
    tomorrow  = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    results = []
    for key, info in TRACKED_TEAMS.items():
        entry = {"display": info["display"], "games": []}
        if info["league"] == "nba":
            for d in [yesterday, today, tomorrow]:
                entry["games"].extend(nba_team_games(info["nba_id"], d))
        else:
            for d in [yesterday, today, tomorrow]:
                entry["games"].extend(nhl_team_games(info["nhl_id"], d))
        results.append(entry)
    return results


# ─────────────────────────────────────────────
#  HTML RENDERING
# ─────────────────────────────────────────────

def truncate(text: str, limit: int = 140) -> str:
    return text[:limit] + ('...' if len(text) > limit else '')


def _change_style(pct: float) -> tuple[str, str]:
    if pct > 0:   return "▲", "text-green-600"
    elif pct < 0: return "▼", "text-red-600"
    return "–", "text-gray-400"


def render_stock_row(q: dict, label: Optional[str] = None) -> str:
    arrow, cls = _change_style(q['change_pct'])
    name = label or q['symbol']
    return (
        f"<div class='flex items-center justify-between text-xs py-1 "
        f"border-b border-gray-100 last:border-0'>"
        f"<span class='font-mono font-bold text-gray-800 w-14 shrink-0'>{q['symbol']}</span>"
        f"<span class='text-gray-500 truncate flex-1 px-1 text-[10px]'>{name}</span>"
        f"<span class='font-semibold text-gray-900 w-14 text-right'>${q['price']:,.2f}</span>"
        f"<span class='{cls} font-bold w-14 text-right whitespace-nowrap'>"
        f"{arrow}{abs(q['change_pct']):.2f}%</span>"
        f"</div>"
    )


def render_stocks_sidebar(stock_data: dict) -> str:
    most_active  = stock_data.get("most_active", [])
    ai_watchlist = stock_data.get("ai_watchlist", [])

    html = (
        "<div class='mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg'>"
        "<h3 class='text-xs font-black uppercase tracking-widest text-gray-700 mb-1'>"
        "Top Movers</h3>"
        "<p class='text-[9px] text-gray-400 uppercase mb-3'>Prior session · by % move</p>"
    )
    for q in most_active:
        html += render_stock_row(q)
    if not most_active:
        html += "<p class='text-xs text-gray-400 italic'>Data unavailable.</p>"
    html += "</div>"

    html += (
        "<div class='mt-4 p-4 bg-indigo-50 border border-indigo-200 rounded-lg'>"
        "<h3 class='text-xs font-black uppercase tracking-widest text-indigo-800 mb-1'>"
        "AI Stocks</h3>"
        "<p class='text-[9px] text-indigo-400 uppercase mb-3'>Watchlist</p>"
    )
    for q in ai_watchlist:
        html += render_stock_row(q, label=q.get("display", q["symbol"]))
    if not ai_watchlist:
        html += "<p class='text-xs text-indigo-400 italic'>Data unavailable.</p>"
    html += "</div>"

    return html


def render_cnbc(articles: list[dict]) -> str:
    if not articles:
        return ""
    html = (
        "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-yellow-300 "
        "pb-1 uppercase text-yellow-800'>Markets &amp; Business (CNBC)</h2>"
    )
    for item in articles:
        summary = truncate(item.get('summary', ''), 180)
        html += (
            f"<div class='mb-6 p-3 bg-yellow-50/40 border-l-4 border-yellow-400 rounded-r'>"
            f"<a href='{item['link']}' target='_blank' "
            f"class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>"
            f"{item['title']}</a>"
            f"<p class='text-gray-700 text-xs font-serif leading-snug'>{summary}</p>"
            f"</div>"
        )
    return html


def render_nyt(nyt_data: dict[str, list[dict]]) -> str:
    section_titles = {
        "home":     "Global News",
        "nyregion": "New York State",
        "opinion":  "Op-Ed",
        "food":     "Food & Wine",
        "style":    "Style & Culture",
    }
    html = ""
    for section, articles in nyt_data.items():
        title = section_titles.get(section, section)
        html += (f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b "
                 f"border-gray-200 pb-1 uppercase'>{title}</h2>")
        if not articles:
            html += "<p class='text-sm text-gray-400 italic'>Stories currently unavailable.</p>"
            continue
        for item in articles:
            abstract = truncate(item.get('abstract', ''))
            html += (
                f"<div class='mb-6'>"
                f"<a href='{item['url']}' target='_blank' "
                f"class='text-blue-800 font-bold hover:underline'>{item['title']}</a>"
                f"<p class='text-gray-600 text-sm mt-1'>{abstract}</p>"
                f"</div>"
            )
    return html


def render_nyt_sports(articles: list[dict]) -> str:
    if not articles:
        return ""
    html = (
        "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-green-200 "
        "pb-1 uppercase text-green-800'>Sports Headlines</h2>"
    )
    for item in articles:
        abstract = truncate(item.get('abstract', ''))
        html += (
            f"<div class='mb-6 p-3 bg-green-50/30 border-l-4 border-green-600 rounded-r'>"
            f"<a href='{item['url']}' target='_blank' "
            f"class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>"
            f"{item['title']}</a>"
            f"<p class='text-gray-700 text-xs font-serif leading-snug'>{abstract}</p>"
            f"</div>"
        )
    return html


def render_buffalo(articles: list[dict]) -> str:
    html = ("<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 "
            "pb-1 uppercase'>Buffalo Local News (WIVB)</h2>")
    if not articles:
        return html + "<p class='text-sm text-gray-400 italic'>Local news currently unavailable.</p>"
    for item in articles:
        html += (
            f"<div class='mb-4'>"
            f"<a href='{item['link']}' target='_blank' "
            f"class='text-red-700 font-bold hover:underline'>{item['title']}</a>"
            f"</div>"
        )
    return html


def render_bbc(articles: list[dict]) -> str:
    html = ("<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-red-200 "
            "pb-1 uppercase text-red-800'>Middle East Update (BBC)</h2>")
    if not articles:
        return html + "<p class='text-sm text-gray-400 italic'>BBC feed currently unavailable.</p>"
    for item in articles:
        summary = truncate(item.get('summary', ''), 180)
        html += (
            f"<div class='mb-6 p-3 bg-red-50/30 border-l-4 border-red-600 rounded-r'>"
            f"<a href='{item['link']}' target='_blank' "
            f"class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>"
            f"{item['title']}</a>"
            f"<p class='text-gray-700 text-xs font-serif leading-snug'>{summary}</p>"
            f"</div>"
        )
    return html


def render_weather(weather: Optional[dict]) -> str:
    if not weather:
        return "<p class='text-sm text-gray-400 italic mt-6'>Weather unavailable.</p>"
    return (
        f"<div class='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>"
        f"<h3 class='text-xs font-black uppercase tracking-widest text-blue-800 mb-1'>"
        f"Buffalo Weather</h3>"
        f"<p class='text-lg font-bold'>{weather['temp']}°{weather['unit']}</p>"
        f"<p class='text-[10px] text-blue-600 font-medium uppercase'>{weather['forecast']}</p>"
        f"</div>"
    )


def _score_line(game: dict) -> str:
    v, h         = game["visitor"], game["home"]
    v_pts, h_pts = game["visitor_pts"], game["home_pts"]
    status       = game["status"]
    is_final     = "final" in status.lower()
    is_live      = "live"  in status.lower()
    score_str    = (f"{v} {v_pts} – {h_pts} {h}"
                    if v_pts is not None and h_pts is not None
                    else f"{v} @ {h}")
    status_cls   = ("text-gray-400" if is_final
                    else "text-red-600 font-bold animate-pulse" if is_live
                    else "text-green-700")
    return (
        f"<div class='flex justify-between items-center text-xs py-1 "
        f"border-b border-gray-100 last:border-0'>"
        f"<span class='font-mono font-semibold'>{score_str}</span>"
        f"<span class='{status_cls} ml-2 whitespace-nowrap'>{status}</span>"
        f"</div>"
    )


def render_scoreboard(sports_data: list[dict]) -> str:
    html = (
        "<div class='mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg'>"
        "<h3 class='text-xs font-black uppercase tracking-widest text-gray-700 mb-3'>"
        "Scoreboard</h3>"
    )
    any_games = False
    for team in sports_data:
        if not team["games"]:
            continue
        any_games = True
        html += (f"<div class='mb-4'>"
                 f"<p class='text-[10px] font-bold uppercase tracking-widest "
                 f"text-gray-500 mb-1'>{team['display']}</p>")
        for game in team["games"]:
            html += _score_line(game)
        html += "</div>"
    if not any_games:
        html += "<p class='text-xs text-gray-400 italic'>No games in this window.</p>"
    html += "</div>"
    return html


# ─────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────

def build_layout(
    news_html:       str,
    local_html:      str,
    bbc_html:        str,
    weather_html:    str,
    scoreboard_html: str,
    sports_html:     str,
    cnbc_html:       str,
    stocks_html:     str,
) -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-900 font-sans leading-snug">
    <div class="max-w-6xl mx-auto bg-white min-h-screen shadow-2xl">
        <header class="p-8 bg-black text-white text-center">
            <h1 class="text-5xl font-serif font-black italic tracking-tighter uppercase mb-2">The Daily Brief</h1>
            <p class="text-xs font-bold uppercase tracking-widest opacity-80">{now.strftime("%A, %B %d, %Y")}</p>
        </header>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6 md:p-12">
            <div class="md:col-span-3">
                {local_html}
                {bbc_html}
                {cnbc_html}
                {sports_html}
                {news_html}
            </div>
            <div class="md:col-span-1 border-l border-gray-100 pl-6">
                {weather_html}
                {scoreboard_html}
                {stocks_html}
            </div>
        </div>
    </div>
</body>
</html>"""


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Fetching data...")
    weather_data    = fetch_weather()
    nyt_data        = fetch_nyt_data()
    buffalo_data    = fetch_buffalo_news()
    bbc_data        = fetch_bbc_middle_east()
    cnbc_data       = fetch_cnbc_business()
    sports_data     = fetch_all_sports_data()
    sports_articles = fetch_nyt_sports()
    stock_data      = fetch_stock_data()

    logger.info("Rendering HTML...")
    html = build_layout(
        news_html       = render_nyt(nyt_data),
        local_html      = render_buffalo(buffalo_data),
        bbc_html        = render_bbc(bbc_data),
        weather_html    = render_weather(weather_data),
        scoreboard_html = render_scoreboard(sports_data),
        sports_html     = render_nyt_sports(sports_articles),
        cnbc_html       = render_cnbc(cnbc_data),
        stocks_html     = render_stocks_sidebar(stock_data),
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Done! Output written to index.html")
