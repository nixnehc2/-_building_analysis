"""
合并被同一直线切开的多边形：根据跨多边形临近点对中「两端重合」对数是否小于阈值判断是否合并，
并输出同结构的 Esri JSON。
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from typing import Any, Dict, List, Sequence, Tuple

from shapely.geometry import Polygon
from shapely.ops import unary_union

try:
    from shapely import make_valid
except ImportError:  # 旧版 shapely
    make_valid = None  # type: ignore[misc, assignment]

Point2 = Tuple[float, float]
Ring = List[Point2]

# 默认容差（度）：约 1e-5° 纬度 ~1.1m；可按数据分辨率调整
DEFAULT_ADJACENCY_TOL = 1e-8
DEFAULT_COLLINEAR_TOL = 1e-7
# 重合点对数阈值：临近点对中两端距离 ≤ collinear_tol 的对数若 < 该值则合并，否则不合并
COINCIDENT_PAIR_COUNT_THRESHOLD = 8


def dist2(a: Point2, b: Point2) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def count_coincident_point_pairs(
    pairs: Sequence[Tuple[Point2, Point2]], tol: float
) -> int:
    """统计点对 (p,q) 中两端点在容差内重合（视为同一点）的对数。"""
    tol2 = tol * tol
    n = 0
    for p, q in pairs:
        if dist2(p, q) <= tol2:
            n += 1
    return n


def collect_adjacency_pairs(
    polygon_rings: List[Sequence[Ring]],
    adj_tol: float,
    *,
    verbose: bool = False,
) -> Dict[Tuple[int, int], List[Tuple[Point2, Point2]]]:
    """
    步骤 1：对无序对 (min(i,j), max(i,j))，收集所有跨多边形的临近点对 (x,y)，
    x 属于 i，y 属于 j。

    实现：枚举全部顶点并建立平面均匀网格；对每个点只在其周围若干格内查找异多边形的点，
    避免 O(多边形对 × 顶点²) 的枚举。格边长取 adj_tol；邻域取 Chebyshev 距离 ≤2 的格子
    （5×5），以保证距离 ≤ adj_tol 的点对必落在某一邻格对中。
    """
    if adj_tol <= 0:
        raise ValueError("adj_tol must be positive")

    cell = adj_tol
    adj_tol2 = adj_tol * adj_tol

    # (x, y, poly_id, global_index)，global_index 用于无序点对只统计一次
    points: List[Tuple[float, float, int, int]] = []
    g = 0
    for pid, rings in enumerate(polygon_rings):
        for ring in rings:
            for x, y in ring:
                points.append((float(x), float(y), pid, g))
                g += 1

    def cell_key(x: float, y: float) -> Tuple[int, int]:
        return (math.floor(x / cell), math.floor(y / cell))

    grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for i, (x, y, _, _) in enumerate(points):
        grid[cell_key(x, y)].append(i)

    with open("debug.txt", "w", encoding="utf-8") as f:
        f.write(str(points))

    pairs_map: Dict[Tuple[int, int], List[Tuple[Point2, Point2]]] = defaultdict(list)

    n_pts = len(points)
    step = max(1, n_pts // 20) if n_pts > 0 else 1
    for ia, (xa, ya, pa, _) in enumerate(points):
        if verbose and n_pts > 0 and (ia + 1 == n_pts or (ia + 1) % step == 0):
            print(
                f"[2/4] 网格扫描临近点对：顶点 {ia + 1}/{n_pts}",
                flush=True,
            )
        cx, cy = cell_key(xa, ya)
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                for ib in grid.get((cx + dx, cy + dy), ()):
                    if ib <= ia:
                        continue
                    xb, yb, pb, _ = points[ib]
                    if pa == pb:
                        continue
                    if (xa - xb) ** 2 + (ya - yb) ** 2 > adj_tol2:
                        continue
                    if pa < pb:
                        pairs_map[(pa, pb)].append(((xa, ya), (xb, yb)))
                    else:
                        pairs_map[(pb, pa)].append(((xb, yb), (xa, ya)))

    with open("debug.txt", "w", encoding="utf-8") as f:
        f.write(f"pairs_map: {pairs_map}\n")

    return pairs_map


def pairs_collinear_ok(
    pairs: Sequence[Tuple[Point2, Point2]], collinear_tol: float
) -> bool:
    """
    步骤 2：统计临近点对中「两端重合」（距离 ≤ collinear_tol）的对数。
    若该对数 < COINCIDENT_PAIR_COUNT_THRESHOLD 则判定为可合并，否则不合并。
    """
    if not pairs:
        return False
    c = count_coincident_point_pairs(pairs, collinear_tol)
    return c < COINCIDENT_PAIR_COUNT_THRESHOLD


def _fix_polygon(g: Polygon) -> Polygon:
    if g.is_empty:
        return g
    if g.is_valid:
        return g
    if make_valid is not None:
        fixed = make_valid(g)
        if fixed.geom_type == "Polygon":
            return fixed  # type: ignore[return-value]
        if fixed.geom_type == "MultiPolygon":
            return max(fixed.geoms, key=lambda x: x.area)  # type: ignore[return-value]
        if fixed.geom_type == "GeometryCollection":
            polys = [x for x in fixed.geoms if x.geom_type == "Polygon" and not x.is_empty]
            if polys:
                return max(polys, key=lambda x: x.area)
    buf = g.buffer(0)
    if buf.geom_type == "Polygon":
        return buf  # type: ignore[return-value]
    if buf.geom_type == "MultiPolygon":
        return max(buf.geoms, key=lambda x: x.area)  # type: ignore[return-value]
    return g


def rings_to_polygon(rings: Sequence[Ring]) -> Polygon:
    if not rings:
        raise ValueError("empty rings")
    exterior = list(rings[0])
    holes = [list(h) for h in rings[1:]] if len(rings) > 1 else []
    p = Polygon(exterior, holes)
    return _fix_polygon(p)


def polygon_to_rings(poly: Polygon) -> List[Ring]:
    if poly.is_empty:
        return []
    rings: List[Ring] = [list(poly.exterior.coords)]
    for hole in poly.interiors:
        rings.append(list(hole.coords))
    return rings


def merge_geometries(geoms: List[Polygon]) -> Polygon:
    fixed = [_fix_polygon(g) for g in geoms if not g.is_empty]
    if not fixed:
        raise ValueError("empty geometry list")
    if len(fixed) == 1:
        return fixed[0]
    try:
        u = unary_union(fixed)
    except Exception:
        u = unary_union([f.buffer(0) for f in fixed])
    if u.geom_type == "Polygon":
        p = u
    elif u.geom_type == "MultiPolygon":
        p = max(u.geoms, key=lambda g: g.area)
    else:
        raise ValueError(f"unexpected union result: {u.geom_type}")
    if not p.is_valid:
        p = _fix_polygon(p)
    return p  # type: ignore[return-value]


class UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            self.p[ra] = rb
        elif self.r[ra] > self.r[rb]:
            self.p[rb] = ra
        else:
            self.p[rb] = ra
            self.r[ra] += 1


def repair_gis(
    data: Dict[str, Any],
    adjacency_tol: float = DEFAULT_ADJACENCY_TOL,
    collinear_tol: float = DEFAULT_COLLINEAR_TOL,
    *,
    verbose: bool = False,
) -> Dict[str, Any]:
    if verbose:
        print("[1/4] 解析要素并整理多边形环 …", flush=True)

    features: List[Dict[str, Any]] = data.get("features") or []
    polygon_rings: List[Sequence[Ring]] = []
    for f in features:
        geom = f.get("geometry") or {}
        rings = geom.get("rings") or []
        polygon_rings.append(rings)

    n = len(polygon_rings)
    if verbose:
        print(f"[1/4] 完成：共 {n} 个多边形要素。", flush=True)
        print("[2/4] 收集跨多边形临近点对（均匀网格）…", flush=True)

    pairs_map = collect_adjacency_pairs(
        polygon_rings, adjacency_tol, verbose=verbose
    )

    if verbose:
        n_poly_pairs = sum(1 for pl in pairs_map.values() if pl)
        n_keys = len(pairs_map)
        print(
            f"[2/4] 完成：无序多边形对 {n_keys} 组（其中非空临近点对 {n_poly_pairs} 组）。",
            flush=True,
        )
        print("[3/4] 逐对判定是否合并（重合点对数规则）…", flush=True)

    uf = UnionFind(n)
    pair_items = [(k, v) for k, v in pairs_map.items() if v]
    total_pairs = len(pair_items)
    step_p = max(1, total_pairs // 40) if total_pairs > 0 else 1
    for done, ((i, j), plist) in enumerate(pair_items, start=1):
        if verbose and total_pairs > 0 and (
            done == total_pairs or done % step_p == 0
        ):
            print(
                f"[3/4] 多边形对进度 {done}/{total_pairs}（当前 ({i},{j})）",
                flush=True,
            )
        if pairs_collinear_ok(plist, collinear_tol):
            uf.union(i, j)

    if verbose:
        print("[3/4] 判定与并查集合并完成。", flush=True)
        print("[4/4] 合并几何并生成输出要素 …", flush=True)

    # 按连通分量合并几何与属性
    components: Dict[int, List[int]] = defaultdict(list)
    for idx in range(n):
        components[uf.find(idx)].append(idx)

    new_features: List[Dict[str, Any]] = []
    new_fid = 0
    n_comp = len(components)
    for comp_i, root in enumerate(sorted(components.keys()), start=1):
        members = sorted(components[root])
        # 属性：取该组中最小原始 FID 对应的那条
        def sort_key(k: int) -> Any:
            attrs = features[k].get("attributes") or {}
            fid = attrs.get("FID", k)
            return fid

        rep = min(members, key=sort_key)
        base_attrs = json.loads(json.dumps(features[rep]["attributes"]))

        polys: List[Polygon] = []
        for k in members:
            rings = polygon_rings[k]
            if not rings:
                continue
            try:
                polys.append(rings_to_polygon(rings))  # type: ignore[arg-type]
            except Exception:
                continue
        if not polys:
            continue

        merged = merge_geometries(polys)
        new_rings = polygon_to_rings(merged)
        base_attrs["FID"] = new_fid
        new_features.append(
            {
                "attributes": base_attrs,
                "geometry": {"rings": new_rings},
            }
        )
        new_fid += 1
        if verbose and n_comp > 0 and (
            comp_i == n_comp or comp_i % max(1, n_comp // 20) == 0
        ):
            print(
                f"[4/4] 合并几何进度 {comp_i}/{n_comp} 个连通分量 …",
                flush=True,
            )

    if verbose:
        print("[4/4] 完成。", flush=True)

    out = json.loads(json.dumps(data))
    out["features"] = new_features
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="合并被直线切开的多边形（Esri JSON）")
    parser.add_argument("input", nargs="?", default="example1.json", help="输入 JSON 路径")
    parser.add_argument("-o", "--output", default="example1_merged.json", help="输出 JSON 路径")
    parser.add_argument(
        "--adj-tol",
        type=float,
        default=DEFAULT_ADJACENCY_TOL,
        help="临近判定距离（度），默认 %(default)s",
    )
    parser.add_argument(
        "--collinear-tol",
        type=float,
        default=DEFAULT_COLLINEAR_TOL,
        help=(
            "两端点「重合」判定距离（度）；重合对数≥"
            + str(COINCIDENT_PAIR_COUNT_THRESHOLD)
            + " 则不合并，默认 %(default)s"
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="不输出步骤与进度信息",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged = repair_gis(
        data,
        adjacency_tol=args.adj_tol,
        collinear_tol=args.collinear_tol,
        verbose=not args.quiet,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(
        f"输入要素数: {len(data.get('features') or [])}, "
        f"输出要素数: {len(merged.get('features') or [])}, 已写入 {args.output}"
    )


if __name__ == "__main__":
    main()
