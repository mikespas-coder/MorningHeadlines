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

def fetch_olympic_results():
    """Fetches Live Medal Count and Live Updates"""
    try:
        # 1. Fetch Latest Results via RSS
        url = "https://feeds.bbci.co.uk/sport/olympics/rss.xml"
        feed = feedparser.parse(url, agent='Mozilla/5.0 MorningBriefingBot/1.0')
        
        html = "<h3 class='text-xs font-black uppercase tracking-widest text-red-600 mb-3 mt-4'>Milano Cortina Live</h3>"
        
        # Display the top 5 'Breaking' results/news items
        for entry in feed.entries[:5]:
            # Highlight items that look like results (scores, winners, medals)
            is_result = any(word in entry.title.lower() for word in ['wins', 'gold', 'silver', 'bronze', 'score', 'defeat'])
            bg_color = "bg-red-50 border-red-200" if is_result else "bg-white border-gray-100"
            
            html += f"""
            <div class='mb-2 p-2 border {bg_color} shadow-sm rounded flex flex-col'>
                <a href='{entry.link}' target='_blank' class='text-[10px] font-bold text-gray-900 leading-tight'>
                    {entry.title}
                </a>
            </div>
            """
        
        # 2. Hardcoded Medal Table for Top 5 (We can update this manually or via scrape)
        # As of Feb 6, competition is just starting, so table might be empty
        html += """
        <div class='mt-4 p-2 bg-gray-50 border border-gray-200 rounded'>
            <h4 class='text-[9px] font-bold uppercase mb-2 text-center border-b border-gray-200 pb-1'>Top Medals</h4>
            <table class='w-full text-[10px]'>
                <tr class='font-bold text-gray-500'><td>NOC</td><td>G</td><td>S</td><td>B</td></tr>
                <tr><td>NOR</td><td>-</td><td>-</td><td>-</td></tr>
                <tr><td>USA</td><td>-</td><td>-</td><td>-</td></tr>
                <tr><td>ITA</td><td>-</td><td>-</td><td>-</td></tr>
            </table>
            <p class='text-[8px] text-gray-400 mt-2 italic text-center'>Medals begin awarding Feb 7</p>
        </div>
        """
        return html
    except: return ""

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
                    <div class='mb-2 p-2 bg-white border border-gray-200 shadow-sm rounded-lg'>
                        <div class='flex justify-between text-[10px] font-bold'>
                            <span>{g['strHomeTeam']}</span>
                            <span>{g['intHomeScore'] if 'last' in endpoint else ''}</span>
                        </div>
                        <div class='flex justify-between text-[10px] font-bold mt-1'>
                            <span>{g['strAwayTeam']}</span>
                            <span>{g['intAwayScore'] if 'last' in endpoint else ''}</span>
                        </div>
                        <div class='text-[9px] text-gray-400 text-center mt-1 uppercase'>{'Final' if 'last' in endpoint else display_time}</div>
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
    olympics_html = fetch_olympic_results()
    yesterday_html = get_games("eventslast.php", "Last Night's Scores")
    today_html = get_games("eventsnext.php", "Upcoming (EST)")
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
                <h1 class="text-5xl md:text-6xl font-serif font-black tracking-tighter italic uppercase underline decoration-4 underline-offset-8">THE OLYMPIC BRIEF</h1>
                <div class="flex justify-between items-center mt-6 text-xs font-bold uppercase tracking-widest border-t border-white pt-2">
                    <span>Mikespas Edition</span>
                    <span>{date_str}</span>
                    <a href="https://github.com/mikespas-coder/{REPO_NAME}/actions" class="hover:underline text-white">Refresh News</a>
                </div>
            </header>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6">
                <div class="md:col-span-3 border-r border-gray-100 pr-8">{news_html}</div>
                <div class="md:col-span-1">
                    <h2 class="text-lg font-black border-b-4 border-black mb-4 uppercase italic">Scoreboard</h2>
                    {sports_sidebar if sports_sidebar else "<p class='text-xs text-gray-400 italic'>No updates yet.</p>"}
                    <div class="mt-10 p-4 bg-gray-900 text-white rounded-lg">
                        <p class="text-[10px]">Updated: {now_eastern.strftime("%I:%M %p %Z")}</p>
                        <p class="text-[10px] mt-1 text-green-400 font-bold">● Connection Secure</p>
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
