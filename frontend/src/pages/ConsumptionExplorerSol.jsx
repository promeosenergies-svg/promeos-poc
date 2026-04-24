/**
 * PROMEOS — ConsumptionExplorerSol (Sprint REFONTE-P6 S1 — Wrapper Option A)
 *
 * Wrapper Sol minimal autour de ConsumptionExplorerPage (1077 LOC, 18 features
 * MAIN dont 12 panels spécialisés : TimeseriesPanel, InsightsPanel, SignaturePanel,
 * MeteoPanel, TunnelPanel, TargetsPanel, BenchmarkPanel, HPHCPanel, GasPanel,
 * CDCViewerPanel, HierarchyPanel, DataQualityPanel).
 *
 * Option A validée Round 3 : wrapper minimal avec SolPageHeader uniquement,
 * les 12 panels restent intacts (zéro risque régression).
 */

import React from 'react';
import { SolPageHeader } from '../ui/sol';
import ConsumptionExplorerPage from './ConsumptionExplorerPage';
import {
  buildExplorerKicker,
  buildExplorerNarrative,
} from './consommations/sol_presenters';

export default function ConsumptionExplorerSol() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SolPageHeader
        kicker={buildExplorerKicker()}
        title="Explorateur de consommation"
        titleEm="— courbes de charge & 12 analyses"
        narrative={buildExplorerNarrative()}
      />
      <ConsumptionExplorerPage />
    </div>
  );
}
