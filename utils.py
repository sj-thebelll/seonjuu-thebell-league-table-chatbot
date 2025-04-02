# utils.py

import os
import pandas as pd
import streamlit as st  # ✅ Streamlit 로그 표시를 위해 추가

def load_dataframes(data_dir):
    dfs = {}

    # ✅ 파일 이름 매핑
    file_mapping = {
        "ECM": "ecm.xlsx",
        "ABS": "abs.xlsx",
        "FB": "fb.xlsx",
        "국내채권": "domestic_bond.xlsx"
    }

    # ✅ 엑셀 시트 이름 매핑 (엑셀 내 실제 시트명과 정확히 일치해야 함)
    sheet_mapping = {
        "ECM": "ECM",
        "ABS": "ABS",
        "FB": "FB",
        "국내채권": "국내채권"
    }

    for product, filename in file_mapping.items():
        file_path = os.path.join(data_dir, filename)
        sheet_name = sheet_mapping[product]

        try:
            # ✅ 로드 로그 출력
            print(f"🔍 [DEBUG] {product} 로딩 중... 파일: {filename}, 시트명: {sheet_name}")
            st.text(f"🔍 {product} 로딩 중...")

            # ✅ 엑셀 시트 읽기
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            # ✅ 컬럼명 문자열 처리
            df.columns = df.columns.astype(str)

            # ✅ '연도' 컬럼 전처리: "2023년" → 2023
            df["연도"] = df["연도"].astype(str).str.replace("년", "").astype(int)

            # ✅ '주관사' 컬럼 전처리 (3번째 열이 주관사라고 가정)
            df["주관사"] = df.iloc[:, 2].astype(str).str.strip()

            # ✅ 로딩된 데이터 저장
            dfs[product] = df

            # ✅ 성공 로그
            print(f"✅ [DEBUG] {product} 데이터 로드 성공. shape: {df.shape}")
            st.text(f"✅ {product} 데이터 로드 완료 ({df.shape[0]} rows)")

        except Exception as e:
            # ❌ 실패 로그
            print(f"❌ [ERROR] {product} 데이터 로딩 실패:", e)
            st.text(f"❌ {product} 데이터 로딩 실패: {e}")

    # ✅ 로드된 데이터 키 확인
    print("📂 [DEBUG] 최종 로드된 데이터 키:", dfs.keys())
    st.text(f"📂 최종 로드된 데이터 키: {list(dfs.keys())}")

    return dfs
