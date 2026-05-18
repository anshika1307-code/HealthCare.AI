import { RAGAS_METRICS, SYSTEM_STATS } from '../config';

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
}

function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
      <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
        {label}
      </p>
      <p className="mt-1 text-base font-medium" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

type RowStatus = 'warn' | 'pass' | 'none';

interface TableRow {
  metric: string;
  score: string;
  threshold: string;
  status: RowStatus;
  statusLabel: string;
}

const TABLE_ROWS: TableRow[] = [
  {
    metric: 'Faithfulness',
    score: RAGAS_METRICS.faithfulness.toString(),
    threshold: RAGAS_METRICS.threshold.toString(),
    status: 'warn',
    statusLabel: '⚠ Just below',
  },
  {
    metric: 'Answer Relevancy',
    score: RAGAS_METRICS.answerRelevancy.toString(),
    threshold: '—',
    status: 'none',
    statusLabel: '—',
  },
  {
    metric: 'Context Precision',
    score: RAGAS_METRICS.contextPrecision.toString(),
    threshold: '—',
    status: 'pass',
    statusLabel: '✓',
  },
  {
    metric: 'Context Recall',
    score: RAGAS_METRICS.contextRecall.toString(),
    threshold: '—',
    status: 'pass',
    statusLabel: '✓',
  },
];

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
  return (
    <div className="space-y-6 p-5">
      {/* RAGAS Scores table */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          RAGAS Scores
        </h2>
        <div className="overflow-hidden rounded-lg border" style={{ borderColor: '#E5E7EB' }}>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b" style={{ backgroundColor: '#F9FAFB', borderColor: '#E5E7EB' }}>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>
                  Metric
                </th>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>
                  Score
                </th>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>
                  Threshold
                </th>
                <th className="px-4 py-2.5 text-left font-medium" style={{ color: TEXT_TERTIARY }}>
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {TABLE_ROWS.map((row, idx) => (
                <tr
                  key={row.metric}
                  className="border-b last:border-0"
                  style={{ borderColor: '#F3F4F6' }}
                >
                  <td className="px-4 py-2.5 font-medium" style={{ color: TEXT_PRIMARY }}>
                    {row.metric}
                  </td>
                  <td className="px-4 py-2.5 font-medium" style={{ color: PRIMARY_BLUE }}>
                    {row.score}
                  </td>
                  <td className="px-4 py-2.5" style={{ color: TEXT_SECONDARY }}>
                    {row.threshold}
                  </td>
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
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          Faithfulness by Difficulty
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Easy', value: '0.7500', sub: 'n=8', color: GREEN },
            { label: 'Medium', value: '0.7556', sub: 'n=15', color: GREEN },
            { label: 'Hard', value: '0.7353', sub: 'n=17', color: AMBER },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-lg border bg-white p-3"
              style={{ borderColor: '#E5E7EB' }}
            >
              <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
                {item.label}
              </p>
              <p className="mt-1 text-base font-medium" style={{ color: item.color }}>
                {item.value}
              </p>
              <p className="text-[10px]" style={{ color: TEXT_TERTIARY }}>
                {item.sub}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Latency breakdown */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          Latency Breakdown
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="p50" value={`${SYSTEM_STATS.p50ms}ms`} color={PRIMARY_BLUE} />
          <StatCard label="p95" value={`${SYSTEM_STATS.p95ms.toLocaleString()}ms`} color={AMBER} />
        </div>
      </section>

      {/* Retrieval quality */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          Retrieval Quality
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Avg confidence" value="0.65" color={GREEN} />
          <StatCard label="Low-conf queries" value="9 / 40 (22.5%)" color={AMBER} />
        </div>
      </section>

      {/* Note card */}
      <div
        className="rounded-lg border p-3"
        style={{ backgroundColor: BLUE_BG, borderColor: '#B5D4F4' }}
      >
        <p className="text-[11px] leading-relaxed" style={{ color: PRIMARY_BLUE }}>
          These scores are from the most recent eval run (eval_report.json). Re-run{' '}
          <code className="rounded px-1 py-0.5 font-mono text-[10px]" style={{ backgroundColor: '#cde4f6' }}>
            python src/evaluation/run_eval.py
          </code>{' '}
          to refresh.
        </p>
      </div>
    </div>
  );
}
