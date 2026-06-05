/* QUARK — 일정 & 비서 화면 (캘린더 일/주/월 · 액션 · 아이디어 캡처 · 자동 알림) */
import { useState } from 'react';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { ActionsCard } from '@/components/widgets/productivity';
import { useHomeStore } from '@/stores/homeStore';
import { QDATA } from '@/data/quarkData';
import type { AlertKind, ScheduleTag, WeekEvent } from '@/types/quark';
import type { IconName } from '@/components/Icon';

const TAG_COLOR: Record<ScheduleTag, string> = {
  회의: 'var(--acc-bright)',
  마감: 'var(--bad)',
  작업: 'var(--warn)',
  개인: 'var(--plant)',
};
const DOW = ['월', '화', '수', '목', '금', '토', '일'];

function DayView() {
  const items = QDATA.schedule;
  const hours = [8, 10, 12, 14, 16, 18, 20, 22];
  const toY = (t: string) => {
    const [h, m] = t.split(':').map(Number);
    return (((h - 8) * 60 + m) / ((22 - 8) * 60)) * 100;
  };
  return (
    <div className="day-view scroll">
      <div className="day-grid">
        {hours.map((h) => (
          <div key={h} className="day-hour">
            <span className="mono">{String(h).padStart(2, '0')}:00</span>
          </div>
        ))}
        {items.map((it, i) => (
          <div
            key={i}
            className="day-evt"
            style={{
              top: toY(it.t) + '%',
              borderColor: TAG_COLOR[it.tag],
              background: `color-mix(in srgb, ${TAG_COLOR[it.tag]} 14%, transparent)`,
            }}
          >
            <span className="mono" style={{ color: TAG_COLOR[it.tag], fontSize: 11 }}>
              {it.t}
            </span>
            <span style={{ fontSize: 12.5, color: 'var(--tx-hi)' }}>{it.title}</span>
            {it.soon && (
              <span className="soon-tag" style={{ marginLeft: 'auto' }}>
                곧
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function WeekView({ week }: { week: WeekEvent[][] }) {
  const today = (new Date().getDay() + 6) % 7; // Mon=0
  const base = new Date();
  base.setDate(base.getDate() - today);
  return (
    <div className="week-view scroll">
      {week.map((evs, i) => {
        const d = new Date(base);
        d.setDate(base.getDate() + i);
        return (
          <div key={i} className={'week-col' + (i === today ? ' today' : '')}>
            <div className="week-head">
              <span className="wd">{DOW[i]}</span>
              <span className={'wn mono' + (i === today ? ' on' : '')}>{d.getDate()}</span>
            </div>
            <div className="week-evts">
              {evs.map((e, j) => (
                <div key={j} className="week-chip" style={{ borderLeftColor: TAG_COLOR[e.tag] }}>
                  <span className="mono" style={{ fontSize: 10, color: TAG_COLOR[e.tag] }}>
                    {e.t}
                  </span>
                  <span style={{ fontSize: 11.5, color: 'var(--tx-hi)', lineHeight: 1.3 }}>{e.title}</span>
                </div>
              ))}
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
  const [view, setView] = useState<'day' | 'week' | 'month'>('week');
  const VIEWS = [
    { id: 'day', n: '일간' },
    { id: 'week', n: '주간' },
    { id: 'month', n: '월간' },
  ] as const;
  const now = new Date();
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
      {view === 'day' && <DayView />}
      {view === 'week' && <WeekView week={QDATA.weekEvents} />}
      {view === 'month' && <MonthView />}
    </div>
  );
}

function IdeaCapture() {
  const ideas = useHomeStore((s) => s.ideas);
  const onAdd = useHomeStore((s) => s.addIdea);
  const [val, setVal] = useState('');
  const [tag, setTag] = useState('아이디어');
  const TAGS = ['아이디어', '하드웨어', 'SW', '영상'];
  const submit = () => {
    if (!val.trim()) return;
    onAdd(val.trim(), tag);
    setVal('');
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
        {ideas.map((it, i) => (
          <div key={i} className="idea-card">
            <div className="row between" style={{ marginBottom: 5 }}>
              <span className="idea-pill">{it.tag}</span>
              <span className="mono" style={{ fontSize: 10.5, color: 'var(--tx-low)' }}>
                {it.time}
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
          <ActionsCard />
        </div>
        <IdeaCapture />
        <AlertsCard />
      </div>
    </div>
  );
}
