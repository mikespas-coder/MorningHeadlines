import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
SPORTS_KEY = "123" 
REPO_NAME = "MorningHeadlines" 
MY_TEAMS = ["Buffalo Sabres", "Chicago Bulls", "Denver Nuggets", "New York Knicks"]

def fetch_data():
    sections = ["home", "nyregion", "opinion"]
    content = ""
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            content += f"<h2 class='text-xl font-bold mt-6 border-b pb-1 uppercase'>{section}</h2>"
            for item in data:
                content += f"<div class='mb-4'><a href='{item['url']}' class='text-blue-700 font-bold'>{item['title']}</a><p class='text-sm text-gray-600'>{item['abstract'][:120]}...</p></div>"
        except: continue
    return content

def fetch_epstein():
    try:
        url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json?q=Jeffrey+Epstein+files&sort=newest&api-key={NYT_KEY}"
        docs = requests.get(url).json().get('response', {}).get('docs', [])[:10]
        html = "<h2 class='text-2xl font-black mb-6 text-red-700'>EPSTEIN INVESTIGATION ARCHIVE</h2>"
        for doc in docs:
            html += f"<div class='mb-6 border-l-4 border-red-700 pl-4'><a href='{doc['web_url']}' class='font-bold text-lg'>{doc['headline']['main']}</a><p class='text-xs text-gray-500 mt-1'>{doc['snippet']}</p></div>"
        return html
    except: return "Archive temporarily unavailable."

def build_layout(content, is_archive=False):
    now = datetime.now(ZoneInfo("America/New_York"))
    return f"""
    <!DOCTYPE html>
    <html>
    <head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-100 p-4 md:p-10">
        <div class="max-w-4xl mx-auto bg-white shadow-lg rounded-xl overflow-hidden">
            <header class="p-8 bg-red-600 text-white text-center">
                <h1 class="text-4xl font-black italic">THE MORNING BRIEF</h1>
                <nav class="mt-4 flex justify-center space-x-4 text-xs font-bold uppercase">
                    <a href="index.html" class="{'underline' if not is_archive else 'opacity-50'}">Daily News</a>
                    <a href="epstein.html" class="{'underline' if is_archive else 'opacity-50'}">Epstein Files</a>
                </nav>
            </header>
            <div class="p-8">{content}</div>
            <footer class="p-4 bg-gray-900 text-white text-center text-[10px]">Updated: {now.strftime("%I:%M %p EST")}</footer>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Create Main Page
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_layout(fetch_data(), False))
    
    # Create Archive Page
    with open("epstein.html", "w", encoding="utf-8") as f:
        f.write(build_layout(fetch_epstein(), True))
    
    print("!!! DEPLOYMENT CHECK: index.html and epstein.html created successfully !!!")
