/**
 * 단계별 스케줄링 API 라우트
 * 각 단계를 독립적으로 실행할 수 있는 엔드포인트 제공
 */

const express = require('express');
const router = express.Router();
const axios = require('axios');
// const { validateStageData } = require('../middleware/validation');
// const { logger } = require('../utils/logger');

const PYTHON_API_BASE = process.env.PYTHON_API_URL || 'http://localhost:8000';

// 세션 저장소 (실제로는 Redis 사용 권장)
const sessions = new Map();

/**
 * 1단계: 데이터 로딩
 */
router.post('/stage1/load-data', async (req, res) => {
  try {
    console.log('1단계 데이터 로딩 시작');
    
    const response = await axios.post(`${PYTHON_API_BASE}/api/v1/stage1/load-data`, req.body, {
      timeout: 30000
    });
    
    const { session_id } = response.data;
    
    // 세션 저장
    sessions.set(session_id, {
      stage: 1,
      status: 'completed',
      data: response.data,
      timestamp: new Date().toISOString()
    });
    
    console.log(`1단계 완료 - 세션 ID: ${session_id}`);
    
    res.json({
      success: true,
      message: '1단계 데이터 로딩 완료',
      session_id,
      stage: 1,
      data: response.data
    });
    
  } catch (error) {
    console.error('1단계 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '1단계 데이터 로딩 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 2단계: 전처리
 */
router.post('/stage2/preprocessing', async (req, res) => {
  try {
    const { session_id } = req.body;
    
    if (!session_id) {
      return res.status(400).json({
        success: false,
        message: '세션 ID가 필요합니다'
      });
    }
    
    console.log(`2단계 전처리 시작 - 세션 ID: ${session_id}`);
    
    const response = await axios.post(`${PYTHON_API_BASE}/api/v1/stage2/preprocessing`, {
      session_id
    }, {
      timeout: 60000
    });
    
    // 세션 업데이트
    const session = sessions.get(session_id);
    if (session) {
      session.stage = 2;
      session.status = 'completed';
      session.data = response.data;
      session.timestamp = new Date().toISOString();
    }
    
    console.log(`2단계 완료 - 세션 ID: ${session_id}`);
    
    res.json({
      success: true,
      message: '2단계 전처리 완료',
      session_id,
      stage: 2,
      data: response.data
    });
    
  } catch (error) {
    console.error('2단계 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '2단계 전처리 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 3단계: 수율 예측
 */
router.post('/stage3/yield-prediction', async (req, res) => {
  try {
    const { session_id } = req.body;
    
    if (!session_id) {
      return res.status(400).json({
        success: false,
        message: '세션 ID가 필요합니다'
      });
    }
    
    console.log(`3단계 수율 예측 시작 - 세션 ID: ${session_id}`);
    
    const response = await axios.post(`${PYTHON_API_BASE}/api/v1/stage3/yield-prediction`, {
      session_id
    }, {
      timeout: 60000
    });
    
    // 세션 업데이트
    const session = sessions.get(session_id);
    if (session) {
      session.stage = 3;
      session.status = 'completed';
      session.data = response.data;
      session.timestamp = new Date().toISOString();
    }
    
    console.log(`3단계 완료 - 세션 ID: ${session_id}`);
    
    res.json({
      success: true,
      message: '3단계 수율 예측 완료',
      session_id,
      stage: 3,
      data: response.data
    });
    
  } catch (error) {
    console.error('3단계 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '3단계 수율 예측 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 4단계: DAG 생성
 */
router.post('/stage4/dag-creation', async (req, res) => {
  try {
    const { session_id } = req.body;
    
    if (!session_id) {
      return res.status(400).json({
        success: false,
        message: '세션 ID가 필요합니다'
      });
    }
    
    console.log(`4단계 DAG 생성 시작 - 세션 ID: ${session_id}`);
    
    const response = await axios.post(`${PYTHON_API_BASE}/api/v1/stage4/dag-creation`, {
      session_id
    }, {
      timeout: 60000
    });
    
    // 세션 업데이트
    const session = sessions.get(session_id);
    if (session) {
      session.stage = 4;
      session.status = 'completed';
      session.data = response.data;
      session.timestamp = new Date().toISOString();
    }
    
    console.log(`4단계 완료 - 세션 ID: ${session_id}`);
    
    res.json({
      success: true,
      message: '4단계 DAG 생성 완료',
      session_id,
      stage: 4,
      data: response.data
    });
    
  } catch (error) {
    console.error('4단계 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '4단계 DAG 생성 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 5단계: 스케줄링 (비동기)
 */
router.post('/stage5/scheduling', async (req, res) => {
  try {
    const { session_id, window_days = 5 } = req.body;
    
    if (!session_id) {
      return res.status(400).json({
        success: false,
        message: '세션 ID가 필요합니다'
      });
    }
    
    console.log(`5단계 스케줄링 시작 - 세션 ID: ${session_id}`);
    
    const response = await axios.post(`${PYTHON_API_BASE}/api/v1/stage5/scheduling`, {
      session_id,
      window_days
    }, {
      timeout: 10000 // 즉시 응답을 위한 짧은 타임아웃
    });
    
    // 세션 업데이트 (진행 중 상태)
    const session = sessions.get(session_id);
    if (session) {
      session.stage = 5;
      session.status = 'running';
      session.data = response.data;
      session.timestamp = new Date().toISOString();
    }
    
    console.log(`5단계 시작됨 - 세션 ID: ${session_id}`);
    
    res.json({
      success: true,
      message: '5단계 스케줄링이 백그라운드에서 시작되었습니다',
      session_id,
      stage: 5,
      status: 'running',
      data: response.data
    });
    
  } catch (error) {
    console.error('5단계 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '5단계 스케줄링 시작 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 5단계: 스케줄링 상태 확인
 */
router.get('/stage5/status/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    
    console.log(`5단계 상태 확인 - 세션 ID: ${sessionId}`);
    
    const response = await axios.get(`${PYTHON_API_BASE}/api/v1/session/${sessionId}/status`, {
      timeout: 5000
    });
    
    // 세션 업데이트
    const session = sessions.get(sessionId);
    if (session) {
      const completedStages = response.data.completed_stages || [];
      const isStage5Completed = completedStages.includes('stage5');
      
      if (isStage5Completed) {
        session.status = 'completed';
        session.data = response.data;
        session.timestamp = new Date().toISOString();
      }
    }
    
    const completedStages = response.data.completed_stages || [];
    const isStage5Completed = completedStages.includes('stage5');
    
    res.json({
      success: true,
      message: '5단계 상태 조회 성공',
      session_id: sessionId,
      stage: 5,
      status: isStage5Completed ? 'completed' : 'running',
      data: response.data
    });
    
  } catch (error) {
    console.error('5단계 상태 확인 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '5단계 상태 확인 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 6단계: 결과 후처리
 */
router.post('/stage6/results', async (req, res) => {
  try {
    const { session_id } = req.body;
    
    if (!session_id) {
      return res.status(400).json({
        success: false,
        message: '세션 ID가 필요합니다'
      });
    }
    
    console.log(`6단계 결과 후처리 시작 - 세션 ID: ${session_id}`);
    
    const response = await axios.post(`${PYTHON_API_BASE}/api/v1/stage6/results`, {
      session_id
    }, {
      timeout: 60000
    });
    
    // 세션 업데이트
    const session = sessions.get(session_id);
    if (session) {
      session.stage = 6;
      session.status = 'completed';
      session.data = response.data;
      session.timestamp = new Date().toISOString();
    }
    
    console.log(`6단계 완료 - 세션 ID: ${session_id}`);
    
    res.json({
      success: true,
      message: '6단계 결과 후처리 완료',
      session_id,
      stage: 6,
      data: response.data
    });
    
  } catch (error) {
    console.error('6단계 실패:', error.message);
    res.status(500).json({
      success: false,
      message: '6단계 결과 후처리 실패',
      error: error.response?.data?.detail || error.message
    });
  }
});

/**
 * 세션 상태 조회
 */
router.get('/session/:sessionId/status', (req, res) => {
  const { sessionId } = req.params;
  const session = sessions.get(sessionId);
  
  if (!session) {
    return res.status(404).json({
      success: false,
      message: '세션을 찾을 수 없습니다'
    });
  }
  
  res.json({
    success: true,
    session_id: sessionId,
    ...session
  });
});

module.exports = router;
