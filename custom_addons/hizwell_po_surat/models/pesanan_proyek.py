from odoo import api, fields, models


class HizwellPesanan(models.Model):
    _inherit = "hizwell.pesanan"

    po_ids = fields.One2many("hizwell.po", "pesanan_id", string="PO")
    po_count = fields.Integer(string="Jumlah PO", compute="_compute_po_count")

    @api.depends("po_ids.state")
    def _compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.po_ids.filtered(lambda p: p.state != "arsip"))

    def action_lihat_po(self):
        self.ensure_one()
        aksi = self.env["ir.actions.act_window"]._for_xml_id("hizwell_po_surat.hizwell_po_action")
        aksi["domain"] = [("pesanan_id", "=", self.id)]
        aksi["context"] = {"default_pesanan_id": self.id, "search_default_filter_berlaku": 1}
        return aksi


class HizwellProyek(models.Model):
    _inherit = "hizwell.proyek"

    surat_ids = fields.One2many("hizwell.surat", "proyek_id", string="Surat")
    surat_count = fields.Integer(string="Jumlah Surat", compute="_compute_surat_count")

    @api.depends("surat_ids.state")
    def _compute_surat_count(self):
        for rec in self:
            rec.surat_count = len(rec.surat_ids.filtered(lambda s: s.state != "arsip"))

    def action_lihat_surat(self):
        self.ensure_one()
        aksi = self.env["ir.actions.act_window"]._for_xml_id("hizwell_po_surat.hizwell_surat_action")
        aksi["domain"] = [("proyek_id", "=", self.id)]
        aksi["context"] = {"default_proyek_id": self.id, "search_default_filter_berlaku": 1}
        return aksi
