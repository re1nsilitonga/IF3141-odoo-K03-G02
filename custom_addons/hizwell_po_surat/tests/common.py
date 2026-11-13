from odoo.tests.common import TransactionCase


class HizwellPoSuratCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        Users = cls.env["res.users"].with_context(no_reset_password=True)

        def user(login, group):
            # email wajib: message_post (dipakai hizwell_base saat gagal/revisi) menolak pengguna tanpa email
            return Users.create({
                "name": login, "login": login, "email": f"{login}@example.com",
                "groups_id": [(6, 0, [ref(group).id])],
            })

        cls.sales = user("t_sales", "hizwell_base.group_staf_sales")
        cls.admin = user("t_admin", "hizwell_base.group_staf_administrasi")
        cls.dirwil = user("t_dirwil", "hizwell_base.group_direktur_wilayah")
        cls.dirut = user("t_dirut", "hizwell_base.group_direktur_utama")
        Partner = cls.env["res.partner"]
        cls.kai = Partner.create({"name": "PT KAI", "is_company": True})
        cls.vendor = Partner.create({
            "name": "Vendor Asia Ltd", "is_company": True,
            "street": "88 Nanjing Road", "city": "Shanghai",
        })
        cls.proyek = cls.env["hizwell.proyek"].create({"name": "Tender A", "pelanggan_id": cls.kai.id})
        cls.pesanan = cls.env["hizwell.pesanan"].create({
            "proyek_id": cls.proyek.id, "pelanggan_id": cls.kai.id, "vendor_id": cls.vendor.id,
        })

    def _akses(self, user, tingkat, proyek=None, pesanan=None):
        return self.env["hizwell.hak.akses"].create({
            "user_id": user.id,
            "proyek_id": proyek and proyek.id,
            "pesanan_id": pesanan and pesanan.id,
            "tingkat_akses": tingkat,
        })
