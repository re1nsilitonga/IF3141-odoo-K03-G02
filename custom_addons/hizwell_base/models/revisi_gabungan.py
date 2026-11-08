import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Field yang tetap boleh ditulis saat dokumen sudah Terbit atau Diarsipkan.
FIELD_BEBAS = {"state", "tanggal_terbit", "pesan_galat", "active"}


class HizwellRevisiGabungan(models.AbstractModel):
    """STD objek 2: dokumen penawaran, PO, dan surat.

    Data Isian Tersimpan -> Terbit, atau -> Gagal Dibuat -> kembali ke Data Isian Tersimpan.
    Terbit -> Diarsipkan saat revisi dibuat; revisi menjadi record baru dengan no_revisi + 1.
    Model pemakai wajib juga mewarisi mail.thread.
    """

    _name = "hizwell.revisi.gabungan"
    _description = "Kelas Gabungan Versi dan Revisi Dokumen"
    _hizwell_field_bebas = set()

    nomor_dokumen = fields.Char(string="Nomor Dokumen", default="/", tracking=True)
    no_revisi = fields.Integer(string="Nomor Revisi", default=0, copy=False, readonly=True)
    kode_revisi = fields.Char(string="Revisi", compute="_compute_kode_revisi")
    alasan_revisi = fields.Text(string="Alasan Revisi", copy=False, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Data Isian Tersimpan"),
            ("gagal", "Gagal Dibuat"),
            ("terbit", "Terbit"),
            ("arsip", "Diarsipkan"),
        ],
        string="Status", default="draft", required=True, copy=False, tracking=True,
    )
    tanggal_terbit = fields.Datetime(string="Tanggal Terbit", copy=False, readonly=True)
    pesan_galat = fields.Text(string="Pesan Galat", copy=False, readonly=True)

    @api.depends("no_revisi")
    def _compute_kode_revisi(self):
        for rec in self:
            rec.kode_revisi = f"Rev{rec.no_revisi:02d}" if rec.no_revisi else ""

    @api.depends("nomor_dokumen", "no_revisi")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.nomor_dokumen or '/'} {rec.kode_revisi}".strip()

    def write(self, vals):
        bebas = FIELD_BEBAS | set(self._hizwell_field_bebas)
        terkunci = [k for k in vals if k not in bebas and not k.startswith(("message_", "activity_"))]
        if terkunci and any(rec.state in ("terbit", "arsip") for rec in self):
            raise UserError(_(
                "Dokumen yang sudah Terbit atau Diarsipkan tidak dapat diubah. "
                "Buat revisi untuk mengubah data isian."
            ))
        return super().write(vals)

    def _hizwell_hasilkan_dokumen(self):
        """Diisi modul C dan D: isi templat, hitung total, buat PDF. Raise jika gagal."""
        return True

    def _cek_transisi(self, asal, tujuan):
        label = dict(self._fields["state"].selection)
        for rec in self:
            if rec.state not in asal:
                raise UserError(_(
                    "Dokumen %(dok)s tidak dapat dipindah dari status %(src)s ke %(dst)s.",
                    dok=rec.display_name, src=label[rec.state], dst=label[tujuan],
                ))

    def action_terbitkan(self):
        self._cek_transisi(("draft",), "terbit")
        for rec in self:
            try:
                with self.env.cr.savepoint():
                    rec._hizwell_hasilkan_dokumen()
            except Exception as e:  # galat apa pun = Gagal Dibuat, sesuai STD
                _logger.warning("Pembuatan dokumen %s gagal: %s", rec.display_name, e)
                rec.write({"state": "gagal", "pesan_galat": str(e)})
                rec.message_post(body=_("Pembuatan dokumen gagal: %s", e))
            else:
                rec.write({"state": "terbit", "tanggal_terbit": fields.Datetime.now(), "pesan_galat": False})
        return True

    def action_ulangi(self):
        self._cek_transisi(("gagal",), "draft")
        self.write({"state": "draft"})
        return True

    def buat_revisi(self, alasan):
        """Terbit -> Diarsipkan, lalu mengembalikan record revisi baru."""
        self.ensure_one()
        if not (alasan or "").strip():
            raise UserError(_("Alasan revisi wajib diisi."))
        self._cek_transisi(("terbit",), "arsip")
        baru = self.copy({
            "nomor_dokumen": self.nomor_dokumen,
            "no_revisi": self.no_revisi + 1,
            "alasan_revisi": alasan.strip(),
        })
        self.write({"state": "arsip"})
        self.message_post(body=_("Diarsipkan karena revisi %s dibuat.", baru.kode_revisi))
        return baru

    def action_buka_wizard_revisi(self):
        self.ensure_one()
        self._cek_transisi(("terbit",), "arsip")
        return {
            "type": "ir.actions.act_window",
            "name": _("Buat Revisi"),
            "res_model": "hizwell.revisi.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_res_model": self._name, "default_res_id": self.id},
        }


class HizwellRevisiWizard(models.TransientModel):
    _name = "hizwell.revisi.wizard"
    _description = "Wizard Buat Revisi Dokumen"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    alasan = fields.Text(string="Alasan Revisi", required=True)

    def action_buat(self):
        self.ensure_one()
        baru = self.env[self.res_model].browse(self.res_id).buat_revisi(self.alasan)
        return {
            "type": "ir.actions.act_window",
            "res_model": baru._name,
            "res_id": baru.id,
            "view_mode": "form",
            "target": "current",
        }