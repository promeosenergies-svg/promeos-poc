/**
 * PROMEOS V39.1 — Bouton "Déposer une preuve" vers la Mémobox
 * Composant réutilisable pour les écrans OPERAT / Tertiaire.
 *
 * Props:
 *   domain  - domaine KB (ex: "conformite/tertiaire-operat")
 *   hint    - texte libre (EFA, étape, anomalie, etc.)
 *   label   - texte du bouton (défaut: "Déposer une preuve")
 *   variant - "primary" | "secondary" | "ghost" (défaut: "secondary")
 *   size    - "xs" | "sm" (défaut: "xs")
 */
import { useNavigate } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { Button } from '../../../ui';
import { buildProofLink } from '../../../models/proofLinkModel';

const DEFAULT_DOMAIN = 'conformite/tertiaire-operat';

export default function ProofDepositCTA({
  domain = DEFAULT_DOMAIN,
  hint = '',
  label = 'Déposer une preuve',
  variant = 'secondary',
  size = 'xs',
}) {
  const navigate = useNavigate();

  const link = buildProofLink({
    type: 'conformite',
    actionKey: 'lev-tertiaire-efa',
    proofHint: hint || 'Preuve OPERAT — Décret tertiaire',
  });

  // Override domain in the generated link if custom domain provided
  const finalLink = domain !== 'reglementaire'
    ? link.replace(/domain=[^&]*/, `domain=${encodeURIComponent(domain)}`)
    : link;

  return (
    <Button
      size={size}
      variant={variant}
      onClick={() => navigate(finalLink)}
      aria-label={`${label} dans la Mémobox`}
    >
      <Upload size={size === 'xs' ? 12 : 14} />
      {label}
    </Button>
  );
}
