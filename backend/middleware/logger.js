/**
 * 요청 로깅 미들웨어
 */

const logger = require('../utils/logger');

/**
 * 요청 로깅 미들웨어
 */
const requestLogger = (req, res, next) => {
  const start = Date.now();
  
  // 응답 완료 시 로그 기록
  res.on('finish', () => {
    const duration = Date.now() - start;
    const logData = {
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration: `${duration}ms`,
      ip: req.ip,
      userAgent: req.get('User-Agent')
    };
    
    if (res.statusCode >= 400) {
      logger.warn('HTTP 요청 완료 (에러):', logData);
    } else {
      logger.info('HTTP 요청 완료:', logData);
    }
  });
  
  next();
};

module.exports = { requestLogger };
