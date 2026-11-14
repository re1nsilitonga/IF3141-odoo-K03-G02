{
    "name": "Hizwell Dokumen",
    "summary": "Penyimpanan dokumen tender dan pengadaan per proyek atau pesanan",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "IF3141 K03-G02",
    "category": "Hizwell",
    "depends": ["hizwell_base"],
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "data/jenis_dokumen_data.xml",
        "views/jenis_dokumen_views.xml",
        "views/dokumen_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
