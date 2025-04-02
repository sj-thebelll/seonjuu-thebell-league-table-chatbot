def process_keywords(keywords, dfs):
    try:
        year_kw = keywords[0].strip()
        product = keywords[1].strip().upper()
        column = keywords[2].strip()
        company_kw = keywords[3].strip()
        rank_kw = keywords[4].strip()

        # 연도 처리
        if "~" in year_kw:
            start, end = map(int, year_kw.split("~"))
            years = list(range(start, end + 1))
        else:
            years = [int(year_kw)]

        # 증권사 처리
        companies = []
        if company_kw:
            for raw in re.split(r"[\/,]", company_kw):
                raw = raw.strip()
                if raw:
                    companies.append(company_aliases.get(raw, raw))

        # 순위 범위 처리
        if "~" in rank_kw:
            rank_start, rank_end = map(int, re.findall(r"\d+", rank_kw))
            rank_range = list(range(rank_start, rank_end + 1))
        else:
            rank_range = [int(s) for s in re.findall(r"\d+", rank_kw)]

        df = dfs.get(product)
        if df is None:
            return f"❌ '{product}' 데이터가 없어요."

        result_rows = []

        for year in years:
            df_year = df[df["연도"] == year]
            if df_year.empty:
                continue

            if column not in df.columns:
                return f"❌ '{column}'이라는 항목은 없어요."

            df_filtered = df_year[df_year[column].isin(rank_range)]

            if companies:
                df_filtered = df_filtered[df_filtered["주관사"].isin(companies)]

            if not df_filtered.empty:
                df_filtered = df_filtered[["연도", "주관사", column]]
                df_filtered = df_filtered.rename(columns={column: "순위"})  # ✅ 컬럼명 변경
                result_rows.append((year, product, df_filtered))

        if not result_rows:
            return "❌ 조건에 맞는 결과가 없습니다."

        # 결과 출력: 연도 + 항목별 구분 출력
        for (year, product, group_df) in result_rows:
            st.markdown(f"### 📌 {year}년 {product} 리그테이블")
            st.dataframe(group_df.reset_index(drop=True))

        return ""

    except Exception as e:
        return f"❌ 오류가 발생했어요: {str(e)}"
