# utils.py

import os
import pandas as pd

def load_dataframes(data_dir):
    dfs = {}

    # ✅ 파일명 매핑
    file_mapping = {
        "ECM": "ecm.xlsx",
        "ABS": "abs.xlsx",
        "FB": "fb.xlsx",
        "국내채권": "domestic_bond.xlsx"
    }

    # ✅ 시트명도 영어로 변경되었다고 가정
    sheet_mapping = {
        "국내채권": "국내채권",
        "ABS": "ABS",
        "FB": "FB",
        "ECM": "ECM"
    }

    for product, filename in file_mapping.items():
        file_path = os.path.join(data_dir, filename)
        sheet_name = sheet_mapping[product]

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            df.columns = df.columns.astype(str)
            df["연도"] = df["연도"].astype(str).str.replace("년", "").astype(int)
            df["주관사"] = df.iloc[:, 2].astype(str).str.strip()  # 3번째 컬럼이 주관사 기준
            dfs[product] = df
        except Exception as e:
            print(f"❌ '{product}' 데이터 로딩 실패:", e)

    return dfs
