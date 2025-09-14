# Node.js에서 FastAPI 연동 예제

## 📋 개요

Node.js에서 FastAPI 서버로 데이터를 전송하고 각 단계별로 처리하는 예제입니다.

## 🔧 필요한 패키지

```bash
npm install axios
```

## 📁 Node.js 예제 코드

### 1. 기본 설정 (config.js)

```javascript
const axios = require('axios');

// FastAPI 서버 설정
const FASTAPI_BASE_URL = 'http://localhost:8000';
const API_TIMEOUT = 300000; // 5분 타임아웃

// axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: FASTAPI_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

module.exports = { apiClient };
```

### 2. 데이터 로더 (dataLoader.js)

```javascript
const fs = require('fs');
const path = require('path');

/**
 * main.py에서 사용하는 JSON 파일들을 로드
 */
class DataLoader {
  constructor(dataPath) {
    this.dataPath = dataPath;
  }

  /**
   * JSON 파일 로드
   */
  loadJsonFile(filename) {
    try {
      const filePath = path.join(this.dataPath, filename);
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      console.error(`파일 로드 실패: ${filename}`, error.message);
      return [];
    }
  }

  /**
   * main.py 데이터 구조로 모든 데이터 로드
   */
  loadAllData() {
    return {
      // 1. 주문 데이터
      order_data: this.loadJsonFile('md_step2_order_data.json'),
      
      // 2. 라인스피드 및 공정 순서 관련
      linespeed: this.loadJsonFile('md_step2_linespeed.json'),
      operation_seperated_sequence: this.loadJsonFile('md_step2_operation_sequence.json'),
      machine_master_info: this.loadJsonFile('md_step4_machine_master_info.json'),
      yield_data: this.loadJsonFile('md_step3_yield_data.json'),
      gitem_operation: this.loadJsonFile('md_step3_gitem_operation.json'),
      
      // 3. 공정 재분류 내역 및 교체 시간 관련
      operation_types: this.loadJsonFile('md_step2_operation_types.json'),
      operation_delay_df: this.loadJsonFile('md_step5 operation_delay.json'),
      width_change_df: this.loadJsonFile('md_step5_width_change.json'),
      
      // 4. 불가능한 공정 입력값 관련
      machine_rest: this.loadJsonFile('user_step5_machine_rest.json'),
      machine_allocate: this.loadJsonFile('user_step2_machine_allocate.json'),
      machine_limit: this.loadJsonFile('user_step2_machine_limit.json')
    };
  }
}

module.exports = DataLoader;
```

### 3. 스케줄링 서비스 (schedulingService.js)

```javascript
const { apiClient } = require('./config');
const DataLoader = require('./dataLoader');

class SchedulingService {
  constructor() {
    this.dataLoader = new DataLoader('./python_engine/data/json');
  }

  /**
   * 1단계: 데이터 검증
   */
  async validateData(sessionId) {
    try {
      console.log(`[1단계] 데이터 검증 시작: ${sessionId}`);
      
      // 데이터 로드
      const data = this.dataLoader.loadAllData();
      
      // API 요청
      const response = await apiClient.post('/api/v1/validation/', {
        session_id: sessionId,
        ...data
      });

      console.log(`[1단계] 데이터 검증 완료:`, response.data);
      return response.data;
    } catch (error) {
      console.error('[1단계] 데이터 검증 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 2단계: 전처리
   */
  async runPreprocessing(sessionId, windowDays = 5) {
    try {
      console.log(`[2단계] 전처리 시작: ${sessionId}`);
      
      const response = await apiClient.post('/api/v1/preprocessing/', {
        session_id: sessionId,
        window_days: windowDays
      });

      console.log(`[2단계] 전처리 완료:`, response.data);
      return response.data;
    } catch (error) {
      console.error('[2단계] 전처리 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 3단계: 수율 예측
   */
  async runYieldPrediction(sessionId) {
    try {
      console.log(`[3단계] 수율 예측 시작: ${sessionId}`);
      
      const response = await apiClient.post('/api/v1/yield-prediction/', {
        session_id: sessionId
      });

      console.log(`[3단계] 수율 예측 완료:`, response.data);
      return response.data;
    } catch (error) {
      console.error('[3단계] 수율 예측 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 4단계: DAG 생성
   */
  async runDAGCreation(sessionId) {
    try {
      console.log(`[4단계] DAG 생성 시작: ${sessionId}`);
      
      const response = await apiClient.post('/api/v1/dag-creation/', {
        session_id: sessionId
      });

      console.log(`[4단계] DAG 생성 완료:`, response.data);
      return response.data;
    } catch (error) {
      console.error('[4단계] DAG 생성 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 5단계: 스케줄링
   */
  async runScheduling(sessionId, windowDays = 5) {
    try {
      console.log(`[5단계] 스케줄링 시작: ${sessionId}`);
      
      const response = await apiClient.post('/api/v1/scheduling/', {
        session_id: sessionId,
        window_days: windowDays
      });

      console.log(`[5단계] 스케줄링 완료:`, response.data);
      return response.data;
    } catch (error) {
      console.error('[5단계] 스케줄링 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 6단계: 결과 처리
   */
  async runResultsProcessing(sessionId) {
    try {
      console.log(`[6단계] 결과 처리 시작: ${sessionId}`);
      
      const response = await apiClient.post('/api/v1/results/', {
        session_id: sessionId
      });

      console.log(`[6단계] 결과 처리 완료:`, response.data);
      return response.data;
    } catch (error) {
      console.error('[6단계] 결과 처리 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 세션 상태 조회
   */
  async getSessionStatus(sessionId) {
    try {
      const response = await apiClient.get(`/api/v1/status/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('세션 상태 조회 실패:', error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 전체 스케줄링 프로세스 실행
   */
  async runFullScheduling(sessionId, windowDays = 5) {
    try {
      console.log(`🚀 전체 스케줄링 프로세스 시작: ${sessionId}`);
      
      // 1단계: 데이터 검증
      await this.validateData(sessionId);
      
      // 2단계: 전처리
      await this.runPreprocessing(sessionId, windowDays);
      
      // 3단계: 수율 예측
      await this.runYieldPrediction(sessionId);
      
      // 4단계: DAG 생성
      await this.runDAGCreation(sessionId);
      
      // 5단계: 스케줄링
      await this.runScheduling(sessionId, windowDays);
      
      // 6단계: 결과 처리
      const results = await this.runResultsProcessing(sessionId);
      
      console.log(`✅ 전체 스케줄링 프로세스 완료: ${sessionId}`);
      return results;
      
    } catch (error) {
      console.error('❌ 전체 스케줄링 프로세스 실패:', error.message);
      throw error;
    }
  }
}

module.exports = SchedulingService;
```

### 4. 메인 실행 파일 (app.js)

```javascript
const SchedulingService = require('./schedulingService');

async function main() {
  const schedulingService = new SchedulingService();
  const sessionId = `session-${Date.now()}`;
  
  try {
    // 전체 스케줄링 프로세스 실행
    const results = await schedulingService.runFullScheduling(sessionId, 5);
    
    console.log('🎉 스케줄링 완료!');
    console.log('결과:', JSON.stringify(results, null, 2));
    
  } catch (error) {
    console.error('스케줄링 실패:', error.message);
    
    // 세션 상태 확인
    try {
      const status = await schedulingService.getSessionStatus(sessionId);
      console.log('현재 세션 상태:', JSON.stringify(status, null, 2));
    } catch (statusError) {
      console.error('세션 상태 조회 실패:', statusError.message);
    }
  }
}

// 실행
if (require.main === module) {
  main();
}

module.exports = { main };
```

### 5. 단계별 실행 예제 (stepByStep.js)

```javascript
const SchedulingService = require('./schedulingService');

async function runStepByStep() {
  const schedulingService = new SchedulingService();
  const sessionId = `step-session-${Date.now()}`;
  
  try {
    // 1단계: 데이터 검증
    console.log('=== 1단계: 데이터 검증 ===');
    await schedulingService.validateData(sessionId);
    
    // 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 2단계: 전처리
    console.log('=== 2단계: 전처리 ===');
    await schedulingService.runPreprocessing(sessionId, 5);
    
    // 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 3단계: 수율 예측
    console.log('=== 3단계: 수율 예측 ===');
    await schedulingService.runYieldPrediction(sessionId);
    
    // 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 4단계: DAG 생성
    console.log('=== 4단계: DAG 생성 ===');
    await schedulingService.runDAGCreation(sessionId);
    
    // 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 5단계: 스케줄링
    console.log('=== 5단계: 스케줄링 ===');
    await schedulingService.runScheduling(sessionId, 5);
    
    // 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 6단계: 결과 처리
    console.log('=== 6단계: 결과 처리 ===');
    const results = await schedulingService.runResultsProcessing(sessionId);
    
    console.log('🎉 모든 단계 완료!');
    console.log('최종 결과:', JSON.stringify(results, null, 2));
    
  } catch (error) {
    console.error('❌ 단계별 실행 실패:', error.message);
    
    // 현재 상태 확인
    try {
      const status = await schedulingService.getSessionStatus(sessionId);
      console.log('현재 상태:', JSON.stringify(status, null, 2));
    } catch (statusError) {
      console.error('상태 조회 실패:', statusError.message);
    }
  }
}

// 실행
if (require.main === module) {
  runStepByStep();
}

module.exports = { runStepByStep };
```

## 🚀 사용 방법

### 1. 전체 프로세스 실행
```bash
node app.js
```

### 2. 단계별 실행
```bash
node stepByStep.js
```

### 3. 개별 단계 실행
```javascript
const SchedulingService = require('./schedulingService');

async function runIndividualStep() {
  const service = new SchedulingService();
  const sessionId = 'my-session-001';
  
  // 1단계만 실행
  await service.validateData(sessionId);
  
  // 2단계만 실행 (1단계 완료 후)
  await service.runPreprocessing(sessionId, 5);
  
  // ... 나머지 단계들
}
```

## 📊 데이터 흐름

```
Node.js → FastAPI → Python Engine → Redis
   ↓
1. 데이터 검증 → Redis 저장
   ↓
2. 전처리 (Redis에서 데이터 조회) → Redis 저장
   ↓
3. 수율 예측 (Redis에서 데이터 조회) → Redis 저장
   ↓
4. DAG 생성 (Redis에서 데이터 조회) → Redis 저장
   ↓
5. 스케줄링 (Redis에서 데이터 조회) → Redis 저장
   ↓
6. 결과 처리 (Redis에서 데이터 조회) → Redis 저장
   ↓
최종 결과 반환
```

## 🔧 환경 설정

### 1. FastAPI 서버 실행
```bash
cd python-server
python run.py
```

### 2. Redis 서버 실행
```bash
redis-server
```

### 3. Node.js 프로젝트 설정
```bash
npm init -y
npm install axios
```

이제 Node.js에서 FastAPI 서버로 데이터를 전송하고 각 단계별로 처리할 수 있습니다!


