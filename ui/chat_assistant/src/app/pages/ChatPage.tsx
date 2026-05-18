import { useState } from 'react';
import { Dna, Activity, Clock } from 'lucide-react';
import { LeftRail } from '../components/LeftRail';
import { CenterPane } from '../components/CenterPane';
import { RightRail } from '../components/RightRail';
import EngineeringTab from '../components/EngineeringTab';
import MetricsTab from '../components/MetricsTab';
import { RAGAS_METRICS, SYSTEM_STATS } from '../config';

interface Citation {
  guidelineId: string;
  section: string;
  guidelineName: string;
  text: string;
  color: string;
  bgColor: string;
}

const GUIDELINES_BASE = [
  {
    id: 'FDA',
    name: 'FDA',
    fullName: 'Metformin Drug Label',
    color: '#1E3A8A',
    bgColor: '#EFF6FF',
    borderColor: '#BFDBFE',
  },
  {
    id: 'ADA',
    name: 'ADA',
    fullName: 'Standards of Medical Care in Diabetes (2024)',
    color: '#15803D',
    bgColor: '#F0FDF4',
    borderColor: '#BBF7D0',
  },
  {
    id: 'JNC8',
    name: 'JNC 8',
    fullName: 'Hypertension Management Guidelines',
    color: '#0E7490',
    bgColor: '#ECFEFF',
    borderColor: '#A5F3FC',
  },
];

type ActiveTab = 'query' | 'engineering' | 'metrics';

const PRIMARY_BLUE = '#185FA5';
const GREEN = '#3B6D11';
const GREEN_BG = '#EAF3DE';
const GREEN_BORDER = '#C0DD97';

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('query');
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [citationCounts, setCitationCounts] = useState<Record<string, number>>({
    FDA: 0, ADA: 0, JNC8: 0,
  });

  const handleCitationsChange = (citations: Citation[]) => {
    const counts: Record<string, number> = { FDA: 0, ADA: 0, JNC8: 0 };
    citations.forEach((c) => {
      const id = c.guidelineId.toUpperCase();
      if (id in counts) counts[id] = (counts[id] || 0) + 1;
    });
    setCitationCounts(counts);
  };

  const guidelines = GUIDELINES_BASE.map((g) => ({
    ...g,
    sectionsUsed: citationCounts[g.id] ?? 0,
  }));

  const tabs: { id: ActiveTab; label: string }[] = [
    { id: 'query', label: 'Query' },
    { id: 'engineering', label: 'Engineering' },
    { id: 'metrics', label: 'Metrics' },
  ];

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-white">
      {/* Top navbar */}
      <nav
        className="flex flex-shrink-0 items-center justify-between border-b px-4"
        style={{ height: 48, borderColor: '#E5E7EB' }}
      >
        {/* Left: logo */}
        <div className="flex items-center gap-2">
          <Dna className="h-4 w-4" style={{ color: PRIMARY_BLUE }} />
          <span className="text-sm font-bold" style={{ color: '#1A1A1A' }}>
            ClinicalRAG
          </span>
        </div>

        {/* Right: live metrics */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3" style={{ color: GREEN }} />
            <span className="font-medium" style={{ color: GREEN }}>
              {RAGAS_METRICS.faithfulness}
            </span>
            <span style={{ color: '#888' }}> faithfulness</span>
          </div>
          <span style={{ color: '#D1D5DB' }}>|</span>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3 text-gray-400" />
            <span style={{ color: '#555' }}>{SYSTEM_STATS.p50ms}ms p50</span>
          </div>
          <span style={{ color: '#D1D5DB' }}>|</span>
          <div
            className="inline-flex items-center gap-1 rounded border px-2 py-0.5"
            style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER }}
          >
            <span className="text-[11px] font-medium" style={{ color: GREEN }}>
              ✓ CI passing
            </span>
          </div>
        </div>
      </nav>

      {/* Body: left rail + main area */}
      <div className="flex flex-1 overflow-hidden">
        <LeftRail guidelines={guidelines} />

        {/* Main area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Tab bar */}
          <div
            className="flex flex-shrink-0 items-center justify-between border-b px-4"
            style={{ borderColor: '#E5E7EB', height: 40 }}
          >
            {/* Left: tab buttons */}
            <div className="flex items-center gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="rounded px-3 py-1 text-xs transition-colors"
                  style={
                    activeTab === tab.id
                      ? { backgroundColor: '#F3F4F6', fontWeight: 500, color: '#1A1A1A' }
                      : { color: '#555' }
                  }
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Right: guest info */}
            <div className="flex items-center gap-2">
              <span className="text-[11px]" style={{ color: '#888' }}>
                Guest · 5 queries available
              </span>
              <button
                className="rounded border px-2 py-0.5 text-[11px] font-medium transition-colors hover:bg-gray-50"
                style={{ borderColor: '#D1D5DB', color: '#555' }}
              >
                Sign in
              </button>
            </div>
          </div>

          {/* Tab content */}
          <div className="flex flex-1 overflow-hidden">
            {activeTab === 'query' && (
              <div className="flex flex-1 overflow-hidden">
                <CenterPane
                  onCitationClick={setSelectedCitation}
                  activeCitation={selectedCitation}
                  onCitationsChange={handleCitationsChange}
                />
                {selectedCitation && (
                  <RightRail
                    selectedCitation={selectedCitation}
                    onClose={() => setSelectedCitation(null)}
                  />
                )}
              </div>
            )}
            {activeTab === 'engineering' && (
              <div className="flex-1 overflow-auto">
                <EngineeringTab />
              </div>
            )}
            {activeTab === 'metrics' && (
              <div className="flex-1 overflow-auto">
                <MetricsTab />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
