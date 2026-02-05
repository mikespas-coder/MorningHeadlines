import requests
import feedparser
import os
import ssl
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix for SSL certificate issues on some servers
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')
SPORTS_KEY = "123" 
REPO_NAME = "MorningHeadlines" 
MY_TEAMS = ["Buffalo Sabres", "Chicago Bulls", "Denver Nuggets", "New York Knicks"]

def fetch_data():
    content = ""
    sections = ["home", "opinion", "food", "style"]
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            titles = {"home": "Global News", "opinion": "Op-Ed & Ideas", "food": "Food & Wine", "style": "Style & Culture"}
            content += format_section(titles.get(section, section), data, "title", "abstract", "url")
        except: continue
    return content

def fetch_olympics():
    """Fetches real-time headlines using the more reliable BBC Olympic feed"""
    try:
        # BBC is much more 'robot-friendly' than the official Olympic site
        url = "https://feeds.bbci.co.uk/sport/olympics/rss.xml"
        
        # We add a 'User-Agent' so the website knows we are a helpful news bot
        feed = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) MorningBriefingBot/1.0')
        
        if not feed.entries:
            return ""

        html = "<h3 class='text-xs font-black uppercase tracking-widest text-red-600 mb-3 mt-6'>Milan Cortina 2026</h3>"
        for entry in feed.entries[:4]:
            html += f"""
            <div class='mb-3 p-3 bg-red-50 border border-red-100 shadow-sm rounded-lg hover:bg-red-100 transition-colors'>
                <a href='{entry.link}' target='_blank' class='text-[11px] font-bold text-red-900 hover:underline leading-tight block'>
                    {entry.title}
                </a>
                <p class='text-[9px] text-red-700 mt-1 uppercase font-semibold'>Latest from BBC Sport</p>
            </div>
            """
        return html
    except Exception as e:
        print(f"Olympic Feed Error: {e}")
        return ""

def get_games(endpoint, title_label):
    leagues = [("4387", "NBA"), ("4380", "NHL")]
    html = f"<h3 class='text-xs font-black uppercase tracking-widest text-blue-600 mb-3 mt-6'>{title_label}</h3>"
    found_any = False
    eastern_tz = ZoneInfo("America/New_York")
    for league_id, league_name in leagues:
        try:
            url = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_KEY}/{endpoint}?id={league_id}"
            games = requests.get(url).json().get('results' if 'last' in endpoint else 'events', [])
            for g in games:
                if g['strHomeTeam'] in MY_TEAMS or g['strAwayTeam'] in MY_TEAMS:
                    found_any = True
                    display_time = ""
                    if 'last' in endpoint:
                        display_time = f"{g.get('intHomeScore', '0')} - {g.get('intAwayScore', '0')}"
                    else:
                        raw_date, raw_time = g.get('dateEvent', ''), g.get('strTime', '')
                        if raw_date and raw_time:
                            try:
                                utc_dt = datetime.strptime(f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
                                display_time = utc_dt.astimezone(eastern_tz).strftime("%I:%M %p %Z")
                            except: display_time = raw_time
                        else: display_time = "TBD"
                    html += f"""
                    <div class='mb-3 p-3 bg-white border border-gray-200 shadow-sm rounded-lg'>
                        <div class='flex justify-between text-xs font-bold'>
                            <span>{g['strHomeTeam']}</span>
                            <span class='text-gray-400'>vs</span>
                            <span>{g['strAwayTeam']}</span>
                        </div>
                        <div class='text-center mt-2 font-black text-lg'>{display_time}</div>
                        <div class='text-[10px] text-gray-400 text-center mt-1 uppercase'>{g.get('dateEvent', '')}</div>
                    </div>
                    """
        except: continue
    return html if found_any else ""

def format_section(header, items, t_key, s_key, l_key):
    html = f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1'>{header}</h2>"
    for item in items:
        html += f"""
        <div class='mb-6'>
            <a href='{item.get(l_key, "#")}' target='_blank' class='text-blue-800 hover:underline font-bold leading-tight'>{item.get(t_key, "No Title")}</a>
            <p class='text-gray-600 text-sm mt-1 leading-snug'>{item.get(s_key, "")[:150]}...</p>
        </div>
        """
    return html

def build_page():
    news_html = fetch_data()
    olympics_html = fetch_olympics()
    yesterday_html = get_games("eventslast.php", "Recent Results")
    today_html = get_games("eventsnext.php", "Upcoming Schedule")
    sports_sidebar = olympics_html + yesterday_html + today_html
    now_eastern = datetime.now(ZoneInfo("America/New_York"))
    date_str = now_eastern.strftime("%A, %B %d, %Y")

    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>The Olympic Brief</title>
    </head>
    <body class="bg-gray-100 text-gray-900 font-sans">
        <div class="max-w-6xl mx-auto bg-white min-h-screen shadow-xl">
            <header class="p-6 border-b-8 border-black text-center bg-red-600 text-white">
                <h1 class="text-6xl font-serif font-black tracking-tighter italic uppercase">THE OLYMPIC BRIEF</h1>
                <div class="flex justify-between items-center mt-4 text-xs font-bold uppercase tracking-widest border-t border-white pt-2">
                    <span>Mikespas Edition</span>
                    <span>{date_str}</span>
                    <a href="https://github.com/mikespas-coder/{REPO_NAME}/actions" class="hover:underline text-white">Refresh</a>
                </div>
            </header>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6">
                <div class="md:col-span-3 border-r border-gray-100 pr-8">
                    {news_html}
                </div>
                <div class="md:col-span-1">
                    <h2 class="text-lg font-black border-b-4 border-black mb-4 uppercase tracking-tighter">Scoreboard</h2>
                    {sports_sidebar if sports_sidebar else "<p class='text-xs text-gray-400 italic'>No recent or upcoming updates.</p>"}
                    <div class="mt-10 p-4 bg-gray-900 text-white rounded-lg">
                        <p class="text-[10px]">Updated: {now_eastern.strftime("%I:%M %p %Z")}</p>
                        <p class="text-[10px] mt-1 text-green-400 font-bold">● Live Connection</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w") as f:
        f.write(full_html)

if __name__ == "__main__":
    build_page()
