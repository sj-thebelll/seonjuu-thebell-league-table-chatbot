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
            '- product: ECM, DCM, SB, ABS, FB, IPO, FO 중 하나 또는 여러 개 (문맥 또는 명시된 키워드 기반 추출)\n'
            '- columns: ["금액", "건수", "점유율"] 중 하나 이상\n'
            '- company: 증권사명 (한 개 또는 여러 개 리스트 가능)\n'
            '- top_n: 숫자 (선택적)\n'
            '- rank_range: [시작위, 끝위] (선택적)\n'
            '- is_chart: true/false\n'
            '- is_compare: true/false\n'
            '\n'
            '🟡 아래 조건을 반드시 따를 것:\n'
            '1. 질문에 "1~10위", "상위 3개", "상위 몇 개" 등 **정확한 숫자 범위나 개수 표현**이 있을 경우에만 "rank_range" 또는 "top_n"을 포함할 것\n'
            '2. 질문에 "금액", "점유율", "건수"가 들어 있으면 "columns" 필드에 반드시 포함할 것\n'
            '3. "그래프", "추이", "변화" 등의 표현이 있으면 "is_chart": true 로 설정할 것\n'
            '4. "비교", "누가 올랐어?", "누가 떨어졌어?" 등의 표현이 있으면 "is_compare": true 로 설정할 것\n'
            '5. 연도가 명시되어 있을 경우 "years" 배열로 정확히 추출할 것\n'
            '6. 질문에 다음 키워드가 포함되면 반드시 해당 "product"로 처리할 것:\n'
            '   - "ABS", "자산유동화증권" → "ABS"\n'
            '   - "FB", "여전채", "여신전문금융회사채권" → "FB"\n'
            '   - "SB", "일반회사채", "회사채" → "SB"\n'
            '   - "IPO", "기업공개" → "IPO"\n'
            '   - "FO", "유상증자", "유증" → "FO"\n'
            '   - "ECM" → "ECM"\n'
            '   - "DCM", "국내채권" → "DCM"\n'
            '\n'
            '- 단, 질문에 명확히 SB/ABS/FB/IPO/FO가 포함되어 있으면 그 하위 상품명을 그대로 product에 사용해야 함\n'
            '  (예: "2024년 FB 순위 알려줘" → product는 "FB")\n'
            '\n'
            '🔴 아래 키워드가 포함된 질문은 무조건 다음과 같이 응답할 것:\n'
            '"⚠️질문 주신 내용은 추후 업데이트 될 예정입니다."\n'
            '\n'
            '- 키워드 목록:\n'
            '  전환사채, CB, BW, 신주인수권부사채, ELB, M&A, VC, 벤처캐피탈, '
            '인수 순위, 인수 실적, 수수료, 수수료 실적, 수수료 순위, 자문 실적, 자문 순위, 부동산, 헤지펀드, 수익률\n'
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
이 챗봇은 더벨의 ECM, DCM, SB(일반회사채), ABS(자산유동화증권), FB(여신전문금융회사채권), IPO, FO(유상증자) 부문 대표주관 리그테이블 데이터(2020~2024)를 기반으로 작동합니다.
질문을 하면, 표 또는 그래프 형태로 응답을 받을 수 있습니다.

#### 💬 예시 질문
- 2024년 DCM 대표주관 순위 1~10위 알려줘.
- 2020~2024년 ABS 대표주관 상위 3개사 보여줘.
- 2022년에 비해 2023년 IPO 주관 점유율이 오른 증권사는?
- 신영증권의 2022~2024년 ECM 순위 그래프 보여줘.
- 2023년 현대차증권이 랭크된 순위 전부 알려줘.
- 미래에셋증권과 KB증권의 2021~2024년 유상증자 주관 순위 비교 그래프 보여줘.

⚠️ M&A, VC, 헤지펀드 등은 향후 업데이트 될 예정입니다.
""")

with st.form(key="question_form"):
    query = st.text_input("질문을 입력하세요:")
    submit = st.form_submit_button("🔍 질문하기")

if submit and query:
    handled = False
    parsed = None  # ✅ parsed를 먼저 선언 (바깥에서도 접근 가능하도록)

    with st.spinner("GPT가 질문을 해석 중입니다..."):
        from utils import product_aliases, company_aliases

        try:
            parsed = parse_natural_query_with_gpt(query)
            st.info(f"🔍 parsed: {parsed}")  # 개발 중 디버깅용

            # ✅ dict 여부 먼저 확인
            if isinstance(parsed, dict):
                if "message" in parsed and len(parsed) == 1:
                    st.warning(f"⚠️ {parsed['message']}")
                    handled = True
                    st.stop()
            else:
                raise ValueError("GPT 결과가 유효한 JSON 형식이 아님")

        except Exception as e:
            if not handled:
                st.error("❌ 질문을 이해하지 못했어요. 다시 시도해 주세요.")
                st.caption(f"[디버그 GPT 파싱 오류: {e}]")
            handled = True
            st.stop()

    # ✅ spinner 바깥에서 메시지 응답 안전하게 처리
    if isinstance(parsed, dict) and "message" in parsed and len(parsed) == 1:
        st.warning(f"⚠️ {parsed['message']}")  # ⚠️ 포함 메시지 출력
        handled = True  # 이후 파싱 로직, 테이블 출력 등 건너뜀

    # ✅ handled 예외 여부 체크로 중단
    if handled:
        st.stop()

    # ✅ 정상 파싱 이후 전처리
    product_display_names = {v: k.upper() for k, v in product_aliases.items()}
    products = parsed.get("product") or []
    products = [products] if isinstance(products, str) else products
    products = [product_aliases.get(p.lower(), p.lower()) for p in products]
    product_strs = [product_display_names.get(p, p.upper()) for p in products]

    companies = parsed.get("company") or []
    companies = [companies] if isinstance(companies, str) else companies
    companies = [company_aliases.get(c, c) for c in companies]

    years = parsed.get("years") or []

    # ✅ 기존 분기 로직 그대로 유지
    if parsed.get("company") and not parsed.get("product"):
        from improved_company_year_chart_logic import handle_company_year_chart_logic
        handle_company_year_chart_logic(parsed, dfs)
        st.stop()

    elif not any([parsed.get("product"), parsed.get("company"), parsed.get("years")]):
        st.warning("⚠️ 어떤 항목이나 증권사에 대한 요청인지 명확하지 않아요.")
        st.stop()

    already_warned = set()  # 중복 경고 방지용


    # ✅ 최고 순위 1건만 출력 (상품 지정 없이)
    if (
        parsed.get("company") and
        not parsed.get("product") and
        not parsed.get("is_chart") and
        not parsed.get("is_compare") and
        not parsed.get("top_n") and
        not parsed.get("rank_range")
    ):
        target_company = companies[0] if isinstance(companies, list) else companies
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
    
    if not handled and (
        parsed.get("product") or
        parsed.get("top_n") or
        parsed.get("rank_range")
    ):
        products = parsed.get("product") or ["ecm"]  # 기본값 지정
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
                    metric_label = "점유율" if metric_col == "점유율(%)" else "순위"
                    st.subheader(f"📈 {y1} → {y2} {product_str} 주관 {metric_label} 상승{target_str}")
                    st.dataframe(상승.reset_index(drop=True))
                    handled = True  # ✅ 여기 추가

                if not 하락.empty:
                    하락 = 하락[["주관사", f"{y1}년 {metric_col}", f"{y2}년 {metric_col}", "변화"]]
                    target_str = f" (대상: {', '.join(companies)})" if companies else ""
                    metric_label = "점유율" if metric_col == "점유율(%)" else "순위"
                    st.subheader(f"📉 {y1} → {y2} {product_str} 주관 {metric_label} 하락{target_str}")
                    st.dataframe(하락.reset_index(drop=True))
                    handled = True  # ✅ 여기 추가

            # ✅ Top N, Rank Range, 전체 순위 질문 처리 (회사명이 지정되지 않은 경우)
            if not handled and products and years and not companies and not parsed.get("is_chart") and not parsed.get("is_compare"):
                top_n = parsed.get("top_n", None)
                rank_range = parsed.get("rank_range", None)

                for product in products:
                    product_lower = product.lower()
                    df = dfs.get(product_lower)
                    if df is None or df.empty:
                        st.warning(f"⚠️ {product.upper()} 데이터가 없습니다.")
                        continue

                    df.columns = df.columns.str.strip()
                    filtered_df = df[df["연도"].isin(years)] if years else df.copy()

                    if rank_range:
                        start, end = rank_range
                        filtered_df = filtered_df[filtered_df["순위"].between(start, end)]
                    elif top_n:
                        filtered_df = (
                            filtered_df.groupby("연도")
                            .apply(lambda x: x.nsmallest(top_n, "순위"))
                            .reset_index(drop=True)
                        )
                    else:
                        # ✅ 전체 순위 요청일 때 연도별 순위 기준 정렬
                        filtered_df = filtered_df.sort_values(["연도", "순위"]).reset_index(drop=True)

                    if filtered_df.empty:
                        st.warning(f"⚠️ {product.upper()} 데이터에서 순위 정보를 찾을 수 없습니다.")
                        continue

                    st.subheader(f"📌 {product.upper()} 대표주관 순위")
                    st.dataframe(filtered_df[["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"]])
                    handled = True

            # ✅ 전체 순위 요청 처리 (회사명 없이 top_n, rank_range 없이 전체 순위)
            elif not handled and products and years and not companies and not parsed.get("is_chart") and not parsed.get("is_compare"):
                for product in products:
                    product_lower = product.lower()
                    df = dfs.get(product_lower)
                    if df is None or df.empty:
                        st.warning(f"⚠️ {product.upper()} 데이터가 없습니다.")
                        continue

                    df.columns = df.columns.str.strip()
                    filtered_df = df[df["연도"].isin(years)].copy()

                    if filtered_df.empty:
                        st.warning(f"⚠️ {product.upper()} 데이터에서 순위 정보를 찾을 수 없습니다.")
                        continue

                    display_cols = ["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"]
                    st.subheader(f"📌 {product.upper()} 대표주관 순위")
                    st.dataframe(filtered_df[display_cols].sort_values(["연도", "순위"]).reset_index(drop=True))
                    handled = True

            # ✅ 회사+연도+상품만 있는 경우 기본 실적 테이블 출력
            if products and companies and years and not parsed.get("is_chart") and not parsed.get("is_compare"):
                for product in products:
                    product_lower = product.lower()
                    df = dfs.get(product_lower)
                    if df is None or df.empty:
                        continue

                    df.columns = df.columns.str.strip()
                    filtered_df = df[
                        df["연도"].isin(years) & df["주관사"].isin(companies)
                    ].copy()

                    if filtered_df.empty:
                        st.warning(f"⚠️ {product.upper()} 데이터에서 {', '.join(companies)} 실적을 찾을 수 없습니다.")
                        continue

                    display_cols = ["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"]
                    st.subheader(f"📊 {', '.join(companies)}의 {product.upper()} 실적")
                    st.dataframe(filtered_df[display_cols].sort_values(["연도", "순위"]))
                    handled = True

                    # ✅ 회사명 + 연도 + 상품 + rank_range만 있는 경우 전용 처리
                    if (
                        not handled and
                        products and companies and years and rank_range and
                        not parsed.get("is_chart") and not parsed.get("is_compare")
                    ):
                        for product in products:
                            product_lower = product.lower()
                            df = dfs.get(product_lower)
                            if df is None or df.empty:
                                continue

                            df.columns = df.columns.str.strip()
                            df_filtered = df[
                                df["연도"].isin(years) & df["주관사"].isin(companies)
                            ].copy()

                            start, end = rank_range
                            df_filtered = df_filtered[df_filtered["순위"].between(start, end)]

                            if df_filtered.empty:
                                st.warning(f"⚠️ {product.upper()} 데이터에서 {', '.join(companies)} 실적을 찾을 수 없습니다.")
                                continue

                            display_cols = ["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"]
                            st.subheader(f"📌 {', '.join(companies)}의 {product.upper()} 실적 (순위 {start}~{end})")
                            st.dataframe(df_filtered[display_cols].sort_values(["연도", "순위"]))
                            handled = True

                    
                    # ✅ 회사 없이 product + years + columns만 있는 경우 (Top N 없이 순위 리스트 요청 등)
                    if not handled and products and years and columns and not companies and not parsed.get("is_chart") and not parsed.get("is_compare"):
                        for product in products:
                            product_lower = product.lower()
                            df = dfs.get(product_lower)
                            if df is None or df.empty:
                                st.warning(f"⚠️ {product.upper()} 데이터가 없습니다.")
                                continue

                            df.columns = df.columns.str.strip()
                            filtered_df = df[df["연도"].isin(years)].copy()

                            if filtered_df.empty:
                                st.warning(f"⚠️ {product.upper()} 데이터에서 조건에 맞는 항목을 찾을 수 없습니다.")
                                continue

                            display_cols = ["연도", "순위", "주관사"] + [c for c in ["금액(원)", "건수", "점유율(%)"] if c in columns]
                            st.subheader(f"📊 {product.upper()} 대표주관 순위")
                            st.dataframe(filtered_df[display_cols].sort_values(["연도", "순위"]).reset_index(drop=True))
                            handled = True

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

with st.expander("📘 더벨 리그테이블 집계기준", expanded=False):
    st.markdown("### 🏦 DCM 리그테이블 작성 기준")
    st.markdown("""
- 대표주관실적과 인수실적을 대상으로 리그테이블을 산정한다. 공동주관 실적은 집계하지 않는다.  
- 일반회사채(SB)는 **수요예측을 실시한 채권만** 대표주관 실적에 포함된다.  
- 일괄신고채권도 수요예측 시 대표주관 실적에 포함한다.  
- FB는 수요예측 여부와 **무관하게 대표주관 실적에 포함**된다.  
- 모집주선 실적은 **별도 집계**하며 종합 성적에는 반영하지 않는다.  
- 외화표시 채권은 증권신고서 환율 기준으로 원화 환산.  
- 대표주관 실적은 **균등 배분**, 인수실적은 **신고서 기준 인수금액** 사용.  
- 실적은 시장평균 수수료 대비 **상대 수수료를 반영해 조정**될 수 있다.
    """)

    st.markdown("### 📈 ECM 리그테이블 작성 기준")
    st.markdown("""
- 주관사, 인수사, 모집주선사 실적을 각각 집계하며, **블록딜은 별도 집계**  
- 증권신고서 및 발행실적보고서 기준  
- 외화표시 주식은 신고 환율 기준으로 **원화 환산**  
- 주관 실적은 **대표 주관사 기준**, 복수일 경우 **균등 배분**  
- IPO 공동주관 실적은 **인수금액 기준**으로 인정  
- 모집주선은 **공모에 한해**, 실적은 **균등 배분**  
- 부분잔액인수의 경우: 인수 책임금액은 주관 실적, 그 외는 모집주선 실적  
- 수수료는 실적보고서 명시 기준, 사모 수수료는 제외  
- 수수료 반영 **조정 리그테이블 시범 발표**
    """)

# ✅ 피드백 폼 UI
st.markdown("## 🛠️ 피드백 보내기")
st.markdown("❗ 챗봇에 문제가 있거나, 좋은 아이디어가 있을 경우 자유롭게 의견을 보내주세요.")

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
            st.success("✅ 피드백이 이메일로 전송되었습니다. 감사합니다!")
        except Exception as e:
            st.error(f"❌ 이메일 전송 중 오류가 발생했습니다: {e}")
