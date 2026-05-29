/**
 * PROMEOS — Section Mutualisation DT (Phase 3 · enrichi S3 P0 juridique 2026-05-28).
 *
 * Affiche la simulation de mutualisation inter-sites + le bloc « Groupe
 * de structures » (Art. 14 arrêté 10/04/2020 modifié, R.174-31 + L.174-1
 * CCH). Consomme :
 *   - GET /api/tertiaire/mutualisation (simulation, déjà existant)
 *   - GET /api/tertiaire/mutualisation/groups (Sprint S3)
 *
 * Doctrine §8.1 zero business logic FE — toutes les règles I1-I5 sont
 * portées backend (cf. tertiaire_groupe_structures_service.py). Le FE
 * affiche le statut et propose les CTA conditionnels.
 */
import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingDown,
  TrendingUp,
  Loader2,
  Info,
  ShieldCheck,
  AlertTriangle,
  Download,
  FileText,
} from 'lucide-react';
import { Card, CardBody, Badge, KpiCard } from '../../ui';
import { EvidenceDrawer as GenericEvidenceDrawer } from '../../ui';
import { getMutualisation, listGroupeStructures, buildExportTable1bUrl } from '../../services/api';
import { fmtEur, fmtKwh } from '../../utils/format';
import Explain from '../../ui/Explain';
import { buildMutualisationEvidence } from '../../pages/tertiaire/tertiaireEvidence';

// S3 — libellés FR canoniques pour le lifecycle du groupe de structures.
// (Source : doctrine S3, cf. crosscheck_legifrance_mutualisation_art14.)
const GROUPE_STATUS_LABEL = {
  draft: { label: 'Brouillon', tone: 'gray', opposable: false },
  pending_validation: {
    label: 'En attente validation représentant légal',
    tone: 'amber',
    opposable: false,
  },
  validated: { label: 'Validé · opposable', tone: 'emerald', opposable: true },
  archived: { label: 'Archivé', tone: 'gray', opposable: false },
};

export default function MutualisationSection({ orgId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  // S3 — Groupes de structures (Art. 14)
  const [groupes, setGroupes] = useState([]);
  const [groupesLoading, setGroupesLoading] = useState(true);

  useEffect(() => {
    if (!orgId) return;
    setLoading(true);
    getMutualisation(orgId, 2030)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [orgId]);

  useEffect(() => {
    if (!orgId) return;
    setGroupesLoading(true);
    listGroupeStructures(orgId)
      .then((g) => setGroupes(Array.isArray(g) ? g : []))
      .catch(() => setGroupes([]))
      .finally(() => setGroupesLoading(false));
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

      {/* Disclaimer reglementaire — toujours affiche */}
      <div
        className="flex items-start gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800"
        data-testid="mutualisation-disclaimer"
      >
        <Info size={14} className="text-amber-500 shrink-0 mt-0.5" />
        <span>
          {data.disclaimer ||
            "Simulation uniquement — La fonctionnalité de mutualisation n'est pas encore disponible dans OPERAT (2026). PROMEOS anticipe cette fonctionnalité pour préparer votre stratégie patrimoniale."}
        </span>
      </div>

      {/* S3 — Bloc « Groupe de structures » (Art. 14 §1) */}
      <div data-testid="groupe-structures-bloc" className="border border-gray-200 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-gray-500" />
            Groupe de structures
          </h4>
          <span className="text-[10px] text-gray-400">
            Module OPERAT mutualisation : préparation du dossier
          </span>
        </div>

        {groupesLoading ? (
          <p className="text-xs text-gray-400">Chargement des groupes…</p>
        ) : groupes.length === 0 ? (
          <div className="text-xs text-gray-500">
            <p>
              Aucun groupe de structures constitué pour le moment. Pour rendre la mutualisation
              opposable au contrôle décennal, créez un groupe et collectez la validation du
              représentant légal de chaque EFA membre.
            </p>
            <p className="text-[10px] text-gray-400 mt-1">
              Source : Article 14 §1 al.2 de l'arrêté du 10 avril 2020 modifié — l'intégration d'une
              EFA dans le périmètre nécessite la validation de son représentant légal.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {groupes.map((g) => {
              const cfg = GROUPE_STATUS_LABEL[g.status] || GROUPE_STATUS_LABEL.draft;
              const memberCount = (g.membres || []).filter((m) => !m.deleted_at).length;
              const rlValidatedCount = (g.membres || []).filter(
                (m) => !m.deleted_at && m.representant_legal_status === 'validated'
              ).length;
              const allRlOk = memberCount > 0 && rlValidatedCount === memberCount;
              return (
                <li
                  key={g.id}
                  className="flex items-start gap-3 p-2 bg-gray-50 rounded border border-gray-100"
                  data-testid={`groupe-structures-row-${g.id}`}
                >
                  <FileText size={14} className="text-gray-400 mt-1 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-gray-800 truncate">{g.nom}</span>
                      <Badge
                        status={
                          cfg.tone === 'emerald' ? 'ok' : cfg.tone === 'amber' ? 'warn' : 'info'
                        }
                        size="xs"
                      >
                        {cfg.label}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      {memberCount} EFA · {rlValidatedCount}/{memberCount} validation(s)
                      représentant légal
                    </p>
                    {!cfg.opposable && memberCount > 0 && (
                      <p
                        className="text-[11px] text-amber-700 mt-1 flex items-center gap-1"
                        data-testid={`groupe-warning-${g.id}`}
                      >
                        <AlertTriangle size={11} />
                        Groupe non opposable — collectez la validation du représentant légal de
                        chaque EFA avant le contrôle décennal (Art. 14 §1 al.2).
                      </p>
                    )}
                  </div>
                  {allRlOk && cfg.opposable ? (
                    <a
                      href={buildExportTable1bUrl(g.id, orgId)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-900 px-2 py-1 rounded border border-emerald-200 bg-white shrink-0"
                      data-testid={`groupe-export-${g.id}`}
                      title="Télécharger l'export Table 1B Annexe IV (CSV)"
                    >
                      <Download size={12} />
                      Exporter Table 1B
                    </a>
                  ) : (
                    <span
                      className="inline-flex items-center gap-1 text-xs text-gray-400 px-2 py-1 rounded border border-gray-200 shrink-0"
                      data-testid={`groupe-export-disabled-${g.id}`}
                      title="Export disponible une fois toutes les validations RL collectées"
                    >
                      <Download size={12} />
                      Export indisponible
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

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
