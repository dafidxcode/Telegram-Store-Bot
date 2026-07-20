"""Translation strings for EN (English) and MS (Bahasa Melayu).

Covers ALL bot text: home, products, buy flow, orders, admin panel, poller notifications.
Each user has their own language preference stored in the DB.
"""

T = {
    # ── Greetings ──────────────────────────────────────────────────────────
    "good_morning":    {"en": "Good Morning",              "ms": "Selamat Pagi"},
    "good_afternoon":  {"en": "Good Afternoon",            "ms": "Selamat Tengah Hari"},
    "good_evening":    {"en": "Good Evening",              "ms": "Selamat Petang"},
    "good_night":      {"en": "Good Night",                "ms": "Selamat Malam"},

    # ── Home ───────────────────────────────────────────────────────────────
    "welcome":         {"en": "Welcome to *{shop}*.",      "ms": "Selamat datang ke *{shop}*."},
    "account_stats":   {"en": "👤 ACCOUNT STATS",          "ms": "👤 STATISTIK AKAUN"},
    "username":        {"en": "Username",                   "ms": "Nama Pengguna"},
    "total_orders":    {"en": "📦 Total Orders : {n} transactions", "ms": "📦 Jumlah Pesanan : {n} transaksi"},
    "bot_stats":       {"en": "📊 BOT STATS",              "ms": "📊 STATISTIK BOT"},
    "accounts_sold":   {"en": "📨 Accounts Sold : {n}",    "ms": "📨 Akaun Dijual : {n}"},
    "active_products": {"en": "🛍 Active Products : {n}",  "ms": "🛍 Produk Aktif : {n}"},
    "total_users":     {"en": "👥 Total Users : {n}",      "ms": "👥 Jumlah Pengguna : {n}"},
    "stock_per":       {"en": "📦 STOCK PER PRODUCT",      "ms": "📦 STOK SETIAP PRODUK"},
    "no_products":     {"en": "  No products yet",         "ms": "  Tiada produk lagi"},
    "where_start":     {"en": "💡 Where to start?",        "ms": "💡 Mula dari mana?"},
    "hint_buy":        {"en": "• Buy account → Product List",      "ms": "• Beli akaun → Senarai Produk"},
    "hint_orders":     {"en": "• Check transactions → Order History", "ms": "• Semak transaksi → Sejarah Pesanan"},

    # ── Navigation buttons ─────────────────────────────────────────────────
    "btn_product_list":  {"en": "🛍️ Product List",         "ms": "🛍️ Senarai Produk"},
    "btn_check_stock":   {"en": "📦 Check Stock",          "ms": "📦 Semak Stok"},
    "btn_order_history": {"en": "📋 Order History",        "ms": "📋 Sejarah Pesanan"},
    "btn_home":          {"en": "🏠 Home",                 "ms": "🏠 Utama"},
    "btn_back":          {"en": "⬅️ Back",                 "ms": "⬅️ Kembali"},
    "btn_cancel_pay":    {"en": "❌ Cancel Payment",       "ms": "❌ Batal Bayaran"},
    "btn_lang_en":       {"en": "🌐 English",              "ms": "🌐 English"},
    "btn_lang_ms":       {"en": "🌐 Bahasa Melayu",       "ms": "🌐 Bahasa Melayu"},
    "btn_admin_panel":   {"en": "⚙️ Admin Panel",          "ms": "⚙️ Panel Admin"},

    # ── Product list ───────────────────────────────────────────────────────
    "product_list_title": {"en": "*🛍️ PRODUCT LIST*",      "ms": "*🛍️ SENARAI PRODUK*"},
    "no_products_yet":    {"en": "*🛍️ PRODUCT LIST*\n\nNo products available yet.", "ms": "*🛍️ SENARAI PRODUK*\n\nTiada produk tersedia lagi."},
    "select_product":     {"en": "Select a product to order:", "ms": "Pilih produk untuk dipesan:"},
    "price":              {"en": "💰 Price",                "ms": "💰 Harga"},
    "stock":              {"en": "📦 Stock",                "ms": "📦 Stok"},
    "accounts":           {"en": "accounts",                "ms": "akaun"},
    "unlimited":          {"en": "Unlimited",               "ms": "Tanpa Had"},
    "duration":           {"en": "⏰ Duration",             "ms": "⏰ Tempoh"},

    # ── Stock info ─────────────────────────────────────────────────────────
    "stock_info":         {"en": "*📦 Stock Info*",         "ms": "*📦 Maklumat Stok*"},
    "total_stock":        {"en": "📦 Total",                "ms": "📦 Jumlah"},

    # ── Order history (user) ───────────────────────────────────────────────
    "order_history":      {"en": "*📋 Order History*",      "ms": "*📋 Sejarah Pesanan*"},
    "no_orders":          {"en": "No orders yet. Buy now! 🛒", "ms": "Tiada pesanan lagi. Beli sekarang! 🛒"},
    "buy_again":          {"en": "🔄 Buy Again",            "ms": "🔄 Beli Lagi"},

    # ── Help ───────────────────────────────────────────────────────────────
    "help_title":         {"en": "*❓ Help*",               "ms": "*❓ Bantuan*"},
    "help_how_buy":       {"en": "*How to Buy:*",           "ms": "*Cara Membeli:*"},
    "help_step1":         {"en": "1. Click *🛍️ Product List*", "ms": "1. Tekan *🛍️ Senarai Produk*"},
    "help_step2":         {"en": "2. Select a product",     "ms": "2. Pilih produk"},
    "help_step3":         {"en": "3. Choose quantity",      "ms": "3. Pilih kuantiti"},
    "help_step4":         {"en": "4. Confirm & pay via QRIS", "ms": "4. Sahkan & bayar melalui QRIS"},
    "help_step5":         {"en": "5. Account is delivered automatically", "ms": "5. Akaun dihantar secara automatik"},
    "help_commands":      {"en": "*Commands:*",             "ms": "*Arahan:*"},
    "help_cmd_start":     {"en": "/start - 🏠 Main menu",  "ms": "/start - 🏠 Menu utama"},
    "help_cmd_produk":    {"en": "/produk - 🛍️ View products", "ms": "/produk - 🛍️ Lihat produk"},
    "help_cmd_beli":      {"en": "/beli - 🛒 Buy account",  "ms": "/beli - 🛒 Beli akaun"},
    "help_cmd_stock":     {"en": "/stock - 📦 Check stock", "ms": "/stock - 📦 Semak stok"},
    "help_cmd_myorders":  {"en": "/myorders - 📋 Order history", "ms": "/myorders - 📋 Sejarah pesanan"},
    "help_cmd_cancel":    {"en": "/cancel - ❌ Cancel process", "ms": "/cancel - ❌ Batal proses"},
    "help_lang_tip":      {"en": "💡 Tap the button below to switch language!", "ms": "💡 Tekan butang di bawah untuk tukar bahasa!"},

    # ── Cancel payment ─────────────────────────────────────────────────────
    "cancel_no_pending":  {"en": "No pending payment to cancel.", "ms": "Tiada bayaran tertanggung untuk dibatalkan."},
    "cancelled":          {"en": "Payment cancelled.",      "ms": "Bayaran dibatalkan."},
    "session_expired":    {"en": "Session expired. /beli to start again.", "ms": "Sesi tamat tempoh. /beli untuk mula semula."},

    # ══════════════════════════════════════════════════════════════════════
    # BUY FLOW
    # ══════════════════════════════════════════════════════════════════════

    # Select product
    "select_product_title": {"en": "*🛍️ Select Product*",  "ms": "*🛍️ Pilih Produk*"},
    "choose_product":       {"en": "Choose a product to purchase:", "ms": "Pilih produk untuk dibeli:"},
    "cancel":               {"en": "❌ Cancel",             "ms": "❌ Batal"},

    # Out of stock
    "out_of_stock":         {"en": "Sorry, *{name}* is out of stock.\n\nPlease choose another product or wait for restock.", "ms": "Maaf, *{name}* telah kehabisan stok.\n\nSila pilih produk lain atau tunggu stok baharu."},
    "choose_another":       {"en": "Please choose another product or wait for restock.", "ms": "Sila pilih produk lain atau tunggu stok baharu."},

    # Product not available
    "product_not_available": {"en": "Product is not available.", "ms": "Produk tidak tersedia."},
    "no_products_available": {"en": "No products available yet. Please wait for admin to add products.", "ms": "Tiada produk tersedia lagi. Sila tunggu admin menambah produk."},

    # Product detail
    "product_details":      {"en": "*📋 Product Details*", "ms": "*📋 Butiran Produk*"},
    "pricing":              {"en": "*💰 Pricing*",         "ms": "*💰 Harga*"},
    "pricing_per_account":  {"en": "All quantities    : Rp {price} / account", "ms": "Semua kuantiti  : Rp {price} / akaun"},
    "stock_heading":        {"en": "*📦 Stock*",           "ms": "*📦 Stok*"},
    "available":            {"en": "Available",            "ms": "Tersedia"},
    "minimum":              {"en": "Minimum",              "ms": "Minimum"},
    "your_order":           {"en": "*🛒 Your Order*",      "ms": "*🛒 Pesanan Anda*"},
    "quantity":             {"en": "Quantity",             "ms": "Kuantiti"},
    "total":                {"en": "Total",                "ms": "Jumlah"},

    # Cart buttons
    "enter_qty_manually":   {"en": "⌨️ Enter Quantity Manually", "ms": "⌨️ Masukkan Kuantiti Secara Manual"},
    "pay_qris":             {"en": "💳 Pay via QRIS - Rp {total}", "ms": "💳 Bayar melalui QRIS - Rp {total}"},

    # Manual quantity input
    "enter_quantity_title": {"en": "*⌨️ Enter Quantity*",  "ms": "*⌨️ Masukkan Kuantiti*"},
    "type_number":          {"en": "Type a number and send it.", "ms": "Taip nombor dan hantar."},
    "example_type":         {"en": "Example: type *{n}* to buy {n} accounts.", "ms": "Contoh: taip *{n}* untuk beli {n} akaun."},

    # Insufficient stock
    "insufficient_stock":   {"en": "Insufficient stock. Available: *{stock}* accounts.", "ms": "Stok tidak mencukupi. Tersedia: *{stock}* akaun."},
    "type_another_or_cancel": {"en": "Type another quantity or /cancel to abort.", "ms": "Taip kuantiti lain atau /cancel untuk membatalkan."},

    # Order confirmation
    "order_confirmation":   {"en": "*✅ Order Confirmation*", "ms": "*✅ Pengesahan Pesanan*"},
    "confirm_pay":          {"en": "✅ Confirm & Pay",      "ms": "✅ Sahkan & Bayar"},
    "proceed_payment":      {"en": "Proceed to payment?",   "ms": "Teruskan ke pembayaran?"},

    # Creating order
    "creating_order":       {"en": "⏳ Creating order & QRIS...", "ms": "⏳ Mencipta pesanan & QRIS..."},
    "creating_order_for":   {"en": "⏳ Creating order for *{name}* x{qty}...", "ms": "⏳ Mencipta pesanan untuk *{name}* x{qty}..."},

    # Order created (caption for QRIS photo)
    "order_created":        {"en": "✅ ORDER CREATED",      "ms": "✅ PESANAN DICIPTA"},
    "product_label":        {"en": "📦 Product",            "ms": "📦 Produk"},
    "quantity_label":       {"en": "🔢 Quantity",           "ms": "🔢 Kuantiti"},
    "accounts_label":       {"en": "accounts",              "ms": "akaun"},
    "status_label":         {"en": "⏳ Status",             "ms": "⏳ Status"},
    "expires_label":        {"en": "⏰ Expires",            "ms": "⏰ Tamat Tempoh"},
    "scan_qris":            {"en": "📱 Scan the QRIS above to pay.", "ms": "📱 Imbas QRIS di atas untuk membayar."},
    "auto_deliver":         {"en": "Account will be delivered automatically after payment. 🤖", "ms": "Akaun akan dihantar secara automatik selepas pembayaran. 🤖"},
    "check_myorders":       {"en": "Check status: /myorders", "ms": "Semak status: /myorders"},

    # QRIS text fallback
    "qr_processing":        {"en": "QRIS image is being generated. 🔄\nCheck status at /myorders.", "ms": "Imej QRIS sedang dijana. 🔄\nSemak status di /myorders."},

    # Cancel order button
    "btn_cancel_order":     {"en": "❌ Cancel Payment",     "ms": "❌ Batal Bayaran"},

    # ══════════════════════════════════════════════════════════════════════
    # ADMIN PANEL
    # ══════════════════════════════════════════════════════════════════════

    # Panel main
    "admin_panel":          {"en": "*⚙️ ADMIN PANEL*",     "ms": "*⚙️ PANEL ADMIN*"},
    "dashboard":            {"en": "*📊 Dashboard*",        "ms": "*📊 Papan Pemuka*"},
    "stock_ready":          {"en": "📦 Stock Ready",        "ms": "📦 Stok Sedia"},
    "sold":                 {"en": "✅ Sold",               "ms": "✅ Dijual"},
    "pending_orders":       {"en": "⏳ Pending Orders",     "ms": "⏳ Pesanan Tertanggung"},
    "total_products":       {"en": "🛍️ Total Products",     "ms": "🛍️ Jumlah Produk"},
    "per_product_stock":    {"en": "*📦 PER-PRODUCT STOCK*","ms": "*📦 STOK SETIAP PRODUK*"},
    "select_admin_menu":    {"en": "Select admin menu below 👇", "ms": "Pilih menu admin di bawah 👇"},
    "no_products_admin":    {"en": "  No products",         "ms": "  Tiada produk"},

    # Admin buttons
    "btn_view_products":    {"en": "📦 View Products",      "ms": "📦 Lihat Produk"},
    "btn_stock_info":       {"en": "📊 Stock Info",         "ms": "📊 Maklumat Stok"},
    "btn_view_orders":      {"en": "📋 View Orders",        "ms": "📋 Lihat Pesanan"},
    "btn_admin_list":       {"en": "👥 Admin List",         "ms": "👥 Senarai Admin"},
    "btn_add_product":      {"en": "➕ Add Product",        "ms": "➕ Tambah Produk"},
    "btn_add_stock":        {"en": "📥 Add Stock",          "ms": "📥 Tambah Stok"},
    "btn_change_price":     {"en": "💰 Change Price",       "ms": "💰 Tukar Harga"},
    "btn_broadcast":        {"en": "📣 Broadcast",          "ms": "📣 Siaran"},
    "btn_add_admin":        {"en": "👤 Add Admin",          "ms": "👤 Tambah Admin"},
    "btn_remove_admin":     {"en": "👤 Remove Admin",       "ms": "👤 Buang Admin"},
    "btn_back_to_admin":    {"en": "⬅️ Back to Admin Panel","ms": "⬅️ Kembali ke Panel Admin"},
    "btn_back_to_menu":     {"en": "🏠 Back to Menu",       "ms": "🏠 Kembali ke Menu"},

    # Admin — product list
    "admin_product_list":   {"en": "*📦 PRODUCT LIST*",     "ms": "*📦 SENARAI PRODUK*"},
    "admin_no_products":    {"en": "*📦 Product List*\n\nNo products yet.", "ms": "*📦 Senarai Produk*\n\nTiada produk lagi."},
    "admin_price":          {"en": "💰 Price",              "ms": "💰 Harga"},
    "admin_stock":          {"en": "📦 Stock",              "ms": "📦 Stok"},

    # Admin — stock info
    "admin_stock_info":     {"en": "*📊 STOCK INFO*",       "ms": "*📊 MAKLUMAT STOK*"},
    "admin_total_ready":    {"en": "📦 Total Ready Stock",  "ms": "📦 Jumlah Stok Sedia"},
    "admin_pending_orders": {"en": "⏳ Pending Orders",     "ms": "⏳ Pesanan Tertanggung"},

    # Admin — orders
    "admin_recent_orders":  {"en": "*📋 RECENT ORDERS*",    "ms": "*📋 PESANAN TERKINI*"},
    "admin_no_orders":      {"en": "*📋 RECENT ORDERS*\n\nNo orders yet.", "ms": "*📋 PESANAN TERKINI*\n\nTiada pesanan lagi."},
    "admin_pending_orders_title": {"en": "*⏳ PENDING ORDERS*", "ms": "*⏳ PESANAN TERTANGGUNG*"},
    "admin_no_pending":     {"en": "*⏳ PENDING ORDERS*\n\nNo pending orders.", "ms": "*⏳ PESANAN TERTANGGUNG*\n\nTiada pesanan tertanggung."},
    "admin_paid_orders":    {"en": "*✅ PAID ORDERS*",      "ms": "*✅ PESANAN DIBAYAR*"},
    "admin_no_paid":        {"en": "*✅ PAID ORDERS*\n\nNo paid orders.", "ms": "*✅ PESANAN DIBAYAR*\n\nTiada pesanan dibayar."},
    "btn_all":              {"en": "📋 All",                "ms": "📋 Semua"},
    "btn_pending":          {"en": "⏳ Pending",            "ms": "⏳ Tertanggung"},
    "btn_paid":             {"en": "✅ Paid",               "ms": "✅ Dibayar"},

    # Admin — admin list
    "admin_list_title":     {"en": "*👥 ADMIN LIST*",       "ms": "*👥 SENARAI ADMIN*"},
    "admin_total":          {"en": "📊 Total",              "ms": "📊 Jumlah"},
    "admins":               {"en": "admins",                "ms": "admin"},

    # Admin — add product interactive
    "admin_add_product":    {"en": "*➕ ADD PRODUCT*",      "ms": "*➕ TAMBAH PRODUK*"},
    "admin_send_name":      {"en": "📝 Send the *product name* now.\n\nExample: `Leonardo AI Account`", "ms": "📝 Hantar *nama produk* sekarang.\n\nContoh: `Leonardo AI Account`"},
    "admin_product_name":   {"en": "📦 Product name",       "ms": "📦 Nama produk"},
    "admin_send_price":     {"en": "📝 Send the *price* (number only).\nExample: `15000`", "ms": "📝 Hantar *harga* (nombor sahaja).\nContoh: `15000`"},
    "admin_send_desc":      {"en": "📝 Send the *description* (or send `-` to skip).", "ms": "📝 Hantar *penerangan* (atau hantar `-` untuk langkau)."},
    "admin_name_empty":     {"en": "Name cannot be empty. Send product name:", "ms": "Nama tidak boleh kosong. Hantar nama produk:"},
    "admin_price_number":   {"en": "Price must be a number. Send again:", "ms": "Harga mestilah nombor. Hantar semula:"},
    "admin_price_positive": {"en": "Price must be > 0. Send again:", "ms": "Harga mestilah > 0. Hantar semula:"},

    # Admin — product added/updated/deleted
    "admin_product_added":  {"en": "*✅ Product added!*",   "ms": "*✅ Produk ditambah!*"},
    "admin_product_updated": {"en": "*✅ Product updated!*","ms": "*✅ Produk dikemas kini!*"},
    "admin_product_deleted": {"en": "*🗑️ Product deleted!*","ms": "*🗑️ Produk dipadam!*"},
    "admin_id":             {"en": "🆔 ID",                 "ms": "🆔 ID"},
    "admin_name":           {"en": "📦 Name",               "ms": "📦 Nama"},
    "admin_description":    {"en": "📝 Description",        "ms": "📝 Penerangan"},
    "admin_active":         {"en": "✅ Active",             "ms": "✅ Aktif"},
    "admin_inactive":       {"en": "❌ Inactive",           "ms": "❌ Tidak Aktif"},

    # Admin — change price
    "admin_change_price":   {"en": "*💰 CHANGE PRICE*",     "ms": "*💰 TUKAR HARGA*"},
    "admin_select_product": {"en": "Select product to change price:", "ms": "Pilih produk untuk menukar harga:"},
    "admin_current_price":  {"en": "Current price",         "ms": "Harga semasa"},
    "admin_send_new_price": {"en": "📝 Send the *new price* now.\n\nExample: `15000`", "ms": "📝 Hantar *harga baharu* sekarang.\n\nContoh: `15000`"},
    "admin_new_price":      {"en": "💰 New price",          "ms": "💰 Harga baharu"},

    # Admin — broadcast
    "admin_broadcast":      {"en": "*📣 BROADCAST*",        "ms": "*📣 SIARAN*"},
    "admin_send_message":   {"en": "📝 Send the *message* to broadcast now.\n\nExample: `Weekend promo 20% off!`", "ms": "📝 Hantar *mesej* untuk siaran sekarang.\n\nContoh: `Weekend promo 20% off!`"},
    "admin_broadcast_done": {"en": "*✅ Broadcast complete!*", "ms": "*✅ Siaran selesai!*"},
    "admin_sent":           {"en": "📤 Sent",               "ms": "📤 Dihantar"},
    "admin_failed":         {"en": "❌ Failed",             "ms": "❌ Gagal"},
    "users":                {"en": "users",                 "ms": "pengguna"},

    # Admin — add admin
    "admin_add_admin":      {"en": "*👤 ADD ADMIN*",        "ms": "*👤 TAMBAH ADMIN*"},
    "admin_send_user_id":   {"en": "📝 Send the *Telegram User ID* now.\n\n💡 To find ID: Forward a message to @userinfobot\n\nExample: `123456789`", "ms": "📝 Hantar *ID Pengguna Telegram* sekarang.\n\n💡 Untuk cari ID: Forward mesej ke @userinfobot\n\nContoh: `123456789`"},
    "admin_id_number":      {"en": "ID must be a number. Send again:", "ms": "ID mestilah nombor. Hantar semula:"},
    "admin_already_admin":  {"en": "ID `{id}` is already an admin.", "ms": "ID `{id}` sudah menjadi admin."},
    "admin_added":          {"en": "*✅ Admin added!*",     "ms": "*✅ Admin ditambah!*"},
    "admin_total_admins":   {"en": "👥 Total admins",       "ms": "👥 Jumlah admin"},

    # Admin — remove admin
    "admin_remove_admin":   {"en": "*👤 REMOVE ADMIN*",     "ms": "*👤 BUANG ADMIN*"},
    "admin_select_admin":   {"en": "Select admin to remove:", "ms": "Pilih admin untuk dibuang:"},
    "admin_no_remove":      {"en": "*👤 REMOVE ADMIN*\n\nNo additional admins to remove.", "ms": "*👤 BUANG ADMIN*\n\nTiada admin tambahan untuk dibuang."},
    "admin_cannot_remove":  {"en": "Cannot remove the main admin.", "ms": "Tidak boleh membuang admin utama."},
    "admin_removed":        {"en": "*✅ Admin removed!*",   "ms": "*✅ Admin dibuang!*"},

    # Admin — add stock
    "admin_add_stock":      {"en": "*📥 ADD STOCK*",        "ms": "*📥 TAMBAH STOK*"},
    "admin_select_stock_product": {"en": "Select product to add stock to:", "ms": "Pilih produk untuk menambah stok:"},
    "admin_no_active_products": {"en": "*📥 ADD STOCK*\n\nNo active products yet. Add a product first.", "ms": "*📥 TAMBAH STOK*\n\nTiada produk aktif lagi. Tambah produk terlebih dahulu."},
    "admin_method1":        {"en": "*Method 1:* Send a .txt file\nFormat per line: `email:password`", "ms": "*Kaedah 1:* Hantar fail .txt\nFormat setiap baris: `email:password`"},
    "admin_method2":        {"en": "*Method 2:* Paste directly in chat\n`email1:password1`\n`email2:password2`", "ms": "*Kaedah 2:* Tampal terus dalam chat\n`email1:password1`\n`email2:password2`"},
    "admin_send_now":       {"en": "Send now! 📤",          "ms": "Hantar sekarang! 📤"},
    "admin_current_stock":  {"en": "Current stock",         "ms": "Stok semasa"},
    "admin_stock_added":    {"en": "*✅ Stock added to {name}*!", "ms": "*✅ Stok ditambah ke {name}*!"},
    "admin_added_count":    {"en": "📥 Added",              "ms": "📥 Ditambah"},
    "admin_product_stock":  {"en": "📦 Product stock",      "ms": "📦 Stok produk"},
    "admin_send_more":      {"en": "💡 Send more stock or click Back below.", "ms": "💡 Hantar lebih banyak stok atau tekan Kembali di bawah."},
    "admin_stock_not_added": {"en": "*⚠️ No stock added to {name}*", "ms": "*⚠️ Tiada stok ditambah ke {name}*"},
    "admin_check_format":   {"en": "Please check format:\n`email:password`\none account per line.", "ms": "Sila semak format:\n`email:password`\nseakaun setiap baris."},
    "admin_try_again":      {"en": "🔄 Try Again",          "ms": "🔄 Cuba Semula"},
    "admin_add_more":       {"en": "📥 Add More",           "ms": "📥 Tambah Lagi"},
    "admin_stock_file_added": {"en": "*✅ Stock added successfully!*", "ms": "*✅ Stok berjaya ditambah!*"},
    "admin_stock_file_none": {"en": "*⚠️ No stock added*\n\nCheck format: `email:password` per line.", "ms": "*⚠️ Tiada stok ditambah*\n\nSemak format: `email:password` setiap baris."},
    "admin_only_txt":       {"en": "Only .txt files are accepted.", "ms": "Hanya fail .txt diterima."},
    "admin_failed_read":    {"en": "Failed to read file. Please try again.", "ms": "Gagal membaca fail. Sila cuba semula."},

    # Admin — generic
    "admin_access_denied":  {"en": "Access denied.",        "ms": "Akses ditolak."},
    "admin_something_wrong": {"en": "Something went wrong. Start again.", "ms": "Sesuatu telah berlaku. Mula semula."},
    "admin_try_again":      {"en": "Sorry, something went wrong. Please try again.", "ms": "Maaf, sesuatu telah berlaku. Sila cuba semula."},
    "admin_no_changes":     {"en": "No changes made. Use field=value.", "ms": "Tiada perubahan. Guna field=nilai."},
    "admin_price_must_be_number": {"en": "Price must be a number.", "ms": "Harga mestilah nombor."},
    "admin_price_gt_zero":  {"en": "Price must be greater than 0.", "ms": "Harga mestilah lebih besar dari 0."},
    "admin_id_must_number": {"en": "ID must be a number.",  "ms": "ID mestilah nombor."},
    "admin_not_found":      {"en": "Product ID `{id}` not found.", "ms": "ID Produk `{id}` tidak ditemui."},
    "admin_id_not_admin":   {"en": "ID `{id}` is not an admin.", "ms": "ID `{id}` bukan admin."},
    "admin_price_updated":  {"en": "*✅ Price updated!*",   "ms": "*✅ Harga dikemas kini!*"},
    "admin_price_per_account": {"en": "💰 New price: *Rp {price}/account*", "ms": "💰 Harga baharu: *Rp {price}/akaun*"},

    # ══════════════════════════════════════════════════════════════════════
    # POLLER NOTIFICATIONS (sent to users)
    # ══════════════════════════════════════════════════════════════════════

    "payment_success":      {"en": "✅ PAYMENT SUCCESSFUL!", "ms": "✅ PEMBAYARAN BERJAYA!"},
    "order_label":          {"en": "🆔 Order",              "ms": "🆔 Pesanan"},
    "quantity_label_short": {"en": "🔢 Quantity",           "ms": "🔢 Kuantiti"},
    "total_label":          {"en": "💰 Total",              "ms": "💰 Jumlah"},
    "file_attached":        {"en": "📁 Your account file is attached.\nKeep it safe! 🔐", "ms": "📁 Fail akaun anda dilampirkan.\nSimpannya dengan selamat! 🔐"},
    "admin_notif_paid":     {"en": "✅ Order *#{order_id}* paid & delivered!\nUser: @{username}\n📦 Product: {product_name}\nQuantity: {qty} accounts\nStatus: Delivered", "ms": "✅ Pesanan *#{order_id}* telah dibayar & dihantar!\nPengguna: @{username}\n📦 Produk: {product_name}\nKuantiti: {qty} akaun\nStatus: Dihantar"},
    "stock_insufficient":   {"en": "Payment successful for Order *#{order_id}*!\n\nHowever, there are not enough accounts in stock. Admin will process this manually shortly.", "ms": "Pembayaran berjaya untuk Pesanan *#{order_id}*!\n\nNamun, stok akaun tidak mencukupi. Admin akan memproses ini secara manual sebentar lagi."},
    "admin_stock_warning":  {"en": "⚠️ WARNING: Order *#{order_id}* paid but OUT OF STOCK!\nUser: @{username}\n📦 Product: {product_name}\nQuantity: {qty} accounts\nPlease process manually!", "ms": "⚠️ AMARAN: Pesanan *#{order_id}* telah dibayar tetapi STOK HABIS!\nPengguna: @{username}\n📦 Produk: {product_name}\nKuantiti: {qty} akaun\nSila proses secara manual!"},
    "order_expired":        {"en": "Your order *#{order_id}* has expired.", "ms": "Pesanan anda *#{order_id}* telah tamat tempoh."},
    "order_cancelled_notify": {"en": "Your order *#{order_id}* has been cancelled.", "ms": "Pesanan anda *#{order_id}* telah dibatalkan."},

    # ── New Keys (for commands and labels) ──────────────────────────────────
    "cmd_delproduct_usage":   {"en": "Use: `/delproduct <id>`", "ms": "Guna: `/delproduct <id>`"},
    "cmd_editproduct_usage":  {"en": "*✏️ EDIT PRODUCT*\n\nUse: `/editproduct <id> <field>=<value>`\n\n*Fields:* name, price, description, stock_type, stock_count, duration, is_active\n\n*Examples:*\n`/editproduct 1 price=15000`\n`/editproduct 1 name=Leonardo Pro`\n`/editproduct 1 is_active=0` (deactivate)", "ms": "*✏️ KEMAS KINI PRODUK*\n\nGuna: `/editproduct <id> <field>=<value>`\n\n*Medan:* name, price, description, stock_type, stock_count, duration, is_active\n\n*Contoh:*\n`/editproduct 1 price=15000`\n`/editproduct 1 name=Leonardo Pro`\n`/editproduct 1 is_active=0` (nyahaktif)"},
    "cmd_addproduct_usage":   {"en": "Format: `/addproduct ProductName|Price|Description`\n\n*Examples:*\n`/addproduct Leonardo|10000|Leonardo AI Account`\n`/addproduct GSuite|100000|GSuite 30 days`", "ms": "Format: `/addproduct NamaProduk|Harga|Penerangan`\n\n*Contoh:*\n`/addproduct Leonardo|10000|Akaun Leonardo AI`\n`/addproduct GSuite|100000|GSuite 30 hari`"},
    "cmd_setprice_usage":     {"en": "Use: `/setprice <product_id> <new_price>`\n\n*Example:*\n`/setprice 1 15000`", "ms": "Guna: `/setprice <product_id> <harga_baru>`\n\n*Contoh:*\n`/setprice 1 15000`"},
    "cmd_broadcast_usage":     {"en": "Use: `/broadcast <message>`\n\n*Example:* `/broadcast Weekend promo 20% off!`", "ms": "Guna: `/broadcast <mesej>`\n\n*Contoh:* `/broadcast Promo hujung minggu diskaun 20%!`"},
    "cmd_addadmin_usage":     {"en": "Use: `/addadmin <telegram_user_id>`\n\n*Example:* `/addadmin 123456789`\n\n💡 To find ID: Forward a message to @userinfobot", "ms": "Guna: `/addadmin <telegram_user_id>`\n\n*Contoh:* `/addadmin 123456789`\n\n💡 Untuk cari ID: Forward mesej ke @userinfobot"},
    "cmd_removeadmin_usage":  {"en": "Use: `/removeadmin <telegram_user_id>`\n\n⚠️ Cannot remove the main admin.", "ms": "Guna: `/removeadmin <telegram_user_id>`\n\n⚠️ Tidak boleh membuang admin utama."},
    "date_label":             {"en": "Date", "ms": "Tarikh"},
    "status_label_header":    {"en": "Status", "ms": "Status"},
}
