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

export function useActionDrawer() {
  const ctx = useContext(ActionDrawerContext);
  if (!ctx) throw new Error('useActionDrawer must be used within ActionDrawerProvider');
  return ctx;
}

export default ActionDrawerContext;
