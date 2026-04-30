/**
 * PROMEOS — Glossaire acronymes énergie/réglementaire (Vague E ét16).
 *
 * Audit Marie DAF #2 (28/04/2026) : « Sur Conformité, je relis 2 fois
 * "BACS/APER/Décret Tertiaire" sans gloss, je décroche dès la 3ᵉ ligne ».
 *
 * Source de vérité unique pour les définitions courtes (1 phrase max)
 * affichées en tooltip via `<SolAcronym code="BACS">BACS</SolAcronym>`.
 *
 * Doctrine §5 grammaire éditoriale : aucun acronyme brut ne doit apparaître
 * en UI sans définition accessible 1-clic (tooltip ou popover).
 *
 * Conventions :
 * - Clé en MAJUSCULES = code canonique (ex: "BACS", "APER", "TURPE")
 * - Valeur = phrase courte FR non-sachant (DAF/CFO comprennent)
 * - Cite la base réglementaire si pertinent (Décret n°XXXX-YYY)
 * - Maximum 120 caractères pour tenir en tooltip (UX P0-C ét12d ≥ 11px)
 */

export const GLOSSARY = Object.freeze({
  // ── Réglementation tertiaire ────────────────────────────────────
  'Décret Tertiaire':
    "Loi ELAN — réduction conso 40 % d'ici 2030 sur bâtiments tertiaires > 1000 m² (Décret 2019-771).",
  DT: "Décret Tertiaire (loi ELAN) — réduction conso 40 % d'ici 2030 sur bâtiments tertiaires > 1000 m².",
  BACS: 'Bâtiments à Automatisation & Contrôle Système — obligation GTB pour bâtiments CVC > 70 kW (Décret 2020-887).',
  APER: 'Loi Accélération Production Énergies Renouvelables — obligation panneaux photovoltaïques sur parkings > 1500 m² (Loi 2023-175).',
  OPERAT:
    'Plateforme ADEME de déclaration annuelle des consommations énergétiques tertiaires (échéance 30/09 chaque année).',
  GTB: "Gestion Technique du Bâtiment — système d'automatisation chauffage/clim/éclairage (chargé par décret BACS).",
  ELAN: "Loi Évolution du Logement, de l'Aménagement et du Numérique (2018) — origine du Décret Tertiaire.",

  // ── Tarifs réseaux ──────────────────────────────────────────────
  TURPE:
    "Tarif d'Utilisation des Réseaux Publics d'Électricité — facturé Enedis sur acheminement (CRE délibération annuelle).",
  ATRD: 'Accès des Tiers au Réseau de Distribution gaz — tarif acheminement GRDF (CRE délibération annuelle).',
  ATRT: 'Accès des Tiers au Réseau de Transport gaz — tarif transport GRTgaz/Teréga.',
  CTA: "Contribution Tarifaire d'Acheminement — taxe sur retraites employés Enedis/GRDF, % du TURPE/ATRD.",

  // ── Marché énergie ──────────────────────────────────────────────
  ARENH:
    "Accès Régulé à l'Électricité Nucléaire Historique — fin 31/12/2025, remplacé par mécanisme capacité 1/11/2026.",
  VNU: 'Versement Nucléaire Universel — remplaçant ARENH, taxe/réduction selon prix marché EPEX (loi 2023-175).',
  EPEX: "Bourse spot européenne de l'électricité — référence prix horaire J-1 (équivalent : Powernext fusionné).",
  PEG: "Point d'Échange de Gaz — bourse spot gaz France (équivalent EPEX pour gaz).",
  NEBCO:
    "Notification d'Effacement Bloc COllectif — mécanisme RTE de rémunération de l'effacement industriel/tertiaire.",
  AOFD: "Appel d'Offres Flexibilité Demande — mécanisme RTE complémentaire NEBCO pour effacement contractualisé annuel.",
  Tempo:
    'Option tarifaire EDF avec 22 jours rouges/an pic prix — différenciation HP/HC + couleurs jour.',
  EcoWatt:
    'Signal RTE de tension réseau (vert/orange/rouge) — invite à différer la consommation jours alerte.',

  // ── Indicateurs technique énergie ──────────────────────────────
  CDC: 'Courbe De Charge — relevé horaire ou demi-horaire des consommations (Enedis CDC J+1, GRDF PCE J+2).',
  PRM: 'Point Référence Mesure — identifiant 14 chiffres compteur électrique Enedis (équivalent PDL legacy).',
  PCE: "Point de Comptage et d'Estimation — identifiant compteur gaz GRDF (équivalent PRM côté gaz).",
  PDL: 'Point De Livraison — ancien terme pour PRM/PCE, encore utilisé dans certains contrats fournisseur.',
  CVC: 'Chauffage, Ventilation, Climatisation — équipements thermiques bâtiments (puissance pertinente pour décret BACS).',
  IRVE: 'Infrastructure de Recharge pour Véhicules Électriques — bornes de recharge VE soumises à régulation tarifaire.',
  BESS: 'Battery Energy Storage System — stockage par batterie (pour effacement, autoconsommation, NEBCO).',
  IPMVP:
    "International Performance Measurement & Verification Protocol — référentiel de mesure des économies d'énergie.",

  // ── Conformité européenne ───────────────────────────────────────
  CBAM: 'Carbon Border Adjustment Mechanism — taxe carbone européenne sur importations (acier/ciment/aluminium/élec/H2/engrais), pleine application 2034.',
  CSRD: 'Corporate Sustainability Reporting Directive — reporting ESG européen obligatoire (post-Omnibus 2025 : seuils relevés).',
  ETS2: 'Emission Trading System 2 — marché carbone européen 2ᵉ phase (bâtiments + transports), démarrage 2028.',
  CEE: "Certificats d'Économies d'Énergie — dispositif français obligeant fournisseurs à financer rénovation (P5 jusqu'à 2025, P6 ensuite).",

  // ── Mesures conso ───────────────────────────────────────────────
  MWh: 'MégaWatt-heure (1 000 kWh) — unité conso annuelle bâtiment moyen ETI tertiaire ~100 MWh/an.',
  kWh: 'kiloWatt-heure — unité énergétique standard facturation.',
  GWh: 'GigaWatt-heure (1 000 MWh) — unité portefeuille multi-sites ETI.',
  CO2: 'Dioxyde de carbone — gaz à effet de serre principal, exprimé en tonnes équivalent CO₂ (tCO₂e).',
  DJU: 'Degré Jour Unifié — référence COSTIC des besoins thermiques selon climat (utilisé pour normaliser conso vs météo).',
  CUSUM:
    'Cumulative Sum control chart — détection statistique de dérive baseline énergétique (norme ISO 50001).',
  // Phase 18.B (audit Phase 17 cumulée) — entrées Phase 17.bis/quater
  // ajoutées ici pour permettre à SolAcronym/SolNarrativeText (présent sur
  // 10+ pages : Compliance, Site360, Flex, BriefCodexCard, etc.) de glosser
  // automatiquement les acronymes apparaissant dans les textes narratifs.
  // Cohérent avec frontend/src/utils/acronyms.js (Phase 17 SoT JargonText).
  CRE: "Commission de Régulation de l'Énergie — autorité française régulant TURPE, ATRD, ARENH, capacité, NEBCO.",
  RTE: "Réseau de Transport d'Électricité — gestionnaire haute tension français. Opère mécanisme capacité, NEBCO, AOFD.",
  'ISO 50001':
    "Norme internationale Système de Management de l'Énergie. Certification SMÉ vaut audit énergétique réglementaire ETI.",
  COSTIC:
    'Comité Scientifique et Technique des Industries Climatiques — référence française du calcul DJU + méthode NF EN 16247-2.',
  EFA: 'Entité Fonctionnelle Assujettie — unité de déclaration OPERAT (>1 000 m² tertiaire). Assujettie aux jalons -40/-50/-60 %.',
  DPE: 'Diagnostic de Performance Énergétique — étiquette énergie/climat A→G obligatoire location/vente bâtiment.',
  SME: "Système de Management de l'Énergie — démarche ISO 50001, vaut audit réglementaire ETI.",
  GTC: 'Gestion Technique Centralisée — système de pilotage centralisé multi-équipements (variante GTB Décret BACS).',
  COFRAC:
    "Comité Français d'Accréditation — accrédite les auditeurs énergétiques. Tout audit réglementaire ETI doit être COFRAC.",
  IPE: "Indicateur de Performance Énergétique — ratio énergie/activité d'un site (kWh/m²/an, kWh/jour ouvré). ISO 50001 §6.3.",
  ADEME:
    'Agence de la transition écologique — publie Base Empreinte (CO₂), benchmarks tertiaires OID, fiches CEE.',
  OPQIBI:
    'Office Professionnel de Qualification (Ingénierie Bâtiment). Qualification 1905 = audit énergétique réglementaire ETI.',
  TVA: 'Taxe sur la Valeur Ajoutée — 20 % uniforme sur tous composants HT facture énergie depuis 01/08/2025 (LFI 2025).',
  GRDF: 'Gaz Réseau Distribution France — gestionnaire distribution gaz (filiale Engie). Opère ATRD7, MMR, ADICT pour PCE.',
  HTA: 'Haute Tension A — tension 1 kV à 50 kV (poste entreprise > 250 kVA). Tarif TURPE 7 dédié, plus avantageux que BT.',
  HTB: 'Haute Tension B — tension > 50 kV (transport RTE). TURPE 7 HTB1/HTB2/HTB3 pour sites raccordés transport.',
  ENR: "Énergies Renouvelables — solaire/éolien/hydraulique/géothermie/biomasse. Couverture obligatoire APER >50 % d'ici 2028.",
});

// Phase 22.3 — fallback vers le SoT canonique `utils/acronyms.js` si la clé
// n'est pas trouvée localement. Conserve les 10 consumers SolAcronym sans
// refactor + garantit accès aux 45 entrées du SoT central depuis ce système.
//
// Architecture finale glossaires (post Phase 22) :
//   1. utils/acronyms.js = SoT canonique 45 entrées (Phase 13/15/17 :
//      structure riche {long, meaning, source} + helpers acronymTooltip).
//   2. domain/glossary.js = façade Sol briefings (54 entrées, simple
//      `code → string`) + fallback SoT.
//   3. ui/glossary.js = façade legacy V1 (453 lignes, {term, short, long}).
//
// Aucun consumer ne change. Toute nouvelle entrée doit être ajoutée au SoT
// `utils/acronyms.js`. Les façades sont maintenues pour rétro-compat tant
// que le refactor cross-pages n'est pas fait.
import { acronymTooltip as _soTooltip, isKnownAcronym as _soIsKnown } from '../utils/acronyms';

/** Helper : retourne la définition ou la chaîne vide si non glossé.
 *  Phase 22.3 : fallback vers SoT canonique `utils/acronyms.js` si absent. */
export function getDefinition(code) {
  if (!code) return '';
  const local = GLOSSARY[code] || GLOSSARY[code.toUpperCase()];
  if (local) return local;
  // Fallback SoT — extrait la `meaning` (description courte) qui est la plus
  // proche du format `domain/glossary.js` (1 phrase non-sachant).
  const sotKey = code.split(/\s+/)[0]?.toUpperCase();
  if (_soIsKnown(sotKey)) {
    const fullTooltip = _soTooltip(sotKey) || '';
    // Le tooltip SoT a le format "Long — Meaning · Source : X" — on extrait
    // la partie "Meaning" pour rester compatible avec le format domain/glossary.
    const m = fullTooltip.match(/—\s*(.+?)(?:\s*·\s*Source\s*:|$)/);
    return m ? m[1].trim() : fullTooltip;
  }
  return '';
}

/** Helper : true si le code a une définition glossée (SoT compris). */
export function isGlossed(code) {
  if (!code) return false;
  if (GLOSSARY[code] || GLOSSARY[code.toUpperCase()]) return true;
  const sotKey = code.split(/\s+/)[0]?.toUpperCase();
  return _soIsKnown(sotKey);
}
