import Tooltip from '../../../ui/Tooltip';

import {
  TARGET_MODULE_DISABLED_TOOLTIP,
  TARGET_MODULE_LABELS,
  TARGET_MODULE_UI_AVAILABLE,
} from '../constants';

/**
 * M2-5.3.B — Affichage d'un link (read-only).
 *
 * `action_center_item` : affiché en info (non cliquable — navigation
 * cross-item différée M3+). Les 6 autres modules : visuellement disabled
 * + tooltip. Aucun filtrage silencieux — tous les links sont affichés.
 */
export function LinkItem({ link }) {
  const moduleLabel = TARGET_MODULE_LABELS[link.target_module] || link.target_module;
  const isAvailable = TARGET_MODULE_UI_AVAILABLE.includes(link.target_module);

  const content = (
    <article
      className={`rounded border p-3 ${
        isAvailable ? 'border-gray-200 bg-white' : 'border-gray-200 bg-gray-50 opacity-60'
      }`}
    >
      <div className="flex items-baseline gap-2">
        <span className="text-xs uppercase tracking-wide text-gray-500">{moduleLabel}</span>
        {link.relation && <span className="text-xs text-gray-400">· {link.relation}</span>}
      </div>
      <div className="mt-1 truncate font-mono text-sm text-gray-700">{link.target_id}</div>
      {link.link_type && <div className="mt-1 text-xs text-gray-500">{link.link_type}</div>}
    </article>
  );

  if (isAvailable) return content;

  return <Tooltip text={TARGET_MODULE_DISABLED_TOOLTIP}>{content}</Tooltip>;
}
