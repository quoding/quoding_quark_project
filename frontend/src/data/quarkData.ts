/* QUARK — 더미 데이터 (한국 사용자 맥락). 추후 실제 API/디바이스로 교체. */
import type {
  ActionItem,
  AlertItem,
  Appliance,
  ApiUsage,
  Automation,
  Caffeine,
  Camera,
  Dday,
  DockerContainer,
  ForecastDay,
  GithubInfo,
  Habit,
  Idea,
  MarketRow,
  MoodDay,
  NewsItem,
  Scene,
  ScheduleItem,
  Service,
  ServerStats,
  SleepSeed,
  SunInfo,
  TransitItem,
  WeekEvent,
  WorldClock,
} from '@/types/quark';

interface QuarkData {
  user: string;
  weather: { temp: number; label: string; city: string; hi: number; lo: number };
  aqi: { pm25: number; grade: string };
  server: ServerStats;
  schedule: ScheduleItem[];
  actions: ActionItem[];
  habits: Habit[];
  dday: Dday[];
  crypto: MarketRow[];
  fx: MarketRow[];
  scenes: Scene[];
  appliances: Appliance[];
  cameras: Camera[];
  forecast: ForecastDay[];
  sun: SunInfo;
  clocks: WorldClock[];
  news: NewsItem[];
  transit: TransitItem[];
  moodSeed: MoodDay[];
  sleepSeed: SleepSeed;
  caffeine: Caffeine;
  weekEvents: WeekEvent[][];
  ideasSeed: Idea[];
  alerts: AlertItem[];
  services: Service[];
  docker: DockerContainer[];
  github: GithubInfo;
  api: ApiUsage;
  automations: Automation[];
  quarkReplies: string[];
}

export const QDATA: QuarkData = {
  user: '쿼딩',
  weather: { temp: 23, label: '맑음', city: '서울', hi: 26, lo: 17 },
  aqi: { pm25: 18, grade: '좋음' },
  server: { cpu: 34, ram: 58, temp: 47, disk: 62, uptimeDays: 41 },
  schedule: [
    { t: '10:30', title: '쿼크 데일리 빌드 회의', tag: '회의', soon: false },
    { t: '13:00', title: '점심 — 영상 촬영 컨셉 정리', tag: '개인', soon: false },
    { t: '15:00', title: '홈랩 LED 제어 펌웨어 테스트', tag: '작업', soon: true },
    { t: '20:00', title: '유튜브 편집 마감', tag: '마감', soon: false },
  ],
  actions: [
    { t: '에어컨 필터 청소', done: false },
    { t: '식물 토양 센서 캘리브레이션', done: false },
    { t: 'API 키 로테이션', done: true },
  ],
  habits: [
    { name: '아침 스트레칭', streak: 12, done: true },
    { name: '물 2L 마시기', streak: 7, done: false },
    { name: '커밋 1회 이상', streak: 23, done: true },
    { name: '독서 20분', streak: 4, done: false },
  ],
  dday: [
    { label: '쿼크 v1 데모', days: 9 },
    { label: '구독자 1만', days: 31 },
  ],
  crypto: [
    { sym: 'BTC', name: '비트코인', price: 96420000, chg: 2.4 },
    { sym: 'ETH', name: '이더리움', price: 5180000, chg: -1.1 },
    { sym: 'SOL', name: '솔라나', price: 312000, chg: 5.7 },
  ],
  fx: [
    { sym: 'USD', name: '미국 달러', price: 1378.5, chg: 0.3 },
    { sym: 'JPY', name: '일본 엔(100)', price: 905.2, chg: -0.6 },
  ],
  scenes: [
    { id: 'focus', name: '집중 모드', ico: 'target', desc: '책상등만 켜고 밝게, 알림 최소화' },
    { id: 'sleep', name: '취침 모드', ico: 'moon', desc: '전체 소등, 에어컨 26도, 무음' },
    { id: 'film', name: '영상 촬영', ico: 'cam', desc: '전체 점등 100%, LED 화이트' },
    { id: 'home', name: '귀가 모드', ico: 'home', desc: '거실·주방 점등, 따뜻한 조명' },
    { id: 'relax', name: '휴식 모드', ico: 'leaf', desc: '은은한 보라 무드등, 밝기 40%' },
  ],
  appliances: [
    { id: 'washer', name: '세탁기', ico: 'wash', on: true, status: '표준 세탁 · 28분 남음', prog: 62 },
    { id: 'purifier', name: '공기청정기', ico: 'wind', on: true, status: '자동 · 청정' },
    { id: 'robot', name: '로봇청소기', ico: 'automation', on: false, status: '충전 완료 · 대기' },
    { id: 'tv', name: '거실 TV', ico: 'monitor', on: false, status: '꺼짐' },
    { id: 'boiler', name: '보일러', ico: 'temp', on: true, status: '난방 22°' },
  ],
  cameras: [
    { id: 'door', name: '현관', status: 'LIVE', tone: 18 },
    { id: 'living', name: '거실', status: 'LIVE', tone: 28 },
    { id: 'desk', name: '작업실', status: 'LIVE', tone: 22 },
  ],
  forecast: [
    { d: '오늘', ico: 'sun', hi: 26, lo: 17, pop: 10 },
    { d: '내일', ico: 'cloud', hi: 24, lo: 16, pop: 30 },
    { d: '목', ico: 'rain', hi: 21, lo: 15, pop: 70 },
    { d: '금', ico: 'rain', hi: 20, lo: 14, pop: 60 },
    { d: '토', ico: 'cloud', hi: 23, lo: 15, pop: 20 },
    { d: '일', ico: 'sun', hi: 27, lo: 18, pop: 5 },
  ],
  sun: { rise: '05:18', set: '19:46', dayLen: '14시간 28분', umbrella: false, laundry: true },
  clocks: [
    { city: '서울', tz: 9, flag: 'KR' },
    { city: '뉴욕', tz: -4, flag: 'US' },
    { city: '런던', tz: 1, flag: 'GB' },
    { city: '선전', tz: 8, flag: 'CN' },
  ],
  news: [
    { title: 'ESP32-S3, 온디바이스 AI 추론 벤치마크 공개', src: 'Hackaday', tag: '하드웨어', time: '2시간 전' },
    { title: '오픈소스 홈 어시스턴트, MQTT 자동 검색 기능 추가', src: 'GitHub Blog', tag: '스마트홈', time: '5시간 전' },
    { title: 'WS2812B 대안 LED, 전력 30% 절감 리포트', src: 'Reddit r/esp32', tag: 'LED', time: '어제' },
    { title: '1인 유튜버를 위한 자동 편집 워크플로 5선', src: 'No Film School', tag: '영상', time: '어제' },
  ],
  transit: [
    { line: '간선 470', kind: 'bus', dest: '강남 방면', eta: 3, next: 12, color: '#3d8bfd' },
    { line: '마을 02', kind: 'bus', dest: '역곡역', eta: 8, next: 21, color: '#4ad295' },
    { line: '2호선', kind: 'subway', dest: '내선순환', eta: 5, next: 11, color: '#2bc6d6' },
  ],
  moodSeed: [
    { day: '월', emo: '😎' }, { day: '화', emo: '🙂' }, { day: '수', emo: '😤' },
    { day: '목', emo: '🙂' }, { day: '금', emo: '😴' }, { day: '토', emo: '😎' }, { day: '일', emo: null },
  ],
  sleepSeed: { lastH: 6, lastM: 40, goal: 7.5, week: [7.2, 6.5, 8.0, 5.8, 6.7, 7.9, 6.4] },
  caffeine: { lastCup: '14:20', cutoff: '16:00', bedtime: '23:30', cupsToday: 2 },
  weekEvents: [
    [{ t: '09:00', title: '데일리 스탠드업', tag: '회의', dur: 1 }],
    [{ t: '14:00', title: '센서 보드 납땜', tag: '작업', dur: 2 }],
    [
      { t: '10:30', title: '쿼크 빌드 회의', tag: '회의', dur: 1 },
      { t: '15:00', title: '펌웨어 테스트', tag: '작업', dur: 1 },
      { t: '20:00', title: '편집 마감', tag: '마감', dur: 2 },
    ],
    [{ t: '11:00', title: '협찬 미팅', tag: '회의', dur: 1 }],
    [{ t: '13:00', title: '촬영', tag: '개인', dur: 3 }],
    [{ t: '16:00', title: '주간 리뷰', tag: '작업', dur: 1 }],
    [],
  ],
  ideasSeed: [
    { text: 'LED 스트립으로 일출 알람 만들기 — 기상 30분 전부터 서서히 밝게', tag: '하드웨어', time: '어제' },
    { text: '쿼크한테 음성으로 메모하면 자동 태깅되게', tag: 'SW', time: '2일 전' },
    { text: '식물 습도 + 날씨 연동해서 급수량 자동 조절', tag: '아이디어', time: '3일 전' },
  ],
  alerts: [
    { kind: 'deadline', title: '유튜브 편집 마감 D-0', desc: '오늘 20:00까지 · 진행률 60%', when: '오늘', urgent: true },
    { kind: 'meeting', title: '쿼크 빌드 회의 15분 전 알림', desc: '10:30 · 자료 준비됨', when: '10:15', urgent: false },
    { kind: 'review', title: '주간 리뷰 자동 생성됨', desc: '커밋 23 · 완료 액션 11개', when: '금 16:00', urgent: false },
  ],
  services: [
    { name: 'quark-core (비서 API)', status: 'up', uptime: '99.98%', latency: 42 },
    { name: 'home-bridge (IoT)', status: 'up', uptime: '99.9%', latency: 18 },
    { name: 'media-server', status: 'up', uptime: '99.7%', latency: 65 },
    { name: 'plant-sensor', status: 'warn', uptime: '97.2%', latency: 210 },
    { name: 'backup-cron', status: 'down', uptime: '—', latency: 0 },
  ],
  docker: [
    { name: 'quark-api', img: 'quark:1.4', status: 'running', cpu: 12, mem: 320 },
    { name: 'postgres', img: 'postgres:16', status: 'running', cpu: 4, mem: 180 },
    { name: 'redis', img: 'redis:7', status: 'running', cpu: 1, mem: 42 },
    { name: 'grafana', img: 'grafana:11', status: 'running', cpu: 3, mem: 96 },
    { name: 'whisper-stt', img: 'whisper:gpu', status: 'stopped', cpu: 0, mem: 0 },
  ],
  github: { streak: 23, today: 4, week: 31, lastCommit: '2시간 전' },
  api: {
    monthCost: 38420,
    budget: 60000,
    items: [
      { name: 'Claude (비서 응답)', tokens: '4.2M', cost: 21300, pct: 55 },
      { name: 'Whisper (음성 인식)', tokens: '—', cost: 9800, pct: 26 },
      { name: 'Embeddings (메모 검색)', tokens: '1.1M', cost: 4200, pct: 11 },
      { name: 'TTS (브리핑 음성)', tokens: '—', cost: 3120, pct: 8 },
    ],
  },
  automations: [
    { id: 'morning', name: '아침 브리핑', trigger: '매일 07:00', action: '날씨·일정·할 일 음성 브리핑', on: true, ico: 'sun', runs: 412 },
    { id: 'sleep', name: '취침 모드 자동 전환', trigger: '매일 00:30 또는 "잘게"', action: '전체 소등 · 에어컨 26° · 무음', on: true, ico: 'moon', runs: 168 },
    { id: 'plant', name: '식물 자동 급수', trigger: '토양 습도 < 30%', action: '워터펌프 8초 가동 + 알림', on: true, ico: 'leaf', runs: 54 },
    { id: 'review', name: '주간 리뷰 리포트', trigger: '매주 금 16:00', action: '커밋·습관·액션 요약 생성', on: true, ico: 'calendar', runs: 33 },
    { id: 'commit', name: '커밋 리마인더', trigger: '23:00에 오늘 커밋 0건이면', action: '쿼크가 푸시 알림', on: false, ico: 'github', runs: 21 },
    { id: 'arrive', name: '귀가 감지', trigger: '폰 Wi-Fi 연결 시', action: '귀가 모드 씬 실행', on: true, ico: 'home', runs: 96 },
  ],
  quarkReplies: [
    '오케이, 거실 불 껐어 💡 침실은 그대로 둘게.',
    '오늘 일정 4개 있어. 15시 펌웨어 테스트가 곧이야 — 미리 준비해두자!',
    '좋은 생각인데? 아이디어 카드로 저장해놨어. 나중에 일정&비서 탭에서 꺼내 쓰자.',
    '에어컨 24도로 맞췄어. 지금 방 온도보다 살짝 시원하게.',
    '물 마실 시간이야 💧 오늘 1.25L 마셨고 목표까지 750ml 남았어.',
    '서버 상태 멀쩡해. CPU 34%, 온도 47도 — 다 정상 범위야.',
    '취침 모드 켜둘까? 불 다 끄고 알림도 조용하게 바꿔줄게.',
  ],
};

export const fmt = (n: number): string => n.toLocaleString('ko-KR');
export const fmtMan = (n: number): string => {
  if (n >= 100000000) return (n / 100000000).toFixed(2) + '억';
  if (n >= 10000) return (n / 10000).toFixed(n >= 1000000 ? 0 : 1) + '만';
  return fmt(n);
};
