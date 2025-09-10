/**
 * 비동기 에러 핸들링 미들웨어
 */

const logger = require('../utils/logger');

/**
 * 비동기 함수를 래핑하여 에러를 자동으로 처리
 * @param {Function} fn - 비동기 함수
 * @returns {Function} Express 미들웨어 함수
 */
const asyncHandler = (fn) => {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch((error) => {
      logger.error('비동기 핸들러 에러:', {
        error: error.message,
        stack: error.stack,
        url: req.url,
        method: req.method,
        body: req.body
      });
      
      // 이미 응답이 전송된 경우
      if (res.headersSent) {
        return next(error);
      }
      
      // 에러 응답
      res.status(500).json({
        success: false,
        message: '서버 내부 오류가 발생했습니다.',
        error: process.env.NODE_ENV === 'development' ? error.message : 'Internal Server Error'
      });
    });
  };
};

module.exports = { asyncHandler };
