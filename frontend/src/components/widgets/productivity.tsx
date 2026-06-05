/* QUARK — 생산성/정보 위젯: 일정·액션·습관·포모도로·D-Day·수분·시세 */
import { useEffect, useState } from 'react';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { useHomeStore } from '@/stores/homeStore';
import { QDATA, fmtMan } from '@/data/quarkData';
import type { MarketRow, ScheduleTag } from '@/types/quark';

const TAG_COLOR: Record<ScheduleTag, string> = {
  회의: 'var(--acc-bright)',
  마감: 'var(--bad)',
  작업: 'var(--warn)',
  개인: 'var(--tx-mid)',
};

/* ============ 오늘 일정 ============ */
export function ScheduleCard() {
  const items = QDATA.schedule;
  return (
    <div className="card hov s5">
      <CardHead icon="calendar" title="오늘 일정" meta={items.length + '건'} />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {items.map((it, i) => (
          <div key={i} className="sched-row">
            <span
              className="mono"
              style={{
                fontSize: 12.5,
                color: it.soon ? 'var(--acc-bright)' : 'var(--tx-mid)',
                width: 46,
                flex: 'none',
                fontWeight: 600,
              }}
            >
              {it.t}
            </span>
            <span className="sched-line" style={{ background: TAG_COLOR[it.tag] || 'var(--tx-faint)' }} />
            <span
              style={{
                fontSize: 13,
                color: 'var(--tx-hi)',
                flex: 1,
                minWidth: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {it.title}
            </span>
            {it.soon && <span className="soon-tag">곧</span>}
            <span style={{ fontSize: 10.5, color: 'var(--tx-low)', flex: 'none' }}>{it.tag}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============ 습관 + 스트릭 ============ */
export function HabitsCard() {
  const habits = useHomeStore((s) => s.habits);
  const onToggle = useHomeStore((s) => s.toggleHabit);
  const doneCt = habits.filter((h) => h.done).length;
  return (
    <div className="card hov s4">
      <CardHead icon="check" title="오늘의 습관" meta={doneCt + '/' + habits.length} metaAcc={doneCt === habits.length} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {habits.map((h, i) => (
          <div key={i} className="between habit-row" onClick={() => onToggle(i)}>
            <div className="row" style={{ gap: 10, minWidth: 0 }}>
              <span className={'cbox' + (h.done ? ' on' : '')}>{h.done && <Icon name="check" />}</span>
              <span
                style={{
                  fontSize: 13,
                  color: h.done ? 'var(--tx-hi)' : 'var(--tx-mid)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {h.name}
              </span>
            </div>
            <span className="streak">
              <Icon name="flame" fill /> {h.streak}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============ 액션 리스트 ============ */
export function ActionsCard() {
  const actions = useHomeStore((s) => s.actions);
  const onToggle = useHomeStore((s) => s.toggleAction);
  return (
    <div className="card hov s3">
      <CardHead icon="zap" title="오늘의 액션" meta={actions.filter((a) => !a.done).length + ' 남음'} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
        {actions.map((a, i) => (
          <div key={i} className="row habit-row" style={{ gap: 10 }} onClick={() => onToggle(i)}>
            <span className={'cbox' + (a.done ? ' on' : '')}>{a.done && <Icon name="check" />}</span>
            <span
              style={{
                fontSize: 12.5,
                color: a.done ? 'var(--tx-low)' : 'var(--tx)',
                textDecoration: a.done ? 'line-through' : 'none',
                lineHeight: 1.35,
              }}
            >
              {a.t}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============ 포모도로 ============ */
export function PomodoroCard() {
  const FULL = 25 * 60;
  const [sec, setSec] = useState(FULL);
  const [run, setRun] = useState(false);
  useEffect(() => {
    if (!run) return;
    const id = setInterval(() => setSec((s) => (s <= 1 ? 0 : s - 1)), 1000);
    return () => clearInterval(id);
  }, [run]);
  useEffect(() => {
    if (sec === 0) setRun(false);
  }, [sec]);
  const mm = String(Math.floor(sec / 60)).padStart(2, '0');
  const ss = String(sec % 60).padStart(2, '0');
  const pct = ((FULL - sec) / FULL) * 100;
  const R = 40;
  const C = 2 * Math.PI * R;
  return (
    <div className="card hov s3">
      <CardHead icon="timer" title="포모도로" meta={run ? '진행 중' : '대기'} metaAcc={run} />
      <div style={{ display: 'grid', placeItems: 'center', position: 'relative', margin: '4px 0 14px' }}>
        <svg width="110" height="110" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="55" cy="55" r={R} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
          <circle
            cx="55"
            cy="55"
            r={R}
            fill="none"
            stroke="var(--acc)"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={C - (C * pct) / 100}
            style={{ transition: 'stroke-dashoffset .9s linear', filter: 'drop-shadow(0 0 5px var(--acc-glow))' }}
          />
        </svg>
        <div style={{ position: 'absolute', textAlign: 'center' }}>
          <div className="mono" style={{ fontSize: 26, fontWeight: 700, color: 'var(--tx-hi)', letterSpacing: 1 }}>
            {mm}:{ss}
          </div>
          <div style={{ fontSize: 10, color: 'var(--tx-mid)' }}>집중 세션</div>
        </div>
      </div>
      <div className="row" style={{ gap: 8 }}>
        <button className="pill acc" style={{ flex: 1, justifyContent: 'center' }} onClick={() => setRun((r) => !r)}>
          <Icon name={run ? 'pause' : 'play'} fill /> {run ? '정지' : '시작'}
        </button>
        <button
          className="pill"
          onClick={() => {
            setRun(false);
            setSec(FULL);
          }}
        >
          <Icon name="reset" />
        </button>
      </div>
    </div>
  );
}

/* ============ D-Day ============ */
export function DdayCard() {
  const items = QDATA.dday;
  return (
    <div className="card hov s3">
      <CardHead icon="target" title="D-Day" meta={items.length + '개'} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
        {items.map((d, i) => (
          <div key={i} className="between" style={{ alignItems: 'flex-end' }}>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: 12.5,
                  color: 'var(--tx-hi)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {d.label}
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--tx-mid)' }}>{d.days <= 14 ? '곧 다가와' : '여유 있어'}</div>
            </div>
            <div
              className="mono"
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: d.days <= 14 ? 'var(--acc-bright)' : 'var(--tx)',
                lineHeight: 1,
                flex: 'none',
              }}
            >
              D-{d.days}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============ 물 마시기 ============ */
export function WaterCard() {
  const ml = useHomeStore((s) => s.water);
  const onAdd = useHomeStore((s) => s.addWater);
  const goal = 2000;
  const pct = Math.min(100, Math.round((ml / goal) * 100));
  return (
    <div className="card hov s3">
      <CardHead icon="droplet" title="수분 섭취" meta={pct + '%'} metaAcc={pct >= 100} />
      <div className="row" style={{ gap: 16, alignItems: 'flex-end', marginBottom: 14 }}>
        <div className="water-tube">
          <div className="fill" style={{ height: pct + '%' }} />
        </div>
        <div style={{ flex: 1 }}>
          <div className="mono" style={{ fontSize: 24, fontWeight: 700, color: 'var(--tx-hi)', lineHeight: 1 }}>
            {(ml / 1000).toFixed(2)}
            <span style={{ fontSize: 13, color: 'var(--tx-mid)' }}>L</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--tx-mid)', marginTop: 4 }}>
            목표 {(goal / 1000).toFixed(1)}L · {Math.max(0, goal - ml)}ml 남음
          </div>
        </div>
      </div>
      <button className="pill acc" style={{ width: '100%', justifyContent: 'center' }} onClick={onAdd}>
        <Icon name="plus" /> 250ml 기록
      </button>
    </div>
  );
}

/* ============ 시세 ============ */
function MarketRowView({ sym, name, price, chg }: MarketRow) {
  return (
    <div className="between" style={{ padding: '7px 0' }}>
      <div className="row" style={{ gap: 9, minWidth: 0 }}>
        <span className="mkt-sym">{sym}</span>
        <span
          style={{
            fontSize: 11.5,
            color: 'var(--tx-mid)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {name}
        </span>
      </div>
      <div style={{ textAlign: 'right', flex: 'none' }}>
        <div className="mono" style={{ fontSize: 12.5, color: 'var(--tx-hi)', fontWeight: 600 }}>
          ₩{fmtMan(price)}
        </div>
        <div
          className="mono"
          style={{
            fontSize: 10.5,
            color: chg >= 0 ? 'var(--ok)' : 'var(--bad)',
            display: 'flex',
            gap: 2,
            justifyContent: 'flex-end',
            alignItems: 'center',
          }}
        >
          <span style={{ width: 10, height: 10 }}>
            <Icon name={chg >= 0 ? 'arrowUp' : 'arrowDown'} />
          </span>
          {Math.abs(chg)}%
        </div>
      </div>
    </div>
  );
}

export function MarketCard() {
  return (
    <div className="card hov s3">
      <CardHead icon="coin" title="시세" meta="실시간" />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {QDATA.crypto.map((c) => (
          <MarketRowView key={c.sym} {...c} />
        ))}
        <div style={{ height: 1, background: 'var(--inset-line)', margin: '4px 0' }} />
        {QDATA.fx.map((c) => (
          <MarketRowView key={c.sym} {...c} />
        ))}
      </div>
    </div>
  );
}
