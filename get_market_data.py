import baostock as bs
import pandas as pd
import os

# 时间窗口保持宽口径，方便画图
TASKS = {
    '002242': ('2023-04-01', '2023-08-31'),
    '601127': ('2023-08-01', '2024-01-31'),
    '603178': ('2023-08-01', '2024-01-31')
}
DATA_DIR = "./real_data"


def fetch_data():
    bs.login()
    print("📉 正在获取 OHLC (开高低收) 全量数据...")

    # 1. 大盘 (用于算CAR)
    rs = bs.query_history_k_data_plus("sh.000300", "date,pctChg",
                                      start_date='2023-01-01', end_date='2024-02-01', frequency="d")
    bench_list = []
    while rs.next(): bench_list.append(rs.get_row_data())
    bench_df = pd.DataFrame(bench_list, columns=rs.fields)
    bench_df['date'] = pd.to_datetime(bench_df['date'])
    bench_df['bench_ret'] = bench_df['pctChg'].replace('', 0).astype(float) / 100
    bench_df = bench_df.set_index('date')

    # 2. 个股 (增加 open, high, low, volume)
    for code, (s, e) in TASKS.items():
        prefix = "sh" if code.startswith('6') else "sz"

        rs = bs.query_history_k_data_plus(f"{prefix}.{code}",
                                          "date,open,high,low,close,volume,pctChg",
                                          start_date=s, end_date=e, frequency="d", adjustflag="3")

        data = []
        while rs.next(): data.append(rs.get_row_data())

        if data:
            df = pd.DataFrame(data, columns=rs.fields)
            df['date'] = pd.to_datetime(df['date'])
            # 转换数值类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
                df[col] = df[col].replace('', 0).astype(float)

            df['pctChg'] = df['pctChg'] / 100
            df = df.set_index('date')

            # 【核心修复点】合并时只取 bench_df 的 ['bench_ret'] 列
            # 这样就不会因为两边都有 pctChg 而产生命名冲突了
            m = pd.merge(df, bench_df[['bench_ret']], left_index=True, right_index=True, how='left')

            # 现在 m['pctChg'] 是存在的
            m['AR'] = m['pctChg'] - m['bench_ret']
            m['CAR'] = m['AR'].cumsum()

            m.to_csv(f"{DATA_DIR}/market_{code}.csv")
            print(f"   ✅ {code} K线数据获取成功")
        else:
            print(f"   ⚠️ {code} 无数据")

    bs.logout()


if __name__ == "__main__":
    fetch_data()