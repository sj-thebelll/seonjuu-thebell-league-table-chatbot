import streamlit as st
import pandas as pd
import openai
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from utils import load_dataframes, plot_bar_chart_plotly

# ✅ 환경 변수 로드 및 API 키 설정
load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ✅ 데이터 로드 (실제 데이터 사용)
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ GPT 기반 질문 파싱 함수
def parse_natural_query_with_gpt(query):
    gpt_prompt = f'''
    다음 질문을 JSON 형식으로 구조화해줘.
    - years: [2023, 2024] 같은 숫자 리스트 (없으면 생략 가능)
    - product: ECM, ABS, FB, 국내채권 중 하나
    - company: 증권사 이름 (없으면 생략 가능)
    - columns: 금액, 건수, 점유율 중 포함된 항목 리스트
    - is_chart: true 또는 false
    - is_top, is_compare, rank_range, top_n 등 추가 정보 포함 가능

    질문: {query}
    JSON만 줘. 설명은 하지 마.
    '''

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "너는 금융 리그테이블 질문을 분석하는 파서야."},
                {"role": "user", "content": gpt_prompt}
            ]
        )
        return json.loads(completion.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"GPT 파싱 실패: {e}")
        return None

# ✅ 기존 정규표현식 기반 파서 (백업용)
def parse_natural_query_backup(query):
    query = query.strip()
    years = list(map(int, re.findall(r"\d{4}", query)))
    product = None
    for key in ["ECM", "ABS", "FB", "국내채권"]:
        if key in query:
            product = key
            break
    company = None
    for keyword in ["증권", "투자", "신한", "삼성", "KB", "NH", "미래에셋", "대신", "하나"]:
        if keyword in query:
            company = keyword + "증권"
            break
    columns = []
    for col in ["금액", "건수", "점유율"]:
        if col in query:
            columns.append(col)
    return {
        "years": years,
        "product": product,
        "company": company,
        "columns": columns or ["금액"]
    }

# ✅ Streamlit UI
st.set_page_config(page_title="더벨 리그테이블 GPT 챗봇", page_icon="🔔")
st.title("🔔 GPT + Pandas 기반 리그테이블 챗봇")
st.markdown("""
자연어 질문을 입력하면 OpenAI가 질문을 해석하고,
Pandas가 데이터를 분석해 표로 결과를 보여줍니다.
""")

query = st.text_input("질문을 입력하세요:", placeholder="예: 2024년 ECM에서 대신증권 순위 알려줘")
submit = st.button("질문하기")

if submit and query:
    parsed = parse_natural_query_with_gpt(query) or parse_natural_query_backup(query)
    if parsed:
        st.subheader("🧠 파싱 결과")
        st.json(parsed)

        # 기본 조건 추출
        years = parsed.get("years", [])
        product = parsed.get("product")
        company = parsed.get("company")
        columns = parsed.get("columns", ["금액"])

        df = dfs.get(product)
        if df is None or df.empty:
            st.warning(f"❌ '{product}' 데이터가 없습니다.")
        elif not years:
            st.warning("❗ 연도가 지정되지 않았습니다.")
        else:
            for year in years:
                df_year = df[df["연도"] == year]
                if company:
                    df_year = df_year[df_year["주관사"].str.contains(company)]
                if df_year.empty:
                    st.warning(f"{year}년 데이터가 없습니다.")
                    continue

                for col in columns:
                    show_col = col if col in df_year.columns else None
                    if not show_col:
                        st.warning(f"⚠️ '{col}' 컬럼을 찾을 수 없습니다.")
                        continue

                    result = df_year[["순위", "주관사", show_col]]
                    st.subheader(f"📊 {year}년 {product} - {col} 기준")
                    st.dataframe(result.reset_index(drop=True))
    else:
        st.warning("질문을 해석하지 못했습니다. 다시 시도해 주세요.")
