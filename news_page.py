import requests
import feedparser
import os
import ssl
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix for SSL certificate issues
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')
SPORTS_KEY = "123" 
REPO_NAME = "MorningHeadlines" 
MY_TEAMS = ["Buffalo Sabres", "Chicago Bulls", "Denver Nuggets", "New York Knicks"]

def fetch_data():
    """Fetches Top Stories for the main page"""
    content = ""
    sections = ["home", "nyregion", "opinion", "food", "style"]
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            titles = {"home": "Global News", "nyregion": "New York Region", "opinion": "Op-Ed & Ideas", "food": "Food & Wine", "style": "Style & Culture"}
            content += format_section(titles.get(section, section), data, "title", "abstract", "url")
        except: continue
    return content

def fetch_epstein_archive():
    """Combines NYT and BBC news regarding the Epstein files"""
    html = "<h2 class='text-3xl font-serif font-black mb-6 border-b-4 border-red-700 pb-2 italic'>THE EPSTEIN INVESTIGATION</h2>"
    
    # 1. Fetch NYT Articles
    try:
        nyt_url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json?q=Jeffrey+Epstein+files&sort=newest&api-key={NYT_KEY}"
        nyt_docs = requests.get(nyt_url).json().get('response', {}).get('docs', [])[:8]
        
        html += "<h3 class='text-xs font-black uppercase tracking-widest text-red-700 mb-4'>NYT Investigations</h3>"
        for doc in nyt_docs:
            title = doc.get('headline', {}).get('main', 'No Title')
            snippet = doc.get('snippet', '')
            link = doc.get('web_url', '#')
            date = doc.get('pub_date', '')[:10]
            html += f"""
            <div class='mb-6 border-l-2 border-red-700 pl-4'>
                <span class='text-[10px] font-bold text-gray-400'>{date}</span>
                <h4 class='text-lg font-bold leading-tight'><a href='{link}' target='_blank' class='hover:underline'>{title}</a></h4>
                <p class='text-gray-600 text-xs mt-1'>{snippet}</p>
            </div>
            """
    except: html += "<p class='text-xs italic'>NYT currently unavailable.</p>"

    # 2. Fetch BBC Articles (Filtered for 'Epstein')
    try:
        html += "<h3 class='text-xs font-black uppercase tracking-widest text-red-700 mb-4 mt-10'>BBC Global Coverage</h3>"
        feed = feedparser.parse("https://feeds.bbci.co.uk/news/world/rss.xml", agent='Mozilla/5.0 MorningBriefingBot/1.0')
        
        found_bbc = False
        for entry in feed.entries:
            if "epstein" in entry.title.lower() or "epstein" in entry.summary.lower():
                found_bbc = True
                html += f"""
                <div class='mb-6 border-l-2 border-black pl-4'>
                    <span class='text-[10px] font-bold text-gray-400 uppercase tracking-widest'>BBC World News</span>
                    <h4 class='text-lg font-bold leading-tight'><a href='{entry.link}' target='_blank' class='hover:underline'>{entry.title}</a></h4>
                    <p class='text-gray-600 text-xs mt-1'>{entry.summary[:150]}...</p>
                </div>
                """
        if not found_bbc:
            html += "<p class='text-xs text-gray-400 italic'>No new Epstein headlines from the BBC in the last 24 hours.</p>"
    except: pass

    return html

def fetch_olympic_dashboard():
    """Live Medals & Schedule for Day 10 - Feb 15, 2026"""
    medals = [
        {"noc": "NOR", "g": 10, "s": 8, "b": 8, "t": 26},
        {"noc": "ITA", "g": 6, "s": 8, "b": 8, "t": 22},
        {"noc": "USA", "g": 4, "s": 7, "b": 6, "t": 17}
    ]
    html = "<h3 class='text-xs font-black uppercase tracking-widest text-red-600 mb-3 mt-4'>Olympic Standings</h3>"
    html += "<div class='bg-red-50 p-2 rounded border border-red-100 mb-4'><table class='w-full text-[10px] text-center'>"
    for m in medals:
        html += f"<tr><td>{m['noc']}</td><td>{m['g']}</td><td>{m['s']}</td><td>{m['b']}</td><td class='font-bold'>{m['t']}</td></tr>"
    html += "</table></div>"
    return html

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
                    display_val = f"{g.get('intHomeScore', '0')} - {g.get('intAwayScore', '0')}" if 'last' in endpoint else g.get('dateEvent', '')
                    html += f"<div class='mb-2 p-2 bg-white border border-gray-100 shadow-sm rounded text-[10px] font-bold flex justify-between'><span>{g['strHomeTeam']}</span><span>{display_val}</span><span>{g['strAwayTeam']}</span></div>"
        except: continue
    return html if found_any else ""

def format_section(header, items, t_key, s_key, l_key):
    html = f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1'>{header}</h2>"
    for item in items:
        html += f"<div class='mb-6'><a href='{item.get(l_key, '#')}' target='_blank' class='text-blue-800 hover:underline font-bold leading-tight'>{item.get(t_key, 'No Title')}</a><p class='text-gray-600 text-sm mt-1'>{item.get(s_key, '')[:150]}...</p></div>"
    return html

def build_layout(content, sidebar, is_archive=False):
    now_eastern = datetime.now(ZoneInfo("America/New_York"))
    menu = f"""
    <div class="flex space-x-4 mb-4 text-xs font-black uppercase">
        <a href="index.html" class="{'text-white border-b-2 border-white' if not is_archive else 'text-red-200 hover:text-white'}">Briefing</a>
        <a href="epstein.html" class="{'text-white border-b-2 border-white' if is_archive else 'text-red-200 hover:text-white'}">Investigation</a>
    </div>
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>{'Epstein Archive' if is_archive else 'The Daily Brief'}</title>
    </head>
    <body class="bg-gray-100 text-gray-900 font-sans leading-tight">
        <div class="max-w-6xl mx-auto bg-white min-h-screen shadow-xl">
            <header class="p-6 {'bg-red-800' if is_archive else 'bg-red-600'} text-white text-center">
                <h1 class="text-4xl md:text-5xl font-serif font-black tracking-tighter uppercase mb-4 italic">{'Investigation Archive' if is_archive else 'The Olympic Brief'}</h1>
                {menu}
            </header>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6">
                <div class="md:col-span-3 border-r border-gray-100 pr-8">{content}</div>
                <div class="md:col-span-1">{sidebar}</div>
            </div>
            <footer class="p-6 bg-gray-900 text-white text-center text-[10px] uppercase font-bold tracking-widest">
                Last Updated: {now_eastern.strftime("%I:%M %p %Z")} • mikespas-coder repository
            </footer>
        </div>
    </body>
    </html>
    """

def build_page():
    # Fetch Data
    main_news = fetch_data()
    archive_news = fetch_epstein_archive()
    
    # Get sidebar data
    olympics = fetch_olympic_dashboard()
    yesterday = get_games("eventslast.php", "Last Night")
    today = get_games("eventsnext.php", "Upcoming")
    sidebar = olympics + yesterday + today

    # GENERATE FILE 1: index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(main_news, sidebar, is_archive=False))
        f.flush() # Forces the robot to finish writing
        
    # GENERATE FILE 2: epstein.html
    with open("epstein.html", "w", encoding="utf-8") as f:
        f.write(build_layout(archive_news, sidebar, is_archive=True))
        f.flush() # Forces the robot to finish writing

    print("Success: Both index.html and epstein.html have been generated.")
