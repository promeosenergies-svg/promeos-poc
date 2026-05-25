/**
 * ConformiteSyntheseCompacte — P2-A simplification visuelle (2026-05-25).
 *
 * Above-the-fold : 4 cartes max pour DAF/DG en 30 secondes :
 *   1. Score conformité (avec tooltip formule + confiance + périmètre clair)
 *   2. Prochaine échéance (date + jours + obligation + sites concernés)
 *   3. Actions prioritaires (count + CTA unique « Voir le plan »)
 *   4. Données / preuves manquantes (count + CTA « Compléter »)
 *
 * Doctrine §8.1 (zero business logic FE) : tous les nombres viennent du
 * backend. Le composant n'effectue qu'un format présentation (texte FR).
 * Doctrine §6.2 (hub unique) : aucune navigation vers un nouvel écran.
 */
import React from 'react';
import { ShieldCheck, CalendarClock, ListChecks, FileText, ArrowRight } from 'lucide-react';
import { Explain } from '../../ui';

function formatEuros(value) {
  if (typeof value !== 'number' || Number.isNaN(value) || value <= 0) return null;
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(value) + ' €';
}

function formatFrenchDate(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function Card({ icon: Icon, title, children, testid }) {
  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 flex flex-col gap-2 min-h-[120px]"
      data-testid={testid}
    >
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-gray-500">
        <Icon size={14} className="text-gray-400" aria-hidden="true" />
        {title}
      </div>
      <div className="flex-1 flex flex-col justify-between gap-2">{children}</div>
    </div>
  );
}

/**
 * @param {object} props
 * @param {{ pct: number|null, pct_confidence: string|null, total_impact_eur: number|null }} props.score
 * @param {{ deadline?: string, days_remaining?: number, label?: string }|null} props.nextDeadline
 *   — issu de `/api/compliance/timeline.next_deadline` (SoT backend canonique).
 * @param {number} props.actionsCount — `actionableFindings.length`.
 * @param {number} props.proofsMissingCount — obligations sans preuve déposée.
 * @param {number} props.sitesEvalues — nombre de sites dans le scope actif.
 * @param {number} props.sitesPerimetre — nombre total de sites du périmètre parent (org/portefeuille).
 * @param {(tab: string) => void} props.onOpenTab — bascule onglet workflow interne.
 */
export default function ConformiteSyntheseCompacte({
  score,
  nextDeadline,
  actionsCount = 0,
  proofsMissingCount = 0,
  sitesEvalues = 0,
  sitesPerimetre = 0,
  onOpenTab,
}) {
  // 1. Score conformité
  const scoreNum = score?.pct;
  const scoreDisplay = scoreNum == null ? '—' : Math.round(scoreNum);
  const scoreColor =
    scoreNum == null
      ? 'text-gray-400'
      : scoreNum >= 70
        ? 'text-emerald-600'
        : scoreNum >= 50
          ? 'text-amber-600'
          : 'text-red-600';
  const scoreSubtitle =
    scoreNum == null
      ? 'Données à compléter pour fiabiliser le score'
      : scoreNum < 50
        ? `Score faible — ${actionsCount} action${actionsCount > 1 ? 's' : ''} prioritaire${actionsCount > 1 ? 's' : ''} à traiter`
        : scoreNum < 70
          ? 'Score moyen — quelques obligations à fiabiliser'
          : 'Score satisfaisant — maintenir le suivi';

  // 2. Prochaine échéance
  const nextDate = formatFrenchDate(nextDeadline?.deadline);
  const nextDays =
    typeof nextDeadline?.days_remaining === 'number' ? nextDeadline.days_remaining : null;
  const nextLabel = nextDeadline?.label || null;

  // 3. Pénalité (encart sous le score, ou message « à qualifier »)
  const penaltyDisplay = formatEuros(score?.total_impact_eur);

  // 4. Périmètre sites — clarifie le 5/13 historiquement ambigu
  const perimetreLabel =
    sitesEvalues > 0 && sitesPerimetre > 0 && sitesEvalues !== sitesPerimetre
      ? `${sitesEvalues} site${sitesEvalues > 1 ? 's' : ''} évalué${sitesEvalues > 1 ? 's' : ''} sur ${sitesPerimetre} dans le périmètre`
      : sitesEvalues > 0
        ? `${sitesEvalues} site${sitesEvalues > 1 ? 's' : ''} dans le périmètre`
        : null;

  return (
    <section
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4"
      data-testid="conformite-synthese-compacte"
      aria-label="Synthèse Conformité"
    >
      {/* Carte 1 — Score conformité */}
      <Card icon={ShieldCheck} title="Score conformité" testid="synthese-card-score">
        <div className="flex items-baseline gap-1.5">
          <span className={`text-3xl font-bold ${scoreColor}`}>{scoreDisplay}</span>
          <span className="text-sm text-gray-400">/100</span>
        </div>
        <p className="text-xs text-gray-600">{scoreSubtitle}</p>
        {perimetreLabel && (
          <p className="text-[11px] text-gray-400" data-testid="synthese-perimetre">
            {perimetreLabel}
          </p>
        )}
      </Card>

      {/* Carte 2 — Prochaine échéance */}
      <Card icon={CalendarClock} title="Prochaine échéance" testid="synthese-card-echeance">
        {nextDate ? (
          <>
            <div>
              <div className="text-lg font-semibold text-gray-900">{nextDate}</div>
              {nextDays != null && (
                <div className="text-xs text-gray-500">
                  dans {nextDays} jour{nextDays > 1 ? 's' : ''}
                </div>
              )}
            </div>
            {nextLabel && <p className="text-xs text-gray-600 line-clamp-2">{nextLabel}</p>}
          </>
        ) : (
          <p className="text-sm text-gray-500">Aucune échéance proche dans les 12 mois</p>
        )}
      </Card>

      {/* Carte 3 — Actions prioritaires */}
      <Card icon={ListChecks} title="Actions prioritaires" testid="synthese-card-actions">
        <div>
          <div className="text-3xl font-bold text-gray-900">{actionsCount}</div>
          <p className="text-xs text-gray-600">
            {actionsCount === 0
              ? 'Aucune action requise pour le moment'
              : `Action${actionsCount > 1 ? 's' : ''} requise${actionsCount > 1 ? 's' : ''}`}
          </p>
        </div>
        {actionsCount > 0 && onOpenTab && (
          <button
            type="button"
            onClick={() => onOpenTab('execution')}
            className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800"
            data-testid="synthese-cta-actions"
          >
            Voir le plan <ArrowRight size={12} aria-hidden="true" />
          </button>
        )}
      </Card>

      {/* Carte 4 — Preuves manquantes (+ risque financier si calculé) */}
      <Card icon={FileText} title="Preuves manquantes" testid="synthese-card-preuves">
        <div>
          <div className="text-3xl font-bold text-gray-900">{proofsMissingCount}</div>
          <p className="text-xs text-gray-600">
            {proofsMissingCount === 0
              ? 'Toutes les preuves attendues sont déposées'
              : `Document${proofsMissingCount > 1 ? 's' : ''} attendu${proofsMissingCount > 1 ? 's' : ''}`}
          </p>
        </div>
        <div className="flex items-center justify-between gap-2">
          {/* Risque financier — toujours visible, qualifié si non calculé */}
          <span className="text-[11px] text-gray-500" data-testid="synthese-risque">
            Risque financier&nbsp;:{' '}
            {penaltyDisplay ? (
              <strong className="text-amber-700">{penaltyDisplay}</strong>
            ) : (
              <Explain term="penalty_exposure">à qualifier</Explain>
            )}
          </span>
          {proofsMissingCount > 0 && onOpenTab && (
            <button
              type="button"
              onClick={() => onOpenTab('preuves')}
              className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800"
              data-testid="synthese-cta-preuves"
            >
              Compléter <ArrowRight size={12} aria-hidden="true" />
            </button>
          )}
        </div>
      </Card>
    </section>
  );
}
