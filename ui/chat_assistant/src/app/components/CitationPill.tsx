import { useState } from 'react';

interface CitationPillProps {
  guidelineId: 'FDA' | 'ADA' | 'JNC8' | 'AHA_ACC';
  section: string;
  sourceText: string;
  onClick: () => void;
  isActive?: boolean;
}

const guidelineStyles = {
  FDA: {
    bg: '#EFF6FF',
    text: '#1E3A8A',
    border: '#BFDBFE',
    activeBg: '#1E3A8A',
  },
  ADA: {
    bg: '#F0FDF4',
    text: '#15803D',
    border: '#BBF7D0',
    activeBg: '#15803D',
  },
  JNC8: {
    bg: '#FFF7ED',
    text: '#C2410C',
    border: '#FED7AA',
    activeBg: '#C2410C',
  },
  AHA_ACC: {
    bg: '#FDF2F2',
    text: '#991B1B',
    border: '#FEE2E2',
    activeBg: '#991B1B',
  },
};

export function CitationPill({ guidelineId, section, sourceText, onClick, isActive = false }: CitationPillProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const styles = guidelineStyles[guidelineId];

  return (
    <span className="relative inline-block">
      <button
        className="inline-flex items-center rounded px-1.5 py-0.5 text-[10pt] font-bold uppercase tracking-wide transition-all cursor-pointer"
        style={{
          backgroundColor: isActive ? styles.activeBg : isHovered ? `${styles.text}1A` : styles.bg,
          color: isActive ? '#FFFFFF' : styles.text,
          border: `1px solid ${isActive ? styles.activeBg : styles.border}`,
          height: '20px',
          boxShadow: isActive ? `0 0 0 2px #3B82F6` : 'none',
        }}
        onMouseEnter={() => {
          setIsHovered(true);
          setShowTooltip(true);
        }}
        onMouseLeave={() => {
          setIsHovered(false);
          setShowTooltip(false);
        }}
        onClick={onClick}
      >
        {guidelineId} § {section}
      </button>

      {showTooltip && (
        <span className="absolute bottom-full left-1/2 z-50 mb-2 w-80 -translate-x-1/2 block">
          <span
            className="rounded-lg border-2 bg-white p-3 shadow-lg block"
            style={{ borderColor: styles.border }}
          >
            <span className="mb-1 flex items-center gap-2">
              <span
                className="rounded px-1.5 py-0.5 text-[9pt] font-bold uppercase"
                style={{
                  backgroundColor: styles.bg,
                  color: styles.text
                }}
              >
                {guidelineId}
              </span>
              <span className="text-xs text-gray-600">{section}</span>
            </span>
            <span className="text-xs text-gray-800 leading-relaxed block mt-1">"{sourceText}"</span>
          </span>
          <span
            className="mx-auto h-2 w-2 -mt-1 rotate-45 border-b-2 border-r-2 bg-white block"
            style={{ borderColor: styles.border, width: '8px' }}
          />
        </span>
      )}
    </span>
  );
}
