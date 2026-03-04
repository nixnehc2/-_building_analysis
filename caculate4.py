import json
import math
import os
import pandas as pd
from typing import Dict, List, Tuple, Optional
from shapely.geometry import Polygon, Point
import numpy as np

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

def calculate_rect(rect_polygon): 
    """
    计算矩形长宽比和长边方向（简洁版本）
    
    返回:
        aspect_ratio: 长宽比（≥1）
        angle: 长边角度（0-180度）
    """
    vertices = list(rect_polygon.exterior.coords)[:-1]
    
    if len(vertices) != 4:
        raise ValueError("输入多边形不是矩形")
    
    # 计算四条边的长度和向量
    sides = []
    vectors = []
    
    for i in range(4):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % 4]
        
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        sides.append(length)
        vectors.append((x2 - x1, y2 - y1))
    
    # 找出不同的边长
    unique_lengths = sorted(set(round(l, 6) for l in sides))
    
    # 计算长宽比
    if len(unique_lengths) == 1:
        aspect_ratio = 1.0
        # 正方形使用第一条边的方向
        dx, dy = vectors[0]
    else:
        # 长宽比 = 长/宽
        aspect_ratio = max(unique_lengths) / min(unique_lengths)
        # 找到长边向量
        long_side_idx = sides.index(max(sides))
        dx, dy = vectors[long_side_idx]
    
    # 计算角度
    angle = np.degrees(np.arctan2(dy, dx)) % 180
    
    return aspect_ratio, angle

def calculate_corner_density(polygon, angle_threshold=165, k=1.5, min_edge_ratio=1.0):
    """
    计算建筑轮廓的转角密度（新版定义）
    
    参数:
        polygon: shapely Polygon对象
        angle_threshold: 有效转角的阈值角度（单位：度）
                        连续三个顶点形成的夹角 < 此值时认定为潜在有效转角
        k: 长边/短边比例阈值，当相邻两条边的比例 > k 时才认定为有效转角
        min_edge_ratio: 边长比例的最小值，用于排除太小的边
    
    返回:
        corner_density: 转角密度（有效转角个数 / 周长，单位：个/米）
        num_effective_corners: 有效转角个数
        corner_details: 转角详细信息列表
    """
    # 获取多边形顶点（去掉最后一个重复点）
    coords = list(polygon.exterior.coords)[:-1]
    n = len(coords)
    
    if n < 3:
        return 0.0, 0, []
    
    # 计算周长
    perimeter = polygon.length
    
    # 计算有效转角个数
    effective_corners = 0
    corner_details = []
    
    for i in range(n):
        # 获取三个连续顶点：前一个点、当前点、下一个点
        p1 = np.array(coords[(i-1) % n])  # 前一个顶点
        p2 = np.array(coords[i])          # 当前顶点
        p3 = np.array(coords[(i+1) % n])  # 后一个顶点
        
        # 计算向量 p1->p2 和 p2->p3
        v1 = p2 - p1
        v2 = p3 - p2
        
        # 计算向量长度（边长）
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            continue  # 跳过零长度向量
        
        # 计算夹角的余弦值
        dot_product = np.dot(v1, v2)
        cos_angle = dot_product / (norm_v1 * norm_v2)
        
        # 处理浮点误差
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        # 计算角度（度）
        angle = np.degrees(np.arccos(cos_angle))
        
        # 计算边长比例（长边/短边）
        edge_ratio = max(norm_v1, norm_v2) / min(norm_v1, norm_v2) if min(norm_v1, norm_v2) > 0 else 1.0
        
        # 判断是否为有效转角（两个条件必须同时满足）：
        # 1. 夹角 < angle_threshold
        # 2. 边长比例 > k 或 至少一条边满足最小比例要求
        is_effective = (angle < angle_threshold) and (edge_ratio > k)
        
        if is_effective:
            effective_corners += 1
            corner_details.append({
                'corner_index': i,
                'angle_degrees': angle,
                'edge1_length': norm_v1,
                'edge2_length': norm_v2,
                'edge_ratio': edge_ratio,
                'vertex_coords': (p2[0], p2[1])
            })
        elif angle < angle_threshold and edge_ratio <= k:
            # 记录不符合边长比例条件的潜在转角（用于调试）
            corner_details.append({
                'corner_index': i,
                'angle_degrees': angle,
                'edge1_length': norm_v1,
                'edge2_length': norm_v2,
                'edge_ratio': edge_ratio,
                'vertex_coords': (p2[0], p2[1]),
                'rejected_reason': f'边长比例 {edge_ratio:.2f} <= k={k}'
            })
    
    # 计算转角密度
    corner_density = effective_corners / perimeter if perimeter > 0 else 0.0
    
    return corner_density, effective_corners, corner_details

def calculate_compactness(polygon):
    """
    计算紧凑度（圆形度）
    
    公式: (4 * π * 面积) / (周长²)
    值越接近1表示形状越接近圆形
    """
    area = polygon.area
    perimeter = polygon.length
    
    if perimeter == 0:
        return 0.0
    
    compactness = (4 * math.pi * area) / (perimeter ** 2)
    return compactness

def calculate_concavity(polygon):
    """
    计算凹凸度
    
    公式: 建筑轮廓面积 / 凸包面积
    值越接近1表示形状越凸
    """
    area = polygon.area
    convex_hull = polygon.convex_hull
    convex_area = convex_hull.area
    
    if convex_area == 0:
        return 0.0
    
    concavity = area / convex_area
    return concavity

def analyze_corner_statistics(corner_details):
    """
    分析转角统计信息
    """
    if not corner_details:
        return None
    
    # 只统计有效转角
    effective_corners = [c for c in corner_details if 'rejected_reason' not in c]
    
    if not effective_corners:
        return None
    
    angles = [c['angle_degrees'] for c in effective_corners]
    edge_ratios = [c['edge_ratio'] for c in effective_corners]
    
    stats = {
        'min_angle': min(angles),
        'max_angle': max(angles),
        'avg_angle': np.mean(angles),
        'median_angle': np.median(angles),
        'min_edge_ratio': min(edge_ratios),
        'max_edge_ratio': max(edge_ratios),
        'avg_edge_ratio': np.mean(edge_ratios),
        'median_edge_ratio': np.median(edge_ratios)
    }
    
    return stats

def check_polygon_intersection(
    A: List[Polygon], 
    x: Polygon, 
    y: Polygon, 
    buffer_tolerance: float = 1e-7
) -> int:
    x_buffered = x.buffer(buffer_tolerance)
    y_buffered = y.buffer(buffer_tolerance)
    if not x_buffered.intersects(y_buffered):
        return 0
    
    intersection_buffered = (x.intersection(y)).buffer(buffer_tolerance)

    if A:
        # 遍历A中的每个polygon，检查是否有交集
        for poly_a in A:
            # 检查交集与A中的polygon是否有交集
            # 使用缓冲处理浮点误差
            a_buffered = poly_a.buffer(buffer_tolerance)
            
            # 检查实际交集与缓冲后的polygon
            if intersection_buffered.intersects(a_buffered):
                    return 2
    
    # x和y有交集，但与A中任何polygon无交集
    return 1

def process_json_data(json_data, filename: str, k: float = 1.5, angle_threshold: float = 165) -> Dict:
    """
    处理JSON数据，计算边界图形的所有形态指标
    
    参数:
        k: 长边/短边比例阈值
        angle_threshold: 有效转角的角度阈值
    
    返回一个字典，包含所有计算结果
    """
    all_results = {}
    for floor_key, floor_data in json_data.items():
        if floor_key.startswith('floor'):
            
            try:
                # 获取边界数据和缩放比例
                boundary_polygon = floor_data['boundary']['边界'][0]
                length_rate = floor_data['meta']['lengthRate']
                
                # 创建多边形并获取缩放比例
                length_rate_mm_per_px = float(length_rate.split()[0])
                polygon = init(boundary_polygon, length_rate_mm_per_px)
                rect = polygon.minimum_rotated_rectangle
                convex_hull = polygon.convex_hull

                # 计算像素单位的面积和周长
                area_px = polygon.area
                perimeter_px = polygon.length
                
                # 转换为米单位
                pixel_to_m = length_rate_mm_per_px / 1000  # 像素到米的转换系数
                area_m = area_px * (pixel_to_m ** 2)
                perimeter_m = perimeter_px * pixel_to_m
                
                # 计算形态指标
                aspect_ratio, principal_angle = calculate_rect(rect)
                concavity = calculate_concavity(polygon)
                compactness = calculate_compactness(polygon)
                
                # 计算转角密度（新版定义）
                corner_density, num_effective_corners, corner_details = calculate_corner_density(
                    polygon, 
                    angle_threshold=angle_threshold, 
                    k=k
                )
                
                # 分析转角统计
                corner_stats = analyze_corner_statistics(corner_details)
                
                # 计算其他面积（米单位）
                convex_area_m = convex_hull.area * (pixel_to_m ** 2)
                rect_area_m = rect.area * (pixel_to_m ** 2)
                
                # 计算衍生指标
                area_utilization = area_m / rect_area_m if rect_area_m > 0 else 0
                convexity_index = area_m / convex_area_m if convex_area_m > 0 else 0
                
                # 创建唯一标识符（文件名 + 楼层）
                result_key = f"{os.path.splitext(filename)[0]}_{floor_key}"
                
                # 存储结果 - 统一使用米单位
                all_results[result_key] = {
                    # 基础信息
                    '文件名': filename,
                    '楼层标识': floor_key,
                    '楼层名称': floor_data['meta']['name'],
                    '缩放比例': length_rate,
                    '边界点数': len(boundary_polygon),
                    
                    # 转角参数配置
                    '转角角度阈值_度': angle_threshold,
                    '转角边长比阈值_k': k,
                    
                    # 基本几何指标（米单位）
                    '周长_m': perimeter_m,
                    '面积_m²': area_m,
                    '凸包面积_m²': convex_area_m,
                    '最小矩形面积_m²': rect_area_m,
                    
                    # 形态指标
                    '长宽比': aspect_ratio,
                    '主方向角_度': principal_angle,
                    '凹凸度': concavity,
                    '紧凑度': compactness,
                    '转角密度_个每米': corner_density,
                    '有效转角数': num_effective_corners,
                    
                    # 衍生指标
                    '面积利用率': area_utilization,
                    '凸性指标': convexity_index,
                }
                
            except KeyError as e:
                print(f"⚠ 缺少必要字段: {e}")
                continue
            except Exception as e:
                print(f"⚠ 处理楼层 {floor_key} 时出错: {e}")
                continue
    
    return all_results

def find_json_files(directory: str = "data") -> List[str]:
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

def create_summary_table(all_results: Dict) -> pd.DataFrame:
    """
    创建汇总表格，包含所有形态指标
    """
    if not all_results:
        print("没有找到任何可处理的数据")
        return pd.DataFrame()
    
    # 转换为DataFrame
    df = pd.DataFrame.from_dict(all_results, orient='index')
    
    # 重置索引并重命名
    df = df.reset_index(drop=True)
    
    # 定义需要格式化的小数位数
    # 6位小数列（主要指标）
    numeric_columns_6f = [
        '周长_m', '面积_m²', '凸包面积_m²', '最小矩形面积_m²',
        '长宽比', '凹凸度', '紧凑度', '面积利用率', '凸性指标'
    ]
    
    # 6位小数列（角度和转角密度）
    numeric_columns_6f_special = [
        '主方向角_度', '转角密度_个每米', '转角角度阈值_度', '转角边长比阈值_k'
    ]
    
    # 整数列
    integer_columns = [
        '有效转角数', '边界点数'
    ]
    
    # 格式化数值列
    for col in df.columns:
        if col in numeric_columns_6f and col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: f"{x:.6f}" if pd.notnull(x) else "")
        elif col in numeric_columns_6f_special and col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: f"{x:.6f}" if pd.notnull(x) else "")
        elif col in integer_columns and col in df.columns:
            # 整数列
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        elif col in ['文件名', '楼层标识', '楼层名称', '缩放比例'] and col in df.columns:
            # 字符串列，保持原样
            pass
    
    return df

def process_graph_information(json_data):
    areas=[]
    doors=[]
    results=[]
    for floor_key, floor_data in json_data.items():
        if floor_key.startswith('floor'):
            result_line1=[]
            result_line2=[]
            length_rate = floor_data['meta']['lengthRate']
            length_rate_mm_per_px = float(length_rate.split()[0])
            # print(floor_data['boundary'])
            for area_key,area_data in floor_data['boundary'].items():
                if(area_key=='边界'):
                    continue
                areas.append(init(area_data[0],length_rate_mm_per_px))
                result_line1.append(1)
                result_line2.append(1)
            for area_key,area_data in floor_data['rooms'].items():
                areas.append(init(area_data[0],length_rate_mm_per_px))
                result_line1.append(2)
                result_line2.append(1)
            for area_key,area_data in floor_data['doors'].items():
                doors.append(init(area_data[0],length_rate_mm_per_px))
            results.append(result_line1)
            results.append(result_line2)

    for i in range(len(areas)):
        polygon_x=areas[i]
        result_line=[]
        for j in range(len(areas)):
            polygon_y=areas[j]
            if(i==j):
                result_line.append(0)
                continue
            result_line.append(check_polygon_intersection(doors,polygon_x,polygon_y))
        results.append(result_line)
    return results

def main():
    
    # 用户输入转角参数
    print("\n=== 转角参数配置 ===")
    try:
        angle_threshold = float(input("请输入转角角度阈值(度，默认165): ") or 165)
        k_value = float(input("请输入长边/短边比例阈值k(默认1.5): ") or 1.5)
        print(f"转角定义: 角度 < {angle_threshold}° 且 长边/短边 > {k_value}")
    except ValueError:
        print("输入无效，使用默认值: angle_threshold=165, k=1.5")
        angle_threshold = 165
        k_value = 1.5
    
    # 获取 data/ 目录下的所有JSON文件
    data_dir = "data"
    json_files = find_json_files(data_dir)
    
    if not json_files:
        print(f"在 {data_dir}/ 目录下未找到JSON文件！")
        print(f"请将JSON文件放入 {data_dir}/ 目录。")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件:")
    for i, file in enumerate(json_files, 1):
        print(f"  {i}. {file}")
    
    # 处理所有JSON文件
    all_results = {}
    processed_files = 0
    
    for json_file in json_files:
            
            # 加载JSON数据
        json_path = os.path.join(data_dir, json_file)
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 处理数据
        results = process_json_data(
            data, 
            json_file, 
            k=k_value, 
            angle_threshold=angle_threshold
        )
        

        all_results.update(results)
        processed_files += 1
        print(f"✓ 文件 {json_file} 处理完成")

        filename=os.path.splitext(json_file)[0]
        results_graph = process_graph_information(data)
        with open(filename+'_anwer.txt',"w",encoding='utf-8') as f:
            print(results_graph,file=f)
    
    # 创建汇总表格
    print("\n正在生成汇总表格...")
    df = create_summary_table(all_results)
    
    # 保存为Excel文件
    excel_filename = "建筑轮廓形态分析汇总.xlsx"
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"\n✓ 汇总表格已保存为: {excel_filename}")
    
if __name__ == "__main__":
    main()