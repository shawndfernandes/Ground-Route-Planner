import { initGroundGlobe, switchGroundMapLayer, GroundRadarController } from "./ground_map.js";
import { renderLiveTrains, renderWeatherHazards, renderRouteAndInfra } from "./ground_renderer.js";
import { drawRoadChart } from "./ground_chart.js";

const API = "http://localhost:8001/api/ground";
const { viewer, sources } = initGroundGlobe("cesiumContainer");
const radar = new GroundRadarController(viewer);

window.setGroundMapLayer = (key, btn) => switchGroundMapLayer(viewer, key, btn);

window.toggleLayer = (key, btn) => {
  const ds = sources[key];
  if (!ds) return;
  ds.show = !ds.show;
  btn.classList.toggle("active", ds.show);
  const labelPrefix = btn.innerText.split(":");
  btn.innerText = `${labelPrefix}: ${ds.show ? "ON" : "OFF"}`;
  viewer.scene.requestRender();
};

window.toggleGroundRadar = (btn) => radar.toggle(btn);
window.toggleGroundRadarAnim = (btn) => radar.toggleAnimation(btn);
window.setGroundRadarOpacity = (pct) => radar.setOpacity(pct);

window.manualGroundRefresh = async (btn) => {
  if (btn) btn.innerText = "↻ ...";
  await loadAlertsAndTraffic();
  if (btn) btn.innerText = "↻ Refresh";
};

async function loadAlertsAndTraffic() {
  try {
    const res = await fetch(`${API}/snapshot`);
    const data = await res.json();

    radar.setFrames(data.radar_config?.frames || []);
    renderLiveTrains(sources.vehicles, data.vehicles || []);
    renderWeatherHazards(sources.alerts, data.alerts_geojson?.features || []);

    const rw = data.road_weather || {};
    document.getElementById("twcGroundBox").innerHTML = `
      <div style="display:flex; justify-content:space-between;">
        <strong>${rw.source || "Weather.com Outlook"}</strong>
        <span>${data.radar_config?.provider || "Radar"}</span>
      </div>
      <div style="margin-top:3px;">
        <strong>Temp:</strong> ${rw.temp_f}°F (Feels ${rw.feels_like_f}°F) · <strong>${rw.phrase}</strong> · Gusts ${rw.gust_mph} mph
      </div>
    `;

    document.getElementById("status").innerText =
      `Live Trains: ${(data.vehicles || []).length} | Snow/Flood/Weather Alerts: ${(data.alerts_geojson?.features || []).length}`;
    viewer.scene.requestRender();
  } catch (err) {
    document.getElementById("status").innerText = "Waiting for Ground backend (:8001)...";
  }
}

window.planDrive = async () => {
  const o = document.getElementById("orig").value.trim();
  const d = document.getElementById("dest").value.trim();
  if (!o || !d) return;

  document.getElementById("status").innerText = `Scanning highway, construction, blockages, train crossings & snow/floods...`;
  const res = await fetch(`${API}/route?origin=${encodeURIComponent(o)}&destination=${encodeURIComponent(d)}`);
  const data = await res.json();

  const counts = renderRouteAndInfra(sources.route, sources.infra, data);
  const card = document.getElementById("card");
  card.style.display = "block";
  card.innerHTML = `
    <div><strong>Direct Highway:</strong> ${data.direct_route.distance_mi} mi (${data.direct_route.duration_min} min)</div>
    <div><strong>Safe Detour Route:</strong> ${data.safe_route.distance_mi} mi (${data.safe_route.duration_min} min)</div>
    <div><strong>Corridor Hazards:</strong> ${counts.workCount} Construction · ${counts.blockCount} Blockages · ${counts.railCount} Train Crossings · ${(data.weather_hits || []).length} Snow/Flood Hits</div>
  `;

  drawRoadChart(data.road_profile || []);
  viewer.flyTo(sources.route.entities);
  viewer.scene.requestRender();
};

const clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
clickHandler.setInputAction((movement) => {
  const picked = viewer.scene.pick(movement.position);
  if (!Cesium.defined(picked) || !picked.id || !picked.id.properties) return;
  const p = picked.id.properties.getValue(Cesium.JulianDate.now());
  const card = document.getElementById("card");
  if (p.kind === "INFRA_HAZARD") {
    card.style.display = "block";
    card.innerHTML = `<strong>${p.type}:</strong> ${p.title}<br/>Coords: ${p.lat}°, ${p.lon}°`;
  } else if (p.kind === "WEATHER_ALERT") {
    card.style.display = "block";
    card.innerHTML = `<strong>${p.event} (${p.severity})</strong><br/>${p.headline || ""}`;
  } else if (p.kind === "VEHICLE") {
    card.style.display = "block";
    card.innerHTML = `<strong>${p.id}</strong> (${p.route_name})<br/>Speed: ${p.speed_mph} mph · Heading: ${Math.round(p.heading)}°`;
  }
}, Cesium.ScreenSpaceEventType.LEFT_CLICK);

loadAlertsAndTraffic();
setInterval(loadAlertsAndTraffic, 30000);
