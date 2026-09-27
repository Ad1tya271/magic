"""Embedded interactive web UI for Vera Bot — Conversational Vendor Journey with Violet & Crème Theme."""
from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vera — Merchant Assistance Partner</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      /* Violet and Crème Color Palette */
      --bg-canvas: #140726;
      --bg-gradient: radial-gradient(circle at 50% 10%, #290e4f 0%, #140726 80%, #0c0317 100%);
      
      --creme-pure: #fefcf8;
      --creme-warm: #f7f2e7;
      --creme-soft: #eee5d3;
      --creme-muted: #d0c4b0;
      --creme-border: rgba(254, 252, 248, 0.14);
      --creme-border-hover: rgba(254, 252, 248, 0.32);

      --violet-deep: #1e0938;
      --violet-card: rgba(30, 9, 56, 0.85);
      --violet-primary: #7c3aed;
      --violet-accent: #8b5cf6;
      --violet-light: #c084fc;
      --violet-glow: rgba(139, 92, 246, 0.3);

      --text-creme: #fefcf8;
      --text-creme-muted: #cdbfad;
      --text-dark: #160428;

      /* WhatsApp & Chat Tokens */
      --wa-chat-bg: #10051e;
      --wa-bot-bubble: #fdfbf7;
      --wa-bot-text: #17042a;
      --wa-user-bubble: #7c3aed;
      --wa-user-text: #fefcf8;
      --wa-input-bg: #f8f4ec;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      background: var(--bg-gradient);
      color: var(--text-creme);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Clean, Modern Header */
    header {
      border-bottom: 1px solid var(--creme-border);
      background: rgba(20, 7, 38, 0.92);
      backdrop-filter: blur(20px);
      padding: 0.85rem 1.75rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }

    .brand-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, var(--creme-soft), var(--violet-accent));
      color: var(--violet-deep);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.25rem;
      box-shadow: 0 4px 14px var(--violet-glow);
    }

    .brand-title {
      font-size: 1.1rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--creme-pure);
    }

    .brand-subtitle {
      font-size: 0.72rem;
      color: var(--text-creme-muted);
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }

    .vendor-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.4rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.76rem;
      font-weight: 600;
      background: rgba(254, 252, 248, 0.08);
      border: 1px solid var(--creme-border);
      color: var(--creme-soft);
      max-width: 280px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .vendor-badge.selected {
      background: rgba(124, 58, 237, 0.22);
      border-color: rgba(192, 132, 252, 0.45);
      color: #e9d5ff;
    }

    .pulse {
      width: 7px;
      height: 7px;
      background: #a78bfa;
      border-radius: 50%;
      box-shadow: 0 0 8px #a78bfa;
      animation: pulse 2s infinite;
      flex-shrink: 0;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    .btn-switch-vendor {
      appearance: none;
      border: 1px solid var(--creme-border);
      background: rgba(254, 252, 248, 0.08);
      color: var(--creme-soft);
      font-family: inherit;
      font-weight: 600;
      font-size: 0.76rem;
      padding: 0.4rem 0.85rem;
      border-radius: 9999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s ease;
    }
    .btn-switch-vendor:hover {
      background: rgba(124, 58, 237, 0.28);
      border-color: var(--violet-light);
      color: #fff;
    }

    .btn-reset-session {
      appearance: none;
      border: 1px solid var(--creme-border);
      background: var(--creme-warm);
      color: var(--violet-deep);
      font-family: inherit;
      font-weight: 700;
      font-size: 0.76rem;
      padding: 0.4rem 0.95rem;
      border-radius: 9999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    }
    .btn-reset-session:hover {
      background: var(--creme-pure);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
    }

    /* Primary Chat-First Layout */
    main {
      flex: 1;
      max-width: 960px;
      margin: 0 auto;
      width: 100%;
      padding: 1.25rem 1rem;
      display: flex;
      flex-direction: column;
    }

    .chat-container {
      flex: 1;
      background: var(--violet-card);
      border: 1px solid var(--creme-border);
      border-radius: 24px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: calc(100vh - 110px);
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 35px rgba(124, 58, 237, 0.15);
      backdrop-filter: blur(18px);
    }

    .chat-subhead {
      background: rgba(22, 6, 42, 0.85);
      padding: 0.7rem 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--creme-border);
      font-size: 0.74rem;
      color: var(--creme-muted);
    }

    .chat-status-indicator {
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }

    .chat-box {
      flex: 1;
      background: var(--wa-chat-bg);
      background-image: radial-gradient(rgba(254, 252, 248, 0.04) 1px, transparent 1px);
      background-size: 20px 20px;
      padding: 1.25rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
    }

    .message-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      max-width: 86%;
    }

    .message-group.bot {
      align-self: flex-start;
    }

    .message-group.user {
      align-self: flex-end;
      max-width: 80%;
    }

    .bubble {
      padding: 0.85rem 1.1rem;
      border-radius: 16px;
      font-size: 0.88rem;
      line-height: 1.5;
      position: relative;
      word-break: break-word;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
    }

    /* Bot Bubble: Warm Crème with Dark Violet Text */
    .bubble-bot {
      background: var(--wa-bot-bubble);
      color: var(--wa-bot-text);
      border-top-left-radius: 4px;
    }

    /* User Bubble: Vibrant Amethyst Violet with Pure Crème Text */
    .bubble-user {
      background: var(--wa-user-bubble);
      color: var(--wa-user-text);
      border-top-right-radius: 4px;
    }

    .bubble-time {
      font-size: 0.65rem;
      opacity: 0.55;
      text-align: right;
      margin-top: 0.35rem;
    }

    /* Clickable Suggestion Chips Inside Chat */
    .inline-chips-wrapper {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.25rem;
    }

    .inline-chip {
      background: rgba(254, 252, 248, 0.08);
      border: 1px solid var(--creme-border-hover);
      color: var(--creme-pure);
      padding: 0.45rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.78rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.18s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      backdrop-filter: blur(8px);
    }
    .inline-chip:hover {
      background: rgba(124, 58, 237, 0.35);
      border-color: var(--violet-light);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
    }
    .inline-chip.chip-vendor {
      background: rgba(139, 92, 246, 0.16);
      border-color: rgba(192, 132, 252, 0.38);
      color: #ede9fe;
    }
    .inline-chip.chip-vendor:hover {
      background: rgba(139, 92, 246, 0.32);
      border-color: #c084fc;
    }

    /* Typing Loading Indicator */
    .typing-indicator {
      display: none;
      align-self: flex-start;
      background: var(--wa-bot-bubble);
      padding: 0.65rem 1rem;
      border-radius: 16px;
      border-top-left-radius: 4px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .typing-indicator.active {
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }
    .typing-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--violet-primary);
      animation: typingBounce 1.4s infinite ease-in-out both;
    }
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    @keyframes typingBounce {
      0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* Error Banner inside Chat */
    .bubble-error {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fca5a5;
      font-size: 0.8rem;
    }

    /* Chat Input Bar */
    .chat-input-bar {
      background: rgba(22, 6, 42, 0.95);
      border-top: 1px solid var(--creme-border);
      padding: 0.85rem 1.1rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .chat-input {
      flex: 1;
      background: var(--wa-input-bg);
      border: 1px solid rgba(0, 0, 0, 0.12);
      outline: none;
      color: var(--text-dark);
      font-family: inherit;
      font-size: 0.88rem;
      padding: 0.75rem 1.15rem;
      border-radius: 22px;
      transition: border-color 0.2s;
    }
    .chat-input:focus {
      border-color: var(--violet-accent);
      box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.25);
    }
    .chat-input::placeholder {
      color: #7b6f84;
    }

    .chat-send-btn {
      background: var(--violet-primary);
      border: 1px solid var(--creme-border);
      outline: none;
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: var(--creme-pure);
      font-size: 1rem;
      transition: transform 0.15s ease, background 0.15s ease;
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);
      flex-shrink: 0;
    }
    .chat-send-btn:hover {
      transform: scale(1.08);
      background: var(--violet-accent);
    }

    @media (max-width: 600px) {
      header { padding: 0.75rem 1rem; }
      .brand-subtitle { display: none; }
      .chat-container { height: calc(100vh - 85px); border-radius: 16px; }
      main { padding: 0.5rem; }
    }
  </style>
</head>
<body>

  <!-- Clean Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">V</div>
      <div>
        <div class="brand-title">Vera Bot</div>
        <div class="brand-subtitle">Proactive Merchant Assistance Partner</div>
      </div>
    </div>
    
    <div class="header-controls">
      <div class="vendor-badge" id="header-vendor-badge">
        <span class="pulse"></span>
        <span id="header-vendor-text">Select Vendor</span>
      </div>
      <button class="btn-switch-vendor" id="header-switch-btn" style="display:none;" onclick="triggerSwitchVendor()">
        ⇄ Switch Vendor
      </button>
      <button class="btn-reset-session" onclick="resetSession()" title="Restart conversation from vendor selection">
        ↺ Reset Session
      </button>
    </div>
  </header>

  <main>
    <div class="chat-container">
      <div class="chat-subhead">
        <div class="chat-status-indicator">
          <span class="pulse"></span>
          <span id="chat-subhead-status">Online • Conversational Flow</span>
        </div>
        <div id="chat-conv-id" style="font-family:'JetBrains Mono',monospace; opacity:0.6; font-size:0.68rem;"></div>
      </div>

      <div class="chat-box" id="chat-box">
        <!-- Messages & Suggestion Chips rendered here -->
      </div>

      <!-- Typing Indicator -->
      <div class="typing-indicator" id="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>

      <!-- Input Bar -->
      <div class="chat-input-bar">
        <input type="text" class="chat-input" id="chat-input" placeholder="Type a vendor name, query, or option..." onkeydown="if(event.key==='Enter') handleUserSend()">
        <button class="chat-send-btn" onclick="handleUserSend()" title="Send Message">➤</button>
      </div>
    </div>
  </main>

  <script>
    // Conversational State Machine
    // States: 'SELECTING_VENDOR' | 'VENDOR_SELECTED' | 'CONVERSING'
    let convState = 'SELECTING_VENDOR';
    let activeVendor = null;
    let activeConversationId = "conv_" + Date.now();
    let loadedMerchants = [];

    // Fallback featured merchants while dataset loads
    const FEATURED_MERCHANTS = [
      { id: "m_005_pizzajunction_restaurant_delhi", name: "SK Pizza Junction", owner: "Suresh", cat: "Restaurant", loc: "Delhi" },
      { id: "m_001_drmeera_dentist_delhi", name: "Dr. Meera's Dental Clinic", owner: "Dr. Meera", cat: "Dentist", loc: "Delhi" },
      { id: "m_003_studio11_salon_hyderabad", name: "Studio11 Family Salon", owner: "Lakshmi", cat: "Salon", loc: "Hyderabad" },
      { id: "m_008_zenyoga_gym_chennai", name: "Zen Yoga Studio", owner: "Padma", cat: "Gym & Yoga", loc: "Chennai" },
      { id: "m_009_apollo_pharmacy_jaipur", name: "Apollo Health Plus", owner: "Ramesh", cat: "Pharmacy", loc: "Jaipur" }
    ];

    async function initDataset() {
      try {
        const res = await fetch('/v1/merchants').then(r => r.json());
        if (res.merchants && res.merchants.length > 0) {
          loadedMerchants = res.merchants;
        }
      } catch (e) {
        console.warn('Could not fetch /v1/merchants, using built-in dataset:', e);
      }
    }

    function getCurrentTime() {
      return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function showTyping(show = true) {
      const el = document.getElementById('typing-indicator');
      if (show) {
        el.classList.add('active');
        document.getElementById('chat-box').appendChild(el);
      } else {
        el.classList.remove('active');
      }
      scrollToBottom();
    }

    function scrollToBottom() {
      const box = document.getElementById('chat-box');
      box.scrollTop = box.scrollHeight;
    }

    function appendMessage(role, text, chips = [], isError = false) {
      const box = document.getElementById('chat-box');
      const group = document.createElement('div');
      group.className = `message-group ${role}`;

      const bubble = document.createElement('div');
      bubble.className = `bubble bubble-${role}` + (isError ? ' bubble-error' : '');
      
      let html = text.replace(/\\n/g, '<br>');
      html += `<div class="bubble-time">${getCurrentTime()}</div>`;
      bubble.innerHTML = html;
      group.appendChild(bubble);

      // Render Clickable Suggestion Chips inside the chat
      if (chips && chips.length > 0) {
        const chipsWrap = document.createElement('div');
        chipsWrap.className = 'inline-chips-wrapper';
        chips.forEach(chip => {
          const btn = document.createElement('button');
          btn.className = 'inline-chip' + (chip.type === 'vendor' ? ' chip-vendor' : '');
          btn.innerHTML = chip.label || chip.text;
          btn.onclick = () => {
            if (chip.type === 'vendor') {
              selectVendor(chip.vendor);
            } else {
              document.getElementById('chat-input').value = chip.text;
              handleUserSend();
            }
          };
          chipsWrap.appendChild(btn);
        });
        group.appendChild(chipsWrap);
      }

      box.appendChild(group);
      scrollToBottom();
    }

    // Step 1: Initial vendor selection question
    function startVendorSelection(promptText = "Hi! I'm Vera, your merchant assistance partner. Which restaurant or vendor are you associated with?") {
      convState = 'SELECTING_VENDOR';
      activeVendor = null;
      document.getElementById('header-vendor-text').textContent = "Select Vendor";
      document.getElementById('header-vendor-badge').classList.remove('selected');
      document.getElementById('header-switch-btn').style.display = "none";
      document.getElementById('chat-subhead-status').textContent = "Online • Vendor Selection";
      document.getElementById('chat-conv-id').textContent = activeConversationId.substring(0, 16);

      const vendors = loadedMerchants.length > 0 ? loadedMerchants.slice(0, 5) : FEATURED_MERCHANTS;
      const chips = vendors.map(v => ({
        type: 'vendor',
        label: `${v.owner || v.owner_first_name} (${v.name})`,
        text: v.name,
        vendor: v
      }));

      chips.push({
        type: 'custom',
        label: '✏️ Enter Manually...',
        text: 'Enter vendor name manually'
      });

      appendMessage('bot', promptText, chips);
    }

    // Step 2: Handle Vendor Selection
    async function selectVendor(vendor) {
      activeVendor = vendor;
      convState = 'VENDOR_SELECTED';

      const vName = vendor.name;
      const oName = vendor.owner || vendor.owner_first_name || 'there';
      const loc = vendor.loc || vendor.locality || '';

      // Update header
      document.getElementById('header-vendor-text').textContent = `Vera · ${vName}`;
      document.getElementById('header-vendor-badge').classList.add('selected');
      document.getElementById('header-switch-btn').style.display = "inline-flex";
      document.getElementById('chat-subhead-status').textContent = `Online with ${oName} (${vName})`;

      // User turn in chat
      appendMessage('user', `${oName} (${vName})`);

      // Step 3: Assistant acknowledges and asks relevant opening question with contextual suggestions
      showTyping(true);
      
      const mid = vendor.id || vendor.merchant_id;
      try {
        const res = await fetch('/v1/reply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: activeConversationId,
            merchant_id: mid,
            message: vName
          })
        }).then(r => r.json());

        showTyping(false);

        const greetingText = res.body || `Great, ${oName}! I've loaded the details for ${vName}${loc ? ' (' + loc + ')' : ''}. What would you like help with today?`;
        
        let suggestionTexts = res.suggestions || vendor.suggestions || [];
        if (!suggestionTexts || suggestionTexts.length === 0) {
          suggestionTexts = [
            "Mid-week dining footfall kaise badhayein?",
            "Current offers and promotions",
            "Corporate lunch packages",
            "What about Option 3 or a custom package?"
          ];
        }

        const chips = suggestionTexts.map(txt => ({
          type: 'query',
          label: `💡 "${txt}"`,
          text: txt
        }));

        appendMessage('bot', greetingText, chips);
      } catch (err) {
        showTyping(false);
        appendMessage('bot', `Great, ${oName}! I've loaded the details for ${vName}. What would you like help with today?`, [
          { type: 'query', label: 'Mid-week footfall growth', text: 'Mid-week dining footfall kaise badhayein?' },
          { type: 'query', label: 'Active offers & promos', text: 'Current offers and promotions' },
          { type: 'query', label: 'What about Option 3?', text: 'What about Option 3 or a custom package?' }
        ]);
      }
    }

    // Step 4: Continue conversation naturally
    async function handleUserSend() {
      const inp = document.getElementById('chat-input');
      const text = inp.value.trim();
      if (!text) return;
      inp.value = '';

      // Check for manual vendor input during SELECTING_VENDOR
      if (convState === 'SELECTING_VENDOR' && !activeVendor) {
        appendMessage('user', text);
        showTyping(true);

        try {
          const res = await fetch('/v1/reply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              conversation_id: activeConversationId,
              message: text
            })
          }).then(r => r.json());

          showTyping(false);

          if (res.conv_state === 'VENDOR_SELECTED' && res.vendor_id) {
            convState = 'VENDOR_SELECTED';
            activeVendor = {
              merchant_id: res.vendor_id,
              name: res.vendor_name,
              owner: res.owner_name
            };
            document.getElementById('header-vendor-text').textContent = `Vera · ${res.vendor_name}`;
            document.getElementById('header-vendor-badge').classList.add('selected');
            document.getElementById('header-switch-btn').style.display = "inline-flex";
            document.getElementById('chat-subhead-status').textContent = `Online with ${res.owner_name}`;

            const chips = (res.suggestions || []).map(txt => ({
              type: 'query',
              label: `💡 "${txt}"`,
              text: txt
            }));
            appendMessage('bot', res.body, chips);
            return;
          } else {
            // Not recognized: ask user to select or re-enter
            const vendors = loadedMerchants.length > 0 ? loadedMerchants.slice(0, 5) : FEATURED_MERCHANTS;
            const chips = vendors.map(v => ({
              type: 'vendor',
              label: `${v.owner || v.owner_first_name} (${v.name})`,
              text: v.name,
              vendor: v
            }));
            appendMessage('bot', res.body || `I couldn't find a vendor matching '${text}'. Please select an available vendor below or type the exact business or owner name:`, chips);
            return;
          }
        } catch (e) {
          showTyping(false);
          appendMessage('bot', `Network error matching vendor: ${e.message}`, [], true);
          return;
        }
      }

      // Check for explicit switch vendor request in conversation
      const low = text.toLowerCase();
      if (low.includes("switch vendor") || low.includes("change vendor") || low.includes("different vendor")) {
        triggerSwitchVendor();
        return;
      }

      // Normal multi-turn conversation
      convState = 'CONVERSING';
      appendMessage('user', text);
      showTyping(true);

      const mid = activeVendor ? (activeVendor.merchant_id || activeVendor.id) : null;
      try {
        const res = await fetch('/v1/reply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: activeConversationId,
            merchant_id: mid,
            message: text
          })
        }).then(r => r.json());

        showTyping(false);

        if (res.action === 'send') {
          // If response suggests follow-up choices
          let followUpChips = [];
          if (res.suggestions && res.suggestions.length > 0) {
            followUpChips = res.suggestions.slice(0, 3).map(t => ({ type: 'query', label: `👉 "${t}"`, text: t }));
          }
          appendMessage('bot', res.body, followUpChips);
        } else if (res.action === 'wait') {
          appendMessage('bot', `⏱ [Scheduled to pause for ${res.wait_seconds}s]`);
        } else if (res.action === 'end') {
          appendMessage('bot', `🔒 [Conversation ended cleanly: ${res.rationale || 'Done'}]`);
        }
      } catch (err) {
        showTyping(false);
        appendMessage('bot', `Error communicating with AI assistant: ${err.message}. Please try again.`, [], true);
      }
    }

    // Switch Vendor Flow
    function triggerSwitchVendor() {
      activeConversationId = "conv_" + Date.now();
      appendMessage('bot', "Sure! Which restaurant or vendor would you like to switch to?");
      startVendorSelection("Which restaurant or vendor would you like to switch to?");
    }

    // Reset Session Flow
    async function resetSession() {
      try {
        await fetch('/v1/teardown', { method: 'POST' });
      } catch (e) {
        console.warn('Teardown warning:', e);
      }
      activeConversationId = "conv_" + Date.now();
      document.getElementById('chat-box').innerHTML = '';
      startVendorSelection();
    }

    // Startup
    window.addEventListener('DOMContentLoaded', async () => {
      await initDataset();
      startVendorSelection();
    });
  </script>
</body>
</html>
"""
