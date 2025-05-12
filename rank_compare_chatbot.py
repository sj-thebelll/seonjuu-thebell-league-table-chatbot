
import streamlit as st

# ✅ 첫 줄에 위치해야 함
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from utils import load_dataframes, plot_bar_chart_plotly
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform

# ✅ 한글 폰트 수동 설정 함수 (업로드한 NanumGothic.ttf 사용)
def set_korean_font():
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        fontprop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = fontprop.get_name()
    else:
        plt.rcParams['font.family'] = 'sans-serif'
        st.warning("⚠️ 'NanumGothic.ttf' 폰트 파일이 없어 한글이 깨질 수 있습니다.")
    plt.rcParams['axes.unicode_minus'] = False

# ✅ 환경 변수 및 API 키
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ GPT 기반 자연어 파싱
def parse_natural_query_with_gpt(query):
    try:
        system_prompt = (
            "사용자의 질문을 다음 항목으로 분석해서 JSON 형태로 정리해줘:\n"
            "- years: [연도]\n- product: ECM, ABS, FB, 국내채권 중 택1\n"
            "- company: 특정 증권사 있을 경우\n"
            "- columns: 금액, 건수, 점유율 중 하나 이상\n"
            "- top_n: 상위 몇 위인지 (선택적)\n"
            "- rank_range: [시작위~끝위] (선택적)\n"
            "- is_chart: 그래프 포함 여부 (boolean)\n"
            "- is_compare: 연도 간 비교인지 여부 (boolean)"
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
        content = response.choices[0].message.content
        return eval(content)
    except Exception as e:
        st.error(f"❌ GPT 파서 오류: {e}")
        return None

# ✅ UI 안내 텍스트
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ECM / ABS / FB / 국내채권 부문 대표주관 리그테이블 데이터를 기반으로  
자연어로 질문하고, 표 형태로 응답을 받는 챗봇입니다.

#### 💬 예시 질문
- 2024년 ECM 대표주관사 순위 알려줘.
- 2020~2024년 ABS 대표주관 상위 3개사 보여줘.
- 2022년 FB 대표주관 1위는 어디야?
- 2023년 ECM 금액과 건수 기준 순위를 그래프로 보여줘. 
""")

# ✅ 입력창
with st.form(key="question_form"):
    query = st.text_input("질문을 입력하세요:")
    submit = st.form_submit_button("🔍 질문하기")

st.markdown("""
<style>
button[kind="formSubmit"] {
    background-color: #ff4b4b;
    color: white;
    border-radius: 10px;
    padding: 0.5em 1.5em;
    font-size: 1.1em;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ✅ 질문 처리
if submit and query:
    with st.spinner("GPT가 질문을 해석 중입니다..."):
        parsed = parse_natural_query_with_gpt(query)

    if not parsed or not parsed.get("product"):
        st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")
    else:
        df = dfs.get(parsed["product"])
        if df is None or df.empty:
            st.warning(f"⚠️ {parsed['product']} 데이터가 없습니다.")
        else:
            for y in parsed["years"]:
                df_year = df[df["연도"] == y]
                if df_year.empty:
                    st.warning(f"⚠️ {y}년 데이터가 없습니다.")
                    continue

                for col in parsed.get("columns", ["금액"]):
                    col_map = {
                        "금액": "금액(원)", "건수": "건수", "점유율": "점유율(%)"
                    }
                    colname = col_map.get(col, col)

                    df_year = df_year.copy()
                    df_year["순위"] = df_year[colname].rank(ascending=False, method="min")

                    if parsed.get("top_n"):
                        result = df_year.nsmallest(parsed["top_n"], "순위")[["순위", "주관사", colname]]
                        st.subheader(f"📌 {y}년 {parsed['product']} {col} 기준 상위 {parsed['top_n']}개사")
                        st.dataframe(result.reset_index(drop=True))
                        if parsed.get("is_chart"):
                            plot_bar_chart_plotly(result.sort_values(colname, ascending=False), "주관사", [colname])

                    elif parsed.get("rank_range"):
                        result = df_year[df_year["순위"].isin(parsed["rank_range"])][["순위", "주관사", colname]]
                        st.subheader(f"📌 {y}년 {parsed['product']} {col} 기준 {parsed['rank_range']}위 범위")
                        st.dataframe(result.reset_index(drop=True))
                        if parsed.get("is_chart"):
                            plot_bar_chart_plotly(result.sort_values(colname, ascending=False), "주관사", [colname])

                    elif parsed.get("company"):
                        result = df_year[df_year["주관사"] == parsed["company"]][["순위", "주관사", colname]]
                        if not result.empty:
                            st.subheader(f"🏅 {y}년 {parsed['product']}에서 {parsed['company']} {col} 순위")
                            st.dataframe(result.reset_index(drop=True))
                        else:
                            st.warning(f"{y}년 데이터에서 {parsed['company']} 찾을 수 없음.")

                    else:
                        result = df_year[["순위", "주관사", colname]]
                        st.subheader(f"📌 {y}년 {parsed['product']} {col} 기준 전체 리그테이블")
                        st.dataframe(result.reset_index(drop=True))
                        if parsed.get("is_chart"):
                            plot_bar_chart_plotly(result.sort_values(colname, ascending=False), "주관사", [colname])
