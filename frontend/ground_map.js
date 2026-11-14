const proto = "https" + String.fromCharCode(58, 47, 47);
const host = "mt1" + String.fromCharCode(46) + "google" + String.fromCharCode(46) + "com";

const GROUND_MAP_PROVIDERS = {
  hybrid: () => new Cesium.UrlTemplateImageryProvider({ url: `${proto}${host}/vt/lyrs=y&x={x}&y={y}&z={z}` }),
  roadmap: () => new Cesium.UrlTemplateImageryProvider({ url: `${proto}${host}/vt/lyrs=m&x={x}&y={y}&z={z}` }),
  satellite: () => new Cesium.UrlTemplateImageryProvider({ url: `${proto}${host}/vt/lyrs=s&x={x}&y={y}&z={z}` }),
  terrain: () => new Cesium.UrlTemplateImageryProvider({ url: `${proto}${host}/vt/lyrs=p&x={x}&y={y}&z={z}` })
};

export function switchGroundMapLayer(viewer, layerKey, btnEl) {
  const factory = GROUND_MAP_PROVIDERS[layerKey];
  if (!factory) return;

  // Replace bottom base imagery layer (index 0) without disturbing radar overlays above it
  if (viewer.imageryLayers.length > 0) {
    viewer.imageryLayers.remove(viewer.imageryLayers.get(0), true);
  }
  const newBase = viewer.imageryLayers.addImageryProvider(factory(), 0);
  viewer.imageryLayers.lowerToBottom(newBase);

  document.querySelectorAll(".map-tab").forEach(b => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  viewer.scene.requestRender();
}

export function initGroundGlobe(containerId) {
  const viewer = new Cesium.Viewer(containerId, {
    baseLayer: new Cesium.ImageryLayer(GROUND_MAP_PROVIDERS.roadmap()),
    baseLayerPicker: false,
    timeline: false,
    animation: false,
    geocoder: false,
    homeButton: false,
    navigationHelpButton: false,
    requestRenderMode: true
  });
  viewer.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(-88.0, 40.5, 1900000) });

  const sources = {
    alerts: new Cesium.CustomDataSource("alerts"),
    vehicles: new Cesium.CustomDataSource("vehicles"),
    infra: new Cesium.CustomDataSource("infra"),
    route: new Cesium.CustomDataSource("route")
  };
  Object.values(sources).forEach(s => viewer.dataSources.add(s));
  return { viewer, sources };
}

export function createTrainCanvas() {
  const c = document.createElement("canvas");
  c.width = 26;
  c.height = 26;
  const ctx = c.getContext("2d");
  ctx.translate(13, 13);
  ctx.fillStyle = "#facc15";
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(0, -10);
  ctx.lineTo(5, -4);
  ctx.lineTo(5, 9);
  ctx.lineTo(-5, 9);
  ctx.lineTo(-5, -4);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  return c;
}

export function extractFirstRingDegrees(geometry) {
  if (!geometry || !geometry.coordinates) return [];
  let rawPoly = geometry.coordinates;
  if (geometry.type === "MultiPolygon") {
    for (const item of geometry.coordinates) {
      rawPoly = item;
      break;
    }
  }
  let ring = null;
  if (Array.isArray(rawPoly)) {
    for (const item of rawPoly) {
      ring = item;
      break;
    }
  }
  if (!Array.isArray(ring)) return [];

  const flat = [];
  for (const pair of ring) {
    if (Array.isArray(pair) && pair.length >= 2) {
      const [lon, lat] = pair;
      if (Number.isFinite(Number(lon)) && Number.isFinite(Number(lat))) {
        flat.push(Number(lon), Number(lat));
      }
    }
  }
  return flat;
}

export class GroundRadarController {
  constructor(viewer) {
    this.viewer = viewer;
    this.layer = null;
    this.frames = [];
    this.enabled = true;
    this.alpha = 0.75;
    this.animTimer = null;
    this.animIdx = 0;
  }

  setFrames(frames) {
    this.frames = frames || [];
    if (this.enabled && this.frames.length && !this.animTimer) {
      this.renderFrame(this.frames[this.frames.length - 1]);
    }
  }

  renderFrame(frame) {
    if (!frame || !frame.tile_url) return;
    if (this.layer) {
      this.viewer.imageryLayers.remove(this.layer, true);
      this.layer = null;
    }
    if (!this.enabled) return;
    this.layer = this.viewer.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({ url: frame.tile_url })
    );
    this.layer.alpha = this.alpha;
    this.viewer.scene.requestRender();
  }

  toggle(btn) {
    this.enabled = !this.enabled;
    if (btn) {
      btn.classList.toggle("active", this.enabled);
      btn.innerText = this.enabled ? "Radar: ON" : "Radar: OFF";
    }
    if (this.enabled && this.frames.length) {
      this.renderFrame(this.frames[this.frames.length - 1]);
    } else if (this.layer) {
      this.viewer.imageryLayers.remove(this.layer, true);
      this.layer = null;
      this.viewer.scene.requestRender();
    }
  }

  toggleAnimation(btn) {
    if (this.animTimer) {
      clearInterval(this.animTimer);
      this.animTimer = null;
      if (btn) {
        btn.classList.remove("active");
        btn.innerText = "▶ Animate";
      }
      if (this.frames.length) this.renderFrame(this.frames[this.frames.length - 1]);
      return;
    }
    if (!this.frames.length) return;
    if (btn) {
      btn.classList.add("active");
      btn.innerText = "⏸ Pause";
    }
    this.animTimer = setInterval(() => {
      this.renderFrame(this.frames[this.animIdx % this.frames.length]);
      this.animIdx++;
    }, 900);
  }

  setOpacity(pct) {
    this.alpha = Math.max(0, Math.min(1, Number(pct) / 100.0));
    if (this.layer) {
      this.layer.alpha = this.alpha;
      this.viewer.scene.requestRender();
    }
  }
}
