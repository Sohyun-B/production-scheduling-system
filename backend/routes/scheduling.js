/**
 * 스케줄링 라우트
 * 단계별 스케줄링 API 엔드포인트
 */

const express = require('express');
const router = express.Router();
const pythonApiService = require('../services/pythonApiService');
const { validateSchedulingData, validateSessionId } = require('../middleware/validation');
const { asyncHandler } = require('../middleware/asyncHandler');
const logger = require('../utils/logger');

/**
 * @route GET /api/scheduling/docs
 * @desc API 문서
 */
router.get('/docs', (req, res) => {
  res.json({
    title: 'Production Scheduling API',
    version: '1.0.0',
    description: '제조업 공정 스케줄링 시스템 API',
    endpoints: {
      'POST /api/scheduling/load-data': '1단계: 직접 데이터 로딩',
      'POST /api/scheduling/load-external-data': '1단계: 외부 API 데이터 로딩',
      'POST /api/scheduling/preprocessing': '2단계: 전처리',
      'POST /api/scheduling/yield-prediction': '3단계: 수율 예측',
      'POST /api/scheduling/dag-creation': '4단계: DAG 생성',
      'POST /api/scheduling/scheduling': '5단계: 스케줄링 실행',
      'POST /api/scheduling/results': '6단계: 결과 후처리',
      'POST /api/scheduling/full-pipeline': '전체 파이프라인 실행',
      'GET /api/scheduling/session/:id/status': '세션 상태 조회',
      'DELETE /api/scheduling/session/:id': '세션 삭제'
    }
  });
});

/**
 * @route POST /api/scheduling/load-data
 * @desc 1단계: 직접 데이터 로딩
 */
router.post('/load-data', 
  validateSchedulingData,
  asyncHandler(async (req, res) => {
    logger.info('1단계: 직접 데이터 로딩 요청');
    
    const result = await pythonApiService.loadData(req.body);
    
    res.json({
      success: true,
      message: '데이터 로딩 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/load-external-data
 * @desc 1단계: 외부 API 데이터 로딩
 */
router.post('/load-external-data',
  asyncHandler(async (req, res) => {
    logger.info('1단계: 외부 API 데이터 로딩 요청');
    
    const { apiConfig } = req.body;
    
    if (!apiConfig) {
      return res.status(400).json({
        success: false,
        message: 'API 설정이 필요합니다.'
      });
    }
    
    const result = await pythonApiService.loadExternalData(apiConfig);
    
    res.json({
      success: true,
      message: '외부 데이터 로딩 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/preprocessing
 * @desc 2단계: 전처리
 */
router.post('/preprocessing',
  validateSessionId,
  asyncHandler(async (req, res) => {
    logger.info('2단계: 전처리 요청', { sessionId: req.body.sessionId });
    
    const result = await pythonApiService.preprocessing(req.body.sessionId);
    
    res.json({
      success: true,
      message: '전처리 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/yield-prediction
 * @desc 3단계: 수율 예측
 */
router.post('/yield-prediction',
  validateSessionId,
  asyncHandler(async (req, res) => {
    logger.info('3단계: 수율 예측 요청', { sessionId: req.body.sessionId });
    
    const result = await pythonApiService.yieldPrediction(req.body.sessionId);
    
    res.json({
      success: true,
      message: '수율 예측 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/dag-creation
 * @desc 4단계: DAG 생성
 */
router.post('/dag-creation',
  validateSessionId,
  asyncHandler(async (req, res) => {
    logger.info('4단계: DAG 생성 요청', { sessionId: req.body.sessionId });
    
    const result = await pythonApiService.dagCreation(req.body.sessionId);
    
    res.json({
      success: true,
      message: 'DAG 생성 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/scheduling
 * @desc 5단계: 스케줄링 실행
 */
router.post('/scheduling',
  validateSessionId,
  asyncHandler(async (req, res) => {
    logger.info('5단계: 스케줄링 실행 요청', { 
      sessionId: req.body.sessionId,
      windowDays: req.body.windowDays 
    });
    
    const { windowDays = 5 } = req.body;
    const result = await pythonApiService.scheduling(req.body.sessionId, windowDays);
    
    res.json({
      success: true,
      message: '스케줄링 실행 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/results
 * @desc 6단계: 결과 후처리
 */
router.post('/results',
  validateSessionId,
  asyncHandler(async (req, res) => {
    logger.info('6단계: 결과 후처리 요청', { sessionId: req.body.sessionId });
    
    const result = await pythonApiService.results(req.body.sessionId);
    
    res.json({
      success: true,
      message: '결과 후처리 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/full-pipeline
 * @desc 전체 파이프라인 실행
 */
router.post('/full-pipeline',
  validateSchedulingData,
  asyncHandler(async (req, res) => {
    logger.info('전체 파이프라인 실행 요청');
    
    const { windowDays = 5 } = req.body;
    const result = await pythonApiService.fullScheduling(req.body, windowDays);
    
    res.json({
      success: true,
      message: '전체 파이프라인 실행 완료',
      data: result.data
    });
  })
);

/**
 * @route GET /api/scheduling/session/:id/status
 * @desc 세션 상태 조회
 */
router.get('/session/:id/status',
  asyncHandler(async (req, res) => {
    const { id: sessionId } = req.params;
    logger.info('세션 상태 조회 요청', { sessionId });
    
    const result = await pythonApiService.getSessionStatus(sessionId);
    
    res.json({
      success: true,
      message: '세션 상태 조회 완료',
      data: result.data
    });
  })
);

/**
 * @route DELETE /api/scheduling/session/:id
 * @desc 세션 삭제
 */
router.delete('/session/:id',
  asyncHandler(async (req, res) => {
    const { id: sessionId } = req.params;
    logger.info('세션 삭제 요청', { sessionId });
    
    const result = await pythonApiService.clearSession(sessionId);
    
    res.json({
      success: true,
      message: '세션 삭제 완료',
      data: result.data
    });
  })
);

/**
 * @route POST /api/scheduling/step-by-step
 * @desc 단계별 스케줄링 실행 (진행 상황 추적)
 */
router.post('/step-by-step',
  validateSchedulingData,
  asyncHandler(async (req, res) => {
    logger.info('단계별 스케줄링 실행 요청');
    
    const { windowDays = 5 } = req.body;
    const results = [];
    
    try {
      // 1단계: 데이터 로딩
      logger.info('1단계: 데이터 로딩 시작');
      const stage1 = await pythonApiService.loadData(req.body);
      results.push({ stage: 1, success: true, data: stage1.data });
      
      // 2단계: 전처리
      logger.info('2단계: 전처리 시작');
      const stage2 = await pythonApiService.preprocessing(stage1.data.session_id);
      results.push({ stage: 2, success: true, data: stage2.data });
      
      // 3단계: 수율 예측
      logger.info('3단계: 수율 예측 시작');
      const stage3 = await pythonApiService.yieldPrediction(stage1.data.session_id);
      results.push({ stage: 3, success: true, data: stage3.data });
      
      // 4단계: DAG 생성
      logger.info('4단계: DAG 생성 시작');
      const stage4 = await pythonApiService.dagCreation(stage1.data.session_id);
      results.push({ stage: 4, success: true, data: stage4.data });
      
      // 5단계: 스케줄링 실행
      logger.info('5단계: 스케줄링 실행 시작');
      const stage5 = await pythonApiService.scheduling(stage1.data.session_id, windowDays);
      results.push({ stage: 5, success: true, data: stage5.data });
      
      // 6단계: 결과 후처리
      logger.info('6단계: 결과 후처리 시작');
      const stage6 = await pythonApiService.results(stage1.data.session_id);
      results.push({ stage: 6, success: true, data: stage6.data });
      
      res.json({
        success: true,
        message: '단계별 스케줄링 실행 완료',
        sessionId: stage1.data.session_id,
        results: results
      });
      
    } catch (error) {
      logger.error('단계별 스케줄링 실행 실패:', error);
      
      res.status(500).json({
        success: false,
        message: '단계별 스케줄링 실행 실패',
        error: error.message,
        completedStages: results
      });
    }
  })
);

module.exports = router;
