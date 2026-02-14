import streamlit as st
import requests
import time
import socket
import re
import cloudscraper
import requests.packages.urllib3.util.connection as urllib3_cn
from datetime import datetime

# --- FIX IPV4 ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- KONFIGURASI TELEGRAM ---
TELEGRAM_BOT_TOKEN = "8497569370:AAGgtCtPyYPBGBhdqGQQv-DVV7d8JPC69Wo"
TELEGRAM_CHAT_ID = "7779160370"

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Multi-Tasker", page_icon="🚀", layout="wide") 

st.title("🚀 Sjinn AI - Multi Task Generator")

# --- FUNGSI KIRIM KE TELEGRAM ---
def send_telegram_notification(email, password, credits):
    """Mengirim data akun ke Telegram Bot"""
    try:
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pesan = f"""
🚀 *NEW ACCOUNT CREATED!*
━━━━━━━━━━━━━━━━━━
📧 *Email:* `{email}`
🔑 *Password:* `{password}`
💰 *Credits:* {credits}
📅 *Time:* {waktu}
━━━━━━━━━━━━━━━━━━
_Sent from Sjinn Multi-Tasker_
        """
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        st.error(f"Gagal kirim Telegram: {e}")

# --- FUNGSI AUTO CREATE ACCOUNT ---
def process_auto_create():
    """Melakukan registrasi otomatis menggunakan cloudscraper & mailticking"""
    status_container = st.status("🛠️ Sedang Membuat Akun Baru...", expanded=True)
    
    try:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False}
        )
        
        base_url_mail = "https://www.mailticking.com"
        headers_mail = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": base_url_mail + "/",
            "Origin": base_url_mail
        }

        # 1. GET EMAIL
        status_container.write("📧 Requesting Temporary Email...")
        r_mail = scraper.post(f"{base_url_mail}/get-mailbox", json={"types": ["4"]}, headers=headers_mail)
        if r_mail.status_code != 200 or not r_mail.json().get("success"):
            status_container.update(label="❌ Gagal ambil email!", state="error")
            return None, None
            
        email_address = r_mail.json().get("email")
        status_container.write(f"✅ Email didapat: **{email_address}**")

        # 2. ACTIVATE EMAIL SESSION
        scraper.post(f"{base_url_mail}/activate-email", json={"email": email_address}, headers=headers_mail)
        
        # 3. GET SESSION TOKEN
        r_home = scraper.get(base_url_mail + "/", headers=headers_mail)
        match = re.search(r'data-code="([^"]+)"', r_home.text)
        if not match:
            status_container.update(label="❌ Gagal ambil session mail!", state="error")
            return None, None
        data_code = match.group(1)

        # 4. REGISTER TO SJINN
        status_container.write("📝 Mendaftar ke Sjinn.ai...")
        payload_reg = {"email": email_address, "password": email_address, "name": ""}
        headers_sjinn = {
            "Host": "sjinn.ai",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": "https://sjinn.ai",
            "Referer": "https://sjinn.ai/login"
        }
        
        r_reg = scraper.post("https://sjinn.ai/api/auth/register", json=payload_reg, headers=headers_sjinn)
        if r_reg.status_code not in [200, 201]:
            status_container.update(label=f"❌ Register Gagal: {r_reg.status_code}", state="error")
            st.error(r_reg.text)
            return None, None
            
        status_container.write("📨 Menunggu Email Verifikasi (Maks 60 detik)...")
        
        # 5. POLLING EMAIL
        message_code = None
        for i in range(20): 
            time.sleep(3)
            try:
                r_check = scraper.post(f"{base_url_mail}/get-emails?lang=", json={"email": email_address, "code": data_code}, headers=headers_mail)
                emails = r_check.json().get("emails", [])
                if emails:
                    for mail in emails:
                        if "sjinn.ai" in mail.get("FromEmail", "").lower():
                            message_code = mail.get("Code")
                            break
                if message_code: break
            except: pass
            
        if not message_code:
            status_container.update(label="❌ Timeout! Email tidak masuk.", state="error")
            return None, None

        # 6. GET TOKEN
        status_container.write("🔍 Mengekstrak Token Verifikasi...")
        r_view = scraper.get(f"{base_url_mail}/mail/view/{message_code}/", headers=headers_mail)
        token_match = re.search(r'token=([a-zA-Z0-9]{64})', r_view.text)
        
        if not token_match:
            status_container.update(label="❌ Token tidak ditemukan di email.", state="error")
            return None, None
            
        final_token = token_match.group(1)

        # 7. VERIFY ACCOUNT
        status_container.write("🔐 Memverifikasi Akun...")
        headers_verify = headers_sjinn.copy()
        if "Content-Type" in headers_verify: del headers_verify["Content-Type"]
        
        r_verify = scraper.get("https://sjinn.ai/api/auth/verify-email", params={"token": final_token, "email": email_address}, headers=headers_verify)
        
        if r_verify.status_code in [200, 201, 302]:
            status_container.update(label="🎉 Akun Berhasil Dibuat!", state="complete", expanded=False)
            send_telegram_notification(email_address, email_address, "Check in App")
            st.toast("✅ Notifikasi dikirim ke Telegram!", icon="✈️")
            return email_address, email_address 
        else:
            status_container.update(label=f"❌ Verifikasi Gagal: {r_verify.status_code}", state="error")
            return None, None
            
    except Exception as e:
        status_container.update(label=f"❌ Error System: {e}", state="error")
        return None, None

# --- FUNGSI CEK CREDITS ---
def check_credits(manual_email=None, manual_pass=None):
    if manual_email and manual_pass:
        email, password = manual_email, manual_pass
    else:
        email = st.session_state.get("u_email", "")
        if st.session_state.get("use_same_pass", True):
            password = email
        else:
            password = st.session_state.get("u_pass", "")

    if not email:
        st.warning("Email belum diisi!")
        return

    with st.spinner("Sedang Login & Cek Saldo..."):
        try:
            session_cred = requests.Session()
            r_csrf = session_cred.get("https://sjinn.ai/api/auth/csrf")
            csrf_token = r_csrf.json().get("csrfToken")
            
            payload = {
                "redirect": "false", "email": email, "password": password,
                "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
            }
            r_login = session_cred.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            if r_login.status_code == 200:
                r_info = session_cred.get("https://sjinn.ai/api/get_user_account")
                if r_info.status_code == 200:
                    data = r_info.json()
                    balance = data.get('data', {}).get('balances', 0)
                    st.session_state["user_credits"] = balance
                    st.toast("✅ Login Berhasil!", icon="🎉")
            else:
                st.session_state["user_credits"] = "Login Gagal"
                st.error("Login Gagal! Cek Email/Password.")
        except Exception as e:
            st.session_state["user_credits"] = "Error"
            st.error(f"Error Koneksi: {e}")

# --- SIDEBAR (INPUT AKUN) ---
with st.sidebar:
    st.header("Account Config")
    st.caption("Akun yang sedang aktif digunakan:")
    
    # 1. Email Logic
    def_email = st.session_state.get("u_email", "")
    email_input = st.text_input("Email", value=def_email, key="u_email_input")
    
    if email_input != st.session_state.get("u_email", ""):
        st.session_state["u_email"] = email_input

    # 2. Password Checkbox Logic
    if "use_same_pass" not in st.session_state:
        st.session_state["use_same_pass"] = True

    is_checked = st.checkbox(
        "Password same as email", 
        value=st.session_state["use_same_pass"], 
        key="chk_pass_widget"
    )
    st.session_state["use_same_pass"] = is_checked

    # 3. Password Input Logic
    if not st.session_state["use_same_pass"]:
        pass_input = st.text_input("Password", key="u_pass", type="password")
    else:
        pass_input = email_input

    st.write("") 
    
    if st.button("🚀 Login / Cek Data", use_container_width=True):
        check_credits()

# --- SISTEM TABS ---
tab1, tab2, tab3 = st.tabs(["🎥 Generate New", "⚡ Auto Create Account", "📚 Account Gallery"])

# --- TAB 1: GENERATE NEW ---
with tab1:
    credits_placeholder = st.empty()
    current_credits = st.session_state.get("user_credits", "---")
    credits_placeholder.info(f"**Sisa Credits Akun:** {current_credits}", icon="💰")
    
    st.write("") 

    c_prompt, c_count, c_delay = st.columns([4, 1, 1]) 
    
    with c_prompt:
        prompt_input = st.text_input("Prompt Video", value="", placeholder="Describe the motion...")
        
    with c_count:
        loop_count = st.number_input("Jumlah", min_value=1, max_value=50, value=1, step=1)
        
    with c_delay:
        delay_sec = st.number_input("Jeda (detik)", min_value=1, max_value=60, value=5, step=1)

    uploaded_file = st.file_uploader("Pilih Gambar (.png/.jpg)", type=['png', 'jpg', 'jpeg'])

    def process_batch():
        if not uploaded_file:
            st.warning("⚠️ Harap upload gambar dulu!")
            return
        
        target_email = st.session_state.get("u_email", "")
        target_pass = target_email if st.session_state.get("use_same_pass") else st.session_state.get("u_pass", "")
        
        if not target_email:
            st.error("Email kosong! Silakan isi manual di sidebar atau buat akun baru di Tab Auto Create.")
            return

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://sjinn.ai/login"
        })

        log_status = st.status("🚀 Memulai Sistem...", expanded=True)

        # LOGIN
        log_status.write("🔐 Sedang Login...")
        try:
            r_csrf = session.get("https://sjinn.ai/api/auth/csrf")
            csrf_token = r_csrf.json().get("csrfToken")
            
            payload = {
                "redirect": "false", "email": target_email, "password": target_pass,
                "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
            }
            r_login = session.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
            if r_login.status_code != 200:
                log_status.update(label="❌ Gagal Login!", state="error")
                st.error("Login gagal. Cek email/password.")
                return
        except Exception as e:
            st.error(f"Error Login: {e}")
            return
        
        # Update credits awal
        try:
            r_info = session.get("https://sjinn.ai/api/get_user_account")
            if r_info.status_code == 200:
                bal = r_info.json().get('data', {}).get('balances', 0)
                st.session_state["user_credits"] = bal
                credits_placeholder.info(f"**Sisa Credits Akun:** {bal}", icon="💰")
        except: pass

        # UPLOAD
        log_status.write("📤 Mengupload Gambar Master...")
        try:
            mime_type = uploaded_file.type
            r_init = session.post("https://sjinn.ai/api/upload_file", json={"content_type": mime_type})
            data_up = r_init.json().get("data", {})
            signed_url = data_up.get("signed_url")
            file_uuid = data_up.get("file_name")
            
            uploaded_file.seek(0)
            requests.put(signed_url, data=uploaded_file, headers={"Content-Type": mime_type, "Content-Length": str(uploaded_file.size)})
        except Exception as e:
            log_status.update(label="❌ Gagal Upload!", state="error")
            return

        # KIRIM TASK
        session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
        tasks_submitted = 0
        progress_bar = st.progress(0)
        
        for i in range(1, loop_count + 1):
            try:
                payload_task = {
                    "id": "sjinn-image-to-video",
                    "input": {"image_url": file_uuid, "prompt": prompt_input},
                    "mode": "template"
                }
                
                r_task = session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=payload_task)
                
                if r_task.status_code == 200:
                    log_status.write(f"➕ Task #{i} dikirim...")
                    tasks_submitted += 1
                    
                    try:
                        r_upd = session.get("https://sjinn.ai/api/get_user_account")
                        if r_upd.status_code == 200:
                            new_bal = r_upd.json().get('data', {}).get('balances', 0)
                            st.session_state["user_credits"] = new_bal
                            credits_placeholder.info(f"**Sisa Credits Akun:** {new_bal}", icon="💰")
                    except: pass
                
                progress_bar.progress(int((i / loop_count) * 100))
                
                if i < loop_count: 
                    time.sleep(delay_sec) 

            except: pass

        # MONITORING
        st.divider()
        result_cols = st.columns(3)
        completed_ids = set()
        start_wait = time.time()
        
        while len(completed_ids) < tasks_submitted:
            if time.time() - start_wait > 300: break
            time.sleep(5)
            try:
                r_check = session.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                if r_check.json().get("success"):
                    all_tasks = r_check.json()["data"].get("list", [])[:tasks_submitted]
                    for task in all_tasks:
                        status, vid_url, tid = task.get("status"), task.get("output_url"), task.get("task_id")
                        if status == 1 and tid not in completed_ids:
                            completed_ids.add(tid)
                            with result_cols[(len(completed_ids)-1)%3]:
                                st.video(vid_url)
                                st.link_button(f"Download #{len(completed_ids)}", vid_url, use_container_width=True)
            except: pass
        
        log_status.update(label="✅ Selesai!", state="complete", expanded=False)
        st.balloons()

    if st.button("MULAI BATCH GENERATE", type="primary", use_container_width=True):
        process_batch()

# --- TAB 2: AUTO CREATE ACCOUNT ---
with tab2:
    st.subheader("⚡ Auto Register & Verify Account")
    st.info("Akun yang berhasil dibuat akan otomatis dikirim ke Telegram Bot Anda.", icon="✈️")
    
    # --- MENAMPILKAN LOG HASIL GENERATE DENGAN TOMBOL COPY ---
    if "new_account_log" in st.session_state:
        acc_data = st.session_state["new_account_log"]
        
        st.success(f"✅ **Akun Berhasil Dibuat** ({acc_data['time']})")
        
        # Layout Kolom untuk Copy
        c_email, c_pass = st.columns(2)
        with c_email:
            st.caption("📧 Email (Hover untuk copy)")
            st.code(acc_data['email'], language="text") # st.code punya tombol copy built-in
        with c_pass:
            st.caption("🔑 Password (Hover untuk copy)")
            st.code(acc_data['pass'], language="text")
        
        st.divider()
    
    col_auto1, col_auto2 = st.columns([1, 2])
    
    with col_auto1:
        if st.button("🛠️ Generate Akun Baru", type="primary", use_container_width=True):
            new_email, new_pass = process_auto_create()
            if new_email:
                # 1. Update Variable Data Utama
                st.session_state["u_email"] = new_email
                st.session_state["u_pass"] = new_pass
                st.session_state["use_same_pass"] = True 

                # 2. SIMPAN LOG SUKSES
                st.session_state["new_account_log"] = {
                    "email": new_email,
                    "pass": new_pass,
                    "time": datetime.now().strftime("%H:%M:%S")
                }

                # 3. RESET WIDGET STATE
                if "u_email_input" in st.session_state:
                    del st.session_state["u_email_input"]
                if "chk_pass_widget" in st.session_state:
                    del st.session_state["chk_pass_widget"]
                
                # 4. Cek saldo otomatis
                check_credits(manual_email=new_email, manual_pass=new_pass)
                
                st.rerun()

# --- TAB 3: ACCOUNT GALLERY ---
with tab3:
    st.write("Klik tombol di bawah untuk memuat semua video yang pernah Anda buat di akun ini.")
    
    if st.button("🔄 Refresh / Muat Gallery", use_container_width=True):
        target_email = st.session_state.get("u_email", "")
        target_pass = target_email if st.session_state.get("use_same_pass") else st.session_state.get("u_pass", "")

        if not target_email:
            st.error("Silakan isi Email & Password di sidebar, lalu klik Login!")
        else:
            with st.spinner("Mengambil data dari server..."):
                session_gal = requests.Session()
                try:
                    r_csrf = session_gal.get("https://sjinn.ai/api/auth/csrf")
                    csrf_token = r_csrf.json().get("csrfToken")
                    payload = {"redirect": "false", "email": target_email, "password": target_pass, "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"}
                    session_gal.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
                    
                    r_info = session_gal.get("https://sjinn.ai/api/get_user_account")
                    if r_info.status_code == 200:
                        st.session_state["user_credits"] = r_info.json().get('data', {}).get('balances', 0)

                    r_list = session_gal.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                    
                    if r_list.json().get("success"):
                        all_videos = r_list.json()["data"].get("list", [])
                        if not all_videos:
                            st.info("Gallery kosong. Belum ada video yang ditemukan.")
                        else:
                            st.write(f"Ditemukan **{len(all_videos)}** video.")
                            gal_cols = st.columns(3)
                            for idx, vid in enumerate(all_videos):
                                with gal_cols[idx % 3]:
                                    with st.container(border=True):
                                        if vid.get("status") == 1:
                                            st.video(vid.get("output_url"))
                                            st.caption(f"Prompt: {vid.get('input', {}).get('prompt', 'N/A')}")
                                            st.link_button("Download ⬇️", vid.get("output_url"), use_container_width=True)
                                        else:
                                            st.info(f"Video Status: {vid.get('status')} (Proses/Gagal)")
                    else:
                        st.error("Gagal mengambil data riwayat.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan koneksi: {e}")
