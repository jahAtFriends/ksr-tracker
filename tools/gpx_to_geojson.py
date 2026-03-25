from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert GPX track/route points to GeoJSON LineString.",
    )
    parser.add_argument("input_gpx", type=Path, help="Input GPX file path")
    parser.add_argument("output_geojson", type=Path, help="Output GeoJSON file path")
    parser.add_argument("--name", default="Baltimore Kinetic Route", help="Route name property")
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Keep every Nth point to reduce route size (default: 1)",
    )
    return parser.parse_args()


def _namespace(root: ET.Element) -> dict[str, str]:
    if root.tag.startswith("{"):
        uri = root.tag.split("}", 1)[0][1:]
        return {"gpx": uri}
    return {"gpx": ""}


def _collect_points(root: ET.Element, ns: dict[str, str]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    trkpts = root.findall(".//gpx:trkpt", ns) if ns["gpx"] else root.findall(".//trkpt")
    rtepts = root.findall(".//gpx:rtept", ns) if ns["gpx"] else root.findall(".//rtept")

    source = trkpts if trkpts else rtepts
    for pt in source:
        lat = pt.attrib.get("lat")
        lon = pt.attrib.get("lon")
        if lat is None or lon is None:
            continue
        points.append((float(lat), float(lon)))

    return points


def to_geojson(name: str, points: list[tuple[float, float]], stride: int) -> dict:
    if stride < 1:
        raise ValueError("Stride must be >= 1")

    sampled = points[::stride]
    if len(sampled) < 2 and len(points) >= 2:
        sampled = [points[0], points[-1]]

    coordinates = [[lon, lat] for lat, lon in sampled]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "source_points": len(points),
                    "kept_points": len(sampled),
                    "stride": stride,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
            }
        ],
    }


def main() -> int:
    args = parse_args()
    tree = ET.parse(args.input_gpx)
    root = tree.getroot()
    ns = _namespace(root)

    points = _collect_points(root, ns)
    if len(points) < 2:
        raise ValueError("GPX file must contain at least 2 track or route points")

    geojson = to_geojson(args.name, points, args.stride)

    args.output_geojson.parent.mkdir(parents=True, exist_ok=True)
    args.output_geojson.write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    print(
        f"Wrote {args.output_geojson} with {geojson['features'][0]['properties']['kept_points']} points "
        f"(from {geojson['features'][0]['properties']['source_points']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
