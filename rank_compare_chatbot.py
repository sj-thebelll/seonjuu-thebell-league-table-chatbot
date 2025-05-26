import streamlit as st

st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

# ✅ 기본 모듈
import os
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import datetime

# ✅ 이메일 전송용 모듈 추가 (Gmail용)
import smtplib
from email.message import EmailMessage

def send_feedback_email(user_name, feedback_text, image_path=None):
    msg = EmailMessage()
    msg["Subject"] = f"[더벨 챗봇 피드백] {user_name or '익명 사용자'}"
    msg["From"] = os.getenv("GMAIL_USER")
    msg["To"] = "1001juu@thebell.co.kr"
    msg.set_content(feedback_text)

    if image_path:
        with open(image_path, "rb") as f:
            file_data = f.read()
            filename = os.path.basename(image_path)
            msg.add_attachment(file_data, maintype="image", subtype="jpeg", filename=filename)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_PASS"))
        smtp.send_message(msg)

# ✅ 환경변수 로드
from dotenv import load_dotenv
load_dotenv()  # .env에서 GMAIL_USER, GMAIL_PASS, OPENAI_API_KEY 불러오기

# ✅ OpenAI GPT API 연결
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ 유틸 함수 import
from utils import (
    load_dataframes,
    plot_bar_chart_plotly,
    plot_line_chart_plotly,
    normalize_column_name,
    plot_multi_metric_line_chart_for_single_company,
    plot_multi_metric_line_chart_for_two_companies
)


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
data_dir = os.path.dirname(__file__)
dfs = load_dataframes(data_dir)

# ✅ GPT 파서
def parse_natural_query_with_gpt(query):
    try:
        system_prompt = (
            '사용자의 질문을 다음 항목으로 분석해서 반드시 올바른 JSON 형식으로 응답해줘. '
            'true/false/null은 반드시 소문자 그대로 사용하고, 문자열은 큰따옴표("")로 감싸줘. '
            '\n\n'
            '- years: [2023, 2024] 형태\n'
            '- product: ECM, ABS, FB, 국내채권 중 하나 또는 여러 개 (문맥 유추 가능)\n'
            '- columns: ["금액", "건수", "점유율"] 중 하나 이상\n'
            '- company: 증권사명 (한 개 또는 여러 개 리스트 가능)\n'
            '- top_n: 숫자 (선택적)\n'
            '- rank_range: [시작위, 끝위] (선택적)\n'
            '- is_chart: true/false\n'
            '- is_compare: true/false\n'
            '\n'
            '🟡 아래 조건을 반드시 따를 것:\n'
            '1. 질문에 "1~10위", "상위 3개", "순위 알려줘" 등의 표현이 있으면 "rank_range" 또는 "top_n"을 포함할 것\n'
            '2. 질문에 "금액", "점유율", "건수"가 들어 있으면 "columns" 필드에 반드시 포함할 것\n'
            '3. "그래프", "추이", "변화" 등의 표현이 있으면 "is_chart": true 로 설정할 것\n'
            '4. "비교", "누가 올랐어?", "누가 떨어졌어?" 등의 표현이 있으면 "is_compare": true 로 설정할 것\n'
            '5. 연도가 명시되어 있을 경우 "years" 배열로 정확히 추출할 것\n'
            '6. ECM, ABS, FB, 국내채권 등의 키워드가 있으면 반드시 "product" 필드에 포함할 것\n'
            '\n'
            '- 특정 증권사만 있을 경우 product 없이도 전체 product 순회해줘\n'
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=800
        )

        content = response.choices[0].message.content.strip()  # ✅ 여기서 content 추출
        parsed = json.loads(content)  # ✅ JSON 파싱
        return parsed  # ✅ 파싱 성공 시 반환

    except Exception as e:
        st.error("❌ GPT 질문 해석에 실패했습니다.")
        st.info("질문 예시: '2024년 ECM 대표주관 순위 알려줘', 'NH와 KB 2023년 순위 비교'")
        print(f"[GPT 파서 오류]: {e}")
        return None
    
# ✅ 비교 함수
def compare_rank(df, year1, year2, metric_col="순위"):
    df1 = df[df["연도"] == year1][["주관사", metric_col]].copy()
    df2 = df[df["연도"] == year2][["주관사", metric_col]].copy()

    df1.rename(columns={metric_col: f"{year1}년 {metric_col}"}, inplace=True)
    df2.rename(columns={metric_col: f"{year2}년 {metric_col}"}, inplace=True)

    merged = pd.merge(df1, df2, on="주관사")
    merged["변화"] = merged[f"{year2}년 {metric_col}"] - merged[f"{year1}년 {metric_col}"]

    if metric_col == "순위":
        상승 = merged[merged["변화"] < 0].sort_values("변화")
        하락 = merged[merged["변화"] > 0].sort_values("변화", ascending=False)
    else:
        상승 = merged[merged["변화"] > 0].sort_values("변화", ascending=False)
        하락 = merged[merged["변화"] < 0].sort_values("변화")

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
        try:
            parsed = parse_natural_query_with_gpt(query)
            if not isinstance(parsed, dict):  # ✅ dict가 아닌 경우 방지
                raise ValueError("GPT 결과가 유효한 JSON 형식이 아님")
        except Exception as e:
            st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")
            st.info("예: 2024년 ECM 대표주관 순위 1~10위 알려줘")
            st.caption(f"[디버그 정보] GPT 파싱 오류: {e}")
            return  # ✅ 여기서 바로 종료 (None 처리 끝)

    # ✅ 여기부터는 parsed가 유효한 dict라는 것이 보장됨
    if parsed.get("company") and not parsed.get("product"):
        from improved_company_year_chart_logic import handle_company_year_chart_logic
        handle_company_year_chart_logic(parsed, dfs)
        handled = True

    elif not any([parsed.get("product"), parsed.get("company"), parsed.get("years")]):
        st.warning("⚠️ 어떤 항목이나 증권사에 대한 요청인지 명확하지 않아요. 예: '2024년 ECM 순위', '신영증권 그래프' 등으로 질문해주세요.")
        handled = True

    
    # ✅ 나머지 일반 루틴 처리
    products = parsed.get("product") or []
    if isinstance(products, str):
        products = [products]

    companies = parsed.get("company") or []
    if isinstance(companies, str):  # 문자열이면 리스트로 변환
       companies = [companies]

    from utils import company_aliases  # utils.py에서 딕셔너리 가져오기
    companies = [company_aliases.get(c, c) for c in companies]  # 약칭 → 정식명칭 보정
    
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
                    
            elif not companies and (parsed.get("top_n") or parsed.get("rank_range")):
                st.subheader(f"📊 {y}년 {product} 상위 주관사")
                if parsed.get("rank_range"):
                    start, end = parsed["rank_range"]
                    row = df_year[df_year["순위"].between(start, end)]
                elif parsed.get("top_n"):
                    row = df_year.nsmallest(parsed["top_n"], "순위")
                else:
                    row = pd.DataFrame()

                if not row.empty:
                    st.dataframe(row[["순위", "주관사", "금액(원)", "건수", "점유율(%)"]].reset_index(drop=True))
                else:
                    st.warning(f"⚠️ {y}년 {product} 데이터에서 상위 주관사를 찾을 수 없습니다.")
    
    if not handled and parsed.get("product"):
        products = parsed.get("product")
        if isinstance(products, str):
            products = [products]

        companies = parsed.get("company") or []
        if isinstance(companies, str):
            companies = [companies]

        years = parsed.get("years") or []
        columns = parsed.get("columns") or []

        # ✅ columns 매핑 (실제 컬럼명에 맞게 정규화)
        column_map = {
            "금액": "금액(원)",
            "점유율": "점유율(%)",
            "건수": "건수",
            "순위": "순위"
        }
        columns = [column_map.get(c.strip(), c.strip()) for c in columns]
        
        # fallback: 질문에 '순위' 포함되었으면 columns에 강제로 추가
        if "순위" in query and "순위" not in columns:
            columns.append("순위")

        for product in products:
            df = dfs.get(product)
            if df is None or df.empty:
                st.warning(f"⚠️ {product} 데이터가 없습니다.")
                continue

            df.columns = df.columns.str.strip()

            # ✅ 비교 요청 처리 (순위 / 건수 / 점유율 변화)
            if parsed.get("is_compare") and len(years) == 2:
                y1, y2 = years

                # ✅ 비교 기준 컬럼 자동 판단
                col_candidates = [normalize_column_name(c) for c in columns]
                metric_col = None
                for candidate in ["점유율(%)", "건수", "순위"]:
                    if candidate in col_candidates:
                        metric_col = candidate
                        break

                if not metric_col:
                    st.warning("⚠️ 비교할 수 있는 항목이 없습니다. (순위/건수/점유율 중 하나 필요)")
                    handled = True  # ✅ 이 return은 반드시 이 블록 안으로 들여쓰기 되어야 함

                # ✅ 항목별 비교 함수 호출
                if metric_col == "점유율(%)":
                    상승, 하락 = compare_share(df, y1, y2)
                else:
                    상승, 하락 = compare_rank(df, y1, y2, metric_col)

                # ✅ 기업 필터링
                if companies:
                    상승 = 상승[상승["주관사"].isin(companies)]
                    하락 = 하락[하락["주관사"].isin(companies)]

                    missing = [c for c in companies if c not in 상승["주관사"].values and c not in 하락["주관사"].values]
                    if missing:
                        product_str = product if isinstance(product, str) else ', '.join(product) if product else "(상품군 없음)"
                        st.warning(f"⚠️ {y1}, {y2}년 {product_str} 데이터에서 {', '.join(missing)} 증권사의 실적을 찾을 수 없습니다.")

                # ✅ 출력 (중복 없이)
                if isinstance(product, list):
                    product_str = ', '.join(product) if product else "(상품군 없음)"
                elif isinstance(product, str):
                    product_str = product
                else:
                    product_str = "(상품군 없음)"

                if not 상승.empty:
                    상승 = 상승[["주관사", f"{y1}년 순위", f"{y2}년 순위", "변화"]]
                    target_str = f" (대상: {', '.join(companies)})" if companies else ""
                    st.subheader(f"📈 {y1} → {y2} {product_str} 주관 순위 상승{target_str}")
                    st.dataframe(상승.reset_index(drop=True))

                if not 하락.empty:
                    하락 = 하락[["주관사", f"{y1}년 순위", f"{y2}년 순위", "변화"]]
                    target_str = f" (대상: {', '.join(companies)})" if companies else ""
                    st.subheader(f"📉 {y1} → {y2} {product_str} 주관 순위 하락{target_str}")
                    st.dataframe(하락.reset_index(drop=True))

            # ✅ 그래프 요청 처리
            if parsed.get("is_chart") and companies and years:
                chart_df = df[df["연도"].isin(years) & df["주관사"].isin(companies)].copy()
                if not chart_df.empty:
                    chart_df.columns = chart_df.columns.str.strip()
                    st.write("📋 현재 columns 목록:", chart_df.columns.tolist())  # ✅ 디버그 출력
                    chart_df = chart_df.sort_values(["주관사", "연도"])
                    chart_df["연도"] = chart_df["연도"].astype(int)

                    if len(companies) == 2:
                        from utils import plot_multi_metric_line_chart_for_two_companies
                        plot_multi_metric_line_chart_for_two_companies(
                          chart_df,
                          companies=companies,
                          x_col="연도",
                          y_cols=columns,
                          title=f"📊 {product} {' vs '.join(companies)} 꺾은선 그래프"
                      )

                    elif len(companies) == 1:
                        from utils import plot_multi_metric_line_chart_for_single_company
                        plot_multi_metric_line_chart_for_single_company(
                            chart_df,
                            company_name=companies[0],
                            x_col="연도",
                            y_cols=columns
                        )

                    else:
                        st.info("⚠️ 그래프 비교는 최대 2개 기업까지만 지원됩니다.")

# ✅ 피드백 폼 UI
st.markdown("## 🛠️ 피드백 보내기")
with st.form("feedback_form"):
    user_name = st.text_input("이름 또는 닉네임 (선택)")
    feedback_text = st.text_area("불편하거나 이상한 점을 알려주세요")
    uploaded_file = st.file_uploader(
        "스크린샷 업로드 (선택, 파일명은 영문/숫자만 사용)", type=["png", "jpg", "jpeg"]
    )
    submitted = st.form_submit_button("✉️ 피드백 제출")

    if submitted:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("feedback", exist_ok=True)

        # ✅ 텍스트 저장
        filepath = os.path.join("feedback", f"feedback_{timestamp}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"[이름] {user_name or '익명'}\n")
            f.write(f"[내용]\n{feedback_text}\n")

        # ✅ 이미지 저장 (있을 경우)
        image_path = None
        if uploaded_file:
            safe_filename = f"{timestamp}_{uploaded_file.name.replace(' ', '_')}"
            image_path = os.path.join("feedback", safe_filename)
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        # ✅ 이메일 전송 시도
        try:
            send_feedback_email(user_name, feedback_text, image_path)
            st.success("✅ 피드백이 저장되었고 이메일로도 전송되었습니다. 감사합니다!")
        except Exception as e:
            st.error(f"❌ 이메일 전송 중 오류 발생: {e}")


