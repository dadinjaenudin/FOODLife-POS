Testing Checklist
Test Flow Normal:

✅ Login sebagai kasir
✅ Halaman POS load → auto-check shift → jika belum ada shift, muncul overlay + modal Open Shift
✅ Isi opening cash → klik "Open Shift"
✅ Modal close → overlay hilang → badge header jadi hijau "Shift Active"
✅ Coba klik produk → bisa add to cart/bill
✅ Badge header update durasi shift otomatis
✅ Klik "Close Shift" di sidebar widget → isi actual cash → close
✅ Badge header jadi merah "Shift Belum Dibuka"
✅ Overlay muncul lagi block UI
✅ Coba klik produk → muncul alert "Shift Belum Dibuka"
Test Edge Cases:

✅ Refresh page saat shift aktif → tidak muncul overlay
✅ Klik produk tanpa shift → SweetAlert dengan tombol "Buka Shift"
✅ Klik "Buka Shift" di alert → modal open shift muncul


Workflow Lengkap:
🌅 Pagi Hari (Open Business Date)
Manager datang pagi → Login → Management → Open/Close Session
Pilih business date (biasanya hari ini: 6 Feb 2026)
Klik "Open New Session" → Session aktif untuk semua brand
Kasir-kasir mulai login → Buka shift masing-masing → Mulai transaksi
☀️ Siang-Sore (Operasional)
Semua kasir kerja dalam business date yang sama (6 Feb 2026)
Beberapa kasir mungkin ganti shift (close → open shift baru)
Session tetap aktif sampai malam
🌙 Malam Hari (Closing/EOD)
Semua kasir close shift → Setor kas, rekonsiliasi
Manager close session → Input closing notes
Sistem otomatis:

📊 Keuntungan Business Date:
Transaksi pukul 23:50 masuk ke tanggal 6 Feb
Bukan tanggal sistem (calendar date)
Laporan akurat per hari operasional
Rekonsiliasi kas terpisah per business date
Jadi sistem ini mirip toko retail: buka pagi (open business date) → operasional → tutup malam (close & EOD).

