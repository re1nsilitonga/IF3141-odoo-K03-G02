from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHakAkses(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        Users = cls.env["res.users"].with_context(no_reset_password=True)

        def user(login, group):
            return Users.create({"name": login, "login": login, "groups_id": [(6, 0, [ref(group).id])]})

        cls.sales = user("t_sales", "hizwell_base.group_staf_sales")
        cls.sales2 = user("t_sales2", "hizwell_base.group_staf_sales")
        cls.admin = user("t_admin", "hizwell_base.group_staf_administrasi")
        cls.dirwil = user("t_dirwil", "hizwell_base.group_direktur_wilayah")
        cls.dirut = user("t_dirut", "hizwell_base.group_direktur_utama")
        cls.kai = cls.env["res.partner"].create({"name": "PT KAI", "is_company": True})
        cls.proyek = cls.env["hizwell.proyek"].create({"name": "Tender A", "pelanggan_id": cls.kai.id})

    def _akses(self, user, tingkat, proyek=None, pesanan=None):
        return self.env["hizwell.hak.akses"].create({
            "user_id": user.id,
            "proyek_id": proyek and proyek.id,
            "pesanan_id": pesanan and pesanan.id,
            "tingkat_akses": tingkat,
        })

    def test_kode_otomatis(self):
        self.assertTrue(self.proyek.kode.startswith("PRJ/"))
        pesanan = self.env["hizwell.pesanan"].create({"pelanggan_id": self.kai.id})
        self.assertTrue(pesanan.name.startswith("PSN/"))

    def test_tanpa_akses_tidak_bisa_melihat(self):
        with self.assertRaises(AccessError):
            self.proyek.with_user(self.sales).read(["name"])
        self.assertFalse(self.env["hizwell.proyek"].with_user(self.sales).search([]))

    def test_akses_lihat_bisa_baca_tidak_bisa_ubah(self):
        self._akses(self.dirwil, "lihat", proyek=self.proyek)
        proyek = self.proyek.with_user(self.dirwil)
        self.assertEqual(proyek.name, "Tender A")
        self.assertFalse(proyek.bisa_ubah)
        with self.assertRaises(AccessError):
            proyek.write({"name": "Diubah"})

    def test_akses_ubah_bisa_mengubah(self):
        self._akses(self.sales, "ubah", proyek=self.proyek)
        proyek = self.proyek.with_user(self.sales)
        self.assertTrue(proyek.bisa_ubah)
        proyek.write({"nomor_tender": "TDR-01"})
        self.assertEqual(self.proyek.nomor_tender, "TDR-01")

    def test_pembuat_otomatis_dapat_akses_ubah(self):
        proyek = self.env["hizwell.proyek"].with_user(self.sales).create(
            {"name": "Tender Baru", "pelanggan_id": self.kai.id}
        )
        self.assertEqual(proyek.akses_ids.user_id, self.sales)
        self.assertEqual(proyek.akses_ids.tingkat_akses, "ubah")
        proyek.write({"nomor_tender": "X"})
        with self.assertRaises(AccessError):
            proyek.with_user(self.sales2).read(["name"])

    def test_staf_sales_tidak_bisa_membuat_pesanan(self):
        with self.assertRaises(AccessError):
            self.env["hizwell.pesanan"].with_user(self.sales).create({"pelanggan_id": self.kai.id})

    def test_staf_administrasi_membuat_pesanan(self):
        pesanan = self.env["hizwell.pesanan"].with_user(self.admin).create({"pelanggan_id": self.kai.id})
        self.assertEqual(pesanan.akses_ids.user_id, self.admin)

    def test_direktur_utama_melihat_semua(self):
        proyek = self.proyek.with_user(self.dirut)
        self.assertEqual(proyek.name, "Tender A")
        self.assertTrue(proyek.bisa_ubah)

    def test_hanya_direktur_utama_mengatur_hak_akses(self):
        self._akses(self.sales, "ubah", proyek=self.proyek)
        with self.assertRaises(AccessError):
            self.env["hizwell.hak.akses"].with_user(self.sales).create(
                {"user_id": self.sales2.id, "proyek_id": self.proyek.id}
            )
        baris = self.env["hizwell.hak.akses"].with_user(self.dirut).create(
            {"user_id": self.sales2.id, "proyek_id": self.proyek.id, "tingkat_akses": "lihat"}
        )
        self.assertEqual(baris.jabatan, "staf_sales")

    def test_pengguna_hanya_melihat_baris_aksesnya_sendiri(self):
        self._akses(self.sales, "ubah", proyek=self.proyek)
        self._akses(self.dirwil, "lihat", proyek=self.proyek)
        baris = self.env["hizwell.hak.akses"].with_user(self.sales).search([])
        self.assertEqual(baris.user_id, self.sales)

    def test_hak_akses_harus_satu_objek(self):
        pesanan = self.env["hizwell.pesanan"].create({"pelanggan_id": self.kai.id})
        with self.assertRaises(ValidationError):
            self._akses(self.sales, "lihat")
        with self.assertRaises(ValidationError):
            self._akses(self.sales, "lihat", proyek=self.proyek, pesanan=pesanan)

    def test_jabatan(self):
        self.assertEqual(self.dirut._hizwell_jabatan(), "direktur_utama")
        self.assertEqual(self.admin._hizwell_jabatan(), "staf_administrasi")