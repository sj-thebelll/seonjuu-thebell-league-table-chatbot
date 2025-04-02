import streamlit as st

# ✅ 이 줄은 반드시 최상단에 있어야 함!
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="📊")

import os
import pandas as pd
import openai
import re
from utils import load_dataframes
from dotenv import load_dotenv
from tabulate import tabulate

# ✅ .env 로드
load_dotenv()

# ✅ 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ OpenAI API 키
openai.api_key = os.environ["OPENAI_API_KEY"]

# ✅ 증권사명 보정 딕셔너리
company_aliases = {
    "미래에셋": "미래에셋증권",
    "삼성": "삼성증권",
    "KB": "KB증권",
    "NH": "NH투자증권",
    "한투": "한국투자증권",
    "한국증권": "한국투자증권",
    "한화": "한화투자증권",
    "메리츠": "메리츠증권",
    "신한": "신한투자증권",
    "하나": "하나증권",
    "키움": "키움증권",
    "이베스트": "이베스트투자증권",
    "교보": "교보증권",
    "대신": "대신증권",
    "하이": "하이투자증권",
    "부국": "부국증권",
    "DB": "DB금융투자",
    "유안타": "유안타증권",
    "유진": "유진투자증권",
    "케이프": "케이프투자증권",
    "SK": "SK증권",
    "현대차": "현대차증권",
    "KTB": "KTB투자증권",
    "BNK": "BNK투자증권",
    "IBK": "IBK투자증권",
    "토스": "토스증권",
    "다올": "다올투자증권",
    "산은": "한국산업은행",
    "농협": "NH투자증권",
    "신금투": "신한투자증권",
}

# ✅ 설명 텍스트
st.title("📊 더벨 리그테이블 챗봇")

st.markdown("""
이 챗봇은 더벨의 ECM, ABS, FB, 국내채권 대표주관 리그테이블 데이터를 기반으로
질문에 답하거나 연도별 비교를 도와줍니다.  
키워드 기반 질문으로 연도, 데이터 종류, 항목, 증권사, 순위를 쉽게 확인할 수 있습니다.
""")

st.markdown("""
#### 💬 예시 질문
- `2024, ABS, 대표주관, 미래에셋, 순위`  
- `2020, ECM, 대표주관, KB, 순위`  
- `2020, ABS, 대표주관, 삼성, 순위`  
- `2021~2023, ECM, 대표주관, 신한, 순위`  
- `2020~2022, ECM, 대표주관, 삼성/KB/미래에셋, 순위`  
- `2020~2024, ABS, 대표주관, , 1~5위`
""")

st.markdown("""
#### ⚠️ 질문 팁
- ⛔ 아래와 같은 질문은 실패할 수 있어요!
  - 조건을 너무 복잡하게 넣거나 문장이 길면 안 돼요.
- ✅ 예시처럼 쉼표로 정확히 **5개 항목**을 입력해주세요:
  - `연도(또는 범위), 상품종류, 항목명, 증권사명(또는 여러개), 순위 또는 순위범위`
""")

# ✅ 키워드 처리 함수
def process_keywords(keywords, dfs):
    try:
        year_kw = keywords[0].strip()
        product = keywords[1].strip().upper()
        column = keywords[2].strip()
        company_kw = keywords[3].strip()
        rank_kw = keywords[4].strip()

        # 연도 처리
        if "~" in year_kw:
            start, end = map(int, year_kw.split("~"))
            years = list(range(start, end + 1))
        else:
            years = [int(year_kw)]

        # 증권사 처리
        companies = []
        if company_kw:
            for raw in re.split(r"[\/,]", company_kw):
                raw = raw.strip()
                if raw:
                    companies.append(company_aliases.get(raw, raw))

        # 순위 범위 처리
        if "~" in rank_kw:
            rank_start, rank_end = map(int, re.findall(r"\d+", rank_kw))
            rank_range = list(range(rank_start, rank_end + 1))
        else:
            rank_range = [int(s) for s in re.findall(r"\d+", rank_kw)]

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        result_rows = []

        for year in years:
            df_year = df[df["연도"] == year]
            if df_year.empty:
                continue

            if column not in df.columns:
                return f"❌ '{column}'이라는 항목은 없어요."

            df_filtered = df_year[df_year[column].isin(rank_range)]

            if companies:
                df_filtered = df_filtered[df_filtered["주관사"].isin(companies)]

            if not df_filtered.empty:
                df_filtered = df_filtered[["연도", "주관사", column]]
                result_rows.append((year, product, df_filtered))

        if not result_rows:
            return "❌ 조건에 맞는 결과가 없습니다."

        # 결과 출력: 연도 + 항목별 구분 출력
        for (year, product, group_df) in result_rows:
            st.markdown(f"### 📌 {year}년 {product} 리그테이블")
            st.dataframe(group_df.reset_index(drop=True))

        return ""

    except Exception as e:
        return f"❌ 오류가 발생했어요: {str(e)}"

# ✅ 입력
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 생성 중입니다..."):
        keywords = [kw.strip() for kw in query.split(",")]
        if len(keywords) == 5:
            response = process_keywords(keywords, dfs)
            if response:
                st.markdown(response)
        else:
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 쉼표로 구분된 5개 항목을 입력해주세요.")
