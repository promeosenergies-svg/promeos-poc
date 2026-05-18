/**
 * M2-5.1 — Tests du module featureFlags (environnement node, vi.stubEnv).
 */
import { afterEach, describe, expect, test, vi } from 'vitest';

describe('featureFlags', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('isActionCenterV4Enabled returns true when env=true', async () => {
    vi.stubEnv('VITE_FEATURE_ACTION_CENTER_V4', 'true');
    const { isActionCenterV4Enabled } = await import('../featureFlags');
    expect(isActionCenterV4Enabled()).toBe(true);
  });

  test('isActionCenterV4Enabled returns false when env=false', async () => {
    vi.stubEnv('VITE_FEATURE_ACTION_CENTER_V4', 'false');
    const { isActionCenterV4Enabled } = await import('../featureFlags');
    expect(isActionCenterV4Enabled()).toBe(false);
  });

  test('isActionCenterV4Enabled returns false when env undefined', async () => {
    vi.stubEnv('VITE_FEATURE_ACTION_CENTER_V4', '');
    const { isActionCenterV4Enabled } = await import('../featureFlags');
    expect(isActionCenterV4Enabled()).toBe(false);
  });
});
