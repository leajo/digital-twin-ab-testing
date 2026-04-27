"""
Digital Twin A/B Testing — Streamlit 데모 앱 (Self-contained)
실제 트래픽 없이 디지털 트윈 기반 사전 시뮬레이션으로 A/B 테스트 결과를 예측합니다.

이 파일은 Streamlit Cloud 배포를 위해 모든 백엔드 로직을 인라인으로 포함합니다.
외부 로컬 모듈 임포트 없이 pip 패키지만 사용합니다.
"""

# === IMPORTS ===
import csv
import io
import json
import math
import os
import random
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


# ═══════════════════════════════════════════════════════════════════
# === DATA MODELS ===
# ═══════════════════════════════════════════════════════════════════

# --- Event Models ---

@dataclass
class EventRecord:
    """이벤트 로그의 단일 레코드."""
    user_id: str
    session_id: str
    event_type: str
    timestamp: datetime
    page: Optional[str] = None
    element: Optional[str] = None
    element_text: Optional[str] = None
    conversion_type: Optional[str] = None
    value: Optional[float] = None
    device: Optional[str] = None
    os: Optional[str] = None
    scroll_depth_pct: Optional[float] = None
    category: Optional[str] = None


@dataclass
class ErrorResponse:
    """공통 오류 응답 모델."""
    error_code: str
    message: str
    details: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# --- Profile Models ---

@dataclass
class Demographics:
    """유저 demographics 정보."""
    primary_device: str
    primary_os: str
    device_distribution: Dict[str, float] = field(default_factory=dict)
    os_distribution: Dict[str, float] = field(default_factory=dict)
    locale: Optional[str] = None


@dataclass
class BehaviorMetrics:
    """유저 행동 지표."""
    avg_session_duration: float
    avg_pages_per_session: float
    conversion_rate: float
    bounce_rate: float
    total_sessions: int
    total_events: int


@dataclass
class Preferences:
    """유저 선호도 정보."""
    top_pages: List[str] = field(default_factory=list)
    top_categories: List[str] = field(default_factory=list)
    price_sensitivity: float = 0.0


@dataclass
class JourneyPattern:
    """세션별 페이지 이동 경로 패턴."""
    path: List[str] = field(default_factory=list)
    frequency: int = 0


@dataclass
class UserProfile:
    """유저별 집계 프로파일."""
    user_id: str
    status: str
    demographics: Demographics
    behavior: BehaviorMetrics
    preferences: Preferences
    journey_patterns: List[JourneyPattern] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


# --- Segment Models ---

@dataclass
class SegmentSummary:
    """세그먼트 요약 정보."""
    member_count: int
    avg_session_duration: float
    avg_pages_per_session: float
    avg_conversion_rate: float
    avg_bounce_rate: float
    primary_device: str
    primary_os: str


@dataclass
class Segment:
    """클러스터링 결과 세그먼트."""
    segment_id: str
    label: str
    member_user_ids: List[str] = field(default_factory=list)
    summary: Optional[SegmentSummary] = None
    centroid: List[float] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


# --- Twin Models ---

@dataclass
class MarkovChainModel:
    """페이지 간 전이 확률 모델."""
    model_id: str
    segment_id: str
    states: List[str] = field(default_factory=list)
    transition_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DigitalTwin:
    """가상 유저 인스턴스."""
    twin_id: str
    segment_id: str
    markov_model_id: str
    demographics: Optional[Demographics] = None
    created_at: datetime = field(default_factory=datetime.now)


# --- Simulation Models ---

@dataclass
class ReactionRule:
    """세그먼트별 variant 반응 규칙."""
    segment_id: str
    variant_id: str
    conversion_rate_modifier: float
    condition: Optional[str] = None


@dataclass
class Variant:
    """A/B 테스트 variant 정의."""
    variant_id: str
    name: str
    description: str
    target_page: str
    changes: Dict[str, str] = field(default_factory=dict)


@dataclass
class AnalysisDimension:
    """분석 태그별 분류 조건 정의."""
    tag_name: str
    source_attribute: str
    classification_rules: Optional[Dict[str, str]] = None


@dataclass
class Scenario:
    """A/B 테스트 시나리오."""
    scenario_id: str
    name: str
    scenario_type: str
    target_page: str
    variants: List[Variant] = field(default_factory=list)
    reaction_rules: List[ReactionRule] = field(default_factory=list)
    primary_metric: str = ""
    analysis_tags: List[str] = field(default_factory=list)
    analysis_dimensions: List[AnalysisDimension] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SessionResult:
    """단일 디지털 트윈의 세션 시뮬레이션 결과."""
    twin_id: str
    variant_id: str
    page_sequence: List[str] = field(default_factory=list)
    converted: bool = False
    session_duration: float = 0.0
    reached_target_page: bool = False


@dataclass
class VariantResult:
    """variant별 시뮬레이션 결과 집계."""
    variant_id: str
    total_twins: int
    conversions: int
    conversion_rate: float
    avg_session_duration: float
    funnel_drop_rates: Dict[str, float] = field(default_factory=dict)


@dataclass
class ChiSquareResult:
    """카이제곱 검정 결과."""
    chi2_statistic: float
    p_value: float
    degrees_of_freedom: int
    is_significant: bool
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    cohens_h: float = 0.0


@dataclass
class SegmentAnalysis:
    """세그먼트별 분리 분석 결과."""
    segment_id: str
    segment_label: str
    segment_proportion: float
    variant_results: Dict[str, VariantResult] = field(default_factory=dict)
    chi_square: Optional[ChiSquareResult] = None
    best_variant: str = ""


@dataclass
class TagGroupAnalysis:
    """분석 태그별 그룹 분석 결과."""
    tag_name: str
    group_value: str
    group_twin_count: int
    group_proportion: float
    variant_results: Dict[str, VariantResult] = field(default_factory=dict)
    chi_square: Optional[ChiSquareResult] = None
    best_variant: str = ""


@dataclass
class ReportSummary:
    """MVP 리포트 요약."""
    one_line_conclusion: str
    recommendation: str
    winning_variant: Optional[str] = None
    is_significant: bool = False


@dataclass
class SimulationResult:
    """시뮬레이션 실행 결과."""
    simulation_id: str
    scenario_id: str
    total_twins: int
    variant_results: Dict[str, VariantResult] = field(default_factory=dict)
    weighted_conversion_rates: Dict[str, float] = field(default_factory=dict)
    overall_chi_square: Optional[ChiSquareResult] = None
    segment_analyses: List[SegmentAnalysis] = field(default_factory=list)
    tag_analyses: Optional[Dict[str, List[TagGroupAnalysis]]] = None
    report_summary: Optional[ReportSummary] = None
    progress_pct: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class SimulationReport:
    """MVP 리포트 전체 구조."""
    summary: ReportSummary
    variant_metrics: Dict[str, VariantResult] = field(default_factory=dict)
    weighted_conversion_rates: Dict[str, float] = field(default_factory=dict)
    segment_heatmap: List[SegmentAnalysis] = field(default_factory=list)
    tag_analyses: Optional[Dict[str, List[TagGroupAnalysis]]] = None
    funnel_comparison: Dict[str, Dict[str, float]] = field(default_factory=dict)
    overall_statistics: Optional[ChiSquareResult] = None
    segment_statistics: List[ChiSquareResult] = field(default_factory=list)
    best_variants_by_segment: Dict[str, str] = field(default_factory=dict)


# --- Pipeline Models ---

class PipelineError(Exception):
    """파이프라인 실행 중 특정 단계에서 발생한 오류."""
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


@dataclass
class UploadResult:
    """업로드 결과 요약."""
    upload_id: str
    total_events: int
    unique_users: int
    date_range_start: datetime
    date_range_end: datetime


@dataclass
class ValidationResult:
    """파일 검증 결과."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PipelineUploadResult:
    """스텝 1 결과."""
    upload_id: str
    upload_summary: UploadResult
    events: List[EventRecord]
    profiles: List[UserProfile]
    profile_count: int
    excluded_user_count: int
    base_segments: List[Segment]
    base_segment_count: int


@dataclass
class PipelineSimulateConfig:
    """스텝 2 입력 설정."""
    scenario_name: str
    scenario_type: str
    target_page: str
    variants: List[dict] = field(default_factory=list)
    reaction_rules: List[dict] = field(default_factory=list)
    primary_metric: str = ""
    twin_count: int = 1000
    key_variables: Optional[List[str]] = None
    analysis_tags: Optional[List[str]] = None
    analysis_dimensions: Optional[List[dict]] = None


@dataclass
class PipelineSimulateResult:
    """스텝 2 결과."""
    scenario_id: str
    key_variables: List[str]
    scenario_segment_count: int
    twin_count: int
    simulation_id: str
    report: SimulationReport


@dataclass
class TwinGenerationResult:
    """디지털 트윈 생성 결과 요약."""
    twins: List[DigitalTwin] = field(default_factory=list)
    segment_counts: Dict[str, int] = field(default_factory=dict)
    total_count: int = 0
    elapsed_seconds: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# === CORE SERVICES ===
# ═══════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────
# Upload Service
# ──────────────────────────────────────────────

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
REQUIRED_FIELDS = ["user_id", "session_id", "event_type", "timestamp"]
ALLOWED_EXTENSIONS = {".csv", ".json"}


def validate_file(file_content: bytes, filename: str) -> ValidationResult:
    """파일 크기, 형식, 필수 필드, timestamp 형식을 검증한다."""
    errors: List[str] = []
    warnings: List[str] = []

    if len(file_content) > MAX_FILE_SIZE:
        errors.append("파일 크기가 100MB 제한을 초과합니다")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        errors.append(f"지원하지 않는 파일 형식입니다. CSV 또는 JSON만 지원합니다: {ext}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    try:
        content_str = file_content.decode("utf-8")
    except UnicodeDecodeError:
        errors.append("파일 인코딩을 읽을 수 없습니다. UTF-8 인코딩을 사용해주세요")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    if ext == ".csv":
        records = _parse_csv_to_dicts(content_str)
    else:
        records = _parse_json_to_dicts(content_str)

    if records is None:
        errors.append("파일 파싱에 실패했습니다")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    if len(records) == 0:
        errors.append("파일에 이벤트 데이터가 없습니다")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    field_errors = _validate_required_fields(records, ext)
    errors.extend(field_errors)

    timestamp_errors = _validate_timestamps(records)
    errors.extend(timestamp_errors)

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def _validate_required_fields(records: List[dict], fmt: str) -> List[str]:
    """각 레코드의 필수 필드 누락을 검증한다."""
    errors: List[str] = []
    if records:
        first_record_keys = set(records[0].keys())
        missing_in_header = [f for f in REQUIRED_FIELDS if f not in first_record_keys]
        if missing_in_header:
            errors.append(f"필수 필드가 누락되었습니다: {', '.join(missing_in_header)}")
            return errors

    for i, record in enumerate(records):
        missing_fields = []
        for field_name in REQUIRED_FIELDS:
            value = record.get(field_name)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_fields.append(field_name)
        if missing_fields:
            row_num = i + 1
            errors.append(f"행 {row_num}: 필수 필드가 누락되었습니다: {', '.join(missing_fields)}")
    return errors


def _validate_timestamps(records: List[dict]) -> List[str]:
    """각 레코드의 timestamp가 ISO 8601 형식인지 검증한다."""
    errors: List[str] = []
    for i, record in enumerate(records):
        ts_value = record.get("timestamp")
        if ts_value is None or (isinstance(ts_value, str) and ts_value.strip() == ""):
            continue
        ts_str = str(ts_value).strip()
        if not _is_valid_iso8601(ts_str):
            row_num = i + 1
            errors.append(f"행 {row_num}: timestamp가 ISO 8601 형식이 아닙니다: {ts_str}")
    return errors


def _is_valid_iso8601(ts_str: str) -> bool:
    """ISO 8601 형식 여부를 검증한다."""
    formats = [
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            datetime.strptime(ts_str, fmt)
            return True
        except ValueError:
            continue
    try:
        datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        pass
    return False


def _parse_csv_to_dicts(content: str) -> Optional[List[dict]]:
    """CSV 문자열을 딕셔너리 리스트로 파싱한다."""
    try:
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    except Exception:
        return None


def _parse_json_to_dicts(content: str) -> Optional[List[dict]]:
    """JSON 문자열을 딕셔너리 리스트로 파싱한다."""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return None
    except (json.JSONDecodeError, Exception):
        return None


def _parse_timestamp(ts_value: str) -> datetime:
    """ISO 8601 문자열을 datetime 객체로 변환한다."""
    return datetime.fromisoformat(ts_value)


def _format_timestamp(dt: datetime) -> str:
    """datetime 객체를 ISO 8601 문자열로 변환한다."""
    return dt.isoformat()


def _parse_optional_float(val) -> Optional[float]:
    """문자열 또는 숫자를 float | None으로 변환한다."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s == "":
        return None
    return float(s)


def _parse_optional_str(val) -> Optional[str]:
    """문자열을 str | None으로 변환한다. 빈 문자열은 None."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    return s


def _dict_to_event_record(d: dict) -> EventRecord:
    """딕셔너리를 EventRecord로 변환한다."""
    return EventRecord(
        user_id=str(d["user_id"]),
        session_id=str(d["session_id"]),
        event_type=str(d["event_type"]),
        timestamp=_parse_timestamp(str(d["timestamp"])),
        page=_parse_optional_str(d.get("page")),
        element=_parse_optional_str(d.get("element")),
        element_text=_parse_optional_str(d.get("element_text")),
        conversion_type=_parse_optional_str(d.get("conversion_type")),
        value=_parse_optional_float(d.get("value")),
        device=_parse_optional_str(d.get("device")),
        os=_parse_optional_str(d.get("os")),
        scroll_depth_pct=_parse_optional_float(d.get("scroll_depth_pct")),
        category=_parse_optional_str(d.get("category")),
    )


def _event_record_to_dict(record: EventRecord) -> dict:
    """EventRecord를 딕셔너리로 변환한다."""
    return {
        "user_id": record.user_id,
        "session_id": record.session_id,
        "event_type": record.event_type,
        "timestamp": _format_timestamp(record.timestamp),
        "page": record.page,
        "element": record.element,
        "element_text": record.element_text,
        "conversion_type": record.conversion_type,
        "value": record.value,
        "device": record.device,
        "os": record.os,
        "scroll_depth_pct": record.scroll_depth_pct,
        "category": record.category,
    }


_EVENT_RECORD_FIELDS = [
    "user_id", "session_id", "event_type", "timestamp",
    "page", "element", "element_text", "conversion_type",
    "value", "device", "os", "scroll_depth_pct", "category",
]


def parse_csv(content: str) -> List[EventRecord]:
    """CSV 내용을 EventRecord 리스트로 파싱한다."""
    reader = csv.DictReader(io.StringIO(content))
    return [_dict_to_event_record(row) for row in reader]


def parse_json_events(content: str) -> List[EventRecord]:
    """JSON 내용을 EventRecord 리스트로 파싱한다."""
    data = json.loads(content)
    if not isinstance(data, list):
        data = [data]
    return [_dict_to_event_record(obj) for obj in data]


def serialize_to_csv(records: List[EventRecord]) -> str:
    """EventRecord 리스트를 CSV 문자열로 직렬화한다."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_EVENT_RECORD_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        d = _event_record_to_dict(record)
        row = {k: ("" if v is None else v) for k, v in d.items()}
        writer.writerow(row)
    return output.getvalue()


def generate_upload_summary(records: List[EventRecord]) -> UploadResult:
    """이벤트 레코드 리스트로부터 업로드 요약 정보를 생성한다."""
    total_events = len(records)
    unique_users = len({r.user_id for r in records})
    timestamps = [r.timestamp for r in records]
    date_range_start = min(timestamps)
    date_range_end = max(timestamps)
    upload_id = str(uuid.uuid4())
    return UploadResult(
        upload_id=upload_id,
        total_events=total_events,
        unique_users=unique_users,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )


def upload_file(file_content: bytes, filename: str) -> UploadResult:
    """파일 업로드를 검증, 파싱, 요약 생성까지 오케스트레이션한다."""
    validation = validate_file(file_content, filename)
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))

    content_str = file_content.decode("utf-8")
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == ".csv":
        records = parse_csv(content_str)
    else:
        records = parse_json_events(content_str)

    return generate_upload_summary(records)


# ──────────────────────────────────────────────
# Profiling Engine
# ──────────────────────────────────────────────

def compute_demographics(user_events: List[EventRecord]) -> Demographics:
    """device, os, locale 정보를 집계한다."""
    device_counter: Counter = Counter()
    os_counter: Counter = Counter()

    for ev in user_events:
        if ev.device:
            device_counter[ev.device] += 1
        if ev.os:
            os_counter[ev.os] += 1

    primary_device = device_counter.most_common(1)[0][0] if device_counter else "unknown"
    primary_os = os_counter.most_common(1)[0][0] if os_counter else "unknown"

    device_total = sum(device_counter.values())
    os_total = sum(os_counter.values())

    device_distribution = (
        {k: v / device_total for k, v in device_counter.items()} if device_total else {}
    )
    os_distribution = (
        {k: v / os_total for k, v in os_counter.items()} if os_total else {}
    )

    return Demographics(
        primary_device=primary_device,
        primary_os=primary_os,
        device_distribution=device_distribution,
        os_distribution=os_distribution,
        locale=None,
    )


def compute_behavior(user_events: List[EventRecord]) -> BehaviorMetrics:
    """세션 지속시간, 페이지수, 전환율, 이탈률을 계산한다."""
    sessions: Dict[str, List[EventRecord]] = defaultdict(list)
    for ev in user_events:
        sessions[ev.session_id].append(ev)

    total_sessions = len(sessions)
    if total_sessions == 0:
        return BehaviorMetrics(
            avg_session_duration=0.0, avg_pages_per_session=0.0,
            conversion_rate=0.0, bounce_rate=0.0,
            total_sessions=0, total_events=len(user_events),
        )

    durations: List[float] = []
    pages_per_session: List[int] = []
    sessions_with_purchase = 0
    bounce_sessions = 0

    for session_events in sessions.values():
        timestamps = [ev.timestamp for ev in session_events]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        duration = (max_ts - min_ts).total_seconds()
        durations.append(duration)

        page_views = [ev for ev in session_events if ev.event_type == "page_view"]
        pages_per_session.append(len(page_views))

        has_purchase = any(ev.event_type == "purchase" for ev in session_events)
        if has_purchase:
            sessions_with_purchase += 1
        if len(page_views) <= 1:
            bounce_sessions += 1

    avg_session_duration = sum(durations) / total_sessions
    avg_pages = sum(pages_per_session) / total_sessions
    conversion_rate = sessions_with_purchase / total_sessions
    bounce_rate = bounce_sessions / total_sessions

    return BehaviorMetrics(
        avg_session_duration=avg_session_duration,
        avg_pages_per_session=avg_pages,
        conversion_rate=conversion_rate,
        bounce_rate=bounce_rate,
        total_sessions=total_sessions,
        total_events=len(user_events),
    )


def compute_preferences(user_events: List[EventRecord]) -> Preferences:
    """top_pages, top_categories, price_sensitivity를 분석한다."""
    page_counter: Counter = Counter()
    category_counter: Counter = Counter()
    coupon_count = 0

    for ev in user_events:
        if ev.event_type == "page_view" and ev.page:
            page_counter[ev.page] += 1
        if ev.category:
            category_counter[ev.category] += 1
        if ev.event_type == "coupon_apply":
            coupon_count += 1

    top_pages = [page for page, _ in page_counter.most_common(5)]
    top_categories = [cat for cat, _ in category_counter.most_common(3)]

    total = len(user_events)
    price_sensitivity = coupon_count / total if total > 0 else 0.0

    return Preferences(
        top_pages=top_pages,
        top_categories=top_categories,
        price_sensitivity=price_sensitivity,
    )


def extract_journey_patterns(user_events: List[EventRecord]) -> List[JourneyPattern]:
    """세션별 페이지 이동 경로를 패턴별 빈도로 집계한다."""
    sessions: Dict[str, List[EventRecord]] = defaultdict(list)
    for ev in user_events:
        sessions[ev.session_id].append(ev)

    pattern_counter: Counter = Counter()

    for session_events in sessions.values():
        sorted_events = sorted(session_events, key=lambda e: e.timestamp)
        page_sequence = tuple(
            ev.page for ev in sorted_events if ev.event_type == "page_view" and ev.page
        )
        if page_sequence:
            pattern_counter[page_sequence] += 1

    top_patterns = pattern_counter.most_common(10)
    return [
        JourneyPattern(path=list(path), frequency=freq)
        for path, freq in top_patterns
    ]


def generate_profiles(events: List[EventRecord]) -> List[UserProfile]:
    """이벤트 로그로부터 유저별 프로파일을 생성한다."""
    user_events_map: Dict[str, List[EventRecord]] = defaultdict(list)
    for ev in events:
        user_events_map[ev.user_id].append(ev)

    profiles: List[UserProfile] = []

    for user_id, user_events in user_events_map.items():
        if len(user_events) < 3:
            profile = UserProfile(
                user_id=user_id,
                status="insufficient_data",
                demographics=Demographics(primary_device="unknown", primary_os="unknown"),
                behavior=BehaviorMetrics(
                    avg_session_duration=0.0, avg_pages_per_session=0.0,
                    conversion_rate=0.0, bounce_rate=0.0,
                    total_sessions=0, total_events=len(user_events),
                ),
                preferences=Preferences(),
                journey_patterns=[],
            )
        else:
            demographics = compute_demographics(user_events)
            behavior = compute_behavior(user_events)
            preferences = compute_preferences(user_events)
            journey_patterns = extract_journey_patterns(user_events)
            profile = UserProfile(
                user_id=user_id, status="active",
                demographics=demographics, behavior=behavior,
                preferences=preferences, journey_patterns=journey_patterns,
            )
        profiles.append(profile)

    return profiles


# ──────────────────────────────────────────────
# Segmentation Engine
# ──────────────────────────────────────────────

_DEVICE_CATEGORIES = ["mobile", "desktop", "tablet"]
_OS_CATEGORIES = ["iOS", "Android", "Windows", "macOS"]

VARIABLE_ATTRIBUTE_MAP: Dict[str, str] = {
    "price_sensitivity": "preferences.price_sensitivity",
    "coupon_apply_rate": "preferences.price_sensitivity",
    "avg_purchase_value": "behavior.avg_session_duration",
    "purchase_frequency": "behavior.total_sessions",
    "conversion_rate": "behavior.conversion_rate",
    "bounce_rate": "behavior.bounce_rate",
    "avg_pages_per_session": "behavior.avg_pages_per_session",
    "avg_session_duration": "behavior.avg_session_duration",
    "visit_frequency": "behavior.total_sessions",
    "click_through_rate": "behavior.conversion_rate",
    "funnel_completion_rate": "behavior.conversion_rate",
    "scroll_depth": "behavior.avg_pages_per_session",
}


def _extract_variable_value(profile: UserProfile, variable_name: str) -> float:
    """변수 이름으로부터 프로파일의 해당 속성 값을 추출한다."""
    attr_path = VARIABLE_ATTRIBUTE_MAP[variable_name]
    section, field_name = attr_path.split(".")
    obj = getattr(profile, section)
    return float(getattr(obj, field_name))


def build_feature_matrix(
    profiles: List[UserProfile],
    selected_variables: Optional[List[str]] = None,
) -> np.ndarray:
    """프로파일의 behavior/demographics를 수치 벡터로 변환한다."""
    if selected_variables is not None:
        rows: List[List[float]] = []
        for p in profiles:
            row = [_extract_variable_value(p, v) for v in selected_variables]
            rows.append(row)
        matrix = np.array(rows, dtype=np.float64)
        scaler = StandardScaler()
        return scaler.fit_transform(matrix)

    rows = []
    for p in profiles:
        row: List[float] = [
            p.behavior.avg_session_duration,
            p.behavior.avg_pages_per_session,
            p.behavior.conversion_rate,
            p.behavior.bounce_rate,
            p.preferences.price_sensitivity,
        ]
        for cat in _DEVICE_CATEGORIES:
            row.append(1.0 if p.demographics.primary_device == cat else 0.0)
        for cat in _OS_CATEGORIES:
            row.append(1.0 if p.demographics.primary_os == cat else 0.0)
        rows.append(row)

    matrix = np.array(rows, dtype=np.float64)
    scaler = StandardScaler()
    return scaler.fit_transform(matrix)


def find_optimal_k(feature_matrix: np.ndarray) -> int:
    """Silhouette Score 기반으로 최적 클러스터 수를 결정한다 (2~10)."""
    n_samples = feature_matrix.shape[0]
    max_k = min(10, n_samples - 1)

    if max_k < 2:
        return 2

    best_k = 2
    best_score = -1.0

    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(feature_matrix)
        score = silhouette_score(feature_matrix, labels)
        if score > best_score:
            best_score = score
            best_k = k

    return best_k


def generate_segment_summary(profiles: List[UserProfile]) -> SegmentSummary:
    """세그먼트 요약 정보를 생성한다."""
    if not profiles:
        return SegmentSummary(
            member_count=0, avg_session_duration=0.0,
            avg_pages_per_session=0.0, avg_conversion_rate=0.0,
            avg_bounce_rate=0.0, primary_device="unknown", primary_os="unknown",
        )

    n = len(profiles)
    avg_session_duration = sum(p.behavior.avg_session_duration for p in profiles) / n
    avg_pages = sum(p.behavior.avg_pages_per_session for p in profiles) / n
    avg_conversion = sum(p.behavior.conversion_rate for p in profiles) / n
    avg_bounce = sum(p.behavior.bounce_rate for p in profiles) / n

    device_counter: Counter = Counter(p.demographics.primary_device for p in profiles)
    os_counter: Counter = Counter(p.demographics.primary_os for p in profiles)

    return SegmentSummary(
        member_count=n,
        avg_session_duration=avg_session_duration,
        avg_pages_per_session=avg_pages,
        avg_conversion_rate=avg_conversion,
        avg_bounce_rate=avg_bounce,
        primary_device=device_counter.most_common(1)[0][0],
        primary_os=os_counter.most_common(1)[0][0],
    )


def _generate_label(summary: SegmentSummary) -> str:
    """세그먼트의 주요 특성으로부터 자동 라벨을 생성한다."""
    parts: List[str] = []
    if summary.avg_conversion_rate >= 0.3:
        parts.append("고전환")
    elif summary.avg_conversion_rate >= 0.1:
        parts.append("중전환")
    else:
        parts.append("저전환")
    parts.append(summary.primary_device)
    if summary.avg_pages_per_session >= 5:
        parts.append("탐색형")
    elif summary.avg_pages_per_session <= 2:
        parts.append("간결형")
    return "_".join(parts)


def cluster_profiles(profiles: List[UserProfile]) -> List[Segment]:
    """K-Means 클러스터링으로 세그먼트를 생성한다."""
    active_profiles = [p for p in profiles if p.status == "active"]

    if len(active_profiles) < 10:
        raise ValueError(
            "세그먼트 생성에 충분한 프로파일이 없습니다. "
            "최소 10개의 유효 프로파일이 필요합니다"
        )

    feature_matrix = build_feature_matrix(active_profiles)
    optimal_k = find_optimal_k(feature_matrix)

    km = KMeans(n_clusters=optimal_k, n_init=10, random_state=42)
    labels = km.fit_predict(feature_matrix)

    cluster_map: Dict[int, List[UserProfile]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(int(label), []).append(active_profiles[idx])

    segments: List[Segment] = []
    for cluster_label in sorted(cluster_map.keys()):
        members = cluster_map[cluster_label]
        summary = generate_segment_summary(members)
        seg_label = _generate_label(summary)
        centroid = km.cluster_centers_[cluster_label].tolist()

        segment = Segment(
            segment_id=str(uuid4()),
            label=seg_label,
            member_user_ids=[p.user_id for p in members],
            summary=summary,
            centroid=centroid,
        )
        segments.append(segment)

    return segments


def recluster_for_scenario(
    profiles: List[UserProfile],
    key_variables: List[str],
    scenario_id: str,
) -> List[Segment]:
    """시나리오의 주요 행동 변수만을 피처로 사용하여 K-Means 재클러스터링을 수행한다."""
    active_profiles = [p for p in profiles if p.status == "active"]

    if len(active_profiles) < 10:
        raise ValueError(
            "세그먼트 생성에 충분한 프로파일이 없습니다. "
            "최소 10개의 유효 프로파일이 필요합니다"
        )

    feature_matrix = build_feature_matrix(active_profiles, selected_variables=key_variables)
    optimal_k = find_optimal_k(feature_matrix)

    km = KMeans(n_clusters=optimal_k, n_init=10, random_state=42)
    labels = km.fit_predict(feature_matrix)

    cluster_map: Dict[int, List[UserProfile]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(int(label), []).append(active_profiles[idx])

    segments: List[Segment] = []
    vars_label = "+".join(key_variables[:3])

    for cluster_label in sorted(cluster_map.keys()):
        members = cluster_map[cluster_label]
        summary = generate_segment_summary(members)
        seg_label = f"scenario_{vars_label}_c{cluster_label}"
        centroid = km.cluster_centers_[cluster_label].tolist()

        segment = Segment(
            segment_id=f"{scenario_id}_{uuid4()}",
            label=seg_label,
            member_user_ids=[p.user_id for p in members],
            summary=summary,
            centroid=centroid,
        )
        segments.append(segment)

    return segments


# ──────────────────────────────────────────────
# Scenario Variable Resolver
# ──────────────────────────────────────────────

SCENARIO_VARIABLE_MAP: Dict[str, List[str]] = {
    "promotion": ["price_sensitivity", "coupon_apply_rate", "avg_purchase_value", "purchase_frequency"],
    "cta_change": ["conversion_rate", "bounce_rate", "avg_pages_per_session", "click_through_rate"],
    "price_display": ["price_sensitivity", "conversion_rate", "avg_purchase_value"],
    "funnel_change": ["funnel_completion_rate", "bounce_rate", "avg_session_duration"],
    "ui_position": ["scroll_depth", "avg_pages_per_session", "bounce_rate"],
    "timing": ["visit_frequency", "avg_session_duration", "bounce_rate"],
}


def get_default_variables(scenario_type: str) -> List[str]:
    """Return the default key variables for scenario_type."""
    if scenario_type not in SCENARIO_VARIABLE_MAP:
        raise ValueError(
            f"Unknown scenario_type '{scenario_type}'. "
            f"Supported types: {sorted(SCENARIO_VARIABLE_MAP)}"
        )
    return list(SCENARIO_VARIABLE_MAP[scenario_type])


def resolve_key_variables(
    scenario_type: str,
    user_specified_variables: Optional[List[str]] = None,
) -> List[str]:
    """Derive key behavioural variables for a scenario."""
    if user_specified_variables:
        return list(user_specified_variables)
    return get_default_variables(scenario_type)


# ──────────────────────────────────────────────
# Scenario Manager
# ──────────────────────────────────────────────

SUPPORTED_SCENARIO_TYPES = frozenset(
    {"cta_change", "price_display", "funnel_change", "ui_position", "timing", "promotion"}
)
MAX_VARIANTS = 5


def create_scenario(config: dict) -> Scenario:
    """Create a Scenario from a config dict."""
    variants_raw: List[dict] = config.get("variants", [])
    if len(variants_raw) > MAX_VARIANTS:
        raise ValueError(f"Maximum {MAX_VARIANTS} variants allowed, got {len(variants_raw)}")

    scenario_type: str = config.get("scenario_type", "")
    if scenario_type not in SUPPORTED_SCENARIO_TYPES:
        raise ValueError(
            f"Unsupported scenario_type '{scenario_type}'. "
            f"Supported: {sorted(SUPPORTED_SCENARIO_TYPES)}"
        )

    variants = [
        Variant(
            variant_id=v.get("variant_id", str(uuid4())),
            name=v.get("name", ""),
            description=v.get("description", ""),
            target_page=v.get("target_page", config.get("target_page", "")),
            changes=v.get("changes", {}),
        )
        for v in variants_raw
    ]

    reaction_rules = [
        ReactionRule(
            segment_id=r["segment_id"],
            variant_id=r["variant_id"],
            conversion_rate_modifier=r["conversion_rate_modifier"],
            condition=r.get("condition"),
        )
        for r in config.get("reaction_rules", [])
    ]

    analysis_dimensions = [
        AnalysisDimension(
            tag_name=d["tag_name"],
            source_attribute=d["source_attribute"],
            classification_rules=d.get("classification_rules"),
        )
        for d in config.get("analysis_dimensions", [])
    ]

    return Scenario(
        scenario_id=str(uuid4()),
        name=config.get("name", ""),
        scenario_type=scenario_type,
        target_page=config.get("target_page", ""),
        variants=variants,
        reaction_rules=reaction_rules,
        primary_metric=config.get("primary_metric", ""),
        analysis_tags=config.get("analysis_tags", []),
        analysis_dimensions=analysis_dimensions,
    )


# ──────────────────────────────────────────────
# Markov Builder
# ──────────────────────────────────────────────

SESSION_START = "session_start"
SESSION_END = "session_end"
_MIN_SESSIONS_FOR_MODEL = 5


def build_markov_model(
    segment_id: str,
    segment_events: List[EventRecord],
) -> MarkovChainModel:
    """세그먼트의 이벤트 로그로부터 전이 확률 행렬을 학습한다."""
    sessions = _group_sessions(segment_events)
    transition_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    states_set: Set[str] = {SESSION_START, SESSION_END}

    for pages in sessions:
        if not pages:
            continue
        transition_counts[SESSION_START][pages[0]] += 1
        states_set.add(pages[0])

        for i in range(len(pages) - 1):
            transition_counts[pages[i]][pages[i + 1]] += 1
            states_set.add(pages[i])
            states_set.add(pages[i + 1])

        transition_counts[pages[-1]][SESSION_END] += 1

    states = sorted(states_set)
    matrix = normalize_transitions(
        {src: dict(targets) for src, targets in transition_counts.items()}
    )

    return MarkovChainModel(
        model_id=str(uuid4()),
        segment_id=segment_id,
        states=states,
        transition_matrix=matrix,
    )


def normalize_transitions(
    matrix: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """각 상태의 전이 확률 합이 1.0이 되도록 정규화한다."""
    normalized: Dict[str, Dict[str, float]] = {}
    for src, targets in matrix.items():
        total = sum(targets.values())
        if total == 0:
            normalized[src] = {}
        else:
            normalized[src] = {dst: count / total for dst, count in targets.items()}
    return normalized


def get_default_model(all_events: List[EventRecord]) -> MarkovChainModel:
    """전체 데이터 기반 기본 전이 확률 모델을 생성한다."""
    model = build_markov_model(segment_id="default", segment_events=all_events)
    model.is_default = True
    return model


def _group_sessions(events: List[EventRecord]) -> List[List[str]]:
    """이벤트를 session_id 별로 그룹핑하고 page_view 이벤트의 page 시퀀스를 추출한다."""
    session_map: Dict[str, List[EventRecord]] = defaultdict(list)
    for ev in events:
        session_map[ev.session_id].append(ev)

    sessions: List[List[str]] = []
    for _sid, session_events in session_map.items():
        session_events.sort(key=lambda e: e.timestamp)
        pages = [
            ev.page
            for ev in session_events
            if ev.event_type == "page_view" and ev.page is not None
        ]
        if pages:
            sessions.append(pages)

    return sessions


def has_sufficient_sessions(segment_events: List[EventRecord]) -> bool:
    """세그먼트의 세션 수가 모델 학습에 충분한지 확인한다 (5건 이상)."""
    session_ids = {ev.session_id for ev in segment_events}
    return len(session_ids) >= _MIN_SESSIONS_FOR_MODEL


# ──────────────────────────────────────────────
# Twin Generator
# ──────────────────────────────────────────────

MIN_TWIN_COUNT = 100
MAX_TWIN_COUNT = 100_000
_DEFAULT_DEVICES = ["mobile", "desktop", "tablet"]
_DEFAULT_OS_LIST = ["iOS", "Android", "Windows", "macOS"]


def generate_twins(
    count: int,
    segments: List[Segment],
    models: Dict[str, MarkovChainModel],
) -> TwinGenerationResult:
    """세그먼트 비율에 따라 디지털 트윈을 분배 생성한다."""
    if count < MIN_TWIN_COUNT or count > MAX_TWIN_COUNT:
        raise ValueError(
            f"트윈 수는 {MIN_TWIN_COUNT}~{MAX_TWIN_COUNT} 범위여야 합니다. 입력값: {count}"
        )
    if not segments:
        raise ValueError("세그먼트 목록이 비어 있습니다.")

    start = time.monotonic()
    allocation = _distribute_proportionally(count, segments)

    twins: List[DigitalTwin] = []
    segment_counts: Dict[str, int] = {}

    for segment, n in allocation:
        segment_counts[segment.segment_id] = n
        model = models.get(segment.segment_id)
        model_id = model.model_id if model else ""

        for _ in range(n):
            demographics = assign_demographics(segment)
            twin = DigitalTwin(
                twin_id=str(uuid4()),
                segment_id=segment.segment_id,
                markov_model_id=model_id,
                demographics=demographics,
            )
            twins.append(twin)

    elapsed = time.monotonic() - start

    return TwinGenerationResult(
        twins=twins,
        segment_counts=segment_counts,
        total_count=len(twins),
        elapsed_seconds=round(elapsed, 4),
    )


def assign_demographics(segment: Segment) -> Demographics:
    """세그먼트 분포에 따라 demographics를 확률적으로 할당한다."""
    summary = segment.summary
    primary_device = summary.primary_device if summary else "mobile"
    device = _pick_with_primary_bias(primary_device, _DEFAULT_DEVICES)
    primary_os = summary.primary_os if summary else "iOS"
    chosen_os = _pick_with_primary_bias(primary_os, _DEFAULT_OS_LIST)

    device_dist = {primary_device: 0.7}
    remaining_devices = [d for d in _DEFAULT_DEVICES if d != primary_device]
    if remaining_devices:
        share = 0.3 / len(remaining_devices)
        for d in remaining_devices:
            device_dist[d] = round(share, 4)

    os_dist = {primary_os: 0.7}
    remaining_os = [o for o in _DEFAULT_OS_LIST if o != primary_os]
    if remaining_os:
        share = 0.3 / len(remaining_os)
        for o in remaining_os:
            os_dist[o] = round(share, 4)

    return Demographics(
        primary_device=device,
        primary_os=chosen_os,
        device_distribution=device_dist,
        os_distribution=os_dist,
    )


def _pick_with_primary_bias(primary: str, pool: List[str]) -> str:
    """70% 확률로 primary 값, 30% 확률로 pool 내 다른 값을 선택한다."""
    if random.random() < 0.7:
        return primary
    alternatives = [v for v in pool if v != primary]
    if not alternatives:
        return primary
    return random.choice(alternatives)


def _distribute_proportionally(
    count: int, segments: List[Segment],
) -> List[Tuple[Segment, int]]:
    """세그먼트 member_count 비율에 따라 count를 분배한다."""
    total_members = sum(
        (seg.summary.member_count if seg.summary else len(seg.member_user_ids))
        for seg in segments
    )
    if total_members == 0:
        base = count // len(segments)
        remainder = count - base * len(segments)
        result = [(seg, base) for seg in segments]
        if remainder > 0:
            seg, n = result[0]
            result[0] = (seg, n + remainder)
        return result

    allocations: List[Tuple[Segment, int]] = []
    for seg in segments:
        members = seg.summary.member_count if seg.summary else len(seg.member_user_ids)
        proportion = members / total_members
        allocations.append((seg, round(count * proportion)))

    allocated_total = sum(n for _, n in allocations)
    diff = count - allocated_total
    if diff != 0:
        largest_idx = max(range(len(allocations)), key=lambda i: allocations[i][1])
        seg, n = allocations[largest_idx]
        allocations[largest_idx] = (seg, n + diff)

    return allocations


# ──────────────────────────────────────────────
# Reaction Model
# ──────────────────────────────────────────────

DEFAULT_BASE_CONVERSION_RATE = 0.05


class ReactionModel:
    """Rule-based reaction model that determines if a twin converts."""

    def evaluate(
        self,
        twin: DigitalTwin,
        variant_id: str,
        scenario: Scenario,
        current_page: str,
        base_conversion_rate: Optional[float] = None,
    ) -> bool:
        """Determine if twin converts for variant_id on current_page."""
        if base_conversion_rate is None:
            base_conversion_rate = DEFAULT_BASE_CONVERSION_RATE

        rules = self.get_segment_rules(twin.segment_id, scenario)
        variant_rules = [r for r in rules if r.variant_id == variant_id]

        if variant_rules:
            modifier = variant_rules[0].conversion_rate_modifier
            effective_rate = min(base_conversion_rate * modifier, 1.0)
            return random.random() < effective_rate

        return self.apply_default_reaction(base_conversion_rate)

    @staticmethod
    def get_segment_rules(segment_id: str, scenario: Scenario) -> List[ReactionRule]:
        """Return reaction rules for segment_id from scenario."""
        return [r for r in scenario.reaction_rules if r.segment_id == segment_id]

    @staticmethod
    def apply_default_reaction(base_conversion_rate: float) -> bool:
        """Use base_conversion_rate directly to decide conversion."""
        return random.random() < base_conversion_rate


# ──────────────────────────────────────────────
# Simulation Engine
# ──────────────────────────────────────────────

SIM_MAX_STEPS = 50
PAGE_DURATION_MIN = 5
PAGE_DURATION_MAX = 300


def assign_variants(
    twins: List[DigitalTwin], variant_count: int
) -> Dict[str, List[DigitalTwin]]:
    """모든 트윈이 모든 variant를 테스트하도록 할당한다 (동일 유저 대상 비교)."""
    groups: Dict[str, List[DigitalTwin]] = {
        f"variant_{i}": list(twins) for i in range(variant_count)
    }
    return groups


def simulate_session(
    twin: DigitalTwin,
    model: MarkovChainModel,
    scenario: Scenario,
    variant_id: str,
    reaction_model: ReactionModel,
) -> SessionResult:
    """Simulate a single session for twin using its Markov model."""
    page_sequence: List[str] = []
    current_state = SESSION_START
    converted = False
    reached_target = False
    total_duration = 0.0

    for _ in range(SIM_MAX_STEPS):
        transitions = model.transition_matrix.get(current_state, {})
        if not transitions:
            break

        next_states = list(transitions.keys())
        weights = list(transitions.values())
        next_state = random.choices(next_states, weights=weights, k=1)[0]

        if next_state == SESSION_END:
            break

        page_sequence.append(next_state)
        total_duration += random.uniform(PAGE_DURATION_MIN, PAGE_DURATION_MAX)

        if next_state == scenario.target_page:
            reached_target = True
            if not converted:
                converted = reaction_model.evaluate(
                    twin, variant_id, scenario, next_state
                )

        current_state = next_state

    return SessionResult(
        twin_id=twin.twin_id,
        variant_id=variant_id,
        page_sequence=page_sequence,
        converted=converted,
        session_duration=total_duration,
        reached_target_page=reached_target,
    )


def run_simulation(
    scenario: Scenario,
    twins: List[DigitalTwin],
    models: Dict[str, MarkovChainModel],
    reaction_model: ReactionModel,
) -> SimulationResult:
    """Run a full simulation: assign variants, simulate sessions, aggregate."""
    variant_count = len(scenario.variants)
    variant_ids = [v.variant_id for v in scenario.variants]

    groups = assign_variants(twins, variant_count)

    variant_twin_map: Dict[str, List[DigitalTwin]] = {}
    for idx, vid in enumerate(variant_ids):
        variant_twin_map[vid] = groups.get(f"variant_{idx}", [])

    session_results: List[SessionResult] = []
    total = len(twins)
    processed = 0

    for vid, group_twins in variant_twin_map.items():
        for twin in group_twins:
            model = models.get(twin.segment_id) or models.get("default")
            if model is None:
                processed += 1
                continue
            result = simulate_session(twin, model, scenario, vid, reaction_model)
            session_results.append(result)
            processed += 1

    variant_results = _aggregate_variant_results(session_results, variant_ids)
    segment_analyses = _compute_segment_analyses(session_results, twins, variant_ids)
    weighted_rates = compute_weighted_conversion_rate(segment_analyses)

    tag_analyses = None
    if scenario.analysis_tags:
        tag_analyses = analyze_by_tags(
            session_results, twins,
            scenario.analysis_tags,
            scenario.analysis_dimensions or None,
        )

    return SimulationResult(
        simulation_id=str(uuid4()),
        scenario_id=scenario.scenario_id,
        total_twins=total,
        variant_results=variant_results,
        weighted_conversion_rates=weighted_rates,
        segment_analyses=segment_analyses,
        tag_analyses=tag_analyses,
        progress_pct=100.0,
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )


def compute_weighted_conversion_rate(
    segment_analyses: List[SegmentAnalysis],
) -> Dict[str, float]:
    """Compute weighted conversion rate per variant."""
    rates: Dict[str, float] = {}
    for sa in segment_analyses:
        for vid, vr in sa.variant_results.items():
            rates[vid] = rates.get(vid, 0.0) + sa.segment_proportion * vr.conversion_rate
    return rates


def analyze_by_tags(
    session_results: List[SessionResult],
    twins: List[DigitalTwin],
    analysis_tags: List[str],
    analysis_dimensions: Optional[List[AnalysisDimension]] = None,
) -> Dict[str, List[TagGroupAnalysis]]:
    """Group twins by each analysis tag and compute per-group variant results."""
    twin_map: Dict[str, DigitalTwin] = {t.twin_id: t for t in twins}
    session_map: Dict[str, SessionResult] = {s.twin_id: s for s in session_results}

    dim_lookup: Dict[str, AnalysisDimension] = {}
    if analysis_dimensions:
        dim_lookup = {d.tag_name: d for d in analysis_dimensions}

    result: Dict[str, List[TagGroupAnalysis]] = {}

    for tag in analysis_tags:
        dim = dim_lookup.get(tag)
        groups: Dict[str, List[str]] = defaultdict(list)

        for twin in twins:
            attr_value = _resolve_attribute(twin, dim.source_attribute if dim else tag)
            if attr_value is None:
                continue

            if dim and dim.classification_rules:
                group_val = _classify_value(attr_value, dim.classification_rules)
            else:
                group_val = str(attr_value)

            if group_val is not None:
                groups[group_val].append(twin.twin_id)

        total_tagged = sum(len(ids) for ids in groups.values())
        tag_group_analyses: List[TagGroupAnalysis] = []

        for group_val, twin_ids in sorted(groups.items()):
            group_sessions = [session_map[tid] for tid in twin_ids if tid in session_map]
            if not group_sessions:
                continue

            v_ids = sorted({s.variant_id for s in group_sessions})
            variant_results = _aggregate_variant_results(group_sessions, v_ids)

            best_variant = max(variant_results.values(), key=lambda v: v.conversion_rate).variant_id if variant_results else ""

            tag_group_analyses.append(
                TagGroupAnalysis(
                    tag_name=tag,
                    group_value=group_val,
                    group_twin_count=len(twin_ids),
                    group_proportion=len(twin_ids) / total_tagged if total_tagged else 0.0,
                    variant_results=variant_results,
                    best_variant=best_variant,
                )
            )

        result[tag] = tag_group_analyses

    return result


def _aggregate_variant_results(
    sessions: List[SessionResult],
    variant_ids: List[str],
) -> Dict[str, VariantResult]:
    """Aggregate session results into per-variant metrics."""
    by_variant: Dict[str, List[SessionResult]] = defaultdict(list)
    for s in sessions:
        by_variant[s.variant_id].append(s)

    results: Dict[str, VariantResult] = {}
    for vid in variant_ids:
        group = by_variant.get(vid, [])
        total = len(group)
        conversions = sum(1 for s in group if s.converted)
        avg_dur = sum(s.session_duration for s in group) / total if total else 0.0

        page_counts: Dict[str, int] = defaultdict(int)
        for s in group:
            for page in s.page_sequence:
                page_counts[page] += 1

        funnel_drop: Dict[str, float] = {}
        if total > 0:
            for page, count in page_counts.items():
                funnel_drop[page] = 1.0 - (count / total)

        results[vid] = VariantResult(
            variant_id=vid,
            total_twins=total,
            conversions=conversions,
            conversion_rate=conversions / total if total else 0.0,
            avg_session_duration=avg_dur,
            funnel_drop_rates=funnel_drop,
        )
    return results


def _compute_segment_analyses(
    sessions: List[SessionResult],
    twins: List[DigitalTwin],
    variant_ids: List[str],
) -> List[SegmentAnalysis]:
    """Compute per-segment variant results for weighted conversion."""
    twin_map = {t.twin_id: t for t in twins}
    total_twins = len(twins)

    seg_sessions: Dict[str, List[SessionResult]] = defaultdict(list)
    seg_twin_ids: Dict[str, Set[str]] = defaultdict(set)
    for s in sessions:
        twin = twin_map.get(s.twin_id)
        if twin:
            seg_sessions[twin.segment_id].append(s)
            seg_twin_ids[twin.segment_id].add(s.twin_id)

    analyses: List[SegmentAnalysis] = []
    for seg_id in sorted(seg_sessions.keys()):
        seg_s = seg_sessions[seg_id]
        proportion = len(seg_twin_ids[seg_id]) / total_twins if total_twins else 0.0
        vr = _aggregate_variant_results(seg_s, variant_ids)
        best = max(vr.values(), key=lambda v: v.conversion_rate).variant_id if vr else ""

        analyses.append(
            SegmentAnalysis(
                segment_id=seg_id,
                segment_label=seg_id,
                segment_proportion=proportion,
                variant_results=vr,
                best_variant=best,
            )
        )
    return analyses


def _resolve_attribute(twin: DigitalTwin, attr_path: str) -> object:
    """Resolve a dotted attribute path on a twin."""
    obj: object = twin
    for part in attr_path.split("."):
        if obj is None:
            return None
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return None
    return obj


def _classify_value(value: object, rules: Dict[str, str]) -> Optional[str]:
    """Classify value according to classification rules."""
    for label, rule in rules.items():
        if _matches_rule(value, rule):
            return label
    return None


def _matches_rule(value: object, rule: str) -> bool:
    """Check if value matches a single classification rule string."""
    rule = rule.strip()

    if "~" in rule:
        parts = rule.split("~")
        if len(parts) == 2:
            try:
                lo, hi = float(parts[0]), float(parts[1])
                return lo <= float(value) <= hi
            except (ValueError, TypeError):
                return False

    if rule.startswith(">="):
        try:
            return float(value) >= float(rule[2:])
        except (ValueError, TypeError):
            return False
    if rule.startswith("<="):
        try:
            return float(value) <= float(rule[2:])
        except (ValueError, TypeError):
            return False
    if rule.startswith(">"):
        try:
            return float(value) > float(rule[1:])
        except (ValueError, TypeError):
            return False
    if rule.startswith("<"):
        try:
            return float(value) < float(rule[1:])
        except (ValueError, TypeError):
            return False

    return str(value) == rule


# ──────────────────────────────────────────────
# Statistics Analyzer
# ──────────────────────────────────────────────

def chi_square_test(variant_results: Dict[str, VariantResult]) -> ChiSquareResult:
    """Perform a chi-square test of independence on variant conversion counts."""
    variant_ids = sorted(variant_results.keys())

    table: List[List[int]] = []
    for vid in variant_ids:
        vr = variant_results[vid]
        non_conversions = vr.total_twins - vr.conversions
        table.append([vr.conversions, non_conversions])

    observed = np.array(table)

    if observed.shape[0] < 2 or observed.sum() == 0:
        ci = {
            vid: compute_confidence_interval(
                variant_results[vid].conversions, variant_results[vid].total_twins
            )
            for vid in variant_ids
        }
        return ChiSquareResult(
            chi2_statistic=0.0, p_value=1.0, degrees_of_freedom=0,
            is_significant=False, confidence_intervals=ci, cohens_h=0.0,
        )

    chi2, p_value, dof, _ = chi2_contingency(observed, correction=False)

    confidence_intervals: Dict[str, Tuple[float, float]] = {}
    for vid in variant_ids:
        vr = variant_results[vid]
        confidence_intervals[vid] = compute_confidence_interval(vr.conversions, vr.total_twins)

    cohens_h = 0.0
    if len(variant_ids) >= 2:
        rate_a = variant_results[variant_ids[0]].conversion_rate
        rate_b = variant_results[variant_ids[1]].conversion_rate
        cohens_h = compute_cohens_h(rate_a, rate_b)

    return ChiSquareResult(
        chi2_statistic=float(chi2),
        p_value=float(p_value),
        degrees_of_freedom=int(dof),
        is_significant=bool(p_value < 0.05),
        confidence_intervals=confidence_intervals,
        cohens_h=cohens_h,
    )


def compute_confidence_interval(
    conversions: int, total: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """Compute a normal-approximation confidence interval for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = conversions / total
    z = 1.96
    se = math.sqrt(p * (1 - p) / total)
    lower = max(0.0, p - z * se)
    upper = min(1.0, p + z * se)
    return (lower, upper)


def compute_cohens_h(rate_a: float, rate_b: float) -> float:
    """Compute Cohen's h effect size between two proportions."""
    rate_a = max(0.0, min(1.0, rate_a))
    rate_b = max(0.0, min(1.0, rate_b))
    h = 2 * math.asin(math.sqrt(rate_a)) - 2 * math.asin(math.sqrt(rate_b))
    return abs(h)


def find_best_variant_per_segment(
    segment_analyses: List[SegmentAnalysis],
) -> Dict[str, str]:
    """For each segment, find the variant with the highest conversion rate."""
    result: Dict[str, str] = {}
    for sa in segment_analyses:
        if sa.variant_results:
            best = max(sa.variant_results.values(), key=lambda v: v.conversion_rate)
            result[sa.segment_id] = best.variant_id
    return result


def generate_report_summary(
    simulation_result: SimulationResult,
    segment_analyses: List[SegmentAnalysis],
) -> ReportSummary:
    """Generate an MVP report summary from simulation results."""
    weighted_rates = simulation_result.weighted_conversion_rates

    if not weighted_rates and simulation_result.variant_results:
        weighted_rates = {
            vid: vr.conversion_rate
            for vid, vr in simulation_result.variant_results.items()
        }

    is_significant = False
    if simulation_result.overall_chi_square is not None:
        is_significant = simulation_result.overall_chi_square.is_significant

    if not weighted_rates:
        return ReportSummary(
            one_line_conclusion="시뮬레이션 결과 데이터가 부족합니다.",
            recommendation="더 많은 데이터로 시뮬레이션을 재실행하세요.",
            winning_variant=None,
            is_significant=False,
        )

    best_vid = max(weighted_rates, key=lambda k: weighted_rates[k])
    best_rate = weighted_rates[best_vid]

    other_rates = {k: v for k, v in weighted_rates.items() if k != best_vid}
    if other_rates:
        runner_up_rate = max(other_rates.values())
        diff_pp = (best_rate - runner_up_rate) * 100
    else:
        diff_pp = 0.0

    if is_significant:
        one_line_conclusion = f"{best_vid}가 전체 전환율 {diff_pp:.1f}%p 향상"
        recommendation = (
            f"{best_vid} 적용을 권장합니다. "
            f"전환율 {best_rate * 100:.1f}%로 통계적으로 유의한 차이가 확인되었습니다."
        )
        winning_variant = best_vid
    else:
        one_line_conclusion = (
            f"Variant 간 전환율 차이가 통계적으로 유의하지 않습니다 (차이: {diff_pp:.1f}%p)."
        )
        recommendation = (
            "통계적으로 유의한 차이가 없으므로 추가 시뮬레이션 또는 "
            "더 많은 트윈으로 재실행을 권장합니다."
        )
        winning_variant = None

    return ReportSummary(
        one_line_conclusion=one_line_conclusion,
        recommendation=recommendation,
        winning_variant=winning_variant,
        is_significant=is_significant,
    )


# ──────────────────────────────────────────────
# Sample Data Generator
# ──────────────────────────────────────────────

SAMPLE_PAGES = [
    "/home", "/category/men", "/category/women", "/category/shoes",
    "/cart", "/checkout", "/order-complete",
]
PRODUCT_IDS = [f"product_{i}" for i in range(1, 51)]
SAMPLE_CATEGORY_PAGES = ["/category/men", "/category/women", "/category/shoes"]
SAMPLE_CATEGORY_MAP = {
    "/category/men": "men", "/category/women": "women", "/category/shoes": "shoes",
}
SAMPLE_EVENT_TYPES = [
    "page_view", "click", "scroll", "purchase", "add_to_cart", "wishlist", "coupon_apply",
]
SAMPLE_CONVERSION_EVENT_TYPES = {"purchase", "add_to_cart", "wishlist"}
SAMPLE_DEVICES = ["mobile", "desktop", "tablet"]
SAMPLE_DEVICE_WEIGHTS = [0.60, 0.30, 0.10]
SAMPLE_OS_LIST = ["iOS", "Android", "Windows", "macOS"]
SAMPLE_OS_WEIGHTS = [0.35, 0.35, 0.20, 0.10]
USER_TYPES = ["price_sensitive", "brand_loyal", "explorer", "impulse"]
USER_TYPE_WEIGHTS = [0.30, 0.25, 0.25, 0.20]
SESSION_RANGE = {
    "price_sensitive": (2, 5), "brand_loyal": (3, 5),
    "explorer": (2, 4), "impulse": (2, 3),
}
EVENTS_PER_SESSION_RANGE = {
    "price_sensitive": (5, 12), "brand_loyal": (5, 10),
    "explorer": (8, 15), "impulse": (3, 6),
}


def _pick_product_page() -> str:
    pid = random.choice(PRODUCT_IDS)
    return f"/product/{pid}"


def _category_from_page(page: str) -> Optional[str]:
    if page in SAMPLE_CATEGORY_MAP:
        return SAMPLE_CATEGORY_MAP[page]
    if page.startswith("/product/"):
        return random.choice(["men", "women", "shoes"])
    return None


def _generate_session_events(
    user_id: str, session_id: str, user_type: str,
    session_start: datetime, device: str, os_name: str,
) -> List[EventRecord]:
    lo, hi = EVENTS_PER_SESSION_RANGE[user_type]
    event_count = random.randint(lo, hi)
    events: List[EventRecord] = []
    current_time = session_start
    current_page = "/home"

    for i in range(event_count):
        current_time = current_time + timedelta(seconds=random.randint(2, 120))
        if i == 0:
            page = "/home"
            event_type = "page_view"
        else:
            page, event_type = _next_page_and_event(current_page, user_type, i, event_count)

        category = _category_from_page(page)
        conversion_type = event_type if event_type in SAMPLE_CONVERSION_EVENT_TYPES else None
        value = _generate_value(event_type)
        scroll_depth = random.uniform(10.0, 100.0) if event_type == "scroll" else None

        events.append(EventRecord(
            user_id=user_id, session_id=session_id, event_type=event_type,
            timestamp=current_time, page=page,
            element=_pick_element(event_type),
            element_text=_pick_element_text(event_type),
            conversion_type=conversion_type, value=value,
            device=device, os=os_name,
            scroll_depth_pct=round(scroll_depth, 1) if scroll_depth else None,
            category=category,
        ))
        current_page = page
    return events


def _next_page_and_event(
    current_page: str, user_type: str, step: int, total_steps: int
) -> Tuple[str, str]:
    progress = step / max(total_steps - 1, 1)
    if user_type == "price_sensitive":
        return _price_sensitive_flow(current_page, progress)
    elif user_type == "brand_loyal":
        return _brand_loyal_flow(current_page, progress)
    elif user_type == "explorer":
        return _explorer_flow(current_page, progress)
    else:
        return _impulse_flow(current_page, progress)


def _price_sensitive_flow(current_page: str, progress: float) -> Tuple[str, str]:
    r = random.random()
    if current_page == "/home":
        if r < 0.4:
            return random.choice(SAMPLE_CATEGORY_PAGES), "page_view"
        return _pick_product_page(), "click"
    if current_page.startswith("/category/"):
        if r < 0.6:
            return _pick_product_page(), "page_view"
        return current_page, "scroll"
    if current_page.startswith("/product/"):
        if r < 0.25:
            return "/cart", "add_to_cart"
        if r < 0.40:
            return current_page, "coupon_apply"
        if r < 0.55:
            return current_page, "wishlist"
        return _pick_product_page(), "click"
    if current_page == "/cart":
        if progress > 0.6 and r < 0.5:
            return "/checkout", "page_view"
        if r < 0.3:
            return "/cart", "coupon_apply"
        return _pick_product_page(), "page_view"
    if current_page == "/checkout":
        if r < 0.55:
            return "/order-complete", "purchase"
        return "/cart", "page_view"
    if current_page == "/order-complete":
        return "/home", "page_view"
    return "/home", "page_view"


def _brand_loyal_flow(current_page: str, progress: float) -> Tuple[str, str]:
    preferred_category = random.choice(SAMPLE_CATEGORY_PAGES[:2])
    r = random.random()
    if current_page == "/home":
        if r < 0.5:
            return preferred_category, "page_view"
        return random.choice(SAMPLE_CATEGORY_PAGES), "page_view"
    if current_page.startswith("/category/"):
        if r < 0.55:
            return _pick_product_page(), "page_view"
        if r < 0.75:
            return current_page, "scroll"
        return preferred_category, "click"
    if current_page.startswith("/product/"):
        if r < 0.3:
            return "/cart", "add_to_cart"
        if r < 0.45:
            return current_page, "wishlist"
        return _pick_product_page(), "click"
    if current_page == "/cart":
        if progress > 0.5 and r < 0.55:
            return "/checkout", "page_view"
        return _pick_product_page(), "page_view"
    if current_page == "/checkout":
        if r < 0.6:
            return "/order-complete", "purchase"
        return "/cart", "page_view"
    if current_page == "/order-complete":
        return "/home", "page_view"
    return "/home", "page_view"


def _explorer_flow(current_page: str, progress: float) -> Tuple[str, str]:
    r = random.random()
    if current_page == "/home":
        return random.choice(SAMPLE_CATEGORY_PAGES), "page_view"
    if current_page.startswith("/category/"):
        if r < 0.5:
            return _pick_product_page(), "page_view"
        if r < 0.8:
            return current_page, "scroll"
        return random.choice(SAMPLE_CATEGORY_PAGES), "page_view"
    if current_page.startswith("/product/"):
        if r < 0.1:
            return "/cart", "add_to_cart"
        if r < 0.3:
            return current_page, "scroll"
        if r < 0.5:
            return _pick_product_page(), "page_view"
        return random.choice(SAMPLE_CATEGORY_PAGES), "page_view"
    if current_page == "/cart":
        if r < 0.25:
            return "/checkout", "page_view"
        return _pick_product_page(), "page_view"
    if current_page == "/checkout":
        if r < 0.35:
            return "/order-complete", "purchase"
        return "/cart", "page_view"
    if current_page == "/order-complete":
        return "/home", "page_view"
    return "/home", "page_view"


def _impulse_flow(current_page: str, progress: float) -> Tuple[str, str]:
    r = random.random()
    if current_page == "/home":
        if r < 0.5:
            return _pick_product_page(), "click"
        return random.choice(SAMPLE_CATEGORY_PAGES), "page_view"
    if current_page.startswith("/category/"):
        return _pick_product_page(), "click"
    if current_page.startswith("/product/"):
        if r < 0.5:
            return "/cart", "add_to_cart"
        if r < 0.65:
            return current_page, "click"
        return _pick_product_page(), "click"
    if current_page == "/cart":
        if r < 0.7:
            return "/checkout", "page_view"
        return "/cart", "click"
    if current_page == "/checkout":
        if r < 0.8:
            return "/order-complete", "purchase"
        return "/cart", "page_view"
    if current_page == "/order-complete":
        return "/home", "page_view"
    return "/home", "page_view"


def _generate_value(event_type: str) -> Optional[float]:
    if event_type == "purchase":
        return float(random.randint(10000, 200000))
    return None


def _pick_element(event_type: str) -> Optional[str]:
    elements = {
        "click": random.choice(["btn_buy", "btn_detail", "img_product", "link_category"]),
        "add_to_cart": "btn_add_cart",
        "wishlist": "btn_wishlist",
        "coupon_apply": "btn_coupon",
        "purchase": "btn_purchase",
        "scroll": None,
        "page_view": None,
    }
    return elements.get(event_type)


def _pick_element_text(event_type: str) -> Optional[str]:
    texts = {
        "click": random.choice(["구매하기", "상세보기", "상품 이미지", "카테고리"]),
        "add_to_cart": "장바구니 담기",
        "wishlist": "찜하기",
        "coupon_apply": "쿠폰 적용",
        "purchase": "결제하기",
    }
    return texts.get(event_type)


def generate_sample_data(user_count: int = 100, days: int = 30) -> List[EventRecord]:
    """무신사 패션 이커머스를 가정한 현실적인 이벤트 로그를 생성한다."""
    all_events: List[EventRecord] = []
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=days)

    user_types = random.choices(USER_TYPES, weights=USER_TYPE_WEIGHTS, k=user_count)

    for i in range(user_count):
        user_id = f"user_{i + 1:04d}"
        user_type = user_types[i]
        device = random.choices(SAMPLE_DEVICES, weights=SAMPLE_DEVICE_WEIGHTS, k=1)[0]
        os_name = random.choices(SAMPLE_OS_LIST, weights=SAMPLE_OS_WEIGHTS, k=1)[0]

        lo, hi = SESSION_RANGE[user_type]
        session_count = random.randint(lo, hi)

        for _ in range(session_count):
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            session_start = start_date + timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )
            session_events = _generate_session_events(
                user_id=user_id, session_id=session_id, user_type=user_type,
                session_start=session_start, device=device, os_name=os_name,
            )
            all_events.extend(session_events)

    all_events.sort(key=lambda e: e.timestamp)
    return all_events


def generate_musinsa_scenario_config() -> dict:
    """무신사 프로모션 A/B 테스트 MVP 시나리오 설정을 반환한다."""
    return {
        "scenario_name": "무신사 프로모션 A/B 테스트",
        "scenario_type": "promotion",
        "target_page": "/home",
        "variants": [
            {
                "variant_id": "variant_a", "name": "control",
                "description": "오늘만 전제품 20% 할인",
                "target_page": "/home",
                "changes": {"promotion_text": "오늘만 전제품 20% 할인"},
            },
            {
                "variant_id": "variant_b", "name": "treatment",
                "description": "오늘만 무료배송 + 5% 적립금 제공",
                "target_page": "/home",
                "changes": {"promotion_text": "오늘만 무료배송 + 5% 적립금 제공"},
            },
        ],
        "reaction_rules": [
            {"segment_id": "*price_sensitive*", "variant_id": "variant_a", "conversion_rate_modifier": 1.4, "condition": None},
            {"segment_id": "*price_sensitive*", "variant_id": "variant_b", "conversion_rate_modifier": 1.0, "condition": None},
            {"segment_id": "*brand_loyal*", "variant_id": "variant_a", "conversion_rate_modifier": 1.0, "condition": None},
            {"segment_id": "*brand_loyal*", "variant_id": "variant_b", "conversion_rate_modifier": 1.3, "condition": None},
            {"segment_id": "*explorer*", "variant_id": "variant_a", "conversion_rate_modifier": 0.7, "condition": None},
            {"segment_id": "*explorer*", "variant_id": "variant_b", "conversion_rate_modifier": 0.7, "condition": None},
            {"segment_id": "*impulse*", "variant_id": "variant_a", "conversion_rate_modifier": 1.2, "condition": None},
            {"segment_id": "*impulse*", "variant_id": "variant_b", "conversion_rate_modifier": 1.2, "condition": None},
        ],
        "primary_metric": "purchase_conversion_rate",
        "twin_count": 1000,
        "analysis_tags": ["price_sensitivity", "device", "visit_frequency"],
        "analysis_dimensions": [
            {
                "tag_name": "price_sensitivity",
                "source_attribute": "preferences.price_sensitivity",
                "classification_rules": {"high": ">0.7", "medium": "0.3~0.7", "low": "<0.3"},
            },
            {
                "tag_name": "device",
                "source_attribute": "demographics.primary_device",
                "classification_rules": None,
            },
            {
                "tag_name": "visit_frequency",
                "source_attribute": "behavior.total_sessions",
                "classification_rules": {"heavy": ">=10", "light": "<10"},
            },
        ],
    }


# ──────────────────────────────────────────────
# 업종별 샘플 데이터 생성기
# ──────────────────────────────────────────────

INDUSTRY_CONFIGS = {
    "패션 이커머스 (무신사)": {
        "pages": ["/home", "/category/men", "/category/women", "/category/shoes",
                  "/cart", "/checkout", "/order-complete"],
        "product_prefix": "product",
        "categories": ["men", "women", "shoes"],
        "event_types": ["page_view", "click", "scroll", "purchase", "add_to_cart", "wishlist", "coupon_apply"],
        "conversion_events": {"purchase", "add_to_cart", "wishlist"},
        "value_range": (10000, 200000),
        "description": "패션 이커머스 서비스 (상품 조회, 장바구니, 구매)",
    },
    "금융 (은행/증권)": {
        "pages": ["/home", "/products/deposit", "/products/loan", "/products/fund",
                  "/apply/start", "/apply/verify", "/apply/complete"],
        "product_prefix": "fin_product",
        "categories": ["deposit", "loan", "fund", "insurance"],
        "event_types": ["page_view", "click", "scroll", "apply_complete", "calculator_use", "document_download", "consultation_request"],
        "conversion_events": {"apply_complete", "consultation_request"},
        "value_range": (1000000, 50000000),
        "description": "금융 서비스 (상품 조회, 금리 계산, 신청 완료)",
    },
    "OTT 콘텐츠 (스트리밍)": {
        "pages": ["/home", "/browse/movie", "/browse/drama", "/browse/variety",
                  "/content/detail", "/player", "/subscribe"],
        "product_prefix": "content",
        "categories": ["movie", "drama", "variety", "documentary"],
        "event_types": ["page_view", "click", "scroll", "play_start", "play_complete", "add_watchlist", "subscribe"],
        "conversion_events": {"subscribe", "play_start", "add_watchlist"},
        "value_range": (7900, 17000),
        "description": "OTT 스트리밍 서비스 (콘텐츠 탐색, 시청, 구독)",
    },
}


def generate_industry_sample_data(
    industry: str, user_count: int = 100, days: int = 30
) -> List[EventRecord]:
    """업종별 샘플 이벤트 로그를 생성한다."""
    config = INDUSTRY_CONFIGS.get(industry)
    if config is None:
        return generate_sample_data(user_count, days)

    all_events: List[EventRecord] = []
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=days)

    product_ids = [f"{config['product_prefix']}_{i}" for i in range(1, 51)]
    pages = config["pages"]
    categories = config["categories"]
    event_types = config["event_types"]
    conversion_events = config["conversion_events"]
    value_lo, value_hi = config["value_range"]

    user_types_list = random.choices(USER_TYPES, weights=USER_TYPE_WEIGHTS, k=user_count)

    for i in range(user_count):
        user_id = f"user_{i + 1:04d}"
        user_type = user_types_list[i]
        device = random.choices(SAMPLE_DEVICES, weights=SAMPLE_DEVICE_WEIGHTS, k=1)[0]
        os_name = random.choices(SAMPLE_OS_LIST, weights=SAMPLE_OS_WEIGHTS, k=1)[0]

        lo_s, hi_s = SESSION_RANGE[user_type]
        session_count = random.randint(lo_s, hi_s)

        for _ in range(session_count):
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            session_start = start_date + timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )

            lo_e, hi_e = EVENTS_PER_SESSION_RANGE[user_type]
            event_count = random.randint(lo_e, hi_e)
            current_time = session_start
            current_page = pages[0]

            for j in range(event_count):
                current_time = current_time + timedelta(seconds=random.randint(2, 120))

                if j == 0:
                    page = pages[0]
                    evt = "page_view"
                else:
                    # 간단한 확률 기반 페이지 전이
                    r = random.random()
                    if r < 0.3:
                        page = random.choice(pages)
                        evt = "page_view"
                    elif r < 0.5:
                        page = f"/{config['product_prefix']}/{random.choice(product_ids)}"
                        evt = "click"
                    elif r < 0.65:
                        page = current_page
                        evt = "scroll"
                    elif r < 0.8:
                        evt = random.choice([e for e in event_types if e not in ("page_view", "scroll")])
                        page = current_page
                    else:
                        # 전환 이벤트 (유저 유형에 따라 확률 조절)
                        if user_type == "impulse" or (user_type == "price_sensitive" and r < 0.9):
                            conv_events = list(conversion_events)
                            evt = random.choice(conv_events)
                            page = pages[-1] if "complete" in pages[-1] else current_page
                        else:
                            page = random.choice(pages[1:-1]) if len(pages) > 2 else pages[0]
                            evt = "page_view"

                category = random.choice(categories) if random.random() < 0.4 else None
                conversion_type = evt if evt in conversion_events else None
                value = float(random.randint(value_lo, value_hi)) if evt in conversion_events and "complete" in evt or evt in ("purchase", "subscribe", "apply_complete") else None

                all_events.append(EventRecord(
                    user_id=user_id, session_id=session_id, event_type=evt,
                    timestamp=current_time, page=page,
                    element=_pick_element(evt) if evt in ("click", "add_to_cart", "wishlist", "coupon_apply", "purchase") else None,
                    element_text=None,
                    conversion_type=conversion_type, value=value,
                    device=device, os=os_name,
                    scroll_depth_pct=round(random.uniform(10, 100), 1) if evt == "scroll" else None,
                    category=category,
                ))
                current_page = page

    all_events.sort(key=lambda e: e.timestamp)
    return all_events


# ──────────────────────────────────────────────
# Pipeline Orchestrator
# ──────────────────────────────────────────────

def step1_upload(file_content: bytes, filename: str) -> PipelineUploadResult:
    """스텝 1: 데이터 업로드 → 파싱 → 프로파일링 → 기본 세그먼트 생성."""
    try:
        result = upload_file(file_content, filename)
    except Exception as exc:
        raise PipelineError("upload", str(exc)) from exc

    try:
        content_str = file_content.decode("utf-8")
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            events = parse_csv(content_str)
        else:
            events = parse_json_events(content_str)
    except Exception as exc:
        raise PipelineError("parse", str(exc)) from exc

    try:
        profiles = generate_profiles(events)
    except Exception as exc:
        raise PipelineError("profiling", str(exc)) from exc

    active_profiles = [p for p in profiles if p.status == "active"]
    excluded_count = len(profiles) - len(active_profiles)

    try:
        base_segments = cluster_profiles(profiles)
    except Exception as exc:
        raise PipelineError("segmentation", str(exc)) from exc

    return PipelineUploadResult(
        upload_id=result.upload_id,
        upload_summary=result,
        events=events,
        profiles=profiles,
        profile_count=len(active_profiles),
        excluded_user_count=excluded_count,
        base_segments=base_segments,
        base_segment_count=len(base_segments),
    )


def step2_simulate(
    config: PipelineSimulateConfig,
    events: List[EventRecord],
    profiles: List[UserProfile],
    base_segments: List[Segment],
) -> PipelineSimulateResult:
    """스텝 2: 시나리오 → 변수 도출 → 맞춤 세그먼트 → Markov → 트윈 → 시뮬레이션 → 리포트."""
    # 1. Resolve key variables
    try:
        key_variables = resolve_key_variables(config.scenario_type, config.key_variables)
    except Exception as exc:
        raise PipelineError("variable_resolution", str(exc)) from exc

    # 2. Create scenario
    try:
        scenario_config = {
            "name": config.scenario_name,
            "scenario_type": config.scenario_type,
            "target_page": config.target_page,
            "variants": config.variants,
            "reaction_rules": config.reaction_rules,
            "primary_metric": config.primary_metric,
            "analysis_tags": config.analysis_tags or [],
            "analysis_dimensions": config.analysis_dimensions or [],
        }
        scenario = create_scenario(scenario_config)
    except Exception as exc:
        raise PipelineError("scenario_creation", str(exc)) from exc

    # 3. Recluster for scenario
    try:
        scenario_segments = recluster_for_scenario(profiles, key_variables, scenario.scenario_id)
    except Exception as exc:
        raise PipelineError("scenario_segmentation", str(exc)) from exc

    # 4. Build Markov models per scenario segment
    try:
        user_events_map: Dict[str, List[EventRecord]] = {}
        for ev in events:
            user_events_map.setdefault(ev.user_id, []).append(ev)

        default_model = get_default_model(events)

        models: Dict[str, MarkovChainModel] = {}
        for seg in scenario_segments:
            seg_events: List[EventRecord] = []
            for uid in seg.member_user_ids:
                seg_events.extend(user_events_map.get(uid, []))

            if has_sufficient_sessions(seg_events):
                models[seg.segment_id] = build_markov_model(seg.segment_id, seg_events)
            else:
                models[seg.segment_id] = default_model

        models["default"] = default_model
    except Exception as exc:
        raise PipelineError("markov_building", str(exc)) from exc

    # 5. Generate twins
    try:
        twin_result = generate_twins(config.twin_count, scenario_segments, models)
        twins = twin_result.twins
    except Exception as exc:
        raise PipelineError("twin_generation", str(exc)) from exc

    # 6. Run simulation
    try:
        reaction = ReactionModel()
        sim_result = run_simulation(scenario, twins, models, reaction)
    except Exception as exc:
        raise PipelineError("simulation", str(exc)) from exc

    # 7. Statistics + report
    try:
        chi_sq = chi_square_test(sim_result.variant_results)
        sim_result.overall_chi_square = chi_sq

        report_summary = generate_report_summary(sim_result, sim_result.segment_analyses)
        sim_result.report_summary = report_summary

        segment_statistics = []
        for sa in sim_result.segment_analyses:
            if sa.variant_results and len(sa.variant_results) >= 2:
                try:
                    seg_chi = chi_square_test(sa.variant_results)
                    sa.chi_square = seg_chi
                    segment_statistics.append(seg_chi)
                except (ValueError, Exception):
                    pass

        best_variants = find_best_variant_per_segment(sim_result.segment_analyses)

        funnel_comparison: Dict[str, Dict[str, float]] = {}
        for vid, vr in sim_result.variant_results.items():
            funnel_comparison[vid] = vr.funnel_drop_rates

        report = SimulationReport(
            summary=report_summary,
            variant_metrics=sim_result.variant_results,
            weighted_conversion_rates=sim_result.weighted_conversion_rates,
            segment_heatmap=sim_result.segment_analyses,
            tag_analyses=sim_result.tag_analyses,
            funnel_comparison=funnel_comparison,
            overall_statistics=chi_sq,
            segment_statistics=segment_statistics,
            best_variants_by_segment=best_variants,
        )
    except Exception as exc:
        raise PipelineError("statistics", str(exc)) from exc

    return PipelineSimulateResult(
        scenario_id=scenario.scenario_id,
        key_variables=key_variables,
        scenario_segment_count=len(scenario_segments),
        twin_count=len(twins),
        simulation_id=sim_result.simulation_id,
        report=report,
    )


# ═══════════════════════════════════════════════════════════════════
# === STREAMLIT UI ===
# ═══════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="TwinPilot — Digital Twin A/B Testing",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# 커스텀 CSS (Pretendard 폰트 + 브랜딩)
# ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    /* Streamlit 내부 요소 전체 폰트 강제 적용 (레이아웃 요소 제외) */
    .stMarkdown, .stMarkdown *,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    /* 좌상단 서비스명 */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0 0 16px 0;
        border-bottom: 2px solid #e8eaf6;
        margin-bottom: 20px;
    }
    .brand-name {
        font-size: 1.4rem;
        font-weight: 800;
        color: #3f51b5;
        letter-spacing: -0.5px;
    }
    .brand-tag {
        font-size: 0.75rem;
        color: #999;
        font-weight: 400;
        margin-left: 4px;
    }

    /* 메인 타이틀 */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3f51b5, #7c4dff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -1px;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #777;
        margin-bottom: 2rem;
        font-weight: 400;
        line-height: 1.6;
    }

    /* 3단 카드 */
    .step-card {
        background: #f8f9fc;
        border-radius: 14px;
        padding: 1.8rem 1.2rem;
        text-align: center;
        border: 1px solid #e8eaf6;
        transition: box-shadow 0.2s;
    }
    .step-card:hover {
        box-shadow: 0 4px 16px rgba(63, 81, 181, 0.1);
    }
    .step-card h4 {
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0.6rem 0 0.4rem 0;
        color: #333;
    }
    .step-card p {
        font-size: 0.88rem;
        color: #666;
        line-height: 1.5;
        margin: 0;
    }
    .step-number {
        font-size: 1.8rem;
        font-weight: 800;
        color: #3f51b5;
    }

    /* 섹션 제목 — 자연스러운 크기 계층 */
    .stMarkdown h1 {
        font-size: 1.6rem;
        font-weight: 800;
        margin-top: 0.8rem;
        margin-bottom: 0.6rem;
    }
    .stMarkdown h2, [data-testid="stHeadingWithActionElements"] {
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 0.6rem;
        margin-bottom: 0.4rem;
        letter-spacing: -0.3px;
    }
    .stMarkdown h3 {
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-bottom: 0.3rem;
    }
    .stMarkdown h4 {
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.4rem;
        margin-bottom: 0.2rem;
        color: #444;
    }

    /* 본문 */
    .stMarkdown p, [data-testid="stMarkdownContainer"] p {
        font-size: 0.9rem;
        line-height: 1.6;
        margin-bottom: 0.5rem;
    }
    td, th {
        font-size: 0.85rem;
        line-height: 1.4;
    }

    /* 영역 간격 */
    .stDivider {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    [data-testid="stVerticalBlock"] > div {
        margin-bottom: 0.3rem;
    }
    .stSubheader {
        margin-top: 0.5rem;
    }

    /* 탭 내부 간격 */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.8rem;
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
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-not-significant {
        background: #ff9800;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .feature-icon {
        font-size: 2.2rem;
        margin-bottom: 0.4rem;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Pretendard', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* 헤더 앵커 링크 숨기기 */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    .stMarkdown a[href^="#"],
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* 데이터프레임 컬럼 소팅 비활성화 */
    [data-testid="stDataFrame"] th button {
        display: none !important;
    }

    /* 버튼 너비 제한 — 전체 너비 대신 콘텐츠 맞춤 */
    .stButton > button {
        max-width: 320px !important;
    }
    .stButton {
        display: flex;
        justify-content: flex-start;
    }

    /* 전체 컨테이너 최대 너비 */
    .block-container {
        max-width: 960px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* 메트릭 카드 간격 */
    [data-testid="stMetric"] {
        background: #f8f9fc;
        border-radius: 10px;
        padding: 12px 16px;
    }

    /* expander 스타일 */
    .streamlit-expanderHeader {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 좌상단 브랜드 헤더
# ──────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <span style="font-size:1.5rem;">🧬</span>
    <span class="brand-name">TwinPilot</span>
    <span class="brand-tag">Digital Twin A/B Testing</span>
</div>
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
    st.markdown('<p class="main-title">TwinPilot</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">고객 행동 데이터 기반 디지털 트윈으로<br>A/B 테스트 결과를 사전에 시뮬레이션합니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Problem Statement
    st.subheader("기존 A/B 테스트의 한계")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.markdown("#### ⏱️ 시간")
        st.markdown("통계적 유의성 확보까지 최소 2~4주 소요. 빠른 의사결정이 어렵습니다.")
    with col_p2:
        st.markdown("#### 💰 비용")
        st.markdown("실제 트래픽을 분할해야 하므로 매출 손실 리스크가 존재합니다.")
    with col_p3:
        st.markdown("#### 📊 트래픽")
        st.markdown("충분한 샘플 확보를 위해 대규모 트래픽이 필요합니다.")

    st.divider()

    # Solution
    st.subheader("TwinPilot의 접근")
    st.markdown("""
    과거 고객 행동 데이터를 기반으로 **디지털 트윈(가상 유저)**을 생성하고,
    두 가지 시나리오에 대한 반응을 시뮬레이션하여 **실제 테스트 전에 결과를 예측**합니다.
    동일한 가상 유저가 시나리오 A와 B를 모두 경험하므로, 순수한 시나리오 효과를 비교할 수 있습니다.
    """)

    st.divider()

    # How it works — 3-step flow
    st.subheader("3스텝 사용 플로우")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">1</div>
            <h4>고객 데이터 셋팅</h4>
            <p>업종별 샘플 데이터를 선택하거나<br>CSV/JSON 파일을 직접 업로드</p>
        </div>
        """, unsafe_allow_html=True)
    with col_s2:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">2</div>
            <h4>시나리오 설정</h4>
            <p>시나리오 유형 선택, A/B 두 가지<br>시나리오 설명 입력, 트윈 수 설정</p>
        </div>
        """, unsafe_allow_html=True)
    with col_s3:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">3</div>
            <h4>결과 리포트</h4>
            <p>세그먼트별 전환율 비교, 퍼널 분석,<br>통계 검정 등 7개 섹션 리포트</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Key Features
    st.subheader("핵심 기능")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown('<div class="feature-icon">🎯</div>', unsafe_allow_html=True)
        st.markdown("**세그먼트별 차별 반응 분석**")
        st.markdown("시나리오 유형에 맞는 주요 변수를 자동 도출하고, 해당 변수 기반으로 유저를 세그먼트화하여 그룹별 반응 차이를 분석합니다.")
    with col_f2:
        st.markdown('<div class="feature-icon">🔬</div>', unsafe_allow_html=True)
        st.markdown("**동일 유저 대상 비교**")
        st.markdown("동일한 디지털 트윈이 시나리오 A와 B를 모두 경험합니다. 유저 구성 차이 없이 순수한 시나리오 효과만 비교할 수 있습니다.")
    with col_f3:
        st.markdown('<div class="feature-icon">📊</div>', unsafe_allow_html=True)
        st.markdown("**통계적 유의성 검증**")
        st.markdown("카이제곱 검정, 95% 신뢰구간, Cohen's h 효과 크기로 결과의 통계적 신뢰도를 제공합니다.")

    st.divider()

    # Supported Industries
    st.subheader("지원 업종")
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        st.markdown("#### 🛍️ 이커머스")
        st.markdown("프로모션, 가격 표시, CTA 변경 등 구매 전환 최적화")
    with col_i2:
        st.markdown("#### 🏦 금융")
        st.markdown("상품 신청, 대출 퍼널, 상담 전환 등 금융 서비스 최적화")
    with col_i3:
        st.markdown("#### 🎬 OTT/콘텐츠")
        st.markdown("구독 전환, 콘텐츠 시청, 워치리스트 추가 등 콘텐츠 서비스 최적화")

    st.divider()

    # Tech Stack
    st.subheader("기술 스택")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.markdown("#### Markov Chain")
        st.markdown("세그먼트별 페이지 전이 확률 모델을 학습하여 현실적인 유저 여정을 시뮬레이션합니다.")
    with col_t2:
        st.markdown("#### K-Means Clustering")
        st.markdown("시나리오별 주요 변수를 기반으로 유저를 동적으로 세그먼트화합니다.")
    with col_t3:
        st.markdown("#### 카이제곱 검정")
        st.markdown("시나리오 간 전환율 차이의 통계적 유의성을 검증합니다.")


# ══════════════════════════════════════════════
# Tab 2: 이용 가이드
# ══════════════════════════════════════════════
with tab_guide:
    st.header("📖 이용 가이드")
    st.markdown("TwinPilot을 사용하는 3단계 가이드입니다.")
    st.divider()

    # Step 1
    st.subheader("Step 1: 고객 데이터 셋팅")
    st.markdown("""
    두 가지 방법 중 하나를 선택합니다:
    - **샘플 데이터 사용**: 업종(패션 이커머스, 금융, OTT)을 선택하면 가상 데이터가 자동 생성됩니다.
    - **직접 파일 업로드**: CSV 또는 JSON 형식의 이벤트 로그 파일을 업로드합니다.

    데이터가 로드되면 자동으로 유저 프로파일링과 기본 세그먼트 생성이 진행됩니다.
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

    with st.expander("선택 필드 및 CSV 예시"):
        optional_fields = pd.DataFrame({
            "필드명": ["page", "device", "os", "conversion_type", "value", "category"],
            "설명": [
                "페이지 경로 (예: /home, /product/123)",
                "디바이스 (mobile, desktop, tablet)",
                "운영체제 (iOS, Android 등)",
                "전환 유형 (purchase, add_to_cart 등)",
                "금액 (구매 시)",
                "상품 카테고리",
            ],
        })
        st.dataframe(optional_fields, use_container_width=True, hide_index=True)

        st.code("""user_id,session_id,event_type,timestamp,page,device,os,category
user_0001,sess_abc123,page_view,2024-01-15T10:30:00,/home,mobile,iOS,
user_0001,sess_abc123,click,2024-01-15T10:30:45,/category/men,mobile,iOS,men
user_0001,sess_abc123,purchase,2024-01-15T10:35:00,/order-complete,mobile,iOS,""", language="csv")

    st.divider()

    # Step 2
    st.subheader("Step 2: 시나리오 설정")
    st.markdown("""
    비교할 두 가지 시나리오를 설정합니다.
    """)

    st.markdown("**설정 항목**")
    settings_data = pd.DataFrame({
        "항목": ["시나리오 이름", "시나리오 유형", "시나리오 A / B", "타겟 페이지", "트윈 수"],
        "설명": [
            "테스트의 이름 (예: 프로모션 A/B 테스트)",
            "promotion, cta_change, price_display, funnel_change, ui_position, timing 중 선택",
            "비교할 두 가지 시나리오 설명을 각각 입력",
            "시뮬레이션 대상 페이지 (예: /home)",
            "생성할 디지털 트윈 수 (100~10,000). 동일한 트윈이 A, B 모두 테스트",
        ],
    })
    st.dataframe(settings_data, use_container_width=True, hide_index=True)

    st.markdown("""
    시나리오 유형을 선택하면 해당 유형에 맞는 **주요 행동 변수가 자동 도출**되고,
    그 변수를 기반으로 유저 세그먼트가 동적으로 재구성됩니다.
    """)

    st.divider()

    # Step 3
    st.subheader("Step 3: 결과 리포트")
    st.markdown("시뮬레이션 완료 후 7개 섹션의 리포트가 제공됩니다.")

    report_sections = pd.DataFrame({
        "섹션": [
            "① 실험 요약", "② 핵심 지표 비교", "③ 세그먼트 히트맵",
            "④ 태그별 분석", "⑤ 퍼널 비교", "⑥ 통계 검정",
            "⑦ 세그먼트별 최적 시나리오",
        ],
        "내용": [
            "한 줄 결론 + 추천 시나리오 + 통계적 유의성 여부",
            "시나리오별 전환율, 전환 수, 가중 전환율, 평균 세션 시간",
            "세그먼트 × 시나리오 전환율 비교 차트",
            "가격 민감도, 디바이스, 방문 빈도 등 태그별 그룹 전환율",
            "시나리오별 퍼널 단계 도달률 비교",
            "카이제곱 통계량, p-value, 95% 신뢰구간, Cohen's h",
            "각 세그먼트에서 더 높은 전환율을 보인 시나리오",
        ],
    })
    st.dataframe(report_sections, use_container_width=True, hide_index=True)

    st.divider()

    # FAQ
    st.subheader("FAQ")
    with st.expander("디지털 트윈이란 무엇인가요?"):
        st.markdown("""
        디지털 트윈은 실제 유저의 행동 패턴을 학습한 가상 유저입니다.
        각 트윈은 특정 세그먼트에 속하며, Markov Chain 전이 확률 모델에 따라
        페이지 이동과 전환 행동을 시뮬레이션합니다.
        """)
    with st.expander("동일한 유저가 A, B를 모두 테스트하나요?"):
        st.markdown("""
        네. 트윈 수를 1,000으로 설정하면 동일한 1,000명의 가상 유저가
        시나리오 A와 시나리오 B를 각각 경험합니다.
        유저 구성 차이 없이 순수한 시나리오 효과만 비교할 수 있습니다.
        """)
    with st.expander("시뮬레이션 결과는 얼마나 정확한가요?"):
        st.markdown("""
        과거 데이터 패턴을 기반으로 한 예측입니다.
        실제 A/B 테스트를 완전히 대체하기보다는
        사전 검증 및 가설 수립 도구로 활용하는 것을 권장합니다.
        """)
    with st.expander("최소 데이터 요구사항은?"):
        st.markdown("""
        - 최소 10명 이상의 유저 (유저당 3건 이상의 이벤트)
        - page_view 이벤트에 page 필드 포함
        - 전환 이벤트 (purchase, subscribe 등) 포함
        """)
    with st.expander("트윈 수는 어떻게 설정하나요?"):
        st.markdown("""
        - **1,000개** (기본값): 빠른 탐색용. 대략적인 경향 파악에 적합합니다.
        - **5,000개**: 세그먼트별 분석에 충분한 샘플 확보.
        - **10,000개**: 높은 통계적 신뢰도. 시뮬레이션 시간이 다소 길어질 수 있습니다.
        """)


# ══════════════════════════════════════════════
# Tab 3: 데모 (Interactive — Step Wizard)
# ══════════════════════════════════════════════
with tab_demo:

    # 현재 스텝 결정
    if "sim_result" in st.session_state:
        current_step = 3
    elif "upload_result" in st.session_state:
        current_step = 2
    else:
        current_step = 1

    # 스텝 인디케이터
    step_labels = ["① 고객 데이터 셋팅", "② 시나리오 설정", "③ 결과 리포트"]
    cols_step = st.columns(3)
    for i, lbl in enumerate(step_labels):
        step_num = i + 1
        with cols_step[i]:
            if step_num < current_step:
                st.markdown(f'<p style="text-align:center; color:#4caf50; font-weight:700; font-size:0.9rem;">✅ {lbl}</p>', unsafe_allow_html=True)
            elif step_num == current_step:
                st.markdown(f'<p style="text-align:center; color:#3f51b5; font-weight:700; font-size:0.9rem;">● {lbl}</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p style="text-align:center; color:#ccc; font-size:0.9rem;">○ {lbl}</p>', unsafe_allow_html=True)

    st.divider()

    # ══════════════════════════════════════
    # STEP 1
    # ══════════════════════════════════════
    if current_step == 1:
        st.subheader("고객 데이터 셋팅")
        data_method = st.radio("데이터 소스를 선택하세요", options=["🎲 샘플 데이터 사용", "📁 직접 파일 업로드"], horizontal=True, label_visibility="collapsed")

        if data_method == "🎲 샘플 데이터 사용":
            industry = st.selectbox("업종 선택", options=list(INDUSTRY_CONFIGS.keys()), index=0)
            st.caption(INDUSTRY_CONFIGS[industry]["description"])
            if st.button("샘플 데이터 생성 및 분석 시작", type="primary"):
                with st.spinner("샘플 데이터 생성 및 분석 중..."):
                    events = generate_industry_sample_data(industry, user_count=100, days=30)
                    csv_str_val = serialize_to_csv(events)
                    csv_bytes_val = csv_str_val.encode("utf-8")
                    upload_result = step1_upload(csv_bytes_val, "sample_data.csv")
                    st.session_state["upload_result"] = upload_result
                    st.session_state["csv_bytes"] = csv_bytes_val
                    st.session_state["csv_str"] = csv_str_val
                    st.session_state["data_source"] = "sample"
                    st.session_state["industry"] = industry
                    st.session_state.pop("sim_result", None)
                st.rerun()
        else:
            st.caption("CSV 또는 JSON 형식의 이벤트 로그 파일을 업로드하세요")
            uploaded_file = st.file_uploader("파일 선택", type=["csv", "json"], label_visibility="collapsed")
            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                filename = uploaded_file.name
                try:
                    with st.spinner("파일 분석 중..."):
                        upload_result = step1_upload(file_bytes, filename)
                        st.session_state["upload_result"] = upload_result
                        st.session_state["csv_bytes"] = file_bytes
                        st.session_state["csv_str"] = file_bytes.decode("utf-8")
                        st.session_state["data_source"] = "upload"
                        st.session_state.pop("sim_result", None)
                    st.rerun()
                except (PipelineError, ValueError) as e:
                    st.error(f"파일 처리 실패: {e}")

    # ══════════════════════════════════════
    # STEP 2
    # ══════════════════════════════════════
    elif current_step == 2:
        ur = st.session_state["upload_result"]

        with st.expander("📊 데이터 요약", expanded=False):
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("총 이벤트", f"{ur.upload_summary.total_events:,}")
            col_m2.metric("유저 수", f"{ur.upload_summary.unique_users:,}")
            col_m3.metric("프로파일", f"{ur.profile_count:,}")
            col_m4.metric("세그먼트", f"{ur.base_segment_count}")

        st.subheader("시나리오 설정")

        use_sample_scenario = False
        if st.session_state.get("data_source") == "sample":
            use_sample_scenario = st.checkbox("샘플 시나리오 자동 채우기", value=True)
        sample_config = generate_musinsa_scenario_config() if use_sample_scenario else None

        col_r1a, col_r1b = st.columns(2)
        with col_r1a:
            scenario_name = st.text_input("시나리오 이름", value=sample_config["scenario_name"] if sample_config else "", placeholder="예: 프로모션 A/B 테스트")
        with col_r1b:
            scenario_type = st.selectbox("시나리오 유형", options=["promotion", "cta_change", "price_display", "funnel_change", "ui_position", "timing"])

        st.markdown('<p style="margin-bottom:-10px;">시나리오 설명</p>', unsafe_allow_html=True)
        col_r2a, col_r2b = st.columns(2)
        with col_r2a:
            st.markdown('<p style="font-size:0.82rem; color:#888; margin-bottom:2px;">시나리오 A</p>', unsafe_allow_html=True)
            variant_a_desc = st.text_input("시나리오 A", value=sample_config["variants"][0]["description"] if sample_config else "", placeholder="예: 오늘만 전제품 20% 할인", label_visibility="collapsed")
        with col_r2b:
            st.markdown('<p style="font-size:0.82rem; color:#888; margin-bottom:2px;">시나리오 B</p>', unsafe_allow_html=True)
            variant_b_desc = st.text_input("시나리오 B", value=sample_config["variants"][1]["description"] if sample_config else "", placeholder="예: 무료배송 + 5% 적립금", label_visibility="collapsed")

        col_r3a, col_r3b = st.columns(2)
        with col_r3a:
            target_page = st.text_input("타겟 페이지", value=sample_config["target_page"] if sample_config else "/home")
        with col_r3b:
            twin_count = st.slider("트윈 수", min_value=100, max_value=10000, value=sample_config["twin_count"] if sample_config else 1000, step=100, help="동일한 트윈이 A, B 모두 테스트합니다.")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("↩️ 데이터 다시 선택"):
                for key in ["upload_result", "sim_result", "csv_bytes", "csv_str", "data_source"]:
                    st.session_state.pop(key, None)
                st.rerun()
        with col_btn2:
            can_run = bool(scenario_name and variant_a_desc and variant_b_desc and target_page)
            if st.button("▶️ 시뮬레이션 실행", type="primary", disabled=not can_run):
                variants = [
                    {"variant_id": "variant_a", "name": "시나리오 A", "description": variant_a_desc, "target_page": target_page, "changes": {}},
                    {"variant_id": "variant_b", "name": "시나리오 B", "description": variant_b_desc, "target_page": target_page, "changes": {}},
                ]
                reaction_rules = sample_config["reaction_rules"] if sample_config else []
                analysis_tags = sample_config.get("analysis_tags", []) if sample_config else []
                analysis_dimensions = sample_config.get("analysis_dimensions", []) if sample_config else []
                config = PipelineSimulateConfig(
                    scenario_name=scenario_name, scenario_type=scenario_type, target_page=target_page,
                    variants=variants, reaction_rules=reaction_rules, primary_metric="purchase_conversion_rate",
                    twin_count=twin_count,
                    analysis_tags=analysis_tags if analysis_tags else None,
                    analysis_dimensions=analysis_dimensions if analysis_dimensions else None,
                )
                progress_bar = st.progress(0, text="시뮬레이션 준비 중...")
                try:
                    progress_bar.progress(20, text="세그먼트 재클러스터링...")
                    progress_bar.progress(50, text="디지털 트윈 생성 및 시뮬레이션...")
                    sim_result = step2_simulate(config=config, events=ur.events, profiles=ur.profiles, base_segments=ur.base_segments)
                    progress_bar.progress(100, text="완료!")
                    st.session_state["sim_result"] = sim_result
                    st.rerun()
                except PipelineError as e:
                    progress_bar.empty()
                    st.error(f"시뮬레이션 실패 [{e.stage}]: {e.message}")
                except Exception as e:
                    progress_bar.empty()
                    st.error(f"오류 발생: {e}")

    # ══════════════════════════════════════
    # STEP 3
    # ══════════════════════════════════════
    elif current_step == 3:
        sim = st.session_state["sim_result"]
        report = sim.report

        if st.button("↩️ 새 시나리오로 다시 테스트"):
            st.session_state.pop("sim_result", None)
            st.rerun()

        # 실험 요약
        st.subheader("실험 요약")
        summary = report.summary
        col_sum1, col_sum2 = st.columns([3, 1])
        with col_sum1:
            st.markdown(f"**결론:** {summary.one_line_conclusion}")
            st.markdown(f"**추천:** {summary.recommendation}")
        with col_sum2:
            if summary.is_significant:
                st.markdown('<span class="badge-significant">✅ 통계적 유의</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-not-significant">⚠️ 유의하지 않음</span>', unsafe_allow_html=True)

        st.divider()

        # 핵심 지표
        variant_ids = sorted(report.variant_metrics.keys())
        st.subheader("핵심 지표 비교")
        metrics_data = []
        for vid in variant_ids:
            vr = report.variant_metrics[vid]
            wcr = report.weighted_conversion_rates.get(vid, 0)
            label = "시나리오 A" if "a" in vid else "시나리오 B"
            metrics_data.append({"시나리오": label, "트윈 수": vr.total_twins, "전환 수": vr.conversions, "전환율 (%)": round(vr.conversion_rate * 100, 2), "가중 전환율 (%)": round(wcr * 100, 2), "평균 세션 (초)": round(vr.avg_session_duration, 1)})
        st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)

        # 상세 분석 탭
        tab_seg, tab_tag, tab_funnel, tab_stats, tab_best = st.tabs(["세그먼트 비교", "태그 분석", "퍼널 비교", "통계 검정", "최적 시나리오"])

        with tab_seg:
            if report.segment_heatmap:
                heatmap_data = []
                for sa in report.segment_heatmap:
                    for vid, vr in sa.variant_results.items():
                        heatmap_data.append({"세그먼트": sa.segment_label, "시나리오": "A" if "a" in vid else "B", "전환율 (%)": round(vr.conversion_rate * 100, 2)})
                fig = px.bar(pd.DataFrame(heatmap_data), x="세그먼트", y="전환율 (%)", color="시나리오", barmode="group", text="전환율 (%)", color_discrete_map={"A": "#3f51b5", "B": "#ff5722"})
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("세그먼트 분석 데이터가 없습니다.")

        with tab_tag:
            if report.tag_analyses:
                for tag_name, tag_groups in report.tag_analyses.items():
                    st.markdown(f"**{tag_name}**")
                    tag_data = []
                    for tg in tag_groups:
                        for vid, vr in tg.variant_results.items():
                            tag_data.append({"그룹": tg.group_value, "시나리오": "A" if "a" in vid else "B", "전환율 (%)": round(vr.conversion_rate * 100, 2)})
                    if tag_data:
                        fig = px.bar(pd.DataFrame(tag_data), x="그룹", y="전환율 (%)", color="시나리오", barmode="group", text="전환율 (%)", color_discrete_map={"A": "#3f51b5", "B": "#ff5722"})
                        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                        fig.update_layout(height=350)
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("분석 태그가 설정되지 않았습니다.")

        with tab_funnel:
            if report.funnel_comparison:
                all_pages = set()
                for vid, funnel in report.funnel_comparison.items():
                    all_pages.update(funnel.keys())
                funnel_order = ["/home", "/category/men", "/category/women", "/category/shoes", "/cart", "/checkout", "/order-complete"]
                ordered_pages = [p for p in funnel_order if p in all_pages]
                remaining = sorted(p for p in all_pages if p not in ordered_pages and not p.startswith("/product/"))
                ordered_pages.extend(remaining)
                if ordered_pages:
                    funnel_data = []
                    for vid in variant_ids:
                        funnel = report.funnel_comparison.get(vid, {})
                        label = "A" if "a" in vid else "B"
                        for page in ordered_pages:
                            drop_rate = funnel.get(page, 0)
                            funnel_data.append({"페이지": page, "시나리오": label, "도달률 (%)": round((1 - drop_rate) * 100, 1)})
                    fig = px.line(pd.DataFrame(funnel_data), x="페이지", y="도달률 (%)", color="시나리오", markers=True, color_discrete_map={"A": "#3f51b5", "B": "#ff5722"})
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("퍼널 데이터가 없습니다.")

        with tab_stats:
            chi_sq = report.overall_statistics
            if chi_sq:
                col_st1, col_st2, col_st3, col_st4 = st.columns(4)
                col_st1.metric("χ² 통계량", f"{chi_sq.chi2_statistic:.4f}")
                col_st2.metric("p-value", f"{chi_sq.p_value:.4f}")
                col_st3.metric("Cohen's h", f"{chi_sq.cohens_h:.4f}")
                col_st4.metric("유의성", "✅ 유의" if chi_sq.is_significant else "❌ 유의하지 않음")
                if chi_sq.confidence_intervals:
                    fig_ci = go.Figure()
                    for vid, (lower, upper) in chi_sq.confidence_intervals.items():
                        mid = (lower + upper) / 2
                        label = "A" if "a" in vid else "B"
                        color = "#3f51b5" if "a" in vid else "#ff5722"
                        fig_ci.add_trace(go.Scatter(x=[mid * 100], y=[label], error_x=dict(type="data", symmetric=False, array=[(upper - mid) * 100], arrayminus=[(mid - lower) * 100]), mode="markers", marker=dict(size=12, color=color), name=label))
                    fig_ci.update_layout(height=200, xaxis_title="전환율 (%)", title="95% 신뢰구간")
                    st.plotly_chart(fig_ci, use_container_width=True)
                h = chi_sq.cohens_h
                if h < 0.2:
                    st.markdown(f"🟡 Cohen's h = {h:.4f} → **작은 효과**")
                elif h < 0.5:
                    st.markdown(f"🟠 Cohen's h = {h:.4f} → **중간 효과**")
                else:
                    st.markdown(f"🔴 Cohen's h = {h:.4f} → **큰 효과**")
            else:
                st.info("통계 검정 결과가 없습니다.")

        with tab_best:
            if report.best_variants_by_segment:
                seg_label_map = {sa.segment_id: sa.segment_label for sa in report.segment_heatmap}
                best_data = []
                for seg_id, best_vid in report.best_variants_by_segment.items():
                    label = seg_label_map.get(seg_id, seg_id)
                    best_label = "시나리오 A" if "a" in best_vid else "시나리오 B"
                    sa_match = next((sa for sa in report.segment_heatmap if sa.segment_id == seg_id), None)
                    rates = {}
                    if sa_match:
                        for vid, vr in sa_match.variant_results.items():
                            k = "A 전환율 (%)" if "a" in vid else "B 전환율 (%)"
                            rates[k] = round(vr.conversion_rate * 100, 2)
                    best_data.append({"세그먼트": label, "최적 시나리오": best_label, **rates})
                st.dataframe(pd.DataFrame(best_data), use_container_width=True, hide_index=True)
            else:
                st.info("데이터가 없습니다.")

        st.caption("🧬 TwinPilot | 디지털 트윈 기반 사전 시뮬레이션 플랫폼")
