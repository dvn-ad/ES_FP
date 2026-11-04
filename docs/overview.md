
# Kerangka Kerja Terintegrasi: Perbandingan & Verifikasi Model BPMN Hibrida (Versi Revisi)

## 1. Urutan Pipeline Ter-refaktor (LLM di Tahap Awal)

### A. Alasan Perubahan Pipeline
Pada rancangan terdahulu, LLM ditempatkan setelah modul box/syntactic matching. Hal ini menyebabkan perubahan nama elemen (rename) terdeteksi sebagai deviasi struktural (elemen dihapus dan elemen baru ditambahkan) di dua tahap awal, yang memicu tingginya angka false positive. Pada pipeline baru, LLM digeser ke tahapan awal (alignment) untuk menyelesaikan ambiguitas semantik label sebelum model didekomposisi menjadi fragmen struktural.


```

[BPMN / XPDL Files]
│
▼

1. Parse & Normalize (Drop Layout/Styling)
│
▼
2. Element Alignment Berperingkat
(Exact ➔ Lexical ➔ Embedding ➔ LLM Fallback)
│
▼
3. Dekomposisi SESE / RPST Fragment Generator
│
▼
4. Relabeling Model Varian (Berdasarkan Hasil Alignment)
│
▼
5. Equivalence Check per Fragmen (Pure Python LTS Engine)
│
▼
6. Fusion Matrix & Edit Script Report Generator

```

### B. Tahapan Pipeline Detail
1. **Parse dan Normalize**: Membaca file BPMN/XPDL, membuang informasi tata letak visual (diagram graphic/layout coordinates), dan mengonversi struktur ke bentuk graf terstandar.
2. **Element Alignment Berperingkat**:
   - **Level 1 (Exact Match)**: Identifikasi pasangan elemen dengan ID atau Teks Label yang persis sama.
   - **Level 2 (Lexical Match)**: Pencocokan berbasis String Similarity (misal: Levenshtein / Jaro-Winkler) untuk variasi ejaan tipis.
   - **Level 3 (Embedding Match)**: Vector Similarity (misal: SBERT / Cosine Similarity) untuk sinonim umum.
   - **Level 4 (LLM Fallback)**: LLM hanya dipanggil untuk pasangan kandidat yang memiliki skor ambigu (rentang $0.4 - 0.7$). LLM bertindak sebagai penilai makna semantik khusus domain.
3. **Dekomposisi SESE / RPST**: Menguraikan graf proses menjadi fragmen Single-Entry Single-Exit (SESE) atau Refined Process Structure Tree (RPST) untuk mengisolasi batas verifikasi formal.
4. **Relabel Model Varian**: Memperbarui nama/label node pada varian dengan pasangan sinonim yang sudah terverifikasi agar model siap diuji secara perilaku.
5. **Equivalence Check per Fragmen**: Pengecekan kesetaraan perilaku (trace/branching equivalence) hanya pada fragmen SESE yang berbeda.
6. **Edit Script & Laporan**: Mengonstruksi langkah perubahan terstruktur (INSERT, DELETE, RENAME, CHANGE_TYPE) beserta analisis dampaknya.

### C. Taksonomi Label Pasangan Elemen & Aturan Fusi (Fusion Rules)
Setiap pasangan elemen dipetakan ke salah satu dari 4 kelas label: `identical`, `synonym`, `meaning_changed`, atau `unmatched`.

| Label LLM / Alignment | Verifikasi Perilaku Formal | Klasifikasi Akhir Diff | Output & Penjelasan |
| :--- | :--- | :--- | :--- |
| **Identical / Synonym** | Equivalent | Rename / Non-behavioral | Perubahan sintaksis/label tanpa mengubah alur eksekusi proses. |
| **Identical / Synonym** | Not Equivalent | Behavioral Change | Alur kontrol berubah meskipun label mirip. Disertai counterexample trace. |
| **Meaning Changed** | Equivalent / Not Equivalent | Semantic & Behavioral Change | Perubahan makna fungsional kegiatan bisnis. |
| **Unmatched** | Not Equivalent | Structural Insert/Delete | Elemen ditambah/dihapus secara penuh pada salah satu varian. |
| **Low Confidence / Hallucination** | Any | Needs Review | Skor LLM di bawah ambang batas (indikasi ragu/halusinasi). |

---

## 2. Desain Analisis Multi-Versi ("Two or More Versions")

Untuk mendukung *process families* dan analisis evolusi proses, metode diperluas dari sekadar pairwise menjadi tiga mode operasi:

### Mode A: Pairwise Comparison ($V_1$ vs $V_2$)
- **Fungsi**: Membandingkan dua versi model secara langsung. Berfungsi sebagai modul dasar (*atomic core*) untuk Mode B dan Mode C.
- **Output**: Edit script mendalam dan counterexample trace jika terjadi inkonsistensi perilaku.

### Mode B: Reference vs. Many Variants ($R$ vs $V_1, V_2, \dots, V_n$)
- **Landasan Teori**: Process Families & Variability Management (Delgado et al. 2022).
- **Fungsi**: Membandingkan satu model acuan utama ($R$) dengan $n$ varian bisnis lokal/regional ($V_1 \dots V_n$).
- **Output**:
  1. Edit script individual untuk setiap pasangan $(R, V_i)$.
  2. Matriks Agregat Process Family:
     - **Core Elements**: Elemen/sub-proses yang wajib ada dan konsisten di seluruh varian ($R \cap V_1 \cap \dots \cap V_n$).
     - **Variant-Specific Elements**: Elemen opsional atau kustomisasi lokal yang hanya muncul di varian tertentu.

### Mode C: Version Chain / Change History ($V_1 \rightarrow V_2 \rightarrow \dots \rightarrow V_n$)
- **Fungsi**: Membandingkan pasangan versi berurutan secara kontinyu untuk merekonstruksi riwayat perubahan sistem (*evolution lineage*).
- **Kemampuan Khusus**:
  - **Element Lineage Tracking**: Melacak riwayat hidup suatu elemen dari versi awal hingga versi akhir.
  - **Revert Detection**: Mendeteksi perubahan pada versi $V_i$ yang dibatalkan/dikembalikan ke bentuk semula pada versi $V_{i+1}$.
- **Test Oracle (Aksioma Konsistensi Transitif)**:
$$\text{diff}(V_1, V_2) \oplus \text{diff}(V_2, V_3) \equiv \text{diff}(V_1, V_3)$$
*Menguji apakah penggabungan riwayat perubahan bertahap secara matematis konsisten dengan perbedaan langsung antara versi awal dan versi akhir.*

---

## 3. Format Representasi Proses (Representation Formats)

Framework ini memanfaatkan beberapa bentuk abstrak representasi proses yang disesuaikan dengan kebutuhan setiap tahapan pipeline:

1. **BPMN / XPDL XML**: Format standar industri berbasis XML yang menyimpan informasi lengkap proses, aktivitas, gateway, dan metadata.
2. **Simplified XML (SXML) & JSON**: Format terstruktur ringkas tanpa informasi layout/visual coordinates. SXML/JSON digunakan sebagai input hemat token untuk LLM dan pencocokan graf.
3. **POWL (Partially Ordered Workflow Language)**: Format representasi tingkat menengah (*intermediate representation*) berbasis hirarki yang menjamin soundness matematis model sebelum diekspor ke notation target.
4. **Graph & Cypher Queries**: Struktur data node-edge terarah yang dihasilkan parser untuk query database graf (Neo4j/NetworkX) dan analisis topologi.
5. **Labeled Transition System (LTS)**: Model formal berarah state-transition untuk mengeksekusi analisis semantik dan kesetaraan perilaku dinamis.

---

## 4. Spesifikasi Prototype CLI (`bpmndiff`)

Dibuat untuk kebutuhan demonstrasi dan pengujian awal pada dataset:

### A. Antarmuka Perintah
```bash
# Penggunaan dasar pairwise
bpmndiff model_a.xpdl model_b.bpmn --mode A

# Mode Reference vs Variants
bpmndiff ref.bpmn var1.bpmn var2.xpdl var3.xml --mode B --out-matrix summary.json

# Mode Version Chain
bpmndiff v1.bpmn v2.bpmn v3.bpmn --mode C --track-reverts

```

### B. Kemampuan Parser Multi-Format

Mengintegrasikan pustaka multi-format parser (*bpmn-graph-transformation* Febryanto et al. 2026) untuk membaca secara native format `.bpmn`, `.xpdl`, `.xml`, dan `.vdx` (Visio) melalui arsitektur plugin terpadu.

### C. Operasi Edit Dasar & Behavioral Check

* **Output Operasi Edit**: `INSERT`, `DELETE`, `RENAME`, `CHANGE_GATEWAY_TYPE` (misal: XOR ke AND).
* **Behavioral Check**: Perbandingan trace set sederhana (ekstraksi trace eksekusi dari fragmen kecil SESE).

### D. Dataset Pengujian Awal (1–5 Pasangan)

* **Camunda BPMN for Research**: Repositori model nyata terstandar.
* **Mendeley Data BPMN Dataset**: Kumpulan model proses bisnis XML.
* **Zenodo Repository**: Dataset pasangan deskripsi teks dan model BPMN.

---

## 5. Backend Verifikasi Formal (Pure Python LTS Engine)

Untuk menjaga dependensi sistem tetap ringan dan portable, Python murni dijadikan sebagai engine default, sedangkan mCRL2 atau CADP bersifat opsional.

### A. Konstruksi LTS untuk Subset BPMN

Engine mengonstruksi Labeled Transition System (LTS) dari subset alur kontrol BPMN (Start/End Events, Tasks, XOR/AND/OR Gateways) dengan *token-passing semantics*.

### B. Algoritma Kesetaraan Perilaku Murni Python

1. **Trace Equivalence**:
* Menghitung $\tau$-closure untuk mengeliminasi transisi internal (*tau steps*) yang dihasilkan oleh gateway.
* Menjalankan determinisasi LTS (*Subset Construction*).
* Membandingkan ketercapaian set jejak (*trace set comparison*) antar fragmen.


2. **Branching Bisimulation (Partition Refinement)**:
* Menerapkan algoritma *partition refinement* sederhana (mengacu pada prinsip Groote et al. 2017 / `ltscompare`) untuk membagi state space fragmen SESE kecil hingga mencapai kondisi konvergen.


