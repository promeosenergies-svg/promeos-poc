import React from 'react';

/**
 * NonApplicableLabel — affichage UI pour score=null + confidence='non_applicable'.
 *
 * Sprint C-2 Phase 4.5a — distingue le cas légitime "0 obligation réglementaire active"
 * (compliance_score V2 wrapper Phase 5 Sprint C-1) des cas erreur (score=null sans
 * confidence). Avant Phase 4.5, ces 2 cas étaient indistincts dans l'UI ("0" ou "—").
 *
 * Propre tracker dette : D-Phase5-Frontend-NonApplicable-001 (Sprint C-2).
 *
 * Usage typique :
 *   const isNonApplicable = score == null && confidence === 'non_applicable';
 *   isNonApplicable ? <NonApplicableLabel /> : <ScoreCircle value={score} />
 *
 * Props :
 *   - variant : 'default' | 'compact' | 'large' (taille texte)
 *   - tooltip : texte d'explication (défaut : "Aucune obligation réglementaire active")
 *   - className : classes additionnelles (composition)
 */
const NonApplicableLabel = ({
  variant = 'default',
  tooltip = 'Aucune obligation réglementaire active',
  className = '',
}) => {
  const sizeClass = variant === 'compact' ? 'text-xs' : variant === 'large' ? 'text-lg' : 'text-sm';

  return (
    <span
      className={`text-gray-400 italic ${sizeClass} ${className}`.trim()}
      title={tooltip}
      aria-label={`Non applicable. ${tooltip}`}
    >
      Non applicable
    </span>
  );
};

export default NonApplicableLabel;
