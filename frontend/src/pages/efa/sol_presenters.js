/**
 * PROMEOS — EfaSol presenters (Lot 3 Phase 4)
 *
 * Helpers purs pour EfaSol (fiche EFA Décret Tertiaire en Pattern C).
 *
 * API consommée (parent TertiaireEfaDetailPage.jsx) :
 *   getTertiaireEfa(id) → {
 *     id, nom, statut ('active'|'closed'|'draft'),
 *     role_assujetti ('proprietaire'|'locataire'|'mandataire'),
 *     reference_year (int), reference_year_kwh (float — baseline),
 *     trajectory_status ('on_track'|'off_track'|'not_evaluable'),
 *     baseline_normalization_status, reporting_start, reporting_end,
 *     closed_at, notes,
 *     buildings: [...], consumptions: [...], responsibilities: [...],
 *     events: [...], declarations: [...], proofs: [...]
 *   }
 *   validateEfaTrajectory(id, year) → {
 *     final_status, final_status_mode, baseline, current
 *   }
 *
 * IMPORTANT : le user spec parlait de `baseline_kwh_2010` mais
 * `reference_year` est dynamique (peut être 2010 OU 2020 OU autre).
 * Les presenters lisent `reference_year_kwh` et affichent l'année réelle.
 *
 * Objectifs DT (legifrance Art. L111-10-3 CCH) :
 *   2030 = −25 % vs reference_year_kwh
 *   2040 = −40 %
 *   2050 = −50 %
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// DT milestones + ratios
// ─────────────────────────────────────────────────────────────────────────────

export const DT_MILESTONES = [
  { year: 2030, ratio: 0.75, label: '−25 %', tone: 'afaire' },
  { year: 2040, ratio: 0.60, label: '−40 %', tone: 'attention' },
  { year: 2050, ratio: 0.50, label: '−50 %', tone: 'refuse' },
];

export function targetKwhForMilestone(referenceKwh, year) {
  if (!referenceKwh || referenceKwh <= 0) return null;
  const m = DT_MILESTONES.find((x) => x.year === year);
  if (!m) return null;
  return Math.round(referenceKwh * m.ratio);
}

// ─────────────────────────────────────────────────────────────────────────────
// Date helpers
// ─────────────────────────────────────────────────────────────────────────────

export function formatDateFR(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ─────────────────────────────────────────────────────────────────────────────
// Mappings statut → tone/label Sol
// ─────────────────────────────────────────────────────────────────────────────

const STATUT_PILL = {
  active: { tone: 'calme', label: 'Active' },
  draft: { tone: 'attention', label: 'Brouillon' },
  closed: { tone: 'afaire', label: 'Clôturée' },
};

const TRAJECTORY_PILL = {
  on_track: { tone: 'succes', label: 'En avance' },
  off_track: { tone: 'refuse', label: 'En retard' },
  review_required: { tone: 'attention', label: 'Revue requise' },
  not_evaluable: { tone: 'afaire', label: 'Non évaluable' },
};

/**
 * Pill prioritaire : trajectory_status si dispo, sinon statut EFA.
 */
export function statusPillFromEfa({ efa, trajectoryStatus } = {}) {
  if (trajectoryStatus && TRAJECTORY_PILL[trajectoryStatus]) {
    return TRAJECTORY_PILL[trajectoryStatus];
  }
  if (efa?.trajectory_status && TRAJECTORY_PILL[efa.trajectory_status]) {
    return TRAJECTORY_PILL[efa.trajectory_status];
  }
  if (efa?.statut && STATUT_PILL[efa.statut]) return STATUT_PILL[efa.statut];
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Owner (responsibilities filter)
// ─────────────────────────────────────────────────────────────────────────────

export function ownerFromEfa(efa) {
  const resps = efa?.responsibilities;
  if (!Array.isArray(resps) || resps.length === 0) return null;
  const owner = resps.find((r) => r?.role === 'proprietaire') || resps[0];
  return owner?.person_name || owner?.name || owner?.email || null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Consumptions (find latest year, sort, etc.)
// ─────────────────────────────────────────────────────────────────────────────

export function latestConsumption(efa) {
  const consos = Array.isArray(efa?.consumptions) ? efa.consumptions : [];
  if (consos.length === 0) return null;
  return consos
    .slice()
    .sort((a, b) => (b.year || 0) - (a.year || 0))[0];
}

export function consumptionKwh(conso) {
  if (!conso) return null;
  return conso.kwh_total ?? conso.kwh_total_final ?? conso.kwh_final ?? null;
}

export function totalSurface(efa) {
  const bldgs = Array.isArray(efa?.buildings) ? efa.buildings : [];
  return bldgs.reduce((acc, b) => acc + (Number(b.surface_m2) || 0), 0);
}

export function usageLabels(efa) {
  const bldgs = Array.isArray(efa?.buildings) ? efa.buildings : [];
  const set = new Set();
  for (const b of bldgs) {
    if (b?.usage_label) set.add(b.usage_label);
  }
  return Array.from(set);
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildEfaKicker({ efa } = {}) {
  if (!efa) return 'CONFORMITÉ · DÉCRET TERTIAIRE';
  const ref = efa.reference_year ? ` · RÉFÉRENCE ${efa.reference_year}` : '';
  const name = (efa.nom || `EFA ${efa.id || '—'}`).toUpperCase();
  return `CONFORMITÉ · DÉCRET TERTIAIRE · ${name}${ref}`;
}

export function buildEfaNarrative({ efa } = {}) {
  if (!efa) return 'Évaluation EFA en cours.';
  const refKwh = Number(efa.reference_year_kwh) || 0;
  const latest = latestConsumption(efa);
  const currKwh = Number(consumptionKwh(latest)) || 0;
  const bldgs = Array.isArray(efa.buildings) ? efa.buildings.length : 0;
  const surface = totalSurface(efa);
  const name = efa.nom || 'Cette EFA';

  const parts = [];
  parts.push(
    `${name} regroupe ${bldgs}${NBSP}bâtiment${bldgs > 1 ? 's' : ''} sur ${formatFR(surface, 0)}${NBSP}m²`
  );
  if (refKwh > 0) {
    parts.push(
      `référence ${efa.reference_year || '—'} ${formatFR(Math.round(refKwh / 1000), 0)}${NBSP}MWh`
    );
  }
  if (currKwh > 0 && refKwh > 0) {
    const progressPct = Math.round(((refKwh - currKwh) / refKwh) * 100);
    if (progressPct >= 25) {
      parts.push(`trajectoire actuelle −${progressPct}${NBSP}% · objectif 2030 déjà atteint`);
    } else if (progressPct > 0) {
      parts.push(`trajectoire actuelle −${progressPct}${NBSP}% sur −25${NBSP}% requis en 2030`);
    } else {
      const gapPct = Math.abs(progressPct);
      parts.push(`consommation actuelle ${gapPct > 0 ? '+' + gapPct : '='}${NBSP}% vs référence`);
    }
  }
  if (efa.trajectory_status === 'off_track') parts.push('en retard sur la trajectoire');
  if (efa.trajectory_status === 'on_track') parts.push('en avance sur la trajectoire');

  return parts.join(' · ') + '.';
}

export function buildEfaSubNarrative({ efa, lastDeclaration } = {}) {
  const parts = ['Sources : OPERAT ADEME + moteur déterministe RegOps'];
  if (lastDeclaration?.updated_at) {
    parts.push(`dernière MAJ ${formatDateFR(lastDeclaration.updated_at)}`);
  } else if (efa?.reporting_end) {
    parts.push(`période ${formatDateFR(efa.reporting_start)} → ${formatDateFR(efa.reporting_end)}`);
  }
  return parts.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Entity card fields
// ─────────────────────────────────────────────────────────────────────────────

export function buildEfaEntityCardFields({ efa, lastDeclaration } = {}) {
  if (!efa) return [];
  const usages = usageLabels(efa);
  const surface = totalSurface(efa);
  const bldgs = Array.isArray(efa.buildings) ? efa.buildings.length : 0;
  const owner = ownerFromEfa(efa);
  const refKwhMwh = efa.reference_year_kwh
    ? Math.round(efa.reference_year_kwh / 1000)
    : null;

  return [
    {
      label: 'Périmètre',
      value: usages.length > 0 ? usages.join(' · ') : (efa.nom || '—'),
    },
    {
      label: 'Bâtiments',
      value: bldgs > 0 ? `${bldgs}${NBSP}rattaché${bldgs > 1 ? 's' : ''}` : '—',
    },
    {
      label: 'Surface totale',
      value: surface > 0 ? `${formatFR(surface, 0)}${NBSP}m²` : '—',
      mono: true,
    },
    {
      label: `Référence ${efa.reference_year || ''}`.trim(),
      value: refKwhMwh != null ? `${formatFR(refKwhMwh, 0)}${NBSP}MWh` : '—',
      mono: true,
    },
    {
      label: 'Dernier OPERAT',
      value: lastDeclaration?.updated_at
        ? formatDateFR(lastDeclaration.updated_at)
        : 'non déposé',
    },
    {
      label: 'Responsable',
      value: owner || '—',
    },
    {
      label: 'Rôle',
      value: efa.role_assujetti || '—',
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretEfaReference({ efa } = {}) {
  if (!efa?.reference_year_kwh) return 'Année de référence en cours de qualification.';
  const mode = efa.baseline_normalization_status;
  if (mode === 'normalized_authoritative') {
    return `Référence normalisée DJU · année ${efa.reference_year || '—'}.`;
  }
  if (mode === 'raw_only') {
    return `Référence en données brutes · année ${efa.reference_year || '—'}.`;
  }
  return `Référence ${efa.reference_year || '—'} verrouillée pour le calcul des objectifs.`;
}

export function interpretEfaCurrent({ efa } = {}) {
  const latest = latestConsumption(efa);
  const currKwh = Number(consumptionKwh(latest)) || 0;
  const refKwh = Number(efa?.reference_year_kwh) || 0;
  if (currKwh <= 0) {
    return 'Consommation actuelle indisponible — prochaine MAJ au dépôt OPERAT annuel.';
  }
  if (refKwh <= 0) {
    return `Consommation ${latest?.year || ''} ${formatFR(Math.round(currKwh / 1000), 0)}${NBSP}MWh.`;
  }
  const progressPct = Math.round(((refKwh - currKwh) / refKwh) * 100);
  if (progressPct >= 25) return `−${progressPct}${NBSP}% vs référence · objectif 2030 atteint.`;
  if (progressPct >= 10) return `−${progressPct}${NBSP}% vs référence · progression à maintenir.`;
  if (progressPct > 0) return `−${progressPct}${NBSP}% vs référence · accélérer pour atteindre −25${NBSP}% en 2030.`;
  return `+${Math.abs(progressPct)}${NBSP}% vs référence · trajectoire en retard, plan requis.`;
}

export function interpretEfaTarget2030({ efa } = {}) {
  const refKwh = Number(efa?.reference_year_kwh) || 0;
  if (refKwh <= 0) return 'Objectif 2030 en attente de la consommation de référence.';
  const latest = latestConsumption(efa);
  const currKwh = Number(consumptionKwh(latest)) || 0;
  const target = targetKwhForMilestone(refKwh, 2030);
  if (target == null) return '—';
  const gapMwh = Math.max(0, Math.round((currKwh - target) / 1000));
  if (currKwh <= target && currKwh > 0) {
    return 'Cible 2030 déjà atteinte · sécurisez via monitoring et actions −40%/2040.';
  }
  if (gapMwh > 0) {
    return `Il reste ${formatFR(gapMwh, 0)}${NBSP}MWh à économiser pour atteindre la cible 2030.`;
  }
  return 'Cible 2030 en ligne de mire.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Trajectory chart data
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Retourne les data + verticalMarkers pour SolTrajectoryChart.
 * Axe X : années (reference_year → 2050).
 * Ligne mesurée : consommations historiques disponibles.
 * Marqueurs verticaux : 2030 / 2040 / 2050.
 */
export function buildEfaTrajectoryChart(efa) {
  if (!efa?.reference_year_kwh || !efa?.reference_year) {
    return { data: [], verticalMarkers: [], targetLine: null };
  }
  const refYear = efa.reference_year;
  const refKwh = efa.reference_year_kwh;
  const refMwh = Math.round(refKwh / 1000);

  // Data : toutes années entre refYear et max(2050, last consumption year)
  const consos = Array.isArray(efa.consumptions) ? efa.consumptions : [];
  const byYear = new Map();
  for (const c of consos) {
    if (c?.year && consumptionKwh(c) > 0) {
      byYear.set(c.year, Math.round(consumptionKwh(c) / 1000));
    }
  }
  // Ajouter le point de référence
  byYear.set(refYear, refMwh);

  const lastConsoYear = consos.reduce(
    (acc, c) => Math.max(acc, c?.year || 0),
    refYear
  );
  const years = [];
  for (let y = refYear; y <= Math.max(2050, lastConsoYear); y += 1) {
    years.push(y);
  }

  const data = years.map((y) => ({
    // SolTrajectoryChart utilise `month` comme clé X (hardcodé recharts).
    month: String(y),
    mwh: byYear.has(y) ? byYear.get(y) : null,
  }));

  const verticalMarkers = DT_MILESTONES.map((m) => ({
    x: String(m.year),
    label: `${m.year} ${m.label}`,
    tone: m.tone,
  }));

  const targetLine = targetKwhForMilestone(refKwh, 2030);
  const targetMwh = targetLine != null ? Math.round(targetLine / 1000) : null;

  return {
    data,
    verticalMarkers,
    targetLine: targetMwh, // MWh
    targetLabel: `Cible 2030 ${formatFR(targetMwh || 0, 0)}${NBSP}MWh`,
    yDomain: [0, Math.max(refMwh + 20, targetMwh ? targetMwh + 20 : refMwh + 20)],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards avec variety guard (reuse pattern Phase 3 RegOps)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 3 week-cards EFA avec variety par construction :
 *   Card 1 'attention' : bâtiment top-contributeur / dérive détectée
 *   Card 2 'afaire'    : prochaine déclaration OPERAT / pièces manquantes
 *   Card 3 'succes'    : validation récente / trajectoire en avance
 */
export function buildEfaWeekCards({ efa, lastDeclaration, onOpenModulation, onOpenProofs } = {}) {
  const cards = [];
  const refKwh = Number(efa?.reference_year_kwh) || 0;
  const latest = latestConsumption(efa);
  const currKwh = Number(consumptionKwh(latest)) || 0;
  const progressPct = refKwh > 0 && currKwh > 0
    ? Math.round(((refKwh - currKwh) / refKwh) * 100)
    : null;

  // Card 1 : attention (bâtiment top-driver conso OU trajectoire off_track)
  if (efa?.trajectory_status === 'off_track' && progressPct != null) {
    cards.push({
      id: 'traj-off',
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: 'Trajectoire en retard sur l\'objectif 2030',
      body: `Progression actuelle ${progressPct >= 0 ? '−' + progressPct : '+' + Math.abs(progressPct)}${NBSP}% vs référence, cible −25${NBSP}% à atteindre.`,
      footerLeft: `référence ${efa.reference_year || '—'}`,
      footerRight: 'Plan requis',
      onClick: () => onOpenModulation?.(),
    });
  } else if (Array.isArray(efa?.buildings) && efa.buildings.length > 0) {
    const topBuilding = efa.buildings
      .slice()
      .sort((a, b) => (b.surface_m2 || 0) - (a.surface_m2 || 0))[0];
    cards.push({
      id: `top-building-${topBuilding?.id || 'top'}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: topBuilding?.nom || topBuilding?.name || 'Bâtiment principal',
      body: `${formatFR(topBuilding?.surface_m2 || 0, 0)}${NBSP}m² · ${topBuilding?.usage_label || 'tertiaire'}. Principal contributeur à la consommation de l'EFA.`,
      footerLeft: 'top contributeur surface',
      footerRight: '⌘K',
    });
  } else {
    cards.push(businessErrorFallback('efa.no_findings', cards.length));
  }

  // Card 2 : afaire (pièces manquantes OU prochain dépôt OPERAT)
  const proofsCount = Array.isArray(efa?.proofs) ? efa.proofs.length : 0;
  if (proofsCount === 0) {
    cards.push({
      id: 'proofs-missing',
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: 'Pièces justificatives à déposer',
      body: "Aucune pièce déposée sur cette EFA. Facture, relevé ou attestation sont nécessaires pour valider la prochaine déclaration OPERAT.",
      footerLeft: 'upload multi-format',
      footerRight: 'Automatisable',
      onClick: () => onOpenProofs?.(),
    });
  } else if (lastDeclaration?.status && lastDeclaration.status !== 'submitted_simulated') {
    cards.push({
      id: 'declaration-pending',
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: `Déclaration OPERAT ${lastDeclaration.year || ''}`.trim(),
      body: `Statut ${lastDeclaration.status}. Finalisez la saisie avant la fenêtre annuelle (30 septembre).`,
      footerLeft: 'calendrier OPERAT',
      footerRight: lastDeclaration.status,
    });
  } else {
    const fb = businessErrorFallback('efa.evaluation_pending', cards.length);
    cards.push({ ...fb, tagKind: 'afaire', tagLabel: 'À faire' });
  }

  // Card 3 : succes (trajectoire on_track OU déclaration validée OU évaluation active)
  if (efa?.trajectory_status === 'on_track') {
    cards.push(businessErrorFallback('efa.on_track', cards.length));
  } else if (lastDeclaration?.status === 'submitted_simulated') {
    cards.push({
      id: `decl-ok-${lastDeclaration.year || 'last'}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: `Déclaration ${lastDeclaration.year || ''} validée`.trim(),
      body: "Votre dernière déclaration OPERAT a été soumise avec succès (simulation). Continuez sur cette régularité.",
      footerLeft: 'OPERAT ADEME',
      footerRight: '✓ Clean',
    });
  } else {
    cards.push({
      id: 'evaluation-active',
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: 'Évaluation déterministe active',
      body: "Le moteur RegOps surveille cette EFA en continu et vous alertera dès qu'une obligation bascule en risque.",
      footerLeft: 'surveillance active',
      footerRight: '—',
    });
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Normalize + re-exports
// ─────────────────────────────────────────────────────────────────────────────

export function normalizeEfa(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    nom: raw.nom || '',
    statut: raw.statut || 'draft',
    role_assujetti: raw.role_assujetti || null,
    reference_year: raw.reference_year || null,
    reference_year_kwh: raw.reference_year_kwh ?? null,
    trajectory_status: raw.trajectory_status || null,
    baseline_normalization_status: raw.baseline_normalization_status || null,
    reporting_start: raw.reporting_start || null,
    reporting_end: raw.reporting_end || null,
    closed_at: raw.closed_at || null,
    notes: raw.notes || null,
    buildings: Array.isArray(raw.buildings) ? raw.buildings : [],
    consumptions: Array.isArray(raw.consumptions) ? raw.consumptions : [],
    responsibilities: Array.isArray(raw.responsibilities) ? raw.responsibilities : [],
    events: Array.isArray(raw.events) ? raw.events : [],
    declarations: Array.isArray(raw.declarations) ? raw.declarations : [],
    proofs: Array.isArray(raw.proofs) ? raw.proofs : [],
  };
}

/**
 * Dernière déclaration par ordre de year DESC.
 */
export function latestDeclaration(efa) {
  const decs = Array.isArray(efa?.declarations) ? efa.declarations : [];
  if (decs.length === 0) return null;
  return decs
    .slice()
    .sort((a, b) => (b.year || 0) - (a.year || 0))[0];
}
