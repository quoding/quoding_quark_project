/* QUARK — 일정 & 비서 화면 (캘린더 일/주/월 · 할일 · 아이디어 캡처 · 자동 알림) */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { TodayCard } from '@/components/widgets/productivity';
import { QDATA } from '@/data/quarkData';
import type { AlertKind, ScheduleTag } from '@/types/quark';
import type { IconName } from '@/components/Icon';

const TAG_COLOR: Record<ScheduleTag, string> = {
  회의: 'var(--acc-bright)',
  마감: 'var(--bad)',
  작업: 'var(--warn)',
  개인: 'var(--plant)',
};
const DOW = ['월', '화', '수', '목', '금', '토', '일'];

// ── API types ────────────────────────────────────────────────────────────────

interface ApiEvent {
  id: number;
  title: string;
  scheduled_at: string;
  tag: string;
  done: boolean;
  created_at: string;
}


interface ApiIdea {
  id: number;
  text: string;
  tag: string;
  created_at: string;
}

// ── Calendar views ────────────────────────────────────────────────────────────

/** UTC 시각 문자열 반환 (에이전트가 UTC naive로 저장하므로 UTC 기준 표시) */
function utcTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
}

function DayView({ dateStr }: { dateStr: string }) {
  const { data: events = [] } = useQuery<ApiEvent[]>({
    queryKey: ['events', dateStr],
    queryFn: () =>
      axios.get<ApiEvent[]>(`/api/agenda/events?date_filter=${dateStr}`).then((r) => r.data),
    refetchInterval: 30_000,
  });

  const hours = [8, 10, 12, 14, 16, 18, 20, 22];
  const toY = (h: number, m: number) =>
    (((h - 8) * 60 + m) / ((22 - 8) * 60)) * 100;

  return (
    <div className="day-view scroll">
      <div className="day-grid">
        {hours.map((h) => (
          <div key={h} className="day-hour">
            <span className="mono">{String(h).padStart(2, '0')}:00</span>
          </div>
        ))}
        {events.map((ev) => {
          const d = new Date(ev.scheduled_at);
          const h = d.getUTCHours();
          const m = d.getUTCMinutes();
          const t = utcTime(ev.scheduled_at);
          const tag = ev.tag as ScheduleTag;
          const color = TAG_COLOR[tag] ?? 'var(--tx-mid)';
          const yPct = toY(h, m);
          if (yPct < -5 || yPct > 105) return null;
          return (
            <div
              key={ev.id}
              className="day-evt"
              style={{
                top: Math.max(0, yPct) + '%',
                borderColor: color,
                background: `color-mix(in srgb, ${color} 14%, transparent)`,
              }}
            >
              <span className="mono" style={{ color, fontSize: 11 }}>{t}</span>
              <span style={{ fontSize: 12.5, color: 'var(--tx-hi)' }}>{ev.title}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WeekView() {
  const today = (new Date().getDay() + 6) % 7;
  const base = new Date();
  base.setDate(base.getDate() - today);
  const monday = new Date(base);
  const sunday = new Date(base);
  sunday.setDate(base.getDate() + 6);
  const dateFrom = monday.toISOString().slice(0, 10);
  const dateTo = sunday.toISOString().slice(0, 10);

  const { data: events = [] } = useQuery<ApiEvent[]>({
    queryKey: ['events-week', dateFrom],
    queryFn: () =>
      axios
        .get<ApiEvent[]>(`/api/agenda/events?date_from=${dateFrom}&date_to=${dateTo}`)
        .then((r) => r.data),
  });

  return (
    <div className="week-view scroll">
      {DOW.map((dow, i) => {
        const d = new Date(base);
        d.setDate(base.getDate() + i);
        const dayStr = d.toISOString().slice(0, 10);
        const dayEvents = events.filter(
          (ev) => new Date(ev.scheduled_at).toISOString().slice(0, 10) === dayStr,
        );
        return (
          <div key={i} className={'week-col' + (i === today ? ' today' : '')}>
            <div className="week-head">
              <span className="wd">{dow}</span>
              <span className={'wn mono' + (i === today ? ' on' : '')}>{d.getDate()}</span>
            </div>
            <div className="week-evts">
              {dayEvents.map((ev) => {
                const t = utcTime(ev.scheduled_at);
                const tag = ev.tag as ScheduleTag;
                const color = TAG_COLOR[tag] ?? 'var(--tx-mid)';
                return (
                  <div key={ev.id} className="week-chip" style={{ borderLeftColor: color }}>
                    <span className="mono" style={{ fontSize: 10, color }}>{t}</span>
                    <span style={{ fontSize: 11.5, color: 'var(--tx-hi)', lineHeight: 1.3 }}>{ev.title}</span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MonthView() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const first = (new Date(y, m, 1).getDay() + 6) % 7;
  const days = new Date(y, m + 1, 0).getDate();
  const marks: Record<number, ScheduleTag[]> = {
    9: ['회의'],
    12: ['작업', '마감'],
    15: ['작업'],
    18: ['회의'],
    22: ['개인'],
    26: ['작업'],
  };
  const cells: (number | null)[] = [];
  for (let i = 0; i < first; i++) cells.push(null);
  for (let d = 1; d <= days; d++) cells.push(d);
  return (
    <div className="month-view">
      <div className="month-dow">
        {DOW.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
      <div className="month-grid">
        {cells.map((d, i) => (
          <div
            key={i}
            className={'month-cell' + (d === now.getDate() ? ' today' : '') + (d == null ? ' empty' : '')}
          >
            {d != null && (
              <>
                <span className="mono md-num">{d}</span>
                <span className="md-dots">
                  {(marks[d] || []).map((t, j) => (
                    <i key={j} style={{ background: TAG_COLOR[t] }} />
                  ))}
                </span>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function CalendarCard() {
  const [view, setView] = useState<'day' | 'week' | 'month'>('day');
  const VIEWS = [
    { id: 'day', n: '일간' },
    { id: 'week', n: '주간' },
    { id: 'month', n: '월간' },
  ] as const;
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  return (
    <div className="card s8" style={{ minHeight: 430 }}>
      <div className="card-h">
        <span className="ico">
          <Icon name="calendar" />
        </span>
        <span className="ttl">캘린더</span>
        <span className="meta">
          {now.getFullYear()}.{String(now.getMonth() + 1).padStart(2, '0')}
        </span>
        <div className="seg-tabs" style={{ marginLeft: 12 }}>
          {VIEWS.map((v) => (
            <button key={v.id} className={'seg-tab' + (view === v.id ? ' on' : '')} onClick={() => setView(v.id)}>
              {v.n}
            </button>
          ))}
        </div>
      </div>
      {view === 'day' && <DayView dateStr={todayStr} />}
      {view === 'week' && <WeekView />}
      {view === 'month' && <MonthView />}
    </div>
  );
}

// ── Todos ─────────────────────────────────────────────────────────────────────
// productivity.tsx의 공유 컴포넌트 사용 (상단 import 참고)

// ── Idea Capture ──────────────────────────────────────────────────────────────

function IdeaCapture() {
  const qc = useQueryClient();
  const [val, setVal] = useState('');
  const [tag, setTag] = useState('아이디어');
  const TAGS = ['아이디어', '하드웨어', 'SW', '영상'];

  const { data: ideas = [] } = useQuery<ApiIdea[]>({
    queryKey: ['ideas'],
    queryFn: () => axios.get<ApiIdea[]>('/api/ideas').then((r) => r.data),
  });

  const addIdea = useMutation({
    mutationFn: (body: { text: string; tag: string }) =>
      axios.post<ApiIdea>('/api/ideas', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ideas'] });
      setVal('');
    },
  });

  const submit = () => {
    if (!val.trim()) return;
    addIdea.mutate({ text: val.trim(), tag });
  };

  return (
    <div className="card s6">
      <CardHead icon="idea" title="아이디어 캡처" meta={ideas.length + '개'} />
      <div className="idea-input">
        <input
          value={val}
          placeholder="번뜩인 생각을 바로 적어둬…"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit();
          }}
        />
        <button className="qc-send" onClick={submit}>
          <Icon name="plus" />
        </button>
      </div>
      <div className="idea-tags">
        {TAGS.map((tg) => (
          <button key={tg} className={'idea-tagbtn' + (tag === tg ? ' on' : '')} onClick={() => setTag(tg)}>
            {tg}
          </button>
        ))}
      </div>
      <div className="idea-list scroll">
        {ideas.map((it) => (
          <div key={it.id} className="idea-card">
            <div className="row between" style={{ marginBottom: 5 }}>
              <span className="idea-pill">{it.tag}</span>
              <span className="mono" style={{ fontSize: 10.5, color: 'var(--tx-low)' }}>
                {new Date(it.created_at).toLocaleDateString('ko-KR')}
              </span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--tx)', lineHeight: 1.5 }}>{it.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AlertsCard() {
  const KIND: Record<AlertKind, IconName> = { deadline: 'flame', meeting: 'bell', review: 'check' };
  return (
    <div className="card s6">
      <CardHead
        icon="bell"
        title="쿼크 자동 알림"
        meta={QDATA.alerts.filter((a) => a.urgent).length + ' 긴급'}
        metaAcc
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
        {QDATA.alerts.map((a, i) => (
          <div key={i} className={'alert-row' + (a.urgent ? ' urgent' : '')}>
            <span className={'alert-ico' + (a.urgent ? ' urgent' : '')}>
              <Icon name={KIND[a.kind]} />
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, color: 'var(--tx-hi)' }}>{a.title}</div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)', marginTop: 2 }}>{a.desc}</div>
            </div>
            <span className="mono" style={{ fontSize: 11, color: a.urgent ? 'var(--bad)' : 'var(--tx-mid)', flex: 'none' }}>
              {a.when}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AgendaScreen() {
  return (
    <div className="canvas scroll">
      <div className="grid">
        <CalendarCard />
        <div className="s4" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap)' }}>
          <TodayCard />
        </div>
        <IdeaCapture />
        <AlertsCard />
      </div>
    </div>
  );
}
