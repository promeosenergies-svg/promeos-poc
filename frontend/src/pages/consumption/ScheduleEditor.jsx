/**
 * PROMEOS — ScheduleEditor V1.1
 * Multi-interval schedule editor: 0..n plages par jour.
 * Validates: HH:MM format, start < end, no overlap, no midnight crossing.
 * Appelle PUT /api/site/{siteId}/schedule puis déclenche un recalcul.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { Clock, Wand2, Save, RefreshCw, Plus, Trash2 } from 'lucide-react';
import { putSiteSchedule, suggestSchedule, refreshConsumptionDiagnose } from '../../services/api';
import { Card, CardBody, Badge, Button } from '../../ui';
import { useToast } from '../../ui/ToastProvider';

import { validateDay, parseHHMM } from './scheduleValidation';

const DAY_KEYS = ['0', '1', '2', '3', '4', '5', '6'];
const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const DEFAULT_INTERVAL = { start: '08:00', end: '19:00' };

// ─── Convert legacy schedule → intervals ───

function scheduleToIntervals(schedule) {
  // If intervals_json is already present, parse it
  if (schedule?.intervals_json) {
    try {
      const parsed = typeof schedule.intervals_json === 'string'
        ? JSON.parse(schedule.intervals_json)
        : schedule.intervals_json;
      // Ensure all 7 days exist
      const result = {};
      for (const k of DAY_KEYS) result[k] = parsed[k] || [];
      return result;
    } catch {
      // fall through to legacy conversion
    }
  }

  // Legacy conversion: open_days + open_time/close_time → intervals
  const openDays = new Set(
    (schedule?.open_days || '0,1,2,3,4').split(',').map(Number)
  );
  const openTime = schedule?.open_time || '08:00';
  const closeTime = schedule?.close_time || '19:00';

  const result = {};
  for (const k of DAY_KEYS) {
    result[k] = openDays.has(Number(k))
      ? [{ start: openTime, end: closeTime }]
      : [];
  }
  return result;
}

// ─── Convert intervals → payload ───

function intervalsToPayload(intervals, timezone) {
  // Compute legacy fields for backward compatibility
  const openDayKeys = DAY_KEYS.filter((k) => intervals[k]?.length > 0);
  const openDays = openDayKeys.length > 0 ? openDayKeys.join(',') : '0,1,2,3,4';

  let earliest = '23:59';
  let latest = '00:00';
  for (const slots of Object.values(intervals)) {
    for (const s of slots) {
      if (s.start < earliest) earliest = s.start;
      if (s.end > latest) latest = s.end;
    }
  }
  if (earliest === '23:59') earliest = '08:00';
  if (latest === '00:00') latest = '19:00';

  return {
    open_days: openDays,
    open_time: earliest,
    close_time: latest,
    is_24_7: false,
    timezone: timezone || 'Europe/Paris',
    exceptions_json: null,
    intervals_json: JSON.stringify(intervals),
  };
}

// ─── Component ───

export default function ScheduleEditor({ schedule, siteId, onSaved }) {
  const { toast } = useToast();

  const [intervals, setIntervals] = useState(() => scheduleToIntervals(schedule));
  const [is247, setIs247] = useState(schedule?.is_24_7 ?? false);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [dirty, setDirty] = useState(false);
  const timezone = schedule?.timezone || 'Europe/Paris';

  // Sync if parent data changes
  useEffect(() => {
    setIntervals(scheduleToIntervals(schedule));
    setIs247(schedule?.is_24_7 ?? false);
    setDirty(false);
  }, [schedule]);

  // Validation
  const dayErrors = useMemo(() => {
    if (is247) return {};
    const errs = {};
    for (const k of DAY_KEYS) {
      const e = validateDay(intervals[k]);
      if (e.length > 0) errs[k] = e;
    }
    return errs;
  }, [intervals, is247]);

  const hasErrors = Object.keys(dayErrors).length > 0;

  // ─── Handlers ───

  const updateSlot = useCallback((day, idx, field, value) => {
    setIntervals((prev) => {
      const next = { ...prev };
      next[day] = [...(prev[day] || [])];
      next[day][idx] = { ...next[day][idx], [field]: value };
      return next;
    });
    setDirty(true);
  }, []);

  const addSlot = useCallback((day) => {
    setIntervals((prev) => {
      const next = { ...prev };
      const existing = prev[day] || [];
      // Suggest a start after last end, or default
      const lastEnd = existing.length > 0 ? existing[existing.length - 1].end : '08:00';
      const endMin = parseHHMM(lastEnd);
      const sugEnd = endMin !== null && endMin + 60 <= 23 * 60 + 59
        ? `${String(Math.floor((endMin + 60) / 60)).padStart(2, '0')}:${String((endMin + 60) % 60).padStart(2, '0')}`
        : '19:00';
      next[day] = [...existing, { start: lastEnd, end: sugEnd }];
      return next;
    });
    setDirty(true);
  }, []);

  const removeSlot = useCallback((day, idx) => {
    setIntervals((prev) => {
      const next = { ...prev };
      next[day] = prev[day].filter((_, i) => i !== idx);
      return next;
    });
    setDirty(true);
  }, []);

  const handleSuggest = async () => {
    if (!siteId) return;
    setSuggesting(true);
    try {
      const sug = await suggestSchedule(siteId);
      if (sug?.suggested_schedule) {
        const s = sug.suggested_schedule;
        // Convert suggestion to intervals
        const openDaysSet = new Set(
          (s.open_days || '0,1,2,3,4').split(',').map(Number)
        );
        const newIntervals = {};
        for (const k of DAY_KEYS) {
          newIntervals[k] = openDaysSet.has(Number(k))
            ? [{ start: s.open_time || '08:00', end: s.close_time || '19:00' }]
            : [];
        }
        setIntervals(newIntervals);
        setIs247(s.is_24_7 ?? false);
        setDirty(true);
        toast(`Suggestion NAF appliqu\u00e9e (${sug.type_site || 'arch\u00e9type'})`, 'info');
      }
    } catch {
      toast('Impossible de r\u00e9cup\u00e9rer la suggestion NAF', 'error');
    } finally {
      setSuggesting(false);
    }
  };

  const handleSave = async () => {
    if (!siteId || hasErrors) return;
    setSaving(true);
    try {
      let payload;
      if (is247) {
        payload = {
          open_days: '0,1,2,3,4,5,6',
          open_time: '00:00',
          close_time: '23:59',
          is_24_7: true,
          timezone,
          exceptions_json: null,
          intervals_json: null,
        };
      } else {
        payload = intervalsToPayload(intervals, timezone);
      }
      await putSiteSchedule(siteId, payload);
      await refreshConsumptionDiagnose(siteId, 30);
      toast('Horaires sauvegard\u00e9s \u2014 diagnostic recalcul\u00e9', 'success');
      setDirty(false);
      onSaved?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.errors) {
        toast(`Validation: ${detail.errors[0]?.message || 'Erreur'}`, 'error');
      } else {
        toast('Erreur lors de la sauvegarde', 'error');
      }
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
            <h3 className="text-sm font-semibold text-gray-700">Horaires d&apos;activit\u00e9</h3>
            {schedule?.source && (
              <Badge variant="neutral">{schedule.source}</Badge>
            )}
            {dirty && <Badge variant="warn">modifi\u00e9</Badge>}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm" variant="outline"
              onClick={handleSuggest}
              disabled={suggesting}
              title="Appliquer les horaires par d\u00e9faut du code NAF"
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

        {/* Day-by-day intervals */}
        {!is247 && (
          <div className="space-y-3">
            {DAY_KEYS.map((dayKey, d) => {
              const slots = intervals[dayKey] || [];
              const errs = dayErrors[dayKey];
              const isOpen = slots.length > 0;

              return (
                <div key={dayKey} data-testid={`day-row-${dayKey}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <button
                      type="button"
                      onClick={() => {
                        if (isOpen) {
                          setIntervals((prev) => ({ ...prev, [dayKey]: [] }));
                        } else {
                          setIntervals((prev) => ({
                            ...prev,
                            [dayKey]: [{ ...DEFAULT_INTERVAL }],
                          }));
                        }
                        setDirty(true);
                      }}
                      className={`w-10 h-6 rounded text-[10px] font-medium transition-colors border ${
                        isOpen
                          ? 'bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-200'
                          : 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      {DAY_LABELS[d]}
                    </button>

                    {isOpen && (
                      <div className="flex flex-wrap items-center gap-2 flex-1">
                        {slots.map((slot, idx) => (
                          <div key={idx} className="flex items-center gap-1" data-testid={`interval-${dayKey}-${idx}`}>
                            <input
                              type="time"
                              value={slot.start}
                              data-testid={`interval-start-${dayKey}-${idx}`}
                              onChange={(e) => updateSlot(dayKey, idx, 'start', e.target.value)}
                              className={`border rounded px-1.5 py-0.5 text-xs text-gray-700 w-20 focus:outline-none focus:ring-1 ${
                                errs ? 'border-red-300 focus:ring-red-300' : 'border-gray-200 focus:ring-indigo-300'
                              }`}
                            />
                            <span className="text-[10px] text-gray-400">\u2192</span>
                            <input
                              type="time"
                              value={slot.end}
                              data-testid={`interval-end-${dayKey}-${idx}`}
                              onChange={(e) => updateSlot(dayKey, idx, 'end', e.target.value)}
                              className={`border rounded px-1.5 py-0.5 text-xs text-gray-700 w-20 focus:outline-none focus:ring-1 ${
                                errs ? 'border-red-300 focus:ring-red-300' : 'border-gray-200 focus:ring-indigo-300'
                              }`}
                            />
                            <button
                              type="button"
                              onClick={() => removeSlot(dayKey, idx)}
                              className="text-gray-300 hover:text-red-400 transition-colors"
                              title="Supprimer cette plage"
                              data-testid={`remove-interval-${dayKey}-${idx}`}
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          onClick={() => addSlot(dayKey)}
                          className="text-indigo-400 hover:text-indigo-600 transition-colors"
                          title="Ajouter une plage"
                          data-testid={`add-interval-${dayKey}`}
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}

                    {!isOpen && (
                      <span className="text-[10px] text-gray-300 italic">Ferm\u00e9</span>
                    )}
                  </div>

                  {errs && (
                    <div data-testid={`day-error-${dayKey}`} className="ml-12 mt-0.5">
                      {errs.map((e, i) => (
                        <p key={i} className="text-xs text-red-500">{e}</p>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Save */}
        <div className="mt-4 flex justify-end">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !dirty || hasErrors}
            data-testid="schedule-save"
          >
            {saving
              ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
              : <Save className="w-3 h-3 mr-1" />}
            {saving ? 'Sauvegarde\u2026' : 'Sauvegarder & Recalculer'}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
