import { useState, useRef, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { ProfileCard } from './components/ProfileCard';
import { Message, TypingIndicator, GuideOptions } from './components/Message';
import { LauncherRobotIcon, CloseIcon, SendIcon } from './components/Icons';
import './index.css';

// Stable session ID for this browser tab
const SESSION_ID = crypto.randomUUID
  ? crypto.randomUUID()
  : 'sb-' + Date.now() + '-' + Math.random().toString(36).slice(2);

// API endpoints
// In dev: Vite proxies /api → http://localhost:5000
// In production (Joomla): set VITE_API_BASE in .env.production
const API_BASE  = import.meta.env.VITE_API_BASE ?? '';
const API_CHAT  = `${API_BASE}/api/chat`;
const API_GUIDE = `${API_BASE}/api/guide`;

// A chat "item" can be: a message, a typing indicator, or guide options
// type: 'message' | 'guide'
// For 'guide': { options, step, criteria, disabled: false, selectedValue: null }

export default function App() {
  const [isOpen,   setIsOpen]   = useState(false);
  const [items,    setItems]    = useState([]);        // chat items
  const [typing,   setTyping]   = useState(false);
  const [input,    setInput]    = useState('');
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom whenever items or typing change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items, typing]);

  // Add a message bubble
  const addMessage = useCallback((text, sender) => {
    setItems(prev => [...prev, { id: Date.now() + Math.random(), type: 'message', text, sender }]);
  }, []);

  // Add a guide options block
  const addGuideOptions = useCallback((options, step, criteria) => {
    setItems(prev => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        type: 'guide',
        options,
        step,
        criteria,
        disabled: false,
        selectedValue: null,
      },
    ]);
  }, []);

  // Disable all buttons of a guide block and mark selected
  const selectGuideOption = useCallback((itemId, selectedValue) => {
    setItems(prev =>
      prev.map(item =>
        item.id === itemId
          ? { ...item, disabled: true, selectedValue }
          : item
      )
    );
  }, []);

  // Handle API response (shared between /chat and /guide)
  const handleApiResponse = useCallback((data) => {
    setTyping(false);
    if (!data) return;
    if (data.type === 'guide') {
      addMessage(data.response, 'bot');
      addGuideOptions(data.options, data.step, data.criteria || {});
    } else if (data.response) {
      addMessage(data.response, 'bot');
    } else {
      addMessage("Désolé, je n'ai pas compris la réponse.", 'bot');
    }
  }, [addMessage, addGuideOptions]);

  const handleApiError = useCallback((err) => {
    setTyping(false);
    console.error('Chatbot error:', err);
    let msg = err.message || 'Erreur de connexion.';
    if (msg === 'Failed to fetch' || msg.includes('network')) {
      msg = 'Impossible de contacter le serveur Flask (localhost:5000). Vérifiez que le backend est démarré.';
    }
    addMessage(msg, 'bot');
  }, [addMessage]);

  // Main send handler
  const handleSend = useCallback(async (text) => {
    const msg = (text ?? input).trim();
    if (!msg) return;
    setInput('');
    addMessage(msg, 'user');
    setTyping(true);

    try {
      const res = await fetch(API_CHAT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, session_id: SESSION_ID }),
      });

      if (!res.ok) {
        let errMsg = 'API Connection Failed';
        try {
          const errJson = await res.json();
          errMsg = errJson.response || errJson.error || errMsg;
        } catch (_) {}
        throw new Error(errMsg);
      }

      const data = await res.json();
      handleApiResponse(data);
    } catch (err) {
      handleApiError(err);
    }
  }, [input, addMessage, handleApiResponse, handleApiError]);

  // Guide option click
  const handleGuideSelect = useCallback(async (opt, step, criteria, itemId) => {
    selectGuideOption(itemId, opt.value);
    addMessage(opt.label, 'user');
    setTyping(true);

    try {
      const res = await fetch(API_GUIDE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step, answer: opt.value, criteria }),
      });

      if (!res.ok) throw new Error('Guide API error');
      const data = await res.json();
      handleApiResponse(data);
    } catch (err) {
      handleApiError(err);
    }
  }, [selectGuideOption, addMessage, handleApiResponse, handleApiError]);

  // Start the guide flow directly (calls /api/guide step 0 → returns step 1)
  const handleStartGuide = useCallback(async () => {
    addMessage('🧭 Guide d\'achat', 'user');
    setTyping(true);

    try {
      const res = await fetch(API_GUIDE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: 0, answer: '', criteria: {} }),
      });

      if (!res.ok) throw new Error('Guide API error');
      const data = await res.json();
      handleApiResponse(data);
    } catch (err) {
      handleApiError(err);
    }
  }, [addMessage, handleApiResponse, handleApiError]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  const openChat = () => {
    setIsOpen(true);
    // Show welcome message only on first open
    if (items.length === 0) {
      addMessage(
        "Bonjour ! 😊 Je suis SonoBot, votre assistant SonoLight. Je peux vous aider à trouver des produits, vérifier les prix et la disponibilité. Comment puis-je vous aider ?",
        'bot'
      );
    }
  };

  const closeChat = () => setIsOpen(false);

  return (
    <div className="sb-widget">
      {/* Chat window */}
      <div className={`sb-window${isOpen ? '' : ' hidden'}`}>
        <Header onClose={closeChat} />

        <div className="sb-messages">
          <ProfileCard onChipClick={(msg) => handleSend(msg)} onGuideClick={handleStartGuide} />

          {items.map((item) => {
            if (item.type === 'message') {
              return <Message key={item.id} text={item.text} sender={item.sender} />;
            }
            if (item.type === 'guide') {
              return (
                <GuideOptions
                  key={item.id}
                  options={item.options.map(opt => ({
                    ...opt,
                    disabled: item.disabled,
                    selected: item.selectedValue === opt.value,
                  }))}
                  step={item.step}
                  criteria={item.criteria}
                  onSelect={(opt) => !item.disabled && handleGuideSelect(opt, item.step, item.criteria, item.id)}
                />
              );
            }
            return null;
          })}

          {typing && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        <div className="sb-input-area">
          <input
            className="sb-input"
            type="text"
            placeholder="Posez votre question sur nos produits..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            autoComplete="off"
          />
          <button className="sb-send-btn" onClick={() => handleSend()} aria-label="Envoyer">
            <SendIcon />
          </button>
        </div>
      </div>

      {/* Floating launcher button */}
      <button
        className={`sb-launcher${isOpen ? ' open' : ''}`}
        onClick={isOpen ? closeChat : openChat}
        aria-label={isOpen ? 'Fermer le chatbot' : 'Ouvrir le chatbot'}
      >
        <LauncherRobotIcon />
        <CloseIcon />
      </button>
    </div>
  );
}
