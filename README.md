# Ground Highway, Live Rail & Multi-Hazard Pathfinder

Real-time 3D highway routing, Weather.com animated radar, NOAA NWS snow/flood hazard avoidance, and infrastructure scanning built with **FastAPI**, **Shapely**, **OSRM**, and **CesiumJS**.

## Key Features
* **Highway Routing & Weather Detours:** OSRM-powered routing with automated lateral detours during active NWS severe weather.
* **Multi-Hazard Corridor Scanner:** Pins road construction, blockages, and railroad grade crossings via OpenStreetMap Overpass.
* **Live Weather & Telemetry:** NWS snow/flood overlays, Weather.com radar tiles, live Amtrak rail feeds, and elevation/temperature profiling.

## Quick Setup
```bash
python3 -m venv backend/venv
./backend/venv/bin/pip install -r backend/requirements.txt
chmod +x setup_cesium.sh restart.sh
./setup_cesium.sh
./restart.sh
```
Open **`http://localhost:3001/`** in your browser.

## Project Structure
* `setup_cesium.sh` / `restart.sh`: Initialization and service launcher scripts.
* `backend/`: FastAPI core (`main.py`), OSRM/weather routers, and hazard telemetry modules.
* `frontend/`: CesiumJS globe (`ground_map.js`), UI HUD (`index.html`), renderers, and profile charts.
