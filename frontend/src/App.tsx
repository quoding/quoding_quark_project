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
import { useMqtt } from '@/hooks/useMqtt';

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  useMqtt();
  return (
    <div className={'app' + (collapsed ? ' collapsed' : '')}>
      <Sidebar onToggle={() => setCollapsed((c) => !c)} />
      <div className="main">
        <TopBar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/iot" element={<IotScreen />} />
          <Route path="/agenda" element={<AgendaScreen />} />
          <Route path="/monitor" element={<MonitorScreen />} />
          <Route path="/automation" element={<AutomationScreen />} />
        </Routes>
      </div>
    </div>
  );
}
