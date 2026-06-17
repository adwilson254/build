import React, { useState, useEffect } from 'react';
import BottomDock from './components/BottomDock';
import WhitePanel from './components/WhitePanel';
import { ToggleRight, ToggleLeft, RefreshCw, CarFront, Zap, ImageIcon, VideoOff, Map as MapIcon, Camera, Maximize } from 'lucide-react';

export default function App() {
  const [telemetry, setTelemetry] = useState({ speed: 0, battery: 100, is_engaged: false });
  const [apiConnected, setApiConnected] = useState(true);
  const [bgMode, setBgMode] = useState('render'); // 'render', 'map', 'camera'

  // In the future, this will fetch from webd.py
  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry(prev => ({ ...prev, speed: Math.floor(Math.random() * 80) }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen relative overflow-x-hidden font-sans pb-24 transition-colors duration-500">
      
      {/* Dynamic Background */}
      <div className={`fixed inset-0 z-0 transition-opacity duration-1000 ${bgMode === 'render' ? 'opacity-100' : 'opacity-0'}`}>
        <div className="absolute inset-0 bg-gradient-to-b from-gray-300 to-gray-400"></div>
        <div className="absolute inset-0 flex flex-col items-center justify-center opacity-30">
          <CarFront size={180} className="text-gray-600 mb-6 drop-shadow-xl" />
          <h1 className="text-5xl font-bold text-gray-600 tracking-widest">OPEN RIVIAN</h1>
        </div>
      </div>

      <div className={`fixed inset-0 z-0 transition-opacity duration-1000 ${bgMode === 'map' ? 'opacity-100' : 'opacity-0'}`}>
        <div className="absolute inset-0 bg-[#e5e5e5]"></div>
        <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] mix-blend-overlay"></div>
        <div className="absolute inset-0 flex flex-col items-center justify-center opacity-50">
           <MapIcon size={120} className="text-gray-500 mb-4" />
           <h2 className="text-2xl font-bold text-gray-500">ABRP Map View</h2>
        </div>
      </div>

      <div className={`fixed inset-0 z-0 transition-opacity duration-1000 ${bgMode === 'camera' ? 'opacity-100' : 'opacity-0'}`}>
        <div className="absolute inset-0 bg-black"></div>
        <div className="absolute inset-0 flex flex-col items-center justify-center opacity-40">
           <Camera size={120} className="text-white mb-4" />
           <h2 className="text-2xl font-bold text-white">Live Camera Feed</h2>
        </div>
      </div>

      {/* Background Cycler Controls */}
      <div className="absolute top-6 right-6 z-20 flex gap-2 bg-white/40 backdrop-blur-md p-1.5 rounded-full shadow-sm border border-white/50">
        <button 
          onClick={() => setBgMode('render')}
          className={`p-2.5 rounded-full transition-all ${bgMode === 'render' ? 'bg-white shadow-md text-rivian-cyan' : 'text-gray-600 hover:bg-white/50'}`}>
          <CarFront size={20} />
        </button>
        <button 
          onClick={() => setBgMode('map')}
          className={`p-2.5 rounded-full transition-all ${bgMode === 'map' ? 'bg-white shadow-md text-rivian-cyan' : 'text-gray-600 hover:bg-white/50'}`}>
          <MapIcon size={20} />
        </button>
        <button 
          onClick={() => setBgMode('camera')}
          className={`p-2.5 rounded-full transition-all ${bgMode === 'camera' ? 'bg-white shadow-md text-rivian-cyan' : 'text-gray-600 hover:bg-white/50'}`}>
          <Camera size={20} />
        </button>
      </div>

      {/* Main Content Area (Responsive Layout) */}
      {/* On desktop (md), it's a fixed floating sidebar on the left. On mobile, it's vertically stacked below a spacer. */}
      <div className="relative z-10 p-6 pt-32 md:pt-12 md:pl-12 w-full md:w-[400px] flex flex-col gap-6">
        
        {/* Driving Models Card */}
        <WhitePanel title="Drive Modes">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button className="bg-gray-800 text-white rounded-xl py-3 font-semibold shadow-md border-2 border-rivian-cyan flex items-center justify-center gap-2">
              <Zap size={18} /> Default
            </button>
            <button className="bg-gray-100 text-gray-500 rounded-xl py-3 font-semibold hover:bg-gray-200 transition-colors">
              Chill
            </button>
            <button className="bg-gray-100 text-gray-500 rounded-xl py-3 font-semibold hover:bg-gray-200 transition-colors col-span-2">
              Experimental Route
            </button>
          </div>
          
          <div className="flex justify-between items-end border-t border-gray-200 pt-4 mt-2">
            <div className="flex flex-col">
              <span className="text-4xl font-light text-gray-800">{telemetry.speed}</span>
              <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">MPH</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-2xl font-light text-gray-800">{telemetry.battery}%</span>
              <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">DEVICE BATT</span>
            </div>
          </div>
        </WhitePanel>

        {/* Rivian API Config Card */}
        <WhitePanel title="Rivian API Config">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-700">API Connection</span>
              <label className="custom-switch">
                <input type="checkbox" checked={apiConnected} onChange={(e) => setApiConnected(e.target.checked)} />
                <span className="slider round"></span>
              </label>
            </div>

            <div className="space-y-3">
              <div>
                <input type="text" disabled={!apiConnected} className="w-full bg-white/50 border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-800 focus:outline-none focus:border-rivian-cyan transition-colors disabled:opacity-50" placeholder="user@example.com" />
              </div>
              <div>
                <input type="password" disabled={!apiConnected} className="w-full bg-white/50 border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-800 focus:outline-none focus:border-rivian-cyan transition-colors disabled:opacity-50" placeholder="••••••••" />
              </div>
            </div>
          </div>
        </WhitePanel>

        {/* Replays Card */}
        <WhitePanel title="Recent Replays">
          <div className="flex flex-col gap-2">
            {[1,2,3].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-white/50 rounded-xl hover:bg-white transition-colors cursor-pointer border border-transparent hover:border-gray-200 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                    <VideoOff size={18} />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-800">Drive #{8042 - i}</span>
                    <span className="text-[10px] text-gray-500 uppercase font-bold">{24 * i} mins ago</span>
                  </div>
                </div>
                <button className="p-2 text-gray-400 hover:text-rivian-cyan transition-colors">
                  <RefreshCw size={18} />
                </button>
              </div>
            ))}
          </div>
        </WhitePanel>
      </div>

      <BottomDock />
    </div>
  );
}
