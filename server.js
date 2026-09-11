// NexSolve Backend REST API Server (Node.js / Express)
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;

// Mock Real-Time Disaster Data Store
const nerDistricts = [
  { id: 'champhai', state: 'Mizoram', name: 'Champhai District', lat: 23.4756, lng: 93.3289, riskScore: 92, status: 'Critical', rain24h: 146, soilSat: 88, slopeAngle: 42, gsiEvents: 14 },
  { id: 'aizawl', state: 'Mizoram', name: 'Aizawl Capital Corridor', lat: 23.7271, lng: 92.7176, riskScore: 64, status: 'High', rain24h: 108, soilSat: 74, slopeAngle: 36, gsiEvents: 8 },
  { id: 'senapati', state: 'Manipur', name: 'Senapati NH-2 Corridor', lat: 25.2686, lng: 94.0186, riskScore: 88, status: 'Critical', rain24h: 138, soilSat: 85, slopeAngle: 44, gsiEvents: 16 },
  { id: 'cherrapunji', state: 'Meghalaya', name: 'Sohra / Cherrapunji Plateau', lat: 25.2700, lng: 91.7320, riskScore: 84, status: 'Critical', rain24h: 194, soilSat: 91, slopeAngle: 40, gsiEvents: 19 }
];

const roadCorridors = [
  { code: 'NH-306', name: 'Silchar – Aizawl Axis', status: 'BLOCKED', eta: '4-6 Hours' },
  { code: 'NH-2', name: 'Dimapur – Imphal Hwy', status: 'BLOCKED', eta: '8-12 Hours' },
  { code: 'NH-10', name: 'Gangtok – Siliguri Axis', status: 'RESTRICTED', eta: 'Monitored 24/7' },
  { code: 'NH-6', name: 'Guwahati – Shillong Expressway', status: 'OPEN', eta: 'Normal' }
];

const fieldReports = [];

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // --- REST API ENDPOINTS ---
  if (url.pathname === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ONLINE', uptime: process.uptime(), timestamp: new Date().toISOString() }));
    return;
  }

  if (url.pathname === '/api/districts') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, count: nerDistricts.length, data: nerDistricts }));
    return;
  }

  if (url.pathname === '/api/corridors') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, count: roadCorridors.length, data: roadCorridors }));
    return;
  }

  if (url.pathname === '/api/reports' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      try {
        const payload = JSON.parse(body || '{}');
        const report = {
          id: 'REP-' + Date.now(),
          type: payload.type || 'Landslide Observation',
          location: payload.location || 'NER Corridor',
          aiConfidence: 95.4,
          verified: true,
          createdAt: new Date().toISOString()
        };
        fieldReports.unshift(report);
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, message: 'Report processed by AI engine', report }));
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON payload' }));
      }
    });
    return;
  }

  // --- STATIC FILE SERVER ---
  let filePath = path.join(__dirname, url.pathname === '/' ? 'index.html' : url.pathname);
  const ext = path.extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('404 Not Found');
      } else {
        res.writeHead(500);
        res.end(`Server Error: ${err.code}`);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

server.listen(PORT, () => {
  console.log(`⚡ NexSolve High-End Backend Server running at http://localhost:${PORT}`);
});
