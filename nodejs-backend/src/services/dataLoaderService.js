/**
 * 데이터 로더 서비스
 * JSON 파일들을 읽어서 Python 서버로 전달
 */
const fs = require('fs').promises;
const path = require('path');
const logger = require('../utils/logger');

class DataLoaderService {
  constructor() {
    // Python 엔진의 JSON 파일 경로
    this.jsonPath = path.join(__dirname, '../../../python_engine/data/json');
  }

  /**
   * 단계별 필요한 파일들 정의
   */
  getFilesByStep(step) {
    const stepFiles = {
      validation: [
        'order', 'linespeed', 'operation_seperated_sequence', 'machine_master_info',
        'yield_data', 'gitem_operation', 'operation_types', 'operation_delay_df',
        'width_change_df', 'machine_rest', 'machine_allocate', 'machine_limit'
      ],
      preprocessing: [
        'order', 'operation_seperated_sequence', 'operation_types',
        'machine_limit', 'machine_allocate', 'linespeed'
      ],
      yieldPrediction: [
        'yield_data', 'gitem_operation'
      ],
      dagCreation: [
        'linespeed', 'machine_master_info'
      ],
      scheduling: [
        'operation_delay_df', 'width_change_df', 'machine_rest'
      ],
      results: [] // 결과 처리에는 추가 파일 불필요
    };
    
    return stepFiles[step] || [];
  }

  /**
   * 모든 JSON 파일을 로드 (main.py와 동일한 방식)
   */
  async loadAllData() {
    try {
      logger.info('JSON 파일 로딩 시작');
      
      const jsonFiles = {
        order: 'md_step2_order_data.json',
        linespeed: 'md_step2_linespeed.json',
        operation_seperated_sequence: 'md_step3_operation_sequence.json',
        machine_master_info: 'md_step4_machine_master_info.json',
        yield_data: 'md_step3_yield_data.json',
        gitem_operation: 'md_step3_gitem_operation.json',
        operation_types: 'md_step2_operation_types.json',
        operation_delay_df: 'md_step5 operation_delay.json',
        width_change_df: 'md_step5_width_change.json',
        machine_rest: 'user_step5_machine_rest.json',
        machine_allocate: 'user_step2_machine_allocate.json',
        machine_limit: 'user_step2_machine_limit.json'
      };

      const loadedData = {};
      const loadResults = {};

      for (const [key, filename] of Object.entries(jsonFiles)) {
        try {
          const filePath = path.join(this.jsonPath, filename);
          const fileContent = await fs.readFile(filePath, 'utf8');
          const data = JSON.parse(fileContent);
          
          // main.py와 동일한 데이터 변환 적용
          const processedData = this.processDataByType(key, data);
          loadedData[key] = processedData;
          
          loadResults[key] = {
            filename,
            records: Array.isArray(processedData) ? processedData.length : 1,
            status: 'success'
          };
          
          logger.info(`로드 완료: ${filename} (${Array.isArray(processedData) ? processedData.length : 1}개 레코드)`);
        } catch (error) {
          logger.error(`파일 로드 실패: ${filename} - ${error.message}`);
          loadResults[key] = {
            filename,
            records: 0,
            status: 'error',
            error: error.message
          };
        }
      }

      // 통계 계산
      const stats = this.calculateStats(loadedData);

      logger.info('JSON 파일 로딩 완료');
      
      return {
        data: loadedData,
        loadResults,
        stats
      };
    } catch (error) {
      logger.error(`데이터 로딩 실패: ${error.message}`);
      throw error;
    }
  }

  /**
   * 데이터 타입별 처리 (main.py와 동일한 로직)
   */
  processDataByType(key, data) {
    switch (key) {
      case 'order':
        // 주문 데이터: 날짜 컬럼 변환 (timezone-naive로 변환)
        return data.map(item => ({
          ...item,
          납기일: item.납기일 ? new Date(item.납기일).toISOString().replace('Z', '') : item.납기일,
          due_date: item.due_date ? new Date(item.due_date).toISOString().replace('Z', '') : item.due_date
        }));
      
      case 'machine_rest':
        // 기계 중단시간: 날짜 컬럼 변환 (timezone-naive로 변환)
        return data.map(item => ({
          ...item,
          시작시간: item.시작시간 ? new Date(item.시작시간).toISOString().replace('Z', '') : item.시작시간,
          종료시간: item.종료시간 ? new Date(item.종료시간).toISOString().replace('Z', '') : item.종료시간
        }));
      
      case 'linespeed':
        // 라인스피드 데이터: GITEM을 숫자로 보장
        return data.map(item => ({
          ...item,
          GITEM: typeof item.GITEM === 'string' ? parseInt(item.GITEM, 10) : item.GITEM
        }));
      
      case 'operation_seperated_sequence':
        // 시퀀스 데이터: GITEM을 숫자로 보장
        return data.map(item => ({
          ...item,
          GITEM: typeof item.GITEM === 'string' ? parseInt(item.GITEM, 10) : item.GITEM
        }));
      
      case 'machine_master_info':
      case 'yield_data':
      case 'gitem_operation':
      case 'operation_types':
      case 'operation_delay_df':
      case 'width_change_df':
      case 'machine_allocate':
      case 'machine_limit':
        // 기본 데이터는 그대로 반환
        return data;
      
      default:
        return data;
    }
  }

  /**
   * 단계별 필요한 파일만 로드
   */
  async loadDataByStep(step) {
    try {
      logger.info(`${step} 단계 데이터 로딩 시작`);
      
      const requiredFiles = this.getFilesByStep(step);
      if (requiredFiles.length === 0) {
        logger.info(`${step} 단계는 추가 파일 로딩이 필요하지 않습니다.`);
        return { data: {}, loadResults: {}, stats: {} };
      }
      
      const jsonFiles = {
        order: 'md_step2_order_data.json',
        linespeed: 'md_step2_linespeed.json',
        operation_seperated_sequence: 'md_step3_operation_sequence.json',
        machine_master_info: 'md_step4_machine_master_info.json',
        yield_data: 'md_step3_yield_data.json',
        gitem_operation: 'md_step3_gitem_operation.json',
        operation_types: 'md_step2_operation_types.json',
        operation_delay_df: 'md_step5 operation_delay.json',
        width_change_df: 'md_step5_width_change.json',
        machine_rest: 'user_step5_machine_rest.json',
        machine_allocate: 'user_step2_machine_allocate.json',
        machine_limit: 'user_step2_machine_limit.json'
      };

      const loadedData = {};
      const loadResults = {};

      // 필요한 파일만 로딩
      for (const fileKey of requiredFiles) {
        const filename = jsonFiles[fileKey];
        if (!filename) {
          logger.warning(`파일 키 '${fileKey}'에 해당하는 파일명이 없습니다.`);
          continue;
        }

        try {
          const filePath = path.join(this.jsonPath, filename);
          const fileContent = await fs.readFile(filePath, 'utf8');
          const data = JSON.parse(fileContent);
          
          // main.py와 동일한 데이터 변환 적용
          const processedData = this.processDataByType(fileKey, data);
          loadedData[fileKey] = processedData;
          
          loadResults[fileKey] = {
            filename,
            records: Array.isArray(processedData) ? processedData.length : 1,
            status: 'success'
          };
          
          logger.info(`로드 완료: ${filename} (${Array.isArray(processedData) ? processedData.length : 1}개 레코드)`);
        } catch (error) {
          logger.error(`파일 로드 실패: ${filename} - ${error.message}`);
          loadResults[fileKey] = {
            filename,
            records: 0,
            status: 'error',
            error: error.message
          };
        }
      }

      // 통계 계산
      const stats = this.calculateStats(loadedData);

      logger.info(`${step} 단계 데이터 로딩 완료`);
      
      return {
        data: loadedData,
        loadResults,
        stats
      };
    } catch (error) {
      logger.error(`${step} 단계 데이터 로딩 실패: ${error.message}`);
      throw error;
    }
  }

  /**
   * 데이터 통계 계산
   */
  calculateStats(loadedData) {
    const stats = {
      total_orders: 0,
      total_linespeed: 0,
      total_machines: 0,
      total_operation_types: 0,
      total_yield_data: 0,
      total_gitem_operation: 0,
      loaded_files_count: 0,
      success_files_count: 0
    };

    // 주문 데이터 통계
    if (loadedData.order && Array.isArray(loadedData.order)) {
      stats.total_orders = loadedData.order.length;
    }

    // 라인스피드 통계
    if (loadedData.linespeed && Array.isArray(loadedData.linespeed)) {
      stats.total_linespeed = loadedData.linespeed.length;
    }

    // 기계 정보 통계
    if (loadedData.machine_master_info && Array.isArray(loadedData.machine_master_info)) {
      stats.total_machines = loadedData.machine_master_info.length;
    }

    // 공정 분류 통계
    if (loadedData.operation_types && Array.isArray(loadedData.operation_types)) {
      stats.total_operation_types = loadedData.operation_types.length;
    }

    // 수율 데이터 통계
    if (loadedData.yield_data && Array.isArray(loadedData.yield_data)) {
      stats.total_yield_data = loadedData.yield_data.length;
    }

    // GITEM 공정 통계
    if (loadedData.gitem_operation && Array.isArray(loadedData.gitem_operation)) {
      stats.total_gitem_operation = loadedData.gitem_operation.length;
    }

    // 파일 로딩 통계
    const fileKeys = Object.keys(loadedData);
    stats.loaded_files_count = fileKeys.length;
    stats.success_files_count = fileKeys.filter(key => loadedData[key] !== undefined).length;

    return stats;
  }
}

module.exports = new DataLoaderService();


