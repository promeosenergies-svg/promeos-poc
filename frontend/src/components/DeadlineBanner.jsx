import React, { useState, useEffect } from 'react';
import { AlertTriangle, X, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useScope } from '../contexts/ScopeContext';
import { getAuditDeadlineStatus } from '../services/api/conformite';

const DISMISS_KEY = 'promeos.audit_sme_deadline_dismissed';

const URGENCY_STYLES = {
  critical: 'bg-red-50 border-red-200 text-red-800',
  high: 'bg-orange-50 border-orange-200 text-orange-800',
  medium: 'bg-amber-50 border-amber-200 text-amber-800',
};

export default function DeadlineBanner() {
  const { org } = useScope();
  const [status, setStatus] = useState(null);
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(DISMISS_KEY) === 'true');
  const navigate = useNavigate();

  useEffect(() => {
    if (dismissed || !org?.id) return;
    getAuditDeadlineStatus(org.id)
      .then(setStatus)
      .catch(() => {});
  }, [org?.id, dismissed]);

  if (dismissed || !status?.show_banner) return null;

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, 'true');
    setDismissed(true);
  };

  return (
    <div
      className={`border rounded-lg px-4 py-3 flex items-center gap-3 w-fit max-w-sol-strip ${URGENCY_STYLES[status.urgency] || URGENCY_STYLES.medium}`}
    >
      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
      <span className="text-sm flex-1">
        <strong>Audit Energetique obligatoire dans {status.days_remaining} jours</strong>
        {' — '}
        Obligation : {status.obligation === 'AUDIT_4ANS' ? 'Audit 4 ans' : 'SME ISO 50001'}
        {status.estimated_penalty_eur > 0 &&
          ` — risque ${status.estimated_penalty_eur.toLocaleString('fr-FR')} \u20AC`}
      </span>
      <button
        onClick={() => navigate('/conformite?tab=audit-sme')}
        className="flex items-center gap-1 text-sm font-medium underline flex-shrink-0"
      >
        Evaluer <ArrowRight className="h-3 w-3" />
      </button>
      <button
        onClick={handleDismiss}
        className="ml-2 opacity-60 hover:opacity-100"
        aria-label="Fermer le bandeau"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
