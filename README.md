# ChatKUHP

> **Goal-oriented Graphs RAG chatbot for Kitab Undang-Undang Hukum Pidana (Indonesia's Criminal Law).**

ChatKUHP adalah prototipe asisten hukum pidana berbasis *Retrieval-Augmented Generation* (RAG) yang memanfaatkan kerangka kerja **Goal-oriented Graphs (GoG)** untuk menalar pasal-pasal **KUHP Baru (UU No. 1 Tahun 2023)**. Alih-alih hanya mengambil potongan teks secara datar, sistem memodelkan tiap pasal sebagai *goal* dengan **prasyarat (preconditions), unsur tindak pidana (elements), dan akibat hukum (postconditions)**, lalu melakukan penelusuran graf untuk menyusun konteks hukum yang terstruktur sebelum menghasilkan jawaban.

---

## Daftar Isi
- [Fitur Utama](#fitur-utama)
- [Arsitektur & Alur Kerja](#arsitektur--alur-kerja)
- [Teknologi](#teknologi)
- [Struktur Proyek](#struktur-proyek)
- [Instalasi & Menjalankan](#instalasi--menjalankan)
- [Variabel Lingkungan](#variabel-lingkungan)
- [API](#api)
- [Knowledge Base](#knowledge-base)
- [Evaluasi](#evaluasi)
- [Sumber Hukum Pelengkap](#sumber-hukum-pelengkap)
- [Keterbatasan & Pengembangan Lanjutan](#keterbatasan--pengembangan-lanjutan)
- [Sitasi & Lisensi](#sitasi--lisensi)

---

## Fitur Utama

- **Penalaran berbasis Goal-oriented Graphs.** Tiap pasal dimodelkan sebagai simpul goal dengan preconditions, elements, dan postconditions, ditelusuri lewat *DFS backward-chaining*.
- **Pipeline RAG multi-tahap.** Kontekstualisasi pertanyaan, klasifikasi, penulisan ulang query, retrieval berbasis embedding, inferensi pasal, ekspansi graf, dan penyusunan jawaban.
- **Jawaban terstruktur.** Format baku: Inti Kesimpulan -> Saran Praktis -> Ringkasan Fakta & Analisis Unsur.
- **Pelengkap doktrin & yurisprudensi.** Bila pertanyaan tidak dapat dijawab cukup dengan teks pasal (istilah/asas asing, doktrin, atau yurisprudensi), sistem mengalihkan ke jalur jawaban pelengkap yang terkurasi dan transparan.
- **Antarmuka percakapan modern.** Efek *thinking steps*, streaming jawaban, pembatalan generasi, dan konsultasi baru.
- **Gerbang topik.** Menolak pertanyaan di luar hukum pidana Indonesia serta menyaring permintaan yang merujuk KUHP Lama.

---

## Arsitektur & Alur Kerja

Alur inti berada pada `PlanningModel` (backend). Diberikan sebuah pertanyaan, sistem menjalankan tahapan berikut:

1. **Contextualize** — pertanyaan ditulis ulang menjadi mandiri berdasarkan riwayat percakapan (`_contextualize_query`).
2. **Classify** — pertanyaan diklasifikasikan: `legal new KUHP`, `legal beyond KUHP`, `legal old KUHP`, `greeting`, atau `other` (`_classify_query`).
3. **Query Rewriting** — cerita pengguna diubah menjadi query pencarian hukum yang padat kata kunci (`_rewrite_query`).
4. **Retrieve** — pencarian kandidat pasal berbasis embedding (top-k) lalu **goal inference** memilih pasal paling relevan (`retrieve`).
5. **Expand (DFS)** — pasal terpilih diekspansi menjadi hierarki subgoal, lalu direduksi berdasar kecocokan dengan query (`dfs`, `reduce_goals`).
6. **Answer** — konteks hukum terstruktur dikirim ke LLM untuk menyusun jawaban akhir dalam markdown (`planning`).

```
User → Contextualize → Classify ─┬─ greeting / other / old KUHP → balasan gerbang
                                 ├─ legal beyond KUHP → jalur doktrin/yurisprudensi
                                 └─ legal new KUHP → Rewrite → Retrieve → DFS → Reduce → LLM → Jawaban
```

---

## Teknologi

**Backend**
- Python 3, FastAPI + Uvicorn
- LLM: Cohere `command-a-plus` (default) dengan dukungan Google Gemini
- Embedding: `intfloat/multilingual-e5-large` (1024 dimensi), via HF Inference API di produksi
- Knowledge Base graf hukum (GoG) tersimpan sebagai artefak pickle

**Frontend**
- React 19 + TypeScript + Vite
- TailwindCSS v4, komponen UI (shadcn-style), `lucide-react`, `sonner`
- `@tanstack/react-router`
- Render markdown: `react-markdown` + `remark-gfm`

---

## Struktur Proyek

> Struktur representatif; sesuaikan dengan repositori Anda.

```
chatkuhp/
├─ backend/
│  ├─ services/
│  │  ├─ gog_chatbot.py       # PlanningModel: pipeline retrieval + generation
│  │  ├─ gog_data.py          # GOGKB: struktur graf, embedding, DFS, reduce_goals
│  │  ├─ gog_prompts.py       # Kumpulan prompt (PROMPTS)
│  │  └─ schemas.py           # Skema output terstruktur (GoalInferenceSchema)
│  ├─ gog_graph/
│  │  └─ kb_kuhp.pkl          # Artefak Knowledge Base terbangun
│  ├─ data/
│  │  └─ kuhp.jsonl           # Sumber pasal KUHP Baru (untuk membangun KB)
│  ├─ main.py                 # Entry FastAPI (endpoint /chat)
│  └─ .env
└─ frontend/
   ├─ src/
   │  ├─ routes/index.tsx     # Halaman chat utama
   │  └─ components/chat/      # MessageBubble, ThinkingSteps, ThemeToggle, dll.
   ├─ index.html
   └─ package.json
```

---

## Instalasi & Menjalankan

### Prasyarat
- Python 3.10+ dan Node.js 18+
- API key: Cohere (dan/atau Google Gemini), serta HF token untuk embedding

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# siapkan .env (lihat bagian Variabel Lingkungan)
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
# set VITE_API_URL bila backend tidak di http://localhost:8000
npm run dev
```

Buka `http://localhost:5173` (atau port yang ditampilkan Vite).

---

## Variabel Lingkungan

**Backend (`backend/.env`)**

| Variabel | Wajib | Keterangan |
|----------|-------|------------|
| `COHERE_API_KEY` | ya* | API key Cohere untuk LLM `command-a-plus`. |
| `GOOGLE_API_KEY` | opsional | API key Google Gemini (LLM alternatif). |
| `HF_TOKEN` | ya (produksi) | Token HF Inference API untuk embedding E5-large. |
| `GOG_EMBED_BACKEND` | opsional | Backend embedding, mis. `hf` (disarankan pada lingkungan RAM kecil). |

\*Minimal salah satu penyedia LLM harus tersedia; `command-a-plus` dipakai secara default.

**Frontend**

| Variabel | Keterangan |
|----------|------------|
| `VITE_API_URL` | Base URL backend. Default `http://localhost:8000`. |

> Catatan produksi: pada lingkungan RAM terbatas (mis. Railway 2 vCPU / 1 GB), embedding query WAJIB via HF Inference API. Jangan memuat E5-large secara lokal untuk menghindari OOM. Model embedding harus identik dengan yang dipakai saat membangun KB.

---

## API

### `POST /chat`

**Request**
```json
{
  "query": "Seseorang mencuri motor tetangga pada malam hari, kena pasal apa?",
  "history": [
    { "sender": "user", "text": "..." },
    { "sender": "assistant", "text": "..." }
  ]
}
```

**Response**
```json
{
  "response": {
    "answer": "...jawaban markdown...",
    "chosen_goal": "KUHP Pasal 476",
    "goal_choices": ["KUHP Pasal 476", "KUHP Pasal 480"],
    "used_postconditions": []
  }
}
```

Jawaban dihasilkan dalam bahasa Indonesia dengan format terstruktur (Inti Kesimpulan, Saran Praktis, Analisis Unsur).

---

## Knowledge Base

Knowledge Base dibangun dari sumber pasal KUHP Baru (`kuhp.jsonl`) menjadi graf goal (`kb_kuhp.pkl`). Tiap simpul memuat:

- **description / bunyi pasal**
- **preconditions** (prasyarat penerapan)
- **elements** (unsur tindak pidana)
- **postconditions** (sanksi / akibat hukum)
- **aliases** dan relasi antar-subgoal

Saat menjawab, sistem juga menambahkan **pasal saudara** (ayat lain dari pasal yang sama) agar konteks hukum lebih utuh.

---

## Evaluasi

Kualitas retrieval dievaluasi dengan pendekatan **RAGAS**. Pada evaluasi penelitian ini diperoleh:

- **Context Precision** rata-rata **0,9875**
- **Context Recall** rata-rata **0,9500**
- **17 dari 20** pertanyaan uji memperoleh skor sempurna

Pipeline khusus evaluasi (`getcontext`) menjalankan retrieval + DFS + reduksi tanpa memanggil LLM untuk generation, sehingga evaluasi berfokus pada mutu konteks yang diambil.

---

## Sumber Hukum Pelengkap

Selain teks pasal KUHP Baru, sistem menyediakan jalur pelengkap yang **transparan** untuk pertanyaan yang tidak cukup dijawab oleh pasal:

- **Istilah & asas hukum asing/Latin** (mis. *mens rea*, *actus reus*, asas legalitas / *nullum crimen sine lege*, *in dubio pro reo*, *ne bis in idem*) dijelaskan beserta arti dalam bahasa Indonesia.
- **Yurisprudensi terkurasi** (putusan Mahkamah Agung) disuntikkan sebagai konteks pelengkap bila relevan.

Jawaban pada jalur ini selalu diberi penanda bahwa isinya **melengkapi** teks KUHP Baru dengan doktrin/yurisprudensi, dan sistem dirancang untuk tidak mengarang nomor putusan.

---

## Keterbatasan & Pengembangan Lanjutan

- Cakupan inti terbatas pada **KUHP Baru (UU 1/2023)**; KUHP Lama tidak dilayani.
- Sumber yurisprudensi bersifat **terkurasi manual**, belum berupa knowledge base yurisprudensi berskala penuh.
- Arah pengembangan: integrasi sumber yurisprudensi yang lebih luas, pemetaan istilah asing yang lebih kaya, dan penguatan mekanisme penyaringan domain.

---

## Sitasi & Lisensi

Proyek ini merupakan bagian dari penelitian skripsi mengenai penerapan kerangka kerja *Goal-oriented Graphs* untuk RAG pada domain hukum pidana Indonesia.

```bibtex
@thesis{chatkuhp,
  title  = {ChatKUHP: Goal-oriented Graphs RAG untuk Kitab Undang-Undang Hukum Pidana Indonesia},
  author = {Muhammad Tsaqiif Ash-Shiddiq},
  year   = {2026}
}
```

**Lisensi:** tentukan lisensi Anda (mis. MIT) pada berkas `LICENSE`.

> Disclaimer: ChatKUHP adalah prototipe penelitian dan **bukan pengganti nasihat hukum profesional**.
