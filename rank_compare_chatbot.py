import streamlit as st

# ✅ 반드시 첫 줄에 있어야 함
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="📊")

import os
import pandas as pd
import openai
import re
from utils import load_dataframes
from dotenv import load_dotenv

# ✅ 환경변수 로딩 (.env에서 OpenAI 키 가져오기)
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

# ✅ 설명 UI
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

# ✅ 질문 처리 함수
def process_keywords(keywords, dfs):
    try:
        year_kw = keywords[0].strip()
        product = keywords[1].strip().upper()
        column = keywords[2].strip()
        company_kw = keywords[3].strip()
        rank_kw = keywords[4].strip()

        # ✅ 허용 컬럼 정의
        allowed_columns = {
            "ECM": ["대표주관", "금액(원)", "건수", "점유율(%)"],
            "ABS": ["대표주관", "금액(원)", "건수", "점유율(%)"],
            "FB": ["대표주관", "금액(원)", "건수", "점유율(%)"],
            "국내채권": ["대표주관", "금액(원)", "건수", "점유율(%)"]
        }

        # 연도 처리
        if "~" in year_kw:
            start, end = map(int, year_kw.split("~"))
            years = list(range(start, end + 1))
        else:
            years = [int(year_kw)]

        # 증권사 처리
        companies = []
        if company_kw:
            for raw in re.split(r"[\/,"]", company_kw):
                raw = raw.strip()
                if raw:
                    companies.append(company_aliases.get(raw, raw))

        # 순위 처리
        if "~" in rank_kw:
            rank_start, rank_end = map(int, re.findall(r"\d+", rank_kw))
            rank_range = list(range(rank_start, rank_end + 1))
        else:
            rank_range = [int(r) for r in re.findall(r"\d+", rank_kw)]

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        if column not in allowed_columns.get(product, []):
            return f"❌ '{product}'에서는 '{column}' 항목으로 필터할 수 없습니다.\n" \
                   f"가능한 항목: {', '.join(allowed_columns.get(product, []))}"

        result_rows = []

        for year in years:
            df_year = df[df["연도"] == year]
            if df_year.empty:
                continue

            df_filtered = df_year[df_year[column].isin(rank_range)]

            # 🔥 증권사 필터 강화
            if companies:
                company_patterns = [c.replace(" ", "").lower() for c in companies]
                df_filtered["주관사_정제"] = df_filtered["주관사"].astype(str).str.replace(" ", "").str.lower()
                df_filtered = df_filtered[df_filtered["주관사_정제"].apply(
                    lambda x: any(pattern in x for pattern in company_patterns)
                )]

            if not df_filtered.empty:
                df_show = df_filtered[["연도", "주관사", column]].rename(columns={column: "순위"})
                result_rows.append((year, product, df_show))

        if not result_rows:
            return "❌ 조건에 맞는 결과가 없습니다."

        # 📌 출력
        for (year, product, group_df) in result_rows:
            st.markdown(f"### 📌 {year}년 {product} 리그테이블")
            st.dataframe(group_df.reset_index(drop=True))

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
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 쉼표로 구분된 5개 항목을 입력해주세요.")

# ✅ ECM 컬럼 구조 디버깅용
st.markdown("## 🔍 ECM 데이터 점검")
ecm_df = dfs.get("ECM")
if ecm_df is not None:
    st.write("✅ ECM 컬럼명:", ecm_df.columns.tolist())
    st.write("✅ ECM 2020년 데이터 샘플:")
    st.dataframe(ecm_df[ecm_df["연도"] == 2020].head(10))
