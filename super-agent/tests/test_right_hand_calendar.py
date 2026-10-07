"""
Calendar (read-only availability from iCal feeds + GoHighLevel bookable slots) and inbox watching (new mail -> attention
items, bounces, STOP). Stdlib unittest only; feeds, inboxes and GoHighLevel are faked; never the real memory/ folder.
    python -m unittest tests.test_right_hand_calendar -v
"""
import os, sys, json, time, shutil, tempfile, unittest
from datetime import datetime, timedelta

TMP = tempfile.mkdtemp(prefix="aixmos-cal-")
os.environ.setdefault("AIXMOS_MEMDIR", os.path.join(TMP, "memory"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "vendor")]

from aixmos import settings, store, approvals, attention, availability, inboxwatch, email_tools, guard, crm, \
    outcomes, briefing, mandate, skillkit, secret_store  # noqa: E402

assert os.path.abspath(settings.MEMDIR).startswith(os.path.abspath(tempfile.gettempdir())), "tests must never touch the real memory folder"

MON = datetime(2030, 10, 7, 8, 0)          # Monday 7 Oct 2030, 08:00 local

ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:a1
DTSTART:20301007T090000
DTEND:20301007T103000
SUMMARY:Team call
ATTENDEE;CN=Mike:mailto:Mike@Johnson.example
BEGIN:VALARM
TRIGGER:-PT10M
SUMMARY:alarm text is not an event
END:VALARM
END:VEVENT
BEGIN:VEVENT
UID:a2
DTSTART:20301007T140000
DURATION:PT1H
SUMMARY:Dentist (looks free
  but folded)
END:VEVENT
BEGIN:VEVENT
UID:a3
DTSTART:20301007T150000
DTEND:20301007T160000
SUMMARY:Birthday reminder
TRANSP:TRANSPARENT
END:VEVENT
BEGIN:VEVENT
UID:a4
DTSTART:20301007T160000
DTEND:20301007T170000
SUMMARY:Cancelled thing
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
UID:w1
DTSTART:20300930T120000
DTEND:20300930T130000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE;COUNT=6
EXDATE:20301009T120000
SUMMARY:Lunch block
END:VEVENT
BEGIN:VEVENT
UID:w1
RECURRENCE-ID:20301014T120000
DTSTART:20301014T130000
DTEND:20301014T140000
SUMMARY:Lunch block (moved)
END:VEVENT
BEGIN:VEVENT
UID:d1
DTSTART;VALUE=DATE:20301010
DTEND;VALUE=DATE:20301011
SUMMARY:Trade show
END:VEVENT
BEGIN:VEVENT
UID:z1
DTSTART:20301008T130000Z
DTEND:20301008T140000Z
SUMMARY:UTC meeting
END:VEVENT
BEGIN:VEVENT
UID:x1
DTSTART;TZID=Mars/Olympus_Mons:20301008T090000
DTEND;TZID=Mars/Olympus_Mons:20301008T093000
SUMMARY:Odd zone
END:VEVENT
BEGIN:VEVENT
UID:m1
DTSTART:20301031T200000
DTEND:20301031T210000
RRULE:FREQ=MONTHLY;BYDAY=-1FR
SUMMARY:Last-Friday social
END:VEVENT
END:VCALENDAR
"""


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def reset():
    attention._ensure(); outcomes._ensure()
    with store.tx() as c:
        for t in ("approvals", "events", "attention", "outcomes", "contact_policy", "sends", "skill_state", "jobs"):
            c.execute("DELETE FROM %s" % t)
    for n in availability._names():
        secret_store.delete(n)
    availability._cache.clear()
    settings.update(prefs={"business_hours": {"days": [0, 1, 2, 3, 4], "start": "09:00", "end": "17:00"},
                           "calendar_min_notice_hours": 2, "calendar_ghl_id": "", "autopilot": {}})


class Calendar(unittest.TestCase):
    def setUp(self):
        reset()
        self._fetch = availability._fetch
        availability._fetch = lambda url: ICS

    def tearDown(self):
        availability._fetch = self._fetch

    def test_feed_url_is_a_secret(self):
        with self.assertRaises(ValueError):
            availability.add_feed("http://calendar.example/basic.ics")
        n = availability.add_feed("webcal://calendar.google.com/calendar/ical/private-abc123/basic.ics")
        self.assertEqual(availability.feeds(), [{"name": n, "host": "calendar.google.com"}])
        self.assertNotIn("private-abc123", json.dumps(store.events(50)))          # never in the audit trail
        with open(settings.FILE, encoding="utf-8") as f:
            self.assertNotIn("private-abc123", f.read())
        self.assertTrue(availability.connected())

    def test_parse_skips_free_cancelled_and_alarms(self):
        notes = set()
        evs = availability.parse_ics(ICS, notes)
        titles = [e["title"] for e in evs]
        self.assertIn("Dentist (looks free but folded)", titles)                  # folded line joined
        for gone in ("Birthday reminder", "Cancelled thing", "alarm text is not an event"):
            self.assertNotIn(gone, titles)
        self.assertEqual(next(e for e in evs if e["title"] == "Dentist (looks free but folded)")["end"],
                         datetime(2030, 10, 7, 15, 0))                             # DURATION
        self.assertIn("mike@johnson.example", next(e for e in evs if e["title"] == "Team call")["attendees"])

    def test_repeats_exceptions_and_unreadable_rules(self):
        availability.add_feed("https://cal.example/x.ics")
        notes = set()
        b = availability.busy(MON - timedelta(days=7), MON + timedelta(days=14), notes)
        lunch = sorted(x["start"] for x in b if x["title"].startswith("Lunch block"))
        # COUNT=6 counts the excluded Wed 9th too (RFC 5545), so the 6th is Wed 16th; Mon 14th moved to 13:00
        self.assertEqual(lunch, [datetime(2030, 9, 30, 12), datetime(2030, 10, 2, 12), datetime(2030, 10, 7, 12),
                                 datetime(2030, 10, 14, 13), datetime(2030, 10, 16, 12)])
        self.assertTrue(any("can't expand" in n for n in notes))                  # last-Friday rule is reported
        self.assertTrue(any("Mars/Olympus_Mons" in n for n in notes))             # unknown zone is reported
        self.assertIn(datetime(2030, 10, 10), [x["start"] for x in b if x["all_day"]])

    def test_free_slots_respect_everything(self):
        availability.add_feed("https://cal.example/x.ics")
        r = availability.free_slots(days=5, minutes=30, limit=20, now=MON, per_day=20)
        starts = [datetime.fromisoformat(s["start"]) for s in r["slots"]]
        self.assertTrue(starts)
        self.assertTrue(all(s >= MON + timedelta(hours=2) for s in starts))          # minimum notice
        for s in starts:
            self.assertTrue(9 <= s.hour < 17 and s.weekday() < 5)
            for bad_from, bad_to in [(datetime(2030, 10, 7, 9), datetime(2030, 10, 7, 10, 30)),
                                     (datetime(2030, 10, 7, 12), datetime(2030, 10, 7, 13)),
                                     (datetime(2030, 10, 7, 14), datetime(2030, 10, 7, 15))]:
                self.assertFalse(bad_from <= s < bad_to, s)
            self.assertNotEqual(s.date(), datetime(2030, 10, 10).date())             # all-day trade show
        self.assertIn(datetime(2030, 10, 7, 15, 0), starts)                          # the "free" birthday doesn't block
        self.assertTrue(r["notes"])                                                  # cautions travel with the answer

    def test_offers_are_spread_out(self):
        availability.add_feed("https://cal.example/x.ics")
        r = availability.free_slots(days=7, limit=6, now=MON)
        days = [s["start"][:10] for s in r["slots"]]
        self.assertTrue(all(days.count(d) <= 2 for d in days))

    def test_ghl_bookable_slots_are_intersected(self):
        from aixmos import ghl
        saved = (ghl.connected, ghl.Client)

        class Fake:
            def req(self, method, path, query=None, body=None, version=None):
                assert path == "/calendars/cal123/free-slots" and method == "GET"
                return {"2030-10-08": {"slots": ["2030-10-08T11:00:00", "2030-10-08T15:00:00"]}, "traceId": "t"}
        try:
            ghl.connected, ghl.Client = (lambda: True), Fake
            settings.update(prefs={"calendar_ghl_id": "cal123"})
            r = availability.free_slots(days=3, now=MON, limit=10, per_day=10)
            self.assertEqual([s["start"] for s in r["slots"]], ["2030-10-08T11:00", "2030-10-08T15:00"])
            self.assertTrue(any("not yet checked on a live calendar" in n for n in r["notes"]))
        finally:
            ghl.connected, ghl.Client = saved

    def test_not_connected_offers_nothing(self):
        r = availability.free_slots(now=MON)
        self.assertEqual((r["slots"], r["connected"]), ([], False))

    def test_unreadable_feed_is_said_not_guessed(self):
        availability.add_feed("https://cal.example/x.ics")
        def boom(url):
            raise OSError("down")
        availability._fetch = boom
        notes = set()
        self.assertEqual(availability.busy(MON, MON + timedelta(days=1), notes), [])
        self.assertTrue(any("couldn't be read" in n for n in notes))

    def test_skill_tools_are_tainting_and_honest(self):
        from aixmos import agent
        skillkit.load(force=True)
        self.assertTrue(agent._spec(skillkit.tool("calendar_free_times")).tainting)
        self.assertIn("No calendar is connected", skillkit.tool("calendar_free_times")[4]({}, {}))
        availability.add_feed("https://cal.example/x.ics")
        self.assertTrue(skillkit.connectors()["calendar"]["ok"])


class FakeMail:
    def __init__(self):
        self.box = {"acc1": []}

    def accounts(self):
        return [{"id": "acc1", "type": "smtp", "label": "owner", "email": "owner@business.example", "imap": True}]

    def inbox(self, aid, n=25):
        return list(reversed(self.box[aid]))[:n]                                    # newest first, like the real one

    def add(self, frm, subject, snippet="", date=None):
        self.box["acc1"].append({"id": str(len(self.box["acc1"]) + 1), "from": frm, "subject": subject,
                                 "snippet": snippet, "date": date or "2030-10-07 0%d:00" % (len(self.box["acc1"]) % 9)})


class Inbox(unittest.TestCase):
    def setUp(self):
        reset()
        self.mail = FakeMail()
        self._saved = (email_tools.list_accounts, email_tools.inbox)
        email_tools.list_accounts, email_tools.inbox = self.mail.accounts, self.mail.inbox
        with crm._LOCK:
            d = crm._load(); d["leads"] = []; crm._save(d)

    def tearDown(self):
        email_tools.list_accounts, email_tools.inbox = self._saved

    def test_first_look_is_a_baseline_then_only_new_mail(self):
        self.mail.add("Old Friend <old@friend.example>", "from last year")
        self.assertEqual(inboxwatch.check()["new"], 0)                                # no flood of old mail
        self.mail.add("New Person <new@person.example>", "hello")
        r = inboxwatch.check()
        self.assertEqual(r["new"], 1)
        self.assertEqual(inboxwatch.check()["new"], 0)                                # seen once

    def test_each_kind_of_mail(self):
        inboxwatch.check()                                                            # baseline (empty)
        approvals.register("rh.mail", lambda p: {"sent_to": p.get("to")})
        it = approvals.decide(approvals.propose("rh.mail", "Quote follow-up", {"to": "sam@client.example", "body": "hi"})["id"],
                              True, by="owner")
        guard.record_send("email", "sam@client.example", "followup")
        guard.record_send("email", "gone@dead.example", "followup")
        approvals.decide(approvals.propose("rh.mail", "To a dead address", {"to": "gone@dead.example", "body": "hi"})["id"],
                         True, by="owner")
        crm.upsert_lead({"name": "Known Lead", "contact": "known@lead.example"})
        self.mail.add("Sam Client <sam@client.example>", "Re: your quote", "Yes, let's talk")
        self.mail.add("Pat <pat@customer.example>", "STOP", "")
        self.mail.add("Shop <no-reply@shop.example>", "Your receipt", "thanks for shopping")
        self.mail.add("Mail Delivery Subsystem <mailer-daemon@googlemail.com>", "Delivery Status Notification (Failure)",
                      "Your message wasn't delivered to gone@dead.example because the address couldn't be found")
        self.mail.add("Known Lead <known@lead.example>", "Question", "I want a refund for the last job")
        self.mail.add("Stranger <s@random.example>", "Refund now!!", "send me a refund")
        self.mail.add("Me <owner@business.example>", "note to self", "")
        r = inboxwatch.check()
        got = {i["kind"]: i for i in attention.items("open", 50)}
        self.assertEqual(got["lead.reply"]["level"], "important")
        self.assertTrue(got["lead.reply"]["title"].startswith("Reply from Sam Client"))
        self.assertTrue(guard.blocked("pat@customer.example"))                        # STOP by email opts out
        self.assertEqual(got["contact.opted_out"]["level"], "routine")
        self.assertEqual(got["email.automated"]["level"], "background")
        self.assertEqual(got["send.bounced"]["level"], "important")
        self.assertEqual(got["customer.message"]["level"], "important")              # known person + "refund"
        self.assertEqual(got["email.unknown"]["level"], "important")                 # stranger's "refund": digest only
        self.assertEqual(got["email.unknown"]["category"], "unknown_sender")
        self.assertEqual(r["new"], 6)                                                 # own mail skipped
        bounced = [a for a in approvals.items("executed") if a["payload"].get("to") == "gone@dead.example"][0]
        self.assertEqual(outcomes.state(bounced["id"])["post"], "mismatch")          # it did not arrive
        self.assertNotEqual(outcomes.state(it["id"])["post"], "mismatch")            # Sam's mail did not bounce
        for i in attention.items("open", 50):
            self.assertTrue(i["source"].startswith("external:email"))

    def test_strangers_never_trip_an_away_alert(self):
        inboxwatch.check()
        m = mandate.draft("Away", time.time() + 86400, will=[], now=time.time())
        mandate.activate(m["id"], by="owner")
        self.mail.add("Stranger <s@random.example>", "angry complaint", "I am furious, refund me")
        inboxwatch.check()
        item = [i for i in attention.items("open") if i["kind"] == "email.unknown"][0]
        self.assertNotEqual(item["interrupt"], "queued")

    def test_briefing_counts_customer_mail_and_bounces(self):
        inboxwatch.check()
        guard.record_send("email", "sam@client.example", "followup")
        self.mail.add("Sam <sam@client.example>", "Re: hi", "sounds good")
        inboxwatch.check()
        b = briefing.morning(health=False)
        self.assertEqual(b["sections"]["happened"]["customer_emails"], 1)
        self.assertIn("1 email from customers", b["text"])

    def test_a_broken_inbox_is_reported(self):
        def boom(aid, n=25):
            raise ConnectionError("imap down")
        email_tools.inbox = boom
        r = inboxwatch.check()
        self.assertEqual(r["new"], 0)
        self.assertTrue(r["errors"])


if __name__ == "__main__":
    unittest.main()
