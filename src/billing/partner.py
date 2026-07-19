"""
PROGRAM AGEN & AFILIASI [B21] F1 — mesin komisi (SPEC = AGENT_AND_AFILIATION_ARCITECTURE.md).

SATU otoritas seluruh hitungan uang program partner (dipanggil midtrans._apply_settlement,
endpoint mv-webhook, dan job bulanan). Prinsip §3 SPEC: buku besar APPEND-ONLY (koreksi = baris
reversal, nilai tak pernah di-UPDATE) · rate di-SNAPSHOT per baris · gagal = raise (pemanggil
yang memutuskan alarm; HARAM menebak diam-diam).

Aturan uang terkunci (§2 SPEC, ketok owner 2026-07-17):
  1. flat_idr = per BULAN-LANGGANAN yang dibayar (order tahunan period_months=12 → ×12).
  2. percent  = dari rupiah yang BENAR-BENAR masuk (gross settlement, sudah net-diskon).
  3. Refund pasca-bayar = pengurang pencairan berikutnya; pra-bayar = saling meniadakan.
  Pembulatan: rupiah penuh terdekat, half-up (§5g.5).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


# ── util config (app_config: angka di `value`, teks di `value_text`) ─────────────────────────
def _cfg_int(sb, key: str, default: int) -> int:
    try:
        r = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        return int(r.data[0]["value"]) if r.data else default
    except Exception:
        return default


def _cfg_text(sb, key: str, default: str) -> str:
    try:
        r = sb.table("app_config").select("value_text").eq("key", key).limit(1).execute()
        v = (r.data[0].get("value_text") if r.data else None)
        return v if v not in (None, "") else default
    except Exception:
        return default


def _round_idr(x) -> int:
    """Rupiah penuh terdekat, half-up (SPEC §5g.5)."""
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_commission(rate_type: str, rate_value, gross_idr, months_paid: int) -> int:
    """Nilai komisi satu pembayaran. flat_idr=per bulan-langganan ×months; percent=dari gross."""
    v = Decimal(str(rate_value or 0))
    if v <= 0:
        return 0
    if rate_type == "flat_idr":
        return _round_idr(v * int(months_paid or 1))
    if rate_type == "percent":
        return _round_idr(Decimal(str(gross_idr or 0)) * v / Decimal(100))
    raise ValueError(f"rate_type tak dikenal: {rate_type!r}")


def _period_month(paid_at_iso: str | None) -> str:
    """Periode = bulan kalender menurut tanggal settlement tercatat (SPEC §5g.4)."""
    if paid_at_iso:
        try:
            d = datetime.fromisoformat(str(paid_at_iso).replace("Z", "+00:00"))
            return f"{d.year:04d}-{d.month:02d}-01"
        except ValueError:
            pass  # format tak terduga → fallback bulan berjalan (di bawah)
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}-01"


# ── ACCRUAL: pembayaran settlement → baris buku besar (dipanggil _apply_settlement) ──────────
def record_settlement_commission(sb, order: dict, paid_at_iso: str | None = None) -> dict | None:
    """Tulis komisi utk 1 order settlement. None = order bukan objek komisi (bukan langganan /
    tanpa atribusi). Raise = data rusak (agen atribusi hilang) — pemanggil wajib alarm admin.
    Idempotent 2 lapis: klaim-optimistik pemanggil + unique(order_id, entry_kind) DB."""
    if (order.get("category") or "subscription") != "subscription":
        return None  # SPEC §5g.10: HANYA pembayaran langganan plan yang berkomisi
    att = (sb.table("tenant_attribution").select("*")
           .eq("tenant_id", order["tenant_id"]).limit(1).execute().data or [None])[0]
    if not att:
        return None  # tanpa kode saat daftar = bukan bawaan siapa pun (SPEC §1b)

    ag = (sb.table("agents").select("id,status,commission_type,commission_value,user_id")
          .eq("id", att["agent_id"]).limit(1).execute().data or [None])[0]
    if not ag:
        raise RuntimeError(f"atribusi tenant {order['tenant_id']} menunjuk agen {att['agent_id']} yang TIDAK ADA")
    # Agen suspended: default K4 SPEC §8 = komisi tenant lama TETAP dihitung (atribusi & ledger sah);
    # pembekuan = keputusan owner per-kasus di gerbang pencairan.
    gross = int(order.get("gross_amount") or 0)
    months = int(order.get("period_months") or 1)
    agent_amount = compute_commission(ag["commission_type"], ag["commission_value"], gross, months)
    # [B21 fix 2026-07-19] Anti-komisi-diri (§5g.9/§6 SPEC — dulu hanya tertulis, TAK ditegakkan
    # di kode): pembayar = pemilik login agen → komisi agen 0 (tak berkomisi atas langganan sendiri).
    # Baris ledger tetap lahir (jejak audit); hanya nominalnya yang dinolkan.
    if ag.get("user_id") and str(ag["user_id"]) == str(order["tenant_id"]):
        logger.warning(f"[Partner] SELF-REFERRAL agen terdeteksi order={order['order_id']} — komisi agen di-nol-kan (§5g.9)")
        agent_amount = 0

    r_type = r_value = None
    r_amount = 0
    if att.get("reseller_id"):
        rs = (sb.table("resellers").select("id,commission_type,commission_value,user_id")
              .eq("id", att["reseller_id"]).limit(1).execute().data or [None])[0]
        if rs:  # nilai INFORMASI utk agen (kewajiban agen, bukan kami — SPEC §1a)
            r_type, r_value = rs["commission_type"], rs["commission_value"]
            r_amount = compute_commission(r_type, r_value, gross, months)
            # [B21 fix 2026-07-19] Anti-komisi-diri reseller: pembayar = pemilik login reseller
            # → jatah reseller 0 (komisi agen atas transaksi ini TETAP — keputusan teknis
            # reversible: agen tak bersalah atas self-referral reseller-nya).
            if rs.get("user_id") and str(rs["user_id"]) == str(order["tenant_id"]):
                logger.warning(f"[Partner] SELF-REFERRAL reseller terdeteksi order={order['order_id']} — jatah reseller di-nol-kan")
                r_amount = 0

    row = {
        "order_id": order["order_id"], "tenant_id": order["tenant_id"],
        "agent_id": att["agent_id"], "reseller_id": att.get("reseller_id"),
        "gross_idr": gross, "months_paid": months,
        "agent_rate_type": ag["commission_type"], "agent_rate_value": float(ag["commission_value"]),
        "agent_amount_idr": agent_amount,
        "reseller_rate_type": r_type,
        "reseller_rate_value": (float(r_value) if r_value is not None else None),
        "reseller_amount_idr": r_amount,
        "entry_kind": "accrual", "status": "accrued",
        "period_month": _period_month(paid_at_iso or order.get("paid_at")),
    }
    try:
        ins = sb.table("commission_ledger").insert(row).execute()
        logger.info(f"[Partner] komisi lahir order={order['order_id']} agen={att['agent_id']} Rp{agent_amount}")
        # [F4] kabar gembira ke agen (fail-soft — uang sudah tercatat di atas)
        notify_agent(sb, att["agent_id"],
                     f"🤝💸 Komisi baru {_idr(agent_amount)} — pelanggan bawaan Anda baru saja membayar"
                     f"{' (tahunan ×' + str(months) + ' bln)' if months > 1 else ''}."
                     f"{' Jatah reseller: ' + _idr(r_amount) + '.' if r_amount else ''} Detail: mesinviral.com/agent")
        return {"ok": True, "ledger_id": ins.data[0]["id"], "agent_amount_idr": agent_amount}
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            logger.info(f"[Partner] accrual order={order['order_id']} sudah ada — lewati (idempotent)")
            return {"ok": True, "skipped": "duplicate"}
        raise


# ── REVERSAL: refund/chargeback → baris minus (SPEC §2.3 / §5e) ──────────────────────────────
def record_refund_reversal(sb, order: dict) -> dict | None:
    """Refund order → baris reversal. Belum dibayar: keduanya 'reversed' (saling meniadakan).
    Sudah dibayar: reversal tinggal 'accrued' minus → pengurang pencairan berikutnya."""
    acc = (sb.table("commission_ledger").select("*")
           .eq("order_id", order["order_id"]).eq("entry_kind", "accrual").limit(1).execute().data or [None])[0]
    if not acc:
        return None  # tak pernah berkomisi (mis. tanpa atribusi) → tak ada yang ditarik
    dup = (sb.table("commission_ledger").select("id")
           .eq("order_id", order["order_id"]).eq("entry_kind", "reversal").limit(1).execute().data)
    if dup:
        return {"ok": True, "skipped": "reversal_exists"}

    # [AUDIT 2026-07-17 T-1] 'approved' diperlakukan seperti 'paid': baris sudah DIKUNCI ke payout
    # (mark_paid menimpa status by payout_id) → reversal WAJIB tinggal 'accrued' sebagai pengurang
    # bulan berikut. Dulu hanya 'paid' → refund di jendela approve→paid membuat tarik-balik HANGUS.
    already_paid = acc["status"] in ("paid", "approved")
    rev_status = "accrued" if already_paid else "reversed"
    rev = {k: acc[k] for k in ("order_id", "tenant_id", "agent_id", "reseller_id", "gross_idr",
                               "months_paid", "agent_rate_type", "agent_rate_value",
                               "reseller_rate_type", "reseller_rate_value", "period_month")}
    rev.update({
        "agent_amount_idr": -int(acc["agent_amount_idr"]),
        "reseller_amount_idr": -int(acc["reseller_amount_idr"]),
        "entry_kind": "reversal", "reversal_of": acc["id"], "status": rev_status,
    })
    ins = sb.table("commission_ledger").insert(rev).execute()
    if not already_paid:
        sb.table("commission_ledger").update({"status": "reversed"}).eq("id", acc["id"]).execute()
    logger.info(f"[Partner] reversal order={order['order_id']} (accrual {'SUDAH' if already_paid else 'belum'} dibayar)")
    return {"ok": True, "ledger_id": ins.data[0]["id"], "deduct_next_payout": already_paid}


# ── PENCAIRAN BULANAN (draft → approve → paid; gerbang owner — SPEC §1d/5c) ──────────────────
def _tax_pct(sb, tax_status: str) -> Decimal:
    return Decimal(_cfg_text(sb, f"partner_tax_pct_{tax_status}", "0"))


def _select_payable(sb, agent_id: str, period_month: str) -> tuple[list, list]:
    """Baris yang masuk pencairan: accrual 'accrued' periode itu + SEMUA reversal 'accrued'
    (pengurang menggantung, periode berapa pun — SPEC §2.3)."""
    accs = (sb.table("commission_ledger").select("id,agent_amount_idr")
            .eq("agent_id", agent_id).eq("entry_kind", "accrual").eq("status", "accrued")
            .eq("period_month", period_month).execute().data or [])
    revs = (sb.table("commission_ledger").select("id,agent_amount_idr")
            .eq("agent_id", agent_id).eq("entry_kind", "reversal").eq("status", "accrued")
            .execute().data or [])
    return accs, revs


def build_monthly_payouts(sb, period_month: str) -> dict:
    """Susun/segarkan DRAFT tagihan per agen utk 1 periode ('YYYY-MM-01'). Di bawah ambang →
    digulung (baris tetap accrued). Draft yang sudah approved/paid TIDAK disentuh."""
    min_idr = _cfg_int(sb, "partner_min_payout_idr", 0)
    agents = sb.table("agents").select("id,company_name,tax_status").execute().data or []
    built, skipped = [], []
    for ag in agents:
        accs, revs = _select_payable(sb, ag["id"], period_month)
        gross = sum(int(a["agent_amount_idr"]) for a in accs)
        deduction = -sum(int(r["agent_amount_idr"]) for r in revs)  # reversal minus → angka positif
        if gross == 0 and deduction == 0:
            continue
        net_pre_tax = gross - deduction
        if net_pre_tax < min_idr:
            skipped.append({"agent_id": ag["id"], "net": net_pre_tax, "reason": "di_bawah_ambang"})
            continue
        tax = _round_idr(Decimal(net_pre_tax) * _tax_pct(sb, ag["tax_status"]) / Decimal(100))
        existing = (sb.table("agent_payouts").select("id,status").eq("agent_id", ag["id"])
                    .eq("period_month", period_month).limit(1).execute().data or [None])[0]
        vals = {"gross_commission_idr": gross, "deduction_idr": deduction,
                "tax_withheld_idr": tax, "net_paid_idr": net_pre_tax - tax,
                "updated_at": datetime.now(timezone.utc).isoformat()}
        if existing:
            if existing["status"] != "draft":
                skipped.append({"agent_id": ag["id"], "reason": f"sudah_{existing['status']}"})
                continue
            sb.table("agent_payouts").update(vals).eq("id", existing["id"]).execute()
            pid = existing["id"]
        else:
            ins = sb.table("agent_payouts").insert({"agent_id": ag["id"], "period_month": period_month,
                                                    "status": "draft", **vals}).execute()
            pid = ins.data[0]["id"]
        built.append({"payout_id": pid, "agent": ag["company_name"], "gross": gross,
                      "deduction": deduction, "tax": tax, "net": net_pre_tax - tax})
    return {"period": period_month, "built": built, "skipped": skipped}


def approve_payout(sb, payout_id: str, tax_override_idr: int | None = None) -> dict:
    """Owner menyetujui draft: baris ledger terkait DIKUNCI (approved + payout_id) dan angka payout
    dibekukan dari baris yang dikunci (satu sumber). Pajak boleh dikoreksi owner saat approve."""
    po = (sb.table("agent_payouts").select("*").eq("id", payout_id).limit(1).execute().data or [None])[0]
    if not po:
        raise ValueError("payout tidak ditemukan")
    if po["status"] != "draft":
        raise ValueError(f"payout berstatus {po['status']} — hanya draft yang bisa disetujui")
    accs, revs = _select_payable(sb, po["agent_id"], po["period_month"])
    ids = [r["id"] for r in accs + revs]
    if not ids:
        raise ValueError("tidak ada baris komisi tersisa utk payout ini (sudah berubah?) — susun ulang draft")
    gross = sum(int(a["agent_amount_idr"]) for a in accs)
    deduction = -sum(int(r["agent_amount_idr"]) for r in revs)
    net_pre_tax = gross - deduction
    ag = (sb.table("agents").select("tax_status").eq("id", po["agent_id"]).limit(1).execute().data)[0]
    tax = int(tax_override_idr) if tax_override_idr is not None else \
        _round_idr(Decimal(net_pre_tax) * _tax_pct(sb, ag["tax_status"]) / Decimal(100))
    now = datetime.now(timezone.utc).isoformat()
    for _id in ids:  # status = workflow (bukan nilai) — append-only tetap terjaga
        sb.table("commission_ledger").update({"status": "approved", "payout_id": payout_id}).eq("id", _id).execute()
    sb.table("agent_payouts").update({
        "gross_commission_idr": gross, "deduction_idr": deduction, "tax_withheld_idr": tax,
        "net_paid_idr": net_pre_tax - tax, "status": "approved", "approved_at": now, "updated_at": now,
    }).eq("id", payout_id).execute()
    return {"ok": True, "rows_locked": len(ids), "net_paid_idr": net_pre_tax - tax}


def mark_payout_paid(sb, payout_id: str, transfer_ref: str = "") -> dict:
    """Owner mencatat bukti transfer → payout & seluruh baris terkuncinya = paid."""
    po = (sb.table("agent_payouts").select("id,status").eq("id", payout_id).limit(1).execute().data or [None])[0]
    if not po:
        raise ValueError("payout tidak ditemukan")
    if po["status"] != "approved":
        raise ValueError(f"payout berstatus {po['status']} — hanya approved yang bisa ditandai dibayar")
    now = datetime.now(timezone.utc).isoformat()
    sb.table("commission_ledger").update({"status": "paid"}).eq("payout_id", payout_id).execute()
    sb.table("agent_payouts").update({"status": "paid", "paid_at": now,
                                      "transfer_ref": transfer_ref or None, "updated_at": now}
                                     ).eq("id", payout_id).execute()
    # [F4] kabar cair ke agen (fail-soft; angka dari baris payout yang barusan dikunci)
    po2 = (sb.table("agent_payouts").select("agent_id,period_month,net_paid_idr").eq("id", payout_id)
           .limit(1).execute().data or [None])[0]
    if po2:
        notify_agent(sb, po2["agent_id"],
                     f"🤝✅ Komisi periode {str(po2['period_month'])[:7]} sebesar {_idr(po2['net_paid_idr'] or 0)} "
                     f"sudah DITRANSFER{(' (ref ' + transfer_ref + ')') if transfer_ref else ''}. Terima kasih!")
    return {"ok": True}


# ── REKENING AGEN (nomor terenkripsi Fernet — pola vault; SPEC §4/§6) ────────────────────────
def set_agent_bank(sb, agent_id: str, bank_name: str, account_no: str, holder: str) -> dict:
    from src.utils.crypto import encrypt
    if not (bank_name and account_no and holder):
        raise ValueError("bank_name, account_no, holder wajib diisi")
    sb.table("agents").update({
        "bank_name": bank_name.strip(), "bank_account_enc": encrypt(account_no.strip()),
        "bank_holder": holder.strip(), "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", agent_id).execute()
    return {"ok": True}


def reveal_agent_bank(sb, agent_id: str) -> dict:
    """Buka nomor rekening (dipakai owner saat transfer) — hanya via endpoint ber-guard."""
    from src.utils.crypto import decrypt
    ag = (sb.table("agents").select("bank_name,bank_account_enc,bank_holder")
          .eq("id", agent_id).limit(1).execute().data or [None])[0]
    if not ag:
        raise ValueError("agen tidak ditemukan")
    return {"bank_name": ag.get("bank_name"), "bank_holder": ag.get("bank_holder"),
            "account_no": (decrypt(ag["bank_account_enc"]) if ag.get("bank_account_enc") else None)}


# ── [F3] RESELLER: rekening terenkripsi + hitungan bulanan utk Excel agen (SPEC 5d) ──────────
def set_reseller_bank(sb, reseller_id: str, bank_name: str, account_no: str, holder: str) -> dict:
    from src.utils.crypto import encrypt
    if not (bank_name and account_no and holder):
        raise ValueError("bank_name, account_no, holder wajib diisi")
    sb.table("resellers").update({
        "bank_name": bank_name.strip(), "bank_account_enc": encrypt(account_no.strip()),
        "bank_holder": holder.strip(), "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", reseller_id).execute()
    return {"ok": True}


def reseller_monthly_breakdown(sb, agent_id: str, period_month: str, include_bank: bool = False) -> dict:
    """Rincian komisi PER-RESELLER satu agen utk 1 periode ('YYYY-MM-01') — dasar Excel
    transfer-massal (SPEC 5d; kewajiban bayar = agen). Angka = Σ reseller_amount_idr baris
    accrual + reversal periode tsb (refund otomatis mengurangi). include_bank=True membuka
    nomor rekening (HANYA utk export ber-guard)."""
    from src.utils.crypto import decrypt
    rs_rows = (sb.table("resellers")
               .select("id,name,email,status,commission_type,commission_value,bank_name,bank_account_enc,bank_holder")
               .eq("agent_id", agent_id).execute().data or [])
    led = (sb.table("commission_ledger")
           .select("reseller_id,reseller_amount_idr,entry_kind")
           .eq("agent_id", agent_id).eq("period_month", period_month)
           .not_.is_("reseller_id", "null").execute().data or [])
    agg: dict[str, dict] = {}
    for row in led:
        a = agg.setdefault(row["reseller_id"], {"total": 0, "n_payment": 0, "n_refund": 0})
        a["total"] += int(row["reseller_amount_idr"])
        a["n_payment" if row["entry_kind"] == "accrual" else "n_refund"] += 1
    out = []
    for r in rs_rows:
        s = agg.get(r["id"], {"total": 0, "n_payment": 0, "n_refund": 0})
        item = {"reseller_id": r["id"], "name": r["name"], "email": r["email"], "status": r["status"],
                "commission_type": r["commission_type"], "commission_value": float(r["commission_value"]),
                "total_idr": s["total"], "n_payment": s["n_payment"], "n_refund": s["n_refund"],
                "bank_name": r.get("bank_name"), "bank_holder": r.get("bank_holder"),
                "bank_account_set": bool(r.get("bank_account_enc"))}
        if include_bank and r.get("bank_account_enc"):
            item["account_no"] = decrypt(r["bank_account_enc"])
        out.append(item)
    out.sort(key=lambda x: -x["total_idr"])
    return {"period": period_month, "rows": out}


# ── [F4] NOTIFIKASI TELEGRAM AGEN (mekanisme chat 1-klik yang sama dgn tenant — ketok owner) ──
def notify_agent(sb, agent_id: str, text: str) -> bool:
    """Kirim teks ke chat Telegram AGEN (agents.telegram_chat_id). Fail-soft total —
    notifikasi TIDAK BOLEH mengganggu jalur uang; belum terhubung → False."""
    try:
        ag = (sb.table("agents").select("telegram_chat_id").eq("id", agent_id).limit(1).execute().data or [None])[0]
        chat = (ag or {}).get("telegram_chat_id")
        if not chat:
            return False
        from src.utils.telegram_notifier import TelegramNotifier
        n = TelegramNotifier()
        return n._send(str(chat), n._escape(text))
    except Exception as e:
        logger.warning(f"[Partner] notify_agent gagal (non-fatal): {e}")
        return False


def _idr(n) -> str:
    return f"Rp {int(n):,}".replace(",", ".")


# ── [F4] PENGINGAT PENCAIRAN ke OWNER (sekali per periode, marker persisten anti-spam) ───────
_REMINDER_KEY = "ops_partner_reminder_last"


def maybe_send_payout_reminder(sb) -> dict:
    """Dipanggil dari loop periodik worker: bila hari ini ≥ partner_payout_day dan pengingat
    periode ini belum terkirim dan ADA komisi accrued → Telegram admin. Fail-soft."""
    try:
        from datetime import date
        today = date.today()
        day = _cfg_int(sb, "partner_payout_day", 5)
        if today.day < day:
            return {"skipped": "belum_tanggalnya"}
        marker = f"{today.year:04d}-{today.month:02d}"
        r = sb.table("app_config").select("value_text").eq("key", _REMINDER_KEY).limit(1).execute()
        if r.data and (r.data[0].get("value_text") or "") == marker:
            return {"skipped": "sudah_dikirim"}
        # periode yang ditagih = bulan SEBELUMNYA (SPEC §5g.4)
        pm = date(today.year - (1 if today.month == 1 else 0), 12 if today.month == 1 else today.month - 1, 1)
        period = pm.isoformat()
        accrued = (sb.table("commission_ledger").select("agent_amount_idr")
                   .eq("entry_kind", "accrual").eq("status", "accrued").eq("period_month", period)
                   .execute().data or [])
        if not accrued:
            # tak ada tagihan → tandai periode ini selesai tanpa kirim (jangan cek terus tiap loop)
            sb.table("app_config").upsert({"key": _REMINDER_KEY, "value": 0, "value_text": marker,
                                           "description": "Program Agen: penanda pengingat pencairan terakhir (otomatis)"}).execute()
            return {"skipped": "nol_komisi"}
        total = sum(int(x["agent_amount_idr"]) for x in accrued)
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_admin(
            f"🤝💰 Pengingat pencairan komisi agen: periode {period[:7]} punya {len(accrued)} komisi "
            f"menunggu (± {_idr(total)}). Buka Admin → Program Agen → Susun draft → setujui → transfer.")
        sb.table("app_config").upsert({"key": _REMINDER_KEY, "value": 0, "value_text": marker,
                                       "description": "Program Agen: penanda pengingat pencairan terakhir (otomatis)"}).execute()
        return {"sent": True, "period": period, "total": total}
    except Exception as e:
        logger.warning(f"[Partner] pengingat pencairan gagal (non-fatal): {e}")
        return {"error": str(e)}
