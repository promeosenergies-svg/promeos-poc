/**
 * PROMEOS V39 + V42 + V43 — Dashboard Tertiaire / OPERAT
 * Route: /conformite/tertiaire
 *
 * V42: section "Sites à traiter" (assujetti_probable + incomplètes)
 * V43: Drawer "Pourquoi ?", filtres par signal, raisons explicables
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useScope } from '../../contexts/ScopeContext';
import {
  Building2,
  AlertTriangle,
  Plus,
  Loader2,
  ArrowRight,
  ShieldAlert,
  MapPin,
  HelpCircle,
  X,
  Check,
  Filter,
} from 'lucide-react';
import { Download, Clock } from 'lucide-react';
import { PageShell, Card, CardBody, Button, Badge, KpiCard, Drawer } from '../../ui';
import {
  getTertiaireDashboard,
  getTertiaireEfas,
  getTertiaireSiteSignals,
} from '../../services/api';
import ExportOperatModal from '../../components/ExportOperatModal';
import MutualisationSection from '../../components/conformite/MutualisationSection';
import DtProgressMultiSite from '../../components/conformite/DtProgressMultiSite';
import Explain from '../../ui/Explain';
import ConformiteTertiaireSol from '../ConformiteTertiaireSol';

const STATUS_LABELS = {
  active: 'Active',
  draft: 'Brouillon',
  closed: 'Fermée',
};

const STATUS_VARIANTS = {
  active: 'ok',
  draft: 'neutral',
  closed: 'neutral',
};

// V43: Signal labels FR
const SIGNAL_LABELS = {
  assujetti_probable: 'Assujetti probable',
  a_verifier: 'À vérifier',
  non_concerne: 'Non concerné',
};

const SIGNAL_BADGE_VARIANTS = {
  assujetti_probable: 'warn',
  a_verifier: 'info',
  non_concerne: 'ok',
};

// V43: Missing field labels FR
const MISSING_FIELD_LABELS = {
  surface: 'Surface',
  usage_site: 'Usage',
  batiments: 'Bâtiments',
  surface_batiment: 'Surfaces bâtiment',
  code_naf: 'Code NAF',
};

export default function TertiaireDashboardPage() {
  const navigate = useNavigate();
  const { selectedSiteId } = useScope();
  const [dashboard, setDashboard] = useState(null);
  const [efas, setEfas] = useState([]);
  const [siteSignals, setSiteSignals] = useState(null);
  const [loading, setLoading] = useState(true);

  // V43: Drawer state
  const [whySite, setWhySite] = useState(null);

  // V113: Export OPERAT modal
  const [showExportModal, setShowExportModal] = useState(false);

  // V43: Filter state
  const [signalFilter, setSignalFilter] = useState(null); // null = all
  const [uncoveredOnly, setUncoveredOnly] = useState(false);
  const [missingFieldFilter, setMissingFieldFilter] = useState(null);

  const fetchData = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    const params = selectedSiteId ? { site_id: selectedSiteId } : {};
    Promise.all([
      getTertiaireDashboard(params).catch(() => null),
      getTertiaireEfas(params).catch(() => ({ efas: [] })),
      getTertiaireSiteSignals(params).catch(() => null),
    ]).then(([dash, efaData, signals]) => {
      if (!cancelled) {
        setDashboard(dash);
        setEfas(efaData?.efas ?? []);
        setSiteSignals(signals);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedSiteId]);

  useEffect(() => {
    const cleanup = fetchData();
    return cleanup;
  }, [fetchData]);

  // V43: Filtered sites — chips filter the "Sites à traiter" list directly
  const filteredSites = useMemo(() => {
    if (!siteSignals?.sites) return [];
    let sites = siteSignals.sites;
    if (signalFilter || uncoveredOnly || missingFieldFilter) {
      if (signalFilter) sites = sites.filter((s) => s.signal === signalFilter);
      if (uncoveredOnly) sites = sites.filter((s) => !s.is_covered);
      if (missingFieldFilter)
        sites = sites.filter((s) => s.missing_fields?.includes(missingFieldFilter));
    } else {
      // Default: show only actionable sites (assujetti probable uncovered + incomplete à vérifier)
      sites = sites.filter(
        (s) =>
          (s.signal === 'assujetti_probable' && !s.is_covered) ||
          (s.signal === 'a_verifier' && !s.data_complete)
      );
    }
    return sites;
  }, [siteSignals, signalFilter, uncoveredOnly, missingFieldFilter]);

  const hasActiveFilters = signalFilter || uncoveredOnly || missingFieldFilter;

  if (loading) {
    return (
      <PageShell title="Décret tertiaire / OPERAT" subtitle="Chargement…">
        <div className="flex items-center justify-center gap-2 py-16 text-gray-400">
          <Loader2 size={20} className="animate-spin" />
          <span>Chargement…</span>
        </div>
      </PageShell>
    );
  }

  const kpis = dashboard || {
    total_efa: 0,
    active: 0,
    draft: 0,
    closed: 0,
    open_issues: 0,
    critical_issues: 0,
  };

  const daysToOperat = Math.max(0, Math.ceil((new Date('2026-09-30') - new Date()) / 86_400_000));

  return (
    <PageShell
      title="Décret tertiaire / OPERAT"
      subtitle={`${kpis.total_efa} EFA enregistrée${kpis.total_efa > 1 ? 's' : ''}`}
      hideHeader
      actions={
        <Button size="sm" variant="secondary" onClick={() => setShowExportModal(true)}>
          <Download size={14} className="mr-1" /> Export OPERAT
        </Button>
      }
    >
      {/* Lot 6 Phase 4 — ConformiteTertiaireSol hero Pattern A injecté
          top. Legacy body (DtProgressMultiSite + Sites à traiter +
          EFA list + MutualisationSection + ExportOperatModal +
          Drawer "Pourquoi ?") préservé intégralement dessous. */}
      <ConformiteTertiaireSol dashboard={dashboard} isLoading={loading} />

      {/* Empty state when no EFA */}
      {kpis.total_efa === 0 && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              Aucune EFA enregistrée pour ce périmètre
            </p>
            <p className="text-xs text-amber-600 mt-1">
              Importez vos déclarations OPERAT ou ajoutez manuellement vos Entités Fonctionnelles
              Assujetties pour suivre votre conformité Décret Tertiaire.
            </p>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="EFA enregistrees" value={kpis.total_efa} icon={Building2} accent="blue" />
        <KpiCard
          label="Anomalies ouvertes"
          value={kpis.open_issues}
          icon={AlertTriangle}
          accent={kpis.open_issues > 0 ? 'amber' : 'slate'}
          onClick={() => navigate('/conformite/tertiaire/anomalies')}
        />
        <KpiCard
          label="Issues critiques"
          value={kpis.critical_issues}
          icon={ShieldAlert}
          accent={kpis.critical_issues > 0 ? 'red' : 'slate'}
        />
        <KpiCard
          label="Deadline OPERAT"
          value={`J-${daysToOperat}`}
          icon={Clock}
          accent={daysToOperat < 90 ? 'red' : 'amber'}
        />
      </div>

      {/* Vue multi-site trajectoire DT */}
      <div className="mt-6">
        <DtProgressMultiSite orgId={efas[0]?.org_id || 1} />
      </div>

      {/* V42+V43: Sites à traiter */}
      {siteSignals && siteSignals.total_sites > 0 && (
        <div className="mt-6" data-testid="sites-a-traiter">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Sites à traiter
            </h3>
            {siteSignals.total_sites > 0 && (
              <span className="text-xs text-gray-400">
                {siteSignals.total_sites} site{siteSignals.total_sites > 1 ? 's' : ''} analysé
                {siteSignals.total_sites > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* V43: Filter chips */}
          <div className="flex flex-wrap items-center gap-2 mb-3" data-testid="signal-filters">
            <Filter size={14} className="text-gray-400 shrink-0" />
            {Object.entries(SIGNAL_LABELS).map(([key, label]) => {
              const count = siteSignals.counts?.[key] ?? 0;
              const active = signalFilter === key;
              return (
                <button
                  key={key}
                  onClick={() => setSignalFilter(active ? null : key)}
                  data-testid={`filter-${key}`}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                    active
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {label} ({count})
                </button>
              );
            })}
            <button
              onClick={() => setUncoveredOnly(!uncoveredOnly)}
              data-testid="filter-uncovered"
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                uncoveredOnly
                  ? 'bg-amber-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Sans EFA
            </button>
            {/* Missing field filters */}
            {siteSignals.top_missing_fields &&
              Object.keys(siteSignals.top_missing_fields).length > 0 && (
                <>
                  <span className="text-gray-300">|</span>
                  {Object.entries(siteSignals.top_missing_fields).map(([field, count]) => {
                    const active = missingFieldFilter === field;
                    return (
                      <button
                        key={field}
                        onClick={() => setMissingFieldFilter(active ? null : field)}
                        data-testid={`filter-missing-${field}`}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                          active
                            ? 'bg-red-600 text-white'
                            : 'bg-red-50 text-red-600 hover:bg-red-100'
                        }`}
                      >
                        {MISSING_FIELD_LABELS[field] || field} ({count})
                      </button>
                    );
                  })}
                </>
              )}
            {hasActiveFilters && (
              <button
                onClick={() => {
                  setSignalFilter(null);
                  setUncoveredOnly(false);
                  setMissingFieldFilter(null);
                }}
                className="text-xs text-gray-400 hover:text-gray-600 underline"
              >
                Réinitialiser
              </button>
            )}
          </div>

          {/* Site cards */}
          <div className="space-y-2">
            {filteredSites.map((site) => (
              <div
                key={site.site_id}
                className={`flex items-center justify-between rounded-lg border p-3 ${
                  site.signal === 'assujetti_probable'
                    ? 'border-amber-200 bg-amber-50/50'
                    : site.signal === 'a_verifier'
                      ? 'border-blue-200 bg-blue-50/30'
                      : 'border-gray-200 bg-white'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <MapPin
                    size={16}
                    className={
                      site.signal === 'assujetti_probable'
                        ? 'text-amber-500 shrink-0'
                        : site.signal === 'a_verifier'
                          ? 'text-blue-400 shrink-0'
                          : 'text-gray-400 shrink-0'
                    }
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900 truncate">{site.site_nom}</p>
                      <Badge
                        status={SIGNAL_BADGE_VARIANTS[site.signal]}
                        className="text-[10px] shrink-0"
                      >
                        {SIGNAL_LABELS[site.signal]}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-500">
                      {site.surface_tertiaire_m2
                        ? `${Math.round(site.surface_tertiaire_m2).toLocaleString('fr-FR')} m²`
                        : 'Surface non renseignée'}
                      {site.ville ? ` · ${site.ville}` : ''}
                      {' · '}
                      {site.nb_batiments} bâtiment{site.nb_batiments > 1 ? 's' : ''}
                    </p>
                    {/* V43: missing fields inline */}
                    {site.missing_fields && site.missing_fields.length > 0 && (
                      <p className="text-[10px] text-red-500 mt-0.5">
                        Données manquantes :{' '}
                        {site.missing_fields.map((f) => MISSING_FIELD_LABELS[f] || f).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {/* V43: Why button */}
                  <button
                    onClick={() => setWhySite(site)}
                    className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
                    aria-label="Pourquoi ce classement ?"
                    data-testid={`why-btn-${site.site_id}`}
                  >
                    <HelpCircle size={16} className="text-gray-400" />
                  </button>
                  {site.recommended_cta && (
                    <Button
                      size="xs"
                      variant="secondary"
                      onClick={() =>
                        navigate(
                          site.recommended_cta.to ||
                            `/conformite/tertiaire/wizard?site_id=${site.site_id}`
                        )
                      }
                    >
                      {site.recommended_cta.label_fr} <ArrowRight size={12} />
                    </Button>
                  )}
                </div>
              </div>
            ))}
            {filteredSites.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-4">
                Aucun site ne correspond aux filtres sélectionnés.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Actions rapides */}
      <div className="flex items-center gap-3 mt-6">
        <Button
          data-testid="btn-nouvelle-efa"
          onClick={() => navigate('/conformite/tertiaire/wizard')}
        >
          <Plus size={16} /> Nouvelle EFA
        </Button>
        <Button variant="secondary" onClick={() => navigate('/conformite/tertiaire/anomalies')}>
          Voir les anomalies <ArrowRight size={14} />
        </Button>
      </div>

      {/* Liste EFA */}
      <div className="mt-6 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          <Explain term="efa">Entités Fonctionnelles Assujetties</Explain>
        </h3>
        {efas.length === 0 ? (
          <Card>
            <CardBody className="text-center py-8">
              <Building2 size={32} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Aucune EFA enregistrée</p>
              <p className="text-xs text-gray-400 mt-1">Créez votre première EFA via l'assistant</p>
              <Button
                size="sm"
                className="mt-4"
                data-testid="btn-creer-efa-empty"
                onClick={() => navigate('/conformite/tertiaire/wizard')}
              >
                Créer une EFA
              </Button>
            </CardBody>
          </Card>
        ) : (
          <div className="space-y-2">
            {efas.map((efa) => (
              <button
                key={efa.id}
                onClick={() => navigate(`/conformite/tertiaire/efa/${efa.id}`)}
                className="w-full text-left rounded-lg border border-gray-200 bg-white p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <Building2 size={18} className="text-gray-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{efa.nom}</p>
                      <p className="text-xs text-gray-400">
                        {efa.role_assujetti ? `Rôle : ${efa.role_assujetti}` : ''}
                        {efa.reporting_start ? ` — Début : ${efa.reporting_start}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={STATUS_VARIANTS[efa.statut] || 'neutral'} size="xs">
                      {STATUS_LABELS[efa.statut] || efa.statut}
                    </Badge>
                    <ArrowRight size={14} className="text-gray-400" />
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Mutualisation (Phase 3) */}
      {kpis.total_efa > 0 && (
        <div className="mt-6">
          <MutualisationSection orgId={efas[0]?.org_id || 1} />
        </div>
      )}

      {/* V43: Drawer "Pourquoi ce classement ?" */}
      <Drawer open={!!whySite} onClose={() => setWhySite(null)} title="Pourquoi ce classement ?">
        {whySite && (
          <div className="space-y-5" data-testid="why-drawer-content">
            {/* Site name + signal badge */}
            <div>
              <p className="text-base font-semibold text-gray-900">{whySite.site_nom}</p>
              {whySite.ville && <p className="text-sm text-gray-500">{whySite.ville}</p>}
              <div className="mt-2">
                <Badge status={SIGNAL_BADGE_VARIANTS[whySite.signal]}>
                  {SIGNAL_LABELS[whySite.signal]}
                </Badge>
              </div>
            </div>

            {/* Rules applied */}
            {whySite.rules_applied && whySite.rules_applied.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                  Règles appliquées
                </h4>
                <div className="space-y-1.5" data-testid="why-rules">
                  {whySite.rules_applied.map((rule, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      {rule.ok ? (
                        <Check size={14} className="text-green-500 shrink-0 mt-0.5" />
                      ) : (
                        <X size={14} className="text-red-400 shrink-0 mt-0.5" />
                      )}
                      <span className={rule.ok ? 'text-gray-700' : 'text-gray-500'}>
                        {rule.label_fr}
                        {rule.value != null && (
                          <span className="text-gray-400 ml-1">
                            (
                            {typeof rule.value === 'number'
                              ? rule.value.toLocaleString('fr-FR')
                              : rule.value}
                            )
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reasons FR */}
            {whySite.reasons_fr && whySite.reasons_fr.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                  Constats
                </h4>
                <ul className="space-y-1" data-testid="why-reasons">
                  {whySite.reasons_fr.map((reason, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-gray-300 shrink-0" />
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Missing fields + CTA */}
            {whySite.missing_fields && whySite.missing_fields.length > 0 && (
              <div className="rounded-lg border border-red-100 bg-red-50/50 p-3">
                <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">
                  À compléter
                </h4>
                <ul className="space-y-1 mb-3">
                  {whySite.missing_fields.map((field, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-red-600">
                      <AlertTriangle size={12} className="shrink-0" />
                      {MISSING_FIELD_LABELS[field] || field}
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setWhySite(null);
                    navigate(
                      whySite.recommended_cta?.to || `/patrimoine?site_id=${whySite.site_id}`
                    );
                  }}
                >
                  Compléter le patrimoine <ArrowRight size={14} />
                </Button>
              </div>
            )}

            {/* CTA principal */}
            {whySite.recommended_cta && whySite.recommended_next_step === 'creer_efa' && (
              <Button
                className="w-full"
                onClick={() => {
                  setWhySite(null);
                  navigate(whySite.recommended_cta.to);
                }}
              >
                {whySite.recommended_cta.label_fr} <ArrowRight size={14} />
              </Button>
            )}

            {/* Disclaimer */}
            <div className="rounded-md bg-gray-50 border border-gray-200 p-3">
              <p className="text-xs text-gray-500" data-testid="why-disclaimer">
                Heuristique V1 — à confirmer par analyse réglementaire. Les règles ci-dessus sont
                dérivées automatiquement des données patrimoniales renseignées.
              </p>
            </div>
          </div>
        )}
      </Drawer>

      {/* V113: Export OPERAT modal */}
      <ExportOperatModal open={showExportModal} onClose={() => setShowExportModal(false)} />
    </PageShell>
  );
}
