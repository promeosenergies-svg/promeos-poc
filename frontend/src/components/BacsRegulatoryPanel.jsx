/**
 * PROMEOS — BACS Regulatory Panel
 * Affichage sobre et B2B du statut reglementaire BACS complet.
 * 6 axes : eligibilite, exigences R.175-3, exploitation, inspection, preuves, statut final.
 */
import { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Loader2,
} from 'lucide-react';
import { getBacsRegulatoryAssessment } from '../services/api';

const STATUS_CONFIG = {
  not_applicable: { label: 'Non concerne', cls: 'bg-gray-100 text-gray-500', icon: null },
  potentially_in_scope: { label: 'A evaluer', cls: 'bg-blue-100 text-blue-700', icon: Clock },
  in_scope_incomplete: {
    label: 'Incomplet',
    cls: 'bg-amber-100 text-amber-700',
    icon: AlertTriangle,
  },
  review_required: { label: 'Revue requise', cls: 'bg-red-100 text-red-700', icon: AlertTriangle },
  ready_for_internal_review: {
    label: 'Pret pour revue',
    cls: 'bg-green-100 text-green-700',
    icon: ShieldCheck,
  },
  not_evaluated: { label: 'Non evalue', cls: 'bg-gray-100 text-gray-500', icon: null },
};

const REQ_STATUS_ICON = {
  ok: { icon: CheckCircle2, cls: 'text-green-600' },
  partial: { icon: AlertTriangle, cls: 'text-amber-500' },
  absent: { icon: XCircle, cls: 'text-red-500' },
  not_demonstrated: { icon: XCircle, cls: 'text-gray-400' },
};

export default function BacsRegulatoryPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getBacsRegulatoryAssessment(siteId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Loader2 size={20} className="animate-spin mx-auto" />
      </div>
    );
  }

  if (!data || data.final_status === 'not_evaluated') {
    return (
      <div className="p-4 text-center text-sm text-gray-400">Aucun actif BACS pour ce site</div>
    );
  }

  const st = STATUS_CONFIG[data.final_status] || STATUS_CONFIG.not_evaluated;
  const StIcon = st.icon;
  const elig = data.eligibility || {};
  const func = data.functional_requirements || {};
  const expl = data.exploitation || {};
  const insp = data.inspection || {};
  const proofs = data.proofs || {};

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
          BACS Reglementaire
        </h3>
        <div className="flex items-center gap-2">
          <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${st.cls}`}>
            {StIcon && <StIcon size={12} className="inline mr-1" />}
            {st.label}
          </span>
        </div>
      </div>

      {/* Aide a la conformite banner */}
      <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-md">
        <AlertTriangle size={14} className="text-amber-600 mt-0.5 shrink-0" />
        <p className="text-[11px] text-amber-700">
          <span className="font-semibold">Aide a la conformite</span> — PROMEOS ne certifie pas la
          conformite BACS. Ce panneau aide a preparer la revue interne.
        </p>
      </div>

      {/* Eligibilite */}
      <Section title="Perimetre">
        <Row
          label="Assujetti"
          value={elig.in_scope === true ? 'Oui' : elig.in_scope === false ? 'Non' : 'A verifier'}
        />
        {elig.tier && <Row label="Seuil" value={elig.tier} />}
        {elig.putile_kw && <Row label="Putile" value={`${Math.round(elig.putile_kw)} kW`} />}
        {elig.deadline && (
          <Row label="Echeance" value={elig.deadline} warn={new Date(elig.deadline) < new Date()} />
        )}
        {elig.tri_exemption_possible && <Row label="Exemption TRI" value="Possible (> 10 ans)" />}
      </Section>

      {/* Exigences fonctionnelles */}
      <Section title={`Exigences R.175-3 (${func.ok_count || 0}/${func.total || 10})`}>
        {func.requirements &&
          Object.entries(func.requirements).map(([key, req]) => {
            const cfg = REQ_STATUS_ICON[req.status] || REQ_STATUS_ICON.not_demonstrated;
            const Icon = cfg.icon;
            return (
              <div key={key} className="flex items-center justify-between py-0.5">
                <span className="text-xs text-gray-600">{req.label}</span>
                <Icon size={14} className={cfg.cls} />
              </div>
            );
          })}
      </Section>

      {/* Exploitation */}
      <Section title="Exploitation / Maintenance">
        {expl.assessed ? (
          <>
            <Row
              label="Consignes ecrites"
              value={expl.written_procedures}
              ok={expl.written_procedures === 'ok'}
            />
            <Row
              label="Formation exploitant"
              value={expl.operator_trained ? `Oui (${expl.training_date || ''})` : 'Non'}
              ok={expl.operator_trained}
            />
            <Row
              label="Points de controle"
              value={expl.control_points_defined ? 'Definis' : 'Non definis'}
              ok={expl.control_points_defined}
            />
          </>
        ) : (
          <p className="text-xs text-red-500">Non evaluee</p>
        )}
      </Section>

      {/* Inspection */}
      <Section title="Inspection">
        {insp.has_inspection ? (
          <>
            <Row label="Derniere" value={insp.last_date || '—'} />
            <Row label="Prochaine" value={insp.next_due || '—'} warn={insp.overdue} />
            {insp.overdue && (
              <p className="text-[11px] text-red-600 font-medium">Inspection en retard</p>
            )}
            <Row
              label="Findings critiques"
              value={String(insp.critical_findings)}
              warn={insp.critical_findings > 0}
            />
            {insp.report_compliant === false && (
              <p className="text-[11px] text-red-600">Rapport non conforme</p>
            )}
          </>
        ) : (
          <p className="text-xs text-red-500">Aucune inspection completee</p>
        )}
      </Section>

      {/* Preuves */}
      <Section title={`Preuves (${proofs.count || 0} / ${proofs.expected_types?.length || 4})`}>
        {proofs.missing_types?.length > 0 ? (
          <div className="space-y-1">
            {proofs.missing_types.map((t) => (
              <div key={t} className="flex items-center gap-1.5 text-xs text-red-600">
                <XCircle size={12} /> {t}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-green-600">Toutes les preuves attendues sont presentes</p>
        )}
      </Section>

      {/* Blockers */}
      {data.blockers?.length > 0 && (
        <Section title="Blockers">
          {data.blockers.map((b, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-red-700 py-0.5">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" />
              <span>{b}</span>
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="border-t border-gray-100 pt-2">
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
        {title}
      </p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Row({ label, value, ok, warn }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-600">{label}</span>
      <span
        className={`font-medium ${warn ? 'text-red-600' : ok ? 'text-green-700' : 'text-gray-700'}`}
      >
        {value}
      </span>
    </div>
  );
}
