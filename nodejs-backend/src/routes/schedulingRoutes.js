/**
 * 스케줄링 라우터
 */
const express = require('express');
const router = express.Router();
const schedulingController = require('../controllers/schedulingController');
const { 
  validateSchedulingRequest, 
  validateStepRequest, 
  validateValidationRequest,
  validateSessionId 
} = require('../middleware/validation');

/**
 * @route   POST /api/scheduling/full
 * @desc    전체 스케줄링 프로세스 실행
 * @access  Public
 */
router.post('/full', validateSchedulingRequest, schedulingController.runFullScheduling);

/**
 * @route   POST /api/scheduling/step/validation
 * @desc    1단계: 데이터 검증 (단계별)
 * @access  Public
 */
router.post('/step/validation', validateValidationRequest, schedulingController.validateData);

/**
 * @route   POST /api/scheduling/validate
 * @desc    1단계: 데이터 검증
 * @access  Public
 */
router.post('/validate', validateSchedulingRequest, schedulingController.validateData);

/**
 * @route   POST /api/scheduling/step/preprocessing
 * @desc    2단계: 전처리 (단계별)
 * @access  Public
 */
router.post('/step/preprocessing', validateStepRequest, schedulingController.runPreprocessing);

/**
 * @route   POST /api/scheduling/preprocessing
 * @desc    2단계: 전처리
 * @access  Public
 */
router.post('/preprocessing', validateStepRequest, schedulingController.runPreprocessing);

/**
 * @route   POST /api/scheduling/step/yield-prediction
 * @desc    3단계: 수율 예측 (단계별)
 * @access  Public
 */
router.post('/step/yield-prediction', validateStepRequest, schedulingController.runYieldPrediction);

/**
 * @route   POST /api/scheduling/yield-prediction
 * @desc    3단계: 수율 예측
 * @access  Public
 */
router.post('/yield-prediction', validateStepRequest, schedulingController.runYieldPrediction);

/**
 * @route   POST /api/scheduling/step/dag-creation
 * @desc    4단계: DAG 생성 (단계별)
 * @access  Public
 */
router.post('/step/dag-creation', validateStepRequest, schedulingController.runDAGCreation);

/**
 * @route   POST /api/scheduling/dag-creation
 * @desc    4단계: DAG 생성
 * @access  Public
 */
router.post('/dag-creation', validateStepRequest, schedulingController.runDAGCreation);

/**
 * @route   POST /api/scheduling/step/scheduling
 * @desc    5단계: 스케줄링 (단계별)
 * @access  Public
 */
router.post('/step/scheduling', validateStepRequest, schedulingController.runScheduling);

/**
 * @route   POST /api/scheduling/scheduling
 * @desc    5단계: 스케줄링
 * @access  Public
 */
router.post('/scheduling', validateStepRequest, schedulingController.runScheduling);

/**
 * @route   POST /api/scheduling/step/results
 * @desc    6단계: 결과 처리 (단계별)
 * @access  Public
 */
router.post('/step/results', validateStepRequest, schedulingController.runResultsProcessing);

/**
 * @route   POST /api/scheduling/results
 * @desc    6단계: 결과 처리
 * @access  Public
 */
router.post('/results', validateStepRequest, schedulingController.runResultsProcessing);

/**
 * @route   GET /api/scheduling/status/:sessionId
 * @desc    세션 상태 조회
 * @access  Public
 */
router.get('/status/:sessionId', validateSessionId, schedulingController.getSessionStatus);

/**
 * @route   GET /api/scheduling/health
 * @desc    헬스 체크
 * @access  Public
 */
router.get('/health', schedulingController.healthCheck);

module.exports = router;
