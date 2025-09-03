# Production Scheduling System

Python 기반 생산계획 스케줄링 시스템

## 📁 프로젝트 구조

```
python_engine/
├── data/                           # 📊 데이터 디렉토리
│   ├── input/                      # 입력 파일들
│   │   ├── preprocessed_order.xlsx                    # 전처리된 주문 데이터 (174개)
│   │   ├── 품목별 분리 라인스피드 및 공정 순서.xlsx     # 기계/공정 정보
│   │   ├── 공정 재분류 내역 및 교체 시간 정리.xlsx     # 공정 분류 및 교체시간
│   │   └── 불가능한 공정 입력값.xlsx                  # 기계 제약조건
│   └── output/                     # 출력 결과들
│       ├── 0829 스케줄링결과.xlsx                     # 최종 스케줄링 결과
│       ├── result.xlsx                               # 원본 알고리즘 결과
│       ├── level4_gantt.png                          # 간트 차트 시각화
│       └── stage*.json                               # 각 단계별 진행상황
├── src/                            # 💻 소스 코드 디렉토리
│   ├── preprocessing/              # 데이터 전처리 모듈
│   ├── scheduler/                  # 스케줄링 알고리즘 (DispatchPriorityStrategy)
│   ├── dag_management/             # 작업 의존성 그래프(DAG) 관리
│   ├── yield_management/           # 수율 예측 및 관리
│   └── results/                    # 결과 후처리 및 Export
├── main.py                         # 🚀 메인 실행 파일
├── config.py                       # ⚙️ 설정 파일 (파일경로, 상수)
├── requirements.txt                # 📦 의존성 파일
└── README.md                       # 📖 프로젝트 문서
```

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
cd python_engine
pip install -r requirements.txt
```

### 2. 실행 방법
```bash
python main.py
```

### 3. 결과 확인
- **Excel 결과**: `data/output/0829 스케줄링결과.xlsx`
- **간트 차트**: `data/output/level4_gantt.png`
- **진행상황**: `data/output/stage*.json` 파일들

## 📊 입출력 데이터

### 입력 파일 (`data/input/`)
- **preprocessed_order.xlsx**: 174개 실제 주문 데이터 (P/O NO, GITEM, 치수, 납기일)
- **품목별 분리 라인스피드 및 공정 순서.xlsx**: 기계별 처리속도 및 공정순서
- **공정 재분류 내역 및 교체 시간 정리.xlsx**: 공정 분류 및 셋업 시간
- **불가능한 공정 입력값.xlsx**: 기계 제약조건 및 강제할당 정보

### 출력 파일 (`data/output/`)
- **0829 스케줄링결과.xlsx**: 주문별 완료시간, 지연정보, 기계별 작업할당
- **result.xlsx**: 알고리즘 원본 결과 (노드별 시작/종료 시간)
- **level4_gantt.png**: 기계별 시간축 간트 차트
- **stage*.json**: 각 처리단계별 실시간 진행상황 데이터

## 🔧 주요 기능

### ✅ 핵심 알고리즘
- **Level 4 DispatchPriorityStrategy**: 우선순위 기반 디스패칭 스케줄링
- **FJSP (Flexible Job Shop Problem)** 해결
- **Multi-constraint 최적화**: 기계제약, 납기일, 셋업시간, 수율 고려
- **Real-time Progress Tracking**: 6단계 세분화된 진행상황 모니터링

### 📈 처리 과정 (6단계)
1. **데이터 로딩** (10-25%): Excel 파일에서 주문, 기계, 공정 정보 로딩
2. **전처리** (25-35%): 주문 데이터 월별 분리 및 공정 순서 생성  
3. **수율 예측** (35-40%): 과거 데이터 기반 공정별 수율 계산
4. **DAG 생성** (40-60%): 작업 의존성 그래프 및 제약조건 적용
5. **스케줄링 실행** (60-85%): DispatchPriorityStrategy 알고리즘 실행
6. **결과 후처리** (85-100%): Excel/JSON 결과 생성 및 간트차트 시각화

### 🎯 성능 지표
- **처리 용량**: 174개 주문 → 약 2-3분 소요
- **메모리 사용량**: 약 100-200MB
- **최적화 목표**: Makespan 최소화 + 납기일 준수율 극대화

## 🛠 기술 스택

- **Core**: Python 3.8+, pandas, numpy
- **Algorithm**: Custom DispatchPriorityStrategy (Priority-based Dispatching)
- **Visualization**: matplotlib (Gantt Chart)
- **Data I/O**: openpyxl (Excel), JSON
- **Architecture**: Modular design with clear separation of concerns

## 📋 API 연동 가이드

FastAPI/React 연동을 위한 세부 가이드는 `PYTHON_DATA_EXTRACTION_GUIDE.md` 참조

### 주요 연동 포인트
- **실행**: `subprocess`로 `python main.py` 호출
- **진행상황**: `data/output/stage*.json` 파일 실시간 모니터링  
- **결과 파싱**: `data/output/0829 스케줄링결과.xlsx` 파싱하여 DB 저장