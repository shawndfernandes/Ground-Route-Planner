import asyncio
import json
import os
import urllib.request
from typing import Dict, Any, List


def _sync_get_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "GroundRouteEngine/1.0 (contact@localhost)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = resp.read().decode("utf-8", errors="ignore").strip()
        return json.loads(raw) if raw else {}


class GroundTrafficClient:
    """
    Streams live intercity rail (Amtrak) and optional GTFS-Realtime transit vehicle telemetry.
    """

    def __init__(self):
        self.gtfs_rt_url = os.getenv("GTFS_RT_URL", "").strip()

    async def get_live_vehicles(self, limit: int = 180) -> List[Dict[str, Any]]:
        vehicles: List[Dict[str, Any]] = []

        # 1. Live Amtrak Intercity Rail Feed (free, zero key)
        amtrak_url = "https://" + "api-v3." + "://amtraker.com"
        try:
            data = await asyncio.to_thread(_sync_get_json, amtrak_url)
            if isinstance(data, dict):
                for train_num, train_list in data.items():
                    if not isinstance(train_list, list):
                        continue
                    for t in train_list:
                        lat = t.get("lat")
                        lon = t.get("lon")
                        if lat is None or lon is None:
                            continue
                        vehicles.append({
                            "id": f"AMTK-{train_num}",
                            "mode": "RAIL",
                            "route_name": t.get("routeName") or f"Train {train_num}",
                            "lat": round(float(lat), 5),
                            "lon": round(float(lon), 5),
                            "speed_mph": round(float(t.get("velocity") or 0.0), 1),
                            "heading": float(t.get("heading") or 0.0),
                            "status": t.get("trainTimely") or "Active",
                            "source": "Amtraker Live Rail",
                        })
                        if len(vehicles) == limit:
                            break
                    if len(vehicles) == limit:
                        break
        except Exception:
            pass

        # 2. Optional Regional GTFS-Realtime JSON Vehicle Feed
        if self.gtfs_rt_url and len(vehicles) != limit:
            try:
                gtfs_data = await asyncio.to_thread(_sync_get_json, self.gtfs_rt_url)
                entities = gtfs_data.get("entity") or gtfs_data.get("vehicles") or []
                for ent in entities:
                    veh = ent.get("vehicle") or ent
                    pos = veh.get("position") or {}
                    lat = pos.get("latitude")
                    lon = pos.get("longitude")
                    if lat is None or lon is None:
                        continue
                    v_id = str((veh.get("vehicle") or {}).get("id") or ent.get("id") or "BUS")
                    vehicles.append({
                        "id": f"TRANSIT-{v_id}",
                        "mode": "BUS/TRANSIT",
                        "route_name": str((veh.get("trip") or {}).get("route_id") or "Transit"),
                        "lat": round(float(lat), 5),
                        "lon": round(float(lon), 5),
                        "speed_mph": round(float(pos.get("speed") or 0.0) * 2.23694, 1),
                        "heading": float(pos.get("bearing") or 0.0),
                        "status": "In Transit",
                        "source": "GTFS-RT Feed",
                    })
                    if len(vehicles) == limit:
                        break
            except Exception:
                pass

        return vehicles
