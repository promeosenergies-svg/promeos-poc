/**
 * PROMEOS — useExplorerPresets
 * localStorage-based named preset management for the Consumption Explorer.
 *
 * Storage key: 'promeos_explorer_presets'
 * Format: [{ name: string, state: object, savedAt: ISO8601 }]
 * Max presets: 10 (oldest dropped on overflow)
 */
import { useState } from 'react';

const STORAGE_KEY = 'promeos_explorer_presets';
const MAX_PRESETS = 10;

function readPresets() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writePresets(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    // quota exceeded or private browsing — silently ignore
  }
}

/**
 * Hook: named preset save/load/delete backed by localStorage.
 *
 * @returns {{
 *   presets: Array<{ name: string, state: object, savedAt: string }>,
 *   savePreset: (name: string, state: object) => void,
 *   loadPreset: (name: string) => object|null,
 *   deletePreset: (name: string) => void,
 * }}
 */
export default function useExplorerPresets() {
  const [presets, setPresets] = useState(() => readPresets());

  const persist = (next) => {
    setPresets(next);
    writePresets(next);
  };

  /**
   * Save (or overwrite) a named preset.
   * @param {string} name
   * @param {object} state  — current explorer state snapshot
   */
  const savePreset = (name, state) => {
    if (!name?.trim()) return;
    // Remove existing entry with same name (overwrite)
    const filtered = presets.filter(p => p.name !== name);
    const entry = { name, state, savedAt: new Date().toISOString() };
    // Append new entry, trim to MAX_PRESETS keeping most recent
    const next = [...filtered, entry].slice(-MAX_PRESETS);
    persist(next);
  };

  /**
   * Load the state for a named preset.
   * @param {string} name
   * @returns {object|null}
   */
  const loadPreset = (name) => {
    return presets.find(p => p.name === name)?.state ?? null;
  };

  /**
   * Delete a named preset.
   * @param {string} name
   */
  const deletePreset = (name) => {
    persist(presets.filter(p => p.name !== name));
  };

  return { presets, savePreset, loadPreset, deletePreset };
}
