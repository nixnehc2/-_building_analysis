import json
import math
import os
import pandas as pd
from typing import Dict, List, Tuple

def calculate_polygon_area_and_perimeter(polygon_points, length_rate):
    """
    计算多边形面积和周长
    polygon_points: 多边形的顶点坐标列表，格式为[(x1, y1), (x2, y2), ...]
    length_rate: 缩放比例，毫米/像素
    """
    if len(polygon_points) < 3:
        return 0, 0
    
    length_rate_mm_per_px = float(length_rate.split()[0])

    # 转换坐标字符串为数值元组
    points = []
    for point_str in polygon_points:
        # 去除括号和引号，分割坐标
        coords = point_str.strip('()"').split(',')
        x = float(coords[0].strip())/length_rate_mm_per_px
        y = float(coords[1].strip())/length_rate_mm_per_px
        points.append((x, y))
    
    # 计算周长（像素单位）
    perimeter_px = 0
    n = len(points)
    
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        perimeter_px += distance

    # 计算面积（像素单位）使用鞋带公式
    area_px = 0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area_px += (x1 * y2 - x2 * y1)
    area_px = abs(area_px) / 2
    
    # 转换为实际尺寸（考虑缩放比例）
    # 注意：length_rate是毫米/像素，所以实际尺寸需要乘以length_rate
    
    # 转换为毫米
    perimeter_mm = perimeter_px * length_rate_mm_per_px
    area_mm2 = area_px * (length_rate_mm_per_px ** 2)
    
    # 转换为米（可选）
    perimeter_m = perimeter_mm / 1000
    area_m2 = area_mm2 / 1000000
    
    return perimeter_px, area_px, perimeter_mm, area_mm2, perimeter_m, area_m2

def process_json_data(json_data, filename: str) -> Dict:
    """
    处理JSON数据，计算边界图形的周长和面积
    返回一个字典，包含所有计算结果
    """
    all_results = {}
    
    for floor_key, floor_data in json_data.items():
        if floor_key.startswith('floor'):
            print(f"\n=== 处理 {floor_data['meta']['name']} (来自文件: {filename}) ===")
            
            # 获取边界数据和缩放比例
            boundary_polygon = floor_data['rooms']['边界'][0]
            length_rate = floor_data['meta']['lengthRate']
            
            # 计算
            perimeter_px, area_px, perimeter_mm, area_mm2, perimeter_m, area_m2 = calculate_polygon_area_and_perimeter(
                boundary_polygon, length_rate
            )
            
            # 创建唯一标识符（文件名 + 楼层）
            result_key = f"{os.path.splitext(filename)[0]}_{floor_key}"
            
            # 存储结果
            all_results[result_key] = {
                '文件名': filename,
                '楼层标识': floor_key,
                '楼层名称': floor_data['meta']['name'],
                '缩放比例': length_rate,
                '边界点数': len(boundary_polygon),
                '周长_px': perimeter_px,
                '面积_px²': area_px,
                '周长_mm': perimeter_mm,
                '面积_mm²': area_mm2,
                '周长_m': perimeter_m,
                '面积_m²': area_m2
            }
            
            # 打印结果
            print(f"缩放比例: {length_rate}")
            print(f"边界点数: {len(boundary_polygon)}")
            print(f"周长 (像素): {perimeter_px:.2f} px")
            print(f"面积 (像素): {area_px:.2f} px²")
            print(f"周长 (毫米): {perimeter_mm:.2f} mm")
            print(f"面积 (平方毫米): {area_mm2:.2f} mm²")
            print(f"周长 (米): {perimeter_m:.2f} m")
            print(f"面积 (平方米): {area_m2:.2f} m²")
    
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
    创建汇总表格
    """
    if not all_results:
        print("没有找到任何可处理的数据")
        return pd.DataFrame()
    
    # 转换为DataFrame
    df = pd.DataFrame.from_dict(all_results, orient='index')
    
    # 重置索引并重命名
    df = df.reset_index(drop=True)
    
    # 对数值列进行格式化，保留2位小数
    numeric_columns = ['周长_px', '面积_px²', '周长_mm', '面积_mm²', '周长_m', '面积_m²']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2f}")
    
    return df

def main():
    print("=== JSON文件批量处理工具 ===")
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
    
    for json_file in json_files:
        try:
            print(f"\n{'='*50}")
            print(f"正在处理文件: {json_file}")
            
            # 加载JSON数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理数据
            results = process_json_data(data, json_file)
            
            if results:
                all_results.update(results)
                print(f"✓ 文件 {json_file} 处理完成")
            else:
                print(f"⚠ 文件 {json_file} 没有找到有效的楼层数据")
                
        except json.JSONDecodeError as e:
            print(f"✗ 文件 {json_file} JSON格式错误: {e}")
        except KeyError as e:
            print(f"✗ 文件 {json_file} 缺少必要字段: {e}")
        except Exception as e:
            print(f"✗ 处理文件 {json_file} 时发生错误: {e}")
    
    print(f"\n{'='*50}")
    print("所有文件处理完成！")
    
    if not all_results:
        print("没有成功处理任何数据，无法生成表格。")
        return
    
    # 创建汇总表格
    print("\n正在生成汇总表格...")
    df = create_summary_table(all_results)
    
    # 显示表格基本信息
    print(f"\n表格形状: {df.shape[0]} 行 × {df.shape[1]} 列")
    print("\n表格预览:")
    print(df.head())
    
    # 保存为Excel文件
    excel_filename = "边界计算汇总.xlsx"
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"\n✓ 汇总表格已保存为: {excel_filename}")
    
    # 保存为CSV文件（可选）
    csv_filename = "边界计算汇总.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✓ 汇总表格已保存为: {csv_filename}")
    
    # 显示统计信息
    print("\n=== 统计信息 ===")
    print(f"总楼层数: {len(all_results)}")
    
    # 如果有面积数据，计算总面积
    if '面积_m²' in df.columns:
        total_area = df['面积_m²'].astype(float).sum()
        print(f"总面积 (平方米): {total_area:.2f} m²")
    
    print(f"\n表格包含以下列:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")

if __name__ == "__main__":
    main()