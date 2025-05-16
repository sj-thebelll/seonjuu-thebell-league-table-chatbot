import streamlit as st

st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from utils import load_dataframes, plot_bar_chart_plotly, plot_line_chart_plotly
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ✅ 한글 폰트 수동 설정
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

# ✅ 환경 설정
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ GPT 파서
def parse_natural_query_with_gpt(query):
    try:
        system_prompt = (
            '사용자의 질문을 다음 항목으로 분석해서 반드시 올바른 JSON 형식으로 응답해줘. '
            'true/false/null은 반드시 소문자 그대로 사용하고, 문자열은 큰따옴표("")로 감싸줘. '
            '- years: [2023, 2024] 형태\n'
            '- product: ECM, ABS, FB, 국내채권 중 하나 또는 여러 개 (문맥 유추 가능)\n'
            '- columns: 금액, 건수, 점유율 중 하나 이상\n'
            '- company: 증권사명 (한 개 또는 여러 개 리스트 가능)\n'
            '- top_n: 숫자 (선택적)\n'
            '- rank_range: [시작위, 끝위] (선택적)\n'
            '- is_chart: true/false\n'
            '- is_compare: true/false\n'
            '- 특정 증권사만 있을 경우 product 없이도 전체 product 순회해줘\n'
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

# ✅ 비교 함수
def compare_rank(df, year1, year2):
    df1 = df[df["연도"] == year1].copy()
    df2 = df[df["연도"] == year2].copy()
    df1[f"{year1}년 순위"] = df1["순위"]
    df2[f"{year2}년 순위"] = df2["순위"]
    merged = pd.merge(df1[["주관사", f"{year1}년 순위"]], df2[["주관사", f"{year2}년 순위"]], on="주관사")
    merged["순위변화"] = merged[f"{year1}년 순위"] - merged[f"{year2}년 순위"]

    상승 = merged[merged["순위변화"] > 0].sort_values("순위변화", ascending=False)
    하락 = merged[merged["순위변화"] < 0].sort_values("순위변화")
    return 상승, 하락

def compare_share(df, year1, year2):
    df1 = df[df["연도"] == year1][["주관사", "점유율(%)"]].copy()
    df2 = df[df["연도"] == year2][["주관사", "점유율(%)"]].copy()
    merged = pd.merge(df1, df2, on="주관사", suffixes=(f"_{year1}", f"_{year2}"))
    merged["점유율변화"] = merged[f"점유율(%)_{year2}"] - merged[f"점유율(%)_{year1}"]
    상승 = merged[merged["점유율변화"] > 0].sort_values("점유율변화", ascending=False)
    하락 = merged[merged["점유율변화"] < 0].sort_values("점유율변화")
    return 상승, 하락

# ✅ UI
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ECM / ABS / FB / 국내채권 부문 대표주관 리그테이블 데이터를 기반으로  
자연어로 질문하고, 표 형태로 응답을 받는 챗봇입니다.

#### 💬 예시 질문
- 2024년 ECM 대표주관 순위 1~10위 알려줘.
- 2020~2024년 ABS 대표주관 상위 3개사 보여줘.
- 2022년에 비해 2023년 국내채권 주관 점유율이 오른 증권사는?
- 신영증권의 2022~2024년 ECM 순위 그래프 보여줘.
- 2023년 현대차증권이 랭크된 순위 전부 알려줘.
- NH투자증권과 KB증권의 2023년 ECM 순위 비교해줘.
""")

with st.form(key="question_form"):
    query = st.text_input("질문을 입력하세요:")
    submit = st.form_submit_button("🔍 질문하기")

if submit and query:
    handled = False
    with st.spinner("GPT가 질문을 해석 중입니다..."):
        parsed = parse_natural_query_with_gpt(query)

    if not parsed:
        st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")
        handled = True

    elif parsed.get("company") and not parsed.get("product"):
        from improved_company_year_chart_logic import handle_company_year_chart_logic
        handle_company_year_chart_logic(parsed, dfs)

    # ✅ 나머지 일반 루틴 처리
    products = parsed.get("product")
    if isinstance(products, str):
        products = [products]

    companies = parsed.get("company") or []
    if isinstance(companies, str):  # 문자열이면 리스트로 변환
       companies = [companies]

    years = parsed.get("years") or []

    for product in products:
        df = dfs.get(product)
        if df is None or df.empty:
            st.warning(f"⚠️ {product} 데이터가 없습니다.")
            continue

        df.columns = df.columns.str.strip()

        for y in years:
            # ✅ 꺾은선 그래프 요청 시, 이 루틴은 생략
            if parsed.get("is_chart"):
                continue

            df_year = df[df["연도"] == y]
            if df_year.empty:
                st.warning(f"⚠️ {y}년 데이터가 없습니다.")
                continue

            if companies:
                row = df_year[df_year["주관사"].isin(companies)]
                if not row.empty:
                    st.subheader(f"🏅 {y}년 {product} 순위 및 실적")
                    st.dataframe(row[["순위", "주관사", "금액(원)", "건수", "점유율(%)"]].reset_index(drop=True))
                else:
                    st.warning(f"⚠️ {y}년 데이터에서 {', '.join(companies)} 찾을 수 없습니다.")

    if not handled and parsed.get("product"):
        products = parsed["product"]
        if isinstance(products, str):
            products = [products]

        companies = parsed.get("company") or []
        if isinstance(companies, str):
            companies = [companies]

        years = parsed.get("years") or []

        for product in products:
            df = dfs.get(product)
            if df is None or df.empty:
                st.warning(f"⚠️ {product} 데이터가 없습니다.")
                continue

            df.columns = df.columns.str.strip()

            if parsed.get("is_compare") and len(years) == 2:
                y1, y2 = years
                상승, 하락 = compare_rank(df, y1, y2)

                if companies:
                    상승 = 상승[상승["주관사"].isin(companies)]
                    하락 = 하락[하락["주관사"].isin(companies)]

                    # ✅ 누락된 증권사 경고 추가
                    missing_companies = [c for c in companies if c not in 상승["주관사"].values and c not in 하락["주관사"].values]
                    if missing_companies:
                        st.warning(f"⚠️ {', '.join(missing_companies)}의 {y1}년 또는 {y2}년 순위 데이터가 없습니다.")

                if not 상승.empty:
                    상승 = 상승[["주관사", f"{y1}년 순위", f"{y2}년 순위", "순위변화"]]
                    st.subheader(f"📈 {y1} → {y2} 순위 상승 (대상: {', '.join(companies)})")
                    st.dataframe(상승.reset_index(drop=True))

                if not 하락.empty:
                    하락 = 하락[["주관사", f"{y1}년 순위", f"{y2}년 순위", "순위변화"]]
                    st.subheader(f"📉 {y1} → {y2} 순위 하락 (대상: {', '.join(companies)})")
                    st.dataframe(하락.reset_index(drop=True))

            # ✅ 연도별 단일 주관사 실적 비교 요약 + 꺾은선 그래프 출력
            if parsed.get("is_chart") and companies and len(years) >= 1:
                chart_df = df[df["연도"].isin(years) & df["주관사"].isin(companies)]
                if not chart_df.empty:
                    chart_df = chart_df.sort_values(["주관사", "연도"])
                    chart_df["연도"] = chart_df["연도"].astype(int)

                    # ✅ 간단 요약 텍스트 출력
                    st.markdown("### ✅ 연도별 ECM 실적 비교 요약")
                    for c in companies:
                        rows = chart_df[chart_df["주관사"] == c]
                        summary = [f"{r['연도']}년: {r['금액(원)']:,}원 ({r['점유율(%)']}%)" for _, r in rows.iterrows()]
                        st.markdown(f"- **{c}** → " + ", ".join(summary))

                    # ✅ 꺾은선 그래프 (금액, 점유율 등 y_col 여러개)
                    if len(companies) == 1:
                        from utils import plot_multi_metric_line_chart_for_single_company
                        plot_multi_metric_line_chart_for_single_company(
                            chart_df,
                            company_name=companies[0],
                            x_col="연도",
                            y_cols=["금액(원)", "점유율(%)"]
                        )
                    else:
                        st.info("⚠️ 여러 기업의 꺾은선 그래프 비교 기능은 현재 미지원입니다. 단일 기업으로 질문해 주세요.")

