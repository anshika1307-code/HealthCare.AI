import { useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Dna,
  Github,
  FileText,
  Activity,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Database,
  Shuffle,
  Filter,
  Network,
  Shield,
  FlaskConical,
  TrendingDown,
  Layers,
  Cpu,
  Clock,
} from 'lucide-react';
import AccessModal from '../components/AccessModal';
import { GITHUB_URL, RAGAS_METRICS, SYSTEM_STATS } from '../config';

const PRIMARY_BLUE = '#185FA5';
const BLUE_BG = '#E6F1FB';
const BLUE_BORDER = '#B5D4F4';
const GREEN = '#3B6D11';
const GREEN_BG = '#EAF3DE';
const GREEN_BORDER = '#C0DD97';
const AMBER = '#854F0B';
const AMBER_BG = '#FAEEDA';
const AMBER_BORDER = '#FAC775';
const RED = '#991B1B';
const RED_BG = '#FEF2F2';
const RED_BORDER = '#FECACA';
const TEXT_PRIMARY = '#1A1A1A';
const TEXT_SECONDARY = '#555';
const TEXT_TERTIARY = '#888';

const GH = (path: string) => `${GITHUB_URL}/blob/main/${path}`;

function DocLink({ path, label }: { path: string; label: string }) {
  return (
    <a
      href={GH(path)}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-[11px] underline underline-offset-2 transition-opacity hover:opacity-70"
      style={{ color: PRIMARY_BLUE }}
    >
      <FileText className="h-2.5 w-2.5 flex-shrink-0" />
      {label}
    </a>
  );
}

const FEATURE_CARDS = [
  {
    num: 1,
    title: 'Custom preprocessing',
    detail: 'PDF → section-aware text extraction preserving clinical structure and table data.',
    icon: Layers,
    color: PRIMARY_BLUE,
    bg: BLUE_BG,
  },
  {
    num: 2,
    title: 'BM25 + dense hybrid search',
    detail: 'BM25 catches exact clinical acronyms (eGFR, SGLT2i, ACE); dense handles semantic variants.',
    icon: Database,
    color: GREEN,
    bg: GREEN_BG,
  },
  {
    num: 3,
    title: 'RRF fusion',
    detail: 'Reciprocal Rank Fusion (k=30) merges BM25 and dense lists without score normalisation.',
    icon: Shuffle,
    color: PRIMARY_BLUE,
    bg: BLUE_BG,
  },
  {
    num: 4,
    title: 'Cross-encoder reranking',
    detail: 'ms-marco-MiniLM-L-6-v2 re-scores top-60 candidates; only top-5 reach the LLM.',
    icon: Filter,
    color: AMBER,
    bg: AMBER_BG,
  },
  {
    num: 5,
    title: 'LangGraph orchestration',
    detail: 'Stateful graph: retrieve → rerank → confidence gate → generate → log.',
    icon: Network,
    color: PRIMARY_BLUE,
    bg: BLUE_BG,
  },
  {
    num: 6,
    title: 'Confidence gateway',
    detail: 'Cross-encoder sigmoid < 0.40 triggers in-answer disclaimer. Never suppresses the answer.',
    icon: Shield,
    color: GREEN,
    bg: GREEN_BG,
  },
  {
    num: 7,
    title: 'RAGAS-eval + CI gate',
    detail: 'GitHub Actions runs 40 hand-written Q&As; blocks deploy if faithfulness < 0.75.',
    icon: FlaskConical,
    color: AMBER,
    bg: AMBER_BG,
  },
  {
    num: 8,
    title: 'Drift detection',
    detail: 'Cosine-distance check on each document batch vs. index centroid. Alerts on semantic shift.',
    icon: TrendingDown,
    color: PRIMARY_BLUE,
    bg: BLUE_BG,
  },
];

const PROCESS_STEPS = [
  {
    step: 1,
    phase: 'PDF inspection',
    description: 'Manual review of raw PDFs — section boundaries, table structure, clinical formatting.',
    files: [
      { label: 'preprocessing_specs_dev.md', path: 'docs/preprocessing_specs_dev.md' },
      { label: 'preprocessing_spec_ai.md', path: 'docs/preprocessing_spec_ai.md' },
    ],
    aiUsage: 'No AI',
    aiColor: TEXT_TERTIARY,
    aiBg: '#F3F4F6',
  },
  {
    step: 2,
    phase: 'Architecture & decisions',
    description: 'System design written before any code — chunking strategy, retrieval model, confidence threshold rationale.',
    files: [
      { label: 'basic_architecture.md', path: 'docs/basic_architecture.md' },
      { label: 'decision.md', path: 'docs/decision.md' },
    ],
    aiUsage: 'No AI',
    aiColor: TEXT_TERTIARY,
    aiBg: '#F3F4F6',
  },
  {
    step: 3,
    phase: 'Chunking experiments',
    description: 'Systematic ablation: fixed-256, fixed-512, fixed-1024, boundary-aware variants tracked in MLflow.',
    files: [
      { label: 'dev_decisions_eval.md', path: 'ai_usage/dev_decisions_eval.md' },
    ],
    extras: ['MLflow experiment runs'],
    aiUsage: 'AI for code only',
    aiColor: AMBER,
    aiBg: AMBER_BG,
  },
  {
    step: 4,
    phase: 'Eval set design',
    description: '40 question–answer pairs written by domain spec, generated with GPT-4o, reviewed manually.',
    files: [
      { label: 'eval_ques_format.md', path: 'docs/eval_ques_format.md' },
    ],
    aiUsage: 'Spec by me · Gen by AI',
    aiColor: PRIMARY_BLUE,
    aiBg: BLUE_BG,
  },
  {
    step: 5,
    phase: 'Observability design',
    description: 'Per-query metrics schema, latency stage breakdown, drift detector spec — before implementation.',
    files: [
      { label: 'observability_specs.md', path: 'docs/observability_specs.md' },
    ],
    aiUsage: 'No AI',
    aiColor: TEXT_TERTIARY,
    aiBg: '#F3F4F6',
  },
  {
    step: 6,
    phase: 'UI specification',
    description: 'Full UI requirements and component hierarchy written as spec; mockup reviewed before building.',
    files: [
      { label: 'ui_requirements.md', path: 'docs/ui_requirements.md' },
    ],
    aiUsage: 'No AI',
    aiColor: TEXT_TERTIARY,
    aiBg: '#F3F4F6',
  },
  {
    step: 7,
    phase: 'Implementation',
    description: 'Backend, eval harness, UI — all built spec-driven using Claude Code with full audit trail.',
    files: [
      { label: 'logic_building.md', path: 'ai_usage/logic_building.md' },
      { label: 'testing.md', path: 'ai_usage/testing.md' },
    ],
    aiUsage: 'Claude Code (spec-driven)',
    aiColor: GREEN,
    aiBg: GREEN_BG,
  },
];

const AI_USAGE_ITEMS = [
  {
    title: 'Experiment code',
    detail:
      'Claude wrote Python scripts for chunking ablations and RAGAS scoring loops. Every script was reviewed and the output validated against manual spot-checks before results were accepted.',
    files: [{ label: 'dev_decisions_eval.md', path: 'ai_usage/dev_decisions_eval.md' }],
  },
  {
    title: 'Implementation',
    detail:
      'Backend pipeline, LangGraph graph, eval harness, and this UI were all built with Claude Code. The session transcripts are preserved in ai_usage/ — every non-trivial decision is traceable.',
    files: [
      { label: 'logic_building.md', path: 'ai_usage/logic_building.md' },
      { label: 'ui_building.md', path: 'ai_usage/ui_building.md' },
    ],
  },
  {
    title: 'Testing',
    detail:
      'Unit and integration test skeletons suggested by Claude, all assertions validated manually. Test coverage does not substitute for the RAGAS eval gate — both run in CI.',
    files: [{ label: 'testing.md', path: 'ai_usage/testing.md' }],
  },
];

const REPO_TREE = [
  { indent: 0, name: 'Healthcare_AI/', type: 'dir' },
  { indent: 1, name: 'configs/', type: 'dir', note: 'LLM + retrieval config' },
  { indent: 1, name: 'data/', type: 'dir', note: 'PDFs, eval set, indexed sources' },
  { indent: 1, name: 'docs/', type: 'dir', note: 'architecture, decisions, specs' },
  { indent: 2, name: 'basic_architecture.md', type: 'file', path: 'docs/basic_architecture.md' },
  { indent: 2, name: 'decision.md', type: 'file', path: 'docs/decision.md' },
  { indent: 2, name: 'observability_specs.md', type: 'file', path: 'docs/observability_specs.md' },
  { indent: 2, name: 'ui_requirements.md', type: 'file', path: 'docs/ui_requirements.md' },
  { indent: 1, name: 'ai_usage/', type: 'dir', note: 'full Claude Code session traces' },
  { indent: 2, name: 'logic_building.md', type: 'file', path: 'ai_usage/logic_building.md' },
  { indent: 2, name: 'testing.md', type: 'file', path: 'ai_usage/testing.md' },
  { indent: 1, name: 'src/', type: 'dir' },
  { indent: 2, name: 'evaluation/', type: 'dir', note: 'RAGAS runner, confidence checker' },
  { indent: 2, name: 'pipeline/', type: 'dir', note: 'LangGraph graph nodes' },
  { indent: 1, name: 'experiments/chunking/', type: 'dir', note: 'ablation results (MLflow)' },
  { indent: 1, name: 'ui/chat_assistant/', type: 'dir', note: 'React + Tailwind frontend' },
  { indent: 1, name: '.github/workflows/', type: 'dir', note: 'eval gate CI' },
];

type NavSection = 'overview' | 'process' | 'architecture' | 'ai-usage';

export default function LandingPage() {
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<NavSection>('overview');

  const scrollTo = (id: NavSection) => {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  const NAV_TABS: { id: NavSection; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'process', label: 'Process' },
    { id: 'architecture', label: 'Architecture' },
    { id: 'ai-usage', label: 'AI Usage' },
  ];

  return (
    <div className="min-h-screen bg-white" style={{ color: TEXT_PRIMARY }}>
      {/* ── Navbar ── */}
      <nav
        className="sticky top-0 z-30 flex items-center justify-between border-b bg-white px-6"
        style={{ height: 48, borderColor: '#E5E7EB' }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Dna className="h-4 w-4" style={{ color: PRIMARY_BLUE }} />
          <span className="text-sm font-bold" style={{ color: TEXT_PRIMARY }}>
            ClinicalRAG
          </span>
          <span className="text-xs" style={{ color: TEXT_TERTIARY }}>
            by Anshika Goel
          </span>
        </div>

        {/* Section tabs */}
        <div className="flex items-center gap-0.5">
          {NAV_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => scrollTo(tab.id)}
              className="rounded px-3 py-1.5 text-xs transition-colors"
              style={
                activeSection === tab.id
                  ? { backgroundColor: '#F3F4F6', fontWeight: 600, color: TEXT_PRIMARY }
                  : { color: TEXT_SECONDARY }
              }
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs transition-colors hover:underline"
            style={{ color: TEXT_SECONDARY }}
          >
            <Github className="h-3 w-3" />
            GitHub
          </a>
          <button
            className="rounded border px-3 py-1 text-xs font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
            onClick={() => setModalOpen(true)}
          >
            Sign in
          </button>
          <button
            className="rounded px-3 py-1 text-xs font-medium text-white transition-opacity hover:opacity-90"
            style={{ backgroundColor: PRIMARY_BLUE }}
            onClick={() => setModalOpen(true)}
          >
            Try for free
          </button>
        </div>
      </nav>

      {/* ══════════════════════════════════════════
          OVERVIEW SECTION
      ══════════════════════════════════════════ */}
      <section id="overview">

        {/* ── Hero ── */}
        <div className="border-b px-6 py-12" style={{ borderColor: '#E5E7EB' }}>
          <div className="mx-auto max-w-3xl">
            {/* Eyebrow */}
            <div
              className="mb-4 inline-flex items-center gap-1.5 rounded-full border px-3 py-1"
              style={{ backgroundColor: BLUE_BG, borderColor: BLUE_BORDER }}
            >
              <span className="text-[11px] font-medium" style={{ color: PRIMARY_BLUE }}>
                🧪 Production RAG · Clinical documents · Health plan use case
              </span>
            </div>

            <h1 className="mb-3 text-[22px] font-semibold leading-snug" style={{ color: TEXT_PRIMARY }}>
              Clinical guidance engine for pharmacists and care coordinators.
            </h1>

            <p className="mb-3 text-sm leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              Natural-language queries against authoritative clinical documents — FDA labels, ADA guidelines,
              JNC hypertension guidelines — with grounded, cited answers.
            </p>

            <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider" style={{ color: PRIMARY_BLUE }}>
              Not a prototype.
            </p>
            <p className="mb-1 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              Production-grade architecture · Built to show how production AI/ML projects should be built.
            </p>
            <p className="mb-6 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              Every architecture decision was documented before code was written, eval harness in CI,
              drift detection on every batch.
            </p>

            {/* CTA buttons */}
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded px-4 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90"
                style={{ backgroundColor: PRIMARY_BLUE }}
                onClick={() => navigate('/chat')}
              >
                Try a query — no login needed
              </button>
              <a
                href={GH('docs/decision.md')}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded border px-4 py-2 text-xs font-medium transition-colors hover:bg-gray-50"
                style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
              >
                <FileText className="h-3 w-3" />
                Read DECISIONS.md
              </a>
              <button
                className="flex items-center gap-1 rounded border px-4 py-2 text-xs font-medium transition-colors hover:bg-gray-50"
                style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
                onClick={() => navigate('/chat')}
              >
                <Activity className="h-3 w-3" />
                Observability dashboard
              </button>
              <a
                href={GH('docs/decision.md')}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded border px-4 py-2 text-xs font-medium transition-colors hover:bg-gray-50"
                style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
              >
                <ExternalLink className="h-3 w-3" />
                FAQs
              </a>
              <a
                href={GH('experiments/chunking')}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded border px-4 py-2 text-xs font-medium transition-colors hover:bg-gray-50"
                style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
              >
                <FlaskConical className="h-3 w-3" />
                Experiment metrics (MLflow)
              </a>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded border px-4 py-2 text-xs font-medium transition-colors hover:bg-gray-50"
                style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
              >
                <Github className="h-3 w-3" />
                GitHub
              </a>
            </div>
          </div>
        </div>

        {/* ── Metrics strip ── */}
        <div className="grid grid-cols-4 border-b" style={{ borderColor: '#E5E7EB' }}>
          <div className="flex flex-col items-center justify-center gap-1 border-r px-4 py-5" style={{ borderColor: '#E5E7EB' }}>
            <span className="text-base font-medium" style={{ color: AMBER }}>
              {RAGAS_METRICS.faithfulness}
            </span>
            <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>Faithfulness (RAGAS)</span>
          </div>
          <div className="flex flex-col items-center justify-center gap-1 border-r px-4 py-5" style={{ borderColor: '#E5E7EB' }}>
            <span className="text-base font-medium" style={{ color: PRIMARY_BLUE }}>
              {SYSTEM_STATS.p50ms}ms
            </span>
            <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>p50 latency</span>
          </div>
          <div className="flex flex-col items-center justify-center gap-1 border-r px-4 py-5" style={{ borderColor: '#E5E7EB' }}>
            <span className="text-base font-medium" style={{ color: GREEN }}>
              {SYSTEM_STATS.evalPassing} / {SYSTEM_STATS.evalTotal}
            </span>
            <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>Eval questions passing</span>
          </div>
          <div className="flex flex-col items-center justify-center gap-1 px-4 py-5">
            <div
              className="inline-flex items-center gap-1.5 rounded border px-2 py-0.5"
              style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER }}
            >
              <span className="text-[11px] font-medium" style={{ color: GREEN }}>✓ CI passing</span>
            </div>
            <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>GitHub Actions</span>
          </div>
        </div>

        {/* ── Indexed sources ── */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-3" style={{ borderColor: '#E5E7EB' }}>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
              Indexed sources
            </span>
            {[
              { label: 'FDA Metformin Label', bg: BLUE_BG, border: BLUE_BORDER, color: PRIMARY_BLUE },
              { label: 'ADA Standards 2023 §6', bg: GREEN_BG, border: GREEN_BORDER, color: GREEN },
              { label: 'ADA Standards 2023 §9', bg: GREEN_BG, border: GREEN_BORDER, color: GREEN },
              { label: 'JNC 8 Hypertension', bg: AMBER_BG, border: AMBER_BORDER, color: AMBER },
            ].map((s) => (
              <div
                key={s.label}
                className="rounded border px-2 py-0.5 text-[11px] font-medium"
                style={{ backgroundColor: s.bg, borderColor: s.border, color: s.color }}
              >
                {s.label}
              </div>
            ))}
          </div>
          <span className="text-[11px] italic" style={{ color: TEXT_TERTIARY }}>
            3 documents · deliberately constrained for retrieval stress-testing
          </span>
        </div>

        {/* ── Three-column: User base / What this demonstrates / Why hallucination = zero ── */}
        <div className="grid grid-cols-3 gap-0 border-b" style={{ borderColor: '#E5E7EB' }}>
          {/* User base */}
          <div className="border-r p-5" style={{ borderColor: '#E5E7EB' }}>
            <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
              User base
            </h3>
            <div className="space-y-2 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              <div>
                <span className="font-medium" style={{ color: TEXT_PRIMARY }}>Primary: </span>
                Pharmacists verifying dosing, contraindications
              </div>
              <div>
                <span className="font-medium" style={{ color: TEXT_PRIMARY }}>Secondary: </span>
                Care coordinators looking up care guidelines
              </div>
              <div>
                <span className="font-medium" style={{ color: TEXT_PRIMARY }}>Not: </span>
                Direct patient use — clinically trained professionals only
              </div>
              <div className="pt-1 text-[11px]" style={{ color: TEXT_TERTIARY }}>
                ~10 concurrent users · ~500 queries/day (prototype)
              </div>
            </div>
          </div>

          {/* What this demonstrates */}
          <div className="border-r p-5" style={{ borderColor: '#E5E7EB' }}>
            <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
              What this demonstrates
            </h3>
            <ul className="space-y-1.5 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              {[
                'Production RAG pipeline design',
                'System design thinking — SLAs, failure modes, observability',
                'Effective and transparent AI tool usage',
                'Documentation, timing, evaluation, monitoring as first-class work',
              ].map((item) => (
                <li key={item} className="flex items-start gap-1.5">
                  <CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0" style={{ color: GREEN }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Why hallucination = zero tolerance */}
          <div className="p-5">
            <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
              Why hallucination = zero tolerance
            </h3>
            <ul className="space-y-1.5 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              {[
                'Wrong dosage generation',
                'Incorrect contraindications stated',
                'Multiple guidelines mixed without attribution',
                'Outdated medical advice from LLM training data',
              ].map((item) => (
                <li key={item} className="flex items-start gap-1.5">
                  <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" style={{ color: RED }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* ── Two-column: Latency SLAs + Accuracy Thresholds ── */}
        <div className="grid grid-cols-2 gap-0 border-b" style={{ borderColor: '#E5E7EB' }}>
          {/* Latency SLAs */}
          <div className="border-r p-5" style={{ borderColor: '#E5E7EB' }}>
            <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
              Latency SLAs
            </h3>
            <div className="space-y-2">
              {[
                { label: 'p50 latency', value: '~800ms', color: PRIMARY_BLUE },
                { label: 'p95 latency', value: '~1,500ms', color: AMBER },
                { label: 'p99 latency', value: '5,000ms (hard ceiling)', color: RED },
                { label: 'Retrieval only', value: '~200ms p75', color: GREEN },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between text-xs">
                  <span style={{ color: TEXT_SECONDARY }}>{row.label}</span>
                  <span className="font-medium" style={{ color: row.color }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Accuracy Thresholds */}
          <div className="p-5">
            <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
              Accuracy Thresholds (RAGAS)
            </h3>
            <div className="space-y-2">
              {[
                { label: 'Faithfulness', value: `≥ 0.75 (CI gate)`, color: AMBER },
                { label: 'Answer Relevancy', value: '> 0.75', color: PRIMARY_BLUE },
                { label: 'Context Precision', value: '> 0.75', color: GREEN },
                { label: 'Confidence gate', value: 'below 0.65 → disclaimer', color: TEXT_SECONDARY },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between text-xs">
                  <span style={{ color: TEXT_SECONDARY }}>{row.label}</span>
                  <span className="font-medium" style={{ color: row.color }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Production risks handled ── */}
        <div className="border-b px-6 py-4" style={{ borderColor: '#E5E7EB' }}>
          <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
            Production risks handled
          </h3>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Wrong dosage generation', bg: RED_BG, border: RED_BORDER, color: RED },
              { label: 'Incorrect contraindications', bg: RED_BG, border: RED_BORDER, color: RED },
              { label: 'Mixed guideline attribution', bg: AMBER_BG, border: AMBER_BORDER, color: AMBER },
              { label: 'Outdated LLM training data', bg: AMBER_BG, border: AMBER_BORDER, color: AMBER },
              { label: 'Incomplete context retrieval', bg: BLUE_BG, border: BLUE_BORDER, color: PRIMARY_BLUE },
            ].map((tag) => (
              <span
                key={tag.label}
                className="rounded border px-2.5 py-1 text-[11px] font-medium"
                style={{ backgroundColor: tag.bg, borderColor: tag.border, color: tag.color }}
              >
                {tag.label}
              </span>
            ))}
          </div>
        </div>

        {/* ── 8 Feature cards ── */}
        <div className="border-b px-6 py-6" style={{ borderColor: '#E5E7EB' }}>
          <h3 className="mb-4 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
            Pipeline components
          </h3>
          <div className="grid grid-cols-4 gap-3">
            {FEATURE_CARDS.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.num}
                  className="rounded-lg border bg-white p-3"
                  style={{ borderColor: '#E5E7EB' }}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <div
                      className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded"
                      style={{ backgroundColor: card.bg }}
                    >
                      <Icon className="h-3.5 w-3.5" style={{ color: card.color }} />
                    </div>
                    <span
                      className="text-[10px] font-bold"
                      style={{ color: card.color }}
                    >
                      {card.num}
                    </span>
                  </div>
                  <p className="mb-1 text-xs font-semibold" style={{ color: TEXT_PRIMARY }}>
                    {card.title}
                  </p>
                  <p className="text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>
                    {card.detail}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Why different from a prototype ── */}
        <div className="border-b px-6 py-8" style={{ borderColor: '#E5E7EB' }}>
          <h2 className="mb-5 text-sm font-semibold" style={{ color: TEXT_PRIMARY }}>
            Why this is different from a prototype
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              {
                icon: FileText,
                iconColor: PRIMARY_BLUE,
                title: 'Documented decisions',
                body: 'Every trade-off written before code. Chunk size, retrieval design, confidence threshold — all in DECISIONS.md.',
                link: { label: 'decision.md', path: 'docs/decision.md' },
              },
              {
                icon: FlaskConical,
                iconColor: GREEN,
                title: 'CI eval gate',
                body: '40 manually written Q&As. GitHub Actions blocks deploys if RAGAS faithfulness drops below 0.75.',
                link: null,
              },
              {
                icon: Activity,
                iconColor: AMBER,
                title: 'Production observability',
                body: 'Per-query metrics, latency by stage, embedding drift detection on every new document batch.',
                link: { label: 'observability_specs.md', path: 'docs/observability_specs.md' },
              },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.title} className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
                  <div className="mb-2 flex items-center gap-2">
                    <Icon className="h-4 w-4 flex-shrink-0" style={{ color: card.iconColor }} />
                    <span className="text-xs font-semibold" style={{ color: TEXT_PRIMARY }}>{card.title}</span>
                  </div>
                  <p className="mb-2 text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>{card.body}</p>
                  {card.link && <DocLink path={card.link.path} label={card.link.label} />}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          PROCESS SECTION
      ══════════════════════════════════════════ */}
      <section id="process" className="border-b px-6 py-8" style={{ borderColor: '#E5E7EB' }}>
        <h2 className="mb-2 text-sm font-semibold" style={{ color: TEXT_PRIMARY }}>
          Process — How it's built
        </h2>
        <p className="mb-5 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
          A 7-step developer workflow from raw PDFs to production CI gate. Every step documented,
          every AI interaction traceable.
        </p>

        <div className="overflow-hidden rounded-lg border" style={{ borderColor: '#E5E7EB' }}>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b" style={{ backgroundColor: '#F9FAFB', borderColor: '#E5E7EB' }}>
                {['Step', 'Phase', 'Description', 'Files', 'AI Usage'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-left font-medium"
                    style={{ color: TEXT_TERTIARY }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white">
              {PROCESS_STEPS.map((row) => (
                <tr
                  key={row.step}
                  className="border-b last:border-0"
                  style={{ borderColor: '#F3F4F6' }}
                >
                  <td className="px-4 py-3">
                    <span
                      className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
                      style={{ backgroundColor: PRIMARY_BLUE }}
                    >
                      {row.step}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium" style={{ color: TEXT_PRIMARY }}>
                    {row.phase}
                  </td>
                  <td className="px-4 py-3 leading-relaxed" style={{ color: TEXT_SECONDARY, maxWidth: 280 }}>
                    {row.description}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      {row.files.map((f) => (
                        <DocLink key={f.path} path={f.path} label={f.label} />
                      ))}
                      {row.extras?.map((e) => (
                        <span key={e} className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
                          {e}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium"
                      style={{
                        color: row.aiColor,
                        backgroundColor: row.aiBg,
                        borderColor: row.aiBg === '#F3F4F6' ? '#E5E7EB' : row.aiBg,
                      }}
                    >
                      {row.aiUsage}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          AI USAGE SECTION
      ══════════════════════════════════════════ */}
      <section id="ai-usage" className="border-b px-6 py-8" style={{ borderColor: '#E5E7EB' }}>
        <h2 className="mb-2 text-sm font-semibold" style={{ color: TEXT_PRIMARY }}>
          AI Usage
        </h2>
        <p className="mb-5 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
          Every Claude Code session is preserved with full context. AI was used as a tool, not
          a driver — every output reviewed and validated.
        </p>

        <div className="space-y-3">
          {AI_USAGE_ITEMS.map((item, idx) => (
            <div
              key={item.title}
              className="rounded-lg border bg-white p-4"
              style={{ borderColor: '#E5E7EB' }}
            >
              <div className="flex items-start gap-3">
                <span
                  className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                  style={{ backgroundColor: PRIMARY_BLUE }}
                >
                  {idx + 1}
                </span>
                <div className="flex-1">
                  <p className="mb-1 text-xs font-semibold" style={{ color: TEXT_PRIMARY }}>
                    {item.title}
                  </p>
                  <p className="mb-2 text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>
                    {item.detail}
                  </p>
                  <div className="flex gap-3">
                    {item.files.map((f) => (
                      <DocLink key={f.path} path={f.path} label={f.label} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div
          className="mt-4 rounded-lg border p-3"
          style={{ backgroundColor: BLUE_BG, borderColor: BLUE_BORDER }}
        >
          <p className="text-[11px] leading-relaxed" style={{ color: PRIMARY_BLUE }}>
            All Claude Code session transcripts live in{' '}
            <a
              href={GH('ai_usage')}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium underline underline-offset-2 hover:opacity-70"
            >
              ai_usage/
            </a>
            . Every non-trivial architectural decision is traceable to a spec written before AI was
            invoked.
          </p>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          ARCHITECTURE SECTION
      ══════════════════════════════════════════ */}
      <section id="architecture" className="px-6 py-8">
        <h2 className="mb-2 text-sm font-semibold" style={{ color: TEXT_PRIMARY }}>
          Architecture
        </h2>
        <p className="mb-5 text-xs leading-relaxed" style={{ color: TEXT_SECONDARY }}>
          Repository structure — every key file links to GitHub.
        </p>

        <div className="grid grid-cols-2 gap-6">
          {/* Repo tree */}
          <div
            className="overflow-hidden rounded-lg border"
            style={{ borderColor: '#E5E7EB', fontFamily: 'monospace' }}
          >
            <div
              className="border-b px-4 py-2 text-[10px] font-medium uppercase tracking-wider"
              style={{ backgroundColor: '#F9FAFB', borderColor: '#E5E7EB', color: TEXT_TERTIARY }}
            >
              Repository structure
            </div>
            <div className="bg-white p-4">
              {REPO_TREE.map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1 py-0.5 text-[11px]"
                  style={{ paddingLeft: entry.indent * 16 }}
                >
                  <span style={{ color: TEXT_TERTIARY }}>{entry.type === 'dir' ? '📁' : '📄'}</span>
                  {entry.type === 'file' && entry.path ? (
                    <a
                      href={GH(entry.path)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline underline-offset-2 hover:opacity-70"
                      style={{ color: PRIMARY_BLUE }}
                    >
                      {entry.name}
                    </a>
                  ) : (
                    <span className="font-medium" style={{ color: entry.type === 'dir' ? TEXT_PRIMARY : TEXT_SECONDARY }}>
                      {entry.name}
                    </span>
                  )}
                  {entry.note && (
                    <span className="ml-2" style={{ color: TEXT_TERTIARY }}>
                      — {entry.note}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Tech stack */}
          <div className="space-y-3">
            <div className="rounded-lg border bg-white p-4" style={{ borderColor: '#E5E7EB' }}>
              <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
                Tech stack
              </h4>
              <div className="space-y-2 text-xs">
                {[
                  { layer: 'LLM', value: 'gpt-4o-mini (extractive system prompt)' },
                  { layer: 'Orchestration', value: 'LangGraph stateful graph' },
                  { layer: 'Retrieval', value: 'BM25 + FAISS dense + RRF fusion' },
                  { layer: 'Reranker', value: 'ms-marco-MiniLM-L-6-v2 cross-encoder' },
                  { layer: 'Embeddings', value: 'text-embedding-3-small' },
                  { layer: 'Eval', value: 'RAGAS (faithfulness, relevancy, precision, recall)' },
                  { layer: 'CI', value: 'GitHub Actions (eval gate, unit + integration tests)' },
                  { layer: 'Frontend', value: 'React + Tailwind v4 + Radix UI' },
                ].map((row) => (
                  <div key={row.layer} className="flex items-baseline gap-2">
                    <span className="w-24 flex-shrink-0 font-medium" style={{ color: TEXT_PRIMARY }}>
                      {row.layer}
                    </span>
                    <span style={{ color: TEXT_SECONDARY }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div
              className="rounded-lg border p-3"
              style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER }}
            >
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" style={{ color: GREEN }} />
                <span className="text-xs font-medium" style={{ color: GREEN }}>
                  Architecture written before code
                </span>
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed" style={{ color: GREEN }}>
                See{' '}
                <a href={GH('docs/basic_architecture.md')} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2 hover:opacity-70">
                  basic_architecture.md
                </a>{' '}
                and{' '}
                <a href={GH('docs/decision.md')} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2 hover:opacity-70">
                  decision.md
                </a>{' '}
                — both committed before the first pipeline code existed.
              </p>
            </div>
          </div>
        </div>
      </section>

      <AccessModal open={modalOpen} onOpenChange={setModalOpen} />
    </div>
  );
}
