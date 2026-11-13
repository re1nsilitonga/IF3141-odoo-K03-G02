from unittest.mock import patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import tagged

from .common import HizwellPoSuratCommon


@tagged("post_install", "-at_install")
class TestPo(HizwellPoSuratCommon):
    def _buat_po(self, user=None, **extra):
        vals = {
            "pesanan_id": self.pesanan.id,
            "incoterm": "fob",
            "baris_ids": [
                (0, 0, {"nama_barang": "Bearing", "part_number": "BR-01", "jumlah": 3, "harga_satuan": 100.0}),
                (0, 0, {"nama_barang": "Seal", "jumlah": 2, "harga_satuan": 25.5}),
            ],
            **extra,
        }
        return self.env["hizwell.po"].with_user(user or self.dirut).create(vals)

    def _jumlah_lampiran(self, po):
        return self.env["ir.attachment"].search_count([("res_model", "=", "hizwell.po"), ("res_id", "=", po.id)])

    def test_nomor_vendor_dan_total(self):
        po = self._buat_po(uang_muka_persen=30)
        self.assertTrue(po.nomor_dokumen.startswith("PO/"))
        self.assertEqual(po.vendor_id, self.vendor)
        self.assertIn("Shanghai", po.alamat_vendor)
        self.assertAlmostEqual(po.total, 3 * 100.0 + 2 * 25.5)
        self.assertAlmostEqual(po.uang_muka_nominal, 351.0 * 0.3)
        self.assertEqual(po.state, "draft")

    def test_terbitkan_menyimpan_pdf(self):
        po = self._buat_po()
        po.action_terbitkan()
        self.assertEqual(po.state, "terbit")
        self.assertTrue(po.tanggal_terbit)
        self.assertTrue(po.pdf_id.name.endswith(".pdf"))
        self.assertEqual(self._jumlah_lampiran(po), 1)

    def test_terbit_tidak_bisa_diubah(self):
        po = self._buat_po()
        po.action_terbitkan()
        with self.assertRaises(UserError):
            po.write({"incoterm": "cif"})
        with self.assertRaises(UserError):
            po.baris_ids[0].write({"jumlah": 9})
        with self.assertRaises(UserError):
            po.baris_ids[0].unlink()
        with self.assertRaises(UserError):
            po.unlink()

    def test_gagal_lalu_diulang_tanpa_dokumen_ganda(self):
        po = self._buat_po()
        with patch.object(
            self.registry["ir.actions.report"], "_render_qweb_pdf",
            side_effect=RuntimeError("wkhtmltopdf tidak tersedia"),
        ):
            po.action_terbitkan()
        self.assertEqual(po.state, "gagal")
        self.assertIn("wkhtmltopdf", po.pesan_galat)
        self.assertEqual(len(po.baris_ids), 2)  # data isian tetap tersimpan
        po.action_ulangi()
        self.assertEqual(po.state, "draft")
        po.action_terbitkan()
        self.assertEqual(po.state, "terbit")
        self.assertEqual(self._jumlah_lampiran(po), 1)

    def test_tanpa_barang_menjadi_gagal(self):
        po = self.env["hizwell.po"].with_user(self.dirut).create({"pesanan_id": self.pesanan.id, "incoterm": "exw"})
        po.action_terbitkan()
        self.assertEqual(po.state, "gagal")

    def test_revisi_mengarsipkan_versi_lama(self):
        po = self._buat_po()
        po.action_terbitkan()
        with self.assertRaises(UserError):
            po.buat_revisi("  ")
        baru = po.buat_revisi("Harga berubah sesuai quotation baru")
        self.assertEqual(po.state, "arsip")
        self.assertTrue(po.pdf_id)  # versi lama tidak dihapus
        self.assertEqual(baru.state, "draft")
        self.assertEqual(baru.no_revisi, 1)
        self.assertEqual(baru.kode_revisi, "Rev01")
        self.assertEqual(baru.nomor_dokumen, po.nomor_dokumen)
        self.assertEqual(len(baru.baris_ids), 2)
        self.assertAlmostEqual(baru.total, po.total)
        self.assertEqual(baru.riwayat_ids, po)
        baru.action_terbitkan()
        self.assertNotEqual(baru.pdf_id, po.pdf_id)
        self.assertIn("Rev01", baru.pdf_id.name)

    def test_revisi_lewat_wizard(self):
        po = self._buat_po()
        po.action_terbitkan()
        aksi = po.action_buka_wizard_revisi()
        self.assertEqual(aksi["res_model"], "hizwell.revisi.wizard")
        wizard = self.env["hizwell.revisi.wizard"].with_user(self.dirut).create(
            {"res_model": "hizwell.po", "res_id": po.id, "alasan": "Jumlah barang bertambah"}
        )
        hasil = wizard.action_buat()
        self.assertEqual(self.env["hizwell.po"].browse(hasil["res_id"]).no_revisi, 1)

    def test_validasi_baris_dan_uang_muka(self):
        with self.assertRaises(ValidationError):
            self._buat_po(baris_ids=[(0, 0, {"nama_barang": "X", "jumlah": 0, "harga_satuan": 1})])
        with self.assertRaises(ValidationError):
            self._buat_po(uang_muka_persen=120)

    def test_hanya_direktur_utama_membuat_po(self):
        self._akses(self.admin, "ubah", pesanan=self.pesanan)
        with self.assertRaises(AccessError):
            self._buat_po(user=self.admin)

    def test_po_mengikuti_hak_akses_pesanan(self):
        po = self._buat_po()
        with self.assertRaises(AccessError):
            po.with_user(self.sales).read(["nomor_dokumen"])
        self._akses(self.dirwil, "lihat", pesanan=self.pesanan)
        po_dirwil = po.with_user(self.dirwil)
        self.assertEqual(po_dirwil.nomor_dokumen, po.nomor_dokumen)
        with self.assertRaises(AccessError):
            po_dirwil.write({"incoterm": "cif"})

    def test_duplikat_mendapat_nomor_baru(self):
        po = self._buat_po()
        salinan = po.copy()
        self.assertNotEqual(salinan.nomor_dokumen, po.nomor_dokumen)
        self.assertEqual(len(salinan.baris_ids), 2)
