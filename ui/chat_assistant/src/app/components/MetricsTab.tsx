import { useMetrics } from '../hooks/useMetrics';

const GREEN = '#3B6D11';
const GREEN_BG = '#EAF3DE';
const GREEN_BORDER = '#C0DD97';
const AMBER = '#854F0B';
const AMBER_BG = '#FAEEDA';
const AMBER_BORDER = '#FAC775';
const PRIMARY_BLUE = '#185FA5';
const BLUE_BG = '#E6F1FB';
const TEXT_PRIMARY = '#1A1A1A';
const TEXT_SECONDARY = '#555';
const TEXT_TERTIARY = '#888';

interface StatCardProps {
  label: string;
  value: string;
  color: string;
  live?: boolean;
}

function StatCard({ label, value, color, live }: StatCardProps) {
  return (
    <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
      <div className="flex items-center gap-1">
        <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
          {label}
        </p>
        {live && (
          <span className="rounded-full px-1 py-0 text-[8px] font-semibold uppercase tracking-wide"
            style={{ backgroundColor: GREEN_BG, color: GREEN }}>live</span>
        )}
      </div>
      <p className="mt-1 text-base font-medium" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

type RowStatus = 'warn' | 'pass' | 'none';

function statusColor(s: RowStatus) {
  if (s === 'pass') return GREEN;
  if (s === 'warn') return AMBER;
  return TEXT_TERTIARY;
}
function statusBg(s: RowStatus) {
  if (s === 'pass') return GREEN_BG;
  if (s === 'warn') return AMBER_BG;
  return 'transparent';
}
function statusBorder(s: RowStatus) {
  if (s === 'pass') return GREEN_BORDER;
  if (s === 'warn') return AMBER_BORDER;
  return 'transparent';
}

export default function MetricsTab() {
  const m = useMetrics();
  const isLive = !m.error && m.queryCount !== null;

  const tableRows = [
    {
      metric: 'Faithfulness',
      score: m.faithfulness.toFixed(4),
      threshold: m.evalThreshold.toString(),
      status: (m.faithfulness >= m.evalThreshold ? 'pass' : 'warn') as RowStatus,
      statusLabel: m.faithfulness >= m.evalThreshold ? '✓' : '⚠ Just below',
    },
    {
      metric: 'Answer Relevancy',
      score: m.answerRelevancy.toFixed(4),
      threshold: '—',
      status: 'none' as RowStatus,
      statusLabel: '—',
    },
    {
      metric: 'Context Precision',
      score: m.contextPrecision.toFixed(4),
      threshold: '—',
      status: 'pass' as RowStatus,
      statusLabel: '✓',
    },
    {
      metric: 'Context Recall',
      score: m.contextRecall.toFixed(4),
      threshold: '—',
      status: 'pass' as RowStatus,
      statusLabel: '✓',
    },
  ];

  return (
    <div className="space-y-6 p-5">
      {/* RAGAS Scores table */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
            RAGAS Scores
          </h2>
          {isLive && (
            <span className="text-[10px]" style={{ color: GREEN }}>
              ● live from /metrics
            </span>
          )}
          {m.error && (
            <span className="text-[10px]" style={{ color: AMBER }}>
              ⚠ Redis unavailable — showing last eval run
            </span>
          )}
        </div>
        <div className="overflow-hidden rounded-lg border" style={{ borderColor: '#E5E7EB' }}>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b" style={{ backgroundColor: '#F9FAFB', borderColor: '#E5E7EB' }}>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>Metric</th>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>Score</th>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>Threshold</th>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>Status</th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {tableRows.map((row) => (
                <tr key={row.metric} className="border-b last:border-0" style={{ borderColor: '#F3F4F6' }}>
                  <td className="px-4 py-2.5 font-medium" style={{ color: TEXT_PRIMARY }}>{row.metric}</td>
                  <td className="px-4 py-2.5 font-medium" style={{ color: PRIMARY_BLUE }}>{row.score}</td>
                  <td className="px-4 py-2.5" style={{ color: TEXT_SECONDARY }}>{row.threshold}</td>
                  <td className="px-4 py-2.5">
                    {row.status !== 'none' ? (
                      <span
                        className="inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium"
                        style={{
                          color: statusColor(row.status),
                          backgroundColor: statusBg(row.status),
                          borderColor: statusBorder(row.status),
                        }}
                      >
                        {row.statusLabel}
                      </span>
                    ) : (
                      <span style={{ color: TEXT_TERTIARY }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Faithfulness by difficulty */}
      <section>
        <h2 className="mb-3 text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
          Faithfulness by Difficulty
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Easy', value: '0.7500', sub: 'n=8', color: GREEN },
            { label: 'Medium', value: '0.7556', sub: 'n=15', color: GREEN },
            { label: 'Hard', value: '0.7353', sub: 'n=17', color: AMBER },
          ].map((item) => (
            <div key={item.label} className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
              <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
                {item.label}
              </p>
              <p className="mt-1 text-base font-medium" style={{ color: item.color }}>{item.value}</p>
              <p className="text-[10px]" style={{ color: TEXT_TERTIARY }}>{item.sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Latency breakdown */}
      <section>
        <h2 className="mb-3 text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
          Latency Breakdown
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="p50"
            value={`${m.p50ms}ms`}
            color={PRIMARY_BLUE}
            live={m.avgLatencyMs !== null}
          />
          <StatCard label="p95" value={`${m.p95ms.toLocaleString()}ms`} color={AMBER} />
        </div>
      </section>

      {/* Retrieval quality */}
      <section>
        <h2 className="mb-3 text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
          Retrieval Quality
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="Avg confidence"
            value={m.avgConfidence != null ? m.avgConfidence.toFixed(4) : '0.65'}
            color={GREEN}
            live={m.avgConfidence !== null}
          />
          <StatCard
            label="Low-conf queries"
            value={
              m.lowConfidenceCount != null && m.queryCount != null
                ? `${m.lowConfidenceCount} / ${m.queryCount} (${m.queryCount > 0 ? ((m.lowConfidenceCount / m.queryCount) * 100).toFixed(1) : 0}%)`
                : '9 / 40 (22.5%)'
            }
            color={AMBER}
            live={m.lowConfidenceCount !== null}
          />
        </div>
      </section>

      {/* Note card */}
      <div className="rounded-lg border p-3" style={{ backgroundColor: BLUE_BG, borderColor: '#B5D4F4' }}>
        <p className="text-[11px] leading-relaxed" style={{ color: PRIMARY_BLUE }}>
          RAGAS scores from the most recent eval run (eval_report.json). Live query stats stream from
          Redis via <code className="rounded px-1 py-0.5 font-mono text-[10px]" style={{ backgroundColor: '#cde4f6' }}>GET /metrics</code>.
          Re-run{' '}
          <code className="rounded px-1 py-0.5 font-mono text-[10px]" style={{ backgroundColor: '#cde4f6' }}>
            python src/evaluation/run_eval.py
          </code>{' '}
          to refresh scores.
        </p>
      </div>
    </div>
  );
}
