import React from 'react';
import styled from 'styled-components';
import { Download, Eye, BarChart3, Calendar, Clock } from 'lucide-react';

const ResultsContainer = styled.div`
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

const ResultsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
`;

const ResultCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
`;

const CardHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
`;

const CardTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
`;

const CardActions = styled.div`
  display: flex;
  gap: 0.5rem;
`;

const ActionButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.75rem;

  &:hover {
    background: #f8fafc;
    color: #475569;
  }
`;

const CardContent = styled.div`
  margin-bottom: 1rem;
`;

const MetricItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;

  &:last-child {
    border-bottom: none;
  }
`;

const MetricLabel = styled.span`
  font-size: 0.875rem;
  color: #64748b;
`;

const MetricValue = styled.span`
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
`;

const StatusBadge = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background: ${props => {
    switch (props.status) {
      case 'completed': return '#dcfce7';
      case 'running': return '#fef3c7';
      case 'error': return '#fef2f2';
      default: return '#f1f5f9';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'completed': return '#16a34a';
      case 'running': return '#d97706';
      case 'error': return '#dc2626';
      default: return '#64748b';
    }
  }};
`;

const ChartContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
`;

const ChartTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1rem;
`;

const ChartPlaceholder = styled.div`
  height: 400px;
  background: #f8fafc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 0.875rem;
`;

const Results = () => {
  const results = [
    {
      id: 1,
      title: '스케줄링 #24',
      status: 'completed',
      createdAt: '2024-01-15 14:30',
      metrics: [
        { label: '총 작업 수', value: '156' },
        { label: '완료된 작업', value: '156' },
        { label: '지연된 작업', value: '3' },
        { label: 'Makespan', value: '72시간' },
        { label: '효율성', value: '94.2%' }
      ]
    },
    {
      id: 2,
      title: '스케줄링 #23',
      status: 'running',
      createdAt: '2024-01-15 13:45',
      metrics: [
        { label: '총 작업 수', value: '142' },
        { label: '완료된 작업', value: '89' },
        { label: '진행 중인 작업', value: '53' },
        { label: '예상 완료', value: '2시간 후' },
        { label: '진행률', value: '62.7%' }
      ]
    },
    {
      id: 3,
      title: '스케줄링 #22',
      status: 'error',
      createdAt: '2024-01-15 12:20',
      metrics: [
        { label: '총 작업 수', value: '98' },
        { label: '완료된 작업', value: '45' },
        { label: '오류 발생', value: '3단계' },
        { label: '오류 메시지', value: '데이터 불일치' },
        { label: '진행률', value: '45.9%' }
      ]
    }
  ];

  return (
    <ResultsContainer>
      <PageHeader>
        <PageTitle>결과 분석</PageTitle>
        <PageDescription>
          스케줄링 실행 결과를 분석하고 성과를 확인하세요.
        </PageDescription>
      </PageHeader>

      <ResultsGrid>
        {results.map((result) => (
          <ResultCard key={result.id}>
            <CardHeader>
              <CardTitle>{result.title}</CardTitle>
              <CardActions>
                <ActionButton>
                  <Eye size={14} />
                  보기
                </ActionButton>
                <ActionButton>
                  <Download size={14} />
                  다운로드
                </ActionButton>
              </CardActions>
            </CardHeader>
            
            <CardContent>
              <div style={{ marginBottom: '1rem' }}>
                <StatusBadge status={result.status}>
                  {result.status === 'completed' && '완료'}
                  {result.status === 'running' && '진행 중'}
                  {result.status === 'error' && '오류'}
                </StatusBadge>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                  {result.createdAt}
                </div>
              </div>
              
              {result.metrics.map((metric, index) => (
                <MetricItem key={index}>
                  <MetricLabel>{metric.label}</MetricLabel>
                  <MetricValue>{metric.value}</MetricValue>
                </MetricItem>
              ))}
            </CardContent>
          </ResultCard>
        ))}
      </ResultsGrid>

      <ChartContainer>
        <ChartTitle>스케줄링 성과 추이</ChartTitle>
        <ChartPlaceholder>
          <div style={{ textAlign: 'center' }}>
            <BarChart3 size={48} color="#cbd5e1" />
            <div style={{ marginTop: '1rem' }}>
              성과 차트가 여기에 표시됩니다
            </div>
          </div>
        </ChartPlaceholder>
      </ChartContainer>

      <ChartContainer>
        <ChartTitle>기계별 작업량 분포</ChartTitle>
        <ChartPlaceholder>
          <div style={{ textAlign: 'center' }}>
            <Calendar size={48} color="#cbd5e1" />
            <div style={{ marginTop: '1rem' }}>
              기계별 작업량 차트가 여기에 표시됩니다
            </div>
          </div>
        </ChartPlaceholder>
      </ChartContainer>
    </ResultsContainer>
  );
};

export default Results;
