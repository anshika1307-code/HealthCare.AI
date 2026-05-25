import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Activity, Clock, LogOut } from 'lucide-react';

function HealthcareAILogo({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden="true">
      {/* Medical cross */}
      <rect x="6" y="1" width="4" height="14" rx="2" fill="#185FA5" />
      <rect x="1" y="6" width="14" height="4" rx="2" fill="#185FA5" />
      {/* Center AI node */}
      <circle cx="8" cy="8" r="2.2" fill="white" />
      <circle cx="8" cy="8" r="1.2" fill="#185FA5" />
    </svg>
  );
}
import { LeftRail } from '../components/LeftRail';
import { CenterPane } from '../components/CenterPane';
import { RightRail } from '../components/RightRail';
import EngineeringTab from '../components/EngineeringTab';
import MetricsTab from '../components/MetricsTab';
import AccessModal, { GoogleUser } from '../components/AccessModal';
import { useMetrics } from '../hooks/useMetrics';

interface Citation {
  guidelineId: string;
  section: string;
  guidelineName: string;
  text: string;
  color: string;
  bgColor: string;
}

const GUIDELINES_BASE = [
  {
    id: 'FDA',
    name: 'FDA',
    fullName: 'Metformin Drug Label',
    color: '#1E3A8A',
    bgColor: '#EFF6FF',
    borderColor: '#BFDBFE',
  },
  {
    id: 'ADA',
    name: 'ADA',
    fullName: 'Standards of Medical Care in Diabetes (2024)',
    color: '#15803D',
    bgColor: '#F0FDF4',
    borderColor: '#BBF7D0',
  },
  {
    id: 'JNC8',
    name: 'JNC 8',
    fullName: 'Hypertension Management Guidelines',
    color: '#0E7490',
    bgColor: '#ECFEFF',
    borderColor: '#A5F3FC',
  },
];

type ActiveTab = 'query' | 'engineering' | 'metrics';

const GUEST_LIMIT = 5;
const AUTH_LIMIT = 25;
const PRIMARY_BLUE = '#185FA5';
const GREEN = '#3B6D11';
const GREEN_BG = '#EAF3DE';
const GREEN_BORDER = '#C0DD97';

function loadStoredUser(): GoogleUser | null {
  try {
    const stored = localStorage.getItem('clinicalrag_user');
    return stored ? (JSON.parse(stored) as GoogleUser) : null;
  } catch {
    return null;
  }
}

/** Persist query count per user per calendar day — resets automatically on a new day. */
function loadQueryCount(userId: string): number {
  try {
    const raw = localStorage.getItem(`clinicalrag_qcount_${userId}`);
    if (!raw) return 0;
    const { date, count } = JSON.parse(raw) as { date: string; count: number };
    return date === new Date().toISOString().slice(0, 10) ? count : 0;
  } catch {
    return 0;
  }
}

function saveQueryCount(userId: string, count: number) {
  try {
    localStorage.setItem(
      `clinicalrag_qcount_${userId}`,
      JSON.stringify({ date: new Date().toISOString().slice(0, 10), count }),
    );
  } catch {}
}

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('query');
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [citationCounts, setCitationCounts] = useState<Record<string, number>>({
    FDA: 0, ADA: 0, JNC8: 0,
  });
  const navigate = useNavigate();
  const liveMetrics = useMetrics();
  const storedUser = loadStoredUser();
  const [queryCount, setQueryCount] = useState(
    storedUser?.id ? loadQueryCount(storedUser.id) : 0,
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [user, setUser] = useState<GoogleUser | null>(storedUser);

  const queryLimit = user ? AUTH_LIMIT : GUEST_LIMIT;
  const queriesRemaining = queryLimit - queryCount;

  // Persist count whenever it changes (signed-in users only)
  useEffect(() => {
    if (user?.id) saveQueryCount(user.id, queryCount);
  }, [user?.id, queryCount]);

  const handleSignIn = (userData: GoogleUser) => {
    setUser(userData);
    // Restore today's count for this user — don't reset to 0 (that's the loophole)
    setQueryCount(loadQueryCount(userData.id));
    localStorage.setItem('clinicalrag_user', JSON.stringify(userData));
    setModalOpen(false);
  };

  const handleSignOut = () => {
    setUser(null);
    setQueryCount(0); // guest starts fresh
    localStorage.removeItem('clinicalrag_user');
  };

  const handleCitationsChange = (citations: Citation[]) => {
    const counts: Record<string, number> = { FDA: 0, ADA: 0, JNC8: 0 };
    citations.forEach((c) => {
      const id = c.guidelineId.toUpperCase();
      if (id in counts) counts[id] = (counts[id] || 0) + 1;
    });
    setCitationCounts(counts);
  };

  const guidelines = GUIDELINES_BASE.map((g) => ({
    ...g,
    sectionsUsed: citationCounts[g.id] ?? 0,
  }));

  const tabs: { id: ActiveTab; label: string }[] = [
    { id: 'query', label: 'Query' },
    { id: 'engineering', label: 'Engineering' },
    { id: 'metrics', label: 'Metrics' },
  ];

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-white">
      {/* Top navbar */}
      <nav
        className="flex flex-shrink-0 items-center justify-between border-b px-4"
        style={{ height: 48, borderColor: '#E5E7EB' }}
      >
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 rounded px-1 py-0.5 transition-colors hover:bg-gray-50"
          aria-label="Go to home"
        >
          <HealthcareAILogo size={16} />
          <span className="text-sm font-bold" style={{ color: '#1A1A1A' }}>
            healthCare<span style={{ color: PRIMARY_BLUE }}>.AI</span>
          </span>
        </button>

        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3" style={{ color: GREEN }} />
            <span className="font-medium" style={{ color: GREEN }}>
              {liveMetrics.faithfulness.toFixed(4)}
            </span>
            <span style={{ color: '#888' }}> faithfulness</span>
          </div>
          <span style={{ color: '#D1D5DB' }}>|</span>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3 text-gray-400" />
            <span style={{ color: '#555' }}>{liveMetrics.p50ms}ms p50</span>
          </div>
          <span style={{ color: '#D1D5DB' }}>|</span>
          <div
            className="inline-flex items-center gap-1 rounded border px-2 py-0.5"
            style={{ backgroundColor: GREEN_BG, borderColor: GREEN_BORDER }}
          >
            <span className="text-[11px] font-medium" style={{ color: GREEN }}>
              ✓ CI passing
            </span>
          </div>
        </div>
      </nav>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <LeftRail guidelines={guidelines} />

        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Tab bar */}
          <div
            className="flex flex-shrink-0 items-center justify-between border-b px-4"
            style={{ borderColor: '#E5E7EB', height: 40 }}
          >
            <div className="flex items-center gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="rounded px-3 py-1 text-xs transition-colors"
                  style={
                    activeTab === tab.id
                      ? { backgroundColor: '#F3F4F6', fontWeight: 500, color: '#1A1A1A' }
                      : { color: '#555' }
                  }
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Auth / query counter area */}
            <div className="flex items-center gap-2">
              {user ? (
                <>
                  {user.picture && (
                    <img
                      src={user.picture}
                      alt={user.name}
                      className="h-5 w-5 rounded-full"
                    />
                  )}
                  <span className="text-[11px] text-gray-600">{user.name}</span>
                  <span style={{ color: '#D1D5DB' }}>·</span>
                  <span
                    className="text-[11px] font-medium"
                    style={{ color: queriesRemaining <= 3 ? '#854F0B' : '#555' }}
                  >
                    {queriesRemaining} of {AUTH_LIMIT} remaining
                  </span>
                  <button
                    onClick={handleSignOut}
                    className="flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium transition-colors hover:bg-gray-50"
                    style={{ borderColor: '#D1D5DB', color: '#555' }}
                    title="Sign out"
                  >
                    <LogOut className="h-3 w-3" />
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  <span className="text-[11px]" style={{ color: '#888' }}>
                    Guest ·{' '}
                    <span
                      style={{ color: queriesRemaining <= 1 ? '#854F0B' : '#555' }}
                      className="font-medium"
                    >
                      {queriesRemaining} of {GUEST_LIMIT} remaining
                    </span>
                  </span>
                  <button
                    className="rounded border px-2 py-0.5 text-[11px] font-medium transition-colors hover:bg-gray-50"
                    style={{ borderColor: '#D1D5DB', color: '#555' }}
                    onClick={() => setModalOpen(true)}
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Tab content — always mounted to preserve CenterPane state on tab switch */}
          <div className="flex flex-1 overflow-hidden">
            <div className={activeTab === 'query' ? 'relative flex flex-1 overflow-hidden' : 'hidden'}>
              <CenterPane
                onCitationClick={setSelectedCitation}
                activeCitation={selectedCitation}
                onCitationsChange={handleCitationsChange}
                queriesRemaining={queriesRemaining}
                queriesDisabled={queryCount >= queryLimit}
                isAuthenticated={!!user}
                userToken={user?.token}
                userId={user?.id}
                onQueryComplete={() => setQueryCount((c) => c + 1)}
                onSignInClick={() => setModalOpen(true)}
              />
              {selectedCitation && (
                <div className="absolute bottom-0 right-0 top-0 z-10 w-96 shadow-xl">
                  <RightRail
                    selectedCitation={selectedCitation}
                    onClose={() => setSelectedCitation(null)}
                  />
                </div>
              )}
            </div>
            <div className={activeTab === 'engineering' ? 'flex-1 overflow-auto' : 'hidden'}>
              <EngineeringTab />
            </div>
            <div className={activeTab === 'metrics' ? 'flex-1 overflow-auto' : 'hidden'}>
              <MetricsTab />
            </div>
          </div>
        </div>
      </div>

      <AccessModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        guestDisabled={!user && queryCount >= GUEST_LIMIT}
        onSignIn={handleSignIn}
      />
    </div>
  );
}
