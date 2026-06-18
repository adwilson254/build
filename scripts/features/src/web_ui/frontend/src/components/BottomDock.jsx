import React from 'react';
import { Home, Map, Car, Settings, Video } from 'lucide-react';

export default function BottomDock() {
  return (
    <div className="fixed bottom-0 left-0 w-full h-20 bg-[#121212] flex justify-around items-center border-t border-gray-800 shadow-[0_-10px_40px_rgba(0,0,0,0.5)] z-50">
      <button className="flex flex-col items-center text-rivian-cyan gap-1 transition-transform active:scale-95">
        <Home size={24} />
      </button>
      <button className="flex flex-col items-center text-gray-400 hover:text-white transition-colors gap-1 active:scale-95">
        <Map size={24} />
      </button>
      <button className="flex flex-col items-center text-gray-400 hover:text-white transition-colors gap-1 active:scale-95">
        <Car size={24} />
      </button>
      <button className="flex flex-col items-center text-gray-400 hover:text-white transition-colors gap-1 active:scale-95">
        <Video size={24} />
      </button>
      <button className="flex flex-col items-center text-gray-400 hover:text-white transition-colors gap-1 active:scale-95">
        <Settings size={24} />
      </button>
    </div>
  );
}
