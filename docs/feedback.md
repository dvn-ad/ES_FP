## Feedback dan pengembangan
1. Urutan pipeline masih salah, dimana LLM sekarang ada setelah box/syntactic matching, sehingga rename menjadi false positive di dua tahap. Harusnnya LLM harus dipindah ke depan. Bisa jadi seperti ini
	- Parse dan normalize (buang layout).
	- Element alignment: exact, lalu lexical, lalu embedding. LLM hanya dipakai untuk pasangan yang meragukan.
	- SESE/RPST decomposition.
	- Relabel model varian memakai hasil alignment.
	- Equivalence check per fragmen.
	- Edit script dan laporan.

    - Tiap pasangan elemen diberi kelas label: identical, synonym, meaning changed, atau unmatched. 
    - Aturan fusi: kalau label synonym dan perilaku equivalent, hasilnya “rename, non behavioral”. Kalau perilaku tidak equivalent, hasilnya “behavioral change” dengan counterexample. Kalau hasil LLM rendah (indikasi bias/ragu/halusinasi), ditandai “needs review”


2. Kemudian “Two or more versions” belum didesain., sehingga RQ dan metodenya masih pairwise. Coba tolong definisikan sebagai reference vs many variants ditambah version chain. Buat beberapa mode:
	- **Mode A**, pairwise: v1 vs v2. Ini dasarnya untuk mode lainnya.
	- **Mode B**, reference vs many variants: satu model R dibandingkan dengan V1 sampai Vn.
		- Output: edit script per varian, ditambah matriks agregat. Matriks ini memisahkan core elements (ada di semua varian) dari variant-specific elements.
		- Dasar teorinya process families (Delgado et al. 2022).
	- **Mode C**, version chain: v1 → v2 → … → vn.
		- Bandingkan pasangan berurutan, lalu gabungkan menjadi change history.
		- Lacak element lineage antar versi dan deteksi revert (perubahan yang dibatalkan di versi berikutnya).
		- Test oracle: gabungan diff(v1,v2) dan diff(v2,v3) harus konsisten dengan diff(v1,v3).

	intinya di bagian ini bisa menjawab seberapa akurat lineage dan alignment tetap konsisten sepanjang chain

3. Minimal untuk kelas besok harus ada Prototype atau hasil awal
	- CLI bpmndiff a.xpdl b.xpdl yang bisa membaca .xpdl dan .bpmn. (ini coba baca dari paper https://www.sciencedirect.com/science/article/pii/S2352711026000427) 
	- Output edit operations dasar: insert, delete, rename, ubah tipe gateway.
	- Behavioral check sederhana (perbandingan trace set) untuk fragmen kecil.
	- Demo pada 1-5 pasangan dari dataset dulu aj

4. Dataset coba mulai diunduh dan dipakai. Jika tidak bisa, coba cari dataset lain. (contoh salah satu dataset: https://data.mendeley.com/datasets/9tgnvj9nsg/1). Ingat format BPMN yg dianalisis yaitu XML bisa .xml, .xpdl, .bpmn, .visio, dll. Bukan excel. Opsi lain dataset bisa pakai https://github.com/camunda/bpmn-for-research atau https://zenodo.org/record/5895006


5. Backend pakai pure python sebagai default dan mCRL2 jd opsional aja. yg penting harus bisa Bangun LTS untuk subset BPMN. Kemudian Trace equivalence yaitu tau closure, lalu determinisasi, lalu bandingkan.
Terus Branching bisimulation yaitu partition refinement atau bagaimana cara memecah sebuah hal kompleks jd fragmen yg kecil. Untuk fragmen kecil, algoritma sederhana aj sdh cukup. ref algoritma efisiennya -> Groote et al. 2017 (Referensi: https://manpages.ubuntu.com/manpages/bionic/man1/ltscompare.1.html)


6. Topik representation format tidak muncul sama sekali, coba ditambahkan

## Referensi Jurnal yg bisa dijadikan acuan tambahan:
| lJurnal | Link |
| - | - |
| Baseline formal (box + LTS) | https://doi.org/10.1016/j.infsof.2026.108128|
|Dasar dari representation format|https://doi.org/10.1016/j.dss.2025.114563|
|Acuan metrik: syntactic, semantic, behavioral|https://www.sciencedirect.com/science/article/pii/S030643792600075X?via%3Dihub|
|Justifikasi kenapa behavioral similarity wajib diuji|https://linkinghub.elsevier.com/retrieve/pii/S0306437925000924|
|Benchmark multi-LLM; dasar memilih LLM|https://doi.org/10.1007/s10270-025-01318-w|
|Model matching untuk model versioning|https://link.springer.com/article/10.1007/s10270-024-01173-1|