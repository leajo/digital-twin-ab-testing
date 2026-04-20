import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { pipelineSimulate } from "../api/client";

const SCENARIO_TYPES = [
  { value: "promotion", label: "프로모션 변경" },
  { value: "cta_change", label: "CTA 텍스트 변경" },
  { value: "price_display", label: "가격 표시 방식 변경" },
  { value: "funnel_change", label: "퍼널 단계 변경" },
  { value: "ui_position", label: "UI 요소 위치 변경" },
  { value: "timing", label: "노출 타이밍 변경" },
];

export default function SimulatePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const uploadId = (location.state as any)?.upload_id || "";

  const [name, setName] = useState("프로모션 A/B 테스트");
  const [type, setType] = useState("promotion");
  const [targetPage, setTargetPage] = useState("/home");
  const [variantA, setVariantA] = useState("오늘만 전제품 20% 할인");
  const [variantB, setVariantB] = useState("오늘만 무료배송 + 5% 적립금 제공");
  const [twinCount, setTwinCount] = useState(1000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadId) {
      setError("먼저 데이터를 업로드해 주세요.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const data = await pipelineSimulate({
        upload_id: uploadId,
        scenario_name: name,
        scenario_type: type,
        target_page: targetPage,
        variants: [
          { name: "control", description: variantA },
          { name: "treatment", description: variantB },
        ],
        twin_count: twinCount,
        primary_metric: "purchase_conversion_rate",
      });
      navigate(`/report/${data.simulation_id}`, {
        state: { report: data.report },
      });
    } catch (e: any) {
      setError(e?.response?.data?.detail?.message || e.message || "시뮬레이션 실패");
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="spinner-wrap">
        <div className="spinner" />
        <p style={{ marginTop: 16, color: "#666" }}>
          시뮬레이션 실행 중... 잠시만 기다려 주세요.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>⚙️ 시나리오 설정</h2>
      {!uploadId && (
        <p style={{ color: "#e65100", marginBottom: 12 }}>
          ⚠️ 업로드 ID가 없습니다. 먼저 데이터를 업로드해 주세요.
        </p>
      )}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>시나리오 이름</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>시나리오 유형</label>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {SCENARIO_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>대상 페이지</label>
          <input value={targetPage} onChange={(e) => setTargetPage(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Variant A (Control)</label>
          <textarea value={variantA} onChange={(e) => setVariantA(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Variant B (Treatment)</label>
          <textarea value={variantB} onChange={(e) => setVariantB(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>디지털 트윈 수</label>
          <input
            type="number"
            min={100}
            max={100000}
            value={twinCount}
            onChange={(e) => setTwinCount(Number(e.target.value))}
          />
        </div>
        {error && <p style={{ color: "red", marginBottom: 12 }}>{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={!uploadId}>
          🚀 시뮬레이션 실행
        </button>
      </form>
    </div>
  );
}
