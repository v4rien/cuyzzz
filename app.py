import streamlit as st
import requests
import time
import socket
import re
import cloudscraper
import io 
import random
import string
import requests.packages.urllib3.util.connection as urllib3_cn
from datetime import datetime

# --- FIX IPV4 ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- KONFIGURASI TELEGRAM ---
TG_TOKEN_ACCOUNT = "8700720215:AAHQiJq1E4yznkAp2C8CV-AGNLcskvkhFNE"
TG_TOKEN_VIDEO = "8607515924:AAGLrYdFV5JhbY9mxChRFynDcztGgPL6DLs"
TG_CHAT_ID = "1146892371"

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Multi-Tasker", page_icon="🚀", layout="wide") 

st.title("🚀 Sjinn AI - Multi Task Generator")

# =====================================================================
# --- AUTO-UPDATE SIDEBAR STATE ---
# =====================================================================
if "pending_account_update" in st.session_state:
    acc_data = st.session_state.pop("pending_account_update")
    
    # Update State UI Widget
    st.session_state["u_email_input"] = acc_data["email"]
    st.session_state["chk_pass_widget"] = True
    
    # Update Variable Logic Internal
    st.session_state["u_email"] = acc_data["email"]
    st.session_state["u_pass"] = acc_data["password"]
    st.session_state["use_same_pass"] = True
# =====================================================================

# --- FUNGSI KIRIM NOTIFIKASI AKUN ---
def send_telegram_notification(email, password, credits):
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
        url = f"https://api.telegram.org/bot{TG_TOKEN_ACCOUNT}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        st.error(f"Gagal kirim Notif Akun: {e}")

# --- FUNGSI KIRIM VIDEO ---
def send_telegram_video(video_url, caption=""):
    try:
        r_get = requests.get(video_url)
        if r_get.status_code == 200:
            video_bytes = io.BytesIO(r_get.content)
            url = f"https://api.telegram.org/bot{TG_TOKEN_VIDEO}/sendVideo"
            files = {'video': ('generated_video.mp4', video_bytes, 'video/mp4')}
            data = {"chat_id": TG_CHAT_ID, "caption": caption, "supports_streaming": "true"}
            
            r_post = requests.post(url, data=data, files=files, timeout=120)
            if r_post.status_code == 200:
                return True, "Berhasil"
            else:
                return False, f"Telegram Error: {r_post.text}"
        return False, "Gagal download video dari source."
    except Exception as e:
        return False, f"System Error: {e}"

# --- FUNGSI AUTO CREATE ACCOUNT ---
def process_auto_create():
    status_container = st.status("🛠️ Sedang Membuat Akun Baru...", expanded=True)
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False})
        
        # 1. GENERATE RANDOM EMAIL
        chars = string.ascii_lowercase + string.digits
        random_name = ''.join(random.choice(chars) for _ in range(8))
        email_address = f"{random_name}@emailqu.com"
        
        status_container.write(f"📧 Menggunakan Email: **{email_address}**")

        # 2. REGISTER TO SJINN
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
        
        # 3. POLLING EMAIL DARI EMAILQU.COM
        final_token = None
        for i in range(20): 
            time.sleep(3)
            try:
                url_check = f"https://emailqu.com/api/public/emails/{email_address}"
                r_check = scraper.get(url_check, timeout=10)
                
                if r_check.status_code == 200:
                    data_check = r_check.json()
                    if data_check.get("success") and data_check.get("emails"):
                        for mail in data_check["emails"]:
                            body_text = mail.get("body_text", "")
                            body_html = mail.get("body_html", "")
                            
                            token_match = re.search(r'token=([a-zA-Z0-9]{64})', body_text)
                            if not token_match:
                                token_match = re.search(r'token=([a-zA-Z0-9]{64})', body_html)
                                
                            if token_match:
                                final_token = token_match.group(1)
                                break
                if final_token: 
                    status_container.write("🔍 Token ditemukan!")
                    break
            except Exception as e:
                pass
            
        if not final_token:
            status_container.update(label="❌ Timeout! Email verifikasi tidak masuk.", state="error")
            return None, None

        # 4. VERIFY ACCOUNT
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

# --- SIDEBAR (INPUT AKUN DIPERBAIKI) ---
with st.sidebar:
    st.header("Account Config")
    st.caption("Akun yang sedang aktif digunakan:")
    
    # Pastikan state widget terinisialisasi di awal agar tidak kosong
    if "u_email_input" not in st.session_state:
        st.session_state["u_email_input"] = st.session_state.get("u_email", "")
    
    # HAPUS parameter value=, biarkan Streamlit mengambil dari session_state
    email_input = st.text_input("Email", key="u_email_input")
    st.session_state["u_email"] = email_input # Sinkronkan ke variabel internal

    if "chk_pass_widget" not in st.session_state:
        st.session_state["chk_pass_widget"] = st.session_state.get("use_same_pass", True)

    # HAPUS parameter value=
    is_checked = st.checkbox("Password same as email", key="chk_pass_widget")
    st.session_state["use_same_pass"] = is_checked

    # Logika Input Password Khusus
    if not st.session_state["use_same_pass"]:
        if "u_pass_input" not in st.session_state:
            st.session_state["u_pass_input"] = st.session_state.get("u_pass", "")
        pass_input = st.text_input("Password", type="password", key="u_pass_input")
        st.session_state["u_pass"] = pass_input
    else:
        pass_input = email_input
        st.session_state["u_pass"] = email_input

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
        target_pass = st.session_state.get("u_pass", "")
        
        if not target_email:
            st.error("Email kosong! Silakan isi manual di sidebar atau buat akun baru di Tab Auto Create.")
            return

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://sjinn.ai/login"
        })

        log_status = st.status("🚀 Memulai Sistem...", expanded=True)

        # 1. LOGIN
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
        
        try:
            r_info = session.get("https://sjinn.ai/api/get_user_account")
            if r_info.status_code == 200:
                bal = r_info.json().get('data', {}).get('balances', 0)
                st.session_state["user_credits"] = bal
                credits_placeholder.info(f"**Sisa Credits Akun:** {bal}", icon="💰")
        except: pass

        # 2. UPLOAD
        log_status.write("📤 Mengupload Gambar Master...")
        file_uuid = None
        max_retries_upload = 3
        
        for attempt in range(max_retries_upload):
            try:
                uploaded_file.seek(0)
                mime_type = uploaded_file.type
                r_init = session.post("https://sjinn.ai/api/upload_file", json={"content_type": mime_type})
                
                if r_init.status_code == 200:
                    data_up = r_init.json().get("data", {})
                    signed_url = data_up.get("signed_url")
                    uuid_temp = data_up.get("file_name")
                    
                    if signed_url and uuid_temp:
                        r_put = requests.put(signed_url, data=uploaded_file, headers={"Content-Type": mime_type, "Content-Length": str(uploaded_file.size)})
                        if r_put.status_code == 200:
                            file_uuid = uuid_temp
                            log_status.write(f"✅ Upload Sukses (Percobaan {attempt+1})")
                            break
            except Exception as e:
                log_status.write(f"⚠️ Gagal Upload (Percobaan {attempt+1}): {e}")
            time.sleep(2)

        if not file_uuid:
            log_status.update(label="❌ Gagal Upload Fatal!", state="error")
            st.error("Gagal mengupload gambar setelah 3x percobaan. Sistem dihentikan.")
            return

        log_status.write("⏳ Menunggu sinkronisasi file (3 detik)...")
        time.sleep(3) 

        # 3. KIRIM TASK
        session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
        tasks_submitted = 0
        progress_bar = st.progress(0)
        
        if "generated_batch" not in st.session_state:
            st.session_state["generated_batch"] = []
        else:
            st.session_state["generated_batch"] = [] 
        
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
                if i < loop_count: time.sleep(delay_sec) 
            except: pass

        # 4. MONITORING
        st.divider()
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
                            st.session_state["generated_batch"].append({
                                "url": vid_url,
                                "prompt": prompt_input,
                                "id": tid
                            })
            except: pass
        
        log_status.update(label="✅ Selesai!", state="complete", expanded=False)
        st.balloons()
        st.rerun()

    # --- TOMBOL START ---
    if st.button("MULAI BATCH GENERATE", type="primary", use_container_width=True):
        process_batch()

    # --- HASIL GENERATE & SEND TO TELEGRAM ---
    if "generated_batch" in st.session_state and st.session_state["generated_batch"]:
        st.divider()
        st.subheader("🎉 Hasil Generate Batch Terakhir")
        
        results = st.session_state["generated_batch"]
        res_cols = st.columns(3)
        
        for idx, item in enumerate(results):
            with res_cols[idx % 3]:
                st.video(item["url"])
                
                btn_col1, btn_col2 = st.columns([1,1])
                with btn_col1:
                    st.link_button("⬇️ Unduh", item["url"], use_container_width=True)
                with btn_col2:
                    if st.button("✈️ Telegram", key=f"gen_tg_{item['id']}"):
                        with st.spinner("Mengupload..."):
                            success, msg = send_telegram_video(item["url"], f"Prompt: {item['prompt']}")
                            if success:
                                st.toast("✅ Video Terkirim!")
                            else:
                                st.error(msg)

        st.divider()
        if st.button("✈️ KIRIM SEMUA VIDEO KE TELEGRAM", type="secondary", use_container_width=True):
            progress_text = "Sedang mengirim semua video..."
            my_bar = st.progress(0, text=progress_text)
            
            success_count = 0
            for idx, item in enumerate(results):
                success, _ = send_telegram_video(item["url"], f"Batch Video #{idx+1}\nPrompt: {item['prompt']}")
                if success: success_count += 1
                my_bar.progress((idx + 1) / len(results))
                time.sleep(1)
            
            st.success(f"Selesai! {success_count}/{len(results)} video terkirim.")


# --- TAB 2: AUTO CREATE ACCOUNT ---
with tab2:
    st.subheader("⚡ Auto Register & Verify Account")
    st.info("Akun yang berhasil dibuat akan otomatis mengisi sidebar dan dikirim ke Telegram Bot Anda.", icon="✈️")
    
    if "new_account_log" in st.session_state:
        acc_data = st.session_state["new_account_log"]
        
        st.success(f"✅ **Akun Berhasil Dibuat** ({acc_data['time']})")
        
        c_email, c_pass = st.columns(2)
        with c_email:
            st.caption("📧 Email (Hover untuk copy)")
            st.code(acc_data['email'], language="text") 
        with c_pass:
            st.caption("🔑 Password (Hover untuk copy)")
            st.code(acc_data['pass'], language="text")
        
        st.divider()
    
    col_auto1, col_auto2 = st.columns([1, 2])
    
    with col_auto1:
        if st.button("🛠️ Generate Akun Baru", type="primary", use_container_width=True):
            new_email, new_pass = process_auto_create()
            if new_email:
                # 1. Simpan Log untuk Tab 2
                st.session_state["new_account_log"] = {
                    "email": new_email,
                    "pass": new_pass,
                    "time": datetime.now().strftime("%H:%M:%S")
                }
                
                # 2. Siapkan Pending State untuk Sidebar
                st.session_state["pending_account_update"] = {
                    "email": new_email,
                    "password": new_pass
                }
                
                # 3. Cek saldo pakai email baru
                check_credits(manual_email=new_email, manual_pass=new_pass)
                
                # 4. Rerun agar State dieksekusi di atas
                st.rerun()

# --- TAB 3: ACCOUNT GALLERY ---
with tab3:
    st.write("Klik tombol di bawah untuk memuat semua video yang pernah Anda buat di akun ini.")
    
    if st.button("🔄 Refresh / Muat Gallery", use_container_width=True):
        target_email = st.session_state.get("u_email", "")
        target_pass = st.session_state.get("u_pass", "")

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
                            st.session_state["gallery_data"] = all_videos
                    else:
                        st.error("Gagal mengambil data riwayat.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan koneksi: {e}")

    # --- RENDER GALLERY ---
    if "gallery_data" in st.session_state and st.session_state["gallery_data"]:
        videos = st.session_state["gallery_data"]
        st.write(f"Ditemukan **{len(videos)}** video.")
        gal_cols = st.columns(3)
        
        for idx, vid in enumerate(videos):
            with gal_cols[idx % 3]:
                with st.container(border=True):
                    if vid.get("status") == 1:
                        video_url = vid.get("output_url")
                        prompt_txt = vid.get('input', {}).get('prompt', 'N/A')
                        
                        st.video(video_url)
                        st.caption(f"Prompt: {prompt_txt}")
                        
                        gb_col1, gb_col2 = st.columns([1,1])
                        with gb_col1:
                            st.link_button("⬇️ Unduh", video_url, use_container_width=True)
                        with gb_col2:
                            if st.button("✈️ Telegram", key=f"gal_tg_{vid.get('task_id')}"):
                                with st.spinner("Mengupload..."):
                                    success, msg = send_telegram_video(video_url, f"From Gallery\nPrompt: {prompt_txt}")
                                    if success:
                                        st.toast("✅ Video Terkirim!")
                                    else:
                                        st.error(msg)
                    else:
                        st.info(f"Video Status: {vid.get('status')} (Proses/Gagal)")
        
        st.divider()
        if st.button("✈️ KIRIM SEMUA VIDEO (GALLERY) KE TELEGRAM", type="secondary", use_container_width=True):
            if "gallery_data" in st.session_state and st.session_state["gallery_data"]:
                videos = st.session_state["gallery_data"]
                progress_text = "Sedang mengirim semua video dari gallery..."
                my_bar = st.progress(0, text=progress_text)
                
                success_count = 0
                for idx, vid in enumerate(videos):
                    if vid.get("status") == 1:
                        video_url = vid.get("output_url")
                        prompt_txt = vid.get('input', {}).get('prompt', 'N/A')
                        
                        success, _ = send_telegram_video(video_url, f"Gallery Batch #{idx+1}\nPrompt: {prompt_txt}")
                        if success: success_count += 1
                    
                    my_bar.progress((idx + 1) / len(videos))
                    time.sleep(1)
                
                st.success(f"Selesai! {success_count}/{len(videos)} video terkirim.")
