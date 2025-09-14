/**
 * Express 애플리케이션 메인 파일
 */
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const bodyParser = require('body-parser');

const config = require('../config');
const logger = require('./utils/logger');
const requestLogger = require('./middleware/requestLogger');
const errorHandler = require('./middleware/errorHandler');

// 라우터 import
const schedulingRoutes = require('./routes/schedulingRoutes');

class App {
  constructor() {
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
    this.setupErrorHandling();
  }

  /**
   * 미들웨어 설정
   */
  setupMiddleware() {
    // 보안 미들웨어
    this.app.use(helmet());
    
    // CORS 설정 - 모든 origin 허용
    this.app.use(cors({
      origin: true, // 모든 origin 허용
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    }));
    
    // 압축 미들웨어
    this.app.use(compression());
    
    // 요청 로깅
    this.app.use(requestLogger);
    
    // Morgan HTTP 로깅
    this.app.use(morgan('combined', {
      stream: {
        write: (message) => logger.info(message.trim())
      }
    }));
    
    // Rate Limiting
    const limiter = rateLimit({
      windowMs: config.rateLimit.windowMs,
      max: config.rateLimit.max,
      message: {
        success: false,
        error: {
          message: '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.',
          statusCode: 429
        }
      }
    });
    this.app.use('/api/', limiter);
    
    // Body parsing 미들웨어
    this.app.use(bodyParser.json({ limit: '50mb' }));
    this.app.use(bodyParser.urlencoded({ extended: true, limit: '50mb' }));
    
    // 정적 파일 서빙
    this.app.use(express.static('public'));
  }

  /**
   * 라우터 설정
   */
  setupRoutes() {
    // 기본 라우트
    this.app.get('/', (req, res) => {
      res.json({
        success: true,
        message: 'Production Scheduling Backend API',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        endpoints: {
          health: '/api/scheduling/health',
          fullScheduling: '/api/scheduling/full',
          validate: '/api/scheduling/validate',
          preprocessing: '/api/scheduling/preprocessing',
          yieldPrediction: '/api/scheduling/yield-prediction',
          dagCreation: '/api/scheduling/dag-creation',
          scheduling: '/api/scheduling/scheduling',
          results: '/api/scheduling/results',
          status: '/api/scheduling/status/:sessionId'
        }
      });
    });

    // API 라우터
    this.app.use('/api/scheduling', schedulingRoutes);

    // 404 처리
    this.app.use('*', (req, res) => {
      res.status(404).json({
        success: false,
        error: {
          message: '요청한 리소스를 찾을 수 없습니다',
          statusCode: 404,
          path: req.originalUrl
        }
      });
    });
  }

  /**
   * 에러 처리 설정
   */
  setupErrorHandling() {
    this.app.use(errorHandler);
  }

  /**
   * 서버 시작
   */
  start() {
    const port = config.server.port;
    const host = config.server.host;
    
    this.app.listen(port, host, () => {
      logger.info(`서버가 시작되었습니다: http://${host}:${port}`);
      logger.info(`환경: ${config.server.env}`);
      logger.info(`Python API: ${config.pythonApi.baseUrl}`);
    });
  }

  /**
   * Express 앱 인스턴스 반환
   */
  getApp() {
    return this.app;
  }
}

module.exports = App;
