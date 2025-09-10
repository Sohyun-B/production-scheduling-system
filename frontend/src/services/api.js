/**
 * API 서비스
 * Node.js 백엔드와의 통신을 담당
 */

import axios from 'axios';
import toast from 'react-hot-toast';

// API 기본 설정
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    console.log(`API 요청: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API 요청 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    console.log(`API 응답: ${response.status} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error('API 응답 오류:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
      url: error.config?.url
    });
    
    // 에러 메시지 표시
    const errorMessage = error.response?.data?.message || error.message || '알 수 없는 오류가 발생했습니다.';
    toast.error(`API 오류: ${errorMessage}`);
    
    return Promise.reject(error);
  }
);

// API 서비스 객체
export const apiService = {
  // 헬스 체크
  async healthCheck() {
    const response = await api.get('/api/health');
    return response.data;
  },

  // 1단계: 직접 데이터 로딩
  async loadData(data) {
    const response = await api.post('/api/scheduling/load-data', data);
    return response.data;
  },

  // 1단계: 외부 API 데이터 로딩
  async loadExternalData(apiConfig) {
    const response = await api.post('/api/scheduling/load-external-data', {
      apiConfig
    });
    return response.data;
  },

  // 2단계: 전처리
  async preprocessing(sessionId) {
    const response = await api.post('/api/scheduling/preprocessing', {
      sessionId
    });
    return response.data;
  },

  // 3단계: 수율 예측
  async yieldPrediction(sessionId) {
    const response = await api.post('/api/scheduling/yield-prediction', {
      sessionId
    });
    return response.data;
  },

  // 4단계: DAG 생성
  async dagCreation(sessionId) {
    const response = await api.post('/api/scheduling/dag-creation', {
      sessionId
    });
    return response.data;
  },

  // 5단계: 스케줄링 실행
  async scheduling(sessionId, windowDays = 5) {
    const response = await api.post('/api/scheduling/scheduling', {
      sessionId,
      windowDays
    });
    return response.data;
  },

  // 6단계: 결과 후처리
  async results(sessionId) {
    const response = await api.post('/api/scheduling/results', {
      sessionId
    });
    return response.data;
  },

  // 전체 파이프라인 실행
  async fullPipeline(data, windowDays = 5) {
    const response = await api.post('/api/scheduling/full-pipeline', {
      ...data,
      windowDays
    });
    return response.data;
  },

  // 단계별 실행 (진행 상황 추적)
  async stepByStep(data, windowDays = 5) {
    const response = await api.post('/api/scheduling/step-by-step', {
      ...data,
      windowDays
    });
    return response.data;
  },

  // 세션 상태 조회
  async getSessionStatus(sessionId) {
    const response = await api.get(`/api/scheduling/session/${sessionId}/status`);
    return response.data;
  },

  // 세션 삭제
  async clearSession(sessionId) {
    const response = await api.delete(`/api/scheduling/session/${sessionId}`);
    return response.data;
  },

  // 단계별 실행 메서드들
  async executeStep(endpoint, method, data) {
    try {
      const response = await api({
        method,
        url: endpoint,
        data,
        timeout: 60000
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.message || error.message || '요청 실행 중 오류가 발생했습니다.');
    }
  },

  async getStage5Status(sessionId) {
    try {
      const response = await api.get(`/api/stages/stage5/status/${sessionId}`);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.message || error.message || '상태 확인 중 오류가 발생했습니다.');
    }
  },

  async getSessionStatus(sessionId) {
    try {
      const response = await api.get(`/api/stages/session/${sessionId}/status`);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.message || error.message || '세션 상태 확인 중 오류가 발생했습니다.');
    }
  }
};

export default api;
