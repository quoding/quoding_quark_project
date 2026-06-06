/* QUARK — 자동화 화면 (DB 연결, IF→THEN 규칙 카드). */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Icon } from '@/components/Icon';
import type { IconName } from '@/components/Icon';

interface Automation {
  id: number;
  name: string;
  trigger_desc: string;
  action_desc: string;
  icon: string;
  enabled: boolean;
  run_count: number;
}

function fmt(n: number): string {
  return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
}

export default function AutomationScreen() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ name: '', trigger_desc: '', action_desc: '', icon: 'zap' });

  const { data: rules = [] } = useQuery<Automation[]>({
    queryKey: ['automations'],
    queryFn: () => axios.get<Automation[]>('/api/automations').then((r) => r.data),
  });

  const toggle = useMutation({
    mutationFn: (id: number) =>
      axios.patch<Automation>(`/api/automations/${id}/toggle`).then((r) => r.data),
    onSuccess: (updated) =>
      qc.setQueryData<Automation[]>(['automations'], (prev = []) =>
        prev.map((r) => (r.id === updated.id ? updated : r)),
      ),
  });

  const remove = useMutation({
    mutationFn: (id: number) => axios.delete(`/api/automations/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['automations'] }),
  });

  const create = useMutation({
    mutationFn: (body: typeof form) => axios.post<Automation>('/api/automations', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automations'] });
      setShowNew(false);
      setForm({ name: '', trigger_desc: '', action_desc: '', icon: 'zap' });
    },
  });

  const onCt = rules.filter((r) => r.enabled).length;
  const totalRuns = rules.reduce((a, r) => a + r.run_count, 0);

  return (
    <div className="canvas scroll">
      <div className="grid">
        {/* summary strip */}
        <div className="card s12" style={{ padding: '18px 22px' }}>
          <div className="auto-summary">
            <div className="as-cell">
              <div className="big-num" style={{ fontSize: 26, color: 'var(--acc-bright)' }}>
                {onCt}<span style={{ fontSize: 13, color: 'var(--tx-mid)' }}>/{rules.length}</span>
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>활성 자동화</div>
            </div>
            <div className="as-div" />
            <div className="as-cell">
              <div className="big-num" style={{ fontSize: 26 }}>{fmt(totalRuns)}</div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>누적 실행 횟수</div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <button className="pill acc" onClick={() => setShowNew((v) => !v)}>
                <Icon name="plus" /> 새 자동화
              </button>
            </div>
          </div>
        </div>

        {/* new automation form */}
        {showNew && (
          <div className="card s12" style={{ padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--tx-hi)' }}>새 자동화 규칙</div>
            {(['name', 'trigger_desc', 'action_desc'] as const).map((k) => (
              <input
                key={k}
                className="memo-area"
                style={{ height: 36, padding: '0 12px', borderRadius: 8 }}
                placeholder={{ name: '규칙 이름', trigger_desc: '트리거 (IF)', action_desc: '동작 (THEN)' }[k]}
                value={form[k]}
                onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
              />
            ))}
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="pill acc"
                onClick={() => create.mutate(form)}
                disabled={!form.name || !form.trigger_desc || !form.action_desc}
              >
                저장
              </button>
              <button className="pill" onClick={() => setShowNew(false)}>취소</button>
            </div>
          </div>
        )}

        {rules.map((r) => (
          <div key={r.id} className={'card hov s6 auto-rule' + (r.enabled ? ' on' : '')}>
            <div className="row between" style={{ alignItems: 'flex-start' }}>
              <div className="row" style={{ gap: 13, minWidth: 0 }}>
                <span className={'auto-ico' + (r.enabled ? ' on' : '')}>
                  <Icon name={r.icon as IconName} />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 14.5, color: 'var(--tx-hi)', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {r.name}
                  </div>
                  <div className="mono" style={{ fontSize: 10.5, color: 'var(--tx-mid)', marginTop: 3 }}>
                    {fmt(r.run_count)}회 실행됨
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                <button
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--tx-faint)', padding: 4 }}
                  onClick={() => remove.mutate(r.id)}
                  title="삭제"
                >
                  <Icon name="close" />
                </button>
                <div className={'sw' + (r.enabled ? ' on' : '')} onClick={() => toggle.mutate(r.id)} />
              </div>
            </div>
            <div className="auto-flow">
              <div className="af-node trigger">
                <span className="af-lbl">트리거 (IF)</span>
                <span className="af-txt">{r.trigger_desc}</span>
              </div>
              <span className="af-arrow"><Icon name="chevron" /></span>
              <div className="af-node action">
                <span className="af-lbl">동작 (THEN)</span>
                <span className="af-txt">{r.action_desc}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
