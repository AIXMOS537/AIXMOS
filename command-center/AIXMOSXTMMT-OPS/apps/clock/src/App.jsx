import { useEffect, useState } from "react";
import { supabase } from "./supabase.js";
import "./App.css";

const STATUSES = [
  { key: "available", label: "Available", color: "#22c55e" },
  { key: "busy", label: "Busy", color: "#eab308" },
  { key: "break", label: "Break", color: "#f97316" },
  { key: "off", label: "Off", color: "#6b7280" },
];

export default function App() {
  const [email, setEmail] = useState("");
  const [session, setSession] = useState(null);
  const [member, setMember] = useState(null);
  const [status, setStatus] = useState("off");
  const [message, setMessage] = useState("");
  const [wall, setWall] = useState([]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session?.user?.email) return;
    loadMember(session.user.email);
  }, [session]);

  useEffect(() => {
    loadWall();
    const t = setInterval(loadWall, 30_000);
    return () => clearInterval(t);
  }, []);

  async function loadMember(userEmail) {
    const { data, error } = await supabase
      .from("team_members")
      .select("id, display_name, email, role")
      .eq("email", userEmail)
      .maybeSingle();
    if (error) {
      setMessage(error.message);
      return;
    }
    if (!data) {
      setMessage("No team_members row for this email. Ask Ops to add you.");
      return;
    }
    setMember(data);
    const { data: live } = await supabase
      .from("availability_live")
      .select("status")
      .eq("member_id", data.id)
      .maybeSingle();
    if (live?.status) setStatus(live.status);
  }

  async function loadWall() {
    const { data } = await supabase
      .from("availability_live")
      .select("status, heartbeat_at, team_members(display_name, office, skills)")
      .order("updated_at", { ascending: false });
    setWall(data || []);
  }

  async function signIn(e) {
    e.preventDefault();
    setMessage("");
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: window.location.origin },
    });
    setMessage(error ? error.message : "Check your email for the magic link.");
  }

  async function signOut() {
    await supabase.auth.signOut();
    setMember(null);
    setSession(null);
  }

  async function setLive(nextStatus, event) {
    if (!member) return;
    setMessage("");
    const now = new Date().toISOString();
    const { error: upsertErr } = await supabase.from("availability_live").upsert({
      member_id: member.id,
      status: nextStatus,
      updated_at: now,
      heartbeat_at: now,
    });
    if (upsertErr) {
      setMessage(upsertErr.message);
      return;
    }
    await supabase.from("time_events").insert({
      member_id: member.id,
      event,
      meta: { status: nextStatus },
    });
    setStatus(nextStatus);
    loadWall();
  }

  if (!session) {
    return (
      <div className="app">
        <h1>Empire Clock</h1>
        <p className="muted">Sign in with your team email (Supabase magic link).</p>
        <form onSubmit={signIn} className="card">
          <input
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit">Send magic link</button>
        </form>
        {message && <p className="msg">{message}</p>}
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <h1>Empire Clock</h1>
        <button type="button" className="ghost" onClick={signOut}>
          Sign out
        </button>
      </header>
      {member && (
        <p className="who">
          {member.display_name} · <span className="role">{member.role}</span>
        </p>
      )}
      <section className="card">
        <h2>Your status</h2>
        <div className="status-grid">
          {STATUSES.map((s) => (
            <button
              key={s.key}
              type="button"
              className={status === s.key ? "active" : ""}
              style={{ borderColor: s.color }}
              onClick={() =>
                setLive(
                  s.key,
                  s.key === "off" ? "clock_out" : "status_change"
                )
              }
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="quick">
          <button type="button" onClick={() => setLive("available", "clock_in")}>
            Clock in
          </button>
          <button type="button" onClick={() => setLive("off", "clock_out")}>
            Clock out
          </button>
        </div>
      </section>
      {message && <p className="msg">{message}</p>}
      <section className="card wall">
        <h2>Live team</h2>
        <ul>
          {wall.map((row, i) => (
            <li key={i}>
              <span
                className="dot"
                style={{
                  background:
                    STATUSES.find((s) => s.key === row.status)?.color || "#666",
                }}
              />
              {row.team_members?.display_name || "—"} — {row.status}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
