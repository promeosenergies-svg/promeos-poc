/**
 * Mock data: KPIs for Command Center
 */
import { mockSites } from './sites';

const total = mockSites.length;
const conformes = mockSites.filter((s) => s.statut_conformite === 'conforme').length;
const nonConformes = mockSites.filter((s) => s.statut_conformite === 'non_conforme').length;
const aRisque = mockSites.filter((s) => s.statut_conformite === 'a_risque').length;
const totalRisque = mockSites.reduce((sum, s) => sum + s.risque_eur, 0);
const totalAnomalies = mockSites.reduce((sum, s) => sum + s.anomalies_count, 0);

export const mockKpis = {
  conformite: {
    label: nonConformes > 0 ? 'Non conforme' : aRisque > 0 ? 'A risque' : 'Conforme',
    color: nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : 'ok',
    total_sites: total,
    conformes,
    non_conformes: nonConformes,
    a_risque: aRisque,
    pct_conforme: Math.round((conformes / total) * 100),
  },
  risque_financier: {
    total_eur: totalRisque,
    pertes_conso_eur: Math.round(totalRisque * 0.35),
    penalites_eur: Math.round(totalRisque * 0.65),
  },
  action_prioritaire: {
    texte: `Declarer vos consommations sur OPERAT pour ${mockSites.filter((s) => s.operat_status && s.operat_status !== 'SUBMITTED').length} sites`,
    priorite: 'critical',
    nb_sites: mockSites.filter((s) => s.operat_status && s.operat_status !== 'SUBMITTED').length,
    reglementation: 'decret_tertiaire',
  },
  anomalies: {
    total: totalAnomalies,
    critiques: Math.round(totalAnomalies * 0.15),
  },
};

const SITE = Object.fromEntries(mockSites.map((s) => [s.id, s]));

export const mockTodos = [
  {
    id: 1,
    texte: 'Declarer consommations OPERAT',
    priorite: 'critical',
    echeance: '2026-03-15',
    site: SITE[4].nom,
    site_id: 4,
  },
  {
    id: 2,
    texte: 'Installer GTB batiment principal',
    priorite: 'critical',
    echeance: '2026-03-20',
    site: SITE[2].nom,
    site_id: 2,
  },
  {
    id: 3,
    texte: 'Corriger non-conformite Decret Tertiaire',
    priorite: 'critical',
    echeance: '2026-03-10',
    site: SITE[3].nom,
    site_id: 3,
  },
  {
    id: 4,
    texte: 'Attestation BACS a obtenir',
    priorite: 'high',
    echeance: '2026-03-25',
    site: SITE[5].nom,
    site_id: 5,
  },
  {
    id: 5,
    texte: 'Verifier compteur gaz (derive detectee)',
    priorite: 'medium',
    echeance: '2026-04-01',
    site: SITE[1].nom,
    site_id: 1,
  },
];

export const mockTopAnomalies = mockSites
  .filter((s) => s.anomalies_count > 2)
  .sort((a, b) => b.risque_eur - a.risque_eur)
  .slice(0, 10)
  .map((s, i) => ({
    id: i + 1,
    site_nom: s.nom,
    site_id: s.id,
    type: ['hors_horaires', 'derive', 'base_load', 'pointe'][i % 4],
    severity: i < 3 ? 'critical' : i < 6 ? 'high' : 'medium',
    message:
      i < 3
        ? `${s.nom}: 58% conso hors horaires`
        : i < 6
          ? `${s.nom}: derive +12% sur 30j`
          : `${s.nom}: talon élevé (55% de la médiane)`,
    perte_eur: Math.round(s.risque_eur * 0.3),
  }));
