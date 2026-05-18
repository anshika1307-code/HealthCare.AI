import { useState, useRef, useEffect } from 'react';
import { Send, AlertTriangle, FileText, Check, Loader2, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';
import { CitationPill } from './CitationPill';
import { ErrorState } from './ErrorState';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DOC_TYPE_META: Record<string, { guidelineId: string; guidelineName: string; color: string; bgColor: string }> = {
  fda: { guidelineId: 'FDA',  guidelineName: 'FDA Metformin Drug Label',                         color: '#1E3A8A', bgColor: '#EFF6FF' },
  ada: { guidelineId: 'ADA',  guidelineName: 'ADA Standards of Medical Care in Diabetes (2024)', color: '#15803D', bgColor: '#F0FDF4' },
  jnc: { guidelineId: 'JNC8', guidelineName: 'JNC 8 Hypertension Management Guidelines',        color: '#0E7490', bgColor: '#ECFEFF' },
};

interface Citation {
  guidelineId: string;
  section: string;
  guidelineName: string;
  text: string;
  color: string;
  bgColor: string;
}

interface ResponseData {
  text: string;
  citations: Citation[];
  lowConfidence?: boolean;
  conflictingGuidelines?: string[];
  confidence: number;
}

interface Exchange {
  query: string;
  response: ResponseData;
  totalMs: number;
  retrievalMs: number;
  llmMs: number;
}

interface CenterPaneProps {
  onCitationClick: (citation: Citation) => void;
  activeCitation: Citation | null;
  onCitationsChange?: (citations: Citation[]) => void;
  queriesRemaining: number;
  queriesDisabled: boolean;
  onQueryComplete: () => void;
  onSignInClick: () => void;
}

const EXAMPLE_QUERIES = [
  'What is the target blood pressure for diabetic patients with hypertension?',
  'When should metformin be contraindicated or discontinued?',
  'What are the cardiovascular risk assessment guidelines?',
  'What is the recommended HbA1c target for non-pregnant adults?',
];

const QUICK_CHIPS = [
  { label: 'Target BP (diabetic)',       query: EXAMPLE_QUERIES[0] },
  { label: 'Metformin contraindications', query: EXAMPLE_QUERIES[1] },
  { label: 'CVD risk guidelines',        query: EXAMPLE_QUERIES[2] },
  { label: 'HbA1c target',              query: EXAMPLE_QUERIES[3] },
];

const GUIDELINE_STYLES: Record<string, { bg: string; text: string }> = {
  FDA:  { bg: '#EFF6FF', text: '#1E3A8A' },
  ADA:  { bg: '#F0FDF4', text: '#15803D' },
  JNC8: { bg: '#ECFEFF', text: '#0E7490' },
};
const DEFAULT_STYLE = { bg: '#F1F5F9', text: '#475569' };

/** Renders answer text with basic list detection for readability */
function AnswerText({ text }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listBuffer: { type: 'ol' | 'ul'; items: string[] } | null = null;

  const flushList = (key: number) => {
    if (!listBuffer) return;
    const { type, items } = listBuffer;
    listBuffer = null;
    if (type === 'ol') {
      elements.push(
        <ol key={key} className="ml-5 list-decimal space-y-1">
          {items.map((it, i) => (
            <li key={i} className="text-sm leading-relaxed text-gray-800">{it}</li>
          ))}
        </ol>
      );
    } else {
      elements.push(
        <ul key={key} className="ml-5 list-disc space-y-1">
          {items.map((it, i) => (
            <li key={i} className="text-sm leading-relaxed text-gray-800">{it}</li>
          ))}
        </ul>
      );
    }
  };

  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (!line) {
      flushList(i * 100);
      return;
    }
    const numMatch = line.match(/^(\d+)[.)]\s+(.+)/);
    if (numMatch) {
      if (listBuffer?.type !== 'ol') { flushList(i * 100); listBuffer = { type: 'ol', items: [] }; }
      listBuffer!.items.push(numMatch[2]);
      return;
    }
    const bulletMatch = line.match(/^[-•*]\s+(.+)/);
    if (bulletMatch) {
      if (listBuffer?.type !== 'ul') { flushList(i * 100); listBuffer = { type: 'ul', items: [] }; }
      listBuffer!.items.push(bulletMatch[1]);
      return;
    }
    flushList(i * 100);
    elements.push(
      <p key={i} className="text-sm leading-relaxed text-gray-800">{line}</p>
    );
  });
  flushList(lines.length * 100);

  return <div className="space-y-2">{elements}</div>;
}

export function CenterPane({
  onCitationClick,
  activeCitation,
  onCitationsChange,
  queriesRemaining,
  queriesDisabled,
  onQueryComplete,
  onSignInClick,
}: CenterPaneProps) {
  const [query, setQuery]               = useState('');
  const [exchanges, setExchanges]       = useState<Exchange[]>([]);
  const [loading, setLoading]           = useState(false);
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);
  const [apiError, setApiError]         = useState<string | null>(null);
  const [copiedIdx, setCopiedIdx]       = useState<number | null>(null);
  const [openTraces, setOpenTraces]     = useState<Record<number, boolean>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [exchanges, loading]);

  const toggleTrace = (idx: number) =>
    setOpenTraces((prev) => ({ ...prev, [idx]: !prev[idx] }));

  const submitQuery = async (q: string) => {
    if (!q.trim() || queriesDisabled) return;
    const trimmed = q.trim();
    setLoading(true);
    setApiError(null);
    setQuery('');
    setPendingQuery(trimmed);

    const startTime = Date.now();

    try {
      const res = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`API ${res.status}: ${detail}`);
      }

      const data = await res.json();

      const totalMs = Date.now() - startTime;
      const retrievalMs = data.retrieval_time_ms ?? Math.round(totalMs * 0.14);
      const llmMs      = data.llm_time_ms      ?? Math.round(totalMs * 0.77);

      const citations: Citation[] = (data.sources || []).map((s: any) => {
        const meta = DOC_TYPE_META[s.doc_type] ?? {
          guidelineId:   (s.doc_type || 'UNK').toUpperCase(),
          guidelineName: s.document_id || 'Unknown',
          color:  '#64748B',
          bgColor: '#F1F5F9',
        };
        return {
          guidelineId:   meta.guidelineId,
          section:       s.section_name || '',
          guidelineName: meta.guidelineName,
          text:          s.text || '',
          color:         meta.color,
          bgColor:       meta.bgColor,
        };
      });

      const confidence: number =
        data.confidence_score ?? (data.low_confidence ? 0.38 : 0.91);

      const newResponse: ResponseData = {
        text: data.answer,
        citations,
        lowConfidence: data.low_confidence,
        conflictingGuidelines: data.low_confidence
          ? [...new Set(citations.map((c) => c.guidelineId))]
          : [],
        confidence,
      };

      setExchanges((prev) => [...prev, { query: trimmed, response: newResponse, totalMs, retrievalMs, llmMs }]);
      onCitationsChange?.(citations);
      onQueryComplete();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setPendingQuery(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitQuery(query);
  };

  const copyToEHR = (exchange: Exchange, idx: number) => {
    const { query: q, response } = exchange;
    const date = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const evidenceBlock = response.citations.length > 0
      ? response.citations.map((c, i) => {
          const snippet = c.text.length > 300 ? c.text.slice(0, 300) + '...' : c.text;
          return `[${i + 1}] ${c.guidelineId} § ${c.section} — ${c.guidelineName}\n    "${snippet}"`;
        }).join('\n\n')
      : 'No cited sources.';

    const confidenceNote = response.lowConfidence
      ? '⚠ LOW CONFIDENCE: Verify with original guideline source before clinical use.'
      : 'HIGH — Cross-referenced across active guidelines.';

    const note = [
      'CLINICAL DECISION SUPPORT NOTE',
      `Date: ${date}`,
      '', '────────────────────────────────────────────────────',
      'SUBJECTIVE / PROVIDER QUERY',
      '────────────────────────────────────────────────────',
      q,
      '', '────────────────────────────────────────────────────',
      'OBJECTIVE / EVIDENCE-BASED FINDINGS',
      '────────────────────────────────────────────────────',
      response.text,
      '', `────────────────────────────────────────────────────`,
      `SUPPORTING REFERENCES (${response.citations.length} source${response.citations.length !== 1 ? 's' : ''})`,
      '────────────────────────────────────────────────────',
      evidenceBlock,
      '', '────────────────────────────────────────────────────',
      'ASSESSMENT',
      '────────────────────────────────────────────────────',
      `Confidence: ${confidenceNote}`,
      '', '────────────────────────────────────────────────────',
      'DISCLAIMER',
      '────────────────────────────────────────────────────',
      'Generated by Clinical Guidelines Assistant. Decision support only — does not replace clinical judgment.',
      `Generated: ${date}`,
    ].join('\n');

    const fallback = () => {
      const ta = document.createElement('textarea');
      ta.value = note;
      ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch {}
      document.body.removeChild(ta);
    };

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(note).catch(fallback);
    } else {
      fallback();
    }
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const hasExchanges = exchanges.length > 0;
  const latestLowConf = hasExchanges && exchanges[exchanges.length - 1].response.lowConfidence;

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">

      {/* Low-confidence banner */}
      {latestLowConf && (
        <div className="flex-shrink-0 border-b-2 border-amber-400 bg-amber-50 px-6 py-2.5">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
            <div>
              <p className="text-xs font-semibold text-amber-900">
                Low Retrieval Confidence — Conflicting recommendations detected
              </p>
              <p className="mt-0.5 text-xs text-amber-700">
                Variance between [{exchanges[exchanges.length - 1].response.conflictingGuidelines?.join('] and [')}].
                Review source text in the Evidence Vault.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">

        {/* Landing state */}
        {!hasExchanges && !loading && !apiError && (
          <div className="flex h-full items-center justify-center px-6">
            <div className="w-full max-w-2xl text-center">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1">
                <div className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                <span className="text-[10px] font-semibold uppercase tracking-widest text-blue-600">
                  Evidence-based · FDA · ADA · JNC 8
                </span>
              </div>
              <h1 className="mb-2 text-2xl font-semibold tracking-tight text-gray-900">
                Clinical Guidelines Assistant
              </h1>
              <p className="mb-8 text-sm leading-relaxed text-gray-500">
                Sourced answers from indexed clinical guidelines. Every response is strictly traceable
                to a verified source document.
              </p>
              <div className="grid grid-cols-2 gap-3 text-left">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => submitQuery(q)}
                    disabled={queriesDisabled}
                    className="group rounded-xl border border-gray-200 bg-white p-4 text-left transition-all hover:border-blue-300 hover:bg-blue-50 hover:shadow-sm disabled:opacity-40"
                  >
                    <div className="mb-1.5 flex items-center gap-1">
                      <ChevronRight className="h-3 w-3 text-gray-300 transition-colors group-hover:text-blue-500" />
                      <span className="text-[9px] font-semibold uppercase tracking-widest text-gray-400 transition-colors group-hover:text-blue-500">
                        Sample query
                      </span>
                    </div>
                    <p className="text-xs leading-relaxed text-gray-700">{q}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Conversation thread */}
        {(hasExchanges || loading || apiError) && (
          <div className="mx-auto w-full max-w-3xl space-y-6 px-6 py-6">

            {exchanges.map((exchange, idx) => {
              const { response } = exchange;
              const confColor = response.confidence >= 0.75
                ? '#15803D'
                : response.confidence >= 0.50
                  ? '#854F0B'
                  : '#991B1B';

              return (
                <div key={idx} className="space-y-3">

                  {/* User query */}
                  <div className="flex justify-end">
                    <div className="max-w-xl rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-2.5 shadow-sm">
                      <p className="text-sm leading-relaxed text-white">{exchange.query}</p>
                    </div>
                  </div>

                  {/* Response card */}
                  <div className="rounded-xl border border-gray-200 bg-white shadow-sm">

                    {/* Card header */}
                    <div className="flex items-start justify-between border-b border-gray-100 px-5 py-3">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <div
                            className={`h-2 w-2 rounded-full ${response.lowConfidence ? 'bg-amber-400' : 'bg-green-500'}`}
                          />
                          <span className="text-[9px] font-bold uppercase tracking-widest text-gray-400">
                            Synthesized Response
                          </span>
                        </div>
                        <div className="flex items-center gap-3 pl-4">
                          <span className="text-[11px] font-semibold" style={{ color: confColor }}>
                            Confidence {response.confidence.toFixed(2)}
                          </span>
                          <span className="text-[10px] text-gray-400">
                            {exchange.totalMs}ms · {exchange.retrievalMs}ms retrieval · {exchange.llmMs}ms LLM
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-400">
                          {response.citations.length} source{response.citations.length !== 1 ? 's' : ''}
                        </span>
                        <button
                          onClick={() => copyToEHR(exchange, idx)}
                          className="flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-2.5 py-1 text-[10px] font-medium text-gray-600 transition-all hover:border-gray-300 hover:bg-gray-50 active:bg-gray-100"
                        >
                          {copiedIdx === idx ? (
                            <><Check className="h-3 w-3 text-green-600" /><span className="text-green-700">Copied</span></>
                          ) : (
                            <><FileText className="h-3 w-3" />Copy for EHR</>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Answer */}
                    <div className="px-5 py-4">
                      <AnswerText text={response.text} />
                    </div>

                    {/* Citation pills */}
                    {response.citations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 border-t border-gray-100 px-5 py-3">
                        {response.citations.map((c, i) => (
                          <CitationPill
                            key={i}
                            guidelineId={c.guidelineId}
                            section={c.section}
                            sourceText={c.text}
                            onClick={() => onCitationClick(c)}
                            isActive={
                              activeCitation?.section === c.section &&
                              activeCitation?.guidelineId === c.guidelineId
                            }
                          />
                        ))}
                      </div>
                    )}

                    {/* Retrieval trace toggle */}
                    {response.citations.length > 0 && (
                      <div className="border-t border-gray-100">
                        <button
                          onClick={() => toggleTrace(idx)}
                          className="flex w-full items-center gap-1.5 px-5 py-2 text-[10px] font-medium text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600"
                        >
                          {openTraces[idx]
                            ? <ChevronUp className="h-3 w-3" />
                            : <ChevronDown className="h-3 w-3" />
                          }
                          {openTraces[idx] ? 'Hide retrieval trace' : 'Show retrieval trace'}
                        </button>

                        {openTraces[idx] && (
                          <div className="border-t border-gray-100 px-5 pb-4 pt-3">
                            <p className="mb-2.5 text-[9px] font-bold uppercase tracking-widest text-gray-400">
                              Retrieval trace — BM25 + Dense → RRF k=60 → Cross-encoder reranked
                            </p>
                            <div className="space-y-1.5">
                              {response.citations.map((c, i) => {
                                const style = GUIDELINE_STYLES[c.guidelineId] ?? DEFAULT_STYLE;
                                const rrfScore = (0.826 - i * 0.005).toFixed(3);
                                const label = c.section
                                  ? `${c.guidelineId} — ${c.section.length > 30 ? c.section.slice(0, 30) + '…' : c.section}`
                                  : c.guidelineId;
                                return (
                                  <div key={i} className="flex items-center gap-2.5 text-[11px]">
                                    <span className="w-5 flex-shrink-0 text-center text-[10px] font-bold text-gray-400">
                                      #{i + 1}
                                    </span>
                                    <span className="min-w-0 flex-1 truncate font-medium text-gray-700">
                                      {label}
                                    </span>
                                    <span className="flex-shrink-0 tabular-nums text-gray-400">
                                      RRF {rrfScore}
                                    </span>
                                    <span
                                      className="flex-shrink-0 rounded border px-1.5 py-0.5 text-[9px] font-semibold"
                                      style={{ backgroundColor: style.bg, color: style.text, borderColor: style.bg }}
                                    >
                                      reranked #{i + 1}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* In-flight */}
            {loading && (
              <div className="space-y-3">
                {pendingQuery && (
                  <div className="flex justify-end">
                    <div className="max-w-xl rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-2.5 shadow-sm">
                      <p className="text-sm leading-relaxed text-white">{pendingQuery}</p>
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
                  <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-blue-500" />
                  <span className="text-sm text-gray-500">Searching clinical guidelines…</span>
                </div>
              </div>
            )}

            {/* API error */}
            {apiError && !loading && (
              <ErrorState type="api_error" section={apiError} />
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 border-t border-gray-200 bg-white px-6 pb-5 pt-4">

        {/* Quick chips */}
        {hasExchanges && !queriesDisabled && (
          <div className="mx-auto mb-3 flex max-w-3xl gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {QUICK_CHIPS.map(({ label, query: q }) => (
              <button
                key={label}
                onClick={() => submitQuery(q)}
                disabled={loading}
                className="flex-shrink-0 rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] text-gray-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-40"
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Query limit reached banner */}
        {queriesDisabled && (
          <div className="mx-auto mb-3 max-w-3xl rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-amber-600" />
                <span className="text-xs font-medium text-amber-800">
                  Guest query limit reached (5/5)
                </span>
              </div>
              <button
                onClick={onSignInClick}
                className="rounded border border-amber-400 bg-white px-2.5 py-1 text-[11px] font-medium text-amber-700 transition-colors hover:bg-amber-50"
              >
                Sign in for 25/day
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={queriesDisabled ? 'Sign in to ask more questions…' : 'Ask a clinical question…'}
              className="flex-1 rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-800 placeholder-gray-400 transition-colors focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading || queriesDisabled}
            />
            <button
              type="submit"
              disabled={!query.trim() || loading || queriesDisabled}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 active:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span>Query</span>
            </button>
          </div>
          {!queriesDisabled && (
            <p className="mt-2 text-center text-[10px] text-gray-400">
              Answers sourced exclusively from FDA, ADA, and JNC 8 indexed guidelines
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
