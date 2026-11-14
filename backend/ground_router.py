import asyncio
import json
import math
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from shapely.geometry import shape, Point


def _get_json(url: str, params: Dict[str, str] = None) -> Any:
    q = urllib.parse.urlencode(params) if params else ""
    full = f"{url}?{q}" if q else url
    req = urllib.request.Request(full, headers={"User-Agent": "GroundRouteEngine/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


async def geocode_city(query: str) -> Optional[Dict[str, Any]]:
    url = "https://" + "nominatim." + "openstreetmap.org/search"
    res = await asyncio.to_thread(_get_json, url, {"q": query.strip(), "format": "json", "limit": "1"})
    if isinstance(res, list) and res:
        top = next(iter(res))
        return {
            "lat": round(float(top["lat"]), 5),
            "lon": round(float(top["lon"]), 5),
            "name": ", ".join(top.get("display_name", query).split(",")[:2]),
        }
    return None


async def fetch_osrm_route(coords: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in coords])
    url = "https://" + "router." + f"project-osrm.org/route/v1/driving/{coord_str}"
    data = await asyncio.to_thread(_get_json, url, {"overview": "full", "geometries": "geojson"})
    routes = data.get("routes") or []
    if not routes:
        return None
    best = next(iter(routes))
    # Extract [lat, lon] cleanly via tuple unpacking
    pts = [[float(lat), float(lon)] for lon, lat in best["geometry"]["coordinates"]]
    return {
        "points": pts,
        "distance_mi": round(best["distance"] * 0.000621371, 1),
        "duration_min": round(best["duration"] / 60.0, 1),
    }


def evaluate_route_hazards(
    points: List[List[float]], alerts_geojson: Dict[str, Any]
) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
    polys = []
    for f in alerts_geojson.get("features") or []:
        if f.get("geometry"):
            props = f.get("properties") or {}
            polys.append(
                (shape(f["geometry"]), props.get("event", "Weather Alert"), props.get("severity", "Moderate"))
            )

    step = max(1, len(points) // 40)
    sampled = points[::step]
    if sampled and sampled[-1] != points[-1]:
        sampled.append(points[-1])

    hits = []
    for lat, lon in sampled:
        pt = Point(lon, lat)
        for poly, event_name, sev in polys:
            if poly.contains(pt):
                hits.append({"lat": lat, "lon": lon, "event": event_name, "severity": sev})
                break
    return sampled, hits


async def compute_safe_ground_route(
    orig: Dict[str, Any], dest: Dict[str, Any], alerts_geojson: Dict[str, Any]
) -> Dict[str, Any]:
    direct = await fetch_osrm_route([(orig["lat"], orig["lon"]), (dest["lat"], dest["lon"])])
    if not direct:
        return {}

    sampled_direct, hits = evaluate_route_hazards(direct["points"], alerts_geojson)
    safe_route = direct

    # If direct highway intersects an active NWS warning polygon, test lateral highway detours via OSRM
    if hits:
        mid_lat = (orig["lat"] + dest["lat"]) / 2.0
        mid_lon = (orig["lon"] + dest["lon"]) / 2.0
        dlat = dest["lat"] - orig["lat"]
        dlon = dest["lon"] - orig["lon"]
        norm = max(0.01, math.hypot(dlat, dlon))
        perp_lat, perp_lon = -dlon / norm, dlat / norm

        best_candidate = None
        best_hit_count = len(hits)
        for shift in (-1.2, 1.2, -2.2, 2.2):
            via = (round(mid_lat + perp_lat * shift, 4), round(mid_lon + perp_lon * shift, 4))
            cand = await fetch_osrm_route([(orig["lat"], orig["lon"]), via, (dest["lat"], dest["lon"])])
            if cand:
                _, cand_hits = evaluate_route_hazards(cand["points"], alerts_geojson)
                if len(cand_hits) < best_hit_count:
                    best_hit_count = len(cand_hits)
                    best_candidate = cand
        if best_candidate:
            safe_route = best_candidate

    return {
        "direct": direct,
        "safe": safe_route,
        "sampled_direct": sampled_direct,
        "hazard_hits": hits,
    }
