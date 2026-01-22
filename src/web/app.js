// === CONFIGURATION ===
const API_BASE = window.location.origin; // Use same origin as the page
const UPDATE_INTERVAL = 2000; // Update every 2 seconds for real-time feel
const INITIAL_LOAD_LIMIT = 50000;
const INITIAL_LOAD_SAMPLE_RATE = 10;
let autoUpdate = true;
let updateTimer = null;
let map = null;
let markersLayer = null;
let pathLayer = null;
let heatLayer = null;
let allPoints = [];
let lastFrameNumber = 0;
let isInitialLoad = true;

// === MAP INITIALIZATION ===
function initMap(centerLat, centerLon) {
  if (map) {
    map.remove();
  }

  map = L.map('map').setView([centerLat, centerLon], 18);
  
  // Add OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  // Initialize layers
  markersLayer = L.layerGroup().addTo(map);
  pathLayer = L.layerGroup().addTo(map);
}

// === HEALTH TO COLOR ===
function healthToColor(health) {
  if (health >= 60) return '#28a745'; // Green
  if (health >= 40) return '#ffc107'; // Yellow
  return '#dc3545'; // Red
}

// === UPDATE MAP WITH DATA === 
function updateMap(points) {
  if (!points || points.length === 0) return;

  // Clear existing layers
  if (markersLayer) markersLayer.clearLayers();
  if (pathLayer) pathLayer.clearLayers();
  if (heatLayer) map.removeLayer(heatLayer);

  // Create polyline for flight path
  const pathCoords = points.map(p => [p.lat, p.lon]);
  const path = L.polyline(pathCoords, {
    color: '#3388ff',
    weight: 3,
    opacity: 0.7
  }).addTo(pathLayer);

  // Add markers for each point
  points.forEach((point, index) => {
    const color = healthToColor(point.health_index);
    const marker = L.circleMarker([point.lat, point.lon], {
      radius: 5,
      fillColor: color,
      color: '#fff',
      weight: 1,
      opacity: 1,
      fillOpacity: 0.8
    });

    marker.bindPopup(`
      <strong>Frame ${point.frame_number}</strong><br/>
      Health: ${point.health_index.toFixed(1)}%<br/>
      Status: ${point.health_status}<br/>
      Time: ${point.timestamp}<br/>
      ${point.altitude ? `Altitude: ${point.altitude.toFixed(1)}m<br/>` : ''}
      <small>Lat: ${point.lat.toFixed(6)}, Lon: ${point.lon.toFixed(6)}</small>
    `);

    markersLayer.addLayer(marker);
  });

  // Add heatmap layer
  // const heatData = points.map(p => [p.lat, p.lon, p.health_index / 100]);
  // heatLayer = L.heatLayer(heatData, {
  //   radius: 20,
  //   blur: 15,
  //   maxZoom: 17,
  //   max: 1.0,
  //   gradient: {
  //     0.0: 'blue',
  //     0.5: 'yellow',
  //     1.0: 'red'
  //   }
  // }).addTo(map);

  // Fit map to bounds (only on initial load)
  if (points.length > 0 && isInitialLoad) {
    const bounds = path.getBounds();
    map.fitBounds(bounds, { padding: [50, 50] });
    isInitialLoad = false;
  }
}

// === UPDATE STATS ===
function updateStats(stats) {
  document.getElementById('totalPoints').textContent = stats.total_points || 0;
  document.getElementById('avgHealth').textContent = stats.average_health?.toFixed(1) || '-';
  document.getElementById('healthyCount').textContent = stats.healthy_count || 0;
  document.getElementById('moderateCount').textContent = stats.moderate_count || 0;
  document.getElementById('unhealthyCount').textContent = stats.unhealthy_count || 0;
  
  if (stats.bounds) {
    document.getElementById('flightInfo').textContent = 
      `Bounds: ${stats.bounds.min_lat.toFixed(6)}, ${stats.bounds.min_lon.toFixed(6)} to ${stats.bounds.max_lat.toFixed(6)}, ${stats.bounds.max_lon.toFixed(6)}`;
  }
}

// === FETCH DATA ===
async function fetchData() {
  try {
    if (isInitialLoad) {
      // Initial load: Get sampled points (last 50,000 with every 10th point = 500 points)
      const pointsRes = await fetch(`${API_BASE}/api/points?limit=${INITIAL_LOAD_LIMIT}&sample=${INITIAL_LOAD_SAMPLE_RATE}`);
      const pointsData = await pointsRes.json();
      
      if (pointsData.success && pointsData.points) {
        allPoints = pointsData.points;
        
        // Initialize map if not done
        if (!map && allPoints.length > 0) {
          const firstPoint = allPoints[0];
          initMap(firstPoint.lat, firstPoint.lon);
        }
        
        // Update map
        updateMap(allPoints);
        
        // Update last frame number
        if (allPoints.length > 0) {
          const lastPoint = allPoints[allPoints.length - 1];
          lastFrameNumber = parseInt(lastPoint.frame_number) || 0;
        }
        
        // Update last update time
        if (pointsData.last_updated) {
          const updateTime = new Date(pointsData.last_updated);
          document.getElementById('lastUpdate').textContent = 
            `Last update: ${updateTime.toLocaleTimeString()} (${pointsData.returned_count} of ${pointsData.total_points} points)`;
        }
      }
    } else {
      // Incremental update: Get only new points since last frame
      const newPointsRes = await fetch(`${API_BASE}/api/points/new?since=${lastFrameNumber}`);
      const newPointsData = await newPointsRes.json();
      
      if (newPointsData.success && newPointsData.points && newPointsData.points.length > 0) {
        // Add new points to existing array
        allPoints.push(...newPointsData.points);
        
        // Update last frame number
        const lastNewPoint = newPointsData.points[newPointsData.points.length - 1];
        lastFrameNumber = parseInt(lastNewPoint.frame_number) || lastFrameNumber;
        
        // Update map with all points
        updateMap(allPoints);
        
        // Update last update time
        document.getElementById('lastUpdate').textContent = 
          `Last update: ${new Date().toLocaleTimeString()} (+${newPointsData.new_count} new, ${newPointsData.total_points} total)`;
      }
    }

    // Fetch stats (always fetch for accurate statistics)
    const statsRes = await fetch(`${API_BASE}/api/stats`);
    const statsData = await statsRes.json();
    
    if (statsData.success) {
      updateStats(statsData);
    }
  } catch (error) {
    console.error('Error fetching data:', error);
    document.getElementById('lastUpdate').textContent = 'Error loading data';
  }
}

// === AUTO UPDATE TOGGLE ===
function toggleAutoUpdate() {
  autoUpdate = !autoUpdate;
  document.getElementById('autoUpdateStatus').textContent = `Auto: ${autoUpdate ? 'ON' : 'OFF'}`;
  
  if (autoUpdate) {
    startAutoUpdate();
  } else {
    stopAutoUpdate();
  }
}

function startAutoUpdate() {
  if (updateTimer) clearInterval(updateTimer);
  updateTimer = setInterval(fetchData, UPDATE_INTERVAL);
}

function stopAutoUpdate() {
  if (updateTimer) {
    clearInterval(updateTimer);
    updateTimer = null;
  }
}

// === INITIALIZE ===
fetchData(); // Load immediately
if (autoUpdate) {
  startAutoUpdate();
}
