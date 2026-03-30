/**
 * PROMEOS — Section Mutualisation DT (Phase 3)
 * Affiche la simulation de mutualisation inter-sites pour un portefeuille.
 * Consomme GET /api/tertiaire/mutualisation (zero calcul metier frontend).
 */
import { useState, useEffect } from 'react';
import { BarChart3, TrendingDown, TrendingUp, Loader2, Info } from 'lucide-react';
import { Card, CardBody, Badge, KpiCard } from '../../ui';
import { EvidenceDrawer as GenericEvidenceDrawer } from '../../ui';
import { getMutualisation } from '../../services/api';
import { fmtEur, fmtKwh } from '../../utils/format';
import Explain from '../../ui/Explain';
import { buildMutualisationEvidence } from '../../pages/tertiaire/tertiaireEvidence';

export default function MutualisationSection({ orgId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  useEffect(() => {
    if (!orgId) return;
    setLoading(true);
    getMutualisation(orgId, 2030)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [orgId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-8 text-gray-400 justify-center">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Calcul mutualisation...</span>
      </div>
    );
  }

  if (!data || !data.sites || data.sites.length === 0) {
    return (
      <Card>
        <CardBody className="text-center py-6">
          <p className="text-sm text-gray-500">
            Aucune EFA avec donnees de reference — mutualisation non calculable.
          </p>
        </CardBody>
      </Card>
    );
  }

  const p = data.portefeuille || data;

  return (
    <div className="space-y-4" data-testid="mutualisation-section">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
        Simulation <Explain term="mutualisation_dt">mutualisation</Explain> — Jalon 2030 (−40 %)
      </h3>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Sites evalues" value={data.sites.length} icon={BarChart3} accent="blue" />
        <KpiCard
          label="Sites en surplus"
          value={p.nb_sites_surplus}
          icon={TrendingDown}
          accent="emerald"
        />
        <KpiCard
          label="Sites en deficit"
          value={p.nb_sites_deficit}
          icon={TrendingUp}
          accent="red"
        />
        <KpiCard
          label="Economie potentielle"
          value={fmtEur(p.economie_mutualisation_eur)}
          accent="emerald"
        />
      </div>

      {/* Badge portefeuille */}
      <div className="flex items-center gap-2">
        <Badge status={p.conforme_mutualise ? 'ok' : 'warn'}>
          {p.conforme_mutualise
            ? 'Portefeuille conforme en mutualise'
            : `Deficit residuel : ${fmtKwh(Math.abs(p.ecart_total_kwh))}`}
        </Badge>
      </div>

      {/* Tableau sites */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-gray-500 text-xs uppercase tracking-wide">
              <th className="text-left py-2 pr-4">Site</th>
              <th className="text-right py-2 px-3">Ref 2020</th>
              <th className="text-right py-2 px-3">Actuel</th>
              <th className="text-right py-2 px-3">Objectif</th>
              <th className="text-right py-2 px-3">Ecart</th>
              <th className="text-center py-2 pl-3">Statut</th>
            </tr>
          </thead>
          <tbody>
            {data.sites.map((s) => (
              <tr key={s.efa_id} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-medium text-gray-900">{s.site_nom}</td>
                <td className="py-2 px-3 text-right text-gray-600">{fmtKwh(s.reference_kwh)}</td>
                <td className="py-2 px-3 text-right text-gray-600">{fmtKwh(s.actuelle_kwh)}</td>
                <td className="py-2 px-3 text-right text-gray-600">{fmtKwh(s.objectif_kwh)}</td>
                <td
                  className={`py-2 px-3 text-right font-medium ${
                    s.ecart_kwh > 0 ? 'text-red-600' : 'text-green-600'
                  }`}
                >
                  {s.ecart_kwh > 0 ? '+' : ''}
                  {fmtKwh(s.ecart_kwh)}
                </td>
                <td className="py-2 pl-3 text-center">
                  <Badge
                    status={s.statut === 'surplus' ? 'ok' : s.statut === 'conforme' ? 'ok' : 'crit'}
                    size="xs"
                  >
                    {s.statut === 'surplus'
                      ? 'Surplus'
                      : s.statut === 'conforme'
                        ? 'Conforme'
                        : 'Deficit'}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Comparaison penalites */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardBody className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Sans mutualisation</p>
            <p className="text-lg font-bold text-red-600 mt-1">
              {fmtEur(p.penalite_sans_mutualisation_eur)}
            </p>
            <p className="text-xs text-gray-400">{p.nb_sites_deficit} site(s) penalise(s)</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Avec mutualisation</p>
            <p className="text-lg font-bold text-emerald-600 mt-1">
              {fmtEur(p.penalite_avec_mutualisation_eur)}
            </p>
            <p className="text-xs text-gray-400">
              {p.conforme_mutualise ? 'Aucune penalite' : '1 penalite residuelle'}
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Note pedagogique + evidence */}
      <div className="flex items-center justify-between">
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 flex items-start gap-2 flex-1">
          <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
          <p className="text-xs text-blue-700">
            La mutualisation permet de compenser les sites en retard avec ceux en avance au sein du
            meme portefeuille. Cette fonctionnalite sera disponible dans OPERAT prochainement —
            PROMEOS vous permet de l'anticiper.
          </p>
        </div>
        <button
          onClick={() => setEvidenceOpen(true)}
          className="ml-3 p-2 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 shrink-0"
          aria-label="Pourquoi ce chiffre ?"
        >
          ?
        </button>
      </div>

      {data && (
        <GenericEvidenceDrawer
          open={evidenceOpen}
          onClose={() => setEvidenceOpen(false)}
          evidence={buildMutualisationEvidence(
            data.sites?.length || 0,
            p.ecart_total_kwh,
            p.economie_mutualisation_eur
          )}
        />
      )}
    </div>
  );
}
