import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import './ProgressMonitor.css';

interface ProgressStep {
  id: number;
  run_id: string;
  step: string;
  step_name: string;
  status: string;
  progress_percent: number;
  current_item?: string;
  processed_count: number;
  total_count: number;
  message?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

interface ProgressMonitorProps {
  runId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

const ProgressMonitor: React.FC<ProgressMonitorProps> = ({ 
  runId, 
  onComplete, 
  onError 
}) => {
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [currentStep, setCurrentStep] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isRunning && runId) {
      // Poll for progress updates every 1 second
      interval = setInterval(async () => {
        try {
          await fetchProgress();
          await fetchCurrentStep();
        } catch (err) {
          console.error('Error fetching progress:', err);
          setError('진행상황을 가져오는 중 오류가 발생했습니다.');
          setIsRunning(false);
          onError?.('진행상황을 가져오는 중 오류가 발생했습니다.');
        }
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [runId, isRunning]);

  const fetchProgress = async () => {
    try {
      const progressData = await apiService.getScheduleProgress(runId);
      setSteps(progressData);
    } catch (err) {
      console.error('Error fetching progress steps:', err);
    }
  };

  const fetchCurrentStep = async () => {
    try {
      const current = await apiService.getCurrentProgress(runId);
      setCurrentStep(current);
      
      if (current.status === 'all_completed') {
        setIsRunning(false);
        onComplete?.();
      } else if (current.status === 'not_running') {
        // Check if any step failed
        const failedStep = steps.find(step => step.status === 'failed');
        if (failedStep) {
          setIsRunning(false);
          setError(failedStep.error_message || '스케줄링 실행 중 오류가 발생했습니다.');
          onError?.(failedStep.error_message || '스케줄링 실행 중 오류가 발생했습니다.');
        }
      }
    } catch (err) {
      console.error('Error fetching current step:', err);
    }
  };

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '⚙️';
      case 'failed': return '❌';
      default: return '⏳';
    }
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed': return '#4caf50';
      case 'running': return '#ff9800';
      case 'failed': return '#f44336';
      default: return '#757575';
    }
  };

  const formatTime = (dateString: string | undefined) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleTimeString('ko-KR');
  };

  const calculateOverallProgress = () => {
    if (steps.length === 0) return 0;
    const totalProgress = steps.reduce((sum, step) => sum + step.progress_percent, 0);
    return Math.round(totalProgress / steps.length);
  };

  return (
    <div className="progress-monitor">
      <div className="progress-header">
        <h3>스케줄링 진행상황</h3>
        <div className="overall-progress">
          <div className="progress-circle">
            <span className="progress-text">{calculateOverallProgress()}%</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="progress-steps">
        {steps.map((step, index) => (
          <div key={step.id} className={`step ${step.status}`}>
            <div className="step-header">
              <div className="step-indicator">
                <span className="step-number">{index + 1}</span>
                <span className="step-icon">{getStepIcon(step.status)}</span>
              </div>
              <div className="step-info">
                <h4 className="step-name">{step.step_name}</h4>
                <p className="step-message">{step.message}</p>
                {step.error_message && (
                  <p className="step-error">{step.error_message}</p>
                )}
                
                {/* 중간 결과 정보 표시 */}
                {step.step === 'scheduling' && step.message && (
                  <div className="intermediate-results">
                    {step.message.includes('노드') && (
                      <div className="result-info dag-info">
                        <span className="result-label">📊 DAG 정보:</span>
                        <span className="result-value">{step.message}</span>
                      </div>
                    )}
                    {step.message.includes('데이터 로딩') && (
                      <div className="result-info data-info">
                        <span className="result-label">📂 데이터:</span>
                        <span className="result-value">{step.message}</span>
                      </div>
                    )}
                    {step.message.includes('전처리') && (
                      <div className="result-info preprocess-info">
                        <span className="result-label">⚙️ 전처리:</span>
                        <span className="result-value">{step.message}</span>
                      </div>
                    )}
                    {step.message.includes('초 경과') && (
                      <div className="result-info time-info">
                        <span className="result-label">⏱️ 실행 시간:</span>
                        <span className="result-value">{step.message}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="step-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ 
                      width: `${step.progress_percent}%`,
                      backgroundColor: getStepColor(step.status)
                    }}
                  />
                </div>
                <span className="progress-percent">{step.progress_percent.toFixed(1)}%</span>
              </div>
            </div>

            <div className="step-details">
              {step.current_item && (
                <div className="current-item">
                  현재: {step.current_item}
                </div>
              )}
              
              {step.total_count > 0 && (
                <div className="progress-count">
                  진행: {step.processed_count} / {step.total_count}
                </div>
              )}

              <div className="step-timing">
                {step.started_at && (
                  <span>시작: {formatTime(step.started_at)}</span>
                )}
                {step.completed_at && (
                  <span>완료: {formatTime(step.completed_at)}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {currentStep && currentStep.status === 'running' && (
        <div className="current-activity">
          <div className="activity-indicator">
            <div className="spinner"></div>
          </div>
          <div className="activity-info">
            <strong>{currentStep.step_name}</strong>
            <p>{currentStep.message}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProgressMonitor;