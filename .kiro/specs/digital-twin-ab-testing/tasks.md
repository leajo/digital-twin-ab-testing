# 구현 계획: 디지털 트윈 기반 A/B 테스트 시뮬레이션 서비스

## 개요

본 구현 계획은 MVP 3스텝 플로우(데이터 업로드 → 시나리오 입력 → 결과 확인)를 중심으로 구성된다. 이미 완료된 레이어 1~2 기반 위에 시나리오별 변수 도출, 동적 세그먼트, 파이프라인 오케스트레이션을 먼저 구축한 후, 시뮬레이션/통계/리포트를 연결하고, 마지막으로 프론트엔드를 구현한다.

## Tasks

- [x] 1. 프로젝트 구조 및 핵심 데이터 모델 설정
  - [x] 1.1 프로젝트 디렉토리 구조 생성 및 의존성 설정
    - `backend/` 디렉토리에 FastAPI 프로젝트 구조 생성 (`app/`, `app/models/`, `app/services/`, `app/api/`, `app/tests/`)
    - `requirements.txt`에 FastAPI, uvicorn, numpy, pandas, scipy, scikit-learn, hypothesis, pytest, psycopg2-binary, sqlalchemy 등 의존성 정의
    - `frontend/` 디렉토리에 React 프로젝트 구조 생성 (Recharts 포함)
    - _Requirements: 전체_
  - [x] 1.2 핵심 데이터 모델 정의
    - `app/models/` 하위에 `event.py`, `profile.py`, `segment.py`, `twin.py`, `simulation.py` 파일 생성
    - 설계 문서의 모든 dataclass 구현 (EventRecord, UserProfile, Segment, MarkovChainModel, DigitalTwin, Scenario, SimulationResult 등)
    - `PipelineUploadResult`, `PipelineSimulateResult`, `PipelineSimulateConfig` dataclass 추가
    - _Requirements: 전체_
  - [x] 1.3 PostgreSQL 데이터베이스 스키마 및 연결 설정
    - SQLAlchemy 모델 정의 (event_logs, uploads, user_profiles, segments, markov_models, digital_twins, scenarios, scenario_segments, simulation_runs)
    - 데이터베이스 연결 설정 (`app/database.py`)
    - Alembic 마이그레이션 초기 설정
    - _Requirements: 전체 (데이터 영속성)_

- [x] 2. 레이어 1: 데이터 수집 & 프로파일링 — Upload Service
  - [x] 2.1 파일 검증 로직 구현 (`app/services/upload_service.py`)
    - `validate_file()`: 파일 크기 100MB 제한, 파일 형식(CSV/JSON) 검증
    - 필수 필드(user_id, session_id, event_type, timestamp) 누락 검증
    - timestamp ISO 8601 형식 검증
    - _Requirements: 1.3, 1.4, 1.5_
  - [x] 2.2 CSV/JSON 파싱 및 직렬화 구현
    - `parse_csv()`, `parse_json()`, `serialize_to_csv()`, `serialize_to_json()` 구현
    - _Requirements: 1.1, 1.2, 11.1~11.5_
  - [ ]* 2.3 Property 테스트: CSV 라운드트립
    - **Property 1: CSV 파싱-직렬화 라운드트립**
    - **Validates: Requirements 11.1, 11.3, 11.5, 1.1**
  - [ ]* 2.4 Property 테스트: JSON 라운드트립
    - **Property 2: JSON 파싱-직렬화 라운드트립**
    - **Validates: Requirements 11.2, 11.4, 11.5, 1.2**
  - [ ]* 2.5 Property 테스트: 필수 필드 누락 검증
    - **Property 3: 필수 필드 누락 검증**
    - **Validates: Requirements 1.3**
  - [ ]* 2.6 Property 테스트: 비-ISO8601 timestamp 검증
    - **Property 4: 비-ISO8601 timestamp 검증**
    - **Validates: Requirements 1.4**
  - [x] 2.7 업로드 요약 정보 생성 구현
    - `upload_file()`: 파일 업로드 → 검증 → 파싱 → DB 저장 → 요약 반환
    - _Requirements: 1.6_
  - [ ]* 2.8 Property 테스트: 업로드 요약 정확성
    - **Property 5: 업로드 요약 정확성**
    - **Validates: Requirements 1.6**
  - [x] 2.9 Upload API 엔드포인트 구현 (`app/api/upload.py`)
    - `POST /api/upload`, `GET /api/upload/{id}/summary`
    - _Requirements: 1.1~1.6_

- [x] 3. 레이어 1: 데이터 수집 & 프로파일링 — Profiling Engine
  - [x] 3.1 유저 프로파일 생성 엔진 구현 (`app/services/profiling_engine.py`)
    - `compute_demographics()`, `compute_behavior()`, `compute_preferences()`, `extract_journey_patterns()`, `generate_profiles()` 구현
    - 이벤트 3건 미만 유저는 "insufficient_data" 상태로 표시하고 제외
    - _Requirements: 2.1~2.6_
  - [ ]* 3.2 Property 테스트: 유저 프로파일 생성 완전성
    - **Property 6: 유저 프로파일 생성 완전성**
    - **Validates: Requirements 2.1~2.5**
  - [ ]* 3.3 Property 테스트: 이벤트 부족 유저 필터링
    - **Property 7: 이벤트 부족 유저 필터링**
    - **Validates: Requirements 2.6**
  - [x] 3.4 Profiling API 엔드포인트 구현 (`app/api/profiles.py`)
    - `POST /api/profiles/generate`, `GET /api/profiles`
    - _Requirements: 2.1~2.6_

- [x] 4. 체크포인트 — 레이어 1 완료 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

- [x] 5. 레이어 2: 디지털 트윈 엔진 — Segmentation Engine
  - [x] 5.1 세그먼테이션 엔진 구현 (`app/services/segmentation_engine.py`)
    - `build_feature_matrix()`, `find_optimal_k()`, `cluster_profiles()`, `generate_segment_summary()` 구현
    - 유효 프로파일 10개 미만 시 오류 반환
    - _Requirements: 3.1~3.5_
  - [ ]* 5.2 Property 테스트: 세그먼트 클러스터링 불변 속성
    - **Property 8: 세그먼트 클러스터링 불변 속성**
    - **Validates: Requirements 3.1, 3.2, 3.4**
  - [x] 5.3 Segmentation API 엔드포인트 구현 (`app/api/segments.py`)
    - `POST /api/segments/cluster`, `GET /api/segments`
    - _Requirements: 3.1~3.5_

- [x] 6. 레이어 2: 디지털 트윈 엔진 — Markov Chain & Twin Generator
  - [x] 6.1 Markov Chain 모델 빌더 구현 (`app/services/markov_builder.py`)
    - `build_model()`, `normalize_transitions()`, `get_default_model()` 구현
    - _Requirements: 4.1~4.5_
  - [ ]* 6.2 Property 테스트: Markov Chain 전이 확률 정규화
    - **Property 9: Markov Chain 전이 확률 정규화**
    - **Validates: Requirements 4.2, 4.3**
  - [x] 6.3 디지털 트윈 생성기 구현 (`app/services/twin_generator.py`)
    - `generate_twins()`, `assign_demographics()` 구현
    - _Requirements: 5.1~5.5_
  - [ ]* 6.4 Property 테스트: 디지털 트윈 세그먼트 비율 분배
    - **Property 10: 디지털 트윈 세그먼트 비율 분배**
    - **Validates: Requirements 5.1~5.3**
  - [x] 6.5 Twin API 엔드포인트 구현 (`app/api/twins.py`)
    - `POST /api/twins/generate`, `GET /api/twins/summary`
    - _Requirements: 5.1~5.5_

- [x] 7. 체크포인트 — 레이어 2 완료 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

- [x] 8. 시나리오별 주요 변수 자동 도출
  - [x] 8.1 ScenarioVariableResolver 구현 (`app/services/scenario_variable_resolver.py`)
    - `SCENARIO_VARIABLE_MAP` 상수 정의: promotion, cta_change, price_display, funnel_change, ui_position, timing 유형별 기본 변수 매핑
    - `resolve_key_variables(scenario_type, user_specified_variables)`: 시나리오 유형 → 주요 변수 자동 도출, 사용자 지정 key_variables가 있으면 우선 사용
    - `get_default_variables(scenario_type)`: 시나리오 유형별 기본 변수 매핑 반환
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
  - [ ]* 8.2 Property 테스트: 시나리오 유형별 주요 변수 자동 도출
    - **Property 19: 시나리오 유형별 주요 변수 자동 도출**
    - **Validates: Requirements 13.1, 13.3, 13.4**

- [x] 9. 시나리오별 동적 세그먼트 재구성
  - [x] 9.1 SegmentationEngine 확장 — recluster_for_scenario 구현 (`app/services/segmentation_engine.py`)
    - `build_feature_matrix()`에 `selected_variables: list[str] | None` 파라미터 추가하여 지정된 변수만 피처로 사용
    - `recluster_for_scenario(profiles, key_variables, scenario_id)`: key_variables만으로 K-Means 재클러스터링, Scenario_Segment 생성 (scenario_id 참조)
    - 각 Scenario_Segment에 사용된 key_variables 목록, 구성원 수, 해당 변수 평균값 포함
    - Silhouette Score 기반 최적 클러스터 수 결정 (2~10개) 적용
    - DB `scenario_segments` 테이블에 저장
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  - [ ]* 9.2 Property 테스트: 시나리오 전용 세그먼트 재구성 불변 속성
    - **Property 20: 시나리오 전용 세그먼트 재구성 불변 속성**
    - **Validates: Requirements 14.1, 14.3, 14.4**

- [x] 10. 체크포인트 — 변수 도출 & 동적 세그먼트 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

- [x] 11. 레이어 3: A/B 테스트 시뮬레이터 — 시나리오 & Reaction Model
  - [x] 11.1 시나리오 관리 및 Reaction Model 구현 (`app/services/scenario_manager.py`, `app/services/reaction_model.py`)
    - `create_scenario()`: 시나리오 생성 (이름, 대상 페이지, Variant 최대 5개, 반응 규칙, 주요 측정 지표, key_variables, analysis_tags, analysis_dimensions 포함)
    - 시나리오 유형 지원: CTA 텍스트 변경, 가격 표시 방식 변경, Funnel 단계 변경, UI 요소 위치 변경, 노출 타이밍 변경, 프로모션 변경
    - `ReactionModel.evaluate()`, `get_segment_rules()`, `apply_default_reaction()` 구현
    - _Requirements: 6.1~6.8_
  - [ ]* 11.2 Property 테스트: 시나리오 분석 태그 라운드트립
    - **Property 16: 시나리오 분석 태그 및 분류 조건 라운드트립**
    - **Validates: Requirements 6.6, 6.7**

- [x] 12. 레이어 3: A/B 테스트 시뮬레이터 — Simulation Engine
  - [x] 12.1 시뮬레이션 실행 엔진 구현 (`app/services/simulation_engine.py`)
    - `assign_variants()`: 디지털 트윈을 variant별로 균등 무작위 분배
    - `simulate_session()`: 단일 트윈의 Markov Chain 기반 세션 시뮬레이션, 대상 페이지 도달 시 Reaction_Model 적용
    - `run_simulation()`: 전체 시뮬레이션 실행, 진행 상태 백분율 제공, variant별 전환율/평균 세션 시간/퍼널 이탈률 집계
    - `compute_weighted_conversion_rate()`: 세그먼트 비율 기반 가중 전환율 계산
    - `analyze_by_tags()`: 분석 태그별 트윈 재그룹핑 및 전환율 비교 결과 산출 (classification_rules 적용 또는 속성 값 직접 사용)
    - _Requirements: 7.1~7.7_
  - [ ]* 12.2 Property 테스트: Variant 균등 분배
    - **Property 11: Variant 균등 분배**
    - **Validates: Requirements 7.1**
  - [ ]* 12.3 Property 테스트: 시뮬레이션 세션 유효성
    - **Property 12: 시뮬레이션 세션 유효성**
    - **Validates: Requirements 7.2, 7.3, 7.4**
  - [ ]* 12.4 Property 테스트: 가중 전환율 계산 정확성
    - **Property 13: 가중 전환율 계산 정확성**
    - **Validates: Requirements 7.6**
  - [ ]* 12.5 Property 테스트: 분석 태그 그룹핑 불변 속성
    - **Property 14: 분석 태그 그룹핑 불변 속성**
    - **Validates: Requirements 7.7**

- [x] 13. 레이어 3: A/B 테스트 시뮬레이터 — Statistics Analyzer & Report
  - [x] 13.1 통계 분석기 구현 (`app/services/statistics_analyzer.py`)
    - `chi_square_test()`: 카이제곱 검정 수행 (SciPy `chi2_contingency`)
    - `compute_confidence_interval()`: 95% 신뢰구간 계산
    - `compute_cohens_h()`: Cohen's h 효과 크기 계산
    - `analyze_by_segment()`: 세그먼트별 분리 분석, 전체 전환율은 세그먼트 비율 기반 가중 평균
    - `find_best_variant_per_segment()`: 각 세그먼트 최고 전환율 variant 식별
    - `compute_weighted_overall_rate()`: variant별 전체 가중 전환율 계산
    - `generate_report_summary()`: MVP 리포트 요약 생성 (한 줄 결론, 추천, 승자 variant, 유의성 여부)
    - _Requirements: 8.1~8.5, 9.1, 9.7, 9.8_
  - [ ]* 13.2 Property 테스트: 세그먼트 볼륨 비율 합 불변
    - **Property 15: 세그먼트 볼륨 비율 합 불변**
    - **Validates: Requirements 9.2**
  - [ ]* 13.3 Property 테스트: 리포트 요약 필수 필드 완전성
    - **Property 17: 리포트 요약 필수 필드 완전성**
    - **Validates: Requirements 9.1, 9.8**
  - [x] 13.4 Simulation API 엔드포인트 구현 (`app/api/simulations.py`)
    - `POST /api/simulations/scenarios` — 시나리오 생성
    - `POST /api/simulations/run` — 시뮬레이션 실행
    - `GET /api/simulations/{id}/results` — 결과 조회
    - `GET /api/simulations/{id}/stats` — 통계 검정 결과 조회
    - `GET /api/simulations/{id}/report` — MVP 리포트 조회 (7개 섹션)
    - _Requirements: 6.1~6.8, 7.1~7.7, 8.1~8.5, 9.1~9.8_

- [x] 14. 체크포인트 — 레이어 3 완료 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

- [x] 15. 파이프라인 오케스트레이션
  - [x] 15.1 PipelineOrchestrator 구현 (`app/services/pipeline_orchestrator.py`)
    - `step1_upload(file)`: 파일 업로드 → UploadService.upload_file() → ProfilingEngine.generate_profiles() → SegmentationEngine.cluster_profiles() → PipelineUploadResult 반환 (upload_summary, profile_count, excluded_user_count, base_segments, base_segment_count)
    - `step2_simulate(config: PipelineSimulateConfig)`: 시나리오 입력 → ScenarioVariableResolver.resolve_key_variables() → ScenarioManager.create_scenario() → SegmentationEngine.recluster_for_scenario() → MarkovChainBuilder.build_model() (세그먼트별) → TwinGenerator.generate_twins() → SimulationEngine.run_simulation() → StatisticsAnalyzer → PipelineSimulateResult 반환
    - Markov 폴백 로직: 시나리오 세그먼트의 세션 데이터 부족 시 기본 세그먼트의 Markov 모델 사용
    - 오류 처리: 실패 시 실패 단계명(stage) + 오류 메시지 포함 응답 반환
    - _Requirements: 15.1, 15.2, 15.4, 15.5_
  - [x] 15.2 Pipeline API 엔드포인트 구현 (`app/api/pipeline.py`)
    - `POST /api/pipeline/upload` — 스텝 1: 데이터 업로드 + 프로파일링 + 기본 세그먼트 자동 생성
    - `POST /api/pipeline/simulate` — 스텝 2: 시나리오 입력 + 변수 도출 + 맞춤 세그먼트 + Markov + 트윈 + 시뮬레이션 + 리포트
    - 기존 개별 API 유지 확인 (고급 사용자용)
    - _Requirements: 15.1, 15.2, 15.3_
  - [ ]* 15.3 Property 테스트: 파이프라인 오류 시 실패 단계 보고
    - **Property 21: 파이프라인 오류 시 실패 단계 보고**
    - **Validates: Requirements 15.4**

- [x] 16. 체크포인트 — 파이프라인 통합 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

- [x] 17. 샘플 데이터 생성 및 MVP 시나리오
  - [x] 17.1 무신사 샘플 데이터 생성기 구현 (`app/services/sample_data_generator.py`)
    - `generate_sample_data()`: 무신사 패션 이커머스 가정 현실적 이벤트 로그 생성
    - 페이지 구조: `/home`, `/category/men`, `/category/women`, `/category/shoes`, `/product/{id}`, `/cart`, `/checkout`, `/order-complete`
    - 이벤트 유형: page_view, click, scroll, purchase, add_to_cart, wishlist, coupon_apply
    - 4가지 유저 행동 유형 반영: 가격 민감형(~30%), 브랜드 충성형(~25%), 탐색형(~25%), 충동 구매형(~20%)
    - 다양한 device/os/locale 분포, 세션 내 이벤트 시간순 정렬 보장, CSV/JSON 형식 지원
    - _Requirements: 10.1~10.7_
  - [ ]* 17.2 Property 테스트: 샘플 데이터 페이지 경로 유효성
    - **Property 18: 샘플 데이터 페이지 경로 유효성**
    - **Validates: Requirements 10.6**
  - [x] 17.3 MVP 무신사 프로모션 시나리오 구현
    - 기본 제공 시나리오: "무신사 프로모션 A/B 테스트" — Variant A: "오늘만 전제품 20% 할인", Variant B: "오늘만 무료배송 + 5% 적립금 제공"
    - 대상 페이지: `/home`, 주요 측정 지표: `purchase_conversion_rate`
    - 기본 분석 태그: `price_sensitivity` (high/medium/low), `device` (mobile/desktop), `visit_frequency` (heavy/light)
    - 세그먼트별 차별 반응 규칙: 가격 민감형 → Variant A 높은 전환율, 브랜드 충성형 → Variant B 높은 전환율
    - _Requirements: 12.1~12.5_
  - [x] 17.4 Sample Data API 엔드포인트 구현 (`app/api/sample_data.py`)
    - `POST /api/sample-data/generate` — 샘플 데이터 생성
    - `POST /api/sample-data/musinsa` — 무신사 샘플 데이터 + MVP 시나리오 일괄 생성
    - _Requirements: 10.1~10.7, 12.1~12.5_

- [x] 18. 체크포인트 — 백엔드 전체 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

- [x] 19. React 프론트엔드 구현
  - [x] 19.1 프론트엔드 기본 구조 및 API 클라이언트 설정
    - React 앱 기본 구조, 라우팅, API 클라이언트 설정
    - Pipeline API (`/api/pipeline/upload`, `/api/pipeline/simulate`) 클라이언트 함수 구현
    - 공통 레이아웃 및 네비게이션 컴포넌트
    - _Requirements: 9.1~9.8, 15.1~15.3_
  - [x] 19.2 스텝 1: 데이터 업로드 페이지 구현
    - 파일 업로드 UI (CSV/JSON 드래그앤드롭)
    - `POST /api/pipeline/upload` 호출 → 업로드 요약 + 프로파일 수 + 기본 세그먼트 수 표시
    - 샘플 데이터 생성 버튼 (무신사 시나리오 원클릭)
    - _Requirements: 1.1~1.6, 15.1, 10.1~10.7_
  - [x] 19.3 스텝 2: 시나리오 입력 및 시뮬레이션 실행 페이지 구현
    - 시나리오 생성 폼 (시나리오 유형, Variant 정의, 반응 규칙, 분석 태그/분류 조건 설정)
    - `POST /api/pipeline/simulate` 호출 → 진행 상태 표시 → 결과 페이지로 이동
    - MVP 시나리오 빠른 실행 버튼
    - _Requirements: 6.1~6.8, 13.1~13.5, 15.2_
  - [x] 19.4 스텝 3: 결과 시각화 대시보드 구현 (Recharts)
    - MVP 리포트 7개 섹션 렌더링: 실험 요약, 핵심 지표 비교 테이블, 세그먼트별 전환율 히트맵(볼륨 비율 표시), 분석 태그별 전환율 비교 차트, 퍼널 이탈률 비교 차트, 통계 검정 결과(신뢰구간 그래프), 세그먼트별 최적 Variant
    - 시나리오 세그먼트 결과(메인) + 기본 세그먼트 결과(참고용) 탭 전환
    - 세그먼트 필터링 기능, 분석 태그 미지정 시 해당 섹션 생략
    - 가중 평균 계산 방식 명시
    - _Requirements: 9.1~9.8, 14.5, 14.6_

- [x] 20. 최종 체크포인트 — 전체 시스템 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의.

## Notes

- `*` 표시된 태스크는 선택 사항이며 빠른 MVP를 위해 건너뛸 수 있습니다.
- 각 태스크는 특정 요구사항을 참조하여 추적 가능합니다.
- 체크포인트는 레이어별 점진적 검증을 보장합니다.
- Property 테스트는 설계 문서의 21개 Correctness Properties를 검증합니다.
- 태스크 순서: 완료된 레이어 1~2 → 변수 도출/동적 세그먼트 → 시뮬레이션/통계 → 파이프라인 → 샘플 데이터 → 프론트엔드
