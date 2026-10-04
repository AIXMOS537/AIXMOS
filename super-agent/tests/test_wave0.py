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

from aixmos import settings, store, guard, approvals, scheduler  # noqa: E402

assert settings.MEMDIR.startswith(TMP), "tests must never touch the real memory folder"


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
