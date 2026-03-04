import json
import math
import os
import pandas as pd
from typing import Dict, List, Tuple
from shapely.geometry import Polygon
import numpy as np

def init(polygon_points, length_rate):
    """
    初始化多边形
    参数:
        polygon_points: 多边形顶点列表
        length_rate: 缩放比例字符串，如 "0.100 mm/pixel"
    返回:
        shapely Polygon对象
    """
    # 提取缩放比例数值
    length_rate_mm_per_px = float(length_rate.split()[0])
    points = []
    
    for point_str in polygon_points:
        # 去除括号和引号，分割坐标
        coords = point_str.strip('()"').split(',')
        x = float(coords[0].strip()) / length_rate_mm_per_px  # 像素单位
        y = float(coords[1].strip()) / length_rate_mm_per_px  # 像素单位
        points.append((x, y))
    
    polygon = Polygon(points)
    return polygon, length_rate_mm_per_px

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

def calculate_corner_density(polygon, angle_threshold=165):
    """
    计算建筑轮廓的转角密度
    
    参数:
        polygon: shapely Polygon对象
        angle_threshold: 有效转角的阈值角度（单位：度）
                        连续三个顶点形成的夹角 < 此值时认定为有效转角
    
    返回:
        corner_density: 转角密度（有效转角个数 / 周长，单位：个/米）
        num_effective_corners: 有效转角个数
    """
    # 获取多边形顶点（去掉最后一个重复点）
    coords = list(polygon.exterior.coords)[:-1]
    n = len(coords)
    
    if n < 3:
        return 0.0, 0
    
    # 计算周长
    perimeter = polygon.length
    
    # 计算有效转角个数
    effective_corners = 0
    
    for i in range(n):
        # 获取三个连续顶点：前一个点、当前点、下一个点
        p1 = np.array(coords[(i-1) % n])  # 前一个顶点
        p2 = np.array(coords[i])          # 当前顶点
        p3 = np.array(coords[(i+1) % n])  # 后一个顶点
        
        # 计算向量 p1->p2 和 p2->p3
        v1 = p2 - p1
        v2 = p3 - p2
        
        # 计算向量长度
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
        
        # 如果夹角 < 阈值，认为是有效转角
        if angle < angle_threshold:
            effective_corners += 1
    
    return effective_corners, perimeter

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

def process_json_data(json_data, filename: str) -> Dict:
    """
    处理JSON数据，计算边界图形的所有形态指标
    返回一个字典，包含所有计算结果
    """
    all_results = {}
    
    for floor_key, floor_data in json_data.items():
        if floor_key.startswith('floor'):
            print(f"\n=== 处理 {floor_data['meta']['name']} (来自文件: {filename}) ===")
            
            try:
                # 获取边界数据和缩放比例
                boundary_polygon = floor_data['boundary']['边界'][0]
                length_rate = floor_data['meta']['lengthRate']
                
                # 创建多边形并获取缩放比例
                polygon, length_rate_mm_per_px = init(boundary_polygon, length_rate)
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
                num_effective_corners, _ = calculate_corner_density(polygon)
                
                # 计算转角密度（有效转角数/周长，单位：个/米）
                corner_density = num_effective_corners / perimeter_m if perimeter_m > 0 else 0.0
                
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
                
                # 打印结果 - 简化输出，统一单位
                print(f"缩放比例: {length_rate}")
                print(f"边界点数: {len(boundary_polygon)}")
                print(f"周长: {perimeter_m:.6f} m")
                print(f"面积: {area_m:.6f} m²")
                print(f"长宽比: {aspect_ratio:.6f}")
                print(f"主方向角: {principal_angle:.6f}°")
                print(f"凹凸度: {concavity:.6f}")
                print(f"紧凑度: {compactness:.6f}")
                print(f"转角密度: {corner_density:.6f} 个/米")
                print(f"有效转角数: {num_effective_corners}")
                print(f"面积利用率: {area_utilization:.6f}")
                
            except KeyError as e:
                print(f"⚠ 缺少必要字段: {e}")
                continue
            except Exception as e:
                print(f"⚠ 处理楼层 {floor_key} 时出错: {e}")
                continue
    
    return all_results

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
        '主方向角_度', '转角密度_个每米'
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

def main():
    print("=== 建筑轮廓形态分析工具 ===")
    print("正在扫描当前目录下的JSON文件...")
    
    # 获取当前目录下的所有JSON文件
    json_files = find_json_files()
    
    if not json_files:
        print("在当前目录下未找到JSON文件！")
        print("请确保JSON文件与脚本在同一目录下。")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件:")
    for i, file in enumerate(json_files, 1):
        print(f"  {i}. {file}")
    
    # 处理所有JSON文件
    all_results = {}
    processed_files = 0
    
    for json_file in json_files:
        try:
            print(f"\n{'='*60}")
            print(f"正在处理文件: {json_file}")
            
            # 加载JSON数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理数据
            results = process_json_data(data, json_file)
            
            if results:
                all_results.update(results)
                processed_files += 1
                print(f"✓ 文件 {json_file} 处理完成")
            else:
                print(f"⚠ 文件 {json_file} 没有找到有效的楼层数据")
                
        except json.JSONDecodeError as e:
            print(f"✗ 文件 {json_file} JSON格式错误: {e}")
        except Exception as e:
            print(f"✗ 处理文件 {json_file} 时发生错误: {e}")
    
    print(f"\n{'='*60}")
    print(f"处理完成！成功处理 {processed_files}/{len(json_files)} 个文件")
    
    if not all_results:
        print("没有成功处理任何数据，无法生成表格。")
        return
    
    # 创建汇总表格
    print("\n正在生成汇总表格...")
    df = create_summary_table(all_results)
    
    # 显示表格基本信息
    print(f"\n表格形状: {df.shape[0]} 行 × {df.shape[1]} 列")
    print("\n表格前5行预览:")
    print(df.head())
    
    # 保存为Excel文件
    excel_filename = "建筑轮廓形态分析汇总.xlsx"
    try:
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        print(f"\n✓ 汇总表格已保存为: {excel_filename}")
    except Exception as e:
        print(f"✗ 保存Excel文件失败: {e}")
        # 尝试保存为CSV
        excel_filename = "建筑轮廓形态分析汇总.csv"
        df.to_csv(excel_filename, index=False, encoding='utf-8-sig')
        print(f"✓ 汇总表格已保存为CSV: {excel_filename}")
    
    # 保存为CSV文件
    csv_filename = "建筑轮廓形态分析汇总.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✓ 汇总表格已保存为: {csv_filename}")
    
    # 显示统计信息
    print("\n=== 统计信息 ===")
    print(f"总楼层数: {len(all_results)}")
    
    # 计算总面积
    if '面积_m²' in df.columns:
        # 注意：需要将格式化后的字符串转回数值
        area_values = pd.to_numeric(df['面积_m²'].replace('', np.nan), errors='coerce')
        total_area = area_values.sum()
        print(f"总面积: {total_area:.6f} m²")
    
    # 形态指标统计
    print(f"\n形态指标统计（保留6位小数）:")
    
    # 长宽比统计
    if '长宽比' in df.columns:
        aspect_ratios = pd.to_numeric(df['长宽比'].replace('', np.nan), errors='coerce')
        if len(aspect_ratios.dropna()) > 0:
            print(f"  长宽比:")
            print(f"    范围: {aspect_ratios.min():.6f} - {aspect_ratios.max():.6f}")
            print(f"    平均值: {aspect_ratios.mean():.6f}")
            print(f"    中位数: {aspect_ratios.median():.6f}")
    
    # 凹凸度统计
    if '凹凸度' in df.columns:
        concavities = pd.to_numeric(df['凹凸度'].replace('', np.nan), errors='coerce')
        if len(concavities.dropna()) > 0:
            print(f"\n  凹凸度:")
            print(f"    范围: {concavities.min():.6f} - {concavities.max():.6f}")
            print(f"    平均值: {concavities.mean():.6f}")
            print(f"    中位数: {concavities.median():.6f}")
    
    # 紧凑度统计
    if '紧凑度' in df.columns:
        compactness_values = pd.to_numeric(df['紧凑度'].replace('', np.nan), errors='coerce')
        if len(compactness_values.dropna()) > 0:
            print(f"\n  紧凑度:")
            print(f"    范围: {compactness_values.min():.6f} - {compactness_values.max():.6f}")
            print(f"    平均值: {compactness_values.mean():.6f}")
            print(f"    中位数: {compactness_values.median():.6f}")
    
    # 转角密度统计
    if '转角密度_个每米' in df.columns:
        corner_densities = pd.to_numeric(df['转角密度_个每米'].replace('', np.nan), errors='coerce')
        if len(corner_densities.dropna()) > 0:
            print(f"\n  转角密度 (个/米):")
            print(f"    范围: {corner_densities.min():.6f} - {corner_densities.max():.6f}")
            print(f"    平均值: {corner_densities.mean():.6f}")
            print(f"    中位数: {corner_densities.median():.6f}")
    
    print(f"\n表格包含以下{len(df.columns)}列指标:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    # 生成指标说明文件
    generate_metrics_explanation()

def generate_metrics_explanation():
    """生成指标说明文件"""
    explanation = """建筑轮廓形态指标说明
====================

所有指标均以米(m)为单位，保留6位小数。

基础几何指标：
1. 周长_m: 建筑轮廓边界的总长度（米）
2. 面积_m²: 建筑轮廓在二维平面上的投影面积（平方米）
3. 凸包面积_m²: 能够完全包住该轮廓的最小凸多边形的面积（平方米）
4. 最小矩形面积_m²: 能够完全包住该轮廓的最小外接矩形的面积（平方米）

形态指标：
1. 长宽比: 最小外接矩形的长边与短边之比，反映建筑轮廓的整体形状比例
   - 值≥1，越接近1表示越接近正方形
   - 保留6位小数
   
2. 主方向角_度: 最小外接矩形长边的朝向角度（与正东方向的夹角）
   - 范围：0-180度
   - 0度：正东方向，90度：正北方向
   - 保留6位小数
   
3. 凹凸度: 建筑轮廓面积与凸包面积的比值，描述轮廓边界的凹陷或突起程度
   - 范围：0-1，越接近1表示形状越凸，值越小表示内凹越严重
   - 保留6位小数
   
4. 紧凑度: 衡量建筑轮廓形状是否紧凑、边界是否简洁的指标
   - 公式: (4 * π * 面积) / (周长²)
   - 范围：0-1，越接近1表示形状越接近圆形（越紧凑）
   - 保留6位小数
   
5. 转角密度_个每米: 建筑外轮廓有效转角个数与周长的比值（单位：个/米）
   - 有效转角定义：连续三个顶点形成的夹角＜165°时，认定为有效转角
   - 值越大表示转角越多，轮廓越复杂
   - 保留6位小数
   
6. 有效转角数: 建筑轮廓中有效转角的数量
   - 整数值

衍生指标：
1. 面积利用率: 建筑轮廓面积与最小外接矩形面积的比值
   - 反映建筑对矩形空间的利用效率
   - 保留6位小数
   
2. 凸性指标: 建筑轮廓面积与凸包面积的比值（同凹凸度）
   - 保留6位小数

注意：
- 所有长度和面积指标均已转换为国际单位制（米，平方米）
- 转角密度单位为"个/米"，表示每米周长有多少个有效转角
- 建议使用6位小数进行精确比较和分析
"""
    
    with open("指标说明.txt", "w", encoding="utf-8") as f:
        f.write(explanation)
    print(f"\n✓ 指标说明已保存至: 指标说明.txt")

if __name__ == "__main__":
    main()