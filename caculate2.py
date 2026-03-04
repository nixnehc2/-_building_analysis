import json
import math
import os
import pandas as pd
from typing import Dict, List
from shapely.geometry import Polygon
import numpy as np

def init_gis_polygon(rings):
    """将 GIS 的 rings 转换为 Shapely 多边形"""
    # 取第一个环（外环）
    shell = rings[0]
    return Polygon(shell)

def calculate_rect(rect_polygon): 
    """计算矩形长宽比和长边方向角"""
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
    
    unique_lengths = sorted(set(round(l, 6) for l in sides))
    if len(unique_lengths) == 1:
        aspect_ratio = 1.0
        dx, dy = vectors[0]
    else:
        aspect_ratio = max(unique_lengths) / min(unique_lengths)
        long_side_idx = sides.index(max(sides))
        dx, dy = vectors[long_side_idx]
    
    angle = np.degrees(np.arctan2(dy, dx)) % 180
    return aspect_ratio, angle

def calculate_corner_density(polygon, angle_threshold=165):
    """计算转角数量"""
    coords = list(polygon.exterior.coords)[:-1]
    n = len(coords)
    if n < 3: return 0
    
    effective_corners = 0
    for i in range(n):
        p1, p2, p3 = np.array(coords[i-1]), np.array(coords[i]), np.array(coords[(i+1)%n])
        v1, v2 = p2 - p1, p3 - p2
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 == 0 or n2 == 0: continue
        cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        if np.degrees(np.arccos(cos_angle)) < angle_threshold:
            effective_corners += 1
    return effective_corners

def process_gis_json(json_data, filename: str) -> Dict:
    """处理 GIS 格式数据并提取指定字段"""
    all_results = {}
    features = json_data.get('features', [])
    
    # 南京纬度投影修正（Web墨卡托转真实米）
    lat_nanjing = 32.0
    cos_lat = math.cos(math.radians(lat_nanjing))

    # 不进行转换
    cos_lat=1

    area_correction = cos_lat ** 2
    dist_correction = cos_lat

    for feat in features:
        try:
            attr = feat.get('attributes', {})
            geom = feat.get('geometry', {})
            fid = attr.get('FID', 'Unknown')
            
            if 'rings' not in geom: continue
            
            polygon = init_gis_polygon(geom['rings'])
            if polygon.area <= 0: continue

            # 基础几何计算
            rect = polygon.minimum_rotated_rectangle
            convex_hull = polygon.convex_hull
            
            # 指标计算
            area_m2 = polygon.area * area_correction
            perimeter_m = polygon.length * dist_correction
            aspect_ratio, principal_angle = calculate_rect(rect)
            num_corners = calculate_corner_density(polygon)
            # 转角密度（个/米）
            corner_density = num_corners / perimeter_m if perimeter_m > 0 else 0
            
            # 紧凑度与凹凸度
            compactness = polygon.area / rect.area if rect.area > 0 else 0
            concavity = polygon.area / convex_hull.area if convex_hull.area > 0 else 0
            
            result_key = f"{filename}_{fid}"
            all_results[result_key] = {
                'FID': fid,
                '建筑高度': attr.get('Height', 0),
                '建筑年份': attr.get('Age', 'N/A'),
                '周长_m': perimeter_m,
                '面积_m^2': area_m2,
                '长宽比': aspect_ratio,
                '主方向角_度': principal_angle,
                '凹凸度': concavity,
                '紧凑度': compactness,
                '转交密度_个': corner_density # 按要求命名
            }

        except Exception:
            continue
            
    return all_results

def create_summary_table(all_results: Dict) -> pd.DataFrame:
    if not all_results: return pd.DataFrame()
    
    # 严格定义列顺序
    column_order = [
        'FID', '建筑高度', '建筑年份', '周长_m', '面积_m^2', 
        '长宽比', '主方向角_度', '凹凸度', '紧凑度', '转交密度_个'
    ]
    
    df = pd.DataFrame.from_dict(all_results, orient='index')
    
    # 仅保留并排序
    df = df[column_order]
    
    # 数值格式化：保留6位小数
    num_cols = ['周长_m', '面积_m^2', '长宽比', '主方向角_度', '凹凸度', '紧凑度', '转交密度_个']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').map(lambda x: f"{x:.6f}")
        
    return df

def main():
    print("正在处理建筑形态数据...")
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建数据目录: {data_dir}/")
    
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not json_files:
        print(f"在 {data_dir}/ 目录下未找到JSON文件！")
        print(f"请将JSON文件放入 {data_dir}/ 目录。")
        return
    
    all_results = {}
    for json_file in json_files:
        try:
            json_path = os.path.join(data_dir, json_file)
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'features' in data:
                results = process_gis_json(data, json_file)
                all_results.update(results)
        except Exception as e:
            print(f"处理 {json_file} 时出错: {e}")

    if all_results:
        df = create_summary_table(all_results)
        output_name = "建筑形态分析精简版.xlsx"
        df.to_excel(output_name, index=False)
        print(f"✓ 处理完成！结果已存入: {output_name}")
    else:
        print("未发现有效数据。")

if __name__ == "__main__":
    main()