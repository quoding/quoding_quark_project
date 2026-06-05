/* QUARK — 집 상태 단일 스토어 (Zustand).
 * Dashboard·IoT·Agenda·Automation 화면이 공유한다(상태 공유 = 단일 스토어).
 * 각 setter는 cmd()로 디바이스 브리지에 명령을 흘려보낸다(현재 더미). */
import { create } from 'zustand';
import { QDATA } from '@/data/quarkData';
import { cmd } from '@/stores/bridge';
import type {
  AcState,
  ActionItem,
  Appliance,
  Automation,
  Habit,
  Idea,
  Lights,
  LightKey,
} from '@/types/quark';

interface HomeState {
  lights: Lights;
  bright: number;
  ledColor: string;
  ledOn: boolean;
  ac: AcState;
  moisture: number;
  watering: boolean;
  scene: string;
  water: number;
  habits: Habit[];
  actions: ActionItem[];
  appliances: Appliance[];
  ideas: Idea[];
  rules: Automation[];

  toggleLight: (k: LightKey) => void;
  setBright: (v: number) => void;
  setLedColor: (c: string) => void;
  toggleLed: () => void;
  setAcField: <K extends keyof AcState>(k: K, v: AcState[K]) => void;
  waterPlant: () => void;
  applyScene: (id: string) => void;
  handleCommand: (t: string) => void;
  addWater: () => void;
  toggleHabit: (i: number) => void;
  toggleAction: (i: number) => void;
  toggleAppliance: (id: string) => void;
  addIdea: (text: string, tag?: string) => void;
  toggleRule: (id: string) => void;
}

export const useHomeStore = create<HomeState>((set, get) => ({
  lights: { living: true, bed: false, desk: true, kitchen: false },
  bright: 72,
  ledColor: '#3d8bfd',
  ledOn: true,
  ac: { on: true, temp: 24 },
  moisture: 31,
  watering: false,
  scene: 'focus',
  water: 1250,
  habits: QDATA.habits.map((h) => ({ ...h })),
  actions: QDATA.actions.map((a) => ({ ...a })),
  appliances: QDATA.appliances.map((a) => ({ ...a })),
  ideas: QDATA.ideasSeed.map((i) => ({ ...i })),
  rules: QDATA.automations.map((r) => ({ ...r })),

  toggleLight: (k) =>
    set((s) => {
      const next = !s.lights[k];
      cmd('light', k, next);
      return { lights: { ...s.lights, [k]: next } };
    }),
  setBright: (v) => {
    cmd('light', 'bright', v);
    set({ bright: v });
  },
  setLedColor: (c) => {
    cmd('led', 'color', c);
    set({ ledColor: c });
  },
  toggleLed: () =>
    set((s) => {
      cmd('led', 'on', !s.ledOn);
      return { ledOn: !s.ledOn };
    }),
  setAcField: (k, v) =>
    set((s) => {
      cmd('ac', String(k), v);
      return { ac: { ...s.ac, [k]: v } };
    }),

  waterPlant: () => {
    if (get().watering) return;
    cmd('plant', 'water', true);
    set({ watering: true });
    let m = get().moisture;
    const id = setInterval(() => {
      m = Math.min(82, m + 6);
      set({ moisture: m });
      if (m >= 82) {
        clearInterval(id);
        setTimeout(() => set({ watering: false }), 400);
      }
    }, 120);
  },

  applyScene: (id) => {
    cmd('scene', 'apply', id);
    if (id === 'sleep') {
      set({
        scene: id,
        lights: { living: false, bed: false, desk: false, kitchen: false },
        ledOn: false,
        ac: { on: true, temp: 26 },
      });
    } else if (id === 'focus') {
      set({
        scene: id,
        lights: { living: false, bed: false, desk: true, kitchen: false },
        ledColor: '#3d8bfd',
        ledOn: true,
        bright: 85,
      });
    } else if (id === 'film') {
      set({
        scene: id,
        lights: { living: true, bed: false, desk: true, kitchen: true },
        ledColor: '#ffffff',
        ledOn: true,
        bright: 100,
      });
    } else if (id === 'home') {
      set({
        scene: id,
        lights: { living: true, bed: false, desk: false, kitchen: true },
        ledColor: '#f5b945',
        ledOn: true,
        bright: 70,
      });
    } else if (id === 'relax') {
      set({
        scene: id,
        lights: { living: true, bed: false, desk: false, kitchen: false },
        ledColor: '#b07bff',
        ledOn: true,
        bright: 40,
      });
    } else {
      set({ scene: id });
    }
  },

  handleCommand: (t) => {
    if (/불.*꺼|조명.*꺼|꺼줘/.test(t)) {
      cmd('light', 'all', false);
      set({ lights: { living: false, bed: false, desk: false, kitchen: false } });
    } else if (/불.*켜|조명.*켜/.test(t)) {
      set((s) => ({ lights: { ...s.lights, living: true, desk: true } }));
    }
    if (/물|수분/.test(t)) set((s) => ({ water: Math.min(2000, s.water + 250) }));
    if (/취침|잘게|자자/.test(t)) get().applyScene('sleep');
  },

  addWater: () => {
    cmd('habit', 'water', 250);
    set((s) => ({ water: Math.min(2000, s.water + 250) }));
  },
  toggleHabit: (i) =>
    set((s) => ({ habits: s.habits.map((h, j) => (j === i ? { ...h, done: !h.done } : h)) })),
  toggleAction: (i) =>
    set((s) => ({ actions: s.actions.map((a, j) => (j === i ? { ...a, done: !a.done } : a)) })),
  toggleAppliance: (id) =>
    set((s) => ({
      appliances: s.appliances.map((a) => {
        if (a.id !== id) return a;
        cmd('appliance', id, !a.on);
        return { ...a, on: !a.on };
      }),
    })),
  addIdea: (text, tag) =>
    set((s) => ({ ideas: [{ text, tag: tag || '아이디어', time: '방금' }, ...s.ideas] })),
  toggleRule: (id) =>
    set((s) => ({
      rules: s.rules.map((r) => {
        if (r.id !== id) return r;
        cmd('automation', id, !r.on);
        return { ...r, on: !r.on };
      }),
    })),
}));
