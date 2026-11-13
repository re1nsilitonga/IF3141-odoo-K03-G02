{
    "name": "Hizwell Penawaran",
    "summary": "Templat penawaran dengan persetujuan Direktur Wilayah dan penyusunan dokumen penawaran (FR-09, FR-03)",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "IF3141 K03-G02",
    "category": "Hizwell",
    "depends": ["hizwell_base"],
    # Urutan penting: security dulu, lalu data, lalu report dan views, menu paling akhir.
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "data/sequence_data.xml",
        "data/templat_data.xml",
        "report/penawaran_report.xml",
        "views/templat_views.xml",
        "views/penawaran_views.xml",
        "views/proyek_views.xml",
        "views/menus.xml",
    ],
}
