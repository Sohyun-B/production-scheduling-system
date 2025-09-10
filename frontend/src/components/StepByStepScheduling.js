import React, { useState, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';
import { apiService } from '../services/api';

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  animation: ${fadeIn} 0.5s ease-out;
`;

const Header = styled.div`
  text-align: center;
  margin-bottom: 40px;
  
  h1 {
    color: #2c3e50;
    font-size: 2.5rem;
    margin-bottom: 10px;
  }
  
  p {
    color: #7f8c8d;
    font-size: 1.1rem;
  }
`;

const StepsContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
`;

const StepCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 2px solid ${props => 
    props.status === 'completed' ? '#27ae60' : 
    props.status === 'running' ? '#f39c12' : 
    props.status === 'failed' ? '#e74c3c' : '#ecf0f1'
  };
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
  }
`;

const StepHeader = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  
  .step-number {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: ${props => 
      props.status === 'completed' ? '#27ae60' : 
      props.status === 'running' ? '#f39c12' : 
      props.status === 'failed' ? '#e74c3c' : '#bdc3c7'
    };
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    margin-right: 12px;
  }
  
  .step-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: #2c3e50;
  }
`;

const StepDescription = styled.p`
  color: #7f8c8d;
  margin-bottom: 20px;
  line-height: 1.5;
`;

const StepButton = styled.button`
  width: 100%;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  
  ${props => {
    if (props.status === 'completed') {
      return `
        background: #27ae60;
        color: white;
        &:hover { background: #229954; }
      `;
    } else if (props.status === 'running') {
      return `
        background: #f39c12;
        color: white;
        cursor: not-allowed;
      `;
    } else if (props.status === 'failed') {
      return `
        background: #e74c3c;
        color: white;
        &:hover { background: #c0392b; }
      `;
    } else {
      return `
        background: #3498db;
        color: white;
        &:hover { background: #2980b9; }
        &:disabled {
          background: #bdc3c7;
          cursor: not-allowed;
        }
      `;
    }
  }}
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: ${spin} 1s ease-in-out infinite;
  margin-right: 8px;
`;

const StatusMessage = styled.div`
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  
  ${props => {
    if (props.type === 'success') {
      return `
        background: #d5f4e6;
        color: #27ae60;
        border: 1px solid #27ae60;
      `;
    } else if (props.type === 'error') {
      return `
        background: #fadbd8;
        color: #e74c3c;
        border: 1px solid #e74c3c;
      `;
    } else if (props.type === 'info') {
      return `
        background: #d6eaf8;
        color: #3498db;
        border: 1px solid #3498db;
      `;
    }
  }}
`;

const DataForm = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 40px;
`;

const FormTitle = styled.h3`
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 1.3rem;
`;

const FormGroup = styled.div`
  margin-bottom: 16px;
  
  label {
    display: block;
    margin-bottom: 6px;
    font-weight: 600;
    color: #2c3e50;
  }
  
  input, select, textarea {
    width: 100%;
    padding: 10px 12px;
    border: 2px solid #ecf0f1;
    border-radius: 6px;
    font-size: 1rem;
    transition: border-color 0.3s ease;
    
    &:focus {
      outline: none;
      border-color: #3498db;
    }
  }
  
  textarea {
    resize: vertical;
    min-height: 100px;
  }
`;

const ResultsContainer = styled.div`
  margin-top: 16px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
`;

const ResultsTitle = styled.h4`
  margin: 0 0 12px 0;
  color: #495057;
  font-size: 1rem;
  font-weight: 600;
`;

const ResultsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
`;

const ResultItem = styled.div`
  background: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #dee2e6;
`;

const ResultLabel = styled.div`
  font-size: 0.8rem;
  color: #6c757d;
  margin-bottom: 4px;
  font-weight: 500;
`;

const ResultValue = styled.div`
  font-size: 1.1rem;
  color: #212529;
  font-weight: 600;
`;

const DataTable = styled.div`
  margin-top: 16px;
  overflow-x: auto;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
`;

const TableHeader = styled.th`
  background-color: #e9ecef;
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border: 1px solid #dee2e6;
`;

const TableCell = styled.td`
  padding: 8px 12px;
  border: 1px solid #dee2e6;
  background-color: white;
`;

const ExpandButton = styled.button`
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #e7f3ff;
  }
`;

const StepByStepScheduling = () => {
  const [sessionId, setSessionId] = useState(null);
  const [stepStatus, setStepStatus] = useState({
    1: 'pending',
    2: 'pending',
    3: 'pending',
    4: 'pending',
    5: 'pending',
    6: 'pending'
  });
  const [stepMessages, setStepMessages] = useState({});
  const [stepResults, setStepResults] = useState({});
  const [formData, setFormData] = useState({
    windowDays: 5,
    // 기본 샘플 데이터
    sampleData: {
      linespeed: [
        { GITEM: "G001", 공정명: "C2010", C2010: 100, C2250: 0, C2260: 0, C2270: 0, O2310: 0, O2340: 0 },
        { GITEM: "G002", 공정명: "C2250", C2010: 0, C2250: 120, C2260: 0, C2270: 0, O2310: 0, O2340: 0 }
      ],
      operation_sequence: [
        { 공정순서: 1, 공정명: "C2010", 공정분류: "CUT", 배합코드: "BH001" },
        { 공정순서: 2, 공정명: "C2250", 공정분류: "CUT", 배합코드: "BH002" }
      ],
      machine_master_info: [
        { 기계인덱스: 1, 기계코드: "C2010", 기계이름: "커팅기1" },
        { 기계인덱스: 2, 기계코드: "C2250", 기계이름: "커팅기2" }
      ],
      yield_data: [
        { GITEM: "G001", 공정명: "C2010", 수율: 0.95 },
        { GITEM: "G002", 공정명: "C2250", 수율: 0.92 }
      ],
      gitem_operation: [
        { GITEM: "G001", 공정명: "C2010", 공정분류: "CUT", 배합코드: "BH001" },
        { GITEM: "G002", 공정명: "C2250", 공정분류: "CUT", 배합코드: "BH002" }
      ],
      operation_types: [
        { 공정명: "C2010", 공정분류: "CUT", 설명: "커팅공정1" },
        { 공정명: "C2250", 공정분류: "CUT", 설명: "커팅공정2" }
      ],
      operation_delay: [
        { 선행공정분류: "CUT", 후행공정분류: "CUT", 타입교체시간: 30, long_to_short: 10, short_to_long: 20 }
      ],
      width_change: [
        { 기계인덱스: 1, 이전폭: 1000, 이후폭: 1200, 변경시간: 15, long_to_short: 10, short_to_long: 20 }
      ],
      machine_rest: [
        { 기계인덱스: 1, 시작시간: "2024-01-01 00:00:00", 종료시간: "2024-01-01 08:00:00", 사유: "야간휴무" }
      ],
      machine_allocate: [
        { 기계인덱스: 1, 공정명: "C2010", 할당유형: "EXCLUSIVE" }
      ],
      machine_limit: [
        { 기계인덱스: 1, 공정명: "C2010", 시작시간: "2024-01-01 08:00:00", 종료시간: "2024-01-01 18:00:00", 제한사유: "작업시간" }
      ],
      order_data: [
        { "P/O NO": "PO001", GITEM: "G001", GITEM명: "제품1", 너비: 1000, 길이: 2000, 의뢰량: 100, 원단길이: 914, 납기일: "2024-01-15" },
        { "P/O NO": "PO002", GITEM: "G002", GITEM명: "제품2", 너비: 1200, 길이: 1500, 의뢰량: 50, 원단길이: 609, 납기일: "2024-01-20" }
      ]
    }
  });

  const steps = [
    {
      id: 1,
      title: "데이터 로딩",
      description: "외부에서 받은 JSON 데이터를 시스템 내부 데이터프레임으로 변환합니다.",
      endpoint: '/api/stages/stage1/load-data',
      method: 'POST',
      data: formData.sampleData
    },
    {
      id: 2,
      title: "전처리",
      description: "스케줄링에 필요한 데이터 구조로 변환 및 정리합니다.",
      endpoint: '/api/stages/stage2/preprocessing',
      method: 'POST',
      data: { session_id: sessionId }
    },
    {
      id: 3,
      title: "수율 예측",
      description: "각 공정별 예상 수율을 계산하여 실제 생산량을 예측합니다.",
      endpoint: '/api/stages/stage3/yield-prediction',
      method: 'POST',
      data: { session_id: sessionId }
    },
    {
      id: 4,
      title: "DAG 생성",
      description: "작업 간 의존성을 나타내는 DAG 구조를 생성합니다.",
      endpoint: '/api/stages/stage4/dag-creation',
      method: 'POST',
      data: { session_id: sessionId }
    },
    {
      id: 5,
      title: "스케줄링",
      description: "최적의 생산 일정을 생성합니다. (백그라운드 처리)",
      endpoint: '/api/stages/stage5/scheduling',
      method: 'POST',
      data: { session_id: sessionId, window_days: formData.windowDays }
    },
    {
      id: 6,
      title: "결과 후처리",
      description: "스케줄링 결과를 분석하고 정리하여 최종 보고서를 생성합니다.",
      endpoint: '/api/stages/stage6/results',
      method: 'POST',
      data: { session_id: sessionId }
    }
  ];

  const executeStep = async (step) => {
    try {
      setStepStatus(prev => ({ ...prev, [step.id]: 'running' }));
      setStepMessages(prev => ({ ...prev, [step.id]: '처리 중...' }));

      const response = await apiService.executeStep(step.endpoint, step.method, step.data);
      
      if (response.success) {
        setStepStatus(prev => ({ ...prev, [step.id]: 'completed' }));
        setStepMessages(prev => ({ 
          ...prev, 
          [step.id]: `완료: ${response.message}` 
        }));

        // 결과 데이터 저장
        if (response.data) {
          setStepResults(prev => ({ 
            ...prev, 
            [step.id]: response.data 
          }));
        }

        // 1단계 완료 시 세션 ID 저장
        if (step.id === 1) {
          setSessionId(response.session_id);
        }

        // 5단계는 비동기이므로 상태 확인 시작
        if (step.id === 5) {
          checkStage5Status();
        }
      } else {
        throw new Error(response.message || '알 수 없는 오류');
      }
    } catch (error) {
      setStepStatus(prev => ({ ...prev, [step.id]: 'failed' }));
      setStepMessages(prev => ({ 
        ...prev, 
        [step.id]: `실패: ${error.message}` 
      }));
    }
  };

  const checkStage5Status = async () => {
    if (!sessionId) return;

    try {
      const response = await apiService.getStage5Status(sessionId);
      
      if (response.status === 'completed') {
        setStepStatus(prev => ({ ...prev, 5: 'completed' }));
        setStepMessages(prev => ({ 
          ...prev, 
          5: `완료: ${response.scheduled_jobs}개 작업 스케줄링` 
        }));
        
        // 5단계 결과 데이터 저장
        setStepResults(prev => ({ 
          ...prev, 
          [5]: response 
        }));
      } else if (response.status === 'failed') {
        setStepStatus(prev => ({ ...prev, 5: 'failed' }));
        setStepMessages(prev => ({ 
          ...prev, 
          5: `실패: ${response.message}` 
        }));
      } else {
        // 2초 후 다시 확인
        setTimeout(checkStage5Status, 2000);
      }
    } catch (error) {
      setStepStatus(prev => ({ ...prev, 5: 'failed' }));
      setStepMessages(prev => ({ 
        ...prev, 
        5: `상태 확인 실패: ${error.message}` 
      }));
    }
  };

  const isStepEnabled = (stepId) => {
    if (stepId === 1) return true;
    if (!sessionId) return false;
    
    // 이전 단계가 완료되어야 다음 단계 실행 가능
    for (let i = 1; i < stepId; i++) {
      if (stepStatus[i] !== 'completed') {
        return false;
      }
    }
    return true;
  };

  const getStepButtonText = (step) => {
    if (stepStatus[step.id] === 'running') {
      return (
        <>
          <LoadingSpinner />
          처리 중...
        </>
      );
    } else if (stepStatus[step.id] === 'completed') {
      return '완료됨';
    } else if (stepStatus[step.id] === 'failed') {
      return '다시 시도';
    } else {
      return `${step.id}단계 실행`;
    }
  };

  const renderStepResults = (stepId) => {
    const results = stepResults[stepId];
    if (!results) return null;

    switch (stepId) {
      case 1:
        return (
          <ResultsContainer>
            <ResultsTitle>📊 데이터 로딩 결과</ResultsTitle>
            <ResultsGrid>
              <ResultItem>
                <ResultLabel>세션 ID</ResultLabel>
                <ResultValue>{results.session_id || 'N/A'}</ResultValue>
              </ResultItem>
              <ResultItem>
                <ResultLabel>데이터 요약</ResultLabel>
                <ResultValue>{JSON.stringify(results.data_summary || {})}</ResultValue>
              </ResultItem>
            </ResultsGrid>
          </ResultsContainer>
        );

      case 2:
        return (
          <ResultsContainer>
            <ResultsTitle>🔧 전처리 결과</ResultsTitle>
            <ResultsGrid>
              <ResultItem>
                <ResultLabel>처리된 작업 수</ResultLabel>
                <ResultValue>{results.processed_jobs || 0}개</ResultValue>
              </ResultItem>
              <ResultItem>
                <ResultLabel>기계 제약사항</ResultLabel>
                <ResultValue>{JSON.stringify(results.machine_constraints || {})}</ResultValue>
              </ResultItem>
            </ResultsGrid>
          </ResultsContainer>
        );

      case 3:
        return (
          <ResultsContainer>
            <ResultsTitle>📈 수율 예측 결과</ResultsTitle>
            <ResultsGrid>
              <ResultItem>
                <ResultLabel>예측된 수율 수</ResultLabel>
                <ResultValue>{results.predicted_yields || 0}개</ResultValue>
              </ResultItem>
              <ResultItem>
                <ResultLabel>평균 수율</ResultLabel>
                <ResultValue>{results.average_yield ? `${(results.average_yield * 100).toFixed(1)}%` : 'N/A'}</ResultValue>
              </ResultItem>
            </ResultsGrid>
          </ResultsContainer>
        );

      case 4:
        return (
          <ResultsContainer>
            <ResultsTitle>🕸️ DAG 생성 결과</ResultsTitle>
            <ResultsGrid>
              <ResultItem>
                <ResultLabel>DAG 노드 수</ResultLabel>
                <ResultValue>{results.dag_nodes || 0}개</ResultValue>
              </ResultItem>
              <ResultItem>
                <ResultLabel>기계 수</ResultLabel>
                <ResultValue>{results.machines || 0}대</ResultValue>
              </ResultItem>
            </ResultsGrid>
          </ResultsContainer>
        );

      case 5:
        return (
          <ResultsContainer>
            <ResultsTitle>⏰ 스케줄링 결과</ResultsTitle>
            <ResultsGrid>
              <ResultItem>
                <ResultLabel>스케줄링 상태</ResultLabel>
                <ResultValue>{results.status || 'N/A'}</ResultValue>
              </ResultItem>
              <ResultItem>
                <ResultLabel>처리된 작업</ResultLabel>
                <ResultValue>{results.scheduled_jobs || 0}개</ResultValue>
              </ResultItem>
            </ResultsGrid>
          </ResultsContainer>
        );

      case 6:
        return (
          <ResultsContainer>
            <ResultsTitle>📋 최종 결과</ResultsTitle>
            <ResultsGrid>
              <ResultItem>
                <ResultLabel>지각 주문 수</ResultLabel>
                <ResultValue>{results.late_orders || 0}개</ResultValue>
              </ResultItem>
              <ResultItem>
                <ResultLabel>결과 요약</ResultLabel>
                <ResultValue>{JSON.stringify(results.results_summary || {})}</ResultValue>
              </ResultItem>
            </ResultsGrid>
          </ResultsContainer>
        );

      default:
        return null;
    }
  };

  return (
    <Container>
      <Header>
        <h1>단계별 스케줄링 시스템</h1>
        <p>각 단계를 순차적으로 실행하여 최적의 생산 일정을 생성합니다.</p>
      </Header>

      <DataForm>
        <FormTitle>스케줄링 설정</FormTitle>
        <FormGroup>
          <label>스케줄링 윈도우 (일)</label>
          <input
            type="number"
            value={formData.windowDays}
            onChange={(e) => setFormData(prev => ({ 
              ...prev, 
              windowDays: parseInt(e.target.value) || 5 
            }))}
            min="1"
            max="30"
          />
        </FormGroup>
        {sessionId && (
          <FormGroup>
            <label>세션 ID</label>
            <input
              type="text"
              value={sessionId}
              readOnly
              style={{ backgroundColor: '#f8f9fa' }}
            />
          </FormGroup>
        )}
      </DataForm>

      <StepsContainer>
        {steps.map(step => (
          <StepCard key={step.id} status={stepStatus[step.id]}>
            <StepHeader status={stepStatus[step.id]}>
              <div className="step-number">{step.id}</div>
              <div className="step-title">{step.title}</div>
            </StepHeader>
            
            <StepDescription>{step.description}</StepDescription>
            
            <StepButton
              status={stepStatus[step.id]}
              onClick={() => executeStep(step)}
              disabled={!isStepEnabled(step.id) || stepStatus[step.id] === 'running'}
            >
              {getStepButtonText(step)}
            </StepButton>
            
            {stepMessages[step.id] && (
              <StatusMessage type={
                stepStatus[step.id] === 'completed' ? 'success' :
                stepStatus[step.id] === 'failed' ? 'error' : 'info'
              }>
                {stepMessages[step.id]}
              </StatusMessage>
            )}
            
            {stepStatus[step.id] === 'completed' && renderStepResults(step.id)}
          </StepCard>
        ))}
      </StepsContainer>
    </Container>
  );
};

export default StepByStepScheduling;
