import requests
import feedparser
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')
SPORTS_KEY = "123" # Updated to the current working key

# Your specific teams to highlight
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

def get_games(endpoint, title_label):
    """General function to fetch games (last or next) for your teams"""
    # 4387 = NBA, 4380 = NHL
    leagues = [("4387", "NBA"), ("4380", "NHL")]
    html = f"<h3 class='text-xs font-black uppercase tracking-widest text-blue-600 mb-3 mt-6'>{title_label}</h3>"
    found_any = False
    
    for league_id, league_name in leagues:
        try:
            url = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_KEY}/{endpoint}?id={league_id}"
            games = requests.get(url).json().get('results' if 'last' in endpoint else 'events', [])
            
            for g in games:
                if g['strHomeTeam'] in MY_TEAMS or g['strAwayTeam'] in MY_TEAMS:
                    found_any = True
                    # If it's a past game, show scores. If next, show time.
                    score_or_time = f"{g.get('intHomeScore', '0')} - {g.get('intAwayScore', '0')}" if 'last' in endpoint else g.get('strTime', 'TBD')
                    
                    html += f"""
                    <div class='mb-3 p-3 bg-white border border-gray-200 shadow-sm rounded-lg'>
                        <div class='flex justify-between text-xs font-bold'>
                            <span>{g['strHomeTeam']}</span>
                            <span class='text-gray-400'>vs</span>
                            <span>{g['strAwayTeam']}</span>
                        </div>
                        <div class='text-center mt-2 font-black text-lg'>{score_or_time}</div>
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
    
    # New Sports Logic: Get Recent Scores AND Upcoming Schedule
    yesterday_html = get_games("eventslast.php", "Yesterday's Results")
    today_html = get_games("eventsnext.php", "Upcoming Games")
    sports_sidebar = yesterday_html + today_html
    
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
                    <h2 class="text-lg font-black border-b-4 border-black mb-4 uppercase">Scoreboard</h2>
                    {sports_sidebar if sports_sidebar else "<p class='text-xs text-gray-400 italic'>No recent or upcoming games for your teams.</p>"}
                    
                    <div class="mt-10 p-4 bg-gray-900 text-white rounded-lg">
                        <p class="text-[10px]">Updated: {datetime.now().strftime("%H:%M:%S")} UTC</p>
                        <p class="text-[10px] mt-1 text-green-400">● Live Connection</p>
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
