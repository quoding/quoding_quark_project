/* QUARK — 자동화 화면 (요약 스트립 + IF→THEN 규칙 카드). useHomeStore.rules 공유. */
import { Icon } from '@/components/Icon';
import { useHomeStore } from '@/stores/homeStore';
import { fmt } from '@/data/quarkData';

export default function AutomationScreen() {
  const rules = useHomeStore((s) => s.rules);
  const toggleRule = useHomeStore((s) => s.toggleRule);
  const onCt = rules.filter((r) => r.on).length;
  const totalRuns = rules.reduce((a, r) => a + r.runs, 0);
  return (
    <div className="canvas scroll">
      <div className="grid">
        {/* summary strip */}
        <div className="card s12" style={{ padding: '18px 22px' }}>
          <div className="auto-summary">
            <div className="as-cell">
              <div className="big-num" style={{ fontSize: 26, color: 'var(--acc-bright)' }}>
                {onCt}
                <span style={{ fontSize: 13, color: 'var(--tx-mid)' }}>/{rules.length}</span>
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>활성 자동화</div>
            </div>
            <div className="as-div" />
            <div className="as-cell">
              <div className="big-num" style={{ fontSize: 26 }}>
                {fmt(totalRuns)}
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>누적 실행 횟수</div>
            </div>
            <div className="as-div" />
            <div className="as-cell">
              <div className="big-num" style={{ fontSize: 26 }}>
                ~2.4<span style={{ fontSize: 13, color: 'var(--tx-mid)' }}>h</span>
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>하루 절약 추정</div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <button className="pill acc">
                <Icon name="plus" /> 새 자동화
              </button>
            </div>
          </div>
        </div>

        {rules.map((r) => (
          <div key={r.id} className={'card hov s6 auto-rule' + (r.on ? ' on' : '')}>
            <div className="row between" style={{ alignItems: 'flex-start' }}>
              <div className="row" style={{ gap: 13, minWidth: 0 }}>
                <span className={'auto-ico' + (r.on ? ' on' : '')}>
                  <Icon name={r.ico} />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 14.5,
                      color: 'var(--tx-hi)',
                      fontWeight: 600,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {r.name}
                  </div>
                  <div className="mono" style={{ fontSize: 10.5, color: 'var(--tx-mid)', marginTop: 3 }}>
                    {fmt(r.runs)}회 실행됨
                  </div>
                </div>
              </div>
              <div className={'sw' + (r.on ? ' on' : '')} onClick={() => toggleRule(r.id)} />
            </div>
            <div className="auto-flow">
              <div className="af-node trigger">
                <span className="af-lbl">트리거 (IF)</span>
                <span className="af-txt">{r.trigger}</span>
              </div>
              <span className="af-arrow">
                <Icon name="chevron" />
              </span>
              <div className="af-node action">
                <span className="af-lbl">동작 (THEN)</span>
                <span className="af-txt">{r.action}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
