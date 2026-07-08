import requests
import os
from markdownify import markdownify as md
import re

url ="https://support.optisigns.com/api/v2/help_center/en-us/articles.json"


def slugify(title):
    res = re.sub(r"[^\w]+","-",title.lower())
    return res.strip('-')

def write_to_file(title, title_slugify, content, url):
    os.makedirs("data", exist_ok=True)
    with open(f"data/{title_slugify}.md", "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Url: {url}\n\n")
        f.write(content)

def take_one_articles(first):
    json_content = first["body"]
    md_content = md(json_content, heading_style="ATX")
    title=first["title"]
    url_article= first["html_url"]
    title_slugify=slugify(title)
    write_to_file(title, title_slugify, md_content, url_article)
    

def take_articles(n, url):
    response = requests.get(url)
    data = response.json()
    articles = data["articles"]
    nums_of_articles = len(articles)
    if articles == None: 
        print("Khong co du lieu")
        return
    i=0
    y=0
    while (i< n):
        if y >= nums_of_articles:
            if n> nums_of_articles:
                print(f"\nOnly have {i+1} articles")
            break
        take_one_articles(articles[y])
        print(f"\rFetching article {i+1}", end="", flush=True)

        y+=1
        i+=1
        if y>=30 and data["next_page"]:
            y=0
            url= data["next_page"]
            response = requests.get(url)
            data = response.json()
            articles = data["articles"]
            nums_of_articles=len(articles)
            
    print("\nDone")



if __name__=="__main__":
    take_articles(40, url)
