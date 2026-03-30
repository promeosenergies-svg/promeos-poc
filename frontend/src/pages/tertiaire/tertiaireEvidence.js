/**
 * PROMEOS — Evidence fixtures Decret Tertiaire (Phase 4)
 * 3 preuves structurees pour trajectoire, mutualisation, modulation.
 */
import { buildEvidence } from '../../ui/evidence';

export function buildTrajectoireEvidence(efaNom, refYear, refKwh, currentKwh, objectifKwh) {
  return buildEvidence({
    id: 'dt-trajectoire',
    title: `Trajectoire Decret Tertiaire — ${efaNom}`,
    valueLabel: currentKwh != null ? `${Math.round(currentKwh).toLocaleString('fr-FR')} kWh` : null,
    periodLabel: `Ref. ${refYear} vs actuel`,
    sources: [
      {
        kind: 'calc',
        label: 'Decret n2019-771, Art. R174-23 — objectifs par palier',
        confidence: 'high',
        details: 'Objectif 2030 = conso_ref x (1 - 40%)',
        links: [
          {
            label: 'Legifrance',
            href: 'https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251',
          },
        ],
      },
    ],
    method: [
      `Consommation de reference (${refYear}) : ${refKwh?.toLocaleString('fr-FR')} kWh`,
      `Objectif 2030 (-40%) : ${objectifKwh?.toLocaleString('fr-FR')} kWh`,
      `Consommation actuelle : ${currentKwh?.toLocaleString('fr-FR')} kWh`,
      `Ecart = actuelle - objectif`,
    ],
    assumptions: [
      `Annee de reference : ${refYear}`,
      'Methode DJU : non appliquee (donnees climatiques non disponibles)',
      'Trajectoire relative (pas Cabs)',
    ],
  });
}

export function buildMutualisationEvidence(nbSites, ecartTotal, economie) {
  return buildEvidence({
    id: 'dt-mutualisation',
    title: 'Simulation de mutualisation inter-sites',
    valueLabel: economie != null ? `Economie : ${economie.toLocaleString('fr-FR')} EUR` : null,
    sources: [
      {
        kind: 'calc',
        label: 'Decret n2019-771, Art. 3 — compensation inter-sites',
        confidence: 'medium',
        details: 'Fonctionnalite non encore disponible dans OPERAT',
      },
    ],
    method: [
      `${nbSites} sites evalues`,
      `Ecart portefeuille : ${ecartTotal?.toLocaleString('fr-FR')} kWh`,
      'Penalite sans mutualisation = 7 500 EUR x nb sites en deficit',
      'Penalite avec mutualisation = 7 500 EUR si deficit residuel, sinon 0',
      'Economie = penalite_sans - penalite_avec',
    ],
    assumptions: [
      'Mutualisation non encore implementee dans OPERAT — simulation anticipee',
      'Penalite forfaitaire 7 500 EUR/site (art. L174-1 CCH)',
    ],
  });
}

export function buildModulationEvidence(efaNom, triMoyen, readinessScore) {
  return buildEvidence({
    id: 'dt-modulation',
    title: `Simulation dossier de modulation — ${efaNom}`,
    valueLabel: readinessScore != null ? `Readiness : ${readinessScore}/100` : null,
    sources: [
      {
        kind: 'calc',
        label: 'Arrete du 10 avril 2020, Art. 6-2 — dossier de modulation',
        confidence: 'high',
        details: 'Depot OPERAT avant le 30/09/2026',
      },
    ],
    method: [
      `TRI moyen des actions : ${triMoyen} ans`,
      'Economie ajustee = somme(economies) x 0.85 (facteur interaction)',
      'Objectif module = conso apres actions (si > objectif initial)',
      'Score readiness = nb criteres remplis / 6 x 100',
    ],
    assumptions: [
      'Facteur prudence 0.85 sur economies cumulees (interactions entre actions)',
      'Norme NF EN 15459 pour le calcul TRI',
    ],
  });
}
