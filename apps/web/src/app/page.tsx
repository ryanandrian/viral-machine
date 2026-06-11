import { redirect } from "next/navigation";

// Root → dashboard (sementara). Nanti: landing publik di mesinviral.com,
// app di app.mesinviral.com (route group (app)).
export default function Home() {
  redirect("/dashboard");
}
