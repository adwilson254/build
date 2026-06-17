import React from 'react';

export default function WidgetPanel({ title, children, className = "" }) {
  return (
    <div className={`bg-rivian-panel border border-white/5 rounded-2xl shadow-xl flex flex-col overflow-hidden relative ${className}`}>
      {/* Subtle top gradient line to give a premium feel */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
      
      {title && (
        <div className="bg-black/20 p-4 border-b border-white/5">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">{title}</h3>
        </div>
      )}
      <div className="p-5 flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
