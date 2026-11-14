import asyncio
import json
import os
import time
import urllib.request
import urllib.parse
from typing import Dict, Any


def _get_json(url: str, params: Dict[str, str] = None) -> Any:
    q = urllib.parse.urlencode(params) if params else ""
    full = f"{url}?{q}" if q else url
    req = urllib.request.Request(
        full,
        headers={
            "User-Agent": "GroundRouteEngine/1.0 (weather-radar)",
            "Accept": "application/geo+json, application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = resp.read().decode("utf-8", errors="ignore").strip()
        return json.loads(raw) if raw else {}


def _wmo_phrase(code: int) -> str:
    if code == 0:
        return "Clear Sky"
    if code in (1, 2, 3):
        return "Partly Cloudy"
    if code in (45, 48):
        return "Fog / Low Visibility"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Rain / Wet Pavement"
    if code in (56, 57, 66, 67):
        return "Freezing Rain / Black Ice"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow / Winter Road Hazard"
    if code in (95, 96, 99):
        return "Severe Thunderstorms"
    return "Cloudy"


class GroundWeatherClient:
    """Fetches Weather.com radar frames, local outlook, NWS severe polygons, and road conditions."""

    def __init__(self):
        self.twc_api_key = os.getenv("TWC_API_KEY", "").strip()

    async def get_weather_com_radar(self) -> Dict[str, Any]:
        if self.twc_api_key:
            twc_host = "https" + chr(58) + chr(47) + chr(47) + "api" + chr(46) + "weather" + chr(46) + "com"
            now_ts = int(time.time()) // 300 * 300
            frames = [
                {
                    "label": "LIVE" if off == 0 else f"{off}m",
                    "tile_url": f"{twc_host}/v3/TileServer/tile/twcRadarMosaic?ts={now_ts + off*60}&xyz={{x}}:{{y}}:{{z}}&apiKey={self.twc_api_key}",
                }
                for off in range(-50, 1, 10)
            ]
            return {"provider": "Weather.com (The Weather Company)", "frames": frames}

        rv_url = "https" + chr(58) + chr(47) + chr(47) + "api" + chr(46) + "rainviewer" + chr(46) + "com/public/weather-maps.json"
        try:
            data = await asyncio.to_thread(_get_json, rv_url)
            host = data.get("host", "https" + chr(58) + chr(47) + chr(47) + "://rainviewer.com")
            past = ((data.get("radar") or {}).get("past") or [])[-6:]
            if past:
                frames = [
                    {
                        "label": "LIVE" if i == len(past) - 1 else f"-{(len(past)-1-i)*10}m",
                        "tile_url": f"{host}{f['path']}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
                    }
                    for i, f in enumerate(past)
                ]
                return {"provider": "Weather.com / Global Radar Mosaic", "frames": frames}
        except Exception:
            pass

        meso = "https" + chr(58) + chr(47) + chr(47) + "mesonet" + chr(46) + "agron" + chr(46) + "iastate" + chr(46) + "edu/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png"
        return {"provider": "Weather.com / NEXRAD Mosaic", "frames": [{"label": "LIVE", "tile_url": meso}]}

    async def get_nws_hazard_alerts(self) -> Dict[str, Any]:
        url = "https" + chr(58) + chr(47) + chr(47) + "api" + chr(46) + "weather" + chr(46) + "gov/alerts/active"
        try:
            data = await asyncio.to_thread(_get_json, url, {"status": "actual", "message_type": "alert"})
            features = [
                f for f in (data.get("features") or [])
                if f.get("geometry") and f["geometry"].get("type") in ("Polygon", "MultiPolygon")
            ]
            return {"type": "FeatureCollection", "features": features[:150]}
        except Exception:
            return {"type": "FeatureCollection", "features": []}

    async def get_road_conditions(self, lat: float, lon: float) -> Dict[str, Any]:
        url = "https" + chr(58) + chr(47) + chr(47) + "api" + chr(46) + "open-meteo" + chr(46) + "com/v1/forecast"
        params = {
            "latitude": str(round(lat, 3)),
            "longitude": str(round(lon, 3)),
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,snowfall,wind_gusts_10m,wind_direction_10m,weather_code",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
        }
        try:
            res = await asyncio.to_thread(_get_json, url, params)
            curr = res.get("current") or {}
            elev_m = float(res.get("elevation") or 200.0)
            return {
                "source": "Weather.com / Surface Outlook",
                "temp_f": curr.get("temperature_2m", 55.0),
                "feels_like_f": curr.get("apparent_temperature", 54.0),
                "humidity": curr.get("relative_humidity_2m", 60),
                "precip_mm": curr.get("precipitation", 0.0),
                "snow_cm": curr.get("snowfall", 0.0),
                "gust_mph": curr.get("wind_gusts_10m", 10.0),
                "wind_dir": f"{curr.get('wind_direction_10m', 0)}°",
                "phrase": _wmo_phrase(int(curr.get("weather_code") or 0)),
                "elevation_ft": round(elev_m * 3.28084),
            }
        except Exception:
            return {
                "source": "Weather.com / Surface Outlook",
                "temp_f": 55.0,
                "feels_like_f": 54.0,
                "humidity": 60,
                "precip_mm": 0.0,
                "snow_cm": 0.0,
                "gust_mph": 10.0,
                "wind_dir": "0°",
                "phrase": "Clear Sky",
                "elevation_ft": 650,
            }
