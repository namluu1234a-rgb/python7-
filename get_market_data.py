import akshare as ak
import baostock as bs  # 【必须有这一行】
import pandas as pd
import os
import datetime

# ===========================
# 0. 强制禁用代理 (保留防身)
# ===========================
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# ===========================
# 1. 配置：真实时间窗口
# ===========================
today = datetime.datetime.now().strftime("%Y%m%d")
today_dash = datetime.datetime.now().strftime("%Y-%m-%d")

TASKS = {
    '002242': {'type': 'A', 'start': '20251001', 'end': today},
    '601127': {'type': 'A', 'start': '20230801', 'end': '20240131'},
    '01810': {'type': 'HK', 'start': '20240201', 'end': '20240531'}
}

DATA_DIR = "./real_data"
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)


def fetch_real_data():
    print("🚀 启动 [Baostock + AkShare] 双引擎获取行情...")

    # ==========================================
    # 第一步：用 Baostock 获取大盘基准 (最稳)
    # ==========================================
    print("📉 [引擎1] Baostock: 获取沪深300基准...")

    # 登录 (必须在 import baostock as bs 之后)
    lg = bs.login()
    if lg.error_code != '0':
        print(f"   ❌ Baostock 登录失败: {lg.error_msg}")
        bench_df = pd.DataFrame()
    else:
        # 获取涵盖所有个股时间段的大盘数据
        rs = bs.query_history_k_data_plus("sh.000300", "date,pctChg",
                                          start_date='2023-01-01', end_date=today_dash, frequency="d")

        data_list = []
        while rs.next(): data_list.append(rs.get_row_data())

        bench_df = pd.DataFrame(data_list, columns=rs.fields)
        bench_df['date'] = pd.to_datetime(bench_df['date'])
        # Baostock pctChg 是百分比，转小数
        bench_df['bench_ret'] = bench_df['pctChg'].replace('', 0).astype(float) / 100
        bench_df = bench_df.set_index('date')

        print(f"   ✅ 基准获取成功 ({len(bench_df)}条)")
        bs.logout()

    # ==========================================
    # 第二步：用 AkShare 获取个股 (支持港股)
    # ==========================================
    print("📉 [引擎2] AkShare: 获取个股数据...")

    for code, conf in TASKS.items():
        market_type = conf['type']
        s_date = conf['start']
        e_date = conf['end']

        print(f"   -> 获取 [{code}]...")

        try:
            df = pd.DataFrame()

            # --- A股 ---
            if market_type == 'A':
                df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=s_date, end_date=e_date, adjust="hfq")
                df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                                        '成交量': 'volume', '涨跌幅': 'pctChg'})
                df['pctChg'] = df['pctChg'] / 100

            # --- 港股 ---
            elif market_type == 'HK':
                df = ak.stock_hk_hist(symbol=code, start_date=s_date, end_date=e_date, adjust="hfq")
                df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                                        '成交量': 'volume', '涨跌幅': 'pctChg'})
                df['pctChg'] = df['pctChg'] / 100

            if df.empty:
                print(f"      ⚠️ 数据为空")
                continue

            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            # 数值转换
            cols = ['open', 'high', 'low', 'close', 'volume', 'pctChg']
            for c in cols: df[c] = pd.to_numeric(df[c], errors='coerce')

            # --- 计算 CAR ---
            # 左连接：保留个股交易日
            if not bench_df.empty:
                m = pd.merge(df, bench_df[['bench_ret']], left_index=True, right_index=True, how='left')
                m['bench_ret'] = m['bench_ret'].fillna(0)  # 港股假期对不齐的补0
            else:
                m = df.copy()
                m['bench_ret'] = 0

            m['AR'] = m['pctChg'] - m['bench_ret']
            m['CAR'] = m['AR'].cumsum()

            save_path = f"{DATA_DIR}/market_{code}.csv"
            m.to_csv(save_path)
            print(f"      ✅ 已保存: {save_path}")

        except Exception as e:
            print(f"      ❌ 失败: {e}")


if __name__ == "__main__":
    fetch_real_data()
