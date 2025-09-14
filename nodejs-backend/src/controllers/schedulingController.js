/**
 * 스케줄링 컨트롤러
 */
const { v4: uuidv4 } = require('uuid');
const pythonApiService = require('../services/pythonApiService');
const dataLoaderService = require('../services/dataLoaderService');
const logger = require('../utils/logger');

class SchedulingController {
  /**
   * 전체 스케줄링 프로세스 실행
   */
  async runFullScheduling(req, res, next) {
    try {
      const { windowDays, data } = req.body;
      const sessionId = `session-${uuidv4()}`;
      
      logger.info(`전체 스케줄링 프로세스 시작: ${sessionId}`);

      // 1단계: 데이터 검증
      const validationResult = await pythonApiService.validateData(sessionId, data);
      
      // 2단계: 전처리
      const preprocessingResult = await pythonApiService.runPreprocessing(sessionId, windowDays);
      
      // 3단계: 수율 예측
      const yieldPredictionResult = await pythonApiService.runYieldPrediction(sessionId);
      
      // 4단계: DAG 생성
      const dagCreationResult = await pythonApiService.runDAGCreation(sessionId);
      
      // 5단계: 스케줄링
      const schedulingResult = await pythonApiService.runScheduling(sessionId, windowDays);
      

      const response = {
        success: true,
        message: '스케줄링 프로세스가 성공적으로 완료되었습니다',
        data: {
          sessionId,
          steps: {
            validation: validationResult,
            preprocessing: preprocessingResult,
            yieldPrediction: yieldPredictionResult,
            dagCreation: dagCreationResult,
            scheduling: schedulingResult,
          },
          summary: {
            totalSteps: 5,
            completedSteps: 5,
            startTime: new Date().toISOString(),
            endTime: new Date().toISOString()
          }
        }
      };

      logger.info(`전체 스케줄링 프로세스 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('전체 스케줄링 프로세스 실패:', error);
      next(error);
    }
  }

  /**
   * 1단계: 데이터 검증
   */
  async validateData(req, res, next) {
    try {
      const { sessionId, windowDays, baseDate, yieldPeriod } = req.body;
      
      logger.info(`데이터 검증 시작: ${sessionId}`);

      // 모든 파일을 한 번에 로드 (main.py와 동일한 방식)
      const loadResult = await dataLoaderService.loadAllData();
      
      // Python 서버로 데이터와 함께 검증 요청
      const result = await pythonApiService.validateDataWithData(sessionId, {
        windowDays,
        baseDate,
        yieldPeriod,
        loadedData: loadResult.data,
        stats: loadResult.stats,
        loadResults: loadResult.loadResults
      });

      const response = {
        success: true,
        message: '데이터 검증이 완료되었습니다',
        data: {
          sessionId,
          validation: result,
          stats: loadResult.stats
        }
      };

      logger.info(`데이터 검증 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('데이터 검증 실패:', error);
      next(error);
    }
  }

  /**
   * 2단계: 전처리
   */
  async runPreprocessing(req, res, next) {
    try {
      const { sessionId, windowDays } = req.body;
      
      logger.info(`전처리 시작: ${sessionId}`);

      const result = await pythonApiService.runPreprocessing(sessionId, windowDays);

      const response = {
        success: true,
        message: '전처리가 완료되었습니다',
        data: {
          sessionId,
          preprocessing: result
        }
      };

      logger.info(`전처리 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('전처리 실패:', error);
      next(error);
    }
  }

  /**
   * 3단계: 수율 예측
   */
  async runYieldPrediction(req, res, next) {
    try {
      const { sessionId } = req.body;
      
      logger.info(`수율 예측 시작: ${sessionId}`);

      const result = await pythonApiService.runYieldPrediction(sessionId);

      const response = {
        success: true,
        message: '수율 예측이 완료되었습니다',
        data: {
          sessionId,
          yieldPrediction: result
        }
      };

      logger.info(`수율 예측 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('수율 예측 실패:', error);
      next(error);
    }
  }

  /**
   * 4단계: DAG 생성
   */
  async runDAGCreation(req, res, next) {
    try {
      const { sessionId } = req.body;
      
      logger.info(`DAG 생성 시작: ${sessionId}`);

      const result = await pythonApiService.runDAGCreation(sessionId);

      const response = {
        success: true,
        message: 'DAG 생성이 완료되었습니다',
        data: {
          sessionId,
          dagCreation: result
        }
      };

      logger.info(`DAG 생성 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('DAG 생성 실패:', error);
      next(error);
    }
  }

  /**
   * 5단계: 스케줄링
   */
  async runScheduling(req, res, next) {
    try {
      const { sessionId, windowDays } = req.body;
      
      logger.info(`스케줄링 시작: ${sessionId}`);

      const result = await pythonApiService.runScheduling(sessionId, windowDays);

      const response = {
        success: true,
        message: '스케줄링이 완료되었습니다',
        data: {
          sessionId,
          scheduling: result
        }
      };

      logger.info(`스케줄링 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('스케줄링 실패:', error);
      next(error);
    }
  }


  /**
   * 세션 상태 조회
   */
  async getSessionStatus(req, res, next) {
    try {
      const { sessionId } = req.params;
      
      logger.info(`세션 상태 조회: ${sessionId}`);

      const result = await pythonApiService.getSessionStatus(sessionId);

      const response = {
        success: true,
        message: '세션 상태 조회가 완료되었습니다',
        data: {
          sessionId,
          status: result
        }
      };

      logger.info(`세션 상태 조회 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('세션 상태 조회 실패:', error);
      next(error);
    }
  }

  /**
   * 6단계: 결과 처리
   */
  async runResultsProcessing(req, res, next) {
    try {
      const { sessionId } = req.body;
      
      logger.info(`결과 처리 시작: ${sessionId}`);

      // Python 서버에서 결과 처리 요청
      const result = await pythonApiService.runResultsProcessing(sessionId);

      const response = {
        success: true,
        message: '결과 처리가 완료되었습니다',
        data: {
          sessionId,
          results: result
        }
      };

      logger.info(`결과 처리 완료: ${sessionId}`);
      res.json(response);

    } catch (error) {
      logger.error('결과 처리 실패:', error);
      next(error);
    }
  }

  /**
   * 헬스 체크
   */
  async healthCheck(req, res, next) {
    try {
      const response = {
        success: true,
        message: '서버가 정상적으로 작동 중입니다',
        data: {
          timestamp: new Date().toISOString(),
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          version: process.version
        }
      };

      res.json(response);
    } catch (error) {
      logger.error('헬스 체크 실패:', error);
      next(error);
    }
  }
}

module.exports = new SchedulingController();
