const axios = require('axios');

async function testAPI() {
    try {
        console.log('🚀 API 테스트 시작...');
        
        // 1. 전체 스케줄링 API 테스트
        console.log('\n📋 1. 전체 스케줄링 API 테스트');
        const fullResponse = await axios.post('http://localhost:3000/api/scheduling/full', {
            sessionId: 'test-session-001',
            windowDays: 5
        });
        
        console.log('✅ 전체 스케줄링 응답:');
        console.log(JSON.stringify(fullResponse.data, null, 2));
        
        // 2. 단계별 스케줄링 API 테스트
        console.log('\n📋 2. 단계별 스케줄링 API 테스트');
        
        // 2-1. 데이터 검증
        console.log('\n🔍 2-1. 데이터 검증');
        const validationResponse = await axios.post('http://localhost:3000/api/scheduling/step/validation', {
            sessionId: 'test-session-002',
            windowDays: 5,
            baseDate: '2025-01-01',
            yieldPeriod: 6
        });
        
        console.log('✅ 데이터 검증 응답:');
        console.log(JSON.stringify(validationResponse.data, null, 2));
        
        // 2-2. 전처리
        console.log('\n🔧 2-2. 전처리');
        const preprocessingResponse = await axios.post('http://localhost:3000/api/scheduling/step/preprocessing', {
            sessionId: 'test-session-002',
            windowDays: 5
        });
        
        console.log('✅ 전처리 응답:');
        console.log(JSON.stringify(preprocessingResponse.data, null, 2));
        
        // 2-3. 수율 예측
        console.log('\n📊 2-3. 수율 예측');
        const yieldResponse = await axios.post('http://localhost:3000/api/scheduling/step/yield-prediction', {
            sessionId: 'test-session-002'
        });
        
        console.log('✅ 수율 예측 응답:');
        console.log(JSON.stringify(yieldResponse.data, null, 2));
        
        // 2-4. DAG 생성
        console.log('\n🕸️ 2-4. DAG 생성');
        const dagResponse = await axios.post('http://localhost:3000/api/scheduling/step/dag-creation', {
            sessionId: 'test-session-002'
        });
        
        console.log('✅ DAG 생성 응답:');
        console.log(JSON.stringify(dagResponse.data, null, 2));
        
        // 2-5. 스케줄링
        console.log('\n⚙️ 2-5. 스케줄링');
        const schedulingResponse = await axios.post('http://localhost:3000/api/scheduling/step/scheduling', {
            sessionId: 'test-session-002',
            windowDays: 5
        });
        
        console.log('✅ 스케줄링 응답:');
        console.log(JSON.stringify(schedulingResponse.data, null, 2));
        
        console.log('\n🎉 모든 API 테스트 완료!');
        
    } catch (error) {
        console.error('❌ API 테스트 실패:', error.response?.data || error.message);
    }
}

testAPI();
