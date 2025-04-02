import os
import pandas as pd

def load_dataframes(data_dir):
    dfs = {}

    # ✅ 파일명 매핑 (파일은 반드시 영문명으로 저장되어 있어야 함)
    file_mapping = {
        "ECM": "ecm.xlsx",
        "ABS": "abs.xlsx",
        "FB": "fb.xlsx",
        "국내채권": "domestic_bond.xlsx"
    }

    # ✅ 시트명 매핑 (실제 엑셀 시트 이름 기준)
    sheet_mapping = {
        "ECM": "ECM 대표주관 순위",
        "ABS": "유동화증권(ABS) 대표주관 순위",
        "FB": "FB 대표주관 순위",
        "국내채권": "전체 국내채권 대표주관 순위"
    }

    for product, filename in file_mapping.items():
        file_path = os.path.join(data_dir, filename)
        sheet_name = sheet_mapping.get(product)

        if not os.path.exists(file_path):
            print(f"⚠️ 파일 없음: {filename}")
            continue

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            df.columns = df.columns.astype(str)

            # 연도 전처리: "2024년" → 2024 (int)
            if "연도" in df.columns:
                df["연도"] = (
                    df["연도"]
                    .astype(str)
                    .str.replace("년", "", regex=False)
                    .astype(int)
                )

            # 주관사 컬럼 정리 (3번째 컬럼 기준, 보통 '주관사' 또는 '회사명')
            df["주관사"] = df.iloc[:, 2].astype(str).str.strip()

            dfs[product] = df

        except Exception as e:
            print(f"❌ {product} 로딩 실패: {e}")

    return dfs
