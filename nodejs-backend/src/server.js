/**
 * 서버 시작 파일
 */
const App = require('./app');
const config = require('../config');
const logger = require('./utils/logger');

// 프로세스 종료 처리
process.on('SIGTERM', () => {
  logger.info('SIGTERM 신호를 받았습니다. 서버를 종료합니다...');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT 신호를 받았습니다. 서버를 종료합니다...');
  process.exit(0);
});

// 처리되지 않은 예외 처리
process.on('uncaughtException', (error) => {
  logger.error('처리되지 않은 예외:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('처리되지 않은 Promise 거부:', { reason, promise });
  process.exit(1);
});

// 애플리케이션 시작
try {
  const app = new App();
  app.start();
} catch (error) {
  logger.error('서버 시작 실패:', error);
  process.exit(1);
}


