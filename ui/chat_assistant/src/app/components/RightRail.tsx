import { X, FileText } from 'lucide-react';

interface Citation {
  guidelineId: string;
  guidelineName: string;
  section: string;
  text: string;
  color: string;
  bgColor: string;
}

interface RightRailProps {
  selectedCitation: Citation | null;
  onClose: () => void;
  comparisonMode?: {
    citation1: Citation;
    citation2: Citation;
  } | null;
}

export function RightRail({ selectedCitation, onClose, comparisonMode }: RightRailProps) {
  if (comparisonMode) {
    return (
      <div className="flex h-full w-96 flex-col border-l border-gray-200 bg-white">
        <div className="flex-shrink-0 border-b border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-gray-600" />
              <h3 className="text-sm font-semibold text-gray-900">Document Comparison</h3>
            </div>
            <button onClick={onClose} className="rounded p-1 transition-colors hover:bg-gray-200">
              <X className="h-4 w-4 text-gray-600" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            {[comparisonMode.citation1, comparisonMode.citation2].map((c, i) => (
              <div key={i} className="rounded-lg border-2 p-4" style={{ borderColor: c.color }}>
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className="rounded px-2 py-1 text-xs font-bold uppercase"
                    style={{ backgroundColor: c.bgColor, color: c.color }}
                  >
                    {c.guidelineId}
                  </span>
                  <span className="text-xs text-gray-600">{c.section}</span>
                </div>
                <p className="break-words text-sm leading-relaxed text-gray-800">"{c.text}"</p>
                <button className="mt-3 w-full rounded bg-green-600 px-4 py-2 text-sm text-white transition-colors hover:bg-green-700">
                  Adopt {c.guidelineId} Metric
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!selectedCitation) {
    return (
      <div className="flex h-full w-96 flex-col border-l border-gray-200 bg-gray-50">
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-4 text-sm text-gray-600">Click a citation to view source text</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full w-96 flex-col border-l border-gray-200 bg-white">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-gray-600" />
            <h3 className="text-sm font-semibold text-gray-900">Evidence Vault</h3>
          </div>
          <button onClick={onClose} className="rounded p-1 transition-colors hover:bg-gray-200">
            <X className="h-4 w-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="rounded-lg border-2 p-4" style={{ borderColor: selectedCitation.color }}>
          {/* Badge + section */}
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span
              className="rounded px-2 py-1 text-xs font-bold uppercase"
              style={{ backgroundColor: selectedCitation.bgColor, color: selectedCitation.color }}
            >
              {selectedCitation.guidelineId}
            </span>
            <span className="min-w-0 break-words text-xs text-gray-600">
              {selectedCitation.section}
            </span>
          </div>

          {/* Guideline name */}
          <h4 className="mb-3 break-words text-sm font-semibold text-gray-900">
            {selectedCitation.guidelineName}
          </h4>

          {/* Source text — scrollable if very long */}
          <div className="rounded bg-gray-50 p-3">
            <p className="break-words text-sm leading-relaxed text-gray-800">
              "{selectedCitation.text}"
            </p>
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
            <div className="h-1 w-1 rounded-full bg-green-500" />
            <span>Verified Source Text</span>
          </div>
        </div>
      </div>
    </div>
  );
}
