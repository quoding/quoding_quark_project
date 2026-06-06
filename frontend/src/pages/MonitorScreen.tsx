/* QUARK — 모니터링 & 시스템 화면 (서버 게이지·서비스·GitHub·Docker·API 비용) */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { CardHead, Gauge } from '@/components/common';
import { QDATA, fmt } from '@/data/quarkData';
import type { ServiceStatus } from '@/types/quark';

interface SystemStats {
  cpu: number;
  ram: number;
  disk: number;
  temp: number | null;
  uptime_days: number;
}

interface DockerContainer {
  name: string;
  img: string;
  status: string;
  cpu: number;
  mem: number;
}

interface ServiceEntry {
  name: string;
  status: ServiceStatus;
  latency: number | null;
}

interface GithubData {
  streak: number;
  today: number;
  week: number;
  lastCommit: string;
  error?: string;
}

interface OpenAIModel {
  name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface OpenAIUsage {
  date: string;
  models: OpenAIModel[];
  error?: string;
}

function ServerCard() {
  const s = QDATA.server;

  const { data: stats } = useQuery<SystemStats>({
    queryKey: ['system'],
    queryFn: () => axios.get<SystemStats>('/api/system/stats').then((r) => r.data),
    refetchInterval: 60_000,
    retry: 1,
  });

  const cpu = stats?.cpu ?? s.cpu;
  const ram = stats?.ram ?? s.ram;
  const disk = stats?.disk ?? s.disk;
  const temp = stats?.temp ?? s.temp;
  const uptimeDays = stats?.uptime_days ?? s.uptimeDays;

  return (
    <div className="card s6">
      <CardHead icon="cpu" title="미니PC 서버" meta={'UP ' + uptimeDays + 'd'} metaAcc />
      <div className="srv-grid">
        <Gauge value={cpu} label="CPU" unit="%" />
        <Gauge value={ram} label="RAM" unit="%" />
        <Gauge value={temp ?? 0} label="온도" unit="°" kind={(temp ?? 0) > 65 ? 'bad' : (temp ?? 0) > 55 ? 'warn' : 'ok'} />
        <Gauge value={disk} label="디스크" unit="%" />
      </div>
    </div>
  );
}

function ServicesCard() {
  const LBL: Record<ServiceStatus, string> = { up: '정상', warn: '지연', down: '다운' };

  const { data: services } = useQuery<ServiceEntry[]>({
    queryKey: ['services'],
    queryFn: () => axios.get<ServiceEntry[]>('/api/system/services').then((r) => r.data),
    refetchInterval: 10_000,
    retry: 1,
  });

  const list = services ?? QDATA.services;
  const upCount = list.filter((s) => s.status === 'up').length;

  return (
    <div className="card s6">
      <CardHead
        icon="zap"
        title="서비스 상태"
        meta={upCount + '/' + list.length + ' UP'}
      />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {list.map((s, i) => (
          <div key={i} className="svc-row">
            <span className={'sdot ' + (s.status === 'up' ? 'ok' : s.status === 'warn' ? 'warn' : 'bad')} />
            <span
              style={{
                fontSize: 13,
                color: s.status === 'down' ? 'var(--tx-mid)' : 'var(--tx-hi)',
                flex: 1,
                minWidth: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {s.name}
            </span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--tx-mid)', flex: 'none' }}>
              {s.latency ? s.latency + 'ms' : '—'}
            </span>
            <span className={'svc-tag ' + s.status}>{LBL[s.status]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function GithubCard() {
  const g = QDATA.github;
  const weeks = 18;

  const { data: gh } = useQuery<GithubData>({
    queryKey: ['github'],
    queryFn: () => axios.get<GithubData>('/api/system/github').then((r) => r.data),
    refetchInterval: 3_600_000,
    retry: 1,
  });

  const streak = gh?.error ? g.streak : (gh?.streak ?? g.streak);
  const today = gh?.error ? g.today : (gh?.today ?? g.today);
  const week = gh?.error ? g.week : (gh?.week ?? g.week);
  const lastCommit = gh?.error ? g.lastCommit : (gh?.lastCommit ?? g.lastCommit);

  const grid = useMemo(() => {
    const out: number[][] = [];
    for (let w = 0; w < weeks; w++) {
      const col: number[] = [];
      for (let d = 0; d < 7; d++) {
        const r = Math.random();
        let lvl = r > 0.82 ? 4 : r > 0.62 ? 3 : r > 0.42 ? 2 : r > 0.22 ? 1 : 0;
        if (w > weeks - 4 && Math.random() > 0.4) lvl = Math.max(lvl, 2);
        col.push(lvl);
      }
      out.push(col);
    }
    return out;
  }, []);

  const COLORS = [
    'rgba(255,255,255,0.06)',
    'var(--acc-dim)',
    'color-mix(in srgb, var(--acc) 70%, transparent)',
    'var(--acc)',
    'var(--acc-bright)',
  ];
  return (
    <div className="card s8">
      <CardHead icon="github" title="GitHub 활동" meta={'마지막 커밋 ' + lastCommit} />
      <div className="row" style={{ gap: 22, marginBottom: 16 }}>
        <div>
          <div className="big-num" style={{ fontSize: 24 }}>
            {streak}
            <span style={{ fontSize: 12, color: 'var(--tx-mid)', marginLeft: 3 }}>일</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--tx-mid)' }}>연속 커밋 🔥</div>
        </div>
        <div>
          <div className="big-num" style={{ fontSize: 24, color: 'var(--acc-bright)' }}>
            {today}
          </div>
          <div style={{ fontSize: 11, color: 'var(--tx-mid)' }}>오늘 커밋</div>
        </div>
        <div>
          <div className="big-num" style={{ fontSize: 24 }}>
            {week}
          </div>
          <div style={{ fontSize: 11, color: 'var(--tx-mid)' }}>이번 주</div>
        </div>
      </div>
      <div className="gh-grid">
        {grid.map((col, w) => (
          <div key={w} className="gh-col">
            {col.map((lvl, d) => (
              <i key={d} title={lvl + ' commits'} style={{ background: COLORS[lvl] }} />
            ))}
          </div>
        ))}
      </div>
      <div className="row" style={{ gap: 6, marginTop: 12, justifyContent: 'flex-end', fontSize: 10, color: 'var(--tx-mid)' }}>
        적음{' '}
        {COLORS.map((c, i) => (
          <span key={i} className="gh-leg" style={{ background: c }} />
        ))}{' '}
        많음
      </div>
    </div>
  );
}

function DockerCard() {
  const { data: containers } = useQuery<DockerContainer[]>({
    queryKey: ['docker'],
    queryFn: () => axios.get<DockerContainer[]>('/api/system/docker').then((r) => r.data),
    refetchInterval: 60_000,
    retry: 1,
  });

  const list = containers ?? QDATA.docker;
  const runningCount = list.filter((d) => d.status === 'running').length;

  return (
    <div className="card s4">
      <CardHead icon="automation" title="Docker" meta={runningCount + ' running'} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {list.map((d, i) => (
          <div key={i} className="dk-row">
            <span
              className={'sdot ' + (d.status === 'running' ? 'ok' : 'bad')}
              style={d.status === 'running' ? { animation: 'breathe 2.4s infinite' } : {}}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 12.5,
                  color: d.status === 'running' ? 'var(--tx-hi)' : 'var(--tx-mid)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {d.name}
              </div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--tx-low)' }}>
                {d.img}
              </div>
            </div>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--tx-mid)', textAlign: 'right', flex: 'none' }}>
              {d.status === 'running' ? (
                <>
                  {d.cpu}% · {d.mem}MB
                </>
              ) : (
                'stopped'
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApiCard() {
  const a = QDATA.api;

  const { data: usage } = useQuery<OpenAIUsage>({
    queryKey: ['openai-usage'],
    queryFn: () => axios.get<OpenAIUsage>('/api/system/openai-usage').then((r) => r.data),
    refetchInterval: 3_600_000,
    retry: 1,
  });

  const hasData = usage && !usage.error && usage.models?.length > 0;
  const totalTokens = hasData ? usage.models.reduce((s, m) => s + m.total_tokens, 0) : 0;
  const pct = a.monthCost ? Math.round((a.monthCost / a.budget) * 100) : 0;

  return (
    <div className="card s12">
      <CardHead
        icon="coin"
        title="API 비용 · 토큰 사용량"
        meta={hasData ? `오늘 ${fmt(totalTokens)} tokens` : '이번 달 ₩' + fmt(a.monthCost) + ' / ₩' + fmt(a.budget)}
        metaAcc={pct < 80}
      />
      {!hasData ? (
        <>
          <div className="between" style={{ marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--tx-mid)' }}>예산 사용률</span>
            <span className="mono" style={{ fontSize: 13, color: pct > 80 ? 'var(--warn)' : 'var(--acc-bright)', fontWeight: 600 }}>
              {pct}%
            </span>
          </div>
          <div className={'bar ' + (pct > 80 ? 'warn' : '')} style={{ marginBottom: 18 }}>
            <i style={{ width: pct + '%' }} />
          </div>
          <div className="api-grid">
            {a.items.map((it, i) => (
              <div key={i} className="api-item">
                <div className="between" style={{ marginBottom: 7 }}>
                  <span style={{ fontSize: 12.5, color: 'var(--tx-hi)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {it.name}
                  </span>
                </div>
                <div className="big-num" style={{ fontSize: 18 }}>₩{fmt(it.cost)}</div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--tx-mid)', margin: '3px 0 8px' }}>
                  {it.tokens !== '—' ? it.tokens + ' tokens' : '사용량 기준'}
                </div>
                <div className="bar" style={{ height: 4 }}>
                  <i style={{ width: it.pct + '%' }} />
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="api-grid">
          {usage.models.map((m, i) => {
            const pctModel = Math.round((m.total_tokens / totalTokens) * 100);
            return (
              <div key={i} className="api-item">
                <div className="between" style={{ marginBottom: 7 }}>
                  <span style={{ fontSize: 12.5, color: 'var(--tx-hi)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {m.name}
                  </span>
                </div>
                <div className="big-num" style={{ fontSize: 18 }}>{fmt(m.total_tokens)}</div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--tx-mid)', margin: '3px 0 8px' }}>
                  in {fmt(m.prompt_tokens)} · out {fmt(m.completion_tokens)}
                </div>
                <div className="bar" style={{ height: 4 }}>
                  <i style={{ width: pctModel + '%' }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function MonitorScreen() {
  return (
    <div className="canvas scroll">
      <div className="grid">
        <ServerCard />
        <ServicesCard />
        <GithubCard />
        <DockerCard />
        <ApiCard />
      </div>
    </div>
  );
}
