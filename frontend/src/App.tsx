/* QUARK — 앱 셸: 사이드바 + 상단바 + 5개 라우트 */
import { useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import Dashboard from '@/pages/Dashboard';
import IotScreen from '@/pages/IotScreen';
import AgendaScreen from '@/pages/AgendaScreen';
import MonitorScreen from '@/pages/MonitorScreen';
import AutomationScreen from '@/pages/AutomationScreen';
import ResearchScreen from '@/pages/ResearchScreen';
import QuarkPreview from '@/pages/QuarkPreview';
import { useMqtt } from '@/hooks/useMqtt';

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  useMqtt();
  if (window.location.pathname.startsWith('/legacy')) {
    return (
      <div className={'app' + (collapsed ? ' collapsed' : '')}>
        <Sidebar onToggle={() => setCollapsed((c) => !c)} />
        <div className="main">
          <TopBar />
          <Routes>
            <Route path="/legacy" element={<Dashboard />} />
            <Route path="/legacy/iot" element={<IotScreen />} />
            <Route path="/legacy/agenda" element={<AgendaScreen />} />
            <Route path="/legacy/monitor" element={<MonitorScreen />} />
            <Route path="/legacy/automation" element={<AutomationScreen />} />
            <Route path="/legacy/research" element={<ResearchScreen />} />
          </Routes>
        </div>
      </div>
    );
  }
  return <QuarkPreview />;
}
