# PowerShell API 테스트 스크립트

Write-Host "🚀 Python API 서버 테스트 시작" -ForegroundColor Green
Write-Host "=" * 50

# 1. 헬스 체크
Write-Host "🔍 1. 헬스 체크 테스트..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET
    Write-Host "✅ 헬스 체크 성공: $($healthResponse.StatusCode)" -ForegroundColor Green
    $healthData = $healthResponse.Content | ConvertFrom-Json
    Write-Host "📊 응답: $($healthData | ConvertTo-Json -Depth 3)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ 헬스 체크 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. 1단계 테스트
Write-Host "`n🔍 2. 1단계 데이터 로딩 테스트..." -ForegroundColor Yellow

# 샘플 데이터 로드
try {
    $sampleData = Get-Content "sample_data.json" -Raw | ConvertFrom-Json
    Write-Host "✅ 샘플 데이터 로드 완료: $($sampleData.PSObject.Properties.Count)개 키" -ForegroundColor Green
} catch {
    Write-Host "❌ 샘플 데이터 로드 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 1단계 API 호출
try {
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    $body = $sampleData | ConvertTo-Json -Depth 10
    $stage1Response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/stage1/load-data" -Method POST -Headers $headers -Body $body
    
    if ($stage1Response.StatusCode -eq 200) {
        $stage1Data = $stage1Response.Content | ConvertFrom-Json
        Write-Host "✅ 1단계 성공: $($stage1Data.message)" -ForegroundColor Green
        Write-Host "📊 세션 ID: $($stage1Data.session_id)" -ForegroundColor Cyan
        Write-Host "📊 데이터 요약: $($stage1Data.data_summary | ConvertTo-Json -Depth 3)" -ForegroundColor Cyan
        $sessionId = $stage1Data.session_id
    } else {
        Write-Host "❌ 1단계 실패: $($stage1Response.StatusCode)" -ForegroundColor Red
        Write-Host "📊 오류 내용: $($stage1Response.Content)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ 1단계 API 호출 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. 세션 상태 확인
Write-Host "`n🔍 3. 세션 상태 확인 (세션: $sessionId)..." -ForegroundColor Yellow
try {
    $statusResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/session/$sessionId/status" -Method GET
    
    if ($statusResponse.StatusCode -eq 200) {
        $statusData = $statusResponse.Content | ConvertFrom-Json
        Write-Host "✅ 세션 상태 조회 성공" -ForegroundColor Green
        Write-Host "📊 완료된 단계: $($statusData.completed_stages)" -ForegroundColor Cyan
        Write-Host "📊 전체 단계: $($statusData.total_stages)" -ForegroundColor Cyan
    } else {
        Write-Host "❌ 세션 상태 조회 실패: $($statusResponse.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ 세션 상태 조회 실패: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. 2단계 테스트
Write-Host "`n🔍 4. 2단계 전처리 테스트 (세션: $sessionId)..." -ForegroundColor Yellow
try {
    $stage2Body = @{
        session_id = $sessionId
    } | ConvertTo-Json
    
    $stage2Response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/stage2/preprocessing" -Method POST -Headers $headers -Body $stage2Body
    
    if ($stage2Response.StatusCode -eq 200) {
        $stage2Data = $stage2Response.Content | ConvertFrom-Json
        Write-Host "✅ 2단계 성공: $($stage2Data.message)" -ForegroundColor Green
        Write-Host "📊 처리된 작업: $($stage2Data.processed_jobs)개" -ForegroundColor Cyan
        Write-Host "`n🎉 모든 테스트 성공! Python API가 정상적으로 작동합니다." -ForegroundColor Green
    } else {
        Write-Host "❌ 2단계 실패: $($stage2Response.StatusCode)" -ForegroundColor Red
        Write-Host "📊 오류 내용: $($stage2Response.Content)" -ForegroundColor Red
        Write-Host "`n⚠️ Python 서버 터미널에서 상세한 오류 메시지를 확인하세요." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ 2단계 API 호출 실패: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n⚠️ Python 서버 터미널에서 상세한 오류 메시지를 확인하세요." -ForegroundColor Yellow
}

Write-Host "`n" + "=" * 50
Write-Host "🏁 테스트 완료" -ForegroundColor Green
