export function drawRoadChart(profile, canvasId = "roadChart") {
  const c = document.getElementById(canvasId);
  if (!c) return;
  const ctx = c.getContext("2d");
  c.width = c.clientWidth || 800;
  c.height = c.clientHeight || 150;
  ctx.clearRect(0, 0, c.width, c.height);
  if (!profile || !profile.length) return;

  const maxElev = Math.max(2000, ...profile.map(p => p.elevation_ft || 0));
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();

  profile.forEach((p, i) => {
    const x = 30 + (i / Math.max(1, profile.length - 1)) * (c.width - 60);
    const y = c.height - 20 - ((p.elevation_ft || 0) / maxElev) * (c.height - 40);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);

    ctx.fillStyle = "#facc15";
    ctx.font = "11px sans-serif";
    ctx.fillText(`${Math.round(p.temp_f || 0)}°F`, x - 12, y - 6);
  });
  ctx.stroke();
}
