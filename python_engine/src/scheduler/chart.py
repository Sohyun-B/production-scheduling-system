import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

class DrawChart:
    def __init__(self, Machines, gap_analyzer=None):
        self.Machines = Machines
        self.gap_analyzer = gap_analyzer
        self.fig = None
        self.ax = None

    def plot(self, figsize=(15, 8), fontsize=6, major_interval=48, minor_interval=24, dpi=300, show_gaps=True, save_path='media/AutoColored_Gantt.png'):
        self.fig, self.ax = plt.subplots(figsize=figsize)
        
        # 모든 작업의 depth 추출 및 정렬
        unique_depths = sorted({job[0] for machine in self.Machines for job in machine.assigned_task})
        cmap = plt.get_cmap('tab20')
        # depth별 색상 동적 할당 (depth 종류 > 20이면 순환)
        depth_to_color = {depth: cmap(i % cmap.N) for i, depth in enumerate(unique_depths)}
        
        # 작업 바 그리기
        for i, machine in enumerate(self.Machines):
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
        import os
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        # plt.show() 제거 - 비대화형 백엔드에서는 경고 발생
        
        return self.fig
    
    def _draw_gaps(self):
        """간격을 셋업시간/대기시간으로 구분하여 표시"""
        gap_df = self.gap_analyzer.analyze_all_machine_gaps()
        
        for _, gap in gap_df.iterrows():
            machine_idx = gap['machine_index']
            gap_start = gap['gap_start']
            gap_end = gap['gap_end']
            setup_time = gap['setup_time']
            idle_time = gap['idle_time']
            
            # 셋업시간 표시 (빨간색)
            if setup_time > 0:
                self.ax.barh(machine_idx, width=setup_time, left=gap_start, height=0.3, 
                           color='red', alpha=0.6, edgecolor='darkred', linewidth=0.5)
            
            # 대기시간 표시 (회색)
            if idle_time > 0:
                idle_start = gap_start + setup_time
                self.ax.barh(machine_idx, width=idle_time, left=idle_start, height=0.3,
                           color='lightgray', alpha=0.6, edgecolor='gray', linewidth=0.5)
    
    def _style_chart(self, major_interval, minor_interval):
        self.ax.set_yticks(np.arange(len(self.Machines)))
        self.ax.set_yticklabels([m.Machine_index for m in self.Machines])
        self.ax.set_title('Depth-Based Colored Gantt Chart', pad=20)
        self.ax.set_xlabel('Time (30 min)', labelpad=15)
        self.ax.set_ylabel('Machines', labelpad=15)

#         self.ax.set_xlim(0, 1300) # 길이를 정의
        self.ax.xaxis.set_major_locator(plt.MultipleLocator(major_interval))
        self.ax.xaxis.set_minor_locator(plt.MultipleLocator(minor_interval))
        self.ax.grid(which='major', axis='x', linestyle='--', linewidth=1.2, alpha=0.8)
        self.ax.grid(which='minor', axis='x', linestyle=':', linewidth=0.7, alpha=0.4)
        plt.tight_layout()
