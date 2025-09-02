import React, { useState, useEffect } from 'react';
import './App.css';
import { mockSchedulingService } from './services/mockScheduling';

function App() {
  const [orders, setOrders] = useState([]);
  const [currentProgress, setCurrentProgress] = useState([]);
  const [currentStep, setCurrentStep] = useState(null);
  const [isScheduling, setIsScheduling] = useState(false);
  const [runResults, setRunResults] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [startDate, setStartDate] = useState('2025-05-15');
  const [windowSize, setWindowSize] = useState(5);
  const [schedulingMethod, setSchedulingMethod] = useState('DispatchPriorityStrategy');

  useEffect(() => {
    // Load mock data on startup
    setOrders(mockSchedulingService.getMockOrders());
  }, []);

  const handleRunScheduling = async () => {
    try {
      setIsScheduling(true);
      setCurrentProgress([]);
      setCurrentStep(null);
      setRunResults(null);

      // Start step-by-step scheduling
      const progressInterval = setInterval(() => {
        const progress = mockSchedulingService.getProgress();
        const currentStep = mockSchedulingService.getCurrentStep();
        
        setCurrentProgress([...progress]);
        setCurrentStep(currentStep);

        if (!mockSchedulingService.isSchedulingRunning() && !mockSchedulingService.isWaitingForConfirmation()) {
          clearInterval(progressInterval);
        }
      }, 200);

      await mockSchedulingService.startScheduling('Mock Scheduling Run', {
        startDate: startDate,
        windowSize: windowSize,
        schedulingMethod: schedulingMethod
      });
      
      // Keep monitoring until completely finished
      const finalCheckInterval = setInterval(() => {
        const progress = mockSchedulingService.getProgress();
        const currentStep = mockSchedulingService.getCurrentStep();
        
        setCurrentProgress([...progress]);
        setCurrentStep(currentStep);

        if (!mockSchedulingService.isSchedulingRunning() && !mockSchedulingService.isWaitingForConfirmation()) {
          if (currentStep && currentStep.isComplete) {
            setRunResults({
              makespan: 523.5,
              totalOrders: 172,  // 생산 가능한 주문 수
              totalTasks: 470,
              totalLateDays: 0,
              unproducedOrders: 2,  // 생산하지 못한 주문 수
              results: mockSchedulingService.generateMockResults()
            });
            setIsScheduling(false);
            clearInterval(finalCheckInterval);
          }
        }
      }, 200);
      
    } catch (error) {
      console.error('스케줄링 실행 중 오류:', error);
      setIsScheduling(false);
    }
  };

  const handleConfirmStep = async () => {
    await mockSchedulingService.confirmCurrentStep();
  };

  const renderDashboard = () => (
    <div className="dashboard">
      <h2>생산 스케줄링 시스템</h2>
      
      <div className="stats-container">
        <div className="stat-card">
          <h3>📦 주문 현황</h3>
          <p className="stat-number">{orders.filter(order => order.status === '생산 가능').length}</p>
          <p className="stat-label">개 주문 생산 가능 (총 {orders.length}개)</p>
        </div>
        
        {runResults ? (
          <>
            <div className="stat-card success">
              <h3>⏱️ Makespan</h3>
              <p className="stat-number">{runResults.makespan}h</p>
              <p className="stat-label">총 소요 시간 ({Math.round(runResults.makespan * 2)} 슬롯)</p>
            </div>
            
            <div className="stat-card success">
              <h3>✅ 완료율</h3>
              <p className="stat-number">100%</p>
              <p className="stat-label">{runResults.totalTasks}개 작업</p>
            </div>
            
            <div className="stat-card success">
              <h3>🎯 정시 달성</h3>
              <p className="stat-number">{runResults.totalLateDays}</p>
              <p className="stat-label">지연 일수</p>
            </div>
          </>
        ) : (
          <>
            <div className="stat-card">
              <h3>⏱️ Makespan</h3>
              <p className="stat-number">-</p>
              <p className="stat-label">대기 중</p>
            </div>
            
            <div className="stat-card">
              <h3>📊 진행률</h3>
              <p className="stat-number">0%</p>
              <p className="stat-label">스케줄링 대기</p>
            </div>
            
            <div className="stat-card">
              <h3>⚙️ 스케줄링 방식</h3>
              <p className="stat-number" style={{fontSize: '1.2rem'}}>{schedulingMethod.replace('DispatchPriorityStrategy', 'Dispatch').replace('DAGBased', 'DAG')}</p>
              <p className="stat-label">선택됨</p>
            </div>
          </>
        )}
      </div>

      <div className="scheduling-config">
        <h3>스케줄링 설정</h3>
        <div className="config-form">
          <div className="form-group">
            <label htmlFor="startDate">스케줄링 시작일:</label>
            <input
              id="startDate"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={isScheduling}
              className="date-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="schedulingMethod">스케줄링 방식:</label>
            <select
              id="schedulingMethod"
              value={schedulingMethod}
              onChange={(e) => setSchedulingMethod(e.target.value)}
              disabled={isScheduling}
              className="select-input"
            >
              <option value="DispatchPriorityStrategy">Dispatch Priority Strategy</option>
              <option value="DAGBased">DAG 기반 스케줄링</option>
              <option value="FIFO">First In First Out</option>
              <option value="SPT">Shortest Processing Time</option>
              <option value="EDD">Earliest Due Date</option>
            </select>
          </div>
        </div>
      </div>

      <div className="action-section">
        <button 
          onClick={handleRunScheduling} 
          disabled={isScheduling}
          className="run-button"
        >
          {isScheduling ? '스케줄링 실행 중...' : '스케줄링 실행'}
        </button>
      </div>

      {isScheduling && (
        <div className="progress-section">
          <div className="progress-header">
            <h3>🔄 실시간 진행 상황</h3>
            {currentStep && (
              <div className="current-status">
                <span className="status-badge">{currentStep.percent}%</span>
                <span className="status-text">{currentStep.message}</span>
              </div>
            )}
          </div>
          
          {currentStep && (
            <div className="progress-visual">
              <div className="progress-steps">
                <div className={`step-indicator ${currentStep.percent > 25 ? 'completed' : currentStep.percent > 0 ? 'active' : ''}`}>
                  <div className="step-circle">1</div>
                  <div className="step-label">데이터 준비</div>
                </div>
                <div className={`step-indicator ${currentStep.percent > 30 ? 'completed' : currentStep.percent > 25 ? 'active' : ''}`}>
                  <div className="step-circle">2</div>
                  <div className="step-label">전처리</div>
                </div>
                <div className={`step-indicator ${currentStep.percent > 40 ? 'completed' : currentStep.percent > 30 ? 'active' : ''}`}>
                  <div className="step-circle">3</div>
                  <div className="step-label">수율 예측</div>
                </div>
                <div className={`step-indicator ${currentStep.percent > 60 ? 'completed' : currentStep.percent > 40 ? 'active' : ''}`}>
                  <div className="step-circle">4</div>
                  <div className="step-label">DAG 생성</div>
                </div>
                <div className={`step-indicator ${currentStep.percent >= 100 ? 'completed' : currentStep.percent > 60 ? 'active' : ''}`}>
                  <div className="step-circle">5</div>
                  <div className="step-label">스케줄링</div>
                </div>
              </div>
              
              <div className="progress-bar-container">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{width: `${currentStep.percent}%`}}
                  ></div>
                </div>
                <div className="progress-text">{currentStep.percent}% 완료</div>
              </div>
            </div>
          )}

          {/* Step-specific detailed information */}
          {currentStep && currentStep.needsConfirmation && (
            <div className="step-details-section">
              {currentStep.step === 'preprocessing' && (
                <div className="preprocessing-details">
                  <h4>🔧 전처리 결과</h4>
                  
                  <div className="detail-box">
                    <h5>📋 1. 기계 휴무 (machine_rest)</h5>
                    <div className="machine-issues">
                      <div className="issue-item">
                        <strong>1호기:</strong> 2025-05-20 09:00 ~ 17:00 정기점검
                      </div>
                      <div className="issue-item">
                        <strong>2호기:</strong> 2025-05-22 전일 설비보수
                      </div>
                      <div className="issue-item">
                        <strong>3호기:</strong> 2025-05-25 08:00 ~ 18:00 예방정비
                      </div>
                    </div>
                  </div>

                  <div className="detail-box">
                    <h5>⚠️ 2. 기계 할당 제한 (machine_allocate)</h5>
                    <div className="machine-issues">
                      <div className="issue-item">
                        <strong>GITEM 31704:</strong> 2호기, 3호기에서 생산 불가 (기계 규격 불일치)
                      </div>
                      <div className="issue-item">
                        <strong>GITEM 32023:</strong> 1호기에서 생산 불가 (공정 특성 불일치)
                      </div>
                      <div className="issue-item">
                        <strong>GITEM 30151:</strong> 3호기에서 생산 불가 (재료 호환성 문제)
                      </div>
                    </div>
                    
                    <h6>⚠️ 영향받는 GITEM:</h6>
                    <p className="unable-gitems">기계 할당 제한으로 생산하지 못하는 GITEM들: 31705, 32024</p>
                  </div>

                  <div className="detail-box">
                    <h5>🔧 3. 기계 제한 사항 (machine_limit)</h5>
                    <div className="machine-issues">
                      <div className="issue-item">
                        <strong>1호기:</strong> 최대 폭 1500mm 제한
                      </div>
                      <div className="issue-item">
                        <strong>2호기:</strong> 최대 길이 3000mm 제한
                      </div>
                      <div className="issue-item">
                        <strong>3호기:</strong> 최소 두께 0.5mm 제한
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {currentStep.step === 'yield_prediction' && (
                <div className="yield-details">
                  <h4>📊 수율 정보</h4>
                  <div className="detail-box">
                    <p><strong>평균 수율 사용</strong></p>
                    <p>수율 예측 방법: 평균 수율 94.5% 적용</p>
                    <p className="no-yield-info">실제 수율 데이터 부족으로 평균값 적용하여 진행합니다.</p>
                  </div>
                </div>
              )}

              {currentStep.step === 'dag_creation' && (
                <div className="dag-details">
                  <h4>🔗 DAG 생성</h4>
                  <div className="detail-box">
                    <p>총 474개 노드 생성 완료</p>
                    <p>4단계 공정 레벨 구성</p>
                    <p className="no-display-info">화면 표시: X (복잡도로 인해 생략)</p>
                  </div>
                  
                  <div className="detail-box">
                    <h5>📅 스케줄링 파라미터 설정</h5>
                    <div className="form-group">
                      <label htmlFor="windowSizeScheduling">Window Size (일):</label>
                      <input
                        id="windowSizeScheduling"
                        type="number"
                        value={windowSize}
                        onChange={(e) => setWindowSize(parseInt(e.target.value) || 5)}
                        min="1"
                        max="365"
                        className="number-input"
                        style={{ width: '120px' }}
                      />
                      <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
                        스케줄링 윈도우 크기를 설정하세요. (기본값: 5일)
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="confirmation-section">
                <button 
                  className="confirm-button" 
                  onClick={handleConfirmStep}
                >
                  확인 - 다음 단계로
                </button>
              </div>
            </div>
          )}

          <div className="progress-details">
            <h4>상세 진행 로그</h4>
            <div className="log-container">
              {currentProgress.map((step, index) => (
                <div key={index} className="log-entry">
                  <span className="log-time">{new Date(step.timestamp).toLocaleTimeString()}</span>
                  <span className="log-step">[{step.step}]</span>
                  <span className="log-percent">{step.percent}%</span>
                  <span className="log-message">{step.message}</span>
                  {step.details && step.details.length > 0 && (
                    <div className="log-details">
                      {step.details.map((detail, idx) => (
                        <div key={idx} className="detail-item">• {detail}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {runResults && (
        <div className="results-section">
          <div className="results-header">
            <h3>🎯 스케줄링 결과</h3>
            <div className="completion-badge">
              <span className="badge-icon">✅</span>
              <span>완료</span>
            </div>
          </div>
          
          <div className="results-grid">
            <div className="result-summary-card">
              <div className="card-header">
                <h4>📊 실행 결과</h4>
                <div className="success-indicator">성공</div>
              </div>
              <div className="summary-stats">
                <div className="stat-row">
                  <span className="stat-icon">⏱️</span>
                  <span className="stat-label">Makespan</span>
                  <span className="stat-value">{runResults.makespan} 시간</span>
                </div>
                <div className="stat-row">
                  <span className="stat-icon">📅</span>
                  <span className="stat-label">총 소요일</span>
                  <span className="stat-value">21.8 일</span>
                </div>
                <div className="stat-row">
                  <span className="stat-icon">📦</span>
                  <span className="stat-label">생산 주문</span>
                  <span className="stat-value">{runResults.totalOrders} 개</span>
                </div>
                <div className="stat-row">
                  <span className="stat-icon">⚠️</span>
                  <span className="stat-label">생산 불가</span>
                  <span className="stat-value">{runResults.unproducedOrders} 개</span>
                </div>
                <div className="stat-row">
                  <span className="stat-icon">🎯</span>
                  <span className="stat-label">지연 일수</span>
                  <span className="stat-value">{runResults.totalLateDays} 일</span>
                </div>
              </div>
            </div>

            <div className="parameters-card">
              <div className="card-header">
                <h4>⚙️ 설정 파라미터</h4>
              </div>
              <div className="parameter-list">
                <div className="parameter-item">
                  <span className="param-label">시작일</span>
                  <span className="param-value">{startDate}</span>
                </div>
                <div className="parameter-item">
                  <span className="param-label">Window Size</span>
                  <span className="param-value">{windowSize} 일</span>
                </div>
                <div className="parameter-item">
                  <span className="param-label">스케줄링 방식</span>
                  <span className="param-value">{schedulingMethod}</span>
                </div>
                <div className="parameter-item">
                  <span className="param-label">평균 수율</span>
                  <span className="param-value">94.5%</span>
                </div>
              </div>
            </div>
          </div>

          <div className="gantt-chart-section">
            <div className="chart-header">
              <h4>📊 간트 차트</h4>
              <div className="chart-info">
                <span>5개 기계 × 21.8일 스케줄</span>
              </div>
            </div>
            <div className="chart-container">
              <img 
                src={mockSchedulingService.generateGanttChart()} 
                alt="생산 스케줄링 간트 차트"
                className="gantt-chart-image"
              />
            </div>
          </div>

          <div className="actions-section">
            <button 
              className="download-btn excel-btn"
              onClick={() => mockSchedulingService.downloadExcelFile()}
            >
              <span className="btn-icon">📄</span>
              <span>엑셀 결과 다운로드</span>
            </button>
          </div>

          <div className="results-table">
            <div className="table-header">
              <h4>📋 주문 생산 요약</h4>
              <span className="table-count">{runResults.results.orderSummary.length}개 주문</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>P/O NO</th>
                  <th>GITEM</th>
                  <th>품목명</th>
                  <th>납기일</th>
                  <th>종료날짜</th>
                  <th>지각일수</th>
                </tr>
              </thead>
              <tbody>
                {runResults.results.orderSummary.map((order, index) => (
                  <tr key={index}>
                    <td>{order.poNo}</td>
                    <td>{order.gitem}</td>
                    <td>{order.gitemName}</td>
                    <td>{order.dueDate}</td>
                    <td>{order.endDate}</td>
                    <td className={order.lateDays > 0 ? 'late' : 'on-time'}>
                      {order.lateDays}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="unproduced-table">
            <div className="table-header">
              <h4>⚠️ 생산하지 못한 주문</h4>
              <span className="table-count">{runResults.results.unproducedOrders.length}개 주문</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>P/O NO</th>
                  <th>GITEM</th>
                  <th>품목명</th>
                  <th>납기일</th>
                  <th>생산 불가 사유</th>
                </tr>
              </thead>
              <tbody>
                {runResults.results.unproducedOrders.map((order, index) => (
                  <tr key={index} className="unproduced-row">
                    <td>{order.poNo}</td>
                    <td>{order.gitem}</td>
                    <td>{order.gitemName}</td>
                    <td>{order.dueDate}</td>
                    <td className="reason-cell">{order.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const renderOrders = () => (
    <div className="orders">
      <h2>주문 관리</h2>
      
      <div className="orders-table">
        <table>
          <thead>
            <tr>
              <th>P/O NO</th>
              <th>GITEM</th>
              <th>품목명</th>
              <th>폭(mm)</th>
              <th>길이(mm)</th>
              <th>의뢰량</th>
              <th>납기일</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            {orders.map(order => (
              <tr key={order.id} className={order.status === '생산 불가' ? 'unproducible' : ''}>
                <td>{order.poNo}</td>
                <td>{order.gitem}</td>
                <td>{order.gitemName}</td>
                <td>{order.width}</td>
                <td>{order.length}</td>
                <td>{order.requestAmount}</td>
                <td>{order.dueDate}</td>
                <td className={order.status === '생산 불가' ? 'status-unproducible' : 'status-producible'}>
                  {order.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="App">
      <header className="app-header">
        <h1>🏭 생산 스케줄링 시스템</h1>
        <div className="nav-tabs">
          <button 
            className={activeTab === 'dashboard' ? 'active' : ''} 
            onClick={() => setActiveTab('dashboard')}
          >
            스케줄링 대시보드
          </button>
          <button 
            className={activeTab === 'orders' ? 'active' : ''} 
            onClick={() => setActiveTab('orders')}
          >
            주문 관리
          </button>
        </div>
      </header>

      <main className="app-main">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'orders' && renderOrders()}
      </main>
    </div>
  );
}

export default App;