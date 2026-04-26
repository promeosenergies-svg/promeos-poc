/**
 * priorityModel — dérive la "priorité #1" du jour pour le PriorityHero.
 *
 * RÈGLE : pas d'appel API, pas de side-effect. Pure function depuis kpis +
 * nextDeadline + alertsCount déjà résolus côté hook.
 *
 * Usage : <PriorityHero priority={buildPriority1({...})} />
 */
import { toActionsList } from '../services/routes';

function formatDeadlineDate(isoStr) {
  if (!isoStr) return null;
  try {
    return new Date(isoStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}

/**
 * Construit l'objet priority1 (priorité unique à afficher en haut de page).
 *
 * @param {Object} args
 * @param {Object} args.kpis — { nonConformes, aRisque, risqueTotal }
 * @param {Object} args.nextDeadline — { deadline, label, days_remaining }
 * @param {number} args.alertsCount
 * @returns {{ type, title, impact, deadline, cta }}
 */
export function buildPriority1({ kpis, nextDeadline, alertsCount }) {
  const k = kpis ?? {};
  const nbNonConformes = k.nonConformes ?? 0;
  const nbARisque = k.aRisque ?? 0;
  const risqueEur = k.risqueTotal ?? 0;
  const expositionLabel = risqueEur > 0 ? `${Math.round(risqueEur / 1000)} k€ d'exposition` : null;

  if (nbNonConformes > 0) {
    return {
      type: 'critical',
      title: `${nbNonConformes} site${nbNonConformes > 1 ? 's' : ''} non conforme${nbNonConformes > 1 ? 's' : ''} — mise en conformité requise`,
      impact: expositionLabel,
      deadline: nextDeadline ? `Échéance : ${formatDeadlineDate(nextDeadline.deadline)}` : null,
      cta: { label: 'Ouvrir conformité', path: '/conformite' },
    };
  }

  if (nbARisque > 0) {
    return {
      type: 'warning',
      title: `${nbARisque} site${nbARisque > 1 ? 's' : ''} à risque réglementaire`,
      impact: expositionLabel,
      deadline: nextDeadline?.label
        ? `Prochaine échéance : ${nextDeadline.label} (J-${nextDeadline.days_remaining})`
        : null,
      cta: { label: "Voir le plan d'action", path: toActionsList() },
    };
  }

  if ((alertsCount ?? 0) > 0) {
    return {
      type: 'info',
      title: `${alertsCount} alerte${alertsCount > 1 ? 's' : ''} active${alertsCount > 1 ? 's' : ''} à traiter`,
      impact: null,
      deadline: null,
      cta: { label: 'Traiter les alertes', path: '/notifications' },
    };
  }

  return {
    type: 'ok',
    title: 'Aucun écart réglementaire détecté',
    impact: null,
    deadline: 'Décret Tertiaire et BACS évalués',
    cta: { label: 'Voir le détail conformité', path: '/conformite' },
  };
}
