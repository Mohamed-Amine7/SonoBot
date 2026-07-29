import { renderMarkdown } from '../utils/markdown';

// A single message bubble (user or bot)
export function Message({ text, sender }) {
  if (sender === 'bot') {
    return (
      <div
        className="sb-message sb-message-bot"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
      />
    );
  }
  return (
    <div className="sb-message sb-message-user">
      {text}
    </div>
  );
}

// Animated typing dots
export function TypingIndicator() {
  return (
    <div className="sb-typing">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
  );
}

const STEP_LABELS = { 1: 'Étape 1/4', 2: 'Étape 2/4', 3: 'Étape 3/4', 4: 'Étape 4/4' };

// Guided conversation option buttons
export function GuideOptions({ options, step, criteria, onSelect }) {
  return (
    <div className="sb-guide-options">
      <div className="sb-guide-step-label">{STEP_LABELS[step] || ''}</div>
      {options.map((opt) => (
        <button
          key={opt.value}
          className={`sb-guide-btn${opt.selected ? ' selected' : ''}`}
          disabled={opt.disabled}
          onClick={() => onSelect(opt, step, criteria)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
