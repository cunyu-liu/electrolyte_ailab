import wikipediaapi
import json
import time
import os
import requests

# --- 配置区域 --- nohup ./monitor.sh > /dev/null 2>&1 &
PROXY_URL = "http://127.0.0.1:7890"
os.environ["http_proxy"] = PROXY_URL
os.environ["https_proxy"] = PROXY_URL

USER_AGENT = "ChemCrawler/2.3 (research_project; contact: student@zju.edu.cn)"
OUTPUT_FILE = "wiki_data_depth1.jsonl"
MAX_RETRIES = 3 
RETRY_DELAY = 5 

# 1. 模糊搜索词 (已加入你的新需求)
# 这些词用于去 Wiki 搜索是否存在同名或近似的“分类”
SEARCH_KEYWORDS = [
    "Lithium-ion battery",
    "Lithium metal battery",
    "Lithium–sulfur battery",
    "Solid-state battery",
    "Polymer electrolytes",         # 对应 Polymer solid-state electrolyte
    "Solid electrolytes",           # 对应 Inorganic solid electrolyte
    "Fast-ion conductors",          # 对应 Sulfide/Oxide solid electrolytes 的学术分类名
    "Sodium-ion battery",
    "Sodium battery",               # 对应 Sodium metal battery
    "Ceramic electrolytes",         # 氧化物电解质常被称为陶瓷电解质
    "Glass electrolytes"            # 硫化物电解质常属于玻璃态电解质
]

# 2. [重点] 核心保底分类列表
# 我已将你列出的关键词映射为维基百科真实存在的分类
DEFAULT_CATEGORIES = [
    # --- 锂电系列 ---
    "Category:Lithium-ion batteries",
    "Category:Lithium batteries",          # 包含 Lithium metal
    "Category:Lithium–sulfur batteries",   # 注意 En-dash
    
    # --- 固态/电解质系列 ---
    "Category:Solid-state batteries",
    "Category:Fast-ion conductors",        # 【核心】无机/硫化物/氧化物电解质都在这里
    "Category:Polyelectrolytes",           # 聚合物电解质
    "Category:Polymers",                   # 聚合物基质
    "Category:Ceramic materials",          # 氧化物固态电解质相关
    "Category:Electrolytes",
    
    # --- 钠电系列 ---
    "Category:Sodium-ion batteries",
    "Category:Sodium batteries",           # 包含 Sodium metal
    
    # --- 通用/材料 ---
    "Category:Battery materials",
    "Category:Electrochemistry",
    "Category:Energy storage"
]

def check_proxy():
    try:
        print("[System] Testing proxy connection...")
        requests.get("https://en.wikipedia.org", proxies={"https": PROXY_URL}, timeout=10)
        print("[System] Proxy is working.")
        return True
    except Exception as e:
        print(f"[Fatal Error] Proxy check failed: {e}")
        return False

def search_valid_categories(keyword):
    """模糊搜索分类"""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "list": "search",
        "srsearch": keyword, "srnamespace": 14, "srlimit": 3, # 14=Category
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, params=params, headers=headers, proxies={"https": PROXY_URL}, timeout=10)
        if response.status_code != 200: return []
        data = response.json()
        found = []
        if "query" in data and "search" in data["query"]:
            for item in data["query"]["search"]:
                title = item["title"]
                if not title.startswith("Category:"): title = f"Category:{title}"
                found.append(title)
        return found
    except: return []

def safe_get_members(category_page):
    for attempt in range(MAX_RETRIES):
        try: return list(category_page.categorymembers.values())
        except: time.sleep(RETRY_DELAY)
    return []

def safe_get_text(page):
    for attempt in range(MAX_RETRIES):
        try: return page.text
        except: time.sleep(RETRY_DELAY)
    return None

def crawl_wiki_data():
    if not check_proxy(): return

    # --- 阶段 1: 构建任务列表 ---
    print("\n[System] Building Category List based on your keywords...")
    valid_root_categories = set()

    # 1.1 加入硬编码的保底列表 (确保你的核心词一定被爬取)
    for cat in DEFAULT_CATEGORIES:
        valid_root_categories.add(cat)
    print(f" -> Added {len(DEFAULT_CATEGORIES)} default mapped categories.")

    # 1.2 尝试搜索补充
    print(" -> Scanning Wiki for more keyword matches...")
    for kw in SEARCH_KEYWORDS:
        results = search_valid_categories(kw)
        if results:
            for cat in results:
                valid_root_categories.add(cat)
        time.sleep(1) 

    print(f"\n[System] Final Target List: {len(valid_root_categories)} categories.")
    print("-" * 50)

    # --- 阶段 2: 爬虫初始化 ---
    wiki = wikipediaapi.Wikipedia(
        user_agent=USER_AGENT,
        language='en',  
        extract_format=wikipediaapi.ExtractFormat.WIKI,
        timeout=30
    )
    
    MAX_DEPTH = 1
    visited_pages = set()
    visited_ids = set()
    
    # --- 阶段 3: 加载历史 ---
    if os.path.exists(OUTPUT_FILE):
        print(f"[System] Loading history from {OUTPUT_FILE}...")
        try:
            loaded_count = 0
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        record = json.loads(line)
                        title = record.get("title")
                        pid = record.get("id")
                        if title: visited_pages.add(title)
                        if pid: visited_ids.add(pid)
                        loaded_count += 1
                    except: continue
            print(f"[System] Loaded {loaded_count} pages.")
        except: pass

    # --- 阶段 4: 执行爬取 ---
    def process_category(category_member, level):
        if level > MAX_DEPTH: return
        
        members = safe_get_members(category_member)
        if not members: return

        skipped_count = 0
        for c in members:
            try:
                # 忽略非内容页
                if c.ns not in [wikipediaapi.Namespace.MAIN, wikipediaapi.Namespace.CATEGORY]:
                    continue

                if c.pageid in visited_ids or c.title in visited_pages:
                    skipped_count += 1
                    if skipped_count % 100 == 0:
                        print(f"[Status] ...Skipped {skipped_count} visited items in '{category_member.title}'")
                    continue
                
                if c.ns == wikipediaapi.Namespace.MAIN:
                    page_text = safe_get_text(c)
                    if not page_text: continue

                    visited_pages.add(c.title)
                    visited_ids.add(c.pageid)
                    
                    data = {
                        "id": c.pageid,
                        "title": c.title,
                        "text": f"{c.title}\n\n{page_text}", 
                        "meta": {"url": c.fullurl, "categories": list(c.categories.keys())}
                    }
                    
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    
                    print(f"[Page] Saved: {c.title}")
                    skipped_count = 0 
                    time.sleep(1) 
                    
                elif c.ns == wikipediaapi.Namespace.CATEGORY:
                    print(f"[Category] Found sub: {c.title} (Level {level+1})")
                    time.sleep(1)
                    process_category(c, level + 1)
                    
            except Exception as e:
                print(f"[Warning] Error on '{c.title}': {e}")
                continue

    # 执行任务
    for cat_name in valid_root_categories:
        print(f"\n--- [Root] Processing: {cat_name} ---")
        cat_page = wiki.page(cat_name)
        if cat_page.exists():
            process_category(cat_page, 0)
        else:
            print(f"[Info] Category '{cat_name}' not found/empty. Skipping.")

    print("\n[System] All tasks finished.")

if __name__ == "__main__":
    crawl_wiki_data()