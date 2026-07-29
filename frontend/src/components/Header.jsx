import { RobotSVG, CloseIcon } from './Icons';

export function Header({ onClose }) {
  return (
    <div className="sb-header">
      <div className="sb-header-left">
        <div className="sb-avatar">
          <RobotSVG width={32} height={32} />
          <span className="sb-status-dot" />
        </div>
        <div className="sb-header-title">
          <h3>SonoBot</h3>
          <p>Assistant SonoLight 💡</p>
        </div>
      </div>
      <button className="sb-close-btn" onClick={onClose} aria-label="Fermer">
        <CloseIcon />
      </button>
    </div>
  );
}
