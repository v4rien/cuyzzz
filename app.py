import streamlit as st
import requests
import time
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

# --- FIX IPV4 ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Multi-Tasker", page_icon="🚀", layout="wide") 

st.title("🚀 Sjinn AI - Multi Task Generator")

# --- FUNGSI CEK CREDITS (Dipanggil via Tombol Sidebar) ---
def check_credits():
    email = st.session_state.get("u_email", "")
    is_same = st.session_state.get("use_same_pass", True)
    
    if is_same:
        password = email
    else:
        password = st.session_state.get("u_pass", "")

    if not email:
        st.warning("Email belum diisi!")
        return

    with st.spinner("Sedang Login & Cek Saldo..."):
        try:
            session_cred = requests.Session()
            # 1. Login Flow
            r_csrf = session_cred.get("https://sjinn.ai/api/auth/csrf")
            csrf_token = r_csrf.json().get("csrfToken")
            
            payload = {
                "redirect": "false", "email": email, "password": password,
                "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
            }
            r_login = session_cred.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            if r_login.status_code == 200:
                # 2. Get Account Info
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

# --- SIDEBAR (PENGATURAN AKUN) ---
with st.sidebar:
    st.header("Account Config")
    
    email_input = st.text_input("Email", key="u_email")
    
    if "use_same_pass" not in st.session_state:
        st.session_state.use_same_pass = True

    if not st.session_state.use_same_pass:
        pass_input = st.text_input("Password", key="u_pass", type="password")
    else:
        pass_input = email_input

    st.checkbox("Password same as email", key="use_same_pass")
    
    st.write("") 
    
    if st.button("🚀 Login / Cek Data", type="primary", use_container_width=True):
        check_credits()

# --- SISTEM TABS ---
tab1, tab2 = st.tabs(["🎥 Generate New", "📚 Account Gallery"])

# --- TAB 1: GENERATE NEW ---
with tab1:
    # [MODIFIKASI] Tampilan Credits dalam Box (st.info)
    credits_placeholder = st.empty()
    current_credits = st.session_state.get("user_credits", "---")
    
    # Menggunakan st.info untuk membuat box berwarna
    credits_placeholder.info(f"**Sisa Credits Akun:** {current_credits}", icon="💰")
    
    st.write("") 

    # B. BAGIAN INPUT UTAMA
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

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://sjinn.ai/login"
        })

        log_status = st.status("🚀 Memulai Sistem...", expanded=True)

        # 1. LOGIN
        final_pass = email_input if st.session_state.use_same_pass else st.session_state.get("u_pass", "")
        
        log_status.write("🔐 Sedang Login...")
        try:
            r_csrf = session.get("https://sjinn.ai/api/auth/csrf")
            csrf_token = r_csrf.json().get("csrfToken")
            
            payload = {
                "redirect": "false", "email": email_input, "password": final_pass,
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
        
        # Update credits awal sebelum loop
        try:
            r_info = session.get("https://sjinn.ai/api/get_user_account")
            if r_info.status_code == 200:
                bal = r_info.json().get('data', {}).get('balances', 0)
                st.session_state["user_credits"] = bal
                # Update box credits real-time
                credits_placeholder.info(f"**Sisa Credits Akun:** {bal}", icon="💰")
        except: pass

        # 2. UPLOAD
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

        # 3. KIRIM TASK
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
                    
                    # Update Credits Real-time Setelah Kirim Task
                    try:
                        r_upd = session.get("https://sjinn.ai/api/get_user_account")
                        if r_upd.status_code == 200:
                            new_bal = r_upd.json().get('data', {}).get('balances', 0)
                            st.session_state["user_credits"] = new_bal
                            # Update box credits real-time
                            credits_placeholder.info(f"**Sisa Credits Akun:** {new_bal}", icon="💰")
                    except: pass
                
                progress_bar.progress(int((i / loop_count) * 100))
                
                if i < loop_count: 
                    time.sleep(delay_sec) 

            except: pass

        # 4. MONITORING
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

# --- TAB 2: ACCOUNT GALLERY ---
with tab2:
    st.info("Klik tombol di bawah untuk memuat semua video yang pernah dibuat di akun ini.")
    
    if st.button("Refresh / Muat Gallery", use_container_width=True):
        if not email_input:
            st.error("Silakan isi Email & Password di sidebar, lalu klik Login!")
        else:
            final_pass = email_input if st.session_state.use_same_pass else st.session_state.get("u_pass", "")
            
            with st.spinner("Mengambil data dari server..."):
                session_gal = requests.Session()
                try:
                    # Login Singkat
                    r_csrf = session_gal.get("https://sjinn.ai/api/auth/csrf")
                    csrf_token = r_csrf.json().get("csrfToken")
                    payload = {"redirect": "false", "email": email_input, "password": final_pass, "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"}
                    session_gal.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
                    
                    # Update credits
                    r_info = session_gal.get("https://sjinn.ai/api/get_user_account")
                    if r_info.status_code == 200:
                        st.session_state["user_credits"] = r_info.json().get('data', {}).get('balances', 0)

                    # Request List Video
                    r_list = session_gal.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                    
                    if r_list.json().get("success"):
                        all_videos = r_list.json()["data"].get("list", [])
                        if not all_videos:
                            st.info("Gallery kosong. Belum ada video yang ditemukan.")
                        else:
                            st.success(f"Ditemukan **{len(all_videos)}** video.")
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
