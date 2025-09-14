/**
 * 요청 데이터 검증 미들웨어
 */
const Joi = require('joi');
const logger = require('../utils/logger');

/**
 * 스케줄링 요청 검증 스키마
 */
const schedulingRequestSchema = Joi.object({
  windowDays: Joi.number().integer().min(1).max(30).optional().default(5),
  data: Joi.object({
    order_data: Joi.array().items(Joi.object()).required(),
    linespeed: Joi.array().items(Joi.object()).required(),
    operation_seperated_sequence: Joi.array().items(Joi.object()).required(),
    machine_master_info: Joi.array().items(Joi.object()).required(),
    yield_data: Joi.array().items(Joi.object()).required(),
    gitem_operation: Joi.array().items(Joi.object()).required(),
    operation_types: Joi.array().items(Joi.object()).required(),
    operation_delay_df: Joi.array().items(Joi.object()).required(),
    width_change_df: Joi.array().items(Joi.object()).required(),
    machine_rest: Joi.array().items(Joi.object()).required(),
    machine_allocate: Joi.array().items(Joi.object()).required(),
    machine_limit: Joi.array().items(Joi.object()).required()
  }).required()
});

/**
 * 단계별 요청 검증 스키마
 */
const stepRequestSchema = Joi.object({
  sessionId: Joi.string().required(),
  windowDays: Joi.number().integer().min(1).max(30).optional().default(5)
});

/**
 * Validation 단계 요청 검증 스키마 (설정만 필요)
 */
const validationRequestSchema = Joi.object({
  sessionId: Joi.string().required(),
  windowDays: Joi.number().integer().min(1).max(30).optional().default(5),
  baseDate: Joi.string().optional(),
  yieldPeriod: Joi.number().integer().min(1).max(12).optional().default(6)
});

/**
 * 세션 ID 검증 스키마
 */
const sessionIdSchema = Joi.object({
  sessionId: Joi.string().required()
});

/**
 * 검증 미들웨어 생성 함수
 */
const createValidationMiddleware = (schema, property = 'body') => {
  return (req, res, next) => {
    const data = req[property];
    
    const { error, value } = schema.validate(data, {
      abortEarly: false,
      stripUnknown: true
    });

    if (error) {
      logger.warn('요청 데이터 검증 실패:', {
        url: req.url,
        method: req.method,
        errors: error.details
      });

      const validationError = new Error('요청 데이터가 올바르지 않습니다');
      validationError.type = 'VALIDATION_ERROR';
      validationError.statusCode = 400;
      validationError.details = error.details.map(detail => ({
        field: detail.path.join('.'),
        message: detail.message
      }));

      return next(validationError);
    }

    // 검증된 데이터로 교체
    req[property] = value;
    next();
  };
};

/**
 * 스케줄링 요청 검증
 */
const validateSchedulingRequest = createValidationMiddleware(schedulingRequestSchema);

/**
 * 단계별 요청 검증
 */
const validateStepRequest = createValidationMiddleware(stepRequestSchema);

/**
 * Validation 단계 요청 검증
 */
const validateValidationRequest = createValidationMiddleware(validationRequestSchema);

/**
 * 세션 ID 검증
 */
const validateSessionId = createValidationMiddleware(sessionIdSchema, 'params');

module.exports = {
  validateSchedulingRequest,
  validateStepRequest,
  validateValidationRequest,
  validateSessionId
};
