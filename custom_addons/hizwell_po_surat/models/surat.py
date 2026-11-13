from odoo import api, fields, models


class HizwellSurat(models.Model):
    """Implementasi FR-05: dokumen surat. Diisi Staf Administrasi (IW-03), disimpan pada proyek."""

    _name = "hizwell.surat"
    _description = "Dokumen Surat"
    _inherit = ["mail.thread", "hizwell.revisi.gabungan", "hizwell.dokumen.pdf"]
    _order = "tanggal_surat desc, nomor_dokumen desc, no_revisi desc, id desc"
    _hizwell_report_ref = "hizwell_po_surat.action_report_surat"

    proyek_id = fields.Many2one(
        "hizwell.proyek", string="Proyek", required=True, index=True, ondelete="restrict", tracking=True,
    )
    penerima_id = fields.Many2one("res.partner", string="Penerima", required=True, tracking=True)
    alamat_penerima = fields.Text(
        string="Alamat Penerima", compute="_compute_alamat_penerima", store=True, readonly=False, precompute=True,
    )
    tanggal_surat = fields.Date(string="Tanggal Surat", required=True, default=fields.Date.context_today)
    perihal = fields.Char(string="Perihal", required=True, tracking=True)
    isi = fields.Html(string="Isi Surat")
    riwayat_ids = fields.Many2many("hizwell.surat", string="Versi Lain", compute="_compute_riwayat_ids")

    _sql_constraints = [
        ("nomor_revisi_uniq", "unique(nomor_dokumen, no_revisi)", "Nomor surat dan nomor revisi harus unik."),
    ]

    @api.depends("penerima_id")
    def _compute_alamat_penerima(self):
        for rec in self:
            rec.alamat_penerima = (
                rec.penerima_id._display_address(without_company=True).strip() if rec.penerima_id else False
            )

    @api.depends("nomor_dokumen", "state")
    def _compute_riwayat_ids(self):
        for rec in self:
            rec.riwayat_ids = self.search([
                ("nomor_dokumen", "=", rec.nomor_dokumen), ("id", "!=", rec._origin.id),
            ]) if rec._origin.id else self.browse()

    @api.model_create_multi
    def create(self, vals_list):
        # Nomor surat bisa diketik manual atau dibiarkan "/" sehingga dibuatkan otomatis.
        for vals in vals_list:
            if vals.get("nomor_dokumen", "/") == "/":
                vals["nomor_dokumen"] = self.env["ir.sequence"].next_by_code("hizwell.surat") or "/"
        return super().create(vals_list)

    def _hizwell_hasilkan_dokumen(self):
        self.ensure_one()
        self._hizwell_simpan_pdf()
