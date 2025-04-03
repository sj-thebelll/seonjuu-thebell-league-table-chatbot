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
자연어로 질문하고, 표 형태로 응답을 받는 챗봇입니다.

예: `2023년, 2024년 비교해서 국내채권 대표주관사 중 순위 오른 증권사 알려줘.`
""")

# ✅ 자연어 질문 처리 함수

def compare_rank_change(df, year1, year2, product):
    df1 = df[(df["연도"] == year1)].copy()
    df2 = df[(df["연도"] == year2)].copy()

    df1["순위"] = df1["대표주관"]
    df2["순위"] = df2["대표주관"]

    df1 = df1[["주관사", "순위"]].rename(columns={"순위": f"{year1} 순위"})
    df2 = df2[["주관사", "순위"]].rename(columns={"순위": f"{year2} 순위"})

    merged = pd.merge(df1, df2, on="주관사")
    merged["변화"] = merged[f"{year1} 순위"] - merged[f"{year2} 순위"]
    merged = merged[merged["변화"] > 0]
    merged = merged.sort_values("변화", ascending=False)

    if merged.empty:
        st.markdown(f"📉 {year1}년 → {year2}년 동안 순위가 상승한 증권사가 없습니다.")
    else:
        st.markdown(f"### ✅ {year1}년 대비 {year2}년 순위가 상승한 증권사")
        st.dataframe(merged.reset_index(drop=True))

# ✅ 입력
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 분석 중입니다..."):
        try:
            pattern = re.search(r"(\d{4})년[과, ]*(\d{4})년.*(ECM|ABS|FB|국내채권).*순위.*오른", query)
            if pattern:
                y1, y2, product = int(pattern.group(1)), int(pattern.group(2)), pattern.group(3).upper()
                df = dfs.get(product)
                if df is not None:
                    compare_rank_change(df, y1, y2, product)
                else:
                    st.markdown(f"❌ '{product}' 데이터가 없습니다.")
            else:
                st.markdown("❌ 아직 이 질문은 이해하지 못해요. 예: `2023년, 2024년 비교해서 국내채권 대표주관사 중 순위 오른 증권사 알려줘.`")
        except Exception as e:
            st.error(f"오류 발생: {e}")
