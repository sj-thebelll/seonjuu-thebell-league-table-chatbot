import openai
import os
import re
import pandas as pd
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수에서 OpenAI API 키 가져오기
openai.api_key = os.getenv("OPENAI_API_KEY")


def answer_query(query, dfs):
    # ✅ 연도와 상품군 추출
    from utils import product_aliases  # 상단에 반드시 import

    match = re.search(r"(\d{4})년\s*(ECM|ABS|FB|SB|IPO|RO|DCM|국내채권|여전채|자산유동화증권|일반회사채|기업공개|유상증자)", query, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        raw_product = match.group(2).lower()
        product = product_aliases.get(raw_product)

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        df_year = df[df["연도"] == year]
        if df_year.empty:
            return f"❌ {year}년 데이터가 없어요."

        df_sorted = df_year.sort_values(by="순위")

        # ✅ GPT 질문 및 응답
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "너는 한국 자본시장 리그테이블 전문가야. 질문에 정확하게 답해줘."},
                    {"role": "user", "content": query}
                ],
                temperature=0.2,
                max_tokens=500
            )
            answer = response['choices'][0]['message']['content']
        except Exception as e:
            answer = f"GPT 응답 실패: {e}"

        # ✅ 표 + GPT 응답 반환
        markdown_table = df_sorted[["순위", "주관사", "금액(원)", "건수", "점유율(%)"]].head(10).to_markdown(index=False)
        return f"📌 {year}년 {product} 대표주관사 순위\n\n{markdown_table}\n\n📍 GPT 분석: {answer}"

    # ✅ 회사명 기반 질문 (예: '한국투자증권 2022~2024년 실적 보여줘')
    company_match = re.search(r"(\d{4})[~\-](\d{4})년.*(증권)", query)
    if company_match:
        y1, y2 = int(company_match.group(1)), int(company_match.group(2))
        company = query.split()[-1]  # 가장 마지막 단어에 증권사가 있다고 가정

        combined_df = pd.DataFrame()
        for product, df in dfs.items():
            df.columns = df.columns.str.strip()
            for y in range(y1, y2 + 1):
                df_year = df[df["연도"] == y]
                row = df_year[df_year["주관사"] == company]
                if not row.empty:
                    row = row.copy()
                    row["product"] = product
                    combined_df = pd.concat([combined_df, row])

        if combined_df.empty:
            return f"⚠️ {company}의 {y1}~{y2}년 실적을 찾을 수 없습니다."

        display_cols = ["연도", "product", "순위", "주관사", "금액(원)", "건수", "점유율(%)"]
        table_text = combined_df[display_cols].sort_values(["product", "연도"]).to_markdown(index=False)

        return f"📊 {company}의 {y1}~{y2}년 상품별 실적\n\n{table_text}"

    return "❓ 죄송해요! 아직 그 질문엔 답변할 수 없어요.\n질문 형식을 다시 확인해 주세요."
