import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

PENANDA_RE = re.compile(r"\[\[\s*(\w+)\s*\]\]")
GROUP_DIRWIL = "hizwell_base.group_direktur_wilayah"
GROUP_DIRUT = "hizwell_base.group_direktur_utama"
REPORT_REF = "hizwell_penawaran.action_report_penawaran"


def format_angka(nilai):
    """Format Indonesia: 1.234.567,00"""
    teks = f"{nilai or 0:,.2f}"
    return teks.replace(",", "X").replace(".", ",").replace("X", ".")


class HizwellPenawaran(models.Model):
    """FR-03: dokumen penawaran disusun otomatis dari templat yang sudah disetujui.

    Status, nomor_dokumen, revisi, dan tombol terbitkan/ulangi/revisi berasal dari
    kelas gabungan hizwell.revisi.gabungan (hizwell_base).
    """

    _name = "hizwell.penawaran"
    _description = "Dokumen Penawaran"
    _inherit = ["mail.thread", "hizwell.revisi.gabungan"]
    _order = "tanggal_penawaran desc, id desc"
    # Field yang tetap boleh ditulis setelah dokumen Terbit atau Diarsipkan.
    _hizwell_field_bebas = {
        "tanggal_kirim", "disetujui_revisi_oleh", "tanggal_persetujuan_revisi", "lampiran_id",
    }

    proyek_id = fields.Many2one(
        "hizwell.proyek", string="Proyek", required=True, index=True,
        ondelete="restrict", tracking=True,
    )
    pelanggan_id = fields.Many2one(
        "res.partner", string="Pelanggan", related="proyek_id.pelanggan_id", store=True, readonly=True,
    )
    nomor_tender = fields.Char(string="Nomor Tender", related="proyek_id.nomor_tender", readonly=True)
    tanggal_tender = fields.Date(string="Tanggal Tender", related="proyek_id.tanggal_tender", readonly=True)
    templat_id = fields.Many2one(
        "hizwell.templat.penawaran", string="Templat", required=True, ondelete="restrict",
        domain="[('state', '=', 'disetujui')]", default=lambda self: self._default_templat(), tracking=True,
    )
    tanggal_penawaran = fields.Date(string="Tanggal Penawaran", default=fields.Date.context_today)
    line_ids = fields.One2many("hizwell.penawaran.baris", "penawaran_id", string="Daftar Barang", copy=True)
    total_harga = fields.Float(
        string="Total Harga (Rp)", digits=(16, 2), compute="_compute_total_harga", store=True,
    )
    lampiran_id = fields.Many2one("ir.attachment", string="Berkas PDF", copy=False, readonly=True)
    perlu_persetujuan_revisi = fields.Boolean(
        string="Perlu Persetujuan Direktur Wilayah", copy=False, readonly=True,
        help="Aktif pada revisi dari penawaran yang sudah dikirim ke pelanggan.",
    )
    disetujui_revisi_oleh = fields.Many2one("res.users", string="Revisi Disetujui Oleh", copy=False, readonly=True)
    tanggal_persetujuan_revisi = fields.Datetime(string="Tanggal Persetujuan Revisi", copy=False, readonly=True)
    tanggal_kirim = fields.Datetime(string="Tanggal Dikirim ke Pelanggan", copy=False, readonly=True)

    @api.model
    def _default_templat(self):
        return self.env["hizwell.templat.penawaran"].search([("state", "=", "disetujui")], limit=1).id

    @api.depends("line_ids.subtotal")
    def _compute_total_harga(self):
        for rec in self:
            rec.total_harga = sum(rec.line_ids.mapped("subtotal"))

    # ------------------------------------------------------------------ CRUD

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("nomor_dokumen", "/") == "/":
                vals["nomor_dokumen"] = self.env["ir.sequence"].next_by_code("hizwell.penawaran") or "/"
            if not self.env.su and vals.get("proyek_id"):
                proyek = self.env["hizwell.proyek"].browse(vals["proyek_id"])
                if not proyek.bisa_ubah:
                    raise AccessError(_("Anda tidak memiliki hak akses Mengubah pada proyek %s.", proyek.display_name))
        return super().create(vals_list)

    def unlink(self):
        if not self.env.user.has_group(GROUP_DIRUT) and any(r.state in ("terbit", "arsip") for r in self):
            raise UserError(_(
                "Dokumen yang sudah Terbit atau Diarsipkan tidak dapat dihapus. Hanya Direktur Utama yang dapat menghapusnya."
            ))
        return super().unlink()

    # ------------------------------------------------- penyusunan dokumen

    def _nilai_penanda(self):
        self.ensure_one()
        tanggal = self.tanggal_tender
        return {
            "nama_pelanggan": self.pelanggan_id.name or "",
            "nama_proyek": self.proyek_id.name or "",
            "nomor_tender": self.nomor_tender or "",
            "tanggal_tender": tanggal.strftime("%d-%m-%Y") if tanggal else "",
            "nomor_penawaran": self.display_name or "",
            "total_harga": f"Rp{format_angka(self.total_harga)}",
        }

    def render_penanda(self, teks):
        """Mengisi penanda [[...]] pada teks templat. Dipanggil dari QWeb report."""
        self.ensure_one()
        nilai = self._nilai_penanda()
        return PENANDA_RE.sub(lambda m: nilai.get(m.group(1), m.group(0)), teks or "")

    def _cek_siap_terbit(self):
        self.ensure_one()
        if self.templat_id.state != "disetujui":
            raise UserError(_("Penawaran hanya dapat dibuat dari templat berstatus Disetujui."))
        if not self.line_ids:
            raise UserError(_("Daftar barang masih kosong."))
        if not (self.nomor_tender or "").strip() or not self.tanggal_tender:
            raise UserError(_("Nomor dan tanggal tender pada proyek harus diisi."))
        templat = self.templat_id
        teks = [templat.kop, templat.kalimat_pembuka, templat.ketentuan, templat.kalimat_penutup]
        sisa = {m for t in teks for m in PENANDA_RE.findall(self.render_penanda(t))}
        if sisa:
            raise ValidationError(_("Penanda isian tidak dikenal pada templat: %s", ", ".join(sorted(sisa))))

    def _hizwell_hasilkan_dokumen(self):
        """Validasi data isian, isi templat, cetak PDF, lalu simpan sebagai lampiran."""
        self.ensure_one()
        self._cek_siap_terbit()
        isi, jenis = self.env["ir.actions.report"]._render_qweb_pdf(REPORT_REF, self.ids)
        if isinstance(isi, str):
            isi = isi.encode()
        # Ulangi dari data isian tanpa membuat dokumen duplikat: lampiran lama diganti.
        self.lampiran_id.unlink()
        nama = (self.display_name or "penawaran").replace("/", "-").replace(" ", "_")
        self.lampiran_id = self.env["ir.attachment"].create({
            "name": f"{nama}.pdf",
            "datas": base64.b64encode(isi),
            "mimetype": "application/pdf" if jenis == "pdf" else "text/html",
            "res_model": self._name,
            "res_id": self.id,
        })

    def action_unduh_pdf(self):
        self.ensure_one()
        if not self.lampiran_id:
            raise UserError(_("Berkas PDF belum tersedia."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.lampiran_id.id}?download=true",
            "target": "self",
        }

    # ------------------------------------------- revisi dan pengiriman

    def buat_revisi(self, alasan):
        # Revisi dari versi yang sudah dikirim (atau yang revisinya mengikuti versi terkirim)
        # baru boleh dikirim setelah disetujui Direktur Wilayah.
        perlu = bool(self.tanggal_kirim) or self.perlu_persetujuan_revisi
        baru = super().buat_revisi(alasan)
        if perlu:
            baru.write({"perlu_persetujuan_revisi": True})
        return baru

    def action_setujui_revisi(self):
        self.ensure_one()
        if not self.env.user.has_group(GROUP_DIRWIL):
            raise AccessError(_("Hanya Direktur Wilayah yang dapat menyetujui revisi penawaran."))
        if self.state != "terbit" or not self.perlu_persetujuan_revisi:
            raise UserError(_("Hanya revisi berstatus Terbit yang memerlukan persetujuan yang dapat disetujui."))
        # sudo: Direktur Wilayah boleh hanya berhak Melihat pada proyek, tetapi berwenang menyetujui revisi.
        self.sudo().write({
            "disetujui_revisi_oleh": self.env.user.id,
            "tanggal_persetujuan_revisi": fields.Datetime.now(),
        })
        self.message_post(body=_("Revisi %s disetujui oleh %s.", self.kode_revisi, self.env.user.name))
        return True

    def action_tandai_terkirim(self):
        self.ensure_one()
        if self.state != "terbit":
            raise UserError(_("Hanya dokumen berstatus Terbit yang dapat dikirim."))
        if self.perlu_persetujuan_revisi and not self.disetujui_revisi_oleh:
            raise UserError(_("Revisi atas penawaran yang sudah dikirim harus disetujui Direktur Wilayah sebelum dikirim."))
        self.write({"tanggal_kirim": fields.Datetime.now()})
        self.message_post(body=_("Penawaran %s ditandai sudah dikirim ke pelanggan.", self.display_name))
        return True


class HizwellPenawaranBaris(models.Model):
    _name = "hizwell.penawaran.baris"
    _description = "Baris Barang Penawaran"
    _order = "sequence, id"

    penawaran_id = fields.Many2one("hizwell.penawaran", string="Penawaran", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    nama_barang = fields.Char(string="Nama Barang", required=True)
    part_number = fields.Char(string="Part Number")
    jumlah = fields.Float(string="Jumlah", digits=(16, 2), default=1.0, required=True)
    harga_satuan = fields.Float(string="Harga Satuan (Rp)", digits=(16, 2), required=True)
    subtotal = fields.Float(string="Subtotal (Rp)", digits=(16, 2), compute="_compute_subtotal", store=True)

    @api.depends("jumlah", "harga_satuan")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.jumlah * rec.harga_satuan

    @api.constrains("jumlah", "harga_satuan")
    def _check_nilai(self):
        for rec in self:
            if rec.jumlah <= 0:
                raise ValidationError(_("Jumlah barang harus lebih dari 0."))
            if rec.harga_satuan < 0:
                raise ValidationError(_("Harga satuan tidak boleh negatif."))

    @api.model
    def _cek_induk_draft(self, penawaran):
        if any(p.state != "draft" for p in penawaran):
            raise UserError(_("Daftar barang hanya dapat diubah saat dokumen berstatus Data Isian Tersimpan."))

    @api.model_create_multi
    def create(self, vals_list):
        ids = {v["penawaran_id"] for v in vals_list if v.get("penawaran_id")}
        self._cek_induk_draft(self.env["hizwell.penawaran"].browse(ids))
        return super().create(vals_list)

    def write(self, vals):
        self._cek_induk_draft(self.penawaran_id)
        return super().write(vals)

    def unlink(self):
        self._cek_induk_draft(self.penawaran_id)
        return super().unlink()
