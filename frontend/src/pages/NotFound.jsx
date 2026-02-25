import { useNavigate, useLocation } from 'react-router-dom';
import { Home } from 'lucide-react';
import { Button, EmptyState } from '../ui';
import { useExpertMode } from '../contexts/ExpertModeContext';

export default function NotFound() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { isExpert } = useExpertMode();

  return (
    <div className="px-6 py-6">
      <EmptyState
        icon={Home}
        title="Page introuvable"
        text={`La page « ${pathname} » n'existe pas ou a été déplacée.`}
        ctaLabel="Retour au Command Center"
        onCta={() => navigate('/')}
      />
      {isExpert && (
        <p className="text-xs text-gray-400 text-center mt-4">
          Route : {pathname} — {new Date().toISOString()}
        </p>
      )}
    </div>
  );
}
