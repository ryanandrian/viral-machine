"""
Test Telegram Notifier — s81
Jalankan dari root folder: python3.11 scripts/test_telegram.py

Test semua 3 tipe notifikasi (success, qc_fail, failure).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.utils.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()

print("=" * 50)
print("TEST TELEGRAM NOTIFIER — MesinViral.com")
print("=" * 50)

# ── Test 1: SUCCESS ─────────────────────────────────
print("\n[1/3] Kirim notifikasi SUCCESS...")
fake_result = {
    "run_id":    "ryan_andrian_test_001",
    "tenant_id": "ryan_andrian",
    "niche":     "universe_mysteries",
    "elapsed_seconds": 735.9,
    "steps": {
        "hook":    {"score": 92, "hook": "Dark matter makes up 85% of the universe"},
        "script":  {"title": "Dark Matter: The Invisible Force Shaping Reality"},
        "tts":     {"timestamps": 216},
        "visuals": {"clips": 6},
        "qc":      {"passed": True, "duration": 111.87, "size_mb": 55.6},
    },
    "published": {
        "youtube": {
            "video_id": "dQw4w9WgXcQ",
            "url":      "https://youtu.be/dQw4w9WgXcQ",
            "title":    "Dark Matter: The Invisible Force Shaping Reality",
        }
    },
}

class FakeConfig:
    channel_name    = "RAD The Explorer"
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_enabled = True

ok1 = notifier.notify_success(fake_result, run_config=FakeConfig())
print(f"   Result: {'✅ OK' if ok1 else '❌ GAGAL'}")

# ── Test 2: QC FAIL ──────────────────────────────────
print("\n[2/3] Kirim notifikasi QC FAIL...")
ok2 = notifier.notify_qc_fail(
    run_id        = "ryan_andrian_test_002",
    tenant_id     = "ryan_andrian",
    topic         = "The Mystery of Dark Energy Explained",
    qc_reason     = "Durasi terlalu pendek: 38.2s < 45s",
    duration_secs = 38.2,
    size_mb       = 12.5,
    run_config    = FakeConfig(),
)
print(f"   Result: {'✅ OK' if ok2 else '❌ GAGAL'}")

# ── Test 3: PIPELINE FAILURE ─────────────────────────
print("\n[3/3] Kirim notifikasi PIPELINE FAILURE...")
ok3 = notifier.notify_failure(
    run_id          = "ryan_andrian_test_003",
    tenant_id       = "ryan_andrian",
    niche           = "universe_mysteries",
    error           = "ElevenLabs API timeout after 3 retries: ConnectTimeout(HTTPSConnectionPool)",
    elapsed_seconds = 245.0,
    run_config      = FakeConfig(),
)
print(f"   Result: {'✅ OK' if ok3 else '❌ GAGAL'}")

print("\n" + "=" * 50)
passed = sum([ok1, ok2, ok3])
print(f"HASIL: {passed}/3 notifikasi terkirim")
if passed == 3:
    print("✅ Semua notifikasi berhasil! Cek Telegram Anda.")
else:
    print("⚠️  Ada yang gagal. Cek TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di .env")
print("=" * 50)
