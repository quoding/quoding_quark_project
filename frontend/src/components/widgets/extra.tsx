/* QUARK — 추가 위젯 8종: 날씨예보·일출일몰·세계시계·뉴스·대중교통·기분·수면·카페인 */
import { useEffect, useState } from 'react';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { QDATA } from '@/data/quarkData';

/* ---- 날씨 주간 예보 ---- */
export function WeatherCard() {
  const w = QDATA.weather;
  const f = QDATA.forecast;
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="cloud" title="날씨 예보" meta={w.city} />
      <div className="row" style={{ gap: 16, marginBottom: 16, alignItems: 'flex-start' }}>
        <div style={{ color: 'var(--warn)', width: 44, height: 44, display: 'grid', placeItems: 'center', flex: 'none' }}>
          <Icon name="sun" />
        </div>
        <div>
          <div className="big-num" style={{ fontSize: 34, lineHeight: 1 }}>
            {w.temp}°
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--tx-mid)', marginTop: 3 }}>
            {w.label} · 최고 {w.hi}° 최저 {w.lo}°
          </div>
        </div>
      </div>
      <div className="fc-row">
        {f.map((d, i) => (
          <div key={i} className={'fc-cell' + (i === 0 ? ' on' : '')}>
            <span className="fc-day">{d.d}</span>
            <span
              className="fc-ico"
              style={{ color: d.ico === 'sun' ? 'var(--warn)' : d.ico === 'rain' ? 'var(--acc-bright)' : 'var(--tx-mid)' }}
            >
              <Icon name={d.ico} />
            </span>
            <span className="mono fc-pop">{d.pop}%</span>
            <span className="mono fc-hi">{d.hi}°</span>
            <span className="mono fc-lo">{d.lo}°</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- 일출·일몰 + 추천 ---- */
export function SunCard() {
  const s = QDATA.sun;
  const now = new Date();
  const toMin = (t: string) => {
    const [h, m] = t.split(':').map(Number);
    return h * 60 + m;
  };
  const cur = now.getHours() * 60 + now.getMinutes();
  const rise = toMin(s.rise);
  const set = toMin(s.set);
  const pct = Math.max(0, Math.min(100, ((cur - rise) / (set - rise)) * 100));
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="sun" title="일출·일몰" meta={s.dayLen} />
      <div className="sun-arc">
        <svg viewBox="0 0 200 80" preserveAspectRatio="none" style={{ width: '100%', height: 64 }}>
          <path d="M6 76 A 94 94 0 0 1 194 76" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2" strokeDasharray="3 4" />
          <path
            d="M6 76 A 94 94 0 0 1 194 76"
            fill="none"
            stroke="var(--warn)"
            strokeWidth="2.5"
            strokeDasharray="296"
            strokeDashoffset={296 - (296 * pct) / 100}
            style={{ transition: 'stroke-dashoffset 1s', filter: 'drop-shadow(0 0 4px var(--warn))' }}
          />
          <circle
            cx={6 + (188 * pct) / 100}
            cy={76 - Math.sin((Math.PI * pct) / 100) * 70}
            r="5"
            fill="var(--warn)"
            style={{ filter: 'drop-shadow(0 0 6px var(--warn))' }}
          />
        </svg>
      </div>
      <div className="between" style={{ marginTop: 6 }}>
        <div>
          <div className="mono" style={{ fontSize: 14, color: 'var(--tx-hi)', fontWeight: 600 }}>
            {s.rise}
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--tx-mid)' }}>일출</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: 14, color: 'var(--tx-hi)', fontWeight: 600 }}>
            {s.set}
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--tx-mid)' }}>일몰</div>
        </div>
      </div>
      <div className="row" style={{ gap: 7, marginTop: 13, flexWrap: 'wrap' }}>
        <span className={'reco' + (s.umbrella ? ' on' : '')}>
          <Icon name="droplet" /> {s.umbrella ? '우산 챙겨' : '우산 필요 없어'}
        </span>
        <span className={'reco' + (s.laundry ? ' on' : '')}>
          <Icon name="wash" /> {s.laundry ? '빨래하기 좋아' : '빨래는 미뤄'}
        </span>
      </div>
    </div>
  );
}

/* ---- 세계 시계 ---- */
export function WorldClockCard() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const fmtTz = (tz: number) => {
    const utc = now.getTime() + now.getTimezoneOffset() * 60000;
    const d = new Date(utc + tz * 3600000);
    const pad = (n: number) => String(n).padStart(2, '0');
    return { time: pad(d.getHours()) + ':' + pad(d.getMinutes()), h: d.getHours() };
  };
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="globe" title="세계 시계" meta="LIVE" />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {QDATA.clocks.map((c, i) => {
          const t = fmtTz(c.tz);
          const night = t.h < 6 || t.h >= 19;
          return (
            <div key={i} className="wc-row">
              <span className="wc-flag">{c.flag}</span>
              <span style={{ fontSize: 13, color: 'var(--tx-hi)', flex: 1 }}>{c.city}</span>
              <span
                style={{
                  color: night ? 'var(--tx-mid)' : 'var(--warn)',
                  width: 14,
                  height: 14,
                  display: 'grid',
                  placeItems: 'center',
                }}
              >
                <Icon name={night ? 'moon' : 'sun'} />
              </span>
              <span className="mono" style={{ fontSize: 15, color: 'var(--tx-hi)', fontWeight: 600, width: 54, textAlign: 'right' }}>
                {t.time}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- 뉴스 피드 ---- */
export function NewsCard() {
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="news" title="관심 뉴스" meta={QDATA.news.length + '건'} />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {QDATA.news.map((n, i) => (
          <div key={i} className="news-row">
            <span className="news-tag">{n.tag}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, color: 'var(--tx-hi)', lineHeight: 1.4, marginBottom: 3 }}>{n.title}</div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--tx-mid)' }}>
                {n.src} · {n.time}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- 대중교통 ---- */
export function TransitCard() {
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="bus" title="대중교통" meta="실시간" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {QDATA.transit.map((t, i) => (
          <div key={i} className="tr-row">
            <span
              className="tr-line"
              style={{
                background: `color-mix(in srgb, ${t.color} 18%, transparent)`,
                color: t.color,
                borderColor: `color-mix(in srgb, ${t.color} 40%, transparent)`,
              }}
            >
              <Icon name={t.kind === 'subway' ? 'subway' : 'bus'} />
              {t.line}
            </span>
            <span
              style={{
                fontSize: 12,
                color: 'var(--tx-mid)',
                flex: 1,
                minWidth: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {t.dest}
            </span>
            <div style={{ textAlign: 'right', flex: 'none' }}>
              <div className="mono" style={{ fontSize: 15, fontWeight: 700, color: t.eta <= 3 ? 'var(--acc-bright)' : 'var(--tx-hi)' }}>
                {t.eta}
                <span style={{ fontSize: 10, color: 'var(--tx-mid)' }}>분</span>
              </div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--tx-low)' }}>
                다음 {t.next}분
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- 기분 로그 ---- */
const MOODS = ['😎', '🙂', '😐', '😤', '😴', '😞'];
export function MoodCard() {
  const [week, setWeek] = useState(QDATA.moodSeed.map((m) => ({ ...m })));
  const [pick, setPick] = useState(false);
  const todayIdx = week.length - 1;
  const setToday = (emo: string) => {
    setWeek((w) => w.map((d, i) => (i === todayIdx ? { ...d, emo } : d)));
    setPick(false);
  };
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="smile" title="기분 로그" meta="이번 주" />
      <div className="mood-week">
        {week.map((d, i) => (
          <div key={i} className={'mood-cell' + (i === todayIdx ? ' today' : '')}>
            <span className="mood-emo">{d.emo || '·'}</span>
            <span className="mood-day">{d.day}</span>
          </div>
        ))}
      </div>
      {pick ? (
        <div className="mood-picker">
          {MOODS.map((e) => (
            <button key={e} className="mood-opt" onClick={() => setToday(e)}>
              {e}
            </button>
          ))}
        </div>
      ) : (
        <button
          className="pill"
          style={{ width: '100%', justifyContent: 'center', marginTop: 12 }}
          onClick={() => setPick(true)}
        >
          오늘 기분 {week[todayIdx].emo ? '바꾸기' : '기록하기'}
        </button>
      )}
    </div>
  );
}

/* ---- 수면 기록 ---- */
export function SleepCard() {
  const s = QDATA.sleepSeed;
  const max = 9;
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="bed" title="수면 기록" meta={'목표 ' + s.goal + 'h'} />
      <div className="row" style={{ gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
        <div className="big-num" style={{ fontSize: 30, lineHeight: 1 }}>
          {s.lastH}
          <span style={{ fontSize: 14, color: 'var(--tx-mid)' }}>h</span> {s.lastM}
          <span style={{ fontSize: 14, color: 'var(--tx-mid)' }}>m</span>
        </div>
        <span style={{ fontSize: 11, color: s.lastH < s.goal ? 'var(--warn)' : 'var(--ok)', paddingBottom: 4 }}>
          {s.lastH < s.goal ? '조금 부족했어' : '충분히 잤어'}
        </span>
      </div>
      <div className="sleep-bars">
        {s.week.map((h, i) => (
          <div key={i} className="sb-col">
            <div className="sb-track">
              <i
                style={{
                  height: (h / max) * 100 + '%',
                  background:
                    h >= s.goal
                      ? 'linear-gradient(180deg,var(--plant),#3f8a5a)'
                      : 'linear-gradient(180deg,var(--acc-bright),var(--acc-dim))',
                }}
              />
            </div>
            <span className="mono sb-lbl">{h}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- 카페인 컷오프 ---- */
export function CaffeineCard() {
  const c = QDATA.caffeine;
  const now = new Date();
  const toMin = (t: string) => {
    const [h, m] = t.split(':').map(Number);
    return h * 60 + m;
  };
  const cutoff = toMin(c.cutoff);
  const cur = now.getHours() * 60 + now.getMinutes();
  const left = cutoff - cur;
  const past = left <= 0;
  const txt = past ? '컷오프 지남' : `${Math.floor(left / 60)}시간 ${left % 60}분 남음`;
  return (
    <div className="card hov" style={{ height: '100%' }}>
      <CardHead icon="coffee" title="카페인 컷오프" meta={'오늘 ' + c.cupsToday + '잔'} />
      <div style={{ display: 'grid', placeItems: 'center', textAlign: 'center', padding: '6px 0 12px' }}>
        <div style={{ color: past ? 'var(--bad)' : 'var(--warn)', width: 34, height: 34, marginBottom: 8 }}>
          <Icon name="coffee" />
        </div>
        <div className="big-num" style={{ fontSize: 19, color: past ? 'var(--bad)' : 'var(--tx-hi)' }}>
          {txt}
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--tx-mid)', marginTop: 4 }}>
          컷오프 {c.cutoff} · 취침 {c.bedtime} 기준
        </div>
      </div>
      <div className="caf-note">
        {past ? '이제 마시면 잠 못 자 — 디카페인 권장 ☕' : '아직 괜찮아. ' + c.cutoff + ' 전까진 OK'}
      </div>
    </div>
  );
}
