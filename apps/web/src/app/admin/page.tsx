import { redirect } from "next/navigation";

// /admin → redirect ke screen admin default.
export default function AdminIndex() {
  redirect("/admin/tenants");
}
