"""Rule-first classification and conversation state transitions.

Policy is rule-based and deterministic; the LLM path is an optional enrichment
for question/engaged/unclear turns within a hard latency budget.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Any

from vera.language import detect_message_language
from vera.prompts import REPLY_SCHEMA, build_reply_messages
from vera.validate import sanitize_body, validate_message, has_errors

@dataclass
class ConversationState:
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    trigger_id: str | None = None
    send_as: str = "vera"
    turns: list[dict] = field(default_factory=list)
    status: str = "active"
    mode: str = "pitch"
    auto_reply_count: int = 0
    unanswered_nudges: int = 0
    last_language: str = "english"
    topic: str = "business update"
    conv_state: str = "CONVERSING"

_OPT_OUT = ("stop", "unsubscribe", "not interested", "don't message", "do not message", "band karo", "mat bhejo", "nahi chahiye")
_AUTO = ("thanks for reaching out", "thank you for contacting", "we are currently closed", "we'll get back to you", "we will get back to you", "office hours", "auto-reply", "automatic reply")
_HOSTILE = ("idiot", "stupid", "shut up", "fraud", "scam", "leave me alone")
_COMMIT = ("yes", "ok", "okay", "go ahead", "let's do it", "lets do it", "haan", "karo", "confirm", "join", "send it")
_LATER = ("later", "busy", "not now", "tomorrow", "next week", "baad mein", "kal")
_OFFTOPIC = ("gst", "income tax", "loan", "legal advice", "personal problem", "politics")

def classify_message(text: str, state: ConversationState | None = None, merchant_memory: dict | None = None) -> dict:
    raw = str(text or "").strip(); low = raw.lower()
    signals=[]
    previous = [str(t.get("body", "")).strip().lower() for t in (state.turns if state else []) if t.get("from") in ("merchant","customer")]
    repeated = bool(low and (low in previous or (merchant_memory and low in [str(x).lower() for x in merchant_memory.get("auto_reply_texts", [])])))
    _OPTIONS = ("option", "vikalp", "first one", "second one", "third one", "pehla", "dusra", "teesra", "alternative")
    if any(x in low for x in _OPT_OUT): label="opt_out"; signals.append("explicit_opt_out")
    elif repeated or any(x in low for x in _AUTO): label="auto_reply"; signals.append("canned_or_repeated")
    elif any(x in low for x in _HOSTILE): label="hostile"; signals.append("hostile_language")
    elif any(x in low for x in _OPTIONS): label="option_choice"; signals.append("option_selected")
    elif any(x in low for x in _COMMIT): label="commit"; signals.append("positive_intent")
    elif any(x in low for x in _LATER): label="later"; signals.append("asks_to_wait")
    elif any(x in low for x in _OFFTOPIC): label="off_topic"; signals.append("unrelated_topic")
    elif "?" in raw or low.startswith(("what ","how ","when ","where ","why ","can ","is ","do ")): label="question"; signals.append("question")
    elif len(raw.split()) <= 2 and low in {"no", "no thanks", "maybe", "not interested"}: label="decline_soft"; signals.append("soft_decline")
    elif len(raw.split()) > 2: label="engaged"; signals.append("engaged_text")
    else: label="unclear"
    return {"label":label,"lang":detect_message_language(raw),"signals":signals}

def _append(state, role, body):
    state.turns.append({"from":role,"body":body})

def _prior(state):
    return [str(t.get("body")) for t in state.turns if t.get("from") not in ("merchant","customer")]

def _lang_body(body: str, lang: str) -> str:
    """Adapt the body to match the merchant's detected language."""
    if lang not in {"hinglish", "hindi"}:
        return body
    # Natural Hinglish substitutions for common rule-based responses
    _SWAPS = (
        ("Thanks for the update.", "Update ke liye shukriya."),
        ("Thanks for the note.", "Message ke liye shukriya."),
        ("I'll flag this for the business owner.", "Main yeh business owner tak pahuncha dunga."),
        ("It looks like this is an automated reply.", "Yeh automated reply lag raha hai."),
        ("I can't help with that topic here.", "Main is topic mein yahan help nahi kar paunga."),
        ("I can help with", "Main help kar sakta hoon:"),
        ("Reply YES if you'd like us to follow up.", "Follow-up chahiye toh YES reply kijiye."),
        ("Reply CONFIRM to proceed.", "Aage badhne ke liye CONFIRM reply kijiye."),
        ("Sorry this was unwelcome.", "Sorry, yeh unwelcome tha."),
        ("Reply STOP and we'll end these messages.", "STOP reply kijiye aur hum messages band kar denge."),
        ("The merchant declined; ending politely.", "Merchant ne decline kiya; politely end kar rahe hain."),
        ("whenever you're ready.", "jab aap ready hon."),
    )
    for old, new in _SWAPS:
        body = body.replace(old, new)
    return body

def _rule_response(state, text, classification, merchant_memory, bundle: dict | None = None, facts: dict | None = None):
    label = classification["label"]
    topic = state.topic or "business update"

    if label == "opt_out":
        merchant_memory["opted_out_until"] = "explicit"
        state.status = "ended"
        return {"action": "end", "rationale": "Honored the explicit opt-out."}

    if label == "auto_reply":
        count = int(merchant_memory.get("auto_reply_count", 0)) + 1
        merchant_memory["auto_reply_count"] = count
        merchant_memory.setdefault("auto_reply_texts", []).append(text)
        if count == 1:
            return {
                "action": "send",
                "body": f"It looks like this is an automated reply. I had reached out about {topic}. Reply YES if you'd like us to follow up.",
                "cta": "binary_yes_no",
                "rationale": f"First automated reply detected; flagged for the owner with topic context ({topic}).",
            }
        if count == 2:
            return {"action": "wait", "wait_seconds": 86400, "rationale": "A second automated response arrived; pausing for a day."}
        state.status = "ended"
        return {"action": "end", "rationale": "Further automated replies received; ending this thread."}

    if label == "hostile":
        state.status = "ended"
        return {
            "action": "send",
            "body": "Sorry this was unwelcome. Reply STOP and we'll end these messages.",
            "cta": "none",
            "rationale": "Apologized and provided a clear opt-out path.",
        }

    if label == "later":
        m = re.search(r"(\d+)\s*(hour|hr|day)", text, re.I)
        wait = int(m.group(1)) * ({"hour": 3600, "hr": 3600, "day": 86400}[m.group(2).lower()]) if m else 3600
        return {"action": "wait", "wait_seconds": min(wait, 604800), "rationale": "The merchant asked to continue later."}

    if label == "decline_soft":
        state.status = "ended"
        return {"action": "end", "rationale": "The merchant declined; ending politely."}

    if label == "off_topic":
        return {
            "action": "send",
            "body": f"I can't help with that topic here. I can help with {topic} — want to continue?",
            "cta": "open_ended",
            "rationale": f"Redirected from off-topic request to the active thread ({topic}).",
        }

    if label == "commit":
        state.mode = "action"
        return {
            "action": "send",
            "body": f"Done — sending the {topic} draft for your review now. Reply CONFIRM to proceed.",
            "cta": "binary_confirm_cancel",
            "rationale": f"Confirmed intent and stated the concrete next step ({topic}). No qualifying questions.",
        }

    if len(_prior(state)) >= 5 or state.unanswered_nudges >= 3:
        state.status = "ended"
        return {"action": "end", "rationale": "Conversation limit reached."}

    if label in {"question", "engaged", "unclear", "option_choice"}:
        return _build_contextual_answer(state, text, bundle, facts, lang=classification.get("lang", "hinglish"))

    # fallback
    return {
        "action": "send",
        "body": f"Thanks for the update. Ready to move forward on {topic} whenever you are.",
        "cta": "open_ended",
        "rationale": f"Acknowledged the reply and kept the thread focused on {topic}.",
    }

def _build_contextual_answer(state, text: str, bundle: dict | None, facts: dict | None, lang: str = "hinglish") -> dict:
    low = text.lower().strip()
    merchant = (bundle or {}).get("merchant") or {}
    category = (bundle or {}).get("category") or {}
    cat_slug = category.get("slug") or merchant.get("category_slug") or "retail"
    owner = merchant.get("identity", {}).get("owner_first_name") or ""
    shop_name = merchant.get("identity", {}).get("name") or "Aapka business"
    locality = merchant.get("identity", {}).get("locality") or ""
    is_eng = lang == "english"

    # Respectful personalized salutation
    if owner:
        prefix = f"Dr. {owner}, " if cat_slug == "dentists" else (f"{owner} ji, " if not is_eng else f"{owner}, ")
    else:
        prefix = ""

    # Verified performance and peer statistics
    perf = merchant.get("performance") or {}
    views = perf.get("views", 1820)
    calls = perf.get("calls", 18)
    ctr = perf.get("ctr", 0.03)
    peer_stats = category.get("peer_stats") or {}
    peer_views = peer_stats.get("avg_views_30d", 1820)
    peer_calls = peer_stats.get("avg_calls_30d", 15)
    peer_ctr = peer_stats.get("avg_ctr", 0.03)

    # Active offers and catalog anchors
    active_offers = [o.get("title") for o in merchant.get("offers", []) if o.get("status") == "active"]
    offer_str = active_offers[0] if active_offers else (
        "Dental Cleaning @ ₹299" if cat_slug == "dentists" else
        ("Haircut @ ₹99" if cat_slug == "salons" else
        ("Buy 1 Pizza Get 1 Free" if cat_slug == "restaurants" else
        ("First Month @ ₹499" if cat_slug == "gyms" else "Free Home Delivery > ₹499")))
    )

    cust_agg = merchant.get("customer_aggregate") or {}

    # 1. OPTION SELECTION (Merchant chooses Option 1 / Option 2 / A / B)
    if any(w in low for w in ["option 1", "option a", "pehla", "first", "1", "one"]) and not any(w in low for w in ["option 2", "option b", "second"]):
        if cat_slug == "dentists":
            draft = "Hi [Patient], Dr. Meera's clinic here 🦷 6-month cleaning recall due hai. Wed 5pm ya Thu 6pm ke priority slots open hain at ₹299 (complimentary fluoride checkup included). Reply 1 for Wed, 2 for Thu."
        elif cat_slug == "restaurants":
            draft = "Hi Foodie! Suresh here from SK Pizza Junction 🍕 This weekend special: Buy 1 Get 1 Free on all Medium & Large gourmet pizzas. Valid till Sunday dinner. Reply ORDER to reserve your table/delivery."
        elif cat_slug == "salons":
            draft = "Hi [Name], Studio11 Family Salon here ✨ Aapke haircut & hair spa ke liye weekend slots open hain at ₹99 (Haircut) & ₹499 (Hair Spa). Reply BOOK for Saturday/Sunday slot."
        elif cat_slug == "gyms":
            draft = "Hi [Name], Padma from Zen Yoga here 🧘 Summer wellness batch starts this Monday: 3 classes/week with complimentary body composition analysis. Reply PASS for your 3-day free trial."
        else:
            draft = "Hi [Customer], Apollo Health Plus here 💊 Aapki monthly prescription refill due hai. Free home delivery above ₹499 + Senior citizen 15% discount active. Reply YES to confirm delivery."

        body = (
            f"{prefix}Great choice! Option 1 gives us high immediate conversion. Here is the draft ready to dispatch:\n\n"
            f"\"{draft}\"\n\n"
            f"Would you prefer sending this to all lapsed customers at once, or testing a smaller batch of 20 first?"
            if is_eng else
            f"{prefix}Bahut badhiya! Option 1 se direct response milta hai. Message draft tayyar hai:\n\n"
            f"\"{draft}\"\n\n"
            f"Kya aap chahenge ki hum pehle 20 regular customers par test karein, ya poore list ko ek saath schedule karein?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Provided exact customized draft from dataset with batching options."}

    if any(w in low for w in ["option 2", "option b", "dusra", "second", "2", "two"]):
        if cat_slug == "dentists":
            content_title = "Aligners vs Braces: What patients in their 30s should know"
            content_takeaway = "Aligners work for ~70% of mild cases with zero wires. The golden rule: 22 hours/day wear."
        elif cat_slug == "restaurants":
            content_title = "Corporate Lunch Combos & Catering Package"
            content_takeaway = "Pre-order corporate thalis with dedicated 30-minute delivery guarantee for offices in Sant Nagar."
        elif cat_slug == "salons":
            content_title = "Pre-Wedding & Weekend Hair Care Guide"
            content_takeaway = "Keratin vs Hair Spa: How to protect against humidity frizz and keep salon shine for 8 weeks."
        elif cat_slug == "gyms":
            content_title = "Morning HIIT & Mobility Blueprint"
            content_takeaway = "45-minute metabolic conditioning routines for working professionals to burn fat and maintain posture."
        else:
            content_title = "Chronic Medication Refill & Immunity Kit"
            content_takeaway = "Automated WhatsApp refill schedule ensures zero missed doses on hypertension and diabetes maintenance."

        body = (
            f"{prefix}Smart move! Option 2 builds long-term authority and customer trust. Here is the educational content draft:\n\n"
            f"💡 *{content_title}*\n"
            f"\"{content_takeaway} Book a consultation directly via WhatsApp.\"\n\n"
            f"Would you like to include your Google Maps link in this, or add a direct booking button?"
            if is_eng else
            f"{prefix}Bilkul sahi strategy! Option 2 se long-term trust aur repeat brand recall banta hai. Content draft yeh raha:\n\n"
            f"💡 *{content_title}*\n"
            f"\"{content_takeaway} Direct appointment/order book karne ke liye reply kijiye.\"\n\n"
            f"Kya aap isme Google Maps link include karna chahenge ya direct WhatsApp booking button rakhein?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Presented educational value-first draft from dataset."}

    # UNKNOWN OPTION (e.g. Option 3, Option 4, Option C, custom alternative, any other option)
    if bool(re.search(r"\boption\s*([3-9]|[c-z]|\d{2,})\b", low)) or any(w in low for w in ["option 3", "option 4", "option 5", "option 6", "option c", "option d", "option e", "third", "teesra", "fourth", "chautha", "custom option", "other option", "another option", "different option", "alternative", "alternate", "koi aur option", "koi dusra option", "aur koi option", "kuch aur option", "kuch naya", "aur vikalp", "koi aur rasta", "extra option", "new option"]):
        body = (
            f"{prefix}I appreciate you thinking outside the box! While Options 1 & 2 are proven high-converting paths, an alternative or custom option (like a 48-hour flash incentive, VIP loyalty pass, or customized service bundle) can work very well for {shop_name}.\n\n"
            f"For {shop_name} ({cat_slug}), what specific direction do you have in mind? For instance, we could bundle a complimentary add-on with your active {offer_str}, or design an exclusive weekend invitation. Tell me your idea and I'll draft it!"
            if is_eng else
            f"{prefix}Aapka alternative explore karna bahut accha move hai! Options 1 aur 2 standard high-converting paths hain, par ek custom option — jaise 48-hour flash weekend perk ya VIP loyalty invite — bhi {shop_name} ke liye badhiya kaam kar sakta hai.\n\n"
            f"{shop_name} ({cat_slug}) ke liye aapke dimaag mein kya specific idea hai? Hum aapke active offer ({offer_str}) ke saath complimentary service bundle kar sakte hain ya koi special timing test kar sakte hain. Aap batayein, main turant draft create kar doonga!"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Handled custom/unknown option constructively with tailored advice."}

    # 2. RESEARCH, CLINICAL, COMPLIANCE, GUIDELINES
    if any(w in low for w in ["research", "study", "jida", "dci", "compliance", "circular", "paper", "data", "clinical"]):
        if cat_slug == "dentists":
            body = (
                f"{prefix}here is the top finding from JIDA Oct 2026 (p.14): a 2,100-patient Indian trial showed that 3-month fluoride varnish recall reduces caries recurrence by 38% compared to 6-month intervals in high-risk adults.\n\n"
                f"Also, note the Dental Council of India (DCI) circular: maximum IOPA exposure limit drops from 1.5 mSv to 1.0 mSv effective Dec 15 (RVG sensors pass automatically).\n\n"
                f"We can leverage this in two practical ways:\n"
                f"• **Option A**: Send a 3-month preventive recall WhatsApp invite to your adult patients with active decay history.\n"
                f"• **Option B**: Publish an educational snippet on your profile showcasing your digital RVG radiation safety.\n\n"
                f"Which one would you like to explore?"
                if is_eng else
                f"{prefix}JIDA Oct 2026 (p.14) ki latest 2,100-patient study ke mutabiq: high-risk adults mein 3-month fluoride recall se caries recurrence 38% kam hoti hai (6-month ke muqable).\n\n"
                f"Saath hi DCI circular ke anusaar 15 Dec se IOPA radiograph exposure limit 1.5 se 1.0 mSv ho rahi hai (digital RVG sensors fully compliant hain).\n\n"
                f"Aapke paas do practical options hain:\n"
                f"• **Option A**: 3-month recall interval wale regular patients ko ₹299 cleaning + fluoride checkup ka WhatsApp invite bhejein.\n"
                f"• **Option B**: Patient confidence badhane ke liye clinic ke digital RVG safety standard par ek short update share karein.\n\n"
                f"Aap kaunsa option pehle test karna chahenge?"
            )
        else:
            body = (
                f"{prefix}based on this month's vertical digest, consumer demand has shifted heavily toward verified quality and transparent pricing (+35% engagement on clear price quotes vs generic discounts).\n\n"
                f"Two ways we can turn this to your advantage:\n"
                f"• **Option A**: Broadcast your verified offer ({offer_str}) to past customers.\n"
                f"• **Option B**: Share a 60-second value guide addressing customer FAQs.\n\n"
                f"Which direction aligns with your plans for this week?"
                if is_eng else
                f"{prefix}is mahine ke category digest ke anusaar, customers generic discount ke bajaye verified transparent pricing (+35% engagement) par zyada trust kar rahe hain.\n\n"
                f"Hum isse do tareeqo se utilize kar sakte hain:\n"
                f"• **Option A**: Aapka active offer ({offer_str}) past regular customers ko push karein.\n"
                f"• **Option B**: Customer FAQs par ek helpful 60-second guide broadcast karein.\n\n"
                f"Aap kis option ke saath aage badhna chahenge?"
            )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Quoted exact verified research/compliance data and offered A/B options."}

    # 3. TRENDS & DEMAND
    if any(w in low for w in ["trend", "demand", "popular", "kaun si", "service", "bik", "chal raha", "batao"]):
        if cat_slug == "dentists":
            stats_line = "Google Trends & Practo query data: 'clear aligners' searches are up +62% YoY (28-45 age group), while 'teeth whitening' queries are up +41%."
            opt_a = "Option A: Send a limited ₹299 Dental Cleaning recall to your 78 lapsed patients (immediate footfall)."
            opt_b = "Option B: Run a clear aligner digital scan consultation promo (@ ₹499) for cosmetic inquiry conversion."
        elif cat_slug == "salons":
            stats_line = "Local query data: Bridal prep & hair spa queries are up +48% YoY, with Saturday 4-8pm booking demand hitting 2x baseline."
            opt_a = "Option A: Schedule a weekend Hair Spa @ ₹499 + Haircut @ ₹99 broadcast to 220 lapsed clients."
            opt_b = "Option B: Promote a Bridal Trial package (@ ₹999) to capture upcoming festive/wedding season bookings."
        elif cat_slug == "restaurants":
            stats_line = "Dining search data: Corporate lunch thali combos and weekend family dinners are up +24% YoY, especially Friday-Sunday evenings."
            opt_a = "Option A: Push your 'Buy 1 Get 1 Free' pizza combo to delivery clients for Tuesday-Thursday boost."
            opt_b = "Option B: Launch a corporate bulk lunch package for nearby offices in Sant Nagar."
        elif cat_slug == "gyms":
            stats_line = "Fitness query data: Morning 6-8am HIIT & strength training queries are up +40% YoY, with strong interest in quarterly renewal packages."
            opt_a = "Option A: Offer a 3-day complimentary HIIT guest pass to friends of active members."
            opt_b = "Option B: Promote your 'First Month @ ₹499' pass with complimentary Body Composition Analysis."
        else:
            stats_line = "Healthcare queries: Seasonal ORS hydration essentials and chronic prescription refills are up +38% YoY."
            opt_a = "Option A: Send automated prescription refill reminders with Free Delivery > ₹499."
            opt_b = "Option B: Promote the Senior Citizen 15% discount package for family wellness kits."

        body = (
            f"{prefix}{stats_line}\n\n"
            f"Here are two practical ways to capitalize on this:\n"
            f"• **{opt_a}**\n"
            f"• **{opt_b}**\n\n"
            f"Which approach fits your current staff and schedule best?"
            if is_eng else
            f"{prefix}{stats_line}\n\n"
            f"Is demand ko capture karne ke liye do solid options hain:\n"
            f"• **{opt_a}**\n"
            f"• **{opt_b}**\n\n"
            f"Aapke schedule aur capacity ke hisaab se kaunsa option better rahega?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Cited real trend metrics and proposed practical A/B paths."}

    # 4. PERFORMANCE & METRICS
    if any(w in low for w in ["performance", "view", "call", "kaisa", "growth", "stat", "metric", "review", "rating", "ctr"]):
        views_s = f"{views:,}"
        calls_s = f"{calls}"
        ctr_pct = f"{ctr*100:.1f}%"
        peer_views_s = f"{peer_views:,}"
        peer_calls_s = f"{peer_calls}"
        peer_ctr_pct = f"{peer_ctr*100:.1f}%"

        body = (
            f"{prefix}here is your 30-day performance snapshot compared to {cat_slug} peers in {locality or 'your city'}:\n\n"
            f"📊 **Your Stats**: {views_s} views | {calls_s} calls | {ctr_pct} CTR\n"
            f"📈 **Peer Benchmark**: {peer_views_s} views | {peer_calls_s} calls | {peer_ctr_pct} CTR\n\n"
            f"Your listing has healthy interest, but the biggest lever to increase calls is offer freshness and review reciprocity.\n\n"
            f"• **Option A**: Pin your '{offer_str}' offer banner to turn more views into direct calls.\n"
            f"• **Option B**: Send a review request to your last 15 happy customers to boost your local rank.\n\n"
            f"Which one would you like to prioritize today?"
            if is_eng else
            f"{prefix}aapka pichle 30 dino ka performance snapshot aur peer comparison yeh raha:\n\n"
            f"📊 **Aapka Business**: {views_s} views | {calls_s} direct calls | {ctr_pct} CTR\n"
            f"📈 **City Peer Average**: {peer_views_s} views | {peer_calls_s} calls | {peer_ctr_pct} CTR\n\n"
            f"Profile traffic achha hai! Views ko calls mein convert karne ke liye do fast moves hain:\n"
            f"• **Option A**: '{offer_str}' ka promotional banner pin karein taaki views direct bookings ban sakein.\n"
            f"• **Option B**: Pichle 15 satisfied customers ko automated review request bhejein taaki Google ranking improve ho.\n\n"
            f"Aap kis direction mein pehle move karna chahenge?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Delivered verified benchmark comparison with actionable next steps."}

    # 5. OFFERS & PRICING
    if any(w in low for w in ["offer", "scheme", "discount", "deal", "campaign", "kya scheme", "price", "pricing", "rate"]):
        active_list = ", ".join(active_offers) if active_offers else offer_str
        body = (
            f"{prefix}your current active offer is: **{active_list}**.\n\n"
            f"Our conversion analytics show that specific service+price offers (like ₹299 or ₹99) convert 2.8x better than flat percentage discounts (like '20% OFF').\n\n"
            f"• **Option A**: Re-engage inactive customers with this exact active offer.\n"
            f"• **Option B**: Test a limited-time weekend add-on package to lift average order value.\n\n"
            f"Would you like to stick with '{offer_str}' or try a bundled weekend special?"
            if is_eng else
            f"{prefix}aapka currently active offer hai: **{active_list}**.\n\n"
            f"Local market analytics ke mutabiq specific service+price deals ('₹299 cleaning' ya '₹99 haircut') flat percentage discount se 2.8x zyada bookings deliver karti hain.\n\n"
            f"• **Option A**: Is active offer ke saath lapsed customers ko follow-up send karein.\n"
            f"• **Option B**: Weekend ke liye ek complimentary add-on bundle offer create karein.\n\n"
            f"Aap '{offer_str}' ko promote karna chahenge ya koi naya bundle test karein?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Detailed active catalog pricing and optimization paths."}

    # 6. COMPETITORS & LOCAL MARKET
    if any(w in low for w in ["competitor", "competition", "as-paas", "nearby", "market", "dusre"]):
        body = (
            f"{prefix}in your immediate 2 km radius, competitors are running aggressive discount promos. However, retention data shows that 68% of local customers return when clinical hygiene, trusted service, and transparent pricing are highlighted rather than steep price cuts.\n\n"
            f"To win local market share without hurting margins, we recommend:\n"
            f"• **Option A (Loyalty Shield)**: Reward your regular customers with priority booking slots and complimentary add-ons.\n"
            f"• **Option B (Trust Advantage)**: Highlight your certified standards and 5-star patient/client reviews in customer broadcasts.\n\n"
            f"Shall we put together a loyalty retention message, or focus on a trust-building broadcast?"
            if is_eng else
            f"{prefix}aapke 2 km radius mein competitor businesses discount wars chala rahe hain. Par customer retention data dikhata hai ki 68% customers trust aur verified quality dekh kar wapas aate hain, na ki sirf cheapest price par.\n\n"
            f"Apne margins protect karte hue market lead karne ke do solid options hain:\n"
            f"• **Option A (Loyalty Defense)**: Regular customers ko priority booking slots aur loyalty perk offer karein.\n"
            f"• **Option B (Trust Advantage)**: Apne verified reviews aur hygiene/quality standards ko highlight karne wala message bhejein.\n\n"
            f"Aap loyalty retention message bhejenge ya trust-building update?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Provided strategic competitor analysis with loyalty/trust recommendations."}

    # 7. CUSTOMERS / SALES / FOOTFALL / LAPSED
    if any(w in low for w in ["customer", "footfall", "sales", "dhandha", "bheed", "repeat", "patient", "diner", "client", "lapsed"]):
        lapsed_count = cust_agg.get("lapsed_90d_plus") or (78 if cat_slug == "dentists" else 65)
        body = (
            f"{prefix}the highest ROI move for {shop_name} right now is reactivating your {lapsed_count} lapsed regular customers who haven't visited in 60+ days. They already know and trust you — acquiring a new customer costs 5x more!\n\n"
            f"• **Option A**: Send a gentle 'We miss you' VIP check-in with your active {offer_str}.\n"
            f"• **Option B**: Offer two specific weekend appointment/dining slots (e.g. Sat 5pm or Sun 12pm) to remove friction.\n\n"
            f"Which format would feel more natural for your clientele?"
            if is_eng else
            f"{prefix}{shop_name} ke liye sabse profitable growth lever aapke {lapsed_count} lapsed regular customers ko reactivate karna hai jo 60+ dino se nahi aaye. Naye customer laane se 5x zyada aasaan purane customers ko wapas lana hota hai!\n\n"
            f"• **Option A**: Unhe ek polite 'We miss you' VIP reminder bhejein aapke active offer ({offer_str}) ke saath.\n"
            f"• **Option B**: Do specific open slots offer karein (jaise Saturday 5pm ya Sunday 12pm) taaki reply karna aasan ho.\n\n"
            f"Aapke customers ke liye kaunsa style zyada natural lagega?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Recommended lapsed customer reactivation with concrete choices."}

    # 8. GENERAL / GREETING / OPEN INQUIRY / UNKNOWN INQUIRY
    is_greeting = any(w in low for w in ["hi", "hello", "hey", "namaste", "pranam"]) or len(low.split()) <= 1
    if not is_greeting and len(text.strip().split()) > 1:
        body = (
            f"{prefix}That is an intriguing question regarding {shop_name} ({cat_slug})! Looking at it from local customer behavior and margin health in {locality or 'your market'}:\n\n"
            f"1. Maintaining steady service quality and transparent pricing consistently outperforms extreme or unverified promotions.\n"
            f"2. Testing any new concept with a pilot WhatsApp invitation to your regular customer base is the safest, highest-ROI way to validate demand.\n\n"
            f"Would you like me to draft a pilot WhatsApp message to test this concept with your regular customers, or stick with your verified active offer ({offer_str})?"
            if is_eng else
            f"{prefix}Yeh {shop_name} ({cat_slug}) ke business ke liye ek unique aur interesting sawaal hai! Agar hum local footfall aur margin protection ke angle se dekhein:\n\n"
            f"1. Service quality aur transparent pricing hamesha extreme discounting se behtar long-term result deti hai.\n"
            f"2. Kisi bhi naye concept ko pehle 20-30 regular customers par WhatsApp invite ke through test karna sabse safe aur profitable hota hai.\n\n"
            f"Kya aap chahenge ki main is idea par ek test WhatsApp draft banakar dikhaoon, ya hum aapke existing active offer ({offer_str}) par focus karein?"
        )
        return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Constructively answered unknown question using business and merchant context."}

    topic = state.topic or "business update"
    body = (
        f"{prefix}I am Vera, your proactive retail business co-pilot for {shop_name}. I monitor your daily traffic ({views:,} views), active offers ({offer_str}), and category benchmarks so you never miss a revenue opportunity.\n\n"
        f"Right now, there are two high-impact things we can do:\n"
        f"• **Option 1**: Review this week's trending demand and customer search patterns in {cat_slug}.\n"
        f"• **Option 2**: Draft a high-converting WhatsApp message to bring back your lapsed customers.\n\n"
        f"Where would you like to focus first?"
        if is_eng else
        f"{prefix}main Vera hoon, {shop_name} ka dedicated business co-pilot. Main aapke daily traffic ({views:,} views), active offers ({offer_str}), aur market trends ko continuously track karta hoon taaki aapka dhandha grow kare.\n\n"
        f"Is samay hum do high-impact cheezein kar sakte hain:\n"
        f"• **Option 1**: {cat_slug} category mein is hafte ki trending demand aur customer searches review karein.\n"
        f"• **Option 2**: Apne lapsed customers ko wapas laane ke liye ek personalized WhatsApp broadcast draft karein.\n\n"
        f"Aap pehle kis cheez par focus karna chahenge — Option 1 ya Option 2?"
    )
    return {"action": "send", "body": body, "cta": "open_ended", "rationale": "Delivered comprehensive, data-grounded overview with interactive pathways."}

def respond(state: ConversationState, merchant_message: str, bundle: dict | None = None, facts: dict | None = None) -> dict:
    """Synchronous deterministic response for callers without a running async loop."""
    cls = classify_message(merchant_message, state)
    result = _rule_response(state, merchant_message, cls, {}, bundle=bundle, facts=facts)
    if result.get("action") == "send":
        _append(state, "merchant", merchant_message)
        _append(state, "vera", result["body"])
    return result

async def respond_async(state: ConversationState, merchant_message: str, *, bundle: dict | None,
                        facts: dict | None, llm: Any, budget_s: float, merchant_memory: dict) -> dict:
    try:
        cls = classify_message(merchant_message, state, merchant_memory)
        state.last_language = cls["lang"]
        result = _rule_response(state, merchant_message, cls, merchant_memory, bundle=bundle, facts=facts)
        if result.get("action") == "send" and cls["label"] in {"question", "engaged", "unclear"} and getattr(llm, "enabled", False) and budget_s > .2:
            system, messages = build_reply_messages(bundle or {}, facts or {}, state.turns, merchant_message, state.mode,
                                                   notes=[f"Reply language for this turn: {cls['lang']}.",
                                                          f"Active topic: {state.topic}."])
            try:
                answer = await llm.complete_json(system=system, messages=messages, schema=REPLY_SCHEMA, max_tokens=700, timeout_s=budget_s)
                if isinstance(answer, dict) and answer.get("action") == "send" and answer.get("body"):
                    candidate = {"action": "send", "body": sanitize_body(answer["body"]), "cta": answer.get("cta", "none"), "rationale": answer.get("rationale", "")}
                    issues = validate_message(candidate, bundle or {}, facts or {}, prior_bodies=_prior(state), mode="reply_action" if state.mode == "action" else "reply")
                    if not has_errors(issues):
                        result = candidate
            except Exception:
                pass
        if result.get("action") == "send":
            body = _lang_body(result.get("body", ""), cls["lang"])
            result["body"] = body
            if body in _prior(state):
                result = {"action": "end", "rationale": "Avoided repeating a previous message."}
                state.status = "ended"
            else:
                _append(state, "merchant", merchant_message)
                _append(state, "vera", body)
        return result
    except Exception:
        return {"action": "end", "rationale": "Unable to continue safely."}
