import json
import os
from typing import List, Tuple, Optional

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon


plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _parse_points_to_pixels(polygon_points: List[str], length_rate_mm_per_px: float) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for point_str in polygon_points:
        coords = point_str.strip('()"').split(",")
        if len(coords) < 2:
            continue
        x = float(coords[0].strip()) / length_rate_mm_per_px
        y = float(coords[1].strip()) / length_rate_mm_per_px
        points.append((x, y))
    return points


def visualize_polygon_direct(vertices: List[Tuple[float, float]], filename: Optional[str], output_dir: str) -> str:
    if not vertices:
        raise ValueError("顶点列表不能为空")

    if vertices[0] != vertices[-1]:
        vertices = vertices + [vertices[0]]

    polygon = Polygon(vertices)

    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))

    try:
        x, y = polygon.exterior.xy
    except Exception:
        arr = np.array(vertices)
        x, y = arr[:, 0], arr[:, 1]

    ax.fill(x, y, alpha=0.3, color="skyblue", edgecolor="none")
    ax.plot(x, y, color="blue", linewidth=2, marker="")

    unique_vertices = vertices[:-1] if vertices[0] == vertices[-1] else vertices
    vx = [v[0] for v in unique_vertices]
    vy = [v[1] for v in unique_vertices]
    ax.scatter(vx, vy, color="red", s=50, zorder=5)

    all_x = [v[0] for v in vertices]
    all_y = [v[1] for v in vertices]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_margin = max((x_max - x_min) * 0.1, 0.1)
    y_margin = max((y_max - y_min) * 0.1, 0.1)
    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)

    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_xlabel("X 坐标", fontsize=12)
    ax.set_ylabel("Y 坐标", fontsize=12)

    if filename is None:
        raise ValueError("filename 不能为空（需要保存图片）")
    if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".pdf", ".svg")):
        filename += ".png"

    full_path = os.path.join(output_dir, filename)
    plt.tight_layout()
    plt.savefig(full_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return full_path


def find_json_files(directory: str) -> List[str]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return []
    files = [f for f in os.listdir(directory) if f.lower().endswith(".json")]
    files.sort()
    return files


def draw_repair_jsons(data_dir: str = "data/repair", output_dir: str = "data/image") -> None:
    json_files = find_json_files(data_dir)
    if not json_files:
        print(f"在 {data_dir}/ 目录下未找到JSON文件！")
        return

    os.makedirs(output_dir, exist_ok=True)

    for json_file in json_files:
        json_path = os.path.join(data_dir, json_file)
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            boundary_polygon = data["floor1"]["boundary"]["边界"][0]
            length_rate = data["floor1"]["meta"]["lengthRate"]
            length_rate_mm_per_px = float(str(length_rate).split()[0])

            vertices = _parse_points_to_pixels(boundary_polygon, length_rate_mm_per_px)
            basename = os.path.splitext(json_file)[0]
            out_name = f"{basename}.png"
            saved = visualize_polygon_direct(vertices, out_name, output_dir)
            print(f"已保存: {saved}")
        except Exception as e:
            print(f"处理失败 {json_file}: {e}")


if __name__ == "__main__":
    draw_repair_jsons(data_dir="data/repair", output_dir="data/image")

