from odoo import api, fields, models

from .status_dokumen import JENIS_DOKUMEN


class HizwellPesanan(models.Model):
    _inherit = "hizwell.pesanan"

    status_ids = fields.One2many("hizwell.status.dokumen", "pesanan_id", string="Status Dokumen")
    jumlah_belum_lengkap = fields.Integer(string="Dokumen Belum Lengkap",
                                          compute="_compute_belum_lengkap", store=True)
    dokumen_belum_lengkap = fields.Char(string="Dokumen yang Belum Ada",
                                        compute="_compute_belum_lengkap")

    @api.depends("status_ids.status", "status_ids.jenis_dokumen")
    def _compute_belum_lengkap(self):
        label = dict(JENIS_DOKUMEN)
        for rec in self:
            kosong = rec.status_ids.filtered(lambda s: s.status == "belum_ada")
            rec.jumlah_belum_lengkap = len(kosong)
            rec.dokumen_belum_lengkap = ", ".join(label[s.jenis_dokumen] for s in kosong) or "Lengkap"

    def _buat_status_dokumen(self):
        # Idempotent: hanya menambah jenis yang belum punya baris.
        # sudo: baris bawaan dibuat sistem, jangan sampai membuat pesanan gagal karena rule.
        Status = self.env["hizwell.status.dokumen"].sudo()
        for rec in self:
            ada = set(rec.status_ids.mapped("jenis_dokumen"))
            baru = [{"pesanan_id": rec.id, "jenis_dokumen": j}
                    for j, __ in JENIS_DOKUMEN if j not in ada]
            if baru:
                Status.create(baru)

    def action_buat_status_dokumen(self):
        # Tombol untuk pesanan lama yang dibuat sebelum modul ini dipasang
        self.check_access_rule("write")
        self._buat_status_dokumen()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._buat_status_dokumen()
        return records


class HizwellProyek(models.Model):
    _inherit = "hizwell.proyek"

    daftar_periksa_ids = fields.One2many("hizwell.daftar.periksa", "proyek_id", string="Daftar Periksa")
    daftar_periksa_count = fields.Integer(string="Jumlah Daftar Periksa",
                                          compute="_compute_daftar_periksa_count")

    @api.depends("daftar_periksa_ids")
    def _compute_daftar_periksa_count(self):
        for rec in self:
            rec.daftar_periksa_count = len(rec.daftar_periksa_ids)

    def action_lihat_daftar_periksa(self):
        self.ensure_one()
        aksi = self.env["ir.actions.act_window"]._for_xml_id("hizwell_status.hizwell_daftar_periksa_action")
        aksi["domain"] = [("proyek_id", "=", self.id)]
        aksi["context"] = {"default_proyek_id": self.id}
        return aksi