"""
预览单个 Esri Polygon JSON 中的多边形。
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import Polygon as ShapelyPolygon

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _rings_to_shapely(rings: List) -> ShapelyPolygon:
    if not rings:
        raise ValueError("empty rings")
    ext = list(rings[0])
    holes = [list(h) for h in rings[1:]] if len(rings) > 1 else []
    return ShapelyPolygon(ext, holes)


def _patches_from_feature(
    rings: List, facecolor: Tuple[float, float, float, float], edgecolor: str, lw: float
) -> List[MplPolygon]:
    poly = _rings_to_shapely(rings)
    if poly.is_empty:
        return []
    patches: List[MplPolygon] = []
    xy = np.array(poly.exterior.coords)
    patches.append(
        MplPolygon(
            xy,
            closed=True,
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=lw,
        )
    )
    for hole in poly.interiors:
        h = np.array(hole.coords)
        patches.append(
            MplPolygon(
                h,
                closed=True,
                facecolor=(1, 1, 1, 1),
                edgecolor=edgecolor,
                linewidth=lw * 0.8,
            )
        )
    return patches


def _collect_bounds(data: Dict[str, Any]) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    for f in data.get("features") or []:
        geom = f.get("geometry") or {}
        for ring in geom.get("rings") or []:
            for x, y in ring:
                xs.append(float(x))
                ys.append(float(y))
    if not xs:
        return (0.0, 1.0, 0.0, 1.0)
    pad_x = (max(xs) - min(xs)) * 0.02 + 1e-6
    pad_y = (max(ys) - min(ys)) * 0.02 + 1e-6
    return (min(xs) - pad_x, max(xs) + pad_x, min(ys) - pad_y, max(ys) + pad_y)


def plot_esri_json(
    path_json: str,
    out_path: str | None,
    show: bool,
    dpi: int,
    title: str | None = None,
) -> None:
    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    n = len(data.get("features") or [])
    fig, ax = plt.subplots(figsize=(10, 8), facecolor="white")

    if hasattr(matplotlib, "colormaps"):
        cmap = matplotlib.colormaps["tab20"]
    else:
        cmap = plt.cm.get_cmap("tab20")

    patches_all: List[MplPolygon] = []
    for i, feat in enumerate(data.get("features") or []):
        rings = (feat.get("geometry") or {}).get("rings") or []
        if not rings:
            continue
        c = cmap(i % 20 / 19.0)
        rgba = (c[0], c[1], c[2], 0.45)
        try:
            patches_all.extend(
                _patches_from_feature(rings, rgba, edgecolor=c[:3], lw=0.6)
            )
        except Exception:
            continue
    for p in patches_all:
        ax.add_patch(p)

    x0, x1, y0, y1 = _collect_bounds(data)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)
    ax.set_xlabel("经度")
    ax.set_ylabel("纬度")

    if title is None:
        base = os.path.basename(path_json)
        title = f"{base}（{n} 个要素）"
    ax.set_title(title, fontsize=13)

    plt.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
        print(f"已保存: {os.path.abspath(out_path)}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="预览单个 Esri JSON 多边形")
    parser.add_argument(
        "input",
        nargs="?",
        default=os.path.join(here, "example1.json"),
        help="输入 JSON 路径",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join(here, "preview_gis.png"),
        help="输出图片路径（默认 preview_gis.png）",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="图标题（默认：文件名 + 要素数）",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存文件，仅弹窗显示（需图形界面）",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="显示交互窗口（可与 -o 同时用：既保存又显示）",
    )
    parser.add_argument("--dpi", type=int, default=160, help="保存分辨率")
    args = parser.parse_args()

    out = None if args.no_save else args.output
    show = args.show or args.no_save

    plot_esri_json(
        args.input,
        out_path=out,
        show=show,
        dpi=args.dpi,
        title=args.title,
    )


if __name__ == "__main__":
    main()
