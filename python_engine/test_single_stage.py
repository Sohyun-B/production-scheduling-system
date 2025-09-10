"""
Python API 서버 단독 테스트 스크립트
각 단계별로 개별 테스트를 수행합니다.
"""

import requests
import json
import time

# API 기본 URL
BASE_URL = "http://localhost:8000"

def test_health():
    """헬스 체크 테스트"""
    print("🔍 1. 헬스 체크 테스트...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ 헬스 체크 성공: {response.status_code}")
        print(f"📊 응답: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        return False

def test_stage1():
    """1단계: 데이터 로딩 테스트"""
    print("\n🔍 2. 1단계 데이터 로딩 테스트...")
    
    # 샘플 데이터 로드
    try:
        with open('sample_data.json', 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        print(f"✅ 샘플 데이터 로드 완료: {len(sample_data)}개 키")
    except Exception as e:
        print(f"❌ 샘플 데이터 로드 실패: {e}")
        return None
    
    # 1단계 API 호출
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/stage1/load-data",
            json=sample_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 1단계 성공: {result['message']}")
            print(f"📊 세션 ID: {result['session_id']}")
            print(f"📊 데이터 요약: {result['data_summary']}")
            return result['session_id']
        else:
            print(f"❌ 1단계 실패: {response.status_code}")
            print(f"📊 오류 내용: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 1단계 API 호출 실패: {e}")
        return None

def test_stage2(session_id):
    """2단계: 전처리 테스트"""
    print(f"\n🔍 3. 2단계 전처리 테스트 (세션: {session_id})...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/stage2/preprocessing",
            json={"session_id": session_id},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 2단계 성공: {result['message']}")
            print(f"📊 처리된 작업: {result['processed_jobs']}개")
            return True
        else:
            print(f"❌ 2단계 실패: {response.status_code}")
            print(f"📊 오류 내용: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 2단계 API 호출 실패: {e}")
        return False

def test_session_status(session_id):
    """세션 상태 확인"""
    print(f"\n🔍 4. 세션 상태 확인 (세션: {session_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/session/{session_id}/status")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 세션 상태 조회 성공")
            print(f"📊 완료된 단계: {result['completed_stages']}")
            print(f"📊 전체 단계: {result['total_stages']}")
            return True
        else:
            print(f"❌ 세션 상태 조회 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 세션 상태 조회 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Python API 서버 단독 테스트 시작")
    print("=" * 50)
    
    # 1. 헬스 체크
    if not test_health():
        print("\n❌ 서버가 실행되지 않았습니다. 먼저 서버를 시작하세요.")
        return
    
    # 2. 1단계 테스트
    session_id = test_stage1()
    if not session_id:
        print("\n❌ 1단계 실패로 인해 테스트를 중단합니다.")
        return
    
    # 3. 세션 상태 확인
    test_session_status(session_id)
    
    # 4. 2단계 테스트
    if test_stage2(session_id):
        print("\n✅ 2단계 성공! 전처리가 정상적으로 작동합니다.")
    else:
        print("\n❌ 2단계 실패! 전처리에서 오류가 발생했습니다.")
        print("Python 서버 터미널에서 상세한 오류 메시지를 확인하세요.")
    
    print("\n" + "=" * 50)
    print("🏁 테스트 완료")

if __name__ == "__main__":
    main()
