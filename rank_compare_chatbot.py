import streamlit as st
import pandas as pd
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from utils import load_dataframes, plot_bar_chart_plotly
from openai import OpenAI

# ✅ 환경 변수 로드 및 API 키 설정
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ GPT 기반 질문 파싱 함수
def parse_natural_query_with_gpt(query):
    gpt_prompt = f'''
    다음 질문을 JSON 형식으로 구조화해줘.
    - years: [2023, 2024] 형태로 추출
    - product: ECM, ABS, FB, 국내채권 중 하나
    - company: 증권사 이름
    - columns: 금액, 건수, 점유율 중 포함된 리스트
    - is_chart: true/false
    - is_top, is_compare, rank_range, top_n 등의 추가 정보 포함

    질문: {query}
    결과는 JSON만 줘.
    예시:
    {
      "years": [2023, 2024],
      "product": "ECM",
      "company": "미래에셋증권",
      "columns": ["금액(원)", "건수"],
      "top_n": 5,
      "rank_range": [1,5],
      "is_chart": true,
      "is_compare": false,
      "is_top": false
    }
    '''
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 금융 리그테이블 질문을 분석하는 파서야."},
                {"role": "user", "content": gpt_prompt}
            ]
        )
        result_text = response.choices[0].message.content.strip()
        if not result_text:
            st.error("GPT 응답이 비어있습니다.")
            return None
        try:
            return json.loads(result_text)
        except json.decoder.JSONDecodeError:
            st.error(f"GPT 응답을 JSON으로 파싱할 수 없습니다:\n{result_text}")
            return None
    except Exception as e:
        st.error(f"GPT 파싱 실패: {e}")
        import traceback
        st.text(traceback.format_exc())
        return None

# ✅ 백업 파서
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

# ✅ UI
st.set_page_config(page_title="더벨 리그테이블 GPT 챗봇", page_icon="🔔")
st.title("🔔리그테이블 챗봇")
st.markdown("질문 예: 2024년 ECM에서 대신증권 순위 알려줘, 2023년 ABS 상위 5개사")

query = st.text_input("질문을 입력하세요:")
submit = st.button("질문하기")

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

if submit and query:
    parsed = parse_natural_query_with_gpt(query) or parse_natural_query_backup(query)
    if parsed:
        st.subheader("🧠 파싱 결과")
        if isinstance(parsed.get("rank_range"), str) and "~" in parsed["rank_range"]:
            try:
                r1, r2 = map(int, parsed["rank_range"].split("~"))
                parsed["rank_range"] = [r1, r2]
            except:
                parsed["rank_range"] = None
        st.json(parsed)

        years = parsed.get("years", [])
        product = parsed.get("product")
        company = parsed.get("company")
        columns = parsed.get("columns", ["금액(원)"])
        columns = [column_aliases.get(c, c) for c in columns]
        top_n = parsed.get("top_n")
        is_top = parsed.get("is_top")
        rank_range = parsed.get("rank_range")
        is_chart = parsed.get("is_chart")

        df = dfs.get(product)
        if df is None or df.empty:
            st.warning(f"❌ '{product}' 데이터가 없습니다.")
        elif not years:
            st.warning("❗ 연도가 지정되지 않았습니다.")
        else:
            for year in years:
                df_year = df[df["연도"] == year]
                if company:
                    for k, v in company_aliases.items():
                        if k in company:
                            company = v
                            break
                    df_year = df_year[df_year["주관사"].str.contains(company)]
                if df_year.empty:
                    st.warning(f"{year}년 데이터가 없습니다.")
                    continue

                for col in columns:
                    actual_col = column_aliases.get(col, col)
                    if actual_col not in allowed_columns.get(product, []):
                        st.warning(f"⚠️ '{actual_col}'은 {product}에서 지원되지 않는 항목입니다.")
                        continue
                    if actual_col not in df_year.columns:
                        st.warning(f"⚠️ '{col}' 컬럼을 찾을 수 없습니다.")
                        continue

                    rank_col = "순위" if "순위" in df_year.columns else "대표주관"
                    expected_cols = [rank_col, "주관사", actual_col]
                    if not all(c in df_year.columns for c in expected_cols):
                        st.warning(f"⚠️ 필요한 컬럼이 없습니다: {expected_cols}")
                        continue

                    result = df_year[expected_cols].sort_values(rank_col)

                    if rank_range:
                        if isinstance(rank_range, list) and len(rank_range) == 2:
                            r1, r2 = rank_range
                            result = result[(df_year[rank_col] >= r1) & (df_year[rank_col] <= r2)]
                        elif isinstance(rank_range, str) and "~" in rank_range:
                            try:
                                r1, r2 = map(int, rank_range.split("~"))
                                result = result[(df_year[rank_col] >= r1) & (df_year[rank_col] <= r2)]
                            except Exception as e:
                                st.warning(f"⚠️ rank_range 해석 실패: {rank_range} → {e}")
                    elif top_n:
                        result = result.head(top_n)
                    elif is_top:
                        result = result[result[rank_col] == 1]

                    st.subheader(f"📊 {year}년 {product} - {col} 기준")
                    st.dataframe(result.reset_index(drop=True))

                    if is_chart:
                        st.subheader("📈 그래프")
                        plot_bar_chart_plotly(result.sort_values(actual_col, ascending=False), "주관사", [actual_col])
    else:
        st.warning("GPT 또는 파서가 질문을 이해하지 못했습니다.")
