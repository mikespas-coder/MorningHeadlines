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
NYT_KEY = os.environ.get('NYT_KEY')

if not NYT_KEY:
    raise EnvironmentError("NYT_KEY environment variable is not set. Please export it before running.")

# Teams to track
TRACKED_TEAMS = {
    "knicks":  {"nba_id": "1610612752", "display": "NY Knicks",        "league": "nba"},
    "sabres":  {"nhl_id": "7",          "display": "Buffalo Sabres",   "league": "nhl"},
    "nuggets": {"nba_id": "1610612743", "display": "Denver Nuggets",   "league": "nba"},
    "bulls":   {"nba_id": "1610612741", "display": "Chicago Bulls",    "league": "nba"},
}

TEAM_KEYWORDS = [
    "knicks", "new york knicks",
    "sabres", "buffalo sabres",
    "nuggets", "denver nuggets",
    "bulls", "chicago bulls",
]


# ─────────────────────────────────────────────
#  DATA FETCHING
# ─────────────────────────────────────────────

def fetch_nyt_section(section: str) -> list[dict]:
    """Fetch up to 3 articles from a single NYT Top Stories section."""
    url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('results', [])[:3]
    except Exception as e:
        logger.error(f"[NYT/{section}] Failed to fetch: {e}")
        return []


def fetch_nyt_data() -> dict[str, list[dict]]:
    sections = ["home", "nyregion", "opinion", "food", "style"]
    return {section: fetch_nyt_section(section) for section in sections}


def fetch_nyt_sports() -> list[dict]:
    """Fetch NYT sports section and filter for tracked teams only."""
    url = f"https://api.nytimes.com/svc/topstories/v2/sports.json?api-key={NYT_KEY}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        all_articles = response.json().get('results', [])
        matched = []
        for article in all_articles:
            text = (article.get('title', '') + ' ' + article.get('abstract', '')).lower()
            if any(kw in text for kw in TEAM_KEYWORDS):
                matched.append(article)
        return matched[:5]
    except Exception as e:
        logger.error(f"[NYT/sports] Failed to fetch: {e}")
        return []


def fetch_buffalo_news() -> list[dict]:
    feed_url = "https://www.wivb.com/news/local-news/buffalo/feed/"
    try:
        feed = feedparser.parse(feed_url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        if not feed.entries:
            logger.warning("[WIVB] Feed returned no entries.")
            return []
        return [{"title": e.title, "link": e.link} for e in feed.entries[:6]]
    except Exception as e:
        logger.error(f"[WIVB] Failed to fetch: {e}")
        return []


def fetch_bbc_middle_east() -> list[dict]:
    feed_url = "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"
    try:
        feed = feedparser.parse(feed_url, agent='Mozilla/5.0')
        if not feed.entries:
            logger.warning("[BBC] Feed returned no entries.")
            return []
        return [
            {
                "title": e.title,
                "link": e.link,
                "summary": e.get('summary', e.get('description', ''))
            }
            for e in feed.entries[:6]
        ]
    except Exception as e:
        logger.error(f"[BBC] Failed to fetch: {e}")
        return []


def fetch_weather() -> Optional[dict]:
    try:
        res = requests.get(
            "https://api.weather.gov/gridpoints/BUF/78,43/forecast", timeout=5
        )
        res.raise_for_status()
        today = res.json()['properties']['periods'][0]
        return {
            "temp": today['temperature'],
            "unit": today['temperatureUnit'],
            "forecast": today['shortForecast'],
        }
    except Exception as e:
        logger.error(f"[Weather] Failed to fetch: {e}")
        return None


# ─────────────────────────────────────────────
#  SPORTS DATA
# ─────────────────────────────────────────────

def nba_team_games(team_id: str, date_str: str) -> list[dict]:
    """Fetch NBA games for a team on a given date (YYYY-MM-DD)."""
    url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nba.com/",
        "Accept": "application/json",
    }
    try:
        res = requests.get(url, headers=headers, timeout=8)
        res.raise_for_status()
        data = res.json()
        # GameHeader resultSet
        game_header = next(r for r in data['resultSets'] if r['name'] == 'GameHeader')
        line_score  = next(r for r in data['resultSets'] if r['name'] == 'LineScore')
        gh_idx  = {h: i for i, h in enumerate(game_header['headers'])}
        ls_idx  = {h: i for i, h in enumerate(line_score['headers'])}

        games = []
        for row in game_header['rowSet']:
            game_id    = row[gh_idx['GAME_ID']]
            home_id    = str(row[gh_idx['HOME_TEAM_ID']])
            visitor_id = str(row[gh_idx['VISITOR_TEAM_ID']])
            status     = row[gh_idx['GAME_STATUS_TEXT']]

            if team_id not in (home_id, visitor_id):
                continue

            # Pull scores from LineScore
            scores = {}
            for ls_row in line_score['rowSet']:
                if ls_row[ls_idx['GAME_ID']] == game_id:
                    tid  = str(ls_row[ls_idx['TEAM_ID']])
                    abbr = ls_row[ls_idx['TEAM_ABBREVIATION']]
                    pts  = ls_row[ls_idx['PTS']]
                    scores[tid] = {"abbr": abbr, "pts": pts}

            home_info    = scores.get(home_id, {})
            visitor_info = scores.get(visitor_id, {})

            games.append({
                "home":        home_info.get("abbr", "?"),
                "home_pts":    home_info.get("pts"),
                "visitor":     visitor_info.get("abbr", "?"),
                "visitor_pts": visitor_info.get("pts"),
                "status":      status.strip(),
                "date":        date_str,
            })
        return games
    except Exception as e:
        logger.error(f"[NBA] Team {team_id} on {date_str}: {e}")
        return []


def nhl_team_games(team_id: str, date_str: str) -> list[dict]:
    """Fetch NHL games for a team on a given date using the NHL API v1."""
    url = f"https://api-web.nhle.com/v1/score/{date_str}"
    try:
        res = requests.get(url, timeout=8)
        res.raise_for_status()
        games_raw = res.json().get("games", [])
        games = []
        for g in games_raw:
            home_id    = str(g.get("homeTeam", {}).get("id", ""))
            away_id    = str(g.get("awayTeam", {}).get("id", ""))
            if team_id not in (home_id, away_id):
                continue
            state = g.get("gameState", "")
            if state in ("OFF", "FINAL"):
                status = "Final"
            elif state in ("LIVE", "CRIT"):
                period = g.get("period", "")
                status = f"Live – P{period}"
            else:
                start = g.get("startTimeUTC", "")
                # Parse UTC time and convert to ET
                try:
                    dt_utc = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
                    dt_et  = dt_utc.astimezone(ZoneInfo("America/New_York"))
                    status = dt_et.strftime("%-I:%M %p ET")
                except Exception:
                    status = "Scheduled"

            home  = g.get("homeTeam", {})
            away  = g.get("awayTeam", {})
            games.append({
                "home":        home.get("abbrev", "?"),
                "home_pts":    home.get("score"),
                "visitor":     away.get("abbrev", "?"),
                "visitor_pts": away.get("score"),
                "status":      status,
                "date":        date_str,
            })
        return games
    except Exception as e:
        logger.error(f"[NHL] Team {team_id} on {date_str}: {e}")
        return []


def fetch_all_sports_data() -> list[dict]:
    """
    For each tracked team, fetch:
      - yesterday's result
      - today's game
      - tomorrow's game
    Returns a list of team-game dicts ready for rendering.
    """
    now       = datetime.now(ZoneInfo("America/New_York"))
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today     = now.strftime("%Y-%m-%d")
    tomorrow  = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    results = []

    for key, info in TRACKED_TEAMS.items():
        team_entry = {"display": info["display"], "games": []}

        if info["league"] == "nba":
            tid = info["nba_id"]
            for d in [yesterday, today, tomorrow]:
                team_entry["games"].extend(nba_team_games(tid, d))
        else:
            tid = info["nhl_id"]
            for d in [yesterday, today, tomorrow]:
                team_entry["games"].extend(nhl_team_games(tid, d))

        results.append(team_entry)

    return results


# ─────────────────────────────────────────────
#  HTML RENDERING
# ─────────────────────────────────────────────

def truncate(text: str, limit: int = 140) -> str:
    return text[:limit] + ('...' if len(text) > limit else '')


def render_nyt(nyt_data: dict[str, list[dict]]) -> str:
    section_titles = {
        "home":    "Global News",
        "nyregion":"New York State",
        "opinion": "Op-Ed",
        "food":    "Food & Wine",
        "style":   "Style & Culture",
    }
    html = ""
    for section, articles in nyt_data.items():
        title = section_titles.get(section, section)
        html += f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>{title}</h2>"
        if not articles:
            html += "<p class='text-sm text-gray-400 italic'>Stories currently unavailable.</p>"
            continue
        for item in articles:
            abstract = truncate(item.get('abstract', ''))
            html += (
                f"<div class='mb-6'>"
                f"<a href='{item['url']}' target='_blank' class='text-blue-800 font-bold hover:underline'>{item['title']}</a>"
                f"<p class='text-gray-600 text-sm mt-1'>{abstract}</p>"
                f"</div>"
            )
    return html


def render_nyt_sports(articles: list[dict]) -> str:
    if not articles:
        return ""  # Skip section entirely if no relevant stories
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-green-200 pb-1 uppercase text-green-800'>Sports Headlines</h2>"
    for item in articles:
        abstract = truncate(item.get('abstract', ''))
        html += (
            f"<div class='mb-6 p-3 bg-green-50/30 border-l-4 border-green-600 rounded-r'>"
            f"<a href='{item['url']}' target='_blank' class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>{item['title']}</a>"
            f"<p class='text-gray-700 text-xs font-serif leading-snug'>{abstract}</p>"
            f"</div>"
        )
    return html


def render_buffalo(articles: list[dict]) -> str:
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>Buffalo Local News (WIVB)</h2>"
    if not articles:
        return html + "<p class='text-sm text-gray-400 italic'>Local news currently unavailable.</p>"
    for item in articles:
        html += (
            f"<div class='mb-4'>"
            f"<a href='{item['link']}' target='_blank' class='text-red-700 font-bold hover:underline'>{item['title']}</a>"
            f"</div>"
        )
    return html


def render_bbc(articles: list[dict]) -> str:
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-red-200 pb-1 uppercase text-red-800'>Middle East Update (BBC)</h2>"
    if not articles:
        return html + "<p class='text-sm text-gray-400 italic'>BBC feed currently unavailable.</p>"
    for item in articles:
        summary = truncate(item.get('summary', ''), 180)
        html += (
            f"<div class='mb-6 p-3 bg-red-50/30 border-l-4 border-red-600 rounded-r'>"
            f"<a href='{item['link']}' target='_blank' class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>{item['title']}</a>"
            f"<p class='text-gray-700 text-xs font-serif leading-snug'>{summary}</p>"
            f"</div>"
        )
    return html


def render_weather(weather: Optional[dict]) -> str:
    if not weather:
        return "<p class='text-sm text-gray-400 italic mt-6'>Weather unavailable.</p>"
    return (
        f"<div class='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>"
        f"<h3 class='text-xs font-black uppercase tracking-widest text-blue-800 mb-1'>Buffalo Weather</h3>"
        f"<p class='text-lg font-bold'>{weather['temp']}°{weather['unit']}</p>"
        f"<p class='text-[10px] text-blue-600 font-medium uppercase'>{weather['forecast']}</p>"
        f"</div>"
    )


def _score_line(game: dict) -> str:
    """Format a single game row inside a scoreboard card."""
    v      = game["visitor"]
    h      = game["home"]
    v_pts  = game["visitor_pts"]
    h_pts  = game["home_pts"]
    status = game["status"]

    is_final = "final" in status.lower()
    is_live  = "live" in status.lower()

    if v_pts is not None and h_pts is not None:
        score_str = f"{v} {v_pts} – {h_pts} {h}"
    else:
        score_str = f"{v} @ {h}"

    # Colour-code status
    if is_final:
        status_cls = "text-gray-400"
    elif is_live:
        status_cls = "text-red-600 font-bold animate-pulse"
    else:
        status_cls = "text-green-700"

    return (
        f"<div class='flex justify-between items-center text-xs py-1 border-b border-gray-100 last:border-0'>"
        f"<span class='font-mono font-semibold'>{score_str}</span>"
        f"<span class='{status_cls} ml-2 whitespace-nowrap'>{status}</span>"
        f"</div>"
    )


def render_scoreboard(sports_data: list[dict]) -> str:
    """Render the sidebar scoreboard widget."""
    html = (
        "<div class='mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg'>"
        "<h3 class='text-xs font-black uppercase tracking-widest text-gray-700 mb-3'>Scoreboard</h3>"
    )

    any_games = False
    for team in sports_data:
        if not team["games"]:
            continue
        any_games = True
        html += (
            f"<div class='mb-4'>"
            f"<p class='text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1'>{team['display']}</p>"
        )
        for game in team["games"]:
            html += _score_line(game)
        html += "</div>"

    if not any_games:
        html += "<p class='text-xs text-gray-400 italic'>No games found in this window.</p>"

    html += "</div>"
    return html


# ─────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────

def build_layout(
    news_html: str,
    local_html: str,
    bbc_html: str,
    weather_html: str,
    scoreboard_html: str,
    sports_html: str,
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
                {sports_html}
                {news_html}
            </div>
            <div class="md:col-span-1 border-l border-gray-100 pl-6">
                {weather_html}
                {scoreboard_html}
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
    weather_data  = fetch_weather()
    nyt_data      = fetch_nyt_data()
    buffalo_data  = fetch_buffalo_news()
    bbc_data      = fetch_bbc_middle_east()
    sports_data   = fetch_all_sports_data()
    sports_articles = fetch_nyt_sports()

    logger.info("Rendering HTML...")
    html = build_layout(
        news_html      = render_nyt(nyt_data),
        local_html     = render_buffalo(buffalo_data),
        bbc_html       = render_bbc(bbc_data),
        weather_html   = render_weather(weather_data),
        scoreboard_html= render_scoreboard(sports_data),
        sports_html    = render_nyt_sports(sports_articles),
    )

    output_path = "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Done! Output written to {output_path}")
