import requests
import feedparser
import os
from datetime import datetime

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')
SPORTS_KEY = "123" # Public test key for TheSportsDB

# Your specific teams to highlight - names verified for TheSportsDB
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

def fetch_sports():
    """Fetches scores and filters for your specific teams"""
    # 4387 = NBA, 4380 = NHL
    leagues = [("4387", "NBA"), ("4380", "NHL")]
    html = "<div class='space-y-6'>"
    
    for league_id, league_name in leagues:
        try:
            url = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_KEY}/eventslast.php?id={league_id}"
            games = requests.get(url).json().get('results', [])
            
            league_html = f"<h3 class='text-sm font-black uppercase tracking-tighter text-gray-400 mb-2'>{league_name} Tracker</h3>"
            found_game = False
            
            for g in games:
                if g['strHomeTeam'] in MY_TEAMS or g['strAwayTeam'] in MY_TEAMS:
                    found_game = True
                    # Highlight the score box if it's one of your teams
                    league_html += f"""
                    <div class='mb-2 p-3 bg-white border-l-4 border-blue-600 shadow-sm rounded-r-lg'>
                        <div class='flex justify-between text-xs font-bold'>
                            <span>{g['strHomeTeam']}</span>
                            <span>{g['intHomeScore']}</span>
                        </div>
                        <div class='flex justify-between text-xs font-bold mt-1'>
                            <span>{g['strAwayTeam']}</span>
                            <span>{g['intAwayScore']}</span>
                        </div>
                        <div class='text-[10px] text-gray-400 mt-2 uppercase'>{g['strStatus']}</div>
                    </div>
                    """
            if not found_game:
                league_html += "<p class='text-xs text-gray-400 italic'>No recent games for your teams.</p>"
            html += league_html
        except: continue
    return html + "</div>"

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
    sports_sidebar = fetch_sports()
    date_str = datetime.now().strftime("%A, %B %d, %Y")

    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>The Daily Brief</title>
    </head>
    <body class="bg-gray-100 text-gray-900 font-sans">
        <div class="max-w-6xl mx-auto bg-white min-h-screen shadow-xl">
            <header class="p-6 border-b-8 border-black text-center">
                <h1 class="text-6xl font-serif font-black tracking-tighter">THE DAILY BRIEF</h1>
                <div class="flex justify-between items-center mt-4 text-xs font-bold uppercase tracking-widest border-t border-black pt-2">
                    <span>Mikespas Edition</span>
                    <span>{date_str}</span>
                    <a href="https://github.com/mikespas-coder/morning-briefing/actions" class="hover:underline text-blue-600">Refresh</a>
                </div>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6">
                <div class="md:col-span-3 border-r border-gray-100 pr-8">
                    {news_html}
                </div>

                <div class="md:col-span-1">
                    <h2 class="text-lg font-black border-b-4 border-black mb-4">SCOREBOARD</h2>
                    {sports_sidebar}
                    
                    <div class="mt-10 p-4 bg-gray-900 text-white rounded-lg">
                        <h3 class="text-xs font-bold uppercase tracking-widest mb-2 text-gray-400">Status</h3>
                        <p class="text-[10px]">Updated: {datetime.now().strftime("%H:%M:%S")} UTC</p>
                        <p class="text-[10px] mt-1 text-green-400">● Systems Active</p>
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
