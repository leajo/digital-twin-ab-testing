import React, { useState, useCallback, DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { pipelineUpload } from "../api/client";

interface UploadSummary {
  upload_id: string;
  total_events: number;
  unique_users: number;
  profile_count: number;
  base_segment_count: number;
  excluded_user_count: number;
  date_range_start: string;
  date_range_end: string;
  base_segment_labels?: string[];
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [dragover, setDragover] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState<UploadSummary | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setError("");
    setLoading(true);
    try {
      const data = await pipelineUpload(file);
      setSummary(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail?.message || e.message || "업로드 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragover(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  if (loading) {
    return (
      <div className="spinner-wrap">
        <div className="spinner" />
        <p style={{ marginTop: 16, color: "#666" }}>
          데이터 분석 중... 프로파일링 및 세그먼트 생성이 자동으로 진행됩니다.
        </p>
      </div>
    );
  }

  if (summary) {
    return (
      <div className="card">
        <h2>✅ 업로드 완료</h2>
        <div className="summary-grid">
          <div className="summary-item">
            <div className="value">{summary.total_events.toLocaleString()}</div>
            <div className="label">총 이벤트</div>
          </div>
          <div className="summary-item">
            <div className="value">{summary.unique_users}</div>
            <div className="label">고유 사용자</div>
          </div>
          <div className="summary-item">
            <div className="value">{summary.profile_count}</div>
            <div className="label">유효 프로파일</div>
          </div>
          <div className="summary-item">
            <div className="value">{summary.base_segment_count}</div>
            <div className="label">기본 세그먼트</div>
          </div>
        </div>
        {summary.base_segment_labels && summary.base_segment_labels.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: "0.85rem", color: "#555", fontWeight: 600 }}>세그먼트: </span>
            {summary.base_segment_labels.map((label, i) => (
              <span key={i} className="badge badge-gray" style={{ marginRight: 6 }}>{label}</span>
            ))}
          </div>
        )}
        <p style={{ fontSize: "0.85rem", color: "#888", marginBottom: 16 }}>
          기간: {summary.date_range_start?.slice(0, 10)} ~ {summary.date_range_end?.slice(0, 10)}
          {summary.excluded_user_count > 0 &&
            ` · 데이터 부족으로 제외된 유저: ${summary.excluded_user_count}명`}
        </p>
        <button
          className="btn btn-primary"
          onClick={() =>
            navigate("/simulate", { state: { upload_id: summary.upload_id } })
          }
        >
          다음: 시나리오 설정 →
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>📂 고객 행동 데이터 업로드</h2>
      <p style={{ color: "#666", marginBottom: 16 }}>
        웹/모바일 서비스의 이벤트 로그 파일(CSV 또는 JSON)을 업로드하세요.
        업로드 후 자동으로 유저 프로파일링과 기본 세그먼트 생성이 진행됩니다.
      </p>
      <div
        className={`drop-zone${dragover ? " dragover" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <p style={{ fontSize: "2rem" }}>📁</p>
        <p>CSV 또는 JSON 파일을 드래그하거나 클릭하여 업로드</p>
        <p style={{ fontSize: "0.8rem", color: "#aaa", marginTop: 8 }}>
          필수 필드: user_id, session_id, event_type, timestamp · 최대 100MB
        </p>
        <input
          id="file-input"
          type="file"
          accept=".csv,.json"
          style={{ display: "none" }}
          onChange={onFileInput}
        />
      </div>
      {error && <p style={{ color: "red", marginTop: 12 }}>{error}</p>}
    </div>
  );
}
