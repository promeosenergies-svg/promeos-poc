/**
 * PROMEOS — Step 34 : Carte SVG des sites geolocalises.
 * Projection simplifiee France. Markers colores par statut conformite.
 * Clic → popup KPIs + CTA "Voir le site".
 */
import { useState, useMemo } from 'react';
import { MapPin, X } from 'lucide-react';

// ── France bounding box (lat/lng → SVG coords) ──────────────────────────────
const BOUNDS = { latMin: 41.3, latMax: 51.1, lngMin: -5.2, lngMax: 9.6 };
const SVG_W = 600;
const SVG_H = 600;

function project(lat, lng) {
  const x = ((lng - BOUNDS.lngMin) / (BOUNDS.lngMax - BOUNDS.lngMin)) * SVG_W;
  const y = ((BOUNDS.latMax - lat) / (BOUNDS.latMax - BOUNDS.latMin)) * SVG_H;
  return { x, y };
}

// ── Statut → couleur ────────────────────────────────────────────────────────
function getMarkerColor(site) {
  const score = site.compliance_score_composite ?? site.compliance_score ?? null;
  if (score === null || score === undefined) {
    // Fallback on statut_conformite
    if (site.statut_conformite === 'conforme') return '#10b981';
    if (site.statut_conformite === 'non_conforme') return '#ef4444';
    if (site.statut_conformite === 'a_risque') return '#f59e0b';
    return '#9ca3af';
  }
  if (score >= 70) return '#10b981';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

function getStatusLabel(site) {
  const score = site.compliance_score_composite ?? site.compliance_score ?? null;
  if (score === null || score === undefined) {
    if (site.statut_conformite === 'conforme') return 'Conforme';
    if (site.statut_conformite === 'non_conforme') return 'Non conforme';
    if (site.statut_conformite === 'a_risque') return 'A risque';
    return 'Non evalue';
  }
  if (score >= 70) return 'Conforme';
  if (score >= 40) return 'A risque';
  return 'Non conforme';
}

// ── France outline (simplified) ─────────────────────────────────────────────
const FRANCE_PATH =
  'M305,30 L340,35 L370,50 L400,55 L430,80 L460,95 L490,120 ' +
  'L510,150 L530,170 L540,200 L545,230 L540,260 L530,290 ' +
  'L510,320 L490,350 L470,380 L440,400 L410,420 L380,440 ' +
  'L350,455 L320,465 L290,470 L260,465 L230,450 L200,430 ' +
  'L175,410 L155,385 L140,360 L125,330 L115,300 L110,270 ' +
  'L115,240 L125,210 L140,180 L155,155 L175,130 L200,110 ' +
  'L225,90 L250,70 L275,50 L305,30 Z';

// ── Composant SitePopup ─────────────────────────────────────────────────────
function SitePopup({ site, onClose, onSiteClick }) {
  const score = site.compliance_score_composite ?? site.compliance_score ?? null;
  const grade = site.compliance_grade || null;
  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-3 min-w-[200px] text-sm z-50">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-gray-900 truncate pr-2">{site.nom}</h4>
        <button onClick={onClose} className="p-0.5 rounded hover:bg-gray-100 text-gray-400">
          <X size={14} />
        </button>
      </div>
      <div className="space-y-1 text-xs text-gray-600">
        {score !== null && (
          <p>
            Score : <span className="font-medium text-gray-900">{Math.round(score)}/100</span>
            {grade ? ` (${grade})` : ''}
          </p>
        )}
        {site.surface_m2 > 0 && <p>Surface : {site.surface_m2.toLocaleString('fr-FR')} m²</p>}
        {site.type && <p>Type : {site.type}</p>}
        {site.ville && (
          <p>
            {site.ville}
            {site.code_postal ? ` (${site.code_postal})` : ''}
          </p>
        )}
      </div>
      <button
        onClick={() => onSiteClick(site.id)}
        className="mt-2 w-full text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 rounded px-2 py-1.5 transition"
      >
        Voir le site →
      </button>
    </div>
  );
}

// ── Composant principal ─────────────────────────────────────────────────────
export default function SitesMap({ sites = [], onSiteClick }) {
  const [selectedSite, setSelectedSite] = useState(null);

  const { geoSites, missingCount, stats } = useMemo(() => {
    const geo = sites.filter((s) => s.latitude && s.longitude);
    const missing = sites.length - geo.length;
    const conformes = geo.filter((s) => {
      const sc = s.compliance_score_composite ?? s.compliance_score ?? null;
      if (sc !== null) return sc >= 70;
      return s.statut_conformite === 'conforme';
    }).length;
    const aRisque = geo.filter((s) => {
      const sc = s.compliance_score_composite ?? s.compliance_score ?? null;
      if (sc !== null) return sc >= 40 && sc < 70;
      return s.statut_conformite === 'a_risque';
    }).length;
    const nonConformes = geo.filter((s) => {
      const sc = s.compliance_score_composite ?? s.compliance_score ?? null;
      if (sc !== null) return sc < 40;
      return s.statut_conformite === 'non_conforme';
    }).length;
    const nonEvalues = geo.length - conformes - aRisque - nonConformes;
    return {
      geoSites: geo,
      missingCount: missing,
      stats: { conformes, aRisque, nonConformes, nonEvalues },
    };
  }, [sites]);

  const projected = useMemo(
    () =>
      geoSites.map((s) => ({
        ...s,
        ...project(s.latitude, s.longitude),
        color: getMarkerColor(s),
        statusLabel: getStatusLabel(s),
      })),
    [geoSites]
  );

  if (!sites.length) return null;

  return (
    <div className="space-y-2" data-testid="sites-map">
      {/* Summary */}
      <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
        <span className="font-medium text-gray-700">
          {geoSites.length} site{geoSites.length > 1 ? 's' : ''}
        </span>
        {stats.conformes > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> {stats.conformes} conforme
            {stats.conformes > 1 ? 's' : ''}
          </span>
        )}
        {stats.aRisque > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> {stats.aRisque} a risque
          </span>
        )}
        {stats.nonConformes > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> {stats.nonConformes} non conforme
            {stats.nonConformes > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* SVG Map */}
      <div
        className="relative bg-gray-50 rounded-xl border border-gray-200 overflow-hidden"
        style={{ height: '400px' }}
      >
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* France outline */}
          <path d={FRANCE_PATH} fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="1.5" />

          {/* Site markers */}
          {projected.map((s) => (
            <g
              key={s.id}
              className="cursor-pointer"
              onClick={() => setSelectedSite(s.id === selectedSite ? null : s.id)}
            >
              <circle cx={s.x} cy={s.y} r={8} fill={s.color} opacity={0.25} />
              <circle cx={s.x} cy={s.y} r={5} fill={s.color} stroke="white" strokeWidth="1.5" />
            </g>
          ))}
        </svg>

        {/* Popup overlay */}
        {selectedSite &&
          (() => {
            const s = projected.find((p) => p.id === selectedSite);
            if (!s) return null;
            const popupLeft = Math.min((s.x / SVG_W) * 100, 70);
            const popupTop = Math.min((s.y / SVG_H) * 100, 60);
            return (
              <div
                className="absolute"
                style={{
                  left: `${popupLeft}%`,
                  top: `${popupTop}%`,
                  transform: 'translate(10px, -50%)',
                }}
              >
                <SitePopup
                  site={s}
                  onClose={() => setSelectedSite(null)}
                  onSiteClick={onSiteClick}
                />
              </div>
            );
          })()}

        {/* Legend */}
        <div className="absolute bottom-3 left-3 flex items-center gap-3 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1.5 text-[10px] text-gray-600 shadow-sm border border-gray-100">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Conforme
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> A risque
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Non conforme
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-gray-400" /> Non evalue
          </span>
        </div>
      </div>

      {/* Missing coords warning */}
      {missingCount > 0 && (
        <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <MapPin size={13} className="shrink-0" />
          <span>
            {missingCount} site{missingCount > 1 ? 's' : ''} sans coordonnées. Complétez les
            coordonnées GPS pour voir tous vos sites sur la carte.
          </span>
        </div>
      )}
    </div>
  );
}
