# utils.py

import os
import pandas as pd

def load_dataframes(data_dir):
    dfs = {}

    file_mapping = {
    "ECM": "ecm.xlsx",
    "ABS": "abs.xlsx",
    "FB": "fb.xlsx",
    "국내채권": "domestic_bond.xlsx"
}


    sheet_mapping = {
        "국내채권": "전체 국내채권 대표주관 순위",
        "ABS": "유동화증권(ABS) 대표주관 순위",
        "FB": "FB 대표주관 순위",
        "ECM": "ECM 대표주관 순위"
    }

    for product, filename in file_mapping.items():
        file_path = os.path.join(data_dir, filename)
        sheet_name = sheet_mapping[product]

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            df.columns = df.columns.astype(str)
            df["연도"] = df["연도"].astype(str).str.replace("년", "").astype(int)
            df["주관사"] = df.iloc[:, 2].astype(str).str.strip()
            dfs[product] = df
        except Exception as e:
            print(f"❌ {product} 로딩 실패:", e)

    return dfs
