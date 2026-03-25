"""
批量处理流水线：修复 -> 简化 -> 可视化
保存三个阶段的图片：原始、修复后、简化后
"""

import json
import os
from typing import Optional
from shapely.geometry import Polygon

import matplotlib.pyplot as plt
import matplotlib

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 导入已有模块的函数
import caculate6
import draw1


def save_polygon_image(polygon: Polygon, filename: str, title: str = "多边形", output_dir: str = "data/images"):
    """
    保存多边形图片（不显示，只保存）
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    vertices = list(polygon.exterior.coords)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    x, y = polygon.exterior.xy
    ax.fill(x, y, alpha=0.3, color='skyblue', edgecolor='none')
    ax.plot(x, y, color='blue', linewidth=2)
    
    unique_vertices = vertices[:-1] if vertices[0] == vertices[-1] else vertices
    vx = [v[0] for v in unique_vertices]
    vy = [v[1] for v in unique_vertices]
    ax.scatter(vx, vy, color='red', s=50, zorder=5)
    
    all_x = [v[0] for v in vertices]
    all_y = [v[1] for v in vertices]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_margin = max((x_max - x_min) * 0.1, 0.1)
    y_margin = max((y_max - y_min) * 0.1, 0.1)
    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('X 坐标', fontsize=12)
    ax.set_ylabel('Y 坐标', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    info_text = f'顶点数: {len(unique_vertices)}\n面积: {polygon.area:.2f}\n周长: {polygon.length:.2f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    return filepath


def process_single_file(json_file: str, data_dir: str = "data", k_value: float = 30):
    """
    处理单个文件：原始 -> 修复 -> 简化，保存三个阶段的图片
    """
    basename = os.path.splitext(json_file)[0]
    output_dir = "data/images"
    
    # 读取原始JSON
    json_path = os.path.join(data_dir, json_file)
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 获取原始多边形
    boundary_polygon = json_data['floor1']['boundary']['边界'][0]
    length_rate = json_data['floor1']['meta']['lengthRate']
    length_rate_mm_per_px = float(length_rate.split()[0])
    
    # 1. 原始多边形
    original_polygon = caculate6.init(boundary_polygon, length_rate_mm_per_px)
    save_polygon_image(original_polygon, f"{basename}_1_original.png", f"{basename} - 原始", output_dir)
    print(f"  [1/3] 原始图片已保存")
    
    # 2. 修复后的多边形（使用 caculate6 的修复函数）
    repaired_polygon = caculate6.get_pro_polygon(original_polygon)
    save_polygon_image(repaired_polygon, f"{basename}_2_repaired.png", f"{basename} - 修复后", output_dir)
    print(f"  [2/3] 修复后图片已保存")
    
    # 保存修复后的JSON（供后续使用）
    caculate6.save_repaired_polygon(json_data, repaired_polygon, json_file)
    
    # 3. 简化后的多边形（使用 draw1 的简化函数）
    simplified_polygon = repaired_polygon.simplify(tolerance=k_value)
    simplified_polygon = Polygon(draw1.get_pro_polygon(simplified_polygon))
    simplified_polygon = draw1.simplify_polygon_by_angle(simplified_polygon)
    save_polygon_image(simplified_polygon, f"{basename}_3_simplified.png", f"{basename} - 简化后", output_dir)
    print(f"  [3/3] 简化后图片已保存")
    
    return original_polygon, repaired_polygon, simplified_polygon


def main():
    print("=" * 60)
    print("批量处理流水线：修复 -> 简化 -> 可视化")
    print("=" * 60)
    
    data_dir = "data"
    k_value = 30  # 简化阈值
    
    # 创建输出目录
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/repair", exist_ok=True)
    
    # 获取所有JSON文件
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    json_files.sort()
    
    if not json_files:
        print(f"在 {data_dir}/ 目录下未找到JSON文件！")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件")
    print(f"输出目录: data/images/")
    print(f"简化阈值 k = {k_value}")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] 处理: {json_file}")
        try:
            process_single_file(json_file, data_dir, k_value)
            success_count += 1
        except Exception as e:
            print(f"  错误: {e}")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"处理完成！成功: {success_count}, 失败: {fail_count}")
    print(f"图片保存在: data/images/")
    print(f"修复后JSON保存在: data/repair/")
    print("=" * 60)


if __name__ == "__main__":
    main()
