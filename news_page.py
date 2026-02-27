import requests
import feedparser
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
SPORTS_KEY = "123" 
MY_TEAMS = ["Buffalo Sabres", "Chicago Bulls", "Denver Nuggets", "New York Knicks"]

def fetch_nyt_data():
    """Fetches Top Stories from NYT"""
    sections = ["home", "nyregion", "opinion"]
    content = ""
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            titles = {"home": "Global News", "nyregion": "New York State", "opinion": "Op-Ed"}
            content += f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>{titles.get(section, section)}</h2>"
            for item in data:
                content += f"<div class='mb-6'><a href='{item['url']}' target='_blank' class='text-blue-800 font-bold hover:underline'>{item['title']}</a><p class='text-gray-600 text-sm mt-1'>{item.get('abstract', '')[:140]}...</p></div>"
        except: continue
    return content

def fetch_buffalo_news():
    """Fetches local Buffalo news from WBFO (BTPM)"""
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>Buffalo Local News (WBFO)</h2>"
    try:
        # Fetching from WBFO/NPR Buffalo feed
        feed = feedparser.parse("https://www.wbfo.org/index.rss")
        for entry in feed.entries[:5]: # Top 5 local stories
            html += f"""
            <div class='mb-6'>
                <a href='{entry.link}' target='_blank' class='text-red-700 font-bold hover:underline'>{entry.title}</a>
                <p class='text-gray-600 text-sm mt-1'>{entry.summary[:150]}...</p>
            </div>
            """
        return html
    except:
        return "<p class='text-sm italic text-gray-400'>Buffalo news temporarily unavailable.</p>"

def fetch_sidebar():
    """Sports Scoreboard"""
    html = "<h3 class='text-xs font-black uppercase tracking-widest text-blue-600 mb-2 mt-4'>NBA/NHL Scores</h3>"
    for lid in ["4387", "4380"]: # NBA and NHL
        try:
            res = requests.get(f"https://www.thesportsdb.com/api/v1/json/{SPORTS_KEY}/eventslast.php?id={lid}").json()
            games = res.get('results', [])
            for g in games:
                if g['strHomeTeam'] in MY_TEAMS or g['strAwayTeam'] in MY_TEAMS:
                    html += f"<div class='mb-1 p-2 bg-white border border-gray-100 text-[10px] flex justify-between'><span>{g['strHomeTeam']}</span><span class='font-bold'>{g['intHomeScore']}-{g['intAwayScore']}</span></div>"
        except: continue
    return html

def build_layout(news_content, local_content, sidebar):
    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%A, %B %d, %Y")
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-100 text-gray-900 font-sans leading-snug">
        <div class="max-w-6xl mx-auto bg-white min-h-screen shadow-2xl">
            <header class="p-8 bg-black text-white text-center">
                <h1 class="text-5xl font-serif font-black italic tracking-tighter uppercase mb-2">The Daily Brief</h1>
                <p class="text-xs font-bold uppercase tracking-widest opacity-80">{date_str}</p>
            </header>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6 md:p-12">
                <div class="md:col-span-3">
                    {local_content}
                    {news_content}
                </div>
                <div class="md:col-span-1 border-l border-gray-100 pl-6">
                    {sidebar}
                </div>
            </div>
            <footer class="p-6 bg-gray-900 text-white text-center text-[10px] uppercase font-bold">Updated: {now.strftime("%I:%M %p %Z")}</footer>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    sidebar = fetch_sidebar()
    nyt_news = fetch_nyt_data()
    buffalo_news = fetch_buffalo_news()
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(nyt_news, buffalo_news, sidebar))
