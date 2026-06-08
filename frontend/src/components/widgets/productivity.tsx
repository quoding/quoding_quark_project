/* QUARK — 생산성/정보 위젯: 일정·액션·습관·포모도로·D-Day·수분·시세 */
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';

interface ApiEvent {
  id: string;
  title: string;
  scheduled_at: string;
  end_at: string | null;
  all_day: boolean;
}

interface ApiTodo {
  id: number;
  text: string;
  done: boolean;
}

interface ApiHabit {
  id: number;
  name: string;
  streak: number;
  done_today: boolean;
}

/* ============ 오늘 일정 ============ */
export function ScheduleCard() {
  const todayStr = new Date().toISOString().slice(0, 10);
  const { data: events = [] } = useQuery<ApiEvent[]>({
    queryKey: ['events', todayStr],
    queryFn: () =>
      axios.get<ApiEvent[]>(`/api/agenda/events?date_filter=${todayStr}`).then((r) => r.data),
    refetchInterval: 30_000,
  });

  const now = new Date();
  return (
    <div className="card hov s5">
      <CardHead icon="calendar" title="오늘 일정" meta={events.length + '건'} />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {events.length === 0 && (
          <span style={{ fontSize: 12, color: 'var(--tx-mid)' }}>일정 없음</span>
        )}
        {events.map((ev) => {
          const t = ev.all_day ? '종일' : ev.scheduled_at.slice(11, 16);
          const color = ev.all_day ? 'var(--plant)' : 'var(--acc-bright)';
          const d = new Date(ev.scheduled_at);
          const soon = !ev.all_day && d.getTime() - now.getTime() < 30 * 60 * 1000 && d.getTime() > now.getTime();
          return (
            <div key={ev.id} className="sched-row">
              <span
                className="mono"
                style={{
                  fontSize: 12.5,
                  color: soon ? 'var(--acc-bright)' : 'var(--tx-mid)',
                  width: 46,
                  flex: 'none',
                  fontWeight: 600,
                }}
              >
                {t}
              </span>
              <span className="sched-line" style={{ background: color }} />
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
                {ev.title}
              </span>
              {soon && <span className="soon-tag">곧</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ============ 오늘 할일 — 습관 + 할일 통합 ============ */
export function TodayCard() {
  const qc = useQueryClient();

  const { data: habits = [] } = useQuery<ApiHabit[]>({
    queryKey: ['habits'],
    queryFn: () => axios.get<ApiHabit[]>('/api/habits').then((r) => r.data),
    refetchInterval: 30_000,
  });
  const { data: todos = [] } = useQuery<ApiTodo[]>({
    queryKey: ['todos'],
    queryFn: () => axios.get<ApiTodo[]>('/api/todos').then((r) => r.data),
    refetchInterval: 30_000,
  });

  const toggleHabit = useMutation({
    mutationFn: (id: number) =>
      axios.patch<ApiHabit>(`/api/habits/${id}/check`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['habits'] }),
  });
  const toggleTodo = useMutation({
    mutationFn: (id: number) => axios.patch<ApiTodo>(`/api/todos/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['todos'] }),
  });

  const totalDone = habits.filter((h) => h.done_today).length + todos.filter((t) => t.done).length;
  const total = habits.length + todos.length;
  const remaining = total - totalDone;

  return (
    <div className="card hov s4">
      <CardHead
        icon="zap"
        title="오늘 할일"
        meta={remaining > 0 ? `${remaining} 남음` : total > 0 ? '완료 ✓' : '없음'}
        metaAcc={total > 0 && remaining === 0}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {total === 0 && (
          <span style={{ fontSize: 12, color: 'var(--tx-mid)' }}>할 일 없음</span>
        )}

        {/* 습관 섹션 */}
        {habits.length > 0 && (
          <>
            <span style={{ fontSize: 10, color: 'var(--tx-faint)', letterSpacing: 1, textTransform: 'uppercase' as const, marginBottom: 2 }}>
              습관
            </span>
            {habits.map((h) => (
              <div key={`h-${h.id}`} className="between habit-row" onClick={() => toggleHabit.mutate(h.id)}>
                <div className="row" style={{ gap: 10, minWidth: 0 }}>
                  <span className={'cbox' + (h.done_today ? ' on' : '')}>{h.done_today && <Icon name="check" />}</span>
                  <span style={{
                    fontSize: 12.5,
                    color: h.done_today ? 'var(--tx-low)' : 'var(--tx)',
                    textDecoration: h.done_today ? 'line-through' : 'none',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {h.name}
                  </span>
                </div>
                {h.streak > 0 && (
                  <span className="streak" style={{ fontSize: 11 }}>
                    <Icon name="flame" fill /> {h.streak}
                  </span>
                )}
              </div>
            ))}
          </>
        )}

        {/* 할일 섹션 */}
        {todos.length > 0 && (
          <>
            <span style={{ fontSize: 10, color: 'var(--tx-faint)', letterSpacing: 1, textTransform: 'uppercase' as const, marginTop: habits.length > 0 ? 4 : 0, marginBottom: 2 }}>
              할일
            </span>
            {todos.map((todo) => (
              <div key={`t-${todo.id}`} className="row habit-row" style={{ gap: 10 }} onClick={() => toggleTodo.mutate(todo.id)}>
                <span className={'cbox' + (todo.done ? ' on' : '')}>{todo.done && <Icon name="check" />}</span>
                <span style={{
                  fontSize: 12.5,
                  color: todo.done ? 'var(--tx-low)' : 'var(--tx)',
                  textDecoration: todo.done ? 'line-through' : 'none',
                  lineHeight: 1.35,
                }}>
                  {todo.text}
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

/** @deprecated HabitsCard와 TodosCard는 TodayCard로 통합됨 */
export function HabitsCard() { return <TodayCard />; }
export function TodosCard() { return <TodayCard />; }

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

/* ============ D-Day — extra.tsx로 이동됨 ============ */
export { DdayCard } from '@/components/widgets/extra';

/* ============ 물 마시기 ============ */
interface WaterData { total_ml: number; goal_ml: number; pct: number; }

export function WaterCard() {
  const qc = useQueryClient();
  const { data } = useQuery<WaterData>({
    queryKey: ['water-today'],
    queryFn: () => axios.get<WaterData>('/api/water/today').then((r) => r.data),
    refetchInterval: 60_000,
  });
  const add = useMutation({
    mutationFn: () => axios.post<WaterData>('/api/water/today').then((r) => r.data),
    onSuccess: (updated) => qc.setQueryData(['water-today'], updated),
  });

  const ml = data?.total_ml ?? 0;
  const goal = data?.goal_ml ?? 2000;
  const pct = data?.pct ?? 0;

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
      <button className="pill acc" style={{ width: '100%', justifyContent: 'center' }} onClick={() => add.mutate()}>
        <Icon name="plus" /> 250ml 기록
      </button>
    </div>
  );
}

/* ============ 시세 — extra.tsx로 이동됨 ============ */
export { MarketCard } from '@/components/widgets/extra';
