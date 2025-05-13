import streamlit as st

st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from utils import load_dataframes, plot_bar_chart_plotly
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한국 폰트 설정
def set_korean_font():
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        fontprop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = fontprop.get_name()
    else:
        plt.rcParams['font.family'] = 'sans-serif'
        st.warning("⚠️ 'NanumGothic.ttf' 폰트 파일이 없어 한글이 깨질 수 있습니다.")
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# 환경 변수 및 GPT 클라이언트 설정
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# GPT 질문 파싱 함수
def parse_natural_query_with_gpt(query):
    try:
        system_prompt = (
            '사용자의 질문을 다음 항목으로 분석해서 반드시 올바른 JSON 형식으로 응답해줘. '
            'true/false/null은 반드시 소문자 그대로 사용하고, 문자열은 큰따옴표(\"\")로 감싸줘. '
            '- years: [2023, 2024] 같은 리스트 형태\n'
            '- product: ECM, ABS, FB, 국내채권 중 하나 (질문에 명시가 없어도 문맥으로 유추해서 채워줘)\n'
            '- columns: 금액, 건수, 점유율 중 하나 이상\n'
            '- company: 증권사명 (선택적)\n'
            '- top_n: 숫자 (선택적)\n'
            '- rank_range: [시작위, 끝위] (선택적)\n'
            '- is_chart: true/false\n'
            '- is_compare: true/false'
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"❌ GPT 파서 오류: {e}")
        return None

# 순위 비교 함수
def compare_rank(df, year1, year2):
    df1 = df[df["연도"] == year1].copy()
    df2 = df[df["연도"] == year2].copy()
    df1["순위1"] = df1["순위"]
    df2["순위2"] = df2["순위"]
    merged = pd.merge(df1[["주관사", "순위1"]], df2[["주관사", "순위2"]], on="주관사")
    merged["순위변화"] = merged["순위1"] - merged["순위2"]
    상승 = merged[merged["순위변화"] > 0].sort_values("순위변화", ascending=False)
    하락 = merged[merged["순위변화"] < 0].sort_values("순위변화")
    return 상승, 하락

# 점유율 비교 함수
def compare_share(df, year1, year2):
    df1 = df[df["연도"] == year1][["주관사", "점유율(%)"]].copy()
    df2 = df[df["연도"] == year2][["주관사", "점유율(%)"]].copy()
    merged = pd.merge(df1, df2, on="주관사", suffixes=(f"_{year1}", f"_{year2}"))
    merged["점유율변화"] = merged[f"점유율(%)_{year2}"] - merged[f"점유율(%)_{year1}"]
    상승 = merged[merged["점유율변화"] > 0].sort_values("점유율변화", ascending=False)
    하락 = merged[merged["점유율변화"] < 0].sort_values("점유율변화")
    return 상승, 하락

# UI
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ECM / ABS / FB / 국내채권 부문 대표주관 리그테이블 데이터를 기반으로  
자연어로 질문하고, 표 형태로 응답을 받는 챗봇입니다.

#### 💬 예시 질문
- 2024년 ECM 대표주관 순위 1~10위 알려줘.
- 2020~2024년 ABS 대표주관 상위 3개사 보여줘.
- 2022년에 비해 2023년 국내채권 주관 점유율이 오른 증권사는?
- 2023년 현대차증권이 랭크된 순위 전부 알려줘.
""")

with st.form(key="question_form"):
    query = st.text_input("질문을 입력하세요:")
    submit = st.form_submit_button("🔍 질문하기")

if submit and query:
    with st.spinner("GPT가 질문을 해석 중입니다..."):
        parsed = parse_natural_query_with_gpt(query)

    if not parsed:
        st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")

    # ✅ 특정 증권사의 전 product 순위 전부 요청한 경우
    elif parsed.get("company") and not parsed.get("product"):
        company = parsed["company"]
        years = parsed.get("years", [])
        for product, df in dfs.items():
            df.columns = df.columns.str.strip()
            for y in years:
                df_year = df[df["연도"] == y]
                row = df_year[df_year["주관사"] == company]
                if not row.empty:
                    st.subheader(f"🏅 {y}년 {product} {company} 순위 및 실적")
                    st.dataframe(row[["순위", "주관사", "금액(원)", "건수", "점유율(%)"]].reset_index(drop=True))

    else:
        df = dfs.get(parsed["product"])
        if df is None or df.empty:
            st.warning(f"⚠️ {parsed['product']} 데이터가 없습니다.")
        else:
            df.columns = df.columns.str.strip()
            col_map = {"금액": "금액(원)", "건수": "건수", "점유율": "점유율(%)"}

            if parsed.get("is_compare") and len(parsed["years"]) == 2 and any("점유율" in col for col in parsed.get("columns", [])):
                y1, y2 = parsed["years"]
                상승, 하락 = compare_share(df, y1, y2)
                st.subheader(f"📈 {y1} → {y2} 점유율 상승")
                st.dataframe(상승.reset_index(drop=True))
                st.subheader(f"📉 {y1} → {y2} 점유율 하락")
                st.dataframe(하락.reset_index(drop=True))

            elif parsed.get("is_compare") and len(parsed["years"]) == 2:
                y1, y2 = parsed["years"]
                상승, 하락 = compare_rank(df, y1, y2)
                st.subheader(f"📈 {y1} → {y2} 순위 상승")
                st.dataframe(상승.reset_index(drop=True))
                st.subheader(f"📉 {y1} → {y2} 순위 하락")
                st.dataframe(하락.reset_index(drop=True))

            else:
                for y in parsed["years"]:
                    df_year = df[df["연도"] == y].copy()
                    if df_year.empty:
                        st.warning(f"⚠️ {y}년 데이터가 없습니다.")
                        continue

                    if parsed.get("company"):
                        row = df_year[df_year["주관사"] == parsed["company"]]
                        if not row.empty:
                            st.subheader(f"🏅 {y}년 {parsed['product']} {parsed['company']} 순위 및 실적")
                            st.dataframe(row[["순위", "주관사", "금액(원)", "건수", "점유율(%)"]].reset_index(drop=True))
                        else:
                            st.warning(f"{y}년 데이터에서 {parsed['company']} 찾을 수 없습니다.")
                        continue

                    start, end = 1, 9999
                    if parsed.get("rank_range"):
                        start, end = parsed["rank_range"]
                    elif parsed.get("top_n"):
                        end = parsed["top_n"]

                    cols = ["순위", "주관사", "금액(원)", "건수", "점유율(%)"]
                    result = df_year[df_year["순위"].between(start, end)][cols]
                    st.subheader(f"📌 {y}년 {parsed['product']} 기준 [{start}, {end}]위 범위 (엑셀 순위 기준)")
                    st.dataframe(result.sort_values("순위").reset_index(drop=True))
