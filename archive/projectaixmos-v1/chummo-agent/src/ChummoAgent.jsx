import { useState } from "react";

// ═══════════════════════════════════════════════════════
// AIXMOS — CHUMMO MESSAGING AGENT
// Powered by Claude (Anthropic API)
// Built for: Muhammad Taha / AIXMOS
//
// HOW TO USE:
// This is a React component. Drop it into:
// - Claude.ai as an artifact (paste into a new chat)
// - Cursor / VS Code with a React project
// - Any React + Vite setup
//
// The Anthropic API key is handled automatically
// when running inside Claude.ai artifacts.
// For external use, add your key to the fetch headers.
// ═══════════════════════════════════════════════════════

const AIXMOS_SYSTEM_PROMPT = `You are CHUMMO — the AIXMOS messaging agent. You write outreach messages, emails, and follow-ups on behalf of AIXMOS operators and Muhammad Taha, the founder.

ABOUT AIXMOS:
- Workforce infrastructure company disguised as a service business
- Mission: Help everyday people access the American Dream through systems, automation, and operational infrastructure
- Founder: Muhammad Taha — immigrant, came to America at 6, built a car rental operation to $90-100K/month, was betrayed, rebuilt, touched $1M+ in operations
- Tagline: "For the people. By the people."
- Target: $10,000/month for every client
- Standard: 5-star restaurant — every interaction is premium

THE SERVICES:
- $97/month Membership: Ecosystem access, credit guidance, vendor network, operator support
- $397 LLC Formation
- $500-$1,000 Credit Guidance (guided process + vetted vendor delegation)
- $3,750 Base Infrastructure: GHL, website, automations, funding pathway
- $7,500 Enterprise Systems
- $15,000 Car Rental in a Box
- $25,000 E-Commerce Ecosystem
- $50,000 Full Ecosystem

THE CHUMMO VOICE — NON-NEGOTIABLE:
- Friend first. Always. Before any pitch.
- Warm, direct, human — never corporate or scripted-sounding
- Short sentences. White space. Easy to read on a phone.
- Never say: "I'm following up on your inquiry" / "As per my last message" / "I wanted to circle back"
- Never open with the company name or a pitch
- Always open with the person's name and something human
- Lead with empathy, not features
- One clear call to action per message — never two
- SMS messages: under 160 characters when possible, always conversational
- Emails: short paragraphs, no corporate jargon, feels like it came from a real person who cares

OPERATOR RULES:
- Never make income guarantees
- Never pressure — guide
- Always leave the door open if they're not ready
- Match urgency level to their situation

OUTPUT FORMAT:
- Write ONLY the message content — no preamble, no explanation, no "here's a draft"
- For SMS: just the text
- For email: Subject line on first line, then blank line, then body
- For voice note scripts: write it like someone would actually say it out loud, with natural pauses marked as [pause]
- Always personalize using the lead info provided`;

const MESSAGE_TYPES = [
  { id: "first_sms", label: "First Outreach — SMS", icon: "💬" },
  { id: "first_email", label: "First Outreach — Email", icon: "📧" },
  { id: "followup_sms", label: "Follow-Up — SMS", icon: "🔄" },
  { id: "postcall_email", label: "Post-Call Recap — Email", icon: "📋" },
  { id: "payment_reminder", label: "Payment Reminder — SMS", icon: "💳" },
  { id: "upgrade_convo", label: "Upgrade Conversation — Email", icon: "⬆️" },
  { id: "reengagement", label: "Re-Engagement — SMS", icon: "🔥" },
  { id: "referral_ask", label: "Referral Ask — SMS", icon: "🤝" },
  { id: "operator_invite", label: "Operator Invite — Email", icon: "🏢" },
  { id: "welcome_message", label: "Welcome — After Payment", icon: "🎉" },
];

const URGENCY_LEVELS = ["Critical — needs to move now", "Warm — within 30 days", "Cold — just researching"];
const TIER_OPTIONS = [
  "Not sure yet",
  "Membership $97/mo",
  "Credit Guidance $500-$1K",
  "LLC Formation $397",
  "Base Infrastructure $3,750",
  "Enterprise Systems $7,500",
  "Car Rental in a Box $15K",
  "E-Commerce Ecosystem $25K",
  "Full Ecosystem $50K",
];

const PIPELINE_STAGES = [
  "New lead — no contact yet",
  "Contacted — no response",
  "Had a conversation — thinking",
  "Call completed — proposal sent",
  "Already paid — needs activation",
  "Active client — check-in needed",
  "Upgrade ready",
  "Gone quiet — re-engagement",
];

export default function ChummoAgent() {
  const [lead, setLead] = useState({
    name: "",
    situation: "",
    urgency: "",
    tier: "",
    stage: "",
    extraContext: "",
  });
  const [messageType, setMessageType] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState([]);

  const buildUserPrompt = () => {
    const type = MESSAGE_TYPES.find((m) => m.id === messageType);
    return `Write a ${type?.label} message for this lead:

NAME: ${lead.name || "Not provided"}
SITUATION: ${lead.situation || "Not provided"}
URGENCY: ${lead.urgency || "Not provided"}
SERVICE INTEREST: ${lead.tier || "Not sure yet"}
PIPELINE STAGE: ${lead.stage || "Not provided"}
ADDITIONAL CONTEXT: ${lead.extraContext || "None"}

Write the message now. Follow the CHUMMO voice rules exactly.`;
  };

  const generate = async () => {
    if (!messageType) return;
    setLoading(true);
    setOutput("");
    setCopied(false);

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: AIXMOS_SYSTEM_PROMPT,
          messages: [{ role: "user", content: buildUserPrompt() }],
        }),
      });

      const data = await response.json();
      const text = data.content?.[0]?.text || "Something went wrong. Try again.";
      setOutput(text);
      setHistory((prev) => [
        { type: MESSAGE_TYPES.find((m) => m.id === messageType)?.label, name: lead.name, output: text, id: Date.now() },
        ...prev.slice(0, 9),
      ]);
    } catch {
      setOutput("Connection error. Check your API access and try again.");
    } finally {
      setLoading(false);
    }
  };

  const copy = () => {
    navigator.clipboard.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const clear = () => {
    setLead({ name: "", situation: "", urgency: "", tier: "", stage: "", extraContext: "" });
    setMessageType("");
    setOutput("");
    setCopied(false);
  };

  const inputStyle = {
    width: "100%",
    padding: "9px 12px",
    border: "1px solid #E2E8F0",
    borderRadius: "8px",
    fontSize: "13px",
    fontFamily: "DM Sans, sans-serif",
    color: "#0A1628",
    background: "#FFFFFF",
    outline: "none",
    transition: "border-color 0.15s",
  };

  const labelStyle = {
    display: "block",
    fontSize: "11px",
    fontWeight: "500",
    color: "#64748B",
    marginBottom: "5px",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  };

  return (
    <div style={{ fontFamily: "DM Sans, system-ui, sans-serif", background: "#F4F7FF", minHeight: "100vh", padding: "0" }}>

      {/* HEADER */}
      <div style={{ background: "#1440C4", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: "22px", fontWeight: "bold", color: "#FFFFFF", letterSpacing: "0.06em" }}>
            AIX<span style={{ color: "#93C5FD" }}>MOS</span>
          </div>
          <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.6)", letterSpacing: "0.12em", textTransform: "uppercase", marginTop: "2px" }}>
            CHUMMO · Messaging Agent
          </div>
        </div>
        <div style={{ background: "rgba(255,255,255,0.15)", borderRadius: "20px", padding: "4px 12px", fontSize: "11px", color: "#FFFFFF", fontWeight: "500" }}>
          Friend First · Always
        </div>
      </div>

      <div style={{ maxWidth: "900px", margin: "0 auto", padding: "20px 16px", display: "grid", gridTemplateColumns: "340px 1fr", gap: "16px" }}>

        {/* LEFT — INPUTS */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

          {/* LEAD INFO */}
          <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "12px", padding: "16px" }}>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#0A1628", marginBottom: "12px", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Lead Info
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={labelStyle}>First name *</label>
              <input
                style={inputStyle}
                placeholder="Their first name"
                value={lead.name}
                onChange={(e) => setLead({ ...lead, name: e.target.value })}
              />
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={labelStyle}>Their situation</label>
              <textarea
                style={{ ...inputStyle, minHeight: "72px", resize: "vertical" }}
                placeholder="What's going on with them? What are they trying to solve?"
                value={lead.situation}
                onChange={(e) => setLead({ ...lead, situation: e.target.value })}
              />
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={labelStyle}>Urgency</label>
              <select style={inputStyle} value={lead.urgency} onChange={(e) => setLead({ ...lead, urgency: e.target.value })}>
                <option value="">Select urgency</option>
                {URGENCY_LEVELS.map((u) => <option key={u}>{u}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={labelStyle}>Service interest</label>
              <select style={inputStyle} value={lead.tier} onChange={(e) => setLead({ ...lead, tier: e.target.value })}>
                <option value="">Select tier</option>
                {TIER_OPTIONS.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={labelStyle}>Pipeline stage</label>
              <select style={inputStyle} value={lead.stage} onChange={(e) => setLead({ ...lead, stage: e.target.value })}>
                <option value="">Select stage</option>
                {PIPELINE_STAGES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>

            <div>
              <label style={labelStyle}>Extra context</label>
              <textarea
                style={{ ...inputStyle, minHeight: "56px", resize: "vertical" }}
                placeholder="Anything else CHUMMO should know..."
                value={lead.extraContext}
                onChange={(e) => setLead({ ...lead, extraContext: e.target.value })}
              />
            </div>
          </div>

          {/* MESSAGE TYPE */}
          <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "12px", padding: "16px" }}>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#0A1628", marginBottom: "12px", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Message Type
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {MESSAGE_TYPES.map((m) => (
                <div
                  key={m.id}
                  onClick={() => setMessageType(m.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "8px 10px",
                    borderRadius: "8px",
                    border: `1px solid ${messageType === m.id ? "#1440C4" : "#E2E8F0"}`,
                    background: messageType === m.id ? "#EFF3FF" : "#FAFAFA",
                    cursor: "pointer",
                    fontSize: "12px",
                    color: messageType === m.id ? "#1440C4" : "#0A1628",
                    fontWeight: messageType === m.id ? "500" : "400",
                    transition: "all 0.15s",
                  }}
                >
                  <span>{m.icon}</span>
                  <span>{m.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* BUTTONS */}
          <button
            onClick={generate}
            disabled={loading || !messageType || !lead.name}
            style={{
              width: "100%",
              padding: "12px",
              background: loading || !messageType || !lead.name ? "#94A3B8" : "#1440C4",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "10px",
              fontSize: "14px",
              fontWeight: "500",
              cursor: loading || !messageType || !lead.name ? "not-allowed" : "pointer",
              fontFamily: "inherit",
              transition: "background 0.15s",
            }}
          >
            {loading ? "CHUMMO is writing..." : "Generate Message ↗"}
          </button>

          <button
            onClick={clear}
            style={{ width: "100%", padding: "10px", background: "transparent", color: "#64748B", border: "1px solid #E2E8F0", borderRadius: "10px", fontSize: "13px", cursor: "pointer", fontFamily: "inherit" }}
          >
            Clear
          </button>
        </div>

        {/* RIGHT — OUTPUT */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

          {/* OUTPUT BOX */}
          <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "12px", padding: "20px", minHeight: "320px", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div style={{ fontSize: "12px", fontWeight: "600", color: "#0A1628", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                {messageType ? MESSAGE_TYPES.find((m) => m.id === messageType)?.label : "Output"}
              </div>
              {output && (
                <button
                  onClick={copy}
                  style={{
                    padding: "5px 14px",
                    background: copied ? "#1D9E75" : "#1440C4",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: "500",
                    cursor: "pointer",
                    fontFamily: "inherit",
                    transition: "background 0.15s",
                  }}
                >
                  {copied ? "Copied ✓" : "Copy"}
                </button>
              )}
            </div>

            {loading ? (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px" }}>
                <div style={{ width: "32px", height: "32px", border: "2px solid #E2E8F0", borderTop: "2px solid #1440C4", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                <div style={{ fontSize: "13px", color: "#64748B" }}>CHUMMO is writing your message...</div>
              </div>
            ) : output ? (
              <div style={{ flex: 1, background: "#F8FAFF", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "16px", fontSize: "14px", lineHeight: "1.75", color: "#0A1628", whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
                {output}
              </div>
            ) : (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "8px", color: "#94A3B8" }}>
                <div style={{ fontSize: "32px" }}>💬</div>
                <div style={{ fontSize: "13px", textAlign: "center", lineHeight: "1.5" }}>
                  Fill in the lead info,<br />pick a message type,<br />and hit Generate.
                </div>
              </div>
            )}

            {output && (
              <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
                <button
                  onClick={generate}
                  style={{ flex: 1, padding: "9px", background: "#F4F7FF", color: "#1440C4", border: "1px solid #DBEAFE", borderRadius: "8px", fontSize: "12px", fontWeight: "500", cursor: "pointer", fontFamily: "inherit" }}
                >
                  Regenerate ↻
                </button>
              </div>
            )}
          </div>

          {/* HISTORY */}
          {history.length > 0 && (
            <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "12px", padding: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: "600", color: "#0A1628", marginBottom: "12px", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                Recent Messages
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {history.map((h) => (
                  <div
                    key={h.id}
                    onClick={() => setOutput(h.output)}
                    style={{ border: "1px solid #E2E8F0", borderRadius: "8px", padding: "10px 12px", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}
                  >
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: "500", color: "#0A1628", marginBottom: "2px" }}>{h.name}</div>
                      <div style={{ fontSize: "11px", color: "#64748B" }}>{h.type}</div>
                    </div>
                    <div style={{ fontSize: "11px", color: "#1440C4", fontWeight: "500", flexShrink: 0 }}>View →</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* QUICK TIPS */}
          <div style={{ background: "#EFF3FF", border: "1px solid #DBEAFE", borderRadius: "12px", padding: "14px 16px" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#1440C4", marginBottom: "8px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              CHUMMO Reminders
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              {[
                "Always use their first name — never 'Hi there'",
                "SMS under 160 chars — read it out loud before sending",
                "One CTA per message — never two",
                "Friend first. Pitch never opens the message.",
                "Send the payment link during the call — not after",
              ].map((tip, i) => (
                <div key={i} style={{ fontSize: "12px", color: "#1440C4", display: "flex", gap: "6px" }}>
                  <span style={{ opacity: 0.5 }}>·</span> {tip}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
        input:focus, select:focus, textarea:focus { border-color: #1440C4 !important; box-shadow: 0 0 0 2px rgba(20,64,196,0.1); }
      `}</style>
    </div>
  );
}
