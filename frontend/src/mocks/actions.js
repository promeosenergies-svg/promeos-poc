/**
 * Mock data: actions backlog for /actions page
 */
import { mockSites } from './sites';

const TYPES = ['conformite', 'conso', 'facture', 'maintenance'];
const STATUTS = ['backlog', 'planned', 'in_progress', 'done'];
const OWNERS = ['J. Dupont', 'M. Martin', 'S. Bernard', 'A. Leroy', 'C. Moreau', ''];

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

const TITLES = [
  'Declarer consommations OPERAT',
  'Installer systeme GTB/GTC',
  'Obtenir attestation BACS',
  'Corriger derive consommation',
  'Verifier compteur principal',
  'Planifier audit energetique',
  'Reduire consommation hors horaires',
  'Optimiser talon de consommation',
  'Mettre en place suivi mensuel',
  'Demander derogation BACS',
  'Deposer dossier CEE',
  'Renover eclairage batiment',
  'Remplacer chaudiere ancienne',
  'Deployer sous-comptage',
  'Former equipe maintenance',
];

function generateAction(id) {
  const site = mockSites[id % mockSites.length];
  const type = pick(TYPES);
  const statut = pick(STATUTS);
  const impact = type === 'conformite' ? rand(2000, 30000) : rand(500, 15000);
  const dueDate = new Date(2026, rand(1, 8), rand(1, 28));

  return {
    id,
    titre: `${pick(TITLES)} — ${site.nom}`,
    type,
    site_id: site.id,
    site_nom: site.nom,
    impact_eur: impact,
    effort: `${rand(1, 10)}j`,
    statut,
    priorite: impact > 15000 ? 'critical' : impact > 8000 ? 'high' : impact > 3000 ? 'medium' : 'low',
    owner: pick(OWNERS),
    due_date: dueDate.toISOString().split('T')[0],
    created_at: '2026-01-15',
    description: '',
    comments: [],
  };
}

export const mockActions = Array.from({ length: 30 }, (_, i) => generateAction(i + 1));

export function getActionsByStatus(status) {
  return mockActions.filter(a => a.statut === status);
}
