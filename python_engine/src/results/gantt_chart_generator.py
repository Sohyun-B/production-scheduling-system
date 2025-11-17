"""
간트차트 생성 전용 모듈 (results 전용)
scheduler의 DrawChart를 results로 이동
"""

import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


class DrawChart:
    """간트차트 그리기 클래스 (원래 scheduler.chart에서 이동)"""
    
    def __init__(self, Machines, gap_analyzer=None):
        self.Machines = Machines
        self.gap_analyzer = gap_analyzer
        self.fig = None
        self.ax = None

    def plot(self, figsize=(15, 8), fontsize=6, major_interval=48, minor_interval=24, dpi=300, show_gaps=True, save_path='data/output/level4_gantt.png'):
        self.fig, self.ax = plt.subplots(figsize=figsize)

        # 모든 작업의 depth 추출 및 정렬
        # ★ 딕셔너리 순회로 변경
        unique_depths = sorted({job[0] for machine in self.Machines.values() for job in machine.assigned_task})
        cmap = plt.get_cmap('tab20')
        # depth별 색상 동적 할당 (depth 종류 > 20이면 순환)
        depth_to_color = {depth: cmap(i % cmap.N) for i, depth in enumerate(unique_depths)}

        # 작업 바 그리기
        # ★ 딕셔너리 순회로 변경
        for i, (machine_code, machine) in enumerate(self.Machines.items()):
            for (start, end), job_info in zip(zip(machine.O_start, machine.O_end), machine.assigned_task):
                depth = job_info[0]
                color = depth_to_color[depth]
                self.ax.barh(i, width=end-start, left=start, height=0.7, color=color,
                             edgecolor='black', linewidth=0.5)
        
        # 간격 분석 및 표시
        if show_gaps and self.gap_analyzer:
            self._draw_gaps()
        
        # 범례 생성
        legend_elements = [Patch(facecolor=depth_to_color[d], edgecolor='black', label=f'Depth: {d}') for d in unique_depths]
        
        # 간격 범례 추가
        if show_gaps and self.gap_analyzer:
            legend_elements.extend([
                Patch(facecolor='red', alpha=0.6, label='Setup Time'),
                Patch(facecolor='lightgray', alpha=0.6, label='Idle Time')
            ])
        
        self.ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.2, 1), title="Legend")

        self._style_chart(major_interval, minor_interval)
        
        # 저장 경로의 디렉토리가 없으면 생성
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        # plt.show() 제거 - 비대화형 백엔드에서는 경고 발생
        
        return self.fig
    
    def _draw_gaps(self):
        """
        간격을 셋업시간/대기시간으로 구분하여 표시
        ⭐ 리팩토링: machine_index → machine_code
        """
        gap_df = self.gap_analyzer.analyze_all_machine_gaps()

        for _, gap in gap_df.iterrows():
            machine_code = gap['machine_code']  # ★ machine_index → machine_code
            gap_start = gap['gap_start']
            gap_end = gap['gap_end']
            setup_time = gap['setup_time']
            idle_time = gap['idle_time']

            # 셋업시간 표시 (빨간색)
            if setup_time > 0:
                self.ax.barh(machine_code, setup_time, left=gap_start, height=0.3,  # ★ machine_code 사용
                           color='red', alpha=0.6, edgecolor='darkred')

            # 대기시간 표시 (회색)
            if idle_time > 0:
                idle_start = gap_start + setup_time
                self.ax.barh(machine_code, idle_time, left=idle_start, height=0.3,  # ★ machine_code 사용
                           color='lightgray', alpha=0.6, edgecolor='gray')

    def _style_chart(self, major_interval, minor_interval):
        """차트 스타일 설정"""
        # Y축: 기계 번호
        machine_labels = [f'Machine {i}' for i in range(len(self.Machines))]
        self.ax.set_yticks(range(len(self.Machines)))
        self.ax.set_yticklabels(machine_labels)
        
        # X축: 시간 간격 설정
        self.ax.set_xlabel('Time (slots)')
        self.ax.set_ylabel('Machines')
        self.ax.set_title('Production Schedule Gantt Chart')
        
        # 격자 설정
        self.ax.grid(True, which='major', alpha=0.3)
        self.ax.grid(True, which='minor', alpha=0.1)
        
        # 시간 간격 표시
        if major_interval:
            self.ax.xaxis.set_major_locator(plt.MultipleLocator(major_interval))
        if minor_interval:
            self.ax.xaxis.set_minor_locator(plt.MultipleLocator(minor_interval))


class GanttChartGenerator:
    """간트차트 생성 및 저장 관리"""
    
    def generate(self, machines, gap_analyzer=None, save_path="data/output/level4_gantt.png"):
        """
        간트차트 생성 파이프라인 실행
        
        Args:
            machines: 스케줄러의 기계 목록 (scheduler.Machines)
            gap_analyzer: 간격 분석기 (선택적)
            save_path (str): 저장 경로
            
        Returns:
            str: 생성된 간트차트 파일 경로 (실패시 None)
        """
        try:
            print("[간트차트] 간트차트 생성 시작...")
            
            # matplotlib 백엔드를 먼저 설정 (import 전에)
            import matplotlib
            matplotlib.use('Agg')
            
            # 간격 분석기가 있으면 포함하여 차트 생성
            gantt = DrawChart(machines, gap_analyzer)
            
            # 직접 저장 경로 지정하여 차트 생성
            fig = gantt.plot(
                show_gaps=True if gap_analyzer else False,
                save_path=save_path,
                dpi=300
            )
            
            plt.close('all')  # 모든 figure 닫기
            
            # 파일 생성 확인
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                print(f"[간트차트] 생성 완료: {save_path} ({file_size} bytes)")
                if gap_analyzer:
                    print("[차트] [PIN] Red: Setup Time, Gray: Wait Time")
                return save_path
            else:
                print("[WARNING] 간트차트 파일이 생성되지 않았습니다")
                return None
                
        except Exception as chart_error:
            print(f"[ERROR] 간트차트 생성 중 오류: {chart_error}")
            return None