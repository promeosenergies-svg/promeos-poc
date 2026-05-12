/**
 * PROMEOS — Persona Context (F.25 doctrine v1.0).
 *
 * Toggle persona consommateur du briefing : Responsable Énergie (défaut) /
 * DAF / DG-COMEX. Le persona pondère le scoring de priorisation des
 * highlights cockpit jour (cf ADR-022 F.22).
 *
 * Persisté en localStorage `promeos_persona`. Consommé par CockpitJour.jsx
 * (paramètre `?persona=` du fetch `/api/cockpit/jour`).
 *
 * Doctrine cardinale PROMEOS : "Le même patrimoine, 3 audiences, 3 priorités".
 */
import { createContext, useCallback, useContext, useState } from 'react';

const STORAGE_KEY = 'promeos_persona';

export const PERSONAS = Object.freeze({
  RESPONSABLE_ENERGIE: 'responsable_energie',
  DAF: 'daf',
  DG_COMEX: 'dg_comex',
});

/** Libellés FR affichés dans le dropdown topbar. */
export const PERSONA_LABELS = Object.freeze({
  responsable_energie: 'Responsable Énergie',
  daf: 'DAF',
  dg_comex: 'DG / COMEX',
});

/** Description courte (tooltip) — pondération scoring v1. */
export const PERSONA_DESCRIPTIONS = Object.freeze({
  responsable_energie: 'Pondération G·3 + I·2 + D·2 (gravité prime)',
  daf: 'Pondération G·2 + I·3 + D·2 (impact financier prime)',
  dg_comex: 'Pondération G·2 + I·3 + D·3 (urgence + impact priment)',
});

function loadPersona() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && Object.values(PERSONAS).includes(stored)) return stored;
  } catch {
    /* ignore */
  }
  return PERSONAS.RESPONSABLE_ENERGIE;
}

const PersonaContext = createContext(null);

export function PersonaProvider({ children }) {
  const [persona, setPersonaState] = useState(loadPersona);
  // F.28 — data quality (0-100) publiée par la page courante. Détermine
  // si DAF/DG-COMEX sont activés (doctrine v1 §14.4.3 V8 : ≥ 80 %).
  // Défaut 100 % = toggle libre tant qu'aucune page n'a publié.
  const [dataQualityPct, setDataQualityPct] = useState(100);

  const setPersona = useCallback((next) => {
    if (!Object.values(PERSONAS).includes(next)) return;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    setPersonaState(next);
  }, []);

  return (
    <PersonaContext.Provider value={{ persona, setPersona, dataQualityPct, setDataQualityPct }}>
      {children}
    </PersonaContext.Provider>
  );
}

export function usePersona() {
  const ctx = useContext(PersonaContext);
  if (!ctx) throw new Error('usePersona must be used within PersonaProvider');
  return ctx;
}
