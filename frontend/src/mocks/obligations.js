/**
 * Mock data: obligations réglementaires for /conformite page
 * V4: aligned with the 5 HELIOS demo sites.
 *
 * Sites tertiaires > 1000 m² : Paris (3500), Lyon (1200), Nice (4000), Marseille (2800) = 4
 * Site industriel (non-tertiaire) : Toulouse (6000) = exclu du Décret Tertiaire
 * BACS (puissance CVC > 70 kW) : Paris, Toulouse, Nice = 3
 * Parkings > 1500 m² (APER) : Toulouse, Nice = 2
 * DPE : tous les 5 sites
 * Audit énergétique : organisation entière = 5 sites
 */

export const mockObligations = [
  {
    id: 1,
    regulation: 'Décret Tertiaire',
    code: 'DT',
    description: 'Réduire la consommation énergétique des bâtiments tertiaires > 1000 m²',
    pourquoi:
      'Vos sites tertiaires dépassent 1000 m² de surface — vous êtes soumis au Décret Tertiaire (loi ELAN).',
    quoi_faire:
      'Déclarer vos consommations sur la plateforme OPERAT et définir une trajectoire de réduction (-40% en 2030, -50% en 2040, -60% en 2050).',
    echeance: '2026-09-30',
    preuve: 'Déclaration OPERAT validée + attestation annuelle',
    proof_status: 'missing',
    sites_concernes: 4,
    sites_conformes: 1,
    statut: 'non_conforme',
    severity: 'critical',
    impact_eur: 45000,
    created_by: 'Système (auto-détection)',
    created_at: '2026-01-15',
    updated_at: '2026-02-10',
  },
  {
    id: 2,
    regulation: 'BACS',
    code: 'BACS',
    description: "Systèmes d'automatisation et de contrôle des bâtiments (GTB/GTC)",
    pourquoi:
      'Vos bâtiments possèdent une puissance CVC > 70 kW — le décret BACS vous impose un système de GTB.',
    quoi_faire:
      'Installer un système GTB conforme à la norme EN 15232 classe B minimum, ou obtenir une attestation de dérogation.',
    echeance: '2025-01-01',
    preuve: "Attestation GTB conforme + rapport d'inspection",
    proof_status: 'in_progress',
    sites_concernes: 3,
    sites_conformes: 1,
    statut: 'non_conforme',
    severity: 'critical',
    impact_eur: 35000,
    created_by: 'Système (auto-détection)',
    created_at: '2026-01-15',
    updated_at: '2026-02-08',
  },
  {
    id: 3,
    regulation: 'Loi APER',
    code: 'APER',
    description: "Installation d'énergies renouvelables sur parkings > 1500 m²",
    pourquoi:
      "Vos parkings extérieurs dépassent 1500 m² — la loi APER impose l'installation d'ombrières photovoltaïques.",
    quoi_faire:
      "Étudier la faisabilité d'ombrières solaires et planifier l'installation avant l'échéance.",
    echeance: '2028-07-01',
    preuve: "Permis de construire + contrat d'installation",
    proof_status: 'missing',
    sites_concernes: 2,
    sites_conformes: 0,
    statut: 'a_risque',
    severity: 'high',
    impact_eur: 15000,
    created_by: 'Système (auto-détection)',
    created_at: '2026-01-15',
    updated_at: '2026-01-15',
  },
  {
    id: 4,
    regulation: 'DPE Tertiaire',
    code: 'DPE',
    description: 'Diagnostic de Performance Énergétique obligatoire',
    pourquoi:
      'Le DPE est obligatoire pour tout bâtiment tertiaire lors de la vente ou la mise en location.',
    quoi_faire: "Commander un DPE auprès d'un diagnostiqueur certifié pour chaque site concerné.",
    echeance: '2026-12-31',
    preuve: 'DPE valide (< 10 ans)',
    proof_status: 'in_progress',
    sites_concernes: 5,
    sites_conformes: 3,
    statut: 'a_risque',
    severity: 'medium',
    impact_eur: 8000,
    created_by: 'J. Dupont',
    created_at: '2026-01-20',
    updated_at: '2026-02-05',
  },
  {
    id: 5,
    regulation: 'Audit Énergétique',
    code: 'AUDIT',
    description: 'Audit énergétique réglementaire pour les grandes entreprises (> 250 salariés)',
    pourquoi:
      'Votre organisation dépasse 250 salariés ou 50M EUR de CA — un audit énergétique est obligatoire tous les 4 ans.',
    quoi_faire:
      "Mandater un bureau d'études certifié pour réaliser l'audit. Couvrir au moins 80% de la facture énergétique.",
    echeance: '2026-12-05',
    preuve: "Rapport d'audit conforme NF EN 16247 + preuve de dépôt ADEME",
    proof_status: 'ok',
    sites_concernes: 5,
    sites_conformes: 5,
    statut: 'conforme',
    severity: 'low',
    impact_eur: 0,
    created_by: 'S. Bernard',
    created_at: '2026-01-10',
    updated_at: '2026-02-11',
  },
];

export function getObligationScore() {
  const total = mockObligations.length;
  const conformes = mockObligations.filter((o) => o.statut === 'conforme').length;
  const nonConformes = mockObligations.filter((o) => o.statut === 'non_conforme').length;
  const aRisque = mockObligations.filter((o) => o.statut === 'a_risque').length;
  const totalImpact = mockObligations.reduce((s, o) => s + o.impact_eur, 0);
  return {
    total,
    conformes,
    non_conformes: nonConformes,
    a_risque: aRisque,
    pct: Math.round((conformes / total) * 100),
    total_impact_eur: totalImpact,
    label: nonConformes > 0 ? 'Non conforme' : aRisque > 0 ? 'À risque' : 'Conforme',
  };
}
