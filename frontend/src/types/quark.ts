/* QUARK — 공유 타입(공유 계약). 데이터·스토어·위젯이 모두 참조한다. */
import type { IconName } from '@/components/Icon';

export type LightKey = 'living' | 'bed' | 'desk' | 'kitchen';
export type Lights = Record<LightKey, boolean>;
export interface AcState {
  on: boolean;
  temp: number;
}

export type ScheduleTag = '회의' | '마감' | '작업' | '개인';
export interface ScheduleItem {
  t: string;
  title: string;
  tag: ScheduleTag;
  soon: boolean;
}

export interface ActionItem {
  t: string;
  done: boolean;
}
export interface Habit {
  name: string;
  streak: number;
  done: boolean;
}
export interface Dday {
  label: string;
  days: number;
}
export interface MarketRow {
  sym: string;
  name: string;
  price: number;
  chg: number;
}
export interface Scene {
  id: string;
  name: string;
  ico: IconName;
  desc: string;
}
export interface Appliance {
  id: string;
  name: string;
  ico: IconName;
  on: boolean;
  status: string;
  prog?: number;
}
export interface Camera {
  id: string;
  name: string;
  status: string;
  tone: number;
}

export interface ForecastDay {
  d: string;
  ico: IconName;
  hi: number;
  lo: number;
  pop: number;
}
export interface SunInfo {
  rise: string;
  set: string;
  dayLen: string;
  umbrella: boolean;
  laundry: boolean;
}
export interface WorldClock {
  city: string;
  tz: number;
  flag: string;
}
export interface NewsItem {
  title: string;
  src: string;
  tag: string;
  time: string;
}
export interface TransitItem {
  line: string;
  kind: 'bus' | 'subway';
  dest: string;
  eta: number;
  next: number;
  color: string;
}
export interface MoodDay {
  day: string;
  emo: string | null;
}
export interface SleepSeed {
  lastH: number;
  lastM: number;
  goal: number;
  week: number[];
}
export interface Caffeine {
  lastCup: string;
  cutoff: string;
  bedtime: string;
  cupsToday: number;
}

export interface WeekEvent {
  t: string;
  title: string;
  tag: ScheduleTag;
  dur: number;
}
export interface Idea {
  text: string;
  tag: string;
  time: string;
}
export type AlertKind = 'deadline' | 'meeting' | 'review';
export interface AlertItem {
  kind: AlertKind;
  title: string;
  desc: string;
  when: string;
  urgent: boolean;
}

export type ServiceStatus = 'up' | 'warn' | 'down';
export interface Service {
  name: string;
  status: ServiceStatus;
  uptime: string;
  latency: number;
}
export interface DockerContainer {
  name: string;
  img: string;
  status: 'running' | 'stopped';
  cpu: number;
  mem: number;
}
export interface GithubInfo {
  streak: number;
  today: number;
  week: number;
  lastCommit: string;
}
export interface ApiItem {
  name: string;
  tokens: string;
  cost: number;
  pct: number;
}
export interface ApiUsage {
  monthCost: number;
  budget: number;
  items: ApiItem[];
}
export interface Automation {
  id: string;
  name: string;
  trigger: string;
  action: string;
  on: boolean;
  ico: IconName;
  runs: number;
}

export interface ServerStats {
  cpu: number;
  ram: number;
  temp: number;
  disk: number;
  uptimeDays: number;
}

/* 위젯 카탈로그 */
export type WidgetCategory = '집 제어' | '일정·비서' | '습관·건강' | '집중·시간' | '정보';
export interface WidgetMeta {
  id: string;
  title: string;
  ico: IconName;
  cat: WidgetCategory;
  sizes: number[];
  def?: boolean;
  locked?: boolean;
}

/* 대시보드 레이아웃 영속 구조 */
export interface DashConfig {
  active: string[];
  sizes: Record<string, number>;
}
