/* QUARK — 비서 콘솔 + 빠른 메모.
 * 응답 생성부는 더미(pickReply) 유지 — 추후 hooks/useQuarkChat.ts(SSE)로 교체 쉽게 분리. */
import { useEffect, useRef, useState } from 'react';
import { CardHead } from '@/components/common';
import { Icon } from '@/components/Icon';
import { useHomeStore } from '@/stores/homeStore';
import { QDATA } from '@/data/quarkData';
import mascot from '@/assets/quark-mascot.png';

const QC_SUGGEST = ['쿼크, 불 꺼줘', '쿼크, 오늘 일정 어때', '쿼크, 아이디어 있어', '쿼크, 물 마실 시간이야?'];

interface ChatMsg {
  who: 'q' | 'me';
  text: string;
}

function pickReply(t: string): string {
  if (/불|조명|꺼|라이트/.test(t)) return QDATA.quarkReplies[0];
  if (/일정|스케줄|약속/.test(t)) return QDATA.quarkReplies[1];
  if (/아이디어|생각|메모/.test(t)) return QDATA.quarkReplies[2];
  if (/에어컨|냉방|더워|시원/.test(t)) return QDATA.quarkReplies[3];
  if (/물|수분|마실/.test(t)) return QDATA.quarkReplies[4];
  if (/서버|상태|cpu|온도/i.test(t)) return QDATA.quarkReplies[5];
  if (/취침|잘|자|불끄고/.test(t)) return QDATA.quarkReplies[6];
  return '응, 접수했어! 그건 곧 처리할게 — 더 필요한 거 있으면 언제든 불러 🦫';
}

export function QuarkConsole() {
  const onCommand = useHomeStore((s) => s.handleCommand);
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    {
      who: 'q',
      text: '좋은 아침이야 쿼딩! ☀️ 어제보다 1.5도 따뜻해. 오늘 일정 4개 잡혀있고, 식물은 물 줄 때 됐어. 뭐부터 도와줄까?',
    },
  ]);
  const [val, setVal] = useState('');
  const [typing, setTyping] = useState(false);
  const streamRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight;
  }, [msgs, typing]);

  const send = (text?: string) => {
    const t = (text || val).trim();
    if (!t) return;
    setMsgs((m) => [...m, { who: 'me', text: t }]);
    setVal('');
    setTyping(true);
    onCommand(t);
    const reply = pickReply(t);
    setTimeout(() => {
      setTyping(false);
      setMsgs((m) => [...m, { who: 'q', text: reply }]);
    }, 750 + Math.random() * 500);
  };

  return (
    <div className="card s8" style={{ minHeight: 340 }}>
      <CardHead icon="mic" title="쿼크에게 말하기" meta="QUARK · 대기 중" metaAcc />
      <div className="qc-stream scroll" ref={streamRef}>
        {msgs.map((m, i) => (
          <div key={i} className={'qc-msg ' + (m.who === 'me' ? 'me' : 'q')}>
            {m.who === 'q' && (
              <div className="qc-ava">
                <img className="pixelated" src={mascot} alt="쿼크" />
              </div>
            )}
            <div className="qc-bub">
              {m.who === 'q' && <div className="qc-who">쿼크 · QUARK</div>}
              {m.text}
            </div>
          </div>
        ))}
        {typing && (
          <div className="qc-msg q">
            <div className="qc-ava">
              <img className="pixelated" src={mascot} alt="쿼크" />
            </div>
            <div className="qc-bub">
              <span className="qc-typing">
                <i />
                <i />
                <i />
              </span>
            </div>
          </div>
        )}
      </div>
      <div className="qc-suggest">
        {QC_SUGGEST.map((s) => (
          <button key={s} className="qc-chip" onClick={() => send(s)}>
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
  const [val, setVal] = useState<string>(() => localStorage.getItem('quark-memo') || '');
  useEffect(() => {
    localStorage.setItem('quark-memo', val);
  }, [val]);
  return (
    <div className="card s4">
      <CardHead icon="memo" title="빠른 메모" meta={val.length ? val.length + '자' : '비어있음'} />
      <textarea
        className="memo-area scroll"
        placeholder={'생각나는 거 아무거나 적어둬.\n쿼크가 나중에 정리해줄게 ✍️'}
        value={val}
        onChange={(e) => setVal(e.target.value)}
      />
    </div>
  );
}
