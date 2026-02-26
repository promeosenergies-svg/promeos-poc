/**
 * PROMEOS — Route Registry
 * Helpers stables pour la navigation interne. Aucun lien bricole.
 * Chaque helper retourne une URL relative prete pour navigate().
 */

/**
 * Explorer consommation — vue mono ou multi-site.
 * @param {object} opts
 * @param {number|string|number[]} [opts.site_id] — ID site ou tableau d'IDs
 * @param {number} [opts.days] — periode en jours (7, 30, 90, 365)
 * @param {string} [opts.date_from] — date debut YYYY-MM-DD (prioritaire sur days)
 * @param {string} [opts.date_to] — date fin YYYY-MM-DD
 * @param {'electricity'|'gas'} [opts.energy]
 * @param {'kwh'|'kw'|'eur'} [opts.unit]
 * @param {'agrege'|'superpose'|'empile'|'separe'} [opts.mode]
 */
export function toConsoExplorer(opts = {}) {
  const p = new URLSearchParams();
  if (opts.site_id != null) {
    const ids = Array.isArray(opts.site_id) ? opts.site_id : [opts.site_id];
    p.set('sites', ids.join(','));
  }
  if (opts.days) p.set('days', String(opts.days));
  if (opts.date_from) p.set('date_from', opts.date_from);
  if (opts.date_to) p.set('date_to', opts.date_to);
  if (opts.energy) p.set('energy', opts.energy);
  if (opts.unit) p.set('unit', opts.unit);
  if (opts.mode) p.set('mode', opts.mode);
  const qs = p.toString();
  return `/consommations/explorer${qs ? '?' + qs : ''}`;
}

/**
 * Diagnostic consommation — vue mono-site.
 * @param {object} opts
 * @param {number|string} opts.site_id
 */
export function toConsoDiag(opts = {}) {
  const p = new URLSearchParams();
  if (opts.site_id) p.set('site_id', String(opts.site_id));
  const qs = p.toString();
  return `/diagnostic-conso${qs ? '?' + qs : ''}`;
}

/**
 * Factures / Bill Intel — vue filtrée par site et mois.
 * @param {object} opts
 * @param {number|string} [opts.site_id]
 * @param {string} [opts.month] — format YYYY-MM
 * @param {number|string} [opts.invoice_id]
 */
export function toBillIntel(opts = {}) {
  const p = new URLSearchParams();
  if (opts.invoice_id) p.set('invoice_id', String(opts.invoice_id));
  if (opts.site_id) p.set('site_id', String(opts.site_id));
  if (opts.month) p.set('month', opts.month);
  const qs = p.toString();
  return `/bill-intel${qs ? '?' + qs : ''}`;
}

/**
 * Creation d'action avec contexte pre-rempli.
 * @param {object} opts
 * @param {'consommation'|'facture'|'patrimoine'} [opts.source_type]
 * @param {number|string} [opts.source_id]
 * @param {number|string} [opts.site_id]
 * @param {number[]|string} [opts.site_ids] — pour campagnes multi-sites
 * @param {string} [opts.title]
 * @param {string} [opts.source] — identifiant origine (portfolio, explorer, etc.)
 * @param {number} [opts.impact_eur] — impact estime en EUR
 * @param {string} [opts.date_from] — date debut YYYY-MM-DD
 * @param {string} [opts.date_to] — date fin YYYY-MM-DD
 */
export function toActionNew(opts = {}) {
  const p = new URLSearchParams();
  if (opts.source_type) p.set('type', opts.source_type);
  if (opts.source) p.set('source', opts.source);
  if (opts.source_id) p.set('ref_id', String(opts.source_id));
  if (opts.site_id) p.set('site_id', String(opts.site_id));
  if (opts.title) p.set('titre', opts.title);
  if (opts.impact_eur != null) p.set('impact_eur', String(opts.impact_eur));
  if (opts.date_from) p.set('date_from', opts.date_from);
  if (opts.date_to) p.set('date_to', opts.date_to);
  if (opts.site_ids) {
    const ids = Array.isArray(opts.site_ids) ? opts.site_ids.join(',') : opts.site_ids;
    p.set('campaign_sites', ids);
  }
  const qs = p.toString();
  return `/actions/new${qs ? '?' + qs : ''}`;
}

/**
 * Vue action existante.
 * @param {number|string} actionId
 */
export function toAction(actionId) {
  return `/actions/${actionId}`;
}

/**
 * Liste des actions filtrée.
 * @param {object} opts
 * @param {number|string} [opts.site_id] — filtre par site
 * @param {string} [opts.source] — filtre par origine (operat, portfolio, etc.)
 * @param {string} [opts.status] — filtre par statut (backlog, in_progress, done)
 * @param {string} [opts.source_type] — filtre par type source
 * @param {string} [opts.date_from] — date debut YYYY-MM-DD
 * @param {string} [opts.date_to] — date fin YYYY-MM-DD
 */
export function toActionsList(opts = {}) {
  const p = new URLSearchParams();
  if (opts.site_id) p.set('site_id', String(opts.site_id));
  if (opts.source) p.set('source', opts.source);
  if (opts.status) p.set('status', opts.status);
  if (opts.source_type) p.set('source_type', opts.source_type);
  if (opts.date_from) p.set('date_from', opts.date_from);
  if (opts.date_to) p.set('date_to', opts.date_to);
  const qs = p.toString();
  return `/actions${qs ? '?' + qs : ''}`;
}

/**
 * Patrimoine — gestion sites, horaires, compteurs.
 * @param {object} opts
 * @param {number|string} [opts.site_id]
 */
export function toPatrimoine(opts = {}) {
  const p = new URLSearchParams();
  if (opts.site_id) p.set('site_id', String(opts.site_id));
  const qs = p.toString();
  return `/patrimoine${qs ? '?' + qs : ''}`;
}

/**
 * Import & Analyse consommation.
 */
export function toConsoImport() {
  return '/consommations/import';
}

/**
 * Compliance pipeline — portfolio view.
 */
export function toCompliancePipeline() {
  return '/compliance/pipeline';
}

/**
 * Compliance site detail — tabs (obligations, preuves, plan).
 * @param {number|string} siteId
 */
export function toSiteCompliance(siteId) {
  return `/compliance/sites/${siteId}`;
}

/**
 * Achat Energie — simulation, portefeuille, echeances, historique.
 * @param {object} opts
 * @param {string} [opts.filter] — filtre preset (renewal, missing, etc.)
 * @param {string} [opts.tab] — onglet actif (simulation, portefeuille, echeances, historique)
 */
export function toPurchase(opts = {}) {
  const p = new URLSearchParams();
  if (opts.filter) p.set('filter', opts.filter);
  if (opts.tab) p.set('tab', opts.tab);
  const qs = p.toString();
  return `/achat-energie${qs ? '?' + qs : ''}`;
}

/**
 * Assistant Achat — wizard 8 etapes.
 */
export function toPurchaseAssistant() {
  return '/achat-energie/assistant';
}
