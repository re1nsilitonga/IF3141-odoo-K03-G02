import base64

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestDokumen(TransactionCase):
    def setUp(self):
        super().setUp()
        self.du = self.env.ref("base.user_admin")
        self.sales = self.env["res.users"].with_user(self.du).create({
            "name": "Uji Dokumen Sales", "login": "uji_dokumen_sales",
            "groups_id": [(6, 0, [self.env.ref("hizwell_base.group_staf_sales").id])],
        })
        partner = self.env["res.partner"].create({"name": "Pelanggan Uji Dokumen"})
        self.proyek = self.env["hizwell.proyek"].with_user(self.du).create({
            "name": "Proyek Uji", "pelanggan_id": partner.id,
        })
        self.pesanan = self.env["hizwell.pesanan"].with_user(self.du).create({
            "pelanggan_id": partner.id, "proyek_id": self.proyek.id,
        })
        self.tender = self.env.ref("hizwell_dokumen.jenis_tender")
        self.oa = self.env.ref("hizwell_dokumen.jenis_oa")
        self.pdf = base64.b64encode(b"%PDF-1.4\n%%EOF")

    def _vals(self, **extra):
        vals = {"name": "Tender", "nama_berkas": "tender.pdf", "berkas": self.pdf,
                "jenis_dokumen_id": self.tender.id, "proyek_id": self.proyek.id}
        vals.update(extra)
        return vals

    def test_unggah_dan_cari(self):
        model = self.env["hizwell.dokumen"].with_user(self.du)
        proyek_doc = model.create(self._vals())
        pesanan_doc = model.create(self._vals(proyek_id=False, pesanan_id=self.pesanan.id,
                                                jenis_dokumen_id=self.oa.id, name="OA"))
        self.assertEqual(proyek_doc.proyek_id, self.proyek)
        self.assertEqual(pesanan_doc.pesanan_id, self.pesanan)
        self.assertIn(proyek_doc, model.search([("nama_berkas", "ilike", "tender")]))
        self.assertIn(proyek_doc, model.search([("proyek_id.kode", "=", self.proyek.kode)]))
        self.assertIn(pesanan_doc, model.search([("pesanan_id.name", "=", self.pesanan.name)]))

    def test_satu_induk_dan_jenis(self):
        model = self.env["hizwell.dokumen"].with_user(self.du)
        with self.assertRaises(ValidationError):
            model.create(self._vals(proyek_id=False))
        with self.assertRaises(ValidationError):
            model.create(self._vals(pesanan_id=self.pesanan.id))
        with self.assertRaises(ValidationError):
            model.create(self._vals(jenis_dokumen_id=self.oa.id))

    def test_akses_pengguna(self):
        model = self.env["hizwell.dokumen"]
        doc = model.with_user(self.du).create(self._vals())
        with self.assertRaises(AccessError):
            doc.with_user(self.sales).read(["name"])
        self.env["hizwell.hak.akses"].with_user(self.du).create({
            "user_id": self.sales.id, "proyek_id": self.proyek.id, "tingkat_akses": "lihat",
        })
        self.assertEqual(doc.with_user(self.sales).name, "Tender")
        with self.assertRaises(AccessError):
            doc.with_user(self.sales).write({"name": "Ubah tanpa izin"})
        with self.assertRaises(AccessError):
            model.with_user(self.sales).create(self._vals())
        self.assertEqual(doc.with_user(self.du).name, "Tender")
