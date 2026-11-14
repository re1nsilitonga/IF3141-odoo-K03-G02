from odoo import fields, models


class HizwellJenisDokumen(models.Model):
    _name = "hizwell.jenis.dokumen"
    _description = "Jenis Dokumen Hizwell"
    _order = "name"

    name = fields.Char(string="Nama Jenis Dokumen", required=True)
    lingkup = fields.Selection(
        [("proyek", "Proyek"), ("pesanan", "Pesanan")],
        string="Lingkup", required=True,
    )
    active = fields.Boolean(string="Aktif", default=True)
