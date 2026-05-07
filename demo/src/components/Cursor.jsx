import React from 'react';
import { motion } from 'framer-motion';

export default function Cursor({ position, clicking }) {
  return (
    <motion.div
      className="absolute pointer-events-none z-50"
      animate={{ x: position.x, y: position.y }}
      transition={{ type: 'spring', stiffness: 80, damping: 18 }}
      style={{ top: 0, left: 0 }}
    >
      {/* Click pulse */}
      {clicking && (
        <motion.div
          initial={{ scale: 0.4, opacity: 0.7 }}
          animate={{ scale: 2.2, opacity: 0 }}
          transition={{ duration: 0.5 }}
          className="absolute -top-3 -left-3 w-10 h-10 rounded-full bg-[#be0f2e]"
        />
      )}
      {/* Cursor SVG */}
      <svg
        width="22"
        height="28"
        viewBox="0 0 22 28"
        fill="none"
        style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.4))' }}
      >
        <path
          d="M2 2 L20 14 L12 16 L18 26 L14 28 L8 18 L2 22 Z"
          fill="white"
          stroke="black"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    </motion.div>
  );
}
