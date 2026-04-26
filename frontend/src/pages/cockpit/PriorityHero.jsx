/**
 * PriorityHero — affiche la priorité unique du jour (above-the-fold).
 *
 * Logique de sélection (dans `priorityModel.buildPriority1`) :
 *   1. Sites non-conformes → critical
 *   2. Sites à risque → warn
 *   3. Alertes actives → info
 *   4. Patrimoine sous contrôle → ok
 *
 * Display-only : accepte un objet `priority` déjà construit.
 */
import { AlertTriangle, AlertCircle, Bell, CheckCircle2, ArrowRight } from 'lucide-react';
import { SEVERITY, getSeverityClasses, normalizeSeverity } from '../../ui/severity';

const ICONS = {
  [SEVERITY.CRITICAL]: AlertTriangle,
  [SEVERITY.WARN]: AlertCircle,
  [SEVERITY.INFO]: Bell,
  [SEVERITY.OK]: CheckCircle2,
};

// Pont legacy : `priorityModel.buildPriority1` retournait `type: 'warning'`
// (et non `warn`) ; on accepte les 2 le temps que tous les call-sites migrent.
function priorityToSeverity(type) {
  if (type === 'warning') return SEVERITY.WARN;
  return normalizeSeverity(type);
}

export default function PriorityHero({ priority, onNavigate }) {
  if (!priority) return null;
  const severity = priorityToSeverity(priority.type);
  const cfg = getSeverityClasses(severity);
  const Icon = ICONS[severity] ?? Bell;

  return (
    <section
      data-testid="priority-hero"
      className={`relative overflow-hidden rounded-xl border ${cfg.border} ${cfg.bg} ${cfg.accentBar} px-5 py-4 shadow-sm max-w-sol-hero`}
      aria-label="Priorité du jour"
    >
      <div className="flex items-start gap-4">
        <div
          className={`shrink-0 w-10 h-10 rounded-full bg-white border ${cfg.border} flex items-center justify-center`}
          aria-hidden="true"
        >
          <Icon size={18} className={cfg.title} />
        </div>
        <div className="flex-1 min-w-0">
          <p
            className={`text-[10px] font-semibold uppercase tracking-wider ${cfg.deadline} mb-0.5`}
          >
            Priorité du jour
          </p>
          <h2 className={`text-base sm:text-lg font-semibold ${cfg.title} leading-tight`}>
            {priority.title}
          </h2>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-sm">
            {priority.impact && (
              <span className={`font-semibold ${cfg.impact}`}>{priority.impact}</span>
            )}
            {priority.deadline && (
              <span className={`text-xs ${cfg.deadline}`}>{priority.deadline}</span>
            )}
          </div>
        </div>
        {priority.cta && (
          <button
            type="button"
            onClick={() => onNavigate?.(priority.cta.path)}
            className={`shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-semibold ${cfg.cta} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 transition-colors whitespace-nowrap`}
            aria-label={priority.cta.label}
          >
            {priority.cta.label}
            <ArrowRight size={14} aria-hidden="true" />
          </button>
        )}
      </div>
    </section>
  );
}
