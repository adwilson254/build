import React from 'react';

export default function WhitePanel({ title, children, className = "" }) {
  return (
    <div className={`bg-white/90 backdrop-blur-xl rounded-[1.5rem] p-5 shadow-lg border border-white/60 ${className}`}>
      {title && (
        <h3 className="text-sm font-bold text-gray-800 mb-4 uppercase tracking-wider">{title}</h3>
      )}
      {children}
    </div>
  );
}
