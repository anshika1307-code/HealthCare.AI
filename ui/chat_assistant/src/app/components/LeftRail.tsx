import { FileText } from 'lucide-react';

interface Guideline {
  id: string;
  name: string;
  fullName: string;
  color: string;
  bgColor: string;
  borderColor: string;
  sectionsUsed: number;
}

interface LeftRailProps {
  guidelines: Guideline[];
}

export function LeftRail({ guidelines }: LeftRailProps) {
  return (
    <div className="w-72 border-r border-gray-200 bg-gray-50 p-6">
      <div className="mb-6">
        <h2 className="mb-1 text-gray-900">Active Guidelines</h2>
        <p className="text-sm text-gray-600">Source frameworks for evidence retrieval</p>
      </div>

      <div className="space-y-3">
        {guidelines.map((guideline) => (
          <div
            key={guideline.id}
            className="rounded-lg border-2 bg-white p-4 transition-all hover:shadow-sm"
            style={{ borderColor: guideline.borderColor }}
          >
            <div className="flex items-start gap-3">
              <div
                className="rounded p-1.5"
                style={{ backgroundColor: guideline.bgColor }}
              >
                <FileText className="h-4 w-4" style={{ color: guideline.color }} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className="rounded px-2 py-0.5 text-xs font-bold uppercase tracking-wide"
                    style={{
                      backgroundColor: guideline.bgColor,
                      color: guideline.color
                    }}
                  >
                    {guideline.id}
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-700 leading-tight">{guideline.fullName}</p>
                <div className="mt-2 flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: guideline.color }} />
                  <span className="text-xs text-gray-600">
                    {guideline.sectionsUsed} {guideline.sectionsUsed === 1 ? 'section' : 'sections'} cited
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-lg bg-gray-100 p-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-700">Scope Limitation</h3>
        <p className="text-xs text-gray-600 leading-relaxed">
          Answers are strictly sourced from indexed guidelines. System does not use internet search or general knowledge.
        </p>
      </div>
    </div>
  );
}
