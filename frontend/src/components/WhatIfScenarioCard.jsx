/**
 * PROMEOS — WhatIfScenarioCard
 *
 * Wow-card simulator exec : 3 sliders pour ajuster les hypothèses,
 * projection live de l'impact sur la facture annuelle. Vraie expérience
 * AI-native d'arbitrage : "si je fais X, ça donne quoi ?"
 *
 * 3 leviers exec :
 *   - Tarif élec (€/kWh) : effet d'une renégociation contrat
 *   - Production PV (kWc) : effet d'une installation autoconsommation
 *   - Baisse conso (%) : effet d'un programme d'efficacité énergétique
 *
 * Différenciateur PROMEOS : Metron/Advizeo affichent du statique, PROMEOS
 * permet à l'exec de SIMULER l'arbitrage budget en temps réel.
 *
 * Calcul (simple, ZÉRO calcul métier complexe) :
 *   conso_optim_kwh  = baseline_kwh × (1 - reduction_pct / 100)
 *   pv_yield_kwh     = pv_kwc × 1100 (heures équivalentes France)
 *   net_kwh          = max(0, conso_optim_kwh - pv_yield_kwh)
 *   facture_eur      = net_kwh × tarif_eur_per_kwh
 *   eco_eur_per_year = baseline_facture - facture_eur
 */
import { useMemo, useState } from 'react';
import { Sliders, RotateCcw } from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const PV_YIELD_HOURS_PER_YEAR = 1100; // Heures équivalentes pleine charge France moyenne
const DEFAULT_TARIFF_EUR_KWH = 0.18;

function formatFREur(eur) {
  if (eur == null || isNaN(eur)) return '—';
  if (Math.abs(eur) >= 1_000_000) return `${(eur / 1_000_000).toFixed(2).replace('.', ',')} M€`;
  if (Math.abs(eur) >= 1_000) return `${Math.round(eur / 100) / 10} k€`.replace('.', ',');
  return `${Math.round(eur).toLocaleString('fr-FR')} €`;
}

function Slider({ label, min, max, step, value, onChange, formatValue, hint }) {
  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 6,
        }}
      >
        <span
          style={{
            fontSize: 11,
            color: 'var(--sol-ink-700)',
            fontFamily: 'var(--sol-font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            fontWeight: 600,
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontSize: 14,
            color: 'var(--sol-ink-900)',
            fontWeight: 600,
            fontFamily: 'var(--sol-font-mono)',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {formatValue(value)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{
          width: '100%',
          accentColor: 'var(--sol-calme-fg, #047857)',
          cursor: 'pointer',
        }}
      />
      {hint && (
        <div
          style={{
            fontSize: 10.5,
            color: 'var(--sol-ink-500)',
            marginTop: 4,
          }}
        >
          {hint}
        </div>
      )}
    </div>
  );
}

export default function WhatIfScenarioCard({
  baselineConsoKwh = 2_750_000, // 2750 MWh par défaut
  baselineFactureEur = 386_972,
  defaultTariff = DEFAULT_TARIFF_EUR_KWH,
}) {
  // Preset par défaut chiffré — empêche le first-paint "0 €" qui donne
  // l'impression "ça marche pas" (audit UX A3 / Jean-Marc).
  // Hypothèse : -3% tarif renégo · 50 kWc PV · -2% efficacité ≈ scénario réaliste.
  const [tariff, setTariff] = useState(
    Math.max(0.10, parseFloat((defaultTariff * 0.97).toFixed(3)))
  );
  const [pvKwc, setPvKwc] = useState(50);
  const [reductionPct, setReductionPct] = useState(2);

  // Calcul live de la projection
  const result = useMemo(() => {
    const consoOptim = baselineConsoKwh * (1 - reductionPct / 100);
    const pvYield = pvKwc * PV_YIELD_HOURS_PER_YEAR;
    const netKwh = Math.max(0, consoOptim - pvYield);
    const factureEur = netKwh * tariff;
    const ecoEur = baselineFactureEur - factureEur;
    const ecoPct = baselineFactureEur > 0 ? (ecoEur / baselineFactureEur) * 100 : 0;
    return {
      consoOptim,
      pvYield,
      netKwh,
      factureEur,
      ecoEur,
      ecoPct,
    };
  }, [baselineConsoKwh, baselineFactureEur, tariff, pvKwc, reductionPct]);

  const chartData = useMemo(
    () => [
      {
        scenario: 'Aujourd\'hui',
        montant: baselineFactureEur,
        isBase: true,
      },
      {
        scenario: 'Scénario Sol',
        montant: result.factureEur,
        isBase: false,
      },
    ],
    [baselineFactureEur, result.factureEur]
  );

  const handleReset = () => {
    setTariff(Math.max(0.10, parseFloat((defaultTariff * 0.97).toFixed(3))));
    setPvKwc(50);
    setReductionPct(2);
  };

  const isImproved = result.ecoEur > 100;
  const accentColor = isImproved
    ? 'var(--sol-calme-fg, #047857)'
    : result.ecoEur < -100
      ? 'var(--sol-afaire-fg, #b91c1c)'
      : 'var(--sol-ink-700)';

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        borderRadius: 8,
        padding: '20px 22px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 14,
        }}
      >
        <div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 9.5,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--sol-calme-fg)',
              fontWeight: 600,
              background: 'var(--sol-calme-bg)',
              padding: '3px 8px',
              borderRadius: 99,
              marginBottom: 8,
            }}
          >
            <Sliders size={10} />
            Simulateur arbitrage exec
          </div>
          <h3
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 16,
              fontWeight: 600,
              color: 'var(--sol-ink-900)',
              margin: 0,
              lineHeight: 1.3,
              letterSpacing: '-0.015em',
            }}
          >
            Et si on activait... ?
          </h3>
        </div>

        <button
          type="button"
          onClick={handleReset}
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 11.5,
            padding: '5px 10px',
            borderRadius: 6,
            border: '1px solid var(--sol-ink-200)',
            background: 'var(--sol-bg-paper)',
            color: 'var(--sol-ink-500)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <RotateCcw size={11} />
          Réinitialiser
        </button>
      </div>

      {/* Grid : Sliders | Visualisation */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 28,
          alignItems: 'stretch',
        }}
      >
        {/* Sliders */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <Slider
            label="Tarif électricité"
            min={0.10}
            max={0.30}
            step={0.005}
            value={tariff}
            onChange={setTariff}
            formatValue={(v) => `${v.toFixed(3).replace('.', ',')} €/kWh`}
            hint="Renégociation contrat ou bascule TRVE/marché"
          />
          <Slider
            label="Photovoltaïque installé"
            min={0}
            max={1000}
            step={10}
            value={pvKwc}
            onChange={setPvKwc}
            formatValue={(v) => `${v} kWc`}
            hint={`≈ ${(pvKwc * PV_YIELD_HOURS_PER_YEAR).toLocaleString('fr-FR')} kWh/an autoconsommés`}
          />
          <Slider
            label="Baisse consommation"
            min={0}
            max={40}
            step={1}
            value={reductionPct}
            onChange={setReductionPct}
            formatValue={(v) => `−${v} %`}
            hint="Programme efficacité énergétique (CVC, LED, GTB)"
          />
        </div>

        {/* Résultat live */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Big number économie */}
          <div
            style={{
              padding: '14px 16px',
              background: 'var(--sol-bg-canvas, #fafaf6)',
              border: `1px solid ${isImproved ? 'var(--sol-calme-fg)' : 'var(--sol-ink-200)'}`,
              borderRadius: 8,
            }}
          >
            <div
              style={{
                fontSize: 10,
                color: 'var(--sol-ink-500)',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                fontFamily: 'var(--sol-font-mono)',
                marginBottom: 6,
                fontWeight: 600,
              }}
            >
              Économie annuelle estimée
            </div>
            <div
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: 36,
                color: accentColor,
                lineHeight: 1,
                fontWeight: 600,
              }}
            >
              {result.ecoEur > 0 ? '+' : ''}
              {formatFREur(result.ecoEur)}
            </div>
            <div
              style={{
                fontSize: 12,
                color: 'var(--sol-ink-500)',
                marginTop: 6,
              }}
            >
              soit {result.ecoEur > 0 ? '−' : '+'}
              {Math.abs(result.ecoPct).toFixed(1)}% sur la facture
            </div>
          </div>

          {/* Mini bar chart compare */}
          <div style={{ width: '100%', height: 120 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 14, right: 8, bottom: 4, left: 8 }}
              >
                <XAxis
                  dataKey="scenario"
                  axisLine={false}
                  tickLine={false}
                  tick={{
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 10,
                    fill: 'var(--sol-ink-700)',
                  }}
                />
                <YAxis hide />
                <Tooltip
                  contentStyle={{
                    background: 'var(--sol-bg-paper)',
                    border: '1px solid var(--sol-rule)',
                    borderRadius: 4,
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 11,
                  }}
                  formatter={(v) => [formatFREur(v), 'Facture annuelle']}
                />
                <Bar dataKey="montant" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={
                        entry.isBase
                          ? 'var(--sol-ink-300)'
                          : isImproved
                            ? 'var(--sol-calme-fg)'
                            : 'var(--sol-ink-700)'
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Footer chiffres */}
          <div
            style={{
              fontSize: 11,
              color: 'var(--sol-ink-500)',
              fontFamily: 'var(--sol-font-mono)',
              letterSpacing: '0.04em',
              lineHeight: 1.6,
            }}
          >
            Baseline : {formatFREur(baselineFactureEur)} · {Math.round(baselineConsoKwh / 1000)} MWh
            <br />
            Scénario : {formatFREur(result.factureEur)} · {Math.round(result.netKwh / 1000)} MWh
            <br />
            <span style={{ fontSize: 10 }}>
              PV : {PV_YIELD_HOURS_PER_YEAR} h éq/an · calcul indicatif
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
