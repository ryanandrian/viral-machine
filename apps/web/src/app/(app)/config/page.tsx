import { redirect } from "next/navigation";

// /config (bare) → redirect ke tab default. Screen sesungguhnya di /config/[tab].
// Path-based routing sinkron dgn sidebar AppShell (href /config/<id>) + active-state pathname.
export default function ConfigIndex() {
  redirect("/config/ai-engines");
}
