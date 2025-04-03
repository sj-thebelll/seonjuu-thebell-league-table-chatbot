import streamlit as st

# ✅ 반드시 첫 줄에 있어야 함
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import pandas as pd
import openai
import re
from utils import load_dataframes
from dotenv import load_dotenv

# ✅ 환경변수 로딩
load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

# ✅ 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ 증권사명 보정
company_aliases = {
    "미래에셋": "미래에셋증권", "삼성": "삼성증권", "KB": "KB증권", "NH": "NH투자증권",
    "한투": "한국투자증권", "한국증권": "한국투자증권", "한화": "한화투자증권", "메리츠": "메리츠증권",
    "신한": "신한투자증권", "하나": "하나증권", "키움": "키움증권", "이베스트": "이베스트투자증권",
    "교보": "교보증권", "대신": "대신증권", "하이": "하이투자증권", "부국": "부국증권",
    "DB": "DB금융투자", "유안타": "유안타증권", "유진": "유진투자증권", "케이프": "케이프투자증권",
    "SK": "SK증권", "현대차": "현대차증권", "KTB": "KTB투자증권", "BNK": "BNK투자증권",
    "IBK": "IBK투자증권", "토스": "토스증권", "다올": "다올투자증권", "산은": "한국산업은행",
    "농협": "NH투자증권", "신금투": "신한투자증권"
}

# ✅ 항목명 보정
column_aliases = {
    "금액": "금액(원)",
    "점유율": "점유율(%)"
}

# ✅ 설명 UI
st.title("🔔더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 국내채권/ABS/FB/ECM 대표주관 리그테이블 데이터를 기반으로  
질문에 답변합니다..

**질문은 반드시 아래 5개 항목을 정확한 순서로 쉼표(,)로 구분해서 입력해주세요.**

> ✅ 질문 형식 (항목 순서)
> ```
> [1] 연도 또는 연도 범위(예: 2024, 2020~2024)  
> [2] 데이터 종류 (ECM, ABS, FB, 국내채권 중 한가지 선택)  
> [3] 순위 또는 순위범위 (예: 순위, 1위, 1~5위)  
> [4] 증권사명 (예: KB, 삼성, 미래에셋 등 / 여러 개 가능)  
> [5] 항목명 (예: 금액, 건수, 점유율)
> ```

> ⛔ 항목의 순서가 바뀌거나 빠지면 질문이 작동하지 않습니다.
""")

st.markdown("""
#### 💬 예시 질문
- `2020, ECM, 순위, SK증권, 금액`  
- `2020, ABS, 순위, 미래에셋/KB, 건수`  
- `2021~2023, ECM, 순위, 신한, 점유율`  
- `2020~2022, ECM, 순위, 삼성/KB/미래에셋, 금액`  
- `2020~2024, ABS, 1~5위, , 점유율`
""")

st.markdown("""
#### ⚠️ 질문 팁
- ⛔ 아래와 같은 질문은 실패할 수 있어요!
  - 조건을 너무 복잡하게 넣거나 문장이 길면 안 돼요.
- ✅ 예시처럼 쉼표로 정확히 **5개 항목**을 **정해진 순서대로** 입력해주세요:
  - `연도(또는 범위), 상품종류, 순위 또는 순위범위, 증권사명(또는 여러개), 항목명`
""")

# ✅ 질문 처리 함수
def process_keywords(keywords, dfs):
    try:
        year_kw = keywords[0].strip()
        product_full = keywords[1].strip()
        rank_kw = keywords[2].strip()
        company_kw = keywords[3].strip()
        column_kw = keywords[4].strip()

        product_parts = product_full.split()
        product = product_parts[0].upper() if product_parts else ""
        column_kw = column_aliases.get(column_kw, column_kw)

        allowed_columns = {
            "ECM": ["금액(원)", "건수", "점유율(%)"],
            "ABS": ["금액(원)", "건수", "점유율(%)"],
            "FB": ["금액(원)", "건수", "점유율(%)"],
            "국내채권": ["금액(원)", "건수", "점유율(%)"]
        }

        if "~" in year_kw:
            start, end = map(int, year_kw.split("~"))
            years = list(range(start, end + 1))
        else:
            years = [int(year_kw)]

        companies = []
        if company_kw:
            for raw in re.split(r"[\\/,]", company_kw):
                raw = raw.strip()
                if raw:
                    companies.append(company_aliases.get(raw, raw))

        if not re.search(r"\d+", rank_kw) and company_kw:
            rank_range = None
        else:
            if "~" in rank_kw:
                rank_start, rank_end = map(int, re.findall(r"\d+", rank_kw))
                rank_range = list(range(rank_start, rank_end + 1))
            else:
                rank_range = [int(r) for r in re.findall(r"\d+", rank_kw)]

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        if column_kw not in allowed_columns.get(product, []):
            return f"❌ '{product}'에서는 '{column_kw}' 항목으로 필터할 수 없습니다.\n" \
                   f"가능한 항목: {', '.join(allowed_columns.get(product, []))}"

        result_rows = []

        for year in years:
            df_year = df[df["연도"] == year]
            if df_year.empty:
                continue

            df_year = df_year.copy()
            df_year["순위"] = df_year["대표주관"]

            if rank_range:
                df_year = df_year[df_year["순위"].isin(rank_range)]

            if companies:
                patterns = [c.replace(" ", "").lower() for c in companies]
                df_year["주관사_정제"] = df_year["주관사"].astype(str).str.replace(" ", "").str.lower()
                df_year = df_year[df_year["주관사_정제"].apply(
                    lambda x: any(p in x for p in patterns)
                )]

            if not df_year.empty:
                show_df = df_year[["연도", "주관사", "순위", column_kw]]
                result_rows.append((year, product_full, show_df))

        if not result_rows:
            return "❌ 조건에 맞는 결과가 없습니다."

        for (year, product_full, df_out) in result_rows:
            st.markdown(f"### 🔗 {year}년 {product_full} 리그테이블")
            st.dataframe(df_out.reset_index(drop=True))

        return ""

    except Exception as e:
        return f"❌ 오류가 발생했어요: {str(e)}"

# ✅ 질문 입력 처리
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 생성 중입니다..."):
        keywords = [kw.strip() for kw in query.split(",")]
        if len(keywords) == 5:
            response = process_keywords(keywords, dfs)
            if response:
                st.markdown(response)
        else:
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 쉼표로 구분된 5가지 항목을 입력해주세요.")
