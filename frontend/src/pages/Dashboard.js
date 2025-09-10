import React from 'react';
import styled from 'styled-components';
import { BarChart3, Calendar, Clock, AlertTriangle, CheckCircle } from 'lucide-react';

const DashboardContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;
`;

const PageTitle = styled.h1`
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
`;

const PageDescription = styled.p`
  color: #64748b;
  font-size: 1rem;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
`;

const StatCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  border-left: 4px solid ${props => props.color || '#3b82f6'};
`;

const StatHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
`;

const StatTitle = styled.h3`
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const StatIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: ${props => props.bgColor || '#f1f5f9'};
  color: ${props => props.color || '#64748b'};
`;

const StatValue = styled.div`
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.25rem;
`;

const StatChange = styled.div`
  font-size: 0.875rem;
  color: ${props => props.positive ? '#16a34a' : '#dc2626'};
  display: flex;
  align-items: center;
  gap: 0.25rem;
`;

const ContentGrid = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const ChartCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const ChartTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1rem;
`;

const ChartPlaceholder = styled.div`
  height: 300px;
  background: #f8fafc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 0.875rem;
`;

const RecentActivity = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const ActivityItem = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
  border-bottom: 1px solid #f1f5f9;
  
  &:last-child {
    border-bottom: none;
  }
`;

const ActivityIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: ${props => props.bgColor || '#f1f5f9'};
  color: ${props => props.color || '#64748b'};
`;

const ActivityContent = styled.div`
  flex: 1;
`;

const ActivityTitle = styled.h4`
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
`;

const ActivityTime = styled.p`
  font-size: 0.75rem;
  color: #64748b;
  margin: 0;
`;

const Dashboard = () => {
  const stats = [
    {
      title: '총 스케줄링',
      value: '24',
      change: '+12%',
      positive: true,
      icon: Calendar,
      color: '#3b82f6',
      bgColor: '#dbeafe'
    },
    {
      title: '완료된 작업',
      value: '18',
      change: '+8%',
      positive: true,
      icon: CheckCircle,
      color: '#16a34a',
      bgColor: '#dcfce7'
    },
    {
      title: '진행 중인 작업',
      value: '3',
      change: '-2%',
      positive: false,
      icon: Clock,
      color: '#f59e0b',
      bgColor: '#fef3c7'
    },
    {
      title: '오류 발생',
      value: '1',
      change: '-50%',
      positive: true,
      icon: AlertTriangle,
      color: '#ef4444',
      bgColor: '#fef2f2'
    }
  ];

  const recentActivities = [
    {
      title: '스케줄링 #24 완료',
      time: '2분 전',
      icon: CheckCircle,
      color: '#16a34a',
      bgColor: '#dcfce7'
    },
    {
      title: '새로운 주문 데이터 업로드',
      time: '15분 전',
      icon: Calendar,
      color: '#3b82f6',
      bgColor: '#dbeafe'
    },
    {
      title: '스케줄링 #23 시작',
      time: '1시간 전',
      icon: Clock,
      color: '#f59e0b',
      bgColor: '#fef3c7'
    },
    {
      title: '시스템 점검 완료',
      time: '2시간 전',
      icon: BarChart3,
      color: '#8b5cf6',
      bgColor: '#f3e8ff'
    }
  ];

  return (
    <DashboardContainer>
      <PageHeader>
        <PageTitle>대시보드</PageTitle>
        <PageDescription>
          제조 공정 스케줄링 시스템의 현재 상태를 확인하세요.
        </PageDescription>
      </PageHeader>

      <StatsGrid>
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <StatCard key={index} color={stat.color}>
              <StatHeader>
                <StatTitle>{stat.title}</StatTitle>
                <StatIcon bgColor={stat.bgColor} color={stat.color}>
                  <Icon size={20} />
                </StatIcon>
              </StatHeader>
              <StatValue>{stat.value}</StatValue>
              <StatChange positive={stat.positive}>
                {stat.change}
              </StatChange>
            </StatCard>
          );
        })}
      </StatsGrid>

      <ContentGrid>
        <ChartCard>
          <ChartTitle>스케줄링 성과</ChartTitle>
          <ChartPlaceholder>
            차트가 여기에 표시됩니다
          </ChartPlaceholder>
        </ChartCard>

        <RecentActivity>
          <ChartTitle>최근 활동</ChartTitle>
          {recentActivities.map((activity, index) => {
            const Icon = activity.icon;
            return (
              <ActivityItem key={index}>
                <ActivityIcon bgColor={activity.bgColor} color={activity.color}>
                  <Icon size={16} />
                </ActivityIcon>
                <ActivityContent>
                  <ActivityTitle>{activity.title}</ActivityTitle>
                  <ActivityTime>{activity.time}</ActivityTime>
                </ActivityContent>
              </ActivityItem>
            );
          })}
        </RecentActivity>
      </ContentGrid>
    </DashboardContainer>
  );
};

export default Dashboard;
