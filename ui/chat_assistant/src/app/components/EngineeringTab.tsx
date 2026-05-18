import { FileText, Github, FlaskConical, ExternalLink, CheckCircle2 } from 'lucide-react';
import { GITHUB_URL, RAGAS_METRICS, SYSTEM_STATS } from '../config';

const GREEN = '#3B6D11';
const GREEN_BG = '#EAF3DE';
const GREEN_BORDER = '#C0DD97';
const AMBER = '#854F0B';
const AMBER_BG = '#FAEEDA';
const AMBER_BORDER = '#FAC775';
const PRIMARY_BLUE = '#185FA5';
const BLUE_BG = '#E6F1FB';
const BLUE_BORDER = '#B5D4F4';
const TEXT_PRIMARY = '#1A1A1A';
const TEXT_SECONDARY = '#555';
const TEXT_TERTIARY = '#888';

interface MetricCellProps {
  label: string;
  value: string;
  color: string;
}

function MetricCell({ label, value, color }: MetricCellProps) {
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

const KEY_DECISIONS = [
  {
    num: 1,
    title: 'Hybrid retrieval — BM25 + dense, RRF k=30',
    detail:
      'Clinical acronyms (eGFR, SGLT2i, ACE, ARB) score poorly in dense-only search. BM25 catches exact matches; RRF fuses both lists.',
  },
  {
    num: 2,
    title: '512-token chunks with boundary-aware splitting',
    detail:
      'Boundary-aware chunking respects paragraph and section structure to avoid splitting clinical thresholds mid-sentence.',
  },
  {
    num: 3,
    title: 'Confidence gate at 0.40 — warn alongside answer',
    detail:
      'Healthcare context: suppressing an answer is worse than flagging uncertainty. Low confidence appends a disclaimer but still returns the answer.',
  },
  {
    num: 4,
    title: 'gpt-4o-mini with extractive system prompt',
    detail:
      'Strict context-only prompt prevents training-data hallucination. Improved faithfulness from 0.62 to 0.74 vs. generative prompt.',
  },
];

export default function EngineeringTab() {
  return (
    <div className="space-y-6 p-5">
      {/* System Health */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          System Health
        </h2>
        <div className="grid grid-cols-3 gap-3">
          <MetricCell
            label="Avg faithfulness"
            value={RAGAS_METRICS.faithfulness.toString()}
            color={GREEN}
          />
          <MetricCell
            label="Answer relevancy"
            value={RAGAS_METRICS.answerRelevancy.toString()}
            color={AMBER}
          />
          <MetricCell
            label="Context precision"
            value={RAGAS_METRICS.contextPrecision.toString()}
            color={GREEN}
          />
          <MetricCell
            label="Context recall"
            value={RAGAS_METRICS.contextRecall.toString()}
            color={GREEN}
          />
          <MetricCell
            label="p50 latency"
            value={`${SYSTEM_STATS.p50ms}ms`}
            color={PRIMARY_BLUE}
          />
          <MetricCell
            label="Eval passing"
            value={`${SYSTEM_STATS.evalPassing}/${SYSTEM_STATS.evalTotal}`}
            color={GREEN}
          />
        </div>
      </section>

      {/* Architecture & Docs */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          Architecture &amp; Docs
        </h2>
        <div className="flex flex-wrap gap-2">
          <a
            href={GITHUB_URL + '/blob/main/docs/decision.md'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            <FileText className="h-3.5 w-3.5" />
            DECISIONS.md
          </a>
          <a
            href={GITHUB_URL + '/blob/main/docs/ARCHITECTURE.md'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            ARCHITECTURE.md
          </a>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            <Github className="h-3.5 w-3.5" />
            GitHub
          </a>
          <a
            href="/eval_report.json"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            <FlaskConical className="h-3.5 w-3.5" />
            Eval Report
          </a>
          <a
            href={GITHUB_URL + '/actions'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            CI Pipeline
          </a>
        </div>
      </section>

      {/* Key Decisions */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          Key Decisions
        </h2>
        <div className="space-y-2.5">
          {KEY_DECISIONS.map((d) => (
            <div
              key={d.num}
              className="rounded-lg border bg-white p-3"
              style={{ borderColor: '#E5E7EB' }}
            >
              <div className="flex items-start gap-2.5">
                <span
                  className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                  style={{ backgroundColor: PRIMARY_BLUE }}
                >
                  {d.num}
                </span>
                <div>
                  <p className="text-xs font-medium" style={{ color: TEXT_PRIMARY }}>
                    {d.title}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>
                    {d.detail}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CI/CD Status */}
      <section>
        <h2
          className="mb-3 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: TEXT_TERTIARY }}
        >
          CI / CD Status
        </h2>
        <div
          className="rounded-lg border bg-white p-3"
          style={{ borderColor: '#E5E7EB' }}
        >
          {/* Main status row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" style={{ color: GREEN }} />
              <span className="text-xs" style={{ color: TEXT_PRIMARY }}>
                GitHub Actions · eval gate · faithfulness {RAGAS_METRICS.faithfulness} vs threshold{' '}
                {RAGAS_METRICS.threshold}
              </span>
            </div>
            <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
              Last run: today
            </span>
          </div>

          {/* Warning note */}
          <div
            className="mt-2.5 rounded border p-2"
            style={{ backgroundColor: AMBER_BG, borderColor: AMBER_BORDER }}
          >
            <p className="text-[11px] leading-relaxed" style={{ color: AMBER }}>
              ⚠ Just below 0.75 threshold — running eval with latest prompt changes
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
