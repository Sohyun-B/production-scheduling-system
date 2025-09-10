import React from 'react';
import styled from 'styled-components';
import { CheckCircle, Circle, Clock, AlertCircle } from 'lucide-react';

const ProgressContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const ProgressTitle = styled.h2`
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1.5rem;
`;

const StepsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const StepItem = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  background: ${props => {
    if (props.status === 'completed') return '#f0fdf4';
    if (props.status === 'current') return '#fef3c7';
    if (props.status === 'error') return '#fef2f2';
    return '#f8fafc';
  }};
  border: 1px solid ${props => {
    if (props.status === 'completed') return '#bbf7d0';
    if (props.status === 'current') return '#fde68a';
    if (props.status === 'error') return '#fecaca';
    return '#e2e8f0';
  }};
  transition: all 0.2s ease;
`;

const StepIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: ${props => {
    if (props.status === 'completed') return '#22c55e';
    if (props.status === 'current') return '#f59e0b';
    if (props.status === 'error') return '#ef4444';
    return '#e2e8f0';
  }};
  color: white;
  flex-shrink: 0;
`;

const StepContent = styled.div`
  flex: 1;
`;

const StepTitle = styled.h3`
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
`;

const StepDescription = styled.p`
  font-size: 0.75rem;
  color: #64748b;
  margin: 0;
`;

const StepStatus = styled.div`
  font-size: 0.75rem;
  font-weight: 500;
  color: ${props => {
    if (props.status === 'completed') return '#16a34a';
    if (props.status === 'current') return '#d97706';
    if (props.status === 'error') return '#dc2626';
    return '#64748b';
  }};
`;

const StepProgress = ({ currentStep, stepResults, isRunning }) => {
  const steps = [
    {
      id: 1,
      title: '데이터 로딩',
      description: '스케줄링에 필요한 데이터를 로딩합니다.',
      status: getStepStatus(1, currentStep, stepResults, isRunning)
    },
    {
      id: 2,
      title: '전처리',
      description: '주문 데이터를 전처리하고 공정별로 분리합니다.',
      status: getStepStatus(2, currentStep, stepResults, isRunning)
    },
    {
      id: 3,
      title: '수율 예측',
      description: '생산 수율을 예측하고 조정합니다.',
      status: getStepStatus(3, currentStep, stepResults, isRunning)
    },
    {
      id: 4,
      title: 'DAG 생성',
      description: '공정 간 의존성 관계를 구축합니다.',
      status: getStepStatus(4, currentStep, stepResults, isRunning)
    },
    {
      id: 5,
      title: '스케줄링 실행',
      description: '최적의 생산 일정을 생성합니다.',
      status: getStepStatus(5, currentStep, stepResults, isRunning)
    },
    {
      id: 6,
      title: '결과 후처리',
      description: '스케줄링 결과를 분석하고 정리합니다.',
      status: getStepStatus(6, currentStep, stepResults, isRunning)
    }
  ];

  function getStepStatus(stepId, currentStep, stepResults, isRunning) {
    const stepResult = stepResults.find(result => result.stage === stepId);
    
    if (stepResult) {
      return stepResult.success ? 'completed' : 'error';
    }
    
    if (isRunning && currentStep === stepId) {
      return 'current';
    }
    
    return 'pending';
  }

  function getStepIcon(status) {
    switch (status) {
      case 'completed':
        return CheckCircle;
      case 'current':
        return Clock;
      case 'error':
        return AlertCircle;
      default:
        return Circle;
    }
  }

  function getStepStatusText(status) {
    switch (status) {
      case 'completed':
        return '완료';
      case 'current':
        return '진행 중';
      case 'error':
        return '오류';
      default:
        return '대기';
    }
  }

  return (
    <ProgressContainer>
      <ProgressTitle>스케줄링 진행 상황</ProgressTitle>
      <StepsList>
        {steps.map((step) => {
          const Icon = getStepIcon(step.status);
          
          return (
            <StepItem key={step.id} status={step.status}>
              <StepIcon status={step.status}>
                <Icon size={20} />
              </StepIcon>
              <StepContent>
                <StepTitle>{step.title}</StepTitle>
                <StepDescription>{step.description}</StepDescription>
              </StepContent>
              <StepStatus status={step.status}>
                {getStepStatusText(step.status)}
              </StepStatus>
            </StepItem>
          );
        })}
      </StepsList>
    </ProgressContainer>
  );
};

export default StepProgress;
