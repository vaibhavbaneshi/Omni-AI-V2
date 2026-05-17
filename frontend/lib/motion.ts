export const premiumEasing = [0.16, 1, 0.3, 1];

export const pageTransition = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.5, ease: premiumEasing },
};

export const fadeUpVariant = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 8 },
  transition: { duration: 0.4, ease: premiumEasing },
};

export const staggerContainer = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

export const sidebarTransition = {
  initial: { width: 0, opacity: 0 },
  animate: { width: 260, opacity: 1 },
  exit: { width: 0, opacity: 0 },
  transition: { duration: 0.25, ease: premiumEasing },
};

export const pulseAnimation = {
  initial: { opacity: 0.3 },
  animate: { opacity: [0.3, 1, 0.3] },
  transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
};
