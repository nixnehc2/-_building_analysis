import json
import math
import os
import pandas as pd
from typing import Dict, List, Tuple, Optional
from shapely.geometry import Polygon, Point
import numpy as np

import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString
import numpy as np
from typing import List, Tuple

import matplotlib.pyplot as plt
import matplotlib

# 方法1：设置中文字体（推荐）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 中文
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def visualize_polygon(vertices: List[Tuple[float, float]], 
                      filename: Optional[str] = None,
                      figsize: Tuple[float, float] = (10, 8),
                      dpi: int = 300) -> Polygon:
    """
    绘制多边形并返回Polygon对象
    
    参数:
        vertices: 多边形顶点列表，每个元素是(x, y)元组
        filename: 保存图片的文件名（可选），如"polygon.jpg"或"output.png"
        figsize: 图形尺寸，默认(10, 8)
        dpi: 图片分辨率，默认300
    
    返回:
        shapely.geometry.Polygon: 创建的多边形对象
    """
    if not vertices:
        raise ValueError("顶点列表不能为空")
    
    # 1. 创建shapely Polygon对象
    # 确保多边形闭合（首尾点相同）
    if vertices[0] != vertices[-1]:
        vertices = vertices + [vertices[0]]
    
    polygon = Polygon(vertices)
    
    if not polygon.is_valid:
        print("警告：创建的多边形可能无效")
    
    # 2. 设置绘图
    fig, ax = plt.subplots(figsize=figsize)
    
    # 3. 绘制多边形区域（填充）
    x, y = polygon.exterior.xy
    ax.fill(x, y, alpha=0.3, color='skyblue', edgecolor='none', label='多边形区域')
    
    # 4. 绘制多边形边界
    ax.plot(x, y, color='blue', linewidth=2, marker='', label='边界')
    
    # 5. 绘制顶点（添加标记点）
    # 提取非重复的顶点（去掉闭合点）
    unique_vertices = vertices[:-1] if vertices[0] == vertices[-1] else vertices
    vx = [v[0] for v in unique_vertices]
    vy = [v[1] for v in unique_vertices]
    
    # 绘制顶点
    ax.scatter(vx, vy, color='red', s=50, zorder=5, label=f'顶点 ({len(unique_vertices)}个)')
    
    # 7. 计算合适的坐标轴范围
    # 获取所有顶点的坐标
    all_x = [v[0] for v in vertices]
    all_y = [v[1] for v in vertices]
    
    # 计算范围并留出一些边距
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    
    x_margin = max((x_max - x_min) * 0.1, 0.1)  # 确保最小边距
    y_margin = max((y_max - y_min) * 0.1, 0.1)
    
    # 设置坐标轴范围
    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    
    # 8. 设置图形属性
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('X 坐标', fontsize=12)
    ax.set_ylabel('Y 坐标', fontsize=12)
    ax.set_title('多边形可视化', fontsize=14, fontweight='bold')
    
    # 9. 添加多边形信息文本
    info_text = f'顶点数: {len(unique_vertices)}\n面积: {polygon.area:.2f}\n周长: {polygon.length:.2f}'
    if polygon.is_valid:
        info_text += '\n状态: 有效'
    else:
        info_text += '\n状态: 可能无效'
    
    # 添加信息文本框
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    # 10. 添加图例
    ax.legend(loc='upper right')
    
    # 11. 保存图片（如果指定了文件名）
    if filename:
    # 确保文件名有正确的扩展名
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.pdf', '.svg')):
            filename += '.jpg'  # 默认使用jpg格式
        
        # 创建输出目录（如果不存在）
        import os
        output_dir = "data/repair"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 构建完整的保存路径
        full_path = os.path.join(output_dir, filename)
        
        # 保存图片
        try:
            plt.savefig(full_path, dpi=dpi, bbox_inches='tight', facecolor='white')
            print(f"图片已保存至: {full_path}")
        except Exception as e:
            print(f"保存图片失败: {e}")
    
    # 12. 显示图形
    plt.tight_layout()
    plt.show()
    
    return polygon

def init(polygon_points, length_rate_mm_per_px):
    """
    初始化多边形
    参数:
        polygon_points: 多边形顶点列表
        length_rate: 缩放比例字符串，如 "0.100 mm/pixel"
    返回:
        shapely Polygon对象
    """
    # 提取缩放比例数值
    points = []
    
    for point_str in polygon_points:
        # 去除括号和引号，分割坐标
        coords = point_str.strip('()"').split(',')
        x = float(coords[0].strip()) / length_rate_mm_per_px  # 像素单位
        y = float(coords[1].strip()) / length_rate_mm_per_px  # 像素单位
        points.append((x, y))
    
    polygon = Polygon(points)
    return polygon

def get_pro_polygon(polygon):
    polygon=list(polygon.exterior.coords)
    assert len(polygon)>=2
    A=[]
    if(polygon[0][0]!=polygon[1][0] and polygon[0][1]!=polygon[1][1]):  
        A.append(polygon[0])
        A.append((polygon[0][0],polygon[1][1]))
        A.append(polygon[1])
    else:
        A.append(polygon[0])
        A.append(polygon[1])
    for i in range(2,len(polygon)):
        if(A[-1][0]==polygon[i][0] or A[-1][1]==polygon[i][1]):
            A.append(polygon[i])
        else:
            if(A[-1][0]==A[-2][0]):
                A.append((A[-1][0],polygon[i][1]))
                A.append(polygon[i])
            else:
                A.append((polygon[i][0],A[-1][1]))
                A.append(polygon[i])
    if(A[-1][0]==A[0][0] or A[-1][1]==A[1][1]):
        return A
    else:
        if(A[-1][0]==A[-2][0]):
            A.append((A[-1][0],A[1][1]))
        else:
            A.append((A[1][0],A[-1][1]))
    return A

def simplify_polygon_by_angle(polygon: Polygon, theta_eps: float = 5.0) -> Polygon:
    """
    通过删除角度过小的顶点来简化多边形
    
    参数:
        polygon: 输入的多边形
        theta_eps: 角度阈值（度），小于此角度的顶点将被删除
        
    返回:
        简化后的多边形
    """
    if polygon.is_empty:
        return polygon
    
    # 获取多边形坐标（移除最后一个重复的闭合点）
    coords = list(polygon.exterior.coords)
    if len(coords) < 4:  # 至少需要3个非重复点才能形成多边形
        return polygon
    
    # 移除闭合点（最后一个点与第一个点相同）
    if coords[0] == coords[-1]:
        coords = coords[:-1]
    
    # 转换为numpy数组便于计算
    points = np.array(coords)
    n = len(points)
    
    if n < 3:
        return polygon
    
    # 将角度阈值转换为弧度
    theta_eps_rad = math.radians(theta_eps)
    
    # 标记要保留的点
    keep_mask = [True] * n
    
    # 创建一个循环索引列表，便于处理相邻关系
    indices = list(range(n))
    
    # 第一轮检查：标记需要删除的点
    for i in range(n):
        # 获取三个相邻点 A(prev), B(current), C(next)
        prev_idx = (i - 1) % n
        curr_idx = i
        next_idx = (i + 1) % n
        
        # 如果当前点已经被标记为删除，跳过
        if not keep_mask[curr_idx]:
            continue
        
        A = points[prev_idx]
        B = points[curr_idx]
        C = points[next_idx]
        
        # 计算向量BA和BC
        BA = A - B
        BC = C - B
        
        # 计算向量长度
        ba_length = np.linalg.norm(BA)
        bc_length = np.linalg.norm(BC)
        
        # 如果向量长度太小，可能是重复点，跳过
        if ba_length < 1e-10 or bc_length < 1e-10:
            continue
        
        # 计算夹角（使用点积公式）
        dot_product = np.dot(BA, BC)
        cos_angle = dot_product / (ba_length * bc_length)
        
        # 处理数值误差
        cos_angle = max(min(cos_angle, 1.0), -1.0)
        
        # 计算夹角（弧度）
        angle = math.acos(cos_angle)
        
        # 计算外角（多边形内角）
        interior_angle = math.pi - angle
        
        # 如果角度小于阈值，标记为删除
        if interior_angle < theta_eps_rad:
            keep_mask[curr_idx] = False
    
    # 收集保留的点
    kept_points = [tuple(points[i]) for i in range(n) if keep_mask[i]]
    
    # 确保至少有3个点
    if len(kept_points) < 3:
        # 如果删除太多点，返回原多边形
        return polygon
    
    # 确保多边形闭合
    if kept_points[0] != kept_points[-1]:
        kept_points.append(kept_points[0])
    
    # 创建新的多边形
    try:
        new_polygon = Polygon(kept_points)
        if new_polygon.is_valid and not new_polygon.is_empty:
            return new_polygon
        else:
            # 如果无效，尝试修复
            new_polygon = new_polygon.buffer(0)
            return new_polygon if not new_polygon.is_empty else polygon
    except Exception:
        return polygon


def process_json_data(json_data, filename: str, k: float) -> Dict:
    basename = os.path.basename(filename)
    # 分割文件名和扩展名
    filename1, ext = os.path.splitext(basename)
    boundary_polygon = json_data['floor1']['boundary']['边界'][0]
    length_rate = json_data['floor1']['meta']['lengthRate']
    length_rate_mm_per_px = float(length_rate.split()[0])
    polygon = init(boundary_polygon, length_rate_mm_per_px)
    # visualize_polygon(list(polygon.exterior.coords),filename1+'_result')
    polygon = polygon.simplify(tolerance=k)
    # visualize_polygon(list(polygon.exterior.coords),filename1+'_result')
    polygon=Polygon(get_pro_polygon(polygon))
    # visualize_polygon(list(polygon.exterior.coords),filename1+'_result')
    polygon=simplify_polygon_by_angle(polygon)
    visualize_polygon(list(polygon.exterior.coords),filename1+'_result')
    return polygon
    

def find_json_files(directory: str = "data/repair") -> List[str]:
    """
    查找指定目录下的所有JSON文件
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"已创建数据目录: {directory}/")
    
    json_files = []
    for file in os.listdir(directory):
        if file.endswith('.json'):
            json_files.append(file)
    
    # 排序文件名
    json_files.sort()
    return json_files


if __name__ == "__main__":
    data_dir = "data/repair"
    k_value = 30  # 递归阈值，待定
    
    json_files = find_json_files(data_dir)
    
    if not json_files:
        print(f"在 {data_dir}/ 目录下未找到JSON文件！")
        print(f"请将JSON文件放入 {data_dir}/ 目录。")
    else:
        for json_file in json_files:
            json_path = os.path.join(data_dir, json_file)
            with open(json_path, 'r', encoding='utf-8') as f:
                print(f"处理文件: {json_file}")
                data = json.load(f)
                
                results = process_json_data(
                    data, 
                    json_file, 
                    k=k_value
                )
