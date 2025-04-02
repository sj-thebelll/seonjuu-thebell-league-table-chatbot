# 리그테이블 챗봇 (League Table Chatbot)

이 프로젝트는 더벨의 리그테이블 데이터를 기반으로  
자연어 질문에 응답할 수 있는 챗봇을 만드는 Python 프로젝트입니다.

OpenAI의 GPT API를 활용하여  
"2024년 ABS 대표주관사 순위는?" 같은 질문을 이해하고  
엑셀 데이터를 조회한 뒤, 자연어 응답과 함께 결과를 제공합니다.

---

## 🛠 주요 기능

- 연도 및 상품(ECM, ABS, FB, 국내채권)별 대표주관사 순위 조회
- 자연어 입력 → 표와 설명으로 응답
- pandas로 데이터 처리
- OpenAI GPT API 기반의 답변 생성

---

## 📁 파일 구조

├── chatbot.py # 챗봇 본문 
├── rank_compare_chatbot.py # 순위 비교 기능 포함 챗봇 
├── dcm_chatbot.py # 딜 관련 기능 챗봇 
├── utils/ # 엑셀 불러오기 등 유틸 
├── .env # OpenAI API 키 (업로드 금지!) 
├── .gitignore # .env 등을 Git에 올리지 않도록 설정 
├── README.md # 이 파일 
├── data/ # 엑셀 파일들 (예: ECM, ABS, FB 등)
yaml
복사
편집

---

## 🧪 예시 질문

- `2023년 ECM 대표주관사 전체 순위 알려줘`
- `2024년 ABS 분야에서 KB증권이 몇 위야?`
- `2022년 FB에서 NH투자증권 순위는?`

---

## ⚠️ 사용 시 주의사항

- `.env` 파일에 본인의 OpenAI API 키를 꼭 저장해야 합니다.

```bash
OPENAI_API_KEY=sk-본인의-진짜-키