/**
 * PROMEOS — ScheduleEditor
 * Éditeur interactif des horaires d'activité d'un site.
 * Appelle PUT /api/site/{siteId}/schedule puis déclenche un recalcul.
 */
import { useState, useEffect } from 'react';
import { Clock, Wand2, Save, RefreshCw } from 'lucide-react';
import { putSiteSchedule, suggestSchedule, refreshConsumptionDiagnose } from '../../services/api';
import { Card, CardBody, Badge, Button } from '../../ui';
import { useToast } from '../../ui/ToastProvider';

const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const DEFAULT_OPEN = '08:00';
const DEFAULT_CLOSE = '19:00';

function parseSchedule(schedule) {
  const openDays = new Set(
    (schedule?.open_days || '0,1,2,3,4').split(',').map(Number)
  );
  return {
    openDays,
    openTime: schedule?.open_time || DEFAULT_OPEN,
    closeTime: schedule?.close_time || DEFAULT_CLOSE,
    is_24_7: schedule?.is_24_7 ?? false,
    timezone: schedule?.timezone || 'Europe/Paris',
  };
}

export default function ScheduleEditor({ schedule, siteId, onSaved }) {
  const { toast } = useToast();
  const parsed = parseSchedule(schedule);

  const [openDays, setOpenDays] = useState(parsed.openDays);
  const [openTime, setOpenTime] = useState(parsed.openTime);
  const [closeTime, setCloseTime] = useState(parsed.closeTime);
  const [is247, setIs247] = useState(parsed.is_24_7);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Sync if parent data changes
  useEffect(() => {
    const p = parseSchedule(schedule);
    setOpenDays(p.openDays);
    setOpenTime(p.openTime);
    setCloseTime(p.closeTime);
    setIs247(p.is_24_7);
    setDirty(false);
  }, [schedule]);

  const toggleDay = (d) => {
    setOpenDays((prev) => {
      const next = new Set(prev);
      if (next.has(d)) next.delete(d);
      else next.add(d);
      return next;
    });
    setDirty(true);
  };

  const handleSuggest = async () => {
    if (!siteId) return;
    setSuggesting(true);
    try {
      const sug = await suggestSchedule(siteId);
      if (sug?.suggested_schedule) {
        const s = sug.suggested_schedule;
        const days = new Set(
          (s.open_days || '0,1,2,3,4').split(',').map(Number)
        );
        setOpenDays(days);
        setOpenTime(s.open_time || DEFAULT_OPEN);
        setCloseTime(s.close_time || DEFAULT_CLOSE);
        setIs247(s.is_24_7 ?? false);
        setDirty(true);
        toast(`Suggestion NAF appliquée (${sug.type_site || 'archétype'})`, 'info');
      }
    } catch {
      toast('Impossible de récupérer la suggestion NAF', 'error');
    } finally {
      setSuggesting(false);
    }
  };

  const handleSave = async () => {
    if (!siteId) return;
    setSaving(true);
    try {
      const payload = {
        open_days: [...openDays].sort().join(','),
        open_time: openTime,
        close_time: closeTime,
        is_24_7: is247,
        timezone: parsed.timezone,
        exceptions_json: null,
      };
      await putSiteSchedule(siteId, payload);
      // Trigger diagnostic recompute → updated offhours_pct
      await refreshConsumptionDiagnose(siteId, 30);
      toast('Horaires sauvegardés — diagnostic recalculé', 'success');
      setDirty(false);
      onSaved?.();
    } catch {
      toast('Erreur lors de la sauvegarde', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardBody>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-gray-700">Horaires d'activité</h3>
            {schedule?.source && (
              <Badge variant="neutral">{schedule.source}</Badge>
            )}
            {dirty && <Badge variant="warn">modifié</Badge>}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm" variant="outline"
              onClick={handleSuggest}
              disabled={suggesting}
              title="Appliquer les horaires par défaut du code NAF"
            >
              <Wand2 className={`w-3 h-3 mr-1 ${suggesting ? 'animate-spin' : ''}`} />
              Suggestion NAF
            </Button>
          </div>
        </div>

        {/* is_24_7 toggle */}
        <div className="flex items-center gap-2 mb-4">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <div
              onClick={() => { setIs247((v) => !v); setDirty(true); }}
              className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${is247 ? 'bg-indigo-500' : 'bg-gray-200'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white shadow mt-0.5 transition-transform ${is247 ? 'translate-x-4 ml-0.5' : 'translate-x-0.5'}`} />
            </div>
            <span className="text-xs text-gray-600">Ouvert 24h/24, 7j/7</span>
          </label>
        </div>

        {/* Day grid */}
        {!is247 && (
          <>
            <div className="grid grid-cols-7 gap-1 mb-4">
              {DAY_LABELS.map((label, d) => {
                const isOpen = openDays.has(d);
                return (
                  <div key={d} className="text-center">
                    <div className="text-[10px] text-gray-400 mb-1">{label}</div>
                    <button
                      onClick={() => toggleDay(d)}
                      className={`w-full h-7 rounded text-[10px] font-medium transition-colors border ${
                        isOpen
                          ? 'bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-200'
                          : 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      {isOpen ? '✓' : '—'}
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Time inputs */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 w-12">Ouverture</label>
                <input
                  type="time"
                  value={openTime}
                  onChange={(e) => { setOpenTime(e.target.value); setDirty(true); }}
                  className="border border-gray-200 rounded px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 w-12">Fermeture</label>
                <input
                  type="time"
                  value={closeTime}
                  onChange={(e) => { setCloseTime(e.target.value); setDirty(true); }}
                  className="border border-gray-200 rounded px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                />
              </div>
            </div>
          </>
        )}

        {/* Save */}
        <div className="mt-4 flex justify-end">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !dirty}
          >
            {saving
              ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
              : <Save className="w-3 h-3 mr-1" />}
            {saving ? 'Sauvegarde…' : 'Sauvegarder & Recalculer'}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
