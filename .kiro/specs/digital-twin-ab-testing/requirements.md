# 요구사항 문서: 디지털 트윈 기반 A/B 테스트 시뮬레이션 서비스

## 소개

디지털 트윈 기반 A/B 테스트 시뮬레이션 서비스는 실제 사용자 행동 데이터를 기반으로 가상 유저(디지털 트윈)를 생성하고, 이를 활용하여 A/B 테스트를 시뮬레이션하는 MVP 서비스이다. 기존 LLM 기반 정성적 피드백 서비스와 달리, 실제 행동 데이터 기반 정량적 시뮬레이션과 세그먼트별 차별 반응 분석에 집중한다.

### MVP 사용자 경험: 3스텝 플로우

사용자는 "데이터 올리고 → 시나리오 적고 → 결과 보기" 3스텝으로 서비스를 이용한다:

```
1. 데이터 업로드 (CSV/JSON)
     ↓ 자동: 파싱 + 프로파일링 + 기본 세그먼트 생성 (캐시)
2. 시나리오 입력 (무엇을 테스트할 것인가)
     ↓ 자동: 주요 변수 도출 → 시나리오 맞춤 세그먼트 생성 → Markov Chain 학습 → 트윈 생성 → 시뮬레이션 + 통계 검정
3. 결과 리포트 출력
```

중간 단계(프로파일링, 세그먼테이션, Markov 학습, 트윈 생성 등)는 파이프라인 오케스트레이션 레이어가 자동으로 실행하며, 사용자가 개별적으로 트리거할 필요가 없다.

### 시스템 구성

서비스는 3개 레이어 + 파이프라인 오케스트레이션으로 구성된다:
1. **데이터 수집 & 프로파일링** — CSV/JSON 파일 업로드를 통한 이벤트 로그 수집 및 유저 프로파일 자동 생성
2. **디지털 트윈 엔진** — Markov Chain 기반 행동 모델과 규칙 기반 반응 모델로 가상 유저 생성
3. **A/B 테스트 시뮬레이터** — 가상 유저 집단에 variant를 노출하고 통계적으로 결과를 비교
4. **파이프라인 오케스트레이션** — 위 3개 레이어를 자동으로 연결하여 3스텝 UX를 제공하는 오케스트레이션 레이어

### 하이브리드 세그먼트 전략

- **기본 세그먼트**: 데이터 업로드 시 전체 피처로 자동 생성 (캐시, 폴백, 비교용)
- **시나리오 세그먼트**: 시나리오 입력 시 주요 변수만으로 동적 생성 (메인 시뮬레이션용)
- **리포트**: 시나리오 세그먼트 결과(메인) + 기본 세그먼트 결과(참고용) 모두 포함

## 용어 사전

- **Event_Log**: 사용자의 행동을 기록한 원시 데이터. user_id, session_id, event_type, timestamp, page, element, element_text, conversion_type, value, device, os, scroll_depth_pct 등의 필드를 포함한다.
- **User_Profile**: Event_Log를 유저별로 집계하여 생성된 프로파일. demographics, behavior, preferences, journey_patterns 섹션으로 구성된다.
- **Segment**: 유사한 행동 패턴과 속성을 가진 User_Profile의 클러스터 그룹.
- **Digital_Twin**: Segment별 Markov Chain 행동 모델과 규칙 기반 반응 모델을 결합하여 생성된 가상 유저 인스턴스.
- **Markov_Chain_Model**: 상태 전이 확률 행렬을 기반으로 유저의 페이지 간 이동 패턴을 모델링하는 확률 모델.
- **Reaction_Model**: 특정 UI 변경(variant)에 대한 Digital_Twin의 반응을 결정하는 규칙 기반 모델.
- **Variant**: A/B 테스트에서 비교 대상이 되는 UI 또는 기능의 변형. Control(기존)과 Treatment(변경)로 구분된다.
- **Simulation_Run**: 특정 A/B 테스트 시나리오에 대해 Digital_Twin 집단을 대상으로 수행하는 한 번의 시뮬레이션 실행.
- **Conversion_Event**: 구매, 회원가입 등 비즈니스 목표 달성을 나타내는 이벤트.
- **Funnel**: 사용자가 최종 Conversion_Event에 도달하기까지 거치는 단계별 경로.
- **Upload_Service**: Event_Log 파일의 업로드, 검증, 파싱을 담당하는 서비스 컴포넌트.
- **Profiling_Engine**: Event_Log를 분석하여 User_Profile을 자동 생성하는 엔진.
- **Segmentation_Engine**: User_Profile을 클러스터링하여 Segment를 생성하는 엔진.
- **Twin_Engine**: Segment 데이터를 기반으로 Digital_Twin을 생성하고 관리하는 엔진.
- **Simulation_Engine**: A/B 테스트 시뮬레이션을 실행하고 결과를 산출하는 엔진.
- **Statistics_Analyzer**: 시뮬레이션 결과에 대한 통계적 유의성 검정 및 분석을 수행하는 컴포넌트.
- **Scenario_Variable_Resolver**: 시나리오 유형을 분석하여 실험에 영향을 미치는 주요 행동 변수를 자동 도출하는 컴포넌트.
- **Scenario_Segment**: 시나리오별로 도출된 주요 행동 변수를 기반으로 동적으로 재구성된 세그먼트. 기본 Segment와 별도로 생성되며, 해당 시나리오의 시뮬레이션에 사용된다.
- **Pipeline_Orchestrator**: 데이터 업로드부터 시뮬레이션 결과까지의 전체 파이프라인을 자동으로 오케스트레이션하는 컴포넌트. 3스텝 UX(업로드 → 시나리오 → 결과)를 제공한다.

## 요구사항

### 요구사항 1: 이벤트 로그 파일 업로드 및 검증

**사용자 스토리:** 데이터 분석가로서, 이벤트 로그 파일을 업로드하여 시뮬레이션에 필요한 원시 데이터를 시스템에 제공하고 싶다.

#### 수용 기준

1. WHEN 사용자가 CSV 형식의 Event_Log 파일을 업로드하면, THE Upload_Service SHALL 파일을 파싱하여 각 행을 이벤트 레코드로 변환한다.
2. WHEN 사용자가 JSON 형식의 Event_Log 파일을 업로드하면, THE Upload_Service SHALL 파일을 파싱하여 각 객체를 이벤트 레코드로 변환한다.
3. WHEN 업로드된 파일에 필수 필드(user_id, session_id, event_type, timestamp)가 누락된 경우, THE Upload_Service SHALL 누락된 필드명을 포함한 검증 오류 메시지를 반환한다.
4. WHEN 업로드된 파일의 timestamp 필드가 ISO 8601 형식이 아닌 경우, THE Upload_Service SHALL 해당 행 번호와 함께 형식 오류 메시지를 반환한다.
5. IF 업로드된 파일의 크기가 100MB를 초과하면, THEN THE Upload_Service SHALL "파일 크기가 100MB 제한을 초과합니다"라는 오류 메시지를 반환한다.
6. WHEN 파일 검증이 성공적으로 완료되면, THE Upload_Service SHALL 총 이벤트 수, 고유 사용자 수, 데이터 기간을 포함한 요약 정보를 반환한다.

### 요구사항 2: 유저 프로파일 자동 생성

**사용자 스토리:** 데이터 분석가로서, 업로드된 이벤트 로그로부터 유저 프로파일이 자동으로 생성되어 각 사용자의 행동 특성을 파악하고 싶다.

#### 수용 기준

1. WHEN Event_Log 업로드가 완료되면, THE Profiling_Engine SHALL 각 고유 user_id에 대해 하나의 User_Profile을 자동 생성한다.
2. THE Profiling_Engine SHALL 각 User_Profile의 demographics 섹션에 device, os, locale 정보를 집계한다.
3. THE Profiling_Engine SHALL 각 User_Profile의 behavior 섹션에 avg_session_duration, avg_pages_per_session, conversion_rate, bounce_rate를 계산하여 포함한다.
4. THE Profiling_Engine SHALL 각 User_Profile의 preferences 섹션에 top_pages, top_categories, price_sensitivity를 분석하여 포함한다.
5. THE Profiling_Engine SHALL 각 User_Profile의 journey_patterns 섹션에 세션별 페이지 이동 경로를 패턴별 빈도로 집계한다.
6. WHEN 특정 user_id의 이벤트 수가 3건 미만인 경우, THE Profiling_Engine SHALL 해당 유저를 "insufficient_data" 상태로 표시하고 프로파일 생성에서 제외한다.

### 요구사항 3: 유저 세그먼트 클러스터링

**사용자 스토리:** 데이터 분석가로서, 유사한 행동 패턴을 가진 사용자들을 자동으로 그룹화하여 세그먼트별 차별 반응을 분석하고 싶다.

#### 수용 기준

1. WHEN User_Profile 생성이 완료되면, THE Segmentation_Engine SHALL behavior 및 demographics 특성을 기반으로 User_Profile을 클러스터링한다.
2. THE Segmentation_Engine SHALL 클러스터링 알고리즘으로 K-Means를 사용하고, 최적 클러스터 수를 Silhouette Score 기반으로 자동 결정한다.
3. THE Segmentation_Engine SHALL 각 Segment에 대해 구성원 수, 평균 행동 지표, 대표 demographics 정보를 포함한 요약을 생성한다.
4. THE Segmentation_Engine SHALL 최소 2개에서 최대 10개 사이의 Segment를 생성한다.
5. IF 유효한 User_Profile 수가 10개 미만인 경우, THEN THE Segmentation_Engine SHALL "세그먼트 생성에 충분한 프로파일이 없습니다. 최소 10개의 유효 프로파일이 필요합니다"라는 오류 메시지를 반환한다.

### 요구사항 4: Markov Chain 행동 모델 학습

**사용자 스토리:** 시스템 운영자로서, 각 세그먼트의 행동 패턴을 확률 모델로 학습하여 디지털 트윈이 실제 사용자와 유사하게 행동하도록 하고 싶다.

#### 수용 기준

1. WHEN Segment 생성이 완료되면, THE Twin_Engine SHALL 각 Segment에 대해 페이지 간 전이 확률을 나타내는 Markov_Chain_Model을 학습한다.
2. THE Twin_Engine SHALL Markov_Chain_Model의 상태를 Event_Log의 고유 page 값들과 "session_start", "session_end" 상태로 정의한다.
3. THE Twin_Engine SHALL 각 상태 전이 확률의 합이 1.0이 되도록 정규화한다.
4. THE Twin_Engine SHALL 학습된 Markov_Chain_Model의 상태 전이 행렬을 JSON 형식으로 저장한다.
5. WHEN 특정 Segment의 세션 데이터가 5건 미만인 경우, THE Twin_Engine SHALL 해당 Segment에 대해 전체 데이터의 평균 전이 확률을 기본값으로 사용한다.

### 요구사항 5: 디지털 트윈 생성

**사용자 스토리:** 데이터 분석가로서, 실제 사용자 분포를 반영한 대량의 디지털 트윈을 생성하여 통계적으로 유의미한 시뮬레이션을 수행하고 싶다.

#### 수용 기준

1. WHEN 사용자가 생성할 Digital_Twin 수를 지정하면, THE Twin_Engine SHALL 각 Segment의 비율에 따라 Digital_Twin을 분배 생성한다.
2. THE Twin_Engine SHALL 각 Digital_Twin에 고유 식별자, 소속 Segment, Markov_Chain_Model 참조, demographics 속성을 부여한다.
3. THE Twin_Engine SHALL 각 Digital_Twin의 demographics 속성을 해당 Segment의 분포에 따라 확률적으로 할당한다.
4. THE Twin_Engine SHALL 최소 100개에서 최대 100,000개의 Digital_Twin 생성을 지원한다.
5. WHEN Digital_Twin 생성이 완료되면, THE Twin_Engine SHALL Segment별 생성 수, 총 생성 수, 생성 소요 시간을 포함한 요약을 반환한다.

### 요구사항 6: A/B 테스트 시나리오 정의

**사용자 스토리:** 데이터 분석가로서, 다양한 A/B 테스트 시나리오를 정의하여 UI 변경의 효과를 시뮬레이션하고 싶다.

#### 수용 기준

1. THE Simulation_Engine SHALL 다음 시나리오 유형을 지원한다: CTA 텍스트 변경, 가격 표시 방식 변경, Funnel 단계 변경, UI 요소 위치 변경, 노출 타이밍 변경, 프로모션 변경.
2. WHEN 사용자가 시나리오를 정의하면, THE Simulation_Engine SHALL 시나리오 이름, 대상 페이지, Control Variant 설명, Treatment Variant 설명, 주요 측정 지표를 포함한 시나리오 객체를 생성한다.
3. THE Simulation_Engine SHALL 각 시나리오에 대해 Segment별 예상 반응 규칙을 Reaction_Model로 정의할 수 있도록 한다.
4. WHEN Reaction_Model이 정의되지 않은 Segment가 있는 경우, THE Simulation_Engine SHALL 전체 평균 반응률을 기본값으로 적용한다.
5. THE Simulation_Engine SHALL 하나의 Simulation_Run에서 최대 5개의 Variant를 비교할 수 있도록 지원한다.
6. WHEN 사용자가 시나리오를 정의할 때, THE Simulation_Engine SHALL 분석 태그(analysis_tags) 목록을 선택적으로 지정할 수 있도록 한다. 분석 태그는 시뮬레이션 결과를 기본 세그먼트 외에 추가적인 관점(예: device, conversion_rate_tier, price_sensitivity_tier, purchase_frequency)으로 재그룹핑하여 분석할 수 있게 한다.
7. WHEN 사용자가 분석 태그를 지정할 때, THE Simulation_Engine SHALL 각 태그에 대해 분류 조건(analysis_dimensions)을 정의할 수 있도록 한다. 분류 조건은 태그명과 그룹 분류 규칙의 매핑이다 (예: `price_sensitivity: {high: ">0.7", medium: "0.3~0.7", low: "<0.3"}`, `device: {mobile: "mobile", desktop: "desktop"}`).
8. WHEN 분석 태그에 분류 조건이 지정되지 않은 경우, THE Simulation_Engine SHALL 디지털 트윈의 demographics/behavior 속성 값을 그대로 그룹 키로 사용한다.

### 요구사항 13: 시나리오별 주요 행동 변수 자동 도출

**사용자 스토리:** 데이터 분석가로서, 실험 시나리오를 정의하면 해당 실험에 영향을 미치는 주요 행동 변수가 자동으로 도출되어, 실험 목적에 최적화된 세그먼트로 분석하고 싶다.

#### 수용 기준

1. WHEN 사용자가 시나리오를 정의하면, THE Scenario_Variable_Resolver SHALL 시나리오 유형(scenario_type)을 분석하여 해당 실험에 영향을 미치는 주요 행동 변수(key_variables) 목록을 자동 도출한다.
2. THE Scenario_Variable_Resolver SHALL 다음 시나리오 유형별 기본 변수 매핑을 제공한다: (1) promotion → price_sensitivity, coupon_apply_rate, avg_purchase_value, purchase_frequency, (2) cta_change → conversion_rate, bounce_rate, avg_pages_per_session, click_through_rate, (3) price_display → price_sensitivity, conversion_rate, avg_purchase_value, (4) funnel_change → funnel_completion_rate, bounce_rate, avg_session_duration, (5) ui_position → scroll_depth, avg_pages_per_session, bounce_rate, (6) timing → visit_frequency, avg_session_duration, bounce_rate.
3. WHEN 사용자가 시나리오 정의 시 key_variables를 직접 지정하면, THE Scenario_Variable_Resolver SHALL 자동 도출된 변수 대신 사용자 지정 변수를 사용한다.
4. WHEN 사용자가 시나리오 정의 시 key_variables를 지정하지 않으면, THE Scenario_Variable_Resolver SHALL 시나리오 유형 기반으로 자동 도출된 변수를 사용한다.
5. THE Scenario_Variable_Resolver SHALL 도출된 key_variables 목록을 시나리오 객체에 포함하여 저장한다.

### 요구사항 14: 시나리오별 동적 세그먼트 재구성

**사용자 스토리:** 데이터 분석가로서, 실험 시나리오에 맞는 주요 행동 변수를 기반으로 고객 세그먼트가 동적으로 재구성되어, 실험 목적에 최적화된 세그먼트별 결과를 확인하고 싶다.

#### 수용 기준

1. WHEN 시나리오의 key_variables가 도출되면, THE Segmentation_Engine SHALL 해당 변수들만을 피처로 사용하여 K-Means 클러스터링을 재실행하고, 시나리오 전용 Scenario_Segment를 생성한다.
2. THE Segmentation_Engine SHALL 시나리오 전용 Scenario_Segment를 기본 Segment와 별도로 저장하며, scenario_id를 참조하여 연결한다.
3. THE Segmentation_Engine SHALL Scenario_Segment 생성 시에도 Silhouette Score 기반 최적 클러스터 수 결정(2~10개)을 적용한다.
4. THE Segmentation_Engine SHALL 각 Scenario_Segment에 대해 사용된 key_variables 목록, 구성원 수, 해당 변수들의 평균값을 포함한 요약을 생성한다.
5. WHEN 시뮬레이션이 실행되면, THE Simulation_Engine SHALL 기본 Segment 대신 해당 시나리오의 Scenario_Segment를 기반으로 디지털 트윈을 분배하고 시뮬레이션을 수행한다.
6. THE Simulation_Engine SHALL 시뮬레이션 결과 리포트에 기본 Segment 기반 결과와 Scenario_Segment 기반 결과를 모두 포함한다.

### 요구사항 15: 파이프라인 오케스트레이션 (3스텝 UX)

**사용자 스토리:** 데이터 분석가로서, 데이터 업로드부터 시뮬레이션 결과 확인까지 중간 단계를 개별적으로 트리거하지 않고 3스텝(업로드 → 시나리오 → 결과)으로 간편하게 이용하고 싶다.

#### 수용 기준

1. WHEN 사용자가 `POST /api/pipeline/upload`로 CSV/JSON 파일을 업로드하면, THE Pipeline SHALL 파일 파싱, 프로파일링, 기본 세그먼트 생성을 자동으로 한 번에 실행하고, 업로드 요약 + 프로파일 수 + 기본 세그먼트 수를 포함한 결과를 반환한다.
2. WHEN 사용자가 `POST /api/pipeline/simulate`로 시나리오를 입력하면, THE Pipeline SHALL 주요 변수 자동 도출 → 시나리오 맞춤 세그먼트 재구성 → Markov Chain 학습 → 디지털 트윈 생성 → 시뮬레이션 실행 → 통계 검정 → 리포트 생성을 자동으로 한 번에 실행하고, 최종 시뮬레이션 리포트를 반환한다.
3. THE Pipeline SHALL 기존 개별 API(`/api/upload`, `/api/profiles/generate`, `/api/segments/cluster`, `/api/twins/generate`, `/api/simulations/scenarios`, `/api/simulations/run`)를 고급 사용자용으로 유지한다.
4. WHEN 파이프라인 실행 중 특정 단계에서 오류가 발생하면, THE Pipeline SHALL 실패한 단계명과 오류 메시지를 포함한 응답을 반환한다.
5. WHEN Markov Chain 학습 시 시나리오 세그먼트의 세션 데이터가 부족하면, THE Pipeline SHALL 기본 세그먼트의 Markov 모델을 폴백으로 사용한다.

### 요구사항 7: A/B 테스트 시뮬레이션 실행

**사용자 스토리:** 데이터 분석가로서, 정의된 시나리오에 따라 디지털 트윈 집단을 대상으로 시뮬레이션을 실행하여 각 variant의 효과를 비교하고 싶다.

#### 수용 기준

1. WHEN 사용자가 시뮬레이션 실행을 요청하면, THE Simulation_Engine SHALL Digital_Twin 집단을 Variant별로 균등하게 무작위 분배한다.
2. THE Simulation_Engine SHALL 각 Digital_Twin에 대해 Markov_Chain_Model을 기반으로 세션 행동을 시뮬레이션한다.
3. WHEN Digital_Twin이 시나리오 대상 페이지에 도달하면, THE Simulation_Engine SHALL Reaction_Model을 적용하여 해당 Variant에 대한 반응(전환 여부)을 결정한다.
4. THE Simulation_Engine SHALL 각 Digital_Twin의 시뮬레이션 결과로 방문 페이지 시퀀스, 전환 여부, 세션 지속 시간을 기록한다.
5. THE Simulation_Engine SHALL 시뮬레이션 진행 상태를 백분율로 제공한다.
6. WHEN 시뮬레이션이 완료되면, THE Simulation_Engine SHALL Variant별 전환율, 평균 세션 지속 시간, Funnel 단계별 이탈률을 집계한다. 전체 전환율은 세그먼트별 전환율의 가중 평균으로 계산한다: `전체 전환율 = Σ(세그먼트 비율 × 세그먼트별 전환율)`, 여기서 세그먼트 비율 = 해당 세그먼트의 트윈 수 / 전체 트윈 수.
7. WHEN 시나리오에 분석 태그(analysis_tags)가 지정된 경우, THE Simulation_Engine SHALL 기본 세그먼트별 결과와 함께 각 분석 태그 기준으로 디지털 트윈을 재그룹핑하여 태그별 전환율 비교 결과를 산출한다. 재그룹핑은 트윈의 demographics/behavior 속성 또는 시나리오에 정의된 분류 조건(analysis_dimensions)을 기준으로 수행한다.

### 요구사항 8: 통계적 유의성 검정 및 결과 분석

**사용자 스토리:** 데이터 분석가로서, 시뮬레이션 결과의 통계적 유의성을 검증하여 신뢰할 수 있는 의사결정을 내리고 싶다.

#### 수용 기준

1. WHEN 시뮬레이션이 완료되면, THE Statistics_Analyzer SHALL Variant 간 전환율 차이에 대해 카이제곱 검정을 수행한다.
2. THE Statistics_Analyzer SHALL 검정 결과로 p-value, 신뢰구간(95%), 효과 크기(Cohen's h)를 산출한다.
3. WHEN p-value가 0.05 미만인 경우, THE Statistics_Analyzer SHALL 해당 결과를 "통계적으로 유의함"으로 표시한다.
4. THE Statistics_Analyzer SHALL Segment별로 분리된 전환율 비교 결과를 제공한다.
5. THE Statistics_Analyzer SHALL 각 Segment에서 가장 높은 전환율 차이를 보이는 Variant 조합을 식별하여 보고한다.

### 요구사항 9: 시뮬레이션 결과 시각화 및 MVP 리포트

**사용자 스토리:** 데이터 분석가로서, 시뮬레이션 결과를 직관적인 차트와 대시보드로 확인하여 인사이트를 빠르게 도출하고 싶다.

#### 수용 기준

1. WHEN 시뮬레이션 결과가 생성되면, THE Simulation_Engine SHALL 다음 7개 섹션을 포함한 MVP 리포트를 제공한다: (1) 실험 요약 — 한 줄 결론 + 추천 (예: "Variant B가 전체 전환율 12% 향상, 적용 권장"), (2) 핵심 지표 비교 테이블 — Variant별 전환율, 평균 세션 시간, 이탈률, (3) 세그먼트별 전환율 비교 히트맵 — 세그먼트 × Variant 히트맵 + 각 세그먼트의 볼륨 비율(%) 표시, (4) 분석 태그별 전환율 비교 — 각 analysis_tag 기준으로 그룹핑된 전환율 비교 차트, (5) 퍼널 단계별 이탈률 비교 — Variant별 퍼널 각 단계의 이탈률 비교, (6) 통계 검정 결과 — p-value, 95% 신뢰구간, Cohen's h 효과 크기, (7) 세그먼트별 최적 Variant 식별.
2. THE Simulation_Engine SHALL Segment별 전환율 비교를 히트맵 형태로 시각화하며, 각 세그먼트의 볼륨 비율을 함께 표시한다.
3. THE Simulation_Engine SHALL Funnel 단계별 이탈률을 Variant별로 비교하는 퍼널 차트를 제공한다.
4. THE Simulation_Engine SHALL 통계적 유의성 결과를 신뢰구간 그래프로 시각화한다.
5. WHEN 사용자가 특정 Segment를 선택하면, THE Simulation_Engine SHALL 해당 Segment의 상세 결과만 필터링하여 표시한다.
6. WHEN 시나리오에 분석 태그가 지정된 경우, THE Simulation_Engine SHALL 분석 태그별 전환율 비교 차트를 추가로 제공한다. 분석 태그가 지정되지 않은 경우 해당 섹션은 생략한다.
7. THE Simulation_Engine SHALL 전체 전환율을 세그먼트 비율 기반 가중 평균 방식으로 계산하며, 리포트에 계산 방식을 명시한다: `전체 전환율 = Σ(세그먼트 비율 × 세그먼트별 전환율)`.
8. THE Simulation_Engine SHALL 실험 요약 섹션에 통계적 유의성 여부, 승자 Variant, 전환율 차이(%), 추천 사항을 포함한다.

### 요구사항 10: 샘플 데이터 생성 (무신사 패션 이커머스)

**사용자 스토리:** 데이터 분석가로서, 실제 데이터 없이도 서비스를 체험할 수 있도록 무신사 패션 이커머스를 가정한 현실적인 샘플 이벤트 로그를 생성하고 싶다.

#### 수용 기준

1. WHEN 사용자가 샘플 데이터 생성을 요청하면, THE Upload_Service SHALL 지정된 사용자 수와 기간에 따라 무신사 패션 이커머스를 가정한 현실적인 Event_Log를 생성한다.
2. THE Upload_Service SHALL 생성된 샘플 Event_Log에 다양한 device(mobile, desktop, tablet), os(iOS, Android, Windows, macOS), locale 분포를 포함한다.
3. THE Upload_Service SHALL 생성된 샘플 Event_Log에 page_view, click, scroll, purchase, add_to_cart, wishlist, coupon_apply 등 패션 이커머스에 적합한 다양한 event_type을 포함한다.
4. THE Upload_Service SHALL 생성된 샘플 데이터에서 세션 내 이벤트 순서가 시간순으로 정렬되도록 보장한다.
5. THE Upload_Service SHALL 생성된 샘플 데이터를 CSV 또는 JSON 형식으로 다운로드할 수 있도록 제공한다.
6. THE Upload_Service SHALL 생성된 샘플 데이터의 페이지 경로에 무신사 패션 이커머스 페이지 구조를 반영한다: `/home`, `/category/men`, `/category/women`, `/category/shoes`, `/product/{id}`, `/cart`, `/checkout`, `/order-complete`.
7. THE Upload_Service SHALL 생성된 샘플 데이터에 다음 4가지 유저 행동 유형을 반영한다: (1) 가격 민감형 — 할인에 강하게 반응, 높은 쿠폰 적용률, (2) 브랜드 충성형 — 특정 카테고리 반복 방문, 높은 재구매율, (3) 탐색형 — 많은 페이지 조회, 낮은 전환율, 긴 세션, (4) 충동 구매형 — 짧은 세션, 높은 전환율, 적은 페이지 조회.

### 요구사항 12: MVP 테스트 시나리오 (무신사 프로모션 A/B 테스트)

**사용자 스토리:** 데이터 분석가로서, 무신사 프로모션 전략의 효과를 비교하기 위해 구체적인 A/B 테스트 시나리오를 실행하고 싶다.

#### 수용 기준

1. THE Simulation_Engine SHALL 다음 MVP 테스트 시나리오를 기본 제공한다: "무신사 프로모션 A/B 테스트" — Variant A (Control): "오늘만 전제품 20% 할인", Variant B (Treatment): "오늘만 무료배송 + 5% 적립금 제공".
2. THE Simulation_Engine SHALL MVP 시나리오의 대상 페이지를 `/home`으로 설정하고, 주요 측정 지표를 `purchase_conversion_rate`로 설정한다.
3. THE Simulation_Engine SHALL MVP 시나리오에 다음 분석 태그를 기본 포함한다: `price_sensitivity` (high/medium/low), `device` (mobile/desktop), `visit_frequency` (heavy/light).
4. THE Simulation_Engine SHALL MVP 시나리오의 Reaction_Model에 세그먼트별 차별 반응 규칙을 포함한다: 가격 민감형은 Variant A(할인)에 더 높은 전환율, 브랜드 충성형은 Variant B(적립금)에 더 높은 전환율.
5. WHEN MVP 시나리오 시뮬레이션이 완료되면, THE Simulation_Engine SHALL 기본 세그먼트별 결과와 분석 태그별 교차 분석 결과를 모두 포함한 리포트를 생성한다.

### 요구사항 11: 이벤트 로그 파싱 및 직렬화

**사용자 스토리:** 시스템 운영자로서, 이벤트 로그 데이터가 파싱과 직렬화 과정에서 손실 없이 정확하게 변환되도록 보장하고 싶다.

#### 수용 기준

1. THE Upload_Service SHALL Event_Log CSV 파일을 내부 이벤트 레코드 객체로 파싱한다.
2. THE Upload_Service SHALL Event_Log JSON 파일을 내부 이벤트 레코드 객체로 파싱한다.
3. THE Upload_Service SHALL 내부 이벤트 레코드 객체를 CSV 형식으로 직렬화하는 기능을 제공한다.
4. THE Upload_Service SHALL 내부 이벤트 레코드 객체를 JSON 형식으로 직렬화하는 기능을 제공한다.
5. FOR ALL 유효한 Event_Log 데이터에 대해, 파싱 후 직렬화한 결과를 다시 파싱하면 원본과 동일한 이벤트 레코드 객체가 생성되어야 한다 (라운드트립 속성).
