import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  BarChart3,
  AlertTriangle,
  Lightbulb,
  Database,
  RefreshCw,
  CheckCircle,
  Zap,
  ArrowRight,
  Link2,
  SlidersHorizontal,
  GitCompareArrows,
  Info,
  HelpCircle,
  Bell,
  CalendarRange,
  Activity,
  RotateCcw,
} from 'lucide-react';
import { PageShell, Tooltip } from '../ui';
import { toConsoExplorer } from '../services/routes';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';
import {
  getMeters,
  createMeter,
  uploadConsumptionData,
  runAnalysis,
  generateDemoEnergy,
  getKBStats,
  getKBArchetypes,
  getKBRules,
  getKBRecommendations,
  reloadKB,
  seedDemoKB,
  pingKB,
} from '../services/api';

// ---- Import Wizard (7 steps) ----
export function ImportWizard() {
  const { orgSites } = useScope();
  const [step, setStep] = useState(1);
  const sites = orgSites || [];
  const [selectedSite, setSelectedSite] = useState(null);
  const [meterName, setMeterName] = useState('Compteur Principal');
  const [file, setFile] = useState(null);
  const [frequency, setFrequency] = useState('hourly');
  const [archetype, setArchetype] = useState('BUREAU_STANDARD');
  const [importResult, setImportResult] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [useDemo, setUseDemo] = useState(false);

  const handleImport = async () => {
    setLoading(true);
    setError(null);
    try {
      if (useDemo) {
        // Generate demo data
        const result = await generateDemoEnergy({
          site_id: selectedSite.id,
          meter_name: meterName,
          days: 365,
          archetype: archetype,
        });
        setImportResult({
          status: 'completed',
          rows_imported: result.readings_generated,
          rows_skipped: 0,
          rows_errored: 0,
          meter_id: result.meter_id,
        });
      } else {
        // Upload real file
        const meters = await getMeters(selectedSite.id);
        let meter = meters.find((m) => m.name === meterName);
        if (!meter) {
          meter = await createMeter({
            meter_id: `PRM-${selectedSite.id.toString().padStart(6, '0')}`,
            name: meterName,
            site_id: selectedSite.id,
          });
        }
        const result = await uploadConsumptionData(file, meter.meter_id, frequency);
        setImportResult({ ...result, meter_id: meter.meter_id });
      }
      setStep(6);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const handleAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const meterId =
        importResult?.meter_id || `PRM-${selectedSite.id.toString().padStart(6, '0')}`;
      const result = await runAnalysis(meterId);
      setAnalysisResult(result);
      setStep(7);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Progress bar */}
      <div className="flex items-center mb-8">
        {[1, 2, 3, 4, 5, 6, 7].map((s) => (
          <div key={s} className="flex-1 flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                s < step
                  ? 'bg-green-500 text-white'
                  : s === step
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-500'
              }`}
            >
              {s < step ? '\u2713' : s}
            </div>
            {s < 7 && (
              <div className={`flex-1 h-1 mx-1 ${s < step ? 'bg-green-400' : 'bg-gray-200'}`} />
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Step 1: Select site */}
      {step === 1 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">1. Selectionner un site</h3>
          <div className="grid grid-cols-2 gap-3 max-h-60 overflow-y-auto">
            {sites.map((site) => (
              <button
                key={site.id}
                onClick={() => {
                  setSelectedSite(site);
                  setStep(2);
                }}
                className={`p-3 border rounded text-left hover:border-blue-400 transition ${
                  selectedSite?.id === site.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="font-medium text-sm">{site.nom}</div>
                <div className="text-xs text-gray-500">
                  {site.ville} - {site.surface_m2 || '?'} m2
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Data source */}
      {step === 2 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">2. Source des données</h3>
          <p className="text-sm text-gray-600 mb-4">
            Site: <strong>{selectedSite?.nom}</strong>
          </p>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => {
                setUseDemo(false);
                setStep(3);
              }}
              className="p-6 border-2 rounded-lg hover:border-blue-400 transition text-center"
            >
              <Upload className="mx-auto mb-2 text-blue-500" size={32} />
              <div className="font-semibold">Importer un fichier</div>
              <div className="text-sm text-gray-500 mt-1">CSV, XLSX, JSON</div>
            </button>
            <button
              onClick={() => {
                setUseDemo(true);
                setStep(4);
              }}
              className="p-6 border-2 rounded-lg hover:border-green-400 transition text-center"
            >
              <Database className="mx-auto mb-2 text-green-500" size={32} />
              <div className="font-semibold">Données de démo</div>
              <div className="text-sm text-gray-500 mt-1">365j synthetiques</div>
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Upload file */}
      {step === 3 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">3. Configuration de l'import</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nom du compteur</label>
              <input
                type="text"
                value={meterName}
                onChange={(e) => setMeterName(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Frequence</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="15min">15 minutes</option>
                <option value="30min">30 minutes</option>
                <option value="hourly">Horaire</option>
                <option value="daily">Journalier</option>
                <option value="monthly">Mensuel</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fichier</label>
              <input
                type="file"
                accept=".csv,.xlsx,.json"
                onChange={(e) => setFile(e.target.files[0])}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <p className="text-xs text-gray-500">
              Format CSV attendu: colonnes 'timestamp' ou 'date' + 'value_kwh' ou 'kwh' (separateur:
              ;)
            </p>
            <button
              onClick={() => setStep(5)}
              disabled={!file}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition"
            >
              Suivant
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Demo config */}
      {step === 4 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">4. Configuration demo</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Archetype de consommation</label>
              <select
                value={archetype}
                onChange={(e) => setArchetype(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="BUREAU_STANDARD">Bureau Standard (150-250 kWh/m2/an)</option>
                <option value="COMMERCE_ALIMENTAIRE">
                  Commerce Alimentaire (400-800 kWh/m2/an)
                </option>
                <option value="RESTAURATION_SERVICE">Restauration (250-450 kWh/m2/an)</option>
                <option value="INDUSTRIE_LEGERE">Industrie Legere (80-200 kWh/m2/an)</option>
              </select>
            </div>
            <button
              onClick={() => setStep(5)}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
            >
              Suivant
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Confirm & import */}
      {step === 5 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">5. Confirmation</h3>
          <div className="bg-gray-50 rounded p-4 space-y-2 text-sm">
            <p>
              <strong>Site:</strong> {selectedSite?.nom} ({selectedSite?.ville})
            </p>
            <p>
              <strong>Surface:</strong> {selectedSite?.surface_m2 || 'Non renseignee'} m2
            </p>
            <p>
              <strong>Source:</strong> {useDemo ? `Demo ${archetype}` : file?.name}
            </p>
            {!useDemo && (
              <p>
                <strong>Frequence:</strong> {frequency}
              </p>
            )}
          </div>
          <button
            onClick={handleImport}
            disabled={loading}
            className="mt-4 px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition"
          >
            {loading ? 'Import en cours...' : "Lancer l'import"}
          </button>
        </div>
      )}

      {/* Step 6: Import result */}
      {step === 6 && importResult && (
        <div>
          <h3 className="text-lg font-semibold mb-4">6. Import termine</h3>
          <div className="bg-green-50 border border-green-200 rounded p-4 space-y-2 text-sm">
            <div className="flex items-center gap-2 text-green-700 font-semibold">
              <CheckCircle size={18} /> Import réussi
            </div>
            <p>
              <strong>Lignes importees:</strong> {importResult.rows_imported?.toLocaleString('fr-FR')}
            </p>
            {importResult.rows_skipped > 0 && (
              <p>
                <strong>Ignorees:</strong> {importResult.rows_skipped}
              </p>
            )}
            {importResult.rows_errored > 0 && (
              <p className="text-red-600">
                <strong>Erreurs:</strong> {importResult.rows_errored}
              </p>
            )}
          </div>
          <button
            onClick={handleAnalysis}
            disabled={loading}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Analyse KB en cours...' : "Lancer l'analyse KB-driven"}
          </button>
        </div>
      )}

      {/* Step 7: Analysis results */}
      {step === 7 && analysisResult && (
        <div>
          <h3 className="text-lg font-semibold mb-4">7. Résultats de l'analyse</h3>
          <AnalysisResultView
            result={analysisResult}
            siteId={selectedSite?.id}
            dateFrom={null}
            dateTo={null}
          />
        </div>
      )}
    </div>
  );
}

// ---- KPI interpretation helpers ----
// C) Seuils alignes sur le brief UX Sprint
function interpretBaseNuit(ratio) {
  const pct = ratio * 100;
  if (pct < 15)
    return {
      label: 'OK',
      color: 'text-green-700 bg-green-50',
      tip: "Talon nuit < 15 % — bonnes pratiques d'extinction",
    };
  if (pct < 30)
    return {
      label: 'A surveiller',
      color: 'text-amber-700 bg-amber-50',
      tip: 'Talon nuit 15-30 % — vérifier les équipements allumés la nuit',
    };
  return {
    label: 'Trop eleve',
    color: 'text-red-700 bg-red-50',
    tip: 'Talon nuit > 30 % — equipements restent actifs 24/7, creer une alerte',
  };
}

function interpretWeekend(ratio) {
  const pct = ratio * 100;
  if (pct < 20)
    return {
      label: 'Normal',
      color: 'text-green-700 bg-green-50',
      tip: 'Ratio weekend < 20 % — reduction marquee le WE',
    };
  if (pct < 35)
    return {
      label: 'Suspect',
      color: 'text-amber-700 bg-amber-50',
      tip: "Ratio weekend 20-35 % — coupure partielle, marge d'amelioration",
    };
  return {
    label: 'Tres eleve',
    color: 'text-red-700 bg-red-50',
    tip: 'Ratio weekend > 35 % — consommation WE ≈ semaine, equipements toujours actifs',
  };
}

function interpretLoadFactor(lf) {
  const pct = lf * 100;
  if (pct < 10)
    return {
      label: 'Sous-utilisation',
      color: 'text-amber-700 bg-amber-50',
      tip: 'Facteur de charge < 10 % — site sous-utilise ou pointes tres fortes',
    };
  if (pct <= 30)
    return {
      label: 'Normal',
      color: 'text-green-700 bg-green-50',
      tip: 'Facteur de charge 10-30 % — profil equilibre',
    };
  return {
    label: 'Saturation',
    color: 'text-red-700 bg-red-50',
    tip: 'Facteur de charge > 30 % — charge quasi-constante, vérifier les pics de puissance',
  };
}

function interpretKwhM2(kwhM2, archetype) {
  if (!kwhM2 || !archetype?.kwh_m2_min) return null;
  if (kwhM2 < archetype.kwh_m2_min)
    return {
      label: 'Sous la ref.',
      color: 'text-green-700 bg-green-50',
      tip: `En dessous du min archetype (${archetype.kwh_m2_min} kWh/m2/an)`,
    };
  if (kwhM2 <= archetype.kwh_m2_max)
    return {
      label: 'Dans la norme',
      color: 'text-blue-700 bg-blue-50',
      tip: `Dans la fourchette archetype (${archetype.kwh_m2_min}-${archetype.kwh_m2_max})`,
    };
  return {
    label: 'Au-dessus',
    color: 'text-red-700 bg-red-50',
    tip: `Au-dessus du max archetype (${archetype.kwh_m2_max} kWh/m2/an)`,
  };
}

// C) Formule de calcul pour tooltip "Comment calcule?"
const KPI_FORMULAS = {
  kwh_total: "Somme de toutes les valeurs kWh sur la periode d'analyse.",
  base_nuit: 'Moyenne conso 0h-5h / moyenne conso 8h-18h en jours ouvres, x 100.',
  weekend: 'Moyenne conso samedi+dimanche / moyenne conso lundi-vendredi, x 100.',
  load_factor: 'Consommation moyenne / consommation max sur la periode, x 100.',
};

// ---- Analysis Result View ----
function AnalysisResultView({ result, siteId, dateFrom, dateTo }) {
  const navigate = useNavigate();
  const { toast } = useToast();

  if (!result || result.status !== 'ok') {
    return (
      <div className="text-red-600">Analyse echouee: {result?.message || 'Erreur inconnue'}</div>
    );
  }

  const baseNuit = result.features?.base_nuit_ratio || 0;
  const weekendRatio = result.features?.weekend_ratio || 0;
  const loadFactor = result.features?.load_factor || 0;
  const kwhM2 = result.features?.kwh_m2_year;
  const archCode = result.archetype?.code;
  const archNotDetermined = !archCode || archCode === 'NON_DETERMINE';
  const matchScore = result.archetype?.match_score || 0;

  const interpBase = interpretBaseNuit(baseNuit);
  const interpWE = interpretWeekend(weekendRatio);
  const interpLF = interpretLoadFactor(loadFactor);
  const interpKwh = interpretKwhM2(kwhM2, result.archetype);

  const handleOpenExplorer = () => {
    navigate(toConsoExplorer({ site_id: siteId, date_from: dateFrom, date_to: dateTo }));
    toast("Analyse terminée — retrouvez vos données dans l'Explorer", 'success');
  };

  return (
    <div className="space-y-6">
      {/* Archetype */}
      <div
        className={`border rounded-lg p-4 ${archNotDetermined ? 'bg-amber-50 border-amber-200' : 'bg-blue-50 border-blue-200'}`}
      >
        <h4
          className={`font-semibold flex items-center gap-2 ${archNotDetermined ? 'text-amber-800' : 'text-blue-800'}`}
        >
          <BarChart3 size={18} /> Archétype détecté
        </h4>
        <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Code</div>
            <div className="font-bold">{archCode || 'Non determine'}</div>
          </div>
          <div>
            <div className="text-gray-500">Confiance</div>
            <div className="font-bold">{(matchScore * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div className="text-gray-500">kWh/m2/an</div>
            <div className="font-bold">{kwhM2 || 'N/A'}</div>
            {interpKwh && (
              <span
                className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${interpKwh.color}`}
                title={interpKwh.tip}
              >
                {interpKwh.label}
              </span>
            )}
          </div>
        </div>

        {/* D) Archetype "Non determine" — explanation detaillee + 3 CTAs */}
        {archNotDetermined && (
          <div className="mt-3 p-3 bg-white/70 rounded-lg border border-amber-100">
            <div className="flex items-start gap-2">
              <Info size={16} className="text-amber-600 mt-0.5 shrink-0" />
              <div className="text-sm text-amber-800">
                <p className="font-medium mb-1">Pourquoi "Non determine" ?</p>
                <p className="text-xs text-amber-700 mb-2">
                  L'archetype est calcule en comparant kWh/m²/an, ratios nuit & WE aux references de
                  la KB. Causes possibles :
                </p>
                <ul className="text-xs text-amber-700 mb-3 list-disc pl-4 space-y-0.5">
                  <li>La Knowledge Base est vide (aucun archetype de reference charge)</li>
                  <li>La surface du site n'est pas renseignee (kWh/m² impossible a calculer)</li>
                  <li>Le code NAF / usage du site manque ou ne correspond a aucun archetype</li>
                </ul>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => navigate('/consommations/kb')}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 text-white rounded text-xs font-medium hover:bg-amber-700 transition"
                  >
                    <Database size={12} /> Vérifier la KB
                  </button>
                  <button
                    onClick={() => navigate('/patrimoine')}
                    className="flex items-center gap-1.5 px-3 py-1.5 border border-amber-300 text-amber-700 rounded text-xs font-medium hover:bg-amber-50 transition"
                  >
                    <SlidersHorizontal size={12} /> Compléter les données site
                  </button>
                  <button
                    onClick={() => {
                      toast("Relancez l'analyse après avoir corrigé les données", 'info');
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 border border-amber-300 text-amber-700 rounded text-xs font-medium hover:bg-amber-50 transition"
                  >
                    <RotateCcw size={12} /> Relancer l'analyse
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* À retenir — top 3 key takeaways */}
      <div className="bg-white border border-blue-100 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <Lightbulb size={16} className="text-blue-500" /> À retenir
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-500">Consommation</div>
            <div className="text-lg font-bold text-gray-900">
              {result.features?.kwh_total?.toLocaleString('fr-FR') || '0'} kWh
            </div>
            <div className="text-[11px] text-gray-400">
              {result.features?.days_count || '—'} jours · {result.features?.meters_count || 1}{' '}
              compteur{(result.features?.meters_count || 1) > 1 ? 's' : ''}
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-500">Anomalies</div>
            <div
              className={`text-lg font-bold ${(result.anomalies?.length || 0) > 0 ? 'text-red-600' : 'text-green-600'}`}
            >
              {result.anomalies?.length || 0}
            </div>
            <div className="text-[11px] text-gray-400">
              {(result.anomalies?.length || 0) === 0 ? 'Site dans les normes' : 'Points à traiter'}
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-500">Recommandations</div>
            <div className="text-lg font-bold text-blue-600">
              {result.recommendations?.length || 0}
            </div>
            <div className="text-[11px] text-gray-400">
              {(result.recommendations?.length || 0) === 0
                ? 'Rien à signaler'
                : 'Actions possibles'}
            </div>
          </div>
        </div>
      </div>

      {/* KPI details — collapsible */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900 flex items-center gap-1 py-2 select-none">
          <span className="transition-transform group-open:rotate-90">▸</span> Indicateurs détaillés
        </summary>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
          {[
            {
              label: 'kWh total',
              value: result.features?.kwh_total?.toLocaleString('fr-FR') || '0',
              interp: null,
              formula: KPI_FORMULAS.kwh_total,
              action: null,
            },
            {
              label: 'Talon nuit',
              value: `${(baseNuit * 100).toFixed(1)}%`,
              interp: interpBase,
              formula: KPI_FORMULAS.base_nuit,
              action:
                interpBase.label !== 'OK'
                  ? { label: 'Creer alerte talon', icon: Bell, to: '/notifications' }
                  : null,
            },
            {
              label: 'Ratio weekend',
              value: `${(weekendRatio * 100).toFixed(1)}%`,
              interp: interpWE,
              formula: KPI_FORMULAS.weekend,
              action:
                interpWE.label !== 'Normal'
                  ? {
                      label: 'Comparer a semaine type',
                      icon: CalendarRange,
                      to: `/consommations/explorer${siteId ? '?site_id=' + siteId : ''}`,
                    }
                  : null,
            },
            {
              label: 'Facteur de charge',
              value: `${(loadFactor * 100).toFixed(1)}%`,
              interp: interpLF,
              formula: KPI_FORMULAS.load_factor,
              action:
                interpLF.label === 'Saturation'
                  ? {
                      label: 'Voir pics de puissance',
                      icon: Activity,
                      to: `/consommations/explorer${siteId ? '?site_id=' + siteId : ''}`,
                    }
                  : null,
            },
          ].map((kpi, i) => (
            <div key={i} className="bg-white border rounded-lg p-3 text-center">
              <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
                {kpi.label}
                <Tooltip text={kpi.formula} position="top">
                  <HelpCircle size={12} className="text-gray-400 cursor-help" />
                </Tooltip>
              </div>
              <div className="text-lg font-bold mt-0.5">{kpi.value}</div>
              {kpi.interp && (
                <Tooltip text={kpi.interp.tip} position="bottom">
                  <span
                    className={`inline-block mt-1.5 px-2 py-0.5 rounded-full text-xs font-medium cursor-help ${kpi.interp.color}`}
                  >
                    {kpi.interp.label}
                  </span>
                </Tooltip>
              )}
              {kpi.action && (
                <button
                  onClick={() => navigate(kpi.action.to)}
                  className="flex items-center gap-1 mx-auto mt-2 text-[11px] text-blue-600 hover:text-blue-800 font-medium transition"
                >
                  <kpi.action.icon size={11} />
                  {kpi.action.label}
                </button>
              )}
            </div>
          ))}
        </div>
      </details>

      {/* Anomalies — collapsible */}
      <details className="group" open={result.anomalies?.length > 0}>
        <summary className="cursor-pointer font-semibold text-red-700 flex items-center gap-2 py-2 select-none">
          <span className="transition-transform group-open:rotate-90">▸</span>
          <AlertTriangle size={18} /> Anomalies détectées ({result.anomalies?.length || 0})
        </summary>
        {result.anomalies?.length > 0 ? (
          <div className="space-y-2">
            {result.anomalies.map((a, i) => (
              <div
                key={i}
                className={`border rounded-lg p-3 ${
                  a.severity === 'high'
                    ? 'border-red-300 bg-red-50'
                    : a.severity === 'medium'
                      ? 'border-orange-300 bg-orange-50'
                      : 'border-yellow-300 bg-yellow-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">{a.title}</div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-bold ${
                      a.severity === 'high'
                        ? 'bg-red-200 text-red-800'
                        : a.severity === 'medium'
                          ? 'bg-orange-200 text-orange-800'
                          : 'bg-yellow-200 text-yellow-800'
                    }`}
                  >
                    {a.severity}
                  </span>
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Mesure: {a.measured} | Seuil: {a.threshold} | KB Rule: {a.code}
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* E) Zero empty screen — next actions when no anomalies */
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 text-green-700 font-medium text-sm mb-3">
              <CheckCircle size={16} /> Aucune anomalie détectée — votre site est dans les normes KB
            </div>
            <p className="text-xs text-green-600 mb-3">
              Prochaines actions pour affiner le diagnostic :
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {[
                {
                  icon: Link2,
                  label: 'Connecter un compteur temps reel',
                  desc: 'Données plus fines pour détection continue',
                  to: '/connectors',
                },
                {
                  icon: SlidersHorizontal,
                  label: 'Affiner les seuils KB',
                  desc: 'Ajuster les regles a votre contexte',
                  to: '/consommations/kb',
                },
                {
                  icon: GitCompareArrows,
                  label: "Comparer avec d'autres sites",
                  desc: 'Benchmark inter-sites en mode overlay',
                  to: '/consommations/explorer',
                },
              ].map((action, i) => (
                <button
                  key={i}
                  onClick={() => navigate(action.to)}
                  className="flex items-start gap-2 p-2.5 bg-white rounded-lg border border-green-100 hover:border-green-300 hover:shadow-sm text-left transition"
                >
                  <action.icon size={14} className="text-green-600 mt-0.5 shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-gray-800">{action.label}</div>
                    <div className="text-[11px] text-gray-500">{action.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </details>

      {/* Recommendations — collapsible */}
      <details className="group" open={result.recommendations?.length > 0}>
        <summary className="cursor-pointer font-semibold text-green-700 flex items-center gap-2 py-2 select-none">
          <span className="transition-transform group-open:rotate-90">▸</span>
          <Lightbulb size={18} /> Recommandations KB ({result.recommendations?.length || 0})
        </summary>
        {result.recommendations?.length > 0 ? (
          <div className="space-y-2">
            {result.recommendations.map((r, i) => (
              <div key={i} className="border border-green-200 bg-green-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">{r.title}</div>
                  <div className="flex items-center gap-2">
                    {r.savings_pct && (
                      <span className="px-2 py-0.5 bg-green-200 text-green-800 rounded text-xs font-bold">
                        -{r.savings_pct}%
                      </span>
                    )}
                    <span className="px-2 py-0.5 bg-blue-200 text-blue-800 rounded text-xs font-bold">
                      ICE: {r.ice_score?.toFixed(3)}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Declenchee par: {r.triggered_by} | KB: {r.code}
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* E) Zero empty screen — next actions when no recommendations */
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-3">
              Aucune recommandation declenchee. Pour en obtenir :
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                {
                  icon: Database,
                  label: 'Enrichir la KB',
                  desc: 'Ajouter des recommandations liees a vos archetypes',
                  to: '/consommations/kb',
                },
                {
                  icon: ArrowRight,
                  label: 'Lancer un diagnostic approfondi',
                  desc: "Detection d'anomalies multi-sites avec historique",
                  to: '/diagnostic-conso',
                },
              ].map((action, i) => (
                <button
                  key={i}
                  onClick={() => navigate(action.to)}
                  className="flex items-start gap-2 p-2.5 bg-white rounded-lg border border-gray-100 hover:border-blue-300 hover:shadow-sm text-left transition"
                >
                  <action.icon size={14} className="text-blue-600 mt-0.5 shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-gray-800">{action.label}</div>
                    <div className="text-[11px] text-gray-500">{action.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </details>

      {/* B) CTA bar: primary Explorer + secondary Nouvelle analyse */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleOpenExplorer}
          className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium text-sm"
        >
          <BarChart3 size={16} />
          Ouvrir dans l'Explorer
          <ArrowRight size={14} />
        </button>
        <button
          onClick={() => navigate('/consommations/import')}
          className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition text-sm"
        >
          <RotateCcw size={14} />
          Nouvelle analyse
        </button>
      </div>
    </div>
  );
}

// ---- KB Admin Panel ----
export function KBAdminPanel() {
  const { toast } = useToast();
  const [stats, setStats] = useState(null);
  const [archetypes, setArchetypes] = useState([]);
  const [rules, setRules] = useState([]);
  const [recos, setRecos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [reloadResult, setReloadResult] = useState(null);
  const [serviceDown, setServiceDown] = useState(false);

  useEffect(() => {
    checkAndLoad();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkAndLoad = async () => {
    try {
      await pingKB();
      setServiceDown(false);
      await loadData();
    } catch {
      setServiceDown(true);
    }
  };

  const loadData = async () => {
    try {
      const [s, a, r, rec] = await Promise.all([
        getKBStats(),
        getKBArchetypes(),
        getKBRules(),
        getKBRecommendations(),
      ]);
      setStats(s);
      setArchetypes(a);
      setRules(r);
      setRecos(rec);
    } catch {
      toast('Erreur lors du chargement de la Knowledge Base', 'error');
    }
  };

  const handleReload = async () => {
    setLoading(true);
    try {
      const result = await reloadKB();
      setReloadResult(result);
      await loadData();
    } catch (err) {
      setReloadResult({ status: 'error', message: err.message });
    }
    setLoading(false);
  };

  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      const result = await seedDemoKB();
      if (result.status === 'already_seeded') {
        toast('Demo KB deja presente', 'info');
      } else {
        toast(result.message, 'success');
      }
      await loadData();
    } catch {
      toast('Erreur lors du seed de la KB demo', 'error');
    }
    setSeeding(false);
  };

  const isEmpty =
    stats &&
    stats.archetypes_count === 0 &&
    stats.anomaly_rules_count === 0 &&
    stats.recommendations_count === 0;

  // ── Service down ──
  if (serviceDown) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
          <AlertTriangle size={40} className="text-red-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-red-800 mb-2">KB service indisponible</h3>
          <p className="text-sm text-red-600 mb-4">
            Le backend Knowledge Base ne repond pas. Verifiez que le serveur est demarre.
          </p>
          <button
            onClick={checkAndLoad}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm transition"
          >
            Diagnostiquer
          </button>
        </div>
      </div>
    );
  }

  // ── F) Empty KB — actionable empty state ──
  if (isEmpty) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <Database size={40} className="text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Knowledge Base vide</h3>
          <p className="text-sm text-gray-500 mb-1">0 archetypes · 0 regles · 0 recommandations</p>
          <p className="text-sm text-gray-500 mb-6">
            La KB alimente l'analyse de vos courbes de charge (detection d'anomalies, archetypes,
            recommandations). Seedez la demo pour demarrer ou rechargez vos propres fichiers YAML.
          </p>
          <div className="flex items-center justify-center gap-3 mb-6">
            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition"
            >
              <Database size={16} className={seeding ? 'animate-spin' : ''} />
              {seeding ? 'Seed en cours...' : 'Seed demo KB (4 archetypes)'}
            </button>
            <button
              onClick={handleReload}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 text-sm transition"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Reload YAML
            </button>
          </div>
          {/* Next steps cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
            {[
              {
                icon: Upload,
                title: '1. Seeder la KB',
                desc: 'Chargez les archetypes, regles et recommandations de reference',
              },
              {
                icon: BarChart3,
                title: '2. Importer vos données',
                desc: 'Import CSV/XLSX ou génération de données démo par site',
              },
              {
                icon: Lightbulb,
                title: "3. Lancer l'analyse",
                desc: "Detection automatique d'anomalies et recommandations KB-driven",
              },
            ].map((s, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 p-3 bg-gray-50 rounded-lg border border-gray-100"
              >
                <s.icon size={16} className="text-blue-500 mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-medium text-gray-800">{s.title}</div>
                  <div className="text-xs text-gray-500">{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Knowledge Base</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-gray-600 rounded hover:bg-gray-50 disabled:opacity-50 text-sm transition"
            >
              <Database size={14} className={seeding ? 'animate-spin' : ''} />
              Seed demo
            </button>
            <button
              onClick={handleReload}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm transition"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Reload KB
            </button>
          </div>
        </div>

        {reloadResult && (
          <div
            className={`mb-4 p-3 rounded text-sm ${
              reloadResult.status === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}
          >
            {reloadResult.message}
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center p-3 bg-blue-50 rounded">
              <div className="text-2xl font-bold text-blue-700">{stats.archetypes_count}</div>
              <div className="text-xs text-gray-500">Archetypes</div>
            </div>
            <div className="text-center p-3 bg-red-50 rounded">
              <div className="text-2xl font-bold text-red-700">{stats.anomaly_rules_count}</div>
              <div className="text-xs text-gray-500">Regles anomalie</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded">
              <div className="text-2xl font-bold text-green-700">{stats.recommendations_count}</div>
              <div className="text-xs text-gray-500">Recommandations</div>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded">
              <div className="text-2xl font-bold text-purple-700">{stats.naf_mappings_count}</div>
              <div className="text-xs text-gray-500">Mappings NAF</div>
            </div>
          </div>
        )}

        {stats?.kb_doc_id && (
          <div className="mt-3 text-xs text-gray-500">
            Source: {stats.kb_doc_id} v{stats.kb_version} | SHA256: {stats.kb_sha256?.slice(0, 16)}
            ...
          </div>
        )}
      </div>

      {/* Archetypes */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Archetypes ({archetypes.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 px-3">Code</th>
                <th className="py-2 px-3">kWh/m2/an</th>
                <th className="py-2 px-3">Codes NAF</th>
                <th className="py-2 px-3">Confiance</th>
              </tr>
            </thead>
            <tbody>
              {archetypes.map((a) => (
                <tr key={a.code} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-3 font-medium">{a.code}</td>
                  <td className="py-2 px-3">
                    {a.kwh_m2_min}-{a.kwh_m2_max}
                  </td>
                  <td className="py-2 px-3 text-xs">{a.naf_codes?.join(', ') || '-'}</td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        a.confidence === 'high'
                          ? 'bg-green-100 text-green-700'
                          : a.confidence === 'medium'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {a.confidence}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rules */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Regles d'Anomalie ({rules.length})</h3>
        <div className="space-y-2">
          {rules.map((r) => (
            <div key={r.code} className="flex items-center justify-between border rounded p-3">
              <div>
                <div className="font-medium text-sm">{r.title}</div>
                <div className="text-xs text-gray-500">
                  {r.rule_type} | {r.source_section}
                </div>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-xs font-bold ${
                  r.severity === 'high' || r.severity === 'critical'
                    ? 'bg-red-200 text-red-800'
                    : r.severity === 'medium'
                      ? 'bg-orange-200 text-orange-800'
                      : 'bg-yellow-200 text-yellow-800'
                }`}
              >
                {r.severity}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Recommandations ({recos.length})</h3>
        <div className="space-y-2">
          {recos.map((r) => (
            <div key={r.code} className="flex items-center justify-between border rounded p-3">
              <div>
                <div className="font-medium text-sm">{r.title}</div>
                <div className="text-xs text-gray-500">
                  {r.action_type} | {r.target_asset}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {r.savings_min_pct != null && r.savings_max_pct != null && (
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                    {r.savings_min_pct}-{r.savings_max_pct}%
                  </span>
                )}
                {r.ice_score != null && (
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-bold">
                    ICE: {r.ice_score.toFixed(3)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---- Main Page (standalone fallback — normally rendered via ConsommationsPage tabs) ----
export default function ConsommationsUsages() {
  const [tab, setTab] = useState('import');

  return (
    <PageShell
      icon={Zap}
      title="Consommations"
      subtitle="Import, analyse KB-driven & base de connaissances"
    >
      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: 'import', label: 'Import & Analyse', icon: Upload },
          { key: 'kb', label: 'Knowledge Base', icon: Database },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              tab === t.key
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100 border'
            }`}
          >
            <t.icon size={16} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'import' && <ImportWizard />}

      {tab === 'kb' && <KBAdminPanel />}
    </PageShell>
  );
}
