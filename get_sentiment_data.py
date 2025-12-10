import pandas as pd
import time
import random
import re
import os
import concurrent.futures
from snownlp import SnowNLP
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

# ==========================================
# 1. 你的“人工导航”坐标 (精准打击)
# ==========================================
CONFIG = {
    '002242': {'name': '九阳股份', 'start': 173, 'end': 177, 'force_year': '2023'},
    '601127': {'name': '赛力斯', 'start': 3208, 'end': 3654, 'force_year': '2023'},
    '603178': {'name': '圣龙股份', 'start': 449, 'end': 699, 'force_year': '2023'}
}

DATA_DIR = "./real_data"
# 开启 8 线程加速
MAX_WORKERS = 8


# ==========================================
# 2. 极速版浏览器驱动
# ==========================================
def get_fast_driver():
    try:
        options = EdgeOptions()
        options.add_argument('--headless')  # 后台运行
        options.add_argument('--disable-gpu')
        # 禁止图片和CSS
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        options.page_load_strategy = 'eager'
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
        return driver
    except:
        try:
            options = ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
            options.page_load_strategy = 'eager'
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except:
            return None


# ==========================================
# 3. 抓取逻辑
# ==========================================
def worker_crawl(stock_code, start_page, end_page, year, worker_id):
    driver = get_fast_driver()
    if not driver: return []

    local_data = []
    try:
        for page in range(start_page, end_page + 1):
            url = f"http://guba.eastmoney.com/list,{stock_code}_{page}.html"
            try:
                driver.get(url)
                time.sleep(random.uniform(0.5, 1.0))

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                items = soup.select('.listitem')
                if not items: items = soup.find_all('tr')

                for item in items:
                    try:
                        text = item.text
                        # 找标题
                        title_tag = item.select_one('.l3 a')
                        if not title_tag:
                            links = item.find_all('a')
                            title_tag = max(links, key=lambda x: len(x.text)) if links else None

                        title = title_tag.get('title') or title_tag.text if title_tag else ""
                        title = title.strip()
                        if not title or "公告" in title: continue

                        # 找日期 (MM-DD)
                        date_match = re.search(r'(\d{2})-(\d{2})', text)
                        if date_match:
                            mm_dd = date_match.group(0)
                            full_date = f"{year}-{mm_dd}"  # 强制拼上2023

                            read_count = 0
                            nums = re.findall(r'\d+', text.replace('万', '0000'))
                            if nums: read_count = int(nums[0])

                            score = SnowNLP(title).sentiments

                            local_data.append({
                                'date': full_date,
                                'title': title,
                                'read_count': read_count,
                                'sentiment': score
                            })
                    except:
                        continue
            except:
                continue

            if (page - start_page) % 20 == 0:
                print(f"   ⚡ [分队-{worker_id}] 推进至第 {page} 页...")

    finally:
        driver.quit()

    return local_data


# ==========================================
# 4. 主程序
# ==========================================
def run_fast_crawl():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

    total_start = time.time()

    for code, conf in CONFIG.items():
        name = conf['name']
        start = conf['start']
        end = conf['end']
        year = conf['force_year']
        total_pages = end - start + 1

        print(f"\n==============================================")
        print(f"🚀 启动抓取: {name} ({code})")
        print(f"📄 页码: {start}-{end} (共 {total_pages} 页)")
        print(f"==============================================")

        chunk_size = (total_pages // MAX_WORKERS) + 1
        futures = []
        all_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for i in range(MAX_WORKERS):
                c_start = start + i * chunk_size
                c_end = min(start + (i + 1) * chunk_size - 1, end)
                if c_start > end: break
                futures.append(executor.submit(worker_crawl, code, c_start, c_end, year, i + 1))

            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())

        # 保存
        if all_results:
            df = pd.DataFrame(all_results)

            # 【修复点】这里定义了列名 'weighted_score'
            df['weighted_score'] = df['sentiment'] * (df['read_count'] + 1)

            # 聚合计算
            daily = df.groupby('date').apply(
                lambda x: pd.Series({
                    'avg_sentiment': x['sentiment'].mean(),
                    'total_buzz': x['read_count'].sum(),
                    'weighted_score': x['weighted_score'].sum() / (x['read_count'].sum() + 1)
                })
            )
            # 排序并保存
            daily = daily.sort_index()
            path = f"{DATA_DIR}/sentiment_{code}.csv"
            daily.to_csv(path)
            print(f"✅ {name} 保存成功！日期范围: {daily.index.min()} ~ {daily.index.max()}")
        else:
            print(f"⚠️ {name} 未抓到数据")

    print(f"\n🏁 全部完成！耗时: {time.time() - total_start:.1f} 秒")


if __name__ == "__main__":
    run_fast_crawl()