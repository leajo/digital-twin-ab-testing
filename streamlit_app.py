"""
Digital Twin A/B Testing — Streamlit 데모 앱
실제 트래픽 없이 디지털 트윈 기반 사전 시뮬레이션으로 A/B 테스트 결과를 예측합니다.
"""

import sys
import os

# Backend 모듈 임포트를 위한 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.services.pipeline_orchestrator import (
    step1_upload,
    step2_simulate,
    PipelineSimulateConfig,
    PipelineError,
)
from app.services.sample_data_generator import (
    generate_sample_data,
    generate_musinsa_scenario_config,
)
from app.services.upload_service import serialize_to_csv

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Digital Twin A/B Testing",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# 커스텀 CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3f51b5, #7c4dff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.15rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .step-card {
        background: #f5f7fa;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .step-number {
        font-size: 2rem;
        font-weight: 700;
        color: #3f51b5;
    }
    .metric-highlight {
        font-size: 1.8rem;
        font-weight: 700;
        color: #3f51b5;
    }
    .badge-significant {
        background: #4caf50;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-not-significant {
        background: #ff9800;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 탭 구성
# ──────────────────────────────────────────────
tab_intro, tab_guide, tab_demo = st.tabs([
    "🏠 서비스 소개",
    "📖 이용 가이드",
    "🚀 데모",
])


# ══════════════════════════════════════════════
# Tab 1: 서비스 소개
# ══════════════════════════════════════════════
with tab_intro:
    # Hero
    st.markdown('<p class="main-title">🧬 Digital Twin A/B Testing</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">실제 트래픽 없이, 디지털 트윈 시뮬레이션으로 A/B 테스트 결과를 미리 예측하세요.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Problem Statement
    st.subheader("❓ 기존 A/B 테스트의 한계")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.markdown("#### ⏱️ 시간")
        st.markdown("통계적 유의성 확보까지 **최소 2~4주** 소요. 빠른 의사결정이 어렵습니다.")
    with col_p2:
        st.markdown("#### 💰 비용")
        st.markdown("실제 트래픽을 분할해야 하므로 **매출 손실 리스크**가 존재합니다.")
    with col_p3:
        st.markdown("#### 📊 트래픽")
        st.markdown("충분한 샘플 확보를 위해 **대규모 트래픽**이 필요합니다.")

    st.divider()

    # Solution
    st.subheader("💡 솔루션: 디지털 트윈 기반 사전 시뮬레이션")
    st.markdown("""
    과거 행동 데이터를 기반으로 **가상 유저(디지털 트윈)**를 생성하고,
    시나리오별 반응을 시뮬레이션하여 **실제 테스트 전에 결과를 예측**합니다.
    트래픽 분할 없이, 비용 없이, 몇 분 안에 결과를 확인할 수 있습니다.
    """)

    st.divider()

    # How it works — 3-step flow
    st.subheader("🔄 작동 방식")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">1</div>
            <h4>📤 데이터 업로드</h4>
            <p>이벤트 로그 CSV/JSON 파일을 업로드하면<br>자동으로 유저 프로파일링 및 세그먼트 생성</p>
        </div>
        """, unsafe_allow_html=True)
    with col_s2:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">2</div>
            <h4>⚙️ 시나리오 입력</h4>
            <p>테스트할 시나리오 유형, Variant A/B 설명,<br>타겟 페이지 등을 설정</p>
        </div>
        """, unsafe_allow_html=True)
    with col_s3:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">3</div>
            <h4>📊 결과 확인</h4>
            <p>전환율 비교, 세그먼트 히트맵, 통계 검정 등<br>7개 섹션의 상세 리포트 제공</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Key Features
    st.subheader("✨ 핵심 기능")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown('<div class="feature-icon">🎯</div>', unsafe_allow_html=True)
        st.markdown("**세그먼트별 차별 반응 분석**")
        st.markdown("유저 유형(가격 민감형, 브랜드 충성형 등)별로 Variant에 대한 반응 차이를 분석합니다.")
    with col_f2:
        st.markdown('<div class="feature-icon">🔀</div>', unsafe_allow_html=True)
        st.markdown("**시나리오별 동적 세그먼트**")
        st.markdown("시나리오 유형에 따라 핵심 행동 변수를 자동 도출하고, 맞춤 세그먼트를 재생성합니다.")
    with col_f3:
        st.markdown('<div class="feature-icon">⚖️</div>', unsafe_allow_html=True)
        st.markdown("**가중 전환율 (Weighted CR)**")
        st.markdown("세그먼트 비율을 반영한 가중 전환율로 전체 효과를 정확하게 측정합니다.")

    st.divider()

    # Tech Stack
    st.subheader("🛠️ 기술 스택")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.markdown("#### 🔗 Markov Chain")
        st.markdown("세그먼트별 페이지 전이 확률 모델을 학습하여 현실적인 유저 여정을 시뮬레이션합니다.")
    with col_t2:
        st.markdown("#### 📊 K-Means Clustering")
        st.markdown("Silhouette Score 기반 최적 K 탐색으로 유저를 행동 패턴별 세그먼트로 분류합니다.")
    with col_t3:
        st.markdown("#### 📐 카이제곱 검정")
        st.markdown("Variant 간 전환율 차이의 통계적 유의성을 검증하고, Cohen's h 효과 크기를 산출합니다.")

    st.divider()

    # Differentiation
    st.subheader("🏆 기존 시장 대비 차별점")
    diff_data = {
        "항목": ["테스트 방식", "소요 시간", "트래픽 필요", "세그먼트 분석", "비용"],
        "기존 A/B 테스트": ["실제 트래픽 분할", "2~4주", "대규모 필요", "제한적", "높음"],
        "Digital Twin A/B": ["디지털 트윈 시뮬레이션", "수 분", "불필요", "자동 세그먼트별 분석", "무료"],
    }
    st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
# Tab 2: 이용 가이드
# ══════════════════════════════════════════════
with tab_guide:
    st.header("📖 이용 가이드")
    st.markdown("Digital Twin A/B Testing 서비스를 사용하는 3단계 가이드입니다.")
    st.divider()

    # Step 1
    st.subheader("Step 1: 데이터 준비")
    st.markdown("""
    이벤트 로그 데이터를 **CSV** 또는 **JSON** 형식으로 준비합니다.
    """)

    st.markdown("**필수 필드**")
    required_fields = pd.DataFrame({
        "필드명": ["user_id", "session_id", "event_type", "timestamp"],
        "타입": ["string", "string", "string", "ISO 8601 datetime"],
        "설명": [
            "유저 고유 식별자",
            "세션 고유 식별자",
            "이벤트 유형 (page_view, click, purchase 등)",
            "이벤트 발생 시각 (예: 2024-01-15T10:30:00)",
        ],
    })
    st.dataframe(required_fields, use_container_width=True, hide_index=True)

    st.markdown("**선택 필드**")
    optional_fields = pd.DataFrame({
        "필드명": ["page", "element", "element_text", "conversion_type", "value", "device", "os", "scroll_depth_pct", "category"],
        "타입": ["string", "string", "string", "string", "float", "string", "string", "float", "string"],
        "설명": [
            "페이지 경로 (예: /home, /product/123)",
            "클릭된 요소 ID",
            "요소 텍스트",
            "전환 유형 (purchase, add_to_cart 등)",
            "금액 (구매 시)",
            "디바이스 (mobile, desktop, tablet)",
            "운영체제 (iOS, Android 등)",
            "스크롤 깊이 (%)",
            "상품 카테고리",
        ],
    })
    st.dataframe(optional_fields, use_container_width=True, hide_index=True)

    with st.expander("📋 CSV 예시"):
        st.code("""user_id,session_id,event_type,timestamp,page,element,device,os,category
user_0001,sess_abc123,page_view,2024-01-15T10:30:00,/home,,mobile,iOS,
user_0001,sess_abc123,click,2024-01-15T10:30:45,/category/men,link_category,mobile,iOS,men
user_0001,sess_abc123,page_view,2024-01-15T10:31:20,/product/product_1,,mobile,iOS,men
user_0001,sess_abc123,add_to_cart,2024-01-15T10:32:00,/product/product_1,btn_add_cart,mobile,iOS,men
user_0001,sess_abc123,page_view,2024-01-15T10:33:00,/cart,,mobile,iOS,
user_0001,sess_abc123,page_view,2024-01-15T10:34:00,/checkout,,mobile,iOS,
user_0001,sess_abc123,purchase,2024-01-15T10:35:00,/order-complete,btn_purchase,mobile,iOS,""", language="csv")

    st.divider()

    # Step 2
    st.subheader("Step 2: 시나리오 설정")

    st.markdown("**시나리오 유형**")
    scenario_types = pd.DataFrame({
        "유형": ["promotion", "cta_change", "price_display", "funnel_change", "ui_position", "timing"],
        "설명": [
            "프로모션/할인 캠페인 테스트",
            "CTA 버튼 문구/디자인 변경",
            "가격 표시 방식 변경",
            "구매 퍼널 단계 변경",
            "UI 요소 배치 변경",
            "노출 타이밍 변경",
        ],
        "자동 도출 변수": [
            "price_sensitivity, coupon_apply_rate, avg_purchase_value, purchase_frequency",
            "conversion_rate, bounce_rate, avg_pages_per_session, click_through_rate",
            "price_sensitivity, conversion_rate, avg_purchase_value",
            "funnel_completion_rate, bounce_rate, avg_session_duration",
            "scroll_depth, avg_pages_per_session, bounce_rate",
            "visit_frequency, avg_session_duration, bounce_rate",
        ],
    })
    st.dataframe(scenario_types, use_container_width=True, hide_index=True)

    st.markdown("""
    **Variant 정의**: 각 Variant에 대해 이름과 설명을 입력합니다.
    - **Variant A (Control)**: 현재 상태 또는 기준안
    - **Variant B (Treatment)**: 변경하려는 시안

    **분석 태그** (선택): `price_sensitivity`, `device`, `visit_frequency` 등의 태그를 지정하면
    해당 기준으로 그룹별 전환율을 추가 분석합니다.
    """)

    st.divider()

    # Step 3
    st.subheader("Step 3: 결과 해석")
    st.markdown("시뮬레이션 완료 후 **7개 섹션**의 상세 리포트가 제공됩니다.")

    report_sections = pd.DataFrame({
        "섹션": [
            "① 실험 요약",
            "② 핵심 지표 비교",
            "③ 세그먼트 히트맵",
            "④ 태그별 분석",
            "⑤ 퍼널 비교",
            "⑥ 통계 검정",
            "⑦ 세그먼트별 최적 Variant",
        ],
        "내용": [
            "한 줄 결론, 추천 Variant, 통계적 유의성 배지",
            "Variant별 전환율, 전환 수, 평균 세션 시간 비교 테이블",
            "세그먼트 × Variant 전환율 히트맵 차트",
            "분석 태그(가격 민감도, 디바이스 등)별 그룹 전환율 비교",
            "Variant별 퍼널 단계 이탈률 비교 차트",
            "카이제곱 통계량, p-value, 신뢰구간, Cohen's h 효과 크기",
            "각 세그먼트에서 가장 높은 전환율을 보인 Variant 매핑",
        ],
    })
    st.dataframe(report_sections, use_container_width=True, hide_index=True)

    st.divider()

    # FAQ
    st.subheader("❓ FAQ")
    with st.expander("디지털 트윈이란 무엇인가요?"):
        st.markdown("""
        디지털 트윈은 실제 유저의 행동 패턴을 학습한 **가상 유저 인스턴스**입니다.
        각 트윈은 특정 세그먼트에 속하며, 해당 세그먼트의 Markov Chain 전이 확률 모델에 따라
        페이지 이동과 전환 행동을 시뮬레이션합니다.
        """)
    with st.expander("시뮬레이션 결과는 얼마나 정확한가요?"):
        st.markdown("""
        시뮬레이션은 과거 데이터 패턴을 기반으로 한 **예측**입니다.
        데이터 품질과 양에 따라 정확도가 달라지며, 실제 A/B 테스트를 완전히 대체하기보다는
        **사전 검증 및 가설 수립** 도구로 활용하는 것을 권장합니다.
        """)
    with st.expander("최소 데이터 요구사항은 무엇인가요?"):
        st.markdown("""
        - 최소 **10명 이상**의 유저 데이터 (유저당 3건 이상의 이벤트)
        - **page_view** 이벤트에 `page` 필드가 포함되어야 합니다
        - 전환 분석을 위해 **purchase** 또는 **add_to_cart** 등의 전환 이벤트가 필요합니다
        """)
    with st.expander("트윈 수는 어떻게 설정하나요?"):
        st.markdown("""
        - **1,000개** (기본값): 빠른 탐색용. 대략적인 경향 파악에 적합합니다.
        - **5,000개**: 세그먼트별 분석에 충분한 샘플 확보.
        - **10,000개**: 높은 통계적 신뢰도. 시뮬레이션 시간이 다소 길어질 수 있습니다.
        """)


# ══════════════════════════════════════════════
# Tab 3: 데모 (Interactive)
# ══════════════════════════════════════════════
with tab_demo:
    st.header("🚀 인터랙티브 데모")
    st.markdown("샘플 데이터 또는 직접 업로드한 데이터로 Digital Twin A/B 테스트를 체험해보세요.")
    st.divider()

    # ── Step 1: 데이터 ──
    st.subheader("Step 1: 데이터")

    col_sample, col_upload = st.columns(2)

    with col_sample:
        st.markdown("**🎲 샘플 데이터 사용**")
        st.caption("무신사 패션 이커머스 가상 데이터 (100명 유저, 30일)")
        if st.button("📦 샘플 데이터 생성", use_container_width=True, type="primary"):
            with st.spinner("샘플 데이터 생성 중..."):
                events = generate_sample_data(user_count=100, days=30)
                csv_str = serialize_to_csv(events)
                csv_bytes = csv_str.encode("utf-8")

                upload_result = step1_upload(csv_bytes, "sample_data.csv")

                st.session_state["upload_result"] = upload_result
                st.session_state["csv_bytes"] = csv_bytes
                st.session_state["csv_str"] = csv_str
                st.session_state["data_source"] = "sample"
                # Clear previous simulation results
                st.session_state.pop("sim_result", None)
            st.success("샘플 데이터가 생성되었습니다!")

    with col_upload:
        st.markdown("**📁 파일 업로드**")
        st.caption("CSV 또는 JSON 형식의 이벤트 로그 파일")
        uploaded_file = st.file_uploader(
            "파일 선택",
            type=["csv", "json"],
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name
            try:
                with st.spinner("파일 처리 중..."):
                    upload_result = step1_upload(file_bytes, filename)
                    st.session_state["upload_result"] = upload_result
                    st.session_state["csv_bytes"] = file_bytes
                    st.session_state["csv_str"] = file_bytes.decode("utf-8")
                    st.session_state["data_source"] = "upload"
                    st.session_state.pop("sim_result", None)
                st.success(f"'{filename}' 파일이 처리되었습니다!")
            except (PipelineError, ValueError) as e:
                st.error(f"파일 처리 실패: {e}")

    # 데이터 요약 표시
    if "upload_result" in st.session_state:
        ur = st.session_state["upload_result"]
        st.divider()
        st.markdown("#### 📊 데이터 요약")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("총 이벤트 수", f"{ur.upload_summary.total_events:,}")
        col_m2.metric("고유 유저 수", f"{ur.upload_summary.unique_users:,}")
        col_m3.metric("프로파일 수", f"{ur.profile_count:,}")
        col_m4.metric("세그먼트 수", f"{ur.base_segment_count}")

        # 데이터 미리보기
        with st.expander("📋 데이터 미리보기", expanded=False):
            csv_str = st.session_state.get("csv_str", "")
            if csv_str:
                try:
                    from io import StringIO
                    preview_df = pd.read_csv(StringIO(csv_str))
                    st.dataframe(preview_df.head(50), use_container_width=True, height=300)
                    st.caption(f"전체 {len(preview_df):,}행 중 상위 50행 표시")
                except Exception:
                    st.info("데이터 미리보기를 표시할 수 없습니다.")

        # 세그먼트 요약
        with st.expander("🏷️ 세그먼트 정보", expanded=False):
            seg_data = []
            for seg in ur.base_segments:
                seg_data.append({
                    "세그먼트": seg.label,
                    "멤버 수": seg.summary.member_count if seg.summary else 0,
                    "평균 전환율": f"{(seg.summary.avg_conversion_rate * 100):.1f}%" if seg.summary else "-",
                    "평균 세션 시간(초)": f"{seg.summary.avg_session_duration:.0f}" if seg.summary else "-",
                    "주요 디바이스": seg.summary.primary_device if seg.summary else "-",
                    "주요 OS": seg.summary.primary_os if seg.summary else "-",
                })
            if seg_data:
                st.dataframe(pd.DataFrame(seg_data), use_container_width=True, hide_index=True)

    st.divider()

    # ── Step 2: 시나리오 설정 ──
    st.subheader("Step 2: 시나리오 설정")

    if "upload_result" not in st.session_state:
        st.info("👆 먼저 Step 1에서 데이터를 로드해주세요.")
    else:
        # 샘플 시나리오 자동 채우기 옵션
        use_sample_scenario = False
        if st.session_state.get("data_source") == "sample":
            use_sample_scenario = st.checkbox(
                "🎯 무신사 샘플 시나리오 자동 채우기",
                value=True,
                help="샘플 데이터에 최적화된 프로모션 A/B 테스트 시나리오를 자동으로 설정합니다.",
            )

        sample_config = generate_musinsa_scenario_config() if use_sample_scenario else None

        col_sc1, col_sc2 = st.columns(2)
        with col_sc1:
            scenario_name = st.text_input(
                "시나리오 이름",
                value=sample_config["scenario_name"] if sample_config else "",
                placeholder="예: 홈페이지 프로모션 A/B 테스트",
            )
            scenario_type = st.selectbox(
                "시나리오 유형",
                options=["promotion", "cta_change", "price_display", "funnel_change", "ui_position", "timing"],
                index=0 if sample_config else 0,
            )
            target_page = st.text_input(
                "타겟 페이지",
                value=sample_config["target_page"] if sample_config else "/home",
                placeholder="예: /home, /product/123",
            )

        with col_sc2:
            variant_a_desc = st.text_input(
                "Variant A (Control) 설명",
                value=sample_config["variants"][0]["description"] if sample_config else "",
                placeholder="예: 현재 홈페이지 디자인",
            )
            variant_b_desc = st.text_input(
                "Variant B (Treatment) 설명",
                value=sample_config["variants"][1]["description"] if sample_config else "",
                placeholder="예: 새로운 프로모션 배너 적용",
            )
            twin_count = st.slider(
                "트윈 수",
                min_value=100,
                max_value=10000,
                value=sample_config["twin_count"] if sample_config else 1000,
                step=100,
                help="생성할 디지털 트윈 수. 많을수록 정확하지만 시간이 더 걸립니다.",
            )

        # 시뮬레이션 실행 버튼
        can_run = bool(scenario_name and variant_a_desc and variant_b_desc and target_page)

        if st.button(
            "▶️ 시뮬레이션 실행",
            use_container_width=True,
            type="primary",
            disabled=not can_run,
        ):
            ur = st.session_state["upload_result"]

            # Build config
            variants = [
                {
                    "variant_id": "variant_a",
                    "name": "control",
                    "description": variant_a_desc,
                    "target_page": target_page,
                    "changes": {"description": variant_a_desc},
                },
                {
                    "variant_id": "variant_b",
                    "name": "treatment",
                    "description": variant_b_desc,
                    "target_page": target_page,
                    "changes": {"description": variant_b_desc},
                },
            ]

            reaction_rules = sample_config["reaction_rules"] if sample_config else []
            analysis_tags = sample_config.get("analysis_tags", []) if sample_config else []
            analysis_dimensions = sample_config.get("analysis_dimensions", []) if sample_config else []

            config = PipelineSimulateConfig(
                scenario_name=scenario_name,
                scenario_type=scenario_type,
                target_page=target_page,
                variants=variants,
                reaction_rules=reaction_rules,
                primary_metric="purchase_conversion_rate",
                twin_count=twin_count,
                analysis_tags=analysis_tags if analysis_tags else None,
                analysis_dimensions=analysis_dimensions if analysis_dimensions else None,
            )

            progress_bar = st.progress(0, text="시뮬레이션 준비 중...")
            try:
                progress_bar.progress(10, text="시나리오 생성 및 세그먼트 재클러스터링...")
                progress_bar.progress(30, text="Markov Chain 모델 학습 중...")
                progress_bar.progress(50, text="디지털 트윈 생성 중...")

                sim_result = step2_simulate(
                    config=config,
                    events=ur.events,
                    profiles=ur.profiles,
                    base_segments=ur.base_segments,
                )

                progress_bar.progress(80, text="통계 분석 및 리포트 생성 중...")
                progress_bar.progress(100, text="완료!")

                st.session_state["sim_result"] = sim_result
                st.session_state["scenario_config"] = config
                st.balloons()

            except PipelineError as e:
                progress_bar.empty()
                st.error(f"시뮬레이션 실패 [{e.stage}]: {e.message}")
            except Exception as e:
                progress_bar.empty()
                st.error(f"시뮬레이션 중 오류 발생: {e}")

    st.divider()

    # ── Step 3: 결과 리포트 ──
    st.subheader("Step 3: 결과 리포트")

    if "sim_result" not in st.session_state:
        st.info("👆 Step 2에서 시뮬레이션을 실행해주세요.")
    else:
        sim = st.session_state["sim_result"]
        report = sim.report

        # ── 섹션 1: 실험 요약 ──
        st.markdown("### ① 실험 요약")
        summary = report.summary

        col_sum1, col_sum2 = st.columns([3, 1])
        with col_sum1:
            st.markdown(f"**결론:** {summary.one_line_conclusion}")
            st.markdown(f"**추천:** {summary.recommendation}")
            if summary.winning_variant:
                st.markdown(f"**우승 Variant:** `{summary.winning_variant}`")
        with col_sum2:
            if summary.is_significant:
                st.markdown(
                    '<span class="badge-significant">✅ 통계적 유의</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span class="badge-not-significant">⚠️ 유의하지 않음</span>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # ── 섹션 2: 핵심 지표 비교 ──
        st.markdown("### ② 핵심 지표 비교")

        # Metric cards
        variant_ids = sorted(report.variant_metrics.keys())
        metric_cols = st.columns(len(variant_ids))
        for i, vid in enumerate(variant_ids):
            vr = report.variant_metrics[vid]
            weighted_cr = report.weighted_conversion_rates.get(vid, 0)
            with metric_cols[i]:
                label = f"{'🅰️' if 'a' in vid else '🅱️'} {vid}"
                st.metric(label, f"{vr.conversion_rate * 100:.2f}%", help="전환율")
                st.metric("가중 전환율", f"{weighted_cr * 100:.2f}%")
                st.metric("전환 수", f"{vr.conversions:,} / {vr.total_twins:,}")
                st.metric("평균 세션 시간", f"{vr.avg_session_duration:.0f}초")

        # Comparison table
        metrics_data = []
        for vid in variant_ids:
            vr = report.variant_metrics[vid]
            wcr = report.weighted_conversion_rates.get(vid, 0)
            metrics_data.append({
                "Variant": vid,
                "트윈 수": vr.total_twins,
                "전환 수": vr.conversions,
                "전환율 (%)": round(vr.conversion_rate * 100, 2),
                "가중 전환율 (%)": round(wcr * 100, 2),
                "평균 세션 시간 (초)": round(vr.avg_session_duration, 1),
            })
        st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)

        st.divider()

        # ── 섹션 3: 세그먼트 히트맵 ──
        st.markdown("### ③ 세그먼트별 전환율 히트맵")

        if report.segment_heatmap:
            heatmap_data = []
            for sa in report.segment_heatmap:
                for vid, vr in sa.variant_results.items():
                    heatmap_data.append({
                        "세그먼트": sa.segment_label,
                        "Variant": vid,
                        "전환율 (%)": round(vr.conversion_rate * 100, 2),
                        "전환 수": vr.conversions,
                        "트윈 수": vr.total_twins,
                    })

            heatmap_df = pd.DataFrame(heatmap_data)

            fig_heatmap = px.bar(
                heatmap_df,
                x="세그먼트",
                y="전환율 (%)",
                color="Variant",
                barmode="group",
                text="전환율 (%)",
                color_discrete_map={
                    "variant_a": "#3f51b5",
                    "variant_b": "#ff5722",
                },
            )
            fig_heatmap.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_heatmap.update_layout(
                height=400,
                xaxis_title="세그먼트",
                yaxis_title="전환율 (%)",
                legend_title="Variant",
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

            # Heatmap table
            with st.expander("📋 세그먼트 상세 데이터"):
                st.dataframe(heatmap_df, use_container_width=True, hide_index=True)
        else:
            st.info("세그먼트 분석 데이터가 없습니다.")

        st.divider()

        # ── 섹션 4: 태그별 분석 ──
        st.markdown("### ④ 태그별 분석")

        if report.tag_analyses:
            for tag_name, tag_groups in report.tag_analyses.items():
                st.markdown(f"**🏷️ {tag_name}**")
                tag_data = []
                for tg in tag_groups:
                    for vid, vr in tg.variant_results.items():
                        tag_data.append({
                            "그룹": tg.group_value,
                            "Variant": vid,
                            "전환율 (%)": round(vr.conversion_rate * 100, 2),
                            "트윈 수": vr.total_twins,
                            "전환 수": vr.conversions,
                        })

                if tag_data:
                    tag_df = pd.DataFrame(tag_data)
                    fig_tag = px.bar(
                        tag_df,
                        x="그룹",
                        y="전환율 (%)",
                        color="Variant",
                        barmode="group",
                        text="전환율 (%)",
                        color_discrete_map={
                            "variant_a": "#3f51b5",
                            "variant_b": "#ff5722",
                        },
                    )
                    fig_tag.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                    fig_tag.update_layout(height=350)
                    st.plotly_chart(fig_tag, use_container_width=True)
        else:
            st.info("분석 태그가 설정되지 않았습니다. 샘플 시나리오를 사용하면 태그 분석을 확인할 수 있습니다.")

        st.divider()

        # ── 섹션 5: 퍼널 비교 ──
        st.markdown("### ⑤ 퍼널 단계별 이탈률 비교")

        if report.funnel_comparison:
            # Collect all pages across variants
            all_pages = set()
            for vid, funnel in report.funnel_comparison.items():
                all_pages.update(funnel.keys())

            # Filter to meaningful funnel pages
            funnel_order = ["/home", "/category/men", "/category/women", "/category/shoes",
                           "/cart", "/checkout", "/order-complete"]
            ordered_pages = [p for p in funnel_order if p in all_pages]
            # Add any remaining pages not in the predefined order
            remaining = sorted(p for p in all_pages if p not in ordered_pages and not p.startswith("/product/"))
            ordered_pages.extend(remaining)

            if ordered_pages:
                funnel_data = []
                for vid in variant_ids:
                    funnel = report.funnel_comparison.get(vid, {})
                    for page in ordered_pages:
                        drop_rate = funnel.get(page, 0)
                        funnel_data.append({
                            "페이지": page,
                            "Variant": vid,
                            "도달률 (%)": round((1 - drop_rate) * 100, 1),
                        })

                funnel_df = pd.DataFrame(funnel_data)
                fig_funnel = px.line(
                    funnel_df,
                    x="페이지",
                    y="도달률 (%)",
                    color="Variant",
                    markers=True,
                    color_discrete_map={
                        "variant_a": "#3f51b5",
                        "variant_b": "#ff5722",
                    },
                )
                fig_funnel.update_layout(
                    height=400,
                    xaxis_title="퍼널 단계",
                    yaxis_title="도달률 (%)",
                )
                st.plotly_chart(fig_funnel, use_container_width=True)
            else:
                st.info("퍼널 데이터가 충분하지 않습니다.")
        else:
            st.info("퍼널 비교 데이터가 없습니다.")

        st.divider()

        # ── 섹션 6: 통계 검정 ──
        st.markdown("### ⑥ 통계 검정 결과")

        chi_sq = report.overall_statistics
        if chi_sq:
            col_st1, col_st2, col_st3, col_st4 = st.columns(4)
            col_st1.metric("카이제곱 통계량", f"{chi_sq.chi2_statistic:.4f}")
            col_st2.metric("p-value", f"{chi_sq.p_value:.4f}")
            col_st3.metric("Cohen's h", f"{chi_sq.cohens_h:.4f}")
            col_st4.metric(
                "유의성 (α=0.05)",
                "✅ 유의" if chi_sq.is_significant else "❌ 유의하지 않음",
            )

            # Confidence intervals
            if chi_sq.confidence_intervals:
                st.markdown("**95% 신뢰구간**")
                ci_data = []
                for vid, (lower, upper) in chi_sq.confidence_intervals.items():
                    ci_data.append({
                        "Variant": vid,
                        "하한 (%)": round(lower * 100, 2),
                        "상한 (%)": round(upper * 100, 2),
                        "구간 폭 (%p)": round((upper - lower) * 100, 2),
                    })
                st.dataframe(pd.DataFrame(ci_data), use_container_width=True, hide_index=True)

                # CI visualization
                fig_ci = go.Figure()
                for vid, (lower, upper) in chi_sq.confidence_intervals.items():
                    mid = (lower + upper) / 2
                    color = "#3f51b5" if "a" in vid else "#ff5722"
                    fig_ci.add_trace(go.Scatter(
                        x=[mid * 100],
                        y=[vid],
                        error_x=dict(
                            type="data",
                            symmetric=False,
                            array=[(upper - mid) * 100],
                            arrayminus=[(mid - lower) * 100],
                        ),
                        mode="markers",
                        marker=dict(size=12, color=color),
                        name=vid,
                    ))
                fig_ci.update_layout(
                    height=200,
                    xaxis_title="전환율 (%)",
                    yaxis_title="",
                    showlegend=True,
                    title="95% 신뢰구간 비교",
                )
                st.plotly_chart(fig_ci, use_container_width=True)

            # Effect size interpretation
            st.markdown("**효과 크기 해석 (Cohen's h)**")
            h = chi_sq.cohens_h
            if h < 0.2:
                effect_label = "작은 효과 (Small)"
                effect_color = "🟡"
            elif h < 0.5:
                effect_label = "중간 효과 (Medium)"
                effect_color = "🟠"
            else:
                effect_label = "큰 효과 (Large)"
                effect_color = "🔴"
            st.markdown(f"{effect_color} Cohen's h = {h:.4f} → **{effect_label}**")
        else:
            st.info("통계 검정 결과가 없습니다.")

        st.divider()

        # ── 섹션 7: 세그먼트별 최적 Variant ──
        st.markdown("### ⑦ 세그먼트별 최적 Variant")

        if report.best_variants_by_segment:
            # Map segment_id to label
            seg_label_map = {}
            for sa in report.segment_heatmap:
                seg_label_map[sa.segment_id] = sa.segment_label

            best_data = []
            for seg_id, best_vid in report.best_variants_by_segment.items():
                label = seg_label_map.get(seg_id, seg_id)
                # Find the conversion rates for context
                sa_match = next((sa for sa in report.segment_heatmap if sa.segment_id == seg_id), None)
                rates = {}
                if sa_match:
                    for vid, vr in sa_match.variant_results.items():
                        rates[vid] = vr.conversion_rate

                best_data.append({
                    "세그먼트": label,
                    "최적 Variant": best_vid,
                    **{f"{vid} 전환율 (%)": round(rate * 100, 2) for vid, rate in sorted(rates.items())},
                })

            best_df = pd.DataFrame(best_data)
            st.dataframe(best_df, use_container_width=True, hide_index=True)

            # Summary visualization
            variant_counts = pd.Series(
                list(report.best_variants_by_segment.values())
            ).value_counts()

            fig_best = px.pie(
                values=variant_counts.values,
                names=variant_counts.index,
                title="세그먼트별 최적 Variant 분포",
                color_discrete_map={
                    "variant_a": "#3f51b5",
                    "variant_b": "#ff5722",
                },
            )
            fig_best.update_layout(height=350)
            st.plotly_chart(fig_best, use_container_width=True)
        else:
            st.info("세그먼트별 최적 Variant 데이터가 없습니다.")

        st.divider()
        st.markdown("---")
        st.caption("🧬 Digital Twin A/B Testing | 디지털 트윈 기반 사전 시뮬레이션 플랫폼")
