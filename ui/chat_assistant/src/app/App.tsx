import { useState } from 'react';
import { LeftRail } from './components/LeftRail';
import { CenterPane } from './components/CenterPane';
import { RightRail } from './components/RightRail';

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

export default function App() {
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

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <LeftRail guidelines={guidelines} />
      <CenterPane
        onCitationClick={setSelectedCitation}
        activeCitation={selectedCitation}
        onCitationsChange={handleCitationsChange}
      />
      <RightRail
        selectedCitation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
}
