/**
 * NextBestActionCard — Hero card showing the single most important action.
 * Placed at top of ConformitePage, before tabs.
 */
import { Database, Clock, FileText, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card, CardBody, Badge, Button } from '../../ui';

const SEVERITY_STYLE = {
  critical: { border: 'border-red-300', bg: 'bg-red-50', badge: 'crit' },
  high: { border: 'border-amber-300', bg: 'bg-amber-50', badge: 'warn' },
  medium: { border: 'border-blue-300', bg: 'bg-blue-50', badge: 'info' },
  low: { border: 'border-green-300', bg: 'bg-green-50', badge: 'ok' },
};

const ICON_MAP = {
  Database,
  Clock,
  FileText,
  AlertTriangle,
  CheckCircle: CheckCircle2,
  CheckCircle2,
};

export default function NextBestActionCard({ action, onAction }) {
  if (!action) return null;

  const style = SEVERITY_STYLE[action.severity] || SEVERITY_STYLE.medium;
  const Icon = ICON_MAP[action.icon] || AlertTriangle;

  return (
    <div data-testid="next-best-action" className="mb-4">
      <Card className={`border-l-4 ${style.border}`}>
        <CardBody className={style.bg}>
          <div className="flex items-start gap-4">
            <div className="p-2.5 rounded-lg bg-white/80 shadow-sm shrink-0">
              <Icon size={20} className="text-gray-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-sm font-bold text-gray-900">{action.title}</h3>
                <Badge status={style.badge}>
                  {action.severity === 'critical'
                    ? 'Urgent'
                    : action.severity === 'high'
                      ? 'Important'
                      : action.severity === 'medium'
                        ? 'Recommandé'
                        : 'Info'}
                </Badge>
              </div>
              <p className="text-sm text-gray-600">{action.description}</p>
            </div>
            <Button data-testid="nba-cta" size="sm" onClick={() => onAction(action.ctaAction)}>
              {action.ctaLabel}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
