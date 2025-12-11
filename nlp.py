import pandas as pd
import numpy as np
import os
import jieba
from snownlp import SnowNLP
from wordcloud import WordCloud

# 配置路径
RAW_DIR = "./raw_data_lake"  # 来源
REAL_DIR = "./real_data"  # 结果
if not os.path.exists(REAL_DIR): os.makedirs(REAL_DIR)

# 股票及停用词 (防止词云出现无关词)
STOCKS = {
    '002242': {'name': '九阳股份', 'stop': ['九阳', '股份', '股票', '今天', '主力', '什么']},
    '601127': {'name': '赛力斯', 'stop': ['赛力斯', '汽车', '股票', '什么时候', '多少', '我们']},
    '01810': {'name': '小米集团', 'stop': ['小米', '集团', '港股', '01810', '股价', '怎么']}
}


def get_sentiment(text):
    """计算情感分"""
    try:
        return SnowNLP(str(text)).sentiments
    except:
        return 0.5


def process_nlp():
    print("🚀 启动 NLP 分析工厂...")

    for code, conf in STOCKS.items():
        name = conf['name']
        raw_path = f"{RAW_DIR}/raw_{code}.csv"

        if not os.path.exists(raw_path):
            print(f"⚠️ 跳过 {name}: 未找到 {raw_path}，请先运行 crawl.py")
            continue

        print(f"\n🔨 正在精炼: {name} ...")

        # 1. 读取原始数据
        df = pd.read_csv(raw_path)

        # 2. 批量情感打分
        print(f"   -> 正在计算 {len(df)} 条数据的情感分...")
        df['sentiment'] = df['title'].apply(get_sentiment)

        # 3. 生成词云图片
        print(f"   -> 正在生成词云...")
        text_content = " ".join(df['title'].astype(str).tolist())
        words = jieba.lcut(text_content)
        clean_words = [w for w in words if len(w) > 1 and w not in conf['stop']]

        wc = WordCloud(font_path="C:/Windows/Fonts/simhei.ttf",
                       background_color="white", width=800, height=500)
        wc.generate(" ".join(clean_words))
        wc.to_file(f"{REAL_DIR}/wc_{code}.png")

        # 4. 聚合为日度数据
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])

        # 计算加权分：(情感 * 热度)
        df['weighted_score_raw'] = df['sentiment'] * (df['read_count'] + 1)

        daily = df.groupby('date').agg({
            'sentiment': 'mean',  # 平均情感
            'read_count': 'sum',  # 总热度 (Buzz)
            'weighted_score_raw': 'sum'  # 总加权分
        })

        # 归一化日度加权情感
        daily['weighted_score'] = daily['weighted_score_raw'] / (daily['read_count'] + 1)

        # 保存
        save_path = f"{REAL_DIR}/sentiment_{code}.csv"
        daily.to_csv(save_path)
        print(f"✅ {name} 处理完毕！已存入 {save_path}")

    print("\n🎉 NLP 任务全部完成！")


if __name__ == "__main__":
    process_nlp()
