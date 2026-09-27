"""Embedded interactive web UI for Vera Bot with 3-Stage Process and Violet & Crème Theme."""
from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vera Bot — 3-Stage Proactive Retail AI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      /* Violet and Crème Color Palette */
      --bg-canvas: #150827;
      --bg-gradient: radial-gradient(circle at 20% 15%, #2a0e4e 0%, #150827 75%, #0e041a 100%);
      
      --creme-pure: #fefcf8;
      --creme-warm: #f7f2e7;
      --creme-soft: #efe7d5;
      --creme-muted: #d9cfbe;
      --creme-border: rgba(254, 252, 248, 0.16);
      --creme-border-strong: rgba(254, 252, 248, 0.32);

      --violet-deep: #220c3d;
      --violet-card: rgba(34, 12, 61, 0.78);
      --violet-accent: #8b5cf6;
      --violet-primary: #7c3aed;
      --violet-light: #c084fc;
      --violet-glow: rgba(139, 92, 246, 0.28);

      --text-creme: #fefcf8;
      --text-creme-muted: #cdbfad;
      --text-dark: #1b0730;

      /* WhatsApp Chat Tokens */
      --wa-chat-bg: #120622;
      --wa-bot-bubble: #fdfbf7;
      --wa-bot-text: #17052a;
      --wa-user-bubble: #7c3aed;
      --wa-user-text: #fefcf8;
      --wa-input-bg: #f7f2e7;
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

    /* Clean Header */
    header {
      border-bottom: 1px solid var(--creme-border);
      background: rgba(21, 8, 39, 0.88);
      backdrop-filter: blur(18px);
      padding: 0.9rem 2rem;
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
      width: 42px;
      height: 42px;
      background: linear-gradient(135deg, var(--creme-soft), var(--violet-accent));
      color: var(--violet-deep);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.3rem;
      box-shadow: 0 4px 14px var(--violet-glow);
    }

    .brand-title {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--creme-pure);
    }

    .brand-subtitle {
      font-size: 0.75rem;
      color: var(--text-creme-muted);
    }

    .header-badges {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.35rem 0.8rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(254, 252, 248, 0.08);
      border: 1px solid var(--creme-border);
      color: var(--creme-soft);
    }

    .badge-live {
      background: rgba(139, 92, 246, 0.18);
      border-color: rgba(139, 92, 246, 0.4);
      color: #ddd6fe;
    }

    .pulse {
      width: 7px;
      height: 7px;
      background: #a78bfa;
      border-radius: 50%;
      box-shadow: 0 0 8px #a78bfa;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    /* 3-Stage Progress Stepper Bar */
    .stepper-container {
      background: rgba(28, 10, 51, 0.7);
      border-bottom: 1px solid var(--creme-border);
      padding: 0.75rem 2rem;
      display: flex;
      justify-content: center;
    }

    .stepper {
      display: flex;
      align-items: center;
      gap: 1rem;
      max-width: 900px;
      width: 100%;
    }

    .step-item {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.5rem 0.85rem;
      border-radius: 10px;
      background: rgba(254, 252, 248, 0.04);
      border: 1px solid var(--creme-border);
      transition: all 0.2s ease;
    }

    .step-item.active {
      background: rgba(124, 58, 237, 0.2);
      border-color: var(--violet-light);
      box-shadow: 0 0 12px rgba(139, 92, 246, 0.25);
    }

    .step-num {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--creme-soft);
      color: var(--violet-deep);
      font-size: 0.75rem;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .step-item.active .step-num {
      background: var(--violet-accent);
      color: var(--creme-pure);
    }

    .step-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--creme-muted);
    }

    .step-item.active .step-label {
      color: var(--creme-pure);
    }

    .step-arrow {
      color: var(--text-creme-muted);
      font-size: 0.8rem;
    }

    /* Main Layout */
    main {
      flex: 1;
      max-width: 1320px;
      margin: 0 auto;
      width: 100%;
      padding: 1.5rem;
      display: grid;
      grid-template-columns: 1.15fr 1fr;
      gap: 1.5rem;
    }

    @media (max-width: 950px) {
      main { grid-template-columns: 1fr; }
    }

    /* Left Column: 3 Stages Control Panel */
    .workflow-panel {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .stage-card {
      background: var(--violet-card);
      border: 1px solid var(--creme-border);
      border-radius: 18px;
      backdrop-filter: blur(16px);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      position: relative;
    }

    .stage-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .stage-title {
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--violet-light);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .stage-tag {
      font-size: 0.68rem;
      font-weight: 600;
      padding: 0.2rem 0.55rem;
      border-radius: 9999px;
      background: rgba(254, 252, 248, 0.1);
      border: 1px solid var(--creme-border);
      color: var(--creme-soft);
    }

    /* Stage 1: Situation Selector */
    .situation-select {
      width: 100%;
      background: #1e0a35;
      color: var(--creme-pure);
      border: 1px solid var(--creme-border-strong);
      padding: 0.75rem 0.9rem;
      border-radius: 12px;
      font-family: inherit;
      font-size: 0.88rem;
      outline: none;
      cursor: pointer;
      transition: border-color 0.2s;
    }
    .situation-select:focus {
      border-color: var(--violet-accent);
    }

    .prompt-box-wrapper {
      border: 1px solid var(--creme-border);
      border-radius: 12px;
      background: rgba(16, 5, 29, 0.9);
      overflow: hidden;
    }

    .prompt-box-header {
      background: rgba(254, 252, 248, 0.05);
      padding: 0.45rem 0.75rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      color: var(--creme-muted);
      border-bottom: 1px solid var(--creme-border);
      font-family: 'JetBrains Mono', monospace;
    }

    .prompt-pre {
      padding: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      line-height: 1.45;
      color: var(--creme-soft);
      max-height: 140px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .highlight-pill {
      display: inline-block;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      background: rgba(139, 92, 246, 0.25);
      color: #e9d5ff;
      font-size: 0.68rem;
      font-weight: 600;
    }

    /* Stage 2: User Input & Quick Chips */
    .chips-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .chip-btn {
      background: rgba(254, 252, 248, 0.07);
      border: 1px solid var(--creme-border);
      color: var(--creme-pure);
      padding: 0.45rem 0.8rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      text-align: left;
    }
    .chip-btn:hover {
      background: rgba(124, 58, 237, 0.3);
      border-color: var(--violet-light);
      transform: translateY(-1px);
    }
    .chip-btn.chip-unknown {
      background: rgba(139, 92, 246, 0.18);
      border-color: rgba(192, 132, 252, 0.4);
      color: #e9d5ff;
    }
    .chip-btn.chip-unknown:hover {
      background: rgba(139, 92, 246, 0.35);
      border-color: #c084fc;
    }

    /* Stage 3: Controls & Reset */
    .stage-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .session-status-text {
      font-size: 0.76rem;
      color: var(--creme-muted);
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .btn-reset {
      appearance: none;
      border: 1px solid var(--creme-border-strong);
      background: var(--creme-warm);
      color: var(--violet-deep);
      font-family: inherit;
      font-weight: 700;
      font-size: 0.8rem;
      padding: 0.55rem 1.1rem;
      border-radius: 10px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      transition: all 0.2s ease;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .btn-reset:hover {
      background: var(--creme-pure);
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
    }

    /* Right Column: WhatsApp Phone Simulator (Violet & Crème) */
    .phone-container {
      background: #11051f;
      border: 2px solid var(--creme-border);
      border-radius: 28px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 680px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.65), 0 0 40px rgba(124, 58, 237, 0.18);
    }

    .phone-header {
      background: #240c42;
      padding: 0.85rem 1.1rem;
      display: flex;
      align-items: center;
      gap: 0.85rem;
      border-bottom: 1px solid var(--creme-border);
    }

    .phone-avatar {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, var(--creme-warm), var(--violet-accent));
      color: var(--violet-deep);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1rem;
    }

    .phone-info {
      flex: 1;
    }

    .phone-name {
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--creme-pure);
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }

    .phone-status {
      font-size: 0.72rem;
      color: var(--creme-muted);
    }

    .chat-box {
      flex: 1;
      background: var(--wa-chat-bg);
      background-image: radial-gradient(rgba(254, 252, 248, 0.05) 1px, transparent 1px);
      background-size: 18px 18px;
      padding: 1.1rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }

    .bubble {
      max-width: 84%;
      padding: 0.75rem 0.95rem;
      border-radius: 14px;
      font-size: 0.85rem;
      line-height: 1.48;
      position: relative;
      word-break: break-word;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    /* Bot Bubble: Warm Crème with Dark Violet Text */
    .bubble-bot {
      background: var(--wa-bot-bubble);
      color: var(--wa-bot-text);
      align-self: flex-start;
      border-top-left-radius: 3px;
    }

    /* User Bubble: Deep Amethyst Violet with Pure Crème Text */
    .bubble-user {
      background: var(--wa-user-bubble);
      color: var(--wa-user-text);
      align-self: flex-end;
      border-top-right-radius: 3px;
    }

    .meta-tag {
      display: inline-block;
      font-size: 0.65rem;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      margin-top: 0.45rem;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      background: rgba(124, 58, 237, 0.12);
      color: #6b21a8;
      border: 1px solid rgba(124, 58, 237, 0.2);
    }

    .bubble-time {
      font-size: 0.65rem;
      opacity: 0.6;
      text-align: right;
      margin-top: 0.25rem;
    }

    /* Chat Input Bar: Crème with Violet Send */
    .chat-input-bar {
      background: #200a3a;
      border-top: 1px solid var(--creme-border);
      padding: 0.75rem 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }

    .chat-input {
      flex: 1;
      background: var(--wa-input-bg);
      border: 1px solid rgba(0, 0, 0, 0.1);
      outline: none;
      color: var(--text-dark);
      font-family: inherit;
      font-size: 0.85rem;
      padding: 0.65rem 1rem;
      border-radius: 20px;
    }
    .chat-input::placeholder {
      color: #7c6e86;
    }

    .chat-send-btn {
      background: var(--violet-primary);
      border: 1px solid var(--creme-border);
      outline: none;
      width: 38px;
      height: 38px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: var(--creme-pure);
      font-size: 0.95rem;
      transition: transform 0.15s ease, background 0.15s ease;
      box-shadow: 0 4px 10px rgba(124, 58, 237, 0.4);
    }
    .chat-send-btn:hover {
      transform: scale(1.08);
      background: var(--violet-accent);
    }
  </style>
</head>
<body>

  <!-- Clean Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">V</div>
      <div>
        <div class="brand-title">Vera Bot Engine</div>
        <div class="brand-subtitle">Proactive WhatsApp Retail AI • 3-Stage Process</div>
      </div>
    </div>
    <div class="header-badges">
      <div class="badge badge-live"><span class="pulse"></span> LIVE LLM ENGINE</div>
      <div class="badge" id="merchant-city-badge">Delhi • Dentist</div>
    </div>
  </header>

  <!-- 3-Stage Stepper Bar -->
  <div class="stepper-container">
    <div class="stepper">
      <div class="step-item active" id="step-ind-1">
        <div class="step-num">1</div>
        <div class="step-label">Stage 1: Situation & Prompt Update</div>
      </div>
      <div class="step-arrow">➔</div>
      <div class="step-item active" id="step-ind-2">
        <div class="step-num">2</div>
        <div class="step-label">Stage 2: Merchant Input</div>
      </div>
      <div class="step-arrow">➔</div>
      <div class="step-item active" id="step-ind-3">
        <div class="step-num">3</div>
        <div class="step-label">Stage 3: LLM Output & Chat (until Reset)</div>
      </div>
    </div>
  </div>

  <main>
    <!-- Left Column: The 3-Stage Studio -->
    <div class="workflow-panel">

      <!-- STAGE 1: Situation & LLM Prompt Live Update -->
      <div class="stage-card">
        <div class="stage-header">
          <div class="stage-title">
            <span class="highlight-pill">STAGE 1</span> Select Situation & Update LLM Prompt
          </div>
          <span class="stage-tag" id="prompt-status-tag">✓ Prompt Updated</span>
        </div>

        <select id="situation-selector" class="situation-select" onchange="onSituationChange(this.value)">
          <option value="m_001_drmeera_dentist_delhi">🦷 Dr. Meera (Dentist, Delhi) — 78 Lapsed Patients & JIDA Fluoride Recall</option>
          <option value="m_005_pizzajunction_restaurant_delhi">🍕 Suresh (Restaurant, Delhi) — Mid-Week Dinner Slump & Corporate Combos</option>
          <option value="m_003_studio11_salon_hyderabad">✂️ Lakshmi (Salon, Hyderabad) — Bridal Season Peak (+48% YoY) & 220 Lapsed Clients</option>
          <option value="m_008_zenyoga_gym_chennai">🧘 Padma (Gym & Yoga, Chennai) — Morning HIIT Surge & Kids Yoga Camp</option>
          <option value="m_009_apollo_pharmacy_jaipur">💊 Ramesh (Pharmacy, Jaipur) — Chronic Refill Delivery & Hydration Surge</option>
        </select>

        <!-- Live LLM Prompt / Context Preview -->
        <div class="prompt-box-wrapper">
          <div class="prompt-box-header">
            <span>LIVE CONTEXT FED TO LLM</span>
            <span id="prompt-tokens-badge">Category: dentists | Mode: pitch</span>
          </div>
          <pre class="prompt-pre" id="prompt-preview-content">
[SYSTEM PROMPT] You are Vera, a proactive retail business co-pilot for Dr. Meera at Sparkle Dental Clinic (Dentists, Lajpat Nagar, Delhi).
[GROUNDED INTELLIGENCE] JIDA Oct 2026 Trial: 3-month fluoride recall cuts caries 38% better in adults. 78 lapsed patients identified.
[MARGIN & ACTIONS] Never qualify commitments. Active offer: Free Home Delivery > ₹499. Propose Option A (₹299 Cleaning) vs Option B (Aligners Guide).
[TRIGGER] Lapsed patients recall batch pending dispatch.
          </pre>
        </div>
      </div>

      <!-- STAGE 2: Merchant / User Input & Quick Chips -->
      <div class="stage-card">
        <div class="stage-header">
          <div class="stage-title">
            <span class="highlight-pill">STAGE 2</span> Merchant Input (Scenario, Inquiry or Custom Option)
          </div>
          <span class="stage-tag">Click Chip or Type</span>
        </div>

        <div class="chips-grid" id="chips-container">
          <!-- Dynamically filled with scenario questions, options, and unknown options -->
        </div>
      </div>

      <!-- STAGE 3: Dialogue State & Reset Session -->
      <div class="stage-card">
        <div class="stage-header">
          <div class="stage-title">
            <span class="highlight-pill">STAGE 3</span> Dialogue Control (Converse until Reset)
          </div>
          <span class="stage-tag" id="turns-counter">Turns: 1</span>
        </div>

        <div class="stage-actions">
          <div class="session-status-text">
            <span>● Status: Active continuous session. Conversation persists until reset is clicked.</span>
          </div>
          <button class="btn-reset" onclick="resetSession()">
            <span>↺</span> Reset Session
          </button>
        </div>
      </div>

    </div>

    <!-- Right Column: WhatsApp Phone Simulator (Stage 3 Live Dialogue) -->
    <div class="phone-container">
      <div class="phone-header">
        <div class="phone-avatar">V</div>
        <div class="phone-info">
          <div class="phone-name" id="chat-header-name">Vera (magicpin partner) <span style="color:#a78bfa; font-size:0.8rem;">✓</span></div>
          <div class="phone-status" id="chat-header-status">active with Dr. Meera • Online</div>
        </div>
      </div>

      <div class="chat-box" id="chat-box">
        <!-- Live WhatsApp turns rendered here -->
      </div>

      <div class="chat-input-bar">
        <input type="text" class="chat-input" id="chat-input" placeholder="Type as merchant (e.g. Option 3, question, discount)..." onkeydown="if(event.key==='Enter') sendMerchantMessage()">
        <button class="chat-send-btn" onclick="sendMerchantMessage()" title="Send Input to LLM">➤</button>
      </div>
    </div>
  </main>

  <script>
    let activeMerchantId = "m_001_drmeera_dentist_delhi";
    let activeConversationId = "conv_stage_" + Date.now();
    let turnCount = 0;

    const SITUATIONS = {
      "m_001_drmeera_dentist_delhi": {
        name: "Dr. Meera",
        business: "Sparkle Dental Clinic",
        category: "Dentist",
        locality: "Lajpat Nagar, Delhi",
        badge: "Delhi • Dentist",
        promptText: `[SYSTEM PROMPT] You are Vera, a proactive retail business co-pilot for Dr. Meera at Sparkle Dental Clinic (Dentists, Lajpat Nagar, Delhi).
[GROUNDED INTELLIGENCE] JIDA Oct 2026 Trial: 3-month fluoride recall cuts caries 38% better in adults. DCI radiation cap: 1.0 mSv.
[DATASET METRICS] 78 lapsed patients due for scaling. Active verified offer: Free Oral Health Kit on Checkup.
[POLICY & SAFEGUARDS] Do not qualify commitments. Handle unknown options constructively. Propose Option A (₹299 Cleaning) vs Option B (Aligners vs Braces guide).`,
        greeting: "Dr. Meera, JIDA's Oct study is in: 3-month fluoride recalls cut caries 38% better in high-risk adults. You have 78 lapsed patients due for scaling. We can offer a ₹299 Dental Cleaning recall (Option A), or share an Aligners vs Braces guide (Option B). Which sounds best for this week?",
        chips: [
          { text: "JIDA research study ke baare mein batao", unknown: false },
          { text: "Option A ke saath chalte hain", unknown: false },
          { text: "Option B content guide bhejo", unknown: false },
          { text: "What about Option 3 or a custom package?", unknown: true },
          { text: "Can we do an alternative option?", unknown: true },
          { text: "Competitor Smile Studio se kaise compete karein?", unknown: false },
          { text: "Can we do a 90% discount flash sale?", unknown: true }
        ]
      },
      "m_005_pizzajunction_restaurant_delhi": {
        name: "Suresh",
        business: "SK Pizza Junction",
        category: "Restaurant",
        locality: "Sant Nagar, Delhi",
        badge: "Delhi • Restaurant",
        promptText: `[SYSTEM PROMPT] You are Vera, proactive retail co-pilot for Suresh at SK Pizza Junction (Restaurants, Sant Nagar, Delhi).
[GROUNDED INTELLIGENCE] Local dining searches: weekend pizza & thali combos up +24% YoY. Mid-week dinner footfall slump.
[DATASET METRICS] Active verified offer: 'Buy 1 Get 1 Free (Tue-Thu)'. 145 lapsed corporate lunch diners.
[POLICY & SAFEGUARDS] Protect margins. Handle custom options constructively. Propose Option 1 (Weekend promo) vs Option 2 (Corporate lunch).`,
        greeting: "Suresh ji, local dining searches show weekend pizza & thali combos up +24% YoY. Your active offer is 'Buy 1 Get 1 Free (Tue-Thu)'. We can push a weekend dining special (Option 1) or corporate lunch packages (Option 2). What would you like to prioritize?",
        chips: [
          { text: "Mid-week dining footfall kaise badhayein?", unknown: false },
          { text: "Option 1 (Weekend promo)", unknown: false },
          { text: "Option 2 (Corporate lunch)", unknown: false },
          { text: "What about Option 3 or a custom package?", unknown: true },
          { text: "Is there any other alternative option?", unknown: true },
          { text: "IPL match nights par kya offer chalayein?", unknown: false },
          { text: "Can we do a 90% discount flash sale?", unknown: true }
        ]
      },
      "m_003_studio11_salon_hyderabad": {
        name: "Lakshmi",
        business: "Studio11 Family Salon",
        category: "Salon",
        locality: "Kapra, Hyderabad",
        badge: "Hyderabad • Salon",
        promptText: `[SYSTEM PROMPT] You are Vera, retail AI co-pilot for Lakshmi at Studio11 Family Salon (Salons, Kapra, Hyderabad).
[GROUNDED INTELLIGENCE] Bridal season bookings surge +48% YoY; Saturday 4-8pm booking volume is peaking.
[DATASET METRICS] 220 lapsed clients. Active verified offer: Hair Spa @ ₹499 + Haircut @ ₹99.
[POLICY & SAFEGUARDS] Action-oriented next steps. Handle unknown options with category tailored pilot. Propose Option 1 (Hair Spa) vs Option 2 (Bridal Trial @ ₹999).`,
        greeting: "Lakshmi ji, bridal season demand is up +48% YoY and Saturday 4-8pm booking volume is peaking. You have 220 lapsed clients. We can send a Hair Spa @ ₹499 + Haircut @ ₹99 invite (Option 1) or launch a Bridal Trial @ ₹999 package (Option 2). Which one shall we run?",
        chips: [
          { text: "Bridal season ke liye kya trending hai?", unknown: false },
          { text: "Option 1 (Hair Spa @ ₹499)", unknown: false },
          { text: "Option 2 (Bridal Trial @ ₹999)", unknown: false },
          { text: "What about Option 3 or a custom package?", unknown: true },
          { text: "Can we explore another option?", unknown: true },
          { text: "220 lapsed clients ko kaise reactivate karein?", unknown: false },
          { text: "What if I want a 90% discount offer?", unknown: true }
        ]
      },
      "m_008_zenyoga_gym_chennai": {
        name: "Padma",
        business: "Zen Yoga Studio",
        category: "Gym & Yoga",
        locality: "Mylapore, Chennai",
        badge: "Chennai • Gym & Yoga",
        promptText: `[SYSTEM PROMPT] You are Vera, retail co-pilot for Padma at Zen Yoga Studio (Gyms & Yoga, Mylapore, Chennai).
[GROUNDED INTELLIGENCE] Morning 6-8am HIIT & strength queries up +40% YoY. Kids summer fitness queries active.
[DATASET METRICS] Active verified offer: 'First Month @ ₹499' with free body analysis. 64 lapsed annual members.
[POLICY & SAFEGUARDS] Retain gym margins. Propose Option 1 (3-day guest trial pass) vs Option 2 (Kids Yoga summer camp).`,
        greeting: "Padma ji, morning 6-8am HIIT & strength queries are up +40% YoY. Your active offer is 'First Month @ ₹499' with free body analysis. We can run a 3-day guest trial pass (Option 1) or a 4-week Kids Yoga summer camp (Option 2). Which sounds exciting?",
        chips: [
          { text: "Morning HIIT batch demand ka data batao", unknown: false },
          { text: "Kids yoga summer camp plan kaisa rahega?", unknown: false },
          { text: "Option 1 (3-day trial pass)", unknown: false },
          { text: "What about Option 3 or a custom package?", unknown: true },
          { text: "Do you have an alternative option?", unknown: true },
          { text: "Members retention kaise improve karein?", unknown: false },
          { text: "Can we sponsor a marathon?", unknown: true }
        ]
      },
      "m_009_apollo_pharmacy_jaipur": {
        name: "Ramesh",
        business: "Apollo Health Plus Pharmacy",
        category: "Pharmacy",
        locality: "Malviya Nagar, Jaipur",
        badge: "Jaipur • Pharmacy",
        promptText: `[SYSTEM PROMPT] You are Vera, retail co-pilot for Ramesh at Apollo Health Plus (Pharmacies, Malviya Nagar, Jaipur).
[GROUNDED INTELLIGENCE] Seasonal hydration ORS kits & chronic medication refills have +38% repeat volume.
[DATASET METRICS] Active verified offers: 'Free Delivery > ₹499' and 'Senior Citizen 15% OFF'.
[POLICY & SAFEGUARDS] Automate monthly refills. Handle unknown options constructively. Propose Option 1 (Chronic refills) vs Option 2 (Family wellness kits).`,
        greeting: "Ramesh ji, seasonal hydration ORS kits and chronic medication refills have the strongest repeat volume (+38% YoY). Your active offers include 'Free Delivery > ₹499' and 'Senior Citizen 15% OFF'. We can automate monthly chronic refills (Option 1) or family wellness kits (Option 2). What should we do?",
        chips: [
          { text: "Chronic medication refill kaise schedule karein?", unknown: false },
          { text: "Seasonal ORS hydration essentials mein kya chal raha hai?", unknown: false },
          { text: "Option 1 (Monthly refill delivery)", unknown: false },
          { text: "What about Option 3 or a custom package?", unknown: true },
          { text: "Can we do a different option?", unknown: true },
          { text: "Senior citizen 15% discount push karo", unknown: false },
          { text: "Can we do a 90% discount flash sale?", unknown: true }
        ]
      }
    };

    function onSituationChange(merchantId) {
      activeMerchantId = merchantId;
      resetSession(false);
    }

    function loadSituation(merchantId) {
      const data = SITUATIONS[merchantId] || SITUATIONS["m_001_drmeera_dentist_delhi"];
      
      // Update Stage 1: Prompt & Context
      document.getElementById('merchant-city-badge').textContent = data.badge;
      document.getElementById('prompt-status-tag').textContent = `✓ Prompt Updated for ${data.name}`;
      document.getElementById('prompt-tokens-badge').textContent = `Category: ${data.category} • Locality: ${data.locality}`;
      document.getElementById('prompt-preview-content').textContent = data.promptText;

      // Update Stage 2: Chips
      const chipsCont = document.getElementById('chips-container');
      chipsCont.innerHTML = '';
      data.chips.forEach(c => {
        const btn = document.createElement('button');
        btn.className = 'chip-btn' + (c.unknown ? ' chip-unknown' : '');
        btn.innerHTML = (c.unknown ? '✨ ' : '') + `"${c.text}"`;
        btn.onclick = () => {
          document.getElementById('chat-input').value = c.text;
          sendMerchantMessage();
        };
        chipsCont.appendChild(btn);
      });

      // Update Stage 3: Phone Header & Initial Greeting
      document.getElementById('chat-header-status').textContent = `active with ${data.name} (${data.business}) • Online`;
      
      const chat = document.getElementById('chat-box');
      chat.innerHTML = `
        <div class="bubble bubble-bot">
          ${data.greeting}
          <div class="bubble-time">${getCurrentTime()}</div>
        </div>
      `;

      turnCount = 1;
      document.getElementById('turns-counter').textContent = `Turns: ${turnCount}`;
    }

    function getCurrentTime() {
      return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function appendBubble(role, text, meta = '') {
      const chat = document.getElementById('chat-box');
      const div = document.createElement('div');
      div.className = 'bubble ' + (role === 'user' ? 'bubble-user' : 'bubble-bot');

      let html = text.replace(/\\n/g, '<br>');
      if (meta) {
        html += `<br><span class="meta-tag">${meta}</span>`;
      }
      html += `<div class="bubble-time">${getCurrentTime()}</div>`;

      div.innerHTML = html;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    async function sendMerchantMessage() {
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';

      // Stage 2: User input sent
      appendBubble('user', text);
      turnCount++;
      document.getElementById('turns-counter').textContent = `Turns: ${turnCount}`;

      // Stage 3: Call LLM API (persisting conversation_id for continuous dialogue until reset)
      try {
        const res = await fetch('/v1/reply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: activeConversationId,
            merchant_id: activeMerchantId,
            message: text
          })
        }).then(r => r.json());

        turnCount++;
        document.getElementById('turns-counter').textContent = `Turns: ${turnCount}`;

        if (res.action === 'send') {
          appendBubble('bot', res.body, `Action: ${res.action} • CTA: ${res.cta || 'interactive'} • Rationale: ${res.rationale || 'Grounded reply'}`);
        } else if (res.action === 'wait') {
          appendBubble('bot', `⏱ [Bot scheduled to pause for ${res.wait_seconds}s]`, `Action: wait`);
        } else if (res.action === 'end') {
          appendBubble('bot', `🔒 [Conversation ended cleanly: ${res.rationale || 'Finished'}]`, `Action: end`);
        }
      } catch (err) {
        appendBubble('bot', 'Error communicating with LLM engine: ' + err.message);
      }
    }

    async function resetSession(callTeardown = true) {
      if (callTeardown) {
        try {
          await fetch('/v1/teardown', { method: 'POST' });
        } catch (e) {
          console.warn('Teardown warning:', e);
        }
      }
      activeConversationId = "conv_stage_" + Date.now();
      loadSituation(activeMerchantId);
    }

    // Initialize with first situation
    loadSituation(activeMerchantId);
  </script>
</body>
</html>
"""
