/* QUARK — 위젯 레지스트리. id → 렌더 노드 매핑(편집 패널의 단일 소스).
 * 새 위젯 추가: widgetMeta에 한 줄 + 컴포넌트 작성 + 여기 매핑하면 편집 패널에 자동 등장. */
import type { ReactNode } from 'react';
import { ScenesBar, LightsCard, LedCard, ClimatePlantCard } from '@/components/widgets/home';
import {
  ScheduleCard,
  ActionsCard,
  HabitsCard,
  PomodoroCard,
  DdayCard,
  WaterCard,
  MarketCard,
} from '@/components/widgets/productivity';
import { QuarkConsole, QuickMemo } from '@/components/widgets/console';
import {
  WeatherCard,
  SunCard,
  WorldClockCard,
  NewsCard,
  TransitCard,
  MoodCard,
  SleepCard,
  CaffeineCard,
} from '@/components/widgets/extra';

export const DASH_WIDGETS: Record<string, ReactNode> = {
  scenes: <ScenesBar />,
  lights: <LightsCard />,
  led: <LedCard />,
  climate: <ClimatePlantCard />,
  schedule: <ScheduleCard />,
  habits: <HabitsCard />,
  actions: <ActionsCard />,
  pomodoro: <PomodoroCard />,
  dday: <DdayCard />,
  water: <WaterCard />,
  market: <MarketCard />,
  console: <QuarkConsole />,
  memo: <QuickMemo />,
  weather: <WeatherCard />,
  sun: <SunCard />,
  worldclock: <WorldClockCard />,
  news: <NewsCard />,
  transit: <TransitCard />,
  mood: <MoodCard />,
  sleep: <SleepCard />,
  caffeine: <CaffeineCard />,
};
