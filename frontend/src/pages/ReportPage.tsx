import { useEffect, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import { getSimulationReport } from "../api/client";

/* ---------- Types ---------- */
interface VariantResult {
  variant_id: string;
  total_twins: number;
  conversions: number;
  conversion_rate: number;
  avg_session_duration: number;
  funnel_drop_rates: Record<string, number>;
}
interface ChiSquareResult {
  chi2_statistic: number;
  p_value: number;
  degrees_of_freedom: number;
  is_significant: boolean;
  confidence_intervals: Record<string, number[]>;
  cohens_h: number;
}
interface SegmentAnalysis {
  segment_id: string;
  segment_label: string;
  segment_proportion: number;
  variant_results: Record<string, VariantResult>;
  chi_square: ChiSquareResult | null;
  best_variant: string;
}
interface TagGroup {
  tag_name: string;
  group_value: string;
  group_twin_count: number;
  group_proportion: number;
  variant_results: Record<string, VariantResult>;
  best_variant: string;
}
interface ReportSummary {
  one_line_conclusion: string;
  recommendation: string;
  winning_variant: string | null;
  is_significant: boolean;
}
interface Report {
  summary: ReportSummary;
  variant_metrics: Record<string, VariantResult>;
  weighted_conversion_rates: Record<string, number>;
  segment_heatmap: SegmentAnalysis[];
  tag_analyses: Record<string, TagGroup[]> | null;
  funnel_comparison: Record<string, Record<string, number>>;
  overall_statistics: ChiSquareResult | null;
  segment_statistics: ChiSquareResult[];
  best_variants_by_segment: Record<string, string>;
}

const COLORS = ["#3f51b5", "#ff9800", "#4caf50", "#e91e63", "#00bcd4"];
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const passedReport = (location.state as any)?.report as Report | undefined;

  const [report, setReport] = useState<Report | null>(passedReport ?? null);
  const [loading, setLoading] = useState(!passedReport);
  const [error, setError] = useState("");

  useEffect(() => {
    if (passedReport || !id) return;
    setLoading(true);
    getSimulationReport(id)
      .then((d) => setReport(d))
      .catch((e) => setError(e?.response?.data?.message || "리포트 로드 실패"))
      .finally(() => setLoading(false));
  }, [id, passedReport]);

  if (loading) {
    return (
      <div className="spinner-wrap">
        <div className="spinner" />
        <p style={{ marginTop: 16, color: "#666" }}>리포트 로딩 중...</p>
      </div>
    );
  }
  if (error) return <div className="card"><p style={{ color: "red" }}>{error}</p></div>;
  if (!report) return <div className="card"><p>리포트 데이터가 없습니다.</p></div>;

  const variantIds = Object.keys(report.variant_metrics);

  return (
    <div>
      {/* Section 1: Summary */}
      <SummaryCard summary={report.summary} />

      {/* Section 2: Variant Metrics Table */}
      <MetricsTable
        metrics={report.variant_metrics}
        weighted={report.weighted_conversion_rates}
      />

      {/* Section 3: Segment Heatmap */}
      <SegmentHeatmap
        segments={report.segment_heatmap}
        variantIds={variantIds}
      />

      {/* Section 4: Tag Analysis */}
      {report.tag_analyses && (
        <TagAnalysis tagAnalyses={report.tag_analyses} variantIds={variantIds} />
      )}

      {/* Section 5: Funnel Comparison */}
      <FunnelComparison funnel={report.funnel_comparison} variantIds={variantIds} />

      {/* Section 6: Statistics */}
      {report.overall_statistics && (
        <StatisticsCard stats={report.overall_statistics} />
      )}

      {/* Section 7: Best Variant per Segment */}
      <BestVariantTable
        best={report.best_variants_by_segment}
        segments={report.segment_heatmap}
      />
    </div>
  );
}


/* ========== Section 1: Summary Card ========== */
function SummaryCard({ summary }: { summary: ReportSummary }) {
  return (
    <div className="card">
      <h2>📊 실험 요약</h2>
      <p style={{ fontSize: "1.1rem", fontWeight: 600, margin: "8px 0" }}>
        {summary.one_line_conclusion}
      </p>
      <p style={{ color: "#555" }}>{summary.recommendation}</p>
      <div className="flex-gap" style={{ marginTop: 12 }}>
        {summary.winning_variant && (
          <span className="badge badge-green">
            승자: {summary.winning_variant}
          </span>
        )}
        <span className={`badge ${summary.is_significant ? "badge-green" : "badge-gray"}`}>
          {summary.is_significant ? "통계적으로 유의함" : "유의하지 않음"}
        </span>
      </div>
    </div>
  );
}

/* ========== Section 2: Metrics Table ========== */
function MetricsTable({
  metrics,
  weighted,
}: {
  metrics: Record<string, VariantResult>;
  weighted: Record<string, number>;
}) {
  return (
    <div className="card">
      <h2>📈 핵심 지표 비교</h2>
      <table>
        <thead>
          <tr>
            <th>Variant</th>
            <th>트윈 수</th>
            <th>전환</th>
            <th>전환율</th>
            <th>가중 전환율</th>
            <th>평균 세션(초)</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(metrics).map(([vid, vr]) => (
            <tr key={vid}>
              <td style={{ fontWeight: 600 }}>{vid}</td>
              <td>{vr.total_twins}</td>
              <td>{vr.conversions}</td>
              <td>{pct(vr.conversion_rate)}</td>
              <td>{weighted[vid] !== undefined ? pct(weighted[vid]) : "-"}</td>
              <td>{vr.avg_session_duration.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ fontSize: "0.8rem", color: "#999", marginTop: 8 }}>
        가중 전환율 = Σ(세그먼트 비율 × 세그먼트별 전환율)
      </p>
    </div>
  );
}

/* ========== Section 3: Segment Heatmap ========== */
function SegmentHeatmap({
  segments,
  variantIds,
}: {
  segments: SegmentAnalysis[];
  variantIds: string[];
}) {
  const data = segments.map((seg) => {
    const row: any = {
      name: `${seg.segment_label} (${pct(seg.segment_proportion)})`,
    };
    variantIds.forEach((vid) => {
      row[vid] = seg.variant_results[vid]?.conversion_rate ?? 0;
    });
    return row;
  });

  return (
    <div className="card">
      <h2>🗺️ 세그먼트별 전환율 비교</h2>
      <ResponsiveContainer width="100%" height={Math.max(250, segments.length * 60)}>
        <BarChart data={data} layout="vertical" margin={{ left: 140 }}>
          <XAxis type="number" tickFormatter={(v: number) => pct(v)} domain={[0, "auto"]} />
          <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v: number) => pct(v)} />
          <Legend />
          {variantIds.map((vid, i) => (
            <Bar key={vid} dataKey={vid} fill={COLORS[i % COLORS.length]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ========== Section 4: Tag Analysis ========== */
function TagAnalysis({
  tagAnalyses,
  variantIds,
}: {
  tagAnalyses: Record<string, TagGroup[]>;
  variantIds: string[];
}) {
  return (
    <>
      {Object.entries(tagAnalyses).map(([tag, groups]) => {
        const data = groups.map((g) => {
          const row: any = { name: `${g.group_value} (${pct(g.group_proportion)})` };
          variantIds.forEach((vid) => {
            row[vid] = g.variant_results[vid]?.conversion_rate ?? 0;
          });
          return row;
        });
        return (
          <div className="card" key={tag}>
            <h2>🏷️ 분석 태그: {tag}</h2>
            <ResponsiveContainer width="100%" height={Math.max(200, groups.length * 55)}>
              <BarChart data={data} layout="vertical" margin={{ left: 120 }}>
                <XAxis type="number" tickFormatter={(v: number) => pct(v)} domain={[0, "auto"]} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v: number) => pct(v)} />
                <Legend />
                {variantIds.map((vid, i) => (
                  <Bar key={vid} dataKey={vid} fill={COLORS[i % COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </>
  );
}

/* ========== Section 5: Funnel Comparison ========== */
function FunnelComparison({
  funnel,
  variantIds,
}: {
  funnel: Record<string, Record<string, number>>;
  variantIds: string[];
}) {
  /* Collect all stages */
  const stageSet = new Set<string>();
  Object.values(funnel).forEach((stages) =>
    Object.keys(stages).forEach((s) => stageSet.add(s))
  );
  const stages = Array.from(stageSet);
  if (stages.length === 0) return null;

  const data = stages.map((stage) => {
    const row: any = { name: stage };
    variantIds.forEach((vid) => {
      row[vid] = funnel[vid]?.[stage] ?? 0;
    });
    return row;
  });

  return (
    <div className="card">
      <h2>🔻 퍼널 단계별 이탈률 비교</h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ left: 20 }}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v: number) => pct(v)} />
          <Tooltip formatter={(v: number) => pct(v)} />
          <Legend />
          {variantIds.map((vid, i) => (
            <Bar key={vid} dataKey={vid} fill={COLORS[i % COLORS.length]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ========== Section 6: Statistics Card ========== */
function StatisticsCard({ stats }: { stats: ChiSquareResult }) {
  return (
    <div className="card">
      <h2>📐 통계 검정 결과</h2>
      <div className="summary-grid">
        <div className="summary-item">
          <div className="value">{stats.p_value.toFixed(4)}</div>
          <div className="label">p-value</div>
        </div>
        <div className="summary-item">
          <div className="value">{stats.chi2_statistic.toFixed(2)}</div>
          <div className="label">χ² 통계량</div>
        </div>
        <div className="summary-item">
          <div className="value">{stats.cohens_h.toFixed(3)}</div>
          <div className="label">Cohen's h</div>
        </div>
        <div className="summary-item">
          <div className="value">
            <span className={`badge ${stats.is_significant ? "badge-green" : "badge-red"}`}>
              {stats.is_significant ? "유의함" : "유의하지 않음"}
            </span>
          </div>
          <div className="label">유의성 (α=0.05)</div>
        </div>
      </div>
      {Object.keys(stats.confidence_intervals).length > 0 && (
        <>
          <h3 style={{ marginTop: 16 }}>95% 신뢰구간</h3>
          <table>
            <thead>
              <tr><th>Variant</th><th>하한</th><th>상한</th></tr>
            </thead>
            <tbody>
              {Object.entries(stats.confidence_intervals).map(([vid, ci]) => (
                <tr key={vid}>
                  <td>{vid}</td>
                  <td>{pct(ci[0])}</td>
                  <td>{pct(ci[1])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

/* ========== Section 7: Best Variant per Segment ========== */
function BestVariantTable({
  best,
  segments,
}: {
  best: Record<string, string>;
  segments: SegmentAnalysis[];
}) {
  const labelMap: Record<string, string> = {};
  segments.forEach((s) => { labelMap[s.segment_id] = s.segment_label; });

  return (
    <div className="card">
      <h2>🏆 세그먼트별 최적 Variant</h2>
      <table>
        <thead>
          <tr><th>세그먼트</th><th>최적 Variant</th></tr>
        </thead>
        <tbody>
          {Object.entries(best).map(([segId, vid]) => (
            <tr key={segId}>
              <td>{labelMap[segId] || segId}</td>
              <td><span className="badge badge-green">{vid}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
