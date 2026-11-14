from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class HizwellDokumen(models.Model):
    _name = "hizwell.dokumen"
    _description = "Dokumen Tender dan Pengadaan"
    _order = "id desc"

    name = fields.Char(string="Nama Dokumen", required=True)
    jenis_dokumen_id = fields.Many2one(
        "hizwell.jenis.dokumen", string="Jenis Dokumen", required=True,
        ondelete="restrict",
    )
    proyek_id = fields.Many2one("hizwell.proyek", string="Proyek", ondelete="restrict", index=True)
    pesanan_id = fields.Many2one("hizwell.pesanan", string="Pesanan", ondelete="restrict", index=True)
    berkas = fields.Binary(string="Berkas PDF", attachment=True, required=True)
    nama_berkas = fields.Char(string="Nama Berkas", required=True)

    _sql_constraints = [
        ("satu_induk", "CHECK ((proyek_id IS NOT NULL AND pesanan_id IS NULL) OR "
         "(proyek_id IS NULL AND pesanan_id IS NOT NULL))",
         "Dokumen harus memiliki tepat satu induk: proyek atau pesanan."),
    ]

    @api.constrains("proyek_id", "pesanan_id", "jenis_dokumen_id")
    def _check_induk_jenis(self):
        for rec in self:
            if bool(rec.proyek_id) == bool(rec.pesanan_id):
                raise ValidationError(_("Dokumen harus memiliki tepat satu induk."))
            lingkup = "proyek" if rec.proyek_id else "pesanan"
            if rec.jenis_dokumen_id.lingkup != lingkup:
                raise ValidationError(_("Jenis dokumen tidak sesuai dengan induknya."))

    @api.constrains("nama_berkas")
    def _check_nama_berkas(self):
        for rec in self:
            if not rec.nama_berkas.lower().endswith(".pdf"):
                raise ValidationError(_("Berkas yang diunggah harus PDF."))

    @api.model
    def _periksa_izin_induk(self, vals, mode="write", record=None):
        proyek_id = vals.get("proyek_id", record.proyek_id.id if record else False)
        pesanan_id = vals.get("pesanan_id", record.pesanan_id.id if record else False)
        if bool(proyek_id) == bool(pesanan_id):
            raise ValidationError(_("Pilih tepat satu induk dokumen."))
        induk = (self.env["hizwell.proyek"].browse(proyek_id) if proyek_id
                 else self.env["hizwell.pesanan"].browse(pesanan_id))
        induk.check_access_rights("read")
        induk.check_access_rule("read")
        if not self.env.user.has_group("hizwell_base.group_direktur_utama"):
            # Hak mengunggah/mengubah dokumen mengikuti tingkat akses 'ubah'.
            induk.check_access_rights(mode)
            induk.check_access_rule(mode)
        return induk

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._periksa_izin_induk(vals)
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            # Cek induk lama dan baru agar perpindahan dokumen tidak membypass ACL.
            rec._periksa_izin_induk({}, record=rec)
            rec._periksa_izin_induk(vals, record=rec)
        return super().write(vals)

    def unlink(self):
        for rec in self:
            rec._periksa_izin_induk({}, record=rec)
        return super().unlink()


class HizwellProyekDokumen(models.Model):
    _inherit = "hizwell.proyek"

    dokumen_ids = fields.One2many("hizwell.dokumen", "proyek_id", string="Dokumen")
    jumlah_dokumen = fields.Integer(string="Jumlah Dokumen", compute="_compute_jumlah_dokumen")

    def _compute_jumlah_dokumen(self):
        for rec in self:
            rec.jumlah_dokumen = self.env["hizwell.dokumen"].search_count([("proyek_id", "=", rec.id)])

    def action_lihat_dokumen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Dokumen Proyek"),
            "res_model": "hizwell.dokumen", "view_mode": "tree,form",
            "domain": [("proyek_id", "=", self.id)],
            "context": {"default_proyek_id": self.id, "default_pesanan_id": False},
        }


class HizwellPesananDokumen(models.Model):
    _inherit = "hizwell.pesanan"

    dokumen_ids = fields.One2many("hizwell.dokumen", "pesanan_id", string="Dokumen")
    jumlah_dokumen = fields.Integer(string="Jumlah Dokumen", compute="_compute_jumlah_dokumen")

    def _compute_jumlah_dokumen(self):
        for rec in self:
            rec.jumlah_dokumen = self.env["hizwell.dokumen"].search_count([("pesanan_id", "=", rec.id)])

    def action_lihat_dokumen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Dokumen Pesanan"),
            "res_model": "hizwell.dokumen", "view_mode": "tree,form",
            "domain": [("pesanan_id", "=", self.id)],
            "context": {"default_pesanan_id": self.id, "default_proyek_id": False},
        }
