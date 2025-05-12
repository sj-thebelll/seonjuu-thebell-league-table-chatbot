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
client = OpenAI()

# ✅ 데이터 로드
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ GPT 기반 질문 파싱 함수 (OpenAI 최신 버전 호환)
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
    {{
      "years": [2023, 2024],
      "product": "ECM",
      "company": "미래에셋증권",
      "columns": ["금액(원)", "건수"],
      "top_n": 5,
      "rank_range": [1,5],
      "is_chart": true,
      "is_compare": false,
      "is_top": false
    }}
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
        st.text("📤 GPT 응답:")
        st.code(result_text)
        try:
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            result_text = result_text[json_start:json_end]
            return json.loads(result_text)
        except json.decoder.JSONDecodeError:
            st.error(f"GPT 응답을 JSON으로 파싱할 수 없습니다:\n{result_text}")
            return None
    except Exception as e:
        st.error(f"GPT 호출 실패: {e}")
        import traceback
        st.text(traceback.format_exc())
        return None
