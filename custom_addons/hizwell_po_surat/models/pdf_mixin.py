import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HizwellDokumenPdf(models.AbstractModel):
    """Penyimpanan PDF hasil cetak untuk PO dan surat.

    Model pemakai wajib juga mewarisi hizwell.revisi.gabungan (state, nomor_dokumen, kode_revisi)
    dan mengisi _hizwell_report_ref dengan XML id aksi laporan QWeb-nya.
    """

    _name = "hizwell.dokumen.pdf"
    _description = "Kelas Gabungan Penyimpanan PDF Dokumen Hizwell"
    _hizwell_report_ref = None

    company_id = fields.Many2one(
        "res.company", string="Perusahaan", required=True, default=lambda self: self.env.company,
    )
    pdf_id = fields.Many2one("ir.attachment", string="Berkas PDF", compute="_compute_pdf_id")

    @api.depends("state")
    def _compute_pdf_id(self):
        lampiran = self.env["ir.attachment"]
        for rec in self:
            res_id = rec._origin.id
            rec.pdf_id = lampiran.search([
                ("res_model", "=", rec._name),
                ("res_id", "=", res_id),
                ("mimetype", "=", "application/pdf"),
            ], order="id desc", limit=1) if res_id else False

    def _hizwell_nama_berkas(self):
        self.ensure_one()
        dasar = re.sub(r"[^\w.-]+", "-", self.nomor_dokumen or "dokumen").strip("-")
        sufiks = f"_{self.kode_revisi}" if self.kode_revisi else ""
        return f"{dasar}{sufiks}.pdf"

    def _hizwell_simpan_pdf(self):
        """Cetak laporan QWeb ke PDF lalu simpan sebagai lampiran record ini.

        Idempoten: pengulangan setelah Gagal Dibuat menimpa lampiran bernama sama,
        jadi tidak ada dokumen ganda.
        """
        self.ensure_one()
        if not self._hizwell_report_ref:
            raise UserError(_("Templat laporan belum ditetapkan untuk model ini."))
        pdf, _tipe = self.env["ir.actions.report"]._render_qweb_pdf(self._hizwell_report_ref, self.ids)
        if not pdf:
            raise UserError(_("Hasil cetak PDF kosong."))
        nama = self._hizwell_nama_berkas()
        lampiran = self.env["ir.attachment"]
        lama = lampiran.search([
            ("res_model", "=", self._name), ("res_id", "=", self.id), ("name", "=", nama),
        ], limit=1)
        vals = {"raw": pdf, "mimetype": "application/pdf"}
        if lama:
            lama.write(vals)
        else:
            lampiran.create({**vals, "name": nama, "type": "binary", "res_model": self._name, "res_id": self.id})
        return True

    def action_unduh_pdf(self):
        self.ensure_one()
        if not self.pdf_id:
            raise UserError(_("PDF belum tersedia. Terbitkan dokumen terlebih dahulu."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.pdf_id.id}?download=true",
            "target": "self",
        }

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault("nomor_dokumen", "/")
        return super().copy(default)

    def unlink(self):
        if any(rec.state in ("terbit", "arsip") for rec in self):
            raise UserError(_(
                "Dokumen yang sudah Terbit atau Diarsipkan tidak boleh dihapus. "
                "Versi lama disimpan di Arsip Revisi."
            ))
        return super().unlink()
