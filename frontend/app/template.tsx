"use client";

import { motion } from "framer-motion";
import { pageTransition } from "@/lib/motion";

export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={pageTransition.initial}
      animate={pageTransition.animate}
      exit={pageTransition.exit}
      transition={pageTransition.transition}
      className="min-h-full flex flex-col"
    >
      {children}
    </motion.div>
  );
}
