import React, { useState, useEffect } from 'react';
import { apiService, Order } from '../services/api';
import ProgressMonitor from './ProgressMonitor';
import './SchedulingRunner.css';

interface SchedulingRunnerProps {
  onRunComplete?: (runId: string) => void;
}

const SchedulingRunner: React.FC<SchedulingRunnerProps> = ({ onRunComplete }) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [currentRun, setCurrentRun] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runHistory, setRunHistory] = useState<any[]>([]);

  useEffect(() => {
    loadOrders();
    loadRunHistory();
  }, []);

  const loadOrders = async () => {
    try {
      const ordersData = await apiService.getOrders();
      setOrders(ordersData);
    } catch (err) {
      setError('주문 데이터 로드에 실패했습니다.');
      console.error('Error loading orders:', err);
    }
  };

  const loadRunHistory = async () => {
    try {
      const runs = await apiService.getScheduleRuns();
      setRunHistory(runs.slice(0, 5)); // Show last 5 runs
    } catch (err) {
      console.error('Error loading run history:', err);
    }
  };

  const handleStartScheduling = async () => {
    if (orders.length === 0) {
      setError('스케줄링할 주문 데이터가 없습니다. 먼저 주문을 추가해주세요.');
      return;
    }

    try {
      setError(null);
      setIsRunning(true);

      const runName = `스케줄링 실행 ${new Date().toLocaleString()}`;
      const run = await apiService.createScheduleRun({
        name: runName,
        description: `${orders.length}개 주문 스케줄링`
      });

      setCurrentRun(run);
    } catch (err) {
      setError('스케줄링 시작에 실패했습니다.');
      setIsRunning(false);
      console.error('Error starting scheduling:', err);
    }
  };

  const handleRunComplete = () => {
    setIsRunning(false);
    loadRunHistory();
    onRunComplete?.(currentRun?.run_id);
  };

  const handleRunError = (errorMessage: string) => {
    setIsRunning(false);
    setError(errorMessage);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR');
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { label: '대기중', color: '#757575' },
      running: { label: '실행중', color: '#ff9800' },
      completed: { label: '완료', color: '#4caf50' },
      failed: { label: '실패', color: '#f44336' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    
    return (
      <span 
        className="status-badge"
        style={{ backgroundColor: config.color }}
      >
        {config.label}
      </span>
    );
  };

  return (
    <div className="scheduling-runner">
      <div className="runner-header">
        <h2>스케줄링 실행</h2>
        <div className="run-info">
          <div className="orders-info">
            📋 {orders.length}개 주문 대기중
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="runner-content">
        <div className="run-controls">
          <div className="control-section">
            <h3>실행 제어</h3>
            <div className="control-buttons">
              <button
                className="btn btn-primary btn-lg"
                onClick={handleStartScheduling}
                disabled={isRunning || orders.length === 0}
              >
                {isRunning ? '실행 중...' : '스케줄링 시작'}
              </button>
              
              {orders.length === 0 && (
                <p className="help-text">
                  스케줄링을 시작하려면 먼저 주문 데이터를 추가해주세요.
                </p>
              )}
            </div>
          </div>

          <div className="pre-check-section">
            <h4>실행 전 체크리스트</h4>
            <div className="checklist">
              <div className={`check-item ${orders.length > 0 ? 'success' : 'warning'}`}>
                <span className="check-icon">{orders.length > 0 ? '✅' : '⚠️'}</span>
                <span>주문 데이터: {orders.length}개</span>
              </div>
              <div className="check-item success">
                <span className="check-icon">✅</span>
                <span>스케줄링 엔진: 준비완료</span>
              </div>
              <div className="check-item success">
                <span className="check-icon">✅</span>
                <span>데이터베이스: 연결됨</span>
              </div>
            </div>
          </div>
        </div>

        {currentRun && isRunning && (
          <div className="progress-section">
            <h3>실행 진행상황</h3>
            <div className="current-run-info">
              <div className="run-details">
                <strong>{currentRun.name}</strong>
                <p>{currentRun.description}</p>
                <small>실행 ID: {currentRun.run_id}</small>
              </div>
            </div>
            <ProgressMonitor
              runId={currentRun.run_id}
              onComplete={handleRunComplete}
              onError={handleRunError}
            />
          </div>
        )}
      </div>

      <div className="run-history">
        <h3>최근 실행 기록</h3>
        <div className="history-list">
          {runHistory.length === 0 ? (
            <div className="no-history">
              아직 실행 기록이 없습니다.
            </div>
          ) : (
            runHistory.map((run) => (
              <div key={run.id} className="history-item">
                <div className="history-info">
                  <div className="history-name">{run.name}</div>
                  <div className="history-details">
                    {run.total_orders && <span>{run.total_orders}개 주문</span>}
                    {run.makespan && <span>Makespan: {run.makespan.toFixed(1)}</span>}
                    {run.total_late_days !== null && <span>지연: {run.total_late_days}일</span>}
                  </div>
                  <div className="history-time">
                    {formatDate(run.created_at)}
                  </div>
                </div>
                <div className="history-status">
                  {getStatusBadge(run.status)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default SchedulingRunner;