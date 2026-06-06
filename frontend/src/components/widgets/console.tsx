/* QUARK — 비서 콘솔 + 빠른 메모.
 * 응답은 hooks/useQuarkChat.ts(백엔드 SSE)로 실시간 스트리밍한다.
 * onCommand(homeStore)는 IoT 화면의 낙관적 UI 동기화를 위해 유지. */
import { useEffect, useRef, useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { useHomeStore } from '@/stores/homeStore';
import { useQuarkChat } from '@/hooks/useQuarkChat';
import mascot from '@/assets/quark-mascot.png';

const QC_SUGGEST = ['쿼크, 불 꺼줘', '쿼크, 오늘 일정 어때', '쿼크, 아이디어 있어', '쿼크, 물 마실 시간이야?'];
const GREETING = '안녕 쿼딩! 뭐든 물어봐 — 집 기기 제어도 되고, 그냥 궁금한 것도 좋아 🦫';

function Avatar() {
  return (
    <div className="qc-ava">
      <img className="pixelated" src={mascot} alt="쿼크" />
    </div>
  );
}

export function QuarkConsole() {
  const onCommand = useHomeStore((s) => s.handleCommand);
  const { messages, streaming, error, send: sendChat } = useQuarkChat();
  const [val, setVal] = useState('');
  const streamRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight;
  }, [messages, streaming]);

  const send = (text?: string) => {
    const t = (text || val).trim();
    if (!t || streaming) return;
    setVal('');
    onCommand(t); // 낙관적 IoT UI 동기화 (실제 제어는 백엔드 에이전트가 MQTT로 수행)
    void sendChat(t);
  };

  // 스트림 시작 직후의 빈 assistant 말풍선은 타이핑 인디케이터로 대체
  const visible = messages.filter((m) => !(m.role === 'assistant' && m.content === ''));
  const awaitingFirstToken =
    streaming &&
    messages.length > 0 &&
    messages[messages.length - 1].role === 'assistant' &&
    messages[messages.length - 1].content === '';

  return (
    <div className="card s8" style={{ minHeight: 340 }}>
      <CardHead
        icon="mic"
        title="쿼크에게 말하기"
        meta={streaming ? 'QUARK · 생각 중…' : 'QUARK · 대기 중'}
        metaAcc
      />
      <div className="qc-stream scroll" ref={streamRef}>
        <div className="qc-msg q">
          <Avatar />
          <div className="qc-bub">
            <div className="qc-who">쿼크 · QUARK</div>
            {GREETING}
          </div>
        </div>
        {visible.map((m) => (
          <div key={m.id} className={'qc-msg ' + (m.role === 'user' ? 'me' : 'q')}>
            {m.role === 'assistant' && <Avatar />}
            <div className="qc-bub">
              {m.role === 'assistant' && <div className="qc-who">쿼크 · QUARK</div>}
              {m.content}
            </div>
          </div>
        ))}
        {awaitingFirstToken && (
          <div className="qc-msg q">
            <Avatar />
            <div className="qc-bub">
              <span className="qc-typing">
                <i />
                <i />
                <i />
              </span>
            </div>
          </div>
        )}
        {error && (
          <div className="qc-msg q">
            <Avatar />
            <div className="qc-bub">
              <div className="qc-who">쿼크 · QUARK</div>⚠️ 연결 오류: {error}
            </div>
          </div>
        )}
      </div>
      <div className="qc-suggest">
        {QC_SUGGEST.map((s) => (
          <button key={s} className="qc-chip" onClick={() => send(s)} disabled={streaming}>
            {s}
          </button>
        ))}
      </div>
      <div className="qc-input">
        <input
          value={val}
          placeholder="쿼크에게 말하기…"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') send();
          }}
        />
        <span className="mic">
          <Icon name="mic" />
        </span>
        <button className="qc-send" onClick={() => send()}>
          <Icon name="send" fill />
        </button>
      </div>
    </div>
  );
}

export function QuickMemo() {
  const qc = useQueryClient();
  const { data } = useQuery<{ id: number; content: string }>({
    queryKey: ['memo'],
    queryFn: () => axios.get('/api/memo').then((r) => r.data),
  });

  const [val, setVal] = useState('');
  useEffect(() => {
    if (data !== undefined) setVal(data.content);
  }, [data]);

  const save = useMutation({
    mutationFn: (content: string) => axios.put('/api/memo', { content }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memo'] }),
  });

  const onSave = useCallback(() => save.mutate(val), [val, save]);

  return (
    <div className="card s4">
      <CardHead icon="memo" title="빠른 메모" meta={val.length ? val.length + '자' : '비어있음'} />
      <textarea
        className="memo-area scroll"
        placeholder={'생각나는 거 아무거나 적어둬.\n쿼크가 나중에 정리해줄게 ✍️'}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onBlur={onSave}
      />
    </div>
  );
}
