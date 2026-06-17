import React from 'react';
import { Home, Settings, Map, Play, Car } from 'lucide-react';

const TopDownCar = () => (
  <div className="w-16 h-32 bg-gray-400 rounded-xl mx-auto border-2 border-gray-500 shadow-lg relative flex items-center justify-center text-xs text-white">CAR</div>
);

const Dock = () => (
  <div className="absolute bottom-0 w-full h-16 bg-[#1e1e1e] flex justify-around items-center text-gray-400">
    <Home /> <Car /> <Map /> <Play /> <Settings />
  </div>
);

const WhitePanel = ({ title, children, className="" }) => (
  <div className={`bg-white/80 backdrop-blur-md rounded-2xl p-4 shadow-sm border border-white/50 ${className}`}>
    <h3 className="text-sm font-bold text-gray-800 mb-2 uppercase tracking-wide">{title}</h3>
    {children}
  </div>
);

// Option 1
const Opt1 = ({ isMobile }) => (
  <div className="w-full h-full relative bg-gray-300 flex flex-col">
    {/* Background Car Render */}
    <div className="absolute inset-0 flex items-center justify-center opacity-30 text-4xl font-bold text-gray-500">3D CAR RENDER</div>
    
    <div className={`relative z-10 p-4 flex ${isMobile ? 'flex-col gap-4 mt-32' : 'w-1/3 h-full flex-col gap-4'}`}>
      <WhitePanel title="Driving Models">
        <div className="h-20 bg-gray-200 rounded-lg mb-2"></div>
        <div className="h-10 bg-gray-200 rounded-lg"></div>
      </WhitePanel>
      <WhitePanel title="Open Rivian API">
        <div className="h-8 bg-gray-200 rounded-lg mb-2"></div>
        <div className="h-8 bg-gray-200 rounded-lg"></div>
      </WhitePanel>
    </div>
    <Dock />
  </div>
);

// Option 2
const Opt2 = ({ isMobile }) => (
  <div className="w-full h-full relative bg-[#e5e5e5] p-4 pb-20 overflow-y-auto">
    <div className={`flex ${isMobile ? 'flex-col' : 'justify-between items-center h-full'}`}>
      
      {!isMobile && (
        <div className="w-1/3 flex flex-col gap-4">
          <WhitePanel title="Driving Models"><div className="h-32 bg-gray-100 rounded-lg"></div></WhitePanel>
          <WhitePanel title="Replays"><div className="h-32 bg-gray-100 rounded-lg"></div></WhitePanel>
        </div>
      )}

      <div className={`flex flex-col items-center justify-center ${isMobile ? 'mb-8 mt-4' : 'w-1/3'}`}>
        <TopDownCar />
        <div className="mt-4 text-center font-bold text-gray-700">RIVIAN R1S</div>
      </div>

      {isMobile && (
        <div className="flex flex-col gap-4">
          <WhitePanel title="Driving Models"><div className="h-24 bg-gray-100 rounded-lg"></div></WhitePanel>
          <WhitePanel title="API Config"><div className="h-24 bg-gray-100 rounded-lg"></div></WhitePanel>
        </div>
      )}

      {!isMobile && (
        <div className="w-1/3 flex flex-col gap-4">
          <WhitePanel title="Telemetry"><div className="h-32 bg-gray-100 rounded-lg"></div></WhitePanel>
          <WhitePanel title="API Config"><div className="h-32 bg-gray-100 rounded-lg"></div></WhitePanel>
        </div>
      )}

    </div>
    <Dock />
  </div>
);

// Option 3
const Opt3 = ({ isMobile }) => (
  <div className={`w-full h-full relative flex ${isMobile ? 'flex-col' : 'flex-row'}`}>
    <div className={`${isMobile ? 'h-1/2 w-full' : 'w-3/5 h-full'} bg-slate-800 flex items-center justify-center text-white font-bold`}>
      ABRP MAP
    </div>
    <div className={`${isMobile ? 'h-1/2 w-full -mt-4 rounded-t-3xl z-10' : 'w-2/5 h-full'} bg-[#f5f5f5] p-6 pb-20 overflow-y-auto shadow-2xl`}>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Open Rivian</h2>
      <WhitePanel title="Driving Models" className="mb-4"><div className="h-20 bg-gray-200 rounded-lg"></div></WhitePanel>
      <WhitePanel title="Replays" className="mb-4"><div className="h-20 bg-gray-200 rounded-lg"></div></WhitePanel>
      <WhitePanel title="API Settings"><div className="h-20 bg-gray-200 rounded-lg"></div></WhitePanel>
    </div>
    <Dock />
  </div>
);

const DeviceFrame = ({ children, isMobile, label }) => (
  <div className="flex flex-col items-center">
    <div className="text-white mb-2 font-bold">{label}</div>
    <div className={`border-8 border-gray-900 rounded-[2.5rem] overflow-hidden shadow-2xl relative bg-white ${isMobile ? 'w-[390px] h-[844px]' : 'w-[1024px] h-[600px]'}`}>
      {children}
    </div>
  </div>
);

export default function Mockups() {
  return (
    <div className="min-h-screen bg-gray-800 p-8 flex flex-col gap-24">
      <div className="text-center text-white">
        <h1 className="text-4xl font-bold">Responsive Layout Options</h1>
        <p className="mt-2 text-gray-400">Live HTML/CSS wireframes demonstrating responsive scaling.</p>
      </div>

      <div>
        <h2 className="text-3xl text-white font-bold mb-8 text-center border-b border-gray-700 pb-4">Option 1: Drive Mode Overlay</h2>
        <div className="flex flex-col xl:flex-row items-center justify-center gap-12">
          <DeviceFrame label="Laptop / Mac View" isMobile={false}><Opt1 isMobile={false}/></DeviceFrame>
          <DeviceFrame label="iPhone 17 View" isMobile={true}><Opt1 isMobile={true}/></DeviceFrame>
        </div>
      </div>

      <div>
        <h2 className="text-3xl text-white font-bold mb-8 text-center border-b border-gray-700 pb-4">Option 2: Top-Down Telemetry Hub</h2>
        <div className="flex flex-col xl:flex-row items-center justify-center gap-12">
          <DeviceFrame label="Laptop / Mac View" isMobile={false}><Opt2 isMobile={false}/></DeviceFrame>
          <DeviceFrame label="iPhone 17 View" isMobile={true}><Opt2 isMobile={true}/></DeviceFrame>
        </div>
      </div>

      <div>
        <h2 className="text-3xl text-white font-bold mb-8 text-center border-b border-gray-700 pb-4">Option 3: Split ABRP Map</h2>
        <div className="flex flex-col xl:flex-row items-center justify-center gap-12">
          <DeviceFrame label="Laptop / Mac View" isMobile={false}><Opt3 isMobile={false}/></DeviceFrame>
          <DeviceFrame label="iPhone 17 View" isMobile={true}><Opt3 isMobile={true}/></DeviceFrame>
        </div>
      </div>

    </div>
  );
}
