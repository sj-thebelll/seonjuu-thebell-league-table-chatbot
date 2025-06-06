import streamlit as st

st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

# ✅ 기본 모듈
import os
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import datetime


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

# utils.py에 있는 다중 첨부 지원 함수 가져오기
from utils import send_feedback_email


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

# ✅ 엑셀 파일들이 들어 있는 data 폴더 기준으로 변경
data_dir = os.path.join(os.path.dirname(__file__), "data")
dfs = load_dataframes(data_dir)

# ✅ GPT 파서
from openai import OpenAI  # openai>=1.0.0 기준

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

        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=800
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return parsed

    except Exception as e:
        st.error("❌ GPT 질문 해석에 실패했습니다.")
        st.info("질문 예시: '2024년 ECM 대표주관 순위 알려줘', 'NH와 KB 2023년 순위 비교'")
        st.caption(f"[디버그 정보] GPT 파싱 오류: {e}")
        return None  # ✅ 반드시 함수는 None을 반환해야 흐름에서 처리 가능

    except Exception as e:
        st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")
        st.info("예: 2024년 ECM 대표주관 순위 1~10위 알려줘")
        st.caption(f"[디버그 정보] GPT 파싱 오류: {e}")
        handled = True  # ✅ 함수가 아니므로 return 대신 플래그로 흐름 제어
    
# ✅ 비교 함수
def compare_rank(df, year1, year2, metric_col="순위"):
    df1 = df[df["연도"] == year1][["주관사", metric_col]].copy()
    df2 = df[df["연도"] == year2][["주관사", metric_col]].copy()

    df1.rename(columns={metric_col: f"{year1}년 {metric_col}"}, inplace=True)
    df2.rename(columns={metric_col: f"{year2}년 {metric_col}"}, inplace=True)

    merged = pd.merge(df1, df2, on="주관사")
    merged["변화"] = merged[f"{year2}년 {metric_col}"] - merged[f"{year1}년 {metric_col}"]

    ascending_order = True if metric_col == "순위" else False

    상승 = merged[merged["변화"] < 0].sort_values("변화", ascending=ascending_order)
    하락 = merged[merged["변화"] > 0].sort_values("변화", ascending=not ascending_order)

    target_columns = ["주관사", f"{year1}년 {metric_col}", f"{year2}년 {metric_col}", "변화"]
    상승 = 상승[target_columns]
    하락 = 하락[target_columns]

    return 상승, 하락


def compare_share(df, year1, year2):
    df1 = df[df["연도"] == year1][["주관사", "점유율(%)"]].copy()
    df2 = df[df["연도"] == year2][["주관사", "점유율(%)"]].copy()

    # ✅ 열 이름을 비교 출력에 맞게 변경 (예: "2022년 점유율(%)")
    df1.rename(columns={"점유율(%)": f"{year1}년 점유율(%)"}, inplace=True)
    df2.rename(columns={"점유율(%)": f"{year2}년 점유율(%)"}, inplace=True)

    # ✅ 병합 후 변화 계산
    merged = pd.merge(df1, df2, on="주관사")
    merged["변화"] = merged[f"{year2}년 점유율(%)"] - merged[f"{year1}년 점유율(%)"]

    # ✅ 상승/하락 정렬
    상승 = merged[merged["변화"] > 0].sort_values("변화", ascending=False)
    하락 = merged[merged["변화"] < 0].sort_values("변화")

    return 상승, 하락

# ✅ UI
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ** ECM(전체) / 국내채권(전체) / ABS / FB / ** 부문 대표주관 **리그테이블 데이터(2020~2024)** 를 기반으로 작동합니다. 자연어로 질문하면, **표 또는 그래프** 형태로 응답을 받을 수 있습니다.

지원되는 질문 유형:
- 연도별 주관사 순위 조회 (금액 / 건수 / 점유율 기준)
- 특정 주관사의 연도별 실적 추이
- 두 증권사의 실적 비교
- 특정 연도의 상위 주관사 리스트 (Top N)
- 연도 간 실적 변화 분석 (예: 순위 상승 / 점유율 증가 증권사)

⚠️ 일부 증권사는 특정 연도에 데이터가 없을 수 있습니다.

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
        
        # ✅ 여기부터 alias 정리 포함 파싱
        from utils import product_aliases, company_aliases
        
        try:
            parsed = parse_natural_query_with_gpt(query)
            if not isinstance(parsed, dict):
                raise ValueError("GPT 결과가 유효한 JSON 형식이 아님")
        except Exception as e:
            st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")
            st.caption(f"[디버그 GPT 파싱 오류: {e}]")
            handled = True
            parsed = {}  # 안전 조치
          
        from utils import product_aliases
        product_display_names = {v: k.upper() for k, v in product_aliases.items()}  # ⬅ 표시용 이름 매핑 추가

        products = parsed.get("product") or []
        products = [products] if isinstance(products, str) else products
        products = [product_aliases.get(p.lower(), p.lower()) for p in products]

        # 표시용 이름 저장 (예: 'dcm' ➝ 'DOMESTIC_BOND' ➝ 'DCM')
        product_strs = [product_display_names.get(p, p.upper()) for p in products]

        companies = parsed.get("company") or []
        companies = [companies] if isinstance(companies, str) else companies
        companies = [company_aliases.get(c, c) for c in companies]

        years = parsed.get("years") or []

   
    # ✅ 여전히 회사명만 있고 연도 없음 or 그래프 요청 등은 기존 루틴대로 분기
    if parsed.get("company") and not parsed.get("product"):
        from improved_company_year_chart_logic import handle_company_year_chart_logic
        handle_company_year_chart_logic(parsed, dfs)
        handled = True

    elif not any([parsed.get("product"), parsed.get("company"), parsed.get("years")]):
        st.warning("⚠️ 어떤 항목이나 증권사에 대한 요청인지 명확하지 않아요. 예: '2024년 ECM 순위', '신영증권 그래프' 등으로 질문해주세요.")
        handled = True

    # ✅ 중복 경고 방지용
    already_warned = set()

    # ✅ 최고 순위 1건만 출력 (상품 지정 없이)
    if (
        parsed.get("company") and
        parsed.get("years") and
        not parsed.get("product") and
        not parsed.get("is_chart") and
        not parsed.get("is_compare") and
        not parsed.get("top_n") and
        not parsed.get("rank_range")
    ):
        target_company = parsed.get("company")[0] if isinstance(parsed.get("company"), list) else parsed.get("company")
        target_year = parsed.get("years")[0]

        top_result = None
        top_product = None

        for product, df in dfs.items():
            if df is None or df.empty:
                continue

            df.columns = df.columns.str.strip()
            df_year = df[df["연도"] == target_year]
            df_year = df_year[df_year["주관사"] == target_company]

            if not df_year.empty:
                row = df_year.sort_values("순위").head(1)
                if top_result is None or row.iloc[0]["순위"] < top_result.iloc[0]["순위"]:
                    top_result = row.copy()
                    top_product = product

        if top_result is not None:
            best_row = top_result.iloc[0]
            best_rank = int(best_row["순위"])
            st.success(f"🏆 {target_year}년 **{target_company}**의 최고 순위는 **{top_product.upper()}**에서 **{best_rank}위**입니다.")
            st.dataframe(top_result[["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"]])
            handled = True

        else:
            st.warning(f"⚠️ {target_year}년 {target_company}의 순위 데이터가 없습니다.")
            handled = True  # 이 위치에 handled = True 유지

            if not companies and (parsed.get("top_n") or parsed.get("rank_range")):
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
        from utils import normalize_column_name  # 맨 위에 import 되어 있어야 함

        columns = [normalize_column_name(c.strip()) for c in columns]
        
        # fallback: 질문에 '순위' 포함되었으면 columns에 강제로 추가
        if "순위" in query and not any(x in query for x in ["점유율", "건수", "금액"]):
            if "순위" not in columns:
                columns.append("순위")

        for product in products:
            product_lower = product.lower()        # ✅ 추가
            df = dfs.get(product_lower)    
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

                st.write("✅ metric_col:", metric_col)
                st.write("✅ columns:", columns)
                st.write("✅ selected function:", "compare_rank" if metric_col == "순위" else "compare_share")

                if not metric_col:
                    st.warning("⚠️ 비교할 수 있는 항목이 없습니다. (순위/건수/점유율 중 하나 필요)")
                    handled = True   # ✅ 이 줄을 꼭 추가해야 중복 경고 방지됨
                    continue         # 또는 return

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

                from utils import product_aliases
                product_display_names = {v: k.upper() for k, v in product_aliases.items()}  # ✅ 맨 위에서 1회만 정의

                # 출력 (중복 없이)
                if isinstance(product, list):
                    product_str = ', '.join([product_display_names.get(p, p.upper()) for p in product]) if product else "(상품군 없음)"
                elif isinstance(product, str):
                    product_str = product_display_names.get(product, product.upper())  # ✅ 오류 해결
                else:
                    product_str = "(상품군 없음)"
                    
                if not 상승.empty:
                    상승 = 상승[["주관사", f"{y1}년 {metric_col}", f"{y2}년 {metric_col}", "변화"]]
                    target_str = f" (대상: {', '.join(companies)})" if companies else ""
                    st.subheader(f"📈 {y1} → {y2} {product_str} 주관 순위 상승{target_str}")
                    st.dataframe(상승.reset_index(drop=True))

                if not 하락.empty:
                    하락 = 하락[["주관사", f"{y1}년 {metric_col}", f"{y2}년 {metric_col}", "변화"]]
                    target_str = f" (대상: {', '.join(companies)})" if companies else ""
                    st.subheader(f"📉 {y1} → {y2} {product_str} 주관 순위 하락{target_str}")
                    st.dataframe(하락.reset_index(drop=True))

    # ✅ 그래프 요청이 있을 때만 아래 로직 전체 수행
    if parsed.get("is_chart") and companies and years:
        # 1. product 가져오기
        products = parsed.get("product") or []
        if isinstance(products, str):
            products = [products]

        # 2. ✅ alias 변환: DCM, IPO 등 정규화
        from utils import product_aliases  # 상단에서 이미 했으면 생략 가능
        product_display_names = {v: k.upper() for k, v in product_aliases.items()}  # 사람이 읽을 수 있는 이름

        products = [product_aliases.get(p.lower(), p.lower()) for p in products]    # 내부용 키 정규화
        product_strs = [product_display_names.get(p, p.upper()) for p in products]  # 그래프 제목용 표시 이름 리스트

        # 3. 기업명 정규화
        companies_normalized = [c.lower().replace(" ", "") for c in companies]

        for product, product_str in zip(products, product_strs):
            if product in already_warned:
                continue

            df = dfs.get(product)
            if df is None or df.empty:
                st.warning(f"⚠️ {product.upper()} 데이터가 없습니다.")
                already_warned.add(product)
                continue

            df.columns = df.columns.str.strip()

            # ✅ 주관사 정규화 컬럼 생성
            df["주관사_normalized"] = df["주관사"].astype(str).str.lower().str.replace(" ", "")

            # ✅ 연도 및 기업 기준 필터링
            chart_df = df[
                df["연도"].isin(years) & 
                df["주관사_normalized"].isin(companies_normalized)
            ].copy()

            if chart_df.empty:
                st.warning(f"⚠️ {product.upper()} 데이터에서 {', '.join(companies)} 데이터가 없습니다.")
                already_warned.add(product)
                continue

            chart_df = chart_df.sort_values(["주관사", "연도"])
            chart_df["연도"] = chart_df["연도"].astype(int)

            # ✅ product_str은 zip에서 이미 확보됨

            # ✅ 꺾은선 그래프 출력 (회사 수에 따라 분기)
            if len(companies) == 2:
                plot_multi_metric_line_chart_for_two_companies(
                    chart_df,
                    companies=companies,
                    x_col="연도",
                    y_cols=columns,
                    title=f"📊 [{product_str}] {' vs '.join(companies)} 꺾은선 그래프",
                    product_name=product_str
                )
                handled = True

            elif len(companies) == 1:
                plot_multi_metric_line_chart_for_single_company(
                    chart_df,
                    company_name=companies[0],
                    x_col="연도",
                    y_cols=columns,
                    product_name=product_str
                )
                handled = True

            else:
                st.info("⚠️ 그래프 비교는 최대 2개 기업까지만 지원됩니다.")

# ✅ 피드백 폼 UI
st.markdown("## 🛠️ 피드백 보내기")
st.markdown("❗ 챗봇이 제대로 작동하지 않거나, 좋은 아이디어가 있을 경우 자유롭게 의견을 보내주세요.")

with st.form("feedback_form"):
    user_name = st.text_input("이름 또는 닉네임 (선택)")
    feedback_text = st.text_area("불편하거나 이상한 점을 알려주세요")
    uploaded_files = st.file_uploader(
        "스크린샷 업로드 (여러 개 선택 가능)", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    submitted = st.form_submit_button("✉️ 보내기")

    if submitted:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("feedback", exist_ok=True)

        # ✅ 텍스트 저장
        feedback_file = os.path.join("feedback", f"feedback_{timestamp}.txt")
        with open(feedback_file, "w", encoding="utf-8") as f:
            f.write(f"[이름] {user_name or '익명'}\n")
            f.write(f"[내용]\n{feedback_text}\n")

        # ✅ 이미지 저장 (다중 파일)
        saved_image_paths = []
        if uploaded_files:
            for i, file in enumerate(uploaded_files, 1):
                filename = f"{timestamp}_img{i}_{file.name.replace(' ', '_')}"
                filepath = os.path.join("feedback", filename)
                with open(filepath, "wb") as out_file:
                    out_file.write(file.getbuffer())
                saved_image_paths.append(filepath)

        # ✅ 이메일 전송
        try:
            send_feedback_email(user_name, feedback_text, saved_image_paths)  # 리스트 그대로 전달
            st.success("✅ 피드백이 저장되었고 이메일로도 전송되었습니다. 감사합니다!")
        except Exception as e:
            st.error(f"❌ 이메일 전송 중 오류가 발생했습니다: {e}")
