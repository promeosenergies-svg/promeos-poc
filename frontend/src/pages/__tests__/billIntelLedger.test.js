/**
 * BillIntelPage — source-guards LEDGER Phase 3.3 + 3.3.fix.
 *
 * Vérifie que la reconstruction LEGO LEDGER est correctement câblée :
 *  - Top 3 DEC anomalies (data-testid="bill-intel-top-decisions")
 *  - Mapping consommé via SoT decisionAdapters.buildDecFromBillingInsight
 *  - Suppression hero rouge sang (data-testid="top-anomaly-hero")
 *  - Pas de dead code topInsight useMemo orphelin
 *
 * Pattern source-guard PROMEOS (readFileSync + toContain). Migration
 * @testing-library/react = backlog Phase 4.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const PAGE = resolve(__dirname, '../BillIntelPage.jsx');
const ADAPTERS = resolve(__dirname, '../../components/grammar/decisionAdapters.js');
const readPage = () => readFileSync(PAGE, 'utf-8');
const readAdapters = () => readFileSync(ADAPTERS, 'utf-8');

describe('BillIntelPage — Phase 3.3 LEDGER + 3.3.fix', () => {
  describe('CARDINAL : Top 3 DEC anomalies (Phase 3.3)', () => {
    it('expose la section data-testid="bill-intel-top-decisions"', () => {
      const src = readPage();
      expect(src).toContain('bill-intel-top-decisions');
    });

    it('utilise top3Insights useMemo + tri par estimated_loss_eur', () => {
      const src = readPage();
      expect(src).toContain('top3Insights');
      expect(src).toMatch(/estimated_loss_eur/);
      expect(src).toMatch(/\.slice\(0,\s*3\)/);
    });

    it('importe DecisionEvidenceCard depuis grammar/', () => {
      const src = readPage();
      expect(src).toContain("from '../components/grammar'");
      expect(src).toContain('DecisionEvidenceCard');
    });
  });

  describe('Phase 3.3.fix P2 #4 : SoT mapping consommé (decisionAdapters)', () => {
    it('BillIntelPage importe buildDecFromBillingInsight (pas de mapping inline)', () => {
      const src = readPage();
      expect(src).toContain('buildDecFromBillingInsight');
      expect(src).toContain("from '../components/grammar/decisionAdapters'");
    });

    it('decisionAdapters expose buildDecFromBillingInsight signature canonique', () => {
      const src = readAdapters();
      expect(src).toContain('export function buildDecFromBillingInsight');
      // 4 cellules garanties (Loi L9 doctrine §5.6)
      expect(src).toMatch(/'ÉCART ESTIMÉ'/);
      expect(src).toMatch(/'TYPE'/);
      expect(src).toMatch(/'SITE'/);
      expect(src).toMatch(/'STATUT'/);
    });
  });

  describe('Phase 3.3.fix P1 #1 : suppression dead code topInsight', () => {
    it('ne déclare plus le useMemo topInsight (dead code après remplacement hero)', () => {
      const src = readPage();
      // Le hero topInsight + son useMemo = retirés Phase 3.3.fix
      expect(src).not.toMatch(/const topInsight = useMemo/);
    });

    it("ne rend plus l'ancien hero data-testid=top-anomaly-hero (régression guard)", () => {
      const src = readPage();
      expect(src).not.toContain('top-anomaly-hero');
    });
  });

  describe('Phase 3.3.fix P1 #2 : ReactNode jamais coercé en string', () => {
    it('résout categoryLabel via BILLING_INSIGHT_TYPE_LABELS (registry plain string)', () => {
      const src = readPage();
      // Le mapping doit utiliser le registry plain string (pas TYPE_LABELS qui contient JSX)
      expect(src).toContain('BILLING_INSIGHT_TYPE_LABELS[insight.type]');
    });
  });

  describe('Phase 3.3.fix P1 #3 : pas de double-action drill-down', () => {
    it('DecisionEvidenceCard rendue sans primaryCta dans le bloc top3 (wrapper onClick suffit)', () => {
      const src = readPage();
      // Le bloc top3 doit utiliser <DecisionEvidenceCard {...decPayload} />
      // sans rajout de primaryCta (qui ferait double-action ancre + bubble)
      expect(src).toContain('<DecisionEvidenceCard {...decPayload} />');
    });
  });
});
