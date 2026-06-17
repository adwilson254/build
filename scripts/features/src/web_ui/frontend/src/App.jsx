import React, { useState, useEffect, useRef } from 'react';
import BottomDock from './components/BottomDock';
import WhitePanel from './components/WhitePanel';
import { ToggleRight, ToggleLeft, RefreshCw, CarFront, Zap, ImageIcon, VideoOff } from 'lucide-react';

const BackgroundLayer = ({ mode, stream, telemetry }) => {
  if (mode === 'map') {
    return (
      <div className="fixed inset-0 z-0 bg-[#121212] overflow-hidden">
        {/* Real Leaflet Map placeholder (currently OpenStreetMap embed, will be replaced with real GPS mapping if telemetry.gps exists) */}
        {telemetry?.gps ? (
          <iframe 
            width="100%" height="100%" frameBorder="0" scrolling="no" marginHeight="0" marginWidth="0" 
            src={`https://www.openstreetmap.org/export/embed.html?bbox=${telemetry.gps[1]-0.05}%2C${telemetry.gps[0]-0.05}%2C${telemetry.gps[1]+0.05}%2C${telemetry.gps[0]+0.05}&layer=mapnik&marker=${telemetry.gps[0]}%2C${telemetry.gps[1]}`}
            className="w-full h-full filter invert hue-rotate-180 opacity-80 pointer-events-none scale-110">
          </iframe>
        ) : (
          <iframe 
            width="100%" height="100%" frameBorder="0" scrolling="no" marginHeight="0" marginWidth="0" 
            src="https://www.openstreetmap.org/export/embed.html?bbox=-122.45%2C37.73%2C-122.35%2C37.81&layer=mapnik" 
            className="w-full h-full filter invert hue-rotate-180 opacity-80 pointer-events-none scale-110">
          </iframe>
        )}
      </div>
    );
  }
  if (mode === 'camera') {
    return (
      <div className="fixed inset-0 z-0 bg-black flex items-center justify-center">
        {stream ? (
          <video autoPlay playsInline muted className="w-full h-full object-cover opacity-80" ref={video => { if (video) video.srcObject = stream; }}></video>
        ) : (
          <div className="text-gray-500 flex flex-col items-center">
            <VideoOff size={48} className="mb-4 opacity-50" />
            <span className="animate-pulse tracking-widest text-sm uppercase">Awaiting WebRTC Stream</span>
          </div>
        )}
      </div>
    );
  }
  if (mode === 'car3d') {
    return (
      <div className="fixed inset-0 z-0 bg-gray-200">
        <iframe src='https://my.spline.design/conceptcar-e08922cfb826f7c9e12bf2ed6bba00d6/' frameBorder='0' width='100%' height='100%' className="pointer-events-none scale-125"></iframe>
      </div>
    );
  }
  if (mode === 'path') {
    return (
      <div className="fixed inset-0 z-0 bg-[#0f172a] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#0f172a] via-transparent to-[#0f172a] z-10 pointer-events-none"></div>
        {/* Fake 3D Road using CSS Transforms (Will be replaced with Canvas modelV2 drawing) */}
        <div className="absolute bottom-0 w-full h-[60vh] perspective-[1000px] flex justify-center">
           <div className="w-[300px] h-[150%] border-l-[12px] border-r-[12px] border-cyan-400 opacity-90 translate-y-20 drop-shadow-[0_0_15px_rgba(34,211,238,0.8)]" style={{ transform: 'rotateX(75deg)'}}>
              <div className="w-full h-full bg-cyan-900/20"></div>
           </div>
           {/* Fake lead car block */}
           <div className="absolute top-[20%] w-32 h-16 bg-blue-500 rounded-xl blur-sm opacity-80"></div>
        </div>
        <div className="absolute top-24 font-mono text-cyan-400 opacity-80 text-3xl font-bold tracking-widest text-center">
          <div>{telemetry.is_engaged ? 'ENGAGED' : 'DISENGAGED'}</div>
          <div className="text-6xl mt-2 text-white">{telemetry.speed.toFixed(0)} <span className="text-2xl text-gray-400">MPH</span></div>
        </div>
      </div>
    );
  }
  return null;
};

export default function App() {
  const [telemetry, setTelemetry] = useState({ speed: 0, battery: 100, is_engaged: false, gps: null, path: null });
  const [apiConnected, setApiConnected] = useState(true);
  const [stream, setStream] = useState(null);
  
  // Array of background modes
  const bgModes = ['camera', 'map', 'car3d', 'path'];
  const [bgIndex, setBgIndex] = useState(0);

  // WebRTC Local Signaling Connection
  useEffect(() => {
    let pc;
    const connectWebRTC = async () => {
      try {
        pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
        pc.addTransceiver('video', { direction: 'recvonly' });

        pc.ontrack = (event) => {
          if (event.track.kind === 'video') setStream(event.streams[0]);
        };

        pc.ondatachannel = (event) => {
          event.channel.onmessage = (e) => {
            try {
              const msg = JSON.parse(e.data);
              if (msg.type === 'carState') {
                setTelemetry(prev => ({ 
                  ...prev, 
                  speed: msg.data.vEgo * 2.23694, // Convert m/s to mph
                  is_engaged: msg.data.cruiseState?.enabled || false
                }));
              } else if (msg.type === 'liveLocationKalman') {
                setTelemetry(prev => ({ ...prev, gps: msg.data.positionGeodetic?.value }));
              }
            } catch (err) {}
          };
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // Proxy SDP Offer through our Python daemon to the local webrtcd daemon
        const response = await fetch('/api/webrtc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            initCamera: "roadCameraState",
            bridge_services_in: [],
            bridge_services_out: ["carState", "liveLocationKalman", "modelV2"]
          })
        });

        if (response.ok) {
          const answer = await response.json();
          await pc.setRemoteDescription(new RTCSessionDescription({ type: answer.type, sdp: answer.sdp }));
        } else {
          console.warn("WebRTC Signaling proxy failed. Is openpilot running?");
        }
      } catch (err) {
        console.error("WebRTC Error:", err);
      }
    };
    
    connectWebRTC();
    return () => { if (pc) pc.close(); };
  }, []);

  const cycleBackground = () => setBgIndex((prev) => (prev + 1) % bgModes.length);

  return (
    <div className="min-h-screen relative overflow-x-hidden font-sans pb-24">
      
      {/* Live Interactive Background */}
      <BackgroundLayer mode={bgModes[bgIndex]} stream={stream} telemetry={telemetry} />

      {/* Floating Background Switcher */}
      <button 
        onClick={cycleBackground}
        className="fixed top-6 right-6 z-50 bg-black/50 hover:bg-black/80 backdrop-blur-md text-white px-4 py-2 rounded-full font-bold text-sm shadow-xl border border-white/20 flex items-center gap-2 transition-all"
      >
        <ImageIcon size={18} />
        {bgModes[bgIndex].toUpperCase()} (Click to Cycle)
      </button>

      {/* Main Content Area */}
      <div className="relative z-10 p-6 pt-24 md:p-12 max-w-md md:max-w-sm flex flex-col gap-6">
        
        {/* Telemetry HUD */}
        <div className="bg-black/40 backdrop-blur-lg rounded-2xl p-4 flex justify-between items-center text-white border border-white/10 shadow-2xl">
          <div className="flex flex-col">
            <span className="text-xs text-gray-400 tracking-wider">SPEED</span>
            <span className="text-3xl font-bold font-mono">{telemetry.speed.toFixed(0)} <span className="text-sm font-sans text-gray-300">mph</span></span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-xs text-gray-400 tracking-wider">STATUS</span>
            <span className={`text-sm font-bold px-3 py-1 rounded-full mt-1 ${telemetry.is_engaged ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-400/50' : 'bg-gray-500/20 text-gray-400 border border-gray-500/50'}`}>
              {telemetry.is_engaged ? 'ENGAGED' : 'DISENGAGED'}
            </span>
          </div>
        </div>

        {/* Driving Models Card */}
        <WhitePanel title="Drive Modes">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button className="bg-gray-800 text-white rounded-xl py-3 font-semibold shadow-md border-2 border-cyan-400 flex items-center justify-center gap-2">
              <Zap size={18} /> Default
            </button>
            <button className="bg-gray-100 text-gray-500 rounded-xl py-3 font-semibold hover:bg-gray-200 transition-colors">
              Chill
            </button>
            <button className="bg-gray-100 text-gray-500 rounded-xl py-3 font-semibold hover:bg-gray-200 transition-colors">
              Aggress
            </button>
            <button className="bg-gray-100 text-gray-500 rounded-xl py-3 font-semibold hover:bg-gray-200 transition-colors">
              Experi
            </button>
          </div>
          <div className="bg-gray-100 rounded-xl p-4 flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-600">Model Auto-Update</span>
            <ToggleRight size={28} className="text-cyan-500" />
          </div>
        </WhitePanel>

        {/* API Settings Card */}
        <WhitePanel title="Rivian API Integration">
          <div className="flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-gray-200 pb-3">
              <div>
                <div className="font-semibold text-gray-800">Vehicle Sync</div>
                <div className="text-xs text-gray-500">Syncs battery and climate data</div>
              </div>
              <button onClick={() => setApiConnected(!apiConnected)}>
                {apiConnected ? <ToggleRight size={32} className="text-cyan-500" /> : <ToggleLeft size={32} className="text-gray-400" />}
              </button>
            </div>
            
            <div className="flex justify-between items-center border-b border-gray-200 pb-3">
              <div>
                <div className="font-semibold text-gray-800">Location Sharing</div>
                <div className="text-xs text-gray-500">Required for ABRP routing</div>
              </div>
              <ToggleRight size={32} className="text-cyan-500" />
            </div>

            <button className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors">
              <RefreshCw size={18} /> Force Sync Now
            </button>
          </div>
        </WhitePanel>

        {/* Replays Card */}
        <WhitePanel title="Recent Drives">
          <div className="flex flex-col gap-3">
            <div className="bg-gray-100 rounded-xl p-3 flex justify-between items-center cursor-pointer hover:bg-gray-200 transition-colors">
              <div>
                <div className="font-bold text-gray-800">Home to Work</div>
                <div className="text-xs text-gray-500">Today, 8:42 AM • 12 miles</div>
              </div>
              <div className="bg-green-100 text-green-700 font-bold px-3 py-1 rounded-full text-xs">
                Score: 98
              </div>
            </div>
            
            <div className="bg-gray-100 rounded-xl p-3 flex justify-between items-center cursor-pointer hover:bg-gray-200 transition-colors">
              <div>
                <div className="font-bold text-gray-800">Grocery Store</div>
                <div className="text-xs text-gray-500">Yesterday, 5:15 PM • 4 miles</div>
              </div>
              <div className="bg-yellow-100 text-yellow-700 font-bold px-3 py-1 rounded-full text-xs">
                Score: 84
              </div>
            </div>
            
            <button className="text-sm font-semibold text-cyan-600 text-center mt-2 hover:underline">
              View All Replays
            </button>
          </div>
        </WhitePanel>

      </div>

      <BottomDock />
    </div>
  );
}
