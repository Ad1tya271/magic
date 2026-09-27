"""Deterministic per-kind WhatsApp composer — the first-class fallback path.

Every number in generated bodies traces to the FactSheet (which traces to raw
contexts), so the anti-fabrication validator always passes. Bodies aim for
2-3 verifiable facts, category-appropriate voice, natural Hinglish/English,
accurate CTA classifications, and clear compulsion levers.
"""
from __future__ import annotations

from vera.validate import sanitize_body


# ── fact extraction helpers ──────────────────────────────────────────────────

def _v(facts: dict, key: str) -> str | None:
    """Value portion of a fact: 'Label: val' → 'val'."""
    raw = (facts.get("facts") or {}).get(key, "")
    return raw.split(": ", 1)[1].strip() if ": " in raw else (raw.strip() or None)


def _first(facts: dict, *keys: str) -> str | None:
    for k in keys:
        v = _v(facts, k)
        if v:
            return v
    return None


def _offer(facts: dict) -> str | None:
    o = facts.get("active_offers")
    return o[0] if o else None


def _cat_offer(facts: dict) -> str | None:
    o = facts.get("catalog_offers")
    return o[0] if o else None


def _mode(facts: dict) -> str:
    return (facts.get("language") or {}).get("mode", "english")


def _loc(facts: dict) -> str:
    return facts.get("locality") or facts.get("city") or ""


def _clean_date_str(val: str | None) -> str | None:
    if not val:
        return None
    val = str(val).strip()
    if "T" in val:
        d = val.split("T")[0]
        t = val.split("T")[1].split("+")[0][:5]
        return f"{d} at {t}"
    return val


_REG = {"te": "Namaskaram", "ta": "Vanakkam", "kn": "Namaskara", "mr": "Namaskar"}


def _sal(facts: dict, route: str | None = None) -> str:
    if route == "customer":
        return facts.get("customer_salutation") or facts.get("customer_name") or ""
    mode = _mode(facts)
    base = facts.get("salutation") or facts.get("business_name") or ""
    if mode == "regional_mix":
        reg = (facts.get("language") or {}).get("regional")
        return f"{_REG.get(reg, 'Namaste')} {base}" if base else _REG.get(reg, "Namaste")
    return base


def _hi(text: str, m: str) -> str:
    """Concise Hinglish for CTA strings; passthrough for English."""
    if m not in ("hinglish", "hindi"):
        return text
    return {
        "Reply YES to get started.": "Shuru karne ke liye YES reply kijiye.",
        "Reply YES if this is useful.": "Useful lage toh YES reply kijiye.",
        "Want me to draft one?": "Main ek draft kar doon?",
        "Shall I send the details?": "Details bhej doon?",
        "Want to take a look?": "Ek nazar daalenge?",
        "Reply YES to confirm.": "Confirm ke liye YES reply kijiye.",
        "Reply YES to confirm your refill.": "Refill confirm karne ke liye YES reply kijiye.",
        "Reply YES to book a session.": "Session book karne ke liye YES reply kijiye.",
        "Reply YES if you'd like to rejoin.": "Rejoin karne ke liye YES reply kijiye.",
        "Which slot works best for you?": "Aapke liye kaunsa slot convenient rahega?",
        "Want a quick summary?": "Quick summary chahiye?",
        "Want me to set it up?": "Main set kar doon?",
        "Shall I prepare it for your review?": "Main aapke review ke liye prepare kar doon?",
        "Which one interests you most?": "Kaunsa sabse zyada interest karta hai?",
        "Reply 1 or 2 to pick.": "Choose karne ke liye 1 ya 2 reply kijiye.",
        "Worth exploring?": "Explore karna chahenge?",
        "Want a short readout?": "Short readout chahiye?",
        "Shall I draft one for your review?": "Main ek draft kar doon review ke liye?",
    }.get(text, text)


def _body(*parts: str | None) -> str:
    return sanitize_body(" ".join(p for p in parts if p))


def _perf_line(facts: dict, m: str) -> str | None:
    """One-line performance context with peer comparison when available."""
    ctr = _v(facts, "performance_ctr")
    views = _v(facts, "performance_views")
    calls = _v(facts, "performance_calls")
    if not (ctr or views or calls):
        return None
    parts = []
    if views:
        parts.append(f"{views} views")
    if calls:
        parts.append(f"{calls} calls")
    if ctr:
        parts.append(f"CTR {ctr}")
    return f"Your current 30-day numbers: {', '.join(parts)}." if m == "english" else f"Aapke 30-day numbers: {', '.join(parts)}."


# ── per-kind builders ────────────────────────────────────────────────────────
# Each returns (body, cta_enum, rationale) or None when data is too thin.

def _research_digest(f, b, m, s):
    title = _v(f, "digest_title")
    source = _v(f, "digest_source")
    trial_n = _v(f, "digest_trial_n")
    segment = _first(f, "digest_patient_segment", "trigger_patient_segment")
    if not title:
        return None
    hook = f"{source} mein ek finding —" if source and m in ("hinglish", "hindi") else (f"a finding from {source} —" if source else "a new finding —")
    detail_parts = []
    if trial_n:
        detail_parts.append(f"{trial_n}-patient study")
    if segment:
        detail_parts.append(segment.replace("_", " "))
    detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
    cta = _hi("Want a quick summary?", m)
    body = _body(f"{s},", hook, f"{title.rstrip('.')}{detail}.", cta)
    return body, "open_ended", f"Research digest from {source or 'latest findings'}; anchors on specific trial data and uses curiosity (summary offer)."


def _regulation_change(f, b, m, s):
    title = _v(f, "digest_title")
    deadline = _first(f, "trigger_deadline", "trigger_due_date", "digest_deadline")
    actionable = _v(f, "digest_actionable")
    if not title:
        return None
    hook = "ek compliance update —" if m in ("hinglish", "hindi") else "a compliance update —"
    extra = ""
    if deadline:
        extra += f" Effective {deadline}." if m == "english" else f" Effective date: {deadline}."
    if actionable:
        extra += f" {actionable.rstrip('.')}."
    cta = _hi("Shall I send the details?", m)
    body = _body(f"{s},", hook, f"{title.rstrip('.')}.{extra}", cta)
    return body, "open_ended", f"Compliance alert with deadline; uses loss aversion (regulatory deadline) and effort externalization (details offer)."


def _perf_dip(f, b, m, s):
    metric = _first(f, "trigger_metric", "why_now")
    delta = _first(f, "trigger_delta_pct", "trigger_perf_dip_pct", "delta_calls_pct", "delta_views_pct")
    perf = _perf_line(f, m)
    offer = _offer(f) or _cat_offer(f)
    baseline = _v(f, "trigger_vs_baseline")
    window = _v(f, "trigger_window") or "7d"
    if not metric and not delta:
        return None
    
    delta_clean = str(delta).replace("+", "").replace("-", "") if delta else ""
    base_str = f" (vs baseline of {baseline})" if baseline else ""
    base_str_hi = f" (vs {baseline} baseline)" if baseline else ""

    if m in ("hinglish", "hindi"):
        if metric and delta and "-" in str(delta):
            hook = f"aapki {metric} pichle {window} mein {delta_clean} down hui hai{base_str_hi}."
        elif metric and delta:
            hook = f"aapki {metric} mein recent change dekhi — {delta}."
        else:
            hook = "ek recent performance signal dikha hai."
        fix = f"Ek fresh Google post" + (f" jismein {offer} ho" if offer else "") + " visibility improve kar sakta hai."
    else:
        if metric and delta and "-" in str(delta):
            hook = f"your {metric} dropped {delta_clean} in the last {window}{base_str}."
        elif metric and delta:
            hook = f"your {metric} shows a recent shift — {delta}."
        else:
            hook = "a recent performance signal was detected."
        fix = f"A fresh Google post" + (f" featuring {offer}" if offer else "") + " could help improve visibility."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, perf, fix, cta)
    return body, "open_ended", f"Performance dip alert with specific metric; uses loss aversion and effort externalization (draft offer)."


def _perf_spike(f, b, m, s):
    metric = _first(f, "trigger_metric")
    delta = _first(f, "trigger_delta_pct", "delta_calls_pct", "delta_views_pct")
    driver = _v(f, "trigger_likely_driver")
    perf = _perf_line(f, m)
    driver_hi = f", likely {driver.replace('_', ' ')} ki wajah se." if driver else "."
    driver_en = f", likely driven by {driver.replace('_', ' ')}." if driver else "."
    if m in ("hinglish", "hindi"):
        hook = f"aapki {metric} upar ja rahi hai" if metric else "ek positive trend dikh raha hai"
        hook += f" — {delta} is hafte{driver_hi}" if delta else " is hafte."
    else:
        hook = f"your {metric} is trending up" if metric else "a positive trend this week"
        hook += f" — {delta} this week{driver_en}" if delta else "."
    cta = _hi("Want a short readout?", m)
    body = _body(f"{s},", hook, perf, cta)
    return body, "open_ended", f"Performance spike highlight; uses reciprocity (proactive good-news flag) and curiosity (readout offer)."


def _recall_due(f, b, m, s):
    route = f.get("route")
    cname = f.get("customer_name")
    service = _first(f, "trigger_service_due", "customer_services_received", "customer_services")
    if service:
        service = service.replace("_", " ")
    last_visit = _first(f, "customer_last_visit", "customer_last_visit_date")
    slots = _v(f, "available_slots")
    if route == "customer" and cname:
        greeting = f"{cname},"
        if m in ("hinglish", "hindi"):
            hook = f"aapki last visit" + (f" ({last_visit})" if last_visit else "") + " ke baad follow-up due hai."
            svc = f"{service} ke liye." if service else ""
            slot_line = f"Available slots: {slots}." if slots else ""
        else:
            hook = f"your follow-up" + (f" since {last_visit}" if last_visit else "") + " is due."
            svc = f"For {service}." if service else ""
            slot_line = f"Available slots: {slots}." if slots else ""
        if slots:
            cta = _hi("Which slot works best for you?", m)
            body = _body(greeting, hook, svc, slot_line, cta)
            return body, "multi_choice_slot", f"Recall reminder with slot options for {service or 'service'}; uses low friction multi-choice CTA."
        else:
            cta = _hi("Reply YES to confirm.", m)
            body = _body(greeting, hook, svc, cta)
            return body, "binary_yes_no", f"Recall reminder with patient history; uses specificity and binary confirmation."
    else:
        greeting = f"{s},"
        customer_ref = f"for {cname}" if cname else ""
        if m in ("hinglish", "hindi"):
            hook = f"ek patient follow-up due hai {customer_ref}."
            svc = f"{service}" + (f", last visit {last_visit}" if last_visit else "") + "." if service else ""
        else:
            hook = f"a patient follow-up is due {customer_ref}."
            svc = f"{service}" + (f", last visit {last_visit}" if last_visit else "") + "." if service else ""
        cta = _hi("Shall I send the details?", m)
        body = _body(greeting, hook, svc, cta)
        return body, "open_ended", f"Recall reminder with patient history; uses specificity ({service or 'service'}) and effort externalization."


def _renewal_due(f, b, m, s):
    plan = _v(f, "subscription_plan")
    days = _first(f, "subscription_days_remaining", "trigger_days_remaining")
    if m in ("hinglish", "hindi"):
        hook = f"aapka {plan} subscription" if plan else "aapka subscription"
        hook += f" {days} din mein renew hone wala hai." if days else " renewal ke kareeb hai."
    else:
        hook = f"your {plan} subscription" if plan else "your subscription"
        hook += f" renews in {days} days." if days else " renewal is approaching."
    cta = _hi("Shall I send the details?", m)
    body = _body(f"{s},", hook, cta)
    return body, "open_ended", f"Renewal reminder with specific timeline ({days or 'upcoming'} days); uses loss aversion (expiry) and effort externalization."


def _festival_upcoming(f, b, m, s):
    festival = _v(f, "trigger_festival")
    days = _v(f, "trigger_days_until")
    offer = _offer(f) or _cat_offer(f)
    
    days_int = None
    if days:
        try:
            days_int = int(str(days).replace("days", "").strip())
        except (ValueError, TypeError):
            pass

    if m in ("hinglish", "hindi"):
        if festival:
            if days_int is not None and days_int <= 45:
                hook = f"{festival} {days_int} din mein hai."
            else:
                hook = f"aane wale {festival} season ke liye advance planning ka samay hai."
        else:
            hook = "ek festival season kareeb hai."
        tie = f"Aapke {offer} ke saath ek festive campaign chal sakta hai." if offer else "Ek timely post se footfall badh sakta hai."
    else:
        if festival:
            if days_int is not None and days_int <= 45:
                hook = f"{festival} is {days_int} days away."
            else:
                hook = f"it is time to plan ahead for the upcoming {festival} season."
        else:
            hook = "a festival season is approaching."
        tie = f"A festive campaign featuring {offer} could drive footfall." if offer else "A timely post could capture seasonal demand."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, tie, cta)
    return body, "open_ended", f"Festival opportunity with active offer tie-in; uses seasonal relevance and effort externalization."


def _wedding_package(f, b, m, s):
    days_to = _v(f, "trigger_days_to_wedding")
    if m in ("hinglish", "hindi"):
        hook = "wedding package follow-up ka time hai."
        detail = f"Wedding {days_to} din mein hai." if days_to else ""
    else:
        hook = "time for the wedding package follow-up."
        detail = f"The wedding is {days_to} days away." if days_to else ""
    cta = _hi("Shall I prepare it for your review?", m)
    body = _body(f"{s},", hook, detail, cta)
    return body, "open_ended", "Wedding follow-up with timeline specificity; uses urgency and effort externalization."


def _curious_ask(f, b, m, s):
    ask = _v(f, "trigger_ask_template")
    perf = _perf_line(f, m)
    if ask:
        clean_ask = ask.replace("_", " ").strip()
        if "service_in_demand" in ask or "service in demand" in clean_ask:
            clean_ask_hi = "is hafte sabse zyada kaun si service demand mein rahi?"
            clean_ask_en = "which service saw the highest demand this week?"
        else:
            clean_ask_hi = clean_ask + "?" if not clean_ask.endswith("?") else clean_ask
            clean_ask_en = clean_ask + "?" if not clean_ask.endswith("?") else clean_ask
        if m in ("hinglish", "hindi"):
            hook = f"ek quick question tha — {clean_ask_hi}"
        else:
            hook = f"a quick question for you — {clean_ask_en}"
    else:
        if m in ("hinglish", "hindi"):
            hook = "aapke business ke liye ek question tha — is hafte sabse zyada kaun si service demand mein rahi?"
        else:
            hook = "a quick question for you — which service saw the most demand this week?"
    body = _body(f"{s},", hook, perf)
    return body, "open_ended", "Curiosity-driven engagement; asks the merchant a question to learn and plan the next update."


def _winback(f, b, m, s):
    route = f.get("route")
    cname = f.get("customer_name")
    services = _first(f, "customer_services_received", "customer_services")
    days_since = _v(f, "trigger_days_since_expiry")
    if route == "customer" and cname:
        if m in ("hinglish", "hindi"):
            hook = f"kaafi time ho gaya aapki last visit se." if not days_since else f"aapki last visit se {days_since} din ho gaye."
            svc = f"Aapne pehle {services} liya tha." if services else ""
            hook2 = "Hum aapko wapas dekhna chahenge."
            cta = _hi("Reply YES if you'd like to rejoin.", m)
        else:
            hook = f"it has been a while since your last visit." if not days_since else f"it has been {days_since} days since your last visit."
            svc = f"You previously had {services}." if services else ""
            hook2 = "We would love to see you again."
            cta = _hi("Reply YES if you'd like to rejoin.", m)
        body = _body(f"{cname},", hook, svc, hook2, cta)
        return body, "binary_yes_no", "Win-back outreach with customer history; uses reciprocity and single binary CTA."
    else:
        perf_dip = _v(f, "trigger_perf_dip_pct")
        if m in ("hinglish", "hindi"):
            hook = "kuch past customers se reconnect karne ka mauka hai."
            detail = f"Performance {perf_dip} neeche aayi hai." if perf_dip else ""
        else:
            hook = "there may be an opportunity to reconnect with past customers."
            detail = f"Performance is down {perf_dip}." if perf_dip else ""
        cta = _hi("Shall I draft one for your review?", m)
        body = _body(f"{s},", hook, detail, cta)
        return body, "open_ended", "Win-back outreach with customer history; uses social proof (past relationship) and effort externalization."


def _ipl_match(f, b, m, s):
    match = _v(f, "trigger_match")
    venue = _v(f, "trigger_venue")
    offer = _offer(f) or _cat_offer(f)
    if m in ("hinglish", "hindi"):
        hook = f"aaj ka match: {match}." if match else "aaj IPL match hai."
        loc_tie = f"{venue} mein excitement hogi." if venue else ""
        tie = f"Aapke {offer} ke saath ek match-day post chal sakta hai." if offer else "Ek match-day post footfall badha sakta hai."
    else:
        hook = f"today's match: {match}." if match else "there is an IPL match today."
        loc_tie = f"Fans near {venue} will be looking for options." if venue else ""
        tie = f"A match-day post featuring {offer} could drive walk-ins." if offer else "A match-day post could drive walk-ins."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, loc_tie, tie, cta)
    return body, "open_ended", f"IPL match-day opportunity; uses urgency (today) and locality tie-in ({venue or 'local demand'})."


def _review_theme(f, b, m, s):
    theme = _v(f, "trigger_theme")
    quote = _v(f, "trigger_common_quote")
    count = _v(f, "trigger_occurrences_30d")
    if not theme:
        return None
    theme_clean = theme.replace("_", " ")
    if m in ("hinglish", "hindi"):
        hook = f"aapki recent reviews mein ek pattern dikh raha hai — \"{theme_clean}\"."
        detail = f"{count} mentions last 30 din mein." if count else ""
        if quote:
            detail += f" Ek customer ne likha: \"{quote}\"."
        reflection = "Ek thoughtful response se trust aur strong ho sakta hai."
    else:
        hook = f"a pattern in your recent reviews — \"{theme_clean}\"."
        detail = f"{count} mentions in the last 30 days." if count else ""
        if quote:
            detail += f" One customer wrote: \"{quote}\"."
        reflection = "A thoughtful response could turn this into a strength."
    cta = _hi("Shall I draft one for your review?", m)
    body = _body(f"{s},", hook, detail, reflection, cta)
    return body, "open_ended", f"Review theme alert with customer quote; uses reciprocity and social proof to encourage constructive response."


def _milestone(f, b, m, s):
    metric = _v(f, "trigger_metric")
    val_now = _v(f, "trigger_value_now")
    milestone_val = _v(f, "trigger_milestone_value")
    summary = _v(f, "trigger_summary")
    value = val_now or milestone_val

    is_review = metric and "review" in str(metric).lower()
    if is_review and val_now and milestone_val and val_now != milestone_val:
        if m in ("hinglish", "hindi"):
            hook = f"aapke {val_now} reviews ho gaye hain — bas {milestone_val} reviews milestone ke kareeb!"
        else:
            hook = f"you have reached {val_now} reviews — closing in on your {milestone_val} reviews milestone!"
    elif value:
        metric_label = "reviews" if is_review else (str(metric).replace("_", " ") if metric else "milestone")
        if m in ("hinglish", "hindi"):
            hook = f"ek milestone cross ho gaya — {value} {metric_label}!"
        else:
            hook = f"you have crossed a milestone — {value} {metric_label}!"
    else:
        if m in ("hinglish", "hindi"):
            hook = "ek business milestone reach ho gaya!"
        else:
            hook = "you have reached a business milestone!"

    detail = f"{summary}." if summary else ""
    tie = "Ek celebration post se aur customers attract ho sakte hain." if m in ("hinglish", "hindi") else "A celebration post could attract more customers."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, detail, tie, cta)
    return body, "open_ended", f"Milestone celebration ({value or 'reached'}); uses social proof and reciprocity (celebration post offer)."


def _active_planning(f, b, m, s):
    topic = _first(f, "trigger_intent_topic", "trigger_topic")
    if topic:
        topic_clean = topic.replace("_", " ")
    else:
        topic_clean = "planning"
    offer = _offer(f) or _cat_offer(f)
    if m in ("hinglish", "hindi"):
        hook = f"aapka {topic_clean} plan aage badhne ke liye ready hai."
        detail = f"Aapke {offer} ko bhi isme include kar sakte hain." if offer else ""
    else:
        hook = f"your {topic_clean} plan is ready for the next step."
        detail = f"Your {offer} could be part of this." if offer else ""
    cta = _hi("Shall I prepare it for your review?", m)
    body = _body(f"{s},", hook, detail, cta)
    return body, "open_ended", f"Planning intent follow-up ({topic_clean}); uses effort externalization (prepared draft) and momentum."


def _seasonal_perf_dip(f, b, m, s):
    offer = _offer(f) or _cat_offer(f)
    perf = _perf_line(f, m)
    if m in ("hinglish", "hindi"):
        hook = "seasonal pattern ki wajah se activity thodi slow hai."
        tie = f"Ek campaign jismein {offer} ho, demand capture kar sakta hai." if offer else "Ek targeted campaign demand capture kar sakta hai."
    else:
        hook = "seasonal patterns may be affecting activity."
        tie = f"A campaign featuring {offer} could capture demand." if offer else "A targeted campaign could capture demand."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, perf, tie, cta)
    return body, "open_ended", "Seasonal dip context with actionable campaign suggestion; uses effort externalization."


def _customer_lapsed(f, b, m, s, hard: bool = False):
    route = f.get("route")
    cname = f.get("customer_name")
    last_visit = _first(f, "customer_last_visit_date", "customer_last_visit")
    services = _first(f, "customer_services_received", "customer_services")
    days_since = _v(f, "trigger_days_since_last_visit")
    focus = _v(f, "trigger_previous_focus")
    if focus:
        focus = focus.replace("_", " ")

    if route == "customer" and cname:
        if m in ("hinglish", "hindi"):
            if days_since:
                hook = f"aapki last visit se {days_since} din ho gaye."
            elif last_visit:
                hook = f"aapki last visit {last_visit} ko thi — kaafi time ho gaya."
            else:
                hook = "kaafi time ho gaya aapki last visit se."
            focus_str = f"Aapka {focus} goal continue karne ke liye hum madad kar sakte hain." if focus else (f"Pehle aapne {services} liya tha." if services else "")
            tie = "Hum aapko wapas dekhna chahenge."
            cta = _hi("Reply YES to book a session.", m)
        else:
            if days_since:
                hook = f"it has been {days_since} days since your last visit."
            elif last_visit:
                hook = f"your last visit was on {last_visit} — it has been a while."
            else:
                hook = "it has been a while since your last visit."
            focus_str = f"We would love to help you continue your {focus} goal." if focus else (f"You previously had {services}." if services else "")
            tie = "We would love to see you again."
            cta = _hi("Reply YES to book a session.", m)
        body = _body(f"{cname},", hook, focus_str, tie, cta)
        label = "hard-lapsed" if hard else "soft-lapsed"
        return body, "binary_yes_no", f"Customer {label} outreach with visit history; uses reciprocity and single binary CTA."
    else:
        if m in ("hinglish", "hindi"):
            hook = f"{cname} ki last visit" if cname else "ek customer ki last visit"
            hook += f" {last_visit} thi." if last_visit else " kaafi pehle thi."
            svc = f"Services: {services}." if services else ""
            tie = "Ek gentle check-in message se wapas aa sakte hain."
        else:
            hook = f"{cname}'s last visit" if cname else "a customer's last visit"
            hook += f" was {last_visit}." if last_visit else " was some time ago."
            svc = f"Services: {services}." if services else ""
            tie = "A gentle check-in could bring them back."
        cta = _hi("Shall I draft one for your review?", m)
        body = _body(f"{s},", hook, svc, tie, cta)
        label = "hard-lapsed" if hard else "soft-lapsed"
        return body, "open_ended", f"Customer {label} outreach with visit history; uses reciprocity and effort externalization."


def _trial_followup(f, b, m, s):
    service = _first(f, "trigger_service_due", "trigger_service_name")
    if service:
        service = service.replace("_", " ")
    slots = _v(f, "available_slots")
    cname = f.get("customer_name")
    route = f.get("route")
    if route == "customer" and cname:
        if m in ("hinglish", "hindi"):
            hook = f"aapka {service} trial kaisa raha?" if service else "aapka trial kaisa raha?"
            slot_line = f"Next session ke liye slots available hain: {slots}." if slots else ""
        else:
            hook = f"how was your {service} trial?" if service else "how was your trial?"
            slot_line = f"Slots available for the next session: {slots}." if slots else ""
        if slots:
            cta = _hi("Which slot works best for you?", m)
            body = _body(f"{cname},", hook, slot_line, cta)
            return body, "multi_choice_slot", "Trial follow-up with slot options; uses momentum and multi-choice CTA."
        else:
            cta = _hi("Reply YES to confirm.", m)
            body = _body(f"{cname},", hook, cta)
            return body, "binary_yes_no", "Trial follow-up with service specificity; uses momentum and binary CTA."
    else:
        if m in ("hinglish", "hindi"):
            hook = f"ek trial follow-up due hai" + (f" ({service})" if service else "") + "."
        else:
            hook = f"a trial follow-up is due" + (f" for {service}" if service else "") + "."
        cta = _hi("Shall I prepare it for your review?", m)
        body = _body(f"{s},", hook, cta)
        return body, "open_ended", f"Trial follow-up with service specificity; uses momentum (post-trial engagement)."


def _supply_alert(f, b, m, s):
    product = _first(f, "trigger_product", "trigger_medicine")
    title = _v(f, "digest_title")
    actionable = _v(f, "digest_actionable")
    if m in ("hinglish", "hindi"):
        hook = f"ek supply update: {product}" if product else "ek supply alert"
        hook += f" — {title}." if title else "."
        detail = actionable + "." if actionable else ""
    else:
        hook = f"a supply update: {product}" if product else "a supply alert"
        hook += f" — {title}." if title else "."
        detail = actionable + "." if actionable else ""
    cta = _hi("Shall I send the details?", m)
    body = _body(f"{s},", hook, detail, cta)
    return body, "open_ended", f"Supply alert with product specificity; uses loss aversion (stock/compliance risk) and actionable advice."


def _chronic_refill(f, b, m, s):
    route = f.get("route")
    cname = f.get("customer_name")
    medicine = _first(f, "trigger_medicine", "trigger_product", "trigger_molecule_list")
    last_visit = _first(f, "customer_last_visit_date", "customer_last_visit", "trigger_last_refill")
    runs_out = _v(f, "trigger_stock_runs_out_iso")
    runs_out_date = _clean_date_str(runs_out)

    if route == "customer" and cname:
        if m in ("hinglish", "hindi"):
            hook = f"aapki regular medicines ({medicine}) refill due hai." if medicine else "aapki refill due hai."
            detail = f"Estimated refill date: {runs_out_date}." if runs_out_date else (f"Last visit: {last_visit}." if last_visit else "")
            cta = _hi("Reply YES to confirm your refill.", m)
        else:
            hook = f"your regular prescription ({medicine}) is due for refill." if medicine else "your refill is due."
            detail = f"Estimated refill date: {runs_out_date}." if runs_out_date else (f"Last visit: {last_visit}." if last_visit else "")
            cta = _hi("Reply YES to confirm your refill.", m)
        body = _body(f"{cname},", hook, detail, cta)
        return body, "binary_yes_no", "Chronic refill reminder with medication specificity; uses reciprocity (proactive flag) and single binary CTA."
    else:
        if m in ("hinglish", "hindi"):
            hook = f"{cname} ki" if cname else "ek patient ki"
            hook += f" {medicine} refill due hai." if medicine else " refill due hai."
            detail = f"Last visit: {last_visit}." if last_visit else ""
        else:
            hook = f"{cname}'s" if cname else "a patient's"
            hook += f" {medicine} refill is due." if medicine else " refill is due."
            detail = f"Last visit: {last_visit}." if last_visit else ""
        cta = _hi("Shall I prepare it for your review?", m)
        body = _body(f"{s},", hook, detail, cta)
        return body, "open_ended", f"Chronic refill reminder with medication specificity; uses reciprocity (proactive flag) and patient care context."


def _category_seasonal(f, b, m, s):
    offer = _offer(f) or _cat_offer(f)
    trends = _v(f, "trigger_trends")
    season = _v(f, "trigger_season")
    season_label = season.replace("_", " ") if season else "seasonal"

    if m in ("hinglish", "hindi"):
        hook = f"{season_label} demand shift ho raha hai" + (f" — {trends}." if trends else " — is samay customers zyada search kar rahe hain.")
        tie = f"Aapke {offer} ke saath ek seasonal campaign chal sakta hai." if offer else "Ek timely campaign visibility badha sakta hai."
    else:
        hook = f"{season_label} demand is shifting" + (f" — {trends}." if trends else " — customers are searching more right now.")
        tie = f"A seasonal campaign featuring {offer} could capture demand." if offer else "A timely campaign could boost visibility."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, tie, cta)
    return body, "open_ended", "Seasonal opportunity with specific category demand trends and offer tie-in; uses urgency and effort externalization."


def _gbp_unverified(f, b, m, s):
    loc = _loc(f)
    uplift = _v(f, "trigger_estimated_uplift_pct")
    uplift_str_hi = f" (~{uplift} search uplift)" if uplift else ""
    uplift_str_en = f" (~{uplift} search uplift)" if uplift else ""

    if m in ("hinglish", "hindi"):
        hook = "aapka Google Business Profile abhi unverified hai."
        tie = f"{loc} mein customers aapko search kar rahe hain, par unverified profile se trust kam hota hai." if loc else "Verified profile se customer trust badhta hai."
        fix = f"Verification 5-min ka process hai{uplift_str_hi}."
    else:
        hook = "your Google Business Profile is currently unverified."
        tie = f"Customers in {loc} are searching for you, but an unverified profile affects trust." if loc else "A verified profile improves customer trust."
        fix = f"Verification takes about 5 minutes{uplift_str_en}."
    cta = _hi("Want me to set it up?", m)
    body = _body(f"{s},", hook, tie, fix, cta)
    return body, "open_ended", "GBP verification nudge with locality context; uses loss aversion (trust gap) and effort externalization (5-min process)."


def _cde_opportunity(f, b, m, s):
    title = _v(f, "digest_title")
    date = _first(f, "digest_date", "trigger_date")
    credits = _first(f, "digest_credits", "trigger_credits")
    fee = _v(f, "trigger_fee")
    if not title:
        return None
    clean_date = _clean_date_str(date)
    detail_parts = []
    if clean_date:
        detail_parts.append(f"Date: {clean_date}")
    if credits:
        detail_parts.append(f"{credits} credits")
    if fee:
        detail_parts.append(f"({fee})")
    detail = " ".join(detail_parts) + "." if detail_parts else ""
    if m in ("hinglish", "hindi"):
        hook = f"ek learning opportunity — {title}."
    else:
        hook = f"a learning opportunity — {title}."
    cta = _hi("Shall I send the details?", m)
    body = _body(f"{s},", hook, detail, cta)
    return body, "open_ended", f"CDE/learning opportunity with specific program details; uses curiosity and professional development appeal."


def _competitor_opened(f, b, m, s):
    competitor = _first(f, "trigger_competitor", "trigger_competitor_name")
    loc = _first(f, "trigger_locality") or _loc(f)
    dist = _v(f, "trigger_distance_km")
    their_offer = _v(f, "trigger_their_offer")
    offer = _offer(f) or _cat_offer(f)
    dist_str = f", {dist} km door" if dist else ""
    dist_str_en = f", {dist} km away" if dist else ""

    if m in ("hinglish", "hindi"):
        comp_part = f"({competitor}{dist_str})" if competitor else ""
        hook = f"ek naya competitor {comp_part} {loc} mein khula hai." if loc else f"ek naya competitor {comp_part} nearby khula hai."
        their_part = f" Unka offer: {their_offer}." if their_offer else ""
        tie = f"Aapke {offer} ko highlight karte hue ek fresh post draft kar doon?" if offer else "Ek fresh profile post draft kar doon?"
        body = _body(f"{s},", hook, their_part, tie)
    else:
        comp_part = f"({competitor}{dist_str_en})" if competitor else ""
        hook = f"a new competitor {comp_part} has opened in {loc}." if loc else f"a new competitor {comp_part} has opened nearby."
        their_part = f" Their offer: {their_offer}." if their_offer else ""
        tie = f"Highlighting your {offer} could help you stand out." if offer else "A refreshed profile post could help you stand out."
        cta = _hi("Want me to draft one?", m)
        body = _body(f"{s},", hook, their_part, tie, cta)
    return body, "open_ended", f"Competitor alert with locality context; uses loss aversion (competitive threat) and effort externalization."


def _dormant(f, b, m, s):
    perf = _perf_line(f, m)
    if m in ("hinglish", "hindi"):
        hook = "kaafi din ho gaye humne saath mein profile par kaam kiya."
        tie = "Ek chhota sa update se hum wapas shuru kar sakte hain."
    else:
        hook = "it has been a while since we worked on your profile together."
        tie = "One small update could get things moving again."
    cta = _hi("Reply YES to get started.", m)
    body = _body(f"{s},", hook, perf, tie, cta)
    return body, "binary_yes_no", "Dormancy re-engagement with performance context; uses effort externalization (one small update) and reciprocity."


def _appointment_tomorrow(f, b, m, s):
    route = f.get("route")
    cname = f.get("customer_name")
    service = _first(f, "trigger_service_due", "customer_services_received", "customer_services")
    if service:
        service = service.replace("_", " ")
    date = _first(f, "trigger_date", "trigger_appointment_date")
    slots = _v(f, "available_slots")
    if route == "customer" and cname:
        if m in ("hinglish", "hindi"):
            hook = "aapka kal ka appointment confirm hai."
            svc = f"Service: {service}." if service else ""
            time_line = f"Time: {slots}." if slots else (f"Date: {date}." if date else "")
        else:
            hook = "your appointment tomorrow is confirmed."
            svc = f"Service: {service}." if service else ""
            time_line = f"Time: {slots}." if slots else (f"Date: {date}." if date else "")
        cta = _hi("Reply YES to confirm.", m)
        body = _body(f"{cname},", hook, svc, time_line, cta)
        return body, "binary_yes_no", "Appointment reminder with service and time specifics; uses specificity and binary confirmation."
    else:
        if m in ("hinglish", "hindi"):
            hook = f"kal ek appointment hai" + (f" — {cname}" if cname else "") + "."
            svc = f"Service: {service}." if service else ""
        else:
            hook = f"there is an appointment tomorrow" + (f" for {cname}" if cname else "") + "."
            svc = f"Service: {service}." if service else ""
        cta = _hi("Shall I send the details?", m)
        body = _body(f"{s},", hook, svc, cta)
        return body, "open_ended", "Appointment reminder with service and time specifics; uses specificity and loss aversion (missed appointment)."


def _weather_heatwave(f, b, m, s):
    offer = _offer(f) or _cat_offer(f)
    loc = _loc(f)
    if m in ("hinglish", "hindi"):
        hook = f"{loc} mein aaj bahut garmi hai." if loc else "Aaj bahut garmi hai."
        tie = "Is mausam mein customers kuch alag dhundhte hain."
        fix = f"Aapke {offer} ke saath ek weather-themed post chal sakta hai." if offer else "Ek weather-themed post se engagement mil sakta hai."
    else:
        hook = f"temperatures are high in {loc} today." if loc else "Temperatures are high today."
        tie = "Customers may be looking for weather-appropriate options."
        fix = f"A weather-themed post featuring {offer} could drive interest." if offer else "A weather-themed post could drive interest."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, tie, fix, cta)
    return body, "open_ended", "Weather opportunity with locality tie-in; uses urgency (today) and effort externalization."


def _local_news(f, b, m, s):
    summary = _v(f, "trigger_summary")
    if m in ("hinglish", "hindi"):
        hook = f"ek local event se nearby demand badh sakti hai" + (f" — {summary}" if summary else "") + "."
    else:
        hook = f"a local event may change nearby demand" + (f" — {summary}" if summary else "") + "."
    cta = _hi("Want me to draft one?", m)
    body = _body(f"{s},", hook, cta)
    return body, "open_ended", "Local news opportunity; uses urgency and locality awareness."


def _category_trend(f, b, m, s):
    title = _v(f, "digest_title")
    source = _v(f, "digest_source")
    if not title:
        return None
    if m in ("hinglish", "hindi"):
        hook = f"aapke category mein ek trend dikh raha hai — {title}."
        detail = f"Source: {source}." if source else ""
    else:
        hook = f"a category trend worth noting — {title}."
        detail = f"Source: {source}." if source else ""
    cta = _hi("Want a quick summary?", m)
    body = _body(f"{s},", hook, detail, cta)
    return body, "open_ended", "Category trend with source citation; uses curiosity and industry awareness."


def _scheduled_recurring(f, b, m, s):
    perf = _perf_line(f, m)
    offer = _offer(f)
    if m in ("hinglish", "hindi"):
        hook = "aapka regular profile check-in ka time hai."
        tie = f"Aapke {offer} ka status bhi dekh lete hain." if offer else "Ek quick review se kya improve ho sakta hai, woh samajh aayega."
    else:
        hook = "time for your regular profile check-in."
        tie = f"Let us also review how {offer} is performing." if offer else "A quick review can identify what to improve next."
    cta = _hi("Reply YES to get started.", m)
    body = _body(f"{s},", hook, perf, tie, cta)
    return body, "binary_yes_no", "Recurring check-in with performance context; uses routine/cadence and effort externalization."


# ── builder registry ─────────────────────────────────────────────────────────

_BUILDERS: dict[str, object] = {
    "research_digest": _research_digest,
    "regulation_change": _regulation_change,
    "perf_dip": _perf_dip,
    "perf_spike": _perf_spike,
    "recall_due": _recall_due,
    "renewal_due": _renewal_due,
    "festival_upcoming": _festival_upcoming,
    "wedding_package_followup": _wedding_package,
    "curious_ask_due": _curious_ask,
    "winback_eligible": _winback,
    "ipl_match_today": _ipl_match,
    "review_theme_emerged": _review_theme,
    "milestone_reached": _milestone,
    "active_planning_intent": _active_planning,
    "seasonal_perf_dip": _seasonal_perf_dip,
    "customer_lapsed_soft": lambda f, b, m, s: _customer_lapsed(f, b, m, s, hard=False),
    "customer_lapsed_hard": lambda f, b, m, s: _customer_lapsed(f, b, m, s, hard=True),
    "trial_followup": _trial_followup,
    "supply_alert": _supply_alert,
    "chronic_refill_due": _chronic_refill,
    "category_seasonal": _category_seasonal,
    "gbp_unverified": _gbp_unverified,
    "cde_opportunity": _cde_opportunity,
    "competitor_opened": _competitor_opened,
    "dormant_with_vera": _dormant,
    "appointment_tomorrow": _appointment_tomorrow,
    "weather_heatwave": _weather_heatwave,
    "local_news_event": _local_news,
    "category_trend_movement": _category_trend,
    "scheduled_recurring": _scheduled_recurring,
}


# ── main entry point ─────────────────────────────────────────────────────────

def compose_fallback(bundle: dict, facts: dict) -> dict:
    kind = facts.get("kind", "unknown")
    route = facts.get("route")
    m = _mode(facts)
    s = _sal(facts, route)

    # Merchant-approval route: message goes to the merchant, not customer
    if route == "merchant_approval":
        cname = facts.get("customer_name")
        if m in ("hinglish", "hindi"):
            hook = f"ek customer follow-up ready hai" + (f" ({cname} ke liye)" if cname else "") + ", par pehle aapki approval chahiye."
        else:
            hook = f"a customer follow-up is ready" + (f" for {cname}" if cname else "") + ", but I need your approval first."
        cta = _hi("Shall I prepare it for your review?", m)
        body = _body(f"{s},", hook, cta)
        return _result(body, "open_ended",
            "Merchant approval gate for customer outreach; respects consent by asking merchant before contacting customer.",
            facts, route)

    builder = _BUILDERS.get(kind)
    if builder:
        result = builder(facts, bundle, m, s)
        if result:
            body, cta, rationale = result
            return _result(body, cta, rationale, facts, route)

    # Generic fallback for unknown or thin-data kinds
    offer = _offer(facts)
    perf = _perf_line(facts, m)
    retrieved = facts.get("retrieved") or []
    best = next((r["text"][:120] for r in retrieved if r.get("score", 0) > 1), None)
    if m in ("hinglish", "hindi"):
        hook = "aapke business ke liye ek update hai."
        detail = best + "." if best else (f"Aapka current offer {offer} relevant ho sakta hai." if offer else "")
    else:
        hook = "there is an update relevant to your business."
        detail = best + "." if best else (f"Your current offer {offer} may be relevant." if offer else "")
    cta = _hi("Reply YES if this is useful.", m)
    body = _body(f"{s},", hook, detail, perf, cta)
    return _result(body, "binary_yes_no",
        "Generic engagement with best available context; uses verified facts and a single low-pressure CTA.",
        facts, route)


def _result(body: str, cta: str, rationale: str, facts: dict, route: str | None) -> dict:
    kind = facts.get("kind", "unknown")
    return {
        "body": body,
        "cta": cta,
        "send_as": facts.get("send_as", "vera"),
        "suppression_key": facts.get("suppression_key", ""),
        "rationale": rationale,
        "template_name": facts.get("template_name", f"vera_{kind}_v1"),
        "template_params": [_sal(facts, route), kind],
        "_meta": {"composer": "fallback", "route": route, "issues": []},
    }
