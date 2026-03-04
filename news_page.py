import requests
from bs4 import BeautifulSoup
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
    """Fetches Buffalo news directly using WIVB's site structure as backup if RSS fails"""
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>Buffalo Local News (WIVB)</h2>"
    try:
        # We'll stick to WIVB's RSS for speed, as it was working well for you
        import feedparser
        feed = feedparser.parse("https://www.wivb.com/news/local-news/buffalo/feed/", agent='Mozilla/5.0')
        for entry in feed.entries[:6]:
            html += f"<div class='mb-4'><a href='{entry.link}' target='_blank' class='text-red-700 font-bold hover:underline'>{entry.title}</a></div>"
        return html
    except: return html

def fetch_middle_east_direct():
    """Scrapes headlines directly from Al Jazeera's Middle East page"""
    html = "<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-orange-200 pb-1 uppercase text-orange-800'>Middle East Headlines (Al Jazeera)</h2>"
    try:
        url = "https://www.aljazeera.com/middle-east/"
        # Pretend to be a real browser to avoid being blocked
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Al Jazeera uses <h3> tags for their main headlines on this page
        headlines = soup.find_all('h3', limit=8)
        
        if not headlines:
            return html + "<p class='text-sm text-gray-400 italic'>Updates currently refreshing on Al Jazeera...</p>"

        for h in headlines:
            link_tag = h.find('a')
            if link_tag:
                title = h.get_text().strip()
                link = "https://www.aljazeera.com" + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
                
                # Try to get the summary (usually in a <p> tag next to the h3)
                summary_tag = h.find_next('p')
                summary_text = summary_tag.get_text().strip()[:160] if summary_tag else "Click to read the full report."
                
                html += f"""
                <div class='mb-6 p-3 bg-orange-50/50 border-l-4 border-orange-600 rounded-r'>
                    <a href='{link}' target='_blank' class='text-gray-900 font-bold hover:underline block leading-tight mb-1'>{title}</a>
                    <p class='text-gray-700 text-xs font-serif leading-snug'>{summary_text}...</p>
                </div>
                """
        return html
    except Exception as e:
        return html + f"<p class='text-xs text-gray-400 italic'>Direct feed update in progress.</p>"

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
                <p class="text-xs font-bold uppercase tracking-widest opacity-80">{now.strftime("%A, %B %d, %Y")}</p>
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
    me_news = fetch_middle_east_direct()
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(nyt, buffalo, me_news, weather))
