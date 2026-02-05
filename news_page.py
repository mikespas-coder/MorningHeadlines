import requests
import feedparser
import os
from datetime import datetime

# --- CONFIGURATION ---
NYT_KEY = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')

def fetch_data():
    content = ""
    # 1. Fetch NYT Sections
    sections = ["home", "opinion", "food", "style"]
    
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            
            titles = {
                "home": "NYT: Global News",
                "opinion": "NYT: Op-Ed & Ideas",
                "food": "NYT: Food & Wine",
                "style": "NYT: Style & Culture"
            }
            display_title = titles.get(section, f"NYT: {section.capitalize()}")
            content += format_section(display_title, data, "title", "abstract", "url")
        except Exception as e:
            print(f"Error fetching NYT {section}: {e}")

    # 2. Fetch BBC (RSS)
    try:
        bbc = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml").entries[:3]
        content += format_section("BBC World Report", bbc, "title", "summary", "link")
    except Exception as e:
        print(f"Error fetching BBC: {e}")

    # 3. Fetch Market News (Finnhub)
    try:
        stocks_url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_KEY}"
        stocks = requests.get(stocks_url).json()[:3]
        content += format_section("Market Pulse", stocks, "headline", "summary", "url")
    except Exception as e:
        print(f"Error fetching Stocks: {e}")

    return content

def format_section(header, items, t_key, s_key, l_key):
    html = f"<h2 class='text-2xl font-bold mt-8 mb-4 border-b-2 border-gray-200 pb-2 text-gray-800'>{header}</h2>"
    html += "<div class='grid gap-4'>"
    for item in items:
        title = item.get(t_key, "No Title")
        summary = item.get(s_key, "No description available.")[:200]
        link = item.get(l_key, "#")
        html += f"""
        <div class='p-4 bg-white shadow-sm rounded-lg border border-gray-100 hover:shadow-md transition-shadow'>
            <a href='{link}' target='_blank' class='text-blue-700 hover:underline font-semibold text-lg'>{title}</a>
            <p class='text-gray-600 text-sm mt-2'>{summary}...</p>
        </div>
        """
    html += "</div>"
    return html

def build_page():
    news_html = fetch_data()
    date_str = datetime.now().strftime("%A, %B %d, %Y")

    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>My Morning Briefing</title>
    </head>
    <body class="bg-gray-50 text-gray-900 font-sans p-4 md:p-10">
        <div class="max-w-3xl mx-auto">
            <header class="mb-10 text-center border-b-4 border-black pb-4">
                <h1 class="text-5xl font-serif font-black text-gray-900">The Daily Brief</h1>
                <p class="text-gray-500 uppercase tracking-widest text-sm mt-3 font-bold">{date_str}</p>
                <a href="https://github.com/mikespas-coder/Morning-News-/actions/workflows/morning_brief.yml" 
                   target="_blank"
                   class="inline-block mt-4 px-4 py-1 border border-gray-800 text-xs font-bold uppercase hover:bg-black hover:text-white transition">
                   Request Fresh Update
                </a>
            </header>
            {news_html}
            <footer class="mt-16 py-8 text-center text-gray-400 text-xs border-t border-gray-200">
                Last Updated: {datetime.now().strftime("%H:%M:%S")} UTC • Generated via GitHub Actions
            </footer>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w") as f:
        f.write(full_html)
    print("Page built successfully!")

if __name__ == "__main__":
    build_page()
