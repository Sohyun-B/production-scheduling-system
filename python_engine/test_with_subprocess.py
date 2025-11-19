"""
프로세스 분리 테스트
main.py를 여러 번 subprocess로 실행하여
각 실행마다 새로운 Python 프로세스에서 hash seed가 달라지는 상황을 재현
"""

import subprocess
import pandas as pd
import hashlib
import os

NUM_RUNS = 5

print("=" * 80)
print(f"main.py를 {NUM_RUNS}번 별도 프로세스로 실행하여 비결정성 검증")
print("=" * 80)
print()

results = []

for i in range(NUM_RUNS):
    print(f"[Run {i+1}/{NUM_RUNS}] main.py 실행 중...", end='', flush=True)

    # main.py를 새로운 프로세스로 실행
    result = subprocess.run(
        ['python', 'main.py'],
        cwd=os.getcwd(),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f" [ERROR]")
        print(f"Error output: {result.stderr[:200]}")
        continue

    # 결과 파일 복사
    result_file = f'result_subprocess_{i+1}.xlsx'
    subprocess.run(['cp', 'data/output/result.xlsx', result_file])

    # DataFrame 로드
    df = pd.read_excel(result_file)
    results.append(df)

    print(f" 완료 (shape: {df.shape})")

print()
print("=" * 80)
print("결과 비교")
print("=" * 80)

# 해시 계산
hashes = []
for i, df in enumerate(results):
    h = hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()
    hashes.append(h)
    print(f"Run {i+1} hash: {h[:16]}")

print()

# 일관성 체크
unique_hashes = len(set(hashes))
if unique_hashes == 1:
    print(f"[OK] 모든 {NUM_RUNS}회 실행 결과가 동일합니다!")
else:
    print(f"[DIFF] {unique_hashes}개의 서로 다른 결과가 발견되었습니다!")
    print()

    # 어떤 run들이 같은지 그룹화
    from collections import defaultdict
    hash_groups = defaultdict(list)
    for i, h in enumerate(hashes):
        hash_groups[h].append(i+1)

    print("동일한 결과 그룹:")
    for idx, (h, runs) in enumerate(hash_groups.items(), 1):
        print(f"  그룹 {idx} (hash: {h[:16]}): Run {runs}")

    print()

    # 첫 번째와 두 번째 비교
    if len(results) >= 2:
        df1 = results[0].sort_values('id').reset_index(drop=True)
        df2 = results[1].sort_values('id').reset_index(drop=True)

        # 기계 할당 차이
        machine_diff = df1['machine'] != df2['machine']
        diff_count = machine_diff.sum()

        print(f"Run 1 vs Run 2 차이 분석:")
        print(f"  - 기계 할당이 다른 작업: {diff_count} / {len(df1)}")

        if diff_count > 0:
            print(f"  - 다른 작업 ID (첫 5개):")
            diff_ids = df1[machine_diff]['id'].head(5).tolist()
            for did in diff_ids:
                m1 = df1[df1['id'] == did]['machine'].iloc[0]
                m2 = df2[df2['id'] == did]['machine'].iloc[0]
                print(f"      {did}: {m1} -> {m2}")

print()
print("=" * 80)
print("결론:")
if unique_hashes == 1:
    print("  -> 프로세스를 분리해도 결과가 동일하므로 완전히 결정적입니다.")
else:
    print("  -> 프로세스마다 결과가 다르므로 비결정성이 존재합니다.")
    print("  -> 원인: Python hash randomization으로 인한 딕셔너리 순회 순서 변화")
print("=" * 80)
