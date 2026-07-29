import { RobotSVG } from './Icons';

const QUICK_ACTIONS = [
  { label: '🛒 Voir les produits', msg: 'Quels produits avez-vous ?' },
  { label: '💰 Prix',              msg: 'Quels sont les prix ?' },
  { label: '🚚 Livraison',         msg: 'Comment se fait la livraison ?' },
];

export function ProfileCard({ onChipClick, onGuideClick }) {
  return (
    <div className="sb-profile-card">
      <div className="sb-profile-avatar-large">
        <RobotSVG width={56} height={56} />
      </div>

      <h4 className="sb-profile-name">
        SonoBot <span className="sb-verified">✓</span>
      </h4>
      <p className="sb-profile-role">Assistant IA • SonoLight</p>
      <p className="sb-profile-desc">
        Votre expert en éclairage professionnel, matériel DJ et effets laser.
        Disponible 24/7 pour vous aider ! 🎵💡
      </p>

      <div className="sb-profile-stats">
        <div className="sb-stat">
          <span className="sb-stat-value">24/7</span>
          <span className="sb-stat-label">Disponible</span>
        </div>
        <div className="sb-stat">
          <span className="sb-stat-value">⚡</span>
          <span className="sb-stat-label">Rapide</span>
        </div>
        <div className="sb-stat">
          <span className="sb-stat-value">🇲🇦</span>
          <span className="sb-stat-label">Maroc</span>
        </div>
      </div>

      <div className="sb-quick-actions">
        {QUICK_ACTIONS.map(({ label, msg }) => (
          <button key={msg} className="sb-chip" onClick={() => onChipClick(msg)}>
            {label}
          </button>
        ))}
      </div>

      <button className="sb-guide-cta" onClick={onGuideClick}>
        <span className="sb-guide-cta-icon">🧭</span>
        <span className="sb-guide-cta-text">
          <strong>Guide d'achat</strong>
          <small>Je vous aide étape par étape</small>
        </span>
        <span className="sb-guide-cta-arrow">→</span>
      </button>
    </div>
  );
}

