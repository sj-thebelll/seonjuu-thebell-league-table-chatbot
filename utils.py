import os
import pandas as pd
import streamlit as st
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from openai import OpenAI
from dotenv import load_dotenv


# ✅ 공통 컬럼 정규화 함수 (모든 함수에서 공통 사용)
def normalize_column_name(col):
    column_map = {
        "금액": "금액(원)",
        "점유율": "점유율(%)",
        "건수": "건수",
        "순위": "순위"
    }
    return column_map.get(col.strip(), col.strip())

def load_dataframes(data_dir):
    dfs = {}

    # ✅ 파일 이름 매핑
    file_mapping = {
        "ECM": "ecm.xlsx",
        "ABS": "abs.xlsx",
        "FB": "fb.xlsx",
        "국내채권": "domestic_bond.xlsx"
    }

    # ✅ 엑셀 시트 이름 매핑
    sheet_mapping = {
        "ECM": "ECM",
        "ABS": "ABS",
        "FB": "FB",
        "국내채권": "국내채권"
    }

    for product, filename in file_mapping.items():
        file_path = os.path.join(data_dir, filename)
        sheet_name = sheet_mapping[product]

        try:
            print(f"🔍 [DEBUG] {product} 로딩 중... 파일: {filename}, 시트명: {sheet_name}")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            df.columns = df.columns.astype(str).str.strip()

            if "연도" in df.columns:
                df["연도"] = df["연도"].astype(str).str.replace("년", "").astype(int)

            if "주관사" not in df.columns and df.shape[1] >= 3:
                df["주관사"] = df.iloc[:, 2].astype(str).str.strip()
            else:
                df["주관사"] = df["주관사"].astype(str).str.strip()

            df["주관사"] = df["주관사"].str.replace(" ", "")
            dfs[product] = df
            print(f"✅ [DEBUG] {product} 데이터 로드 성공. shape: {df.shape}")

        except Exception as e:
            print(f"❌ [ERROR] {product} 데이터 로딩 실패:", e)

    print("📂 [DEBUG] 최종 로드된 데이터 키:", dfs.keys())
    return dfs

# ✅ (옵션) matplotlib 그래프에서 사용할 한글 폰트 설정
def set_korean_font():
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    nanum_font_path = os.path.abspath("NanumGothic.ttf")
    if os.path.exists(nanum_font_path):
        fm.fontManager.addfont(nanum_font_path)
        font_name = fm.FontProperties(fname=nanum_font_path).get_name()
        plt.rcParams['font.family'] = font_name
    else:
        plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False  # ✅ 마이너스 깨짐 방지

# ✅ plotly 기반 꺾은선 차트 함수 (한글 깨짐 방지)
def plot_line_chart_plotly(df, x_col, y_col, color_col="주관사", title="📈 주관사 순위 변화 추이", key=None):
    import plotly.express as px

    df[x_col] = df[x_col].astype(int)  # ✅ 연도는 반드시 정수형 처리
    fig = px.line(df, x=x_col, y=y_col, color=color_col, markers=True, title=title)
    fig.update_traces(textposition="top center")
    fig.update_layout(
        title_font=dict(family="Nanum Gothic", size=20),
        font=dict(family="Nanum Gothic", size=12),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis_autorange='reversed',  # 순위는 숫자 작을수록 위쪽
        xaxis_type='category'
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

# ✅ bar chart 함수도 유지 (필요 시 사용 가능)
def plot_bar_chart_plotly(df, x_col, y_cols, title="📊 주관사별 비교", key=None):
    import plotly.express as px
    import streamlit as st
    import uuid

    for y_col in y_cols:
        unique_key = key or f"{y_col}_{uuid.uuid4().hex[:8]}"
        fig = px.bar(df, x=x_col, y=y_col, text=y_col, title=title)
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True, key=unique_key)


# ✅ 단일 주관사 기준, 여러 연도 실적 항목을 하나의 꺾은선 그래프로 표현
def plot_multi_metric_line_chart_for_single_company(df, company_name, x_col="연도", y_cols=["금액(원)", "건수", "점유율(%)"], product_name=None):
    import plotly.express as px

    if df.empty:
        label = f"{product_name} 데이터에서 " if product_name else ""
        st.warning(f"⚠️ {label}{company_name}의 그래프 데이터가 없습니다.")
        return

    # ✅ 컬럼명 정규화 및 필터링
    y_cols = [normalize_column_name(col) for col in y_cols]
    y_cols = [col for col in y_cols if col in df.columns]

    if not y_cols:
        st.warning(f"⚠️ {company_name}에 대해 시각화할 수 있는 컬럼이 없습니다.")
        return

    df[x_col] = df[x_col].astype(int)
    df_melted = df.melt(id_vars=[x_col, "주관사"], value_vars=y_cols,
                        var_name="항목", value_name="값")

    for 항목 in df_melted["항목"].unique():
        sub_df = df_melted[df_melted["항목"] == 항목].copy()
        fig = px.line(sub_df, x=x_col, y="값", color="주관사", markers=True,
                      title=(
                          f"📊 [{product_name}] {company_name} 연도별 {항목} 추이"
                          if product_name else f"📊 {company_name} 연도별 {항목} 추이"
                      )


        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            xaxis_title=x_col,
            yaxis_title=항목,
            legend_title="주관사",
            xaxis=dict(type="category", tickformat=".0f")
        )

        if 항목 == "순위":
            fig.update_yaxes(autorange="reversed")

        st.plotly_chart(fig, use_container_width=True, key=f"{company_name}_{항목}_line_chart")


# ✅ 여러 기업 비교용 꺾은선 그래프 함수
def plot_multi_line_chart_plotly(df, x_col, y_cols, color_col, title="📊 비교 꺾은선 그래프"):
    import plotly.express as px
    import streamlit as st

    df[x_col] = df[x_col].astype(int)

    for y_col in y_cols:
        fig = px.line(df, x=x_col, y=y_col, color=color_col, markers=True, title=f"{title} - {y_col}")

        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            xaxis_title=x_col,
            yaxis_title="값",
            legend_title=color_col
        )

        # ✅ 순위일 경우 y축 반전
        if y_col == "순위":
            fig.update_yaxes(autorange="reversed")

        st.plotly_chart(fig, use_container_width=True, key=f"{y_col}_{color_col}_multi")

# ✅ 2개 이하 기업의 순위 비교 꺾은선 그래프 함수
def plot_rank_comparison_for_up_to_two_companies(df, companies, x_col="연도", y_col="순위"):
    import plotly.express as px
    import streamlit as st
    import uuid

    if df.empty or not companies:
        st.warning("⚠️ 비교할 데이터가 없습니다.")
        return

    if y_col not in df.columns:
        st.warning(f"⚠️ '{y_col}' 항목이 데이터에 없습니다.")
        return

    if len(companies) > 2:
        st.warning("⚠️ 현재는 기업 2개까지만 비교 가능합니다.")
        return

    df[x_col] = df[x_col].astype(int)
    chart_df = df[df["주관사"].isin(companies)].copy()
    chart_df = chart_df.sort_values([x_col, "주관사"])

    fig = px.line(
        chart_df,
        x=x_col,
        y=y_col,
        color="주관사",
        markers=True,
        title=(
            f"📊 [{product_name}] {' vs '.join(companies)} 연도별 {y_col} 추이"
            if product_name else f"📊 {' vs '.join(companies)} 연도별 {y_col} 추이"
        )

    fig.update_layout(
        title_font=dict(family="Nanum Gothic", size=20),
        font=dict(family="Nanum Gothic", size=12),
        xaxis_title=x_col,
        yaxis_title=y_col,
        legend_title="주관사",
        xaxis=dict(
            type="category",
            tickformat=".0f"  # ✅ 연도를 소수점 없이 정수로 표시
        )
    )

    if y_col == "순위":
        fig.update_yaxes(autorange="reversed")  # ✅ 순위는 낮을수록 상위

    key_suffix = str(uuid.uuid4())[:8]
    st.plotly_chart(fig, use_container_width=True, key=f"rank_compare_{key_suffix}")

def plot_multi_metric_line_chart_for_two_companies(df, companies, x_col="연도", y_cols=["금액(원)", "점유율(%)", "순위"]):
    import plotly.express as px
    import streamlit as st
    import uuid

    if df.empty or not companies:
        st.warning("⚠️ 비교할 데이터가 없습니다.")
        return

    if len(companies) != 2:
        st.warning("⚠️ 정확히 2개 기업만 비교 가능합니다.")
        return

    col_name_map = {
        "금액": "금액(원)",
        "점유율": "점유율(%)",
        "건수": "건수",
        "순위": "순위"
    }
    y_cols = [col_name_map.get(c, c) for c in y_cols if c in df.columns]

    if not y_cols:
        st.warning("⚠️ 비교 가능한 항목이 없습니다.")
        return

    df = df[df["주관사"].isin(companies)].copy()
    df[x_col] = df[x_col].astype(int)
    df_melted = df.melt(id_vars=[x_col, "주관사"], value_vars=y_cols,
                        var_name="항목", value_name="값")

    for 항목 in df_melted["항목"].unique():
        sub_df = df_melted[df_melted["항목"] == 항목]
        fig = px.line(sub_df, x=x_col, y="값", color="주관사", markers=True,
                      title=f"📊 [{product_name}] {' vs '.join(companies)} 연도별 {항목} 추이" if product_name else f"📊 {' vs '.join(companies)} 연도별 {항목} 추이"

        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            xaxis_title=x_col,
            yaxis_title=항목,
            legend_title="주관사",
            xaxis=dict(type="category", tickformat=".0f")
        )
        if 항목 == "순위":
            fig.update_yaxes(autorange="reversed")

        st.plotly_chart(fig, use_container_width=True, key=f"{항목}_{uuid.uuid4().hex[:8]}")
