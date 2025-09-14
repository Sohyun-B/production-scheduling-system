/**
 * Winston 로거 설정
 */
const winston = require('winston');
const path = require('path');
const config = require('../../config');

// 로그 포맷 설정
const logFormat = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss'
  }),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

// 콘솔 포맷 설정
const consoleFormat = winston.format.combine(
  winston.format.colorize(),
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss'
  }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let msg = `${timestamp} [${level}]: ${message}`;
    if (Object.keys(meta).length > 0) {
      try {
        // circular structure 방지를 위해 safe stringify 사용
        const safeMeta = JSON.parse(JSON.stringify(meta, (key, value) => {
          if (typeof value === 'object' && value !== null) {
            if (value.constructor && value.constructor.name === 'ClientRequest') {
              return '[ClientRequest]';
            }
            if (value.constructor && value.constructor.name === 'IncomingMessage') {
              return '[IncomingMessage]';
            }
          }
          return value;
        }));
        msg += ` ${JSON.stringify(safeMeta)}`;
      } catch (e) {
        msg += ` [Circular structure detected]`;
      }
    }
    return msg;
  })
);

// 로거 생성
const logger = winston.createLogger({
  level: config.logging.level,
  format: logFormat,
  defaultMeta: { service: 'production-scheduling-backend' },
  transports: [
    // 파일 로그
    new winston.transports.File({
      filename: path.join(__dirname, '../../logs/error.log'),
      level: 'error',
      maxsize: config.logging.maxSize,
      maxFiles: config.logging.maxFiles
    }),
    new winston.transports.File({
      filename: path.join(__dirname, '../../logs/combined.log'),
      maxsize: config.logging.maxSize,
      maxFiles: config.logging.maxFiles
    })
  ]
});

// 개발 환경에서는 콘솔에도 출력
if (config.server.env !== 'production') {
  logger.add(new winston.transports.Console({
    format: consoleFormat
  }));
}

module.exports = logger;
