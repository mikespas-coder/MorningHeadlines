import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
SPORTS_KEY = "123" 
MY_TEAMS = ["Buffalo Sabres", "Chicago Bulls", "Denver Nuggets", "New York Knicks"]

def fetch_data():
    sections = ["home", "nyregion", "opinion", "food", "style"]
    content = ""
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            titles = {"home": "Global News", "nyregion": "NY Region", "opinion": "Op-Ed", "food": "Food & Wine", "style": "Style & Culture"}
            content += f"<h2 class='text-xl font-serif font-bold mt-8 mb-4 border-b border-gray-200 pb-1 uppercase'>{titles.get(section, section)}</h2>"
            for item in data:
                content += f"<div class='mb-6'><a href='{item['url']}' target='_blank' class='text-blue-800 font-bold hover:underline'>{item['title']}</a><p class='text-gray-600 text-sm mt-1'>{item.get('abstract', '')[:140]}...</p></div>"
        except: continue
    return content

def fetch_epstein():
    try:
        url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json?q=Jeffrey+Epstein+files&sort=newest&api-key={NYT_KEY}"
        docs = requests.get(url).json().get('response', {}).get('docs', [])[:12]
        html = "<h2 class='text-3xl font-serif font-black mb-8 border-b-4 border-red-700 pb-2 italic uppercase'>Investigation Archive</h2>"
        for doc in docs:
            html += f"<div class='mb-8 border-l-4 border-red-700 pl-4 bg-gray-50 p-4 rounded-r'><span class='text-[10px] font-bold text-gray-400'>{doc.get('pub_date', '')[:10]}</span><h4 class='text-lg font-bold mt-1'><a href='{doc['web_url']}' target='_blank' class='hover:underline'>{doc['headline']['main']}</a></h4><p class='text-sm text-gray-600 mt-2'>{doc.get('snippet', '')}</p></div>"
        return html
    except: return "Archive temporarily unavailable."

def fetch_sidebar():
    # Olympics are over, so we move straight to NBA/NHL scores
    html = "<h3 class='text-xs font-black uppercase tracking-widest text-blue-600 mb-2 mt-4'>NBA/NHL Scores</h3>"
    for lid in ["4387", "4380"]:
        try:
            res = requests.get(f"https://www.thesportsdb.com/api/v1/json/{SPORTS_KEY}/eventslast.php?id={lid}").json()
            games = res.get('results', [])
            for g in games:
                if g['strHomeTeam'] in MY_TEAMS or g['strAwayTeam'] in MY_TEAMS:
                    html += f"<div class='mb-1 p-2 bg-white border border-gray-100 text-[10px] flex justify-between'><span>{g['strHomeTeam']}</span><span class='font-bold'>{g['intHomeScore']}-{g['intAwayScore']}</span></div>"
        except: continue
    return html

def build_layout(content, sidebar, is_archive=False):
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
                <p class="text-xs font-bold uppercase tracking-widest opacity-80 mb-6">{date_str}</p>
                <nav class="flex justify-center space-x-8 text-xs font-black uppercase tracking-widest">
                    <a href="./" class="pb-1 {'border-b-2 border-white' if not is_archive else 'opacity-60 hover:opacity-100'}">Main Briefing</a>
                    <a href="./epstein.html" class="pb-1 {'border-b-2 border-white' if is_archive else 'opacity-60 hover:opacity-100'}">Investigation Archive</a>
                </nav>
            </header>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 p-6 md:p-12">
                <div class="md:col-span-3">{content}</div>
                <div class="md:col-span-1 border-l border-gray-100 pl-6">{sidebar}</div>
            </div>
            <footer class="p-6 bg-gray-900 text-white text-center text-[10px] uppercase font-bold">Updated: {now.strftime("%I:%M %p %Z")}</footer>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    sidebar = fetch_sidebar()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(fetch_data(), sidebar, False))
    with open("epstein.html", "w", encoding="utf-8") as f:
        f.write(build_layout(fetch_epstein(), sidebar, True))
    print("Success: Generated Post-Olympic Dashboard.")
