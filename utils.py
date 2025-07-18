import os
import pandas as pd
import streamlit as st
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from dotenv import load_dotenv
from collections import defaultdict

# ✅ 보정 딕셔너리는 함수 밖, 파일 상단이나 중단에 위치해야 함
company_aliases = {
    "미래에셋": "미래에셋증권", "삼성": "삼성증권", "KB": "KB증권", "NH": "NH투자증권",
    "한투": "한국투자증권", "한국증권": "한국투자증권", "한화": "한화투자증권", "메리츠": "메리츠증권",
    "신한": "신한투자증권", "하나": "하나증권", "키움": "키움증권", "이베스트": "이베스트투자증권",
    "교보": "교보증권", "대신": "대신증권", "하이": "하이투자증권", "부국": "부국증권",
    "DB": "DB금융투자", "유안타": "유안타증권", "유진": "유진투자증권", "케이프": "케이프투자증권",
    "SK": "SK증권", "현대차": "현대차증권", "KTB": "KTB투자증권", "BNK": "BNK투자증권",
    "IBK": "IBK투자증권", "토스": "토스증권", "다올": "다올투자증권", "산은": "한국산업은행",
    "신금투": "신한투자증권", "JP모건": "JP모간", "IM증권": "아이엠증권", "한화증권": "한화투자증권", 
    "코리아에셋증권": "코리아에셋투자증권", "크레디아크리꼴": "크레디아그리콜", "크레디트아그리콜": "크레디아그리콜" ,
    "웰스파고": "Wells Fargo", "BofA메릴린치": "BOA메릴린치", "소시에떼제네랄": "소시에테제네랄", "노무라증권": "노무라",
    "코메르츠방크": "코메르츠", "코메르츠크": "코메르츠", "메릴린치증권": "메릴린치증권 서울지점", "메릴린치": "메릴린치증권 서울지점",
}

def send_feedback_email(name, text, image_paths=None):
    import os
    import smtplib
    from email.message import EmailMessage
    from dotenv import load_dotenv  # ✅ 환경변수 로드용 추가
    load_dotenv()  # ✅ .env 파일에서 GMAIL_USER, GMAIL_PASS 로딩

    msg = EmailMessage()
    msg["Subject"] = f"[챗봇 피드백] {name or '익명'}"
    msg["From"] = os.getenv("GMAIL_USER")
    msg["To"] = "1001juuu@gmail.com"  # ✅ 실제 수신자 주소
    msg.set_content(text)

    # ✅ 이미지 첨부
    if image_paths:
        for path in image_paths:
            if isinstance(path, str) and os.path.exists(path):
                with open(path, "rb") as f:
                    file_data = f.read()
                    filename = os.path.basename(path)
                    msg.add_attachment(file_data, maintype="image", subtype="jpeg", filename=filename)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_PASS"))
        smtp.send_message(msg)

# utils.py 내 적절한 위치에 추가
product_aliases = {
    "ecm": "ecm",
    "abs": "abs",
    "fb": "fb",
    "ipo": "ipo",
    "sb": "sb",
    "dcm": "dcm",
    "ro": "ro",
}

role_aliases = {
    "lead": "lead",
    "underwrite": "underwrite",
    "arrange": "arrange"
}

# ✅ product_aliases와 함께 상단에서 import 후 선언
from utils import product_aliases

product_display_names = {v: k.upper() for k, v in product_aliases.items()}

# ✅ 공통 컬럼 정규화 함수 (모든 함수에서 공통 사용)
def normalize_column_name(col):
    column_map = {
        "금액": "금액(원)",
        "점유율": "점유율(%)",
        "건수": "건수",
        "순위": "순위"
    }
    return column_map.get(col.strip(), col.strip())

def load_dataframes(data_dir):
    dfs = defaultdict(dict)
    structured_dfs = {}  # 새롭게 추가되는 구조화된 딕셔너리

    for filename in os.listdir(data_dir):
        if filename.endswith(".xlsx"):
            base = filename.replace(".xlsx", "").lower()
            file_path = os.path.join(data_dir, filename)

            # 파일명 예: ecm_lead_rank → 상품: ecm, 역할: lead
            tokens = base.split("_")
            print(f"[DEBUG] 📂 파일명: {base}, tokens: {tokens}")  # ✅ 디버깅 추가
            product = tokens[0]

            role = None
            filter_cond = None

            # ✅ 수정된 코드
            for token in tokens[1:]:
                token_lower = token.lower()

                # 역할 설정
                if token_lower in role_aliases and role is None:
                    role = role_aliases[token_lower]

                # 필터 조건 설정 (복수 가능성 고려)
                elif token_lower in ["noabs", "nofbabs", "corp"] and filter_cond is None:
                    filter_cond = token_lower

                    
            print(f"[DEBUG] 🔍 상품: {product}, 역할: {role}, 필터조건: {filter_cond}")

            try:
                # 엑셀 파일 첫 시트를 로딩 (시트명이 정확하지 않아도 동작)
                try:
                    df = pd.read_excel(file_path, sheet_name=base)
                except:
                    xls = pd.ExcelFile(file_path)
                    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])

                # 공통 컬럼 정리
                df.columns = df.columns.astype(str).str.strip().str.replace('"', '', regex=False)

                if "연도" in df.columns:
                    df["연도"] = df["연도"].astype(str).str.replace("년", "").astype(int)

                if "주관사" not in df.columns and df.shape[1] >= 3:
                    df["주관사"] = df.iloc[:, 2].astype(str).str.strip()
                else:
                    df["주관사"] = df["주관사"].astype(str).str.strip()

                df["주관사"] = df["주관사"].str.replace(" ", "")
                structured_dfs[(product, role, filter_cond)] = df  # ✅ 이 줄 추가

                # 기존 방식 저장 (기존 코드 호환)
                dfs[product] = df

                # 구조화 방식 저장
                key = (product, role, filter_cond) if filter_cond else (product, role)
                structured_dfs[key] = df
                dfs[key] = df  # ✅ 이 줄 추가

                print(f"✅ [DEBUG] '{filename}' → key: {key} / shape: {df.shape}")

            except Exception as e:
                print(f"❌ [ERROR] '{filename}' 로딩 실패:", e)

    # 기존 dfs에 구조화된 항목 추가
    dfs.update(structured_dfs)
    print("🟡 [DEBUG] 최종 로드된 데이터 키:", list(dfs.keys()))

    # [DEBUG] structured_dfs 내부 키 목록 확인용 (임시 확인 코드)
    print("[DEBUG] structured_dfs keys:")
    for key in structured_dfs:
        print("  →", key)

    return dfs, structured_dfs



# ✅ (옵션) matplotlib 그래프에서 사용할 한글 폰트 설정
def set_korean_font():
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    nanum_font_path = os.path.abspath("NanumGothic.ttf")
    if os.path.exists(nanum_font_path):
        fm.fontManager.addfont(nanum_font_path)
        font_name = fm.FontProperties(fname=nanum_font_path).get_name()
        plt.rcParams['font.family'] = font_name
    else:
        plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False  # ✅ 마이너스 깨짐 방지

# ✅ plotly 기반 꺾은선 차트 함수 (한글 깨짐 방지)
def plot_line_chart_plotly(df, x_col, y_col, color_col="주관사", title="📈 주관사 순위 변화 추이", key=None):
    import plotly.express as px

    df[x_col] = df[x_col].astype(int)  # ✅ 연도는 반드시 정수형 처리
    fig = px.line(df, x=x_col, y=y_col, color=color_col, markers=True, title=title)
    fig.update_traces(textposition="top center")
    fig.update_layout(
        title_font=dict(family="Nanum Gothic", size=20),
        font=dict(family="Nanum Gothic", size=12),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis_autorange='reversed',  # 순위는 숫자 작을수록 위쪽
        xaxis_type='category'
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

# ✅ bar chart 함수도 유지 (필요 시 사용 가능)
def plot_bar_chart_plotly(df, x_col, y_cols, title="📊 주관사별 비교", key=None):
    import plotly.express as px
    import streamlit as st
    import uuid

    for y_col in y_cols:
        unique_key = key or f"{y_col}_{uuid.uuid4().hex[:8]}"
        fig = px.bar(df, x=x_col, y=y_col, text=y_col, title=title)
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True, key=unique_key)


# ✅ 단일 주관사 기준, 여러 연도 실적 항목을 하나의 꺾은선 그래프로 표현
def plot_multi_metric_line_chart_for_single_company(df, company_name, x_col="연도", y_cols=["금액(원)", "건수", "점유율(%)"], product_name=None):
    import plotly.express as px

    if df.empty:
        label = f"{product_name} 데이터에서 " if product_name else ""
        st.warning(f"⚠️ {label}{company_name}의 그래프 데이터가 없습니다.")
        return

    # ✅ 컬럼명 정규화 및 필터링
    y_cols = [normalize_column_name(col) for col in y_cols]
    y_cols = [col for col in y_cols if col in df.columns]

    if not y_cols:
        st.warning(f"⚠️ {company_name}에 대해 시각화할 수 있는 컬럼이 없습니다.")
        return

    df[x_col] = df[x_col].astype(int)
    df_melted = df.melt(id_vars=[x_col, "주관사"], value_vars=y_cols,
                        var_name="항목", value_name="값")

    for 항목 in df_melted["항목"].unique():
        sub_df = df_melted[df_melted["항목"] == 항목].copy()
        fig = px.line(sub_df, x=x_col, y="값", color="주관사", markers=True,
                      title=(
                          f"📊 [{product_name}] {company_name} 연도별 {항목} 추이"
                          if product_name else f"📊 {company_name} 연도별 {항목} 추이"
                      ))


        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            xaxis_title=x_col,
            yaxis_title=항목,
            legend_title="주관사",
            xaxis=dict(type="category", tickformat=".0f")
        )

        if 항목 == "순위":
            fig.update_yaxes(autorange="reversed")

        st.plotly_chart(fig, use_container_width=True)


# ✅ 여러 기업 비교용 꺾은선 그래프 함수
def plot_multi_line_chart_plotly(df, x_col, y_cols, color_col, title="📊 비교 꺾은선 그래프"):
    import plotly.express as px
    import streamlit as st

    df[x_col] = df[x_col].astype(int)

    for y_col in y_cols:
        fig = px.line(df, x=x_col, y=y_col, color=color_col, markers=True, title=f"{title} - {y_col}")

        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            xaxis_title=x_col,
            yaxis_title="값",
            legend_title=color_col
        )

        # ✅ 순위일 경우 y축 반전
        if y_col == "순위":
            fig.update_yaxes(autorange="reversed")

        st.plotly_chart(fig, use_container_width=True, key=f"{y_col}_{color_col}_multi")

# ✅ 2개 이하 기업의 순위 비교 꺾은선 그래프 함수
def plot_rank_comparison_for_up_to_two_companies(
    df, companies, x_col="연도", y_col="순위", product_name=None
):
    import plotly.express as px
    import streamlit as st
    import uuid

    if df.empty or not companies:
        st.warning("⚠️ 비교할 데이터가 없습니다.")
        return

    if y_col not in df.columns:
        st.warning(f"⚠️ '{y_col}' 항목이 데이터에 없습니다.")
        return

    if len(companies) > 2:
        st.warning("⚠️ 현재는 기업 2개까지만 비교 가능합니다.")
        return

    df[x_col] = df[x_col].astype(int)
    chart_df = df[df["주관사"].isin(companies)].copy()
    chart_df = chart_df.sort_values([x_col, "주관사"])

    fig = px.line(
        chart_df,
        x=x_col,
        y=y_col,
        color="주관사",
        markers=True,
        title=(
            f"📊 [{product_name}] {' vs '.join(companies)} 연도별 {y_col} 추이"
            if product_name else f"📊 {' vs '.join(companies)} 연도별 {y_col} 추이"
        ))

    fig.update_layout(
        title_font=dict(family="Nanum Gothic", size=20),
        font=dict(family="Nanum Gothic", size=12),
        xaxis_title=x_col,
        yaxis_title=y_col,
        legend_title="주관사",
        xaxis=dict(
            type="category",
            tickformat=".0f"  # ✅ 연도를 소수점 없이 정수로 표시
        )
    )

    if y_col == "순위":
        fig.update_yaxes(autorange="reversed")  # ✅ 순위는 낮을수록 상위

    key_suffix = str(uuid.uuid4())[:8]
    st.plotly_chart(fig, use_container_width=True, key=f"rank_compare_{key_suffix}")

def plot_multi_metric_line_chart_for_two_companies(
    df, companies, x_col="연도", y_cols=["금액(원)", "점유율(%)", "순위"], title=None, product_name=None
):
    import plotly.express as px
    import streamlit as st
    import uuid

    if df.empty or not companies:
        st.warning("⚠️ 비교할 데이터가 없습니다.")
        return

    if len(companies) != 2:
        st.warning("⚠️ 정확히 2개 기업만 비교 가능합니다.")
        return

    col_name_map = {
        "금액": "금액(원)",
        "점유율": "점유율(%)",
        "건수": "건수",
        "순위": "순위"
    }
    y_cols = [col_name_map.get(c, c) for c in y_cols if c in df.columns]

    if not y_cols:
        st.warning("⚠️ 비교 가능한 항목이 없습니다.")
        return

    df = df[df["주관사"].isin(companies)].copy()
    df[x_col] = df[x_col].astype(int)
    df_melted = df.melt(id_vars=[x_col, "주관사"], value_vars=y_cols,
                        var_name="항목", value_name="값")

    for 항목 in df_melted["항목"].unique():
        sub_df = df_melted[df_melted["항목"] == 항목]
        fig = px.line(sub_df, x=x_col, y="값", color="주관사", markers=True,
                      title=(
                          f"📊 [{product_name}] {' vs '.join(companies)} 연도별 {항목} 추이"
                          if product_name else f"📊 {' vs '.join(companies)} 연도별 {항목} 추이"
                      ))  

     
        fig.update_layout(
            title_font=dict(family="Nanum Gothic", size=20),
            font=dict(family="Nanum Gothic", size=12),
            xaxis_title=x_col,
            yaxis_title=항목,
            legend_title="주관사",
            xaxis=dict(type="category", tickformat=".0f")
        )
        if 항목 == "순위":
            fig.update_yaxes(autorange="reversed")

        st.plotly_chart(fig, use_container_width=True, key=f"{항목}_{uuid.uuid4().hex[:8]}")
