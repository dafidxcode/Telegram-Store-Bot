"""Translation strings for EN (English) and ID (Bahasa Indonesia).

Covers ALL bot text: home, products, buy flow, orders, admin panel, poller notifications.
Each user has their own language preference stored in the DB.
"""

T = {
    # ── Greetings ──────────────────────────────────────────────────────────
    "good_morning":    {"en": "🌅 Good Morning",           "id": "🌅 Selamat Pagi"},
    "good_afternoon":  {"en": "☀️ Good Afternoon",         "id": "☀️ Selamat Siang"},
    "good_evening":    {"en": "🌆 Good Evening",           "id": "🌆 Selamat Sore"},
    "good_night":      {"en": "🌙 Good Night",             "id": "🌙 Selamat Malam"},

    # ── Home ───────────────────────────────────────────────────────────────
    "welcome":         {"en": "👋 Welcome to *{shop}*.",   "id": "👋 Selamat datang di *{shop}*."},
    "account_stats":   {"en": "📋 ACCOUNT STATS",          "id": "📋 STATISTIK AKUN"},
    "username":        {"en": "👤 Username",               "id": "👤 Nama Pengguna"},
    "user_id_label":   {"en": "🆔 User ID",                "id": "🆔 ID Pengguna"},
    "total_orders":    {"en": "📦 Total Orders : {n} transactions", "id": "📦 Total Pesanan : {n} transaksi"},
    "bot_stats":       {"en": "📊 BOT STATS",              "id": "📊 STATISTIK BOT"},
    "accounts_sold":   {"en": "📨 Accounts Sold : {n}",    "id": "📨 Akun Terjual : {n}"},
    "active_products": {"en": "🛍 Active Products : {n}",  "id": "🛍 Produk Aktif : {n}"},
    "total_users":     {"en": "👥 Total Users : {n}",      "id": "👥 Total Pengguna : {n}"},
    "stock_per":       {"en": "📦 STOCK PER PRODUCT",      "id": "📦 STOK PER PRODUK"},
    "no_products":     {"en": "❌ No products yet",      "id": "❌ Belum ada produk"},
    "where_start":     {"en": "💡 Where to start?",        "id": "💡 Mulai dari mana?"},
    "hint_buy":        {"en": "🛒 Buy account → Product List",      "id": "🛒 Beli akun → Daftar Produk"},
    "hint_orders":     {"en": "📋 Check transactions → Order History", "id": "📋 Cek transaksi → Riwayat Pesanan"},

    # ── Navigation buttons ─────────────────────────────────────────────────
    "btn_product_list":  {"en": "🛍️ Product List",         "id": "🛍️ Daftar Produk"},
    "btn_check_stock":   {"en": "📦 Check Stock",          "id": "📦 Cek Stok"},
    "btn_order_history": {"en": "📋 Order History",        "id": "📋 Riwayat"},
    "btn_home":          {"en": "🏠 Menu Utama",           "id": "🏠 Menu Utama"},
    "btn_admin_home":    {"en": "🏠 Home Admin Panel",     "id": "🏠 Home Admin Panel"},
    "btn_back":          {"en": "⬅️ Kembali",              "id": "⬅️ Kembali"},
    "btn_cancel_pay":    {"en": "❌ Batal Bayar",          "id": "❌ Batal Bayar"},
    "btn_lang_en":       {"en": "🌐 English",              "id": "🌐 English"},
    "btn_lang_id":       {"en": "🌐 Bahasa Indonesia",    "id": "🌐 Bahasa Indonesia"},
    "btn_admin_panel":   {"en": "⚙️ Admin Panel",          "id": "⚙️ Admin Panel"},

    # ── Product list ───────────────────────────────────────────────────────
    "product_list_title": {"en": "*🛍️ PRODUCT LIST*",      "id": "*🛍️ DAFTAR PRODUK*"},
    "no_products_yet":    {"en": "*🛍️ PRODUCT LIST*\n\n❌ No products available yet.", "id": "*🛍️ DAFTAR PRODUK*\n\n❌ Belum ada produk yang tersedia."},
    "select_product":     {"en": "👇 Select a product to order:", "id": "👇 Pilih produk yang ingin dipesan:"},
    "price":              {"en": "💰 Price",                "id": "💰 Harga"},
    "stock":              {"en": "📦 Stock",                "id": "📦 Stok"},
    "accounts":           {"en": "accounts",                "id": "akun"},
    "unlimited":          {"en": "♾️ Unlimited",           "id": "♾️ Tanpa Batas"},
    "duration":           {"en": "⏰ Duration",             "id": "⏰ Durasi"},

    # ── Stock info ─────────────────────────────────────────────────────────
    "stock_info":         {"en": "*📦 Stock Info*",         "id": "*📦 Informasi Stok*"},
    "total_stock":        {"en": "📦 Total",                "id": "📦 Total"},

    # ── Order history (user) ───────────────────────────────────────────────
    "order_history":      {"en": "*📋 Order History*",      "id": "*📋 Riwayat Pesanan*"},
    "no_orders":          {"en": "❌ No orders yet. Buy now! 🛒", "id": "❌ Belum ada pesanan. Beli sekarang! 🛒"},
    "buy_again":          {"en": "🔄 Buy Again",            "id": "🔄 Beli Lagi"},

    # ── Help ───────────────────────────────────────────────────────────────
    "help_title":         {"en": "*❓ Help*",               "id": "*❓ Bantuan*"},
    "help_how_buy":       {"en": "*📖 How to Buy:*",        "id": "*📖 Cara Membeli:*"},
    "help_step1":         {"en": "1. Click *Product List*", "id": "1. Klik *Daftar Produk*"},
    "help_step2":         {"en": "2. Select a product",  "id": "2. Pilih produk"},
    "help_step3":         {"en": "3. Choose quantity",   "id": "3. Pilih jumlah"},
    "help_step4":         {"en": "4. Confirm & pay via QRIS", "id": "4. Konfirmasi & bayar melalui QRIS"},
    "help_step5":         {"en": "5. Account is delivered automatically", "id": "5. Akun akan dikirimkan secara otomatis"},
    "help_commands":      {"en": "*📜 Commands:*",          "id": "*📜 Perintah:*"},
    "help_cmd_start":     {"en": "/start - 🏠 Main menu",  "id": "/start - 🏠 Menu utama"},
    "help_cmd_produk":    {"en": "/produk - 🛍️ View products", "id": "/produk - 🛍️ Lihat produk"},
    "help_cmd_beli":      {"en": "/beli - 🛒 Buy account",  "id": "/beli - 🛒 Beli akun"},
    "help_cmd_stock":     {"en": "/stock - 📦 Check stock", "id": "/stock - 📦 Cek stok"},
    "help_cmd_myorders":  {"en": "/myorders - 📋 Order history", "id": "/myorders - 📋 Riwayat pesanan"},
    "help_cmd_cancel":    {"en": "/cancel - ❌ Cancel process", "id": "/cancel - ❌ Batal proses"},
    "help_lang_tip":      {"en": "💡 Tap the button below to switch language!", "id": "💡 Tekan tombol di bawah untuk mengubah bahasa!"},

    # ── Cancel payment ─────────────────────────────────────────────────────
    "cancel_no_pending":  {"en": "⚠️ No pending payment to cancel.", "id": "⚠️ Tidak ada pembayaran tertunda yang dibatalkan."},
    "cancelled":          {"en": "❌ Payment cancelled.",   "id": "❌ Pembayaran dibatalkan."},
    "session_expired":    {"en": "⏰ Session expired. /beli to start again.", "id": "⏰ Sesi telah berakhir. Ketik /beli untuk memulai kembali."},

    # ══════════════════════════════════════════════════════════════════════
    # BUY FLOW
    # ══════════════════════════════════════════════════════════════════════

    # Select product
    "select_product_title": {"en": "*🛍️ Select Product*",  "id": "*🛍️ Pilih Produk*"},
    "choose_product":       {"en": "👇 Choose a product to purchase:", "id": "👇 Pilih produk yang ingin dibeli:"},
    "cancel":               {"en": "❌ Cancel",             "id": "❌ Batal"},

    # Out of stock
    "out_of_stock":         {"en": "⚠️ Sorry, *{name}* is out of stock.\n\nPlease choose another product or wait for restock.", "id": "⚠️ Maaf, *{name}* stok sedang habis.\n\nSilakan pilih produk lain atau tunggu stok diisi kembali."},
    "choose_another":       {"en": "🔄 Please choose another product or wait for restock.", "id": "🔄 Silakan pilih produk lain atau tunggu stok diisi kembali."},

    # Product not available
    "product_not_available": {"en": "❌ Product is not available.", "id": "❌ Produk tidak tersedia."},
    "no_products_available": {"en": "❌ No products available yet. Please wait for admin to add products.", "id": "❌ Belum ada produk yang tersedia. Silakan tunggu admin menambahkan produk."},

    # Product detail
    "product_details":      {"en": "*📋 Product Details*", "id": "*📋 Detail Produk*"},
    "pricing":              {"en": "*💰 Pricing*",         "id": "*💰 Harga*"},
    "pricing_per_account":  {"en": "🏷️ All quantities    : Rp {price} / account", "id": "🏷️ Semua jumlah     : Rp {price} / akun"},
    "stock_heading":        {"en": "*📦 Stock*",           "id": "*📦 Stok*"},
    "available":            {"en": "✅ Available",         "id": "✅ Tersedia"},
    "minimum":              {"en": "🔹 Minimum",           "id": "🔹 Minimal"},
    "your_order":           {"en": "*🛒 Your Order*",      "id": "*🛒 Pesanan Anda*"},
    "quantity":             {"en": "🔢 Quantity",          "id": "🔢 Jumlah"},
    "total":                {"en": "💰 Total",             "id": "💰 Total"},

    # Cart buttons
    "enter_qty_manually":   {"en": "⌨️ Enter Quantity Manually", "id": "⌨️ Masukkan Jumlah Manual"},
    "pay_qris":             {"en": "💳 Pay via QRIS - Rp {total}", "id": "💳 Bayar via QRIS - Rp {total}"},

    # Manual quantity input
    "enter_quantity_title": {"en": "*⌨️ Enter Quantity*",  "id": "*⌨️ Masukkan Jumlah*"},
    "type_number":          {"en": "📝 Type a number and send it.", "id": "📝 Ketik angka jumlah dan kirimkan."},
    "example_type":         {"en": "💡 Example: type *{n}* to buy {n} accounts.", "id": "💡 Contoh: ketik *{n}* untuk membeli {n} akun."},

    # Insufficient stock
    "insufficient_stock":   {"en": "⚠️ Insufficient stock. Available: *{stock}* accounts.", "id": "⚠️ Stok tidak mencukupi. Tersedia: *{stock}* akun."},
    "type_another_or_cancel": {"en": "✍️ Type another quantity or /cancel to abort.", "id": "✍️ Ketik jumlah lain atau /cancel untuk membatalkan."},

    # Order confirmation
    "order_confirmation":   {"en": "*✅ Order Confirmation*", "id": "*✅ Konfirmasi Pesanan*"},
    "confirm_pay":          {"en": "✅ Confirm & Pay",      "id": "✅ Konfirmasi & Bayar"},
    "proceed_payment":      {"en": "❓ Proceed to payment?", "id": "❓ Lanjutkan ke pembayaran?"},

    # Creating order
    "creating_order":       {"en": "⏳ Creating order & QRIS...", "id": "⏳ Membuat pesanan & QRIS..."},
    "creating_order_for":   {"en": "⏳ Creating order for *{name}* x{qty}...", "id": "⏳ Membuat pesanan untuk *{name}* x{qty}..."},

    # Order created (caption for QRIS photo)
    "order_created":        {"en": "✅ ORDER CREATED",      "id": "✅ PESANAN DIBUAT"},
    "product_label":        {"en": "📦 Product",            "id": "📦 Produk"},
    "quantity_label":       {"en": "🔢 Quantity",           "id": "🔢 Jumlah"},
    "accounts_label":       {"en": "accounts",              "id": "akun"},
    "status_label":         {"en": "⏳ Status",             "id": "⏳ Status"},
    "expires_label":        {"en": "⏰ Expires",            "id": "⏰ Kadaluarsa"},
    "scan_qris":            {"en": "📱 Scan the QRIS above to pay.", "id": "📱 Scan QRIS di atas untuk melakukan pembayaran."},
    "auto_deliver":         {"en": "🤖 Account will be delivered automatically after payment.", "id": "🤖 Akun akan dikirimkan otomatis setelah pembayaran terverifikasi."},
    "check_myorders":       {"en": "🔍 Check status: /myorders", "id": "🔍 Cek status: /myorders"},

    # QRIS text fallback
    "qr_processing":        {"en": "🔄 QRIS image is being generated.\nCheck status at /myorders.", "id": "🔄 Gambar QRIS sedang diproses.\nCek status di /myorders."},

    # Cancel order button
    "btn_cancel_order":     {"en": "❌ Cancel Payment",     "id": "❌ Batal Bayar"},

    # ══════════════════════════════════════════════════════════════════════
    # ADMIN PANEL
    # ══════════════════════════════════════════════════════════════════════

    # Panel main
    "admin_panel":          {"en": "*⚙️ ADMIN PANEL*",     "id": "*⚙️ PANEL ADMIN*"},
    "dashboard":            {"en": "*📊 Dashboard*",        "id": "*📊 Papan Utama*"},
    "stock_ready":          {"en": "📦 Stock Ready",        "id": "📦 Stok Ready"},
    "sold":                 {"en": "✅ Sold",               "id": "✅ Terjual"},
    "pending_orders":       {"en": "⏳ Pending Orders",     "id": "⏳ Pesanan Pending"},
    "total_products":       {"en": "🛍️ Total Products",     "id": "🛍️ Total Produk"},
    "per_product_stock":    {"en": "*📦 PER-PRODUCT STOCK*","id": "*📦 STOK PER PRODUK*"},
    "select_admin_menu":    {"en": "👇 Select admin menu below", "id": "👇 Pilih menu admin di bawah ini"},
    "no_products_admin":    {"en": "  ❌ No products",      "id": "  ❌ Belum ada produk"},

    # Admin buttons
    "btn_view_products":    {"en": "📦 View Products",      "id": "📦 Lihat Produk"},
    "btn_stock_info":       {"en": "📊 Stock Info",         "id": "📊 Informasi Stok"},
    "btn_view_orders":      {"en": "📋 View Orders",        "id": "📋 Lihat Pesanan"},
    "btn_financial_report": {"en": "📊 Revenue Report",     "id": "📊 Laporan Keuangan"},
    "btn_add_product":      {"en": "➕ Add Product",        "id": "➕ Tambah Produk"},
    "btn_edit_product":     {"en": "✏️ Edit Product",       "id": "✏️ Edit Produk"},
    "btn_delete_product":   {"en": "🗑️ Delete Product",     "id": "🗑️ Hapus Produk"},
    "btn_add_stock":        {"en": "📥 Add Stock",          "id": "📥 Tambah Stok"},
    "btn_change_price":     {"en": "💰 Change Price",       "id": "💰 Ubah Harga"},
    "btn_export_stock":     {"en": "📤 Export Stock",       "id": "📤 Export Stok"},
    "btn_search_order":     {"en": "🔍 Search Order",       "id": "🔍 Cari Pesanan"},
    "btn_broadcast":        {"en": "📣 Broadcast",          "id": "📣 Broadcast Pesan"},
    "btn_bot_settings":     {"en": "⚙️ Bot Settings",       "id": "⚙️ Pengaturan Bot"},
    "btn_admin_list":       {"en": "👥 Admin List",         "id": "👥 Daftar Admin"},
    "btn_add_admin":        {"en": "👤 Add Admin",          "id": "👤 Tambah Admin"},
    "btn_remove_admin":     {"en": "👤 Remove Admin",       "id": "👤 Hapus Admin"},
    "btn_back_to_admin":    {"en": "⬅️ Back to Admin Panel","id": "⬅️ Kembali ke Panel Admin"},
    "btn_back_to_menu":     {"en": "🏠 Back to Menu",       "id": "🏠 Menu Utama"},
    "btn_feedback_list":    {"en": "💬 Feedback List",      "id": "💬 Kelola Feedback"},
    "btn_sub_products":     {"en": "📦 Products & Stock",   "id": "📦 Kelola Produk"},
    "btn_sub_orders":       {"en": "📋 Orders & Revenue",   "id": "📋 Pesanan & Keuangan"},
    "btn_sub_users":        {"en": "👥 Users & Referrals",  "id": "👥 Kelola Pengguna & Referral"},
    "btn_sub_system":       {"en": "⚙️ System & Settings",  "id": "⚙️ Sistem Bot"},


    # Admin new features
    "admin_financial_report_title": {"en": "*📊 FINANCIAL REPORT*", "id": "*📊 LAPORAN KEUANGAN*"},
    "admin_bot_settings_title":     {"en": "*⚙️ BOT SETTINGS*",     "id": "*⚙️ PENGATURAN BOT*"},
    "admin_export_stock_title":     {"en": "*📤 EXPORT STOCK*",     "id": "*📤 EXPORT STOK*"},
    "admin_search_order_title":     {"en": "*🔍 SEARCH ORDER*",     "id": "*🔍 CARI PESANAN*"},
    "admin_search_order_prompt":    {"en": "🔍 Please send Order ID or Telegram User ID to search:", "id": "🔍 Kirimkan ID Pesanan (Order ID) atau Telegram User ID untuk mencari:"},
    "maintenance_mode_alert":       {"en": "⚠️ Bot is currently undergoing maintenance. Please try again later.", "id": "⚠️ Bot sedang dalam pemeliharaan/restock. Silakan coba lagi nanti."},

    # Product edit feature
    "admin_edit_product_title":     {"en": "*✏️ EDIT PRODUCT*",     "id": "*✏️ EDIT PRODUK*"},
    "admin_edit_select_prompt":     {"en": "👇 Select a product to edit:", "id": "👇 Pilih produk yang ingin diubah:"},
    "admin_send_new_name":          {"en": "📝 Please send new name for product *{name}*:", "id": "📝 Kirimkan nama baru untuk produk *{name}*:"},
    "admin_send_new_desc":          {"en": "📝 Please send new description for product *{name}* (send `-` for empty):", "id": "📝 Kirimkan deskripsi baru untuk produk *{name}* (kirim `-` jika tanpa deskripsi):"},
    "admin_send_new_price":         {"en": "💰 Please send new price (in IDR) for product *{name}*:", "id": "💰 Kirimkan harga baru (dalam Rupiah) untuk produk *{name}*:"},

    # Admin — product list
    "admin_product_list":   {"en": "*📦 PRODUCT LIST*",     "id": "*📦 DAFTAR PRODUK*"},
    "admin_no_products":    {"en": "*📦 Product List*\n\n❌ No products yet.", "id": "*📦 Daftar Produk*\n\n❌ Belum ada produk."},
    "admin_price":          {"en": "💰 Price",              "id": "💰 Harga"},
    "admin_stock":          {"en": "📦 Stock",              "id": "📦 Stok"},

    # Admin — stock info
    "admin_stock_info":     {"en": "*📊 STOCK INFO*",       "id": "*📊 INFORMASI STOK*"},
    "admin_total_ready":    {"en": "📦 Total Ready Stock",  "id": "📦 Total Stok Ready"},
    "admin_pending_orders": {"en": "⏳ Pending Orders",     "id": "⏳ Pesanan Pending"},

    # Admin — orders
    "admin_recent_orders":  {"en": "*📋 RECENT ORDERS*",    "id": "*📋 PESANAN TERBARU*"},
    "admin_no_orders":      {"en": "*📋 RECENT ORDERS*\n\n❌ No orders yet.", "id": "*📋 PESANAN TERBARU*\n\n❌ Belum ada pesanan."},
    "admin_pending_orders_title": {"en": "*⏳ PENDING ORDERS*", "id": "*⏳ PESANAN PENDING*"},
    "admin_no_pending":     {"en": "*⏳ PENDING ORDERS*\n\n❌ No pending orders.", "id": "*⏳ PESANAN PENDING*\n\n❌ Tidak ada pesanan pending."},
    "admin_paid_orders":    {"en": "*✅ PAID ORDERS*",      "id": "*✅ PESANAN LUNAS*"},
    "admin_no_paid":        {"en": "*✅ PAID ORDERS*\n\n❌ No paid orders.", "id": "*✅ PESANAN LUNAS*\n\n❌ Tidak ada pesanan lunas."},
    "btn_all":              {"en": "📋 All",                "id": "📋 Semua"},
    "btn_pending":          {"en": "⏳ Pending",            "id": "⏳ Pending"},
    "btn_paid":             {"en": "✅ Paid",               "id": "✅ Lunas"},

    # Admin — admin list
    "admin_list_title":     {"en": "*👥 ADMIN LIST*",       "id": "*👥 DAFTAR ADMIN*"},
    "admin_total":          {"en": "📊 Total",              "id": "📊 Total"},
    "admins":               {"en": "admins",                "id": "admin"},

    # Admin — add product interactive
    "admin_add_product":    {"en": "*➕ ADD PRODUCT*",      "id": "*➕ TAMBAH PRODUK*"},
    "admin_send_name":      {"en": "📝 Send the *product name* now.\n\nExample: `Leonardo AI Account`", "id": "📝 Kirim *nama produk* sekarang.\n\nContoh: `Canva Pro`"},
    "admin_product_name":   {"en": "📦 Product name",       "id": "📦 Nama produk"},
    "admin_send_price":     {"en": "📝 Send the *price* (number only).\nExample: `15000`", "id": "📝 Kirim *harga* (hanya angka).\nContoh: `1000`"},
    "admin_send_desc":      {"en": "📝 Send the *description* (or send `-` to skip).", "id": "📝 Kirim *deskripsi produk* (atau kirim `-` untuk melewatinya)."},
    "admin_name_empty":     {"en": "⚠️ Name cannot be empty. Send product name:", "id": "⚠️ Nama tidak boleh kosong. Kirim nama produk:"},
    "admin_price_number":   {"en": "⚠️ Price must be a number. Send again:", "id": "⚠️ Harga harus berupa angka. Kirim ulang:"},
    "admin_price_positive": {"en": "⚠️ Price must be > 0. Send again:", "id": "⚠️ Harga harus > 0. Kirim ulang:"},

    # Admin — delete product
    "admin_select_delete_product": {"en": "🗑️ Select product to delete:", "id": "🗑️ Pilih produk yang ingin dihapus:"},
    "admin_confirm_delete_product": {"en": "❓ Are you sure you want to delete *{name}*?", "id": "❓ Apakah Anda yakin ingin menghapus produk *{name}*?"},
    "admin_product_deleted_success": {"en": "✅ Product #{id} (*{name}*) deleted!", "id": "✅ Produk #{id} (*{name}*) berhasil dihapus!"},

    # Admin — product added/updated/deleted
    "admin_product_added":  {"en": "*✅ Product added!*",   "id": "*✅ Produk berhasil ditambahkan!*"},
    "admin_product_updated": {"en": "*✅ Product updated!*","id": "*✅ Produk berhasil diperbarui!*"},
    "admin_product_deleted": {"en": "*🗑️ Product deleted!*","id": "*🗑️ Produk berhasil dihapus!*"},
    "admin_id":             {"en": "🆔 ID",                 "id": "🆔 ID"},
    "admin_name":           {"en": "📦 Name",               "id": "📦 Nama"},
    "admin_description":    {"en": "📝 Description",        "id": "📝 Deskripsi"},
    "admin_active":         {"en": "✅ Active",             "id": "✅ Aktif"},
    "admin_inactive":       {"en": "❌ Inactive",           "id": "❌ Tidak Aktif"},

    # Admin — change price
    "admin_change_price":   {"en": "*💰 CHANGE PRICE*",     "id": "*💰 UBAH HARGA*"},
    "admin_select_product": {"en": "👇 Select product to change price:", "id": "👇 Pilih produk yang ingin diubah harganya:"},
    "admin_current_price":  {"en": "💰 Current price",      "id": "💰 Harga saat ini"},
    "admin_send_new_price": {"en": "📝 Send the *new price* now.\n\nExample: `15000`", "id": "📝 Kirim *harga baru* sekarang.\n\nContoh: `15000`"},
    "admin_new_price":      {"en": "💰 New price",          "id": "💰 Harga baru"},

    # Admin — broadcast
    "admin_broadcast":      {"en": "*📣 BROADCAST*",        "id": "*📣 BROADCAST PESAN*"},
    "admin_send_message":   {"en": "📝 Send the *message* to broadcast now.\n\nExample: `Weekend promo 20% off!`", "id": "📝 Kirim *pesan broadcast* sekarang.\n\nContoh: `Promo hemat 50%!`"},
    "admin_broadcast_done": {"en": "*✅ Broadcast complete!*", "id": "*✅ Broadcast selesai!*"},
    "admin_sent":           {"en": "📤 Sent",               "id": "📤 Terkirim"},
    "admin_failed":         {"en": "❌ Failed",             "id": "❌ Gagal"},
    "users":                {"en": "users",                 "id": "pengguna"},

    # Admin — add admin
    "admin_add_admin":      {"en": "*👤 ADD ADMIN*",        "id": "*👤 TAMBAH ADMIN*"},
    "admin_send_user_id":   {"en": "📝 Send the *Telegram User ID* now.\n\n💡 To find ID: Forward a message to @userinfobot\n\nExample: `123456789`", "id": "📝 Kirim *ID Pengguna Telegram* sekarang.\n\n💡 Untuk mencari ID: Forward pesan ke @userinfobot\n\nContoh: `123456789`"},
    "admin_id_number":      {"en": "⚠️ ID must be a number. Send again:", "id": "⚠️ ID harus berupa angka. Kirim ulang:"},
    "admin_already_admin":  {"en": "⚠️ ID `{id}` is already an admin.", "id": "⚠️ ID `{id}` sudah menjadi admin."},
    "admin_added":          {"en": "*✅ Admin added!*",     "id": "*✅ Admin ditambahkan!*"},
    "admin_total_admins":   {"en": "👥 Total admins",       "id": "👥 Total admin"},

    # Admin — remove admin
    "admin_remove_admin":   {"en": "*👤 REMOVE ADMIN*",     "id": "*👤 HAPUS ADMIN*"},
    "admin_select_admin":   {"en": "👇 Select admin to remove:", "id": "👇 Pilih admin yang ingin dihapus:"},
    "admin_no_remove":      {"en": "*👤 REMOVE ADMIN*\n\n❌ No additional admins to remove.", "id": "*👤 HAPUS ADMIN*\n\n❌ Tidak ada admin tambahan untuk dihapus."},
    "admin_cannot_remove":  {"en": "⚠️ Cannot remove the main admin.", "id": "⚠️ Tidak dapat menghapus admin utama."},
    "admin_removed":        {"en": "*✅ Admin removed!*",   "id": "*✅ Admin berhasil dihapus!*"},

    # Admin — add stock
    "admin_add_stock":      {"en": "*📥 ADD STOCK*",        "id": "*📥 TAMBAH STOK*"},
    "admin_select_stock_product": {"en": "👇 Select product to add stock to:", "id": "👇 Pilih produk yang ingin ditambah stoknya:"},
    "admin_no_active_products": {"en": "*📥 ADD STOCK*\n\n❌ No active products yet. Add a product first.", "id": "*📥 TAMBAH STOK*\n\n❌ Belum ada produk aktif. Tambahkan produk terlebih dahulu."},
    "admin_method1":        {"en": "*Method 1:* 📁 Send a .txt file\n(1 line = 1 account/item)", "id": "*Cara 1:* 📁 Kirim file berformat `.txt`\n(Setiap baris baru = 1 stok akun/produk)"},
    "admin_method2":        {"en": "*Method 2:* 📝 Paste directly in chat\n(Setiap baris baru = 1 akun/produk)", "id": "*Cara 2:* 📝 Tempel (*paste*) langsung di chat\n(Setiap baris baru = 1 stok akun/produk)"},
    "admin_send_now":       {"en": "📤 Send now!",          "id": "📤 Kirimkan sekarang!"},
    "admin_current_stock":  {"en": "📦 Current stock",      "id": "📦 Stok saat ini"},
    "admin_stock_added":    {"en": "*✅ Stock added to {name}*!", "id": "*✅ Stok berhasil ditambahkan ke {name}*!"},
    "admin_added_count":    {"en": "📥 Added",              "id": "📥 Ditambahkan"},
    "admin_product_stock":  {"en": "📦 Product stock",      "id": "📦 Stok produk"},
    "admin_send_more":      {"en": "💡 Send more stock or click Back below.", "id": "💡 Kirim stok tambahan atau klik Kembali di bawah ini."},
    "admin_stock_not_added": {"en": "*⚠️ No stock added to {name}*", "id": "*⚠️ Tidak ada stok yang ditambahkan ke {name}*"},
    "admin_check_format":   {"en": "📝 Please send 1 account item per line.", "id": "📝 Silakan kirimkan 1 akun per baris baru."},
    "admin_try_again":      {"en": "🔄 Try Again",          "id": "🔄 Coba Lagi"},
    "admin_add_more":       {"en": "📥 Add More",           "id": "📥 Tambah Lagi"},
    "admin_stock_file_added": {"en": "*✅ Stock added successfully!*", "id": "*✅ Stok berhasil ditambahkan!*"},
    "admin_stock_file_none": {"en": "*⚠️ No stock added*\n\nEnsure there is text on each line.", "id": "*⚠️ Tidak ada stok yang ditambahkan*\n\nPastikan terdapat isi teks pada setiap baris."},
    "admin_only_txt":       {"en": "⚠️ Only .txt files are accepted.", "id": "⚠️ Hanya file .txt yang diterima."},
    "admin_failed_read":    {"en": "❌ Failed to read file. Please try again.", "id": "❌ Gagal membaca file. Silakan coba lagi."},

    # Admin — generic
    "admin_access_denied":  {"en": "🚫 Access denied.",     "id": "🚫 Akses ditolak."},
    "admin_something_wrong": {"en": "❌ Something went wrong. Start again.", "id": "❌ Terjadi kesalahan. Silakan mulai kembali."},
    "admin_no_changes":     {"en": "⚠️ No changes made. Use field=value.", "id": "⚠️ Tidak ada perubahan dibuat."},
    "admin_price_must_be_number": {"en": "⚠️ Price must be a number.", "id": "⚠️ Harga harus berupa angka."},
    "admin_price_gt_zero":  {"en": "⚠️ Price must be greater than 0.", "id": "⚠️ Harga harus lebih besar dari 0."},
    "admin_id_must_number": {"en": "⚠️ ID must be a number.",  "id": "⚠️ ID harus berupa angka."},
    "admin_not_found":      {"en": "❌ Product ID `{id}` not found.", "id": "❌ ID Produk `{id}` tidak ditemukan."},
    "admin_id_not_admin":   {"en": "❌ ID `{id}` is not an admin.", "id": "❌ ID `{id}` bukan admin."},
    "admin_price_updated":  {"en": "*✅ Price updated!*",   "id": "*✅ Harga berhasil diperbarui!*"},
    "admin_price_per_account": {"en": "💰 New price: *Rp {price}/account*", "id": "💰 Harga baru: *Rp {price}/akun*"},

    # POLLER NOTIFICATIONS (sent to users)
    "payment_success":      {"en": "✅ PAYMENT SUCCESSFUL!", "id": "✅ PEMBAYARAN BERHASIL!"},
    "order_label":          {"en": "🆔 Order",              "id": "🆔 Pesanan"},
    "quantity_label_short": {"en": "🔢 Quantity",           "id": "🔢 Jumlah"},
    "total_label":          {"en": "💰 Total",              "id": "💰 Total"},
    "file_attached":        {"en": "📁 Your account file is attached.\nKeep it safe! 🔐", "id": "📁 File data akun Anda dilampirkan.\nSimpan dengan aman! 🔐"},
    "admin_notif_paid":     {"en": "✅ Order *#{order_id}* paid & delivered!\nUser: @{username}\n📦 Product: {product_name}\nQuantity: {qty} accounts\nStatus: Delivered", "id": "✅ Pesanan *#{order_id}* terbayar & dikirim!\nPengguna: @{username}\n📦 Produk: {product_name}\nJumlah: {qty} akun\nStatus: Dikirim"},
    "stock_insufficient":   {"en": "⚠️ Payment successful for Order *#{order_id}*!\n\nHowever, there are not enough accounts in stock. Admin will process this manually shortly.", "id": "⚠️ Pembayaran berhasil untuk Pesanan *#{order_id}*!\n\nNamun stok sedang kurang. Admin akan memprosesnya secara manual segera."},
    "admin_stock_warning":  {"en": "⚠️ WARNING: Order *#{order_id}* paid but OUT OF STOCK!\nUser: @{username}\n📦 Product: {product_name}\nQuantity: {qty} accounts\nPlease process manually!", "id": "⚠️ PERINGATAN: Pesanan *#{order_id}* lunas tapi STOK HABIS!\nPengguna: @{username}\n📦 Produk: {product_name}\nJumlah: {qty} akun\nSilakan proses manual!"},
    "order_expired":        {"en": "⏰ Your order *#{order_id}* has expired.", "id": "⏰ Pesanan Anda *#{order_id}* telah kadaluarsa."},
    "order_cancelled_notify": {"en": "❌ Your order *#{order_id}* has been cancelled.", "id": "❌ Pesanan Anda *#{order_id}* telah dibatalkan."},

    # Commands & Usages
    "cmd_delproduct_usage":   {"en": "💡 Use: `/delproduct <id>`", "id": "💡 Gunakan: `/delproduct <id>`"},
    "cmd_editproduct_usage":  {"en": "*✏️ EDIT PRODUCT*\n\nUse: `/editproduct <id> <field>=<value>`\n\n*Fields:* name, price, description, stock_type, stock_count, duration, is_active\n\n*Examples:*\n`/editproduct 1 price=15000`\n`/editproduct 1 name=Leonardo Pro`\n`/editproduct 1 is_active=0` (deactivate)", "id": "*✏️ EDIT PRODUK*\n\nGunakan: `/editproduct <id> <field>=<nilai>`\n\n*Medan:* name, price, description, stock_type, stock_count, duration, is_active\n\n*Contoh:*\n`/editproduct 1 price=15000`\n`/editproduct 1 name=Leonardo Pro`\n`/editproduct 1 is_active=0` (nonaktif)"},
    "cmd_addproduct_usage":   {"en": "💡 Format: `/addproduct ProductName|Price|Description`\n\n*Examples:*\n`/addproduct Leonardo|10000|Leonardo AI Account`\n`/addproduct GSuite|100000|GSuite 30 days`", "id": "💡 Format: `/addproduct NamaProduk|Harga|Deskripsi`\n\n*Contoh:*\n`/addproduct Canva|1000|Canva Pro 1 Bulan`"},
    "cmd_setprice_usage":     {"en": "💡 Use: `/setprice <product_id> <new_price>`\n\n*Example:*\n`/setprice 1 15000`", "id": "💡 Gunakan: `/setprice <product_id> <harga_baru>`\n\n*Contoh:* `/setprice 1 15000`"},
    "cmd_broadcast_usage":     {"en": "💡 Use: `/broadcast <message>`\n\n*Example:* `/broadcast Weekend promo 20% off!`", "id": "💡 Gunakan: `/broadcast <pesan>`\n\n*Contoh:* `/broadcast Promo diskon 20%!`"},
    "cmd_addadmin_usage":     {"en": "💡 Use: `/addadmin <telegram_user_id>`\n\n*Example:* `/addadmin 123456789`\n\n💡 To find ID: Forward a message to @userinfobot", "id": "💡 Gunakan: `/addadmin <telegram_user_id>`\n\n*Contoh:* `/addadmin 123456789`\n\n💡 Untuk cari ID: Forward pesan ke @userinfobot"},
    "cmd_removeadmin_usage":  {"en": "💡 Use: `/removeadmin <telegram_user_id>`\n\n⚠️ Cannot remove the main admin.", "id": "💡 Gunakan: `/removeadmin <telegram_user_id>`\n\n⚠️ Tidak dapat menghapus admin utama."},
    "date_label":             {"en": "📅 Date", "id": "📅 Tanggal"},
    "status_label_header":    {"en": "📊 Status", "id": "📊 Status"},

    # REFERRAL SYSTEM
    "btn_referral":           {"en": "🔗 Referral Program", "id": "🔗 Program Referral"},
    "referral_title":         {"en": "*🔗 REFERRAL PROGRAM*", "id": "*🔗 PROGRAM REFERRAL*"},
    "referral_code_label":    {"en": "🔑 Your Referral Code", "id": "🔑 Kode Referral Anda"},
    "referral_share":         {"en": "📢 Share this link to invite friends:", "id": "📢 Bagikan tautan ini untuk mengajak teman:"},
    "referral_link":          {"en": "🔗 Referral Link", "id": "🔗 Tautan Referral"},
    "referral_count":         {"en": "👥 Total Referrals", "id": "👥 Total Referral"},
    "referral_bonus":         {"en": "💰 Referral Bonus", "id": "💰 Bonus Referral"},
    "referral_claimed":       {"en": "✅ Bonus claimed!", "id": "✅ Bonus berhasil diklaim!"},
    "referral_already_claimed": {"en": "⚠️ You already claimed the referral bonus.", "id": "⚠️ Anda sudah mengklaim bonus referral."},
    "referral_invalid":       {"en": "❌ Invalid referral code.", "id": "❌ Kode referral tidak valid."},
    "referral_self":          {"en": "❌ You cannot use your own referral code.", "id": "❌ Anda tidak bisa menggunakan kode referral sendiri."},
    "referral_used_code":     {"en": "🔗 Use referral code on first purchase:", "id": "🔗 Gunakan kode referral saat pembelian pertama:"},
    "referral_stats":         {"en": "*📊 Referral Stats*", "id": "*📊 Statistik Referral*"},
    "referral_list_empty":    {"en": "❌ No referrals yet.", "id": "❌ Belum ada referral."},
    "btn_use_referral":       {"en": "🔗 Use Referral Code", "id": "🔗 Gunakan Kode Referral"},
    "referral_enter_code":    {"en": "📝 Send your referral code:", "id": "📝 Kirimkan kode referral Anda:"},
    "referral_applied":       {"en": "✅ Referral code *{code}* applied!", "id": "✅ Kode referral *{code}* berhasil diterapkan!"},
    "referral_claim_bonus_btn": {"en": "🎁 Claim Bonus", "id": "🎁 Klaim Bonus"},

    # PURCHASE DETAILS
    "btn_purchase_detail":    {"en": "📋 Purchase Detail", "id": "📋 Detail Pembelian"},
    "purchase_detail_title":  {"en": "*📋 PURCHASE DETAIL*", "id": "*📋 DETAIL PEMBELIAN*"},
    "purchase_detail_order":  {"en": "🆔 Order ID", "id": "🆔 ID Pesanan"},
    "purchase_detail_product": {"en": "📦 Product", "id": "📦 Produk"},
    "purchase_detail_qty":    {"en": "🔢 Quantity", "id": "🔢 Jumlah"},
    "purchase_detail_total":  {"en": "💰 Total Paid", "id": "💰 Total Bayar"},
    "purchase_detail_status": {"en": "📊 Status", "id": "📊 Status"},
    "purchase_detail_date":   {"en": "📅 Date", "id": "📅 Tanggal"},
    "purchase_detail_accounts": {"en": "🔐 Accounts Delivered", "id": "🔐 Akun Diterima"},
    "purchase_detail_voucher": {"en": "🎟️ Voucher Used", "id": "🎟️ Voucher Digunakan"},
    "purchase_detail_discount": {"en": "💸 Discount", "id": "💸 Diskon"},
    "no_purchase_details":    {"en": "❌ No purchase details available.", "id": "❌ Detail pembelian belum tersedia."},
    "btn_download_again":     {"en": "📥 Download Again", "id": "📥 Download Ulang"},

    # FEEDBACK / KRITIK SARAN
    "btn_feedback":           {"en": "💬 Feedback", "id": "💬 Kritik & Saran"},
    "feedback_title":         {"en": "*💬 FEEDBACK*", "id": "*💬 KRITIK & SARAN*"},
    "feedback_category":      {"en": "🏷️ Category", "id": "🏷️ Kategori"},
    "feedback_saran":         {"en": "💡 Suggestion", "id": "💡 Saran"},
    "feedback_kritik":        {"en": "🔴 Complaint", "id": "🔴 Keluhan"},
    "feedback_bugs":          {"en": "🐛 Bug Report", "id": "🐛 Laporan Bug"},
    "feedback_lainnya":       {"en": "📝 Other", "id": "📝 Lainnya"},
    "feedback_select_cat":    {"en": "👇 Select category:", "id": "👇 Pilih kategori:"},
    "feedback_send_msg":      {"en": "📝 Send your feedback message:", "id": "📝 Kirimkan pesan kritik/saran Anda:"},
    "feedback_sent":          {"en": "✅ Feedback sent! Admin will review it.", "id": "✅ Feedback terkirim! Admin akan meninjaunya."},
    "feedback_thanks":        {"en": "🙏 Thank you for your feedback!", "id": "🙏 Terima kasih atas feedback Anda!"},
    "feedback_list_title":    {"en": "*💬 FEEDBACK LIST*", "id": "*💬 DAFTAR FEEDBACK*"},
    "feedback_no_items":      {"en": "❌ No feedback yet.", "id": "❌ Belum ada feedback."},
    "feedback_reply_prompt":  {"en": "📝 Send your reply:", "id": "📝 Kirimkan balasan Anda:"},
    "feedback_reply_sent":    {"en": "✅ Reply sent to user!", "id": "✅ Balasan terkirim ke pengguna!"},
    "feedback_reply_to_user": {"en": "*💬 Admin Reply*\n\nYour feedback has been reviewed:\n\n{reply}", "id": "*💬 Balasan Admin*\n\nFeedback Anda telah ditinjau:\n\n{reply}"},

    # USER MANAGEMENT (ADMIN)
    "btn_user_management":    {"en": "👥 User Management", "id": "👥 Kelola Pengguna"},
    "user_mgmt_title":        {"en": "*👥 USER MANAGEMENT*", "id": "*👥 KELOLA PENGGUNA*"},
    "user_detail_title":      {"en": "*👤 USER DETAIL*", "id": "*👤 DETAIL PENGGUNA*"},
    "user_banned":            {"en": "🚫 User BANNED", "id": "🚫 Pengguna DIBLOKIR"},
    "user_ban_reason":        {"en": "📝 Reason", "id": "📝 Alasan"},
    "user_total_orders":      {"en": "📦 Total Orders", "id": "📦 Total Pesanan"},
    "user_total_spent":       {"en": "💰 Total Spent", "id": "💰 Total Belanja"},
    "user_joined":            {"en": "📅 Joined", "id": "📅 Bergabung"},
    "user_last_seen":         {"en": "🕐 Last Seen", "id": "🕐 Terakhir Aktif"},
    "user_ban_btn":           {"en": "🚫 Ban User", "id": "🚫 Blokir Pengguna"},
    "user_unban_btn":         {"en": "✅ Unban User", "id": "✅ Buka Blokir"},
    "user_banned_success":    {"en": "✅ User {id} has been banned.", "id": "✅ Pengguna {id} telah diblokir."},
    "user_unbanned_success":  {"en": "✅ User {id} has been unbanned.", "id": "✅ Blokir pengguna {id} telah dibuka."},
    "user_ban_reason_prompt": {"en": "📝 Send the ban reason:", "id": "📝 Kirimkan alasan pemblokiran:"},
    "banned_alert":           {"en": "⚠️ Your account has been blocked. Contact admin for more info.", "id": "⚠️ Akun Anda telah diblokir. Hubungi admin untuk info lebih lanjut."},
    "admin_feedback_list":    {"en": "*💬 FEEDBACK MANAGEMENT*", "id": "*💬 KELOLA FEEDBACK*"},

    # Navigation buttons (new)
    "btn_detail_history":     {"en": "📋 Detail History", "id": "📋 Riwayat Detail"},
    "btn_back_to_history":    {"en": "⬅️ Back to History", "id": "⬅️ Kembali ke Riwayat"},

    # REFERRAL COMMISSION SYSTEM
    "commission_balance":      {"en": "💰 Commission Balance", "id": "💰 Saldo Komisi"},
    "commission_earned":       {"en": "📈 Total Earned", "id": "📈 Total Diperoleh"},
    "commission_rate_label":   {"en": "📊 Commission Rate", "id": "📊 Rate Komisi"},
    "commission_history":      {"en": "*💰 COMMISSION HISTORY*", "id": "*💰 RIWAYAT KOMISI*"},
    "commission_from":         {"en": "👤 from", "id": "👤 dari"},
    "commission_on_order":     {"en": "📦 on order", "id": "📦 pada pesanan"},
    "commission_no_history":   {"en": "❌ No commission history yet.", "id": "❌ Belum ada riwayat komisi."},
    "commission_notif":        {"en": "🎉 You earned *Rp {amount}* commission from {name}'s purchase! (Order #{order_id})", "id": "🎉 Anda memperoleh komisi *Rp {amount}* dari pembelian {name}! (Pesanan #{order_id})"},

    # Withdrawal
    "withdraw_title":          {"en": "*💸 WITHDRAWAL*", "id": "*💸 PENCAIRAN DANA*"},
    "withdraw_balance":        {"en": "💰 Available Balance", "id": "💰 Saldo Tersedia"},
    "withdraw_min":            {"en": "💸 Minimum withdrawal", "id": "💸 Pencairan minimum"},
    "withdraw_btn":            {"en": "💸 Withdraw", "id": "💸 Tarik Dana"},
    "withdraw_bank_prompt":    {"en": "🏦 Send your *bank name* (e.g. BCA, Mandiri, BRI):", "id": "🏦 Kirimkan *nama bank* Anda (contoh: BCA, Mandiri, BRI):"},
    "withdraw_account_prompt": {"en": "🔢 Send your *account number*:", "id": "🔢 Kirimkan *nomor rekening* Anda:"},
    "withdraw_name_prompt":    {"en": "👤 Send your *account holder name*:", "id": "👤 Kirimkan *nama pemegang rekening*:"},
    "withdraw_amount_prompt":  {"en": "💰 Send withdrawal *amount* (Rp):", "id": "💰 Kirimkan *jumlah* pencairan (Rp):"},
    "withdraw_success":        {"en": "✅ Withdrawal request sent! Admin will process it shortly.", "id": "✅ Permintaan pencairan terkirim! Admin akan segera memprosesnya."},
    "withdraw_pending":        {"en": "⏳ Waiting", "id": "⏳ Menunggu"},
    "withdraw_approved":       {"en": "✅ Approved", "id": "✅ Disetujui"},
    "withdraw_rejected":       {"en": "❌ Rejected", "id": "❌ Ditolak"},
    "withdraw_insufficient":   {"en": "❌ Insufficient balance. Your balance: Rp {balance}", "id": "❌ Saldo tidak cukup. Saldo Anda: Rp {balance}"},
    "withdraw_below_min":      {"en": "❌ Minimum withdrawal is Rp {min}. Your balance: Rp {balance}", "id": "❌ Pencairan minimum adalah Rp {min}. Saldo Anda: Rp {balance}"},
    "withdraw_request_sent":   {"en": "✅ Withdrawal request #{id} sent!", "id": "✅ Permintaan pencairan #{id} terkirim!"},
    "withdraw_history":        {"en": "*💸 WITHDRAWAL HISTORY*", "id": "*💸 RIWAYAT PENCAIRAN*"},
    "withdraw_no_history":     {"en": "❌ No withdrawal history.", "id": "❌ Belum ada riwayat pencairan."},
    "withdraw_detail":         {"en": "💸 #{id} | Rp {amount} | {status}\n🏦 {bank} - {account} ({name})\n📅 {date}", "id": "💸 #{id} | Rp {amount} | {status}\n🏦 {bank} - {account} ({name})\n📅 {date}"},
    "withdraw_notif":          {"en": "💸 New withdrawal request!\nUser: {name} (ID: {user_id})\nAmount: Rp {amount}\n🏦 {bank} - {account} ({acc_name})", "id": "💸 Permintaan pencairan baru!\nPengguna: {name} (ID: {user_id})\nJumlah: Rp {amount}\n🏦 {bank} - {account} ({acc_name})"},
    "withdraw_approved_notif": {"en": "✅ Your withdrawal request #{id} has been approved!\nAmount: Rp {amount} has been sent to your account.", "id": "✅ Permintaan pencairan #{id} telah disetujui!\nJumlah: Rp {amount} telah dikirim ke rekening Anda."},
    "withdraw_rejected_notif": {"en": "❌ Your withdrawal request #{id} has been rejected.\nReason: {reason}", "id": "❌ Permintaan pencairan #{id} ditolak.\nAlasan: {reason}"},
    "btn_withdraw":            {"en": "💸 Withdraw", "id": "💸 Tarik Dana"},
    "btn_commission_history":  {"en": "💰 Commission History", "id": "💰 Riwayat Komisi"},

    # Admin — Commission Settings
    "admin_commission_title":  {"en": "*⚙️ COMMISSION SETTINGS*", "id": "*⚙️ PENGATURAN KOMISI*"},
    "admin_commission_rate":   {"en": "📊 Commission Rate", "id": "📊 Rate Komisi"},
    "admin_min_withdrawal":    {"en": "💸 Min. Withdrawal", "id": "💸 Min. Pencairan"},
    "admin_set_commission":    {"en": "⚙️ Set Commission %", "id": "⚙️ Atur Komisi %"},
    "admin_set_min_withdraw":  {"en": "⚙️ Set Min. Withdrawal", "id": "⚙️ Atur Min. Pencairan"},
    "admin_commission_updated":{"en": "✅ Commission rate updated to {percent}%!", "id": "✅ Rate komisi diperbarui ke {percent}%!"},
    "admin_min_withdraw_updated":{"en": "✅ Min. withdrawal updated to Rp {amount}!", "id": "✅ Min. pencairan diperbarui ke Rp {amount}!"},

    # Admin — Withdrawal Management
    "admin_withdrawal_title":  {"en": "*💸 WITHDRAWAL REQUESTS*", "id": "*💸 PERMINTAAN PENCAIRAN*"},
    "admin_withdrawal_pending":{"en": "*⏳ PENDING WITHDRAWALS*", "id": "*⏳ PENCAIRAN PENDING*"},
    "admin_no_withdrawals":    {"en": "❌ No pending withdrawal requests.", "id": "❌ Tidak ada permintaan pencairan pending."},
    "admin_withdraw_detail":   {"en": "💸 *WITHDRAWAL #{id}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n👤 {name} (ID: `{user_id}`)\n🏦 Bank: *{bank}*\n🔢 Account: `{account}`\n📛 Name: *{acc_name}*\n💰 Amount: *Rp {amount}*\n📊 Status: *{status}*\n📅 {date}\n━━━━━━━━━━━━━━━━━━━━━━━━",
                                 "id": "💸 *PENCAIRAN #{id}*\n━━━━━━━━━━━━━━━━━━━━━━━━\n👤 {name} (ID: `{user_id}`)\n🏦 Bank: *{bank}*\n🔢 Rekening: `{account}`\n📛 Nama: *{acc_name}*\n💰 Jumlah: *Rp {amount}*\n📊 Status: *{status}*\n📅 {date}\n━━━━━━━━━━━━━━━━━━━━━━━━"},
    "admin_approve_withdraw":  {"en": "✅ Approve", "id": "✅ Setujui"},
    "admin_reject_withdraw":   {"en": "❌ Reject", "id": "❌ Tolak"},
    "btn_commission_settings": {"en": "⚙️ Commission Settings", "id": "⚙️ Pengaturan Komisi"},
    "btn_withdrawal_requests": {"en": "💸 Withdrawal Requests", "id": "💸 Permintaan Pencairan"},

    # Pre-Order System
    "preorder_label":          {"en": "⏳ Pre-Order", "id": "⏳ Pre-Order"},
    "preorder_stock_text":    {"en": "⏳ PRE-ORDER (Proses Manual)", "id": "⏳ PRE-ORDER (Proses Manual)"},
    "preorder_paid_buyer":     {"en": "⏳ *PEMBAYARAN PRE-ORDER BERHASIL!*\n━━━━━━━━━━━━━━━━━━━━━━━━\n🆔 Pesanan: #{order_id}\n📦 Produk: *{product_name}*\n🔢 Jumlah: {qty} akun\n💰 Total: Rp {total}\n📊 Status: *⏳ Sedang Diproses Admin*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nℹ️ Pesanan Pre-Order Anda telah berhasil dibayar dan sedang diproses oleh Admin.\nData produk akan dikirimkan otomatis di sini setelah selesai diproses. Terima kasih! 🙏",
                                "id": "⏳ *PEMBAYARAN PRE-ORDER BERHASIL!*\n━━━━━━━━━━━━━━━━━━━━━━━━\n🆔 Pesanan: #{order_id}\n📦 Produk: *{product_name}*\n🔢 Jumlah: {qty} akun\n💰 Total: Rp {total}\n📊 Status: *⏳ Sedang Diproses Admin*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nℹ️ Pesanan Pre-Order Anda telah berhasil dibayar dan sedang diproses oleh Admin.\nData produk akan dikirimkan otomatis di sini setelah selesai diproses. Terima kasih! 🙏"},
    "btn_pending_preorders":   {"en": "⏳ Pre-Orders Pending", "id": "⏳ Pesanan Pre-Order"},
}
