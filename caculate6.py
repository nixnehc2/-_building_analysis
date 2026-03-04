from typing import List, Tuple, Optional
from shapely.geometry import Polygon, Point
import numpy as np

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
        
        # 保存图片
        try:
            plt.savefig(filename, dpi=dpi, bbox_inches='tight', facecolor='white')
            print(f"图片已保存至: {filename}")
        except Exception as e:
            print(f"保存图片失败: {e}")
    
    # 12. 显示图形
    plt.tight_layout()
    plt.show()
    
    return polygon

def save_repaired_polygon(
    original_json_data: Dict,
    repaired_polygon: Polygon,
    original_filename: str,
    output_dir: str = "repair"
) -> str:
    """
    将修复后的多边形保存为JSON文件，格式与输入JSON类似
    
    参数:
        original_json_data: 原始JSON数据
        repaired_polygon: 修复后的多边形对象
        original_filename: 原始JSON文件名
        output_dir: 输出目录，默认为'repair'
    
    返回:
        str: 保存的文件路径
    """
    # 获取原始多边形的缩放比例
    length_rate = original_json_data['floor1']['meta']['lengthRate']
    length_rate_mm_per_px = float(length_rate.split()[0])
    
    # 将修复后的多边形坐标转换回原始单位
    repaired_coords = list(repaired_polygon.exterior.coords)
    
    # 转换坐标（从像素单位转回原始单位）
    converted_points = []
    for x_px, y_px in repaired_coords[:-1]:  # 去掉最后一个闭合点
        # 转换回原始坐标（乘以缩放比例）
        x_original = x_px * length_rate_mm_per_px
        y_original = y_px * length_rate_mm_per_px
        
        # 格式化为字符串，与原始格式匹配
        point_str = f"({x_original:.2f},{y_original:.2f})"
        converted_points.append(point_str)
    
    # 创建新的JSON数据（复制原始结构，只替换多边形点）
    new_json_data = original_json_data.copy()
    
    # 更新边界多边形点
    new_json_data['floor1']['boundary']['边界'][0] = converted_points
    
    # 可选：添加修复信息到meta中
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 生成输出文件名
    basename = os.path.basename(original_filename)
    filename_without_ext = os.path.splitext(basename)[0]
    output_filename = f"{filename_without_ext}_1.json"
    output_path = os.path.join(output_dir, output_filename)
    
    # 保存为JSON文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_json_data, f, ensure_ascii=False, indent=2)
        
        print(f"修复后的多边形已保存到: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"保存文件失败: {e}")
        return None

def detect_and_fix_symmetry(
    polygon: Polygon, 
    eps_match: float = 50,      # 用于判断两个点是否"接近"的容差
    eps_axis: float = 10,       # 用于判断点是否在对称轴上的容差（通常更小）
    min_match_ratio: float = 0.9
) -> Polygon:
    """
    检测多边形是否大致对称，如果是则将对称的一半复制到另一半
    
    参数:
        polygon: shapely多边形
        eps_match: 容差距离，用于判断对称点是否匹配
        eps_axis: 容差距离，用于判断点是否在对称轴上
        min_match_ratio: 最小匹配比例阈值
        
    返回:
        修正后的多边形（如果不对称则返回原多边形）
    """
    # 获取多边形坐标（移除最后一个重复的闭合点）
    original_coords = list(polygon.exterior.coords)
    coords = original_coords[:-1] if len(original_coords) > 1 and original_coords[0] == original_coords[-1] else original_coords
    
    if len(coords) < 3:
        return polygon
    
    # 将坐标转换为numpy数组方便计算
    points = np.array(coords)
    
    # 计算x和y坐标的平均值作为对称轴的备选位置
    x_mean = np.mean(points[:, 0])
    y_mean = np.mean(points[:, 1])
    
    # 尝试两种对称轴：垂直对称轴（x=常数）和水平对称轴（y=常数）
    best_symmetry_axis = None
    best_symmetry_type = None  # 'vertical' 或 'horizontal'
    best_symmetry_ratio = 0
    best_left_indices = []  # 存储左/下半部分的点索引
    best_right_indices = [] # 存储右/上半部分的点索引
    best_on_axis_indices = []  # 存储对称轴上的点索引
    
    def check_symmetry(axis_type: str, axis_value: float) -> Tuple[float, List[int], List[int], List[int]]:
        """检查对称性并返回匹配比例、点索引和对称轴上的点索引"""
        if axis_type == 'vertical':
            # 垂直对称轴 x = axis_value
            left_indices = []
            right_indices = []
            on_axis_indices = []
            
            # 使用 eps_axis 判断点是否在对称轴上
            for i, (x, y) in enumerate(points):
                if abs(x - axis_value) <= eps_axis:
                    on_axis_indices.append(i)
                elif x < axis_value:
                    left_indices.append(i)
                else:
                    right_indices.append(i)
            
            if not left_indices or not right_indices:
                return 0.0, [], [], []
            
            # 计算对称匹配比例
            matches = 0
            total_points = len(left_indices) + len(right_indices)
            
            # 建立对称点映射
            left_to_right_map = {}
            right_to_left_map = {}
            
            # 使用 eps_match 判断对称点是否匹配
            for i in left_indices:
                x, y = points[i]
                x_sym = 2 * axis_value - x
                
                # 在右边寻找匹配的点
                for j in right_indices:
                    xj, yj = points[j]
                    distance = np.sqrt((xj - x_sym)**2 + (yj - y)**2)
                    if distance < eps_match:
                        matches += 2
                        left_to_right_map[i] = j
                        right_to_left_map[j] = i
                        break
            
            symmetry_ratio = matches / total_points if total_points > 0 else 0
            return symmetry_ratio, left_indices, right_indices, on_axis_indices
            
        else:  # 'horizontal'
            # 水平对称轴 y = axis_value
            bottom_indices = []
            top_indices = []
            on_axis_indices = []
            
            # 使用 eps_axis 判断点是否在对称轴上
            for i, (x, y) in enumerate(points):
                if abs(y - axis_value) <= eps_axis:
                    on_axis_indices.append(i)
                elif y < axis_value:
                    bottom_indices.append(i)
                else:
                    top_indices.append(i)
            
            if not bottom_indices or not top_indices:
                return 0.0, [], [], []
            
            # 计算对称匹配比例
            matches = 0
            total_points = len(bottom_indices) + len(top_indices)
            
            # 建立对称点映射
            bottom_to_top_map = {}
            top_to_bottom_map = {}
            
            # 使用 eps_match 判断对称点是否匹配
            for i in bottom_indices:
                x, y = points[i]
                y_sym = 2 * axis_value - y
                
                # 在上部寻找匹配的点
                for j in top_indices:
                    xj, yj = points[j]
                    distance = np.sqrt((xj - x)**2 + (yj - y_sym)**2)
                    if distance < eps_match:
                        matches += 2
                        bottom_to_top_map[i] = j
                        top_to_bottom_map[j] = i
                        break
            
            symmetry_ratio = matches / total_points if total_points > 0 else 0
            return symmetry_ratio, bottom_indices, top_indices, on_axis_indices
    
    # 检查垂直对称
    vert_ratio, vert_left_indices, vert_right_indices, vert_on_axis = check_symmetry('vertical', x_mean)
    if vert_ratio > best_symmetry_ratio:
        best_symmetry_ratio = vert_ratio
        best_symmetry_axis = x_mean
        best_symmetry_type = 'vertical'
        best_left_indices = vert_left_indices
        best_right_indices = vert_right_indices
        best_on_axis_indices = vert_on_axis
    
    # 检查水平对称
    horiz_ratio, horiz_bottom_indices, horiz_top_indices, horiz_on_axis = check_symmetry('horizontal', y_mean)
    if horiz_ratio > best_symmetry_ratio:
        best_symmetry_ratio = horiz_ratio
        best_symmetry_axis = y_mean
        best_symmetry_type = 'horizontal'
        best_left_indices = horiz_bottom_indices
        best_right_indices = horiz_top_indices
        best_on_axis_indices = horiz_on_axis
    
    # 如果对称比例达到阈值，进行对称修正
    if best_symmetry_ratio >= min_match_ratio and best_symmetry_type:
        # 获取对称轴上的点（已经计算过了，使用 best_on_axis_indices）
        on_axis_indices = best_on_axis_indices
        
        # 按照顺序构建对称多边形
        n = len(points)
        ordered_points = []
        if best_symmetry_type == 'vertical':
            print("vertical")
            # 对于垂直对称，我们需要左半部分和对称轴上的点
            # 找到遍历顺序的起始点：前一个是右点，这个是左点或对称轴上的点
            start_idx = None
            for i in range(n):
                prev_idx = (i - 1) % n
                curr_idx = i
                
                # 检查前一个点是否在右边，当前点是否在左边或对称轴上
                if prev_idx in best_right_indices and (curr_idx in best_left_indices or curr_idx in on_axis_indices):
                    start_idx = curr_idx
                    break
            
            # 如果没有找到合适的起始点，使用第一个左点
            if start_idx is None and best_left_indices:
                start_idx = best_left_indices[0]
            elif start_idx is None and on_axis_indices:
                start_idx = on_axis_indices[0]
            
            if start_idx is not None:
                # 按照顺时针顺序收集左半部分和对称轴上的点
                idx = start_idx
                visited = []
                
                while idx not in visited:
                    visited.append(idx)
                    if idx in best_left_indices or idx in on_axis_indices:
                        ordered_points.append(tuple(points[idx]))
                    
                    idx = (idx + 1) % n
                    if idx == start_idx:
                        break
                # 现在添加对称的右半部分（逆序）
                symmetric_points = []
                for idx in reversed(visited):
                    if idx in best_left_indices:
                        x, y = points[idx]
                        x_sym = 2 * best_symmetry_axis - x
                        symmetric_points.append((x_sym, y))
                    elif idx in on_axis_indices:
                        # 对称轴上的点保持不变
                        symmetric_points.append(tuple(points[idx]))

                # 合并点序列
                final_points = ordered_points + symmetric_points
                
                # 确保闭合
                if final_points and final_points[0] != final_points[-1]:
                    final_points.append(final_points[0])
                
                return Polygon(final_points)
        
        else:  # horizontal symmetry
            print("horizontal")
            # 对于水平对称，我们需要下半部分和对称轴上的点
            # 找到遍历顺序的起始点：前一个是上点，这个是下点或对称轴上的点
            start_idx = None
            for i in range(n):
                prev_idx = (i - 1) % n
                curr_idx = i
                
                # 检查前一个点是否在上边，当前点是否在下边或对称轴上
                if prev_idx in best_right_indices and (curr_idx in best_left_indices or curr_idx in on_axis_indices):
                    start_idx = curr_idx
                    break
            
            # 如果没有找到合适的起始点，使用第一个下点
            if start_idx is None and best_left_indices:
                start_idx = best_left_indices[0]
            elif start_idx is None and on_axis_indices:
                start_idx = on_axis_indices[0]
            
            if start_idx is not None:
                # 按照顺时针顺序收集下半部分和对称轴上的点
                idx = start_idx
                visited = set()
                
                while idx not in visited:
                    visited.add(idx)
                    if idx in best_left_indices or idx in on_axis_indices:
                        ordered_points.append(tuple(points[idx]))
                    
                    idx = (idx + 1) % n
                    if idx == start_idx:
                        break
                
                # 添加对称的上半部分（逆序）
                symmetric_points = []
                for idx in reversed(list(visited)):
                    if idx in best_left_indices:
                        x, y = points[idx]
                        y_sym = 2 * best_symmetry_axis - y
                        symmetric_points.append((x, y_sym))
                    elif idx in on_axis_indices:
                        # 对称轴上的点保持不变
                        symmetric_points.append(tuple(points[idx]))
                
                # 合并点序列
                final_points = ordered_points + symmetric_points
                
                # 确保闭合
                if final_points and final_points[0] != final_points[-1]:
                    final_points.append(final_points[0])
                
                return Polygon(final_points)
    
    # 如果不满足对称条件，返回原多边形
    return polygon


from typing import Tuple, List
from shapely.geometry import Polygon, Point
import numpy as np
import math

def fix_right_angles(polygon: Polygon, theta_eps: float = 5.0) -> Polygon:
    """
    调整多边形的角度使其成为直角（90度或270度）
    
    参数:
        polygon: 输入的多边形
        theta_eps: 角度容差（度），如果角度与90或270度的差小于这个值，就进行调整
        
    返回:
        调整后的多边形
    """
    # 获取多边形坐标
    coords = list(polygon.exterior.coords)
    
    # 确保多边形是闭合的（第一个和最后一个点相同）
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    
    # 移除重复的闭合点以便处理
    coords_list = coords[:-1]  # 去掉最后一个重复的点
    n = len(coords_list)
    
    if n < 3:
        return polygon
    
    # 将度转换为弧度

    theta_eps_rad = math.radians(theta_eps)
    target_angle_90_rad = math.pi / 2  # 90度
    target_angle_270_rad = 3 * math.pi / 2  # 270度
    
    # 创建一个可修改的点列表
    new_coords = coords_list.copy()
    
    # 遍历所有相邻的三个点（考虑循环）
    for i in range(n):
        # 获取三个点：p1, p2, p3
        p1 = np.array(new_coords[(i - 1) % n])
        p2 = np.array(new_coords[i])
        p3 = np.array(new_coords[(i + 1) % n])
        
        # 计算向量
        v1 = p1 - p2  # p2指向p1的向量
        v2 = p3 - p2  # p2指向p3的向量
        
        # 计算向量长度
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 > 1e-10 and norm_v2 > 1e-10:  # 避免除零
            # 计算夹角（使用点积公式）
            cos_theta = np.dot(v1, v2) / (norm_v1 * norm_v2)
            # 处理数值误差
            cos_theta = max(-1.0, min(1.0, cos_theta))
            theta = math.acos(cos_theta)
            
            # 检查角度是否接近90度
            diff_90 = abs(theta - target_angle_90_rad)
            diff_270 = abs(theta - target_angle_270_rad)
            
            if diff_90 <= theta_eps_rad or diff_270 <= theta_eps_rad:
                # 需要调整角度为直角
                # 确定目标角度是90度还是270度（选择更接近的）
                target_angle = target_angle_90_rad if diff_90 <= diff_270 else target_angle_270_rad
                
                # 计算新的p3位置
                # 方法1：保持p2到p3的距离不变，调整方向使其与v1垂直
                
                # 计算v1的单位向量
                v1_unit = v1 / norm_v1
                
                # 计算垂直于v1的单位向量（有两个方向）
                # 使用旋转矩阵旋转90度
                rot_matrix_90 = np.array([[0, -1], [1, 0]])  # 逆时针旋转90度
                rot_matrix_270 = np.array([[0, 1], [-1, 0]])  # 逆时针旋转270度（顺时针90度）
                
                # 计算两个可能的垂直方向
                v_perp_90 = rot_matrix_90 @ v1_unit
                v_perp_270 = rot_matrix_270 @ v1_unit
                
                # 当前v2的方向
                v2_unit_current = v2 / norm_v2
                
                # 选择与当前v2方向更接近的垂直方向
                dot_with_90 = np.dot(v2_unit_current, v_perp_90)
                dot_with_270 = np.dot(v2_unit_current, v_perp_270)
                
                if dot_with_90 >= dot_with_270:
                    selected_perp = v_perp_90
                else:
                    selected_perp = v_perp_270
                
                # 计算新的p3位置
                new_p3 = p2 + norm_v2 * selected_perp
                
                # 更新点坐标
                new_coords[(i + 1) % n] = tuple(new_p3)
    
    # 重新构建闭合多边形
    final_coords = new_coords.copy()
    final_coords.append(final_coords[0])  # 闭合
    
    # 创建新多边形
    fixed_polygon = Polygon(final_coords)
    
    return fixed_polygon

def simplify_coords(polygon, min_distance=2.0):
    """
    简化坐标点，合并过于接近的点
    注意：第一个点和最后一个点是相邻的（多边形是闭合的）
    """
    coords=list(polygon.exterior.coords)
    if not coords or len(coords) < 3:
        return coords
    
    # 首先检查起点和终点是否相同（多边形通常是闭合的）
    if coords[0] == coords[-1]:
        # 移除重复的终点，处理内部点后再闭合
        coords = coords[:-1]
    
    if len(coords) < 3:
        return coords
    
    simplified_coords = [coords[0]]
    
    # 简化中间点
    for i in range(1, len(coords)):
        last_point = simplified_coords[-1]
        current_point = coords[i]
        distance = np.linalg.norm(np.array(current_point) - np.array(last_point))
        
        if distance >= min_distance:
            simplified_coords.append(current_point)
    
    # 检查简化后的第一个点和最后一个点是否过于接近
    if len(simplified_coords) >= 3:
        first_point = simplified_coords[0]
        last_point = simplified_coords[-1]
        first_last_distance = np.linalg.norm(np.array(last_point) - np.array(first_point))
        
        # 如果第一个点和最后一个点过于接近，则移除最后一个点
        if first_last_distance < min_distance:
            simplified_coords.pop()
    
    # 确保多边形至少有三个点
    if len(simplified_coords) < 3:
        return coords
    
    # 添加闭合点（与第一个点相同）
    if simplified_coords[0] != simplified_coords[-1]:
        simplified_coords.append(simplified_coords[0])
    
    return Polygon(simplified_coords)

from shapely.geometry import Polygon
import numpy as np
from typing import List, Tuple
import math

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
    polygon=simplify_polygon_by_angle(polygon)
    polygon=simplify_coords(polygon)
    polygon=fix_right_angles(polygon)
    polygon=detect_and_fix_symmetry(polygon)
    # visualize_polygon(list(polygon.exterior.coords))
    return polygon

def process_json_data(json_data, filename: str) -> Dict:
    basename = os.path.basename(filename)
    # 分割文件名和扩展名
    filename1, ext = os.path.splitext(basename)
    boundary_polygon = json_data['floor1']['boundary']['边界'][0]
    length_rate = json_data['floor1']['meta']['lengthRate']
    length_rate_mm_per_px = float(length_rate.split()[0])
    polygon = init(boundary_polygon, length_rate_mm_per_px)
    # visualize_polygon(list(polygon.exterior.coords),filename1+"_pre")
    polygon=get_pro_polygon(polygon)
    # visualize_polygon(list(polygon.exterior.coords),filename1+'_result')
    save_repaired_polygon(json_data, polygon, filename)
    return polygon

def find_json_files(directory: str = ".") -> List[str]:
    """
    查找指定目录下的所有JSON文件
    """
    json_files = []
    for file in os.listdir(directory):
        if file.endswith('.json'):
            json_files.append(file)
    
    # 排序文件名
    json_files.sort()
    return json_files

json_files = find_json_files()
for json_file in json_files:
    with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 处理数据
            print(json_file)
            results = process_json_data(
                data, 
                json_file
            )