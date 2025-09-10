"""
API 테스트용 샘플 데이터 생성기
main.py에서 사용되는 실제 데이터 구조를 기반으로 샘플 데이터 생성
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

class SampleDataGenerator:
    """API 테스트용 샘플 데이터 생성기"""
    
    def __init__(self):
        self.base_date = datetime(2025, 5, 15)
    
    def generate_stage1_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """1단계: 모든 마스터 데이터 생성"""
        
        # 1. 주문 데이터 (order_data)
        order_data = self._generate_order_data()
        
        # 2. 라인스피드 데이터 (linespeed)
        linespeed = self._generate_linespeed_data()
        
        # 3. 공정 순서 데이터 (operation_sequence)
        operation_sequence = self._generate_operation_sequence_data()
        
        # 4. 기계 마스터 정보 (machine_master_info)
        machine_master_info = self._generate_machine_master_info()
        
        # 5. 수율 데이터 (yield_data)
        yield_data = self._generate_yield_data()
        
        # 6. GITEM별 공정 데이터 (gitem_operation)
        gitem_operation = self._generate_gitem_operation_data()
        
        # 7. 공정 분류 데이터 (operation_types)
        operation_types = self._generate_operation_types_data()
        
        # 8. 공정 지연 데이터 (operation_delay)
        operation_delay = self._generate_operation_delay_data()
        
        # 9. 폭 변경 데이터 (width_change)
        width_change = self._generate_width_change_data()
        
        # 10. 기계 휴식 데이터 (machine_rest)
        machine_rest = self._generate_machine_rest_data()
        
        # 11. 기계 할당 데이터 (machine_allocate)
        machine_allocate = self._generate_machine_allocate_data()
        
        # 12. 기계 제한 데이터 (machine_limit)
        machine_limit = self._generate_machine_limit_data()
        
        return {
            "linespeed": linespeed,
            "operation_sequence": operation_sequence,
            "machine_master_info": machine_master_info,
            "yield_data": yield_data,
            "gitem_operation": gitem_operation,
            "operation_types": operation_types,
            "operation_delay": operation_delay,
            "width_change": width_change,
            "machine_rest": machine_rest,
            "machine_allocate": machine_allocate,
            "machine_limit": machine_limit,
            "order_data": order_data
        }
    
    def _generate_order_data(self) -> List[Dict[str, Any]]:
        """주문 데이터 생성"""
        orders = []
        gitems = [31704, 25026, 31705, 25027, 31706]
        gitem_names = ["PPF-NS-TGA(WHITE)", "PPF-NS-TGA(BLACK)", "PPF-NS-TGA(RED)", "PPF-NS-TGA(BLUE)", "PPF-NS-TGA(GREEN)"]
        widths = [1524, 1372, 1220, 1067, 914]
        lengths = [15, 20, 25, 30, 35]
        
        for i in range(50):  # 50개 주문 생성
            gitem_idx = i % len(gitems)
            order = {
                "P/O NO": f"SW1250407{101 + i:03d}",
                "GITEM": gitems[gitem_idx],
                "GITEM명": gitem_names[gitem_idx],
                "너비": widths[gitem_idx % len(widths)],
                "길이": lengths[gitem_idx % len(lengths)],
                "의뢰량": random.randint(10, 100),
                "원단길이": random.randint(200, 500),
                "납기일": (self.base_date + timedelta(days=random.randint(1, 30))).isoformat()
            }
            orders.append(order)
        
        return orders
    
    def _generate_linespeed_data(self) -> List[Dict[str, Any]]:
        """라인스피드 데이터 생성"""
        linespeed = []
        gitems = [31704, 25026, 31705, 25027, 31706]
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        machines = ["C2010", "C2250", "C2260", "C2270", "O2310", "O2340"]
        
        for gitem in gitems:
            for operation in operations:
                row = {"GITEM": gitem, "공정명": operation}
                for machine in machines:
                    # 일부 기계는 해당 공정을 처리할 수 없음
                    if random.random() > 0.3:
                        row[machine] = round(random.uniform(20, 50), 1)
                    else:
                        row[machine] = None
                linespeed.append(row)
        
        return linespeed
    
    def _generate_operation_sequence_data(self) -> List[Dict[str, Any]]:
        """공정 순서 데이터 생성"""
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        sequences = []
        
        for i, operation in enumerate(operations):
            sequences.append({
                "공정순서": i + 1,
                "공정명": operation,
                "공정분류": f"분류_{i + 1}",
                "배합코드": f"BATCH_{i + 1:03d}"
            })
        
        return sequences
    
    def _generate_machine_master_info(self) -> List[Dict[str, Any]]:
        """기계 마스터 정보 생성"""
        machines = [
            {"기계인덱스": 0, "기계코드": "C2010", "기계이름": "1호기"},
            {"기계인덱스": 1, "기계코드": "C2250", "기계이름": "25호기"},
            {"기계인덱스": 2, "기계코드": "C2260", "기계이름": "26호기"},
            {"기계인덱스": 3, "기계코드": "C2270", "기계이름": "27호기"},
            {"기계인덱스": 4, "기계코드": "O2310", "기계이름": "31호기"},
            {"기계인덱스": 5, "기계코드": "O2340", "기계이름": "34호기"}
        ]
        return machines
    
    def _generate_yield_data(self) -> List[Dict[str, Any]]:
        """수율 데이터 생성"""
        yield_data = []
        gitems = [31704, 25026, 31705, 25027, 31706]
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        
        for gitem in gitems:
            for operation in operations:
                yield_data.append({
                    "GITEM": gitem,
                    "공정명": operation,
                    "수율": round(random.uniform(0.85, 0.98), 3)
                })
        
        return yield_data
    
    def _generate_gitem_operation_data(self) -> List[Dict[str, Any]]:
        """GITEM별 공정 데이터 생성"""
        gitem_operation = []
        gitems = [31704, 25026, 31705, 25027, 31706]
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        
        for gitem in gitems:
            for operation in operations:
                gitem_operation.append({
                    "GITEM": gitem,
                    "공정명": operation,
                    "공정분류": f"분류_{operations.index(operation) + 1}",
                    "배합코드": f"BATCH_{operations.index(operation) + 1:03d}"
                })
        
        return gitem_operation
    
    def _generate_operation_types_data(self) -> List[Dict[str, Any]]:
        """공정 분류 데이터 생성"""
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        operation_types = []
        
        for operation in operations:
            operation_types.append({
                "공정명": operation,
                "공정분류": f"분류_{operations.index(operation) + 1}",
                "설명": f"{operation} 공정 분류"
            })
        
        return operation_types
    
    def _generate_operation_delay_data(self) -> List[Dict[str, Any]]:
        """공정 지연 데이터 생성"""
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        operation_delay = []
        
        for i, operation in enumerate(operations):
            for j, next_operation in enumerate(operations):
                if i != j:
                    operation_delay.append({
                        "선행공정분류": f"분류_{i + 1}",
                        "후행공정분류": f"분류_{j + 1}",
                        "타입교체시간": random.randint(10, 60),
                        "long_to_short": random.randint(5, 30),
                        "short_to_long": random.randint(15, 45)
                    })
        
        return operation_delay
    
    def _generate_width_change_data(self) -> List[Dict[str, Any]]:
        """폭 변경 데이터 생성"""
        widths = [1524, 1372, 1220, 1067, 914]
        width_change = []
        
        for i, from_width in enumerate(widths):
            for j, to_width in enumerate(widths):
                if i != j:
                    width_change.append({
                        "이전폭": from_width,
                        "이후폭": to_width,
                        "변경시간": random.randint(5, 20)
                    })
        
        return width_change
    
    def _generate_machine_rest_data(self) -> List[Dict[str, Any]]:
        """기계 휴식 데이터 생성"""
        machine_rest = []
        machines = [0, 1, 2, 3, 4, 5]
        
        for machine in machines:
            # 일부 기계만 휴식 시간 설정
            if random.random() > 0.5:
                start_time = self.base_date + timedelta(days=random.randint(1, 10), hours=random.randint(8, 18))
                end_time = start_time + timedelta(hours=random.randint(1, 8))
                
                machine_rest.append({
                    "기계인덱스": machine,
                    "시작시간": start_time.isoformat(),
                    "종료시간": end_time.isoformat(),
                    "사유": "정기점검"
                })
        
        return machine_rest
    
    def _generate_machine_allocate_data(self) -> List[Dict[str, Any]]:
        """기계 할당 데이터 생성"""
        machine_allocate = []
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        machines = [0, 1, 2, 3, 4, 5]
        
        for operation in operations:
            # 각 공정에 특정 기계 강제 할당
            if random.random() > 0.7:
                machine_allocate.append({
                    "기계인덱스": random.choice(machines),
                    "공정명": operation,
                    "할당유형": "강제할당"
                })
        
        return machine_allocate
    
    def _generate_machine_limit_data(self) -> List[Dict[str, Any]]:
        """기계 제한 데이터 생성"""
        machine_limit = []
        operations = ["염료점착", "세척", "건조", "검사", "포장"]
        machines = [0, 1, 2, 3, 4, 5]
        
        for machine in machines:
            # 일부 기계는 특정 공정 제한
            if random.random() > 0.8:
                restricted_operations = random.sample(operations, random.randint(1, 3))
                for operation in restricted_operations:
                    start_time = self.base_date + timedelta(days=random.randint(1, 15))
                    end_time = start_time + timedelta(days=random.randint(1, 5))
                    
                    machine_limit.append({
                        "기계인덱스": machine,
                        "공정명": operation,
                        "시작시간": start_time.isoformat(),
                        "종료시간": end_time.isoformat(),
                        "제한사유": "공정불가"
                    })
        
        return machine_limit
    
    def save_sample_data(self, filename: str = "sample_data.json"):
        """샘플 데이터를 JSON 파일로 저장"""
        data = self.generate_stage1_data()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"샘플 데이터가 {filename}에 저장되었습니다.")
        return data

def main():
    """샘플 데이터 생성 및 저장"""
    generator = SampleDataGenerator()
    data = generator.save_sample_data("sample_data.json")
    
    print("\n=== 생성된 샘플 데이터 요약 ===")
    for key, value in data.items():
        print(f"{key}: {len(value)}개 레코드")
    
    print("\n=== 1단계 API 요청 예시 ===")
    print("POST /api/v1/stage1/load-data")
    print("Content-Type: application/json")
    print()
    print(json.dumps({
        "linespeed": data["linespeed"][:2],  # 처음 2개만 표시
        "operation_sequence": data["operation_sequence"],
        "machine_master_info": data["machine_master_info"],
        "yield_data": data["yield_data"][:2],
        "gitem_operation": data["gitem_operation"][:2],
        "operation_types": data["operation_types"],
        "operation_delay": data["operation_delay"][:2],
        "width_change": data["width_change"][:2],
        "machine_rest": data["machine_rest"],
        "machine_allocate": data["machine_allocate"],
        "machine_limit": data["machine_limit"],
        "order_data": data["order_data"][:2]
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
