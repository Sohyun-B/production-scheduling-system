# Python 스케줄링 엔진

## 스케줄링 엔진 구조

### 디렉토리 구조
```
python_engine/
├── main.py                     # 메인 실행 파일 (Level 4 스케줄링)
├── config.py                   # 설정 파일 (데이터 경로, 상수)
├── preprocessing/              # 데이터 전처리 모듈
├── yield_management/           # 수율 관리 모듈  
├── dag_management/            # DAG 생성 및 관리 모듈
├── scheduler/                 # 스케줄링 알고리즘
│   └── scheduling_core.py     # DispatchPriorityStrategy
└── results/                   # 결과 생성 모듈
```

### 데이터 파일
```
python_engine/
├── preprocessed_order.xlsx              # 전처리된 주문 데이터 (174개)
├── 25년 생산 제품 공정정보(1월~7월)-베합코드 추가.xlsx
├── 품목별 분리 라인스피드 및 공정 순서.xlsx
├── 공정 재분류 내역 및 교체 시간 정리(250820).xlsx
└── 불가능한 공정 입력값.xlsx
```

### 결과 파일
```
python_engine/
├── 0829 스케줄링결과.xlsx      # 스케줄링 결과 (주문_생산_요약본, 호기_정보 시트)
├── level4_gantt.png           # 간트 차트 시각화
├── level4_result.xlsx         # Level 4 결과
└── result.xlsx               # 일반 결과
```

## 메인 실행 로직 (main.py)

### Level 4 스케줄링 프로세스
```python
def run_level4_scheduling():
    # 1. 데이터 로딩 및 전처리
    print("데이터 로딩 및 전처리 중...")
    
    # Excel 파일들 읽기
    excel_data_1 = pd.read_excel(config.files.ITEM_LINESPEED_SEQUENCE, sheet_name=None)
    linespeed = excel_data_1[config.sheets.ITEM_LINESPEED]
    operation_sequence = excel_data_1[config.sheets.GITEM_OPERATION]
    
    # 2. 전처리 실행
    preprocessed_data = preprocessing.run_preprocessing(
        po_data, linespeed, operation_sequence, 
        machine_master_info, yield_data, base_date, window_days
    )
    
    # 3. DAG 생성
    process_table = make_process_table(preprocessed_data, operation_sequence)
    DAG, node_dict = run_dag_pipeline(process_table)
    
    # 4. 스케줄링 실행
    print("\n스케줄링 실행 중...")
    strategy = DispatchPriorityStrategy()
    result = strategy.schedule(DAG, node_dict)
    
    # 5. 결과 생성 및 저장
    create_results.create_all_results(result, config.output_files)
```

## 설정 파일 (config.py)

### 파일 경로 설정
```python
@dataclass
class FileConfig:
    # 입력 파일들
    ORDERS_DATA = "25년 5월 PO 내역(송부건).xlsx"
    ITEM_LINESPEED_SEQUENCE = "품목별 분리 라인스피드 및 공정 순서.xlsx"
    PROCESS_INFO = "25년 생산 제품 공정정보(1월~7월)-베합코드 추가.xlsx"
    
    # 출력 파일들
    SCHEDULING_RESULT = "0829 스케줄링결과.xlsx"
    GANTT_CHART = "level4_gantt.png"
```

### 시트명 설정
```python
@dataclass
class SheetConfig:
    ITEM_LINESPEED = "품목별 분리 라인스피드"
    OPERATION_SEQUENCE = "GITEM별 공정 순서"
    MACHINE_MASTER_INFO = "호기 마스터 정보"
    YIELD_DATA = "수율"
```

### 상수 설정
```python
@dataclass
class Constants:
    BASE_YEAR = 2025
    BASE_MONTH = 5
    BASE_DAY = 1
    WINDOW_DAYS = 60
    MAX_SCHEDULING_TIME = 300  # 최대 실행 시간 (초)
```

## 전처리된 주문 데이터 (preprocessed_order.xlsx)

### 데이터 구조
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| P/O NO | String | 주문번호 | SW1250407101 |
| GITEM | String | 품목코드 | 31704 |
| GITEM명 | String | 품목명 | PPF-NS-TGA(WHITE) |
| 너비 | Float | 폭 (mm) | 1524.0 |
| 길이 | Float | 길이 (mm) | 15.0 |
| 의뢰량 | Integer | 요청 수량 | 20 |
| 원단길이 | Float | 원단 길이 | 300.0 |
| 납기일 | Date | 납기일 | 2025-05-21 |

### 데이터 특징
- **총 174개 주문** (실제 생산 데이터)
- **다양한 제품 타입**: PPF, WINDSHIELD, Phantom 등
- **실제 치수 정보**: 350x1524, 143x1220, 84x914 등
- **납기일 범위**: 2025년 5-6월

## 스케줄링 알고리즘

### DispatchPriorityStrategy
```python
class DispatchPriorityStrategy:
    def schedule(self, DAG, node_dict):
        # 우선순위 기반 디스패칭 알고리즘
        # 1. 준비된 작업 큐 관리
        # 2. 기계 가용성 확인
        # 3. 우선순위에 따른 작업 할당
        # 4. 완료 시간 계산
        return scheduling_result
```

### 주요 고려사항
- **기계 제약사항**: 호기별 가능 작업 타입
- **공정 순서**: DAG를 통한 선후 관계 관리
- **납기일 우선순위**: 지연 최소화
- **기계 교체 시간**: 제품 변경 시 소요시간

## 결과 파일 구조

### 0829 스케줄링결과.xlsx
#### 주문_생산_요약본 시트
- P/O NO, GITEM, 납기일, 종료날짜, 지각일수
- 각 주문별 최종 완료 시간 및 지연 정보

#### 호기_정보 시트  
- 기계별 작업 할당 정보
- 작업 시작/종료 시간, 작업시간
- 기계코드, 기계이름

### level4_gantt.png
- 기계별 시간축 간트 차트
- 작업 순서 및 기간 시각화
- 색상별 제품 구분

## 웹 시스템 연동

### 백엔드 연동 방식
```python
# scheduling_service.py에서 subprocess로 실행
process = subprocess.Popen(
    [sys.executable, "main.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

### 진행상황 모니터링
웹 시스템에서 5단계로 나누어 진행상황 추적:
1. **데이터 준비**: 주문 데이터 로딩
2. **전처리**: 월별 분리, 병합, 공정 순서 생성
3. **DAG 생성**: 작업 의존성 그래프 생성  
4. **스케줄링 실행**: 실제 스케줄링 알고리즘 실행
5. **결과 저장**: Excel 파일 생성 및 DB 저장

## 해결된 문제들

### 1. Unicode 인코딩 오류
```python
# 수정 전: 이모지 사용으로 cp949 에러
print("📂 데이터 로딩 및 전처리 중...")

# 수정 후: 이모지 제거
print("데이터 로딩 및 전처리 중...")
```

### 2. 파일 경로 문제
```python
# config.py에서 절대 경로 설정
python_engine_path = os.path.abspath(settings.PYTHON_ENGINE_PATH)
os.chdir(python_engine_path)  # 작업 디렉토리 변경
```

### 3. 실행 시간 모니터링
```python
# 타임아웃 설정으로 무한 대기 방지
timeout = 300  # 5분
if elapsed > timeout:
    process.kill()
    raise Exception("스케줄링 실행 시간 초과")
```

## 실행 방법

### 직접 실행
```bash
cd python_engine
python main.py
```

### 웹 시스템을 통한 실행
1. 웹 인터페이스에서 "스케줄링 실행" 클릭
2. 백엔드가 subprocess로 `python main.py` 실행
3. 실시간 진행상황 모니터링
4. 완료 후 결과 파일 자동 파싱

## 성능 특징

- **처리 용량**: 174개 주문 기준 약 2-3분 소요
- **메모리 사용량**: 약 100-200MB
- **결과 파일 크기**: Excel 약 500KB, PNG 약 200KB
- **정확도**: 납기일 준수율 및 makespan 최적화

Python 엔진은 실제 생산 환경의 복잡한 제약사항을 고려한 고도화된 스케줄링 알고리즘을 구현하고 있습니다.