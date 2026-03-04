# 建筑轮廓形态分析工具集

本项目包含一系列用于建筑轮廓形态分析的 Python 脚本，主要用于从 JSON 数据中提取建筑边界信息，计算各种形态指标，并进行数据处理和可视化。

## 环境依赖

```bash
pip install pandas numpy shapely openpyxl pyproj matplotlib
```

---

## 快速开始

### 第一步：准备数据文件

将 JSON 文件放入 **`data/`** 文件夹中。如果文件夹不存在，程序会自动创建。

### 第二步：运行程序

```bash
python caculate1.py
```

### 第三步：查看输出

输出文件会生成在**脚本所在目录**下（与 `data/` 同级）。

---

## 数据格式说明

本工具集支持两种 JSON 数据格式：

### 格式一：户型图数据

适用于：`caculate.py`, `caculate1.py`, `caculate4.py`, `caculate6.py`, `draw1.py`

```json
{
  "floor1": {
    "meta": {
      "name": "1F",
      "lengthRate": "0.100 mm/pixel"
    },
    "boundary": {
      "边界": [["(100.5,200.3)", "(150.2,200.3)", "(150.2,300.1)", ...]]
    },
    "rooms": {
      "客厅": [["(x1,y1)", "(x2,y2)", ...]],
      "卧室": [["(x1,y1)", "(x2,y2)", ...]]
    },
    "doors": {
      "门1": [["(x1,y1)", "(x2,y2)", ...]]
    }
  }
}
```

### 格式二：GIS 数据

适用于：`caculate2.py`, `caculate3.py`, `caculate5.py`

```json
{
  "features": [
    {
      "attributes": {
        "FID": 1,
        "Height": 10.5,
        "Age": 2000,
        "Function": "Residence"
      },
      "geometry": {
        "rings": [[[13358000.5, 3756000.2], [13358100.3, 3756000.2], ...]]
      }
    }
  ]
}
```

---

## 目录结构

```
dachuang/
├── caculate.py
├── caculate1.py
├── caculate2.py
├── caculate3.py
├── caculate4.py
├── caculate5.py
├── caculate6.py
├── draw1.py
├── README.md
│
├── data/                          # ← 【输入】所有JSON文件放这里
│   ├── 户型1.json
│   ├── 户型2.json
│   ├── building_data.json
│   └── repair/                    # ← caculate6.py输出 / draw1.py输入
│       ├── 户型1_1.json
│       └── 户型1_result.jpg
│
├── 边界计算汇总.xlsx               # ← 【输出】caculate.py
├── 建筑轮廓形态分析汇总.xlsx        # ← 【输出】caculate1.py
├── 建筑形态分析精简版.xlsx          # ← 【输出】caculate2.py
├── 建筑形态分析_CGCS2000版.xlsx    # ← 【输出】caculate3.py
├── 建筑形态分析_Residence.xlsx     # ← 【输出】caculate5.py
└── polygon_visualizations/        # ← 【输出】caculate5.py 可视化图片
    ├── FID_1.png
    └── FID_2.png
```

---

## 各程序详细说明

### 1. caculate.py - 基础边界计算工具

| 项目 | 说明 |
|------|------|
| **功能** | 计算建筑边界的周长和面积（支持多单位） |
| **输入格式** | 户型图 JSON |
| **输入位置** | `data/` |
| **输出文件** | `边界计算汇总.xlsx`、`边界计算汇总.csv` |
| **输出位置** | 脚本所在目录 |

```bash
python caculate.py
```

---

### 2. caculate1.py - 完整形态分析工具

| 项目 | 说明 |
|------|------|
| **功能** | 全面的建筑轮廓形态分析 |
| **输入格式** | 户型图 JSON |
| **输入位置** | `data/` |
| **输出文件** | `建筑轮廓形态分析汇总.xlsx`、`.csv`、`指标说明.txt` |
| **输出位置** | 脚本所在目录 |

```bash
python caculate1.py
```

**输出指标**：周长、面积、凸包面积、最小矩形面积、长宽比、主方向角、凹凸度、紧凑度、转角密度、面积利用率

---

### 3. caculate2.py - GIS 数据处理工具（简化版）

| 项目 | 说明 |
|------|------|
| **功能** | 处理 GIS 格式数据，计算建筑形态指标 |
| **输入格式** | GIS JSON（含 features 数组） |
| **输入位置** | `data/` |
| **输出文件** | `建筑形态分析精简版.xlsx` |
| **输出位置** | 脚本所在目录 |

```bash
python caculate2.py
```

---

### 4. caculate3.py - GIS 数据处理工具（坐标转换版）

| 项目 | 说明 |
|------|------|
| **功能** | 带坐标系转换的 GIS 数据处理（EPSG:3857 → EPSG:4507） |
| **输入格式** | GIS JSON（Web墨卡托坐标） |
| **输入位置** | `data/` |
| **输出文件** | `建筑形态分析_CGCS2000版.xlsx` |
| **输出位置** | 脚本所在目录 |

```bash
python caculate3.py
```

---

### 5. caculate4.py - 带图结构分析的形态工具

| 项目 | 说明 |
|------|------|
| **功能** | 形态分析 + 建筑空间关系图生成 |
| **输入格式** | 户型图 JSON（需包含 rooms 和 doors） |
| **输入位置** | `data/` |
| **输出文件** | `建筑轮廓形态分析汇总.xlsx`、`{文件名}_anwer.txt` |
| **输出位置** | 脚本所在目录 |

```bash
python caculate4.py
# 程序会提示输入：
# - 转角角度阈值（默认165度）
# - 长边/短边比例阈值k（默认1.5）
```

---

### 6. caculate5.py - Residence 建筑专用分析工具

| 项目 | 说明 |
|------|------|
| **功能** | 专门筛选并分析住宅类型建筑 |
| **输入格式** | GIS JSON（需包含 Function 字段） |
| **输入位置** | `data/` |
| **输出文件** | `建筑形态分析_Residence.xlsx`、`建筑形态中间信息_Residence.xlsx` |
| **输出位置** | 脚本所在目录 |
| **可视化** | `polygon_visualizations/` 目录 |

```bash
python caculate5.py
```

---

### 7. caculate6.py - 多边形修复工具

| 项目 | 说明 |
|------|------|
| **功能** | 修复和规整化建筑轮廓多边形 |
| **输入格式** | 户型图 JSON |
| **输入位置** | `data/` |
| **输出文件** | `{原文件名}_1.json` |
| **输出位置** | `data/repair/` |

```bash
python caculate6.py
```

**修复功能**：对称性修复、直角修正、删除冗余点

---

### 8. draw1.py - 多边形简化与可视化工具

| 项目 | 说明 |
|------|------|
| **功能** | 使用 Douglas-Peucker 算法简化多边形 |
| **输入格式** | 户型图 JSON |
| **输入位置** | `data/repair/`（通常是 caculate6.py 的输出） |
| **输出文件** | `{文件名}_result.jpg` |
| **输出位置** | `data/repair/` |

```bash
python draw1.py
```

**参数**：在脚本中修改 `k_value` 变量调整简化程度（默认30）

---

## 形态指标说明

| 指标 | 计算公式 | 说明 | 取值范围 |
|------|----------|------|----------|
| 长宽比 | 长边 / 短边 | 最小外接矩形的长宽比 | ≥1 |
| 主方向角 | arctan(dy/dx) | 长边与正东方向的夹角 | 0-180° |
| 紧凑度 | (4πA) / P² | 形状接近圆形的程度，圆形=1 | 0-1 |
| 凹凸度 | 轮廓面积 / 凸包面积 | 形状的凸性程度 | 0-1 |
| 转角密度 | 有效转角数 / 周长 | 轮廓复杂程度 | ≥0 |

---

## 常见问题

**Q: 程序提示找不到 JSON 文件？**  
A: 确保 JSON 文件放在 `data/` 目录下，且文件扩展名为 `.json`

**Q: `data/` 目录不存在怎么办？**  
A: 程序会自动创建，或者手动创建 `data/` 文件夹

**Q: 如何批量处理多个文件？**  
A: 将所有 JSON 文件放入 `data/` 目录，程序会自动扫描并批量处理

**Q: draw1.py 的输入文件从哪来？**  
A: 先运行 `caculate6.py`，它会将修复后的文件输出到 `data/repair/`，然后 `draw1.py` 从该目录读取

---