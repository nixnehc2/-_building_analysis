import json
import math
import os
import pandas as pd
from typing import Dict, Tuple, List
from shapely.geometry import Polygon
import numpy as np
from pyproj import Transformer
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Polygon as MplPolygon
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体 - 解决中文乱码问题
# Windows系统
if os.name == 'nt':
    font_name = 'SimHei'  # 黑体
# Mac系统
elif os.name == 'posix':
    font_name = 'Arial Unicode MS'
# Linux系统
else:
    font_name = 'DejaVu Sans'

# 设置matplotlib使用中文字体
matplotlib.rcParams['font.sans-serif'] = [font_name]
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# 初始化坐标转换器：从 3857 (Web墨卡托) 转到 4507 (CGCS2000 南京所在分带平面坐标)
transformer = Transformer.from_crs("epsg:3857", "epsg:4507", always_xy=True)

def init_gis_polygon(rings):
    """
    将 GIS 的 rings 转换为经 pyproj 转换后的 Shapely 多边形
    """
    shell = rings[0]
    # 使用 pyproj 将每一个点从 3857 转为 4507 (单位：米)
    transformed_shell = [transformer.transform(pt[0], pt[1]) for pt in shell]
    return Polygon(transformed_shell)

def simplify_coords(coords, min_distance=2.0):
    """
    简化坐标点，合并过于接近的点
    注意：第一个点和最后一个点是相邻的（多边形是闭合的）
    """
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
    
    return simplified_coords


def visualize_polygon(polygon, simplified_coords, fid, output_dir='polygon_visualizations'):
    """
    可视化多边形并保存为PNG图片
    Args:
        polygon: shapely Polygon 对象（原始多边形）
        simplified_coords: 简化后的坐标点列表（应该是闭合的）
        fid: 建筑FID
        output_dir: 输出目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # 绘制原始多边形（浅色背景）
    original_coords = list(polygon.exterior.coords)  # shapely多边形已经是闭合的
    
    # 绘制简化后的多边形（突出显示）
    simplified_polygon = MplPolygon(simplified_coords, closed=True, 
                                    edgecolor='blue', facecolor='lightblue', 
                                    linewidth=3, alpha=0.6, label='简化后多边形')
    ax.add_patch(simplified_polygon)
    
    # 绘制原始多边形（浅色背景）
    original_polygon = MplPolygon(original_coords, closed=True, 
                                  edgecolor='lightgray', facecolor='whitesmoke', 
                                  linewidth=2, alpha=0.3, label='原始多边形')
    ax.add_patch(original_polygon)
    
    # 标注简化后的每个点（不显示重复的起点）
    display_coords = simplified_coords
    if len(simplified_coords) > 0 and simplified_coords[0] == simplified_coords[-1]:
        display_coords = simplified_coords[:-1]
    
    for i, (x, y) in enumerate(display_coords):
        # 绘制点
        ax.plot(x, y, 'ro', markersize=8, markeredgecolor='red', markerfacecolor='yellow')
        
        # 添加点标签
        label = f"P{i}"
        ax.text(x, y, label, fontsize=10, fontweight='bold', 
                ha='right', va='bottom', color='darkred',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        # 显示坐标
        coord_text = f"({x:.2f}, {y:.2f})"
        ax.text(x, y, f'\n\n{coord_text}', fontsize=8, 
                ha='center', va='top', color='green', style='italic')
    
    # 计算边界并设置合适的视图范围
    all_x = [coord[0] for coord in original_coords] + [coord[0] for coord in simplified_coords]
    all_y = [coord[1] for coord in original_coords] + [coord[1] for coord in simplified_coords]
    
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    
    # 添加10%的边距
    x_margin = (x_max - x_min) * 0.1
    y_margin = (y_max - y_min) * 0.1
    
    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    
    # 设置标题和标签
    ax.set_title(f'建筑多边形可视化 - FID: {fid}', fontsize=14, fontweight='bold')
    ax.set_xlabel('X坐标 (米)', fontsize=12)
    ax.set_ylabel('Y坐标 (米)', fontsize=12)
    
    # 添加网格
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # 添加图例
    ax.legend(loc='upper right', fontsize=10)
    
    # 添加统计信息框
    stats_text = f"原始点数: {len(original_coords)-1}\n简化后点数: {len(display_coords)}"
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
    
    # 设置纵横比相等
    ax.set_aspect('equal', adjustable='datalim')
    
    # 保存图片
    output_path = os.path.join(output_dir, f'FID_{fid}.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return output_path

def calculate_rect(rect_polygon) -> Tuple[float, float, float, float]: 
    """计算矩形长宽比、长边方向角，并返回长和宽"""
    vertices = list(rect_polygon.exterior.coords)[:-1]
    if len(vertices) != 4:
        rect_polygon = rect_polygon.minimum_rotated_rectangle
        vertices = list(rect_polygon.exterior.coords)[:-1]
    
    sides = []
    vectors = []
    for i in range(len(vertices)):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % len(vertices)]
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        sides.append(length)
        vectors.append((x2 - x1, y2 - y1))
    
    # 获取相邻边的长度作为长和宽
    sorted_lengths = sorted(sides, reverse=True)
    length_long = sorted_lengths[0]
    length_short = sorted_lengths[-1] if len(sorted_lengths) > 1 else length_long
    
    unique_lengths = sorted(set(round(l, 6) for l in sides))
    if len(unique_lengths) == 1:
        aspect_ratio = 1.0
        dx, dy = vectors[0]
    else:
        aspect_ratio = max(unique_lengths) / min(unique_lengths)
        long_side_idx = sides.index(max(sides))
        dx, dy = vectors[long_side_idx]
    
    angle = np.degrees(np.arctan2(dy, dx)) % 180
    return aspect_ratio, angle, length_long, length_short

def calculate_corner_density(polygon, angle_threshold=165, min_distance=2.0):
    """计算转角数量，相邻点距离小于min_distance时视为同一个点"""
    coords = list(polygon.exterior.coords)[:-1]  # 移除重复的终点
    n = len(coords)
    if n < 3: 
        return 0, coords  # 返回0和原始坐标
    
    # 第一步：合并过于接近的点
    simplified_coords = simplify_coords(coords, min_distance)
    
    # 第二步：在简化后的点上计算转角（移除重复的起点）
    if simplified_coords and simplified_coords[0] == simplified_coords[-1]:
        simplified_coords = simplified_coords[:-1]
    
    effective_corners = 0
    m = len(simplified_coords)
    
    for i in range(m):
        p1, p2, p3 = np.array(simplified_coords[i-1]), np.array(simplified_coords[i]), np.array(simplified_coords[(i+1)%m])
        
        # 检查三个点是否过于接近（以防万一）
        if np.linalg.norm(p2 - p1) < min_distance or np.linalg.norm(p3 - p2) < min_distance:
            continue
            
        v1, v2 = p2 - p1, p3 - p2
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        
        if n1 == 0 or n2 == 0: 
            continue
            
        cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        if np.degrees(np.arccos(cos_angle)) < angle_threshold:
            effective_corners += 1
    
    # 返回用于可视化的闭合多边形
    if simplified_coords and simplified_coords[0] != simplified_coords[-1]:
        viz_coords = simplified_coords + [simplified_coords[0]]
    else:
        viz_coords = simplified_coords
    
    return effective_corners, viz_coords

def process_gis_json(json_data, filename: str) -> Tuple[Dict, Dict]:
    """处理 GIS 格式数据并提取指定字段，只处理Function为Residence的建筑"""
    all_results = {}
    intermediate_results = {}
    features = json_data.get('features', [])
    
    print(f"正在转换并处理: {filename}...")
    
    residence_count = 0
    total_count = 0
    visualization_count = 0
    
    # 指定要绘制的FID列表
    target_fids = ['52975', '419']  # 新增：指定要绘制的FID

    for feat in features:
        total_count += 1
        try:
            attr = feat.get('attributes', {})
            geom = feat.get('geometry', {})
            
            # 关键修改：只处理 Function 为 Residence 的建筑
            function = attr.get('Function', '').strip()
            if function != 'Residence':
                continue
            
            residence_count += 1
            fid = attr.get('FID', 'Unknown')

            # if str(fid) not in target_fids:  # 新增过滤条件
            #     continue
            
            if 'rings' not in geom: 
                continue
            
            # 这里的 polygon 已经是转换后的 CGCS2000 投影坐标（单位：米）
            polygon = init_gis_polygon(geom['rings'])
            if polygon.area <= 0: 
                continue

            # 基础几何计算
            rect = polygon.minimum_rotated_rectangle
            convex_hull = polygon.convex_hull
            
            # 由于已经是平面坐标，直接计算即为真实米制单位
            area_m2 = polygon.area 
            perimeter_m = polygon.length
            aspect_ratio, principal_angle, rect_long, rect_short = calculate_rect(rect)
            num_corners, simplified_coords = calculate_corner_density(polygon)
            
            # 转角密度（个/米）
            corner_density = num_corners / perimeter_m if perimeter_m > 0 else 0
            
            # 紧凑度与凹凸度
            compactness = area_m2 / rect.area if rect.area > 0 else 0
            concavity = area_m2 / convex_hull.area if convex_hull.area > 0 else 0
            
            # 获取建筑年份
            age = attr.get('Age', 'N/A')
            # 如果Age是数字，转换为字符串
            if isinstance(age, (int, float)):
                age = str(int(age))
            
            # # 可视化多边形
            # if len(simplified_coords) >= 3:
            #     try:
            #         img_path = visualize_polygon(polygon, simplified_coords, fid)
            #         visualization_count += 1
            #         print(f"    ✓ 已生成可视化图片: {img_path}")
            #     except Exception as e:
            #         print(f"    ⚠  FID {fid} 可视化失败: {e}")
            
            result_key = f"{filename}_{fid}"
            all_results[result_key] = {
                'FID': fid,
                'Function': function,  # 添加Function字段
                '建筑高度': attr.get('Height', 0),
                '建筑年份': age,  # 使用提取的Age
                '周长_m': perimeter_m,
                '面积_m^2': area_m2,
                '长宽比': aspect_ratio,
                '主方向角_度': principal_angle,
                '凹凸度': concavity,
                '紧凑度': compactness,
                '转交密度_个': corner_density
            }
            
            # 中间结果
            intermediate_results[result_key] = {
                'FID': fid,
                'Function': function,
                '外接矩形长_m': rect_long,
                '外接矩形宽_m': rect_short,
                '凸包面积_m^2': convex_hull.area,
                '转角个数': num_corners,
                '简化后点数': len(simplified_coords),
                '原始点数': len(list(polygon.exterior.coords)[:-1]),
                '原始面积_m^2': area_m2,
                '原始周长_m': perimeter_m
            }

        except Exception as e:
            print(f"处理建筑时出错 (FID: {attr.get('FID', 'Unknown')}): {e}")
            continue
    
    print(f"  - 总共 {total_count} 个建筑，其中 {residence_count} 个为 Residence 类型")
    print(f"  - 已生成 {visualization_count} 个可视化图片")
    return all_results, intermediate_results

def create_summary_table(all_results: Dict) -> pd.DataFrame:
    if not all_results: 
        return pd.DataFrame()
    
    # 修改列顺序，添加 Function 和 建筑年份
    column_order = [
        'FID', 'Function', '建筑高度', '建筑年份', '周长_m', '面积_m^2', 
        '长宽比', '主方向角_度', '凹凸度', '紧凑度', '转交密度_个'
    ]
    
    df = pd.DataFrame.from_dict(all_results, orient='index')
    
    # 确保所有必需的列都存在
    for col in column_order:
        if col not in df.columns:
            df[col] = ''
    
    df = df[column_order]
    
    # 数值格式化
    num_cols = ['建筑高度', '周长_m', '面积_m^2', '长宽比', '主方向角_度', 
                '凹凸度', '紧凑度', '转交密度_个']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: f"{x:.6f}" if pd.notnull(x) else '')
    
    # 确保建筑年份是字符串格式
    if '建筑年份' in df.columns:
        df['建筑年份'] = df['建筑年份'].astype(str)
    
    return df

def create_intermediate_table(intermediate_results: Dict) -> pd.DataFrame:
    if not intermediate_results: 
        return pd.DataFrame()
    
    column_order = [
        'FID', 'Function', '外接矩形长_m', '外接矩形宽_m', '凸包面积_m^2', 
        '转角个数', '简化后点数', '原始点数', '原始面积_m^2', '原始周长_m'
    ]
    
    df = pd.DataFrame.from_dict(intermediate_results, orient='index')
    
    # 确保所有必需的列都存在
    for col in column_order:
        if col not in df.columns:
            df[col] = ''
    
    df = df[column_order]
    
    # 数值格式化
    num_cols = ['外接矩形长_m', '外接矩形宽_m', '凸包面积_m^2', 
                '转角个数', '简化后点数', '原始点数',
                '原始面积_m^2', '原始周长_m']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: f"{x:.6f}" if pd.notnull(x) else '')
    
    return df

def main():
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    
    if not json_files:
        print("未找到JSON文件！")
        return
    
    all_results = {}
    all_intermediate = {}
    total_residence_count = 0
    total_visualization_count = 0
    
    # 创建可视化输出目录
    viz_dir = 'polygon_visualizations'
    if os.path.exists(viz_dir):
        print(f"警告: {viz_dir} 目录已存在，将覆盖其中的图片")
    
    for json_file in json_files:
        print(f"\n处理文件: {json_file}")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'features' in data:
                results, intermediate = process_gis_json(data, json_file)
                all_results.update(results)
                all_intermediate.update(intermediate)
                total_residence_count += len(results)
                # 统计可视化数量
                for key in intermediate:
                    if '简化后点数' in intermediate[key]:
                        if intermediate[key]['简化后点数'] >= 3:
                            total_visualization_count += 1
            else:
                print(f"  - 警告: {json_file} 中没有找到 'features' 字段")
                
        except Exception as e:
            print(f"  - 错误: 处理文件 {json_file} 时出错: {e}")
    
    print(f"\n{'='*60}")
    print(f"处理完成！")
    print(f"总共找到 {len(json_files)} 个JSON文件")
    print(f"总共处理了 {total_residence_count} 个 Residence 类型建筑")
    print(f"总共生成了 {total_visualization_count} 个可视化PNG图片")
    print(f"图片保存在 '{viz_dir}' 目录中")
    print(f"{'='*60}")
    
    if all_results:
        # 输出最终结果表格
        df = create_summary_table(all_results)
        output_file = "建筑形态分析_Residence.xlsx"
        df.to_excel(output_file, index=False)
        
        # 输出中间信息表格
        df_intermediate = create_intermediate_table(all_intermediate)
        intermediate_file = "建筑形态中间信息_Residence.xlsx"
        df_intermediate.to_excel(intermediate_file, index=False)
        
        print(f"\n✓ 坐标转换完成！已导出以下文件：")
        print(f"  1. {output_file} (包含 {len(df)} 个 Residence 建筑)")
        print(f"  2. {intermediate_file}")
        print(f"  3. {total_visualization_count} 个PNG图片在 '{viz_dir}' 目录")
        
        # 显示部分结果
        print(f"\n前5个 Residence 建筑信息：")
        print(df.head().to_string())
    else:
        print("警告：未找到任何 Residence 类型的建筑！")

if __name__ == "__main__":
    main()