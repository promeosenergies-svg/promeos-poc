/**
 * PROMEOS — ActionDrawerContext (Étape 4.1)
 * Centralized context for opening the CreateActionDrawer from anywhere.
 * Handles idempotency UX: when an action already exists, exposes it for opening.
 *
 * Usage:
 *   const { openActionDrawer } = useActionDrawer();
 *   openActionDrawer({ prefill, siteId, sourceType, sourceId, idempotencyKey, evidenceRequired }, { onSave });
 */
import { createContext, useContext, useState, useCallback } from 'react';
import CreateActionDrawer from '../components/CreateActionDrawer';
import { useToast } from '../ui/ToastProvider';

const ActionDrawerContext = createContext(null);

export function ActionDrawerProvider({ children }) {
  const { toast } = useToast();
  const [state, setState] = useState({ open: false, payload: null, onSave: null });
  // Idempotency: last existing action for "open" UX
  const [existingAction, setExistingAction] = useState(null);

  const openActionDrawer = useCallback((payload = {}, { onSave } = {}) => {
    setExistingAction(null);
    setState({ open: true, payload, onSave: onSave || null });
  }, []);

  const closeDrawer = useCallback(() => {
    setState({ open: false, payload: null, onSave: null });
  }, []);

  const handleSave = useCallback(
    (result) => {
      // Idempotency UX: if backend returned existing action
      if (result?._existed) {
        setExistingAction(result);
        toast('Action déjà créée pour cette source', 'info');
      }
      state.onSave?.(result);
      closeDrawer();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state.onSave, closeDrawer, toast]
  );

  return (
    <ActionDrawerContext.Provider value={{ openActionDrawer, existingAction }}>
      {children}
      <CreateActionDrawer
        open={state.open}
        onClose={closeDrawer}
        onSave={handleSave}
        prefill={state.payload?.prefill}
        siteId={state.payload?.siteId}
        sourceType={state.payload?.sourceType}
        sourceId={state.payload?.sourceId}
        idempotencyKey={state.payload?.idempotencyKey}
        evidenceRequired={state.payload?.evidenceRequired}
      />
    </ActionDrawerContext.Provider>
  );
}

const NOOP_CTX = { openActionDrawer: () => {}, existingAction: null };

export function useActionDrawer() {
  const ctx = useContext(ActionDrawerContext);
  if (!ctx) {
    // Graceful fallback — allows rendering outside provider (e.g. during SSR or lazy load race)
    console.warn('useActionDrawer called outside ActionDrawerProvider — using no-op fallback');
    return NOOP_CTX;
  }
  return ctx;
}

export default ActionDrawerContext;
