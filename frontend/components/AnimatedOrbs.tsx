"use client";

import { motion } from "framer-motion";

export default function AnimatedOrbs() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-grid-glow" />
      <motion.div
        className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-signal/20 blur-3xl animate-floaty"
        style={{ animationDelay: "0s" }}
      />
      <motion.div
        className="absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-intel/15 blur-3xl animate-floaty"
        style={{ animationDelay: "1.5s" }}
      />
      <motion.div
        className="absolute right-1/4 top-1/3 h-56 w-56 rounded-full bg-violet/10 blur-3xl animate-floaty"
        style={{ animationDelay: "3s" }}
      />
    </div>
  );
}
