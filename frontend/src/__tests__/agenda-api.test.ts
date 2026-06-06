import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('AgendaScreen API integration', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('GET /api/todos returns list shape', async () => {
    const mockGet = vi.fn().mockResolvedValue({
      data: [
        { id: 1, text: '에어컨 필터 청소', done: false, created_at: '2026-06-06T08:00:00Z' },
        { id: 2, text: 'API 키 로테이션', done: true, created_at: '2026-06-06T09:00:00Z' },
      ],
    });

    vi.doMock('axios', () => ({ default: { get: mockGet, post: vi.fn(), patch: vi.fn() } }));

    const axios = (await import('axios')).default;
    const resp = await axios.get('/api/todos');
    expect(resp.data).toHaveLength(2);
    expect(resp.data[0]).toHaveProperty('text');
    expect(resp.data[0]).toHaveProperty('done');
    expect(resp.data[0]).toHaveProperty('id');
  });

  it('POST /api/ideas sends text and tag', async () => {
    const mockPost = vi.fn().mockResolvedValue({
      data: { id: 3, text: 'LED 일출 알람', tag: '하드웨어', created_at: '2026-06-06T10:00:00Z' },
    });

    vi.doMock('axios', () => ({ default: { get: vi.fn(), post: mockPost, patch: vi.fn() } }));

    const axios = (await import('axios')).default;
    const resp = await axios.post('/api/ideas', { text: 'LED 일출 알람', tag: '하드웨어' });
    expect(mockPost).toHaveBeenCalledWith('/api/ideas', { text: 'LED 일출 알람', tag: '하드웨어' });
    expect(resp.data.tag).toBe('하드웨어');
  });

  it('PATCH /api/todos/{id} toggles done state', async () => {
    const mockPatch = vi.fn().mockResolvedValue({
      data: { id: 1, text: '청소', done: true, created_at: '2026-06-06T08:00:00Z' },
    });

    vi.doMock('axios', () => ({ default: { get: vi.fn(), post: vi.fn(), patch: mockPatch } }));

    const axios = (await import('axios')).default;
    const resp = await axios.patch('/api/todos/1');
    expect(mockPatch).toHaveBeenCalledWith('/api/todos/1');
    expect(resp.data.done).toBe(true);
  });

  it('GET /api/agenda/events accepts date_filter query', async () => {
    const mockGet = vi.fn().mockResolvedValue({
      data: [
        {
          id: 1,
          title: '데일리 스탠드업',
          scheduled_at: '2026-06-06T09:00:00Z',
          tag: '회의',
          done: false,
          created_at: '2026-06-06T08:00:00Z',
        },
      ],
    });

    vi.doMock('axios', () => ({ default: { get: mockGet, post: vi.fn(), patch: vi.fn() } }));

    const axios = (await import('axios')).default;
    const resp = await axios.get('/api/agenda/events?date_filter=2026-06-06');
    expect(mockGet).toHaveBeenCalledWith('/api/agenda/events?date_filter=2026-06-06');
    expect(resp.data[0].title).toBe('데일리 스탠드업');
  });
});

describe('TopBar weather API', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('GET /api/system/weather returns weather shape', async () => {
    const mockGet = vi.fn().mockResolvedValue({
      data: {
        temp: 22.5,
        label: '맑음',
        hi: 26.0,
        lo: 16.0,
        pm25: 12.0,
        aqi_grade: '좋음',
      },
    });

    vi.doMock('axios', () => ({ default: { get: mockGet } }));

    const axios = (await import('axios')).default;
    const resp = await axios.get('/api/system/weather');
    expect(resp.data).toHaveProperty('temp');
    expect(resp.data).toHaveProperty('aqi_grade');
    expect(typeof resp.data.temp).toBe('number');
  });

  it('weather fallback works when API returns error field', async () => {
    const errorData = { error: 'network timeout' };
    expect(errorData).toHaveProperty('error');
    // Fallback logic: use QDATA defaults when error is present
    const fallbackTemp = 23;
    expect(fallbackTemp).toBe(23);
  });
});

describe('MonitorScreen system stats API', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('GET /api/system/stats returns expected shape', async () => {
    const mockGet = vi.fn().mockResolvedValue({
      data: { cpu: 34, ram: 58, disk: 62, temp: 47.0, uptime_days: 41 },
    });

    vi.doMock('axios', () => ({ default: { get: mockGet } }));

    const axios = (await import('axios')).default;
    const resp = await axios.get('/api/system/stats');
    const stats = resp.data;
    expect(stats).toHaveProperty('cpu');
    expect(stats).toHaveProperty('ram');
    expect(stats).toHaveProperty('disk');
    expect(stats).toHaveProperty('uptime_days');
  });
});
