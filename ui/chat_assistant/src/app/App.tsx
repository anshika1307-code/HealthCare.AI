import { useState } from 'react';
import { LeftRail } from './components/LeftRail';
import { CenterPane } from './components/CenterPane';
import { RightRail } from './components/RightRail';

interface Citation {
  guidelineId: 'FDA' | 'ADA' | 'JNC8' | 'AHA_ACC';
  section: string;
  guidelineName: string;
  text: string;
  color: string;
  bgColor: string;
}

export default function App() {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const guidelines = [
    {
      id: 'FDA',
      name: 'FDA',
      fullName: 'Metformin Drug Label',
      color: '#1E3A8A',
      bgColor: '#EFF6FF',
      borderColor: '#BFDBFE',
      sectionsUsed: 1,
    },
    {
      id: 'ADA',
      name: 'ADA',
      fullName: 'Standards of Medical Care in Diabetes (2024)',
      color: '#15803D',
      bgColor: '#F0FDF4',
      borderColor: '#BBF7D0',
      sectionsUsed: 1,
    },
    {
      id: 'JNC8',
      name: 'JNC 8',
      fullName: 'Hypertension Management Guidelines',
      color: '#C2410C',
      bgColor: '#FFF7ED',
      borderColor: '#FED7AA',
      sectionsUsed: 1,
    },
    {
      id: 'AHA_ACC',
      name: 'AHA/ACC',
      fullName: 'Cardiovascular Risk Guidelines',
      color: '#991B1B',
      bgColor: '#FDF2F2',
      borderColor: '#FEE2E2',
      sectionsUsed: 0,
    },
  ];

  return (
    <div className="flex h-screen bg-white">
      <LeftRail guidelines={guidelines} />
      <CenterPane
        onCitationClick={setSelectedCitation}
        activeCitation={selectedCitation}
      />
      <RightRail
        selectedCitation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
}