import streamlit as st
import pandas as pd
from utils import plot_line_chart_plotly

def handle_company_year_chart_logic(parsed, dfs):
    companies = parsed["company"]
    if isinstance(companies, str):
        companies = [companies]
    req_years = parsed.get("years", [])
    is_chart_requested = parsed.get("is_chart", False)

    y_column_name_in_query = parsed.get("columns", ["금액(원)"])[0]
    possible_y_cols = {
        "금액": "금액(원)", "금액(원)": "금액(원)",
        "건수": "건수",
        "점유율": "점유율(%)", "점유율(%)": "점유율(%)",
        "순위": "순위"
    }
    y_column_to_plot = possible_y_cols.get(y_column_name_in_query, "금액(원)")

    if is_chart_requested and len(req_years) >= 1:
        line_chart_data_all_products = []
        table_data_to_display_company_no_prod = {}

        for product_name_iter, df_iter in dfs.items():
            df_iter.columns = df_iter.columns.str.strip()
            df_filtered_by_year = df_iter[df_iter["연도"].isin(req_years)] if req_years else df_iter
            df_company_product = df_filtered_by_year[df_filtered_by_year["주관사"].isin(companies)]

            if not df_company_product.empty:
                years_to_iterate_for_table = req_years if req_years else sorted(df_company_product["연도"].unique())

                for y_iter in years_to_iterate_for_table:
                    df_year_specific = df_company_product[df_company_product["연도"] == y_iter]
                    if not df_year_specific.empty:
                        key = f"{product_name_iter}_{y_iter}_{'_'.join(companies)}"
                        display_cols_table = [col for col in ["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"] if col in df_year_specific.columns]
                        table_data_to_display_company_no_prod[key] = df_year_specific[display_cols_table]

                if req_years:
                    df_company_product_for_chart = df_company_product[df_company_product["연도"].isin(req_years)]
                    if not df_company_product_for_chart.empty:
                        df_company_product_copy = df_company_product_for_chart.copy()
                        df_company_product_copy["product_source"] = product_name_iter
                        line_chart_data_all_products.append(df_company_product_copy)

        if table_data_to_display_company_no_prod:
            st.subheader(f"📄 {', '.join(companies)}의 상품별 실적 데이터")
            for key in sorted(table_data_to_display_company_no_prod.keys(), key=lambda x: (x.split("_")[1], x.split("_")[0])):
                df_to_show = table_data_to_display_company_no_prod[key]
                p_name, yr, _ = key.split("_", 2)
                st.markdown(f"**{yr}년 {p_name}**")
                st.dataframe(df_to_show.reset_index(drop=True))

        if is_chart_requested and line_chart_data_all_products:
            combined_df_all_products = pd.concat(line_chart_data_all_products).reset_index(drop=True)
            if not combined_df_all_products.empty and y_column_to_plot in combined_df_all_products.columns:
                color_by = "product_source"
                if len(companies) > 1:
                    color_by = "주관사"
                elif len(combined_df_all_products["product_source"].unique()) == 1:
                    if "주관사" in combined_df_all_products.columns and len(combined_df_all_products["주관사"].unique()) > 1:
                        color_by = "주관사"

                y_col_name_map = {"금액(원)": "금액", "건수": "건수", "점유율(%)": "점유율", "순위": "순위"}
                y_title_suffix = y_col_name_map.get(y_column_to_plot, y_column_to_plot)
                title_chart = f"📊 {', '.join(companies)}의 연돌별 {y_title_suffix} 변화 ({color_by}별)"
                if len(req_years) == 1:
                    title_chart = f"📊 {', '.join(companies)}의 {req_years[0]}년 {y_title_suffix} 현황 ({color_by}별)"

                st.subheader(title_chart)
                plot_line_chart_plotly(combined_df_all_products, x_col="연돌", y_col=y_column_to_plot, color_col=color_by, title=title_chart)
            elif is_chart_requested:
                st.info(f"ℹ️ '{', '.join(companies)}'에 대한 차트({y_column_to_plot} 기준)만큼의 데이터가 없거나 충분하지 않습니다.")
        elif is_chart_requested:
            st.warning(f"⚠️ '{', '.join(companies)}'에 대한 차트 데이터를 찾을 수 없습니다 (요청 연돌: {req_years}).")

    elif not is_chart_requested or not req_years:
        table_data_to_display_no_chart_company = {}
        found_data_for_company_table_only = False

        if req_years:
            for product_name_iter, df_iter in dfs.items():
                df_iter.columns = df_iter.columns.str.strip()
                for y_iter in req_years:
                    df_year_iter = df_iter[df_iter["연도"] == y_iter]
                    row_data = df_year_iter[df_year_iter["주관사"].isin(companies)]
                    if not row_data.empty:
                        found_data_for_company_table_only = True
                        key = f"{product_name_iter}_{y_iter}_{'_'.join(companies)}"
                        display_cols_table = [col for col in ["연도", "순위", "주관사", "금액(원)", "건수", "점유율(%)"] if col in row_data.columns]
                        table_data_to_display_no_chart_company[key] = row_data[display_cols_table]

            if table_data_to_display_no_chart_company:
                st.subheader(f"📄 {', '.join(companies)}의 상품별 실적 데이터 (차트 요청 없음)")
                for key in sorted(table_data_to_display_no_chart_company.keys(), key=lambda x: (x.split("_")[1], x.split("_")[0])):
                    df_to_show = table_data_to_display_no_chart_company[key]
                    p_name, yr, _ = key.split("_", 2)
                    st.markdown(f"**{yr}년 {p_name}**")
                    st.dataframe(df_to_show.reset_index(drop=True))

            if not found_data_for_company_table_only:
                st.warning(f"⚠️ '{', '.join(companies)}'의 {min(req_years)}~{max(req_years)}년 데이터를 찾을 수 없습니다.")
        elif not req_years and companies:
            st.warning(f"⚠️ '{', '.join(companies)}' 관련 데이터를 표시하려면 조회할 연돌을 지정해주세요. (예: 최근 3개년)")
