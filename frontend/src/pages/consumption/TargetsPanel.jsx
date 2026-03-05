/**
 * PROMEOS — TargetsPanel (extracted from ConsumptionExplorerPage)
 * Objectifs & Budgets: CRUD targets, progression chart, variance decomposition.
 */
import { useState, useCallback, useEffect } from 'react';
import { Plus, Trash2, Save, X, AlertTriangle, CheckCircle } from 'lucide-react';
import { Bar } from 'recharts';
import { Card, CardBody, Button } from '../../ui';
import { SkeletonCard } from '../../ui';
import { track } from '../../services/tracker';
import {
  getConsumptionTargets,
  createConsumptionTarget,
  deleteConsumptionTarget,
  getTargetsProgressionV2,
} from '../../services/api';
import ExplorerChart from './ExplorerChart';
import LayerToggle from './LayerToggle';
import ObjectivesLayer from './layers/ObjectivesLayer';
import { ALERT_COLOR } from './constants';

const MONTH_NAMES = [
  'Jan',
  'Fev',
  'Mar',
  'Avr',
  'Mai',
  'Jun',
  'Jul',
  'Aou',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

export default function TargetsPanel({
  siteId,
  energyType,
  toast,
  initialTargets,
  initialProgression,
  onRefreshMotor,
}) {
  const [targets, setTargets] = useState(initialTargets || []);
  const [progression, setProgression] = useState(initialProgression || null);
  const [loading, setLoading] = useState(false);
  const [year, setYear] = useState(new Date().getFullYear());
  const [showAdd, setShowAdd] = useState(false);
  const [newTarget, setNewTarget] = useState({ month: 1, target_kwh: '', target_eur: '' });

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [t, p] = await Promise.all([
        getConsumptionTargets(siteId, energyType, year),
        getTargetsProgressionV2(siteId, energyType, year),
      ]);
      setTargets(t);
      setProgression(p);
      track('targets_loaded', { site_id: siteId, year, energy_type: energyType });
    } catch (e) {
      toast?.('Erreur chargement objectifs', 'error');
    } finally {
      setLoading(false);
    }
  }, [siteId, year, energyType, toast]);

  // Skip initial fetch if motor already provided data (for current year)
  useEffect(() => {
    if (!initialTargets) load();
  }, [load, initialTargets]);

  const handleAdd = async () => {
    try {
      await createConsumptionTarget({
        site_id: siteId,
        energy_type: energyType,
        period: 'monthly',
        year,
        month: newTarget.month,
        target_kwh: parseFloat(newTarget.target_kwh) || null,
        target_eur: parseFloat(newTarget.target_eur) || null,
      });
      setShowAdd(false);
      setNewTarget({ month: 1, target_kwh: '', target_eur: '' });
      load();
      onRefreshMotor?.();
    } catch (e) {
      toast?.('Erreur ajout objectif', 'error');
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteConsumptionTarget(id);
      load();
      onRefreshMotor?.();
    } catch (e) {
      toast?.('Erreur suppression objectif', 'error');
    }
  };

  if (loading) return <SkeletonCard rows={6} />;

  const alert = progression?.alert;
  const alertConf = ALERT_COLOR[alert] || ALERT_COLOR.on_track;

  const chartData = (progression?.months || []).map((m) => ({
    name: MONTH_NAMES[m.month - 1],
    objectif: m.target_kwh,
    reel: m.actual_kwh,
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Objectifs & Budgets</h3>
        <div className="flex items-center gap-2">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="text-sm border rounded px-2 py-1"
          >
            {[2024, 2025, 2026].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <Button size="sm" variant="ghost" onClick={() => setShowAdd(!showAdd)}>
            <Plus size={14} className="mr-1" /> Objectif
          </Button>
        </div>
      </div>

      {/* Alert banner */}
      {progression && (
        <div className={`${alertConf.bg} ${alertConf.border} border rounded-lg p-3`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {alert === 'on_track' ? (
                <CheckCircle size={16} className="text-green-600" />
              ) : (
                <AlertTriangle size={16} className={alertConf.text} />
              )}
              <span className={`text-sm font-medium ${alertConf.text}`}>{alertConf.label}</span>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Progression YTD</p>
              <p className={`text-lg font-bold ${alertConf.text}`}>{progression.progress_pct}%</p>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-3 text-center">
            <div>
              <p className="text-xs text-gray-500">Objectif annuel</p>
              <p className="text-sm font-semibold">
                {(progression.yearly_target_kwh || 0).toLocaleString('fr-FR')} kWh
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Reel YTD</p>
              <p className="text-sm font-semibold">
                {(progression.ytd_actual_kwh || 0).toLocaleString('fr-FR')} kWh
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Run-rate annuel</p>
              <p
                className={`text-sm font-semibold ${(progression.run_rate_kwh || 0) > (progression.yearly_target_kwh || 0) ? 'text-red-600' : 'text-green-600'}`}
              >
                {(progression.run_rate_kwh || 0).toLocaleString('fr-FR')} kWh
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Prévision</p>
              <p
                className={`text-sm font-semibold ${progression.forecast_vs_target_pct > 0 ? 'text-red-600' : 'text-green-600'}`}
              >
                {progression.forecast_vs_target_pct > 0 ? '+' : ''}
                {progression.forecast_vs_target_pct}%
              </p>
            </div>
          </div>

          {/* Variance decomposition (top 3 causes) */}
          {progression.variance_decomposition?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-2">
                Causes principales de l'ecart :
              </p>
              <div className="space-y-1.5">
                {progression.variance_decomposition.map((cause, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        cause.severity === 'critical'
                          ? 'bg-red-500'
                          : cause.severity === 'high'
                            ? 'bg-orange-500'
                            : 'bg-amber-500'
                      }`}
                    />
                    <span className="text-gray-700 flex-1">{cause.label}</span>
                    <span className="font-semibold text-gray-800">
                      {(cause.estimated_loss_kwh || 0).toLocaleString('fr-FR')} kWh/an
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <Card>
          <CardBody className="flex items-end gap-3">
            <div>
              <label className="text-xs text-gray-500 block">Mois</label>
              <select
                value={newTarget.month}
                onChange={(e) => setNewTarget({ ...newTarget, month: Number(e.target.value) })}
                className="text-sm border rounded px-2 py-1"
              >
                {MONTH_NAMES.map((m, i) => (
                  <option key={i} value={i + 1}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block">Objectif kWh</label>
              <input
                type="number"
                value={newTarget.target_kwh}
                onChange={(e) => setNewTarget({ ...newTarget, target_kwh: e.target.value })}
                className="text-sm border rounded px-2 py-1 w-28"
                placeholder="5000"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block">Budget EUR</label>
              <input
                type="number"
                value={newTarget.target_eur}
                onChange={(e) => setNewTarget({ ...newTarget, target_eur: e.target.value })}
                className="text-sm border rounded px-2 py-1 w-28"
                placeholder="900"
              />
            </div>
            <Button size="sm" onClick={handleAdd}>
              <Save size={14} className="mr-1" /> Enregistrer
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowAdd(false)}>
              <X size={14} />
            </Button>
          </CardBody>
        </Card>
      )}

      {/* Bar chart with ObjectivesLayer overlay */}
      {chartData.length > 0 && (
        <Card>
          <CardBody>
            <div className="flex gap-4">
              <div className="flex-1 min-w-0">
                <ExplorerChart
                  data={chartData}
                  xKey="name"
                  valueKey="reel"
                  mode="agrege"
                  unit="kwh"
                  height={250}
                  summaryData={{
                    points: chartData.length,
                    series: targets.length,
                  }}
                >
                  <Bar dataKey="objectif" fill="#93c5fd" name="Objectif" />
                  <Bar dataKey="reel" fill="#3b82f6" name="Reel" />
                  <ObjectivesLayer targets={targets} visible unit="kwh" />
                </ExplorerChart>
              </div>
              <LayerToggle layers={{ objectifs: true }} onToggle={() => {}} />
            </div>
          </CardBody>
        </Card>
      )}

      {/* Targets table */}
      {targets.length > 0 && (
        <Card>
          <CardBody className="p-0">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-2">Mois</th>
                  <th className="text-right px-4 py-2">Objectif kWh</th>
                  <th className="text-right px-4 py-2">Reel kWh</th>
                  <th className="text-right px-4 py-2">Ecart</th>
                  <th className="text-center px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {targets.map((t) => {
                  const delta =
                    t.actual_kwh != null && t.target_kwh
                      ? (((t.actual_kwh - t.target_kwh) / t.target_kwh) * 100).toFixed(1)
                      : null;
                  return (
                    <tr key={t.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-2">
                        {t.month ? MONTH_NAMES[t.month - 1] : 'Annuel'} {t.year}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {t.target_kwh?.toLocaleString('fr-FR') || '—'}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {t.actual_kwh?.toLocaleString('fr-FR') || '—'}
                      </td>
                      <td
                        className={`px-4 py-2 text-right font-medium ${delta && parseFloat(delta) > 0 ? 'text-red-600' : 'text-green-600'}`}
                      >
                        {delta ? `${delta > 0 ? '+' : ''}${delta}%` : '—'}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <button
                          onClick={() => handleDelete(t.id)}
                          className="text-gray-400 hover:text-red-500 transition"
                          aria-label={`Supprimer objectif ${MONTH_NAMES[t.month - 1] || ''} ${t.year}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
