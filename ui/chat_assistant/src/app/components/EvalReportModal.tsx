import { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, ChevronDown, ChevronUp } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const GREEN = '#3B6D11';
const GREEN_BG = '#EAF3DE';
const GREEN_BORDER = '#C0DD97';
const AMBER = '#854F0B';
const AMBER_BG = '#FAEEDA';
const AMBER_BORDER = '#FAC775';
const RED = '#991B1B';
const RED_BG = '#FEF2F2';
const RED_BORDER = '#FECACA';
const PRIMARY_BLUE = '#185FA5';
const BLUE_BG = '#E6F1FB';
const TEXT_PRIMARY = '#1A1A1A';
const TEXT_SECONDARY = '#555';
const TEXT_TERTIARY = '#888';

const FAITHFULNESS_THRESHOLD = 0.70;

interface EvalQuestion {
  id: string;
  question: string;
  ground_truth: string;
  section: string;
  difficulty: 'easy' | 'medium' | 'hard';
  source_doc: string;
  answer: string;
  confidence_score: number;
  low_confidence: boolean;
  sources: string[];
  latency_ms: number;
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
}

interface EvalReport {
  metadata: {
    timestamp: string;
    eval_set: string;
    num_questions: number;
    errors: number;
    ragas_version: string;
    pipeline_time_s: number;
  };
  thresholds: { faithfulness: number };
  averages: {
    faithfulness: number;
    answer_relevancy: number;
    context_precision: number;
    context_recall: number;
  };
  per_question: EvalQuestion[];
}

function scoreColor(score: number, threshold = 0): string {
  if (score === 0) return TEXT_TERTIARY;
  if (threshold > 0) {
    if (score >= threshold) return GREEN;
    if (score >= threshold * 0.9) return AMBER;
    return RED;
  }
  if (score >= 0.70) return GREEN;
  if (score >= 0.5) return AMBER;
  return RED;
}

function difficultyStyle(d: string): { bg: string; text: string; border: string } {
  if (d === 'easy') return { bg: GREEN_BG, text: GREEN, border: GREEN_BORDER };
  if (d === 'hard') return { bg: RED_BG, text: RED, border: RED_BORDER };
  return { bg: AMBER_BG, text: AMBER, border: AMBER_BORDER };
}

function sourceLabel(doc: string): string {
  if (doc.includes('fda') || doc.includes('metformin')) return 'FDA';
  if (doc.includes('ada')) return doc.includes('section6') || doc.includes('_6') ? 'ADA §6' : 'ADA §9';
  if (doc.includes('jnc')) return 'JNC 8';
  return doc.slice(0, 6).toUpperCase();
}

function ScorePill({ value }: { value: number }) {
  const color = scoreColor(value);
  return (
    <span className="tabular-nums font-medium text-[11px]" style={{ color }}>
      {value === 0 ? '—' : value.toFixed(3)}
    </span>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
      <p className="text-[9px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>{label}</p>
      <p className="mt-1 text-sm font-semibold" style={{ color }}>{value}</p>
    </div>
  );
}

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export default function EvalReportModal({ open, onOpenChange }: Props) {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diffFilter, setDiffFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    if (!open || report) return;
    setLoading(true);
    setError(null);
    fetch(`${API_URL}/eval-report`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d) => { setReport(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [open, report]);

  const questions = report?.per_question ?? [];

  const sources = [...new Set(questions.map((q) => sourceLabel(q.source_doc)))].sort();

  const filtered = questions.filter((q) => {
    if (diffFilter !== 'all' && q.difficulty !== diffFilter) return false;
    if (sourceFilter !== 'all' && sourceLabel(q.source_doc) !== sourceFilter) return false;
    return true;
  });

  const threshold = report?.thresholds.faithfulness ?? FAITHFULNESS_THRESHOLD;
  const passing = questions.filter((q) => q.faithfulness >= threshold).length;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" style={{ backdropFilter: 'blur(2px)' }} />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-full max-w-4xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl border bg-white shadow-lg"
          style={{ borderColor: '#E5E7EB' }}
        >
          {/* Header */}
          <div className="flex flex-shrink-0 items-center justify-between border-b px-5 py-3.5" style={{ borderColor: '#E5E7EB' }}>
            <div>
              <Dialog.Title className="text-sm font-semibold text-gray-900">RAGAS Evaluation Report</Dialog.Title>
              {report && (
                <p className="text-[10px]" style={{ color: TEXT_TERTIARY }}>
                  {new Date(report.metadata.timestamp).toLocaleString()} ·{' '}
                  {report.metadata.num_questions} questions · RAGAS {report.metadata.ragas_version} ·{' '}
                  {(report.metadata.pipeline_time_s / 60).toFixed(0)} min runtime
                </p>
              )}
            </div>
            <Dialog.Close asChild>
              <button className="rounded p-1 transition-colors hover:bg-gray-100" aria-label="Close">
                <X className="h-4 w-4 text-gray-400" />
              </button>
            </Dialog.Close>
          </div>

          {/* Scrollable body */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {loading && (
              <div className="flex items-center justify-center py-16 text-sm text-gray-400">
                Loading report…
              </div>
            )}
            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                Failed to load eval report: {error}
              </div>
            )}
            {report && (
              <>
                {/* Averages */}
                <div className="mb-5 grid grid-cols-5 gap-2">
                  <SummaryCard
                    label="Faithfulness"
                    value={report.averages.faithfulness.toFixed(4)}
                    color={report.averages.faithfulness >= threshold ? GREEN : AMBER}
                  />
                  <SummaryCard
                    label="Answer Relevancy"
                    value={report.averages.answer_relevancy.toFixed(4)}
                    color={scoreColor(report.averages.answer_relevancy)}
                  />
                  <SummaryCard
                    label="Context Precision"
                    value={report.averages.context_precision.toFixed(4)}
                    color={scoreColor(report.averages.context_precision)}
                  />
                  <SummaryCard
                    label="Context Recall"
                    value={report.averages.context_recall.toFixed(4)}
                    color={scoreColor(report.averages.context_recall)}
                  />
                  <SummaryCard
                    label={`Passing (≥${threshold})`}
                    value={`${passing} / ${questions.length}`}
                    color={passing / questions.length >= 0.7 ? GREEN : AMBER}
                  />
                </div>

                {/* Filters */}
                <div className="mb-3 flex items-center gap-3">
                  <span className="text-[10px] font-medium" style={{ color: TEXT_TERTIARY }}>Filter:</span>
                  <div className="flex gap-1.5">
                    {['all', 'easy', 'medium', 'hard'].map((d) => (
                      <button
                        key={d}
                        onClick={() => setDiffFilter(d)}
                        className="rounded-full border px-2.5 py-0.5 text-[10px] font-medium transition-colors"
                        style={diffFilter === d
                          ? { backgroundColor: PRIMARY_BLUE, borderColor: PRIMARY_BLUE, color: 'white' }
                          : { borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
                      >
                        {d === 'all' ? 'All difficulty' : d}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-1.5">
                    {['all', ...sources].map((s) => (
                      <button
                        key={s}
                        onClick={() => setSourceFilter(s)}
                        className="rounded-full border px-2.5 py-0.5 text-[10px] font-medium transition-colors"
                        style={sourceFilter === s
                          ? { backgroundColor: PRIMARY_BLUE, borderColor: PRIMARY_BLUE, color: 'white' }
                          : { borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
                      >
                        {s === 'all' ? 'All sources' : s}
                      </button>
                    ))}
                  </div>
                  <span className="ml-auto text-[10px]" style={{ color: TEXT_TERTIARY }}>
                    {filtered.length} of {questions.length}
                  </span>
                </div>

                {/* Table */}
                <div className="overflow-hidden rounded-lg border" style={{ borderColor: '#E5E7EB' }}>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b" style={{ backgroundColor: '#F9FAFB', borderColor: '#E5E7EB' }}>
                        <th className="px-3 py-2 text-left font-medium w-16" style={{ color: TEXT_TERTIARY }}>ID</th>
                        <th className="px-3 py-2 text-left font-medium" style={{ color: TEXT_TERTIARY }}>Question</th>
                        <th className="px-3 py-2 text-left font-medium w-16" style={{ color: TEXT_TERTIARY }}>Diff.</th>
                        <th className="px-3 py-2 text-right font-medium w-20" style={{ color: TEXT_TERTIARY }}>Faith.</th>
                        <th className="px-3 py-2 text-right font-medium w-20" style={{ color: TEXT_TERTIARY }}>Rel.</th>
                        <th className="px-3 py-2 text-right font-medium w-20" style={{ color: TEXT_TERTIARY }}>Prec.</th>
                        <th className="px-3 py-2 text-right font-medium w-20" style={{ color: TEXT_TERTIARY }}>Recall</th>
                        <th className="px-3 py-2 text-right font-medium w-20" style={{ color: TEXT_TERTIARY }}>Conf.</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {filtered.map((q) => {
                        const diff = difficultyStyle(q.difficulty);
                        const isExpanded = expandedId === q.id;
                        return (
                          <>
                            <tr
                              key={q.id}
                              className="cursor-pointer hover:bg-gray-50"
                              onClick={() => setExpandedId(isExpanded ? null : q.id)}
                            >
                              <td className="px-3 py-2 font-mono text-[10px]" style={{ color: TEXT_TERTIARY }}>{q.id}</td>
                              <td className="px-3 py-2 font-medium" style={{ color: TEXT_PRIMARY }}>
                                <div className="flex items-center gap-2">
                                  {isExpanded
                                    ? <ChevronUp className="h-3 w-3 flex-shrink-0 text-gray-400" />
                                    : <ChevronDown className="h-3 w-3 flex-shrink-0 text-gray-400" />}
                                  <span className="line-clamp-1">{q.question}</span>
                                </div>
                              </td>
                              <td className="px-3 py-2">
                                <span
                                  className="rounded border px-1.5 py-0.5 text-[9px] font-semibold uppercase"
                                  style={{ backgroundColor: diff.bg, color: diff.text, borderColor: diff.border }}
                                >
                                  {q.difficulty}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-right"><ScorePill value={q.faithfulness} /></td>
                              <td className="px-3 py-2 text-right"><ScorePill value={q.answer_relevancy} /></td>
                              <td className="px-3 py-2 text-right"><ScorePill value={q.context_precision} /></td>
                              <td className="px-3 py-2 text-right"><ScorePill value={q.context_recall} /></td>
                              <td className="px-3 py-2 text-right">
                                <span
                                  className="tabular-nums font-medium text-[11px]"
                                  style={{ color: q.low_confidence ? AMBER : GREEN }}
                                >
                                  {q.confidence_score.toFixed(2)}
                                </span>
                              </td>
                            </tr>
                            {isExpanded && (
                              <tr key={`${q.id}-detail`} style={{ backgroundColor: BLUE_BG }}>
                                <td colSpan={8} className="px-4 py-3">
                                  <div className="space-y-2 text-[11px]">
                                    <div>
                                      <span className="font-semibold" style={{ color: TEXT_SECONDARY }}>Answer: </span>
                                      <span style={{ color: TEXT_PRIMARY }}>{q.answer}</span>
                                    </div>
                                    <div>
                                      <span className="font-semibold" style={{ color: TEXT_SECONDARY }}>Ground truth: </span>
                                      <span style={{ color: TEXT_PRIMARY }}>{q.ground_truth}</span>
                                    </div>
                                    <div className="flex items-center gap-4">
                                      <span style={{ color: TEXT_TERTIARY }}>
                                        Section: <span className="font-medium" style={{ color: TEXT_SECONDARY }}>{q.section}</span>
                                      </span>
                                      <span style={{ color: TEXT_TERTIARY }}>
                                        Source: <span className="font-medium" style={{ color: TEXT_SECONDARY }}>{sourceLabel(q.source_doc)}</span>
                                      </span>
                                      <span style={{ color: TEXT_TERTIARY }}>
                                        Latency: <span className="font-medium" style={{ color: TEXT_SECONDARY }}>{q.latency_ms.toFixed(0)}ms</span>
                                      </span>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
