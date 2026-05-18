import { useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Dna,
  Github,
  FileText,
  Sitemap,
  FlaskConical,
  Activity,
  ExternalLink,
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
const TEXT_PRIMARY = '#1A1A1A';
const TEXT_SECONDARY = '#555';
const TEXT_TERTIARY = '#888';

export default function LandingPage() {
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white" style={{ color: TEXT_PRIMARY }}>
      {/* Navbar */}
      <nav
        className="flex items-center justify-between border-b px-6"
        style={{ height: 48, borderColor: '#E5E7EB' }}
      >
        {/* Left */}
        <div className="flex items-center gap-2">
          <Dna className="h-4 w-4" style={{ color: PRIMARY_BLUE }} />
          <span className="text-sm font-bold" style={{ color: TEXT_PRIMARY }}>
            ClinicalRAG
          </span>
          <span className="text-xs" style={{ color: TEXT_TERTIARY }}>
            by Anshika Goel
          </span>
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          <a
            href={GITHUB_URL + '#architecture'}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs transition-colors hover:underline"
            style={{ color: TEXT_SECONDARY }}
          >
            How it&apos;s built
          </a>
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
            Try it free
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section
        className="flex flex-col items-center border-b px-6 py-12 text-center"
        style={{ borderColor: '#E5E7EB' }}
      >
        {/* Eyebrow badge */}
        <div
          className="mb-4 inline-flex items-center gap-1.5 rounded-full border px-3 py-1"
          style={{ backgroundColor: BLUE_BG, borderColor: BLUE_BORDER }}
        >
          <span className="text-[11px] font-medium" style={{ color: PRIMARY_BLUE }}>
            🧪 Production RAG · Clinical documents · Health plan use case
          </span>
        </div>

        <h1 className="mb-3 max-w-2xl text-[22px] font-medium leading-snug" style={{ color: TEXT_PRIMARY }}>
          Ask clinical questions. Get grounded, cited answers.
        </h1>

        <p className="mb-7 max-w-xl text-sm leading-relaxed" style={{ color: TEXT_SECONDARY }}>
          A RAG system built the way a senior AI/ML engineer would build it — architecture documented
          before code was written, eval harness in CI, drift detection on every batch.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            className="rounded px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
            style={{ backgroundColor: PRIMARY_BLUE }}
            onClick={() => navigate('/chat')}
          >
            Try a query — no login needed
          </button>
          <a
            href={GITHUB_URL + '/blob/main/docs/DECISIONS.md'}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded border px-4 py-2 text-sm font-medium transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: TEXT_SECONDARY }}
          >
            Read the Decisions doc
          </a>
        </div>
      </section>

      {/* Metrics strip */}
      <section
        className="grid grid-cols-4 border-b"
        style={{ borderColor: '#E5E7EB' }}
      >
        {/* Cell 1 */}
        <div
          className="flex flex-col items-center justify-center gap-1 border-r px-4 py-5"
          style={{ borderColor: '#E5E7EB' }}
        >
          <span className="text-base font-medium" style={{ color: GREEN }}>
            0.75
          </span>
          <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
            Faithfulness (RAGAS)
          </span>
        </div>

        {/* Cell 2 */}
        <div
          className="flex flex-col items-center justify-center gap-1 border-r px-4 py-5"
          style={{ borderColor: '#E5E7EB' }}
        >
          <span className="text-base font-medium" style={{ color: PRIMARY_BLUE }}>
            {SYSTEM_STATS.p50ms}ms
          </span>
          <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
            p50 latency
          </span>
        </div>

        {/* Cell 3 */}
        <div
          className="flex flex-col items-center justify-center gap-1 border-r px-4 py-5"
          style={{ borderColor: '#E5E7EB' }}
        >
          <span className="text-base font-medium" style={{ color: GREEN }}>
            {SYSTEM_STATS.evalPassing} / {SYSTEM_STATS.evalTotal}
          </span>
          <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
            Eval questions passing
          </span>
        </div>

        {/* Cell 4 */}
        <div className="flex flex-col items-center justify-center gap-1 px-4 py-5">
          <div
            className="inline-flex items-center gap-1.5 rounded border px-2 py-0.5"
            style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER }}
          >
            <span className="text-[11px] font-medium" style={{ color: GREEN }}>
              ✓ CI passing
            </span>
          </div>
          <span className="text-[11px]" style={{ color: TEXT_TERTIARY }}>
            GitHub Actions
          </span>
        </div>
      </section>

      {/* Sources row */}
      <section
        className="flex flex-wrap items-center gap-3 border-b px-6 py-3"
        style={{ borderColor: '#E5E7EB' }}
      >
        <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color: TEXT_TERTIARY }}>
          Indexed sources
        </span>
        <div
          className="rounded border px-2 py-0.5 text-[11px] font-medium"
          style={{ backgroundColor: BLUE_BG, borderColor: BLUE_BORDER, color: PRIMARY_BLUE }}
        >
          FDA Metformin Label
        </div>
        <div
          className="rounded border px-2 py-0.5 text-[11px] font-medium"
          style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER, color: GREEN }}
        >
          ADA Standards 2023 §6
        </div>
        <div
          className="rounded border px-2 py-0.5 text-[11px] font-medium"
          style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER, color: GREEN }}
        >
          ADA Standards 2023 §9
        </div>
        <div
          className="rounded border px-2 py-0.5 text-[11px] font-medium"
          style={{ backgroundColor: AMBER_BG, borderColor: AMBER_BORDER, color: AMBER }}
        >
          JNC 8 Hypertension
        </div>
      </section>

      {/* How it's different section */}
      <section className="border-b px-6 py-8" style={{ borderColor: '#E5E7EB' }}>
        <h2 className="mb-5 text-sm font-semibold" style={{ color: TEXT_PRIMARY }}>
          Why this is different from a prototype
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {/* Card 1 */}
          <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
            <div className="mb-2 flex items-center gap-2">
              <FileText className="h-4 w-4 flex-shrink-0" style={{ color: PRIMARY_BLUE }} />
              <span className="text-xs font-semibold" style={{ color: TEXT_PRIMARY }}>
                Documented decisions
              </span>
            </div>
            <p className="text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              Every trade-off written before code. Chunk size, retrieval design, confidence
              threshold — all in DECISIONS.md.
            </p>
          </div>

          {/* Card 2 */}
          <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
            <div className="mb-2 flex items-center gap-2">
              <FlaskConical className="h-4 w-4 flex-shrink-0" style={{ color: GREEN }} />
              <span className="text-xs font-semibold" style={{ color: TEXT_PRIMARY }}>
                CI eval gate
              </span>
            </div>
            <p className="text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              40 manually written Q&As. GitHub Actions blocks deploys if RAGAS faithfulness
              drops below 0.75.
            </p>
          </div>

          {/* Card 3 */}
          <div className="rounded-lg border bg-white p-3" style={{ borderColor: '#E5E7EB' }}>
            <div className="mb-2 flex items-center gap-2">
              <Activity className="h-4 w-4 flex-shrink-0" style={{ color: AMBER }} />
              <span className="text-xs font-semibold" style={{ color: TEXT_PRIMARY }}>
                Production observability
              </span>
            </div>
            <p className="text-[11px] leading-relaxed" style={{ color: TEXT_SECONDARY }}>
              Per-query metrics, latency by stage, embedding drift detection on every new
              document batch.
            </p>
          </div>
        </div>
      </section>

      {/* Links row */}
      <section
        className="flex flex-wrap items-center gap-3 px-6 py-3"
        style={{ borderColor: '#E5E7EB' }}
      >
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] transition-colors hover:underline"
          style={{ color: TEXT_SECONDARY }}
        >
          <Github className="h-3 w-3" />
          GitHub
        </a>
        <span style={{ color: '#D1D5DB' }}>|</span>
        <a
          href={GITHUB_URL + '/blob/main/docs/DECISIONS.md'}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] transition-colors hover:underline"
          style={{ color: TEXT_SECONDARY }}
        >
          <FileText className="h-3 w-3" />
          DECISIONS.md
        </a>
        <span style={{ color: '#D1D5DB' }}>|</span>
        <a
          href={GITHUB_URL + '/blob/main/docs/ARCHITECTURE.md'}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] transition-colors hover:underline"
          style={{ color: TEXT_SECONDARY }}
        >
          <ExternalLink className="h-3 w-3" />
          ARCHITECTURE.md
        </a>
        <span style={{ color: '#D1D5DB' }}>|</span>
        <div
          className="inline-flex items-center gap-1.5 rounded border px-2 py-0.5"
          style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER }}
        >
          <span className="text-[11px] font-medium" style={{ color: GREEN }}>
            ✓ CI passing · faithfulness {RAGAS_METRICS.faithfulness}
          </span>
        </div>
      </section>

      <AccessModal open={modalOpen} onOpenChange={setModalOpen} />
    </div>
  );
}
