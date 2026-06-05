/* QUARK — 집 제어 위젯 (대시보드·IoT 공용). 스토어를 직접 구독해 상태 공유. */
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { useHomeStore } from '@/stores/homeStore';
import { QDATA } from '@/data/quarkData';
import type { LightKey } from '@/types/quark';

/* ============ 씬 빠른 스트립 (대시보드) ============ */
export function ScenesBar() {
  const scene = useHomeStore((s) => s.scene);
  const applyScene = useHomeStore((s) => s.applyScene);
  return (
    <div className="card s12" style={{ padding: '15px 18px' }}>
      <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 10.5,
            letterSpacing: 1.2,
            color: 'var(--tx-faint)',
            textTransform: 'uppercase',
            marginRight: 4,
          }}
        >
          SCENE
        </span>
        {QDATA.scenes.map((s) => (
          <button
            key={s.id}
            className={'scene-btn' + (scene === s.id ? ' on' : '')}
            onClick={() => applyScene(s.id)}
          >
            <span className="ic">
              <Icon name={s.ico} />
            </span>
            <span>{s.name}</span>
            {scene === s.id && <span className="live">활성</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ============ 조명 빠른 제어 ============ */
const LIGHT_NAMES: Record<LightKey, string> = { living: '거실', bed: '침실', desk: '책상', kitchen: '주방' };
export function LightsCard() {
  const lights = useHomeStore((s) => s.lights);
  const toggleLight = useHomeStore((s) => s.toggleLight);
  const bright = useHomeStore((s) => s.bright);
  const setBright = useHomeStore((s) => s.setBright);
  const keys = Object.keys(lights) as LightKey[];
  const onCount = keys.filter((k) => lights[k]).length;
  return (
    <div className="card hov s4">
      <CardHead icon="bulb" title="조명" meta={onCount + '/' + keys.length + ' ON'} metaAcc={onCount > 0} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
        {keys.map((k) => (
          <div key={k} className="between">
            <span style={{ fontSize: 13, color: lights[k] ? 'var(--tx-hi)' : 'var(--tx-mid)' }}>
              {LIGHT_NAMES[k]}
            </span>
            <div className={'sw' + (lights[k] ? ' on' : '')} onClick={() => toggleLight(k)} />
          </div>
        ))}
      </div>
      <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--inset-line)' }}>
        <div className="between" style={{ marginBottom: 9 }}>
          <span style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>전체 밝기</span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--tx-hi)' }}>{bright}%</span>
        </div>
        <input
          className="slider"
          type="range"
          min="0"
          max="100"
          value={bright}
          onChange={(e) => setBright(+e.target.value)}
        />
      </div>
    </div>
  );
}

/* ============ LED 무드 컬러 ============ */
const LED_COLORS = ['#3d8bfd', '#6fd08c', '#f5b945', '#ff6b6b', '#b07bff', '#ff8cc8', '#ffffff'];
export function LedCard() {
  const color = useHomeStore((s) => s.ledColor);
  const on = useHomeStore((s) => s.ledOn);
  const onColor = useHomeStore((s) => s.setLedColor);
  const onToggle = useHomeStore((s) => s.toggleLed);
  return (
    <div className="card hov s4">
      <CardHead icon="palette" title="LED 무드등" meta={on ? '켜짐' : '꺼짐'} metaAcc={on} />
      <div
        style={{
          height: 88,
          borderRadius: 'var(--r-md)',
          marginBottom: 15,
          background: on
            ? `radial-gradient(120% 130% at 30% 10%, ${color}, ${color}22 70%, transparent), #0e0f13`
            : '#0e0f13',
          border: '1px solid var(--inset-line)',
          boxShadow: on ? `0 0 26px -6px ${color}` : 'none',
          transition: 'all .35s',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            right: 12,
            bottom: 10,
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: on ? '#fff' : 'var(--tx-faint)',
            opacity: on ? 0.85 : 1,
          }}
        >
          {on ? color.toUpperCase() : 'OFF'}
        </div>
      </div>
      <div className="between">
        <div className="row" style={{ gap: 8 }}>
          {LED_COLORS.map((c) => (
            <button
              key={c}
              onClick={() => onColor(c)}
              title={c}
              style={{
                width: 22,
                height: 22,
                borderRadius: '50%',
                background: c,
                cursor: 'pointer',
                border: color === c ? '2px solid #fff' : '2px solid transparent',
                boxShadow: color === c ? `0 0 0 2px ${c}, 0 0 10px ${c}` : 'none',
                outline: 'none',
                flex: 'none',
              }}
            />
          ))}
        </div>
        <div className={'sw' + (on ? ' on' : '')} onClick={onToggle} />
      </div>
    </div>
  );
}

/* ============ 냉방 + 식물 ============ */
export function ClimatePlantCard() {
  const ac = useHomeStore((s) => s.ac);
  const onAc = useHomeStore((s) => s.setAcField);
  const moisture = useHomeStore((s) => s.moisture);
  const onWater = useHomeStore((s) => s.waterPlant);
  const watering = useHomeStore((s) => s.watering);
  return (
    <div className="card hov s4">
      <CardHead icon="snow" title="냉방 · 식물" meta="LIVE" />
      {/* AC */}
      <div className="between" style={{ marginBottom: 14 }}>
        <div className="row" style={{ gap: 11 }}>
          <span
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              display: 'grid',
              placeItems: 'center',
              background: ac.on ? 'var(--acc-wash)' : 'rgba(255,255,255,0.04)',
              color: ac.on ? 'var(--acc-bright)' : 'var(--tx-mid)',
              transition: 'all .2s',
            }}
          >
            <Icon name="snow" />
          </span>
          <div>
            <div style={{ fontSize: 13, color: 'var(--tx-hi)' }}>에어컨</div>
            <div className="mono" style={{ fontSize: 11, color: 'var(--tx-mid)' }}>
              거실 · {ac.on ? '냉방' : '대기'}
            </div>
          </div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          {ac.on && (
            <div className="row" style={{ gap: 4 }}>
              <button className="step" onClick={() => onAc('temp', Math.max(18, ac.temp - 1))}>
                −
              </button>
              <span
                className="mono"
                style={{ fontSize: 15, fontWeight: 700, color: 'var(--tx-hi)', width: 38, textAlign: 'center' }}
              >
                {ac.temp}°
              </span>
              <button className="step" onClick={() => onAc('temp', Math.min(30, ac.temp + 1))}>
                +
              </button>
            </div>
          )}
          <div className={'sw' + (ac.on ? ' on' : '')} onClick={() => onAc('on', !ac.on)} />
        </div>
      </div>
      {/* Plant */}
      <div style={{ paddingTop: 14, borderTop: '1px solid var(--inset-line)' }}>
        <div className="between" style={{ marginBottom: 9 }}>
          <div className="row" style={{ gap: 8 }}>
            <span style={{ color: 'var(--plant)', width: 16, height: 16, display: 'grid', placeItems: 'center' }}>
              <Icon name="leaf" />
            </span>
            <span style={{ fontSize: 13, color: 'var(--tx-hi)' }}>몬스테라 · 토양 습도</span>
          </div>
          <span
            className="mono"
            style={{ fontSize: 12.5, color: moisture < 35 ? 'var(--warn)' : 'var(--plant)', fontWeight: 600 }}
          >
            {moisture}%
          </span>
        </div>
        <div className="bar plant" style={{ marginBottom: 11 }}>
          <i style={{ width: moisture + '%' }} />
        </div>
        <button
          className="pill"
          style={{ width: '100%', justifyContent: 'center' }}
          onClick={onWater}
          disabled={watering}
        >
          <Icon name="droplet" /> {watering ? '급수 중…' : '수동 급수'}
        </button>
      </div>
    </div>
  );
}
