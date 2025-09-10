# 간단한 PowerShell API 테스트

Write-Host "🚀 간단한 API 테스트 시작" -ForegroundColor Green

# 1. 헬스 체크
Write-Host "`n🔍 헬스 체크..." -ForegroundColor Yellow
curl.exe -X GET "http://localhost:8000/health"

# 2. 1단계 테스트 (샘플 데이터 사용)
Write-Host "`n🔍 1단계 데이터 로딩..." -ForegroundColor Yellow
$sampleData = Get-Content "sample_data.json" -Raw
curl.exe -X POST "http://localhost:8000/api/v1/stage1/load-data" -H "Content-Type: application/json" -d $sampleData

Write-Host "`n✅ 테스트 완료! Python 서버 터미널에서 로그를 확인하세요." -ForegroundColor Green
