from odoo import fields, models

JENIS_DOKUMEN = [
    ("po", "PO"),
    ("oa", "OA"),
    ("proforma_invoice", "Proforma Invoice"),
    ("dokumen_impor", "Dokumen Impor"),
    ("bst", "BST"),
    ("tagihan", "Tagihan"),
]


class HizwellStatusDokumen(models.Model):
    _name = "hizwell.status.dokumen"
    _description = "Status Dokumen Pesanan"
    _order = "pesanan_id, id"

    pesanan_id = fields.Many2one("hizwell.pesanan", string="Pesanan", required=True,
                                 ondelete="cascade", index=True)
    jenis_dokumen = fields.Selection(JENIS_DOKUMEN, string="Jenis Dokumen", required=True)
    status = fields.Selection([
        ("belum_ada", "Belum Ada"),
        ("sudah_diterima", "Sudah Diterima"),
        ("sudah_diterbitkan", "Sudah Diterbitkan"),
    ], string="Status", required=True, default="belum_ada")
    tanggal_pembaruan = fields.Date(string="Tanggal Pembaruan", readonly=True,
                                    default=fields.Date.context_today)

    _sql_constraints = [("jenis_uniq", "unique(pesanan_id, jenis_dokumen)",
                         "Jenis dokumen sudah tercatat pada pesanan ini.")]

    def write(self, vals):
        # Tanggal pembaruan otomatis setiap status berubah (FR-07)
        if "status" in vals:
            vals["tanggal_pembaruan"] = fields.Date.context_today(self)
        return super().write(vals)