/**
 * PROMEOS — Carte interactive des sites (MapLibre GL JS)
 * Tuiles IGN Géoplateforme (Plan + Satellite) + clustering + popups
 * Remplace l'ancienne version SVG statique.
 */
import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapPin, Layers, Loader2, AlertTriangle } from 'lucide-react';

// ── Tile sources ────────────────────────────────────────────────────────────
const TILE_SOURCES = {
  plan: {
    label: 'Plan',
    url: 'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
  },
  satellite: {
    label: 'Satellite',
    url: 'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
  },
};

// ── Default center (France) ─────────────────────────────────────────────────
const FRANCE_CENTER = [2.35, 46.85];
const DEFAULT_ZOOM = 5.5;

// ── Compliance colors ───────────────────────────────────────────────────────
function getScoreColor(site) {
  const score = site.compliance_score_composite ?? site.compliance_score ?? null;
  if (score === null || score === undefined) {
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
    if (site.statut_conformite === 'a_risque') return 'À risque';
    return 'Non évalué';
  }
  if (score >= 70) return 'Conforme';
  if (score >= 40) return 'À risque';
  return 'Non conforme';
}

// ── Popup HTML builder ──────────────────────────────────────────────────────
function buildPopupHTML(site) {
  const score = site.compliance_score_composite ?? site.compliance_score ?? null;
  const color = getScoreColor(site);
  const label = getStatusLabel(site);
  const scoreText = score !== null && score !== undefined ? `${Math.round(score)}/100` : '';

  return `
    <div style="min-width:200px;font-family:system-ui,sans-serif;font-size:13px">
      <div style="font-weight:600;font-size:14px;margin-bottom:6px;color:#111">${site.nom || 'Site'}</div>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
        <span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block"></span>
        <span style="color:#555">${label}${scoreText ? ` — ${scoreText}` : ''}</span>
      </div>
      ${site.ville ? `<div style="color:#777;font-size:12px">${site.ville}${site.code_postal ? ` (${site.code_postal})` : ''}</div>` : ''}
      ${site.surface_m2 ? `<div style="color:#777;font-size:12px">Surface : ${Number(site.surface_m2).toLocaleString('fr-FR')} m²</div>` : ''}
      ${site.type ? `<div style="color:#777;font-size:12px">Type : ${site.type}</div>` : ''}
      <button onclick="window.__promeos_site_click(${site.id})"
        style="margin-top:8px;width:100%;padding:6px;background:#eff6ff;color:#2563eb;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:500">
        Voir le site →
      </button>
    </div>
  `;
}

// ── Main component ──────────────────────────────────────────────────────────
export default function SitesMap({ sites = [], onSiteClick, selectedSiteId = null }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(null);
  const [tileMode, setTileMode] = useState('plan');

  // Sites with coordinates
  const { geoSites, missingCount, stats } = useMemo(() => {
    const geo = sites.filter((s) => s.latitude && s.longitude);
    const missing = sites.length - geo.length;
    const conformes = geo.filter((s) => getScoreColor(s) === '#10b981').length;
    const aRisque = geo.filter((s) => getScoreColor(s) === '#f59e0b').length;
    const nonConformes = geo.filter((s) => getScoreColor(s) === '#ef4444').length;
    const nonEvalues = geo.length - conformes - aRisque - nonConformes;
    return {
      geoSites: geo,
      missingCount: missing,
      stats: { conformes, aRisque, nonConformes, nonEvalues },
    };
  }, [sites]);

  // GeoJSON
  const geojson = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: geoSites.map((s) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [s.longitude, s.latitude] },
        properties: {
          id: s.id,
          nom: s.nom || '',
          ville: s.ville || '',
          code_postal: s.code_postal || '',
          type: s.type || '',
          surface_m2: s.surface_m2 || 0,
          color: getScoreColor(s),
          statusLabel: getStatusLabel(s),
          compliance_score_composite: s.compliance_score_composite ?? s.compliance_score ?? null,
          statut_conformite: s.statut_conformite || '',
        },
      })),
    }),
    [geoSites]
  );

  // Global click handler for popup buttons
  useEffect(() => {
    window.__promeos_site_click = (id) => onSiteClick?.(id);
    return () => {
      delete window.__promeos_site_click;
    };
  }, [onSiteClick]);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    try {
      const map = new maplibregl.Map({
        container: containerRef.current,
        style: {
          version: 8,
          sources: {
            ign: {
              type: 'raster',
              tiles: [TILE_SOURCES.plan.url],
              tileSize: 256,
              attribution: '© IGN Géoplateforme',
            },
          },
          layers: [{ id: 'ign-tiles', type: 'raster', source: 'ign' }],
        },
        center: FRANCE_CENTER,
        zoom: DEFAULT_ZOOM,
        maxZoom: 18,
        minZoom: 3,
      });

      map.addControl(new maplibregl.NavigationControl(), 'top-right');

      map.on('load', () => {
        // Clustered source
        map.addSource('sites', {
          type: 'geojson',
          data: geojson,
          cluster: true,
          clusterMaxZoom: 14,
          clusterRadius: 50,
        });

        // Cluster circles
        map.addLayer({
          id: 'clusters',
          type: 'circle',
          source: 'sites',
          filter: ['has', 'point_count'],
          paint: {
            'circle-color': [
              'step',
              ['get', 'point_count'],
              '#60a5fa',
              10,
              '#3b82f6',
              30,
              '#1d4ed8',
            ],
            'circle-radius': ['step', ['get', 'point_count'], 18, 10, 24, 30, 30],
            'circle-stroke-width': 2,
            'circle-stroke-color': '#fff',
          },
        });

        // Cluster count labels
        map.addLayer({
          id: 'cluster-count',
          type: 'symbol',
          source: 'sites',
          filter: ['has', 'point_count'],
          layout: {
            'text-field': '{point_count_abbreviated}',
            'text-size': 13,
            'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
          },
          paint: { 'text-color': '#fff' },
        });

        // Individual site markers
        map.addLayer({
          id: 'site-markers',
          type: 'circle',
          source: 'sites',
          filter: ['!', ['has', 'point_count']],
          paint: {
            'circle-color': ['get', 'color'],
            'circle-radius': 7,
            'circle-stroke-width': 2,
            'circle-stroke-color': '#fff',
          },
        });

        // Halo for selected site
        map.addLayer({
          id: 'site-selected',
          type: 'circle',
          source: 'sites',
          filter: ['==', ['get', 'id'], -1],
          paint: {
            'circle-color': 'transparent',
            'circle-radius': 14,
            'circle-stroke-width': 3,
            'circle-stroke-color': '#2563eb',
          },
        });

        // Interactions — click cluster to zoom
        map.on('click', 'clusters', (e) => {
          const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
          if (!features.length) return;
          const clusterId = features[0].properties.cluster_id;
          map.getSource('sites').getClusterExpansionZoom(clusterId, (err, zoom) => {
            if (err) return;
            map.easeTo({ center: features[0].geometry.coordinates, zoom });
          });
        });

        // Click marker to show popup
        map.on('click', 'site-markers', (e) => {
          const feat = e.features[0];
          const coords = feat.geometry.coordinates.slice();
          const siteData = {
            id: feat.properties.id,
            nom: feat.properties.nom,
            ville: feat.properties.ville,
            code_postal: feat.properties.code_postal,
            type: feat.properties.type,
            surface_m2: feat.properties.surface_m2,
            compliance_score_composite:
              feat.properties.compliance_score_composite === 'null'
                ? null
                : Number(feat.properties.compliance_score_composite),
            statut_conformite: feat.properties.statut_conformite,
          };
          new maplibregl.Popup({ offset: 12, maxWidth: '260px' })
            .setLngLat(coords)
            .setHTML(buildPopupHTML(siteData))
            .addTo(map);
        });

        // Cursor
        map.on('mouseenter', 'clusters', () => {
          map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'clusters', () => {
          map.getCanvas().style.cursor = '';
        });
        map.on('mouseenter', 'site-markers', () => {
          map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'site-markers', () => {
          map.getCanvas().style.cursor = '';
        });

        setMapReady(true);
      });

      map.on('error', (e) => {
        console.warn('MapLibre error:', e.error?.message || e.message);
      });

      mapRef.current = map;
    } catch (err) {
      console.error('Map init error:', err);
      setMapError(err.message);
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        setMapReady(false);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update GeoJSON data when sites change
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const source = mapRef.current.getSource('sites');
    if (source) source.setData(geojson);
  }, [geojson, mapReady]);

  // Fit bounds to sites
  useEffect(() => {
    if (!mapReady || !mapRef.current || geoSites.length === 0) return;

    if (geoSites.length === 1) {
      mapRef.current.easeTo({ center: [geoSites[0].longitude, geoSites[0].latitude], zoom: 13 });
      return;
    }

    const bounds = new maplibregl.LngLatBounds();
    geoSites.forEach((s) => bounds.extend([s.longitude, s.latitude]));
    mapRef.current.fitBounds(bounds, { padding: 60, maxZoom: 14 });
  }, [geoSites, mapReady]);

  // Highlight selected site
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    mapRef.current.setFilter('site-selected', ['==', ['get', 'id'], selectedSiteId ?? -1]);

    if (selectedSiteId) {
      const site = geoSites.find((s) => s.id === selectedSiteId);
      if (site) {
        mapRef.current.easeTo({ center: [site.longitude, site.latitude], zoom: 13 });
      }
    }
  }, [selectedSiteId, geoSites, mapReady]);

  // Switch tile source
  const switchTiles = useCallback(
    (mode) => {
      if (!mapRef.current || !mapReady) return;
      setTileMode(mode);
      const source = mapRef.current.getSource('ign');
      if (source) {
        // MapLibre doesn't allow changing tiles directly, re-set the style
        const currentStyle = mapRef.current.getStyle();
        currentStyle.sources.ign.tiles = [TILE_SOURCES[mode].url];
        mapRef.current.setStyle(currentStyle);
      }
    },
    [mapReady]
  );

  if (!sites.length) return null;

  return (
    <div className="space-y-2" data-testid="sites-map">
      {/* Summary bar */}
      <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
        <span className="font-medium text-gray-700">
          {geoSites.length} site{geoSites.length > 1 ? 's' : ''} géolocalisé
          {geoSites.length > 1 ? 's' : ''}
        </span>
        {stats.conformes > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> {stats.conformes} conforme
            {stats.conformes > 1 ? 's' : ''}
          </span>
        )}
        {stats.aRisque > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> {stats.aRisque} à risque
          </span>
        )}
        {stats.nonConformes > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> {stats.nonConformes} non conforme
            {stats.nonConformes > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Map container */}
      <div
        className="relative bg-gray-50 rounded-xl border border-gray-200 overflow-hidden"
        style={{ height: '450px' }}
      >
        {/* Loading overlay */}
        {!mapReady && !mapError && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-50/80">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 size={18} className="animate-spin" />
              Chargement de la carte…
            </div>
          </div>
        )}

        {/* Error state */}
        {mapError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-gray-50 gap-2">
            <AlertTriangle size={24} className="text-amber-500" />
            <p className="text-sm text-gray-600">Impossible de charger la carte</p>
            <p className="text-xs text-gray-400">{mapError}</p>
          </div>
        )}

        {/* MapLibre container */}
        <div ref={containerRef} className="w-full h-full" />

        {/* Tile switcher */}
        {mapReady && (
          <div className="absolute top-3 left-3 z-10 flex rounded-lg overflow-hidden shadow-sm border border-gray-200">
            {Object.entries(TILE_SOURCES).map(([key, { label }]) => (
              <button
                key={key}
                onClick={() => switchTiles(key)}
                className={`px-3 py-1.5 text-xs font-medium transition ${
                  tileMode === key
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {key === 'satellite' && <Layers size={11} className="inline mr-1 -mt-0.5" />}
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Legend */}
        {mapReady && (
          <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1.5 text-[10px] text-gray-600 shadow-sm border border-gray-100">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" /> Conforme
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-400" /> À risque
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" /> Non conforme
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-400" /> Non évalué
            </span>
          </div>
        )}
      </div>

      {/* Missing coords warning */}
      {missingCount > 0 && (
        <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <MapPin size={13} className="shrink-0" />
          <span>
            {missingCount} site{missingCount > 1 ? 's' : ''} sans coordonnées GPS. Lancez le
            géocodage pour les localiser automatiquement.
          </span>
        </div>
      )}
    </div>
  );
}
