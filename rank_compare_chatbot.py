import streamlit as st

st.set_page_config(page_title="더벨 리그테이블 챗봇", page_icon="🔔")

import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
# utils에서 모든 플로팅 함수를 가져오도록 수정 (또는 필요한 것만 명시)
from utils import load_dataframes, plot_bar_chart_plotly, plot_line_chart_plotly, plot_multi_line_chart_plotly
from improved_company_year_chart_logic import handle_company_year_chart_logic # 순서 변경 없음
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정 (matplotlib 용, plotly는 함수 내에서 처리)
def set_korean_font_matplotlib(): # 함수 이름 변경하여 구분
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        fontprop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = fontprop.get_name()
    else:
        # st.warning("⚠️ 'NanumGothic.ttf' 폰트 파일이 없어 matplotlib 차트의 한글이 깨질 수 있습니다.")
        plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font_matplotlib()

# 환경 설정
load_dotenv()
# OPENAI_API_KEY 환경변수 확인
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하거나 환경변수를 설정해주세요.")
    st.stop()
client = OpenAI(api_key=api_key)

# 데이터 디렉토리 설정 (스크립트 파일 위치 기준)
# __file__은 streamlit 클라우드 등에서 문제를 일으킬 수 있으므로, 상대 경로 사용 시 주의
# 여기서는 스크립트와 데이터 파일이 같은 디렉토리에 있다고 가정
data_dir = os.path.dirname(os.path.abspath(__file__))
try:
    dfs = load_dataframes(data_dir)
    if not dfs:
        st.error("데이터 로딩에 실패했습니다. 엑셀 파일들이 올바른 위치에 있는지, 파일 내용이 정확한지 확인해주세요.")
        st.stop()
except Exception as e:
    st.error(f"데이터 로딩 중 심각한 오류 발생: {e}")
    st.stop()


# GPT 파서 (기존 코드 유지)
def parse_natural_query_with_gpt(query):
    try:
        system_prompt = (
            '사용자의 질문을 다음 항목으로 분석해서 반드시 올바른 JSON 형식으로 응답해줘. '
            'true/false/null은 반드시 소문자 그대로 사용하고, 문자열은 큰따옴표("")로 감싸줘. '
            '항목이 없으면 결과에서 제외하거나 null로 표시해줘. columns는 항상 리스트 형태로 반환해줘 (예: ["금액", "건수"]).'
            '- years: [2023, 2024] 형태 (없으면 null 또는 빈 리스트)\n'
            '- product: ECM, ABS, FB, 국내채권 중 하나 또는 여러 개 리스트 (없으면 null 또는 빈 리스트, 문맥 유추 가능)\n'
            '- columns: ["금액", "건수", "점유율", "순위"] 중 요청된 지표 리스트 (없으면 ["금액"] 또는 ["금액(원)"])\n'
            '- company: 증권사명 리스트 (없으면 null 또는 빈 리스트)\n'
            '- top_n: 숫자 (선택적, 없으면 null)\n'
            '- rank_range: [시작순위, 끝순위] (선택적, 없으면 null)\n'
            '- is_chart: true/false (차트 요청 여부, 없으면 false)\n'
            '- is_compare: true/false (비교 요청 여부, 없으면 false)\n'
            '- 특정 증권사만 있고 product가 명시되지 않으면, 해당 증권사의 모든 product에 대한 정보를 의미할 수 있음.\n'
        )
        response = client.chat.completions.create(
            model="gpt-4", # 또는 사용 가능한 최신 모델
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1 # 일관된 결과 위해 낮은 값 사용
        )
        # GPT 응답 문자열에서 불필요한 prefix/suffix (e.g., ```json ... ```) 제거
        content = response.choices[0].message.content
        if content.startswith("```json"):
            content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content.strip())
    except Exception as e:
        st.error(f"❌ GPT 파서 오류: {e}. GPT 응답을 확인해주세요.")
        # st.text_area("GPT Raw Response", response.choices[0].message.content if 'response' in locals() else "No response")
        return None

# 비교 함수 (기존 코드 유지)
def compare_rank(df, year1, year2):
    df1 = df[df["연도"] == year1].copy()
    df2 = df[df["연도"] == year2].copy()

    if df1.empty or df2.empty: return pd.DataFrame(), pd.DataFrame() # 빈 DF 반환

    df1[f"{year1}년 순위"] = df1["순위"]
    df2[f"{year2}년 순위"] = df2["순위"]
    # '주관사' 컬럼이 있는지 확인
    if "주관사" not in df1.columns or "주관사" not in df2.columns:
        return pd.DataFrame(), pd.DataFrame()

    merged = pd.merge(df1[["주관사", f"{year1}년 순위"]], df2[["주관사", f"{year2}년 순위"]], on="주관사", how="inner")
    if merged.empty: return pd.DataFrame(), pd.DataFrame()

    merged["순위변화"] = merged[f"{year1}년 순위"] - merged[f"{year2}년 순위"] # 양수: 순위 상승(숫자 작아짐), 음수: 순위 하락
    merged["순위변화"] = merged["순위변화"] * -1 # 변화량 직관적으로 (양수: 좋아짐, 음수: 나빠짐) -> 사용자 피드백에 따라 결정

    상승 = merged[merged["순위변화"] > 0].sort_values("순위변화", ascending=False) # 순위변화가 큰 순 (예: +5)
    하락 = merged[merged["순위변화"] < 0].sort_values("순위변화", ascending=True)  # 순위변화가 작은 순 (예: -5)
    return 상승, 하락

def compare_share(df, year1, year2):
    df1 = df[df["연도"] == year1].copy()
    df2 = df[df["연도"] == year2].copy()

    if df1.empty or df2.empty or "점유율(%)" not in df1.columns or "점유율(%)" not in df2.columns :
        return pd.DataFrame(), pd.DataFrame()
    if "주관사" not in df1.columns or "주관사" not in df2.columns:
        return pd.DataFrame(), pd.DataFrame()


    merged = pd.merge(df1[["주관사", "점유율(%)"]], df2[["주관사", "점유율(%)"]], on="주관사", suffixes=(f"_{year1}", f"_{year2}"), how="inner")
    if merged.empty: return pd.DataFrame(), pd.DataFrame()

    merged["점유율변화"] = merged[f"점유율(%)_{year2}"] - merged[f"점유율(%)_{year1}"]
    상승 = merged[merged["점유율변화"] > 0].sort_values("점유율변화", ascending=False)
    하락 = merged[merged["점유율변화"] < 0].sort_values("점유율변화", ascending=True)
    return 상승, 하락


# UI
st.title("🔔 더벨 리그테이블 챗봇")
st.markdown("""
이 챗봇은 더벨의 ECM / ABS / FB / 국내채권 부문 대표주관 리그테이블 데이터를 기반으로
자연어로 질문하고, 표 또는 그래프 형태로 응답을 받는 챗봇입니다.

#### 💬 예시 질문
- 2023년 ECM 대표주관 순위 1~5위 알려줘. (금액, 건수, 점유율 함께)
- NH투자증권의 최근 3년간(2022~2024년) ECM 순위와 금액 변화를 차트로 보여줘.
- 2022년 대비 2023년 국내채권 주관 시장점유율이 가장 많이 오른 증권사는 어디야?
- KB증권과 삼성증권의 2024년 FB 실적(금액, 건수)을 비교해서 차트로 나타내줘.
- 2023년에 KB증권이 참여한 모든 상품의 순위와 금액을 알려줘.
""")

with st.form(key="question_form"):
    query = st.text_input("질문을 입력하세요:", placeholder="예: 2023년 ECM TOP5 순위와 금액 차트")
    submit = st.form_submit_button("🔍 질문하기")

if submit and query:
    main_handled_flag = False # 전체 요청에 대한 처리 여부 플래그
    with st.spinner("GPT가 질문을 해석 중입니다..."):
        parsed = parse_natural_query_with_gpt(query)

    if not parsed:
        st.error("❌ 질문을 이해하지 못했습니다. 다른 방식으로 질문해주시거나, 잠시 후 다시 시도해주세요.")
        st.stop()

    # 파싱 결과 확인 (디버깅용)
    # with st.expander("GPT 파싱 결과 보기"):
    # st.json(parsed)

    # 필수 정보 추출 및 기본값 설정
    req_companies = parsed.get("company") if parsed.get("company") else [] # 항상 리스트로
    if isinstance(req_companies, str): req_companies = [req_companies]

    req_products = parsed.get("product") if parsed.get("product") else [] # 항상 리스트로
    if isinstance(req_products, str): req_products = [req_products]

    req_years = parsed.get("years") if parsed.get("years") else [] # 항상 리스트로
    if req_years: req_years = sorted([int(y) for y in req_years]) # 정수형 및 정렬

    # GPT가 "columns"를 ["금액(원)"] 등으로 줄 수도 있고, ["금액"]으로 줄 수도 있음. 실제 컬럼명으로 매핑.
    requested_cols_from_gpt = parsed.get("columns", ["금액"]) # 기본값은 금액
    if not isinstance(requested_cols_from_gpt, list): requested_cols_from_gpt = [requested_cols_from_gpt]

    possible_y_cols_map = {
        "금액": "금액(원)", "금액(원)": "금액(원)", "deal size": "금액(원)",
        "건수": "건수", "deals": "건수", "횟수": "건수",
        "점유율": "점유율(%)", "점유율(%)": "점유율(%)", "share": "점유율(%)",
        "순위": "순위", "rank": "순위"
    }
    actual_cols_to_use = [possible_y_cols_map.get(col.strip(), col.strip()) for col in requested_cols_from_gpt]
    actual_cols_to_use = list(dict.fromkeys(actual_cols_to_use)) # 중복 제거 및 순서 유지

    is_chart_req = parsed.get("is_chart", False)
    is_compare_req = parsed.get("is_compare", False)
    top_n_req = parsed.get("top_n")
    rank_range_req = parsed.get("rank_range")


    # 시나리오 1: 특정 회사 조회 (상품 무관 또는 모든 상품) + 차트 요청
    # handle_company_year_chart_logic는 여러 상품에 걸쳐 한 회사의 특정 "지표" 추이를 그림
    if req_companies and not req_products and is_chart_req and req_years:
        st.info(f"'{', '.join(req_companies)}'의 모든 상품에 대한 '{actual_cols_to_use[0] if actual_cols_to_use else '기본 지표'}' 추이를 검색합니다.")
        # 이 함수는 내부적으로 루프를 돌며 상품별 데이터를 테이블과 차트로 표시.
        # handle_company_year_chart_logic 내부에서 y_col을 결정하므로, parsed 전달
        handle_company_year_chart_logic(parsed, dfs)
        main_handled_flag = True

    # 시나리오 2: 일반적인 상품, 연도, 회사 기반 조회 (위에서 처리 안 된 경우)
    if not main_handled_flag:
        if not req_products: # 상품 정보가 없으면
            if req_companies : # 회사 정보는 있는데 상품 정보가 없으면 모든 상품으로 간주
                st.caption(f"특정 상품이 지정되지 않아 '{', '.join(req_companies)}'에 대해 모든 상품에서 정보를 검색합니다.")
                req_products = list(dfs.keys())
            else: # 회사도 상품도 없으면 조회 불가
                st.warning("⚠️ 조회할 상품 또는 회사 정보가 명확하지 않습니다.")
                st.stop()
        if not req_products: # 그래도 product가 없으면 (dfs.keys()가 비었을 수도 있음)
             st.error("조회 가능한 상품 데이터가 없습니다.")
             st.stop()


        for prod_idx, product_name in enumerate(req_products):
            df_prod = dfs.get(product_name)
            if df_prod is None or df_prod.empty:
                st.warning(f"⚠️ '{product_name}' 상품 데이터를 찾을 수 없습니다.")
                continue

            df_prod_filtered = df_prod.copy()

            # 연도 필터링
            if req_years:
                df_prod_filtered = df_prod_filtered[df_prod_filtered["연도"].isin(req_years)]
            if df_prod_filtered.empty and req_years:
                st.info(f"ℹ️ '{product_name}' 상품의 요청하신 연도({', '.join(map(str,req_years))})에 대한 데이터가 없습니다.")
                continue

            # 회사 필터링
            if req_companies:
                df_prod_filtered = df_prod_filtered[df_prod_filtered["주관사"].isin(req_companies)]
            if df_prod_filtered.empty and req_companies:
                st.info(f"ℹ️ '{product_name}' 상품, 요청 연도에서 '{', '.join(req_companies)}'에 대한 데이터가 없습니다.")
                continue

            # 필터링 후 데이터 없으면 다음 상품으로
            if df_prod_filtered.empty:
                st.info(f"ℹ️ '{product_name}' 상품에서 현재 조건에 맞는 데이터를 찾을 수 없습니다.")
                continue

            st.markdown(f"--- \n###  wyniki dla produktu: {product_name}") # 상품별 구분선 및 제목

            # 1. 비교 요청 처리 (is_compare_req)
            if is_compare_req and len(req_years) == 2:
                y1, y2 = req_years[0], req_years[1] # 이미 정렬됨
                st.subheader(f"🔄 {product_name}: {y1}년 vs {y2}년 비교")

                # 순위 비교
                rank_up, rank_down = compare_rank(df_prod, y1, y2) # 원본 df_prod에서 해당 연도만 필터링
                # 비교 결과에 회사 필터 적용
                if req_companies:
                    rank_up = rank_up[rank_up["주관사"].isin(req_companies)]
                    rank_down = rank_down[rank_down["주관사"].isin(req_companies)]

                if not rank_up.empty :
                    st.markdown(f"**📈 순위 상승** ({', '.join(req_companies) if req_companies else '전체 증권사'})")
                    st.dataframe(rank_up.reset_index(drop=True))
                if not rank_down.empty:
                    st.markdown(f"**📉 순위 하락** ({', '.join(req_companies) if req_companies else '전체 증권사'})")
                    st.dataframe(rank_down.reset_index(drop=True))
                if rank_up.empty and rank_down.empty:
                    st.info("해당 조건의 순위 변화 데이터가 없습니다.")

                # 점유율 비교 (요청된 컬럼에 "점유율"이 있거나, 기본 비교 항목으로 포함 시)
                if "점유율(%)" in actual_cols_to_use or not actual_cols_to_use : # 명시적 요청 또는 기본 비교
                    share_up, share_down = compare_share(df_prod, y1, y2)
                    if req_companies:
                        share_up = share_up[share_up["주관사"].isin(req_companies)]
                        share_down = share_down[share_down["주관사"].isin(req_companies)]
                    if not share_up.empty:
                        st.markdown(f"**📈 점유율(%) 상승** ({', '.join(req_companies) if req_companies else '전체 증권사'})")
                        st.dataframe(share_up.reset_index(drop=True))
                    if not share_down.empty:
                        st.markdown(f"**📉 점유율(%) 하락** ({', '.join(req_companies) if req_companies else '전체 증권사'})")
                        st.dataframe(share_down.reset_index(drop=True))
                    if share_up.empty and share_down.empty and ("점유율(%)" in actual_cols_to_use or not actual_cols_to_use):
                         st.info("해당 조건의 점유율 변화 데이터가 없습니다.")
                main_handled_flag = True


            # 2. 차트 요청 처리 (is_chart_req)
            if is_chart_req:
                if not req_years:
                    st.warning(f"⚠️ [{product_name}] 차트를 그리려면 연도 정보가 필요합니다.")
                elif not actual_cols_to_use:
                    st.warning(f"⚠️ [{product_name}] 차트를 그릴 지표(컬럼)가 지정되지 않았습니다.")
                else:
                    # 유효한 실제 컬럼만 필터링 (데이터프레임에 존재하는지 확인)
                    valid_chart_cols = [col for col in actual_cols_to_use if col in df_prod_filtered.columns]
                    if not valid_chart_cols:
                        st.warning(f"⚠️ [{product_name}] 요청하신 지표 {actual_cols_to_use}에 대한 데이터를 찾을 수 없어 차트를 그릴 수 없습니다.")
                    else:
                        chart_title_suffix = f"{', '.join(valid_chart_cols)}"
                        chart_key_suffix = f"{product_name}_{'_'.join(req_companies)}_{'_'.join(map(str,req_years))}_{prod_idx}"

                        if len(req_years) > 1 and req_companies: # 여러 연도, 여러 회사/단일 회사 -> 라인 차트 (추이)
                            st.subheader(f"📈 {product_name}: {', '.join(req_companies)} 연도별 {chart_title_suffix} 추이")
                            plot_multi_line_chart_plotly(
                                df_prod_filtered.sort_values(["주관사", "연도"]),
                                x_col="연도",
                                y_cols=valid_chart_cols,
                                color_col="주관사",
                                title=f"{', '.join(req_companies)} 실적 추이",
                                key=f"multi_line_{chart_key_suffix}"
                            )
                        elif len(req_years) == 1 : # 단일 연도 -> 바 차트 (회사별 비교)
                            year_for_bar = req_years[0]
                            # 바 차트용 데이터는 해당 연도만
                            df_bar_chart = df_prod_filtered[df_prod_filtered["연도"] == year_for_bar]
                            if top_n_req: df_bar_chart = df_bar_chart[df_bar_chart["순위"] <= top_n_req]
                            elif rank_range_req: df_bar_chart = df_bar_chart[df_bar_chart["순위"].between(rank_range_req[0], rank_range_req[1])]

                            if not df_bar_chart.empty:
                                st.subheader(f"📊 {product_name}: {year_for_bar}년 주관사별 {chart_title_suffix}")
                                plot_bar_chart_plotly(
                                    df_bar_chart.sort_values("순위"),
                                    x_col="주관사",
                                    y_cols=valid_chart_cols,
                                    title=f"{year_for_bar}년 실적 비교",
                                    key_prefix=f"bar_{chart_key_suffix}"
                                )
                            else:
                                st.info(f"[{product_name}] {year_for_bar}년 바 차트 표시를 위한 데이터가 없습니다 (필터 적용 후).")
                        else: # 그 외 차트 요청 (예: 여러 연도인데 회사가 지정되지 않은 경우 등)
                            st.info(f"[{product_name}] 현재 조건으로는 명확한 차트 유형을 결정하기 어렵습니다. 회사 지정 및 연도(들)를 확인해주세요.")
                        main_handled_flag = True

            # 3. 테이블 조회 (차트나 비교 요청이 아니거나, 항상 테이블도 보여주고 싶을 때)
            # 여기서는 is_chart_req == False 그리고 is_compare_req == False 일때만 테이블을 보여주도록 함.
            # 또는, 사용자가 명시적으로 "표로 보여줘" 라고 했을 때 parsed에 table_req = True 같은 플래그를 추가해서 활용.
            if not is_chart_req and not is_compare_req :
                st.subheader(f"📋 {product_name}: 실적 데이터")
                df_display_table = df_prod_filtered.copy()

                # Top N 또는 순위 범위 적용 (회사 지정이 없을 때 주로 의미 있음)
                if not req_companies:
                    if top_n_req and "순위" in df_display_table.columns:
                        df_display_table = df_display_table[df_display_table["순위"] <= top_n_req]
                    elif rank_range_req and "순위" in df_display_table.columns:
                        df_display_table = df_display_table[df_display_table["순위"].between(rank_range_req[0], rank_range_req[1])]

                if not df_display_table.empty:
                    # 보여줄 컬럼 선택: 요청된 컬럼 + 기본 컬럼(순위, 주관사)
                    cols_for_table = ["연도", "순위", "주관사"] + actual_cols_to_use
                    cols_for_table = [col for col in cols_for_table if col in df_display_table.columns]
                    cols_for_table = list(dict.fromkeys(cols_for_table)) # 중복제거 및 순서유지

                    st.dataframe(df_display_table[cols_for_table].sort_values(["연도", "순위"]).reset_index(drop=True))
                else:
                    st.info(f"[{product_name}] 해당 조건의 테이블 데이터를 찾을 수 없습니다.")
                main_handled_flag = True


    if not main_handled_flag and parsed: # GPT 파싱은 성공했으나, 위 로직에서 아무것도 처리하지 못한 경우
        st.info("요청하신 내용에 대한 정보를 찾거나 표시할 수 없었습니다. 조건을 다시 확인해주세요. "
                "예를 들어, 연도, 상품, 회사명 등을 명확히 지정해주시면 좋습니다.")


elif submit and not query:
    st.warning("⚠️ 질문을 입력해주세요.")
