import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os

# ===========================
# 1. 页面配置
# ===========================
st.set_page_config(
    page_title="舆情信息有效性审计系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 商务风格 CSS
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    h1, h2, h3 {color: #2c3e50; font-family: 'Arial', sans-serif;}
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    .big-stat {font-size: 24px; font-weight: bold; color: #2980b9;}
</style>
""", unsafe_allow_html=True)

DATA_DIR = "./real_data"

# ===========================
# 2. 标题区
# ===========================
c1, c2 = st.columns([1, 5])
with c1:
    st.image("https://img.icons8.com/color/96/data-configuration.png", width=80)
with c2:
    st.title("上市公司舆情信息有效性审计系统")
    st.markdown("**项目逻辑**：基于行为金融学，识别社交媒体舆情中的“有效信息”与“无效噪音”，量化资产定价偏离风险。")

st.markdown("---")

# ===========================
# 3. 核心功能区 (分两大板块)
# ===========================

# 读取数据
combine_file = f"{DATA_DIR}/combined_timeline.csv"

if os.path.exists(combine_file):
    df_all = pd.read_csv(combine_file)

    # -------------------------------------------------------
    # 模块 A: 动态全景侦察 (最炫酷的部分)
    # -------------------------------------------------------
    st.header("1. 市场全景侦察：舆情-价值效能矩阵")
    st.info(
        "💡 **观察指南**：点击下方“Play”按钮。圆圈向**右上方**移动代表“价值共振”（有效舆情）；向**右下方**移动代表“无效噪音”（虚假繁荣）。")

    # 使用 Plotly Express 制作动态气泡图
    fig_motion = px.scatter(
        df_all,
        x="Heat_Score",  # X轴：舆情热度
        y="CAR_Score",  # Y轴：累计收益
        animation_frame="Date_Str",  # 动画轴：日期
        animation_group="Name",  # 追踪对象
        size="total_buzz",  # 气泡大小：当日讨论量
        color="Type",  # 颜色：分类
        hover_name="Name",
        range_x=[0, 105],
        range_y=[-20, 60],
        color_discrete_map={'价值型': '#2ecc71', '噪音型': '#e74c3c', '博弈型': '#f1c40f'},
        template="plotly_white"
    )

    # 划分为四个象限背景
    fig_motion.add_shape(type="rect", x0=0, y0=0, x1=105, y1=60,
                         fillcolor="rgba(46, 204, 113, 0.1)", layer="below", line_width=0)
    fig_motion.add_annotation(x=90, y=50, text="<b>有效共振区</b><br>(赛力斯)", showarrow=False,
                              font=dict(size=14, color="green"))

    fig_motion.add_shape(type="rect", x0=0, y0=-20, x1=105, y1=0,
                         fillcolor="rgba(231, 76, 60, 0.1)", layer="below", line_width=0)
    fig_motion.add_annotation(x=90, y=-10, text="<b>无效噪音区</b><br>(九阳股份)", showarrow=False,
                              font=dict(size=14, color="red"))

    fig_motion.update_layout(
        height=600,
        xaxis_title="<-- 舆情累积热度 (关注度) -->",
        yaxis_title="<-- 股价累计超额收益 (CAR) -->",
        showlegend=True
    )

    st.plotly_chart(fig_motion, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------------
    # 模块 B: 微观个股审计 (详细证据)
    # -------------------------------------------------------
    st.header("2. 个股微观审计：非理性繁荣的解构")

    col_selector, col_detail = st.columns([1, 3])

    with col_selector:
        st.markdown("#### 选择审计对象")
        target = st.radio(
            "Target Asset",
            ["赛力斯 (601127)", "九阳股份 (002242)", "圣龙股份 (603178)"]
        )

        # 动态显示该股票的风险评级
        code = target.split("(")[1].split(")")[0]

        # 读取个股统计
        df_single = pd.read_csv(f"{DATA_DIR}/final_{code}.csv", index_col=0)
        corr = df_single['meme_heat'].corr(df_single['CAR'])

        st.markdown("#### 审计结论")
        if corr > 0.8:
            st.success("✅ **有效性：高**")
            st.caption("舆情与基本面高度吻合，非理性泡沫成分低。")
        elif corr > 0:
            st.warning("⚠️ **有效性：中**")
            st.caption("存在投机博弈，需警惕资金撤离。")
        else:
            st.error("❌ **有效性：低**")
            st.caption("典型的信息噪音，股价与舆情严重背离，建议规避。")

    with col_detail:
        # 画个股详情图
        tab1, tab2 = st.tabs(["📉 趋势拟合证据", "☁️ 语义内容核查"])

        with tab1:
            # 双轴图
            fig_dual = go.Figure()
            fig_dual.add_trace(go.Bar(
                x=df_single.index, y=df_single['meme_heat'],
                name='舆情累积指数', marker_color='rgba(255, 165, 0, 0.5)'
            ))
            fig_dual.add_trace(go.Scatter(
                x=df_single.index, y=df_single['CAR'],
                name='股价CAR', yaxis='y2', line=dict(width=3, color='#2c3e50')
            ))

            fig_dual.update_layout(
                yaxis=dict(title='舆情热度', showgrid=False),
                yaxis2=dict(title='股价收益', overlaying='y', side='right'),
                title=f"{target}：舆情-价格 拟合度分析 (R={corr:.2f})",
                height=400,
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_dual, use_container_width=True)

        with tab2:
            img_path = f"{DATA_DIR}/wc_{code}.png"
            if os.path.exists(img_path):
                c_img, c_txt = st.columns([1, 1])
                with c_img:
                    st.image(Image.open(img_path), use_column_width=True)
                with c_txt:
                    st.info("**语义特征提取：**")
                    if code == '002242':
                        st.write("高频词：`哈基米` `离谱` `甚至`")
                        st.write("特征：**娱乐化、无逻辑**。这解释了为什么其舆情无法转化为持久的买入力量（即右下角陷阱）。")
                    elif code == '601127':
                        st.write("高频词：`遥遥领先` `华为` `大定`")
                        st.write("特征：**产品驱动、信仰驱动**。这种舆情具有极强的行动转化率，推动股价进入右上角共振区。")
                    else:
                        st.write("高频词：`龙字辈` `涨停` `妖股`")
                        st.write("特征：**博弈驱动**。资金关注度极高，但缺乏实体支撑，风险敞口大。")

else:
    st.error("数据文件缺失，请先运行 processing.py")

# 页脚
st.markdown("---")
st.caption("© 2025 MPAcc | 数据赋能财务决策展示")