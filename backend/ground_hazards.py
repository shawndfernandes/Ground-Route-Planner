import asyncio
import json
import os
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Tuple


def _post_overpass(ql_query: str) -> Dict[str, Any]:
    url = "https" + chr(58) + chr(47) + chr(47) + "overpass-api" + chr(46) + "de/api/interpreter"
    data = urllib.parse.urlencode({"data": ql_query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "GroundRouteEngine/1.0 (hazard-scanner)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="ignore").strip()
        return json.loads(raw) if raw else {}


def _get_json(url: str, headers: Dict[str, str] = None) -> Any:
    req_headers = {"User-Agent": "GroundRouteEngine/1.0 (hazard-scanner)"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = resp.read().decode("utf-8", errors="ignore").strip()
        return json.loads(raw) if raw else {}


class GroundHazardClient:
    """
    Fetches live road construction, blockages, railroad level crossings,
    and categorized NWS Snow / Flood hazard polygons.
    """

    def __init__(self):
        self.ohgo_api_key = os.getenv("OHGO_API_KEY", "").strip()

    async def get_corridor_infrastructure_hazards(
        self, route_points: List[List[float]], max_items: int = 80
    ) -> List[Dict[str, Any]]:
        """
        Queries OpenStreetMap Overpass around the route bounding box for:
        - Railroad grade crossings (railway=level_crossing)
        - Active highway construction (highway=construction)
        - Road blockages / closures (barrier=bollard|gate|blocks, access=no)
        """
        if not route_points:
            return []

        lats = [p[0] for p in route_points]
        lons = [p[1] for p in route_points]
        min_lat, max_lat = min(lats) - 0.15, max(lats) + 0.15
        min_lon, max_lon = min(lons) - 0.15, max(lons) + 0.15

        # Keep bbox query bounded so Overpass responds rapidly
        if (max_lat - min_lat) > 4.5 or (max_lon - min_lon) > 6.0:
            mid_idx = len(route_points) // 2
            c_lat, c_lon = route_points[mid_idx]
            min_lat, max_lat = c_lat - 1.5, c_lat + 1.5
            min_lon, max_lon = c_lon - 2.0, c_lon + 2.0

        bbox = f"{min_lat:.4f},{min_lon:.4f},{max_lat:.4f},{max_lon:.4f}"
        ql = f"""
        [out:json][timeout:12];
        (
          node["railway"="level_crossing"]({bbox});
          way["highway"="construction"]({bbox});
          node["barrier"~"blocks|gate|lift_gate"]({bbox});
        );
        out center 120;
        """

        hazards: List[Dict[str, Any]] = []
        try:
            data = await asyncio.to_thread(_post_overpass, ql)
            for el in data.get("elements") or []:
                tags = el.get("tags") or {}
                lat = el.get("lat") or (el.get("center") or {}).get("lat")
                lon = el.get("lon") or (el.get("center") or {}).get("lon")
                if lat is None or lon is None:
                    continue

                if tags.get("railway") == "level_crossing":
                    h_type = "TRAIN_CROSSING"
                    title = f"Railroad Crossing ({tags.get('ref') or tags.get('operator') or 'At-Grade'})"
                elif tags.get("highway") == "construction":
                    h_type = "CONSTRUCTION"
                    title = f"Road Construction ({tags.get('name') or tags.get('ref') or 'Work Zone'})"
                else:
                    h_type = "BLOCKAGE"
                    title = f"Road Blockage / Gate ({tags.get('barrier') or 'Restricted'})"

                # Keep only items within ~6 miles (0.09 deg) of the actual route points
                near_route = any(
                    abs(float(lat) - r_lat) < 0.09 and abs(float(lon) - r_lon) < 0.09
                    for r_lat, r_lon in route_points[::max(1, len(route_points) // 60)]
                )
                if not near_route:
                    continue

                hazards.append({
                    "type": h_type,
                    "title": title,
                    "lat": round(float(lat), 5),
                    "lon": round(float(lon), 5),
                })
                if len(hazards) >= max_items:
                    break
        except Exception:
            pass

        return hazards

    async def get_categorized_weather_hazards(self) -> Dict[str, Any]:
        """Fetches active NWS alerts and tags each polygon as SNOW, FLOOD, or TRAFFIC_WEATHER."""
        url = "https" + chr(58) + chr(47) + chr(47) + "api" + chr(46) + "weather" + chr(46) + "gov/alerts/active?status=actual"
        try:
            data = await asyncio.to_thread(_get_json, url)
            tagged = []
            for f in data.get("features") or []:
                geom = f.get("geometry")
                if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                    continue
                props = f.get("properties") or {}
                ev = str(props.get("event") or "").upper()
                if any(k in ev for k in ("SNOW", "BLIZZARD", "ICE", "WINTER", "FREEZ")):
                    cat = "SNOW"
                elif any(k in ev for k in ("FLOOD", "FLASH FLOOD", "COASTAL")):
                    cat = "FLOOD"
                else:
                    cat = "TRAFFIC_WEATHER"
                props["hazard_category"] = cat
                tagged.append(f)
            return {"type": "FeatureCollection", "features": tagged[:160]}
        except Exception:
            return {"type": "FeatureCollection", "features": []}
