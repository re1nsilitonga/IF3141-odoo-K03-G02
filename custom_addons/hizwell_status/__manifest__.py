{
    "name": "Hizwell Status",
    "summary": "Daftar periksa dokumen tender (FR-06), status dokumen pesanan (FR-07), dan laporan kelengkapan (FR-08)",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "IF3141 K03-G02",
    "category": "Hizwell",
    "depends": ["hizwell_base", "hizwell_dokumen"],
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/status_dokumen_views.xml",
        "views/daftar_periksa_views.xml",
        "views/pesanan_proyek_views.xml",
        "views/menus.xml",
    ],
}