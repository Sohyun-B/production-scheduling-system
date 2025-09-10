import React from 'react';
import styled from 'styled-components';
import { Download, Eye, BarChart3, Clock, CheckCircle, AlertCircle } from 'lucide-react';

const ResultsContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const ResultsHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
`;

const ResultsTitle = styled.h2`
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
`;

const ResultsActions = styled.div`
  display: flex;
  gap: 0.5rem;
`;

const ActionButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;

  &:hover {
    background: #f8fafc;
    color: #475569;
  }
`;

const StatusCard = styled.div`
  background: ${props => {
    switch (props.status) {
      case 'completed': return '#f0fdf4';
      case 'running': return '#fef3c7';
      case 'error': return '#fef2f2';
      default: return '#f8fafc';
    }
  }};
  border: 1px solid ${props => {
    switch (props.status) {
      case 'completed': return '#bbf7d0';
      case 'running': return '#fde68a';
      case 'error': return '#fecaca';
      default: return '#e2e8f0';
    }
  }};
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

const StatusIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: ${props => {
    switch (props.status) {
      case 'completed': return '#22c55e';
      case 'running': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#64748b';
    }
  }};
  color: white;
`;

const StatusContent = styled.div`
  flex: 1;
`;

const StatusTitle = styled.h3`
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
`;

const StatusDescription = styled.p`
  font-size: 0.75rem;
  color: #64748b;
  margin: 0;
`;

const MetricsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const MetricCard = styled.div`
  background: #f8fafc;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
`;

const MetricValue = styled.div`
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.25rem;
`;

const MetricLabel = styled.div`
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const ChartContainer = styled.div`
  background: #f8fafc;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
`;

const SchedulingResults = ({ sessionId, sessionStatus }) => {
  if (!sessionId) return null;

  const getStatusInfo = () => {
    if (!sessionStatus) {
      return {
        status: 'running',
        title: '로딩 중',
        description: '세션 상태를 확인하고 있습니다...',
        icon: Clock
      };
    }

    const completedStages = sessionStatus.completed_stages || [];
    const totalStages = sessionStatus.total_stages || 6;

    if (completedStages.length === totalStages) {
      return {
        status: 'completed',
        title: '스케줄링 완료',
        description: '모든 단계가 성공적으로 완료되었습니다.',
        icon: CheckCircle
      };
    } else if (completedStages.length > 0) {
      return {
        status: 'running',
        title: '스케줄링 진행 중',
        description: `${completedStages.length}/${totalStages} 단계 완료`,
        icon: Clock
      };
    } else {
      return {
        status: 'error',
        title: '스케줄링 실패',
        description: '스케줄링 실행 중 오류가 발생했습니다.',
        icon: AlertCircle
      };
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  const mockMetrics = [
    { label: '총 작업 수', value: '156' },
    { label: '완료된 작업', value: '142' },
    { label: '진행 중인 작업', value: '14' },
    { label: 'Makespan', value: '72시간' },
    { label: '효율성', value: '94.2%' },
    { label: '지연된 작업', value: '3' }
  ];

  return (
    <ResultsContainer>
      <ResultsHeader>
        <ResultsTitle>스케줄링 결과</ResultsTitle>
        <ResultsActions>
          <ActionButton>
            <Eye size={16} />
            상세 보기
          </ActionButton>
          <ActionButton>
            <Download size={16} />
            결과 다운로드
          </ActionButton>
        </ResultsActions>
      </ResultsHeader>

      <StatusCard status={statusInfo.status}>
        <StatusIcon status={statusInfo.status}>
          <StatusIcon size={20} />
        </StatusIcon>
        <StatusContent>
          <StatusTitle>{statusInfo.title}</StatusTitle>
          <StatusDescription>{statusInfo.description}</StatusDescription>
        </StatusContent>
      </StatusCard>

      <MetricsGrid>
        {mockMetrics.map((metric, index) => (
          <MetricCard key={index}>
            <MetricValue>{metric.value}</MetricValue>
            <MetricLabel>{metric.label}</MetricLabel>
          </MetricCard>
        ))}
      </MetricsGrid>

      <ChartContainer>
        <BarChart3 size={48} color="#cbd5e1" />
        <div style={{ marginTop: '1rem' }}>
          스케줄링 결과 차트가 여기에 표시됩니다
        </div>
      </ChartContainer>
    </ResultsContainer>
  );
};

export default SchedulingResults;
