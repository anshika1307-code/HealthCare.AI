import { AlertCircle, XCircle } from 'lucide-react';

interface ErrorStateProps {
  type: 'missing_section' | 'parse_error' | 'network_error' | 'no_results' | 'api_error';
  guideline?: string;
  section?: string;
  details?: string;
}

export function ErrorState({ type, guideline, section, details }: ErrorStateProps) {
  const getErrorContent = () => {
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
          description: `No results found in FDA, ADA, or JNC 8 guidelines for this query. ${details || 'The question may be outside the scope of indexed documents.'}`,
          action: 'Rephrase your query or verify it falls within the scope of the three indexed guidelines.',
        };
      case 'api_error':
        return {
          title: 'Query Processing Error',
          description: `Backend error: ${section || details || 'An unexpected error occurred while processing your query.'}`,
          action: 'Please try again. If the issue persists, verify the backend server is running at the configured API URL.',
        };
      default:
        return {
          title: 'Query Processing Error',
          description: 'An unexpected error occurred while processing your query.',
          action: 'Please try again or contact support.',
        };
    }
  };

  const error = getErrorContent();

  return (
    <div className="rounded-lg border-2 border-red-200 bg-red-50 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex-shrink-0 rounded-full bg-red-100 p-1.5">
          <XCircle className="h-4 w-4 text-red-600" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="mb-1.5 text-sm font-semibold text-red-900">{error.title}</h3>
          <p className="mb-3 break-words text-xs leading-relaxed text-red-800">{error.description}</p>
          <div className="flex items-start gap-2 rounded bg-red-100 p-2.5">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red-700" />
            <p className="text-xs text-red-700">{error.action}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
