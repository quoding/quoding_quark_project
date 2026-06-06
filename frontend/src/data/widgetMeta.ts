/* QUARK — 위젯 카탈로그. 대시보드 편집(추가/숨기기/크기)의 단일 소스.
   cat: 카테고리 / sizes: 허용 폭(grid span) / def: 기본표시 / locked: 미구현(로드맵) */
import type { WidgetCategory, WidgetMeta } from '@/types/quark';

export const WIDGET_META: WidgetMeta[] = [
  // 집 제어
  { id: 'scenes', title: '씬 프리셋', ico: 'zap', cat: '집 제어', sizes: [12, 8], def: true },
  { id: 'lights', title: '조명', ico: 'bulb', cat: '집 제어', sizes: [4, 3], def: true },
  { id: 'led', title: 'LED 무드등', ico: 'palette', cat: '집 제어', sizes: [4, 3], def: true },
  { id: 'climate', title: '냉방·식물', ico: 'snow', cat: '집 제어', sizes: [4, 3], def: true },
  // 일정 & 비서
  { id: 'schedule', title: '오늘 일정', ico: 'calendar', cat: '일정·비서', sizes: [5, 4], def: true },
  { id: 'today', title: '오늘 할일', ico: 'check', cat: '일정·비서', sizes: [4, 3], def: true },
  { id: 'actions', title: '오늘 할일 (구)', ico: 'zap', cat: '일정·비서', sizes: [3, 4], def: false },
  { id: 'console', title: '쿼크 비서', ico: 'mic', cat: '일정·비서', sizes: [8, 6, 12], def: true },
  { id: 'memo', title: '빠른 메모', ico: 'memo', cat: '일정·비서', sizes: [4, 3], def: true },
  { id: 'news', title: '뉴스 피드', ico: 'news', cat: '일정·비서', sizes: [4, 6], def: false },
  { id: 'transit', title: '대중교통', ico: 'bus', cat: '일정·비서', sizes: [4, 3], def: false },
  // 습관 & 건강
  { id: 'habits', title: '오늘의 습관 (구)', ico: 'check', cat: '습관·건강', sizes: [4, 3], def: false },
  { id: 'water', title: '수분 섭취', ico: 'droplet', cat: '습관·건강', sizes: [3, 4], def: true },
  { id: 'mood', title: '기분 로그', ico: 'smile', cat: '습관·건강', sizes: [3, 4], def: false },
  { id: 'sleep', title: '수면 기록', ico: 'bed', cat: '습관·건강', sizes: [3, 4], def: false },
  { id: 'caffeine', title: '카페인 컷오프', ico: 'coffee', cat: '습관·건강', sizes: [3, 4], def: false },
  // 집중 & 시간
  { id: 'pomodoro', title: '포모도로', ico: 'timer', cat: '집중·시간', sizes: [3, 4], def: true },
  { id: 'dday', title: 'D-Day', ico: 'target', cat: '집중·시간', sizes: [3, 4], def: true },
  { id: 'worldclock', title: '세계 시계', ico: 'globe', cat: '집중·시간', sizes: [4, 3], def: false },
  // 정보
  { id: 'weather', title: '날씨 예보', ico: 'cloud', cat: '정보', sizes: [4, 6], def: false },
  { id: 'sun', title: '일출·일몰', ico: 'sun', cat: '정보', sizes: [3, 4], def: false },
  { id: 'market', title: '시세', ico: 'coin', cat: '정보', sizes: [3, 4], def: true },
  // 로드맵 — 준비 중 (잠금)
  { id: 'camera', title: '카메라 피드', ico: 'cam', cat: '집 제어', sizes: [6], locked: true },
  { id: 'appliances', title: '가전 제어', ico: 'home', cat: '집 제어', sizes: [6], locked: true },
  { id: 'envSensor', title: '실내 환경(CO2)', ico: 'wind', cat: '습관·건강', sizes: [4], locked: true },
  { id: 'mail', title: '메일 분류', ico: 'news', cat: '일정·비서', sizes: [4], locked: true },
  { id: 'newsAI', title: 'AI 뉴스 요약', ico: 'idea', cat: '일정·비서', sizes: [6], locked: true },
  { id: 'focusStats', title: '집중 세션 통계', ico: 'target', cat: '집중·시간', sizes: [4], locked: true },
  { id: 'docker', title: 'Docker 상태', ico: 'automation', cat: '정보', sizes: [4], locked: true },
  { id: 'backup', title: '백업 리포트', ico: 'check', cat: '정보', sizes: [4], locked: true },
];

export const WIDGET_CATS: WidgetCategory[] = ['집 제어', '일정·비서', '습관·건강', '집중·시간', '정보'];

export const META_BY_ID: Record<string, WidgetMeta> = Object.fromEntries(
  WIDGET_META.map((w) => [w.id, w]),
);

export const DASH_DEFAULT: string[] = WIDGET_META.filter((w) => w.def).map((w) => w.id);
