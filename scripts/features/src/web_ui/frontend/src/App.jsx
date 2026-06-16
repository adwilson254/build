import React, { useState, useEffect } from 'react';
import { Settings, Home, Car, Music, Wind, Battery, Signal, User, Play, RefreshCw, Key } from 'lucide-react';

export default function App() {
  const [apiStatus, setApiStatus] = useState('Checking...');
  const [apiToken, setApiToken] = useState('');
  const [time, setTime] = useState('');

  useEffect(() => {
    // Update clock
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleRefreshKey = async () => {
    try {
      const res = await fetch('/api/params/RivianApiStatus');
      const data = await res.json();
      setApiStatus(data.value || 'Not configured');
    } catch (e) {
      setApiStatus('Disconnected (Offline)');
    }
  };

  useEffect(() => {
    handleRefreshKey();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-rivian-darker text-white font-sans overflow-hidden">
      
      {/* Top Status Bar */}
      <div className="flex justify-between items-center px-6 py-2 bg-black/80 text-sm text-gray-400 z-10">
        <div className="flex items-center gap-4">
          <span>Time: {time}</span>
          <div className="flex items-center gap-1">
            <Battery size={16} />
            <span>92% | 310 mi</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-1">
            <span>Signal</span>
            <Signal size={16} />
          </div>
          <div className="flex items-center gap-2">
            <span>Profile: User</span>
            <User size={16} />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex gap-6 p-6 bg-gradient-to-br from-neutral-800 to-stone-900 overflow-y-auto">
        
        {/* Column 1: Driving Models */}
        <div className="flex-1 glass-panel flex flex-col overflow-hidden">
          <div className="bg-rivian-yellow text-black font-bold px-4 py-2 flex justify-between">
            <span>DRIVING MODELS</span>
            <span>SPORT</span>
          </div>
          <div className="p-6 flex flex-col gap-6 flex-1">
            <h2 className="text-2xl font-light">R1S 3D</h2>
            <div className="h-40 bg-black/30 rounded-xl flex items-center justify-center border border-white/5">
              <span className="text-gray-500">Vehicle Render</span>
            </div>
            
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-gray-400">Current mode:</span>
              <span className="text-rivian-yellow font-bold">SPORT</span>
            </div>
            
            <div className="flex flex-col gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Suspension:</span>
                <span>Stiff</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Steering:</span>
                <span>Sporty</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Stability:</span>
                <span>Dynamic</span>
              </div>
            </div>

            <div className="mt-auto pt-4">
              <button className="w-full bg-rivian-yellow hover:bg-yellow-400 text-black font-bold py-3 rounded-lg transition-colors">
                CHANGE MODE
              </button>
            </div>
          </div>
        </div>

        {/* Column 2: Rivian API Config */}
        <div className="flex-1 glass-panel flex flex-col overflow-hidden">
          <div className="bg-rivian-yellow text-black font-bold px-4 py-2">
            SETTING PANEL: RIVIAN API CONFIGURATION
          </div>
          <div className="p-6 flex flex-col gap-6 flex-1">
            <h2 className="text-2xl font-light uppercase tracking-wider">Rivian API Config</h2>
            
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-300">API Key Management</span>
                <div className="w-10 h-6 bg-rivian-cyan rounded-full flex items-center px-1">
                  <div className="w-4 h-4 bg-white rounded-full translate-x-4"></div>
                </div>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-400">Key Status:</span>
                <span className={apiStatus.includes('Offline') ? 'text-red-400' : 'text-green-400'}>
                  {apiStatus}
                </span>
              </div>
              <button onClick={handleRefreshKey} className="w-full bg-white/10 hover:bg-white/20 text-white font-medium py-2 rounded-lg flex items-center justify-center gap-2 transition-colors border border-white/10">
                <RefreshCw size={16} /> REFRESH KEY
              </button>
            </div>

            <div className="flex flex-col gap-2 mt-4">
              <span className="text-gray-400 text-sm">Permissions</span>
              <div className="flex justify-between items-center text-sm">
                <span>Location</span>
                <div className="w-10 h-6 bg-rivian-cyan rounded-full flex items-center px-1">
                  <div className="w-4 h-4 bg-white rounded-full translate-x-4"></div>
                </div>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span>Telemetry</span>
                <div className="w-10 h-6 bg-rivian-cyan rounded-full flex items-center px-1">
                  <div className="w-4 h-4 bg-white rounded-full translate-x-4"></div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-4">
              <button className="w-full bg-rivian-yellow hover:bg-yellow-400 text-black font-bold py-3 rounded-lg transition-colors">
                UPDATE SETTINGS
              </button>
            </div>
          </div>
        </div>

        {/* Column 3: Replays */}
        <div className="flex-1 glass-panel flex flex-col overflow-hidden">
          <div className="bg-rivian-yellow text-black font-bold px-4 py-2">
            REPLAYS
          </div>
          <div className="p-6 flex flex-col gap-6 flex-1 overflow-y-auto">
            <h2 className="text-lg text-gray-300 uppercase tracking-wider">Recent Replays</h2>
            
            {[
              { title: "*Mountain Pass Run", date: "28/10/23, 4:20 PM - 38 min" },
              { title: "*Highway Cruise", date: "27/10/23, 10:15 AM - 55 min" },
              { title: "*Canyon Drive", date: "26/10/23, 2:30 PM - 22 min" }
            ].map((replay, idx) => (
              <div key={idx} className="flex flex-col gap-2 pb-4 border-b border-white/10 last:border-0">
                <span className="font-medium text-sm text-gray-200">{replay.title} - {replay.date}</span>
                <div className="flex gap-2">
                  <div className="flex-1 h-16 bg-black/40 rounded-lg border border-white/5"></div>
                  <div className="flex-1 h-16 bg-black/40 rounded-lg flex flex-col justify-center items-center border border-white/5">
                    <button className="bg-white/10 hover:bg-white/20 w-full h-full rounded-lg flex items-center justify-center gap-2 transition-colors text-sm text-gray-300">
                      <Play size={14} /> PLAY
                    </button>
                  </div>
                </div>
              </div>
            ))}

          </div>
        </div>

      </div>

      {/* Bottom Navigation Dock */}
      <div className="flex justify-around items-center px-6 py-4 bg-black/95 border-t border-white/10 z-10">
        <div className="flex flex-col items-center gap-1 text-rivian-yellow cursor-pointer">
          <Home size={24} />
          <span className="text-[10px] tracking-wider font-semibold">HOME</span>
        </div>
        <div className="flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors cursor-pointer">
          <Car size={24} />
          <span className="text-[10px] tracking-wider font-semibold">DRIVING MODELS</span>
        </div>
        <div className="flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors cursor-pointer">
          <Settings size={24} />
          <span className="text-[10px] tracking-wider font-semibold">SETTINGS</span>
        </div>
        <div className="flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors cursor-pointer">
          <Music size={24} />
          <span className="text-[10px] tracking-wider font-semibold">MEDIA</span>
        </div>
        <div className="flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors cursor-pointer">
          <Wind size={24} />
          <span className="text-[10px] tracking-wider font-semibold">CLIMATE</span>
        </div>
      </div>
    </div>
  );
}
