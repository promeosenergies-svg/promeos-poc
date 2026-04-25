/**
 * PROMEOS — CX Dashboard (admin plateforme)
 * Sprint CX 3 adoption réelle — P0.3
 *
 * Consomme :
 *   GET /api/admin/cx-dashboard       — vue générale events par org + inactive_orgs
 *   GET /api/admin/cx-dashboard/t2v   — Time-to-Value (p50/p90/p95 jours)
 *   GET /api/admin/cx-dashboard/iar   — Insight-to-Action Rate (+ is_capped)
 *   GET /api/admin/cx-dashboard/wau-mau — WAU/MAU stickiness (+ interpretation)
 *
 * Accès : DG_OWNER / DSI_ADMIN uniquement (hasPermission('admin')).
 */
import { useState, useEffect, useCallback } from 'react';
import { BarChart3, RefreshCw, Clock, Zap, Users, AlertTriangle } from 'lucide-react';
import { getCxDashboard, getT2V, getIAR, getWauMau } from '../../services/api/cxDashboard';
import { useAuth } from '../../contexts/AuthContext';
import {
  PageShell,
  Card,
  CardHeader,
  CardBody,
  EmptyState,
  Explain,
  Table,
  Thead,
  Tbody,
  Th,
  Tr,
  Td,
  Skeleton,
} from '../../ui';
import { useToast } from '../../ui/ToastProvider';

// ── Helpers tone (Color-Life : accent rouge uniquement pour seuils dépassés) ──

function t2vTone(days) {
  if (days == null) return 'neutral';
  if (days < 7) return 'good';
  if (days <= 14) return 'warn';
  return 'bad';
}

function wauMauTone(ratio) {
  if (ratio == null) return 'neutral';
  if (ratio >= 0.4) return 'good';
  if (ratio >= 0.3) return 'neutral';
  if (ratio >= 0.2) return 'warn';
  return 'bad';
}

const TONE_CLASS = {
  good: 'bg-green-50 border-green-200 text-green-900',
  warn: 'bg-amber-50 border-amber-200 text-amber-900',
  bad: 'bg-red-50 border-red-200 text-red-900',
  neutral: 'bg-white border-gray-200 text-gray-900',
};

function formatDays(v) {
  if (v == null) return '—';
  return `${v.toFixed(1)} j`;
}

function formatPct(v) {
  if (v == null) return '—';
  return `${Math.round(v * 1000) / 10} %`;
}

// ── Tiles North-Star ─────────────────────────────────────────────────────────

function NorthStarTile({ icon: Icon, label, explainTerm, value, hint, tone = 'neutral', badge }) {
  return (
    <div className={`rounded-lg border p-5 ${TONE_CLASS[tone]}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide opacity-70">
          <Icon size={14} />
          <Explain term={explainTerm}>{label}</Explain>
        </div>
        {badge && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
            {badge}
          </span>
        )}
      </div>
      <div className="mt-3 text-3xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1.5 text-xs opacity-80">{hint}</div>}
    </div>
  );
}

// ── Page principale ──────────────────────────────────────────────────────────

export default function CxDashboardPage() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();

  const [general, setGeneral] = useState(null);
  const [t2v, setT2v] = useState(null);
  const [iar, setIar] = useState(null);
  const [wau, setWau] = useState(null);
  const [loading, setLoading] = useState(true);

  const isAdmin = hasPermission('admin');

  const load = useCallback(() => {
    if (!isAdmin) return;
    setLoading(true);
    Promise.all([
      getCxDashboard(30).catch(() => null),
      getT2V(180).catch(() => null),
      getIAR(30).catch(() => null),
      getWauMau().catch(() => null),
    ])
      .then(([g, t, i, w]) => {
        setGeneral(g);
        setT2v(t);
        setIar(i);
        setWau(w);
      })
      .catch(() => toast('Erreur lors du chargement du CX dashboard', 'error'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  // ── Guard accès (DG_OWNER / DSI_ADMIN uniquement) ────────────────────────
  if (!isAdmin) {
    return (
      <PageShell icon={BarChart3} title="CX Dashboard">
        <EmptyState
          variant="error"
          title="Accès réservé à l'administration plateforme"
          text="Ce tableau de bord est réservé aux rôles DG_OWNER et DSI_ADMIN. Contactez votre administrateur si vous pensez devoir y accéder."
        />
      </PageShell>
    );
  }

  // ── Loading skeleton ─────────────────────────────────────────────────────
  if (loading && !general && !t2v && !iar && !wau) {
    return (
      <PageShell icon={BarChart3} title="CX Dashboard" subtitle="Chargement des drivers…">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </PageShell>
    );
  }

  // ── Données dérivées ─────────────────────────────────────────────────────
  const t2vP50 = t2v?.p50_days ?? null;
  const t2vP90 = t2v?.p90_days ?? null;
  const t2vP95 = t2v?.p95_days ?? null;
  const t2vSample = t2v?.sample_size ?? 0;

  const iarGlobal = iar?.global ?? {};
  const iarValue = iarGlobal.iar ?? null;
  const iarRaw = iarGlobal.iar_raw ?? null;
  const iarCapped = iarGlobal.is_capped === true;

  const wauRatio = wau?.stickiness_ratio ?? null;
  const wauInterp = wau?.interpretation ?? null;

  const byOrgEntries = Object.entries(general?.orgs ?? {});
  const topActiveOrgs = [...byOrgEntries]
    .sort((a, b) => (b[1].total || 0) - (a[1].total || 0))
    .slice(0, 5);
  const inactiveOrgs = general?.inactive_orgs ?? [];

  // Breakdown par org : merge events + T2V + IAR
  const t2vByOrg = t2v?.by_org ?? {};
  const iarByOrg = iar?.by_org ?? {};
  const orgIds = Array.from(
    new Set([
      ...Object.keys(general?.orgs ?? {}),
      ...Object.keys(t2vByOrg),
      ...Object.keys(iarByOrg),
    ])
  );

  return (
    <PageShell
      icon={BarChart3}
      title="CX Dashboard"
      subtitle="Drivers North-Star adoption réelle — usage interne PROMEOS"
      actions={
        <button
          type="button"
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm bg-white border border-gray-200 hover:bg-gray-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Actualiser
        </button>
      }
    >
      {/* ── 3 tiles North-Star ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <NorthStarTile
          icon={Clock}
          label="T2V (p50)"
          explainTerm="t2v"
          tone={t2vTone(t2vP50)}
          value={formatDays(t2vP50)}
          hint={
            t2vSample > 0
              ? `p90 ${formatDays(t2vP90)} · p95 ${formatDays(t2vP95)} · n=${t2vSample} users (fenêtre 180j)`
              : 'Aucun user avec action validée — échantillon insuffisant'
          }
        />
        <NorthStarTile
          icon={Zap}
          label="IAR"
          explainTerm="iar"
          tone="neutral"
          badge={iarCapped ? 'capped' : null}
          value={formatPct(iarValue)}
          hint={
            iarValue == null
              ? 'Aucun insight consulté — signal insuffisant'
              : iarCapped
                ? `brut ${formatPct(iarRaw)} (1 insight → N actions) · fenêtre 30j`
                : `${iarGlobal.actions_validated ?? 0} actions / ${iarGlobal.insights_consulted ?? 0} insights · fenêtre 30j`
          }
        />
        <NorthStarTile
          icon={Users}
          label="WAU/MAU"
          explainTerm="wau_mau"
          tone={wauMauTone(wauRatio)}
          value={formatPct(wauRatio)}
          hint={
            wauRatio == null
              ? 'signal insuffisant'
              : `WAU ${wau.wau} · MAU ${wau.mau} · ${wauInterp}`
          }
        />
      </div>

      {/* ── Orgs actives / inactives ───────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-gray-900">Top 5 orgs les plus actives</h3>
            <p className="text-xs text-gray-500 mt-0.5">Events CX sur les 30 derniers jours</p>
          </CardHeader>
          <CardBody>
            {topActiveOrgs.length === 0 ? (
              <EmptyState
                variant="empty"
                title="Aucune activité sur la fenêtre"
                text="Les events CX apparaîtront dès que les utilisateurs interagiront avec PROMEOS."
              />
            ) : (
              <ul className="space-y-2">
                {topActiveOrgs.map(([orgId, data]) => (
                  <li
                    key={orgId}
                    className="flex items-center justify-between text-sm border-b border-gray-50 pb-1.5 last:border-0"
                  >
                    <span className="font-mono text-xs text-gray-700 truncate">{orgId}</span>
                    <span className="font-semibold tabular-nums text-gray-900">
                      {data.total ?? 0}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle
                size={14}
                className={inactiveOrgs.length > 0 ? 'text-amber-500' : 'text-gray-400'}
              />
              <h3 className="text-sm font-semibold text-gray-900">Orgs inactives &gt; 10j</h3>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Dernière activité CX dépassant le seuil de réactivation
            </p>
          </CardHeader>
          <CardBody>
            {inactiveOrgs.length === 0 ? (
              <div className="text-xs text-green-700 bg-green-50 rounded p-2">
                Toutes les orgs actives ont interagi dans les 10 derniers jours.
              </div>
            ) : (
              <ul className="space-y-1.5">
                {inactiveOrgs.map((orgId) => (
                  <li
                    key={orgId}
                    className="flex items-center justify-between text-sm bg-amber-50 rounded px-2 py-1.5"
                  >
                    <span className="font-mono text-xs text-amber-900 truncate">{orgId}</span>
                    <span className="text-[10px] uppercase tracking-wide text-amber-700">
                      inactive
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>

      {/* ── Breakdown par org (T2V + IAR + events) ─────────────────────── */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-gray-900">Breakdown par organisation</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Croisement <Explain term="t2v" />, <Explain term="iar" /> et events CX par org_id
          </p>
        </CardHeader>
        <CardBody className="p-0">
          {orgIds.length === 0 ? (
            <div className="p-6">
              <EmptyState
                variant="empty"
                title="Aucune donnée par org"
                text="Le breakdown apparaîtra dès que les events CX, T2V ou IAR auront un échantillon."
              />
            </div>
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th>Org</Th>
                  <Th className="text-right">Events 30j</Th>
                  <Th className="text-right">T2V p50</Th>
                  <Th className="text-right">T2V p95</Th>
                  <Th className="text-right">IAR</Th>
                  <Th className="text-right">Insights / Actions</Th>
                </tr>
              </Thead>
              <Tbody>
                {orgIds.map((orgId) => {
                  const orgData = general?.orgs?.[orgId];
                  const t2vOrg = t2vByOrg[orgId];
                  const iarOrg = iarByOrg[orgId];
                  return (
                    <Tr key={orgId}>
                      <Td>
                        <span className="font-mono text-xs">{orgId}</span>
                      </Td>
                      <Td className="text-right tabular-nums">{orgData?.total ?? 0}</Td>
                      <Td className="text-right tabular-nums">{formatDays(t2vOrg?.p50_days)}</Td>
                      <Td className="text-right tabular-nums">{formatDays(t2vOrg?.p95_days)}</Td>
                      <Td className="text-right tabular-nums">
                        {formatPct(iarOrg?.iar)}
                        {iarOrg?.is_capped && (
                          <span className="ml-1 text-[10px] text-amber-600">capped</span>
                        )}
                      </Td>
                      <Td className="text-right text-xs text-gray-500 tabular-nums">
                        {iarOrg?.insights_consulted ?? 0} / {iarOrg?.actions_validated ?? 0}
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>
    </PageShell>
  );
}
