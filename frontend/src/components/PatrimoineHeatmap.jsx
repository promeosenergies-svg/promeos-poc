/**
 * PatrimoineHeatmap — V63
 * Grille "heatmap" des sites patrimoniaux : risque, anomalies, framework dominant.
 *
 * Props:
 *   tiles       : TileModel[] — [{site_id, site_nom, total_risk_eur, anomalies_count,
 *                                  max_severity, dominant_framework, completude_score,
 *                                  top_anomalies[]}]
 *   onOpenSite  : (site_id) → void — ouvre SiteDrawer onglet Anomalies
 *   loading     : bool — skeleton skeleton
 *   error       : string|null
 *
 * Couleur tile :
 *   - Si risque > 0 : quantile (top 33% rouge, mid 33% amber, bas 33% vert)
 *   - Fallback si risque = 0 : max_severity (CRITICAL=rouge, HIGH=orange, …)
 *
 * Filtres locaux : framework, sévérité, recherche nom, tri.
 * Reset-safe : si tiles=[] → CTA "Charger HELIOS" → /import.
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Search, Upload, ChevronDown, X, LayoutGrid,
} from 'lucide-react';

/* ── Constantes ─────────────────────────────────────────────────────────── */

const FRAMEWORK_LABEL = {
  DECRET_TERTIAIRE: 'Décret Tertiaire',
  FACTURATION:      'Facturation',
  BACS:             'BACS',
};

const FRAMEWORK_CHIP = {
  DECRET_TERTIAIRE: 'bg-purple-50 text-purple-700 border-purple-200',
  FACTURATION:      'bg-blue-50 text-blue-700 border-blue-200',
  BACS:             'bg-teal-50 text-teal-700 border-teal-200',
};

const SEV_BADGE = {
  CRITICAL: 'bg-red-100 text-red-700',
  HIGH:     'bg-orange-100 text-orange-700',
  MEDIUM:   'bg-amber-100 text-amber-700',
  LOW:      'bg-yellow-100 text-yellow-700',
};

// Couleur tile selon niveau de risque/sévérité
const COLOR_CLASSES = {
  critical: { card: 'bg-red-50 border-red-200',     bar: 'bg-red-500',    risk: 'text-red-600'    },
  high:     { card: 'bg-orange-50 border-orange-200', bar: 'bg-orange-400', risk: 'text-orange-600' },
  medium:   { card: 'bg-amber-50 border-amber-200',  bar: 'bg-amber-400',  risk: 'text-amber-600'  },
  low:      { card: 'bg-yellow-50 border-yellow-200', bar: 'bg-yellow-300', risk: 'text-yellow-700' },
  none:     { card: 'bg-gray-50 border-gray-200',    bar: 'bg-green-300',  risk: 'text-gray-500'   },
};

const FW_OPTIONS = [
  { value: '',                label: 'Tous frameworks'  },
  { value: 'DECRET_TERTIAIRE', label: 'Décret Tertiaire' },
  { value: 'FACTURATION',      label: 'Facturation'      },
  { value: 'BACS',             label: 'BACS'             },
];

const SEV_OPTIONS = [
  { value: '',         label: 'Toute sévérité' },
  { value: 'CRITICAL', label: 'Critique'       },
  { value: 'HIGH',     label: 'Élevée'         },
  { value: 'MEDIUM',   label: 'Moyenne'        },
  { value: 'LOW',      label: 'Faible'         },
];

const SORT_OPTIONS = [
  { value: 'risk',      label: 'Risque ↓'         },
  { value: 'anomalies', label: 'Anomalies ↓'      },
  { value: 'score',     label: 'Score qualité ↑'  },
];

/* ── Utilitaires ─────────────────────────────────────────────────────────── */

function fmtRisk(eur) {
  if (!eur || eur <= 0) return '0 €';
  if (eur >= 1_000_000) return `~${(eur / 1_000_000).toFixed(1)} M€`;
  if (eur >= 1_000)     return `~${(eur / 1_000).toFixed(0)} k€`;
  return `~${Math.round(eur)} €`;
}

/**
 * Détermine la couleur d'une tile :
 *  - Si au moins un site a risque > 0 → quantile rank parmi les sites à risque
 *  - Sinon → fallback sur max_severity
 */
function getTileColorKey(tile, allTiles) {
  const riskyTiles = allTiles.filter(t => (t.total_risk_eur || 0) > 0);
  if (riskyTiles.length > 0 && (tile.total_risk_eur || 0) > 0) {
    const sorted = [...riskyTiles].sort((a, b) => b.total_risk_eur - a.total_risk_eur);
    const rank = sorted.findIndex(t => t.site_id === tile.site_id);
    if (rank === -1) return 'none';
    const pct = sorted.length > 1 ? rank / (sorted.length - 1) : 0;
    if (pct < 0.34) return 'critical';
    if (pct < 0.67) return 'high';
    return 'medium';
  }
  // Fallback sévérité
  const sev = tile.max_severity;
  if (sev === 'CRITICAL') return 'critical';
  if (sev === 'HIGH')     return 'high';
  if (sev === 'MEDIUM')   return 'medium';
  if (sev === 'LOW')      return 'low';
  return 'none';
}

/* ── Sous-composants ─────────────────────────────────────────────────────── */

function FilterSelect({ options, value, onChange, label }) {
  return (
    <div className="relative">
      <select
        aria-label={label}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="appearance-none pl-2.5 pr-6 py-1.5 text-xs border border-gray-200 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <ChevronDown size={11} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
    </div>
  );
}

function SiteTile({ tile, allTiles, onOpenSite }) {
  const colorKey = getTileColorKey(tile, allTiles);
  const cls      = COLOR_CLASSES[colorKey] ?? COLOR_CLASSES.none;
  const fwLabel  = FRAMEWORK_LABEL[tile.dominant_framework] ?? tile.dominant_framework;
  const fwCls    = FRAMEWORK_CHIP[tile.dominant_framework] ?? 'bg-gray-50 text-gray-600 border-gray-200';

  return (
    <button
      onClick={() => onOpenSite?.(tile.site_id)}
      className={`relative flex flex-col text-left w-full rounded-xl border p-3 pt-3.5 hover:shadow-md hover:-translate-y-px transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-400 ${cls.card}`}
    >
      {/* Bande colorée haut */}
      <div className={`absolute top-0 left-0 right-0 h-1 rounded-t-xl ${cls.bar}`} />

      {/* Nom site */}
      <span className="text-xs font-semibold text-gray-800 truncate w-full block leading-snug">
        {tile.site_nom}
      </span>

      {/* Risque */}
      <span className={`text-sm font-bold mt-1 ${cls.risk}`}>
        {fmtRisk(tile.total_risk_eur)}
      </span>

      {/* Anomalies + sévérité */}
      <div className="flex items-center gap-1 mt-1.5 flex-wrap">
        {tile.anomalies_count > 0 ? (
          <span className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded-full ${SEV_BADGE[tile.max_severity] ?? 'bg-gray-100 text-gray-600'}`}>
            {tile.anomalies_count} anom.
          </span>
        ) : (
          <span className="text-[10px] text-green-600 font-medium">✓ OK</span>
        )}

        {/* Score qualité */}
        {tile.completude_score != null && (
          <span className="text-[10px] text-gray-400 font-medium">
            {tile.completude_score}%
          </span>
        )}
      </div>

      {/* Framework dominant */}
      {tile.dominant_framework && (
        <span className={`mt-1.5 inline-flex items-center text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded border shrink-0 ${fwCls}`}>
          {fwLabel}
        </span>
      )}

      {/* Preview top anomalie */}
      {tile.top_anomalies?.[0] && (
        <span className="mt-1.5 text-[10px] text-gray-400 truncate block w-full" title={tile.top_anomalies[0].title_fr}>
          {tile.top_anomalies[0].title_fr}
        </span>
      )}
    </button>
  );
}

/* ── Composant principal ─────────────────────────────────────────────────── */

export default function PatrimoineHeatmap({ tiles = [], onOpenSite, loading = false, error = null }) {
  const navigate = useNavigate();

  // Filtres locaux
  const [fwFilter, setFwFilter]   = useState('');
  const [sevFilter, setSevFilter] = useState('');
  const [search, setSearch]       = useState('');
  const [sort, setSort]           = useState('risk');

  const filtered = useMemo(() => {
    let r = [...tiles];
    if (search) {
      const q = search.toLowerCase();
      r = r.filter(t => t.site_nom.toLowerCase().includes(q));
    }
    if (fwFilter)  r = r.filter(t => t.dominant_framework === fwFilter);
    if (sevFilter) r = r.filter(t => t.max_severity === sevFilter);
    if (sort === 'risk')      r.sort((a, b) => (b.total_risk_eur   ?? 0) - (a.total_risk_eur   ?? 0));
    if (sort === 'anomalies') r.sort((a, b) => (b.anomalies_count  ?? 0) - (a.anomalies_count  ?? 0));
    if (sort === 'score')     r.sort((a, b) => (a.completude_score ?? 0) - (b.completude_score ?? 0));
    return r;
  }, [tiles, search, fwFilter, sevFilter, sort]);

  const hasActiveFilters = !!(fwFilter || sevFilter || search);

  // V63-scale — Top 15 : sélectionner les sites les plus risqués après filtres
  const MAX_TILES = 15;
  const showTopBanner = filtered.length > MAX_TILES;
  const visibleTiles  = showTopBanner
    ? [...filtered]
        .sort((a, b) => (b.total_risk_eur ?? 0) - (a.total_risk_eur ?? 0))
        .slice(0, MAX_TILES)
    : filtered;

  /* ── État chargement ── */
  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <LayoutGrid size={14} className="text-gray-400" />
          <span className="text-sm font-semibold text-gray-500">Heatmap sites</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  /* ── État erreur ── */
  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-50 border border-gray-100 rounded-xl px-4 py-3">
        <AlertTriangle size={14} className="text-amber-400 shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  /* ── Vide (0 sites, ex : scope vide ou post-reset) ── */
  if (tiles.length === 0) {
    return (
      <div className="flex items-center justify-between bg-gray-50 border border-dashed border-gray-200 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <LayoutGrid size={14} className="shrink-0" />
          <span>Aucun site dans le scope</span>
        </div>
        <button
          onClick={() => navigate('/import')}
          className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-1.5 hover:bg-blue-100 transition"
        >
          <Upload size={12} /> Charger HELIOS
        </button>
      </div>
    );
  }

  /* ── Vue nominale ── */
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">

      {/* ── En-tête + Toolbar ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <LayoutGrid size={14} className="text-gray-500 shrink-0" />
        <span className="text-sm font-semibold text-gray-700">Heatmap sites</span>
        <span className="text-[10px] font-medium text-gray-400 bg-gray-100 rounded-full px-2 py-0.5 shrink-0">
          {tiles.length}
        </span>

        <div className="flex items-center gap-1.5 flex-wrap ml-auto">
          {/* Recherche par nom */}
          <div className="relative">
            <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Chercher…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-6 pr-2.5 py-1.5 text-xs border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 w-28"
            />
          </div>

          <FilterSelect options={FW_OPTIONS}   value={fwFilter}  onChange={setFwFilter}  label="Filtre framework" />
          <FilterSelect options={SEV_OPTIONS}  value={sevFilter} onChange={setSevFilter} label="Filtre sévérité"  />
          <FilterSelect options={SORT_OPTIONS} value={sort}      onChange={setSort}      label="Tri"             />

          {hasActiveFilters && (
            <button
              onClick={() => { setFwFilter(''); setSevFilter(''); setSearch(''); }}
              className="flex items-center gap-0.5 text-[10px] text-gray-400 hover:text-gray-600 transition"
            >
              <X size={10} /> Réinitialiser
            </button>
          )}
        </div>
      </div>

      {/* ── Bandeau Top-15 (discret, 1 ligne) ── */}
      {showTopBanner && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700">
          <span>
            Affichage&nbsp;: <strong>{visibleTiles.length}</strong> / {filtered.length} (Top risques)
          </span>
          <button
            onClick={() => document.getElementById('sites-table')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
            className="font-semibold underline underline-offset-2 hover:text-blue-900 transition shrink-0"
          >
            Voir tous les sites
          </button>
        </div>
      )}

      {/* ── Grille de tiles ── */}
      {filtered.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-3">Aucun site ne correspond aux filtres.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
          {visibleTiles.map(tile => (
            <SiteTile
              key={tile.site_id}
              tile={tile}
              allTiles={tiles}
              onOpenSite={onOpenSite}
            />
          ))}
        </div>
      )}
    </div>
  );
}
