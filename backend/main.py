from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from ground_weather import GroundWeatherClient
from ground_router import geocode_city, compute_safe_ground_route
from ground_traffic import GroundTrafficClient
from ground_hazards import GroundHazardClient

app = FastAPI(title="Ground Highway, Live Rail/Transit & Multi-Hazard Routing Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
wx = GroundWeatherClient()
traffic = GroundTrafficClient()
hazards_client = GroundHazardClient()


@app.get("/api/ground/snapshot")
async def ground_snapshot(lat: float = Query(40.09), lon: float = Query(-83.02)):
    alerts, road_wx, vehicles, radar_cfg = await asyncio.gather(
        hazards_client.get_categorized_weather_hazards(),
        wx.get_road_conditions(lat, lon),
        traffic.get_live_vehicles(limit=180),
        wx.get_weather_com_radar(),
    )
    return {
        "vehicles": vehicles,
        "alerts_geojson": alerts,
        "road_weather": road_wx,
        "radar_config": radar_cfg,
    }


@app.get("/api/ground/route")
async def plan_ground_route(origin: str = Query(...), destination: str = Query(...)):
    orig, dest = await asyncio.gather(geocode_city(origin), geocode_city(destination))
    if not orig or not dest:
        raise HTTPException(status_code=404, detail="Could not geocode origin or destination city.")

    alerts = await hazards_client.get_categorized_weather_hazards()
    result = await compute_safe_ground_route(orig, dest, alerts)
    if not result:
        raise HTTPException(status_code=400, detail="OSRM could not find a drivable highway route.")

    pts = result["safe"]["points"]
    step = max(1, len(pts) // 10)
    profile_pts = pts[::step][:10]

    road_samples, infra_hazards = await asyncio.gather(
        asyncio.gather(*[wx.get_road_conditions(lat, lon) for lat, lon in profile_pts]),
        hazards_client.get_corridor_infrastructure_hazards(pts, max_items=90),
    )

    return {
        "origin": orig,
        "destination": dest,
        "direct_route": result["direct"],
        "safe_route": result["safe"],
        "weather_hits": result["hazard_hits"],
        "infrastructure_hazards": infra_hazards,
        "road_profile": [
            {"lat": lat, "lon": lon, **sample}
            for (lat, lon), sample in zip(profile_pts, road_samples)
        ],
    }
