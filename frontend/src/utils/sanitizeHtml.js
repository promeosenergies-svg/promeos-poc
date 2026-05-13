/**
 * utils/sanitizeHtml — Nettoyage HTML léger pour contenu interne contrôlé.
 *
 * Phase 3.8 NN — extrait de MethodologiePage.jsx pour réutilisation dans
 * DossierP1.jsx (champs body_html + why_promeos provenant des constructeurs
 * de la page Synthèse stratégique).
 *
 * Politique :
 *   - Retire balises actives (script, iframe, object, embed, applet, meta, link)
 *   - Retire tous attributs gestionnaires d'événements (on*)
 *   - Neutralise les URL « javascript: » (devient #)
 *   - Préserve mise en forme texte courant (strong, em, p, ul, li, br, code)
 *
 * Conditions d'usage :
 *   - Contenu provenant du serveur (constructeurs Python) — pas d'utilisateur final
 *   - Si la page s'ouvre à des sources externes, migrer vers une bibliothèque
 *     dédiée (DOMPurify) avec configuration stricte.
 */
const _SCRIPT_RE = /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi;
const _IFRAME_RE = /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi;
const _RISKY_TAGS_RE = /<(object|embed|applet|meta|link|style)\b[^>]*>/gi;
const _EVENT_ATTR_QUOTED_RE = /\son\w+\s*=\s*(['"])[^'"]*\1/gi;
const _EVENT_ATTR_UNQUOTED_RE = /\son\w+\s*=\s*[^\s>]+/gi;
const _JS_PROTOCOL_RE = /(href|src)\s*=\s*(['"])\s*javascript:[^'"]*\2/gi;

export function sanitizeHtml(html) {
  if (typeof html !== 'string' || html.length === 0) return '';
  return html
    .replace(_SCRIPT_RE, '')
    .replace(_IFRAME_RE, '')
    .replace(_RISKY_TAGS_RE, '')
    .replace(_EVENT_ATTR_QUOTED_RE, '')
    .replace(_EVENT_ATTR_UNQUOTED_RE, '')
    .replace(_JS_PROTOCOL_RE, '$1="#"');
}

export default sanitizeHtml;
