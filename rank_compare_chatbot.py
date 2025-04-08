import streamlit as st

# ✅ 첫 줄에 위치해야 함
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import re
import pandas as pd
import openai
from datetime import datetime
from dotenv import load_dotenv
from utils import load_dataframes
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import subprocess  # ✅ 추가

# ✅ 한글 폰트 설치 함수 (Linux 환경 한정)
def install_font_linux():
    if platform.system() == "Linux":
        font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
        if not os.path.exists(font_path):
            st.warning("📦 한글 폰트를 설치 중입니다. 잠시만 기다려주세요...")
            try:
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "fonts-nanum"], check=True)
                subprocess.run(["fc-cache", "-fv"], check=True)
                st.success("✅ 한글 폰트 설치가 완료되었습니다. 새로고침 후 이용해주세요.")
            except Exception as e:
                st.error(f"❌ 폰트 설치 중 오류 발생: {e}")

# ✅ 한글 폰트 설치 먼저 시도
install_font_linux()

# ✅ 운영체제별 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    nanum_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
    if os.path.exists(nanum_path):
        # ✅ 폰트를 수동 등록하여 matplotlib이 인식하도록 처리
        fm.fontManager.addfont(nanum_path)
        nanum_name = fm.FontProperties(fname=nanum_path).get_name()
        plt.rcParams['font.family'] = nanum_name
    else:
        plt.rcParams['font.family'] = 'sans-serif'
        st.warning("⚠️ 시스템에 한글 폰트가 설치되어 있지 않아 글자가 깨질 수 있습니다.")

plt.rcParams['axes.unicode_minus'] = False  # 마이너스 깨짐 방지


# ✅ 바 차트 또는 선 차트 자동 선택 함수
def plot_bar_chart(df, x_col, y_cols):
    plt.figure(figsize=(10, 5))
    if len(y_cols) == 1:
        for y in y_cols:
            plt.bar(df[x_col], df[y], label=y)
    else:
        for y in y_cols:
            plt.plot(df[x_col], df[y], marker='o', label=y)

    plt.xlabel(x_col)
    plt.ylabel("금액" if "금액" in y_cols[0] else "순위")
    plt.title("📊 주관사별 비교")
    plt.xticks(rotation=45)
    plt.legend()
    st.pyplot(plt)


# ✅ 환경 변수 및 API 키
load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

# ✅ 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ 증권사/항목 보정 딕셔너리
company_aliases = {
    "미래에셋": "미래에셋증권", "삼성": "삼성증권", "KB": "KB증권", "NH": "NH투자증권",
    "한투": "한국투자증권", "한국증권": "한국투자증권", "한화": "한화투자증권", "메리츠": "메리츠증권",
    "신한": "신한투자증권", "하나": "하나증권", "키움": "키움증권", "이베스트": "이베스트투자증권",
    "교보": "교보증권", "대신": "대신증권", "하이": "하이투자증권", "부국": "부국증권",
    "DB": "DB금융투자", "유안타": "유안타증권", "유진": "유진투자증권", "케이프": "케이프투자증권",
    "SK": "SK증권", "현대차": "현대차증권", "KTB": "KTB투자증권", "BNK": "BNK투자증권",
    "IBK": "IBK투자증권", "토스": "토스증권", "다올": "다올투자증권", "산은": "한국산업은행",
    "신금투": "신한투자증권"
}

column_aliases = {"금액": "금액(원)", "점유율": "점유율(%)", "건수": "건수"}
allowed_columns = {
    "ECM": ["금액(원)", "건수", "점유율(%)"],
    "ABS": ["금액(원)", "건수", "점유율(%)"],
    "FB": ["금액(원)", "건수", "점유율(%)"],
    "국내채권": ["금액(원)", "건수", "점유율(%)"]
}

# ✅ UI 안내 텍스트
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ECM / ABS / FB / 국내채권 부문 대표주관 리그테이블 데이터를 기반으로  
자연어로 질문하고, 표 형태로 응답을 받는 챗봇입니다.

#### 💬 예시 질문
- 2024년 ECM 대표주관사 순위 알려줘.  
- 2023년 ABS 대표주관 상위 3개사 보여줘.  
- 2022년 FB 대표주관 1위는 어디야?  
- 2021~2023년 국내채권 대표주관사 순위 비교해줘.  
- 2024년 ECM에서 삼성증권 대표주관 순위 알려줘.  

#### ℹ️ 질문 팁
- 부문: ECM, ABS, FB, 국내채권  
- 기준: 금액 / 건수 / 점유율  
- 연도, 증권사, 순위 비교 질문 가능  
- 월별·딜 단위 질문은 지원하지 않음
""")


# ✅ 자연어 질문 파싱 함수 (rank_range + top_n 개선 + is_chart 포함)
def parse_natural_query(query):
    try:
        current_year = datetime.now().year

        query = query.strip()
        query_no_space = query.replace(" ", "")

        # ✅ 연도 추출
        years = []
        range_match = re.search(r"(\d{4})\s*[~\-]\s*(\d{4})", query)
        if range_match:
            start_year = int(range_match.group(1))
            end_year = int(range_match.group(2))
            years = list(range(start_year, end_year + 1))
        else:
            year_matches = re.findall(r"\d{4}", query)
            years = list(map(int, year_matches))

        # ✅ 부문 추출
        product_keywords = {
            "ECM": ["ECM", "이씨엠"],
            "ABS": ["ABS", "에이비에스"],
            "FB": ["FB", "회사채", "에프비"],
            "국내채권": ["국내채권", "국내 채권", "국채", "국내채권리그테이블", "국내채권 리그테이블"]
        }

        product = None
        for key, aliases in product_keywords.items():
            if any(alias in query or alias in query_no_space for alias in aliases):
                product = key
                break

        if not product:
            return None

        # ✅ 증권사 추출
        company = next((company_aliases[k] for k in company_aliases if k in query), None)

        # ✅ 조건 플래그
        is_compare = any(k in query for k in ["비교", "변화", "오른", "하락"])
        is_trend = any(k in query for k in ["추이", "변화", "3년간", "최근"])
        is_top = any(k in query for k in ["가장 많은", "가장 높은", "최고", "1위"])
        is_chart = any(k in query for k in ["그래프", "차트"])

        # ✅ 복수 기준 추출
        columns = []
        for keyword, col in column_aliases.items():
            if keyword in query:
                columns.append(col)

        if not columns:
            columns = ["금액(원)"]  # 기본값

        # ✅ 순위 범위 추출
        rank_range = None
        top_n = None

        # "상위 3위", "Top 3" → top_n
        top_n_match = re.search(r"(?:상위\s*|Top\s*)(\d+)(?:위|개)?", query, re.IGNORECASE)
        if top_n_match:
            top_n = int(top_n_match.group(1))
            rank_range = list(range(1, top_n + 1))

        # "1~3위", "2-5위" → rank_range
        range_match = re.search(r"(\d+)\s*[~\-]\s*(\d+)\s*위", query)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            rank_range = list(range(start, end + 1))
            top_n = end  # top_n도 설정해둠 (선택사항)

        return {
            "years": years,
            "product": product,
            "company": company,
            "compare": is_compare,
            "rank_range": rank_range,
            "is_trend": is_trend,
            "is_top": is_top,
            "top_n": top_n,
            "columns": columns,
            "is_chart": is_chart  # ✅ 추가된 항목
        }

    except Exception as e:
        st.write("❗ 파싱 중 오류 발생:", e)
        return None

# ✅ 비교 함수
def compare_rank(data, year1, year2):
    df1 = data[data["연도"] == year1][["주관사", "대표주관"]].copy()
    df2 = data[data["연도"] == year2][["주관사", "대표주관"]].copy()
    df1.columns = ["주관사", f"{year1}_순위"]
    df2.columns = ["주관사", f"{year2}_순위"]
    merged = pd.merge(df1, df2, on="주관사")
    merged["순위변화"] = merged[f"{year1}_순위"] - merged[f"{year2}_순위"]
    상승 = merged[merged["순위변화"] > 0].sort_values("순위변화", ascending=False)
    하락 = merged[merged["순위변화"] < 0].sort_values("순위변화")
    return 상승, 하락

# ✅ 입력창 + 버튼 → st.form으로 묶어서 Enter로 제출 가능하게
with st.form(key="question_form"):
    query = st.text_input("질문을 입력하세요:")
    submit = st.form_submit_button("🔍 질문하기")  # 버튼 이름 유지

# ✅ 버튼 스타일은 아래처럼 유지
st.markdown("""
<style>
button[kind="formSubmit"] {
    background-color: #ff4b4b;
    color: white;
    border-radius: 10px;
    padding: 0.5em 1.5em;
    font-size: 1.1em;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ✅ 금액(원) → 금액(억원) 변환 함수
def format_억단위(df, colname):
    df = df.copy()
    df["금액(억원)"] = df[colname] / 1e8  
    df.drop(columns=[colname], inplace=True) 
    return df

# ✅ 질문 처리
if submit and query:
    parsed = parse_natural_query(query)
    st.write("🔍 파싱 결과:", parsed)

    with st.spinner("답변을 생성 중입니다..."):
        if not parsed or not parsed.get("product"):
            st.error("❌ 아직 이 질문은 이해하지 못해요. 예: KB증권이 대표주관 1위인 해 알려줘.")
        else:
            df = dfs.get(parsed["product"])
            if df is not None and not df.empty:

                # 1️⃣ 연도 2개, 기준 1개 → 연도별 비교
                if parsed["compare"] and len(parsed["years"]) == 2 and len(parsed["columns"]) == 1:
                    year1, year2 = parsed["years"]
                    col = parsed["columns"][0]

                    df1 = df[df["연도"] == year1].copy()
                    df2 = df[df["연도"] == year2].copy()

                    if col == "금액(원)":
                        df1 = format_억단위(df1, col)
                        df2 = format_억단위(df2, col)
                        col = "금액(억원)"

                    if df1.empty or df2.empty:
                        st.warning(f"⚠️ {year1}년 또는 {year2}년 {parsed['product']} 데이터가 없습니다.")
                    else:
                        df1["순위1"] = df1[col].rank(ascending=False, method="min")
                        df2["순위2"] = df2[col].rank(ascending=False, method="min")

                        merged = pd.merge(df1[["주관사", "순위1"]], df2[["주관사", "순위2"]], on="주관사")
                        merged["순위변화"] = merged["순위1"] - merged["순위2"]

                        상승 = merged[merged["순위변화"] > 0].sort_values("순위변화", ascending=False)
                        하락 = merged[merged["순위변화"] < 0].sort_values("순위변화")

                        st.subheader(f"📈 {year1} → {year2} 순위 상승 주관사 ({col} 기준)")
                        st.dataframe(상승.reset_index(drop=True))
                        st.subheader(f"📉 {year1} → {year2} 순위 하락 주관사 ({col} 기준)")
                        st.dataframe(하락.reset_index(drop=True))

                # 2️⃣ 같은 연도, 기준 2개 → 기준 간 순위 비교 + 그래프
                elif len(parsed["columns"]) == 2 and len(parsed["years"]) == 1:
                    y = parsed["years"][0]
                    col1, col2 = parsed["columns"]
                    df_year = df[df["연도"] == y].copy()

                    if df_year.empty:
                        st.warning(f"⚠️ {y}년 {parsed['product']} 데이터가 없습니다.")
                    else:
                        if col1 == "금액(원)":
                            df_year = format_억단위(df_year, col1)
                            col1 = "금액(억원)"
                        if col2 == "금액(원)":
                            df_year = format_억단위(df_year, col2)
                            col2 = "금액(억원)"

                        df_year[f"{col1}_순위"] = df_year[col1].rank(ascending=False, method="min").astype(int)
                        df_year[f"{col2}_순위"] = df_year[col2].rank(ascending=False, method="min").astype(int)
                        df_year["순위차이"] = (df_year[f"{col1}_순위"] - df_year[f"{col2}_순위"]).abs()

                        if parsed["rank_range"]:
                            df_year = df_year[df_year[f"{col1}_순위"].isin(parsed["rank_range"])]

                        result = df_year[["주관사", f"{col1}_순위", f"{col2}_순위", "순위차이"]].sort_values(f"{col1}_순위")
                        st.subheader(f"📊 {y}년 {parsed['product']} - {col1} vs {col2} 순위 비교")
                        st.dataframe(result.reset_index(drop=True))

                        # 그래프
                        st.subheader("📈 순위 비교 그래프")
                        plot_bar_chart(result, "주관사", [f"{col1}_순위", f"{col2}_순위"])

                # 3️⃣ 단일 연도 기준별 리그테이블
                else:
                    for y in parsed["years"]:
                        df_year = df[df["연도"] == y]
                        if df_year.empty:
                            st.warning(f"⚠️ {y}년 {parsed['product']} 데이터가 없습니다.")
                            continue

                        for col in parsed["columns"]:
                            df_year = df_year.copy()

                            if col == "금액(원)":
                                df_year = format_억단위(df_year, col)
                                col = "금액(억원)"

                            df_year["순위"] = df_year[col].rank(ascending=False, method="min")

                            # 3-1️⃣ 1위
                            if parsed["is_top"]:
                                sorted_df = df_year.sort_values(col, ascending=False).copy()
                                result = sorted_df[sorted_df["순위"] == 1][["순위", "주관사", col]]
                                st.subheader(f"🏆 {y}년 {parsed['product']} {col} 1위 주관사")
                                st.dataframe(result.reset_index(drop=True))

                            # 3-2️⃣ top_n
                            elif parsed["top_n"]:
                                sorted_df = df_year.sort_values(col, ascending=False).copy()
                                result = sorted_df.head(parsed["top_n"])[["순위", "주관사", col]]
                                st.subheader(f"📌 {y}년 {parsed['product']} {col} 상위 {parsed['top_n']}개 주관사")
                                st.dataframe(result.reset_index(drop=True))

                                if parsed.get("is_chart"):
                                    result_for_chart = result.sort_values(col, ascending=False)
                                    st.subheader("📈 그래프")
                                    plot_bar_chart(result_for_chart, "주관사", [col])

                            # 3-3️⃣ rank_range
                            elif parsed["rank_range"]:
                                result = df_year[df_year["순위"].isin(parsed["rank_range"])]
                                result = result[["순위", "주관사", col]]
                                st.subheader(f"📌 {y}년 {parsed['product']} {col} 기준 리그테이블")
                                st.dataframe(result.reset_index(drop=True))

                                if parsed.get("is_chart"):
                                    result_for_chart = result.sort_values(col, ascending=False)
                                    st.subheader("📈 그래프")
                                    plot_bar_chart(result_for_chart, "주관사", [col])

                            # 3-4️⃣ 특정 주관사
                            elif parsed["company"]:
                                result = df_year[df_year["주관사"] == parsed["company"]][["순위", "주관사", col]]
                                if not result.empty:
                                    st.subheader(f"🏅 {y}년 {parsed['product']}에서 {parsed['company']} {col} 순위")
                                    st.dataframe(result.reset_index(drop=True))
                                else:
                                    st.warning(f"{y}년 {parsed['product']} 데이터에서 {parsed['company']}를 찾을 수 없습니다.")

                            # 3-5️⃣ 기타 전체 테이블
                            else:
                                result = df_year[["순위", "주관사", col]]
                                st.subheader(f"📌 {y}년 {parsed['product']} {col} 기준 리그테이블")
                                st.dataframe(result.reset_index(drop=True))

                                if parsed.get("is_chart"):
                                    result_for_chart = result.sort_values(col, ascending=False)
                                    st.subheader("📈 그래프")
                                    plot_bar_chart(result_for_chart, "주관사", [col])
