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
def plot_line_chart_plotly(df, x_col, y_col, title="📈 주관사 순위 변화 추이"):
    import plotly.express as px

    fig = px.line(df, x=x_col, y=y_col, color='주관사', markers=True, title=title)
    fig.update_traces(textposition="top center")
    fig.update_layout(
        title_font=dict(family="Nanum Gothic", size=20),
        font=dict(family="Nanum Gothic", size=12),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis_autorange='reversed'  # ✅ 순위는 작을수록 높은 것이므로 역순으로 표시
    )
    st.plotly_chart(fig, use_container_width=True)


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
