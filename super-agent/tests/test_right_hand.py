"""
Right-hand tests: delegated authority (mandates + LOCK), attention management, the pre-action judgment and the
evidence-only briefing. Stdlib unittest only, no network, never the real memory/ folder.
    python -m unittest tests.test_right_hand -v
"""
import os, sys, json, time, shutil, tempfile, unittest
from datetime import datetime

TMP = tempfile.mkdtemp(prefix="aixmos-rh-")
os.environ.setdefault("AIXMOS_MEMDIR", os.path.join(TMP, "memory"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "vendor")]

from aixmos import settings, store, approvals, mandate, attention, judgment, briefing, crm, skillkit, channels  # noqa: E402,F401

assert os.path.abspath(settings.MEMDIR).startswith(os.path.abspath(tempfile.gettempdir())), "tests must never touch the real memory folder"

RAN = []
approvals.register("rh.send", lambda p: RAN.append(p) or {"ok": True})
approvals.register("contract.send", lambda p: {"ok": True})


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def at(h, m=0, day=5):
    return datetime(2030, 10, day, h, m).timestamp()     # always in the future


def wipe():
    mandate._ensure(); attention._ensure()
    with store.tx() as c:
        for t in ("approvals", "events", "mandates", "attention", "contact_policy", "sends", "skill_state", "jobs"):
            c.execute("DELETE FROM %s" % t)
    settings.update(prefs={"autopilot": {}, "business_rules": {}, "attention_rules": {}})
    RAN.clear()


class Mandates(unittest.TestCase):
    def setUp(self):
        wipe()

    def test_hard_limits(self):
        now = time.time()
        for kind in ("contract.send", "payment.refund", "settings.change", "mandate.extend", "crm.delete"):
            with self.assertRaises(ValueError, msg=kind):
                mandate.draft("x", now + 3600, will=[kind], now=now)
        with self.assertRaises(ValueError):
            mandate.draft("x", now + 15 * 86400, will=["rh.send"], now=now)       # longer than 14 days
        with self.assertRaises(ValueError):
            mandate.draft("x", now - 1, will=["rh.send"], now=now)                # already over
        with self.assertRaises(ValueError):
            mandate.draft("x", now + 3600, will=["ghost.send"], now=now)            # a power that doesn't exist

    def test_draft_grants_nothing_until_owner_activates(self):
        m = mandate.draft("Away", time.time() + 86400, will=["rh.send"])
        self.assertEqual(m["status"], "draft")
        self.assertIsNone(mandate.covers("rh.send"))
        with self.assertRaises(PermissionError):
            mandate.activate(m["id"], by="agent")
        with self.assertRaises(PermissionError):
            mandate.activate(m["id"], by="external:email")
        mandate.activate(m["id"], by="owner")
        self.assertEqual(mandate.covers("rh.send"), m["id"])
        self.assertIsNone(mandate.covers("rh.send", risk="spend"))           # money never, even if listed
        self.assertIsNone(mandate.covers("rh.send", risk="post"))            # public posting never
        self.assertIsNone(mandate.covers("other.send"))
        self.assertIn("I WILL ASK BEFORE", mandate.plan(m)["text"])

    def test_expires_and_revokes(self):
        now = time.time()
        m = mandate.draft("Short", now + 60, will=["rh.send"], now=now)
        mandate.activate(m["id"], by="owner", now=now)
        self.assertTrue(mandate.covers("rh.send", now=now + 30))
        self.assertIsNone(mandate.covers("rh.send", now=now + 61))
        self.assertEqual(mandate.get(m["id"])["status"], "expired")
        with self.assertRaises(ValueError):
            mandate.activate(m["id"], by="owner")                              # can't be switched back on
        m2 = mandate.draft("Two", now + 3600, will=["rh.send"])
        mandate.activate(m2["id"], by="owner")
        mandate.revoke(m2["id"], by="owner")
        self.assertIsNone(mandate.covers("rh.send"))

    def test_mandate_runs_inbox_items_and_is_recorded(self):
        m = mandate.draft("Away", time.time() + 86400, will=["rh.send"])
        mandate.activate(m["id"], by="owner")
        it = approvals.propose("rh.send", "Follow-up to Sam", {"to": "sam@example.com"}, skill="t", auto=True)
        self.assertEqual(it["status"], "executed")
        self.assertEqual(it["decided_by"], "mandate:" + m["id"])
        paid = approvals.propose("rh.send", "Paid thing", {}, skill="t", risk="spend", auto=True)
        self.assertEqual(paid["status"], "pending")                             # spend never rides a mandate
        manual = approvals.propose("rh.send", "Not auto", {}, skill="t")
        self.assertEqual(manual["status"], "pending")                           # auto=False still waits

    def test_lock_stops_everything_automatic(self):
        settings.update(prefs={"autopilot": {"t": True}})
        m = mandate.draft("Away", time.time() + 86400, will=["rh.send"])
        mandate.activate(m["id"], by="owner")
        with self.assertRaises(PermissionError):
            mandate.lock(by="external:telegram-stranger")
        mandate.lock(by="owner:telegram", why="lost phone")
        self.assertTrue(mandate.locked())
        self.assertEqual(mandate.get(m["id"])["status"], "revoked")
        it = approvals.propose("rh.send", "Held", {}, skill="t", auto=True)
        self.assertEqual(it["status"], "pending")                               # autopilot is off while locked
        with self.assertRaises(PermissionError):
            approvals.decide(it["id"], True, by="owner:telegram")               # remote approvals refused
        with self.assertRaises(PermissionError):
            mandate.unlock(by="owner:telegram")                                 # unlock only on this computer
        with self.assertRaises(PermissionError):
            mandate.activate(mandate.draft("New", time.time() + 3600, will=["rh.send"])["id"], by="owner")
        self.assertEqual(approvals.decide(it["id"], True, by="owner")["status"], "executed")  # the owner, locally
        mandate.unlock(by="owner")
        self.assertFalse(mandate.locked())
        self.assertEqual(mandate.get(m["id"])["status"], "revoked")             # unlocking never revives it


class Attention(unittest.TestCase):
    def setUp(self):
        wipe()
        settings.update(prefs={"quiet_start": 21, "quiet_end": 8})

    def test_levels_and_content_cannot_page(self):
        self.assertEqual(attention.classify("lead.new"), "routine")
        self.assertEqual(attention.classify("lead.new", text="I want a refund now"), "important")
        i = attention.observe("security.alert", "URGENT!!! wire money", source="external:email", now=at(3))
        self.assertEqual(i["level"], "important")                               # content never reaches urgent
        self.assertEqual(i["interrupt"], "none")
        u = attention.observe("security.alert", "New login from an unknown device", now=at(3))
        self.assertEqual((u["level"], u["interrupt"]), ("urgent", "queued"))    # urgent goes out even at 3 a.m.

    def test_owner_can_rerank(self):
        settings.update(prefs={"attention_rules": {"lead.new": "important"}})
        self.assertEqual(attention.classify("lead.new"), "important")

    def test_dedupe_and_rate_limits(self):
        a = attention.observe("approval.pending", "OK to send #1?", dedupe="approval:1", now=at(10))
        b = attention.observe("approval.pending", "OK to send #1?", dedupe="approval:1", now=at(10, 5))
        self.assertEqual(a["id"], b["id"]); self.assertEqual(b["count"], 2)
        self.assertEqual(a["interrupt"], "queued")
        c = attention.observe("approval.pending", "OK to send #2?", dedupe="approval:2", now=at(10, 10))
        self.assertEqual(c["interrupt"], "held")                                # one nudge per kind per hour
        q = attention.observe("approval.pending", "OK to send #3?", dedupe="approval:3", now=at(23))
        self.assertEqual(q["interrupt"], "held")                                # quiet hours hold decisions
        self.assertEqual(attention.resolve(dedupe="approval:1"), 1)
        self.assertEqual(attention.get(a["id"])["interrupt"], "cancelled")      # resolved before delivery: no ping

    def test_mandate_alert_categories_interrupt(self):
        r1 = attention.observe("lead.reply", "Big client replied", now=at(11))
        self.assertEqual(r1["interrupt"], "none")                               # important: waits for the brief
        m = mandate.draft("Away", at(12) + 86400, will=["rh.send"], now=at(12))     # fixed clock, not today's
        mandate.activate(m["id"], by="owner", now=at(12))
        r2 = attention.observe("lead.reply", "Another big client replied", now=at(12, 30))
        self.assertEqual(r2["interrupt"], "queued")                             # owner asked to be told at once

    def test_push_delivers_scheduled_brief(self):
        b = attention.observe("brief.ready", "Morning briefing", level="routine", push=True, now=at(7, 30))
        self.assertEqual(b["interrupt"], "queued")
        e = attention.observe("brief.ready", "fake brief", source="external:web", push=True, now=at(7, 31))
        self.assertNotEqual(e["interrupt"], "queued")                           # content can't push
        attention.delivered(b["id"], "telegram")
        self.assertNotIn(b["id"], [x["id"] for x in attention.outbox()])

    def test_sweep_turns_events_into_items(self):
        it = approvals.propose("rh.send", "Reply to Dana", {}, skill="t")
        store.audit("job.failed", "j1", {"action": "followup.step", "error": "smtp down"})
        attention.sweep()
        open_ = {r["kind"]: r for r in attention.items("open")}
        self.assertIn("approval.pending", open_)
        self.assertIn("job.failed", open_)
        approvals.decide(it["id"], False)
        attention.sweep()
        self.assertNotIn("approval.pending", [r["kind"] for r in attention.items("open")])
        self.assertEqual(attention.sweep()["read"], 0)                          # cursor: events read once


class Judgment(unittest.TestCase):
    def setUp(self):
        wipe()

    def test_content_is_data_not_command(self):
        v = judgment.evaluate({"kind": "crm.delete", "requested_by": "external:lead-note", "targets": ["all"]})
        self.assertEqual(v["decision"], "refuse")
        self.assertIn("not from you", v["summary"])

    def test_never_touches_own_authority(self):
        for kind in ("permissions.grant", "security.disable", "mandate.extend", "agent.replicate", "settings.update"):
            self.assertEqual(judgment.evaluate({"kind": kind, "requested_by": "owner"})["decision"], "refuse", kind)

    def test_ambiguous_target_and_missing_facts_ask(self):
        v = judgment.evaluate({"kind": "email.send", "requested_by": "owner:telegram",
                               "candidates": ["Sarah Lee (lead)", "Sarah Khan (customer)"]})
        self.assertEqual(v["decision"], "ask"); self.assertEqual(len(v["options"]), 2)
        v = judgment.evaluate({"kind": "contract.create", "requested_by": "owner", "missing": ["project value"]})
        self.assertEqual(v["decision"], "ask"); self.assertIn("project value", v["summary"])
        v = judgment.evaluate({"kind": "email.send", "requested_by": "owner", "confidence": 0.3})
        self.assertEqual(v["decision"], "ask")

    def test_fifty_percent_to_everyone_pushes_back(self):
        settings.update(prefs={"business_rules": {"max_discount_pct": 15, "bulk_confirm_over": 25}})
        contacts = ["lead%d@example.com" % i for i in range(438)]
        from aixmos import guard
        guard.opt_out(contacts[0], reason="STOP")
        v = judgment.evaluate({"kind": "message.bulk", "requested_by": "owner:telegram", "targets": contacts,
                               "text": "Everyone gets 50% off this week!"})
        self.assertEqual(v["decision"], "confirm")
        self.assertEqual(v["impact"], {"targets": 438, "blocked": 1, "reachable": 437})
        self.assertIn("438 people", v["summary"]); self.assertIn("above your limit of 15%", v["summary"])
        self.assertTrue(any("inactive" in o for o in v["options"]))

    def test_forbidden_claims_and_prices(self):
        settings.update(prefs={"business_rules": {"forbidden_phrases": ["guaranteed results"]}})
        v = judgment.evaluate({"kind": "email.send", "requested_by": "owner", "targets": ["a@example.com"],
                               "text": "Guaranteed results for just $499"})
        self.assertEqual(v["decision"], "confirm")
        self.assertIn("guaranteed results", v["summary"]); self.assertIn("quotes a price", v["summary"])

    def test_risk_cannot_be_talked_down_and_mandates_count(self):
        v = judgment.evaluate({"kind": "email.send", "requested_by": "owner", "risk": "low", "targets": ["a@example.com"],
                               "text": "Thanks for your call."})
        self.assertEqual((v["risk"], v["decision"]), ("high", "confirm"))      # a send is high whatever the caller says
        m = mandate.draft("Away", time.time() + 86400, will=["rh.send"])
        mandate.activate(m["id"], by="owner")
        v = judgment.evaluate({"kind": "rh.send", "requested_by": "mandate:" + m["id"], "risk": "high",
                               "targets": ["a@example.com"], "text": "Following up on your quote request."})
        self.assertEqual(v["decision"], "proceed")
        v = judgment.evaluate({"kind": "rh.send", "requested_by": "mandate:" + m["id"], "risk": "high",
                               "reversible": False, "targets": ["a@example.com"], "text": "hi"})
        self.assertEqual(v["decision"], "confirm")                              # irreversible: always the owner
        self.assertEqual(judgment.evaluate({"kind": "crm.search", "requested_by": "owner"})["decision"], "proceed")

    def test_locked_refuses_changes(self):
        mandate.lock(by="owner")
        try:
            self.assertEqual(judgment.evaluate({"kind": "crm.update", "requested_by": "owner:telegram"})["decision"], "refuse")
            self.assertEqual(judgment.evaluate({"kind": "crm.update", "requested_by": "mandate:x"})["decision"], "refuse")
            self.assertEqual(judgment.evaluate({"kind": "crm.update", "requested_by": "owner"})["decision"], "confirm")
            self.assertEqual(judgment.evaluate({"kind": "price.update", "requested_by": "owner"})["risk"], "high")
            self.assertEqual(judgment.evaluate({"kind": "crm.search", "requested_by": "owner"})["decision"], "proceed")
        finally:
            mandate.unlock(by="owner")


class Briefing(unittest.TestCase):
    def setUp(self):
        wipe()
        with crm._LOCK:
            d = crm._load()
            for k in ("leads", "appointments", "sequences", "activity"):
                d[k] = []
            crm._save(d)

    def test_empty_business_invents_nothing(self):
        b = briefing.morning(health=False)
        self.assertEqual(b["sections"]["happened"]["new_leads"], 0)
        self.assertIn("Nothing new recorded.", b["text"])
        self.assertIn("Nothing. You're clear.", b["text"])
        self.assertNotIn("handled", b["text"])

    def test_counts_match_the_record(self):
        crm.upsert_lead({"name": "Mike", "company": "ABC", "contact": "mike@abc.example"})
        today = datetime.now().strftime("%Y-%m-%d")
        crm.book({"name": "Johnson", "when": today + "T10:00", "service": "proposal review"})
        settings.update(prefs={"autopilot": {"t": ["rh.send"]}})
        approvals.propose("rh.send", "Routine follow-up", {}, skill="t", auto=True)       # handled by AIXMOS
        settings.update(prefs={"autopilot": {}})
        owner_item = approvals.propose("rh.send", "Owner-approved", {}, skill="t")
        approvals.decide(owner_item["id"], True, by="owner")
        approvals.propose("rh.send", "Johnson proposal", {}, skill="t")                   # still pending
        store.audit("send.email", "mailto:mike@abc.example", {"skill": "followup"})
        b = briefing.morning(health=False)
        h = b["sections"]["happened"]
        self.assertEqual((h["new_leads"], h["messages_sent"], h["handled_by_aixmos"], h["approved_by_you"]), (1, 1, 1, 1))
        self.assertEqual(len(b["evidence"]["happened"]["handled_by_aixmos"]), 1)          # every number has its ids
        self.assertEqual(b["sections"]["needs_you"]["approvals"], 1)
        self.assertEqual(b["sections"]["needs_you"]["top"], "Johnson proposal")
        self.assertEqual(len(b["sections"]["schedule"]["appointments"]), 1)
        self.assertIn("I handled 1 routine action", b["text"])
        self.assertIn("10:00 Johnson", b["text"])

    def test_locked_is_said_first(self):
        mandate.lock(by="owner")
        try:
            self.assertIn("AIXMOS IS LOCKED", briefing.end_of_day(health=False)["text"])
        finally:
            mandate.unlock(by="owner")



approvals.register("rh.confirmed", lambda p: {"id": "x1"})
approvals.register("rh.mail", lambda p: {"sent_to": p.get("to")})
approvals.register("rh.badcheck", lambda p: {"ok": True})


class Outcomes(unittest.TestCase):
    def setUp(self):
        wipe()
        from aixmos import outcomes
        self.o = outcomes
        outcomes._ensure()
        with store.tx() as c:
            c.execute("DELETE FROM outcomes")

    def test_default_rules_block_classic_false_claims(self):
        self.assertTrue(judgment.rule_conflicts("A risk-free trial with guaranteed results"))
        self.assertTrue(judgment.rule_conflicts("Only $49 this week"))
        self.assertEqual(judgment.rule_conflicts("Thanks for stopping by, see you soon."), [])

    def test_states_are_kept_apart(self):
        self.o.verifier("rh.confirmed")(lambda item, res: ("confirmed", "found it") if res.get("id") else ("mismatch", ""))
        it = approvals.decide(approvals.propose("rh.confirmed", "Make the thing", {"body": "hello"})["id"], True, by="owner")
        st = self.o.state(it["id"])
        self.assertEqual(st["state"], "successful")
        self.assertEqual(st["ladder"], {"requested": True, "authorized": True, "verified": True, "executed": True,
                                        "successful": True})
        plain = approvals.decide(approvals.propose("rh.send", "No check exists", {})["id"], True, by="owner")
        st = self.o.state(plain["id"])
        self.assertEqual((st["state"], st["ladder"]["executed"], st["ladder"]["successful"]), ("not confirmed", True, False))
        waiting = approvals.propose("rh.send", "Still waiting", {})
        self.assertEqual(self.o.state(waiting["id"])["state"], "requested")

    def test_email_is_accepted_never_successful(self):
        self.o.verifier("rh.mail")(self.o._email_accepted)
        it = approvals.decide(approvals.propose("rh.mail", "Mail Jo", {"to": "jo@example.com", "body": "Hi Jo"})["id"],
                              True, by="owner")
        st = self.o.state(it["id"])
        self.assertEqual((st["state"], st["post"]), ("executed", "accepted"))
        self.assertIn("bounces are not visible", st["detail"])

    def test_broken_check_never_fails_a_done_action(self):
        def boom(item, res):
            raise RuntimeError("checker crashed")
        self.o.verifier("rh.badcheck")(boom)
        it = approvals.decide(approvals.propose("rh.badcheck", "x", {})["id"], True, by="owner")
        self.assertEqual(it["status"], "executed")
        self.assertEqual(self.o.state(it["id"])["post"], "unconfirmed")

    def test_automatic_message_breaking_rules_goes_back_to_owner(self):
        settings.update(prefs={"autopilot": {"t": ["rh.send"]}})
        it = approvals.propose("rh.send", "Promo to Sam", {"to": "sam@example.com", "body": "Get 50% off today!"},
                               skill="t", auto=True)
        self.assertEqual((it["status"], it["decided_by"]), ("pending", None))  # held, not sent, not failed
        self.assertIn("not verified", it["note"])
        self.assertEqual(RAN, [])
        self.assertEqual(self.o.state(it["id"])["pre"], "blocked")
        attention.sweep()
        self.assertTrue(any(r["title"].startswith("Held for you") for r in attention.items("open")))
        b = briefing.morning(health=False)
        self.assertEqual(b["sections"]["happened"]["held_for_rules"], 1)
        self.assertIn("held 1 automatic message back", b["text"])
        done = approvals.decide(it["id"], True, by="owner")                    # the owner saw it and said yes
        self.assertEqual(done["status"], "executed")
        self.assertIn("owner approved despite", self.o.state(it["id"])["detail"] + store.one(
            "SELECT pre_detail FROM outcomes WHERE aid=?", (it["id"],))["pre_detail"])
        attention.sweep()
        self.assertFalse(any(r["title"].startswith("Held for you") for r in attention.items("open")))

    def test_mandate_cannot_carry_a_forbidden_claim(self):
        m = mandate.draft("Away", time.time() + 86400, will=["rh.send"])
        mandate.activate(m["id"], by="owner")
        it = approvals.propose("rh.send", "Follow-up", {"to": "a@example.com", "body": "Guaranteed results, no risk!"},
                               skill="t", auto=True)
        self.assertEqual(it["status"], "pending")
        self.assertEqual(RAN, [])


class Skill(unittest.TestCase):
    def test_chief_of_staff_loads_with_tools_and_timers(self):
        cat = {s["id"]: s for s in skillkit.load(force=True)}
        self.assertIn("chief_of_staff", cat)
        self.assertNotEqual(cat["chief_of_staff"]["state"], "error", cat["chief_of_staff"].get("error"))
        self.assertIn("chief_of_staff_check", cat["chief_of_staff"]["tools"])
        out = json.loads(skillkit.tool("chief_of_staff_check")[4]({"kind": "email.send", "targets": ["a@b.co"],
                                                                     "text": "hello"}, {}))
        self.assertEqual(out["decision"], "confirm")                            # the agent never counts as the owner


if __name__ == "__main__":
    unittest.main()
