import openai
import os
import re
from dotenv import load_dotenv  # dotenv 패키지로 환경변수 사용

# .env 파일 로드
load_dotenv()

# 환경변수에서 OpenAI API 키 가져오기
openai.api_key = os.getenv("OPENAI_API_KEY")

def answer_query(query, dfs):
    # 예시 질의: "2024년 ABS 대표주관사 순위는?"

    # 정규식으로 연도와 상품군 추출
    match = re.search(r"(\d{4})년\s*(ECM|ABS|FB|국내채권)", query)
    if match:
        year = int(match.group(1))
        product = match.group(2)

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        df_year = df[df["연도"] == year]
        if df_year.empty:
            return f"❌ {year}년 데이터가 없어요."

        df_sorted = df_year.sort_values(by=df_year.columns[1])

        # OpenAI API에 질문 보내기
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        )

        # 응답 추출
        answer = response['choices'][0]['message']['content']

        return f"📌 {year}년 {product} 대표주관사 순위\n\n" + df_sorted.head(10).to_markdown(index=False) + "\n\n📍 " + answer

    return "❓ 죄송해요! 아직 그 질문엔 답변할 수 없어요.\n질문 형식을 다시 확인해 주세요."
