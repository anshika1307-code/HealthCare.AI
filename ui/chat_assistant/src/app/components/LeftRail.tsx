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
    <div className="flex w-64 flex-shrink-0 flex-col border-r border-gray-200 bg-gray-50">
      <div className="flex-shrink-0 border-b border-gray-200 px-5 py-5">
        <h2 className="text-sm font-semibold text-gray-900">Active Guidelines</h2>
        <p className="mt-0.5 text-xs text-gray-500">Indexed source frameworks</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="space-y-2.5">
          {guidelines.map((guideline) => (
            <div
              key={guideline.id}
              className="rounded-lg border bg-white p-3.5 transition-shadow hover:shadow-sm"
              style={{ borderColor: guideline.borderColor }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="mt-0.5 flex-shrink-0 rounded p-1.5"
                  style={{ backgroundColor: guideline.bgColor }}
                >
                  <FileText className="h-3.5 w-3.5" style={{ color: guideline.color }} />
                </div>
                <div className="min-w-0 flex-1">
                  <span
                    className="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest"
                    style={{ backgroundColor: guideline.bgColor, color: guideline.color }}
                  >
                    {guideline.id}
                  </span>
                  <p className="mt-1.5 text-[11px] leading-snug text-gray-600">{guideline.fullName}</p>
                  <div className="mt-2 flex items-center gap-1.5">
                    <div
                      className="h-1.5 w-1.5 flex-shrink-0 rounded-full"
                      style={{ backgroundColor: guideline.sectionsUsed > 0 ? guideline.color : '#D1D5DB' }}
                    />
                    <span className="text-[10px] text-gray-500">
                      {guideline.sectionsUsed > 0
                        ? `${guideline.sectionsUsed} ${guideline.sectionsUsed === 1 ? 'section' : 'sections'} cited`
                        : 'Available'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-shrink-0 border-t border-gray-200 px-4 py-4">
        <div className="rounded-lg bg-gray-100 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Scope Limitation</p>
          <p className="mt-1.5 text-[10px] leading-relaxed text-gray-500">
            Answers are strictly sourced from indexed guidelines. No internet search or general knowledge is used.
          </p>
        </div>
      </div>
    </div>
  );
}
