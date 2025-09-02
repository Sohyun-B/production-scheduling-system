// Mock scheduling service that simulates your Python scheduling process
// This replaces the backend entirely with realistic simulation

export class MockSchedulingService {
  constructor() {
    this.isRunning = false;
    this.progress = [];
    this.currentStep = null;
    this.stepResults = {};
    this.waitingForUserConfirmation = false;
  }

  // Step-by-step scheduling with user confirmation
  async startScheduling(runName, config = {}) {
    this.config = {
      startDate: config.startDate || '2025-05-15',
      windowSize: config.windowSize || 5,
      schedulingMethod: config.schedulingMethod || 'DispatchPriorityStrategy'
    };
    if (this.isRunning) {
      throw new Error('스케줄링이 이미 실행 중입니다.');
    }

    this.isRunning = true;
    this.progress = [];
    this.stepResults = {};
    
    const runId = `mock-${Date.now()}`;
    
    // Step 1: Data Loading (automatic)
    await this.executeDataLoading();
    
    // Step 2: Preprocessing (needs user confirmation)
    await this.executePreprocessing();
    
    return runId;
  }

  async executeDataLoading() {
    const steps = [
      { percent: 5, message: 'Python 스케줄링 엔진 시작' },
      { percent: 10, message: '설정 데이터 로딩 중...', details: [
        '라인스피드 997개, 기계정보 8개',
        `스케줄링 시작일: ${this.config.startDate}`,
        `Window Size: ${this.config.windowSize}일`,
        `스케줄링 방식: ${this.config.schedulingMethod}`
      ] },
      { percent: 15, message: '공정 분류 데이터 로딩 중...', details: ['공정분류 37개, 지연정보 37개'] },
      { percent: 20, message: '기계 제약 데이터 로딩 중...', details: ['기계할당 0개, 기계제한 0개'] },
      { percent: 25, message: '주문 데이터 로딩 완료', details: ['총 174개 주문 로딩 완료'] },
    ];

    for (const step of steps) {
      await new Promise(resolve => setTimeout(resolve, 500));
      this.currentStep = {
        step: 'data_loading',
        name: '데이터 로딩',
        ...step,
        timestamp: new Date().toISOString()
      };
      this.progress.push(this.currentStep);
    }
  }

  async executePreprocessing() {
    // 불가능한 공정 입력값.xlsx 기준 3가지 제약조건
    const constraints = {
      // 1. 기계 휴무 (machine_rest)
      machineRest: [
        { machine: 'T0915', date: '2025-05-20', reason: '정기점검' },
        { machine: 'T02149', date: '2025-05-22', reason: '설비보수' },
        { machine: 'T02299', date: '2025-05-25', reason: '예방정비' }
      ],
      
      // 2. 기계 할당 제한 (machine_allocate)  
      machineAllocate: [
        { gitem: '31704', impossibleMachines: ['T02149', 'T02299'], reason: '기계 규격 불일치' },
        { gitem: '32023', impossibleMachines: ['T0915'], reason: '공정 특성 불일치' },
        { gitem: '30151', impossibleMachines: ['T02299'], reason: '재료 호환성 문제' }
      ],
      
      // 3. 기계 제한 사항 (machine_limit)
      machineLimit: [
        { machine: 'T0915', maxWidth: 1500, reason: '최대 폭 제한' },
        { machine: 'T02149', maxLength: 3000, reason: '최대 길이 제한' },
        { machine: 'T02299', minThickness: 0.5, reason: '최소 두께 제한' }
      ]
    };

    // 영향받는 주문 분석
    const affectedOrders = [
      { poNo: 'SW1250407101', gitem: '31704', issue: 'T02149, T02299 사용 불가', type: '기계 할당 제한' },
      { poNo: 'SW1250503301', gitem: '32023', issue: 'T0915 사용 불가', type: '기계 할당 제한' },
      { poNo: 'SW1250502301', gitem: '30151', issue: 'T02299 사용 불가', type: '기계 할당 제한' }
    ];
    
    this.stepResults.preprocessing = {
      constraints,
      affectedOrders,
      totalConstraints: constraints.machineRest.length + constraints.machineAllocate.length + constraints.machineLimit.length
    };

    this.currentStep = {
      step: 'preprocessing',
      name: '전처리',
      percent: 30,
      message: '전처리 분석 완료 - 제약조건 확인',
      details: [`제약조건: ${this.stepResults.preprocessing.totalConstraints}개`, `영향받는 주문: ${affectedOrders.length}개`],
      timestamp: new Date().toISOString(),
      needsConfirmation: true
    };
    
    this.progress.push(this.currentStep);
    this.waitingForUserConfirmation = true;
  }

  async executeYieldPrediction() {
    this.waitingForUserConfirmation = false;
    
    this.stepResults.yieldPrediction = {
      method: '평균 수율 사용',
      averageYield: 94.5,
      note: '실제 수율 데이터 부족으로 평균값 적용'
    };

    this.currentStep = {
      step: 'yield_prediction',
      name: '수율 예측',
      percent: 40,
      message: '수율 예측 완료 - 평균 수율 적용',
      details: ['평균 수율 94.5% 사용', '실제 수율 데이터 부족'],
      timestamp: new Date().toISOString(),
      needsConfirmation: true
    };
    
    this.progress.push(this.currentStep);
    this.waitingForUserConfirmation = true;
  }

  async executeDAGCreation() {
    this.waitingForUserConfirmation = false;
    
    this.stepResults.dagCreation = {
      totalNodes: 474,
      levels: 4,
      status: 'DAG 생성은 화면에 표시하지 않음'
    };

    this.currentStep = {
      step: 'dag_creation',
      name: 'DAG 생성',
      percent: 60,
      message: 'DAG 생성 완료',
      details: ['총 474개 노드 생성', '4단계 공정 레벨', '화면 표시: X'],
      timestamp: new Date().toISOString(),
      needsConfirmation: true
    };
    
    this.progress.push(this.currentStep);
    this.waitingForUserConfirmation = true;
  }

  async executeScheduling() {
    this.waitingForUserConfirmation = false;
    
    // 스케줄링 실행 중 진행 표시
    const schedulingSteps = [
      { percent: 65, message: '스케줄링 알고리즘 초기화 중...' },
      { percent: 70, message: '디스패치 규칙 생성 중...' },
      { percent: 75, message: '기계 자원 할당 중...' },
      { percent: 85, message: '스케줄링 실행 완료!' },
    ];

    for (const step of schedulingSteps) {
      await new Promise(resolve => setTimeout(resolve, 800));
      this.currentStep = {
        step: 'scheduling',
        name: '스케줄링 실행',
        ...step,
        timestamp: new Date().toISOString()
      };
      this.progress.push(this.currentStep);
    }
    
    // 스케줄링 결과 생성
    this.stepResults.scheduling = {
      makespan: 1047.0,
      totalDays: 21.8,
      ganttChart: this.generateGanttChart(),
      excelFile: '스케줄링결과.xlsx'
    };

    this.currentStep = {
      step: 'scheduling',
      name: '스케줄링 완료',
      percent: 100,
      message: '스케줄링 완료!',
      details: [
        `총 걸리는 시간: 1047시간`,
        `총 소요일: 21.8일`,
        `간트 차트: 생성 완료`,
        `엑셀 파일: 저장 가능`
      ],
      timestamp: new Date().toISOString(),
      isComplete: true
    };
    
    this.progress.push(this.currentStep);
    this.isRunning = false;
    
    // Generate final results
    const mockResults = this.generateMockResults();
    
    return {
      runId: `mock-${Date.now()}`,
      status: 'completed',
      makespan: 1047.0,
      totalOrders: 174,
      totalTasks: 474,
      totalLateDays: 0,
      results: mockResults
    };
  }

  getAffectedOrders(unableGitems) {
    // Mock affected orders
    return [
      { poNo: 'SW1250407101', gitem: '31704', gitemName: 'PPF필름', reason: 'T0915 정기점검' },
      { poNo: 'SW1250503301', gitem: '32023', gitemName: '윈드실드', reason: 'T02149 기계고장' }
    ];
  }

  // User confirms current step and moves to next
  async confirmCurrentStep() {
    if (!this.waitingForUserConfirmation) return;
    
    const currentStepName = this.currentStep.step;
    
    switch (currentStepName) {
      case 'preprocessing':
        await this.executeYieldPrediction();
        break;
      case 'yield_prediction':
        await this.executeDAGCreation();
        break;
      case 'dag_creation':
        await this.executeScheduling();
        break;
      default:
        this.waitingForUserConfirmation = false;
    }
  }

  generateMockResults() {
    // Generate realistic mock scheduling results based on your actual data
    const mockOrders = [
      { poNo: 'SW1250407101', gitem: '31704', gitemName: 'PPF필름', dueDate: '2025-05-21', endDate: '2025-05-15', lateDays: 0 },
      { poNo: 'SW1250503301', gitem: '32023', gitemName: '윈드실드', dueDate: '2025-05-22', endDate: '2025-05-15', lateDays: 0 },
      { poNo: 'SW1250503601', gitem: '32528', gitemName: '팬텀 S/R', dueDate: '2025-05-25', endDate: '2025-05-15', lateDays: 0 },
      { poNo: 'SW1250502301', gitem: '30151', gitemName: '방충필름', dueDate: '2025-05-20', endDate: '2025-05-15', lateDays: 0 },
      { poNo: 'SW1250506104', gitem: '31539', gitemName: '보호필름', dueDate: '2025-05-28', endDate: '2025-05-15', lateDays: 0 }
    ];

    const mockMachineInfo = [
      { poNo: 'SW1250407101', gitem: '31704', machineCode: 'T0915', machineName: '코팅기1호', startTime: 0, endTime: 48, workTime: 48 },
      { poNo: 'SW1250503301', gitem: '32023', machineCode: 'T0915', machineName: '코팅기1호', startTime: 48, endTime: 96, workTime: 48 },
      { poNo: 'SW1250503601', gitem: '32528', machineCode: 'T02149', machineName: '슬리터2호', startTime: 0, endTime: 72, workTime: 72 },
      { poNo: 'SW1250502301', gitem: '30151', machineCode: 'T02159', machineName: '슬리터3호', startTime: 0, endTime: 60, workTime: 60 },
      { poNo: 'SW1250506104', gitem: '31539', machineCode: 'T02299', machineName: '검사기1호', startTime: 96, endTime: 120, workTime: 24 }
    ];

    return {
      orderSummary: mockOrders,
      machineInfo: mockMachineInfo,
      totalMakespan: 1047.0,
      totalDays: 21.8,
      efficiency: 95.2
    };
  }

  getProgress() {
    return this.progress;
  }

  getCurrentStep() {
    return this.currentStep;
  }

  isSchedulingRunning() {
    return this.isRunning;
  }

  isWaitingForConfirmation() {
    return this.waitingForUserConfirmation;
  }

  getStepResults() {
    return this.stepResults;
  }

  // Generate fake Gantt chart for display (no download)
  generateGanttChart() {
    const canvas = document.createElement('canvas');
    canvas.width = 1000;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    
    // Background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 1000, 400);
    
    // Title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 18px Arial';
    ctx.fillText('생산 스케줄링 간트 차트', 20, 30);
    
    // Time axis
    ctx.font = '12px Arial';
    ctx.fillStyle = '#666';
    for (let day = 0; day <= 21; day += 3) {
      const x = 120 + (day / 21) * 800;
      ctx.fillText(`${day}일`, x, 55);
      ctx.beginPath();
      ctx.moveTo(x, 60);
      ctx.lineTo(x, 370);
      ctx.strokeStyle = '#ddd';
      ctx.stroke();
    }
    
    // Machine labels and bars
    const machines = ['T0915 (코팅기)', 'T02149 (슬리터)', 'T02159 (슬리터)', 'T02299 (검사기)'];
    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'];
    
    machines.forEach((machine, i) => {
      const y = 80 + i * 70;
      
      // Machine label
      ctx.fillStyle = '#333';
      ctx.font = '14px Arial';
      ctx.fillText(machine, 10, y + 20);
      
      // Work bars for this machine
      const workSlots = [
        { start: 0, duration: 3, task: 'PPF필름' },
        { start: 3, duration: 4, task: '윈드실드' },
        { start: 8, duration: 2, task: '팬텀 S/R' },
        { start: 12, duration: 5, task: '보호필름' },
        { start: 18, duration: 3, task: '방충필름' }
      ];
      
      workSlots.forEach((slot, j) => {
        if (j < 3) { // Only show some slots per machine
          const startX = 120 + (slot.start / 21) * 800;
          const width = (slot.duration / 21) * 800;
          
          ctx.fillStyle = colors[i];
          ctx.fillRect(startX, y, width, 40);
          
          // Task text
          ctx.fillStyle = '#fff';
          ctx.font = '11px Arial';
          ctx.fillText(slot.task, startX + 5, y + 25);
        }
      });
    });
    
    // Convert to data URL
    return canvas.toDataURL();
  }

  // Generate Excel file (mock)
  downloadExcelFile() {
    const data = [
      ['P/O NO', 'GITEM', '품목명', '납기일', '종료날짜', '지각일수'],
      ['SW1250407101', '31704', 'PPF필름', '2025-05-21', '2025-05-15', '0'],
      ['SW1250503301', '32023', '윈드실드', '2025-05-22', '2025-05-15', '0'],
      ['SW1250503601', '32528', '팬텀 S/R', '2025-05-25', '2025-05-15', '0'],
      ['SW1250502301', '30151', '방충필름', '2025-05-20', '2025-05-15', '0'],
      ['SW1250506104', '31539', '보호필름', '2025-05-28', '2025-05-15', '0']
    ];
    
    let csvContent = data.map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '스케줄링결과.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Mock data for orders (replaces database)
  getMockOrders() {
    return [
      { id: 1, poNo: 'SW1250407101', gitem: '31704', gitemName: 'PPF필름', width: 1524, length: 15, requestAmount: 20, dueDate: '2025-05-21' },
      { id: 2, poNo: 'SW1250503301', gitem: '32023', gitemName: '윈드실드', width: 1220, length: 143, requestAmount: 15, dueDate: '2025-05-22' },
      { id: 3, poNo: 'SW1250503601', gitem: '32528', gitemName: '팬텀 S/R', width: 914, length: 84, requestAmount: 25, dueDate: '2025-05-25' },
      { id: 4, poNo: 'SW1250502301', gitem: '30151', gitemName: '방충필름', width: 609, length: 30, requestAmount: 18, dueDate: '2025-05-20' },
      { id: 5, poNo: 'SW1250506104', gitem: '31539', gitemName: '보호필름', width: 1524, length: 50, requestAmount: 12, dueDate: '2025-05-28' }
    ];
  }
}

export const mockSchedulingService = new MockSchedulingService();