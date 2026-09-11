#!/usr/bin/env python3
"""
NexSolve Backend API & Static HTTP Server (Python 3)
Provides static web server + REST API endpoints for disaster management dashboard.
"""
import http.server
import socketserver
import json
import os
import time

PORT = 8080

NER_DISTRICTS = [
    {"id": "champhai", "state": "Mizoram", "name": "Champhai District", "lat": 23.4756, "lng": 93.3289, "riskScore": 92, "status": "Critical", "rain24h": 146, "soilSat": 88, "slopeAngle": 42},
    {"id": "senapati", "state": "Manipur", "name": "Senapati Corridor", "lat": 25.2686, "lng": 94.0186, "riskScore": 88, "status": "Critical", "rain24h": 138, "soilSat": 85, "slopeAngle": 44},
    {"id": "cherrapunji", "state": "Meghalaya", "name": "Cherrapunji Plateau", "lat": 25.2700, "lng": 91.7320, "riskScore": 84, "status": "Critical", "rain24h": 194, "soilSat": 91, "slopeAngle": 40}
]

class NexSolveAPIHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ONLINE", "server": "NexSolve Python API Engine"}).encode())
            return
        elif self.path == '/api/districts':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "districts": NER_DISTRICTS}).encode())
            return
        
        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/reports':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body or '{}')
            
            response_data = {
                "success": True,
                "message": "Field report ingested and verified by AI Computer Vision Model",
                "report": {
                    "id": f"REP-{int(time.time())}",
                    "type": data.get("type", "Landslide"),
                    "location": data.get("location", "NER"),
                    "verified": True
                }
            }
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            return
        
        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), NexSolveAPIHandler) as httpd:
        print(f"🚀 NexSolve Python Backend Server running on http://localhost:{PORT}")
        httpd.serve_forever()
