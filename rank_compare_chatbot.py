import streamlit as st

st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import pandas as pd
import openai
from dotenv import load_dotenv
from utils import load_dataframes, plot_bar_chart_plotly

# ✅ 환경 설정
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ 데이터 불러오기
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ 보정 딕셔너리
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

# ✅ GPT 파서 함수
def parse_query_with_gpt(query):
    try:
        system_prompt = (
            "사용자의 질문을 다음 항목으로 분석해서 JSON 형태로 정리해줘:\\n"
            "- years: [2023, 2024] 형태\\n"
            "- product: ECM, ABS, FB, 국내채권 중 하나 (명시 없으면 문맥상 추정)\\n"
            "- columns: 금액, 건수, 점유율 중 하나 이상\\n"
            "- company: 증권사 이름 있을 경우 전체 명칭으로\\n"
            "- is_compare: '비교', '오른', '하락' 포함 여부\\n"
            "- top_n: '상위 5위' 등 있으면 숫자\\n"
            "- rank_range: [1, 3] 형태\\n"
            "- is_chart: 그래프 여부"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
        return eval(response["choices"][0]["message"]["content"])
    except Exception as e:
        st.error(f"❌ 질문 파싱 오류: {e}")
        return None

# ✅ 순위 비교 함수
def compare_rank(df, year1, year2, col):
    df1 = df[df["연도"] == year1].copy()
    df2 = df[df["연도"] == year2].copy()
    df1["순위1"] = df1[col].rank(ascending=False, method="min")
    df2["순위2"] = df2[col].rank(ascending=False, method="min")
    merged = pd.merge(df1[["주관사", "순위1"]], df2[["주관사", "순위2"]], on="주관사")
    merged["순위변화"] = merged["순위1"] - merged["순위2"]
    상승 = merged[merged["순위변화"] > 0].sort_values("순위변화", ascending=False)
    하락 = merged[merged["순위변화"] < 0].sort_values("순위변화")
    return 상승, 하락

# ✅ UI
st.title("🔔 더벨 리그테이블 챗봇")
with st.form(key="form"):
    query = st.text_input("질문을 입력하세요:")
    submit = st.form_submit_button("🔍 질문하기")

# ✅ 질문 처리
if submit and query:
    parsed = parse_query_with_gpt(query)

    if not parsed or "product" not in parsed or "years" not in parsed:
        st.error("❌ 질문을 이해하지 못했어요. ECM/ABS/FB/국내채권 등의 부문과 연도를 포함해 주세요.")
    else:
        product = parsed["product"]
        years = parsed["years"]
        columns = parsed.get("columns", ["금액"])
        df = dfs.get(product)

        if df is None or df.empty:
            st.warning(f"{product} 데이터가 없습니다.")
        else:
            for y in years:
                df_year = df[df["연도"] == y].copy()
                if df_year.empty:
                    st.warning(f"{y}년 데이터가 없습니다.")
                    continue

                for col in columns:
                    colname = column_aliases.get(col, col)
                    if colname == "금액(원)":
                        df_year["금액(억원)"] = df_year[colname] / 1e8
                        colname = "금액(억원)"
                    df_year["순위"] = df_year[colname].rank(ascending=False, method="min")

                    if parsed.get("top_n"):
                        result = df_year.nsmallest(parsed["top_n"], "순위")[["순위", "주관사", colname]]
                        st.subheader(f"{y}년 {product} {col} 기준 상위 {parsed['top_n']}개사")
                        st.dataframe(result.reset_index(drop=True))
                        if parsed.get("is_chart"):
                            plot_bar_chart_plotly(result, "주관사", [colname])

                    elif parsed.get("company"):
                        name = parsed["company"]
                        std_name = company_aliases.get(name, name)
                        result = df_year[df_year["주관사"] == std_name][["순위", "주관사", colname]]
                        st.subheader(f"{y}년 {product} {std_name} 순위")
                        st.dataframe(result.reset_index(drop=True))

                    else:
                        result = df_year[["순위", "주관사", colname]]
                        st.subheader(f"{y}년 {product} 전체 순위표 ({col})")
                        st.dataframe(result.reset_index(drop=True))

            # ✅ 연도 비교 질문 처리
            if parsed.get("is_compare") and len(years) == 2:
                y1, y2 = years
                col = column_aliases.get(columns[0], columns[0])
                if col == "금액(원)":
                    df["금액(억원)"] = df["금액(원)"] / 1e8
                    col = "금액(억원)"
                상승, 하락 = compare_rank(df, y1, y2, col)
                st.subheader(f"📈 {y1} → {y2} 순위 상승")
                st.dataframe(상승.reset_index(drop=True))
                st.subheader(f"📉 {y1} → {y2} 순위 하락")
                st.dataframe(하락.reset_index(drop=True))
