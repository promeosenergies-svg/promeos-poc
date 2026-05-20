/**
 * M2-5.1 — Tests des 14 wrappers v4ActionCenter (apiClientV4 mocké).
 *
 * 1 test par fonction : vérifie URL, params/payload et headers transmis.
 * Environnement node (pas de DOM) — File/FormData sont des globals Node 20+.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('../apiClientV4', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

import apiClientV4 from '../apiClientV4';
import * as v4 from '../v4ActionCenter';

describe('v4ActionCenter wrappers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── READ ──────────────────────────────────────────────────────

  test('fetchItems passes pagination params', async () => {
    apiClientV4.get.mockResolvedValue({ data: { items: [], total: 0 } });
    await v4.fetchItems({ offset: 20, limit: 10 });
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items', {
      params: { offset: 20, limit: 10 },
    });
  });

  test('fetchItems applies default pagination', async () => {
    apiClientV4.get.mockResolvedValue({ data: {} });
    await v4.fetchItems();
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items', {
      params: { offset: 0, limit: 50 },
    });
  });

  test('fetchItem builds the item URL', async () => {
    apiClientV4.get.mockResolvedValue({ data: {} });
    await v4.fetchItem('item-1');
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items/item-1');
  });

  test('fetchItemEvents builds the events URL with params', async () => {
    apiClientV4.get.mockResolvedValue({ data: {} });
    await v4.fetchItemEvents('item-1', { offset: 5, limit: 25 });
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items/item-1/events', {
      params: { offset: 5, limit: 25 },
    });
  });

  test('fetchItemEvidences builds the evidences URL', async () => {
    apiClientV4.get.mockResolvedValue({ data: {} });
    await v4.fetchItemEvidences('item-1');
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items/item-1/evidences', {
      params: { offset: 0, limit: 50 },
    });
  });

  test('fetchItemBlockers builds the blockers URL', async () => {
    apiClientV4.get.mockResolvedValue({ data: {} });
    await v4.fetchItemBlockers('item-1');
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items/item-1/blockers', {
      params: { offset: 0, limit: 50 },
    });
  });

  test('fetchItemLinks builds the links URL', async () => {
    apiClientV4.get.mockResolvedValue({ data: {} });
    await v4.fetchItemLinks('item-1');
    expect(apiClientV4.get).toHaveBeenCalledWith('/v4/action-center/items/item-1/links', {
      params: { offset: 0, limit: 50 },
    });
  });

  // ── WRITE ─────────────────────────────────────────────────────

  test('createItem with idempotencyKey adds header', async () => {
    apiClientV4.post.mockResolvedValue({ data: {} });
    await v4.createItem({ title: 'T' }, { idempotencyKey: 'abc-123' });
    expect(apiClientV4.post).toHaveBeenCalledWith(
      '/v4/action-center/items',
      { title: 'T' },
      { headers: { 'Idempotency-Key': 'abc-123' } }
    );
  });

  test('createItem without idempotencyKey sends empty headers', async () => {
    apiClientV4.post.mockResolvedValue({ data: {} });
    await v4.createItem({ title: 'T' });
    expect(apiClientV4.post).toHaveBeenCalledWith(
      '/v4/action-center/items',
      { title: 'T' },
      { headers: {} }
    );
  });

  test('updateItem patches the item', async () => {
    apiClientV4.patch.mockResolvedValue({ data: {} });
    await v4.updateItem('item-1', { title: 'X' });
    expect(apiClientV4.patch).toHaveBeenCalledWith('/v4/action-center/items/item-1', {
      title: 'X',
    });
  });

  test('transitionLifecycle patches the lifecycle sub-resource', async () => {
    apiClientV4.patch.mockResolvedValue({ data: {} });
    await v4.transitionLifecycle('item-1', { to_state: 'triaged' });
    expect(apiClientV4.patch).toHaveBeenCalledWith('/v4/action-center/items/item-1/lifecycle', {
      to_state: 'triaged',
    });
  });

  test('uploadEvidence sends multipart FormData', async () => {
    apiClientV4.post.mockResolvedValue({ data: {} });
    const file = new File(['x'], 'test.pdf', { type: 'application/pdf' });
    await v4.uploadEvidence('item-1', file, { description: 'demo' });
    const call = apiClientV4.post.mock.calls[0];
    expect(call[0]).toBe('/v4/action-center/items/item-1/evidences');
    expect(call[1]).toBeInstanceOf(FormData);
    expect(call[2].headers['Content-Type']).toBe('multipart/form-data');
  });

  test('verifyEvidence patches the verify sub-resource', async () => {
    apiClientV4.patch.mockResolvedValue({ data: {} });
    await v4.verifyEvidence('ev-1', { note: 'ok' });
    expect(apiClientV4.patch).toHaveBeenCalledWith('/v4/action-center/evidences/ev-1/verify', {
      note: 'ok',
    });
  });

  test('addBlocker posts the blocker', async () => {
    apiClientV4.post.mockResolvedValue({ data: {} });
    await v4.addBlocker('item-1', { reason: 'Attente facture' });
    expect(apiClientV4.post).toHaveBeenCalledWith('/v4/action-center/items/item-1/blockers', {
      reason: 'Attente facture',
    });
  });

  test('resolveBlocker patches the resolve sub-resource', async () => {
    apiClientV4.patch.mockResolvedValue({ data: {} });
    await v4.resolveBlocker('bl-1', { resolution: 'reçue' });
    expect(apiClientV4.patch).toHaveBeenCalledWith('/v4/action-center/blockers/bl-1/resolve', {
      resolution: 'reçue',
    });
  });

  test('createLink posts the link', async () => {
    apiClientV4.post.mockResolvedValue({ data: {} });
    await v4.createLink('item-1', { target_module: 'invoice', target_id: 'inv-1' });
    expect(apiClientV4.post).toHaveBeenCalledWith('/v4/action-center/items/item-1/links', {
      target_module: 'invoice',
      target_id: 'inv-1',
    });
  });
});
