
DAFTAR FITUR LENGKAP
BOT AUTO ORDER - TELEGRAM
===============================================================================

-------------------------------------------------------------------------------
[ 1 ] FITUR UNTUK PEMBELI
-------------------------------------------------------------------------------
[ + ] Daftar akun otomatis saat user menekan /start.
[ + ] Menu utama berbentuk tombol Telegram.
[ + ] Katalog produk berdasarkan kategori.
[ + ] Detail nama, deskripsi, harga, stok, dan batas pembelian.
[ + ] Harga bertingkat sesuai jumlah barang.
[ + ] Pilihan jumlah pembelian.
[ + ] Checkout memakai saldo akun.
[ + ] Checkout langsung memakai QRIS.
[ + ] Isi saldo memakai QRIS.
[ + ] Cek pembayaran otomatis setiap dua detik.
[ + ] Tombol cek pembayaran manual.
[ + ] Pengiriman produk digital otomatis.
[ + ] Produk dengan proses manual oleh admin.
[ + ] Riwayat pembelian dan pembayaran.
[ + ] Detail setiap transaksi.
[ + ] Download ulang produk yang sudah dibeli.
[ + ] Saldo akun dan catatan perubahan saldo.
[ + ] Program referral.
[ + ] Bonus referral dapat diatur admin.
[ + ] Menu bantuan dan channel resmi.
[ + ] Mode perbaikan atau maintenance
[ + ] User yang diblokir tidak dapat memakai toko.
-------------------------------------------------------------------------------
[ 2 ] FITUR PEMBAYARAN
-------------------------------------------------------------------------------
[ + ] Terhubung ke Payment Gateway REST API mutasi QRIS.
[ + ] Membuat QRIS otomatis.
[ + ] Membaca status pembayaran otomatis.
[ + ] Nominal dari Payment Gateway diperiksa sebelum saldo masuk.
[ + ] Pembayaran sukses tidak dapat masuk dua kali.
[ + ] Order tidak dibuat dua kali saat pengecekan diulang.
[ + ] Deposit tidak dapat menambah saldo dua kali.
[ + ] QRIS memiliki batas waktu.
[ + ] Status PENDING, SUCCESS, EXPIRED, FAILED, dan CANCELLED.
[ + ] ID pembayaran toko terpisah dari ID internal Payment.
[ + ] Pembayaran langsung produk dan deposit saldo.
[ + ] Polling tetap berjalan tanpa domain webhook publik.
-------------------------------------------------------------------------------
[ 3 ] FITUR PRODUK DAN STOK
-------------------------------------------------------------------------------
[ + ] Kategori produk.
[ + ] Produk AUTO.
[ + ] Produk MANUAL.
[ + ] Nama dan deskripsi produk.
[ + ] Batas jumlah beli minimum dan maksimum.
[ + ] Harga bertingkat.
[ + ] Stok real-time.
[ + ] Tambah sampai 500 stok dalam satu input.
[ + ] Stok boleh berisi satu baris atau banyak baris.
[ + ] Pemisah stok memakai satu baris yang isinya tepat --.
[ + ] Stok disimpan dalam bentuk terenkripsi.
[ + ] Stok otomatis berubah menjadi terjual setelah order berhasil.
[ + ] Produk dan kategori dapat diaktifkan atau dimatikan.
[ + ] Produk lama dapat diarsipkan tanpa merusak riwayat.
[ + ] Kategori lama dapat diarsipkan tanpa merusak riwayat.
[ + ] Pengecekan aman sebelum hapus permanen.
[ + ] Broadcast otomatis saat produk baru dibuat.
[ + ] Broadcast otomatis saat stok masuk kembali.
[ + ] Broadcast produk tidak terkirim dua kali untuk kejadian yang sama.
-------------------------------------------------------------------------------
[ 4 ] FITUR VOUCHER
-------------------------------------------------------------------------------
[ + ] Potongan harga berupa nominal tetap.
[ + ] Kode dibuat sendiri oleh admin.
[ + ] Kode otomatis menjadi huruf besar.
[ + ] Panjang kode 4 sampai 32 karakter.
[ + ] Kode dapat memakai A-Z, 0-9, underscore, dan tanda minus.
[ + ] Voucher wajib untuk satu kategori atau satu produk.
[ + ] Voucher tidak dapat berlaku ke semua produk tanpa target.
[ + ] Minimum belanja dapat diatur atau dimatikan.
[ + ] Minimum total setelah diskon dapat diatur.
[ + ] Jumlah kuota keseluruhan dapat diatur.
[ + ] Batas pemakaian per user dapat diatur.
[ + ] Tanggal dan jam berakhir wajib diisi.
[ + ] Waktu voucher memakai WIB.
[ + ] Voucher dapat diaktifkan dan dimatikan.
[ + ] Voucher dapat diatur boleh digabung atau tidak.
[ + ] Maksimal dua voucher dalam satu checkout.
[ + ] Dua voucher hanya dapat dipakai jika keduanya boleh digabung.
[ + ] Berlaku untuk bayar saldo dan QRIS.
[ + ] Tidak berlaku untuk deposit saldo.
[ + ] Kuota ditahan saat QRIS masih menunggu pembayaran.
[ + ] Kuota dilepas saat pembayaran gagal atau lewat waktu.
[ + ] Kuota tidak dapat melewati batas saat banyak user checkout bersamaan.
[ + ] Riwayat menyimpan kode, target, dan diskon saat order dibuat.
[ + ] Riwayat lama tidak berubah saat voucher diedit atau diarsipkan.
[ + ] Laporan pemakaian voucher.
[ + ] Broadcast voucher setelah admin memberi konfirmasi.
-------------------------------------------------------------------------------
[ 5 ] FITUR ADMIN
-------------------------------------------------------------------------------
[ + ] Panel admin melalui /admin
[ + ] Semua akses admin diperiksa memakai numeric Telegram ID
[ + ] Statistik user, produk, stok, order, omzet, dan saldo user
[ + ] Tambah dan kelola kategori
[ + ] Tambah dan kelola produk
[ + ] Atur harga bertingkat
[ + ] Tambah dan hapus stok yang masih tersedia
[ + ] Lihat jumlah stok
[ + ] Lihat daftar dan detail order
[ + ] Selesaikan order manual
[ + ] Refund order ke saldo user
[ + ] Lihat daftar dan detail user
[ + ] Tambah atau kurangi saldo dengan alasan
[ + ] Blokir dan buka blokir user
[ + ] Lihat pembayaran dan statusnya
[ + ] Buat dan kelola voucher
[ + ] Lihat pemakaian voucher
[ + ] Broadcast pesan ke semua user aktif
[ + ] Preview sebelum broadcast dikirim
[ + ] Konfirmasi sekali pakai agar broadcast tidak dobel
[ + ] Buat voting Telegram anonim
[ + ] Voting berisi 2 sampai 10 pilihan
[ + ] Hasil voting terkumpul pada poll yang sama
[ + ] Riwayat jumlah voting terkirim dan gagal
[ + ] Tutup voting dari panel admin
[ + ] Atur mode maintenance
[ + ] Atur bonus referral
[ + ] Atur link bantuan, channel resmi, dan syarat toko
[ + ] Lihat audit tindakan penting
[ + ] Notifikasi user baru kepada admin
[ + ] Notifikasi order baru kepada admin
[ + ] Menu command admin melalui /helpadmin
-------------------------------------------------------------------------------
[ 6 ] BACKGROUND DAN BRANDING OTOMATIS
-------------------------------------------------------------------------------
[ + ] Ada 12 background untuk halaman utama bot
[ + ] Nama toko diambil dari STORE_NAME dalam file .env
[ + ] Foto profil diambil dari foto profil bot Telegram
[ + ] Background dibuat otomatis saat bot mulai berjalan
[ + ] Nama toko otomatis ditulis ke semua background
[ + ] Foto profil bot otomatis dipasang ke semua background
[ + ] Background dibuat ulang setelah nama toko berubah dan bot direstart
[ + ] Background dibuat ulang setelah foto profil bot berubah dan bot direstart
[ + ] Jika bot belum punya foto profil, background tetap dibuat tanpa foto
[ + ] Nama panjang otomatis diperkecil agar tetap muat
[ + ] Background berukuran 1280 x 720 piksel
[ + ] File lama diganti dengan aman setelah gambar baru selesai dibuat
[ + ] Cache mencegah gambar dibuat ulang jika nama dan foto tidak berubah
Background yang tersedia:
[ + ] Halaman utama
[ + ] Selamat datang
[ + ] Katalog
[ + ] Detail produk
[ + ] Checkout
[ + ] Isi saldo
[ + ] Akun
[ + ] Riwayat transaksi
[ + ] Transaksi berhasil
[ + ] Referral
[ + ] Bantuan
[ + ] Pemberitahuan
-------------------------------------------------------------------------------
[ 7 ] RIWAYAT DAN LAPORAN
-------------------------------------------------------------------------------
[ + ] Riwayat order
[ + ] Riwayat pembayaran
[ + ] Riwayat perubahan saldo
[ + ] Detail subtotal, potongan, dan total
[ + ] Detail voucher pada order
[ + ] Data pengiriman produk
[ + ] Download ulang hanya untuk pemilik order
[ + ] Laporan order baru kepada admin
[ + ] Laporan user baru kepada admin
[ + ] Laporan voucher
[ + ] Laporan broadcast
[ + ] Laporan voting
[ + ] Audit tindakan admin dan sistem
-------------------------------------------------------------------------------
[ 8 ] KEAMANAN
-------------------------------------------------------------------------------
[ + ] Stok dienkripsi memakai Fernet
[ + ] API key tidak ditulis ke log
[ + ] Isi stok tidak masuk audit
[ + ] Query database memakai parameter aman
[ + ] Teks Telegram dibersihkan sebelum dikirim sebagai HTML
[ + ] Admin diperiksa pada command dan tombol
[ + ] User hanya dapat membuka transaksi miliknya sendiri
[ + ] Callback lama dan callback ulang ditolak
[ + ] Operasi saldo, stok, order, dan voucher memakai transaksi database
[ + ] Foreign key SQLite diaktifkan
[ + ] Aturan nilai database memakai constraint
[ + ] Order dan pembayaran lama tetap dapat dibaca setelah update
[ + ] Backup dapat dibuat saat bot masih aktif dengan SQLite backup API
[ + ] Self-test tersedia melalui python app.py --self-test.