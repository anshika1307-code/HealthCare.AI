import { useState } from 'react';
import { FileText, Github, FlaskConical, ExternalLink, CheckCircle2 } from 'lucide-react';
import { GITHUB_URL } from '../config';
import { useMetrics } from '../hooks/useMetrics';
import EvalReportModal from './EvalReportModal';

const GREEN = '#3B6D11';
const AMBER = '#854F0B';
const AMBER_BG = '#FAEEDA';
const AMBER_BORDER = '#FAC775';
const PRIMARY_BLUE = '#185FA5';
const TEXT_PRIMARY = '#1A1A1A';
const TEXT_SECONDARY = '#555';
const TEXT_TERTIARY = '#888';

interface MetricCellProps {
  label: string;
  value: string;
  color: string;
  live?: boolean;
}

function MetricCell({ label, value, color, live }: MetricCellProps) {
  return (
    <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
      <div className="flex items-center gap-1">
        <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
          {label}
        </p>
        {live && (
          <span className="rounded-full px-1 py-0 text-[8px] font-semibold uppercase tracking-wide"
            style={{ backgroundColor: '#EAF3DE', color: GREEN }}>live</span>
        )}
      </div>
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
    title: 'Groq Llama-3.3-70B primary + OpenAI gpt-4o-mini fallback',
    detail:
      'Groq cuts LLM latency from ~9s to ~300ms at zero cost. OpenAI fallback activates on Groq rate-limit. Embeddings remain on text-embedding-3-small.',
  },
];

export default function EngineeringTab() {
  const m = useMetrics();
  const [evalOpen, setEvalOpen] = useState(false);

  return (
    <div className="space-y-6 p-5">
      {/* System Health */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[10px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
            System Health
          </h2>
          {m.queryCount !== null && (
            <span className="text-[10px]" style={{ color: TEXT_TERTIARY }}>
              {m.queryCount} total queries · {m.errorCount ?? 0} errors
            </span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-3">
          <MetricCell
            label="Avg faithfulness"
            value={m.faithfulness.toFixed(4)}
            color={m.faithfulness >= m.evalThreshold ? GREEN : AMBER}
            live={!m.error && m.queryCount !== null}
          />
          <MetricCell
            label="Answer relevancy"
            value={m.answerRelevancy.toFixed(4)}
            color={AMBER}
            live={!m.error && m.queryCount !== null}
          />
          <MetricCell
            label="Context precision"
            value={m.contextPrecision.toFixed(4)}
            color={GREEN}
            live={!m.error && m.queryCount !== null}
          />
          <MetricCell
            label="Context recall"
            value={m.contextRecall.toFixed(4)}
            color={GREEN}
            live={!m.error && m.queryCount !== null}
          />
          <MetricCell
            label="p50 latency"
            value={`${m.p50ms}ms`}
            color={PRIMARY_BLUE}
            live={!m.error && m.avgLatencyMs !== null}
          />
          <MetricCell
            label="Eval passing"
            value={`${m.evalPassing}/${m.evalTotal}`}
            color={GREEN}
          />
        </div>
        {m.avgConfidence !== null && (
          <p className="mt-2 text-[10px]" style={{ color: TEXT_TERTIARY }}>
            Live avg confidence: <span className="font-medium" style={{ color: PRIMARY_BLUE }}>
              {m.avgConfidence.toFixed(4)}
            </span>
            {m.lowConfidenceCount !== null && ` · ${m.lowConfidenceCount} low-confidence queries`}
          </p>
        )}
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
            href={GITHUB_URL + '/blob/main/docs/basic_architecture.md'}
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
          <button
            onClick={() => setEvalOpen(true)}
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            <FlaskConical className="h-3.5 w-3.5" />
            Eval Report
          </button>
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

      <EvalReportModal open={evalOpen} onOpenChange={setEvalOpen} />

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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" style={{ color: GREEN }} />
              <span className="text-xs" style={{ color: TEXT_PRIMARY }}>
                GitHub Actions · eval gate · faithfulness {m.faithfulness.toFixed(4)} vs threshold{' '}
                {m.evalThreshold}
              </span>
            </div>
            <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
              Last run: today
            </span>
          </div>

          {m.faithfulness < m.evalThreshold && (
            <div
              className="mt-2.5 rounded border p-2"
              style={{ backgroundColor: AMBER_BG, borderColor: AMBER_BORDER }}
            >
              <p className="text-[11px] leading-relaxed" style={{ color: AMBER }}>
                ⚠ Just below {m.evalThreshold} threshold — running eval with latest prompt changes
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
