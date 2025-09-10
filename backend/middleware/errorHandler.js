/**
 * 에러 핸들링 미들웨어
 */

const logger = require('../utils/logger');

/**
 * 404 에러 핸들러
 */
const notFound = (req, res, next) => {
  const error = new Error(`Not Found - ${req.originalUrl}`);
  error.status = 404;
  next(error);
};

/**
 * 전역 에러 핸들러
 */
const errorHandler = (err, req, res, next) => {
  let error = { ...err };
  error.message = err.message;

  // 로그 기록
  logger.error('에러 발생:', {
    message: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });

  // Mongoose 잘못된 ObjectId
  if (err.name === 'CastError') {
    const message = '리소스를 찾을 수 없습니다.';
    error = { message, status: 404 };
  }

  // Mongoose 중복 키
  if (err.code === 11000) {
    const message = '중복된 데이터입니다.';
    error = { message, status: 400 };
  }

  // Mongoose 유효성 검사 오류
  if (err.name === 'ValidationError') {
    const message = Object.values(err.errors).map(val => val.message).join(', ');
    error = { message, status: 400 };
  }

  // JWT 오류
  if (err.name === 'JsonWebTokenError') {
    const message = '유효하지 않은 토큰입니다.';
    error = { message, status: 401 };
  }

  // JWT 만료 오류
  if (err.name === 'TokenExpiredError') {
    const message = '토큰이 만료되었습니다.';
    error = { message, status: 401 };
  }

  res.status(error.status || 500).json({
    success: false,
    message: error.message || '서버 오류가 발생했습니다.',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
};

module.exports = {
  notFound,
  errorHandler
};
