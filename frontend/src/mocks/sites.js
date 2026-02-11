/**
 * Mock data: 60 sites for Patrimoine + Site 360
 * Structure aligned with backend Site model.
 */

const VILLES = [
  'Paris', 'Lyon', 'Marseille', 'Toulouse', 'Bordeaux', 'Nantes', 'Lille',
  'Strasbourg', 'Montpellier', 'Rennes', 'Nice', 'Grenoble', 'Rouen',
  'Dijon', 'Clermont-Ferrand',
];

const USAGES = ['bureau', 'commerce', 'entrepot', 'hotel', 'sante', 'enseignement', 'copropriete', 'collectivite'];
const STATUTS = ['conforme', 'non_conforme', 'a_risque', 'a_evaluer'];
const REGIONS = ['IDF', 'ARA', 'PACA', 'NAQ', 'OCC', 'HDF', 'GE', 'BRE', 'NOR', 'BFC'];

function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick(arr) { return arr[rand(0, arr.length - 1)]; }

function generateSite(id) {
  const ville = pick(VILLES);
  const usage = pick(USAGES);
  const statut = pick(STATUTS);
  const surface = rand(200, 15000);
  const risque = statut === 'conforme' ? 0 : rand(500, 50000);
  const anomalies = statut === 'conforme' ? rand(0, 1) : rand(1, 8);

  return {
    id,
    nom: `${usage === 'bureau' ? 'Bureau' : usage === 'commerce' ? 'Magasin' : usage === 'hotel' ? 'Hotel' : usage === 'sante' ? 'Clinique' : usage === 'entrepot' ? 'Entrepot' : usage === 'enseignement' ? 'Lycee' : usage === 'copropriete' ? 'Residence' : 'Mairie'} ${ville} ${id}`,
    ville,
    region: pick(REGIONS),
    usage,
    surface_m2: surface,
    statut_conformite: statut,
    risque_eur: risque,
    anomalies_count: anomalies,
    conso_kwh_an: rand(50000, 2000000),
    nb_compteurs: rand(1, 5),
    actif: true,
    adresse: `${rand(1, 200)} rue ${pick(['de la Paix', 'Victor Hugo', 'Pasteur', 'Gambetta', 'Jean Jaures', 'de la Republique'])}`,
    code_postal: `${rand(10, 95)}000`.slice(0, 5),
    operat_status: pick(['submitted', 'not_started', 'verified', null]),
    derniere_evaluation: '2026-01-15',
  };
}

export const mockSites = Array.from({ length: 60 }, (_, i) => generateSite(i + 1));

export function getMockSite(id) {
  return mockSites.find((s) => s.id === Number(id));
}
