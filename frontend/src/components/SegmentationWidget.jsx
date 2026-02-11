import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { UserCheck, ChevronRight, AlertCircle } from 'lucide-react';
import { getSegmentationProfile } from '../services/api';

const TYPO_LABELS = {
  tertiaire_prive: 'Tertiaire Prive',
  tertiaire_public: 'Tertiaire Public',
  industrie: 'Industrie',
  commerce_retail: 'Commerce / Retail',
  copropriete_syndic: 'Copropriete / Syndic',
  bailleur_social: 'Bailleur Social',
  collectivite: 'Collectivite',
  hotellerie_restauration: 'Hotellerie / Restauration',
  sante_medico_social: 'Sante / Medico-social',
  enseignement: 'Enseignement',
  mixte: 'Mixte (multi-activites)',
};

function ConfidenceBar({ score }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-600">{Math.round(score)}%</span>
    </div>
  );
}

export default function SegmentationWidget() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSegmentationProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
        <div className="h-6 bg-gray-200 rounded w-2/3" />
      </div>
    );
  }

  if (!profile || !profile.has_profile) {
    return (
      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-gray-300">
        <div className="flex items-center gap-2 text-gray-500">
          <AlertCircle size={18} />
          <span className="text-sm">Profil non detecte — creez d'abord une organisation.</span>
        </div>
      </div>
    );
  }

  const label = TYPO_LABELS[profile.typologie] || profile.typologie;

  return (
    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <UserCheck size={18} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">Profil detecte</h3>
        </div>
        <Link
          to="/segmentation"
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition"
        >
          Affiner <ChevronRight size={14} />
        </Link>
      </div>

      <p className="text-lg font-bold text-gray-900 mb-2">{label}</p>

      <div className="mb-2">
        <p className="text-xs text-gray-500 mb-1">Confiance</p>
        <ConfidenceBar score={profile.confidence_score} />
      </div>

      {profile.reasons && profile.reasons.length > 0 && (
        <div className="mt-2">
          <p className="text-xs text-gray-400 mb-1">Signaux:</p>
          <ul className="space-y-0.5">
            {profile.reasons.slice(0, 3).map((r, i) => (
              <li key={i} className="text-xs text-gray-500">• {r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
