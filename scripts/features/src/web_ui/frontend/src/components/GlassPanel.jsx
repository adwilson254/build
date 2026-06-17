import React from 'react';
import { motion } from 'framer-motion';

export default function GlassPanel({ title, children, className = "", delay = 0 }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: delay, ease: [0.16, 1, 0.3, 1] }}
      className={`glass-panel neon-border p-4 ${className}`}
    >
      {title && (
        <h3 className="text-sm font-bold text-gray-300 mb-3 px-1">{title}</h3>
      )}
      {children}
    </motion.div>
  );
}
