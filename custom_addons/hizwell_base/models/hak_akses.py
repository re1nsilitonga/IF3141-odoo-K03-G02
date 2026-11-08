from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

JABATAN = [
    ("direktur_utama", "Direktur Utama"),
    ("direktur_wilayah", "Direktur Wilayah"),
    ("staf_administrasi", "Staf Administrasi"),
    ("staf_sales", "Staf Sales dan Marketing"),
]
GROUP_JABATAN = [
    ("hizwell_base.group_direktur_utama", "direktur_utama"),
    ("hizwell_base.group_direktur_wilayah", "direktur_wilayah"),
    ("hizwell_base.group_staf_administrasi", "staf_administrasi"),
    ("hizwell_base.group_staf_sales", "staf_sales"),
]


class HizwellHakAkses(models.Model):
    _name = "hizwell.hak.akses"
    _description = "Aturan Hak Akses Dokumen"
    _order = "user_id, id"

    user_id = fields.Many2one("res.users", string="Akun Pengguna", required=True, ondelete="cascade")
    jabatan = fields.Selection(JABATAN, compute="_compute_jabatan")
    proyek_id = fields.Many2one("hizwell.proyek", string="Proyek", ondelete="cascade", index=True)
    pesanan_id = fields.Many2one("hizwell.pesanan", string="Pesanan", ondelete="cascade", index=True)
    tingkat_akses = fields.Selection(
        [("lihat", "Melihat"), ("ubah", "Mengubah")],
        string="Tingkat Akses", required=True, default="lihat",
    )

    _sql_constraints = [
        ("user_proyek_uniq", "unique(user_id, proyek_id)", "Pengguna sudah punya hak akses pada proyek ini."),
        ("user_pesanan_uniq", "unique(user_id, pesanan_id)", "Pengguna sudah punya hak akses pada pesanan ini."),
    ]

    @api.depends("user_id")
    def _compute_jabatan(self):
        for rec in self:
            rec.jabatan = rec.user_id._hizwell_jabatan() if rec.user_id else False

    @api.constrains("proyek_id", "pesanan_id")
    def _check_satu_objek(self):
        for rec in self:
            if bool(rec.proyek_id) == bool(rec.pesanan_id):
                raise ValidationError(_("Hak akses harus untuk tepat satu proyek atau satu pesanan."))


class ResUsers(models.Model):
    _inherit = "res.users"

    def _hizwell_jabatan(self):
        self.ensure_one()
        for xmlid, kode in GROUP_JABATAN:
            if self.has_group(xmlid):
                return kode
        return False