import os
import streamlit as st
import pandas as pd
import openai
from utils import load_dataframes
import re
from dotenv import load_dotenv  # .env 파일 로드

# ✅ .env 파일 로드
load_dotenv()

# ✅ Streamlit Cloud에 등록된 Secrets에서 키 가져오기
openai.api_key = os.getenv("OPENAI_API_KEY")

# 챗봇 제목
st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="📊")
st.title("📊 더벨 리그테이블 챗봇")

# 챗봇 소개
st.markdown("""
이 챗봇은 더벨의 ECM, ABS, FB, 국내채권 대표주관 리그테이블 데이터를 기반으로
질문에 답하거나 연도별 비교를 도와줍니다.
키워드 기반 질문으로 연도, 데이터 종류, 항목, 증권사, 순위를 쉽게 확인할 수 있습니다.
""")

# 예시 질문
st.markdown("""
#### 💬 예시 질문
- `2024, ABS, 대표주관, 미래에셋, 순위`  
  → 2024년 미래에셋증권의 ABS 대표주관사 순위는 없습니다.
- `2020, ECM, 대표주관, KB증권, 순위`  
  → 2020년 ECM의 대표주관사 순위는 KB증권입니다.
- `2020, ABS, 대표주관, 삼성증권, 순위`  
  → 2020년 ABS의 대표주관사 순위는 삼성증권입니다.
""")

# 질문 팁
st.markdown("""
#### ⚠️ 질문 팁
**⛔ 아래와 같은 질문은 실패할 수 있어요!**
- 여러 큰 단위 조건을 한 문장에 다 넣으면 문장이 복잡해져서 잘 안 돼요.

예: `2020~2024 ECM과 ABS 모든 연도와 상품별로 증권사 순위 알려줘`
""")

# 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# 키워드 기반 처리 함수
def process_keywords(keywords, dfs):
    year = int(keywords[0])  # 연도 추출
    product = keywords[1]    # 데이터 종류 추출
    column = keywords[2]     # 항목 추출
    company = keywords[3]    # 증권사 추출
    rank = keywords[4]       # 순위 요청

    # 데이터 로드
    df = dfs.get(product)
    if df is None:
        return f"❌ '{product}' 데이터가 없어요."

    df_year = df[df["연도"] == year]  # 해당 연도의 데이터만 필터링
    if df_year.empty:
        return f"❌ {year}년 데이터가 없어요."

    # 해당 증권사의 데이터만 필터링
    df_company = df_year[df_year["주관사"] == company]
    if df_company.empty:
        return f"❌ {company}의 데이터가 없어요."
    
    # 실제 컬럼명 확인
    if column not in df.columns:
        return f"❌ '{column}'이라는 항목은 없습니다. 데이터 컬럼을 확인해주세요."

    # 원하는 항목의 순위 제공
    result = df_company[column].values[0]
    return f"📌 {year}년 {company}의 {column} 순위는 {result}입니다."

# 질의 입력
query = st.text_input("질문을 입력하세요:")

if query:
    with st.spinner("답변을 생성 중입니다..."):
        # 키워드 추출
        keywords = query.split(",")  # 쉼표로 키워드를 구분
        keywords = [kw.strip() for kw in keywords]  # 공백 제거

        if len(keywords) == 5:
            response = process_keywords(keywords, dfs)
            st.markdown(response)
        else:
            st.markdown("❌ 잘못된 형식입니다. 예시처럼 키워드를 쉼표로 구분하여 입력해주세요.")
