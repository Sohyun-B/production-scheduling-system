/**
 * 헬스 체크 라우트
 */

const express = require('express');
const router = express.Router();
const pythonApiService = require('../services/pythonApiService');
const { asyncHandler } = require('../middleware/asyncHandler');

/**
 * @route GET /api/health
 * @desc 서버 상태 확인
 */
router.get('/', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.env.npm_package_version || '1.0.0'
  });
});

/**
 * @route GET /api/health/python
 * @desc Python API 상태 확인
 */
router.get('/python', asyncHandler(async (req, res) => {
  const pythonHealth = await pythonApiService.healthCheck();
  
  res.json({
    status: pythonHealth.success ? 'healthy' : 'unhealthy',
    python_api: pythonHealth,
    timestamp: new Date().toISOString()
  });
}));

/**
 * @route GET /api/health/detailed
 * @desc 상세 상태 확인
 */
router.get('/detailed', asyncHandler(async (req, res) => {
  const pythonHealth = await pythonApiService.healthCheck();
  
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {
      nodejs: {
        status: 'healthy',
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        version: process.version
      },
      python_api: {
        status: pythonHealth.success ? 'healthy' : 'unhealthy',
        response: pythonHealth.data || null,
        error: pythonHealth.error || null
      }
    },
    environment: {
      node_env: process.env.NODE_ENV,
      port: process.env.PORT,
      python_api_url: process.env.PYTHON_API_URL
    }
  });
}));

module.exports = router;
