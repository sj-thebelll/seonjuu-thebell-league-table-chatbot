import os
import pandas as pd
import streamlit as st  # ✅ Streamlit 로그 표시

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
def plot_bar_chart_plotly(df, x_col, y_cols, title="📊 주관사별 비교"):
    import plotly.express as px

    for y_col in y_cols:
        fig = px.bar(df, x=x_col, y=y_col, text=y_col, title=title)
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)

# ✅ 한 기업의 여러 연도 실적 (금액/건수/점유율)을 한 그래프에 그리는 꺾은선 차트 함수
def plot_multi_metric_line_chart_for_single_company(df, company_name, x_col="연도", y_cols=["금액(원)", "건수", "점유율(%)"]):
    import plotly.express as px

    # ✅ 데이터 melt: 하나의 y축에 여러 항목(금액/건수/점유율)을 표현
    df_melted = df.melt(id_vars=[x_col, "주관사"], value_vars=y_cols,
                        var_name="항목", value_name="값")

    df_melted[x_col] = df_melted[x_col].astype(int)  # 연도 정수 처리

    fig = px.line(df_melted, x=x_col, y="값", color="항목", markers=True,
                  title=f"📊 {company_name} 연도별 실적 추이")

    fig.update_layout(
        title_font=dict(family="Nanum Gothic", size=20),
        font=dict(family="Nanum Gothic", size=12),
        xaxis_title=x_col,
        yaxis_title="값",
        legend_title="항목"
    )
    st.plotly_chart(fig, use_container_width=True)
