/* QUARK — 연구 아카이브 화면 (Arxiv 연구조수, LangGraph 파이프라인). */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Icon } from '@/components/Icon';

interface ResearchNote {
  id: number;
  arxiv_id: string;
  title: string;
  authors: string;
  summary_ko: string;
  url: string;
  keyword: string;
  citation_count: number;
  created_at: string;
}

interface RunResult {
  keywords: string[];
  fetched: number;
  saved: number;
}

export default function ResearchScreen() {
  const qc = useQueryClient();
  const [keyword, setKeyword] = useState('');

  const { data: notes = [] } = useQuery<ResearchNote[]>({
    queryKey: ['research'],
    queryFn: () => axios.get<ResearchNote[]>('/api/research').then((r) => r.data),
  });

  const run = useMutation({
    mutationFn: (kw: string) =>
      axios
        .post<RunResult>('/api/research/run', kw ? { keyword: kw } : {})
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['research'] }),
  });

  return (
    <div className="canvas scroll">
      <div className="grid">
        <div className="card s12" style={{ padding: '18px 22px' }}>
          <div className="row between" style={{ alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--tx-hi)' }}>
                📚 연구 아카이브 — Arxiv 연구조수
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--tx-mid)', marginTop: 3 }}>
                {notes.length}건 저장됨 · LangGraph 파이프라인(fetch → filter → summarize → save) · 수동 실행
              </div>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <input
                className="memo-area"
                style={{ height: 36, padding: '0 12px', borderRadius: 8, width: 180 }}
                placeholder="키워드 (비우면 기본값 전체)"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
              <button
                className="pill acc"
                disabled={run.isPending}
                onClick={() => run.mutate(keyword.trim())}
              >
                <Icon name="idea" /> {run.isPending ? '조사 중...' : '지금 조사하기'}
              </button>
            </div>
          </div>
          {run.data && (
            <div style={{ fontSize: 11.5, color: 'var(--tx-mid)', marginTop: 10 }}>
              키워드 [{run.data.keywords.join(', ')}] — {run.data.fetched}건 확인, 새 논문 {run.data.saved}건 저장
            </div>
          )}
        </div>

        {notes.length === 0 && (
          <div className="card s12" style={{ padding: '18px 22px', textAlign: 'center', color: 'var(--tx-mid)', fontSize: 12.5 }}>
            아직 저장된 논문이 없어 — "지금 조사하기"로 시작해봐.
          </div>
        )}

        {notes.map((n) => (
          <div key={n.id} className="card hov s6" style={{ padding: '16px 18px' }}>
            <div className="row between" style={{ alignItems: 'flex-start', gap: 10 }}>
              <div style={{ minWidth: 0 }}>
                <a
                  href={n.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--tx-hi)', textDecoration: 'none' }}
                >
                  {n.title}
                </a>
                <div style={{ fontSize: 10.5, color: 'var(--tx-mid)', marginTop: 3 }}>
                  {n.authors}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <span className="news-tag" style={{ color: 'var(--acc-bright)' }}>인용 {n.citation_count}</span>
                <span className="news-tag">{n.keyword}</span>
              </div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--tx)', lineHeight: 1.6, marginTop: 10 }}>
              {n.summary_ko}
            </div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--tx-low)', marginTop: 10 }}>
              {n.arxiv_id} · {new Date(n.created_at).toLocaleDateString('ko-KR')}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
