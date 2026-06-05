/* QUARK — 대시보드(홈) + 위젯 편집 시스템 (이 빌드의 핵심).
 * 편집모드 토글 → 핸들바 → HTML5 드래그 재배치 → 크기조절(sizes 순환) → 숨기기
 * → 추가 모달 → localStorage['quark-dash-v2'] 영속 → 새로고침 복원 → "기본값" 초기화. */
import { useState } from 'react';
import { Icon } from '@/components/Icon';
import { AddWidgetPanel } from '@/components/dashboard/AddWidgetPanel';
import { DASH_WIDGETS } from '@/components/widgets/registry';
import { DASH_DEFAULT, META_BY_ID } from '@/data/widgetMeta';
import type { DashConfig } from '@/types/quark';

const STORAGE_KEY = 'quark-dash-v2';

function loadConfig(): DashConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const saved = raw ? (JSON.parse(raw) as Partial<DashConfig>) : null;
    if (saved && Array.isArray(saved.active)) {
      const active = saved.active.filter((id) => META_BY_ID[id] && !META_BY_ID[id].locked);
      return { active, sizes: saved.sizes || {} };
    }
  } catch {
    /* ignore malformed storage */
  }
  return { active: DASH_DEFAULT.slice(), sizes: {} };
}

export default function Dashboard() {
  const [edit, setEdit] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [conf, setConf] = useState<DashConfig>(loadConfig);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  const save = (next: DashConfig): DashConfig => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    return next;
  };
  const spanOf = (id: string): number => conf.sizes[id] ?? META_BY_ID[id].sizes[0];

  const onDragStart = (e: React.DragEvent, id: string) => {
    setDragId(id);
    e.dataTransfer.effectAllowed = 'move';
    try {
      e.dataTransfer.setData('text/plain', id);
    } catch {
      /* some browsers throw on setData during start */
    }
  };
  const onDragEnter = (id: string) => {
    if (!dragId || dragId === id) {
      setOverId(id);
      return;
    }
    setOverId(id);
    setConf((prev) => {
      const from = prev.active.indexOf(dragId);
      const to = prev.active.indexOf(id);
      if (from < 0 || to < 0) return prev;
      const active = prev.active.slice();
      active.splice(from, 1);
      active.splice(to, 0, dragId);
      return { ...prev, active };
    });
  };
  const onDragEnd = () => {
    setConf((c) => save(c));
    setDragId(null);
    setOverId(null);
  };

  const addWidget = (id: string) => setConf((c) => save({ ...c, active: [...c.active, id] }));
  const hideWidget = (id: string) => setConf((c) => save({ ...c, active: c.active.filter((x) => x !== id) }));
  const cycleSize = (id: string) =>
    setConf((c) => {
      const opts = META_BY_ID[id].sizes;
      const cur = c.sizes[id] ?? opts[0];
      const next = opts[(opts.indexOf(cur) + 1) % opts.length];
      return save({ ...c, sizes: { ...c.sizes, [id]: next } });
    });
  const reset = () => setConf(save({ active: DASH_DEFAULT.slice(), sizes: {} }));

  return (
    <div className="canvas scroll">
      <div className="dash-bar">
        <div className="db-info">
          <span className="db-title">대시보드</span>
          {edit ? (
            <span className="db-hint">
              <span className="db-dot" />
              끌어서 이동 · 크기 조절 · 숨기기 — 자동 저장돼
            </span>
          ) : (
            <span className="db-sub">쿼크가 정리한 오늘의 한눈 보기 · 위젯 {conf.active.length}개</span>
          )}
        </div>
        <div className="row" style={{ gap: 9 }}>
          {edit && (
            <button className="pill" onClick={() => setShowAdd(true)}>
              <Icon name="plus" /> 위젯 추가
            </button>
          )}
          {edit && (
            <button className="pill" onClick={reset}>
              <Icon name="reset" /> 기본값
            </button>
          )}
          <button
            className={'pill' + (edit ? ' acc' : '')}
            onClick={() => {
              setEdit((v) => !v);
              setShowAdd(false);
            }}
          >
            <Icon name={edit ? 'check' : 'sliders'} /> {edit ? '편집 완료' : '위젯 편집'}
          </button>
        </div>
      </div>

      <div className={'grid' + (edit ? ' editing' : '')}>
        {conf.active.map((id) => {
          const node = DASH_WIDGETS[id];
          const meta = META_BY_ID[id];
          if (!node || !meta) return null;
          const span = spanOf(id);
          return (
            <div
              key={id}
              className={
                'dash-cell s' +
                span +
                (dragId === id ? ' dragging' : '') +
                (overId === id && dragId && dragId !== id ? ' over' : '')
              }
              draggable={edit}
              onDragStart={(e) => onDragStart(e, id)}
              onDragEnter={() => onDragEnter(id)}
              onDragOver={(e) => {
                if (edit) e.preventDefault();
              }}
              onDragEnd={onDragEnd}
              onDrop={(e) => {
                if (edit) e.preventDefault();
              }}
            >
              {edit && (
                <div className="dash-handle">
                  <span className="dh-grip">
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                  </span>
                  <span className="dh-name">{meta.title}</span>
                  <div className="dh-tools">
                    {meta.sizes.length > 1 && (
                      <button
                        className="dh-btn"
                        title="크기 조절"
                        onClick={(e) => {
                          e.stopPropagation();
                          cycleSize(id);
                        }}
                      >
                        <Icon name="expand" />
                      </button>
                    )}
                    <button
                      className="dh-btn del"
                      title="숨기기"
                      onClick={(e) => {
                        e.stopPropagation();
                        hideWidget(id);
                      }}
                    >
                      <Icon name="close" />
                    </button>
                  </div>
                </div>
              )}
              <div className={'dash-inner' + (edit ? ' locked' : '')}>{node}</div>
            </div>
          );
        })}
        {edit && (
          <button className="dash-cell s4 add-tile" onClick={() => setShowAdd(true)}>
            <span className="at-plus">
              <Icon name="plus" />
            </span>
            <span>위젯 추가</span>
          </button>
        )}
      </div>

      {showAdd && (
        <AddWidgetPanel activeIds={conf.active} onAdd={addWidget} onClose={() => setShowAdd(false)} />
      )}
    </div>
  );
}
