import streamlit as st

# ✅ 첫 줄에 위치해야 함
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import re
import pandas as pd
import openai
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

column_aliases = {"금액": "금액(원)", "점유율": "점유율(%)"}
allowed_columns = {
    "ECM": ["금액(원)", "건수", "점유율(%)"],
    "ABS": ["금액(원)", "건수", "점유율(%)"],
    "FB": ["금액(원)", "건수", "점유율(%)"],
    "국내채권": ["금액(원)", "건수", "점유율(%)"]
}

# ✅ UI 안내 텍스트
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 국내채권/ABS/FB/ECM 대표주관 리그테이블 데이터를 기반으로  자연어로 질문하고, 표 형태로 응답을 받는 창번입니다.

#### 💬 예시 질문
- `2024년 ECM 대표주관사 순위를 알려줘.`  
- `2021년 ABS에서 KB주관 순위가 몇 위야?`  
- `2023년 국내채권 리그테이블 1~5위 보여줘.`  
- `2020년부터 2024년까지 ECM에서 삼성주관 순위가 어떻게 변하여있는지 알려줘.`  
- `2023년, 2024년 비교해서 국내채권 대표주관사 중 순위가 올라간 주관사는?`  
- `2020~2023년 FB에서 금액 기준 상위 3개 주관사 알려줘.`  
- `ABS 부문에서 간 최근 3년간 점유율이 가장 높은 주관사는?`  
- `ECM에서 2022년에 가장 많은 건수를 기록한 주관사는?`  
- `KB주관의 순위 차표를 3년간 보여줘.`  
- `삼성주관이 점유율 1위인 해는 어느 해야?`
""")

# ✅ 자연어 질문 파싱

def parse_natural_query(query):
    try:
        years = list(map(int, re.findall(r"\d{4}", query)))
        product = next((p for p in ["ECM", "ABS", "FB", "국내채권"] if p in query), None)
        company = next((company_aliases[k] for k in company_aliases if k in query), None)
        is_compare = any(k in query for k in ["비교", "변화", "오른", "하락"])
        rank_range = list(range(1, 6)) if any(k in query for k in ["1~5위", "1-5위", "상위 5위"]) else None
        is_trend = "추이" in query or "변화" in query or "3년간" in query or "최근" in query
        is_top = any(k in query for k in ["가장 높은", "최고", "1위"])

        return {
            "years": years,
            "product": product,
            "company": company,
            "compare": is_compare,
            "rank_range": rank_range,
            "is_trend": is_trend,
            "is_top": is_top
        }
    except:
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

# ✅ 질문 입력
query = st.text_input("질문을 입력하세요:")
submit = st.button("질문하기")

if submit and query:
    with st.spinner("답변을 생성 중입니다..."):
        parsed = parse_natural_query(query)

        if not parsed or not parsed.get("product"):
            st.error("❌ 아직 이 질문은 이해하지 못해요. 예: `삼성증권이 점유율 1위인 해 알려줘.`")
        else:
            df = dfs.get(parsed["product"])
            if df is not None and not df.empty:

                # 추이 분석 (특정 증권사의 연도별 순위)
                if parsed["is_trend"] and parsed["company"]:
                    trend_df = df[df["주관사"] == parsed["company"]][["연도", "대표주관"]].sort_values("연도")
                    st.subheader(f"📈 {parsed['company']} 순위 추이")
                    st.dataframe(trend_df.rename(columns={"대표주관": "순위"}).reset_index(drop=True))

                # 특정 항목 1위 기업 (예: 점유율 1위)
                elif parsed["is_top"]:
                    top_result = df[df["대표주관"] == 1][["연도", "주관사"]].sort_values("연도")
                    st.subheader("🏆 연도별 1위 주관사")
                    st.dataframe(top_result.reset_index(drop=True))

                # 비교 요청 (두 연도 간 상승/하락 비교)
                elif parsed["compare"] and len(parsed["years"]) == 2:
                    up, down = compare_rank(df, parsed["years"][0], parsed["years"][1])
                    st.subheader(f"📈 {parsed['years'][0]} → {parsed['years'][1]} 상승한 증권사")
                    st.dataframe(up.reset_index(drop=True))
                    st.subheader(f"📉 {parsed['years'][0]} → {parsed['years'][1]} 하락한 증권사")
                    st.dataframe(down.reset_index(drop=True))

                # 기본 출력 (연도 + 상위 순위)
                else:
                    for y in parsed["years"]:
                        df_year = df[df["연도"] == y]
                        if parsed["rank_range"]:
                            df_year = df_year[df_year["대표주관"].isin(parsed["rank_range"])]
                        st.subheader(f"📌 {y}년 {parsed['product']} 리그테이블")
                        st.dataframe(df_year[["주관사", "대표주관"]].reset_index(drop=True))
