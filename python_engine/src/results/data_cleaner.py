"""
스케줄링 결과의 공통 전처리 모듈 (results 전용)
가짜 작업(depth -1) 제거 및 makespan 계산
"""

import pandas as pd
from config import config


class DataCleaner:
    """스케줄링 결과 데이터 정리 및 가짜 작업 제거"""
    
    @staticmethod
    def clean_scheduling_result(raw_scheduling_result):
        """
        원본 스케줄링 결과에서 가짜 작업 제거 및 makespan 계산
        
        Args:
            raw_scheduling_result (pd.DataFrame): 스케줄러 원본 결과 (depth -1 포함)
            
        Returns:
            dict: {
                'result_cleaned': pd.DataFrame,     # 가짜 작업 제거된 결과
                'actual_makespan': float,          # 실제 makespan (가짜 작업 제외)
                'total_makespan': float            # 전체 makespan (가짜 작업 포함)
            }
        """
        # makespan 계산
        actual_makespan = raw_scheduling_result[
            ~(raw_scheduling_result['depth'] == -1)
        ]['node_end'].max()
        total_makespan = raw_scheduling_result['node_end'].max()
        
        # depth -1인 가짜 공정 제거
        result_cleaned = raw_scheduling_result[
            ~(raw_scheduling_result['depth'] == -1)
        ].copy()
        
        return {
            'result_cleaned': result_cleaned,
            'actual_makespan': actual_makespan,
            'total_makespan': total_makespan
        }
    
    @staticmethod
    def clean_machine_schedule(scheduler):
        """
        기계 스케줄에서 가짜 작업 제거
        
        Args:
            scheduler: 스케줄러 인스턴스
            
        Returns:
            pd.DataFrame: 가짜 작업이 제거된 기계 스케줄
        """
        # 기계 스케줄 데이터프레임 생성
        machine_schedule_df = scheduler.create_machine_schedule_dataframe()
        
        # 할당 작업이 -1 공정인 경우 삭제
        machine_schedule_df = machine_schedule_df[
            ~machine_schedule_df[config.columns.ALLOCATED_WORK].astype(str).str.startswith('[-1', na=False)
        ]
        
        return machine_schedule_df
    
    @staticmethod
    def clean_all_data(raw_scheduling_result, scheduler):
        """
        모든 데이터 정리 (스케줄링 결과 + 기계 스케줄)
        
        Args:
            raw_scheduling_result (pd.DataFrame): 원본 스케줄링 결과
            scheduler: 스케줄러 인스턴스
            
        Returns:
            dict: {
                'result_cleaned': pd.DataFrame,
                'actual_makespan': float,
                'total_makespan': float,
                'machine_schedule_df': pd.DataFrame
            }
        """
        # 스케줄링 결과 정리
        scheduling_results = DataCleaner.clean_scheduling_result(raw_scheduling_result)
        
        # 기계 스케줄 정리
        machine_schedule_df = DataCleaner.clean_machine_schedule(scheduler)
        
        return {
            **scheduling_results,
            'machine_schedule_df': machine_schedule_df
        }