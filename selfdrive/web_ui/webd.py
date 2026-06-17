#!/usr/bin/env python3
import os
import json
import asyncio
from aiohttp import web
from openpilot.common.params import Params

# Get the directory of this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, 'frontend', 'dist')

class WebServer:
    def __init__(self):
        self.app = web.Application()
        self.params = Params()
        self.setup_routes()

    def setup_routes(self):
        # API Routes
        self.app.router.add_get('/api/params/{key}', self.get_param)
        self.app.router.add_post('/api/params/{key}', self.set_param)
        self.app.router.add_get('/api/telemetry', self.get_telemetry)

        # Static file serving for the React App
        if os.path.exists(FRONTEND_DIST):
            self.app.router.add_static('/assets', os.path.join(FRONTEND_DIST, 'assets'))
            # Route all other GET requests to index.html for SPA routing
            self.app.router.add_get('/{tail:.*}', self.serve_index)
        else:
            print(f"Warning: Frontend dist folder not found at {FRONTEND_DIST}. UI will not load.")

    async def get_param(self, request):
        key = request.match_info['key']
        val = self.params.get(key)
        if val is None:
            return web.json_response({'error': 'Not found'}, status=404)
        
        try:
            val_str = val.decode('utf-8')
        except:
            val_str = str(val)
            
        return web.json_response({'key': key, 'value': val_str})

    async def set_param(self, request):
        key = request.match_info['key']
        data = await request.json()
        if 'value' not in data:
            return web.json_response({'error': 'Missing value'}, status=400)
            
        val = data['value']
        if isinstance(val, bool):
            self.params.put_bool(key, val)
        else:
            self.params.put(key, str(val))
            
        return web.json_response({'success': True})

    async def get_telemetry(self, request):
        # Stub for telemetry. We will wire this up to cereal later.
        # For now, return mock data.
        mock_data = {
            "speed": 65.2,
            "score": 94,
            "status": "engaged",
            "model_path": []
        }
        return web.json_response(mock_data)

    async def serve_index(self, request):
        index_path = os.path.join(FRONTEND_DIST, 'index.html')
        if os.path.exists(index_path):
            return web.FileResponse(index_path)
        return web.Response(text="Frontend not built. Please run 'npm run build' in the frontend directory.", status=404)

def main():
    server = WebServer()
    print("Starting OpenRivian Web UI on port 8080...")
    web.run_app(server.app, host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main()
