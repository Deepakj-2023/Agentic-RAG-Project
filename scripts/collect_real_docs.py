import os
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv
import time

load_dotenv()

# Initialize Tavily
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

TARGET_DIR = "data/unstructured"
os.makedirs(TARGET_DIR, exist_ok=True)

TOPICS = [
    "FIFA World Cup 2022 full final match report Argentina vs France",
    "IPL 2024 season review and top performers and each match stats",
    "PSL 2024 match by match results summary",
    "Lionel Messi 2024-2025 season stats and news",
    "Virat Kohli IPL 2024 performance analysis",
    "Babar Azam PSL 2024 records and highlights"
    " Complete each match schedule and stats in FIFA World Cup 2022, ipl 2025,2024 and psl 2025,2024 "
    "FIFA World Cup 2022 full final match report Argentina vs France"
]

def scrape_url(url):
    if url.lower().endswith('.pdf'):
        print(f"Skipping PDF: {url}")
        return None
    try:
        print(f"Scraping: {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Check if content type is HTML
            if 'text/html' not in response.headers.get('Content-Type', ''):
                print(f"Skipping non-HTML content: {url}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove junk
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            # Focus on main article content if possible
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
            
            text = main_content.get_text(separator=' ')
            # Clean up whitespace and junk lines
            lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 20]
            clean_text = '\n'.join(lines)
            
            if len(clean_text) < 500:
                print(f"Content too short, skipping: {url}")
                return None
                
            return clean_text[:30000] 
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return None

def collect_docs():
    for topic in TOPICS:
        print(f"\nSearching for: {topic}")
        search_result = tavily.search(query=topic, search_depth="advanced", max_results=2)
        
        for i, res in enumerate(search_result.get('results', [])):
            url = res.get('url')
            content = scrape_url(url)
            
            if content:
                filename = topic.replace(" ", "_").lower()[:50] + f"_{i}.txt"
                filepath = os.path.join(TARGET_DIR, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"Title: {res.get('title')}\nURL: {url}\n\n{content}")
                print(f"Saved: {filename}")
            
            time.sleep(2) # Avoid rate limiting

if __name__ == "__main__":
    collect_docs()
    print("\n--- Document collection complete. Now run setup_data.py to re-index. ---")
