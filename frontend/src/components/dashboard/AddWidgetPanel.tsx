/* QUARK — 위젯 추가 모달 (5탭 카테고리 / 추가됨·잠금 상태) */
import { useState } from 'react';
import { Icon } from '@/components/Icon';
import { WIDGET_CATS, WIDGET_META } from '@/data/widgetMeta';

interface AddWidgetPanelProps {
  activeIds: string[];
  onAdd: (id: string) => void;
  onClose: () => void;
}

export function AddWidgetPanel({ activeIds, onAdd, onClose }: AddWidgetPanelProps) {
  const [cat, setCat] = useState(WIDGET_CATS[0]);
  const list = WIDGET_META.filter((w) => w.cat === cat);
  return (
    <div className="addw-overlay" onClick={onClose}>
      <div className="addw-panel" onClick={(e) => e.stopPropagation()}>
        <div className="addw-head">
          <div>
            <div className="addw-title">위젯 추가</div>
            <div className="addw-sub">대시보드에 올릴 위젯을 골라봐 · 잠긴 건 곧 만들 기능이야</div>
          </div>
          <button className="addw-x" onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>
        <div className="addw-cats">
          {WIDGET_CATS.map((c) => (
            <button key={c} className={'addw-cat' + (cat === c ? ' on' : '')} onClick={() => setCat(c)}>
              {c}
            </button>
          ))}
        </div>
        <div className="addw-grid scroll">
          {list.map((w) => {
            const added = activeIds.includes(w.id);
            return (
              <button
                key={w.id}
                className={'addw-item' + (w.locked ? ' locked' : '') + (added ? ' added' : '')}
                disabled={w.locked || added}
                onClick={() => {
                  if (!w.locked && !added) onAdd(w.id);
                }}
              >
                <span className="addw-ico">
                  <Icon name={w.locked ? 'lock' : w.ico} />
                </span>
                <span className="addw-name">{w.title}</span>
                <span className="addw-state">
                  {w.locked ? (
                    '준비 중'
                  ) : added ? (
                    '추가됨'
                  ) : (
                    <span className="addw-plus">
                      <Icon name="plus" /> 추가
                    </span>
                  )}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
