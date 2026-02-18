/**
 * PROMEOS — V25: Logger tests
 * Structured logger + Sentry bridge.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// We test at source level + runtime
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'logger.js'), 'utf8');

describe('logger.js source guards', () => {
  it('exports logger object', () => {
    expect(src).toMatch(/export\s+const\s+logger/);
  });

  it('exports initSentry function', () => {
    expect(src).toMatch(/export\s+function\s+initSentry/);
  });

  it('has debug, info, warn, error methods', () => {
    expect(src).toContain("debug:");
    expect(src).toContain("info:");
    expect(src).toContain("warn:");
    expect(src).toContain("error:");
  });

  it('bridges to Sentry for error/warn', () => {
    expect(src).toContain('captureMessage');
    expect(src).toContain('__SENTRY__');
  });
});

describe('logger runtime', () => {
  let logger;

  beforeEach(async () => {
    vi.stubGlobal('__SENTRY__', undefined);
    const mod = await import('../logger.js');
    logger = mod.logger;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('logger.error calls console.error', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    logger.error('Test', 'boom');
    expect(spy).toHaveBeenCalledWith('[Test] boom', '');
  });

  it('logger.warn calls console.warn', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    logger.warn('Test', 'attention');
    expect(spy).toHaveBeenCalledWith('[Test] attention', '');
  });

  it('logger.info calls console.log', () => {
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
    logger.info('Test', 'hello');
    expect(spy).toHaveBeenCalledWith('[Test] hello', '');
  });

  it('logger.debug calls console.log', () => {
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
    logger.debug('Test', 'trace');
    expect(spy).toHaveBeenCalledWith('[Test] trace', '');
  });
});

describe('initSentry safety', () => {
  it('does not crash without VITE_SENTRY_DSN', async () => {
    // initSentry should be a no-op when DSN is missing
    const mod = await import('../logger.js');
    expect(() => mod.initSentry()).not.toThrow();
  });
});
