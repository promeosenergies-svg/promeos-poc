/**
 * ComplianceSummaryBanner — Bandeau unifié 3 états (vert / orange / rouge).
 *
 * S2 simplicité (2026-05-28) — dédoublonné :
 * - Suppression du Top 3 urgences (déjà rendu par ObligationsTab + chips
 *   réglementaires + ConformiteSyntheseCompacte carte 3 « Actions »).
 * - Suppression du résumé exécutif (déjà rendu par ConformiteSyntheseCompacte
 *   cartes 1+2+3 lisibles en 30 s).
 * - Suppression du RiskBadge (déjà rendu par carte 4 « Preuves manquantes /
 *   Risque financier » — évite la triple lecture du même chiffre).
 * - Un seul CTA primaire par état (anti-paradoxe du choix DAF).
 *
 * États (mutuellement exclusifs) :
 *   - vert  : pct >= 70 et 0 non conforme → « Conforme · suivi à jour »
 *   - orange : sinon, par défaut (données ou preuves à compléter)
 *   - rouge : pct < 40 OU au moins 1 site non conforme
 *
 * Doctrine §6.2 hub unique : un seul bandeau, un seul état affiché.
 */
import { ShieldCheck, ArrowRight, CalendarClock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from '../../ui';

const STATE_CONFIG = {
  green: {
    bg: 'bg-green-50 border-green-200',
    iconColor: 'text-green-600',
    textColor: 'text-green-800',
    Icon: CheckCircle2,
    title: 'Conformité à jour',
    body: 'Aucun écart bloquant sur le périmètre. Continuez à suivre les échéances à venir.',
    cta: null,
  },
  amber: {
    bg: 'bg-amber-50 border-amber-200',
    iconColor: 'text-amber-600',
    textColor: 'text-amber-800',
    Icon: ShieldCheck,
    title: 'Données ou preuves à compléter',
    body: 'Certaines obligations sont à qualifier ou attendent une preuve pour fiabiliser le score.',
    cta: {
      label: 'Préparer les échéances',
      testid: 'cta-preparer-echeances',
      target: '/conformite?tab=obligations',
    },
  },
  red: {
    bg: 'bg-red-50 border-red-200',
    iconColor: 'text-red-600',
    textColor: 'text-red-800',
    Icon: AlertTriangle,
    title: 'Action réglementaire urgente',
    body: 'Au moins une obligation est en non-conformité. Traitez le plan d’action prioritaire.',
    cta: {
      label: "Voir le plan d'action",
      testid: 'cta-plan-action',
      target: '/action-center-v4?domain=conformite',
    },
  },
};

function deriveState({ pct, nonConformes }) {
  if (pct == null) return 'amber';
  if (pct < 40 || nonConformes > 0) return 'red';
  if (pct >= 70 && nonConformes === 0) return 'green';
  return 'amber';
}

export default function ComplianceSummaryBanner({ score, timeline, navigate }) {
  const pct = score?.pct ?? null;
  const nonConformes = score?.non_conformes ?? 0;
  const state = deriveState({ pct, nonConformes });
  const cfg = STATE_CONFIG[state];
  const Icon = cfg.Icon;
  const nextDeadline = timeline?.next_deadline || null;

  return (
    <div
      data-testid="compliance-summary-banner"
      data-state={state}
      className={`p-4 border rounded-lg ${cfg.bg}`}
    >
      <div className="flex items-start gap-3">
        <Icon size={20} className={`${cfg.iconColor} mt-0.5 shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold ${cfg.textColor}`}>{cfg.title}</p>
          <p className="text-xs mt-0.5 text-gray-700">{cfg.body}</p>
          {nextDeadline && (
            <p
              className="text-xs mt-1.5 flex items-center gap-1 text-gray-600"
              data-testid="next-deadline"
            >
              <CalendarClock size={12} />
              Prochaine échéance : {nextDeadline.label || nextDeadline.regulation} —{' '}
              {new Date(nextDeadline.deadline).toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
              {nextDeadline.days_remaining != null && (
                <span
                  className={nextDeadline.days_remaining <= 30 ? 'font-semibold text-red-600' : ''}
                >
                  {' '}
                  (dans {nextDeadline.days_remaining} jour
                  {nextDeadline.days_remaining > 1 ? 's' : ''})
                </span>
              )}
            </p>
          )}
        </div>
        {cfg.cta && (
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => navigate(cfg.cta.target)}
              data-testid={cfg.cta.testid}
            >
              {cfg.cta.label} <ArrowRight size={14} />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
