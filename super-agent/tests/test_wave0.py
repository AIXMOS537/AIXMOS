"""
Wave 0 tests: the head agent's rails. One SQLite store, the contact/spend guard, the approvals inbox and the
scheduler. Stdlib unittest only, no network, never the real memory/ folder.
    python -m unittest tests.test_wave0 -v
"""
import os, sys, time, shutil, tempfile, threading, unittest
from datetime import datetime

TMP = tempfile.mkdtemp(prefix="aixmos-w0-")
os.environ["AIXMOS_MEMDIR"] = os.path.join(TMP, "memory")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "vendor")]

from aixmos import settings, store, guard, approvals, scheduler, skillkit, agent, crm, email_tools  # noqa: E402

# In a full-suite run another test module may have set the scratch folder first; either way never the real one.
assert os.path.abspath(settings.MEMDIR).startswith(os.path.abspath(tempfile.gettempdir())), "tests must never touch the real memory folder"


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def at(h, m=0):
    return datetime(2026, 10, 5, h, m).timestamp()


def wipe(*tables):
    with store.tx() as c:
        for t in tables:
            c.execute("DELETE FROM %s" % t)


class Store(unittest.TestCase):
    def test_state_roundtrip_and_audit(self):
        store.state_set("demo", "k", {"a": [1, 2]})
        self.assertEqual(store.state_get("demo", "k"), {"a": [1, 2]})
        self.assertEqual(store.state_get("demo", "missing", "d"), "d")
        store.audit("test.event", "r1", {"x": 1})
        self.assertEqual(store.events(1, "test.event")[0]["ref"], "r1")

    def test_rollback_on_error(self):
        with self.assertRaises(RuntimeError):
            with store.tx() as c:
                c.execute("INSERT INTO events(ts, kind) VALUES (1, 'rollback.me')")
                raise RuntimeError("boom")
        self.assertEqual(store.events(5, "rollback.me"), [])


class Contacts(unittest.TestCase):
    def setUp(self):
        wipe("contact_policy", "sends")

    def test_normalize(self):
        self.assertEqual(guard.normalize("Jo <JO@Example.COM>"), "mailto:jo@example.com")
        self.assertEqual(guard.normalize("(555) 123-4567"), "tel:+15551234567")
        self.assertEqual(guard.normalize("+1 555 123 4567"), "tel:+15551234567")
        self.assertEqual(guard.normalize("not a contact"), "")
        self.assertEqual(guard.channel_of("555-123-4567"), "sms")

    def test_stop_words(self):
        for t in ("STOP", "stop.", " Unsubscribe ", "STOP please", "opt out", "Remove me"):
            self.assertTrue(guard.is_stop(t), t)
        for t in ("stopped by yesterday, can we talk?", "", "yes", "can you stop by at 5"):
            self.assertFalse(guard.is_stop(t), t)

    def test_opt_out_blocks_every_format_of_the_same_person(self):
        guard.opt_out("555.123.4567", reason="replied STOP", source="sms")
        for form in ("+15551234567", "(555) 123-4567", "1-555-123-4567"):
            self.assertIn("opted out", guard.blocked(form))
            self.assertFalse(guard.check_send("sms", form, now=at(12)))
        guard.opt_in("5551234567", source="texted START")
        self.assertIsNone(guard.blocked("5551234567"))

    def test_quiet_hours_only_hold_texts(self):
        d = guard.check_send("sms", "5559990000", now=at(22, 30))
        self.assertFalse(d)
        self.assertEqual(d.reason, "quiet hours")
        self.assertEqual(datetime.fromtimestamp(d.retry_at).hour, 8)
        self.assertTrue(guard.check_send("email", "a@b.co", now=at(22, 30)))
        self.assertTrue(guard.check_send("sms", "5559990000", now=at(10)))

    def test_per_contact_cap(self):
        for _ in range(3):
            guard.record_send("email", "cap@b.co", now=at(10))
        d = guard.check_send("email", "cap@b.co", now=at(11))
        self.assertFalse(d)
        self.assertIn("3 times today", d.reason)

    def test_channel_mismatch(self):
        self.assertFalse(guard.check_send("sms", "a@b.co", now=at(10)))


class Spend(unittest.TestCase):
    def setUp(self):
        wipe("spend")
        settings.update(prefs={"spend_daily_usd": 1.0})

    def tearDown(self):
        settings.update(prefs={"spend_daily_usd": 2.0})

    def test_free_engines_cost_nothing(self):
        self.assertEqual(guard.charge("ollama", "chat"), 0.0)
        self.assertEqual(guard.charge("pollinations", "image"), 0.0)

    def test_automatic_calls_stop_at_budget_people_do_not(self):
        guard.charge("openai", "image", now=at(9))          # 0.08
        with self.assertRaises(guard.SpendBlocked):
            guard.charge("openai", "video", now=at(9))      # 1.50 would pass 1.00
        self.assertEqual(guard.charge("openai", "video", interactive=True, now=at(9)), 1.5)
        self.assertAlmostEqual(guard.spent_today(now=at(9)), 1.58)
        self.assertAlmostEqual(guard.spent_today(now=at(9), automated_only=True), 0.08)


class Approvals(unittest.TestCase):
    def setUp(self):
        wipe("approvals")
        self.calls = []
        approvals.register("test.send", lambda p: self.calls.append(p) or {"sent": p["to"]})
        approvals.register("test.boom", lambda p: (_ for _ in ()).throw(RuntimeError("provider down")))
        settings.update(prefs={"autopilot": {}})

    def test_nothing_runs_until_approved(self):
        it = approvals.propose("test.send", "Email Jo", {"to": "jo@b.co"}, skill="demo")
        self.assertEqual(it["status"], "pending")
        self.assertEqual(self.calls, [])
        done = approvals.decide(it["id"], True)
        self.assertEqual(done["status"], "executed")
        self.assertEqual(done["result"], {"sent": "jo@b.co"})

    def test_reject_never_runs_and_double_decide_is_safe(self):
        it = approvals.propose("test.send", "Email Al", {"to": "al@b.co"})
        approvals.decide(it["id"], False)
        approvals.decide(it["id"], True)                     # too late: stays rejected
        self.assertEqual(approvals.get(it["id"])["status"], "rejected")
        it2 = approvals.propose("test.send", "Email Bo", {"to": "bo@b.co"})
        approvals.decide(it2["id"], True)
        approvals.decide(it2["id"], True)
        self.assertEqual(len(self.calls), 1)

    def test_concurrent_approve_runs_once(self):
        it = approvals.propose("test.send", "Email Cy", {"to": "cy@b.co"})
        ts = [threading.Thread(target=approvals.decide, args=(it["id"], True)) for _ in range(6)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(self.calls), 1)

    def test_dedupe_and_failure(self):
        a = approvals.propose("test.send", "x", {"to": "d@b.co"}, dedupe="seq1:step1")
        b = approvals.propose("test.send", "x", {"to": "d@b.co"}, dedupe="seq1:step1")
        self.assertEqual(a["id"], b["id"])
        f = approvals.decide(approvals.propose("test.boom", "y", {})["id"], True)
        self.assertEqual(f["status"], "failed")
        self.assertIn("provider down", f["error"])
        self.assertEqual(approvals.retry(f["id"])["status"], "pending")

    def test_autopilot_is_opt_in_per_skill_and_kind(self):
        it = approvals.propose("test.send", "z", {"to": "e@b.co"}, skill="demo", auto=True)
        self.assertEqual(it["status"], "pending")
        settings.update(prefs={"autopilot": {"demo": ["test.send"]}})
        it = approvals.propose("test.send", "z", {"to": "f@b.co"}, skill="demo", auto=True)
        self.assertEqual(it["status"], "executed")
        self.assertEqual(it["decided_by"], "autopilot:demo")
        it = approvals.propose("test.send", "z", {"to": "g@b.co"}, skill="other", auto=True)
        self.assertEqual(it["status"], "pending")

    def test_unknown_kind_refused(self):
        with self.assertRaises(ValueError):
            approvals.propose("nope.kind", "t", {})


class Scheduler(unittest.TestCase):
    def setUp(self):
        wipe("jobs")
        self.ran = []
        scheduler.handler("t.ok")(lambda p, j: self.ran.append(p["n"]) or {"ok": p["n"]})
        scheduler.handler("t.flaky")(lambda p, j: (_ for _ in ()).throw(RuntimeError("flaky")))
        scheduler.handler("t.later")(lambda p, j: (_ for _ in ()).throw(scheduler.Later(p["at"], "quiet hours")))

    def test_runs_only_when_due_and_once(self):
        j = scheduler.schedule("t.ok", {"n": 1}, due=at(10))
        self.assertEqual(scheduler.run_due(now=at(9)), [])
        self.assertEqual(scheduler.run_due(now=at(10)), [(j["id"], "done")])
        self.assertEqual(scheduler.run_due(now=at(11)), [])
        self.assertEqual(self.ran, [1])

    def test_dedupe_keeps_one_live_job(self):
        a = scheduler.schedule("t.ok", {"n": 2}, due=at(10), dedupe="k1")
        b = scheduler.schedule("t.ok", {"n": 3}, due=at(10), dedupe="k1")
        self.assertEqual(a["id"], b["id"])
        scheduler.run_due(now=at(10))
        c = scheduler.schedule("t.ok", {"n": 4}, due=at(12), dedupe="k1")   # finished key is reusable
        self.assertNotEqual(c["id"], a["id"])

    def test_retry_then_fail(self):
        j = scheduler.schedule("t.flaky", {}, due=at(10), max_attempts=2)
        self.assertEqual(scheduler.run_due(now=at(10)), [(j["id"], "retry")])
        self.assertEqual(scheduler.get(j["id"])["due"], at(10) + 60)
        self.assertEqual(scheduler.run_due(now=at(10) + 60), [(j["id"], "failed")])
        self.assertIn("flaky", scheduler.get(j["id"])["last_error"])

    def test_later_moves_without_spending_an_attempt(self):
        j = scheduler.schedule("t.later", {"at": at(8) + 86400}, due=at(22), max_attempts=1)
        self.assertEqual(scheduler.run_due(now=at(22)), [(j["id"], "later")])
        row = scheduler.get(j["id"])
        self.assertEqual((row["status"], row["attempts"], row["due"]), ("pending", 0, at(8) + 86400))

    def test_crashed_lease_is_reclaimed(self):
        j = scheduler.schedule("t.ok", {"n": 5}, due=at(10))
        with store.tx() as c:                                   # simulate a crash mid-run
            c.execute("UPDATE jobs SET status='running', lease_until=?, attempts=1 WHERE id=?", (at(10) + 10, j["id"]))
        self.assertEqual(scheduler.run_due(now=at(10) + 5), [])
        self.assertEqual(scheduler.run_due(now=at(10) + 11), [(j["id"], "done")])

    def test_cancel(self):
        j = scheduler.schedule("t.ok", {"n": 6}, due=at(10))
        self.assertEqual(scheduler.cancel(j["id"]), 1)
        self.assertEqual(scheduler.run_due(now=at(11)), [])


class AgentSpendGuard(unittest.TestCase):
    """Automatic paid calls (agent, MCP, /v1) stop at the daily budget; free engines never do."""
    def setUp(self):
        wipe("spend")
        from aixmos import imagegen
        self.imagegen, self.calls = imagegen, []
        self._orig = imagegen.generate
        imagegen.generate = lambda prompt, **k: self.calls.append(prompt) or {"url": "/media/x.png", "final_prompt": prompt}
        settings.update(providers={"openai": {"api_key": "sk-test-not-real-0000000000000000000000"}},
                        prefs={"image_provider": "openai", "spend_daily_usd": 0.10})

    def tearDown(self):
        self.imagegen.generate = self._orig
        settings.update(providers={"openai": {"api_key": "__clear__"}}, prefs={"image_provider": "auto", "spend_daily_usd": 2.0})

    def ctx(self):
        return {"autonomy": "builder", "artifacts": []}

    def test_paid_image_is_charged_then_blocked_at_budget(self):
        out = agent.call_tool("generate_image", {"prompt": "a red van"}, self.ctx())
        self.assertIn("image saved", out)
        self.assertAlmostEqual(guard.spent_today(), 0.08)
        out = agent.call_tool("generate_image", {"prompt": "a blue van"}, self.ctx())
        self.assertTrue(out.startswith("ERROR"), out)
        self.assertIn("budget", out)
        self.assertEqual(self.calls, ["a red van"])                  # the second paid call never happened

    def test_free_provider_is_never_blocked(self):
        settings.update(prefs={"image_provider": "pollinations", "spend_daily_usd": 0.0, "image_free_public": True})
        settings.update(providers={"openai": {"api_key": "__clear__"}})
        for i in range(3):
            self.assertIn("image saved", agent.call_tool("generate_image", {"prompt": "p%d" % i}, self.ctx()))
        self.assertEqual(guard.spent_today(), 0.0)


DEMO_SKILL = '''
from aixmos import scheduler
CALLS = []
def t_hello(a, ctx): return "hello " + (a.get("who") or "world")
def tick(payload, job): CALLS.append(1); return {"ticked": True}
def run_it(payload): return {"ran": payload}
SKILL = {"id": "demo", "name": "Demo", "summary": "A demo skill for tests.", "needs": [],
         "tools": [("demo_hello", "Say hello.", {"who": "string"}, [], t_hello, "safe")],
         "actions": {"tick": tick}, "executors": {"demo.run": run_it},
         "triggers": [{"action": "tick", "every_minutes": 30}],
         "rules": ["Never shout."]}
'''
BAD_SKILL = '''
SKILL = {"id": "broken", "name": "Broken", "summary": "Tool name breaks the prefix rule.", "needs": [],
         "tools": [("hello", "x", {}, [], lambda a, c: "x", "safe")]}
'''
GUIDE = "\n".join(["# Demo", "", "## Rules", "Keep it calm.", "", "## Pricing questions", "Quote ranges only.", "",
                   "## Weather small talk", "Sunny. " * 400])


class SkillRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join(TMP, "skills-fixture")
        for sid, src in (("demo", DEMO_SKILL), ("broken", BAD_SKILL)):
            os.makedirs(os.path.join(cls.dir, sid), exist_ok=True)
            with open(os.path.join(cls.dir, sid, "skill.py"), "w", encoding="utf-8") as f:
                f.write(src)
        with open(os.path.join(cls.dir, "demo", "guide.md"), "w", encoding="utf-8") as f:
            f.write(GUIDE)
        cls.real = skillkit.SKILLS_DIR
        skillkit.SKILLS_DIR = cls.dir
        skillkit.load(force=True)

    @classmethod
    def tearDownClass(cls):
        skillkit.SKILLS_DIR = cls.real
        skillkit.load(force=True)

    def test_catalog_reports_good_and_broken_skills(self):
        cat = {s["id"]: s for s in skillkit.catalog()}
        self.assertEqual(cat["demo"]["state"], "ready")
        self.assertEqual(cat["broken"]["state"], "error")
        self.assertIn("must start with broken_", cat["broken"]["error"])

    def test_agent_sees_and_runs_skill_tools(self):
        names = [t["function"]["name"] for t in agent.tool_schemas("safe")]
        self.assertIn("demo_hello", names)
        self.assertIn("read_file", names)
        self.assertEqual(agent.call_tool("demo_hello", {"who": "Jo"}, {"autonomy": "safe"}), "hello Jo")

    def test_executor_and_action_registered(self):
        self.assertIn("demo.run", approvals.EXECUTORS)
        self.assertIn("demo.tick", scheduler.HANDLERS)

    def test_trigger_reschedules_itself(self):
        wipe("jobs")
        skillkit.ensure_triggers(datetime(2026, 10, 5, 9, 0))
        j = scheduler.jobs("pending")
        self.assertEqual([x["action"] for x in j], ["demo.tick"])
        self.assertEqual(scheduler.run_due(now=j[0]["due"]), [(j[0]["id"], "done")])
        nxt = scheduler.jobs("pending")
        self.assertEqual([x["action"] for x in nxt], ["demo.tick"])      # the timer keeps ticking
        self.assertNotEqual(nxt[0]["id"], j[0]["id"])

    def test_persona_keeps_rules_and_profile_and_picks_relevant_sections(self):
        from aixmos import skills
        skills.save_profile({"name": "Brightside Plumbing"})
        p = skillkit.persona("demo", query="what are your pricing questions answer", budget=1200)
        self.assertIn("Never shout.", p)
        self.assertIn("Brightside Plumbing", p)
        self.assertIn("Quote ranges only.", p)
        self.assertIn("Keep it calm.", p)              # a Rules section is always kept
        self.assertNotIn("Sunny. Sunny.", p)          # the irrelevant, oversized section is left out
        self.assertLessEqual(len(p), 1400)


class FollowupSkill(unittest.TestCase):
    """The real skills/followup skill, with the mailbox and the model replaced by fakes."""
    @classmethod
    def setUpClass(cls):
        skillkit.load(force=True)
        cls.sk = skillkit.get("followup")
        assert cls.sk, skillkit.catalog()

    def setUp(self):
        wipe("jobs", "approvals", "sends", "contact_policy")
        with crm._LOCK:
            d = crm._load(); d["sequences"] = []; d["leads"] = []; crm._save(d)
        self.sent, self.inbox, self.body = [], [], "Hi Jo, sorry we missed your call earlier. What can we help with? Just reply here."
        self._orig = (email_tools.list_accounts, email_tools.draft, email_tools.send, email_tools.inbox)
        email_tools.list_accounts = lambda: [{"id": "acc1", "type": "smtp", "email": "me@shop.co", "imap": True}]
        email_tools.draft = lambda intent, to=None, tone=None, **k: {"subject": "Sorry we missed you", "body": self.body}
        email_tools.send = lambda aid, to, subject, body, **k: self.sent.append((aid, to, subject))
        email_tools.inbox = lambda aid, n=12: self.inbox
        settings.update(prefs={"autopilot": {}})

    def tearDown(self):
        email_tools.list_accounts, email_tools.draft, email_tools.send, email_tools.inbox = self._orig

    def act(self, name, payload=None):
        return self.sk["actions"][name](payload or {}, None)

    def start(self, kind="missed_call", contact="jo@b.co"):
        return crm.start_sequence(kind, contact=contact, name="Jo")

    def test_due_step_goes_to_inbox_then_sends_once_after_approval(self):
        seq = self.start()
        self.assertEqual(self.act("sweep")["queued"], 1)
        scheduler.run_due()
        items = approvals.pending()
        self.assertEqual(len(items), 1)
        self.assertEqual(self.sent, [])
        step1 = crm.all_data()["sequences"][0]["steps"][0]
        self.assertEqual(step1["status"], "awaiting_approval")
        self.assertEqual(self.act("sweep")["queued"], 0)          # step 2 waits for step 1
        done = approvals.decide(items[0]["id"], True)
        self.assertEqual(done["status"], "executed", done.get("error"))
        self.assertEqual(self.sent, [("acc1", "jo@b.co", "Sorry we missed you")])
        self.assertEqual(crm.all_data()["sequences"][0]["steps"][0]["status"], "sent")
        self.assertEqual(guard.check_send("email", "jo@b.co").ok, True)
        approvals.decide(items[0]["id"], True)
        self.assertEqual(len(self.sent), 1)

    def test_opt_out_stops_the_sequence(self):
        self.start(contact="al@b.co")
        guard.opt_out("al@b.co", reason="unsubscribed")
        self.act("sweep"); scheduler.run_due()
        self.assertEqual(approvals.pending(), [])
        self.assertEqual(crm.all_data()["sequences"][0]["status"], "stopped")

    def test_opt_out_after_approval_still_wins(self):
        self.start(contact="bo@b.co")
        self.act("sweep"); scheduler.run_due()
        it = approvals.pending()[0]
        guard.opt_out("bo@b.co", reason="replied STOP")
        res = approvals.decide(it["id"], True)
        self.assertEqual(res["status"], "failed")
        self.assertIn("opted out", res["error"])
        self.assertEqual(self.sent, [])

    def test_reply_stops_before_drafting_and_before_sending(self):
        seq = self.start(contact="cy@b.co")
        self.act("sweep"); scheduler.run_due()
        it = approvals.pending()[0]
        later = datetime.fromtimestamp(seq["created"] + 120).strftime("%Y-%m-%d %H:%M")
        self.inbox = [{"from": "Cy <CY@b.co>", "date": later, "subject": "re: call"}]
        res = approvals.decide(it["id"], True)
        self.assertEqual(res["status"], "failed")
        self.assertIn("replied", res["error"])
        self.assertEqual(crm.all_data()["sequences"][0]["status"], "stopped")
        self.assertEqual(self.sent, [])

    def test_unwritten_or_off_brand_link_drafts_are_never_proposed(self):
        self.start(contact="di@b.co")
        self.body = "Hi Di, book here: https://bookme.example.evil.io/x to grab a slot."
        self.act("sweep")
        self.assertEqual([s for _, s in scheduler.run_due()], ["retry"])
        self.assertEqual(approvals.pending(), [])
        with store.tx() as c:
            c.execute("UPDATE jobs SET due=0")
        self.body = "opener"                                       # model failed: fallback echo of the instruction
        self.assertEqual([s for _, s in scheduler.run_due()], ["retry"])
        self.assertEqual(approvals.pending(), [])

    def test_review_request_needs_the_owners_review_link(self):
        from aixmos import skills
        skills.save_profile({"review_link": ""})
        self.start(kind="review_request", contact="ed@b.co")
        self.act("sweep"); scheduler.run_due()
        self.assertEqual(approvals.pending(), [])
        self.assertEqual(crm.all_data()["sequences"][0]["steps"][0]["status"], "skipped")
        skills.save_profile({"review_link": "https://g.page/r/brightside/review"})
        self.body = "Thanks Ed! If you have a minute: https://g.page/r/brightside/review means a lot to us."
        self.start(kind="review_request", contact="fa@b.co")
        self.act("sweep"); scheduler.run_due()
        self.assertEqual(len(approvals.pending()), 1)

    def test_rejected_step_is_skipped_and_autopilot_sends_directly(self):
        self.start(contact="gi@b.co")
        self.act("sweep"); scheduler.run_due()
        approvals.decide(approvals.pending()[0]["id"], False)
        self.act("sweep")
        self.assertEqual(crm.all_data()["sequences"][0]["steps"][0]["status"], "skipped")
        settings.update(prefs={"autopilot": {"followup": ["followup.email"]}})
        self.start(contact="ha@b.co")
        self.act("sweep"); scheduler.run_due()
        self.assertEqual([to for _, to, _ in self.sent], ["ha@b.co"])

    def test_manual_email_send_respects_opt_out_too(self):
        email_tools.send = self._orig[2]
        guard.opt_out("iv@b.co", reason="asked by phone")
        with self.assertRaises(ValueError) as e:
            email_tools.send("acc1", "iv@b.co", "hi", "hello there")
        self.assertIn("opted out", str(e.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
