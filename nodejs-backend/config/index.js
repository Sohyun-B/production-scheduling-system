/**
 * 애플리케이션 설정 관리
 */
require('dotenv').config();

const config = {
  // 서버 설정
  server: {
    port: process.env.PORT || 3000,
    host: process.env.HOST || 'localhost',
    env: process.env.NODE_ENV || 'development'
  },

  // Python FastAPI 서버 설정
  pythonApi: {
    baseUrl: process.env.PYTHON_API_BASE_URL || 'http://localhost:8000',
    timeout: parseInt(process.env.PYTHON_API_TIMEOUT) || 300000, // 5분
    endpoints: {
      validation: '/api/v1/validation/',
      preprocessing: '/api/v1/preprocessing/',
      yieldPrediction: '/api/v1/yield-prediction/',
      dagCreation: '/api/v1/dag-creation/',
      scheduling: '/api/v1/scheduling/',
      results: '/api/v1/results/',
      status: '/api/v1/status/'
    }
  },

  // 로깅 설정
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || 'logs/app.log',
    maxSize: '20m',
    maxFiles: 5
  },

  // CORS 설정
  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
    credentials: true
  },

  // Rate Limiting 설정
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 900000, // 15분
    max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100
  },

  // 세션 설정
  session: {
    secret: process.env.SESSION_SECRET || 'your-session-secret-key',
    timeout: parseInt(process.env.SESSION_TIMEOUT) || 3600000 // 1시간
  },

  // 에러 처리 설정
  error: {
    detailsInResponse: process.env.ERROR_DETAILS_IN_RESPONSE === 'true'
  }
};

module.exports = config;


