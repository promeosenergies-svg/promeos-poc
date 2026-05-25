/**
 * CockpitBillingKpis — P0 cleanup cockpit (2026-05-25).
 *
 * Rend le bloc billing_kpis injecté par /api/cockpit/strategique
 * (cf. backend/services/billing_kpis_cockpit_service.py).
 *
 * 4 KPIs (toutes valeurs depuis le backend, doctrine §8.1) :
 *   1. Surfacturations à contester (€)
 *   2. Anomalies factures ouvertes (count)
 *   3. Anomalies par énergie (élec / gaz)
 *   4. Actions facturation ouvertes (count)
 *
 * 2 liens canoniques :
 *   - /bill-intel (vue Anomalies)
 *   - /centre-action?domain=facturation (file prioritaire Facturation)
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Receipt, AlertTriangle, Zap, Flame, ArrowRight } from 'lucide-react';

function formatEuros(value) {
  if (typeof value !== 'number' || Number.isNaN(value) || value <= 0) return null;
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(value) + ' €';
}

function Card({ icon: Icon, label, value, subtitle, source, link, linkLabel, testid }) {
  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 flex flex-col gap-2"
      data-testid={testid}
    >
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-gray-500">
        {Icon && <Icon size={14} className="text-gray-400" aria-hidden="true" />}
        {label}
      </div>
      <div className="text-2xl font-bold text-gray-900" data-testid={`${testid}-value`}>
        {value}
      </div>
      {subtitle && <p className="text-xs text-gray-600">{subtitle}</p>}
      <div className="flex items-center justify-between gap-2 mt-auto">
        <span className="text-[10px] text-gray-400 truncate" title={source}>
          {source}
        </span>
        {link && (
          <Link
            to={link}
            className="inline-flex items-center gap-1 text-xs font-medium text-cyan-700 hover:text-cyan-800 shrink-0"
            data-testid={`${testid}-link`}
          >
            {linkLabel} <ArrowRight size={12} aria-hidden="true" />
          </Link>
        )}
      </div>
    </div>
  );
}

/**
 * @param {object} props
 * @param {{ kpis: Array, links: object, _error?: string }|null} props.billingKpis
 *   — Payload `payload.billing_kpis` de /api/cockpit/strategique (SoT backend).
 */
export default function CockpitBillingKpis({ billingKpis }) {
  if (!billingKpis || !Array.isArray(billingKpis.kpis) || billingKpis.kpis.length === 0) {
    // Pas de bloc rendu si pas de KPIs (mode démo vide, ou backend en panne).
    return null;
  }

  const kpiById = Object.fromEntries(billingKpis.kpis.map((k) => [k.id, k]));
  const surfact = kpiById.surfacturations_a_contester;
  const anomalies = kpiById.anomalies_ouvertes;
  const parEnergie = kpiById.anomalies_par_energie;
  const actions = kpiById.actions_facturation_ouvertes;

  const energieValue = parEnergie?.value || { elec: 0, gaz: 0, inconnu: 0 };
  const energieDisplay =
    `${energieValue.elec || 0} élec · ${energieValue.gaz || 0} gaz` +
    (energieValue.inconnu > 0 ? ` · ${energieValue.inconnu} ?` : '');

  return (
    <section
      className="mt-4"
      data-testid="cockpit-billing-kpis"
      aria-label="Signaux Bill Intelligence"
    >
      <h3 className="mb-2 text-sm font-semibold text-gray-700 flex items-center gap-2">
        <Receipt size={16} className="text-cyan-600" aria-hidden="true" />
        Bill Intelligence — signaux factures
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {surfact && (
          <Card
            icon={Receipt}
            label="À contester"
            value={formatEuros(surfact.value) || '—'}
            subtitle={surfact.formula}
            source={`Source : ${surfact.source}`}
            link={surfact.link_to}
            linkLabel="Voir les factures"
            testid="billing-kpi-surfacturations"
          />
        )}
        {anomalies && (
          <Card
            icon={AlertTriangle}
            label="Anomalies ouvertes"
            value={anomalies.value}
            subtitle={anomalies.formula}
            source={`Source : ${anomalies.source}`}
            link={anomalies.link_to}
            linkLabel="Voir les anomalies"
            testid="billing-kpi-anomalies-ouvertes"
          />
        )}
        {parEnergie && (
          <Card
            icon={Zap}
            label="Anomalies par énergie"
            value={energieDisplay}
            subtitle={parEnergie.formula}
            source={`Source : ${parEnergie.source}`}
            link={parEnergie.link_to}
            linkLabel="Voir détails"
            testid="billing-kpi-anomalies-energie"
          />
        )}
        {actions && (
          <Card
            icon={Flame}
            label="Actions facturation"
            value={actions.value}
            subtitle={actions.formula}
            source={`Source : ${actions.source}`}
            link={actions.link_to}
            linkLabel="Ouvrir le plan"
            testid="billing-kpi-actions-facturation"
          />
        )}
      </div>
    </section>
  );
}
