from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from .common import HizwellPoSuratCommon


@tagged("post_install", "-at_install")
class TestSurat(HizwellPoSuratCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._akses(cls, cls.admin, "ubah", proyek=cls.proyek)

    def _buat_surat(self, user=None, **extra):
        return self.env["hizwell.surat"].with_user(user or self.admin).create({
            "proyek_id": self.proyek.id,
            "penerima_id": self.kai.id,
            "perihal": "Permohonan klarifikasi",
            "isi": "<p>Dengan hormat,</p>",
            **extra,
        })

    def test_nomor_otomatis_atau_diketik(self):
        otomatis = self._buat_surat()
        self.assertTrue(otomatis.nomor_dokumen.startswith("SRT/"))
        manual = self._buat_surat(nomor_dokumen="012/HSI/XI/2026")
        self.assertEqual(manual.nomor_dokumen, "012/HSI/XI/2026")
        self.assertIn("012-HSI-XI-2026", manual._hizwell_nama_berkas())

    def test_terbitkan_dan_kunci(self):
        surat = self._buat_surat()
        surat.action_terbitkan()
        self.assertEqual(surat.state, "terbit")
        self.assertTrue(surat.pdf_id)
        with self.assertRaises(UserError):
            surat.write({"perihal": "Diubah"})

    def test_revisi_surat(self):
        surat = self._buat_surat()
        surat.action_terbitkan()
        baru = surat.buat_revisi("Salah ketik nama penerima")
        self.assertEqual(surat.state, "arsip")
        self.assertEqual((baru.no_revisi, baru.state), (1, "draft"))
        self.assertEqual(baru.perihal, surat.perihal)

    def test_staf_sales_tidak_membuat_surat(self):
        self._akses(self.sales, "ubah", proyek=self.proyek)
        with self.assertRaises(AccessError):
            self._buat_surat(user=self.sales)

    def test_surat_mengikuti_hak_akses_proyek(self):
        surat = self._buat_surat()
        with self.assertRaises(AccessError):
            surat.with_user(self.sales).read(["perihal"])
        self._akses(self.dirwil, "lihat", proyek=self.proyek)
        self.assertEqual(surat.with_user(self.dirwil).perihal, "Permohonan klarifikasi")
        with self.assertRaises(AccessError):
            surat.with_user(self.dirwil).write({"perihal": "x"})

    def test_duplikat_mendapat_nomor_baru(self):
        surat = self._buat_surat()
        salinan = surat.copy()
        self.assertNotEqual(salinan.nomor_dokumen, surat.nomor_dokumen)
        self.assertEqual((salinan.no_revisi, salinan.state), (0, "draft"))
