import { useState } from 'react';

interface CitationPillProps {
  guidelineId: string;
  section: string;
  sourceText: string;
  onClick: () => void;
  isActive?: boolean;
}

const GUIDELINE_STYLES: Record<string, { bg: string; text: string; border: string; activeBg: string }> = {
  FDA:  { bg: '#EFF6FF', text: '#1E3A8A', border: '#BFDBFE', activeBg: '#1E3A8A' },
  ADA:  { bg: '#F0FDF4', text: '#15803D', border: '#BBF7D0', activeBg: '#15803D' },
  JNC8: { bg: '#ECFEFF', text: '#0E7490', border: '#A5F3FC', activeBg: '#0E7490' },
};

const DEFAULT_STYLE = { bg: '#F1F5F9', text: '#475569', border: '#CBD5E1', activeBg: '#475569' };

export function CitationPill({ guidelineId, section, sourceText, onClick, isActive = false }: CitationPillProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const styles = GUIDELINE_STYLES[guidelineId] ?? DEFAULT_STYLE;

  return (
    <span className="relative inline-block">
      <button
        className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide transition-all cursor-pointer"
        style={{
          backgroundColor: isActive ? styles.activeBg : isHovered ? `${styles.text}18` : styles.bg,
          color:            isActive ? '#FFFFFF' : styles.text,
          border:           `1px solid ${isActive ? styles.activeBg : styles.border}`,
          boxShadow:        isActive ? `0 0 0 2px ${styles.activeBg}30` : 'none',
        }}
        onMouseEnter={() => { setIsHovered(true); setShowTooltip(true); }}
        onMouseLeave={() => { setIsHovered(false); setShowTooltip(false); }}
        onClick={onClick}
      >
        {guidelineId} § {section}
      </button>

      {showTooltip && (
        <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-72 -translate-x-1/2 block">
          <span
            className="block rounded-lg border bg-white p-3 shadow-xl"
            style={{ borderColor: styles.border }}
          >
            <span className="mb-1.5 flex items-center gap-2">
              <span
                className="flex-shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase"
                style={{ backgroundColor: styles.bg, color: styles.text }}
              >
                {guidelineId}
              </span>
              <span className="min-w-0 break-words text-xs font-medium text-gray-500">{section}</span>
            </span>
            <span className="mt-1 block break-words text-xs leading-relaxed text-gray-700">
              "{sourceText.length > 200 ? sourceText.slice(0, 200) + '…' : sourceText}"
            </span>
          </span>
          {/* Caret */}
          <span
            className="mx-auto block h-2 w-2 -mt-1 rotate-45 border-b border-r bg-white"
            style={{ borderColor: styles.border }}
          />
        </span>
      )}
    </span>
  );
}
