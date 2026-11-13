from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

INCOTERM = [
    ("exw", "EXW - Ex Works"),
    ("fca", "FCA - Free Carrier"),
    ("fas", "FAS - Free Alongside Ship"),
    ("fob", "FOB - Free On Board"),
    ("cfr", "CFR - Cost and Freight"),
    ("cif", "CIF - Cost, Insurance and Freight"),
    ("cpt", "CPT - Carriage Paid To"),
    ("cip", "CIP - Carriage and Insurance Paid To"),
    ("dap", "DAP - Delivered at Place"),
    ("dpu", "DPU - Delivered at Place Unloaded"),
    ("ddp", "DDP - Delivered Duty Paid"),
]


class HizwellPo(models.Model):
    """Implementasi FR-04: dokumen PO kepada vendor. Diisi Direktur Utama (IW-02), dicetak dari templat QWeb."""

    _name = "hizwell.po"
    _description = "Dokumen PO"
    _inherit = ["mail.thread", "hizwell.revisi.gabungan", "hizwell.dokumen.pdf"]
    _order = "nomor_dokumen desc, no_revisi desc, id desc"
    _hizwell_report_ref = "hizwell_po_surat.action_report_po"

    # Sama seperti nomor pesanan/kode proyek di hizwell_base: dibuat otomatis, tidak bisa diketik.
    nomor_dokumen = fields.Char(readonly=True)
    pesanan_id = fields.Many2one(
        "hizwell.pesanan", string="Pesanan", required=True, index=True, ondelete="restrict", tracking=True,
    )
    vendor_id = fields.Many2one(
        "res.partner", string="Vendor", required=True, tracking=True,
        compute="_compute_vendor_id", store=True, readonly=False, precompute=True,
    )
    alamat_vendor = fields.Text(
        string="Alamat Vendor", compute="_compute_alamat_vendor", store=True, readonly=False, precompute=True,
    )
    tanggal_po = fields.Date(string="Tanggal PO", required=True, default=fields.Date.context_today)
    incoterm = fields.Selection(INCOTERM, string="Incoterm", required=True, tracking=True)
    lokasi_incoterm = fields.Char(string="Lokasi Incoterm", help="Contoh: Shanghai, Tanjung Priok")
    currency_id = fields.Many2one(
        "res.currency", string="Mata Uang", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    uang_muka_persen = fields.Float(string="Uang Muka (%)", digits=(5, 2))
    ketentuan_uang_muka = fields.Text(string="Ketentuan Uang Muka")
    baris_ids = fields.One2many("hizwell.po.baris", "po_id", string="Daftar Barang", copy=True)
    total = fields.Monetary(string="Total Harga", compute="_compute_total", store=True)
    uang_muka_nominal = fields.Monetary(string="Nilai Uang Muka", compute="_compute_total", store=True)
    riwayat_ids = fields.Many2many("hizwell.po", string="Versi Lain", compute="_compute_riwayat_ids")

    _sql_constraints = [
        ("nomor_revisi_uniq", "unique(nomor_dokumen, no_revisi)", "Nomor PO dan nomor revisi harus unik."),
    ]

    @api.depends("pesanan_id")
    def _compute_vendor_id(self):
        for rec in self:
            rec.vendor_id = rec.pesanan_id.vendor_id

    @api.depends("vendor_id")
    def _compute_alamat_vendor(self):
        # disalin sebagai isian: alamat di PO tidak ikut berubah jika data vendor diubah kemudian
        for rec in self:
            rec.alamat_vendor = (
                rec.vendor_id._display_address(without_company=True).strip() if rec.vendor_id else False
            )

    @api.depends("baris_ids.subtotal", "uang_muka_persen", "currency_id")
    def _compute_total(self):
        for rec in self:
            total = sum(rec.baris_ids.mapped("subtotal"))
            rec.total = total
            nominal = total * rec.uang_muka_persen / 100.0
            rec.uang_muka_nominal = rec.currency_id.round(nominal) if rec.currency_id else nominal

    @api.depends("nomor_dokumen", "state")
    def _compute_riwayat_ids(self):
        for rec in self:
            rec.riwayat_ids = self.search([
                ("nomor_dokumen", "=", rec.nomor_dokumen), ("id", "!=", rec._origin.id),
            ]) if rec._origin.id else self.browse()

    @api.constrains("uang_muka_persen")
    def _check_uang_muka_persen(self):
        for rec in self:
            if not 0 <= rec.uang_muka_persen <= 100:
                raise ValidationError(_("Uang muka harus antara 0 dan 100 persen."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("nomor_dokumen", "/") == "/":
                vals["nomor_dokumen"] = self.env["ir.sequence"].next_by_code("hizwell.po") or "/"
        return super().create(vals_list)

    def _hizwell_hasilkan_dokumen(self):
        """Dipanggil action_terbitkan di dalam savepoint; galat apa pun membuat state Gagal Dibuat."""
        self.ensure_one()
        if not self.baris_ids:
            raise UserError(_("Daftar barang masih kosong."))
        if not self.alamat_vendor:
            raise UserError(_("Alamat vendor belum diisi."))
        self._hizwell_simpan_pdf()


class HizwellPoBaris(models.Model):
    _name = "hizwell.po.baris"
    _description = "Baris Barang PO"
    _order = "sequence, id"

    po_id = fields.Many2one("hizwell.po", string="PO", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    nama_barang = fields.Char(string="Nama Barang", required=True)
    part_number = fields.Char(string="Part Number")
    jumlah = fields.Float(string="Jumlah", digits=(16, 2), default=1.0)
    satuan = fields.Char(string="Satuan", default="pcs")
    currency_id = fields.Many2one(related="po_id.currency_id", string="Mata Uang")
    harga_satuan = fields.Monetary(string="Harga Satuan")
    subtotal = fields.Monetary(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("jumlah", "harga_satuan", "currency_id")
    def _compute_subtotal(self):
        for rec in self:
            nilai = rec.jumlah * rec.harga_satuan
            rec.subtotal = rec.currency_id.round(nilai) if rec.currency_id else nilai

    @api.constrains("jumlah", "harga_satuan")
    def _check_nilai(self):
        for rec in self:
            if rec.jumlah <= 0:
                raise ValidationError(_("Jumlah barang harus lebih dari 0."))
            if rec.harga_satuan < 0:
                raise ValidationError(_("Harga satuan tidak boleh negatif."))

    # write() pada hizwell.po hanya melindungi field PO sendiri; baris perlu dikunci terpisah.
    def _cek_po_masih_draft(self, daftar_po):
        if any(po.state in ("terbit", "arsip") for po in daftar_po):
            raise UserError(_(
                "Daftar barang PO yang sudah Terbit atau Diarsipkan tidak dapat diubah. Buat revisi."
            ))

    @api.model_create_multi
    def create(self, vals_list):
        ids_po = [v["po_id"] for v in vals_list if v.get("po_id")]
        self._cek_po_masih_draft(self.env["hizwell.po"].browse(ids_po))
        return super().create(vals_list)

    def write(self, vals):
        self._cek_po_masih_draft(self.po_id)
        return super().write(vals)

    def unlink(self):
        self._cek_po_masih_draft(self.po_id)
        return super().unlink()
