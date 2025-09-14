/**
 * 프론트엔드 연동 예제
 * 이 파일은 프론트엔드에서 Node.js 백엔드와 연동하는 방법을 보여줍니다.
 */

// HTML에서 사용할 수 있는 JavaScript 코드
class SchedulingAPI {
  constructor(baseURL = 'http://localhost:3000') {
    this.baseURL = baseURL;
  }

  /**
   * API 요청 헬퍼 함수
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || 'API 요청 실패');
      }

      return data;
    } catch (error) {
      console.error('API 요청 오류:', error);
      throw error;
    }
  }

  /**
   * 전체 스케줄링 프로세스 실행
   */
  async runFullScheduling(data, windowDays = 5) {
    return await this.request('/api/scheduling/full', {
      method: 'POST',
      body: JSON.stringify({
        windowDays,
        data
      })
    });
  }

  /**
   * 1단계: 데이터 검증
   */
  async validateData(data) {
    return await this.request('/api/scheduling/validate', {
      method: 'POST',
      body: JSON.stringify({ data })
    });
  }

  /**
   * 2단계: 전처리
   */
  async runPreprocessing(sessionId, windowDays = 5) {
    return await this.request('/api/scheduling/preprocessing', {
      method: 'POST',
      body: JSON.stringify({ sessionId, windowDays })
    });
  }

  /**
   * 3단계: 수율 예측
   */
  async runYieldPrediction(sessionId) {
    return await this.request('/api/scheduling/yield-prediction', {
      method: 'POST',
      body: JSON.stringify({ sessionId })
    });
  }

  /**
   * 4단계: DAG 생성
   */
  async runDAGCreation(sessionId) {
    return await this.request('/api/scheduling/dag-creation', {
      method: 'POST',
      body: JSON.stringify({ sessionId })
    });
  }

  /**
   * 5단계: 스케줄링
   */
  async runScheduling(sessionId, windowDays = 5) {
    return await this.request('/api/scheduling/scheduling', {
      method: 'POST',
      body: JSON.stringify({ sessionId, windowDays })
    });
  }

  /**
   * 6단계: 결과 처리
   */
  async runResultsProcessing(sessionId) {
    return await this.request('/api/scheduling/results', {
      method: 'POST',
      body: JSON.stringify({ sessionId })
    });
  }

  /**
   * 세션 상태 조회
   */
  async getSessionStatus(sessionId) {
    return await this.request(`/api/scheduling/status/${sessionId}`);
  }

  /**
   * 헬스 체크
   */
  async healthCheck() {
    return await this.request('/api/scheduling/health');
  }
}

// 사용 예제
document.addEventListener('DOMContentLoaded', function() {
  const api = new SchedulingAPI();
  
  // 예제 데이터 (실제로는 서버에서 가져와야 함)
  const exampleData = {
    order_data: [],
    linespeed: [],
    operation_seperated_sequence: [],
    machine_master_info: [],
    yield_data: [],
    gitem_operation: [],
    operation_types: [],
    operation_delay_df: [],
    width_change_df: [],
    machine_rest: [],
    machine_allocate: [],
    machine_limit: []
  };

  // 전체 스케줄링 실행 버튼
  const runFullSchedulingBtn = document.getElementById('runFullScheduling');
  if (runFullSchedulingBtn) {
    runFullSchedulingBtn.addEventListener('click', async function() {
      try {
        console.log('전체 스케줄링 시작...');
        const result = await api.runFullScheduling(exampleData, 5);
        console.log('전체 스케줄링 완료:', result);
        
        // 결과를 화면에 표시
        displayResult(result);
      } catch (error) {
        console.error('전체 스케줄링 실패:', error);
        displayError(error);
      }
    });
  }

  // 단계별 실행 버튼들
  const stepButtons = {
    validate: document.getElementById('runValidation'),
    preprocessing: document.getElementById('runPreprocessing'),
    yieldPrediction: document.getElementById('runYieldPrediction'),
    dagCreation: document.getElementById('runDAGCreation'),
    scheduling: document.getElementById('runScheduling'),
    results: document.getElementById('runResults')
  };

  // 각 단계별 실행 함수
  stepButtons.validate?.addEventListener('click', async function() {
    try {
      const result = await api.validateData(exampleData);
      console.log('데이터 검증 완료:', result);
      displayResult(result);
    } catch (error) {
      console.error('데이터 검증 실패:', error);
      displayError(error);
    }
  });

  // 결과 표시 함수
  function displayResult(result) {
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
      resultDiv.innerHTML = `
        <h3>결과</h3>
        <pre>${JSON.stringify(result, null, 2)}</pre>
      `;
    }
  }

  // 에러 표시 함수
  function displayError(error) {
    const errorDiv = document.getElementById('error');
    if (errorDiv) {
      errorDiv.innerHTML = `
        <h3>에러</h3>
        <p>${error.message}</p>
      `;
    }
  }
});

// 모듈로 사용할 경우
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SchedulingAPI;
}


