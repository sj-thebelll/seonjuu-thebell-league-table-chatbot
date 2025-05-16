import streamlit as st
import pandas as pd
from utils import plot_line_chart_plotly # 단일 y축 라인 차트 함수

def handle_company_year_chart_logic(parsed, dfs):
    companies = parsed.get("company")
    if isinstance(companies, str):
        companies = [companies]
    if not companies:
        st.warning("회사명이 지정되지 않았습니다.")
        return

    req_years = parsed.get("years", [])
    is_chart_requested = parsed.get("is_chart", False)

    # 사용자가 요청한 컬럼을 파악 (GPT 파서가 "columns"로 전달 가정)
    # 기본값은 "금액(원)" 이지만, 파서 결과에 따라 여러 개일 수 있음
    # 이 함수는 단일 회사에 대해 "상품별"로 "하나의 지표"를 비교하는 데 중점
    # 따라서 y_column_name_in_query가 여러 개여도 첫 번째 것을 사용하거나,
    # 또는 이 함수를 여러 지표에 대해 반복 호출하도록 상위 로직 수정 필요.
    # 여기서는 첫 번째 요청된 컬럼 또는 기본 컬럼을 사용.
    requested_chart_columns = parsed.get("columns", ["금액"]) # GPT가 "금액"으로 줄 수 있음
    y_column_name_in_query = requested_chart_columns[0] if requested_chart_columns else "금액"


    possible_y_cols = {
        "금액": "금액(원)", "금액(원)": "금액(원)",
        "건수": "건수",
        "점유율": "점유율(%)", "점유율(%)": "점유율(%)",
        "순위": "순위"
    }
    y_column_to_plot = possible_y_cols.get(y_column_name_in_query, "금액(원)")

    line_chart_data_all_products = []
    table_data_to_display_company_no_prod = {}

    found_data_for_company = False

    for product_name_iter, df_iter_original in dfs.items():
        if df_iter_original is None or df_iter_original.empty:
            continue
        df_iter = df_iter_original.copy() # 원본 수정 방지
        df_iter.columns = df_iter.columns.str.strip()

        # 특정 회사 데이터 필터링
        df_company_product_all_years = df_iter[df_iter["주관사"].isin(companies)]

        if df_company_product_all_years.empty:
            continue

        found_data_for_company = True # 해당 회사에 대한 데이터를 하나라도 찾음

        # 테이블 데이터 준비 (요청 연도 있든 없든)
        years_for_table = req_years if req_years else sorted(df_company_product_all_years["연도"].unique())
        for y_iter in years_for_table:
            df_year_specific = df_company_product_all_years[df_company_product_all_years["연도"] == y_iter]
            if not df_year_specific.empty:
                key_table = f"table_{product_name_iter}_{y_iter}_{'_'.join(companies)}"
                display_cols_table = [col for col in ["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"] if col in df_year_specific.columns]
                table_data_to_display_company_no_prod[key_table] = df_year_specific[display_cols_table]

        # 차트 데이터 준비 (차트 요청 & 연도 지정 & y_column_to_plot이 존재할 때)
        if is_chart_requested and req_years and y_column_to_plot in df_company_product_all_years.columns:
            df_company_product_for_chart = df_company_product_all_years[df_company_product_all_years["연도"].isin(req_years)]
            if not df_company_product_for_chart.empty:
                df_company_product_copy = df_company_product_for_chart.copy()
                df_company_product_copy["product_source"] = product_name_iter # 어떤 상품인지 구분하기 위한 컬럼
                line_chart_data_all_products.append(df_company_product_copy)

    if not found_data_for_company:
        st.warning(f"⚠️ '{', '.join(companies)}'에 대한 데이터를 어떤 상품에서도 찾을 수 없습니다.")
        return # 데이터 없으면 함수 종료

    # 테이블 데이터 출력
    if table_data_to_display_company_no_prod:
        st.subheader(f"📄 {', '.join(companies)}의 상품별 실적 데이터")
        # 연도 우선, 그 다음 상품명으로 정렬
        for key_table in sorted(table_data_to_display_company_no_prod.keys(), key=lambda x: (x.split("_")[2], x.split("_")[1])):
            df_to_show = table_data_to_display_company_no_prod[key_table]
            _, p_name, yr, comps_str = key_table.split("_", 3)
            st.markdown(f"**{yr}년 {p_name}** ({comps_str})")
            st.dataframe(df_to_show.reset_index(drop=True))
    elif not is_chart_requested: # 차트 요청도 없고 테이블 데이터도 없을 때 (매우 드문 경우)
        st.info(f"'{', '.join(companies)}'에 대한 조회 가능한 실적 데이터가 없습니다.")


    # 라인 차트 데이터 출력
    if is_chart_requested:
        if line_chart_data_all_products:
            combined_df_all_products = pd.concat(line_chart_data_all_products).reset_index(drop=True)
            if not combined_df_all_products.empty and y_column_to_plot in combined_df_all_products.columns:
                # color_by는 상품별로 (product_source)
                # 만약 단일 상품에 대해 여러 회사를 이 함수에서 그린다면 color_by="주관사"
                # 현재 이 함수는 "여러 회사" 입력도 받지만, 각 회사별로 상품별 추이를 그리는게 아니라
                # "지정된 회사들"의 "각 상품별" 추이를 "하나의 차트"에 그리는 것을 가정.
                # 이 경우, 색상은 product_source가 적합.
                color_by_chart = "product_source"

                # 차트 제목
                y_col_name_map = {"금액(원)": "금액", "건수": "건수", "점유율(%)": "점유율", "순위": "순위"}
                y_title_suffix = y_col_name_map.get(y_column_to_plot, y_column_to_plot)
                title_chart = f"📊 {', '.join(companies)}의 연도별 {y_title_suffix} 변화 (상품별 비교)"
                if len(req_years) == 1:
                     title_chart = f"📊 {', '.join(companies)}의 {req_years[0]}년 {y_title_suffix} 현황 (상품별 비교)"


                st.subheader(title_chart)
                # plot_line_chart_plotly는 단일 y_col을 받음
                plot_line_chart_plotly(
                    combined_df_all_products,
                    x_col="연도",
                    y_col=y_column_to_plot,
                    color_col=color_by_chart, # 상품별로 색상 구분
                    title=title_chart,
                    key=f"company_line_{'_'.join(companies)}_{y_column_to_plot}"
                )
            elif y_column_to_plot not in combined_df_all_products.columns :
                 st.warning(f"⚠️ 차트를 그릴 수 없습니다. 선택된 지표 '{y_column_to_plot}'가 데이터에 없습니다.")
            else: # combined_df_all_products가 비어있는 경우
                st.info(f"ℹ️ '{', '.join(companies)}'에 대한 차트 데이터(요청 지표: {y_column_to_plot}, 요청 연도: {req_years})가 충분하지 않습니다.")
        elif req_years : # 차트 요청은 있었으나, line_chart_data_all_products가 비어 있고, 연도 요청이 있었을 때
            st.warning(f"⚠️ '{', '.join(companies)}'에 대한 차트 데이터를 찾을 수 없습니다 (요청 연도: {req_years}, 요청 지표: {y_column_to_plot}).")
        else: # 차트 요청은 있었으나, 연도 요청이 없을 때
            st.warning("⚠️ 차트를 표시하려면 조회할 연도를 지정해주세요.")
