import { useNavigate } from 'react-router';
import * as Dialog from '@radix-ui/react-dialog';
import { MessageCircle, Clock, Lock, X } from 'lucide-react';

interface AccessModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Minimal inline Google "G" icon SVG
function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M44.5 20H24v8.5h11.7C34.2 33.2 29.6 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c2.9 0 5.5 1 7.5 2.7l6.4-6.4C34.4 5.1 29.5 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21c10.8 0 20.2-7.8 20.2-21 0-1.4-.1-2.7-.3-4z"
      />
      <path fill="#34A853" d="M6.3 14.7l7 5.1C14.9 16 19.1 13 24 13c2.9 0 5.5 1 7.5 2.7l6.4-6.4C34.4 5.1 29.5 3 24 3c-7.7 0-14.4 4.3-17.7 11.7z" />
      <path fill="#FBBC05" d="M24 45c5.4 0 10.3-1.9 14.1-5.1l-6.5-5.3C29.7 36 27 37 24 37c-5.6 0-10.2-3.8-11.7-8.9l-7 5.4C8.5 41.2 15.8 45 24 45z" />
      <path fill="#EA4335" d="M44.5 20H24v8.5h11.7c-.9 2.7-2.7 4.9-5.1 6.4l6.5 5.3C41.5 37.3 45 31 45 24c0-1.4-.1-2.7-.3-4z" />
    </svg>
  );
}

export default function AccessModal({ open, onOpenChange }: AccessModalProps) {
  const navigate = useNavigate();

  const handleGoogleSignIn = () => {
    alert('Google sign-in coming soon.');
  };

  const handleGuestAccess = () => {
    onOpenChange(false);
    navigate('/chat');
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        {/* Overlay */}
        <Dialog.Overlay
          className="fixed inset-0 z-40 bg-black/40"
          style={{ backdropFilter: 'blur(2px)' }}
        />

        {/* Content */}
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-white p-6 shadow-lg"
          style={{ borderColor: '#E5E7EB' }}
        >
          {/* Close button */}
          <Dialog.Close asChild>
            <button
              className="absolute right-3 top-3 rounded p-1 transition-colors hover:bg-gray-100"
              aria-label="Close"
            >
              <X className="h-4 w-4 text-gray-400" />
            </button>
          </Dialog.Close>

          {/* Title */}
          <Dialog.Title className="mb-1 text-base font-semibold text-gray-900">
            Access ClinicalRAG
          </Dialog.Title>

          {/* Subtitle */}
          <Dialog.Description className="mb-5 text-xs leading-relaxed text-gray-500">
            Sign in for 25 queries/day and saved history, or try as a guest with 5 queries.
          </Dialog.Description>

          {/* Google sign-in button */}
          <button
            onClick={handleGoogleSignIn}
            className="mb-3 flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB' }}
          >
            <GoogleIcon />
            Continue with Google
          </button>

          {/* Divider */}
          <div className="mb-3 flex items-center gap-2">
            <div className="flex-1 border-t" style={{ borderColor: '#E5E7EB' }} />
            <span className="text-[11px] text-gray-400">or</span>
            <div className="flex-1 border-t" style={{ borderColor: '#E5E7EB' }} />
          </div>

          {/* Guest button */}
          <button
            onClick={handleGuestAccess}
            className="mb-4 w-full rounded-lg border px-4 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB' }}
          >
            Continue as guest
          </button>

          {/* Guest limits card */}
          <div
            className="rounded-lg border p-3"
            style={{ backgroundColor: '#F9FAFB', borderColor: '#E5E7EB' }}
          >
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-gray-400">
              Guest access
            </p>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-3 w-3 flex-shrink-0 text-gray-400" />
                <span className="text-[11px] text-gray-500">5 queries</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-3 w-3 flex-shrink-0 text-gray-400" />
                <span className="text-[11px] text-gray-500">no history</span>
              </div>
              <div className="flex items-center gap-2">
                <Lock className="h-3 w-3 flex-shrink-0 text-gray-400" />
                <span className="text-[11px] text-gray-500">rate-limited server-side</span>
              </div>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
