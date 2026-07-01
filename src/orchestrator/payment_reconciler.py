"""Payment reconciler (Midtrans) — PENJAMIN pembayaran (PULL via API status).

Kenapa ada: akun Midtrans DIBAGI dgn app lain (aiwa) → notifikasi webhook (push) bisa dikirim ke URL
global app lain, TAK sampai ke kita. Reconciler menarik status transaksi langsung dari API Midtrans
untuk tiap `payments` yang masih 'pending' → terapkan settlement (jalur `_apply_settlement` yang SAMA
dgn webhook, anti-redundan). Jadi pembayaran PASTI tercatat walau notifikasi tak pernah datang.

service_role. Fail-soft: error per-baris/loop tak menghentikan thread. Dijalankan worker_decoupled
sebagai thread. Cadence: PAYMENT_RECONCILE_INTERVAL_SEC (default 120s).
"""

import os
import time

from loguru import logger


def run_forever(interval_seconds=None) -> None:
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    interval = int(interval_seconds or os.getenv("PAYMENT_RECONCILE_INTERVAL_SEC", "120"))
    logger.info(f"[PaymentReconcile] start | tiap {interval}s (pull status Midtrans utk payments pending)")
    while True:
        try:
            from src.billing.midtrans import reconcile_pending
            reconcile_pending(sb)
        except Exception as e:  # fire-and-forget: jangan pernah matikan loop
            logger.error(f"[PaymentReconcile] error: {e}")
        time.sleep(interval)
