// SVG Robot avatar – reused in Header and ProfileCard
export function RobotSVG({ width = 100, height = 100 }) {
  return (
    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" width={width} height={height}>
      {/* Antenna */}
      <line x1="50" y1="18" x2="50" y2="8" stroke="#a5b4fc" strokeWidth="2.5" strokeLinecap="round"/>
      <circle cx="50" cy="6" r="3.5" fill="#00e5ff" className="antenna-glow"/>
      {/* Headphone band */}
      <path d="M22 45 Q22 22, 50 20 Q78 22, 78 45" stroke="#6366f1" strokeWidth="4" fill="none" strokeLinecap="round"/>
      {/* Left ear cup */}
      <rect x="14" y="38" width="12" height="20" rx="5" fill="#6366f1"/>
      <rect x="16" y="41" width="8" height="14" rx="3" fill="#818cf8"/>
      {/* Right ear cup */}
      <rect x="74" y="38" width="12" height="20" rx="5" fill="#6366f1"/>
      <rect x="76" y="41" width="8" height="14" rx="3" fill="#818cf8"/>
      {/* Head / face */}
      <rect x="26" y="24" width="48" height="42" rx="14" fill="#1e1b4b"/>
      <rect x="29" y="27" width="42" height="36" rx="11" fill="#312e81"/>
      {/* Visor */}
      <rect x="32" y="32" width="36" height="20" rx="8" fill="#0f0b2e"/>
      {/* Eyes */}
      <circle cx="42" cy="42" r="5" fill="#00e5ff" className="eye-glow"/>
      <circle cx="42" cy="42" r="2.5" fill="#ffffff" opacity="0.8"/>
      <circle cx="58" cy="42" r="5" fill="#00e5ff" className="eye-glow"/>
      <circle cx="58" cy="42" r="2.5" fill="#ffffff" opacity="0.8"/>
      {/* Smile */}
      <path d="M42 52 Q50 58, 58 52" stroke="#00e5ff" strokeWidth="2" fill="none" strokeLinecap="round"/>
      {/* Mic boom */}
      <path d="M24 52 Q18 58, 22 65" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round"/>
      <circle cx="22" cy="67" r="3" fill="#6366f1"/>
      <circle cx="22" cy="67" r="1.5" fill="#00e5ff"/>
      {/* Body */}
      <rect x="36" y="68" width="28" height="14" rx="7" fill="#1e1b4b"/>
      <rect x="39" y="71" width="22" height="8" rx="4" fill="#312e81"/>
      <circle cx="50" cy="75" r="2.5" fill="#00e5ff" className="body-glow"/>
    </svg>
  );
}

// Launcher robot icon (small)
export function LauncherRobotIcon() {
  return (
    <svg className="icon-chat" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="12" y1="4" x2="12" y2="1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
      <circle cx="12" cy="1" r="1" fill="#00e5ff"/>
      <rect x="5" y="5" width="14" height="12" rx="4" fill="currentColor"/>
      <rect x="7" y="8" width="10" height="5.5" rx="2.2" fill="#1e1b4b"/>
      <circle cx="9.5" cy="10.8" r="1.5" fill="#00e5ff"/>
      <circle cx="14.5" cy="10.8" r="1.5" fill="#00e5ff"/>
      <path d="M10 13.5 Q12 15, 14 13.5" stroke="#00e5ff" strokeWidth="0.8" fill="none" strokeLinecap="round"/>
      <rect x="2.5" y="9" width="3" height="5.5" rx="1.3" fill="currentColor" opacity="0.8"/>
      <rect x="18.5" y="9" width="3" height="5.5" rx="1.3" fill="currentColor" opacity="0.8"/>
      <rect x="8" y="18" width="8" height="4" rx="2" fill="currentColor"/>
      <circle cx="12" cy="20" r="0.8" fill="#00e5ff"/>
    </svg>
  );
}

// Close (X) icon for launcher
export function CloseIcon() {
  return (
    <svg className="icon-close" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z" fill="currentColor"/>
    </svg>
  );
}

// Send paper-plane icon
export function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z" fill="currentColor"/>
    </svg>
  );
}
