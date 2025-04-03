import streamlit as st

# ✅ 마지막에 들어와야 함
st.set_page_config(page_title="더벨 리그테이블 채드박스", page_icon="🔔")

import os
import pandas as pd
import openai
import re
from utils import load_dataframes
from dotenv import load_dotenv

# ✅ OpenAI 환경변수 로드
load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

# ✅ 데이터 로드하기
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ 증권사 명 복정
company_aliases = {
    "미래에셋": "미래에셋주관", "삼성": "삼성주관", "KB": "KB주관", "NH": "NH투자주관",
    "한투": "한국투자주관", "한국주관": "한국투자주관", "한화": "한화투자주관", "메리츠": "메리츠주관",
    "신한": "신한투자주관", "하나": "하나주관", "키울": "키울주관", "이베스트": "이베스트투자주관",
    "교복": "교복주관", "대신": "대신주관", "하이": "하이투자주관", "부국": "부국주관",
    "DB": "DB금융투자", "유안타": "유안타주관", "유진": "유진투자주관", "카이프": "카이프투자주관",
    "SK": "SK주관", "현대차": "현대차주관", "KTB": "KTB투자주관", "BNK": "BNK투자주관",
    "IBK": "IBK투자주관", "토스": "토스주관", "다옥": "다옥투자주관", "산은": "한국산업은회",
    "논협": "NH투자주관", "신금투": "신한투자주관"
}

# ✅ 항목명 복정 (괄호 없는 질문 → 실제 컬럼명)
column_aliases = {
    "금액": "금액(원)",
    "점유율": "점유율(%)"
}

# ✅ UI 설명
st.title("🔔 더벨 리그테이블 채드박스")
st.markdown("""
**질문 형식 예시 (쉼표로 구분된 5개 항목)**
- `2024, ABS 대표주관, 금액, KB증권, 순위`
- `2020~2022, ECM 대표주관, 점유율, 삼성/KB, 1~3위`
- `2023, 국내채권 대표주관, 건수, NH, 순위`

**항목은 반드시 아래 5개를 정확한 순서로 입력해주세요:**
> `[연도], [데이터 종류], [항목명], [증권사명], [순위 또는 범위]`
""")

# ✅ 핵심 질문 처리 함수
def process_keywords(keywords, dfs):
    try:
        year_kw, product_kw, column_kw, company_kw, rank_kw = [kw.strip() for kw in keywords]
        column = column_aliases.get(column_kw, column_kw)

        # 데이터 종류에서 product와 column 나누기
        product = product_kw.replace(" 대표주관", "")

        allowed_columns = ["금액(원)", "건수", "점유율(%)"]

        if column not in allowed_columns:
            return f"❌ '{product_kw}'에서는 '{column_kw}' 항목으로 필터할 수 없습니다. 가능한 항목: 금액, 건수, 점유율"

        # 연도 처리
        if "~" in year_kw:
            start, end = map(int, year_kw.split("~"))
            years = list(range(start, end + 1))
        else:
            years = [int(year_kw)]

        # 증권사 처리
        companies = []
        if company_kw:
            for raw in re.split(r"[\\/,]", company_kw):
                raw = raw.strip()
                if raw:
                    companies.append(company_aliases.get(raw, raw))

        # 순위 범위 처리
        if not re.search(r"\\d+", rank_kw) and company_kw:
            rank_range = None
        else:
            if "~" in rank_kw:
                rank_start, rank_end = map(int, re.findall(r"\\d+", rank_kw))
                rank_range = list(range(rank_start, rank_end + 1))
            else:
                rank_range = [int(r) for r in re.findall(r"\\d+", rank_kw)]

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        result_rows = []

        for year in years:
            df_year = df[df["연도"] == year]
            if df_year.empty:
                continue

            if rank_range:
                df_filtered = df_year[df_year["대표주관"].isin(rank_range)]
            else:
                df_filtered = df_year.copy()

            if companies:
                patterns = [c.replace(" ", "").lower() for c in companies]
                df_filtered["주관사_정제"] = df_filtered["주관사"].astype(str).str.replace(" ", "").str.lower()
                df_filtered = df_filtered[df_filtered["주관사_정제"].apply(lambda x: any(p in x for p in patterns))]

            if not df_filtered.empty:
                df_show = df_filtered[["연도", "주관사", column, "대표주관"]]
                df_show = df_show.rename(columns={column: column_kw, "대표주관": "순위"})
                result_rows.append((year, product_kw, df_show))

        if not result_rows:
            return "❌ 조건에 맞는 결과가 없습니다."

        for (year, product_kw, table) in result_rows:
            st.markdown(f"### 📌 {year}년 {product_kw} 리그테이블")
            st.dataframe(table.reset_index(drop=True))

        return ""

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"

# ✅ 질문 입력 UI
query = st.text_input("질문을 입력하세요:")
if query:
    with st.spinner("답변을 생성 중입니다..."):
        keywords = query.split(",")
        if len(keywords) == 5:
            msg = process_keywords(keywords, dfs)
            if msg:
                st.markdown(msg)
        else:
            st.markdown("❌ 잘못된 형식입니다. 쉼표로 구분된 5개 항목을 입력해주세요.")
