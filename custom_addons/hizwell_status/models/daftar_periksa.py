from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class HizwellDaftarPeriksa(models.Model):
    _name = "hizwell.daftar.periksa"
    _description = "Daftar Periksa Kelengkapan Dokumen Tender"
    _rec_name = "proyek_id"

    proyek_id = fields.Many2one("hizwell.proyek", string="Proyek", required=True,
                                ondelete="cascade", index=True)
    state = fields.Selection([("draft", "Disusun"), ("diverifikasi", "Diverifikasi")],
                             string="Status", default="draft", readonly=True)
    diverifikasi_oleh = fields.Many2one("res.users", string="Diverifikasi Oleh", readonly=True)
    tanggal_verifikasi = fields.Date(string="Tanggal Verifikasi", readonly=True)
    baris_ids = fields.One2many("hizwell.daftar.periksa.baris", "daftar_id", string="Dokumen Wajib")
    jumlah_belum = fields.Integer(string="Belum Tersedia", compute="_compute_jumlah_belum", store=True)

    _sql_constraints = [("proyek_uniq", "unique(proyek_id)",
                         "Proyek ini sudah memiliki daftar periksa.")]

    @api.depends("baris_ids.tersedia")
    def _compute_jumlah_belum(self):
        for rec in self:
            rec.jumlah_belum = len(rec.baris_ids.filtered(lambda b: not b.tersedia))

    def action_verifikasi(self):
        if not self.env.user.has_group("hizwell_base.group_direktur_wilayah"):
            raise AccessError("Hanya Direktur Wilayah yang dapat memverifikasi daftar periksa.")
        if any(not rec.baris_ids for rec in self):
            raise UserError("Tambahkan dokumen wajib sebelum diverifikasi.")
        # sudo: Direktur Wilayah belum tentu punya akses "Mengubah" pada proyek.
        # Role sudah dicek di atas, dan hanya tiga field ini yang ditulis.
        self.sudo().write({
            "state": "diverifikasi",
            "diverifikasi_oleh": self.env.user.id,
            "tanggal_verifikasi": fields.Date.context_today(self),
        })


class HizwellDaftarPeriksaBaris(models.Model):
    _name = "hizwell.daftar.periksa.baris"
    _description = "Baris Daftar Periksa"
    _order = "id"

    daftar_id = fields.Many2one("hizwell.daftar.periksa", required=True, ondelete="cascade", index=True)
    name = fields.Char(string="Dokumen Wajib", required=True)
    tersedia = fields.Boolean(string="Sudah Tersedia")
    catatan = fields.Char(string="Catatan")