/**
 * 에러 처리 미들웨어
 */
const logger = require('../utils/logger');
const config = require('../../config');

const errorHandler = (err, req, res, next) => {
  logger.error('에러 발생:', {
    error: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });

  // 기본 에러 응답
  let statusCode = err.statusCode || 500;
  let message = err.message || '서버 내부 오류가 발생했습니다';
  let details = null;

  // 에러 타입별 처리
  if (err.type === 'API_ERROR') {
    statusCode = err.status || 500;
    message = err.message || 'Python API 오류가 발생했습니다';
    details = config.error.detailsInResponse ? err.details : null;
  } else if (err.type === 'NETWORK_ERROR') {
    statusCode = 503;
    message = 'Python API 서버에 연결할 수 없습니다';
  } else if (err.type === 'VALIDATION_ERROR') {
    statusCode = 400;
    message = '요청 데이터가 올바르지 않습니다';
    details = config.error.detailsInResponse ? err.details : null;
  } else if (err.name === 'ValidationError') {
    statusCode = 400;
    message = '요청 데이터 검증 실패';
    details = config.error.detailsInResponse ? err.details : null;
  }

  // 응답 생성
  const errorResponse = {
    success: false,
    error: {
      message,
      statusCode,
      timestamp: new Date().toISOString(),
      path: req.url,
      method: req.method
    }
  };

  // 개발 환경에서만 상세 정보 포함
  if (config.server.env === 'development' && details) {
    errorResponse.error.details = details;
  }

  res.status(statusCode).json(errorResponse);
};

module.exports = errorHandler;


