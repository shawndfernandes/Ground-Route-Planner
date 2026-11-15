import { createTrainCanvas, extractFirstRingDegrees } from "./ground_map.js";

const TRAIN_ICON = createTrainCanvas();

export function renderLiveTrains(vehicleSource, vehicles) {
  vehicleSource.entities.removeAll();
  (vehicles || []).forEach(v => {
    vehicleSource.entities.add({
      name: v.id,
      properties: { kind: "VEHICLE", ...v },
      position: Cesium.Cartesian3.fromDegrees(v.lon, v.lat, 120),
      billboard: {
        image: TRAIN_ICON,
        width: 18,
        height: 18,
        rotation: -Cesium.Math.toRadians(v.heading || 0),
        alignedAxis: Cesium.Cartesian3.UNIT_Z
      },
      label: {
        text: `${v.id} (${v.speed_mph}mph)`,
        font: "10px sans-serif",
        fillColor: Cesium.Color.YELLOW,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -14),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1100000)
      }
    });
  });
}

export function renderWeatherHazards(alertSource, features) {
  alertSource.entities.removeAll();
  (features || []).forEach(f => {
    const props = f.properties || {};
    const cat = props.hazard_category || "TRAFFIC_WEATHER";
    let polyColor = Cesium.Color.RED.withAlpha(0.24);
    let edgeColor = Cesium.Color.ORANGE;

    if (cat === "SNOW") {
      polyColor = Cesium.Color.DEEPSKYBLUE.withAlpha(0.32);
      edgeColor = Cesium.Color.CYAN;
    } else if (cat === "FLOOD") {
      polyColor = Cesium.Color.MEDIUMPURPLE.withAlpha(0.34);
      edgeColor = Cesium.Color.VIOLET;
    }

    const flat = extractFirstRingDegrees(f.geometry);
    if (flat.length >= 6) {
      alertSource.entities.add({
        properties: {
          kind: "WEATHER_ALERT",
          event: props.event,
          severity: props.severity,
          headline: props.headline
        },
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(flat),
          height: 0,
          heightReference: Cesium.HeightReference.NONE,
          height: 0,
          material: polyColor,
          outline: true,
          outlineColor: edgeColor
        }
      });
    }
  });
}

export function renderRouteAndInfra(routeSource, infraSource, data) {
  routeSource.entities.removeAll();
  infraSource.entities.removeAll();

  routeSource.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArray(data.direct_route.points.flatMap(([lat, lon]) => [lon, lat])),
      width: 5,
      material: Cesium.Color.ORANGE
    }
  });

  routeSource.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArray(data.safe_route.points.flatMap(([lat, lon]) => [lon, lat])),
      width: 6,
      material: Cesium.Color.LIMEGREEN
    }
  });

  let workCount = 0;
  let blockCount = 0;
  let railCount = 0;

  (data.infrastructure_hazards || []).forEach(h => {
    let pinColor = Cesium.Color.YELLOW;
    let shortTag = "RAIL XING";

    if (h.type === "CONSTRUCTION") {
      pinColor = Cesium.Color.ORANGE;
      shortTag = "WORK ZONE";
      workCount++;
    } else if (h.type === "BLOCKAGE") {
      pinColor = Cesium.Color.RED;
      shortTag = "BLOCKAGE";
      blockCount++;
    } else {
      railCount++;
    }

    infraSource.entities.add({
      properties: { kind: "INFRA_HAZARD", ...h },
      position: Cesium.Cartesian3.fromDegrees(h.lon, h.lat, 80),
      point: { pixelSize: 9, color: pinColor, outlineColor: Cesium.Color.BLACK, outlineWidth: 2 },
      label: {
        text: shortTag,
        font: "bold 10px sans-serif",
        fillColor: pinColor,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -14),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 450000)
      }
    });
  });

  return { workCount, blockCount, railCount };
}
