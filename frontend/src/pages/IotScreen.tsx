/* QUARK — 집 제어 (IoT) 화면. 대시보드와 useHomeStore를 공유한다. */
import { useState } from 'react';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { LightsCard, LedCard, ClimatePlantCard } from '@/components/widgets/home';
import { useHomeStore } from '@/stores/homeStore';
import { QDATA } from '@/data/quarkData';

function SceneGrid() {
  const scene = useHomeStore((s) => s.scene);
  const applyScene = useHomeStore((s) => s.applyScene);
  return (
    <div className="card s12">
      <CardHead
        icon="zap"
        title="씬 프리셋"
        meta={'활성 · ' + (QDATA.scenes.find((s) => s.id === scene)?.name || '없음')}
        metaAcc
      />
      <div className="scene-grid">
        {QDATA.scenes.map((s) => (
          <button key={s.id} className={'scene-card' + (scene === s.id ? ' on' : '')} onClick={() => applyScene(s.id)}>
            <div className="sc-top">
              <span className="sc-ico">
                <Icon name={s.ico} />
              </span>
              {scene === s.id && <span className="sc-live">활성</span>}
            </div>
            <div className="sc-name">{s.name}</div>
            <div className="sc-desc">{s.desc}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function AppliancesCard() {
  const appliances = useHomeStore((s) => s.appliances);
  const onToggle = useHomeStore((s) => s.toggleAppliance);
  const onCount = appliances.filter((a) => a.on).length;
  return (
    <div className="card s6">
      <CardHead icon="home" title="가전 제어" meta={onCount + '/' + appliances.length + ' 작동'} metaAcc={onCount > 0} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {appliances.map((a) => (
          <div key={a.id} className="appl-row">
            <span className={'appl-ico' + (a.on ? ' on' : '')}>
              <Icon name={a.ico} />
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13.5, color: a.on ? 'var(--tx-hi)' : 'var(--tx-mid)' }}>{a.name}</div>
              <div
                className="mono"
                style={{
                  fontSize: 11,
                  color: 'var(--tx-mid)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {a.status}
              </div>
              {a.on && a.prog != null && (
                <div className="bar" style={{ marginTop: 6, height: 4 }}>
                  <i style={{ width: a.prog + '%' }} />
                </div>
              )}
            </div>
            <div className={'sw' + (a.on ? ' on' : '')} onClick={() => onToggle(a.id)} />
          </div>
        ))}
      </div>
    </div>
  );
}

function CameraCard() {
  const cameras = QDATA.cameras;
  const [sel, setSel] = useState(0);
  return (
    <div className="card s6">
      <CardHead
        icon="cam"
        title="카메라"
        meta={
          <span className="row" style={{ gap: 5 }}>
            <span className="sdot bad" style={{ animation: 'breathe 1.6s infinite' }} />
            REC
          </span>
        }
      />
      <div className="cam-main">
        <div className="cam-feed" style={{ '--tone': cameras[sel].tone + '%' } as React.CSSProperties}>
          <div className="cam-scan" />
          <div className="cam-lbl">
            <span className="sdot ok" /> {cameras[sel].name} · {cameras[sel].status}
          </div>
          <div className="cam-time mono">{new Date().toLocaleTimeString('ko-KR', { hour12: false })}</div>
          <div className="cam-ph mono">CAMERA FEED</div>
        </div>
      </div>
      <div className="cam-thumbs">
        {cameras.map((c, i) => (
          <button
            key={c.id}
            className={'cam-thumb' + (sel === i ? ' on' : '')}
            onClick={() => setSel(i)}
            style={{ '--tone': c.tone + '%' } as React.CSSProperties}
          >
            <span className="ct-lbl">{c.name}</span>
            <span className="sdot ok" />
          </button>
        ))}
      </div>
    </div>
  );
}

export default function IotScreen() {
  return (
    <div className="canvas scroll">
      <div className="grid">
        <SceneGrid />
        <LightsCard />
        <LedCard />
        <ClimatePlantCard />
        <AppliancesCard />
        <CameraCard />
      </div>
    </div>
  );
}
