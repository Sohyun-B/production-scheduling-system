import React, { useState } from 'react';
import Dashboard from './Dashboard';
import OrderTable from './OrderTable';
import SchedulingRunner from './SchedulingRunner';
import './MainDashboard.css';

type TabType = 'overview' | 'orders' | 'scheduling' | 'results';

interface TabConfig {
  key: TabType;
  label: string;
  icon: string;
  component: React.ReactNode;
}

const MainDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const tabs: TabConfig[] = [
    {
      key: 'overview',
      label: '전체 현황',
      icon: '📊',
      component: <Dashboard />
    },
    {
      key: 'orders',
      label: '주문 관리',
      icon: '📋',
      component: <OrderTable />
    },
    {
      key: 'scheduling',
      label: '스케줄링 실행',
      icon: '⚙️',
      component: <SchedulingRunner onRunComplete={() => setActiveTab('overview')} />
    },
    {
      key: 'results',
      label: '결과 분석',
      icon: '📈',
      component: <div className="coming-soon">결과 분석 기능 개발 중...</div>
    }
  ];

  const handleTabChange = (tabKey: TabType) => {
    setActiveTab(tabKey);
  };

  const currentTab = tabs.find(tab => tab.key === activeTab) || tabs[0];

  return (
    <div className="main-dashboard">
      <div className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-title">
            🏭 생산계획 스케줄링 시스템
          </h1>
          <div className="system-info">
            <span className="status-indicator online">
              <span className="status-dot"></span>
              시스템 온라인
            </span>
            <span className="current-time">
              {new Date().toLocaleString('ko-KR')}
            </span>
          </div>
        </div>
      </div>

      <div className="dashboard-nav">
        <div className="nav-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={`nav-tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => handleTabChange(tab.key)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="dashboard-content">
        <div className="tab-header">
          <h2 className="tab-title">
            <span className="title-icon">{currentTab.icon}</span>
            {currentTab.label}
          </h2>
          {activeTab === 'scheduling' && (
            <div className="quick-actions">
              <button 
                className="quick-action-btn"
                onClick={() => setActiveTab('orders')}
              >
                📋 주문 관리
              </button>
            </div>
          )}
        </div>

        <div className="tab-content">
          {currentTab.component}
        </div>
      </div>

      <div className="dashboard-footer">
        <div className="footer-content">
          <div className="footer-info">
            <span>Production Scheduling System v1.0</span>
            <span>React + FastAPI + Python 스케줄링 엔진</span>
          </div>
          <div className="footer-links">
            <button className="footer-link">시스템 정보</button>
            <button className="footer-link">도움말</button>
            <button className="footer-link">설정</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainDashboard;