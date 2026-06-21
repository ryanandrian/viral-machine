"use client";

import { useState, useEffect } from "react";
import { Sparkles } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { InsightsView, type Insights } from "@/components/insights-view";

// D21 Self-Learning Insights — F2-13: AGREGAT semua channel via RPC get_tenant_insights_agg.
// Render = komponen bersama <InsightsView> (dipakai juga di tab Channel Detail per-channel).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

export default function InsightsPage() {
  const supabase = createClient();
  const [ins, setIns] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.rpc("get_tenant_insights_agg")
      .then(({ data }) => { const i = data as Insights | null; if (i && (i.channels_count ?? 0) > 0) setIns(i); setLoading(false); });
  }, [supabase]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1><Sparkles size={26} style={{ color: "var(--accent)" }} /> Self-Learning Insights</h1>
          <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Apa yang mesin pelajari dari semua channelmu" en="What the engine learned across all your channels" /></div>
        </div>
      </div>
      <InsightsView insights={ins} loading={loading} scopeLabel={{ id: "semua channel", en: "all your channels" }} />
    </>
  );
}
