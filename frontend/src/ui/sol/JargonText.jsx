/**
 * JargonText — Auto-wrappe les acronymes du glossaire `acronyms.js` dans
 * un texte arbitraire avec `<AcronymTooltip>`. Phase 17.ter.A · 30/04/2026.
 *
 * Audit Phase 17 sévère : 14 routes / 16 affichaient leurs acronymes en
 * clair sans tooltip (CVC, ISO 50001, CRE, RTE, ATRD, COSTIC, EFA…).
 * Câbler manuellement `<AcronymTooltip>` sur des centaines de strings est
 * irréaliste — ce composant scanne le texte runtime et wrappe seulement
 * les tokens connus.
 *
 * Détection : regex `\b[A-Z]{2,}(?:\s?\d+)?\b` (acronymes ALL CAPS de 2+
 * chars, optionnellement suivis d'un nombre — ex "TURPE 7" / "ISO 50001"
 * / "BAT-TH-116"). Filtré par `isKnownAcronym` du glossaire.
 *
 * Utilisation :
 *   <JargonText>Décret BACS 2020-887 sur tertiaire >290 kW</JargonText>
 *   → "Décret <AcronymTooltip>BACS</AcronymTooltip> 2020-887 sur tertiaire >290 kW"
 *
 * Limitations connues :
 *   - Ne traverse pas les éléments React enfants (uniquement string children).
 *   - Si le texte contient déjà un AcronymTooltip wrap, on ne re-wrap pas.
 *   - HELIOS / COMEX / CODIR / EUR / TTC = labels UI (pas dans glossaire) —
 *     non wrappés, conforme à la doctrine "labels UI ≠ jargon métier".
 *
 * Doctrine §6.4 : "acronyme → récit". Plus aucun acronyme métier exposé brut.
 */
import { Fragment } from 'react';

import { isKnownAcronym } from '../../utils/acronyms';
import AcronymTooltip from './AcronymTooltip';

// Match acronymes ALL CAPS 2+ chars + suffixe numérique optionnel ou tiré
// (ex BAT-TH-116). Multilingue safe : on utilise [A-Z] strict pour ne pas
// matcher accidentellement des mots français ALL CAPS courts (ÉCO, NOTE…).
const ACRONYM_REGEX = /\b([A-Z]{2,}(?:[\s-]?\d+)?(?:[\s-]?TH-?\d+)?)\b/g;

export default function JargonText({ children, className = '' }) {
  // Si non-string (élément React, fragment, array), on rend tel quel.
  if (typeof children !== 'string') {
    return <span className={className}>{children}</span>;
  }
  return <span className={className}>{wrapAcronyms(children)}</span>;
}

/**
 * Wrappe les acronymes connus dans une string. Renvoie un array de
 * <Fragment>/<AcronymTooltip>, ou la string brute si rien à wrapper.
 */
function wrapAcronyms(text) {
  const matches = [...text.matchAll(ACRONYM_REGEX)];
  if (matches.length === 0) return text;

  // On reconstitue le texte morceau par morceau.
  const parts = [];
  let cursor = 0;
  matches.forEach((m, i) => {
    const token = m[0];
    const start = m.index ?? 0;
    // Dérivation baseKey :
    //  - Token "TURPE 7" / "ATRD7" / "ISO 50001" → on retire suffixe numérique.
    //  - Token "BAT-TH-116" → on garde le préfixe "BAT".
    //  - Token "CRE" → identité.
    const baseKey = token.split(/[\s-]/)[0].replace(/\d+$/, ''); // strip trailing digits (ATRD7 → ATRD)
    const known = isKnownAcronym(token) || isKnownAcronym(baseKey);
    if (cursor < start) parts.push(text.slice(cursor, start));
    if (known) {
      parts.push(
        <AcronymTooltip key={`acr-${i}-${start}`} acronym={baseKey}>
          {token}
        </AcronymTooltip>
      );
    } else {
      parts.push(token);
    }
    cursor = start + token.length;
  });
  if (cursor < text.length) parts.push(text.slice(cursor));

  return parts.map((p, i) =>
    typeof p === 'string' ? <Fragment key={`txt-${i}`}>{p}</Fragment> : p
  );
}

export { wrapAcronyms };
