/**
 * Python API 서비스
 * Python 백엔드 서버와의 통신을 담당
 */

const axios = require('axios');
const logger = require('../utils/logger');

class PythonApiService {
  constructor() {
    this.baseURL = process.env.PYTHON_API_URL || 'http://localhost:8000';
    this.timeout = 300000; // 5분 타임아웃
    
    // Axios 인스턴스 생성
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });

    // 요청 인터셉터
    this.client.interceptors.request.use(
      (config) => {
        logger.info(`Python API 요청: ${config.method.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        logger.error('Python API 요청 오류:', error);
        return Promise.reject(error);
      }
    );

    // 응답 인터셉터
    this.client.interceptors.response.use(
      (response) => {
        logger.info(`Python API 응답: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        logger.error('Python API 응답 오류:', {
          status: error.response?.status,
          statusText: error.response?.statusText,
          url: error.config?.url,
          message: error.message
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Python API 헬스 체크
   */
  async healthCheck() {
    try {
      const response = await this.client.get('/health');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * 1단계: 데이터 로딩 (직접 데이터)
   */
  async loadData(data) {
    try {
      const response = await this.client.post('/api/v1/stage1/load-data', data);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '데이터 로딩');
    }
  }

  /**
   * 1단계: 외부 API에서 데이터 로딩
   */
  async loadExternalData(apiConfig) {
    try {
      const response = await this.client.post('/api/v1/stage1/load-external-data', {
        api_config: apiConfig
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '외부 데이터 로딩');
    }
  }

  /**
   * 2단계: 전처리
   */
  async preprocessing(sessionId) {
    try {
      const response = await this.client.post('/api/v1/stage2/preprocessing', {
        session_id: sessionId
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '전처리');
    }
  }

  /**
   * 3단계: 수율 예측
   */
  async yieldPrediction(sessionId) {
    try {
      const response = await this.client.post('/api/v1/stage3/yield-prediction', {
        session_id: sessionId
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '수율 예측');
    }
  }

  /**
   * 4단계: DAG 생성
   */
  async dagCreation(sessionId) {
    try {
      const response = await this.client.post('/api/v1/stage4/dag-creation', {
        session_id: sessionId
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, 'DAG 생성');
    }
  }

  /**
   * 5단계: 스케줄링 실행
   */
  async scheduling(sessionId, windowDays = 5) {
    try {
      const response = await this.client.post('/api/v1/stage5/scheduling', {
        session_id: sessionId,
        window_days: windowDays
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '스케줄링 실행');
    }
  }

  /**
   * 6단계: 결과 후처리
   */
  async results(sessionId) {
    try {
      const response = await this.client.post('/api/v1/stage6/results', {
        session_id: sessionId
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '결과 후처리');
    }
  }

  /**
   * 전체 파이프라인 실행
   */
  async fullScheduling(data, windowDays = 5) {
    try {
      const response = await this.client.post('/api/v1/full-scheduling', {
        data: data,
        window_days: windowDays
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '전체 스케줄링');
    }
  }

  /**
   * 세션 상태 조회
   */
  async getSessionStatus(sessionId) {
    try {
      const response = await this.client.get(`/api/v1/session/${sessionId}/status`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '세션 상태 조회');
    }
  }

  /**
   * 세션 삭제
   */
  async clearSession(sessionId) {
    try {
      const response = await this.client.delete(`/api/v1/session/${sessionId}`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      throw this.handleError(error, '세션 삭제');
    }
  }

  /**
   * 에러 처리
   */
  handleError(error, operation) {
    const errorInfo = {
      operation,
      message: error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data
    };

    logger.error(`Python API ${operation} 실패:`, errorInfo);

    // HTTP 상태 코드에 따른 에러 메시지
    if (error.response) {
      switch (error.response.status) {
        case 404:
          return new Error(`${operation} 실패: 요청한 리소스를 찾을 수 없습니다.`);
        case 500:
          return new Error(`${operation} 실패: 서버 내부 오류가 발생했습니다.`);
        case 503:
          return new Error(`${operation} 실패: 서비스를 사용할 수 없습니다.`);
        default:
          return new Error(`${operation} 실패: ${error.response.data?.detail || error.message}`);
      }
    } else if (error.code === 'ECONNREFUSED') {
      return new Error(`${operation} 실패: Python API 서버에 연결할 수 없습니다.`);
    } else if (error.code === 'ETIMEDOUT') {
      return new Error(`${operation} 실패: 요청 시간이 초과되었습니다.`);
    } else {
      return new Error(`${operation} 실패: ${error.message}`);
    }
  }
}

module.exports = new PythonApiService();
