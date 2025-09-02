# 🏭 Python 스케줄링 엔진 데이터 추출 가이드

## 개요
Python 스케줄링 엔진에서 FastAPI를 통해 프론트엔드로 전달해야 하는 실제 데이터들과 JSON 저장 방식을 정리한 문서입니다.

---

## 1단계: 데이터 로딩

### Python 코드 위치
`main.py` 34~58번째 줄에서 Excel 파일들을 읽어들입니다.

### 추출할 데이터
- **라인스피드 데이터 개수**: `len(linespeed)` 
- **기계 정보 개수**: `len(machine_master_info)`
- **공정 분류 개수**: `len(operation_types)`
- **지연 정보 개수**: `len(operation_delay_df)`
- **총 주문 개수**: `len(order)`
- **기본 설정값**: `config.constants.BASE_YEAR`, `BASE_MONTH`, `BASE_DAY`, `window_days`

### JSON 저장 코드
```python
# main.py 58줄 이후 추가
stage1_data = {
    "stage": "loading",
    "data": {
        "linespeed_count": len(linespeed),
        "machine_count": len(machine_master_info),
        "operation_types_count": len(operation_types),
        "operation_delay_count": len(operation_delay_df),
        "total_orders": len(order),
        "base_config": {
            "base_year": config.constants.BASE_YEAR,
            "base_month": config.constants.BASE_MONTH,
            "base_day": config.constants.BASE_DAY,
            "window_days": window_days
        }
    }
}

import json
with open("stage1_loading.json", "w", encoding="utf-8") as f:
    json.dump(stage1_data, f, ensure_ascii=False)
```

---

## 2단계: 전처리

### Python 코드 위치
`main.py` 62번째 줄의 `preprocessing()` 함수 호출 결과

### 추출할 데이터
- **입력 주문 수**: `len(order)` (전처리 전)
- **처리된 작업 수**: `len(sequence_seperated_order)` (전처리 후)
- **기계 제약조건 정보**: 각 시트별 딕셔너리 형태 변환

### JSON 저장 코드
```python
# main.py 63줄 이후 추가
stage2_data = {
    "stage": "preprocessing", 
    "data": {
        "input_orders": len(order),
        "processed_jobs": len(sequence_seperated_order),
        "machine_constraints": {
            "machine_rest": machine_rest.to_dict('records'),
            "machine_allocate": machine_allocate.to_dict('records'),
            "machine_limit": machine_limit.to_dict('records')
        }
    }
}

with open("stage2_preprocessing.json", "w", encoding="utf-8") as f:
    json.dump(stage2_data, f, ensure_ascii=False)
```

---

## 5단계: 스케줄링 실행

### Python 코드 위치
`main.py` 119~137번째 줄의 스케줄링 알고리즘 실행

### 추출할 데이터
- **사용된 윈도우 크기**: `window_days`
- **실제 makespan (슬롯 단위)**: `result[~(result['depth'] == -1)]['node_end'].max()`
- **전체 makespan (슬롯 단위)**: `result['node_end'].max()`  
- **실제 makespan (시간 단위)**: 슬롯 * 0.5 (30분 슬롯이므로)
- **총 소요 일수**: (슬롯 * 0.5) / 24
- **처리된 실제 작업 수**: `len(result[~(result['depth'] == -1)])`

### JSON 저장 코드
```python
# main.py 137줄 이후 추가
actual_makespan = result[~(result['depth'] == -1)]['node_end'].max()
total_makespan = result['node_end'].max()

stage5_data = {
    "stage": "scheduling",
    "data": {
        "window_days_used": window_days,
        "actual_makespan_slots": int(actual_makespan),
        "total_makespan_slots": int(total_makespan),
        "actual_makespan_hours": actual_makespan * 0.5,
        "total_days": (actual_makespan * 0.5) / 24,
        "processed_jobs_count": len(result[~(result['depth'] == -1)])
    }
}

with open("stage5_scheduling.json", "w", encoding="utf-8") as f:
    json.dump(stage5_data, f, ensure_ascii=False)
```

### 주요 계산식
- 30분 슬롯 기준이므로 시간 변환 시 0.5를 곱함
- depth가 -1인 가짜 공정은 제외하고 계산
- `DispatchPriorityStrategy().execute()` 메서드의 반환값이 핵심 결과

---

## 6단계: 최종 결과 생성

### Python 코드 위치
`main.py` 155~252번째 줄의 결과 생성 및 파일 저장

### 추출할 데이터
- **지각 총 일수**: `results['late_days_sum']`
- **최종 makespan**: `results['new_output_final_result']['종료시각'].max()`
- **주문 생산 요약**: `results['new_output_final_result']` DataFrame을 딕셔너리 리스트로 변환
- **기계 정보**: `results['machine_info']` DataFrame을 딕셔너리 리스트로 변환  
- **전체 주문 정보**: `results['merged_result']` DataFrame을 딕셔너리 리스트로 변환
- **생성된 파일 정보**: 파일 존재 여부 및 크기

### JSON 저장 코드
```python
# main.py 252줄 이후 추가
stage6_data = {
    "stage": "results",
    "data": {
        "late_days_sum": results['late_days_sum'],
        "final_makespan": float(results['new_output_final_result']['종료시각'].max()),
        "order_summary": results['new_output_final_result'].to_dict('records'),
        "machine_info": results['machine_info'].to_dict('records'),
        "merged_result": results['merged_result'].to_dict('records'),
        "files": {
            "excel_filename": processed_filename,
            "gantt_filename": gantt_filename,
            "excel_exists": os.path.exists(processed_filename),
            "gantt_exists": os.path.exists(gantt_filename),
            "excel_size": os.path.getsize(processed_filename) if os.path.exists(processed_filename) else 0,
            "gantt_size": os.path.getsize(gantt_filename) if os.path.exists(gantt_filename) else 0
        }
    }
}

with open("stage6_results.json", "w", encoding="utf-8") as f:
    json.dump(stage6_data, f, ensure_ascii=False, default=str)  # datetime 처리를 위해 default=str 추가
```

### 생성되는 파일들
- **단계별 JSON 파일**: `stage1_loading.json`, `stage2_preprocessing.json`, `stage5_scheduling.json`, `stage6_results.json`
- **Excel 파일**: `0829 스케줄링결과.xlsx` (3개 시트 포함)
- **간트 차트**: `level4_gantt.png`

---

## FastAPI 연동 방법

### JSON 파일 읽기
FastAPI에서는 각 단계별 JSON 파일을 순차적으로 읽어서 프론트엔드로 전달합니다:

```python
# FastAPI 백엔드에서
import json
import os

def read_stage_data(stage_name):
    file_path = f"python_engine/stage{stage_name}.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# 모든 단계 데이터 수집
all_stages_data = {
    "stage1": read_stage_data("1_loading"),
    "stage2": read_stage_data("2_preprocessing"), 
    "stage5": read_stage_data("5_scheduling"),
    "stage6": read_stage_data("6_results")
}
```

---

## 주요 구현 주의사항

1. **DataFrame 변환**: `to_dict('records')` 사용으로 JSON 호환 형태 변환
2. **datetime 처리**: `default=str` 옵션으로 날짜 객체 문자열 변환  
3. **NaN 값 처리**: pandas NaN을 JSON null로 자동 변환
4. **파일 인코딩**: UTF-8로 한글 파일명/데이터 처리
5. **파일 존재 확인**: `os.path.exists()`로 파일 생성 여부 검증

이 가이드를 바탕으로 Python 엔진의 4개 단계별 데이터를 JSON으로 저장하고 FastAPI를 통해 프론트엔드로 전달할 수 있습니다.