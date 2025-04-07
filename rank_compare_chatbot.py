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
st.title("🔔 더벨 리그테이블 채포")
st.markdown("""
이 채포는 더벨의 국내체국/ABS/FB/ECM 대표주관 리그테이블 데이터를 기반으로  
자연어로 질문하고, 표 형태로 응답을 받는 채포입니다.
""")

# ✅ 자연어 질문 파싱 함수
def parse_natural_query(query):
    try:
        current_year = datetime.now().year

        if "최근 3년" in query or "최근 3년간" in query:
            years = [current_year - 2, current_year - 1, current_year]
        elif "부터" in query and "까지" in query:
            start, end = map(int, re.findall(r"\d{4}", query))
            years = list(range(start, end + 1))
        elif "~" in query:
            start, end = map(int, re.findall(r"\d{4}", query))
            years = list(range(start, end + 1))
        else:
            years = list(map(int, re.findall(r"\d{4}", query)))

        product = next((p for p in ["ECM", "ABS", "FB", "국내체국"] if p in query), None)
        company = next((company_aliases[k] for k in company_aliases if k in query), None)

        is_compare = any(k in query for k in ["비교", "변화", "올어", "하락"])
        is_trend = any(k in query for k in ["추이", "변화", "3년간", "최근"])
        is_top = any(k in query for k in ["가장 높은", "최고", "1위"])

        column = "금액(원)"
        for keyword, col in column_aliases.items():
            if keyword in query:
                column = col
                break

        rank_range = None
        if re.search(r"1[~\-]5위", query) or "상위 5위" in query:
            rank_range = list(range(1, 6))

        top_n_match = re.search(r"상위 (\d+)개", query)
        top_n = int(top_n_match.group(1)) if top_n_match else None

        return {
            "years": years,
            "product": product,
            "company": company,
            "compare": is_compare,
            "rank_range": rank_range,
            "is_trend": is_trend,
            "is_top": is_top,
            "top_n": top_n,
            "column": column
        }

    except:
        return None

# ✅ 비교 함수
def compare_rank(data, year1, year2):
    df1 = data[data["\uc5f0\ub3c4"] == year1][["\uc8fc\uad00\uc0ac", "\ub300\ud45c\uc8fc\uad00"]].copy()
    df2 = data[data["\uc5f0\ub3c4"] == year2][["\uc8fc\uad00\uc0ac", "\ub300\ud45c\uc8fc\uad00"]].copy()
    df1.columns = ["\uc8fc\uad00\uc0ac", f"{year1}_\uc21c\uc704"]
    df2.columns = ["\uc8fc\uad00\uc0ac", f"{year2}_\uc21c\uc704"]
    merged = pd.merge(df1, df2, on="\uc8fc\uad00\uc0ac")
    merged["\uc21c\uc704\ubcc0\ud654"] = merged[f"{year1}_\uc21c\uc704"] - merged[f"{year2}_\uc21c\uc704"]
    상증 = merged[merged["\uc21c\uc704\ubcc0\ud654"] > 0].sort_values("\uc21c\uc704\ubcc0\ud654", ascending=False)
    하락 = merged[merged["\uc21c\uc704\ubcc0\ud654"] < 0].sort_values("\uc21c\uc704\ubcc0\ud654")
    return 상증, 하락

# ✅ 입력창 및 버튼
query = st.text_input("질문을 입력하세요:")

st.markdown("""
<style>
.stButton > button {
    background-color: #ff4b4b;
    color: white;
    border-radius: 10px;
    padding: 0.5em 1.5em;
    font-size: 1.1em;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

submit = st.button("🔍 질문하기")

# ✅ 질문 처리
if submit and query:
    with st.spinner("답변을 생성 중입니다..."):
        parsed = parse_natural_query(query)

        if not parsed or not parsed.get("product"):
            st.error("❌ 아직 이 질문은 이해하지 못해요. 예: `삼성주관이 점유율 1위인 해 알려줘.`")
        else:
            df = dfs.get(parsed["product"])
            if df is not None and not df.empty:

                # 1. 특정 주관사 순위 추이
                if parsed["is_trend"] and parsed["company"]:
                    trend_df = df[df["주관사"] == parsed["company"]][["연도", "대표주관"]].sort_values("연도")
                    st.subheader(f"📈 {parsed['company']} 순위 추이")
                    st.dataframe(trend_df.rename(columns={"대표주관": "순위"}).reset_index(drop=True))

                # 2. 연도별 1위
                elif parsed["is_top"]:
                    top_result = df[df["대표주관"] == 1][["연도", "주관사"]].sort_values("연도")
                    st.subheader("🏆 연도별 1위 주관사")
                    st.dataframe(top_result.reset_index(drop=True))

                # 3. 특정 주관사 특정 연도
                elif parsed["company"] and parsed["years"]:
                    for y in parsed["years"]:
                        company_df = df[(df["연도"] == y) & (df["주관사"] == parsed["company"])]
                        if not company_df.empty:
                            st.subheader(f"🏅 {y}년 {parsed['product']}에서 {parsed['company']} 순위")
                            st.dataframe(company_df[["주관사", "대표주관"]].rename(columns={"대표주관": "순위"}).reset_index(drop=True))
                        else:
                            st.warning(f"{y}년 {parsed['product']} 데이터에서 {parsed['company']}를 찾을 수 없습니다.")

                # 4. 비교 질문
                elif parsed["compare"] and len(parsed["years"]) == 2:
                    up, down = compare_rank(df, parsed["years"][0], parsed["years"][1])
                    st.subheader(f"📈 {parsed['years'][0]} → {parsed['years'][1]} 상증한 주관사")
                    st.dataframe(up.reset_index(drop=True))
                    st.subheader(f"📉 {parsed['years'][0]} → {parsed['years'][1]} 하락한 주관사")
                    st.dataframe(down.reset_index(drop=True))

                # 5. 기본 \출력 (column 기준 정렬 + 순위 산정)
                else:
                    for y in parsed["years"]:
                        df_year = df[df["연도"] == y].copy()
                        if parsed["top_n"]:
                            df_year = df_year.sort_values(parsed["column"], ascending=False)
                            df_year["순위"] = df_year[parsed["column"]].rank(method="min", ascending=False).astype(int)
                            df_year = df_year.head(parsed["top_n"])
                            st.subheader(f"📌 {y}년 {parsed['product']} 리그테이블")
                            st.dataframe(df_year[["주관사", parsed["column"], "순위"]].reset_index(drop=True))

                        elif parsed["rank_range"]:
                            df_year = df_year[df_year["대표주관"].isin(parsed["rank_range"])]
                            st.subheader(f"📌 {y}년 {parsed['product']} 리그테이블")
                            st.dataframe(df_year[["주관사", "금액(원)", "대표주관"]].reset_index(drop=True))
