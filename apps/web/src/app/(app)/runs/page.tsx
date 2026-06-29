"use client";

import RunsTable from "@/components/runs-table";

// Menu utama Runs (SEMUA channel). Tabel = komponen bersama <RunsTable> (dipakai juga di
// channels/[id] tab "Runs" dengan channelId → scope channel). Satu sumber, nol duplikat.
export default function RunsListPage() {
  return <RunsTable />;
}
