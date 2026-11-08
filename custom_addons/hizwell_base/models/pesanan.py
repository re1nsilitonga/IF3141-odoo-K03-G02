from odoo import api, fields, models


class HizwellPesanan(models.Model):
    _name = "hizwell.pesanan"
    _description = "Pesanan"
    _inherit = ["mail.thread", "hizwell.akses.gabungan"]
    _hizwell_akses_field = "pesanan_id"
    _order = "tanggal_pesanan desc, id desc"

    name = fields.Char(string="Nomor Pesanan", readonly=True, copy=False, default="/")
    proyek_id = fields.Many2one("hizwell.proyek", string="Proyek", tracking=True, index=True)
    pelanggan_id = fields.Many2one("res.partner", string="Pelanggan", required=True, tracking=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor", tracking=True)
    nomor_po_pelanggan = fields.Char(string="Nomor PO Pelanggan", tracking=True)
    tanggal_pesanan = fields.Date(string="Tanggal Pesanan", default=fields.Date.context_today)
    active = fields.Boolean(default=True)
    akses_ids = fields.One2many("hizwell.hak.akses", "pesanan_id", string="Hak Akses")

    _sql_constraints = [("name_uniq", "unique(name)", "Nomor pesanan harus unik.")]

    @api.onchange("proyek_id")
    def _onchange_proyek_id(self):
        if self.proyek_id and not self.pelanggan_id:
            self.pelanggan_id = self.proyek_id.pelanggan_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("hizwell.pesanan") or "/"
        return super().create(vals_list)