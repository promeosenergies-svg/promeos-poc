/**
 * Tests presenter NotificationsSol (Sprint REFONTE-P6 S1 pilot)
 */
import { describe, it, expect } from 'vitest';
import {
  buildNotificationsKicker,
  buildNotificationsNarrative,
  interpretWeek,
  formatFREurCompact,
} from '../sol_presenters';

describe('NotificationsSol presenters', () => {
  describe('buildNotificationsKicker', () => {
    it('builds base kicker without counts', () => {
      const s = buildNotificationsKicker({ liveSummary: { by_severity: {} } });
      expect(s).toContain('PILOTAGE');
      expect(s).toContain('ALERTES');
      expect(s).not.toContain('CRITIQUE');
    });

    it('includes critical count when present', () => {
      const s = buildNotificationsKicker({
        liveSummary: { by_severity: { critical: 5, warn: 11 } },
      });
      expect(s).toContain('5 CRITIQUES');
      expect(s).toContain('11 ATTENTION');
    });

    it('singular form for 1 critical', () => {
      const s = buildNotificationsKicker({
        liveSummary: { by_severity: { critical: 1 } },
      });
      expect(s).toContain('1 CRITIQUE');
      expect(s).not.toContain('1 CRITIQUES');
    });
  });

  describe('buildNotificationsNarrative', () => {
    it('pluralizes correctly for 0/1/N events', () => {
      expect(buildNotificationsNarrative({ events: [] })).toContain('0 alerte active');
      expect(buildNotificationsNarrative({ events: [{}] })).toContain('1 alerte active');
      expect(buildNotificationsNarrative({ events: [{}, {}] })).toContain('2 alertes actives');
    });

    it('includes 5 briques sources mention', () => {
      const s = buildNotificationsNarrative({ events: [] });
      expect(s).toContain('Conformité');
      expect(s).toContain('Facturation');
      expect(s).toContain('Achats');
      expect(s).toContain('Consommation');
      expect(s).toContain('Actions');
    });

    it('shows impact cumulé when events have estimated_impact_eur', () => {
      const events = [
        { estimated_impact_eur: 1250 },
        { estimated_impact_eur: 450 },
      ];
      const s = buildNotificationsNarrative({ events });
      expect(s).toMatch(/impact cumulé/);
    });
  });

  describe('interpretWeek', () => {
    it('returns 3 cards with correct tagKinds', () => {
      const w = interpretWeek({ events: [] });
      expect(w.aRegarder.tagKind).toMatch(/calme|afaire/);
      expect(w.deriveDetectee.tagKind).toMatch(/calme|attention/);
      expect(w.bonneNouvelle.tagKind).toBe('succes');
    });

    it('picks highest-impact critical event for aRegarder', () => {
      const events = [
        {
          severity: 'critical',
          status: 'new',
          title: 'Low impact',
          estimated_impact_eur: 100,
        },
        {
          severity: 'critical',
          status: 'new',
          title: 'High impact',
          estimated_impact_eur: 5000,
        },
      ];
      const w = interpretWeek({ events });
      expect(w.aRegarder.title).toBe('High impact');
      expect(w.aRegarder.tagKind).toBe('afaire');
    });

    it('picks most-recent consumption/billing drift', () => {
      const events = [
        {
          source_type: 'billing',
          status: 'new',
          title: 'Old drift',
          created_at: '2024-01-01',
        },
        {
          source_type: 'consumption',
          status: 'new',
          title: 'Recent drift',
          created_at: '2026-01-01',
        },
      ];
      const w = interpretWeek({ events });
      expect(w.deriveDetectee.title).toBe('Recent drift');
    });

    it('counts resolved events in bonneNouvelle', () => {
      const events = [
        { status: 'read' },
        { status: 'dismissed' },
        { status: 'new' },
      ];
      const w = interpretWeek({ events });
      expect(w.bonneNouvelle.title).toContain('2 alertes traitées');
    });
  });

  describe('formatFREurCompact', () => {
    it('handles null/undefined', () => {
      expect(formatFREurCompact(null)).toBe('—');
      expect(formatFREurCompact(undefined)).toBe('—');
    });

    it('formats thousands as k€', () => {
      expect(formatFREurCompact(1250)).toContain('1,3');
      expect(formatFREurCompact(1250)).toContain('k€');
      expect(formatFREurCompact(50000)).toContain('50');
      expect(formatFREurCompact(50000)).toContain('k€');
    });

    it('formats sub-1000 as integer €', () => {
      expect(formatFREurCompact(450)).toContain('450');
      expect(formatFREurCompact(450)).toContain('€');
    });
  });
});
