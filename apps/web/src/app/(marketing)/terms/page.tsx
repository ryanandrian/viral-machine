import "../about/about.css";

// B2 (GOOGLE_OAUTH_PLATFORM_MIGRATION.md §6/§7) — Ketentuan Layanan: URL sendiri /terms. WAJIB memuat
// pernyataan pengguna terikat YouTube Terms of Service + link Google Privacy Policy (syarat YouTube API).
// Server component (SEO) + bilingual via pola <Bi> data-id/data-en (toggle shell).

export const metadata = {
  title: "Ketentuan Layanan · MesinViral",
  description:
    "Ketentuan penggunaan MesinViral — layanan produksi & publikasi video otomatis ke YouTube. Termasuk kepatuhan terhadap YouTube Terms of Service.",
};

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}
function Ext({ href, children }: { href: string; children: React.ReactNode }) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
}

export default function TermsPage() {
  return (
    <div className="mk-container">
      <div className="ab-hero">
        <h1 style={{ fontSize: "var(--text-4xl)" }}><Bi id="Ketentuan Layanan" en="Terms of Service" /></h1>
        <p className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Berlaku 26 Juni 2026" en="Effective June 26, 2026" /></p>
      </div>

      <div className="ab-legal">
        <h2><Bi id="1. Penerimaan ketentuan" en="1. Acceptance of terms" /></h2>
        <p>
          <Bi
            id="Dengan membuat akun atau menggunakan MesinViral (“Layanan”, dioperasikan oleh Lumite), Anda menyetujui Ketentuan ini. Jika Anda tidak setuju, jangan gunakan Layanan."
            en="By creating an account or using MesinViral (the “Service”, operated by Lumite), you agree to these Terms. If you do not agree, do not use the Service."
          />
        </p>

        <h2><Bi id="2. Layanan" en="2. The Service" /></h2>
        <p>
          <Bi
            id="MesinViral memproduksi video pendek dengan bantuan AI dan mempublikasikannya ke channel YouTube Anda, sesuai paket langganan Anda (jumlah channel dapat berbeda per paket). Layanan menggunakan model BYOK — Anda menyediakan kunci API penyedia AI Anda sendiri."
            en="MesinViral produces short videos with the help of AI and publishes them to your YouTube channel, according to your subscription plan (the number of channels may differ per plan). The Service uses a BYOK model — you provide your own AI provider API keys."
          />
        </p>

        <h2><Bi id="3. Akun & kelayakan" en="3. Account & eligibility" /></h2>
        <p>
          <Bi
            id="Anda wajib memberikan informasi yang akurat, menjaga keamanan akun Anda, dan bertanggung jawab atas seluruh aktivitas di akun Anda. Anda harus memenuhi usia minimum yang disyaratkan hukum setempat."
            en="You must provide accurate information, keep your account secure, and are responsible for all activity under your account. You must meet the minimum age required by local law."
          />
        </p>

        <h2><Bi id="4. YouTube" en="4. YouTube" /></h2>
        <p>
          <Bi
            id="Dengan menggunakan fitur YouTube pada Layanan, Anda setuju untuk terikat pada "
            en="By using the YouTube features of the Service, you agree to be bound by the "
          />
          <Ext href="https://www.youtube.com/t/terms"><Bi id="Persyaratan Layanan YouTube" en="YouTube Terms of Service" /></Ext>
          <Bi id=". Penanganan data Google tunduk pada " en=". Google’s handling of data is governed by the " />
          <Ext href="https://policies.google.com/privacy"><Bi id="Kebijakan Privasi Google" en="Google Privacy Policy" /></Ext>
          <Bi
            id=". Anda bertanggung jawab memastikan konten yang dipublikasikan ke channel Anda mematuhi Pedoman Komunitas dan kebijakan YouTube."
            en=". You are responsible for ensuring that content published to your channel complies with YouTube’s Community Guidelines and policies."
          />
        </p>

        <h2><Bi id="5. Kunci API & penyedia AI (BYOK)" en="5. API keys & AI providers (BYOK)" /></h2>
        <p>
          <Bi
            id="Anda menyediakan kunci API penyedia AI Anda sendiri. Biaya penggunaan AI ditagihkan oleh penyedia tersebut langsung kepada Anda; MesinViral tidak menambahkan markup tersembunyi. Anda bertanggung jawab atas kepatuhan dan biaya penyedia yang Anda gunakan."
            en="You provide your own AI provider API keys. AI usage costs are billed by those providers directly to you; MesinViral adds no hidden markup. You are responsible for the compliance and costs of the providers you use."
          />
        </p>

        <h2><Bi id="6. Konten Anda" en="6. Your content" /></h2>
        <p>
          <Bi
            id="Anda memiliki konten yang Anda hasilkan dan publikasikan. Anda memberi MesinViral lisensi terbatas untuk memproses dan mengunggah konten tersebut atas nama Anda guna menjalankan Layanan. Anda bertanggung jawab memastikan konten mematuhi hukum dan kebijakan platform tujuan."
            en="You own the content you generate and publish. You grant MesinViral a limited license to process and upload that content on your behalf to operate the Service. You are responsible for ensuring the content complies with applicable law and the policies of the destination platform."
          />
        </p>

        <h2><Bi id="7. Penggunaan yang dilarang" en="7. Prohibited use" /></h2>
        <p>
          <Bi
            id="Anda dilarang menggunakan Layanan untuk aktivitas melanggar hukum, spam, konten yang melanggar Pedoman Komunitas YouTube, pelanggaran hak kekayaan intelektual, atau upaya merusak, meretas, atau merekayasa-balik Layanan."
            en="You may not use the Service for unlawful activity, spam, content that violates YouTube’s Community Guidelines, intellectual-property infringement, or attempts to disrupt, hack, or reverse-engineer the Service."
          />
        </p>

        <h2><Bi id="8. Pembayaran & langganan" en="8. Payment & subscription" /></h2>
        <p>
          <Bi
            id="Layanan ditawarkan secara berlangganan. Biaya, siklus penagihan, dan pembatalan diatur pada halaman harga dan saat pembelian. Anda dapat membatalkan langganan kapan saja; akses berlanjut hingga akhir periode yang telah dibayar."
            en="The Service is offered on a subscription basis. Fees, billing cycles, and cancellation are described on the pricing page and at checkout. You may cancel anytime; access continues until the end of the paid period."
          />
        </p>

        <h2><Bi id="9. Penghentian" en="9. Termination" /></h2>
        <p>
          <Bi
            id="Kami dapat menangguhkan atau menghentikan akses jika terjadi pelanggaran Ketentuan ini. Anda dapat berhenti menggunakan Layanan dan menghapus akun kapan saja."
            en="We may suspend or terminate access in the event of a breach of these Terms. You may stop using the Service and delete your account at any time."
          />
        </p>

        <h2><Bi id="10. Penafian & batasan tanggung jawab" en="10. Disclaimer & limitation of liability" /></h2>
        <p>
          <Bi
            id="Layanan disediakan “sebagaimana adanya”. Kami tidak menjamin hasil tertentu (mis. jumlah penonton, viralitas, atau kelayakan monetisasi). Sejauh diizinkan hukum, tanggung jawab kami terbatas pada jumlah yang Anda bayarkan untuk Layanan dalam periode yang relevan."
            en="The Service is provided “as is”. We do not guarantee specific results (e.g. view counts, virality, or monetization eligibility). To the extent permitted by law, our liability is limited to the amount you paid for the Service in the relevant period."
          />
        </p>

        <h2><Bi id="11. Perubahan ketentuan" en="11. Changes to terms" /></h2>
        <p><Bi id="Kami dapat memperbarui Ketentuan ini; perubahan material akan diberitahukan dan tanggal berlaku diperbarui." en="We may update these Terms; material changes will be notified and the effective date updated." /></p>

        <h2><Bi id="12. Hukum yang berlaku" en="12. Governing law" /></h2>
        <p><Bi id="Ketentuan ini diatur oleh hukum Republik Indonesia." en="These Terms are governed by the laws of the Republic of Indonesia." /></p>

        <h2><Bi id="13. Kontak" en="13. Contact" /></h2>
        <p><Bi id="MesinViral (Lumite), Jakarta Selatan, Indonesia — " en="MesinViral (Lumite), South Jakarta, Indonesia — " /><Ext href="mailto:mesinviral@lumite.biz.id">mesinviral@lumite.biz.id</Ext>.</p>
      </div>
      <div style={{ height: "4rem" }} />
    </div>
  );
}
