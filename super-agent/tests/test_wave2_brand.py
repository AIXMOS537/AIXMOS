"""
Brand Profile tests: what a reply may claim, how it should sound, and the check before anything goes out.
    python -m unittest tests.test_wave2_brand -v
"""
import os, sys, shutil, tempfile, unittest

TMP = tempfile.mkdtemp(prefix="aixmos-brand-")
os.environ["AIXMOS_MEMDIR"] = os.path.join(TMP, "memory")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "vendor")]

from aixmos import settings, skills, brand  # noqa: E402

assert os.path.abspath(settings.MEMDIR).startswith(os.path.abspath(tempfile.gettempdir())), "tests must never touch the real memory folder"


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


PROFILE = {"name": "Shine Mobile Detailing", "services": "Interior detail, exterior wash, ceramic coating",
           "pricing": "Interior detail $129. Exterior wash $59.", "hours": "Mon-Sat 8-6", "area": "Austin",
           "policies": "A $25 deposit holds the booking; free cancellation up to 24 hours before.",
           "voice": "Warm, short, plain words. First name basis.",
           "preferred_phrases": "Happy to help!\nSee you soon", "prohibited_claims": "best in town\nlifetime warranty",
           "examples": "Hi Jo! Happy to help. We can come Saturday morning, does 9 work?\n\n"
                       "Hey Sam, thanks for the photos of the seats. The interior detail would sort that out.",
           "booking_link": "https://book.example.test/shine"}


class Brand(unittest.TestCase):
    def setUp(self):
        skills.save_profile({k: "" for k in skills.PROFILE_FIELDS})

    def test_missing_fields_are_asked_not_guessed(self):
        self.assertEqual(brand.missing(), list(brand.KEY_FIELDS))
        skills.save_profile(PROFILE)
        self.assertEqual(brand.missing(), [])

    def test_facts_hold_only_what_the_owner_wrote(self):
        skills.save_profile(PROFILE)
        f = brand.facts_text()
        self.assertIn("$129", f); self.assertIn("deposit", f); self.assertIn("book.example.test", f)
        self.assertNotIn("best in town", f)                       # never-say lines are not facts

    def test_reply_check(self):
        skills.save_profile(PROFILE)
        ok, probs, notes = brand.check_reply("Hi Jo! The interior detail is $129 and the deposit is $25.")
        self.assertTrue(ok, probs)
        self.assertTrue(notes)                                     # prices still flagged for the owner's eye
        ok, probs, _ = brand.check_reply("We are the best in town and every job has a guarantee.")
        self.assertFalse(ok)
        self.assertTrue(any("best in town" in p for p in probs))
        self.assertTrue(any("guarantee" in p for p in probs))
        skills.save_profile({"pricing": "", "policies": ""})
        ok, probs, _ = brand.check_reply("The interior detail is $129.")
        self.assertFalse(ok)                                       # price removed from the profile -> invented

    def test_no_promised_times_or_deliveries(self):
        skills.save_profile(PROFILE)
        for bad in ("Hi Sam, yes! We're available next Tuesday afternoon.", "I'll send over a quick overview by end of day.",
                    "See you tomorrow at 3pm!"):
            ok, probs, _ = brand.check_reply(bad)
            self.assertFalse(ok, bad)
            self.assertTrue(any("promises a time" in p for p in probs))
        self.assertTrue(brand.check_reply("What day works best for you? Book here: https://book.example.test/shine")[0])

    def test_only_verified_calendar_slots_may_be_offered(self):
        skills.save_profile(PROFILE)
        slots = [{"text": "Tue 13 Oct 9:00"}, {"text": "Wed 14 Oct 14:30"}]
        ok, probs, _ = brand.check_reply("Hi Jo! We're available Tue 13 Oct 9:00 or Wednesday, 14 October at 14:30.", slots=slots)
        self.assertTrue(ok, probs)
        ok, probs, _ = brand.check_reply("Hi Jo! How about Thu 15 Oct 10:00?", slots=slots)
        self.assertFalse(ok)
        self.assertTrue(any("not a free slot" in p for p in probs))
        ok, probs, _ = brand.check_reply("Hi Jo! How about Tue 13 Oct 9:00?")      # no calendar -> every time is invented
        self.assertFalse(ok)

    def test_voice_brief_uses_the_owners_examples_within_budget(self):
        skills.save_profile(PROFILE)
        v = brand.voice_brief("customer sent photos of stained seats")
        self.assertIn("Warm, short", v); self.assertIn("Never say: best in town", v)
        self.assertLess(v.index("photos of the seats"), v.index("Saturday morning") if "Saturday morning" in v else 10**6)
        self.assertLessEqual(len(brand.voice_brief("x", budget=120)), 120)


if __name__ == "__main__":
    unittest.main()
