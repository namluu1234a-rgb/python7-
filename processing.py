import pandas as pd
import numpy as np
import os
from scipy.stats import pearsonr
from wordcloud import WordCloud
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
DATA_DIR = "./real_data"

STOCKS = {
    '002242': {'name': '九阳股份', 'type': '噪音型'},
    '601127': {'name': '赛力斯', 'type': '价值型'},
    '603178': {'name': '圣龙股份', 'type': '博弈型'}
}


def process_final():
    print("🚀 启动数据清洗与全景整合引擎 (修复版)...")

    all_data_list = []

    for code, info in STOCKS.items():
        name = info['name']
        s_path = f"{DATA_DIR}/sentiment_{code}.csv"
        m_path = f"{DATA_DIR}/market_{code}.csv"

        if not os.path.exists(s_path) or not os.path.exists(m_path):
            print(f"⚠️ 跳过 {name}")
            continue

        # 1. 读取与清洗
        df_s = pd.read_csv(s_path, index_col=0)
        df_m = pd.read_csv(m_path, index_col=0)

        df_s.index = pd.to_datetime(df_s.index, errors='coerce')
        df_m.index = pd.to_datetime(df_m.index, errors='coerce')
        df_s = df_s.dropna(how='all')

        # 2. 合并
        df = pd.merge(df_m, df_s, left_index=True, right_index=True, how='inner')
        if len(df) < 5: continue

        # 3. 统一因子计算
        if code in ['601127', '603178']:
            # 热门股用热度累积
            raw = df['total_buzz'].cumsum()
        else:
            # 九阳也用热度累积，放大一点数值以便观察
            raw = df['total_buzz'].cumsum() * 2

        df['cum_factor'] = raw.bfill().fillna(0)

        # 【关键修复】APP 需要读取 'meme_heat' 列，这里必须赋值
        df['meme_heat'] = df['cum_factor']

        # 4. 计算其他展示指标
        # 背离度
        df['divergence'] = df['cum_factor'] / (df['CAR'].abs() + 0.01)

        # 归一化 (0-100分制，用于动态气泡图)
        df['Heat_Score'] = (df['cum_factor'] - df['cum_factor'].min()) / (
                    df['cum_factor'].max() - df['cum_factor'].min()) * 100
        df['CAR_Score'] = df['CAR'] * 100

        # 保存单文件
        df.to_csv(f"{DATA_DIR}/final_{code}.csv")

        # 5. 准备合并数据 (用于动态图)
        df['Name'] = name
        df['Type'] = info['type']
        df['Date_Str'] = df.index.strftime('%Y-%m-%d')

        df_reset = df.reset_index()
        # 确保包含 app 需要的所有列
        all_data_list.append(
            df_reset[['date', 'Date_Str', 'Name', 'Type', 'Heat_Score', 'CAR_Score', 'total_buzz', 'meme_heat', 'CAR']])

        # 6. 生成词云
        wc = WordCloud(font_path="C:/Windows/Fonts/simhei.ttf", background_color="white", width=600, height=400)
        if code == '601127':
            words = {'遥遥领先': 100, '华为': 90, 'M7': 80, '大定': 60}
        elif code == '603178':
            words = {'龙字辈': 100, '涨停': 90, '圣龙': 80, '跨年妖': 70}
        else:
            words = {'哈基米': 100, '离谱': 50, '甚至': 40, '好玩': 30}
        wc.generate_from_frequencies(words)
        wc.to_file(f"{DATA_DIR}/wc_{code}.png")

    # 7. 生成全景时间轴数据
    if all_data_list:
        full_df = pd.concat(all_data_list)
        full_df = full_df.sort_values('date')
        full_df.to_csv(f"{DATA_DIR}/combined_timeline.csv", index=False)
        print("✅ 数据修复完成！请重新运行 streamlit run app.py")


if __name__ == "__main__":
    process_final()
