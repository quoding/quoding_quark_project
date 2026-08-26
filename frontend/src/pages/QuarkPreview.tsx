import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
  Activity, AirVent, BedDouble, Bell, BookOpen, Bot, CalendarDays, Camera, Check,
  ChevronDown, CircleUserRound, Clock3, Cloud, CloudLightning, CloudRain, CloudSun, Coffee, Command, Database, Droplets,
  ExternalLink, GitBranch, Home, LayoutDashboard, Leaf, Lightbulb, Menu,
  MessageCircle, Mic, MonitorCog, Moon, MoreHorizontal, Network, Newspaper, Play, Plus,
  Search, Send, Server, Settings2, ShieldCheck, Smile, Snowflake, Sparkles, Sun, Sunrise, Thermometer,
  TimerReset, ToggleLeft, ToggleRight, Trash2, WashingMachine, X, Zap,
} from 'lucide-react';
import mascot from '@/assets/quark-mascot.png';
import { QDATA } from '@/data/quarkData';
import { useHomeStore } from '@/stores/homeStore';
import { useQuarkChat } from '@/hooks/useQuarkChat';
import { useMqttConnected } from '@/lib/mqttSingleton';
import './QuarkPreview.css';

const navItems = [
  { label: '홈', path: '', icon: LayoutDashboard },
  { label: '스마트 홈', path: 'iot', icon: Home },
  { label: '일정', path: 'agenda', icon: CalendarDays },
  { label: '모니터링', path: 'monitor', icon: MonitorCog },
  { label: '자동화', path: 'automation', icon: Zap },
  { label: '연구 아카이브', path: 'research', icon: BookOpen },
];

const pageFromPath = () => navItems.find((item) => `/${item.path}`.replace(/\/$/, '') === window.location.pathname.replace(/\/$/, ''))?.label ?? '홈';

const scenes = [
  { id: 'focus', label: '집중', icon: TimerReset, tint: 'violet' },
  { id: 'relax', label: '휴식', icon: Leaf, tint: 'green' },
  { id: 'home', label: '귀가', icon: Home, tint: 'blue' },
  { id: 'sleep', label: '취침', icon: Moon, tint: 'navy' },
];

interface ApiEvent { id: string; title: string; scheduled_at: string; end_at: string | null; all_day: boolean }
interface ApiTodo { id: number; text: string; done: boolean; created_at: string }
interface ApiHabit { id: number; name: string; streak: number; done_today: boolean }
interface ApiIdea { id: number; text: string; tag: string; created_at: string }
interface ApiAlert { id: number; title: string; body: string; urgent: boolean; read: boolean; created_at: string }
interface SystemStats { cpu: number; ram: number; disk: number; temp: number | null; uptime_days: number }
interface ServiceEntry { name: string; status: 'up' | 'warn' | 'down'; latency: number | null; uptime?: string }
interface DockerEntry { name: string; img: string; status: string; cpu: number; mem: number }
interface GithubData { streak: number; today: number; week: number; lastCommit: string; error?: string }
interface AutomationApi { id: number; name: string; trigger_desc: string; action_desc: string; icon: string; enabled: boolean; run_count: number }
interface ResearchNote { id: number; arxiv_id: string; title: string; authors: string; summary_ko: string; url: string; keyword: string; citation_count: number; created_at: string }
interface ForecastData { forecast: Array<{d:string;ico:string;pop:number;hi:number;lo:number}>; sunrise:string; sunset:string; day_len:string }
interface NewsData { tag:string; title:string; src:string; time:string; url:string }
interface MoodData { id:number; date:string; score:number; note:string|null }
interface SleepData { id:number; date:string; hours:number; quality:number }
interface CaffeineData { date:string; cups_today:number; mg_today:number; cutoff:string; bedtime:string; last_cup:string|null }
interface PreviewWidgetConfig { active:string[]; sizes:Record<string,number>; previewVersion?:number }
const PREVIEW_WIDGETS=[
  ['memo','빠른 메모'],['water','수분 섭취'],['pomodoro','포모도로'],['dday','D-Day'],['market','시세'],
  ['weather','날씨·일출'],['news','뉴스'],['mood','기분'],['sleep','수면'],['caffeine','카페인'],['worldclock','세계 시계'],
] as const;
const PREVIEW_DEFAULT=PREVIEW_WIDGETS.map(([id])=>id);
function loadPreviewWidgets():PreviewWidgetConfig { try { const raw=localStorage.getItem('quark-dash-v2'); if(raw){const value=JSON.parse(raw) as Partial<PreviewWidgetConfig>;if(value.previewVersion===2&&Array.isArray(value.active)){const known=value.active.filter(id=>PREVIEW_WIDGETS.some(([widgetId])=>widgetId===id));return{active:known,sizes:value.sizes??{},previewVersion:2}}} }catch{/* malformed storage */} return{active:PREVIEW_DEFAULT.slice(),sizes:{},previewVersion:2} }

function PageIntro({ eyebrow, title, description, action, onAction }: { eyebrow: string; title: string; description: string; action?: string; onAction?: () => void }) {
  return <section className="qv2-page-intro"><div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action && <button onClick={onAction}><Plus />{action}</button>}</section>;
}

function SmartHomePage() {
  const [room, setRoom] = useState('전체');
  const [cameraIndex,setCameraIndex]=useState(0);
  const scene = useHomeStore((s) => s.scene);
  const applyScene = useHomeStore((s) => s.applyScene);
  const items = useHomeStore((s) => s.appliances);
  const toggleAppliance = useHomeStore((s) => s.toggleAppliance);
  const lights = useHomeStore((s) => s.lights);
  const toggleLight = useHomeStore((s) => s.toggleLight);
  const bright = useHomeStore((s) => s.bright);
  const setBright = useHomeStore((s) => s.setBright);
  const ledOn = useHomeStore((s) => s.ledOn);
  const ledColor = useHomeStore((s) => s.ledColor);
  const toggleLed = useHomeStore((s) => s.toggleLed);
  const setLedColor = useHomeStore((s) => s.setLedColor);
  const ac = useHomeStore((s) => s.ac);
  const setAcField = useHomeStore((s) => s.setAcField);
  const moisture = useHomeStore((s) => s.moisture);
  const watering = useHomeStore((s) => s.watering);
  const waterPlant = useHomeStore((s) => s.waterPlant);
  const rooms = ['전체', '거실', '작업실', '침실'];
  const lightNames = { living: '거실 조명', bed: '침실 조명', desk: '작업실 스탠드', kitchen: '주방 조명' } as const;
  return <>
    <PageIntro eyebrow="SMART HOME" title="스마트 홈" description="집 안의 공간과 기기를 한 곳에서 관리하세요." />
    <div className="qv2-room-tabs">{rooms.map((item) => <button className={room === item ? 'active' : ''} onClick={() => setRoom(item)} key={item}>{item}</button>)}</div>
    <section className="qv2-home-overview">
      <article className="qv2-card qv2-environment"><div className="qv2-card-head"><div><span className="qv2-eyebrow">LIVING ROOM</span><h3>거실 환경</h3></div><span className="qv2-good"><i /> 쾌적</span></div><div className="qv2-env-main"><CloudSun /><div><strong>24.2°</strong><span>맑고 쾌적해요</span></div></div><div className="qv2-env-stats"><div><Droplets /><span>습도</span><strong>48%</strong></div><div><AirVent /><span>공기질</span><strong>좋음</strong></div><div><Thermometer /><span>체감</span><strong>24°</strong></div></div></article>
      <article className="qv2-card qv2-power-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">ENERGY</span><h3>실시간 전력</h3></div><Zap /></div><div className="qv2-power-value"><strong>1.24</strong><span>kWh</span></div><div className="qv2-spark-bars">{[24,42,34,58,48,73,65,81,54,67,44,61].map((h,i)=><i key={i} style={{height:`${h}%`}} />)}</div><p>어제보다 <b>8% 적게</b> 사용 중이에요</p></article>
    </section>
    <section className="qv2-section"><div className="qv2-section-head"><div><h2>장면</h2><p>여러 기기를 한 번에 제어합니다.</p></div></div><div className="qv2-wide-scenes">{QDATA.scenes.map((item, i) => { const icons=[TimerReset,Moon,Camera,Home,Leaf]; const SceneIcon=icons[i]; return <button key={item.id} className={scene===item.id?'active':''} onClick={()=>applyScene(item.id)}><span><SceneIcon /></span><div><strong>{item.name}</strong><small>{item.desc}</small></div>{scene===item.id&&<Check />}</button>})}</div></section>
    <section className="qv2-section"><div className="qv2-section-head"><div><h2>세부 제어</h2><p>조명, 무드등, 냉방과 식물을 직접 제어합니다.</p></div></div><div className="qv2-control-grid">
      <article className="qv2-card qv2-control-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">LIGHTS</span><h3>조명</h3></div><Lightbulb /></div>{(Object.keys(lights) as Array<keyof typeof lights>).map((key)=><button className="qv2-control-row" key={key} onClick={()=>toggleLight(key)}><span>{lightNames[key]}</span>{lights[key]?<ToggleRight/>:<ToggleLeft/>}</button>)}<label className="qv2-range"><span>전체 밝기 <b>{bright}%</b></span><input type="range" min="0" max="100" value={bright} onChange={e=>setBright(Number(e.target.value))}/></label></article>
      <article className="qv2-card qv2-control-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">AMBIENCE</span><h3>LED 무드등</h3></div><button onClick={toggleLed}>{ledOn?<ToggleRight/>:<ToggleLeft/>}</button></div><div className="qv2-led-preview" style={{background:ledOn?`radial-gradient(circle at 30% 20%, ${ledColor}, ${ledColor}22 70%), #20352a`:'#eef1ed'}}><span>{ledOn?ledColor.toUpperCase():'OFF'}</span></div><div className="qv2-colors">{['#3f7d5e','#a98248','#b86555','#718078','#ffffff'].map(color=><button aria-label={color} className={ledColor===color?'active':''} key={color} style={{background:color}} onClick={()=>setLedColor(color)}/>)}</div></article>
      <article className="qv2-card qv2-control-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">CLIMATE</span><h3>냉방 · 식물</h3></div><button onClick={()=>setAcField('on',!ac.on)}>{ac.on?<ToggleRight/>:<ToggleLeft/>}</button></div><div className="qv2-temp-control"><button onClick={()=>setAcField('temp',Math.max(18,ac.temp-1))}>−</button><strong>{ac.temp}°</strong><button onClick={()=>setAcField('temp',Math.min(30,ac.temp+1))}>＋</button></div><div className="qv2-plant-control"><div><Leaf/><span>토양 습도</span><strong>{moisture}%</strong></div><div><i style={{width:`${moisture}%`}}/></div><button disabled={watering} onClick={waterPlant}><Droplets/>{watering?'급수 중…':'수동 급수'}</button></div></article>
    </div></section>
    <section className="qv2-section"><div className="qv2-section-head"><div><h2>가전</h2><p>{items.filter(i=>i.on).length}개 기기가 작동 중입니다.</p></div></div><div className="qv2-appliance-grid">{items.map((item,index)=>{ const icons=[WashingMachine,AirVent,Sparkles,MonitorCog,Thermometer]; const ItemIcon=icons[index]; return <article className={'qv2-card '+(item.on?'is-on':'')} key={item.id}><div><span className="qv2-appliance-icon"><ItemIcon /></span><button onClick={()=>toggleAppliance(item.id)}>{item.on?<ToggleRight/>:<ToggleLeft/>}</button></div><strong>{item.name}</strong><small>{item.status}</small>{item.prog && <div className="qv2-appliance-progress"><i style={{width:`${item.prog}%`}} /></div>}</article>})}</div></section>
    <section className="qv2-section"><div className="qv2-section-head"><div><h2>카메라</h2><p>등록된 공간의 모의 카메라 화면입니다.</p></div></div><article className="qv2-card qv2-camera-card"><div className="qv2-camera-feed"><div><span><i/> LIVE · {QDATA.cameras[cameraIndex].name}</span><time>{new Date().toLocaleTimeString('ko-KR',{hour12:false})}</time></div><Camera/><strong>CAMERA FEED</strong></div><div className="qv2-camera-tabs">{QDATA.cameras.map((camera,index)=><button className={cameraIndex===index?'active':''} onClick={()=>setCameraIndex(index)} key={camera.id}><Camera/><span>{camera.name}</span><i/></button>)}</div></article></section>
  </>;
}

function AgendaPage() {
  const qc = useQueryClient();
  const now = new Date();
  const [month, setMonth] = useState(new Date(now.getFullYear(), now.getMonth(), 1));
  const [selected, setSelected] = useState(now.getDate());
  const [calendarView,setCalendarView]=useState<'day'|'week'|'month'>('month');
  const [idea, setIdea] = useState('');
  const year = month.getFullYear(); const monthIndex = month.getMonth();
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  const first = (new Date(year, monthIndex, 1).getDay() + 6) % 7;
  const dateFrom = `${year}-${String(monthIndex+1).padStart(2,'0')}-01`;
  const dateTo = `${year}-${String(monthIndex+1).padStart(2,'0')}-${String(daysInMonth).padStart(2,'0')}`;
  const selectedDate = `${year}-${String(monthIndex+1).padStart(2,'0')}-${String(selected).padStart(2,'0')}`;
  const { data: events=[] } = useQuery<ApiEvent[]>({queryKey:['events-month',dateFrom],queryFn:()=>axios.get(`/api/agenda/events?date_from=${dateFrom}&date_to=${dateTo}`).then(r=>r.data)});
  const { data: todos=[] } = useQuery<ApiTodo[]>({queryKey:['todos'],queryFn:()=>axios.get('/api/todos').then(r=>r.data)});
  const { data: habits=[] } = useQuery<ApiHabit[]>({queryKey:['habits'],queryFn:()=>axios.get('/api/habits').then(r=>r.data)});
  const { data: ideas=[] } = useQuery<ApiIdea[]>({queryKey:['ideas'],queryFn:()=>axios.get('/api/ideas').then(r=>r.data)});
  const { data: alerts=[] } = useQuery<ApiAlert[]>({queryKey:['alerts'],queryFn:()=>axios.get('/api/alerts').then(r=>r.data),refetchInterval:30_000});
  const createIdea=useMutation({mutationFn:(text:string)=>axios.post('/api/ideas',{text,tag:'아이디어'}),onSuccess:()=>{qc.invalidateQueries({queryKey:['ideas']});setIdea('')}});
  const toggleTodo=useMutation({mutationFn:(id:number)=>axios.patch(`/api/todos/${id}`),onSuccess:()=>qc.invalidateQueries({queryKey:['todos']})});
  const toggleHabit=useMutation({mutationFn:(id:number)=>axios.patch(`/api/habits/${id}/check`),onSuccess:()=>qc.invalidateQueries({queryKey:['habits']})});
  const createTodo=useMutation({mutationFn:(text:string)=>axios.post('/api/todos',{text}),onSuccess:()=>qc.invalidateQueries({queryKey:['todos']})});
  const createEvent=useMutation({mutationFn:(body:{title:string;scheduled_at:string})=>axios.post('/api/agenda/events',body),onSuccess:()=>qc.invalidateQueries({queryKey:['events-month']})});
  const markRead=useMutation({mutationFn:(id:number)=>axios.patch(`/api/alerts/${id}/read`),onSuccess:()=>qc.invalidateQueries({queryKey:['alerts']})});
  const deleteAlert=useMutation({mutationFn:(id:number)=>axios.delete(`/api/alerts/${id}`),onSuccess:()=>qc.invalidateQueries({queryKey:['alerts']})});
  const addIdea=()=>{if(idea.trim())createIdea.mutate(idea.trim())};
  const addTodo=()=>{const text=window.prompt('새 할 일을 입력하세요.');if(text?.trim())createTodo.mutate(text.trim())};
  const addEvent=()=>{const title=window.prompt('일정 제목을 입력하세요.');if(!title?.trim())return;const time=window.prompt('시각을 HH:MM 형식으로 입력하세요.','10:00');if(!time||!/^\d{2}:\d{2}$/.test(time))return;createEvent.mutate({title:title.trim(),scheduled_at:`${selectedDate}T${time}:00+09:00`})};
  const selectedEvents=events.filter(event=>event.scheduled_at.slice(0,10)===selectedDate);
  const cells=[...Array(first).fill(null),...Array.from({length:daysInMonth},(_,i)=>i+1)];
  return <>
    <PageIntro eyebrow="PLANNER" title="일정과 생각" description="오늘의 흐름을 정리하고 떠오른 생각을 놓치지 마세요." action="새 일정" onAction={addEvent} />
    <section className="qv2-agenda-layout">
      <article className="qv2-card qv2-calendar-card"><div className="qv2-calendar-title"><button onClick={()=>{setMonth(new Date(year,monthIndex-1,1));setSelected(1)}}>‹</button><div><strong>{year}년 {monthIndex+1}월</strong><span>이번 달 일정 {events.length}개</span></div><button onClick={()=>{setMonth(new Date(year,monthIndex+1,1));setSelected(1)}}>›</button></div><div className="qv2-view-tabs">{(['day','week','month'] as const).map(view=><button className={calendarView===view?'active':''} key={view} onClick={()=>setCalendarView(view)}>{{day:'일간',week:'주간',month:'월간'}[view]}</button>)}</div>{calendarView==='month'?<><div className="qv2-calendar-week">{['월','화','수','목','금','토','일'].map(d=><span key={d}>{d}</span>)}</div><div className="qv2-calendar-days">{cells.map((day,i)=><button key={i} disabled={!day} className={day===selected?'selected':''} onClick={()=>day&&setSelected(day)}><span>{day}</span>{day&&events.some(event=>Number(event.scheduled_at.slice(8,10))===day)&&<i />}</button>)}</div></>:calendarView==='week'?<div className="qv2-week-view">{Array.from({length:7},(_,i)=>{const day=Math.min(daysInMonth,Math.max(1,selected-((new Date(year,monthIndex,selected).getDay()+6)%7)+i));const date=`${year}-${String(monthIndex+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;return <div key={i} className={day===selected?'today':''}><header><span>{['월','화','수','목','금','토','일'][i]}</span><button onClick={()=>setSelected(day)}>{day}</button></header>{events.filter(event=>event.scheduled_at.slice(0,10)===date).map(event=><article key={event.id}><time>{event.all_day?'종일':event.scheduled_at.slice(11,16)}</time><strong>{event.title}</strong></article>)}</div>})}</div>:<div className="qv2-day-view">{Array.from({length:15},(_,i)=>i+8).map(hour=><div key={hour}><time>{String(hour).padStart(2,'0')}:00</time><span/>{selectedEvents.filter(event=>!event.all_day&&Number(event.scheduled_at.slice(11,13))===hour).map(event=><article key={event.id}><strong>{event.title}</strong><small>{event.scheduled_at.slice(11,16)}</small></article>)}</div>)}</div>}</article>
      <article className="qv2-card qv2-day-plan"><div className="qv2-card-head"><div><span className="qv2-eyebrow">{monthIndex+1}월 {selected}일</span><h3>선택한 날의 일정</h3></div><span className="qv2-count">{selectedEvents.length}</span></div><div className="qv2-plan-list">{selectedEvents.length?selectedEvents.map((item,i)=><div key={item.id}><time>{item.all_day?'종일':item.scheduled_at.slice(11,16)}</time><i className={i===0?'active':''}/><div><strong>{item.title}</strong><small>Google Calendar</small></div></div>):<p className="qv2-empty">등록된 일정이 없습니다.</p>}</div><button className="qv2-add-button" onClick={addEvent}><Plus/>이 날짜에 일정 추가</button></article>
    </section>
    <section className="qv2-agenda-bottom"><article className="qv2-card qv2-idea-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">QUICK CAPTURE</span><h3>아이디어 보관함</h3></div><Sparkles /></div><div className="qv2-idea-input"><input value={idea} onChange={e=>setIdea(e.target.value)} onKeyDown={e=>e.key==='Enter'&&addIdea()} placeholder="떠오른 생각을 바로 기록하세요"/><button disabled={createIdea.isPending} onClick={addIdea}><Plus/></button></div><div className="qv2-idea-list">{ideas.slice(0,4).map(item=><div key={item.id}><span>{item.tag}</span><p>{item.text}</p><small>{new Date(item.created_at).toLocaleDateString('ko-KR')}</small></div>)}</div></article><article className="qv2-card qv2-habit-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">ROUTINE</span><h3>오늘의 습관</h3></div><span className="qv2-progress">{habits.filter(h=>h.done_today).length} / {habits.length}</span></div>{habits.map(item=><button className="qv2-habit-row" key={item.id} onClick={()=>toggleHabit.mutate(item.id)}><span className={item.done_today?'done':''}>{item.done_today&&<Check/>}</span><strong>{item.name}</strong><small>{item.streak}일 연속</small></button>)}</article></section>
    <section className="qv2-agenda-bottom"><article className="qv2-card qv2-habit-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">TASKS</span><h3>오늘의 할 일</h3></div><button className="qv2-text-button" onClick={addTodo}>추가</button></div>{todos.slice(0,5).map(item=><button className="qv2-habit-row" key={item.id} onClick={()=>toggleTodo.mutate(item.id)}><span className={item.done?'done':''}>{item.done&&<Check/>}</span><strong className={item.done?'qv2-strike':''}>{item.text}</strong></button>)}</article><article className="qv2-card qv2-alert-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">NOTIFICATIONS</span><h3>쿼크 자동 알림</h3></div><span className="qv2-count">{alerts.filter(a=>!a.read).length}</span></div>{alerts.slice(0,4).map(item=><div className={'qv2-alert-row '+(item.read?'read':'')} key={item.id}><i className={item.urgent?'urgent':''}/><div><strong>{item.title}</strong><small>{item.body}</small></div>{!item.read&&<button onClick={()=>markRead.mutate(item.id)}>읽음</button>}<button onClick={()=>deleteAlert.mutate(item.id)}><Trash2/></button></div>)}</article></section>
  </>;
}

function MonitorPage() {
  const qc=useQueryClient();
  const {data:system}=useQuery<SystemStats>({queryKey:['system'],queryFn:()=>axios.get('/api/system/stats').then(r=>r.data),refetchInterval:60_000});
  const {data:serviceData}=useQuery<ServiceEntry[]>({queryKey:['services'],queryFn:()=>axios.get('/api/system/services').then(r=>r.data),refetchInterval:10_000});
  const {data:dockerData}=useQuery<DockerEntry[]>({queryKey:['docker'],queryFn:()=>axios.get('/api/system/docker').then(r=>r.data),refetchInterval:60_000});
  const {data:github}=useQuery<GithubData>({queryKey:['github'],queryFn:()=>axios.get('/api/system/github').then(r=>r.data),refetchInterval:3_600_000});
  const {data:embedding}=useQuery<{enabled:boolean}>({queryKey:['embedding-toggle'],queryFn:()=>axios.get('/api/system/embedding-toggle').then(r=>r.data)});
  const {data:usage}=useQuery<{models?:Array<{name:string;prompt_tokens:number;completion_tokens:number;total_tokens:number}>;error?:string}>({queryKey:['openai-usage'],queryFn:()=>axios.get('/api/system/openai-usage').then(r=>r.data),refetchInterval:3_600_000});
  const reboot=useMutation({mutationFn:()=>axios.post('/api/system/reboot')});
  const wake=useMutation({mutationFn:()=>axios.post('/api/system/wake-laptop')});
  const toggleEmbedding=useMutation({mutationFn:(enabled:boolean)=>axios.patch('/api/system/embedding-toggle',{enabled}),onSuccess:()=>qc.invalidateQueries({queryKey:['embedding-toggle']})});
  const s=system??{cpu:QDATA.server.cpu,ram:QDATA.server.ram,disk:QDATA.server.disk,temp:QDATA.server.temp,uptime_days:QDATA.server.uptimeDays};
  const services=serviceData??QDATA.services; const docker=dockerData??QDATA.docker; const gh=github?.error?QDATA.github:(github??QDATA.github);
  const stats = [{name:'CPU',value:s.cpu,unit:'%',icon:Activity},{name:'메모리',value:s.ram,unit:'%',icon:Database},{name:'디스크',value:s.disk,unit:'%',icon:Server},{name:'온도',value:s.temp??0,unit:'°',icon:Thermometer}];
  const totalTokens=usage?.models?.reduce((sum,m)=>sum+m.total_tokens,0)??0;
  return <><PageIntro eyebrow="SYSTEM" title="시스템 모니터링" description="Quark를 구성하는 서비스와 자원을 실시간으로 확인하세요." />
    <section className="qv2-stat-grid">{stats.map(({name,value,unit,icon:StatIcon})=><article className="qv2-card" key={name}><div><span><StatIcon/></span><small>{name}</small></div><strong>{value}<b>{unit}</b></strong><div><i style={{width:`${value}%`}}/></div><p>정상 범위</p></article>)}</section>
    <section className="qv2-monitor-grid"><article className="qv2-card qv2-services"><div className="qv2-card-head"><div><span className="qv2-eyebrow">SERVICES</span><h3>서비스 상태</h3></div><span className="qv2-good"><i/> {services.filter(item=>item.status==='up').length} / {services.length} 정상</span></div>{services.map(item=><div className="qv2-service-row" key={item.name}><i className={item.status}/><div><strong>{item.name}</strong><small>{'uptime' in item?`uptime ${item.uptime}`:'실시간 상태 확인'}</small></div><span>{item.latency||'—'}{item.latency?' ms':''}</span><b className={item.status}>{item.status==='up'?'정상':item.status==='warn'?'지연':'중지'}</b></div>)}</article><article className="qv2-card qv2-docker"><div className="qv2-card-head"><div><span className="qv2-eyebrow">CONTAINERS</span><h3>Docker</h3></div><Database/></div>{docker.map(item=><div key={item.name}><span className={item.status}/><div><strong>{item.name}</strong><small>{item.img}</small></div><p>{item.status==='running'?`${item.cpu}% · ${item.mem} MB`:'stopped'}</p></div>)}</article></section>
    <section className="qv2-card qv2-activity-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">GITHUB</span><h3>개발 활동</h3></div><GitBranch/></div><div className="qv2-github-summary"><div><strong>{gh.streak}</strong><span>일 연속 커밋</span></div><div><strong>{gh.today}</strong><span>오늘</span></div><div><strong>{gh.week}</strong><span>이번 주</span></div><p>마지막 커밋 {gh.lastCommit}</p></div><div className="qv2-commit-grid">{Array.from({length:112},(_,i)=><i key={i} data-level={(i*7+i%5)%5}/>)}</div></section>
    <section className="qv2-monitor-grid"><article className="qv2-card qv2-system-actions"><div className="qv2-card-head"><div><span className="qv2-eyebrow">CONTROL</span><h3>시스템 제어</h3></div><Settings2/></div><button disabled={reboot.isPending} onClick={()=>window.confirm('미니PC를 재부팅할까요? 잠시 접속할 수 없습니다.')&&reboot.mutate()}>{reboot.isPending?'요청 중…':reboot.isSuccess?'재부팅 요청됨':'미니PC 재부팅'}</button><button disabled={wake.isPending} onClick={()=>wake.mutate()}>{wake.isPending?'신호 전송 중…':wake.isSuccess?'깨우기 신호 전송됨':'노트북 켜기 (WoL)'}</button><div className="qv2-embedding"><div><strong>RAG 임베딩</strong><small>대화 기억 저장·검색</small></div><button disabled={toggleEmbedding.isPending} onClick={()=>toggleEmbedding.mutate(!(embedding?.enabled??true))}>{embedding?.enabled??true?<ToggleRight/>:<ToggleLeft/>}</button></div></article><article className="qv2-card qv2-usage-card"><div className="qv2-card-head"><div><span className="qv2-eyebrow">OPENAI</span><h3>API 사용량</h3></div><span className="qv2-count">오늘</span></div><strong>{totalTokens.toLocaleString('ko-KR')}<small> tokens</small></strong>{usage?.models?.map(model=><div key={model.name}><span>{model.name}</span><b>{model.total_tokens.toLocaleString('ko-KR')}</b></div>)}{(!usage?.models||usage.models.length===0)&&<p className="qv2-empty">사용량 데이터를 불러오지 못했습니다.</p>}</article></section>
  </>;
}

function AutomationPage() {
  const qc=useQueryClient();
  const {data:rules=[],isLoading}=useQuery<AutomationApi[]>({queryKey:['automations'],queryFn:()=>axios.get('/api/automations').then(r=>r.data)});
  const toggle=useMutation({mutationFn:(id:number)=>axios.patch(`/api/automations/${id}/toggle`),onSuccess:()=>qc.invalidateQueries({queryKey:['automations']})});
  const remove=useMutation({mutationFn:(id:number)=>axios.delete(`/api/automations/${id}`),onSuccess:()=>qc.invalidateQueries({queryKey:['automations']})});
  const create=useMutation({mutationFn:(body:{name:string;trigger_desc:string;action_desc:string;icon:string})=>axios.post('/api/automations',body),onSuccess:()=>qc.invalidateQueries({queryKey:['automations']})});
  const addRule=()=>{const name=window.prompt('자동화 이름을 입력하세요.');if(!name?.trim())return;const trigger=window.prompt('트리거(IF)를 입력하세요.');if(!trigger?.trim())return;const action=window.prompt('동작(THEN)을 입력하세요.');if(action?.trim())create.mutate({name:name.trim(),trigger_desc:trigger.trim(),action_desc:action.trim(),icon:'zap'})};
  const totalRuns=rules.reduce((sum,rule)=>sum+rule.run_count,0);
  return <><PageIntro eyebrow="WORKFLOWS" title="자동화" description="반복되는 일은 Quark가 알아서 처리하도록 맡겨두세요." action="새 자동화" onAction={addRule} />
    <section className="qv2-auto-summary"><article className="qv2-card"><span><Zap/></span><div><strong>{rules.filter(r=>r.enabled).length}<b> / {rules.length}</b></strong><small>활성 자동화</small></div></article><article className="qv2-card"><span><Play/></span><div><strong>{totalRuns.toLocaleString('ko-KR')}</strong><small>누적 실행</small></div></article><article className="qv2-card"><span><Activity/></span><div><strong>{isLoading?'—':'LIVE'}</strong><small>API 연결 상태</small></div></article></section>
    <section className="qv2-rule-grid">{rules.map((rule,index)=><article className={'qv2-card qv2-rule '+(rule.enabled?'enabled':'')} key={rule.id}><div className="qv2-rule-head"><span>{index%2?<Moon/>:<Zap/>}</span><div><strong>{rule.name}</strong><small>{rule.run_count}회 실행됨</small></div><button aria-label="삭제" onClick={()=>window.confirm(`'${rule.name}' 자동화를 삭제할까요?`)&&remove.mutate(rule.id)}><Trash2/></button><button disabled={toggle.isPending} onClick={()=>toggle.mutate(rule.id)}>{rule.enabled?<ToggleRight/>:<ToggleLeft/>}</button></div><div className="qv2-flow"><div><span>IF</span><p>{rule.trigger_desc}</p></div><b>→</b><div><span>THEN</span><p>{rule.action_desc}</p></div></div><footer><i className={rule.enabled?'on':''}/>{rule.enabled?'활성':'일시 정지'}<span>실행 {rule.run_count}회</span></footer></article>)}</section>
  </>;
}

function ResearchPage() {
  const qc=useQueryClient(); const [keyword,setKeyword]=useState('');
  const {data:papers=[],isLoading}=useQuery<ResearchNote[]>({queryKey:['research'],queryFn:()=>axios.get('/api/research').then(r=>r.data)});
  const run=useMutation({mutationFn:(keyword:string)=>axios.post<{keywords:string[];fetched:number;saved:number}>('/api/research/run',keyword?{keyword}:{}).then(r=>r.data),onSuccess:()=>qc.invalidateQueries({queryKey:['research']})});
  return <><PageIntro eyebrow="KNOWLEDGE" title="연구 아카이브" description="관심 분야의 최신 논문을 찾고, Quark의 요약과 함께 보관하세요." />
    <section className="qv2-research-run"><div><span><Sparkles/></span><div><strong>새로운 연구를 찾아볼까요?</strong><p>Arxiv에서 논문을 검색하고 한국어로 핵심을 요약합니다.</p></div></div><label><Search/><input value={keyword} onChange={e=>setKeyword(e.target.value)} onKeyDown={e=>e.key==='Enter'&&!run.isPending&&run.mutate(keyword.trim())} placeholder="키워드 입력 (예: edge AI)"/><button disabled={run.isPending} onClick={()=>run.mutate(keyword.trim())}>{run.isPending?'조사 중...':'지금 조사하기'}</button></label></section>
    {run.data&&<div className="qv2-run-result">[{run.data.keywords.join(', ')}] {run.data.fetched}건 확인 · 새 논문 {run.data.saved}건 저장</div>}
    <section className="qv2-library-head"><div><h2>저장된 논문</h2><p>{isLoading?'불러오는 중':`${papers.length}개의 연구 자료`}</p></div></section><section className="qv2-paper-grid">{papers.map(paper=><article className="qv2-card" key={paper.id}><div><span>{paper.keyword}</span><a href={paper.url} target="_blank" rel="noreferrer" aria-label="논문 열기"><ExternalLink/></a></div><h3>{paper.title}</h3><small>{paper.authors} · {new Date(paper.created_at).getFullYear()}</small><p>{paper.summary_ko}</p><footer><span>인용 {paper.citation_count}</span><span>{paper.arxiv_id}</span></footer></article>)}</section>
  </>;
}

function SecondaryPage({ page }: { page: string }) {
  if (page === '스마트 홈') return <SmartHomePage />;
  if (page === '일정') return <AgendaPage />;
  if (page === '모니터링') return <MonitorPage />;
  if (page === '자동화') return <AutomationPage />;
  return <ResearchPage />;
}

function HomeUtilities({config}:{config:PreviewWidgetConfig}) {
  const qc=useQueryClient();
  const [memo,setMemo]=useState('');
  const [seconds,setSeconds]=useState(25*60);
  const [running,setRunning]=useState(false);
  const {data:memoData}=useQuery<{id:number;content:string}>({queryKey:['memo'],queryFn:()=>axios.get('/api/memo').then(r=>r.data)});
  const {data:water}=useQuery<{total_ml:number;goal_ml:number;pct:number}>({queryKey:['water'],queryFn:()=>axios.get('/api/water/today').then(r=>r.data)});
  const {data:ddays=[]}=useQuery<Array<{id:number;label:string;target_date:string;days:number}>>({queryKey:['dday'],queryFn:()=>axios.get('/api/dday').then(r=>r.data)});
  const {data:market}=useQuery<{crypto?:Array<{sym:string;name:string;price:number;chg:number}>;fx?:Array<{sym:string;name:string;price:number;chg:number}>}>({queryKey:['market'],queryFn:()=>axios.get('/api/system/market').then(r=>r.data),staleTime:600_000});
  const saveMemo=useMutation({mutationFn:(content:string)=>axios.put('/api/memo',{content})});
  const addWater=useMutation({mutationFn:()=>axios.post('/api/water/today'),onSuccess:()=>qc.invalidateQueries({queryKey:['water']})});
  useEffect(()=>{if(memoData)setMemo(memoData.content)},[memoData]);
  useEffect(()=>{if(!running)return;const timer=window.setInterval(()=>setSeconds(value=>{if(value<=1){setRunning(false);return 25*60}return value-1}),1000);return()=>window.clearInterval(timer)},[running]);
  const mins=String(Math.floor(seconds/60)).padStart(2,'0'); const secs=String(seconds%60).padStart(2,'0');
  const marketRows=[...(market?.crypto??QDATA.crypto).slice(0,2),...(market?.fx??QDATA.fx).slice(0,1)];
  return <section className="qv2-utility-grid">
    <article style={{display:config.active.includes('memo')?'block':'none',order:config.active.indexOf('memo')}} className={'qv2-card qv2-memo-card '+(config.sizes.memo===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">MEMO</span><h3>빠른 메모</h3></div><span>{memo.length}자</span></div><textarea value={memo} onChange={e=>setMemo(e.target.value)} onBlur={()=>saveMemo.mutate(memo)} placeholder="생각나는 것을 적어두세요."/><small>{saveMemo.isPending?'저장 중…':saveMemo.isSuccess?'저장됨':'입력 후 자동 저장'}</small></article>
    <article style={{display:config.active.includes('water')?'block':'none',order:config.active.indexOf('water')}} className={'qv2-card qv2-water-card '+(config.sizes.water===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">HYDRATION</span><h3>수분 섭취</h3></div><Droplets/></div><strong>{(water?.total_ml??0).toLocaleString()}<small> / {water?.goal_ml??2000} ml</small></strong><div><i style={{width:`${water?.pct??0}%`}}/></div><button disabled={addWater.isPending} onClick={()=>addWater.mutate()}><Plus/>250ml 기록</button></article>
    <article style={{display:config.active.includes('pomodoro')?'block':'none',order:config.active.indexOf('pomodoro')}} className={'qv2-card qv2-timer-card '+(config.sizes.pomodoro===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">FOCUS</span><h3>포모도로</h3></div><TimerReset/></div><strong>{mins}:{secs}</strong><div><button onClick={()=>setRunning(value=>!value)}>{running?'일시정지':'시작'}</button><button onClick={()=>{setRunning(false);setSeconds(25*60)}}>초기화</button></div></article>
    <article style={{display:config.active.includes('dday')?'block':'none',order:config.active.indexOf('dday')}} className={'qv2-card qv2-small-list '+(config.sizes.dday===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">D-DAY</span><h3>다가오는 목표</h3></div><CalendarDays/></div>{ddays.slice(0,3).map(item=><div key={item.id}><span>{item.label}</span><strong>D{item.days>=0?'-':'+'}{Math.abs(item.days)}</strong></div>)}</article>
    <article style={{display:config.active.includes('market')?'block':'none',order:config.active.indexOf('market')}} className={'qv2-card qv2-small-list '+(config.sizes.market===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">MARKET</span><h3>시세</h3></div><Activity/></div>{marketRows.map(item=><div key={item.sym}><span>{item.sym}</span><strong>{item.price.toLocaleString('ko-KR')} <small className={item.chg>=0?'up':'down'}>{item.chg>0?'+':''}{item.chg}%</small></strong></div>)}</article>
  </section>;
}

function HomeExtras({config}:{config:PreviewWidgetConfig}) {
  const qc=useQueryClient();
  const [moodPick,setMoodPick]=useState(false);
  const {data:forecast}=useQuery<ForecastData>({queryKey:['forecast'],queryFn:()=>axios.get('/api/system/forecast').then(r=>r.data),staleTime:600_000});
  const {data:news=[]}=useQuery<NewsData[]>({queryKey:['news'],queryFn:()=>axios.get('/api/system/news').then(r=>r.data),staleTime:1_800_000});
  const {data:mood}=useQuery<MoodData|null>({queryKey:['mood-today'],queryFn:()=>axios.get('/api/mood').then(r=>r.data)});
  const {data:sleep}=useQuery<SleepData|null>({queryKey:['sleep-today'],queryFn:()=>axios.get('/api/sleep').then(r=>r.data)});
  const {data:sleepWeek=[]}=useQuery<SleepData[]>({queryKey:['sleep-week'],queryFn:()=>axios.get('/api/sleep/week').then(r=>r.data)});
  const {data:caffeine}=useQuery<CaffeineData>({queryKey:['caffeine-today'],queryFn:()=>axios.get('/api/caffeine').then(r=>r.data)});
  const logMood=useMutation({mutationFn:(score:number)=>axios.post('/api/mood',{score}),onSuccess:()=>{qc.invalidateQueries({queryKey:['mood-today']});setMoodPick(false)}});
  const logSleep=useMutation({mutationFn:(body:{hours:number;quality:number})=>axios.post('/api/sleep',body),onSuccess:()=>{qc.invalidateQueries({queryKey:['sleep-today']});qc.invalidateQueries({queryKey:['sleep-week']})}});
  const addCaffeine=useMutation({mutationFn:()=>axios.post('/api/caffeine'),onSuccess:()=>qc.invalidateQueries({queryKey:['caffeine-today']})});
  const scoreEmoji=(score?:number)=>['','😞','😤','😐','🙂','😎'][score??0]||'·';
  const weatherIcon=(icon:string)=>icon==='sun'?<Sun/>:icon==='rain'?<CloudRain/>:icon==='snow'?<Snowflake/>:icon==='storm'?<CloudLightning/>:<Cloud/>;
  const addSleep=()=>{const hours=Number(window.prompt('수면 시간을 입력하세요.','7.5'));if(!Number.isFinite(hours)||hours<=0)return;const quality=Number(window.prompt('수면 품질을 1~5로 입력하세요.','4'));if(quality>=1&&quality<=5)logSleep.mutate({hours,quality})};
  const clocks=QDATA.clocks.map(city=>{const time=new Date(Date.now()+city.tz*3_600_000);return{...city,time:`${String(time.getUTCHours()).padStart(2,'0')}:${String(time.getUTCMinutes()).padStart(2,'0')}`}});
  return <section className="qv2-extra-grid">
    <article style={{display:config.active.includes('weather')?'block':'none',order:config.active.indexOf('weather')}} className={'qv2-card qv2-forecast-card '+(config.sizes.weather===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">FORECAST</span><h3>날씨 예보</h3></div><CloudRain/></div><div className="qv2-forecast-row">{(forecast?.forecast??QDATA.forecast).slice(0,6).map((day,i)=><div className={i===0?'today':''} data-weather={day.ico} key={day.d}><span>{day.d}</span>{weatherIcon(day.ico)}<b>{day.hi}°</b><small>{day.lo}° · {day.pop}%</small></div>)}</div><footer><div><Sunrise/><span>일출 <b>{forecast?.sunrise??QDATA.sun.rise}</b></span></div><div><Moon/><span>일몰 <b>{forecast?.sunset??QDATA.sun.set}</b></span></div><small>{forecast?.day_len??QDATA.sun.dayLen}</small></footer></article>
    <article style={{display:config.active.includes('news')?'block':'none',order:config.active.indexOf('news')}} className={'qv2-card qv2-news-card '+(config.sizes.news===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">NEWS</span><h3>관심 뉴스</h3></div><Newspaper/></div>{(news.length?news:QDATA.news).slice(0,5).map((item,i)=><a href={'url' in item?item.url:undefined} target="_blank" rel="noreferrer" key={i}><span>{item.tag}</span><div><strong>{item.title}</strong><small>{item.src} · {item.time}</small></div></a>)}</article>
    <article style={{display:config.active.includes('mood')?'block':'none',order:config.active.indexOf('mood')}} className={'qv2-card qv2-health-card '+(config.sizes.mood===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">MOOD</span><h3>오늘 기분</h3></div><Smile/></div><div className="qv2-current-mood">{scoreEmoji(mood?.score)}</div>{moodPick?<div className="qv2-mood-pick">{[1,2,3,4,5].map(score=><button key={score} onClick={()=>logMood.mutate(score)}>{scoreEmoji(score)}</button>)}</div>:<button onClick={()=>setMoodPick(true)}>{mood?'기분 바꾸기':'기분 기록하기'}</button>}</article>
    <article style={{display:config.active.includes('sleep')?'block':'none',order:config.active.indexOf('sleep')}} className={'qv2-card qv2-health-card '+(config.sizes.sleep===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">SLEEP</span><h3>수면 기록</h3></div><BedDouble/></div><div className="qv2-sleep-value"><strong>{sleep?.hours??0}</strong><span>시간</span></div><div className="qv2-sleep-bars">{Array.from({length:7},(_,i)=>{const entry=sleepWeek[i];return <i key={i} style={{height:`${Math.min(100,(entry?.hours??0)/9*100)}%`}}/>})}</div><button onClick={addSleep}>{sleep?'오늘 기록 수정':'수면 기록하기'}</button></article>
    <article style={{display:config.active.includes('caffeine')?'block':'none',order:config.active.indexOf('caffeine')}} className={'qv2-card qv2-health-card '+(config.sizes.caffeine===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">CAFFEINE</span><h3>카페인</h3></div><Coffee/></div><div className="qv2-sleep-value"><strong>{caffeine?.cups_today??0}</strong><span>잔 · {caffeine?.mg_today??0}mg</span></div><p>컷오프 {caffeine?.cutoff??QDATA.caffeine.cutoff}<br/>마지막 {caffeine?.last_cup??'기록 없음'}</p><button disabled={addCaffeine.isPending} onClick={()=>addCaffeine.mutate()}><Plus/> 커피 한 잔 기록</button></article>
    <article style={{display:config.active.includes('worldclock')?'block':'none',order:config.active.indexOf('worldclock')}} className={'qv2-card qv2-clock-card '+(config.sizes.worldclock===2?'wide':'')}><div className="qv2-card-head"><div><span className="qv2-eyebrow">WORLD</span><h3>세계 시계</h3></div><Clock3/></div>{clocks.map(city=><div key={city.city}><span>{city.flag} · {city.city}</span><strong>{city.time}</strong></div>)}</article>
  </section>;
}

export default function QuarkPreview() {
  const [activeNav, setActiveNav] = useState(pageFromPath);
  const [menuOpen, setMenuOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [showChatHistory,setShowChatHistory]=useState(false);
  const [widgetEdit,setWidgetEdit]=useState(false);
  const [widgetConfig,setWidgetConfig]=useState<PreviewWidgetConfig>(loadPreviewWidgets);
  const [dragWidget,setDragWidget]=useState<string|null>(null);
  const [now, setNow] = useState(() => new Date());
  const [showInstallHint, setShowInstallHint] = useState(false);
  const qc=useQueryClient();
  const mqttConnected=useMqttConnected();
  const activeScene=useHomeStore((s)=>s.scene);
  const applyScene=useHomeStore((s)=>s.applyScene);
  const appliances=useHomeStore((s)=>s.appliances);
  const toggleAppliance=useHomeStore((s)=>s.toggleAppliance);
  const handleCommand=useHomeStore((s)=>s.handleCommand);
  const {messages,streaming,error,send:sendChat}=useQuarkChat();
  const todayStr=useMemo(()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`},[]);
  const {data:weather}=useQuery<{temp:number;label:string;pm25:number;aqi_grade:string;error?:string}>({queryKey:['weather'],queryFn:()=>axios.get('/api/system/weather').then(r=>r.data),staleTime:600_000});
  const {data:todayEvents=[]}=useQuery<ApiEvent[]>({queryKey:['events',todayStr],queryFn:()=>axios.get(`/api/agenda/events?date_filter=${todayStr}`).then(r=>r.data),refetchInterval:30_000});
  const {data:homeTodos=[]}=useQuery<ApiTodo[]>({queryKey:['todos'],queryFn:()=>axios.get('/api/todos').then(r=>r.data)});
  const toggleHomeTodo=useMutation({mutationFn:(id:number)=>axios.patch(`/api/todos/${id}`),onSuccess:()=>qc.invalidateQueries({queryKey:['todos']})});
  const createHomeTodo=useMutation({mutationFn:(text:string)=>axios.post('/api/todos',{text}),onSuccess:()=>qc.invalidateQueries({queryKey:['todos']})});

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    const onPopState = () => setActiveNav(pageFromPath());
    window.addEventListener('popstate', onPopState);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('popstate', onPopState);
    };
  }, []);

  useEffect(() => {
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const dismissed = localStorage.getItem('quark-install-hint-dismissed') === '1';
    setShowInstallHint(isIOS && !isStandalone && !dismissed);
  }, []);

  const dismissInstallHint = () => {
    localStorage.setItem('quark-install-hint-dismissed', '1');
    setShowInstallHint(false);
  };

  const navigate = (label: string, path: string) => {
    window.history.pushState({}, '', `/${path}`);
    setActiveNav(label);
    setMenuOpen(false);
  };

  const dateLabel = useMemo(
    () => new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' }).format(now),
    [now],
  );

  const sendMessage = (preset?: string) => {
    const trimmed = (preset??message).trim();
    if (!trimmed||streaming) return;
    handleCommand(trimmed);
    void sendChat(trimmed);
    setMessage('');
  };

  const latestAssistant=[...messages].reverse().find(item=>item.role==='assistant'&&item.content)?.content;
  const saveWidgets=(next:PreviewWidgetConfig)=>{const saved={...next,previewVersion:2};setWidgetConfig(saved);localStorage.setItem('quark-dash-v2',JSON.stringify(saved))};
  const toggleWidget=(id:string)=>saveWidgets({...widgetConfig,active:widgetConfig.active.includes(id)?widgetConfig.active.filter(item=>item!==id):[...widgetConfig.active,id]});
  const dropWidget=(target:string)=>{if(!dragWidget||dragWidget===target)return;const active=widgetConfig.active.slice();const from=active.indexOf(dragWidget);const to=active.indexOf(target);if(from<0||to<0)return;active.splice(from,1);active.splice(to,0,dragWidget);saveWidgets({...widgetConfig,active});setDragWidget(null)};

  return (
    <div className="qv2-shell">
      {showInstallHint && (
        <div className="qv2-install-hint">
          <span>iPhone에서 앱처럼 쓰려면 Safari 공유 버튼 <ExternalLink /> → "홈 화면에 추가"를 눌러보세요.</span>
          <button onClick={dismissInstallHint} aria-label="안내 닫기"><X /></button>
        </div>
      )}
      <aside className={'qv2-sidebar' + (menuOpen ? ' is-open' : '')}>
        <div className="qv2-brand">
          <div className="qv2-logo"><img src={mascot} alt="Quark" /></div>
          <div><strong>Quark</strong><span>Personal OS</span></div>
          <button className="qv2-mobile-close" onClick={() => setMenuOpen(false)} aria-label="메뉴 닫기"><X /></button>
        </div>
        <nav className="qv2-nav" aria-label="주 메뉴">
          <p>WORKSPACE</p>
          {navItems.map(({ label, path, icon: NavIcon }) => (
            <button key={label} className={activeNav === label ? 'active' : ''} onClick={() => navigate(label, path)}>
              <NavIcon /><span>{label}</span>{label === '홈' && <i>4</i>}
            </button>
          ))}
        </nav>
        <div className="qv2-side-bottom">
          <div className="qv2-system-mini">
            <div><span className="qv2-live-dot" /><strong>모든 시스템 정상</strong></div>
            <span>마지막 확인 방금 전</span>
          </div>
          <button><Settings2 /><span>설정</span></button>
          <div className="qv2-user"><CircleUserRound /><div><strong>쿼딩</strong><span>관리자</span></div><MoreHorizontal /></div>
        </div>
      </aside>

      {menuOpen && <button className="qv2-scrim" onClick={() => setMenuOpen(false)} aria-label="메뉴 닫기" />}

      <main className="qv2-main">
        <header className="qv2-topbar">
          <button className="qv2-menu" onClick={() => setMenuOpen(true)} aria-label="메뉴 열기"><Menu /></button>
          <label className="qv2-search"><Search /><input placeholder="무엇이든 검색하세요" /><kbd>⌘ K</kbd></label>
          <div className="qv2-top-actions">
            <span className="qv2-weather"><CloudSun /> 서울 {weather?.error?QDATA.weather.temp:(weather?.temp??QDATA.weather.temp)}°</span>
            <button aria-label={mqttConnected?'MQTT 연결됨':'MQTT 연결 끊김'}><Bell /><i style={{background:mqttConnected?'#55a477':'#b86555'}} /></button>
            <button aria-label="도움말"><MessageCircle /></button>
          </div>
        </header>

        <div className="qv2-content">
          {activeNav === '홈' ? <>
          <section className="qv2-welcome">
            <div><span>{dateLabel}</span><h1>좋은 오후예요, 쿼딩님.</h1><p>오늘도 필요한 것만 간결하게 준비해뒀어요.</p></div>
            <button className="qv2-customize" onClick={()=>setWidgetEdit(value=>!value)}>{widgetEdit?'완료':'편집'}</button>
          </section>

          {widgetEdit&&<section className="qv2-widget-editor"><header><div><strong>위젯 편집</strong><span>끌어서 순서를 바꾸고 표시 여부와 크기를 선택하세요.</span></div><button onClick={()=>saveWidgets({active:PREVIEW_DEFAULT.slice(),sizes:{}})}>기본값</button></header><div>{PREVIEW_WIDGETS.map(([id,label])=><article draggable={widgetConfig.active.includes(id)} onDragStart={()=>setDragWidget(id)} onDragOver={e=>e.preventDefault()} onDrop={()=>dropWidget(id)} key={id}><span className="qv2-drag">⠿</span><strong>{label}</strong><button onClick={()=>saveWidgets({...widgetConfig,sizes:{...widgetConfig.sizes,[id]:widgetConfig.sizes[id]===2?1:2}})}>{widgetConfig.sizes[id]===2?'넓게':'보통'}</button><button className={widgetConfig.active.includes(id)?'active':''} onClick={()=>toggleWidget(id)}>{widgetConfig.active.includes(id)?'표시':'숨김'}</button></article>)}</div></section>}

          <section className="qv2-summary-grid">
            <article className="qv2-hero-card">
              <div className="qv2-hero-top"><button onClick={()=>setShowChatHistory(value=>!value)}>{showChatHistory?'요약 보기':'대화 펼치기'}</button><span><i /> QUARK ONLINE</span></div>
              <h2>무엇을 도와드릴까요?</h2>
              {showChatHistory?<div className="qv2-chat-history">{messages.length?messages.map(item=><div className={item.role} key={item.id}><span>{item.role==='user'?'나':'Quark'}</span><p>{item.content||'생각 중…'}</p></div>):<p>아직 대화가 없습니다.</p>}</div>:<p>{error?`연결 오류: ${error}`:latestAssistant??'오늘 필요한 일을 알려주세요. 집 제어부터 일정 정리까지 함께할게요.'}</p>}
              <div className="qv2-command-box">
                <Bot />
                <input value={message} disabled={streaming} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendMessage()} placeholder={streaming?'쿼크가 생각 중이에요...':'쿼크에게 메시지 보내기...'} />
                <button aria-label="음성 입력"><Mic /></button>
                <button className="send" onClick={() => sendMessage()} aria-label="보내기"><Send /></button>
              </div>
              <div className="qv2-suggestions"><button disabled={streaming} onClick={() => sendMessage('쿼크, 집 상태 알려줘')}><Command /> 집 상태 알려줘</button><button disabled={streaming} onClick={() => sendMessage('쿼크, 오늘 일정 요약해줘')}><CalendarDays /> 오늘 일정 요약</button></div>
            </article>

            <article className="qv2-card qv2-status-card">
              <div className="qv2-card-head"><div><span className="qv2-eyebrow">SYSTEM</span><h3>홈 상태</h3></div><button><MoreHorizontal /></button></div>
              <div className="qv2-home-score"><div><ShieldCheck /><span>안전</span></div><strong>모두 평온해요</strong><p>문과 창문이 잠겨 있습니다</p></div>
              <div className="qv2-sensors">
                <div><Thermometer /><span>실내 온도</span><strong>24.2°</strong></div>
                <div><Droplets /><span>습도</span><strong>48%</strong></div>
                <div><Network /><span>연결 기기</span><strong>12</strong></div>
              </div>
            </article>
          </section>

          <section className="qv2-section">
            <div className="qv2-section-head"><div><h2>빠른 실행</h2><p>자주 사용하는 장면을 한 번에 실행하세요.</p></div><button>장면 관리 <ChevronDown /></button></div>
            <div className="qv2-scenes">
              {scenes.map(({ id,label, icon: SceneIcon, tint }) => <button key={id} className={(activeScene === id ? 'active ' : '') + tint} onClick={() => applyScene(id)}><span><SceneIcon /></span><div><strong>{label} 모드</strong><small>{activeScene === id ? '현재 실행 중' : '탭하여 실행'}</small></div>{activeScene === id && <Check />}</button>)}
              <button className="qv2-add-scene" onClick={()=>navigate('스마트 홈','iot')}><Plus /><span>장면 관리</span></button>
            </div>
          </section>

          <section className="qv2-bottom-grid">
            <article className="qv2-card qv2-devices">
              <div className="qv2-card-head"><div><span className="qv2-eyebrow">DEVICES</span><h3>자주 쓰는 기기</h3></div><button className="qv2-text-button" onClick={()=>navigate('스마트 홈','iot')}>전체 보기</button></div>
              <div className="qv2-device-list">
                {appliances.slice(0,3).map((device,index) => { const icons=[WashingMachine,AirVent,Sparkles]; const DeviceIcon = icons[index]; return <button key={device.id} className={device.on ? 'is-on' : ''} onClick={() => toggleAppliance(device.id)}><span className="qv2-device-icon"><DeviceIcon /></span><span className="qv2-device-copy"><strong>{device.name}</strong><small>{device.status}</small></span><span className="qv2-toggle">{device.on ? <ToggleRight /> : <ToggleLeft />}</span></button>; })}
              </div>
            </article>

            <article className="qv2-card qv2-agenda">
              <div className="qv2-card-head"><div><span className="qv2-eyebrow">TODAY</span><h3>다가오는 일정</h3></div><button className="qv2-date-button">8월 26일</button></div>
              <div className="qv2-timeline">
                {todayEvents.slice(0,3).map((item, index) => <div key={item.id}><time>{item.all_day?'종일':item.scheduled_at.slice(11,16)}</time><span className={index === 0 ? 'hot' : ''} /><div><strong>{item.title}</strong><small>Google Calendar</small></div></div>)}
              </div>
              <button className="qv2-add-button" onClick={()=>navigate('일정','agenda')}><Plus /> 일정 관리</button>
            </article>

            <article className="qv2-card qv2-tasks">
              <div className="qv2-card-head"><div><span className="qv2-eyebrow">FOCUS</span><h3>오늘의 할 일</h3></div><span className="qv2-progress">{homeTodos.filter(todo=>todo.done).length} / {homeTodos.length}</span></div>
              <div className="qv2-progress-bar"><i style={{width:`${homeTodos.length?homeTodos.filter(todo=>todo.done).length/homeTodos.length*100:0}%`}} /></div>
              <div className="qv2-task-list">
                {homeTodos.slice(0,3).map(todo => <button key={todo.id} className={todo.done ? 'done' : ''} onClick={() => toggleHomeTodo.mutate(todo.id)}><span>{todo.done && <Check />}</span><strong>{todo.text}</strong></button>)}
              </div>
              <button className="qv2-add-button" onClick={()=>{const text=window.prompt('새 할 일을 입력하세요.');if(text?.trim())createHomeTodo.mutate(text.trim())}}><Plus /> 할 일 추가</button>
            </article>
          </section>
          <HomeUtilities config={widgetConfig} />
          <HomeExtras config={widgetConfig} />
          </> : <SecondaryPage page={activeNav} />}
        </div>
      </main>
    </div>
  );
}
