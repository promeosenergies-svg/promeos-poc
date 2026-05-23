/**
 * M2-5.11.B — Fixtures partagées pour les tests des composants V4
 * (audit code-reviewer P1-4 — réduction duplication mock cross-fichiers).
 *
 * Limitation Vitest : `vi.mock(...)` est hoisté en tête de fichier et ne
 * peut pas être appelé via un helper. Cette fixture exporte donc :
 * - `emptyList` : la shape `{data:{items:[],total:0}, loading, error, refetch}`
 *   réutilisée x15 fichiers
 * - `setupV4HooksDefault(mocks)` : applique `mockReturnValue` par défaut
 *   sur l'objet `mocks` passé (= le résultat de `vi.mocked(useXxx)` ou
 *   l'import direct dans le fichier de test).
 *
 * Chaque fichier de test garde son `vi.mock('../../../hooks/v4', ...)` en
 * tête (contrainte Vitest), mais peut alléger son `beforeEach` :
 *
 *     beforeEach(() => {
 *       vi.clearAllMocks();
 *       setupV4HooksDefault({
 *         useActionCenterV4Items, useActionCenterV4Item, useActionCenterV4Events,
 *         useActionCenterV4Evidences, useActionCenterV4Blockers, useActionCenterV4Links,
 *         useActionCenterV4Impact,
 *       });
 *     });
 */
import { vi } from 'vitest';

/** Réponse vide standard de tous les list-hooks V4 (loaded, no error). */
export const emptyList = {
  data: { items: [], total: 0 },
  loading: false,
  error: null,
  refetch: vi.fn(),
};

/** Réponse vide standard du hook impact (loaded, no data, no error). */
export const emptyImpact = {
  data: null,
  loading: false,
  error: null,
  refetch: vi.fn(),
};

/** Réponse vide standard du hook impact en état loading (skeleton). */
export const loadingImpact = {
  data: null,
  loading: true,
  error: null,
  refetch: vi.fn(),
};

/** Réponse vide standard du hook item (single fetch). */
export const emptyItem = {
  data: null,
  loading: false,
  error: null,
  refetch: vi.fn(),
};

/** Réponse vide standard du hook summary (compteurs à 0, M2-5.11.C/J).
 * M2-6.C.P2-cleanup P2-5 — ajout des champs agrégés CFO (`sums_eur_*` +
 * `items_*`) cohérents avec le schéma `/summary` réel (M2-6.B.backend). Sans
 * eux, les composants qui accèdent à `summary.sums_eur_by_priority?.P0`
 * crashent silencieusement sur le mock vide (`undefined` → NaN propagé). */
export const emptySummary = {
  data: {
    count_p0: 0,
    count_p1: 0,
    count_without_owner: 0,
    // M2-5.11.J — breakdown CFO sur `count_without_owner`.
    count_p0_without_owner: 0,
    count_p1_without_owner: 0,
    count_at_risk: 0,
    count_secured: 0,
    // M2-6.B.backend — agrégat CFO source unique (jamais recalculé FE).
    sums_eur_by_priority: { P0: 0, P1: 0, P2: 0, P3: 0 },
    sums_eur_total: 0,
    items_with_impact_known: 0,
    items_total: 0,
  },
  loading: false,
  error: null,
  refetch: vi.fn(),
};

/**
 * Applique les `mockReturnValue` par défaut sur les hooks V4 fournis.
 * Le caller passe les imports `useXxx` qu'il a mockés via `vi.mock`. Tous
 * les arguments sont optionnels — passer uniquement les hooks pertinents
 * au fichier.
 */
export function setupV4HooksDefault({
  useActionCenterV4Items,
  useActionCenterV4Item,
  useActionCenterV4Events,
  useActionCenterV4Evidences,
  useActionCenterV4Blockers,
  useActionCenterV4Links,
  useActionCenterV4Impact,
  useActionCenterV4Summary,
  usePilotageFilePrioritaire,
  usePilotageJournal,
} = {}) {
  if (useActionCenterV4Items) useActionCenterV4Items.mockReturnValue(emptyList);
  if (useActionCenterV4Item) useActionCenterV4Item.mockReturnValue(emptyItem);
  if (useActionCenterV4Events) useActionCenterV4Events.mockReturnValue(emptyList);
  if (useActionCenterV4Evidences) useActionCenterV4Evidences.mockReturnValue(emptyList);
  if (useActionCenterV4Blockers) useActionCenterV4Blockers.mockReturnValue(emptyList);
  if (useActionCenterV4Links) useActionCenterV4Links.mockReturnValue(emptyList);
  // Impact est loading par défaut (skeleton inoffensif dans la plupart des
  // tests qui n'auditent pas la section Impact).
  if (useActionCenterV4Impact) useActionCenterV4Impact.mockReturnValue(loadingImpact);
  // Summary M2-5.11.C : 5 compteurs à 0 par défaut (NarrativeBar montre l'état
  // vide sans crasher les tests qui ne ciblent pas la synthèse).
  if (useActionCenterV4Summary) useActionCenterV4Summary.mockReturnValue(emptySummary);
  if (usePilotageFilePrioritaire) usePilotageFilePrioritaire.mockReturnValue(emptyList);
  if (usePilotageJournal) usePilotageJournal.mockReturnValue(emptyList);
}

/**
 * M2-6.C.3 (commit 1/4) — variante paramétrée per-test avec overrides.
 *
 * `setupV4HooksDefault` ne fait qu'appliquer des defaults. Beaucoup de tests
 * ont besoin d'injecter des données métier custom (summary HELIOS riche,
 * impact rich, etc.) — d'où la prolifération de helpers locaux `mockSummary`
 * dupliqués dans plusieurs fichiers. Cette variante évite la duplication :
 *
 *     setupHooksV4Mock(
 *       { useActionCenterV4Summary, useActionCenterV4Impact },
 *       {
 *         summary: { items_total: 9, sums_eur_total: 47500, ... },
 *         impact: { has_data: true, estimated: {...}, ... },
 *       }
 *     );
 *
 * - `overrides.<hookKey>` absent → fallback sur le default existant (emptyXxx)
 * - `overrides.<hookKey>` fourni → wrappé dans `{ data, loading:false, error:null, refetch }`
 * - `overrides.<hookKey>State` permet de surcharger loading/error finement
 *
 * Comme `setupV4HooksDefault`, on passe l'objet `hooks` mocké en argument
 * (contrainte Vitest hoisting — `vi.mock(...)` reste en tête du fichier test).
 */
export function setupHooksV4Mock(hooks = {}, overrides = {}) {
  const wrap = (key, defaultValue) => {
    const data = overrides[key];
    const state = overrides[`${key}State`] || {};
    if (data === undefined) return defaultValue;
    return { data, loading: false, error: null, refetch: vi.fn(), ...state };
  };

  if (hooks.useActionCenterV4Items)
    hooks.useActionCenterV4Items.mockReturnValue(wrap('items', emptyList));
  if (hooks.useActionCenterV4Item)
    hooks.useActionCenterV4Item.mockReturnValue(wrap('item', emptyItem));
  if (hooks.useActionCenterV4Events)
    hooks.useActionCenterV4Events.mockReturnValue(wrap('events', emptyList));
  if (hooks.useActionCenterV4Evidences)
    hooks.useActionCenterV4Evidences.mockReturnValue(wrap('evidences', emptyList));
  if (hooks.useActionCenterV4Blockers)
    hooks.useActionCenterV4Blockers.mockReturnValue(wrap('blockers', emptyList));
  if (hooks.useActionCenterV4Links)
    hooks.useActionCenterV4Links.mockReturnValue(wrap('links', emptyList));
  if (hooks.useActionCenterV4Impact)
    hooks.useActionCenterV4Impact.mockReturnValue(wrap('impact', loadingImpact));
  if (hooks.useActionCenterV4Summary)
    hooks.useActionCenterV4Summary.mockReturnValue(wrap('summary', emptySummary));
  if (hooks.usePilotageFilePrioritaire)
    hooks.usePilotageFilePrioritaire.mockReturnValue(wrap('filePrioritaire', emptyList));
  if (hooks.usePilotageJournal)
    hooks.usePilotageJournal.mockReturnValue(wrap('journal', emptyList));
}
