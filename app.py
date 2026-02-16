import streamlit as st
import requests
import time
import socket
import re
import cloudscraper
import io 
import requests.packages.urllib3.util.connection as urllib3_cn
from datetime import datetime

# --- FIX IPV4 ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- KONFIGURASI TELEGRAM ---
TG_TOKEN_ACCOUNT = "8497569370:AAGgtCtPyYPBGBhdqGQQv-DVV7d8JPC69Wo"
TG_TOKEN_VIDEO = "7994485589:AAFRA_wJhn4Q4r8UHp_Egud5oEIw2GXcfPc"
TG_CHAT_ID = "7779160370"

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Multi-Tasker", page_icon="🚀", layout="wide") 

st.title("🚀 Sjinn AI - Multi Task Generator")

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

        # 2. ACTIVATE
        scraper.post(f"{base_url_mail}/activate-email", json={"email": email_address}, headers=headers_mail)
        
        # 3. GET SESSION
        r_home = scraper.get(base_url_mail + "/", headers=headers_mail)
        match = re.search(r'data-code="([^"]+)"', r_home.text)
        if not match: return None, None
        data_code = match.group(1)

        # 4. REGISTER
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
        if r_reg.status_code not in [200, 201]: return None, None
            
        status_container.write("📨 Menunggu Email Verifikasi (Maks 60 detik)...")
        
        # 5. POLLING
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
            
        if not message_code: return None, None

        # 6. GET TOKEN
        status_container.write("🔍 Mengekstrak Token Verifikasi...")
        r_view = scraper.get(f"{base_url_mail}/mail/view/{message_code}/", headers=headers_mail)
        token_match = re.search(r'token=([a-zA-Z0-9]{64})', r_view.text)
        if not token_match: return None, None
        final_token = token_match.group(1)

        # 7. VERIFY
        status_container.write("🔐 Memverifikasi Akun...")
        headers_verify = headers_sjinn.copy()
        if "Content-Type" in headers_verify: del headers_verify["Content-Type"]
        r_verify = scraper.get("https://sjinn.ai/api/auth/verify-email", params={"token": final_token, "email": email_address}, headers=headers_verify)
        
        if r_verify.status_code in [200, 201, 302]:
            status_container.update(label="🎉 Akun Berhasil Dibuat!", state="complete", expanded=False)
            send_telegram_notification(email_address, email_address, "Check in App")
            st.toast("✅ Notifikasi dikirim ke Telegram!", icon="✈️")
            return email_address, email_address 
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
            
            payload = {"redirect": "false", "email": email, "password": password, "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"}
            r_login = session_cred.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            if r_login.status_code == 200:
                r_info = session_cred.get("https://sjinn.ai/api/get_user_account")
                if r_info.status_code == 200:
                    balance = r_info.json().get('data', {}).get('balances', 0)
                    st.session_state["user_credits"] = balance
                    st.toast("✅ Login Berhasil!", icon="🎉")
            else:
                st.session_state["user_credits"] = "Login Gagal"
                st.error("Login Gagal! Cek Email/Password.")
        except Exception as e:
            st.session_state["user_credits"] = "Error"
            st.error(f"Error Koneksi: {e}")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Account Config")
    st.caption("Akun yang sedang aktif digunakan:")
    
    def_email = st.session_state.get("u_email", "")
    email_input = st.text_input("Email", value=def_email, key="u_email_input")
    
    if email_input != st.session_state.get("u_email", ""):
        st.session_state["u_email"] = email_input

    if "use_same_pass" not in st.session_state:
        st.session_state["use_same_pass"] = True

    is_checked = st.checkbox("Password same as email", value=st.session_state["use_same_pass"], key="chk_pass_widget")
    st.session_state["use_same_pass"] = is_checked

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
            st.error("Email kosong!")
            return

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Referer": "https://sjinn.ai/login"})

        log_status = st.status("🚀 Memulai Sistem...", expanded=True)
        log_status.write("🔐 Sedang Login...")
        
        try:
            r_csrf = session.get("https://sjinn.ai/api/auth/csrf")
            csrf_token = r_csrf.json().get("csrfToken")
            payload = {"redirect": "false", "email": target_email, "password": target_pass, "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"}
            r_login = session.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
            if r_login.status_code != 200:
                log_status.update(label="❌ Gagal Login!", state="error")
                return
        except: return
        
        # Upload Logic
        log_status.write("📤 Mengupload Gambar Master...")
        file_uuid = None
        for attempt in range(3):
            try:
                uploaded_file.seek(0)
                r_init = session.post("https://sjinn.ai/api/upload_file", json={"content_type": uploaded_file.type})
                if r_init.status_code == 200:
                    data_up = r_init.json().get("data", {})
                    signed_url, uuid_temp = data_up.get("signed_url"), data_up.get("file_name")
                    if signed_url:
                        r_put = requests.put(signed_url, data=uploaded_file, headers={"Content-Type": uploaded_file.type, "Content-Length": str(uploaded_file.size)})
                        if r_put.status_code == 200:
                            file_uuid = uuid_temp
                            break
            except: pass
            time.sleep(2)

        if not file_uuid:
            log_status.update(label="❌ Gagal Upload!", state="error")
            return

        log_status.write("⏳ Menunggu sinkronisasi (3 detik)...")
        time.sleep(3) 

        # Task Loop
        session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
        tasks_submitted = 0
        progress_bar = st.progress(0)
        
        # Clear previous batch result
        st.session_state["generated_batch"] = []
        
        for i in range(1, loop_count + 1):
            try:
                payload_task = {"id": "sjinn-image-to-video", "input": {"image_url": file_uuid, "prompt": prompt_input}, "mode": "template"}
                r_task = session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=payload_task)
                
                if r_task.status_code == 200:
                    log_status.write(f"➕ Task #{i} dikirim...")
                    tasks_submitted += 1
                progress_bar.progress(int((i / loop_count) * 100))
                if i < loop_count: time.sleep(delay_sec) 
            except: pass

        # Monitoring
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
                            # SAVE TO SESSION STATE
                            st.session_state["generated_batch"].append({"url": vid_url, "prompt": prompt_input, "id": tid})
            except: pass
        
        log_status.update(label="✅ Selesai!", state="complete", expanded=False)
        st.balloons()
        st.rerun()

    if st.button("MULAI BATCH GENERATE", type="primary", use_container_width=True):
        process_batch()

    # Tampilan Hasil Batch
    if "generated_batch" in st.session_state and st.session_state["generated_batch"]:
        st.divider()
        st.subheader("🎉 Hasil Generate Batch Terakhir")
        results = st.session_state["generated_batch"]
        res_cols = st.columns(3)
        for idx, item in enumerate(results):
            with res_cols[idx % 3]:
                st.video(item["url"])
                if st.button("✈️ Telegram", key=f"gen_tg_{item['id']}"):
                    with st.spinner("Mengupload..."):
                        success, msg = send_telegram_video(item["url"], f"Prompt: {item['prompt']}")
                        if success: st.toast("✅ Terkirim!"); 
                        else: st.error(msg)
        
        st.divider()
        if st.button("✈️ KIRIM SEMUA", type="secondary", use_container_width=True):
            bar = st.progress(0, "Mengirim...")
            for idx, item in enumerate(results):
                send_telegram_video(item["url"], f"Batch #{idx+1}\n{item['prompt']}")
                bar.progress((idx+1)/len(results))
            st.success("Selesai dikirim.")

# --- TAB 2: AUTO CREATE ---
with tab2:
    st.subheader("⚡ Auto Register")
    if "new_account_log" in st.session_state:
        acc_data = st.session_state["new_account_log"]
        st.success(f"✅ Akun Baru: {acc_data['time']}")
        c1, c2 = st.columns(2)
        with c1: st.code(acc_data['email'], language="text")
        with c2: st.code(acc_data['pass'], language="text")
        st.divider()
    
    if st.button("🛠️ Generate Akun Baru", type="primary", use_container_width=True):
        new_email, new_pass = process_auto_create()
        if new_email:
            st.session_state["u_email"] = new_email
            st.session_state["u_pass"] = new_pass
            st.session_state["use_same_pass"] = True 
            st.session_state["new_account_log"] = {"email": new_email, "pass": new_pass, "time": datetime.now().strftime("%H:%M:%S")}
            if "u_email_input" in st.session_state: del st.session_state["u_email_input"]
            if "chk_pass_widget" in st.session_state: del st.session_state["chk_pass_widget"]
            check_credits(manual_email=new_email, manual_pass=new_pass)
            st.rerun()

# --- TAB 3: ACCOUNT GALLERY (FIXED BUTTON) ---
with tab3:
    st.write("Klik Refresh untuk memuat video dari akun ini.")
    
    # 1. TOMBOL REFRESH -> HANYA UPDATE DATA
    if st.button("🔄 Refresh / Muat Gallery", use_container_width=True):
        target_email = st.session_state.get("u_email", "")
        target_pass = target_email if st.session_state.get("use_same_pass") else st.session_state.get("u_pass", "")

        if not target_email:
            st.error("Isi Email & Password dulu!")
        else:
            with st.spinner("Mengambil data..."):
                session_gal = requests.Session()
                try:
                    r_csrf = session_gal.get("https://sjinn.ai/api/auth/csrf")
                    csrf_token = r_csrf.json().get("csrfToken")
                    payload = {"redirect": "false", "email": target_email, "password": target_pass, "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"}
                    session_gal.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
                    
                    r_list = session_gal.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                    
                    if r_list.json().get("success"):
                        all_videos = r_list.json()["data"].get("list", [])
                        # SIMPAN KE SESSION STATE (PERSISTEN)
                        st.session_state["gallery_data"] = all_videos
                    else:
                        st.error("Gagal ambil data.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 2. RENDER GALLERY DI LUAR BLOK TOMBOL REFRESH
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
                            # TOMBOL KIRIM TELEGRAM (Sekarang bekerja karena data persisten)
                            if st.button("✈️ Telegram", key=f"gal_tg_{vid.get('task_id')}"):
                                with st.spinner("Mengupload ke Telegram..."):
                                    success, msg = send_telegram_video(video_url, f"From Gallery\nPrompt: {prompt_txt}")
                                    if success:
                                        st.toast("✅ Video Terkirim!", icon="✈️")
                                    else:
                                        st.error(msg)
                    else:
                        st.info(f"Status: {vid.get('status')} (Proses/Gagal)")
