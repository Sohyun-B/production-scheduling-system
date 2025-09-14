/**
 * Python FastAPI 서버 연동 서비스
 */
const axios = require('axios');
const config = require('../../config');
const logger = require('../utils/logger');

class PythonApiService {
  constructor() {
    this.client = axios.create({
      baseURL: config.pythonApi.baseUrl,
      timeout: config.pythonApi.timeout,
      headers: {
        'Content-Type': 'application/json'
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
          url: error.config?.url,
          status: error.response?.status,
          message: error.message,
          data: error.response?.data
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * 1단계: 데이터 검증
   */
  async validateData(sessionId, data) {
    try {
      logger.info(`데이터 검증 시작: ${sessionId}`);
      
      const response = await this.client.post(config.pythonApi.endpoints.validation, {
        session_id: sessionId,
        ...data
      });

      logger.info(`데이터 검증 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`데이터 검증 실패: ${sessionId}`, error);
      throw this.handleError(error, '데이터 검증');
    }
  }

  /**
   * 1단계: 데이터 검증 (Node.js에서 데이터 로드 후 전달)
   */
  async validateDataWithData(sessionId, data) {
    try {
      logger.info(`데이터 검증 시작 (데이터 포함): ${sessionId}`);
      
      const response = await this.client.post('/api/v1/validation-with-data/', {
        session_id: sessionId,
        window_days: data.windowDays,
        base_date: data.baseDate,
        yield_period: data.yieldPeriod,
        loaded_data: data.loadedData,
        stats: data.stats,
        load_results: data.loadResults
      });

      logger.info(`데이터 검증 완료 (데이터 포함): ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`데이터 검증 실패 (데이터 포함): ${sessionId}`, error);
      throw this.handleError(error, '데이터 검증');
    }
  }

  /**
   * 2단계: 전처리
   */
  async runPreprocessing(sessionId, windowDays = 5) {
    try {
      logger.info(`전처리 시작: ${sessionId}`);
      
      const response = await this.client.post(config.pythonApi.endpoints.preprocessing, {
        session_id: sessionId,
        window_days: windowDays
      });

      logger.info(`전처리 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`전처리 실패: ${sessionId}`, error);
      throw this.handleError(error, '전처리');
    }
  }

  /**
   * 3단계: 수율 예측
   */
  async runYieldPrediction(sessionId) {
    try {
      logger.info(`수율 예측 시작: ${sessionId}`);
      
      const response = await this.client.post(config.pythonApi.endpoints.yieldPrediction, {
        session_id: sessionId
      });

      logger.info(`수율 예측 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`수율 예측 실패: ${sessionId}`, error);
      throw this.handleError(error, '수율 예측');
    }
  }

  /**
   * 4단계: DAG 생성
   */
  async runDAGCreation(sessionId) {
    try {
      logger.info(`DAG 생성 시작: ${sessionId}`);
      
      const response = await this.client.post(config.pythonApi.endpoints.dagCreation, {
        session_id: sessionId
      });

      logger.info(`DAG 생성 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`DAG 생성 실패: ${sessionId}`, error);
      throw this.handleError(error, 'DAG 생성');
    }
  }

  /**
   * 5단계: 스케줄링
   */
  async runScheduling(sessionId, windowDays = 5) {
    try {
      logger.info(`스케줄링 시작: ${sessionId}`);
      
      const response = await this.client.post(config.pythonApi.endpoints.scheduling, {
        session_id: sessionId,
        window_days: windowDays
      });

      logger.info(`스케줄링 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`스케줄링 실패: ${sessionId}`, error);
      throw this.handleError(error, '스케줄링');
    }
  }


  /**
   * 6단계: 결과 처리
   */
  async runResultsProcessing(sessionId) {
    try {
      logger.info(`결과 처리 시작: ${sessionId}`);
      
      const response = await this.client.post(config.pythonApi.endpoints.results, {
        session_id: sessionId
      });

      logger.info(`결과 처리 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`결과 처리 실패: ${sessionId}`, error);
      throw this.handleError(error, '결과 처리');
    }
  }

  /**
   * 세션 상태 조회
   */
  async getSessionStatus(sessionId) {
    try {
      logger.info(`세션 상태 조회: ${sessionId}`);
      
      const response = await this.client.get(`${config.pythonApi.endpoints.status}/${sessionId}`);
      
      logger.info(`세션 상태 조회 완료: ${sessionId}`);
      return response.data;
    } catch (error) {
      logger.error(`세션 상태 조회 실패: ${sessionId}`, error);
      throw this.handleError(error, '세션 상태 조회');
    }
  }

  /**
   * 전체 스케줄링 프로세스 실행
   */
  async runFullScheduling(sessionId, windowDays = 5) {
    try {
      logger.info(`전체 스케줄링 프로세스 시작: ${sessionId}`);
      
      const results = {
        sessionId,
        steps: {},
        startTime: new Date().toISOString(),
        endTime: null,
        success: false,
        error: null
      };

      try {
        // 1단계: 데이터 검증
        results.steps.validation = await this.validateData(sessionId, {});
        
        // 2단계: 전처리
        results.steps.preprocessing = await this.runPreprocessing(sessionId, windowDays);
        
        // 3단계: 수율 예측
        results.steps.yieldPrediction = await this.runYieldPrediction(sessionId);
        
        // 4단계: DAG 생성
        results.steps.dagCreation = await this.runDAGCreation(sessionId);
        
        // 5단계: 스케줄링
        results.steps.scheduling = await this.runScheduling(sessionId, windowDays);
        
        // 6단계: 결과 처리
        results.steps.results = await this.runResultsProcessing(sessionId);
        
        results.endTime = new Date().toISOString();
        results.success = true;
        
        logger.info(`전체 스케줄링 프로세스 완료: ${sessionId}`);
        return results;
        
      } catch (error) {
        results.endTime = new Date().toISOString();
        results.error = error.message;
        results.success = false;
        
        logger.error(`전체 스케줄링 프로세스 실패: ${sessionId}`, error);
        throw error;
      }
    } catch (error) {
      logger.error(`전체 스케줄링 프로세스 오류: ${sessionId}`, error);
      throw error;
    }
  }

  /**
   * 에러 처리
   */
  handleError(error, operation) {
    if (error.response) {
      // Python API에서 응답이 온 경우
      const status = error.response.status;
      const data = error.response.data;
      
      return {
        type: 'API_ERROR',
        operation,
        status,
        message: data?.message || data?.detail || 'Python API 오류',
        details: data
      };
    } else if (error.request) {
      // 요청은 보냈지만 응답을 받지 못한 경우
      return {
        type: 'NETWORK_ERROR',
        operation,
        message: 'Python API 서버에 연결할 수 없습니다',
        details: error.message
      };
    } else {
      // 기타 오류
      return {
        type: 'UNKNOWN_ERROR',
        operation,
        message: error.message,
        details: error
      };
    }
  }
}

module.exports = new PythonApiService();
