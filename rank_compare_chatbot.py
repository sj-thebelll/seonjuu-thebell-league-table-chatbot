import os
import streamlit as st
import pandas as pd
import openai
import re
from utils import load_dataframes
from dotenv import load_dotenv

# ✅ .env 로드
load_dotenv()

# ✅ 페이지 설정 (항상 최상단!)
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="📊")

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

# ✅ 제목
st.title("📊 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ECM, ABS, FB, 국내채권 대표주관 리그테이블 데이터를 기반으로
질문에 답하거나 연도별 비교를 도와줍니다.
키워드 기반 질문으로 연도, 데이터 종류, 항목, 증권사, 순위를 쉽게 확인할 수 있습니다.
""")

# ✅ 예시 질문
st.markdown("""
#### 💬 예시 질문
- `2024, ABS, 대표주관, 미래에셋, 순위`  
  → ❌ 2024년 ABS 대표주관사 순위에 미래에셋증권은 포함되어 있지 않습니다.
- `2020, ECM, 대표주관, KB, 순위`  
  → ✅ 2020년 ECM 대표주관사 순위에서 KB증권은 **1위**입니다.
- `2020, ABS, 대표주관, 삼성, 순위`  
  → ✅ 2020년 ABS 대표주관사 순위에서 삼성증권은 **3위**입니다.
- `2021~2023, ECM, 대표주관, 신한, 순위`  
  → ✅ 여러 연도에 걸친 ECM 대표주관사 순위를 확인할 수 있어요.
- `2020~2022, ECM, 대표주관, 삼성/KB/미래에셋, 순위`  
  → ✅ 여러 증권사를 동시에 비교할 수 있어요.
- `2020~2024, ABS, 대표주관, , 1~5위`  
  → ✅ 특정 순위 구간에 속한 증권사를 보여줄 수 있어요.
""")

st.markdown("""
#### ⚠️ 질문 팁
**⛔ 아래와 같은 질문은 실패할 수 있어요!**
- 여러 조건을 한 문장에 다 넣으면 복잡해서 잘 안 돼요.
예: `2020~2024 ECM과 ABS 상품별로 증권사 순위 알려줘`
""")

# ✅ 키워드 처리 함수
def process_keywords(keywords, dfs):
    try:
        year_part = keywords[0].strip()
        product = keywords[1].strip().upper()
        column = keywords[2].strip()
        company_input = keywords[3].strip()
        rank_input = keywords[4].strip()

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        # ✅ 연도 범위 처리
        if "~" in year_part:
            start, end = map(int, year_part.split("~"))
            years = list(range(start, end + 1))
        else:
            years = [int(year_part)]

        df_year = df[df["연도"].isin(years)]
        if df_year.empty:
            return f"❌ {year_part} 데이터가 없어요."

        # ✅ 순위 범위 처리
        if re.match(r"\d+~\d+위", rank_input):
            r1, r2 = map(lambda x: int(x.replace("위", "")), rank_input.split("~"))
            df_filtered = df_year[(df_year[column] >= r1) & (df_year[column] <= r2)]
            if df_filtered.empty:
                return f"❌ {year_part}년 {product} {r1}~{r2}위에 해당하는 데이터가 없어요."
            grouped = df_filtered[["연도", "주관사", column]].sort_values(["연도", column])
            return grouped.to_markdown(index=False)

        # ✅ 증권사 복수 처리
        companies = [company_aliases.get(c.strip(), c.strip()) for c in company_input.split("/")]
        df_companies = df_year[df_year["주관사"].isin(companies)]
        if df_companies.empty:
            return f"❌ {year_part}년 {product} 대표주관사 순위에 해당 증권사가 포함되어 있지 않습니다."

        if column not in df.columns:
            return f"❌ '{column}'이라는 항목은 없어요."

        grouped = df_companies[["연도", "주관사", column]].sort_values(["연도"])
        return grouped.to_markdown(index=False)

    except Exception as e:
        return f"❌ 오류가 발생했어요: {str(e)}"

# ✅ 입력
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 생성 중입니다..."):
        keywords = [kw.strip() for kw in query.split(",")]
        if len(keywords) == 5:
            response = process_keywords(keywords, dfs)
            st.markdown(response)
        else:
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 쉼표로 구분된 5개 항목을 입력해주세요.")
