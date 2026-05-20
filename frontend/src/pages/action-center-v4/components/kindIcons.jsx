/**
 * M2-5.10.A — Icônes SVG 7 kinds (doctrine V4 / maquette referentiel §8.3).
 *
 * Chaque icône reprend strictement le path data de la maquette HTML figée
 * (cf. `docs/maquettes/centre_action_v4/centre_action_v4_referentiel.html`).
 * Pas d'extraction depuis `lucide-react` : la maquette est la SoT visuelle,
 * et plusieurs paths sont des compositions custom (workflow décision, signal
 * radar avec 9 dots…) sans équivalent direct lucide.
 *
 * Chaque composant rend un `<svg>` 24×24 stroke-only — la couleur vient du
 * conteneur (cf. `KindCell` qui pose `color` depuis `KIND_SOL_VARIANTS`).
 */

const STROKE_PROPS = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function AnomalyIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <path d="M12 9v4M12 17h.01" />
      <path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    </svg>
  );
}

function ActionIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  );
}

function DecisionIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="12" r="3" />
      <path d="M9 6h6a3 3 0 0 1 3 3v3" />
      <path d="M9 18h6a3 3 0 0 0 3-3v-3" />
    </svg>
  );
}

function SignalIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <path d="M5 12h.01M19 12h.01M12 5v.01M12 19v.01M7.05 7.05l.01.01M16.95 7.05l.01.01M7.05 16.95l.01.01M16.95 16.95l.01.01M12 12h.01" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EvidenceRequestIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}

function DeadlineIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <path d="M6 2h12M6 22h12M6 2v6a6 6 0 0 0 12 0V2M6 22v-6a6 6 0 0 1 12 0v6" />
    </svg>
  );
}

function RecommendationIcon(props) {
  return (
    <svg {...STROKE_PROPS} {...props}>
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

// Mapping kind → composant icône. 7 entrées explicites, zéro méta-prog
// (doctrine V4 §13.5 : duplication contrôlée préférée à la factorisation).
export const KIND_ICONS = {
  anomaly: AnomalyIcon,
  action: ActionIcon,
  decision: DecisionIcon,
  signal: SignalIcon,
  evidence_request: EvidenceRequestIcon,
  deadline: DeadlineIcon,
  recommendation: RecommendationIcon,
};
