from odoo import api, fields, models


class HizwellProyek(models.Model):
    _inherit = "hizwell.proyek"

    penawaran_ids = fields.One2many("hizwell.penawaran", "proyek_id", string="Penawaran")
    jumlah_penawaran = fields.Integer(string="Jumlah Penawaran", compute="_compute_jumlah_penawaran")

    @api.depends("penawaran_ids.state")
    def _compute_jumlah_penawaran(self):
        for rec in self:
            rec.jumlah_penawaran = len(rec.penawaran_ids.filtered(lambda p: p.state != "arsip"))

    def action_lihat_penawaran(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Penawaran",
            "res_model": "hizwell.penawaran",
            "view_mode": "tree,form",
            "domain": [("proyek_id", "=", self.id)],
            "context": {"default_proyek_id": self.id},
        }
