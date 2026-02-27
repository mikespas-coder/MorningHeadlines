import requests
import feedparser
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')

def fetch_nyt_data():
    sections = ["home", "nyregion", "opinion", "food", "style"]
    content = ""
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            response = requests.get(url, timeout=5)
            data = response.json().get('results', [])[:3]
            titles = {
                "home": "Global News", 
                "nyregion": "New York State", 
                "opinion": "Op-Ed",
                "food": "Food & Wine",
                "style": "Style & Culture"
            }
            content += f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>{titles.get(section, section)}</h2>"
            for item in data:
                content += f"<div class='mb-6'><a href='{item['url']}' target='_blank' class='text-blue-800 font-bold hover:underline'>{item['title']}</a><p class='text-gray-600 text-sm mt-1'>{item.get('abstract', '')[:140]}...</p></div>"
        except: continue
    return content

def fetch_buffalo_news():
    """Fetches local Buffalo news via WIVB (News 4) - more stable for automation"""
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>Buffalo Local News (WIVB)</h2>"
    try:
        # WIVB News 4 Buffalo Feed
        feed_url = "https://www.wivb.com/news/local-news/buffalo/feed/"
        # Using a Safari/Mac User-Agent to bypass bot filters
        feed = feedparser.parse(feed_url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15')
        
        if not feed.entries:
            return html + "<p class='text-sm text-gray-400 italic font-serif'>Buffalo updates are currently being refreshed...</p>"
            
        for entry in feed.entries[:8]:
            summary = entry.get('summary', entry.get('description', 'Click to read full local coverage.'))
            clean_summary = summary.split('<')[0].strip()
            html += f"""
            <div class='mb-6'>
                <a href='{entry.link}' target='_blank' class='text-red-700 font-bold hover:underline'>{entry.title}</a>
                <p class='text-gray-600 text-sm mt-1 leading-snug font-serif'>{clean_summary[:180]}...</p>
            </div>
            """
        return html
    except:
        return html + "<p class='text-sm italic text-gray-400'>Local news feed currently updating.</p>"

def fetch_weather():
    try:
        res = requests.get("https://api.weather.gov/gridpoints/BUF/78,43/forecast", timeout=5).json()
        today = res['properties']['periods'][0]
        return f"""
        <div class='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
            <h3 class='text-xs font-black uppercase tracking-widest text-blue-800 mb-1'>Buffalo Weather</h3>
            <p class='text-lg font-bold'>{today['temperature']}°{today['temperatureUnit']}</p>
            <p class='text-[10px] text-blue-600 font-medium uppercase'>{today['shortForecast']}</p>
        </div>
        """
    except: return ""

def build_layout(news_content, local_content, weather_sidebar):
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
                    {weather_sidebar}
                </div>
            </div>
            <footer class="p-6 bg-gray-900 text-white text-center text-[10px] uppercase font-bold tracking-widest">
                Updated: {now.strftime("%I:%M %p %Z")} • Buffalo, NY
            </footer>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    weather = fetch_weather()
    nyt_news = fetch_nyt_data()
    buffalo_news = fetch_buffalo_news()
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(nyt_news, buffalo_news, weather))
