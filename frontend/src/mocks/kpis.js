/**
 * Mock data: KPIs for Command Center
 */
import { mockSites } from './sites';

const total = mockSites.length;
const conformes = mockSites.filter(s => s.statut_conformite === 'conforme').length;
const nonConformes = mockSites.filter(s => s.statut_conformite === 'non_conforme').length;
const aRisque = mockSites.filter(s => s.statut_conformite === 'a_risque').length;
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
    pct_conforme: Math.round(conformes / total * 100),
  },
  risque_financier: {
    total_eur: totalRisque,
    pertes_conso_eur: Math.round(totalRisque * 0.35),
    penalites_eur: Math.round(totalRisque * 0.65),
  },
  action_prioritaire: {
    texte: 'Declarer vos consommations sur OPERAT pour 12 sites',
    priorite: 'critical',
    nb_sites: 12,
    reglementation: 'decret_tertiaire',
  },
  anomalies: {
    total: totalAnomalies,
    critiques: Math.round(totalAnomalies * 0.15),
  },
};

export const mockTodos = [
  { id: 1, texte: 'Declarer OPERAT pour Bureau Paris 3', priorite: 'critical', echeance: '2026-02-15', site: 'Bureau Paris 3' },
  { id: 2, texte: 'Installer GTB batiment principal Hotel Lyon 8', priorite: 'critical', echeance: '2026-03-01', site: 'Hotel Lyon 8' },
  { id: 3, texte: 'Verifier compteur Entrepot Bordeaux 12', priorite: 'high', echeance: '2026-02-20', site: 'Entrepot Bordeaux 12' },
  { id: 4, texte: 'Attestation BACS Clinique Marseille 5', priorite: 'high', echeance: '2026-02-28', site: 'Clinique Marseille 5' },
  { id: 5, texte: 'Corriger derive conso Magasin Nantes 15', priorite: 'medium', echeance: '2026-03-15', site: 'Magasin Nantes 15' },
];

export const mockTopAnomalies = mockSites
  .filter(s => s.anomalies_count > 2)
  .sort((a, b) => b.risque_eur - a.risque_eur)
  .slice(0, 10)
  .map((s, i) => ({
    id: i + 1,
    site_nom: s.nom,
    site_id: s.id,
    type: ['hors_horaires', 'derive', 'base_load', 'pointe'][i % 4],
    severity: i < 3 ? 'critical' : i < 6 ? 'high' : 'medium',
    message: i < 3
      ? `${s.nom}: 58% conso hors horaires`
      : i < 6
        ? `${s.nom}: derive +12% sur 30j`
        : `${s.nom}: talon eleve (55% de la mediane)`,
    perte_eur: Math.round(s.risque_eur * 0.3),
  }));
