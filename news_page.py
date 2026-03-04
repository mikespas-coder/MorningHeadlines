import requests
import feedparser
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

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


# ─────────────────────────────────────────────
#  DATA FETCHING  (returns dicts, not HTML)
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
    """Fetches all requested NYT sections. Returns a dict keyed by section name."""
    sections = ["home", "nyregion", "opinion", "food", "style"]
    return {section: fetch_nyt_section(section) for section in sections}


def fetch_buffalo_news() -> list[dict]:
    """Fetch Buffalo local news from WIVB RSS feed."""
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
    """Fetch Middle East news from BBC RSS feed."""
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


def fetch_weather() -> dict | None:
    """Fetch Buffalo weather from NWS. Returns a dict or None on failure."""
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
#  HTML RENDERING  (takes dicts, returns HTML)
# ─────────────────────────────────────────────

def truncate(text: str, limit: int = 140) -> str:
    """Truncate text and append ellipsis only when actually truncated."""
    return text[:limit] + ('...' if len(text) > limit else '')


def render_nyt(nyt_data: dict[str, list[dict]]) -> str:
    section_titles = {
        "home": "Global News",
        "nyregion": "New York State",
        "opinion": "Op-Ed",
        "food": "Food & Wine",
        "style": "Style & Culture",
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


def render_weather(weather: dict | None) -> str:
    if not weather:
        return "<p class='text-sm text-gray-400 italic mt-6'>Weather unavailable.</p>"
    return (
        f"<div class='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>"
        f"<h3 class='text-xs font-black uppercase tracking-widest text-blue-800 mb-1'>Buffalo Weather</h3>"
        f"<p class='text-lg font-bold'>{weather['temp']}°{weather['unit']}</p>"
        f"<p class='text-[10px] text-blue-600 font-medium uppercase'>{weather['forecast']}</p>"
        f"</div>"
    )


# ─────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────

def build_layout(news_html: str, local_html: str, bbc_html: str, weather_html: str) -> str:
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
                {news_html}
            </div>
            <div class="md:col-span-1 border-l border-gray-100 pl-6">
                {weather_html}
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
    weather_data = fetch_weather()
    nyt_data = fetch_nyt_data()
    buffalo_data = fetch_buffalo_news()
    bbc_data = fetch_bbc_middle_east()

    logger.info("Rendering HTML...")
    html = build_layout(
        news_html=render_nyt(nyt_data),
        local_html=render_buffalo(buffalo_data),
        bbc_html=render_bbc(bbc_data),
        weather_html=render_weather(weather_data),
    )

    output_path = "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Done! Output written to {output_path}")
