/**
 * PROMEOS — OpportunitiesCard (Sprint WOW Phase 7.0)
 * 3 max reco cards — Expert only (guarded by caller).
 * Uses tint.module('analyse') for border accent.
 *
 * Props:
 *   opportunities {Opportunity[]} — from buildOpportunities()
 *   onNavigate    {fn}            — navigate(path)
 */
import { Lightbulb, ArrowRight } from 'lucide-react';
import { Card, CardBody, Button, Badge } from '../../ui';
import { tint } from '../../ui/colorTokens';

export default function OpportunitiesCard({ opportunities = [], onNavigate }) {
  if (!opportunities.length) return null;

  const analyseTint = tint.module('analyse');
  const borderClass = analyseTint.raw().activeBorder || 'border-indigo-500';

  return (
    <Card>
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
        <Lightbulb size={15} className="text-indigo-500 shrink-0" />
        <h3 className="text-sm font-semibold text-gray-800">Opportunités</h3>
        <Badge variant="info" className="text-[10px] px-1.5 py-0 ml-1">
          Expert
        </Badge>
      </div>

      <CardBody>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {opportunities.map((opp) => (
            <div
              key={opp.id}
              className={`rounded-lg border border-gray-100 pl-3 pr-4 py-3.5 border-l-[3px] ${borderClass} flex flex-col gap-2`}
            >
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-800 leading-snug">{opp.label}</p>
                {opp.sub && <p className="text-xs text-gray-500 mt-1 leading-snug">{opp.sub}</p>}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onNavigate?.(opp.path)}
                className="self-start text-xs"
              >
                {opp.cta} <ArrowRight size={11} className="ml-1" />
              </Button>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}
