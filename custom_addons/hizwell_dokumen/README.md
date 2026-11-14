# Hizwell Dokumen (FR-01)

Modul Odoo 17 Community untuk unggah dokumen PDF tender dan pesanan.
Nama file asli dipertahankan sementara sampai SOP OW-05 ditetapkan; tidak ada sequence dokumen baru.

## Instalasi

Salin folder `hizwell_dokumen` ke `custom_addons/` repository tim.

```bash
docker compose run --rm web odoo -d odoo_app -i hizwell_dokumen --stop-after-init
docker compose restart web
```

Update: `docker compose run --rm web odoo -d odoo_app -u hizwell_dokumen --stop-after-init`

Testing pada DB terpisah: `docker compose run --rm web odoo -d odoo_test -i hizwell_dokumen --test-enable --test-tags /hizwell_dokumen --stop-after-init`

## Batasan

- Belum ada SOP format nama berkas, mekanisme trash 30 hari, versioning, retensi 10 tahun, dan backup bulanan.
- Validasi PDF berbasis ekstensi nama berkas, bukan inspeksi isi file.
- Perlu uji instalasi dan HTTP `/web/content` di lingkungan Docker Odoo 17 yang berjalan sebelum produksi.
- Model konfigurasi jenis dokumen hanya dapat diubah Direktur Utama sesuai menu konfigurasi `hizwell_base`.
