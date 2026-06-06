/* QUARK — 상단바 (인사말 + 날씨/미세먼지/서버/시계 칩) */
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Icon } from '@/components/Icon';
import { useClock } from '@/hooks/useClock';
import { QDATA } from '@/data/quarkData';
import { useMqttConnected } from '@/lib/mqttSingleton';

const DAYS = ['일', '월', '화', '수', '목', '금', '토'];
const pad = (n: number) => String(n).padStart(2, '0');

interface WeatherData {
  temp: number;
  label: string;
  hi: number;
  lo: number;
  pm25: number;
  aqi_grade: string;
  error?: string;
}

export function TopBar() {
  const now = useClock();
  const mqttConnected = useMqttConnected();
  const h = now.getHours();
  const greet = h < 6 ? '늦은 밤이야' : h < 12 ? '좋은 아침이야' : h < 18 ? '좋은 오후야' : '좋은 저녁이야';
  const s = QDATA.server;

  const { data: weather } = useQuery<WeatherData>({
    queryKey: ['weather'],
    queryFn: () => axios.get<WeatherData>('/api/system/weather').then((r) => r.data),
    staleTime: 10 * 60 * 1000, // 10분
    retry: 1,
  });

  const temp = weather && !weather.error ? weather.temp : QDATA.weather.temp;
  const label = weather && !weather.error ? weather.label : QDATA.weather.label;
  const pm25 = weather && !weather.error ? weather.pm25 : QDATA.aqi.pm25;
  const aqiGrade = weather && !weather.error ? weather.aqi_grade : QDATA.aqi.grade;

  return (
    <div className="topbar">
      <div className="tb-greet">
        <div className="tb-hello">
          {greet}, <b>{QDATA.user}</b> 🦫
        </div>
        <div className="tb-sub">
          쿼크가 집 안 모든 걸 지켜보고 있어 · <span className="mono">서버 {s.uptimeDays}일째 무중단</span>
        </div>
      </div>
      <div className="tb-chips">
        <div
          className="chip"
          title={mqttConnected ? 'MQTT 연결됨' : 'MQTT 연결 끊김'}
          style={{ gap: 6 }}
        >
          <span
            style={{
              display: 'inline-block',
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: mqttConnected ? '#22c55e' : '#ef4444',
              flexShrink: 0,
            }}
          />
          <span className="lbl">MQTT</span>
        </div>
        <div className="chip">
          <span className="ic">
            <Icon name="sun" />
          </span>
          <span className="v">{temp}°</span>
          <span className="lbl">
            {label} · {QDATA.weather.city}
          </span>
        </div>
        <div className="chip chip-aqi">
          <span className="ic">
            <Icon name="wind" />
          </span>
          <span className="v">{pm25}</span>
          <span className="lbl">초미세 · {aqiGrade}</span>
        </div>
        <div className="chip" title="미니PC 서버 상태">
          <span className="ic">
            <Icon name="cpu" />
          </span>
          <div className="row" style={{ gap: 10 }}>
            <span>
              <span className="v" style={{ fontSize: 12 }}>
                {s.cpu}%
              </span>
              <span className="u"> CPU</span>
            </span>
            <span>
              <span className="v" style={{ fontSize: 12 }}>
                {s.ram}%
              </span>
              <span className="u"> RAM</span>
            </span>
            <span>
              <span className="v" style={{ fontSize: 12 }}>
                {s.temp}°
              </span>
              <span className="u"> TEMP</span>
            </span>
          </div>
        </div>
        <div className="chip chip-time">
          <span className="ic tb-clock">
            <Icon name="clock" />
          </span>
          <span className="v">
            {pad(now.getHours())}:{pad(now.getMinutes())}
            <span style={{ color: 'var(--tx-mid)', fontSize: 12 }}>:{pad(now.getSeconds())}</span>
          </span>
          <span className="lbl">
            {now.getMonth() + 1}/{now.getDate()}({DAYS[now.getDay()]})
          </span>
        </div>
      </div>
    </div>
  );
}
