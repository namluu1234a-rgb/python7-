import pandas as pd
import numpy as np
import os
from scipy.stats import pearsonr
from wordcloud import WordCloud
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
DATA_DIR = "./real_data"

# 股票清单
STOCKS = {
    '002242': {'name': '九阳股份', 'type': 'noise'},
    '601127': {'name': '赛力斯', 'type': 'value'},
    '01810': {'name': '小米集团', 'type': 'value'}
}


def process_final():
    print("🚀 启动跨平台舆情融合引擎 (Guba + Bilibili)...")
    stats_list = []

    for code, info in STOCKS.items():
        name = info['name']

        # 1. 定义文件路径
        guba_path = f"{DATA_DIR}/sentiment_{code}.csv"
        bili_path = f"{DATA_DIR}/bilibili_{code}.csv"
        market_path = f"{DATA_DIR}/market_{code}.csv"

        # 检查市场数据 (必须有)
        if not os.path.exists(market_path):
            print(f"⚠️ 跳过 {name}: 缺股价数据")
            continue

        # 2. 读取各路数据
        df_m = pd.read_csv(market_path, index_col=0)
        df_m.index = pd.to_datetime(df_m.index, errors='coerce')

        # 读取股吧
        if os.path.exists(guba_path):
            df_guba = pd.read_csv(guba_path, index_col=0)
            df_guba.index = pd.to_datetime(df_guba.index, errors='coerce')
            df_guba = df_guba.rename(columns={'read_count': 'guba_buzz'})
            # 确保列存在
            if 'guba_buzz' in df_guba.columns:
                df_guba = df_guba[['guba_buzz']]
            else:
                df_guba['guba_buzz'] = 0
        else:
            df_guba = pd.DataFrame(columns=['guba_buzz'])

        # 读取B站
        if os.path.exists(bili_path):
            df_bili = pd.read_csv(bili_path, index_col=0)
            df_bili.index = pd.to_datetime(df_bili.index, errors='coerce')
            if 'bili_buzz' in df_bili.columns:
                df_bili = df_bili[['bili_buzz']]
            else:
                df_bili['bili_buzz'] = 0
        else:
            df_bili = pd.DataFrame(columns=['bili_buzz'])

        # 3. 跨平台数据融合 (Outer Join)
        # 这一步把股吧和B站的时间轴并集，哪天没数据就填0
        df_social = pd.merge(df_guba, df_bili, left_index=True, right_index=True, how='outer')
        df_social = df_social.fillna(0)

        # 4. 计算全网总热度
        if 'guba_buzz' not in df_social.columns: df_social['guba_buzz'] = 0
        if 'bili_buzz' not in df_social.columns: df_social['bili_buzz'] = 0

        df_social['total_buzz'] = df_social['guba_buzz'] + df_social['bili_buzz']

        print(f"\n🔨 处理 {name}: 股吧+B站 -> 融合后{len(df_social)}天")

        # 5. 交易日对齐与递延 (Weekend Effect)
        trade_days = df_m.index.sort_values()

        def get_next_trade_day(d):
            future_days = trade_days[trade_days >= d]
            return future_days[0] if len(future_days) > 0 else pd.NaT

        df_social['trade_date'] = df_social.index.to_series().apply(get_next_trade_day)
        df_social = df_social.dropna(subset=['trade_date'])

        # 按交易日聚合
        df_social_agg = df_social.groupby('trade_date').agg({
            'total_buzz': 'sum',
            'guba_buzz': 'sum',
            'bili_buzz': 'sum'
        })

        # 6. 与股价合并 【核心修复点】
        # 这里之前写错了变量名，现在修正为 df_social_agg
        df_final = pd.merge(df_m, df_social_agg, left_index=True, right_index=True, how='left')

        df_final['total_buzz'] = df_final['total_buzz'].fillna(0)

        # 7. 计算累积趋势因子 (Cumulative Trend)
        df_final['cum_factor'] = df_final['total_buzz'].cumsum()

        # 归一化 (0-100)，方便画图和APP展示，命名为 meme_heat
        # 避免除以0
        denom = df_final['cum_factor'].max() - df_final['cum_factor'].min()
        if denom == 0: denom = 1

        df_final['meme_heat'] = (df_final['cum_factor'] - df_final['cum_factor'].min()) / denom

        # 8. 统计分析
        valid_df = df_final.dropna(subset=['CAR', 'meme_heat'])

        if len(valid_df) > 5:
            corr, p = pearsonr(valid_df['meme_heat'], valid_df['CAR'])
            print(f"   📊 融合后效果: R={corr:.4f} (P={p:.4e})")

            # 保存最终宽表
            df_final.to_csv(f"{DATA_DIR}/final_{code}.csv")

            # 记录统计结果
            total_buzz_sum = df_social['total_buzz'].sum() + 1
            stats_list.append({
                'code': code, 'name': name,
                'r': corr, 'p': p,
                'guba_ratio': df_social['guba_buzz'].sum() / total_buzz_sum,
                'bili_ratio': df_social['bili_buzz'].sum() / total_buzz_sum
            })

            # 生成混合词云 (兜底)
            wc_path = f"{DATA_DIR}/wc_{code}.png"
            if not os.path.exists(wc_path):
                wc = WordCloud(font_path="C:/Windows/Fonts/simhei.ttf", background_color="white", width=800, height=500)
                wc.generate(name)
                wc.to_file(wc_path)
        else:
            print("   ⚠️ 有效数据不足，无法回归")

    # 保存统计表
    if stats_list:
        stat_df = pd.DataFrame(stats_list)
        stat_df.to_csv(f"{DATA_DIR}/stats.csv", index=False)
        print("\n✅ 全流程结束！统计结果已保存。")


if __name__ == "__main__":
    process_final()
