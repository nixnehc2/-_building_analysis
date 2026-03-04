import json
import math
import os
import pandas as pd
from typing import Dict
from shapely.geometry import Polygon
import numpy as np
from pyproj import Transformer

# 初始化坐标转换器：从 3857 (Web墨卡托) 转到 4507 (CGCS2000 南京所在分带平面坐标)
# always_xy=True 确保输入输出均为 [东经/X, 北纬/Y]
transformer = Transformer.from_crs("epsg:3857", "epsg:4507", always_xy=True)

# 如果需要转换改这里，目前未转换
def init_gis_polygon(rings):
    """
    将 GIS 的 rings 转换为经 pyproj 转换后的 Shapely 多边形
    """
    shell = rings[0]
    # 使用 pyproj 将每一个点从 3857 转为 4507 (单位：米)
    transformed_shell = [(pt[0], pt[1]) for pt in shell]
    return Polygon(transformed_shell)

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
    
    print(f"正在转换并处理: {filename}...")

    for feat in features:
        try:
            attr = feat.get('attributes', {})
            geom = feat.get('geometry', {})
            fid = attr.get('FID', 'Unknown')
            
            if 'rings' not in geom: continue
            
            # 这里的 polygon 已经是转换后的 CGCS2000 投影坐标（单位：米）
            polygon = init_gis_polygon(geom['rings'])
            if polygon.area <= 0: continue

            # 基础几何计算
            rect = polygon.minimum_rotated_rectangle
            convex_hull = polygon.convex_hull
            
            # 由于已经是平面坐标，直接计算即为真实米制单位
            area_m2 = polygon.area 
            perimeter_m = polygon.length
            aspect_ratio, principal_angle = calculate_rect(rect)
            num_corners = calculate_corner_density(polygon)
            
            # 转角密度（个/米）
            corner_density = num_corners / perimeter_m if perimeter_m > 0 else 0
            
            # 紧凑度与凹凸度
            compactness = (4 * math.pi * area_m2) / (perimeter_m ** 2) if perimeter_m > 0 else 0
            concavity = area_m2 / convex_hull.area if convex_hull.area > 0 else 0
            
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
                '转交密度_个': corner_density
            }

        except Exception as e:
            continue
            
    return all_results

def create_summary_table(all_results: Dict) -> pd.DataFrame:
    if not all_results: return pd.DataFrame()
    
    column_order = [
        'FID', '建筑高度', '建筑年份', '周长_m', '面积_m^2', 
        '长宽比', '主方向角_度', '凹凸度', '紧凑度', '转交密度_个'
    ]
    
    df = pd.DataFrame.from_dict(all_results, orient='index')
    df = df[column_order]
    
    # 数值格式化
    num_cols = ['周长_m', '面积_m^2', '长宽比', '主方向角_度', '凹凸度', '紧凑度', '转交密度_个']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').map(lambda x: f"{x:.6f}")
        
    return df

def main():
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    all_results = {}
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'features' in data:
            all_results.update(process_gis_json(data, json_file))

    if all_results:
        df = create_summary_table(all_results)
        df.to_excel("建筑形态分析_CGCS2000版.xlsx", index=False)
        print(f"\n✓ 坐标转换完成！已导出高精度 CGCS2000 数据。")

if __name__ == "__main__":
    main()