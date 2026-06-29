"use client";

import { useState, useEffect } from "react";
import { ShieldCheck } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { ComplianceView, type Compliance } from "@/components/compliance-view";
import { PageHeader } from "@/components/page-header";

// D20 Compliance — F2-13: AGREGAT semua channel via RPC get_tenant_compliance_agg (bukan limit(1)).
// Render = komponen bersama <ComplianceView> (dipakai juga di tab Channel Detail per-channel).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

export default function CompliancePage() {
  const supabase = createClient();
  const [cmp, setCmp] = useState<Compliance | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasRow, setHasRow] = useState(false);

  useEffect(() => {
    supabase.rpc("get_tenant_compliance_agg")
      .then(({ data }) => { const c = data as Compliance | null; if (c && (c.channels_count ?? 0) > 0) { setCmp(c); setHasRow(true); } setLoading(false); });
  }, [supabase]);

  return (
    <>
      <PageHeader icon={ShieldCheck} title="Compliance Score" subtitle={<Bi id="AI Slop Defense · rata-rata semua channel" en="AI Slop Defense · averaged across all channels" />} />
      <ComplianceView compliance={cmp} loading={loading} hasRow={hasRow} />
    </>
  );
}
