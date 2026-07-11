"use client";

import { useState, useEffect } from "react";
import { Sparkles } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { InsightsView, type Insights, type LearnedWeights } from "@/components/insights-view";
import { LearningCurveCard } from "@/components/learning-curve-card";
import { PageHeader } from "@/components/page-header";

// D21 Self-Learning Insights — F2-13: AGREGAT semua channel via RPC get_tenant_insights_agg.
// Render = komponen bersama <InsightsView> (dipakai juga di tab Channel Detail per-channel).
// Formula adaptif (S3-A) = tenant_configs.viral_score_weights (tenant-wide, RLS).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

export default function InsightsPage() {
  const supabase = createClient();
  const [ins, setIns] = useState<Insights | null>(null);
  const [learned, setLearned] = useState<LearnedWeights>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.rpc("get_tenant_insights_agg")
      .then(({ data }) => { const i = data as Insights | null; if (i && (i.channels_count ?? 0) > 0) setIns(i); setLoading(false); });
    supabase.from("tenant_configs").select("viral_score_weights").maybeSingle()
      .then(({ data }) => { const w = (data as { viral_score_weights?: LearnedWeights } | null)?.viral_score_weights; if (w && w.weights) setLearned(w); });
  }, [supabase]);

  return (
    <>
      <PageHeader icon={Sparkles} title="Self-Learning Insights" subtitle={<Bi id="Apa yang mesin pelajari dari semua channelmu" en="What the engine learned across all your channels" />} />
      <InsightsView insights={ins} loading={loading} scopeLabel={{ id: "semua channel", en: "all your channels" }} learnedWeights={learned}
        curveSlot={<LearningCurveCard scopeLabel={{ id: "semua channel-mu", en: "all your channels" }} />} />
    </>
  );
}
