import os 
import streamlit as st
import pandas as pd
import openai
import reimport streamlit as st

# ✅ 페이지 설정은 가장 위에서 실행
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
    "미래에셋": "미래에셋증권", "삼성": "삼성증권", "KB": "KB증권", "NH": "NH투자증권",
    "한투": "한국투자증권", "한국증권": "한국투자증권", "한화": "한화투자증권", "메리츠": "메리츠증권",
    "신한": "신한투자증권", "하나": "하나증권", "키움": "키움증권", "이베스트": "이베스트투자증권",
    "교보": "교보증권", "대신": "대신증권", "하이": "하이투자증권", "부국": "부국증권",
    "DB": "DB금융투자", "유안타": "유안타증권", "유진": "유진투자증권", "케이프": "케이프투자증권",
    "SK": "SK증권", "현대차": "현대차증권", "KTB": "KTB투자증권", "BNK": "BNK투자증권",
    "IBK": "IBK투자증권", "토스": "토스증권", "다올": "다올투자증권", "산은": "한국산업은행",
    "농협": "NH투자증권", "신금투": "신한투자증권",
}

# ✅ 페이지 UI
st.title("📊 더벨 리그테이블 챗봇")

st.markdown("""
이 챗봇은 더벨의 ECM, ABS, FB, 국내채권 대표주관 리그테이블 데이터를 기반으로 질문에 답하거나 연도별 비교를 도와줍니다. 키워드 기반 질문으로 연도, 데이터 종류, 항목, 증권사, 순위를 쉽게 확인할 수 있습니다.
""")

# ✅ 예시 질문
st.markdown("""
### 💬 예시 질문
- `2024, ABS, 대표주관, 미래에셋, 순위`  
  ➤ ❌ 2024년 ABS 대표주관사 순위에 미래에셋증권은 포함되어 있지 않습니다.  
- `2020, ECM, 대표주관, KB, 순위`  
  ➤ ✅ 2020년 ECM 대표주관사 순위에서 KB증권은 1위입니다.  
- `2020, ABS, 대표주관, 삼성, 순위`  
  ➤ ✅ 2020년 ABS 대표주관사 순위에서 삼성증권은 3위입니다.  
- `2021~2023, ECM, 대표주관, 신한, 순위`  
  ➤ ✅ 여러 연도에 걸친 ECM 대표주관사 순위를 확인할 수 있어요.  
- `2020~2022, ECM, 대표주관, 삼성/KD/미래에셋, 순위`  
  ➤ ✅ 여러 증권사를 동시에 비교할 수 있어요.  
- `2020~2024, ABS, 대표주관, , 1~5위`  
  ➤ ✅ 특정 순위 구간에 속한 증권사를 보여줄 수 있어요.
""")

st.markdown("""
### ⚠️ 질문 팁
- ⛔ 아래와 같은 질문은 실패할 수 있어요!
- 여러 조건을 한 문장에 다 넣으면 복잡해서 잘 안 돼요.  
예: `2020~2024 ECM과 ABS 상품별로 증권사 순위 알려줘`
""")

# ✅ 키워드 처리 함수
def process_keywords(keywords, dfs):
    try:
        # 키워드 파싱
        year_part = keywords[0].strip()
        product = keywords[1].strip().upper()
        column = keywords[2].strip()
        company_part = keywords[3].strip()
        rank_part = keywords[4].strip()

        # 연도 처리
        if "~" in year_part:
            start_year, end_year = map(int, year_part.split("~"))
            years = list(range(start_year, end_year + 1))
        else:
            years = [int(year_part)]

        # 증권사 처리
        companies = [company_aliases.get(c.strip(), c.strip()) for c in company_part.split("/") if c.strip()] if company_part else []

        # 순위 처리
        if "~" in rank_part or "-" in rank_part:
            rank_range = re.split("~|-", rank_part)
            start_rank, end_rank = map(int, rank_range)
            rank_filter = lambda r: start_rank <= r <= end_rank
        elif rank_part.isdigit():
            rank_filter = lambda r: r == int(rank_part)
        else:
            rank_filter = lambda r: True  # 무시

        # 데이터 확인
        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        # 출력용 테이블 생성
        output_tables = []

        for year in years:
            df_year = df[df["연도"] == year]
            if df_year.empty:
                continue

            df_filtered = df_year.copy()

            if companies:
                df_filtered = df_filtered[df_filtered["주관사"].apply(lambda x: any(comp in x for comp in companies))]
                if df_filtered.empty:
                    continue

            if column in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[column].apply(lambda x: isinstance(x, int) and rank_filter(x))]
            else:
                return f"❌ '{column}'이라는 항목은 없어요."

            if df_filtered.empty:
                continue

            df_result = df_filtered[["연도", "주관사", column]].sort_values(column)
            df_result = df_result.rename(columns={column: "대표주관"})
            output_tables.append((year, product, df_result))

        if not output_tables:
            return "❌ 해당 조건에 맞는 데이터가 없어요."

        # ✅ 출력
        for year, product, table in output_tables:
            st.markdown(f"#### 📌 {year}년 {product} 대표주관 순위")
            st.dataframe(table, use_container_width=True)

        return None

    except Exception as e:
        return f"❌ 오류가 발생했어요: {str(e)}"

# ✅ 사용자 입력
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 생성 중입니다..."):
        keywords = [kw.strip() for kw in query.split(",")]
        if len(keywords) == 5:
            result = process_keywords(keywords, dfs)
            if result:
                st.markdown(result)
        else:
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 쉼표로 구분된 5개 항목을 입력해주세요.")

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

# ✅ 페이지 설정
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="📊")
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
- 여러 조건을 한 문장에 다 넣으면 복잡해서 잘 안 돼요. 예: `2020~2024 ECM과 ABS 상품별로 증권사 순위 알려줘`
""")

# ✅ 키워드 처리 함수 (고급)
def process_keywords_advanced(keywords, dfs):
    try:
        # 연도 범위 처리
        year_str = keywords[0].strip()
        if "~" in year_str:
            start_year, end_year = map(int, year_str.split("~"))
            years = list(range(start_year, end_year + 1))
        else:
            years = [int(year_str)]

        product = keywords[1].strip().upper()
        column = keywords[2].strip()
        company_input = keywords[3].strip()
        rank_input = keywords[4].strip()

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        df = df[df["연도"].isin(years)]

        if column not in df.columns:
            return f"❌ '{column}'이라는 항목은 없어요."

        if company_input:
            companies = [company_aliases.get(c.strip(), c.strip()) for c in company_input.split("/")]
            df = df[df["주관사"].isin(companies)]

        if rank_input:
            if "~" in rank_input:
                start, end = map(int, rank_input.replace("위", "").split("~"))
                df = df[df[column].between(start, end)]
            else:
                target_rank = int(rank_input.replace("위", ""))
                df = df[df[column] == target_rank]

        if df.empty:
            return "❌ 조건에 맞는 데이터가 없습니다."

        # ✅ 연도+항목 기준 분리 출력
        for y in sorted(df["연도"].unique()):
            st.markdown(f"### 📅 {y}년 {product}")
            st.dataframe(df[df["연도"] == y][["연도", "주관사", column]].reset_index(drop=True))

        return "✅ 조건에 맞는 결과를 위에 표시했어요."

    except Exception as e:
        return f"❌ 오류가 발생했어요: {str(e)}"

# ✅ 입력
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 생성 중입니다..."):
        keywords = [kw.strip() for kw in query.split(",")]
        if len(keywords) == 5:
            response = process_keywords_advanced(keywords, dfs)
            st.markdown(response)
        else:
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 쉼표로 구분된 5개 항목을 입력해주세요.")
