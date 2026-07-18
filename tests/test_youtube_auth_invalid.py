"""
Uji regresi PERMANEN — [B11] 3.2: koneksi YouTube putus (OAuth invalid_grant) → GAGAL JUJUR,
bukan gagal-senyap. Hermetik (nol DB / nol jaringan): semua I/O di-mock.

Jalankan:  python -m unittest tests.test_youtube_auth_invalid    (dari root repo)
       atau python tests/test_youtube_auth_invalid.py

Yang dijaga (regresi bila salah satu berubah):
  A. Taksonomi   — AUTH_INVALID ADA di FAST_FAIL (ketok owner 2026-07-18 "rem segera").
  B. mark_invalid — flip valid→invalid SEKALI (idempoten) + notif tenant SEKALI pada transisi.
  C. publisher._get_credentials — invalid_grant → PublishError(AUTH_INVALID) + tandai invalid;
     RefreshError LAIN (transien) → re-raise apa adanya, TIDAK menandai invalid (anti asumsi liar).
  D. Propagasi seam — dict {status:failed, error_class:auth_invalid} → PublishError(AUTH_INVALID)
     (bukan RuntimeError generik yang membuang makna).
"""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

# root repo di sys.path (agar `import src...` jalan saat dipanggil langsung)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.exceptions import RefreshError
from src.exceptions import PipelineError, PublishError, ErrorClass, FAST_FAIL


# ─────────────────────────── Fake Supabase (chainable) ───────────────────────────
class _Chain:
    def __init__(self, fake):
        self.f = fake
        self._upd = None

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def update(self, upd):
        self._upd = upd
        self.f.updates.append(upd)
        return self

    def execute(self):
        if self._upd is not None:
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=self.f.select_data)


class _FakeSB:
    def __init__(self, select_data):
        self.select_data = select_data
        self.updates = []

    def table(self, name):
        return _Chain(self)


# ─────────────────────────────── A. Taksonomi ────────────────────────────────
class TestTaxonomy(unittest.TestCase):
    def test_auth_invalid_in_fast_fail(self):
        # Ketok owner 2026-07-18: koneksi mati permanen = rem segera. Jangan pernah dicabut diam-diam.
        self.assertIn(ErrorClass.AUTH_INVALID, FAST_FAIL)

    def test_billing_quota_still_fast_fail(self):
        # Regresi [B22]: jangan sampai penambahan AUTH menggeser dua kelas lama.
        self.assertIn(ErrorClass.ACCOUNT_BILLING, FAST_FAIL)
        self.assertIn(ErrorClass.QUOTA_EXHAUSTED, FAST_FAIL)

    def test_transient_not_fast_fail(self):
        self.assertNotIn(ErrorClass.TRANSIENT, FAST_FAIL)
        self.assertNotIn(ErrorClass.UNKNOWN, FAST_FAIL)


# ────────────────────── B. mark_youtube_account_invalid ──────────────────────
class TestMarkInvalid(unittest.TestCase):
    def _run(self, current_status):
        import src.utils.tenant_credentials as tc
        fake = _FakeSB(select_data=[{"status": current_status,
                                     "yt_channel_title": "RAD The Explorer", "label": "acc-1"}])
        notified = []
        with mock.patch.object(tc, "_sb", return_value=fake), \
             mock.patch.object(tc, "_account_id_for", return_value="acc-1"), \
             mock.patch.object(tc, "_notify_youtube_invalid",
                               side_effect=lambda *a, **k: notified.append(a)):
            result = tc.mark_youtube_account_invalid("tenant-1", "chan-1", reason="invalid_grant: revoked")
        return result, fake, notified

    def test_transition_valid_to_invalid_flips_and_notifies_once(self):
        result, fake, notified = self._run("valid")
        self.assertTrue(result, "transisi valid→invalid harus return True")
        self.assertEqual(len(fake.updates), 1, "harus tepat 1 update DB")
        self.assertEqual(fake.updates[0].get("status"), "invalid")
        self.assertEqual(len(notified), 1, "notif tenant harus dikirim TEPAT sekali")

    def test_idempotent_already_invalid_no_flip_no_notify(self):
        result, fake, notified = self._run("invalid")
        self.assertFalse(result, "status sudah invalid → no-op, return False")
        self.assertEqual(len(fake.updates), 0, "tidak ada update ulang")
        self.assertEqual(len(notified), 0, "TIDAK boleh notif berulang (anti-spam)")

    def test_no_account_returns_false(self):
        import src.utils.tenant_credentials as tc
        with mock.patch.object(tc, "_sb", return_value=_FakeSB([])), \
             mock.patch.object(tc, "_account_id_for", return_value=None):
            self.assertFalse(tc.mark_youtube_account_invalid("t", "c"))


# ─────────────────── C. publisher._get_credentials (refresh) ───────────────────
class TestPublisherGetCredentials(unittest.TestCase):
    def _get_publisher_and_tc(self):
        from src.distribution.youtube_publisher import YouTubePublisher
        from src.intelligence.config import TenantConfig
        pub = YouTubePublisher()
        tc = TenantConfig(tenant_id="tenant-1", niche="space")
        tc.channel_name = "RAD The Explorer"
        tc.channel_id = "chan-1"
        return pub, tc

    def _fake_creds(self, refresh_exc):
        creds = mock.MagicMock()
        creds.expired = True
        creds.refresh_token = "rt"
        creds.token = "at"
        creds.refresh = mock.Mock(side_effect=refresh_exc)
        return creds

    def test_invalid_grant_raises_authinvalid_and_marks(self):
        import src.distribution.youtube_publisher as yp
        import src.utils.tenant_credentials as tc_mod
        pub, tc = self._get_publisher_and_tc()
        creds = self._fake_creds(RefreshError("invalid_grant: Token has been expired or revoked."))
        marked = []
        with mock.patch.object(yp, "Credentials", return_value=creds), \
             mock.patch.object(tc_mod, "load_google_credentials",
                               return_value={"token": "at", "refresh_token": "rt",
                                             "client_id": "c", "client_secret": "s", "scopes": []}), \
             mock.patch.object(tc_mod, "mark_youtube_account_invalid",
                               side_effect=lambda *a, **k: marked.append((a, k)) or True):
            with self.assertRaises(PublishError) as ctx:
                pub._get_credentials(tc)
        self.assertEqual(ctx.exception.error_class, ErrorClass.AUTH_INVALID)
        self.assertTrue(ctx.exception.human_message, "harus ada pesan manusiawi untuk tenant")
        self.assertIn("RAD The Explorer", ctx.exception.human_message)
        self.assertEqual(len(marked), 1, "koneksi harus ditandai invalid TEPAT sekali")

    def test_other_refresherror_reraised_not_marked(self):
        # REGRESI: RefreshError bukan-invalid_grant (mis. 5xx endpoint) = transien → JANGAN tandai
        # invalid, JANGAN jadi AUTH_INVALID. Re-raise apa adanya (perilaku lama, retryable).
        import src.distribution.youtube_publisher as yp
        import src.utils.tenant_credentials as tc_mod
        pub, tc = self._get_publisher_and_tc()
        creds = self._fake_creds(RefreshError("could not reach token endpoint (503)"))
        marked = []
        with mock.patch.object(yp, "Credentials", return_value=creds), \
             mock.patch.object(tc_mod, "load_google_credentials",
                               return_value={"token": "at", "refresh_token": "rt",
                                             "client_id": "c", "client_secret": "s", "scopes": []}), \
             mock.patch.object(tc_mod, "mark_youtube_account_invalid",
                               side_effect=lambda *a, **k: marked.append(1) or True):
            with self.assertRaises(RefreshError):
                pub._get_credentials(tc)
            # pastikan BUKAN PublishError yang bocor
            self.assertEqual(len(marked), 0, "RefreshError transien TIDAK boleh menandai invalid")


# ───────────────────── D. Propagasi seam _publish_from_buffer ─────────────────────
class TestPublishFromBufferPropagation(unittest.TestCase):
    def _call(self, yt_dict):
        import src.orchestrator.publisher as pub_mod
        fake_pub = mock.MagicMock()
        fake_pub.publish.return_value = yt_dict
        item = {"id": 1, "s3_key": "k.mp4", "niche": "space",
                "metadata": {"script": {}, "thumb_s3": None}}
        with mock.patch.object(pub_mod, "s3_buffer") as s3, \
             mock.patch("src.intelligence.config.tenant_config_from_channel",
                        return_value=SimpleNamespace(niche="space", channel_id="chan-1", tenant_id="t")), \
             mock.patch("src.distribution.youtube_publisher.YouTubePublisher", return_value=fake_pub):
            s3.download.return_value = None
            return pub_mod._publish_from_buffer(mock.MagicMock(), {"tenant_id": "t", "id": "chan-1"}, item)

    def test_authinvalid_class_propagates_through_dict(self):
        with self.assertRaises(PublishError) as ctx:
            self._call({"platform": "youtube", "status": "failed", "error": "invalid_grant",
                        "error_class": "auth_invalid", "human_error": "sambungkan ulang"})
        self.assertEqual(ctx.exception.error_class, ErrorClass.AUTH_INVALID)

    def test_generic_failure_defaults_unknown(self):
        # Kegagalan publish biasa (tanpa error_class) → UNKNOWN (perilaku lama; tetap PipelineError).
        with self.assertRaises(PublishError) as ctx:
            self._call({"platform": "youtube", "status": "failed", "error": "quota upload penuh"})
        self.assertEqual(ctx.exception.error_class, ErrorClass.UNKNOWN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
