import { useNavigate } from 'react-router-dom';
import { Home } from 'lucide-react';
import { Button, EmptyState } from '../ui';

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="px-6 py-6">
      <EmptyState
        icon={Home}
        title="Page introuvable"
        text="La page que vous cherchez n'existe pas ou a ete deplacee."
        ctaLabel="Retour au Command Center"
        onCta={() => navigate('/')}
      />
    </div>
  );
}
