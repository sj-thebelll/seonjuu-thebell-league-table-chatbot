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


# ✅ plotly 기반 바 차트 함수 (한글 깨짐 방지)
def plot_bar_chart_plotly(df, x_col, y_cols, title="📊 주관사별 비교"):
    import plotly.express as px

    for y_col in y_cols:
        fig = px.bar(df, x_col, y_col, text=y_col, title=title)  # ✅ 위치 인자로 전달
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),  # ✅ 제목 한글 폰트 지정
            font=dict(family="Nanum Gothic", size=12),        # ✅ 전체 텍스트 한글 폰트 지정
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)

# 🔁 함수 호출 시 위치 인자 사용 예시:
# plot_bar_chart_plotly(df, "주관사", ["금액(원)", "점유율(%)"])
