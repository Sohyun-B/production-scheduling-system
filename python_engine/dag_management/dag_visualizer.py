class DAGVisualizer:
    """DAG 구조 시각화 전문 클래스"""
    
    @staticmethod
    def visualize(manager):
        """DAGGraphManager 인스턴스를 통해 시각화 수행
        
        :param manager: DAGGraphManager 인스턴스
        """
        import networkx as nx
        import matplotlib.pyplot as plt

        G = nx.DiGraph()
        
        # 노드 및 엣지 추가
        for node in manager.nodes.values():
            G.add_node(node.id, layer=node.depth)
            for child in node.children:
                G.add_edge(node.id, child.id)

        # 레이아웃 설정
        pos = nx.multipartite_layout(G, subset_key="layer")
        pos = nx.multipartite_layout(G, subset_key="layer",
                scale=4.0,    # 기본값 1.0 → 레이어 간 거리 증가
            )
        pos = {node.id: (node.depth, idx) for idx, node in enumerate(sorted(manager.nodes.values(), key=lambda x: x.id))}


        
        # 시각화 옵션
        plt.figure(figsize=(18, 12))
        nx.draw(G, pos,
                with_labels=True,
                node_size=2500,
                node_color='#11dbff',
                edge_color='#607D8B',
                font_size=10,
                font_weight='bold',
                arrowsize=25)
        plt.title("DAG Structure Visualization", pad=20)
        plt.show()