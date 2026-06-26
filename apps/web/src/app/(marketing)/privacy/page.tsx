import "../about/about.css";

// B1 (GOOGLE_OAUTH_PLATFORM_MIGRATION.md §6/§7) — Kebijakan Privasi: URL sendiri /privacy (bukan tab JS),
// PATUH Google API Services User Data Policy + YouTube API Developer Policies (link wajib, Limited Use,
// revoke, hapus-data-7-hari). Server component (SEO) + bilingual via pola <Bi> data-id/data-en (toggle shell).

export const metadata = {
  title: "Kebijakan Privasi · MesinViral",
  description:
    "Bagaimana MesinViral mengumpulkan, menggunakan, menyimpan, dan melindungi data Anda — termasuk data Google/YouTube. Patuh Google API Services User Data Policy.",
};

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}
function Ext({ href, children }: { href: string; children: React.ReactNode }) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
}

export default function PrivacyPage() {
  return (
    <div className="mk-container">
      <div className="ab-hero">
        <h1 style={{ fontSize: "var(--text-4xl)" }}><Bi id="Kebijakan Privasi" en="Privacy Policy" /></h1>
        <p className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Berlaku 26 Juni 2026" en="Effective June 26, 2026" /></p>
      </div>

      <div className="ab-legal">
        <p>
          <Bi
            id="MesinViral (“kami”) adalah layanan produksi dan publikasi video pendek otomatis ke channel YouTube Anda, dioperasikan oleh Lumite. Kebijakan ini menjelaskan data apa yang kami kumpulkan, bagaimana kami menggunakannya, dan kendali yang Anda miliki. Untuk pertanyaan, hubungi "
            en="MesinViral (“we”) is a service that automatically produces and publishes short videos to your YouTube channel, operated by Lumite. This policy explains what data we collect, how we use it, and the controls you have. For questions, contact "
          />
          <Ext href="mailto:mesinviral@lumite.biz.id">mesinviral@lumite.biz.id</Ext>.
        </p>

        <h2><Bi id="1. Data yang kami kumpulkan" en="1. Data we collect" /></h2>
        <ul>
          <li><strong><Bi id="Informasi akun" en="Account information" /></strong> — <Bi id="email dan nama, dari pendaftaran atau saat Anda “Daftar dengan Google”." en="email and name, from sign-up or when you “Sign in with Google”." /></li>
          <li><strong><Bi id="Data channel YouTube yang Anda hubungkan" en="Data from the YouTube channels you connect" /></strong> — <Bi id="ID & info channel, daftar video, dan metrik performa (views, suka, komentar, retensi) yang diambil melalui YouTube Data API dan YouTube Analytics API." en="channel ID & info, your video list, and performance metrics (views, likes, comments, retention) retrieved via the YouTube Data API and YouTube Analytics API." /></li>
          <li><strong><Bi id="Token Google (OAuth)" en="Google tokens (OAuth)" /></strong> — <Bi id="refresh & access token untuk mengunggah video dan membaca analitik atas nama Anda. Disimpan terenkripsi." en="refresh & access tokens used to upload videos and read analytics on your behalf. Stored encrypted." /></li>
          <li><strong><Bi id="Kunci API penyedia AI Anda (BYOK)" en="Your AI provider API keys (BYOK)" /></strong> — <Bi id="kunci yang Anda masukkan sendiri, disimpan terenkripsi (Fernet AES-128) dan tidak pernah dicatat di log." en="keys you provide yourself, stored encrypted (Fernet AES-128) and never written to logs." /></li>
          <li><strong><Bi id="Data penggunaan" en="Usage data" /></strong> — <Bi id="log produksi, preferensi, dan metrik operasional untuk menjalankan dan meningkatkan layanan." en="production logs, preferences, and operational metrics to run and improve the service." /></li>
        </ul>

        <h2><Bi id="2. Bagaimana kami menggunakannya" en="2. How we use it" /></h2>
        <p>
          <Bi
            id="Data digunakan untuk: menjalankan produksi dan publikasi video ke channel YouTube Anda; menghasilkan insight self-learning per-channel dari analitik Anda; serta mengoperasikan, memelihara, dan meningkatkan layanan. Kami tidak menjual data Anda."
            en="We use data to: run the production and publishing of videos to your YouTube channel; generate per-channel self-learning insights from your analytics; and operate, maintain, and improve the service. We do not sell your data."
          />
        </p>

        <h2><Bi id="3. Penggunaan Terbatas data Google (Limited Use)" en="3. Limited Use of Google data" /></h2>
        <p>
          <Bi
            id="Penggunaan dan transfer informasi yang diterima MesinViral dari Google API mematuhi "
            en="MesinViral’s use and transfer of information received from Google APIs adheres to the "
          />
          <Ext href="https://developers.google.com/terms/api-services-user-data-policy"><Bi id="Google API Services User Data Policy" en="Google API Services User Data Policy" /></Ext>
          <Bi
            id=", termasuk persyaratan Limited Use. Data Google hanya kami gunakan untuk menyediakan dan meningkatkan fitur yang terlihat oleh Anda; tidak dijual; tidak digunakan untuk iklan; dan tidak ditransfer ke pihak lain kecuali sejauh diperlukan untuk menyediakan layanan, mematuhi hukum yang berlaku, atau dengan persetujuan Anda."
            en=", including the Limited Use requirements. We only use Google data to provide and improve user-facing features; we do not sell it; we do not use it for advertising; and we do not transfer it to others except as necessary to provide the service, comply with applicable law, or with your consent."
          />
        </p>

        <h2><Bi id="4. YouTube API Services" en="4. YouTube API Services" /></h2>
        <p>
          <Bi
            id="MesinViral menggunakan YouTube API Services. Dengan memakai fitur YouTube, Anda juga terikat pada "
            en="MesinViral uses YouTube API Services. By using the YouTube features, you are also bound by the "
          />
          <Ext href="https://www.youtube.com/t/terms"><Bi id="Persyaratan Layanan YouTube" en="YouTube Terms of Service" /></Ext>
          <Bi id=". Penanganan data Google juga tunduk pada " en=". Google’s handling of data is also governed by the " />
          <Ext href="https://policies.google.com/privacy"><Bi id="Kebijakan Privasi Google" en="Google Privacy Policy" /></Ext>.
        </p>

        <h2><Bi id="5. Penyimpanan & keamanan" en="5. Storage & security" /></h2>
        <p>
          <Bi
            id="Kunci API dan token OAuth Anda disimpan terenkripsi (Fernet AES-128 dengan HMAC). Kunci master enkripsi hanya berada di server dan tidak pernah dikirim ke browser maupun dicatat di log. Aset media disimpan di penyimpanan objek (S3) yang aman."
            en="Your API keys and OAuth tokens are stored encrypted (Fernet AES-128 with HMAC). The master encryption key resides only on the server and is never sent to the browser or written to logs. Media assets are stored in secure object storage (S3)."
          />
        </p>

        <h2><Bi id="6. Berbagi data & sub-prosesor" en="6. Data sharing & sub-processors" /></h2>
        <p><Bi id="Kami tidak menjual data Anda. Kami membagikan data hanya seperlunya untuk menjalankan layanan, kepada:" en="We do not sell your data. We share data only as needed to run the service, with:" /></p>
        <ul>
          <li><Bi id="Google / YouTube — untuk publikasi video dan analitik (atas instruksi Anda)." en="Google / YouTube — for publishing videos and analytics (at your direction)." /></li>
          <li><Bi id="Penyedia AI yang kuncinya Anda berikan (mis. OpenAI, ElevenLabs) — hanya saat Anda meminta produksi." en="AI providers whose keys you supply (e.g. OpenAI, ElevenLabs) — only when you request production." /></li>
          <li><Bi id="Penyedia infrastruktur (hosting, basis data, penyimpanan) dan gateway pembayaran." en="Infrastructure providers (hosting, database, storage) and the payment gateway." /></li>
        </ul>

        <h2><Bi id="7. Mencabut akses & menghapus data" en="7. Revoking access & deleting data" /></h2>
        <p>
          <Bi
            id="Anda dapat mencabut akses MesinViral ke Akun Google Anda kapan saja melalui halaman keamanan Google di "
            en="You can revoke MesinViral’s access to your Google Account at any time via the Google security page at "
          />
          <Ext href="https://myaccount.google.com/permissions">myaccount.google.com/permissions</Ext>
          <Bi
            id=", atau di dalam MesinViral dengan menghapus koneksi YouTube pada halaman Kredensial. Setelah akses dicabut, kami menghapus seluruh data yang diperoleh dari Google/YouTube API (Authorized Data) dalam waktu 7 hari kalender. Anda juga dapat mengekspor atau menghapus seluruh data akun Anda kapan saja melalui Pengaturan → Zona berbahaya."
            en=", or inside MesinViral by removing the YouTube connection on the Credentials page. After access is revoked, we delete all data obtained from the Google/YouTube APIs (Authorized Data) within 7 calendar days. You may also export or delete your entire account data anytime via Settings → Danger zone."
          />
        </p>

        <h2><Bi id="8. Hak Anda" en="8. Your rights" /></h2>
        <p><Bi id="Anda berhak mengakses, mengoreksi, mengekspor, dan menghapus data Anda. Hubungi kami untuk menggunakan hak-hak ini." en="You have the right to access, correct, export, and delete your data. Contact us to exercise these rights." /></p>

        <h2><Bi id="9. Anak-anak" en="9. Children" /></h2>
        <p><Bi id="Layanan tidak ditujukan untuk anak di bawah usia minimum yang disyaratkan hukum setempat, dan kami tidak dengan sengaja mengumpulkan data mereka." en="The service is not directed to children below the minimum age required by local law, and we do not knowingly collect their data." /></p>

        <h2><Bi id="10. Perubahan kebijakan" en="10. Changes to this policy" /></h2>
        <p><Bi id="Kami dapat memperbarui kebijakan ini dari waktu ke waktu. Perubahan material akan diberitahukan, dan tanggal berlaku di atas akan diperbarui." en="We may update this policy from time to time. Material changes will be notified, and the effective date above will be updated." /></p>

        <h2><Bi id="11. Kontak" en="11. Contact" /></h2>
        <p><Bi id="MesinViral (Lumite), Jakarta Selatan, Indonesia — " en="MesinViral (Lumite), South Jakarta, Indonesia — " /><Ext href="mailto:mesinviral@lumite.biz.id">mesinviral@lumite.biz.id</Ext>.</p>
      </div>
      <div style={{ height: "4rem" }} />
    </div>
  );
}
