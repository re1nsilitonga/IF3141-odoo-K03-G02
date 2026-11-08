from odoo import api, fields, models


class HizwellProyek(models.Model):
    _name = "hizwell.proyek"
    _description = "Proyek Tender"
    _inherit = ["mail.thread", "hizwell.akses.gabungan"]
    _hizwell_akses_field = "proyek_id"
    _order = "tanggal_tender desc, id desc"

    kode = fields.Char(string="Kode Proyek", readonly=True, copy=False, default="/")
    name = fields.Char(string="Nama Proyek", required=True, tracking=True)
    pelanggan_id = fields.Many2one("res.partner", string="Pelanggan", required=True, tracking=True)
    nomor_tender = fields.Char(string="Nomor Tender", tracking=True)
    tanggal_tender = fields.Date(string="Tanggal Tender", default=fields.Date.context_today)
    active = fields.Boolean(default=True)
    pesanan_ids = fields.One2many("hizwell.pesanan", "proyek_id", string="Pesanan")
    akses_ids = fields.One2many("hizwell.hak.akses", "proyek_id", string="Hak Akses")

    _sql_constraints = [("kode_uniq", "unique(kode)", "Kode proyek harus unik.")]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("kode", "/") == "/":
                vals["kode"] = self.env["ir.sequence"].next_by_code("hizwell.proyek") or "/"
        return super().create(vals_list)