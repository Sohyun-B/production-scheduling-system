/**
 * Production Scheduling Backend Server
 * Node.js Express 서버 - Python API와 프론트엔드 사이의 중간 계층
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const schedulingRoutes = require('./routes/scheduling');
const stagesRoutes = require('./routes/stages');
const healthRoutes = require('./routes/health');
const { errorHandler, notFound } = require('./middleware/errorHandler');
const { requestLogger } = require('./middleware/logger');

const app = express();
const PORT = process.env.PORT || 3001;

// 보안 미들웨어
app.use(helmet());

// CORS 설정
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true
}));

// 압축 미들웨어
app.use(compression());

// 로깅 미들웨어
app.use(morgan('combined'));
app.use(requestLogger);

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100, // 최대 100 요청
  message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

// Body parsing 미들웨어
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 라우트 설정
app.use('/api/health', healthRoutes);
app.use('/api/scheduling', schedulingRoutes);
app.use('/api/stages', stagesRoutes);

// 루트 엔드포인트
app.get('/', (req, res) => {
  res.json({
    message: 'Production Scheduling Backend Server',
    version: '1.0.0',
    status: 'running',
    timestamp: new Date().toISOString()
  });
});

// 에러 핸들링 미들웨어
app.use(notFound);
app.use(errorHandler);

// 서버 시작
app.listen(PORT, () => {
  console.log(`🚀 Backend server running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log(`📋 API docs: http://localhost:${PORT}/api/scheduling/docs`);
});

module.exports = app;
