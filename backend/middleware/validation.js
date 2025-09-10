/**
 * 유효성 검사 미들웨어
 */

const Joi = require('joi');
const logger = require('../utils/logger');

// 스케줄링 데이터 유효성 검사 스키마
const schedulingDataSchema = Joi.object({
  linespeed: Joi.array().items(Joi.object()).required(),
  operation_sequence: Joi.array().items(Joi.object()).required(),
  machine_master_info: Joi.array().items(Joi.object()).required(),
  yield_data: Joi.array().items(Joi.object()).required(),
  gitem_operation: Joi.array().items(Joi.object()).required(),
  operation_types: Joi.array().items(Joi.object()).required(),
  operation_delay: Joi.array().items(Joi.object()).required(),
  width_change: Joi.array().items(Joi.object()).required(),
  machine_rest: Joi.array().items(Joi.object()).required(),
  machine_allocate: Joi.array().items(Joi.object()).required(),
  machine_limit: Joi.array().items(Joi.object()).required(),
  order_data: Joi.array().items(Joi.object()).required(),
  windowDays: Joi.number().integer().min(1).max(30).optional()
});

// 세션 ID 유효성 검사 스키마
const sessionIdSchema = Joi.object({
  sessionId: Joi.string().required()
});

// 외부 API 설정 유효성 검사 스키마
const externalApiConfigSchema = Joi.object({
  base_url: Joi.string().uri().required(),
  api_key: Joi.string().optional(),
  use_mock: Joi.boolean().default(false)
});

/**
 * 스케줄링 데이터 유효성 검사
 */
const validateSchedulingData = (req, res, next) => {
  const { error, value } = schedulingDataSchema.validate(req.body);
  
  if (error) {
    logger.warn('스케줄링 데이터 유효성 검사 실패:', error.details);
    return res.status(400).json({
      success: false,
      message: '유효하지 않은 데이터입니다.',
      errors: error.details.map(detail => detail.message)
    });
  }
  
  req.body = value;
  next();
};

/**
 * 세션 ID 유효성 검사
 */
const validateSessionId = (req, res, next) => {
  const { error, value } = sessionIdSchema.validate(req.body);
  
  if (error) {
    logger.warn('세션 ID 유효성 검사 실패:', error.details);
    return res.status(400).json({
      success: false,
      message: '세션 ID가 필요합니다.',
      errors: error.details.map(detail => detail.message)
    });
  }
  
  req.body = value;
  next();
};

/**
 * 외부 API 설정 유효성 검사
 */
const validateExternalApiConfig = (req, res, next) => {
  const { error, value } = externalApiConfigSchema.validate(req.body.apiConfig);
  
  if (error) {
    logger.warn('외부 API 설정 유효성 검사 실패:', error.details);
    return res.status(400).json({
      success: false,
      message: '유효하지 않은 API 설정입니다.',
      errors: error.details.map(detail => detail.message)
    });
  }
  
  req.body.apiConfig = value;
  next();
};

/**
 * 윈도우 일수 유효성 검사
 */
const validateWindowDays = (req, res, next) => {
  const { windowDays } = req.body;
  
  if (windowDays !== undefined) {
    if (!Number.isInteger(windowDays) || windowDays < 1 || windowDays > 30) {
      return res.status(400).json({
        success: false,
        message: '윈도우 일수는 1-30 사이의 정수여야 합니다.'
      });
    }
  }
  
  next();
};

module.exports = {
  validateSchedulingData,
  validateSessionId,
  validateExternalApiConfig,
  validateWindowDays
};
