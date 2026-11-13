from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

# Field isi templat. Jika salah satunya diubah, persetujuan sebelumnya gugur (OW-06).
FIELD_ISI = {
    "kop", "kalimat_pembuka", "ketentuan", "kalimat_penutup",
    "nama_penandatangan", "jabatan_penandatangan",
}
GROUP_DIRWIL = "hizwell_base.group_direktur_wilayah"


class HizwellTemplatPenawaran(models.Model):
    """FR-09: templat penawaran yang harus disetujui Direktur Wilayah sebelum dipakai.

    Penanda isian memakai format [[nama_penanda]], misalnya [[nama_pelanggan]],
    [[nomor_tender]], [[tanggal_tender]], [[nomor_penawaran]], [[nama_proyek]],
    dan [[total_harga]]. Penanda diisi otomatis oleh hizwell.penawaran.
    """

    _name = "hizwell.templat.penawaran"
    _description = "Templat Penawaran"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Nama Templat", required=True, tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("draft", "Rancangan"),
            ("diajukan", "Menunggu Persetujuan"),
            ("disetujui", "Disetujui"),
            ("revisi", "Perlu Revisi"),
        ],
        string="Status", default="draft", required=True, copy=False, tracking=True,
    )
    kop = fields.Text(string="Kop Surat", required=True)
    kalimat_pembuka = fields.Text(string="Kalimat Pembuka", required=True)
    ketentuan = fields.Text(string="Ketentuan Penawaran")
    kalimat_penutup = fields.Text(string="Kalimat Penutup")
    nama_penandatangan = fields.Char(string="Nama Penandatangan")
    jabatan_penandatangan = fields.Char(string="Jabatan Penandatangan")
    catatan_persetujuan = fields.Text(string="Catatan Direktur Wilayah", copy=False)
    disetujui_oleh = fields.Many2one("res.users", string="Disetujui Oleh", copy=False, readonly=True)
    tanggal_persetujuan = fields.Datetime(string="Tanggal Persetujuan", copy=False, readonly=True)

    def write(self, vals):
        # Mengubah isi templat yang sudah diajukan/disetujui membatalkan persetujuan.
        reset = self.browse()
        if FIELD_ISI & set(vals) and "state" not in vals:
            reset = self.filtered(lambda r: r.state in ("diajukan", "disetujui"))
        res = super().write(vals)
        if reset:
            super(HizwellTemplatPenawaran, reset).write({
                "state": "draft", "disetujui_oleh": False, "tanggal_persetujuan": False,
            })
            for rec in reset:
                rec.message_post(body=_("Isi templat diubah, persetujuan dibatalkan. Ajukan kembali ke Direktur Wilayah."))
        return res

    def _cek_status(self, asal, tujuan):
        label = dict(self._fields["state"].selection)
        for rec in self:
            if rec.state not in asal:
                raise UserError(_(
                    "Templat %(nama)s tidak dapat dipindah dari status %(src)s ke %(dst)s.",
                    nama=rec.name, src=label[rec.state], dst=label[tujuan],
                ))

    def _cek_dirwil(self):
        if not self.env.user.has_group(GROUP_DIRWIL):
            raise AccessError(_("Hanya Direktur Wilayah yang dapat memutuskan persetujuan templat."))

    def action_ajukan(self):
        self._cek_status(("draft", "revisi"), "diajukan")
        self.write({"state": "diajukan", "catatan_persetujuan": False})
        for rec in self:
            rec.message_post(body=_("Templat diajukan ke Direktur Wilayah untuk ditinjau."))
        return True

    def action_setujui(self):
        self._cek_dirwil()
        self._cek_status(("diajukan",), "disetujui")
        self.write({
            "state": "disetujui",
            "disetujui_oleh": self.env.user.id,
            "tanggal_persetujuan": fields.Datetime.now(),
        })
        for rec in self:
            rec.message_post(body=_("Templat disetujui oleh %s.", self.env.user.name))
        return True

    def action_minta_revisi(self):
        self._cek_dirwil()
        self._cek_status(("diajukan",), "revisi")
        for rec in self:
            if not (rec.catatan_persetujuan or "").strip():
                raise UserError(_("Isi catatan Direktur Wilayah sebelum meminta revisi."))
        self.write({"state": "revisi"})
        for rec in self:
            rec.message_post(body=_("Direktur Wilayah meminta revisi: %s", rec.catatan_persetujuan))
        return True
