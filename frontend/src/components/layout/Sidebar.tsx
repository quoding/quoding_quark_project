/* QUARK — 사이드바 네비게이션 (5개 라우트). 활성 항목 좌측 블루바 + wash 배경. */
import { NavLink } from 'react-router-dom';
import { Icon, type IconName } from '@/components/Icon';
import mascot from '@/assets/quark-mascot.png';

interface NavEntry {
  to: string;
  name: string;
  ico: IconName;
  badge?: string;
}

const NAV: NavEntry[] = [
  { to: '/', name: '대시보드', ico: 'dashboard', badge: 'HOME' },
  { to: '/iot', name: '집 제어', ico: 'home' },
  { to: '/agenda', name: '일정 & 비서', ico: 'calendar' },
  { to: '/monitor', name: '모니터링', ico: 'monitor' },
  { to: '/automation', name: '자동화', ico: 'automation' },
  { to: '/research', name: '연구 아카이브', ico: 'news' },
];

interface SidebarProps {
  onToggle: () => void;
}

export function Sidebar({ onToggle }: SidebarProps) {
  return (
    <nav className="nav">
      <div className="brand">
        <div className="brand-mark">
          <img className="pixelated" src={mascot} alt="쿼크" />
        </div>
        <div className="brand-txt">
          <div className="brand-word">
            QUAR<b>K</b>
          </div>
          <div className="brand-state">
            <span className="dot" />
            쿼크 · 대기 중
          </div>
        </div>
      </div>
      <div className="nav-sec">CONTROL</div>
      <div className="nav-items">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            className={({ isActive }) => 'nav-item' + (isActive ? ' on' : '')}
          >
            <span className="nav-ico">
              <Icon name={n.ico} />
            </span>
            <span>{n.name}</span>
            {n.badge && <span className="nav-badge">{n.badge}</span>}
          </NavLink>
        ))}
      </div>
      <div className="nav-foot">
        <button className="nav-collapse" onClick={onToggle}>
          <Icon name="chevron" />
          <span>접기</span>
        </button>
      </div>
    </nav>
  );
}
