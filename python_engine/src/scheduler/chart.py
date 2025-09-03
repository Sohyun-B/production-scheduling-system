import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

class DrawChart:
    def __init__(self, Machines):
        self.Machines = Machines
        self.fig = None
        self.ax = None

    def plot(self, figsize=(15, 8), fontsize=6, major_interval=48, minor_interval=24, dpi=300):
        self.fig, self.ax = plt.subplots(figsize=figsize)
        
        # 모든 작업의 depth 추출 및 정렬
        unique_depths = sorted({job[0] for machine in self.Machines for job in machine.assigned_task})
        cmap = plt.get_cmap('tab20')
        # depth별 색상 동적 할당 (depth 종류 > 20이면 순환)
        depth_to_color = {depth: cmap(i % cmap.N) for i, depth in enumerate(unique_depths)}
        
        for i, machine in enumerate(self.Machines):
            for (start, end), job_info in zip(zip(machine.O_start, machine.O_end), machine.assigned_task):
                depth = job_info[0]
                color = depth_to_color[depth]
                self.ax.barh(i, width=end-start, left=start, height=0.7, color=color,
                             edgecolor='black', linewidth=0.5)
        
        legend_elements = [Patch(facecolor=depth_to_color[d], edgecolor='black', label=f'Depth: {d}') for d in unique_depths]
        self.ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.2, 1), title="Depth")

        self._style_chart(major_interval, minor_interval)
        plt.savefig('media/AutoColored_Gantt.png', dpi=dpi, bbox_inches='tight')
        plt.show()
    
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
