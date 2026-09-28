"""intents.py -- recognise image / video / edit / email / agent / carousel / vault / skill requests inside plain chat."""
import re

EMAIL_RE = r"[\w.+-]+@[\w-]+\.[\w.-]+"
IMG_NOUNS = r"(?:image|picture|photo|photograph|illustration|logo|artwork|art piece|art|poster|wallpaper|icon|drawing|sketch|painting|render|thumbnail|banner|portrait)"
VID_NOUNS = r"(?:video|clip|animation|movie|film|reel)"
MAKE_VERBS = r"(?:generate|create|make|draw|render|paint|design|produce|show me|give me|build|imagine|visualize|visualise)"
EDIT_WORDS = r"(?:trim|cut|crop|speed up|slow down|slow-mo|slowmo|mute|reverse|caption|subtitle|black and white|grayscale|greyscale|resize|rotate|flip|fade|brighter|darker|louder|quieter|gif|extract the audio|add text|overlay|watermark|stabili[sz]e|vertical|9:16|square|zoom|sepia|blur|sharpen|volume|loop)"
BUILD_NOUNS = r"(?:script|app|application|project|website|landing page|cli|tool|program|dashboard|api|bot|scraper|automation|spreadsheet|report)"
SLASH = r"^/(image|img|video|vid|edit|email|mail|agent|run|carousel|vault|kb|skill|use|lead|book|research|google|web|search|factcheck|fact-check|xref|pathway|cert)\s*(.*)$"
ALIAS = {"img": "image", "vid": "video", "mail": "email", "run": "agent", "kb": "vault", "use": "skill",
         "google": "research", "web": "research", "search": "research", "factcheck": "research", "fact-check": "research", "xref": "research",
         "cert": "pathway"}

def detect(text, has_video=False):
    t = (text or "").strip()
    low = t.lower()
    if not t:
        return None
    # Slash commands are explicit
    m = re.match(SLASH, t, flags=re.S | re.I)
    if m:
        cmd, rest = m.group(1).lower(), m.group(2).strip()
        kind = ALIAS.get(cmd, cmd)
        if kind == "email":
            return {"kind": "email", **_email_args(rest)}
        if kind == "edit":
            return {"kind": "edit", "instruction": rest}
        if kind == "agent":
            return {"kind": "agent", "goal": rest}
        if kind in ("carousel", "vault", "skill", "lead", "book", "research", "pathway"):
            return {"kind": kind, "arg": rest}
        return {"kind": kind, "prompt": rest}
    if re.match(r"^agent\s*[:,-]\s*\S", low):
        return {"kind": "agent", "goal": re.sub(r"^agent\s*[:,-]\s*", "", t, flags=re.I).strip()}
    # Web research / fact-check phrasing
    m = re.match(r"^(?:please\s+|can you\s+|could you\s+)?(?:google|research|look up|lookup|search (?:the web|online|google) for|search for|fact[- ]?check|cross[- ]?reference|verify online|find out online)\s*[:,]?\s*(.+)$", t, flags=re.I | re.S)
    if m and len(m.group(1).strip()) > 3:
        return {"kind": "research", "arg": m.group(1).strip().rstrip("?.") + ("?" if t.strip().endswith("?") else "")}
    if re.search(r"\b(on google|online|on the web|latest|current|as of (20\d\d|today|now)|recent|this (week|month|year)|news about|what does the internet say)\b", low) \
       and re.search(r"\b(what|how|who|when|where|which|why|is|are|does|do|should|compare|vs|versus)\b", low):
        return {"kind": "research", "arg": t.strip()}
    # Carousel before generic build phrasing
    if re.search(r"\b(make|create|write|build|generate)\s+(me\s+)?(a\s+|an\s+)?(instagram\s+|ig\s+)?carousel\b", low):
        return {"kind": "carousel", "arg": re.sub(r"^.*?carousel\s*(about|on|for)?\s*", "", t, flags=re.I).strip() or t}
    # Strong "build something" phrasing goes to the super agent
    if re.search(r"\b(build|code|scaffold|write|create|make)\s+(me\s+)?(a\s+|an\s+)?(python\s+|node\s+|web\s+|html\s+|small\s+|simple\s+)?" + BUILD_NOUNS + r"\b", low) \
       and not re.search(r"\b" + IMG_NOUNS + r"\b|\b" + VID_NOUNS + r"\b|\bemail\b", low):
        return {"kind": "agent", "goal": t}
    # Email
    if re.search(r"\b(write|draft|compose|send|shoot|fire off)\b.{0,40}\b(an?\s+)?(email|e-mail|mail)\b", low) or \
       re.search(r"\bemail\b.{0,30}\bto\b", low):
        return {"kind": "email", **_email_args(t)}
    # Video editing (only when a video is loaded, or the message clearly refers to a video)
    if re.search(r"\b" + EDIT_WORDS + r"\b", low) and (has_video or re.search(r"\b(this|the|my)\s+(video|clip)\b", low)):
        if not re.search(r"\b" + MAKE_VERBS + r"\b.{0,30}\b(new|a)\s+" + VID_NOUNS, low):
            return {"kind": "edit", "instruction": t}
    # Video generation
    if re.search(r"\b" + MAKE_VERBS + r"\b.{0,60}\b" + VID_NOUNS + r"\b", low) or re.search(r"\banimate\b", low):
        return {"kind": "video", "prompt": _strip_lead(t, VID_NOUNS)}
    # Image generation
    if re.search(r"\b" + MAKE_VERBS + r"\b.{0,60}\b" + IMG_NOUNS + r"\b", low) or re.match(r"^(imagine|visuali[sz]e)\b", low):
        return {"kind": "image", "prompt": _strip_lead(t, IMG_NOUNS)}
    return None

def _strip_lead(t, nouns):
    """'generate an image of a red fox' -> 'a red fox' (keeps full text if nothing matches)."""
    m = re.match(r"^(?:please\s+|can you\s+|could you\s+)?(?:" + MAKE_VERBS + r")\s+(?:me\s+)?(?:an?\s+|the\s+|some\s+)?(?:[\w-]+\s+){0,3}?" + nouns + r"\s*(?:of|showing|with|about|that shows|depicting|:)?\s*(.+)$", t, flags=re.I | re.S)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return t

def _email_args(t):
    to = re.findall(EMAIL_RE, t)
    subj = None
    m = re.search(r"\b(?:subject|titled)\s*[:\"]?\s*([^\n\"]{3,80})", t, flags=re.I)
    if m:
        subj = m.group(1).strip().rstrip(".")
    return {"to": to, "subject": subj, "intent": t}
