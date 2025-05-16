import os
import pandas as pd
import streamlit as st
import plotly.express as px # plotly.express를 상단에 임포트

# (load_dataframes 함수 및 set_korean_font 함수는 기존 코드 유지)
# ... 기존 코드 ...

def load_dataframes(data_dir):
    dfs = {}

    # 파일 이름 매핑
    file_mapping = {
        "ECM": "ecm.xlsx",
        "ABS": "abs.xlsx",
        "FB": "fb.xlsx",
        "국내채권": "domestic_bond.xlsx"
    }

    # 엑셀 시트 이름 매핑
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
            # print(f"🔍 [DEBUG] {product} 로딩 중... 파일: {filename}, 시트명: {sheet_name}")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            df.columns = df.columns.astype(str).str.strip()

            if "연도" in df.columns:
                df["연도"] = df["연도"].astype(str).str.replace("년", "").astype(int)

            # '주관사' 컬럼이 없을 경우, 세 번째 컬럼을 주관사로 가정 (데이터 특성에 따라 조정 필요)
            if "주관사" not in df.columns and df.shape[1] >= 3:
                df["주관사"] = df.iloc[:, 2].astype(str).str.strip()
            elif "주관사" in df.columns: # 주관사 컬럼이 존재하면 타입 변경 및 공백 제거
                df["주관사"] = df["주관사"].astype(str).str.strip()
            else: # 주관사 컬럼을 찾을 수 없는 경우
                st.error(f"'{product}' 데이터에서 '주관사' 컬럼을 찾을 수 없습니다. 데이터 형식을 확인해주세요.")
                # 또는 빈 '주관사' 컬럼을 추가하거나, 해당 df를 건너뛰는 등의 처리
                df["주관사"] = "정보없음" # 임시 처리

            if "주관사" in df.columns: # 주관사 컬럼이 최종적으로 존재하면 공백 제거
                 df["주관사"] = df["주관사"].str.replace(" ", "")
            dfs[product] = df
            # print(f"✅ [DEBUG] {product} 데이터 로드 성공. shape: {df.shape}")

        except Exception as e:
            print(f"❌ [ERROR] {product} 데이터 로딩 실패: {e}")
            st.error(f"'{filename}' 파일 또는 '{sheet_name}' 시트 처리 중 오류: {e}")


    # print("📂 [DEBUG] 최종 로드된 데이터 키:", dfs.keys())
    return dfs


def set_korean_font():
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # NanumGothic.ttf 파일이 실행 스크립트와 동일한 위치에 있다고 가정
    nanum_font_path = "NanumGothic.ttf"
    if os.path.exists(nanum_font_path):
        fm.fontManager.addfont(nanum_font_path)
        font_name = fm.FontProperties(fname=nanum_font_path).get_name()
        plt.rcParams['font.family'] = font_name
    else:
        # st.warning("NanumGothic.ttf 폰트 파일을 찾을 수 없어 matplotlib 한글이 깨질 수 있습니다.")
        plt.rcParams['font.family'] = 'sans-serif' # 기본 폰트로 대체
    plt.rcParams['axes.unicode_minus'] = False


def plot_line_chart_plotly(df, x_col, y_col, color_col="주관사", title="📈 주관사 순위 변화 추이", key=None):
    # import plotly.express as px # 상단으로 이동

    if df.empty or x_col not in df.columns or y_col not in df.columns:
        st.warning(f"라인 차트를 그릴 데이터가 없거나, 필요한 컬럼({x_col}, {y_col})이 없습니다.")
        return

    df_copy = df.copy() # 원본 데이터 변경 방지
    df_copy[x_col] = df_copy[x_col].astype(str) # X축을 문자열(카테고리)로 변환하여 모든 연도 표시

    fig = px.line(df_copy, x=x_col, y=y_col, color=color_col, markers=True, title=title)
    fig.update_traces(textposition="top center")
    fig.update_layout(
        title_font=dict(family="NanumGothic, sans-serif", size=20), # NanumGothic 우선, 없으면 sans-serif
        font=dict(family="NanumGothic, sans-serif", size=12),
        xaxis_title=x_col,
        yaxis_title=y_col,
        xaxis_type='category' # X축을 카테고리 타입으로 명시
    )
    if y_col == "순위": # '순위' 컬럼일 경우 y축을 뒤집음
        fig.update_yaxes(autorange='reversed')

    st.plotly_chart(fig, use_container_width=True, key=key)


def plot_bar_chart_plotly(df, x_col, y_cols, title="📊 주관사별 비교", key_prefix=None):
    # import plotly.express as px # 상단으로 이동

    if df.empty or x_col not in df.columns:
        st.warning(f"막대 차트를 그릴 데이터가 없거나, 필요한 X축 컬럼({x_col})이 없습니다.")
        return

    for i, y_col in enumerate(y_cols):
        if y_col not in df.columns:
            st.warning(f"막대 차트를 위한 Y축 컬럼 '{y_col}'이 데이터에 없습니다.")
            continue

        fig = px.bar(df, x=x_col, y=y_col, text=y_col, title=f"{title} - {y_col}")
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside') # 금액 등은 천단위 콤마
        fig.update_layout(
            title_font=dict(family="NanumGothic, sans-serif", size=18), # 제목 폰트 크기 조정
            font=dict(family="NanumGothic, sans-serif", size=12),
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            xaxis_tickangle=-45,
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        # 각 차트에 고유한 key 부여
        current_key = f"{key_prefix}_{y_col}_{i}" if key_prefix else f"bar_{x_col}_{y_col}_{i}"
        st.plotly_chart(fig, use_container_width=True, key=current_key)

def plot_multi_line_chart_plotly(df, x_col, y_cols, color_col="주관사", title="📈 실적 추이", key=None):
    # import plotly.express as px # 상단으로 이동
    # import pandas as pd # 상단으로 이동

    if df.empty or x_col not in df.columns or not y_cols:
        st.warning(f"다중 라인 차트를 그릴 데이터가 없거나, 필요한 컬럼({x_col}, {y_cols})이 없습니다.")
        return

    valid_y_cols = [col for col in y_cols if col in df.columns]
    if not valid_y_cols:
        st.warning(f"다중 라인 차트를 위한 유효한 Y축 컬럼이 데이터에 없습니다. (요청: {y_cols})")
        return

    df_copy = df.copy()
    df_copy[x_col] = df_copy[x_col].astype(str) # X축을 카테고리형으로

    # Plotly Express는 y 인자에 리스트를 직접 전달하여 여러 라인을 그릴 수 있음 (동일 y축 스케일 가정)
    # 만약 각 y_col마다 다른 스케일 또는 서브플롯이 필요하면 facet_row 또는 make_subplots 사용
    if len(valid_y_cols) == 1: # y축이 하나면 기존 plot_line_chart_plotly와 유사하게
         fig = px.line(df_copy, x=x_col, y=valid_y_cols[0], color=color_col, markers=True, title=title)
         if valid_y_cols[0] == "순위":
             fig.update_yaxes(autorange='reversed', title_text=valid_y_cols[0])
         else:
             fig.update_yaxes(title_text=valid_y_cols[0])

    else: # y축이 여러개일 경우
        # 데이터를 long format으로 변경 (melt)
        id_vars_for_melt = [x_col]
        if color_col in df_copy.columns: # color_col이 실제 컬럼인지 확인
            id_vars_for_melt.append(color_col)
        else: # color_col이 없으면 (예: 단일 회사 조회 시 상품별 비교 등 다른 기준으로 색상 구분해야 할 때)
              # 이 경우, 함수 호출 시 color_col을 적절히 지정하거나, 여기서 기본값 처리
              # 지금은 color_col이 주관사로 고정된 경향이 있음.
              # 만약 color_col이 주관사가 아닌 다른 것(예: 상품명)이 될 수 있다면,
              # 함수 인자에서 이를 명확히 받거나, 데이터 구조에 따라 동적으로 결정해야 함.
              # 여기서는 color_col이 존재한다고 가정. 만약 없으면 색상 구분 없이 그려지거나 오류 발생 가능.
              pass


        df_melted = df_copy.melt(id_vars=id_vars_for_melt,
                                 value_vars=valid_y_cols,
                                 var_name='지표', # Metric -> 지표
                                 value_name='값') # Value -> 값

        fig = px.line(df_melted, x=x_col, y='값', color=color_col if color_col in id_vars_for_melt else '지표',
                      line_group='지표', # 각 지표(y_col)마다 다른 라인
                      markers=True, title=title,
                      # facet_row='지표', # 각 지표를 다른 서브플롯으로 분리하려면 활성화
                      # facet_row_spacing=0.05, # 서브플롯 간 간격 조정
                      labels={'값': '수치', '지표': '구분'}) #凡例 제목 등

        # facet_row를 사용하지 않고 한 플롯에 모두 그릴 때, y축 제목은 일반적인 "값"으로 두거나 생략.
        # 각 라인에 대한 정보는 범례(legend)로 표시.

        # 만약 facet_row를 사용한다면 각 y축을 개별적으로 제어 가능
        # for i, y_ax_name in enumerate(valid_y_cols):
        #     if y_ax_name == "순위":
        #         fig.update_yaxes(autorange='reversed', row=i+1, col=1, title_text=y_ax_name)
        #     else:
        #         fig.update_yaxes(row=i+1, col=1, title_text=y_ax_name)

        # 만약 facet_row 없이 한 그래프에 그린다면, '순위'만 있는 경우에만 y축을 뒤집거나,
        # '순위' 데이터는 별도 차트로 그리는 것을 고려. 여기서는 범용성을 위해 뒤집지 않음.
        # 또는, y_cols에 '순위'가 있고 다른 지표와 함께 있다면, y축 스케일이 매우 달라 같이 그리기 어려울 수 있음.
        # 이 경우 사용자가 어떤 형태로 보고 싶은지에 따라 facet_row 사용 여부, 정규화 등을 결정.
        # 현재는 같은 y축에 그린다고 가정. '순위'가 포함되면 스케일 문제 인지 필요.
        if "순위" in valid_y_cols and len(valid_y_cols) > 1 :
             st.caption("ℹ️ '순위' 지표는 다른 지표와 함께 표시될 때 값의 범위 차이로 인해 가독성이 낮을 수 있습니다. 단독으로 조회하거나 '순위' 지표만 차트로 보는 것을 권장합니다.")


    fig.update_traces(textposition="top center") # 데이터 포인트에 값 표시 (너무 많으면 지저분해질 수 있음)
    fig.update_layout(
        title_font=dict(family="NanumGothic, sans-serif", size=20),
        font=dict(family="NanumGothic, sans-serif", size=12),
        xaxis_title=x_col,
        xaxis_type='category'
    )
    st.plotly_chart(fig, use_container_width=True, key=key)
