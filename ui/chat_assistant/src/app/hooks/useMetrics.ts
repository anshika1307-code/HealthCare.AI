import { useEffect, useState } from 'react';
import { RAGAS_METRICS, SYSTEM_STATS } from '../config';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface LiveMetrics {
  queryCount: number | null;
  lowConfidenceCount: number | null;
  errorCount: number | null;
  avgLatencyMs: number | null;
  avgConfidence: number | null;
  faithfulness: number;
  answerRelevancy: number;
  contextPrecision: number;
  contextRecall: number;
  evalThreshold: number;
  p50ms: number;
  p95ms: number;
  evalTotal: number;
  evalPassing: number;
  loading: boolean;
  error: boolean;
}

const STATIC_FALLBACK: LiveMetrics = {
  queryCount: null,
  lowConfidenceCount: null,
  errorCount: null,
  avgLatencyMs: null,
  avgConfidence: null,
  faithfulness: RAGAS_METRICS.faithfulness,
  answerRelevancy: RAGAS_METRICS.answerRelevancy,
  contextPrecision: RAGAS_METRICS.contextPrecision,
  contextRecall: RAGAS_METRICS.contextRecall,
  evalThreshold: RAGAS_METRICS.threshold,
  p50ms: SYSTEM_STATS.p50ms,
  p95ms: SYSTEM_STATS.p95ms,
  evalTotal: SYSTEM_STATS.evalTotal,
  evalPassing: SYSTEM_STATS.evalPassing,
  loading: false,
  error: false,
};

/** Use the live value only when it is a positive number — fall back to static otherwise.
 *  A 0.0 from the API means "not yet computed / eval not run", not a true zero score. */
function liveOrStatic(liveVal: number | null | undefined, staticVal: number): number {
  return liveVal != null && liveVal > 0 ? liveVal : staticVal;
}

export function useMetrics(): LiveMetrics {
  const [metrics, setMetrics] = useState<LiveMetrics>({ ...STATIC_FALLBACK, loading: true });

  useEffect(() => {
    let cancelled = false;

    async function fetchMetrics() {
      try {
        const res = await fetch(`${API_URL}/metrics`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (cancelled) return;

        const ev = data.eval ?? {};

        setMetrics({
          queryCount: data.query_count ?? null,
          lowConfidenceCount: data.low_confidence_count ?? null,
          errorCount: data.error_count ?? null,
          avgLatencyMs: data.avg_latency_ms ?? null,
          avgConfidence: data.avg_confidence ?? null,
          // Use static eval scores from config when live value is 0 or absent.
          // "0" means the eval key is missing in Redis, not a real zero score.
          faithfulness: liveOrStatic(ev.faithfulness, RAGAS_METRICS.faithfulness),
          answerRelevancy: liveOrStatic(
            ev.answer_relevancy ?? ev.answerRelevancy,
            RAGAS_METRICS.answerRelevancy,
          ),
          contextPrecision: liveOrStatic(
            ev.context_precision ?? ev.contextPrecision,
            RAGAS_METRICS.contextPrecision,
          ),
          contextRecall: liveOrStatic(
            ev.context_recall ?? ev.contextRecall,
            RAGAS_METRICS.contextRecall,
          ),
          evalThreshold: RAGAS_METRICS.threshold,
          p50ms: data.avg_latency_ms != null && data.avg_latency_ms > 0
            ? Math.round(data.avg_latency_ms)
            : SYSTEM_STATS.p50ms,
          p95ms: SYSTEM_STATS.p95ms,
          evalTotal: SYSTEM_STATS.evalTotal,
          evalPassing: SYSTEM_STATS.evalPassing,
          loading: false,
          error: false,
        });
      } catch {
        if (!cancelled) {
          setMetrics({ ...STATIC_FALLBACK, loading: false, error: true });
        }
      }
    }

    fetchMetrics();
    return () => { cancelled = true; };
  }, []);

  return metrics;
}
