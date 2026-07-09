import os
import json
import time
import hashlib
import requests
from markdownify import markdownify as md
import re
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not set in environment")

client = genai.Client(api_key=API_KEY)

URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
NUMS_ARTICLES = 40
DATA_FOLDER = "data"
STORE_NAME_FILE = "file_search_store_name.txt"
METADATA_FILE = "metadata.json"
CHUNK_SIZE_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 100
STORE_DISPLAY_NAME = "optisigns-support-docs"

def slugify(title):
    res = re.sub(r"[^\w]+", "-", title.lower())
    return res.strip('-')

def get_content_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

def write_to_file(title, title_slugify, content, url):
    os.makedirs(DATA_FOLDER, exist_ok=True)
    filepath = f"{DATA_FOLDER}/{title_slugify}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Url: {url}\n\n")
        f.write(content)
    return filepath

def fetch_article_data(article):
    title = article["title"]
    body = article["body"]
    url_article = article["html_url"]
    content_md = md(body, heading_style="ATX")
    return title, content_md, url_article

def create_store():
    store = client.file_search_stores.create(
        config={"display_name": STORE_DISPLAY_NAME}
    )
    print(f"Da tao File Search Store: {store.name}")
    return store

def scrape_articles(n, url):
    articles_data = []
    response = requests.get(url)
    data = response.json()
    articles = data["articles"]
    nums_of_articles = len(articles)
    
    if not articles:
        print("Khong co du lieu")
        return []
    
    i, y = 0, 0
    while i < n:
        if y >= nums_of_articles:
            if n > nums_of_articles:
                print(f"\nChi co {i} bai viet")
            break
        
        article = articles[y]
        title, content, url_article = fetch_article_data(article)
        articles_data.append({
            "title": title,
            "content": content,
            "url": url_article,
            "hash": get_content_hash(content)
        })
        
        print(f"\rDang scrape bai {i+1}", end="", flush=True)
        y += 1
        i += 1
        
        if y >= 30 and data.get("next_page"):
            y = 0
            url = data["next_page"]
            response = requests.get(url)
            data = response.json()
            articles = data["articles"]
            nums_of_articles = len(articles)
    
    print("\nDa scrape xong")
    return articles_data

def upload_delta(articles_data, store_name):
    metadata = load_metadata()
    uploaded = 0
    failed = 0
    total = len(articles_data)
    
    for idx, article in enumerate(articles_data, 1):
        title = article["title"]
        content = article["content"]
        url = article["url"]
        current_hash = article["hash"]
        title_slug = slugify(title)
        
        if title_slug in metadata:
            stored_hash = metadata[title_slug].get("hash")
            if stored_hash == current_hash:
                print(f"  [{idx}/{total}] Bo qua (khong thay doi): {title}")
                continue
        
        filepath = write_to_file(title, title_slug, content, url)
        try:
            operation = client.file_search_stores.upload_to_file_search_store(
                file=filepath,
                file_search_store_name=store_name,
                config={"display_name": title_slug},
                mime_type="text/markdown"
            )
            while not operation.done:
                time.sleep(2)
                operation = client.operations.get(operation)
            
            uploaded += 1
            print(f"  [{idx}/{total}] Upload thanh cong: {title}")
            
            metadata[title_slug] = {
                "hash": current_hash,
                "url": url,
                "title": title,
                "last_upload": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_metadata(metadata)
            
        except Exception as e:
            failed += 1
            print(f"  [{idx}/{total}] LOI: {title} -> {e}")
        
    return uploaded, failed, total

def main():
    store_name = None
    if os.path.exists(STORE_NAME_FILE):
        with open(STORE_NAME_FILE, "r", encoding="utf-8") as f:
            store_name = f.read().strip()
    
    if not store_name:
        print("Khong tim thay store name hoac file rong. Tao store moi...")
        store = create_store()
        store_name = store.name
        with open(STORE_NAME_FILE, "w", encoding="utf-8") as f:
            f.write(store_name)
        print(f"Da luu store name vao {STORE_NAME_FILE}")
    
    print("Bat dau scrape bai viet...")
    articles = scrape_articles(NUMS_ARTICLES, URL)
    
    if not articles:
        print("Khong co bai viet nao duoc scrape.")
        return
    
    print("Dang upload delta (chi bai moi/thay doi)...")
    uploaded, failed, total = upload_delta(articles, store_name)
    
    store_info = client.file_search_stores.get(name=store_name)
    total_bytes = store_info.size_bytes or 0
    stride_tokens = CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS
    estimated_chunks = round((total_bytes / 4) / stride_tokens) if total_bytes else 0
    
    print("\n=== LOG ===")
    print(f"Store: {store_name}")
    print(f"Articles scraped: {total}")
    print(f"Uploaded (new/updated): {uploaded}")
    print(f"Failed: {failed}")
    print(f"Chunking: max={CHUNK_SIZE_TOKENS}, overlap={CHUNK_OVERLAP_TOKENS}")
    print(f"Total bytes ingested: {total_bytes}")
    print(f"Estimated chunks: ~{estimated_chunks}")

if __name__ == "__main__":
    main()
