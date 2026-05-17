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
      <div className="w-96 border-l border-gray-200 bg-white">
        <div className="border-b border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-gray-600" />
              <h3 className="font-semibold text-gray-900">Document Comparison Mode</h3>
            </div>
            <button
              onClick={onClose}
              className="rounded p-1 hover:bg-gray-200 transition-colors"
            >
              <X className="h-4 w-4 text-gray-600" />
            </button>
          </div>
        </div>

        <div className="p-4">
          <div className="space-y-4">
            <div className="rounded-lg border-2 p-4" style={{ borderColor: comparisonMode.citation1.color }}>
              <div className="mb-2 flex items-center gap-2">
                <span
                  className="rounded px-2 py-1 text-xs font-bold uppercase"
                  style={{
                    backgroundColor: comparisonMode.citation1.bgColor,
                    color: comparisonMode.citation1.color
                  }}
                >
                  {comparisonMode.citation1.guidelineId}
                </span>
                <span className="text-xs text-gray-600">{comparisonMode.citation1.section}</span>
              </div>
              <p className="text-sm text-gray-800 leading-relaxed">"{comparisonMode.citation1.text}"</p>
              <button
                className="mt-3 w-full rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 transition-colors"
              >
                Adopt {comparisonMode.citation1.guidelineId} Metric
              </button>
            </div>

            <div className="rounded-lg border-2 p-4" style={{ borderColor: comparisonMode.citation2.color }}>
              <div className="mb-2 flex items-center gap-2">
                <span
                  className="rounded px-2 py-1 text-xs font-bold uppercase"
                  style={{
                    backgroundColor: comparisonMode.citation2.bgColor,
                    color: comparisonMode.citation2.color
                  }}
                >
                  {comparisonMode.citation2.guidelineId}
                </span>
                <span className="text-xs text-gray-600">{comparisonMode.citation2.section}</span>
              </div>
              <p className="text-sm text-gray-800 leading-relaxed">"{comparisonMode.citation2.text}"</p>
              <button
                className="mt-3 w-full rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 transition-colors"
              >
                Adopt {comparisonMode.citation2.guidelineId} Metric
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!selectedCitation) {
    return (
      <div className="w-96 border-l border-gray-200 bg-gray-50 p-6">
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-4 text-sm text-gray-600">
              Click a citation to view source text
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-96 border-l border-gray-200 bg-white">
      <div className="border-b border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-gray-600" />
            <h3 className="font-semibold text-gray-900">Evidence Vault</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-gray-200 transition-colors"
          >
            <X className="h-4 w-4 text-gray-600" />
          </button>
        </div>
      </div>

      <div className="p-4">
        <div className="rounded-lg border-2 p-4" style={{ borderColor: selectedCitation.color }}>
          <div className="mb-3 flex items-center gap-2">
            <span
              className="rounded px-2 py-1 text-xs font-bold uppercase"
              style={{
                backgroundColor: selectedCitation.bgColor,
                color: selectedCitation.color
              }}
            >
              {selectedCitation.guidelineId}
            </span>
            <span className="text-xs text-gray-600">{selectedCitation.section}</span>
          </div>

          <h4 className="mb-2 text-sm font-semibold text-gray-900">{selectedCitation.guidelineName}</h4>

          <div className="rounded bg-gray-50 p-3">
            <p className="text-sm text-gray-800 leading-relaxed">"{selectedCitation.text}"</p>
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
