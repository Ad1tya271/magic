"""Embedded interactive web UI for Vera Bot."""
from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vera Bot — Proactive WhatsApp AI for Retail Merchants</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0a0f1d;
      --card-bg: rgba(17, 24, 39, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent-green: #10b981;
      --accent-emerald: #059669;
      --accent-blue: #3b82f6;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --wa-chat-bg: #0b141a;
      --wa-bot-bubble: #202c33;
      --wa-user-bubble: #005c4b;
      --wa-green: #25d366;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      background: radial-gradient(circle at 15% 15%, #131d36 0%, #0a0f1d 100%);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      border-bottom: 1px solid var(--card-border);
      background: rgba(10, 15, 29, 0.85);
      backdrop-filter: blur(16px);
      padding: 1rem 2rem;
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
      gap: 0.75rem;
    }

    .brand-icon {
      width: 42px;
      height: 42px;
      background: linear-gradient(135deg, #10b981, #3b82f6);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.25rem;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
    }

    .brand-title {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .brand-subtitle {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .header-badges {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
    }

    .badge-live {
      background: rgba(16, 185, 129, 0.12);
      border-color: rgba(16, 185, 129, 0.3);
      color: #34d399;
    }

    .pulse {
      width: 7px;
      height: 7px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 8px #10b981;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    main {
      flex: 1;
      max-width: 1280px;
      margin: 0 auto;
      width: 100%;
      padding: 2rem 1.5rem;
      display: grid;
      grid-template-columns: 1fr 1.2fr;
      gap: 2rem;
    }

    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
    }

    .panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      backdrop-filter: blur(16px);
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
    }

    .panel-title {
      font-size: 0.95rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.75rem;
    }

    .metric-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1rem;
    }

    .metric-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }

    .metric-val {
      font-size: 1.35rem;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
    }

    .sim-controls {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    .btn {
      appearance: none;
      border: none;
      outline: none;
      cursor: pointer;
      font-family: inherit;
      font-weight: 600;
      font-size: 0.85rem;
      padding: 0.75rem 1rem;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .btn-primary {
      background: linear-gradient(135deg, #10b981, #059669);
      color: #fff;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
    }
    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      color: var(--text-main);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }

    .quick-replies {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.25rem;
    }

    .chip {
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
      padding: 0.4rem 0.8rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .chip:hover {
      background: rgba(59, 130, 246, 0.25);
      color: #fff;
    }

    /* WhatsApp Simulator Mockup */
    .phone-container {
      background: #000;
      border: 3px solid #27272a;
      border-radius: 32px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 600px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
    }

    .phone-header {
      background: #202c33;
      padding: 0.75rem 1rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    .avatar {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #10b981, #047857);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      color: #fff;
      font-size: 0.95rem;
    }

    .phone-info {
      flex: 1;
    }

    .phone-name {
      font-size: 0.9rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }

    .verified-check {
      color: #25d366;
      font-size: 0.85rem;
    }

    .phone-status {
      font-size: 0.7rem;
      color: #8696a0;
    }

    .chat-box {
      flex: 1;
      background: var(--wa-chat-bg);
      background-image: radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px);
      background-size: 16px 16px;
      padding: 1rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .bubble {
      max-width: 82%;
      padding: 0.65rem 0.9rem;
      border-radius: 12px;
      font-size: 0.85rem;
      line-height: 1.45;
      position: relative;
      word-break: break-word;
    }

    .bubble-bot {
      background: var(--wa-bot-bubble);
      align-self: flex-start;
      border-top-left-radius: 2px;
      color: #e9edef;
    }

    .bubble-user {
      background: var(--wa-user-bubble);
      align-self: flex-end;
      border-top-right-radius: 2px;
      color: #e9edef;
    }

    .meta-tag {
      display: inline-block;
      font-size: 0.65rem;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      margin-top: 0.35rem;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      background: rgba(0, 0, 0, 0.25);
      color: #6ee7b7;
    }

    .bubble-time {
      font-size: 0.65rem;
      color: rgba(255, 255, 255, 0.4);
      text-align: right;
      margin-top: 0.2rem;
    }

    .chat-input-bar {
      background: #202c33;
      padding: 0.65rem 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .chat-input {
      flex: 1;
      background: #2a3942;
      border: none;
      outline: none;
      color: #fff;
      font-family: inherit;
      font-size: 0.85rem;
      padding: 0.6rem 0.9rem;
      border-radius: 20px;
    }

    .chat-send-btn {
      background: var(--wa-green);
      border: none;
      outline: none;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: #0b141a;
      transition: transform 0.15s ease;
    }
    .chat-send-btn:hover { transform: scale(1.08); }

    .api-links {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .api-link {
      font-size: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
      text-decoration: none;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.2);
      padding: 0.4rem 0.65rem;
      border-radius: 8px;
      transition: background 0.15s ease;
    }
    .api-link:hover { background: rgba(56, 189, 248, 0.15); }
    .merchant-select {
      width: 100%;
      background: #1e293b;
      color: #f8fafc;
      border: 1px solid var(--card-border);
      padding: 0.65rem 0.85rem;
      border-radius: 10px;
      font-family: inherit;
      font-size: 0.85rem;
      margin-top: 0.25rem;
      margin-bottom: 0.75rem;
      outline: none;
      cursor: pointer;
    }
    .merchant-select:focus {
      border-color: var(--accent-green);
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">V</div>
      <div>
        <div class="brand-title">Vera Bot Dashboard</div>
        <div class="brand-subtitle">Proactive WhatsApp Retail Engine • Magicpin AI Challenge</div>
      </div>
    </div>
    <div class="header-badges">
      <div class="badge badge-live"><span class="pulse"></span> LIVE API</div>
      <div class="badge" id="model-badge">claude-opus-4-7</div>
    </div>
  </header>

  <main>
    <!-- Left: Status & Controls -->
    <div class="panel">
      <div class="panel-title">System Status</div>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Uptime</div>
          <div class="metric-val" id="uptime-val">--</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Categories Loaded</div>
          <div class="metric-val" id="cat-val">--</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Merchants Indexed</div>
          <div class="metric-val" id="merch-val">--</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Triggers Active</div>
          <div class="metric-val" id="trig-val">--</div>
        </div>
      </div>

      <div class="panel-title" style="margin-top: 0.5rem;">Select Active Merchant Profile</div>
      <select id="merchant-selector" class="merchant-select" onchange="switchMerchant(this.value)">
        <option value="m_001_drmeera_dentist_delhi">🦷 Dr. Meera — Sparkle Dental Clinic (Dentist, Delhi)</option>
        <option value="m_005_pizzajunction_restaurant_delhi">🍕 Suresh — SK Pizza Junction (Restaurant, Delhi)</option>
        <option value="m_003_studio11_salon_hyderabad">✂️ Lakshmi — Studio11 Family Salon (Salon, Hyderabad)</option>
        <option value="m_008_zenyoga_gym_chennai">🧘 Padma — Zen Yoga Studio (Gym & Yoga, Chennai)</option>
        <option value="m_009_apollo_pharmacy_jaipur">💊 Ramesh — Apollo Health Plus (Pharmacy, Jaipur)</option>
      </select>

      <div class="panel-title" style="margin-top: 0.5rem;">Simulation Actions</div>
      <div class="sim-controls">
        <button class="btn btn-primary" onclick="simulateTick()">⚡ Trigger Proactive Wakeup (Tick)</button>
        <button class="btn btn-secondary" onclick="resetState()">↺ Reset Context Store (Teardown)</button>
      </div>

      <div class="panel-title" style="margin-top: 0.5rem;">Interactive Dialogue Chips</div>
      <div class="quick-replies" id="quick-replies-container">
        <!-- Dynamically rendered based on active merchant -->
      </div>

      <div class="panel-title" style="margin-top: 0.5rem;">REST API Surface</div>
      <div class="api-links">
        <a class="api-link" href="/v1/healthz" target="_blank">GET /v1/healthz</a>
        <a class="api-link" href="/v1/metadata" target="_blank">GET /v1/metadata</a>
        <a class="api-link" href="/docs" target="_blank">Swagger /docs</a>
      </div>
    </div>

    <!-- Right: WhatsApp Phone Simulator -->
    <div class="phone-container">
      <div class="phone-header">
        <div class="avatar" id="phone-avatar">V</div>
        <div class="phone-info">
          <div class="phone-name" id="phone-header-title">Vera (magicpin partner) <span class="verified-check">✓</span></div>
          <div class="phone-status" id="chat-sub">active with Dr. Meera (Dentist, Delhi)</div>
        </div>
      </div>

      <div class="chat-box" id="chat-box">
        <!-- Messages rendered here -->
      </div>

      <div class="chat-input-bar">
        <input type="text" class="chat-input" id="chat-input" placeholder="Type a message as merchant..." onkeydown="if(event.key==='Enter') sendMessage()">
        <button class="chat-send-btn" onclick="sendMessage()">➤</button>
      </div>
    </div>
  </main>

  <script>
    let activeConversationId = "conv_demo_1";
    let activeMerchantId = "m_001_drmeera_dentist_delhi";

    const MERCHANT_PROFILES = {
      "m_001_drmeera_dentist_delhi": {
        name: "Dr. Meera",
        business: "Sparkle Dental Clinic",
        category: "Dentist",
        locality: "Lajpat Nagar, Delhi",
        greeting: "Dr. Meera, JIDA's Oct study is in: 3-month fluoride recalls cut caries 38% better in high-risk adults. You have 78 lapsed patients due for scaling. We can offer a ₹299 Dental Cleaning recall (Option A), or share an Aligners vs Braces guide (Option B). Which sounds best for this week?",
        chips: [
          "Is hafte dental mein kya trending hai?",
          "JIDA research study ke baare mein batao",
          "Option A ke saath chalte hain",
          "Option B content guide bhejo",
          "Competitor Smile Studio se kaise compete karein?",
          "Meri profile ka performance kaisa hai?"
        ]
      },
      "m_005_pizzajunction_restaurant_delhi": {
        name: "Suresh",
        business: "SK Pizza Junction",
        category: "Restaurant",
        locality: "Sant Nagar, Delhi",
        greeting: "Suresh ji, local dining searches show weekend pizza & thali combos up +24% YoY. Your active offer is 'Buy 1 Get 1 Free (Tue-Thu)'. We can push a weekend dining special (Option 1) or corporate lunch packages (Option 2). What would you like to prioritize?",
        chips: [
          "Mid-week dining footfall kaise badhayein?",
          "Option 1 (Weekend promo)",
          "Option 2 (Corporate lunch)",
          "IPL match nights par kya offer chalayein?",
          "Aapke paas kya scheme ya offer hai?",
          "Meri dukaan ka performance kaisa hai?"
        ]
      },
      "m_003_studio11_salon_hyderabad": {
        name: "Lakshmi",
        business: "Studio11 Family Salon",
        category: "Salon",
        locality: "Kapra, Hyderabad",
        greeting: "Lakshmi ji, bridal season demand is up +48% YoY and Saturday 4-8pm booking volume is peaking. You have 220 lapsed clients. We can send a Hair Spa @ ₹499 + Haircut @ ₹99 invite (Option 1) or launch a Bridal Trial @ ₹999 package (Option 2). Which one shall we run?",
        chips: [
          "Bridal season ke liye kya trending hai?",
          "Option 1 (Hair Spa @ ₹499)",
          "Option 2 (Bridal Trial @ ₹999)",
          "220 lapsed clients ko kaise reactivate karein?",
          "Aas-paas ke competitor kya de rahe hain?",
          "Aapke paas kya scheme ya offer hai?"
        ]
      },
      "m_008_zenyoga_gym_chennai": {
        name: "Padma",
        business: "Zen Yoga Studio",
        category: "Gym & Yoga",
        locality: "Mylapore, Chennai",
        greeting: "Padma ji, morning 6-8am HIIT & strength queries are up +40% YoY. Your active offer is 'First Month @ ₹499' with free body analysis. We can run a 3-day guest trial pass (Option 1) or a 4-week Kids Yoga summer camp (Option 2). Which sounds exciting?",
        chips: [
          "Morning HIIT batch demand ka data batao",
          "Kids yoga summer camp plan kaisa rahega?",
          "Option 1 (3-day trial pass)",
          "Option 2 (Summer camp program)",
          "Members retention kaise improve karein?",
          "Meri listing ka CTR aur calls kaisa hai?"
        ]
      },
      "m_009_apollo_pharmacy_jaipur": {
        name: "Ramesh",
        business: "Apollo Health Plus Pharmacy",
        category: "Pharmacy",
        locality: "Malviya Nagar, Jaipur",
        greeting: "Ramesh ji, seasonal hydration ORS kits and chronic medication refills have the strongest repeat volume (+38% YoY). Your active offers include 'Free Delivery > ₹499' and 'Senior Citizen 15% OFF'. We can automate monthly chronic refills (Option 1) or family wellness kits (Option 2). What should we do?",
        chips: [
          "Seasonal ORS hydration essentials mein kya chal raha hai?",
          "Chronic medication refill kaise schedule karein?",
          "Option 1 (Monthly refill delivery)",
          "Option 2 (Family wellness kit)",
          "Senior citizen 15% discount push karo",
          "Meri calls aur directions ki performance kaisa hai?"
        ]
      }
    };

    function renderChips(chips) {
      const container = document.getElementById('quick-replies-container');
      container.innerHTML = '';
      chips.forEach(text => {
        const span = document.createElement('span');
        span.className = 'chip';
        span.textContent = `"${text}"`;
        span.onclick = () => sendQuickReply(text);
        container.appendChild(span);
      });
    }

    function switchMerchant(mid) {
      activeMerchantId = mid;
      activeConversationId = "conv_" + mid.substring(0, 10) + "_" + Date.now();
      const profile = MERCHANT_PROFILES[mid] || MERCHANT_PROFILES["m_001_drmeera_dentist_delhi"];
      
      document.getElementById('chat-sub').textContent = `active with ${profile.name} (${profile.category}, ${profile.locality.split(',')[1] || profile.locality})`;
      renderChips(profile.chips);

      const chat = document.getElementById('chat-box');
      chat.innerHTML = `
        <div class="bubble bubble-bot">
          ${profile.greeting}
          <div class="bubble-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      `;
    }

    async function updateMetrics() {
      try {
        const h = await fetch('/v1/healthz').then(r => r.json());
        const m = await fetch('/v1/metadata').then(r => r.json());
        document.getElementById('uptime-val').textContent = h.uptime_seconds + 's';
        document.getElementById('cat-val').textContent = h.contexts_loaded.category || 0;
        document.getElementById('merch-val').textContent = h.contexts_loaded.merchant || 0;
        document.getElementById('trig-val').textContent = h.contexts_loaded.trigger || 0;
        document.getElementById('model-badge').textContent = m.model || 'claude-opus-4-7';
      } catch (e) {
        console.error('Metrics fetch error:', e);
      }
    }
    setInterval(updateMetrics, 5000);
    updateMetrics();

    // Initialize with Dr. Meera
    switchMerchant("m_001_drmeera_dentist_delhi");

    function appendMessage(role, text, tag = '') {
      const chat = document.getElementById('chat-box');
      const b = document.createElement('div');
      b.className = 'bubble ' + (role === 'user' ? 'bubble-user' : 'bubble-bot');
      
      let html = text.replace(/\\n/g, '<br>');
      if (tag) {
        html += `<br><span class="meta-tag">${tag}</span>`;
      }
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      html += `<div class="bubble-time">${now}</div>`;
      
      b.innerHTML = html;
      chat.appendChild(b);
      chat.scrollTop = chat.scrollHeight;
    }

    async function simulateTick() {
      appendMessage('bot', '⚡ Processing simulated tick wake-up for ' + activeMerchantId + '...');
      try {
        const res = await fetch('/v1/tick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ available_triggers: [] })
        }).then(r => r.json());

        const actions = res.actions || [];
        if (actions.length > 0) {
          const act = actions[0];
          activeConversationId = act.conversation_id;
          activeMerchantId = act.merchant_id;
          appendMessage('bot', act.body, `CTA: ${act.cta} | Rationale: ${act.rationale.substring(0, 50)}...`);
        } else {
          appendMessage('bot', 'All current triggers evaluated. No new messages due for sending right now.');
        }
      } catch (e) {
        appendMessage('bot', 'Tick failed: ' + e.message);
      }
      updateMetrics();
    }

    async function sendQuickReply(text) {
      document.getElementById('chat-input').value = text;
      await sendMessage();
    }

    async function sendMessage() {
      const inp = document.getElementById('chat-input');
      const msg = inp.value.trim();
      if (!msg) return;
      inp.value = '';

      appendMessage('user', msg);

      try {
        const res = await fetch('/v1/reply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: activeConversationId,
            merchant_id: activeMerchantId,
            message: msg
          })
        }).then(r => r.json());

        if (res.action === 'send') {
          appendMessage('bot', res.body, `Action: send | Mode: ${res.cta || 'interactive'}`);
        } else if (res.action === 'wait') {
          appendMessage('bot', `⏱ [Bot scheduled to pause for ${res.wait_seconds}s]`, `Action: wait`);
        } else if (res.action === 'end') {
          appendMessage('bot', `🔒 [Conversation ended cleanly: ${res.rationale}]`, `Action: end`);
        }
      } catch (e) {
        appendMessage('bot', 'Reply error: ' + e.message);
      }
      updateMetrics();
    }

    async function resetState() {
      await fetch('/v1/teardown', { method: 'POST' });
      switchMerchant(activeMerchantId);
      updateMetrics();
    }
  </script>
</body>
</html>
"""
