import requests
import feedparser
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')

def fetch_nyt_data():
    sections = ["home", "nyregion", "opinion"]
    content = ""
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            response = requests.get(url, timeout=5)
            data = response.json().get('results', [])[:3]
            titles = {"home": "Global News", "nyregion": "New York State", "opinion": "Op-Ed"}
            content += f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>{titles.get(section, section)}</h2>"
            for item in data:
                content += f"<div class='mb-6'><a href='{item['url']}' target='_blank' class='text-blue-800 font-bold hover:underline'>{item['title']}</a><p class='text-gray-600 text-sm mt-1'>{item.get('abstract', '')[:140]}...</p></div>"
        except: continue
    return content

def fetch_buffalo_news():
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>Buffalo Local News (WIVB)</h2>"
    try:
        feed_url = "https://www.wivb.com/news/local-news/buffalo/feed/"
        feed = feedparser.parse(feed_url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15')
        if not feed.entries:
            return html + "<p class='text-sm text-gray-400 italic font-serif'>Refreshing local updates...</p>"
        for entry in feed.entries[:5]:
            html += f"<div class='mb-6'><a href='{entry.link}' target='_blank' class='text-red-700 font-bold hover:underline'>{entry.title}</a></div>"
        return html
    except: return html

def fetch_middle_east_conflict():
    """Specific filter for Middle East Conflict news via Al Jazeera"""
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-orange-200 pb-1 uppercase text-orange-800'>Conflict Update: Middle East</h2>"
    
    # War-related keywords to filter out sports/fluff
    war_keywords = ['war', 'strike', 'missile', 'gaza', 'israel', 'lebanon', 'hezbollah', 'iran', 'bomb', 'blast', 'houthi', 'military', 'death', 'killed', 'idf', 'hamas', 'red sea', 'attack']
    
    try:
        # Targeting the Middle East specific regional feed
        feed_url = "https://www.aljazeera.com/xml/rss/middle-east.xml"
        feed = feedparser.parse(feed_url, agent='Mozilla/5.0')
        
        found_stories = 0
        for entry in feed.entries:
            title_lower = entry.title.lower()
            # Only include the story if it contains one of our keywords
            if any(keyword in title_lower for keyword in war_keywords) and found_stories < 6:
                summary = entry.get('summary', entry.get('description', ''))
                clean_summary = summary.split('<')[0].strip()[:180]
                html += f"""
                <div class='mb-6 p-3 bg-orange-50/50 border-l-4 border-orange-600 rounded-r'>
                    <a href='{entry.link}' target='_blank' class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>{entry.title}</a>
                    <p class='text-gray-700 text-xs font-serif leading-snug'>{clean_summary}...</p>
                </div>
                """
                found_stories += 1
        
        if found_stories == 0:
            return html + "<p class='text-xs text-gray-400 italic'>No conflict-specific updates in the current hour.</p>"
        return html
    except:
        return ""

def fetch_weather():
    try:
        res = requests.get("https://api.weather.gov/gridpoints/BUF/78,43/forecast", timeout=5).json()
        today = res['properties']['periods'][0]
        return f"<div class='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'><h3 class='text-xs font-black uppercase tracking-widest text-blue-800 mb-1'>Buffalo Weather</h3><p class='text-lg font-bold'>{today['temperature']}°{today['temperatureUnit']}</p><p class='text-[10px] text-blue-600 font-medium uppercase'>{today['shortForecast']}</p></div>"
    except: return ""

def build_layout(news_content, local_content, middle_east_content, weather_sidebar):
    now = datetime.now(ZoneInfo("America/New_York"))
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-100 text-gray-900 font-sans leading-snug">
        <div class="max-w-6xl mx-auto bg-white min-h-screen shadow-2xl">
            <header class="p-8 bg-black text-white text-center">
                <h1 class="text-5xl font-serif font-black italic tracking-tighter uppercase mb-2">The Daily Brief</h1>
                <p class="text-xs font-bold uppercase tracking-widest opacity-80">{now.strftime("%A, %B % d, %Y")}</p>
            </header>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6 md:p-12">
                <div class="md:col-span-3">
                    {local_content}
                    {middle_east_content}
                    {news_content}
                </div>
                <div class="md:col-span-1 border-l border-gray-100 pl-6">
                    {weather_sidebar}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    weather = fetch_weather()
    nyt = fetch_nyt_data()
    buffalo = fetch_buffalo_news()
    me_conflict = fetch_middle_east_conflict()
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(nyt, buffalo, me_conflict, weather))
