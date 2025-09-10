import React, { useState } from 'react';
import styled from 'styled-components';
import { useMutation, useQuery } from 'react-query';
import { Play, Pause, RotateCcw, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiService } from '../services/api';
import StepProgress from '../components/StepProgress';
import DataUploadForm from '../components/DataUploadForm';
import SchedulingResults from '../components/SchedulingResults';

const SchedulingContainer = styled.div`
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

const ControlPanel = styled.div`
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const ControlButtons = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  
  @media (max-width: 768px) {
    flex-direction: column;
  }
`;

const Button = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const PrimaryButton = styled(Button)`
  background: #3b82f6;
  color: white;
  
  &:hover:not(:disabled) {
    background: #2563eb;
    transform: translateY(-1px);
  }
`;

const SecondaryButton = styled(Button)`
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
  
  &:hover:not(:disabled) {
    background: #e2e8f0;
    color: #475569;
  }
`;

const DangerButton = styled(Button)`
  background: #ef4444;
  color: white;
  
  &:hover:not(:disabled) {
    background: #dc2626;
    transform: translateY(-1px);
  }
`;

const StatusCard = styled.div`
  background: ${props => {
    switch (props.status) {
      case 'success': return '#f0fdf4';
      case 'error': return '#fef2f2';
      case 'warning': return '#fffbeb';
      case 'info': return '#f0f9ff';
      default: return '#f8fafc';
    }
  }};
  border: 1px solid ${props => {
    switch (props.status) {
      case 'success': return '#bbf7d0';
      case 'error': return '#fecaca';
      case 'warning': return '#fed7aa';
      case 'info': return '#bae6fd';
      default: return '#e2e8f0';
    }
  }};
  border-radius: 8px;
  padding: 1rem;
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
      case 'success': return '#22c55e';
      case 'error': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#64748b';
    }
  }};
  color: white;
`;

const StatusText = styled.div`
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

const Scheduling = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [sessionId, setSessionId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [stepResults, setStepResults] = useState([]);

  // 단계별 실행 뮤테이션
  const stepByStepMutation = useMutation(
    (data) => apiService.stepByStep(data),
    {
      onSuccess: (data) => {
        console.log('단계별 실행 성공:', data);
        setSessionId(data.sessionId);
        setStepResults(data.results);
        setIsRunning(false);
        toast.success('스케줄링이 완료되었습니다!');
      },
      onError: (error) => {
        console.error('단계별 실행 오류:', error);
        setIsRunning(false);
        toast.error('스케줄링 실행 중 오류가 발생했습니다.');
      }
    }
  );

  // 전체 파이프라인 실행 뮤테이션
  const fullPipelineMutation = useMutation(
    (data) => apiService.fullPipeline(data),
    {
      onSuccess: (data) => {
        console.log('전체 파이프라인 성공:', data);
        setSessionId(data.sessionId);
        setIsRunning(false);
        toast.success('전체 파이프라인이 완료되었습니다!');
      },
      onError: (error) => {
        console.error('전체 파이프라인 오류:', error);
        setIsRunning(false);
        toast.error('전체 파이프라인 실행 중 오류가 발생했습니다.');
      }
    }
  );

  // 세션 상태 조회
  const { data: sessionStatus, refetch: refetchSessionStatus } = useQuery(
    ['sessionStatus', sessionId],
    () => apiService.getSessionStatus(sessionId),
    {
      enabled: !!sessionId,
      refetchInterval: 5000, // 5초마다 상태 조회
    }
  );

  const handleStepByStep = (data = {}) => {
    console.log('단계별 실행 시작:', data);
    setIsRunning(true);
    setCurrentStep(0);
    setStepResults([]);
    
    // 샘플 데이터가 없으면 기본 샘플 데이터 사용
    const sampleData = Object.keys(data).length > 0 ? data : {
      linespeed: [
        { "GITEM": 31704, "공정명": "염료점착", "C2010": 29.8, "C2250": null, "C2260": 29.8, "C2270": null, "O2310": null, "O2340": null },
        { "GITEM": 31704, "공정명": "세척", "C2010": null, "C2250": 36.9, "C2260": 47.1, "C2270": 49.4, "O2310": null, "O2340": null }
      ],
      operation_sequence: [
        { "공정순서": 1, "공정명": "염료점착", "공정분류": "분류_1", "배합코드": "BATCH_001" },
        { "공정순서": 2, "공정명": "세척", "공정분류": "분류_2", "배합코드": "BATCH_002" }
      ],
      machine_master_info: [
        { "기계인덱스": 0, "기계코드": "C2010", "기계이름": "1호기" },
        { "기계인덱스": 1, "기계코드": "C2250", "기계이름": "25호기" }
      ],
      yield_data: [
        { "GITEM": 31704, "공정명": "염료점착", "수율": 0.862 },
        { "GITEM": 31704, "공정명": "세척", "수율": 0.933 }
      ],
      gitem_operation: [
        { "GITEM": 31704, "공정명": "염료점착", "공정분류": "분류_1", "배합코드": "BATCH_001" },
        { "GITEM": 31704, "공정명": "세척", "공정분류": "분류_2", "배합코드": "BATCH_002" }
      ],
      operation_types: [
        { "공정명": "염료점착", "공정분류": "분류_1", "설명": "염료점착 공정 분류" },
        { "공정명": "세척", "공정분류": "분류_2", "설명": "세척 공정 분류" }
      ],
      operation_delay: [
        { "선행공정분류": "분류_1", "후행공정분류": "분류_2", "타입교체시간": 50, "long_to_short": 5, "short_to_long": 42 }
      ],
      width_change: [
        { "이전폭": 1524, "이후폭": 1372, "변경시간": 15 }
      ],
      machine_rest: [],
      machine_allocate: [],
      machine_limit: [],
      order_data: [
        { "P/O NO": "SW1250407101", "GITEM": 31704, "GITEM명": "PPF-NS-TGA(WHITE)", "너비": 1524, "길이": 15, "의뢰량": 79, "원단길이": 319, "납기일": "2025-06-14T00:00:00" }
      ]
    };
    
    stepByStepMutation.mutate(sampleData);
  };

  const handleFullPipeline = (data = {}) => {
    console.log('전체 파이프라인 실행 시작:', data);
    setIsRunning(true);
    setCurrentStep(0);
    setStepResults([]);
    
    // 샘플 데이터가 없으면 기본 샘플 데이터 사용
    const sampleData = Object.keys(data).length > 0 ? data : {
      linespeed: [
        { "GITEM": 31704, "공정명": "염료점착", "C2010": 29.8, "C2250": null, "C2260": 29.8, "C2270": null, "O2310": null, "O2340": null },
        { "GITEM": 31704, "공정명": "세척", "C2010": null, "C2250": 36.9, "C2260": 47.1, "C2270": 49.4, "O2310": null, "O2340": null }
      ],
      operation_sequence: [
        { "공정순서": 1, "공정명": "염료점착", "공정분류": "분류_1", "배합코드": "BATCH_001" },
        { "공정순서": 2, "공정명": "세척", "공정분류": "분류_2", "배합코드": "BATCH_002" }
      ],
      machine_master_info: [
        { "기계인덱스": 0, "기계코드": "C2010", "기계이름": "1호기" },
        { "기계인덱스": 1, "기계코드": "C2250", "기계이름": "25호기" }
      ],
      yield_data: [
        { "GITEM": 31704, "공정명": "염료점착", "수율": 0.862 },
        { "GITEM": 31704, "공정명": "세척", "수율": 0.933 }
      ],
      gitem_operation: [
        { "GITEM": 31704, "공정명": "염료점착", "공정분류": "분류_1", "배합코드": "BATCH_001" },
        { "GITEM": 31704, "공정명": "세척", "공정분류": "분류_2", "배합코드": "BATCH_002" }
      ],
      operation_types: [
        { "공정명": "염료점착", "공정분류": "분류_1", "설명": "염료점착 공정 분류" },
        { "공정명": "세척", "공정분류": "분류_2", "설명": "세척 공정 분류" }
      ],
      operation_delay: [
        { "선행공정분류": "분류_1", "후행공정분류": "분류_2", "타입교체시간": 50, "long_to_short": 5, "short_to_long": 42 }
      ],
      width_change: [
        { "이전폭": 1524, "이후폭": 1372, "변경시간": 15 }
      ],
      machine_rest: [],
      machine_allocate: [],
      machine_limit: [],
      order_data: [
        { "P/O NO": "SW1250407101", "GITEM": 31704, "GITEM명": "PPF-NS-TGA(WHITE)", "너비": 1524, "길이": 15, "의뢰량": 79, "원단길이": 319, "납기일": "2025-06-14T00:00:00" }
      ]
    };
    
    fullPipelineMutation.mutate(sampleData);
  };

  const handleStop = () => {
    setIsRunning(false);
    toast.info('스케줄링이 중단되었습니다.');
  };

  const handleReset = () => {
    setCurrentStep(0);
    setSessionId(null);
    setStepResults([]);
    setIsRunning(false);
  };

  const getCurrentStatus = () => {
    if (isRunning) {
      return {
        status: 'info',
        title: '스케줄링 실행 중',
        description: '현재 스케줄링이 진행 중입니다. 잠시만 기다려주세요.',
        icon: Clock
      };
    }

    if (stepResults.length > 0) {
      const hasError = stepResults.some(step => !step.success);
      if (hasError) {
        return {
          status: 'error',
          title: '스케줄링 실패',
          description: '일부 단계에서 오류가 발생했습니다.',
          icon: AlertCircle
        };
      } else {
        return {
          status: 'success',
          title: '스케줄링 완료',
          description: '모든 단계가 성공적으로 완료되었습니다.',
          icon: CheckCircle
        };
      }
    }

    return {
      status: 'info',
      title: '스케줄링 준비',
      description: '데이터를 업로드하고 스케줄링을 시작하세요.',
      icon: Clock
    };
  };

  const currentStatus = getCurrentStatus();
  const StatusIconComponent = currentStatus.icon;

  return (
    <SchedulingContainer>
      <PageHeader>
        <PageTitle>스케줄링 관리</PageTitle>
        <PageDescription>
          제조 공정 스케줄링을 실행하고 결과를 확인하세요.
        </PageDescription>
      </PageHeader>

      <ControlPanel>
        <ControlButtons>
          <PrimaryButton
            onClick={() => {
              console.log('단계별 실행 버튼 클릭됨');
              handleStepByStep({});
            }}
            disabled={isRunning}
          >
            <Play size={18} />
            단계별 실행
          </PrimaryButton>
          
          <SecondaryButton
            onClick={() => {
              console.log('전체 실행 버튼 클릭됨');
              handleFullPipeline({});
            }}
            disabled={isRunning}
          >
            <Play size={18} />
            전체 실행
          </SecondaryButton>
          
          <SecondaryButton
            onClick={handleStop}
            disabled={!isRunning}
          >
            <Pause size={18} />
            중단
          </SecondaryButton>
          
          <DangerButton
            onClick={handleReset}
            disabled={isRunning}
          >
            <RotateCcw size={18} />
            초기화
          </DangerButton>
        </ControlButtons>

        <StatusCard status={currentStatus.status}>
          <StatusIcon status={currentStatus.status}>
            <StatusIconComponent size={20} />
          </StatusIcon>
          <StatusText>
            <StatusTitle>{currentStatus.title}</StatusTitle>
            <StatusDescription>{currentStatus.description}</StatusDescription>
          </StatusText>
        </StatusCard>
      </ControlPanel>

      <StepProgress
        currentStep={currentStep}
        stepResults={stepResults}
        isRunning={isRunning}
      />

      <DataUploadForm
        onDataUpload={handleStepByStep}
        disabled={isRunning}
      />

      {sessionId && (
        <SchedulingResults
          sessionId={sessionId}
          sessionStatus={sessionStatus}
        />
      )}
    </SchedulingContainer>
  );
};

export default Scheduling;
