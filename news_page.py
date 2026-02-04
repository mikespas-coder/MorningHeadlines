import requests
import feedparser
import os
from datetime import datetime

# --- CONFIGURATION ---
# These pull from the "Secrets" you set up in GitHub
NYT_KEY = os.environ.get('NYT_KEY')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY')

def fetch_data():
    content = ""

    # 1. Fetch NYT Top Stories & Op-Eds
    # 'home' is the front page, 'opinion' is the Op-Ed section
    sections = ["home", "opinion"]
    for section in sections:
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={NYT_KEY}"
            data = requests.get(url).json().get('results', [])[:3]
            title = "NYT: Global News" if section == "home" else "NYT: Op-Ed & Ideas"
            content += format_section(title, data, "title", "abstract", "url")
        except Exception as e:
            print(f"Error fetching NYT {section}: {e}")

    # 2. Fetch BBC (RSS - No key needed)
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
    """Turns raw data into HTML cards with a clean look"""
    html = f"<h2 class='text-2xl font-bold mt-8 mb-4 border-b-2 border-gray-200 pb-2 text-gray-800'>{header}</h2>"
    html += "<div class='grid gap-4'>"
    for item in items:
        # We use .get() to prevent the code from crashing if a piece of news is missing a description
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
            </header>
            
            {news_html}

            <footer class="mt-16 py-8 text-center text-gray-400 text-xs border-t border-gray-200">
                Generated via GitHub Actions • Automated Personal Curator
            </footer>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w") as f:
        f.write(full_html)
    print("Landing page generated successfully!")

if __name__ == "__main__":
    build_page()
