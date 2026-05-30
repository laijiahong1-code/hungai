from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Sequence
from urllib import request

import pandas as pd


DEFAULT_EXCEL_PATH = Path(
    r"C:\Users\赖宏\Desktop\原始数据\区域国资适配评分结果.xlsx"
)
DEFAULT_OUTPUT_DIR = Path("outputs") / "region_visualizations"
HTML_NAME = "province_industry_match_heatmap.html"
PNG_NAME = "province_industry_match_heatmap.png"
CHINA_GEOJSON_URL = "https://unpkg.com/echarts@4.1.0/map/json/china.json"

PROVINCE_SHORT_NAMES = {
    "北京市": "北京",
    "天津市": "天津",
    "上海市": "上海",
    "重庆市": "重庆",
    "河北省": "河北",
    "山西省": "山西",
    "辽宁省": "辽宁",
    "吉林省": "吉林",
    "黑龙江省": "黑龙江",
    "江苏省": "江苏",
    "浙江省": "浙江",
    "安徽省": "安徽",
    "福建省": "福建",
    "江西省": "江西",
    "山东省": "山东",
    "河南省": "河南",
    "湖北省": "湖北",
    "湖南省": "湖南",
    "广东省": "广东",
    "海南省": "海南",
    "四川省": "四川",
    "贵州省": "贵州",
    "云南省": "云南",
    "陕西省": "陕西",
    "甘肃省": "甘肃",
    "青海省": "青海",
    "台湾省": "台湾",
    "内蒙古自治区": "内蒙古",
    "广西壮族自治区": "广西",
    "西藏自治区": "西藏",
    "宁夏回族自治区": "宁夏",
    "新疆维吾尔自治区": "新疆",
    "香港特别行政区": "香港",
    "澳门特别行政区": "澳门",
}


def province_short_name(value: object) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        return ""
    if text in PROVINCE_SHORT_NAMES:
        return PROVINCE_SHORT_NAMES[text]
    for suffix in (
        "壮族自治区",
        "回族自治区",
        "维吾尔自治区",
        "特别行政区",
        "自治区",
        "省",
        "市",
    ):
        if text.endswith(suffix):
            return text[: -len(suffix)]
    return text


def aggregate_industry_scores(frame: pd.DataFrame) -> list[tuple[str, float]]:
    required = {"所在地省份", "产业匹配度得分"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(sorted(missing))}")
    working = frame.loc[:, ["所在地省份", "产业匹配度得分"]].copy()
    working["省份"] = working["所在地省份"].map(province_short_name)
    working["产业匹配度得分"] = pd.to_numeric(working["产业匹配度得分"], errors="coerce")
    working = working.dropna(subset=["省份", "产业匹配度得分"])
    grouped = (
        working.groupby("省份", as_index=False)["产业匹配度得分"]
        .mean()
        .sort_values("省份")
    )
    return [
        (str(row["省份"]), round(float(row["产业匹配度得分"]), 4))
        for _, row in grouped.iterrows()
        if str(row["省份"]).strip()
    ]


def load_region_scores(path: Path) -> list[tuple[str, float]]:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_excel(path, sheet_name=0)
    return aggregate_industry_scores(frame)


def build_heatmap(data: list[tuple[str, float]]):
    from pyecharts import options as opts
    from pyecharts.charts import Map

    return (
        Map(init_opts=opts.InitOpts(width="1200px", height="760px", bg_color="#F8FAFC"))
        .add(
            "产业匹配度得分",
            data,
            maptype="china",
            is_map_symbol_show=False,
            name_map=PROVINCE_SHORT_NAMES,
            label_opts=opts.LabelOpts(is_show=False),
            tooltip_opts=opts.TooltipOpts(formatter="{b}<br/>产业匹配度得分：{c}"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="各省份产业匹配度得分热力图",
                subtitle="基于区域国资适配评分数据（得分越高颜色越红）",
                pos_left="center",
                title_textstyle_opts=opts.TextStyleOpts(color="#101820", font_size=22),
                subtitle_textstyle_opts=opts.TextStyleOpts(color="#667085", font_size=13),
            ),
            visualmap_opts=opts.VisualMapOpts(
                min_=0,
                max_=4,
                range_text=["4", "0"],
                is_calculable=True,
                orient="vertical",
                pos_left="4%",
                pos_top="middle",
                range_color=["#1E3A5F", "#FCA5A5", "#991B1B"],
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )


def _color_for_score(score: float | None) -> tuple[int, int, int]:
    if score is None:
        return (226, 232, 240)
    value = max(0.0, min(4.0, float(score)))
    low = (0x1E, 0x3A, 0x5F)
    middle = (0xFC, 0xA5, 0xA5)
    high = (0x99, 0x1B, 0x1B)
    if value <= 2:
        ratio = value / 2
        start, end = low, middle
    else:
        ratio = (value - 2) / 2
        start, end = middle, high
    return tuple(round(start[index] + (end[index] - start[index]) * ratio) for index in range(3))


def load_china_geojson(output_dir: Path) -> dict:
    cache_path = output_dir / "china.json"
    if cache_path.exists():
        return decode_echarts_geojson(json.loads(cache_path.read_text(encoding="utf-8")))
    with request.urlopen(CHINA_GEOJSON_URL, timeout=30) as response:
        payload = response.read().decode("utf-8")
    cache_path.write_text(payload, encoding="utf-8")
    return decode_echarts_geojson(json.loads(payload))


def _decode_echarts_ring(encoded: str, offset: list[int]) -> list[list[float]]:
    previous_x, previous_y = int(offset[0]), int(offset[1])
    ring = []
    for index in range(0, len(encoded), 2):
        x = ord(encoded[index]) - 64
        y = ord(encoded[index + 1]) - 64
        x = (x >> 1) ^ (-(x & 1))
        y = (y >> 1) ^ (-(y & 1))
        x += previous_x
        y += previous_y
        previous_x, previous_y = x, y
        ring.append([x / 1024.0, y / 1024.0])
    return ring


def decode_echarts_geojson(geojson: dict) -> dict:
    if not geojson.get("UTF8Encoding"):
        return geojson
    decoded = {**geojson, "UTF8Encoding": False, "features": []}
    for feature in geojson.get("features", []):
        copied = {**feature}
        geometry = {**feature.get("geometry", {})}
        coordinates = geometry.get("coordinates") or []
        offsets = geometry.get("encodeOffsets") or []
        if geometry.get("type") == "Polygon":
            geometry["coordinates"] = [
                _decode_echarts_ring(ring, offsets[index])
                for index, ring in enumerate(coordinates)
                if isinstance(ring, str)
            ]
        elif geometry.get("type") == "MultiPolygon":
            geometry["coordinates"] = [
                [
                    _decode_echarts_ring(ring, offsets[polygon_index][ring_index])
                    for ring_index, ring in enumerate(polygon)
                    if isinstance(ring, str)
                ]
                for polygon_index, polygon in enumerate(coordinates)
            ]
        geometry.pop("encodeOffsets", None)
        copied["geometry"] = geometry
        decoded["features"].append(copied)
    return decoded


def render_fallback_html(data: list[tuple[str, float]], geojson: dict, html_path: Path) -> None:
    data_json = json.dumps(
        [{"name": province, "value": round(value, 4)} for province, value in data],
        ensure_ascii=False,
    )
    geojson_json = json.dumps(geojson, ensure_ascii=False)
    html_path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>各省份产业匹配度得分热力图</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    html, body {{ margin: 0; background: #F8FAFC; font-family: "Microsoft YaHei", sans-serif; }}
    #chart {{ width: 1200px; height: 760px; margin: 0 auto; }}
  </style>
</head>
<body>
  <div id="chart"></div>
  <script>
    const geoJson = {geojson_json};
    const data = {data_json};
    echarts.registerMap("china", geoJson);
    const chart = echarts.init(document.getElementById("chart"));
    chart.setOption({{
      backgroundColor: "#F8FAFC",
      title: {{
        text: "各省份产业匹配度得分热力图",
        subtext: "基于区域国资适配评分数据（得分越高颜色越红）",
        left: "center",
        top: 20,
        textStyle: {{ color: "#101820", fontSize: 22, fontWeight: 800 }},
        subtextStyle: {{ color: "#667085", fontSize: 13 }}
      }},
      tooltip: {{
        trigger: "item",
        formatter: function(params) {{
          const value = params.value == null || Number.isNaN(params.value) ? "暂无数据" : Number(params.value).toFixed(2);
          return params.name + "<br/>产业匹配度得分：" + value;
        }}
      }},
      visualMap: {{
        min: 0,
        max: 4,
        left: 36,
        top: "middle",
        calculable: true,
        text: ["4", "0"],
        inRange: {{ color: ["#1E3A5F", "#FCA5A5", "#991B1B"] }},
        textStyle: {{ color: "#344054" }}
      }},
      series: [{{
        name: "产业匹配度得分",
        type: "map",
        map: "china",
        roam: true,
        data,
        itemStyle: {{ borderColor: "#F8FAFC", borderWidth: 0.8 }},
        emphasis: {{ label: {{ show: true, color: "#101820" }} }}
      }}]
    }});
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def inject_china_geojson_into_html(html_path: Path, geojson: dict) -> None:
    html = html_path.read_text(encoding="utf-8")
    geojson_json = json.dumps(geojson, ensure_ascii=False)
    map_script = '<script type="text/javascript" src="https://assets.pyecharts.org/assets/v6/maps/china.js"></script>'
    html = html.replace(map_script, "")
    marker = "</script>"
    registration = f'\n<script type="text/javascript">echarts.registerMap("china", {geojson_json});</script>'
    if registration not in html and marker in html:
        html = html.replace(marker, marker + registration, 1)
    html_path.write_text(html, encoding="utf-8")


def capture_with_chrome(html_path: Path, png_path: Path) -> bool:
    chrome_candidates = [
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    browser = next((candidate for candidate in chrome_candidates if candidate.exists()), None)
    if browser is None:
        return False
    profile_dir = png_path.parent / "chrome-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    target = html_path.resolve().as_uri()
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile_dir}",
        "--window-size=1200,760",
        "--virtual-time-budget=5000",
        f"--screenshot={png_path.resolve()}",
        target,
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
    return png_path.exists() and png_path.stat().st_size > 0 and result.returncode == 0


def _iter_exterior_rings(geometry: dict):
    if not geometry:
        return
    geo_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geo_type == "Polygon":
        for ring in coordinates[:1]:
            yield ring
    elif geo_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon[:1]:
                yield ring


def render_static_png(data: list[tuple[str, float]], geojson: dict, png_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    value_by_province = {province: value for province, value in data}
    points = [
        point
        for feature in geojson.get("features", [])
        for ring in _iter_exterior_rings(feature.get("geometry", {}))
        for point in ring
        if isinstance(point, list) and len(point) >= 2
    ]
    min_lon = min(point[0] for point in points)
    max_lon = max(point[0] for point in points)
    min_lat = min(point[1] for point in points)
    max_lat = max(point[1] for point in points)

    width, height = 1200, 760
    map_left, map_top, map_width, map_height = 150, 100, 990, 600
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        candidates = [
            r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
        ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    title_font = font(26, True)
    subtitle_font = font(15)
    label_font = font(13, True)
    small_font = font(12)

    def project(lon: float, lat: float) -> tuple[float, float]:
        x = map_left + (lon - min_lon) / (max_lon - min_lon) * map_width
        y = map_top + (max_lat - lat) / (max_lat - min_lat) * map_height
        return x, y

    draw.text((width / 2, 26), "各省份产业匹配度得分热力图", fill="#101820", font=title_font, anchor="ma")
    draw.text(
        (width / 2, 62),
        "基于区域国资适配评分数据（得分越高颜色越红）",
        fill="#667085",
        font=subtitle_font,
        anchor="ma",
    )

    for feature in geojson.get("features", []):
        name = str(feature.get("properties", {}).get("name", "")).strip()
        fill = _color_for_score(value_by_province.get(name))
        for ring in _iter_exterior_rings(feature.get("geometry", {})):
            polygon = [project(float(point[0]), float(point[1])) for point in ring if len(point) >= 2]
            if len(polygon) >= 3:
                draw.polygon(polygon, fill=fill, outline="#FFFFFF")
                draw.line(polygon + [polygon[0]], fill="#FFFFFF", width=1)

    legend_x, legend_y, legend_w, legend_h = 46, 252, 20, 220
    for offset in range(legend_h):
        score = 4 - (offset / max(1, legend_h - 1) * 4)
        color = _color_for_score(score)
        draw.rectangle((legend_x, legend_y + offset, legend_x + legend_w, legend_y + offset + 1), fill=color)
    draw.rectangle((legend_x, legend_y, legend_x + legend_w, legend_y + legend_h), outline="#CBD5E1")
    for score in (4, 2, 0):
        y = legend_y + (4 - score) / 4 * legend_h
        draw.line((legend_x + legend_w + 4, y, legend_x + legend_w + 12, y), fill="#344054", width=1)
        draw.text((legend_x + legend_w + 18, y), f"{score}", fill="#344054", font=label_font, anchor="lm")
    draw.text((legend_x, legend_y - 22), "产业匹配度", fill="#344054", font=small_font)
    draw.text((legend_x, legend_y + legend_h + 16), "0 - 4 分", fill="#667085", font=small_font)

    png_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(png_path)


def render_heatmap(excel_path: Path, output_dir: Path) -> tuple[Path, Path | None]:
    data = load_region_scores(excel_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / HTML_NAME
    png_path = output_dir / PNG_NAME
    geojson = load_china_geojson(output_dir)
    try:
        chart = build_heatmap(data)
        chart.render(str(html_path))
    except ImportError as exc:
        print(f"pyecharts不可用，使用ECharts HTML回退生成：{exc}")
        render_fallback_html(data, geojson, html_path)
    try:
        from pyecharts.render import make_snapshot
        from snapshot_selenium import snapshot

        make_snapshot(snapshot, str(html_path), str(png_path))
    except Exception as exc:
        print(f"pyecharts截图生成失败，尝试使用本地Chrome截图：{exc}")
        if capture_with_chrome(html_path, png_path):
            return html_path, png_path
        print("本地Chrome截图不可用，使用PIL静态地图回退生成")
        render_static_png(data, geojson, png_path)
        return html_path, png_path
    return html_path, png_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成区域国资适配省份产业匹配度热力图")
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    html_path, png_path = render_heatmap(args.excel, args.output_dir)
    print(f"HTML: {html_path}")
    print(f"PNG: {png_path if png_path else '未生成'}")
    return 0 if png_path else 2


if __name__ == "__main__":
    raise SystemExit(main())
