import { Inbox } from 'lucide-react';
import Button from './Button';

export default function EmptyState({ icon: Icon = Inbox, title, text, ctaLabel, onCta, actions }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4">
        <Icon size={28} className="text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700 mb-1">{title}</h3>
      {text && <p className="text-sm text-gray-500 mb-6 max-w-md">{text}</p>}
      <div className="flex items-center gap-3">
        {ctaLabel && onCta && <Button onClick={onCta}>{ctaLabel}</Button>}
        {actions}
      </div>
    </div>
  );
}
