/**
 * PROMEOS — Source guards FE Hub Page L11 (Sprint Grammaire v1.2 / Phase 3.4).
 *
 * Surveille pages/CockpitJour.jsx (premier consommateur des primitifs L11) +
 * la composition globale grammar/hub/* + composants grammar/index.js exports.
 * Doctrine PROMEOS Sol v1.1 + addendum L11 (§12).
 *
 * Guards :
 *   SG_HUB_L11_01 — hub-page-uses-canonical-grammar :
 *       toute page Hub L11 importe HubPage + SolHeroPremiumNight + ChartFrame +
 *       HubHighlight + HubPageFooter depuis components/grammar (alias canoniques).
 *
 *   SG_HUB_L11_02 — promeos-marque-correcte :
 *       le mot PROMEOS s'ecrit toujours en majuscules sans accent (« PROMEOS »).
 *       Forme interdite : « Promeos », « Proméos », « promeos » dans labels UI.
 *       Tolere dans imports / chemins / commentaires WHY.
 *
 *   SG_HUB_L11_03 — kpi-3-no-misleading-formulation :
 *       les libelles KPI ne doivent pas annoncer faussement un total ou
 *       formule trompeuse (ex. « 100 % de … » sans periode, « total ARR »
 *       sans contexte). Heuristique conservatrice — lint stricte sur libelles
 *       value+label inline du fichier page.
 *
 * Pattern repo : readFileSync + regex (env=node), aligne events_fe_source_guards.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const COCKPIT_JOUR = join(SRC_ROOT, 'pages', 'CockpitJour.jsx');
const GRAMMAR_INDEX = join(SRC_ROOT, 'components', 'grammar', 'index.js');
const HUB_DIR = join(SRC_ROOT, 'components', 'grammar', 'hub');

const REQUIRED_HUB_PRIMITIVES = [
  'HubPage',
  'SolHeroPremiumNight',
  'ChartFrame',
  'HubHighlight',
  'HubPageFooter',
  // Phase F.1 — HubKpiCard extrait de KpiTriptychCard inline.
  // L'import devient requis : sans lui, scaling 5 hubs = drift garanti.
  'HubKpiCard',
];

function readFile(filePath) {
  return readFileSync(filePath, 'utf-8');
}

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_HUB_L11_01 — hub-page-uses-canonical-grammar ────────────────────────

describe('SG_HUB_L11_01 — hub-page-uses-canonical-grammar', () => {
  it('CockpitJour.jsx existe (premier consommateur Hub Page L11)', () => {
    expect(existsSync(COCKPIT_JOUR)).toBe(true);
  });

  it('CockpitJour.jsx importe les 5 primitifs L11 depuis components/grammar', () => {
    const src = readFile(COCKPIT_JOUR);
    const importBlock = src.match(/import\s*\{[^}]*\}\s*from\s*['"][^'"]*components\/grammar['"]/g);
    expect(importBlock).not.toBeNull();
    const joined = (importBlock || []).join('\n');
    for (const primitive of REQUIRED_HUB_PRIMITIVES) {
      expect(joined).toMatch(new RegExp(`\\b${primitive}\\b`));
    }
  });

  it('CockpitJour.jsx pose les marqueurs data-page="cockpit-jour" + data-doctrine="L11"', () => {
    const src = readFile(COCKPIT_JOUR);
    expect(src).toMatch(/data-page=['"]cockpit-jour['"]/);
    expect(src).toMatch(/data-doctrine=['"]L11['"]/);
  });

  it('grammar/index.js re-exporte les 5 primitifs L11 (alias canoniques)', () => {
    const src = readFile(GRAMMAR_INDEX);
    for (const primitive of REQUIRED_HUB_PRIMITIVES) {
      expect(src).toMatch(new RegExp(`export\\s*\\{\\s*default\\s+as\\s+${primitive}\\s*\\}`));
    }
  });

  it('chacun des 5 primitifs L11 existe sur disque sous grammar/hub/', () => {
    for (const primitive of REQUIRED_HUB_PRIMITIVES) {
      const filePath = join(HUB_DIR, `${primitive}.jsx`);
      expect(existsSync(filePath), `${primitive}.jsx manquant dans grammar/hub/`).toBe(true);
    }
  });

  it('CockpitJour.jsx utilise useFilter (mecanisme filtres L11 partage)', () => {
    const src = readFile(COCKPIT_JOUR);
    expect(src).toMatch(/import\s*\{\s*useFilter\s*\}/);
    expect(src).toMatch(/useFilter\(\)/);
  });

  it("CockpitJour.jsx consomme l'endpoint canonique /cockpit/jour via getCockpitJour", () => {
    const src = readFile(COCKPIT_JOUR);
    expect(src).toMatch(/getCockpitJour/);
  });

  // Phase F.2 — guard flexible variant : chaque <ChartFrame> doit contenir
  // au moins un enfant <ChartFrame[A-Z]…> (variante). On NE prescrit PAS
  // ChartFrameBars+ChartFrameLine en strict — Phase 3.5 introduira Stack /
  // Donut / Map selon le hub. Ce qu'on protège, c'est le pattern wrapper +
  // variante (pas la nomenclature des variantes).
  it('si <ChartFrame> utilisé alors ≥1 variante <ChartFrame*> dans le même fichier', () => {
    const src = readFile(COCKPIT_JOUR);
    // Détection tolérante à l'ordre textuel : la variante peut être déclarée
    // dans une variable `let inner = <ChartFrameX/>` AVANT le wrapper
    // <ChartFrame>{inner}</ChartFrame>. On valide la coexistence dans le
    // même fichier, pas l'imbrication textuelle directe (Phase F.3 compression).
    const usesWrapper = /<ChartFrame[\s>]/.test(src);
    const usesVariant = /<ChartFrame[A-Z][a-zA-Z]+\b/.test(src);
    if (usesWrapper) {
      expect(
        usesVariant,
        'Wrapper <ChartFrame> détecté sans variante <ChartFrame*> (Bars/Line/Stack/Donut/Map)'
      ).toBe(true);
    }
  });

  it('aucune balise <svg> inline directe dans CockpitJour.jsx (chart inline interdit)', () => {
    const src = readFile(COCKPIT_JOUR);
    // Anti-pattern : Skeleton et Error utilisent <div> aria-hidden, pas <svg>.
    // Si un <svg> apparait, c'est qu'un chart est inline (drift architectural).
    // Note : on tolere les <svg> SOUS forme commentaire JSX dans le wireframe
    // doctrinal (Hero), mais Hero est un import primitif → pas de match ici.
    const svgMatches = src.match(/<svg\b/g) || [];
    expect(svgMatches.length, '<svg> inline interdit : utiliser les variantes ChartFrame*').toBe(0);
  });

  // Phase F.3 — primitifs states CONDITIONNELS :
  // si la page implemente loading/error states, elle DOIT utiliser HubSkeleton
  // ou HubError respectivement. Pas obligatoire si la page n'a pas de state
  // loading/error (cas rare — peu probable pour un hub).
  it('HubSkeleton utilise si page implemente loading state (conditionnel)', () => {
    const src = readFileSync(COCKPIT_JOUR, 'utf-8');
    // Detecte l'utilisation de `loading` comme variable d'etat
    const hasLoadingState = /\bsetLoading\b|\bloading\s*&&/.test(src);
    if (hasLoadingState) {
      expect(src).toMatch(/<HubSkeleton\b/);
      expect(src).toMatch(/import\s*\{[^}]*\bHubSkeleton\b/);
    }
  });

  it('HubError utilise si page implemente error state (conditionnel)', () => {
    const src = readFileSync(COCKPIT_JOUR, 'utf-8');
    const hasErrorState = /\bsetError\b|\berror\s*&&/.test(src);
    if (hasErrorState) {
      expect(src).toMatch(/<HubError\b/);
      expect(src).toMatch(/import\s*\{[^}]*\bHubError\b/);
    }
  });

  it('HubSkeleton + HubError primitifs existent sur disque', () => {
    expect(existsSync(join(HUB_DIR, 'states', 'HubSkeleton.jsx'))).toBe(true);
    expect(existsSync(join(HUB_DIR, 'states', 'HubError.jsx'))).toBe(true);
  });

  // Phase F.5 — Tooltip Sol acronymes (résout audit 1.4 + 3.8) :
  // la page hub L11 doit utiliser <AutoTerm> ou <Term> pour wrapper les
  // acronymes dans les chaînes rendues depuis le payload backend.
  // Sans ce wrap, audit Phase D critère 1.4 (acronymes BACS/EMS/OPERAT/CVC/DT
  // sans tooltip Sol) reste à 1/3.
  it('CockpitJour.jsx importe et utilise AutoTerm (wrap acronymes payload backend)', () => {
    const src = readFileSync(COCKPIT_JOUR, 'utf-8');
    expect(src).toMatch(/import\s*\{[^}]*\bAutoTerm\b/);
    expect(src).toMatch(/<AutoTerm\b/);
  });

  it('AutoTerm primitif existe sur disque', () => {
    expect(existsSync(join(SRC_ROOT, 'components', 'grammar', 'AutoTerm.jsx'))).toBe(true);
  });
});

// ── SG_HUB_L11_02 — promeos-marque-correcte ────────────────────────────────

describe('SG_HUB_L11_02 — promeos-marque-correcte', () => {
  /**
   * La marque PROMEOS doit toujours apparaitre en majuscules, sans accent,
   * dans tout libelle UI ou contenu visible.
   *
   * On scanne UNIQUEMENT le contenu hors commentaires + hors imports/paths.
   * Formes interdites : Promeos, Proméos, ProMeos, proméos, etc.
   */
  const FORBIDDEN_MARK = /\b(?:Promeos|Proméos|ProMeos|promeos|proméos)\b/g;

  function scanForBadMark(filePath) {
    const raw = readFile(filePath);
    const noComments = stripComments(raw);
    // Retire les import/from path strings (chemins peuvent contenir 'promeos').
    const noImports = noComments.replace(/(import\s.+from\s+['"][^'"]+['"])/g, '');
    const matches = noImports.match(FORBIDDEN_MARK) || [];
    return matches;
  }

  it("CockpitJour.jsx n'utilise pas de forme incorrecte de la marque PROMEOS", () => {
    const badMarks = scanForBadMark(COCKPIT_JOUR);
    expect(badMarks).toEqual([]);
  });

  it('grammar/hub/*.jsx — aucun primitif L11 ne mentionne mal la marque', () => {
    for (const primitive of REQUIRED_HUB_PRIMITIVES) {
      const filePath = join(HUB_DIR, `${primitive}.jsx`);
      if (!existsSync(filePath)) continue;
      const badMarks = scanForBadMark(filePath);
      expect(badMarks, `${primitive}.jsx contient marque PROMEOS mal orthographiee`).toEqual([]);
    }
  });
});

// ── SG_HUB_L11_03 — kpi-3-no-misleading-formulation ────────────────────────

describe('SG_HUB_L11_03 — kpi-3-no-misleading-formulation', () => {
  /**
   * Les KPI Hub Page L11 (3 du triptyque) ne doivent pas afficher de
   * formulation trompeuse cote frontend. Le backend fournit le payload
   * (label, value, unit, delta) — la page se contente de l'afficher.
   *
   * Heuristiques conservatrices (false-positives toleres) :
   *  1. Pas de string litterale "100%" ou "100 %" hardcodee dans le rendu
   *     (eviterait un signal "tout va bien" trompeur sans data).
   *  2. Pas de string litterale "ARR total" / "Total ARR" hors contexte CFO
   *     (mot "ARR" sans annee/periode = ambiguite).
   *  3. Pas de mot "garantie" / "garanti" hors footScm (engagement implicite
   *     juridique non couvert par les sources).
   */
  const MISLEADING_PATTERNS = [
    { name: '"100%" hardcode (signal trompeur sans data)', pattern: /\b100\s?%\b/ },
    {
      name: '"ARR total" / "Total ARR" hors contexte',
      pattern: /\b(?:ARR\s+total|Total\s+ARR)\b/i,
    },
    {
      name: '"garantie" / "garanti" hors footScm (engagement juridique)',
      pattern: /\b(?:garantie|garanti)\b/i,
    },
  ];

  function scanFile(filePath) {
    const cleaned = stripComments(readFile(filePath));
    return MISLEADING_PATTERNS.filter(({ pattern }) => pattern.test(cleaned));
  }

  it('CockpitJour.jsx — aucun pattern KPI trompeur hardcode', () => {
    const violations = scanFile(COCKPIT_JOUR);
    if (violations.length) {
      // eslint-disable-next-line no-console
      console.error(
        'SG_HUB_L11_03 violations CockpitJour.jsx :',
        violations.map((v) => v.name)
      );
    }
    expect(violations).toEqual([]);
  });

  it('grammar/hub/*.jsx — aucun primitif L11 ne hardcode pattern trompeur', () => {
    for (const primitive of REQUIRED_HUB_PRIMITIVES) {
      const filePath = join(HUB_DIR, `${primitive}.jsx`);
      if (!existsSync(filePath)) continue;
      const violations = scanFile(filePath);
      if (violations.length) {
        // eslint-disable-next-line no-console
        console.error(
          `SG_HUB_L11_03 violations ${primitive}.jsx :`,
          violations.map((v) => v.name)
        );
      }
      expect(violations).toEqual([]);
    }
  });
});
