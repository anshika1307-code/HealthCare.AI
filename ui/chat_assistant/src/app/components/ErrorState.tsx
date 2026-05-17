import { AlertCircle, XCircle } from 'lucide-react';

interface ErrorStateProps {
  type: 'missing_section' | 'parse_error' | 'network_error' | 'no_results';
  guideline?: string;
  section?: string;
  details?: string;
}

export function ErrorState({ type, guideline, section, details }: ErrorStateProps) {
  const getErrorMessage = () => {
    switch (type) {
      case 'missing_section':
        return {
          title: 'Section Not Found in Guideline Index',
          description: `Error: Section ${section} missing from ${guideline} index. This section may have been removed or renumbered in the latest guideline update.`,
          action: 'Try rephrasing your query or verify the section number in the source document.',
        };
      case 'parse_error':
        return {
          title: 'Unable to Parse Guideline Text',
          description: `Error: Failed to extract structured data from ${guideline}. The document format may have changed or contains unexpected formatting.`,
          action: 'This query cannot be processed. Contact system administrator if issue persists.',
        };
      case 'network_error':
        return {
          title: 'Connection to Guideline Database Failed',
          description: 'Error: Network timeout while accessing indexed guidelines. Local database connection unavailable.',
          action: 'Check network connection and retry query.',
        };
      case 'no_results':
        return {
          title: 'No Matching Guidelines Found',
          description: `No results found in FDA, ADA, JNC 8, or AHA/ACC guidelines for this query. ${details || 'The question may be outside the scope of indexed documents.'}`,
          action: 'Rephrase your query or verify it falls within the scope of the four indexed guidelines.',
        };
      default:
        return {
          title: 'Query Processing Error',
          description: 'An unexpected error occurred while processing your query.',
          action: 'Please try again or contact support.',
        };
    }
  };

  const error = getErrorMessage();

  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-lg border-2 border-red-200 bg-red-50 p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-full bg-red-100 p-2">
            <XCircle className="h-5 w-5 text-red-600" />
          </div>
          <div className="flex-1">
            <h3 className="mb-2 font-semibold text-red-900">{error.title}</h3>
            <p className="mb-3 text-sm text-red-800 leading-relaxed">{error.description}</p>
            <div className="flex items-start gap-2 rounded bg-red-100 p-3">
              <AlertCircle className="h-4 w-4 text-red-700 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700">{error.action}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
