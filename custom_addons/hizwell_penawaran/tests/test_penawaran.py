from . import test_penawaran
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPenawaran(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        Users = cls.env["res.users"].with_context(no_reset_password=True)

        def user(login, group):
            return Users.create({"name": login, "login": login, "groups_id": [(6, 0, [ref(group).id])]})

        cls.sales = user("p_sales", "hizwell_base.group_staf_sales")
        cls.admin = user("p_admin", "hizwell_base.group_staf_administrasi")
        cls.dirwil = user("p_dirwil", "hizwell_base.group_direktur_wilayah")
        cls.dirut = user("p_dirut", "hizwell_base.group_direktur_utama")
        kai = cls.env["res.partner"].create({"name": "PT KAI", "is_company": True})
        cls.proyek = cls.env["hizwell.proyek"].create({
            "name": "Tender Sparepart", "pelanggan_id": kai.id,
            "nomor_tender": "TDR-001", "tanggal_tender": "2026-11-01",
        })
        cls.env["hizwell.hak.akses"].create([
            {"user_id": cls.sales.id, "proyek_id": cls.proyek.id, "tingkat_akses": "ubah"},
            {"user_id": cls.dirwil.id, "proyek_id": cls.proyek.id, "tingkat_akses": "lihat"},
        ])
        cls.templat = cls.env.ref("hizwell_penawaran.templat_penawaran_standar")

    def _setujui_templat(self):
        self.templat.with_user(self.admin).action_ajukan()
        self.templat.with_user(self.dirwil).action_setujui()

    def _penawaran(self, **extra):
        vals = {
            "proyek_id": self.proyek.id,
            "templat_id": self.templat.id,
            "line_ids": [
                (0, 0, {"nama_barang": "Brake Pad", "part_number": "BP-01", "jumlah": 4, "harga_satuan": 1500000}),
                (0, 0, {"nama_barang": "Coupler", "part_number": "CP-02", "jumlah": 2, "harga_satuan": 250000.5}),
            ],
        }
        vals.update(extra)
        return self.env["hizwell.penawaran"].with_user(self.sales).create(vals)

    # FR-09
    def test_templat_hanya_disetujui_dirwil(self):
        self.templat.with_user(self.admin).action_ajukan()
        with self.assertRaises(AccessError):
            self.templat.with_user(self.sales).action_setujui()
        with self.assertRaises(AccessError):
            self.templat.with_user(self.admin).action_setujui()
        self.templat.with_user(self.dirwil).action_setujui()
        self.assertEqual(self.templat.state, "disetujui")

    def test_minta_revisi_wajib_catatan(self):
        self.templat.with_user(self.admin).action_ajukan()
        with self.assertRaises(UserError):
            self.templat.with_user(self.dirwil).action_minta_revisi()
        self.templat.catatan_persetujuan = "Tambahkan masa berlaku"
        self.templat.with_user(self.dirwil).action_minta_revisi()
        self.assertEqual(self.templat.state, "revisi")

    def test_ubah_isi_membatalkan_persetujuan(self):
        self._setujui_templat()
        self.templat.write({"kalimat_penutup": "Terima kasih."})
        self.assertEqual(self.templat.state, "draft")
        self.assertFalse(self.templat.disetujui_oleh)

    def test_penawaran_dari_templat_belum_disetujui_gagal(self):
        pnw = self._penawaran()
        pnw.with_user(self.sales).action_terbitkan()
        self.assertEqual(pnw.state, "gagal")
        self.assertTrue(pnw.pesan_galat)
        pnw.with_user(self.sales).action_ulangi()
        self.assertEqual(pnw.state, "draft")

    # FR-03
    def test_nomor_dan_total(self):
        pnw = self._penawaran()
        self.assertTrue(pnw.nomor_dokumen.startswith("PNW/"))
        self.assertAlmostEqual(pnw.total_harga, 4 * 1500000 + 2 * 250000.5)

    def test_terbitkan_menghasilkan_lampiran(self):
        self._setujui_templat()
        pnw = self._penawaran()
        pnw.with_user(self.sales).action_terbitkan()
        self.assertEqual(pnw.state, "terbit", pnw.pesan_galat)
        self.assertTrue(pnw.lampiran_id)
        self.assertEqual(self.env["ir.attachment"].search_count(
            [("res_model", "=", "hizwell.penawaran"), ("res_id", "=", pnw.id)]), 1)

    def test_dokumen_terbit_terkunci(self):
        self._setujui_templat()
        pnw = self._penawaran()
        pnw.with_user(self.sales).action_terbitkan()
        with self.assertRaises(UserError):
            pnw.with_user(self.sales).write({"tanggal_penawaran": "2026-12-01"})
        with self.assertRaises(UserError):
            pnw.line_ids[0].with_user(self.sales).write({"jumlah": 9})

    def test_revisi(self):
        self._setujui_templat()
        pnw = self._penawaran()
        pnw.with_user(self.sales).action_terbitkan()
        baru = pnw.with_user(self.sales).buat_revisi("Harga berubah")
        self.assertEqual(pnw.state, "arsip")
        self.assertEqual(baru.state, "draft")
        self.assertEqual(baru.kode_revisi, "Rev01")
        self.assertEqual(baru.nomor_dokumen, pnw.nomor_dokumen)
        self.assertEqual(len(baru.line_ids), 2)
        self.assertFalse(baru.lampiran_id)

    def test_revisi_setelah_terkirim_butuh_persetujuan_dirwil(self):
        self._setujui_templat()
        pnw = self._penawaran()
        pnw.with_user(self.sales).action_terbitkan()
        pnw.with_user(self.sales).action_tandai_terkirim()
        baru = pnw.with_user(self.sales).buat_revisi("Klarifikasi pelanggan")
        self.assertTrue(baru.perlu_persetujuan_revisi)
        baru.with_user(self.sales).action_terbitkan()
        with self.assertRaises(UserError):
            baru.with_user(self.sales).action_tandai_terkirim()
        with self.assertRaises(AccessError):
            baru.with_user(self.sales).action_setujui_revisi()
        baru.with_user(self.dirwil).action_setujui_revisi()
        baru.with_user(self.sales).action_tandai_terkirim()
        self.assertTrue(baru.tanggal_kirim)

    def test_hak_akses_proyek(self):
        pnw = self._penawaran()
        with self.assertRaises(AccessError):
            pnw.with_user(self.admin).read(["nomor_dokumen"])
        self.assertEqual(pnw.with_user(self.dirwil).nomor_dokumen, pnw.nomor_dokumen)
        with self.assertRaises(AccessError):
            self.env["hizwell.penawaran"].with_user(self.dirwil).create({
                "proyek_id": self.proyek.id, "templat_id": self.templat.id,
            })
