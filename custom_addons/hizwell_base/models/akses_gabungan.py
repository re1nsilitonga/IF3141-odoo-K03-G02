from odoo import api, fields, models


class HizwellAksesGabungan(models.AbstractModel):
    _name = "hizwell.akses.gabungan"
    _description = "Kelas Gabungan Hak Akses Hizwell"
    _hizwell_akses_field = None  # diisi model pemakai: "proyek_id" atau "pesanan_id"

    bisa_ubah = fields.Boolean(compute="_compute_bisa_ubah")

    @api.depends_context("uid")
    def _compute_bisa_ubah(self):
        if self.env.user.has_group("hizwell_base.group_direktur_utama"):
            self.bisa_ubah = True
            return
        for rec in self:
            rec.bisa_ubah = any(
                a.user_id == self.env.user and a.tingkat_akses == "ubah"
                for a in rec.sudo().akses_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        user = self.env.user
        # sudo: hanya Direktur Utama yang boleh membuat baris hak akses secara langsung
        if not self.env.su and not user.has_group("hizwell_base.group_direktur_utama"):
            self.env["hizwell.hak.akses"].sudo().create([
                {"user_id": user.id, self._hizwell_akses_field: rec.id, "tingkat_akses": "ubah"}
                for rec in records
            ])
        return records