import streamlit as st
import requests
import time
import mimetypes
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

# --- FIX IPV4 (Agar Upload Cepat & Stabil) ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Multi-Tasker", page_icon="🚀", layout="wide") 

st.title("🚀 Sjinn AI - Multi Task Generator")

# --- SIDEBAR (PENGATURAN AKUN) ---
with st.sidebar:
    st.header("Account Config")
    
    # 1. Input Email
    email_input = st.text_input("Email", value="")
    
    # 2. Input Password
    # Logika: Cek session_state dulu untuk menentukan status disabled
    # Default value checkbox kita anggap True jika belum ada di state
    is_checked = st.session_state.get("use_same_pass", True)
    
    if is_checked:
        pass_input = email_input
        st.text_input("Password", value=pass_input, type="password", disabled=True)
    else:
        # Jika user mengetik manual, kita perlu key agar value tidak hilang saat refresh
        pass_input = st.text_input("Password", value="", type="password", key="manual_pass")

    # 3. Kolom Centang (DILETAKKAN DI BAWAH)
    st.checkbox("Password same as email", value=True, key="use_same_pass")

# --- SISTEM TABS ---
# Memisahkan area kerja (Generate) dan area pantau (Gallery)
tab1, tab2 = st.tabs(["🎥 Generate New", "📚 Account Gallery"])

# ==========================================
# TAB 1: GENERATE NEW VIDEO
# ==========================================
with tab1:
    c1, c2 = st.columns([3, 1])
    with c1:
        prompt_input = st.text_input("Prompt Video", value="", placeholder="e.g. she is waving")
    with c2:
        loop_count = st.number_input("Jumlah Video", min_value=1, max_value=20, value=1, step=1)

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
        log_status.write("🔐 Sedang Login...")
        try:
            r_csrf = session.get("https://sjinn.ai/api/auth/csrf")
            csrf_token = r_csrf.json().get("csrfToken")
            
            payload = {
                "redirect": "false", "email": email_input, "password": pass_input,
                "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
            }
            h_login = session.headers.copy()
            h_login["Content-Type"] = "application/x-www-form-urlencoded"
            
            r_login = session.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers=h_login)
            if r_login.status_code != 200:
                log_status.update(label="❌ Gagal Login!", state="error")
                st.error("Login gagal. Cek email/password.")
                return
        except Exception as e:
            st.error(f"Error Login: {e}")
            return

        # 2. UPLOAD (Sekali Saja)
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
            st.error(f"Error Upload: {e}")
            return

        log_status.write("✅ Upload selesai. Mengirim Task...")
        
        # 3. KIRIM TASK (DENGAN DELAY 3 DETIK)
        session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
        
        tasks_submitted = 0
        progress_bar = st.progress(0)
        
        for i in range(1, loop_count + 1):
            try:
                # Create Task
                payload_task = {
                    "id": "sjinn-image-to-video",
                    "input": {"image_url": file_uuid, "prompt": prompt_input},
                    "mode": "template"
                }
                if i > 1: payload_task["input"]["prompt"] += " " * i 

                r_task = session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=payload_task)
                
                if r_task.status_code == 200:
                    log_status.write(f"➕ Task #{i} dikirim...")
                    tasks_submitted += 1
                else:
                    log_status.warning(f"⚠️ Gagal kirim Task #{i}")

                progress_bar.progress(int((i / loop_count) * 100))
                if i < loop_count: time.sleep(3)
                    
            except Exception as e:
                st.error(f"Error sending task {i}: {e}")

        log_status.update(label=f"⏳ Menunggu {tasks_submitted} Video Selesai...", state="running", expanded=True)
        
        # 4. MONITORING HASIL (BATCH)
        st.divider()
        st.subheader("📺 Galeri Hasil (Sesi Ini)")
        
        result_cols = st.columns(3)
        completed_ids = set()
        start_wait = time.time()
        
        while len(completed_ids) < tasks_submitted:
            
            if time.time() - start_wait > 300: # Timeout 5 menit
                st.warning("⚠️ Timeout Waktu Habis.")
                break
                
            time.sleep(5) 
            
            try:
                r_check = session.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                
                if r_check.json().get("success"):
                    all_tasks = r_check.json()["data"].get("list", [])
                    relevant_tasks = all_tasks[:tasks_submitted]
                    
                    for task in relevant_tasks:
                        status = task.get("status")
                        vid_url = task.get("output_url")
                        task_id = task.get("task_id")
                        
                        if status == 1 and task_id not in completed_ids:
                            completed_ids.add(task_id)
                            with result_cols[(len(completed_ids)-1)%3]:
                                st.video(vid_url)
                                st.link_button(f"Download Video #{len(completed_ids)}", vid_url, use_container_width=True)
                                
                        elif status == 3 and task_id not in completed_ids:
                            completed_ids.add(task_id)
                            st.toast(f"Satu video gagal.", icon="⚠️")

            except Exception:
                pass
                
        log_status.update(label="✅ Selesai!", state="complete", expanded=False)
        st.balloons()

    if st.button("MULAI BATCH GENERATE", type="primary", use_container_width=True):
        process_batch()

# ==========================================
# TAB 2: ACCOUNT GALLERY (FITUR BARU)
# ==========================================
with tab2:
    st.subheader("📚 Riwayat Video Akun")
    st.info("Fitur ini mengambil semua video yang pernah dibuat oleh akun di atas.")
    
    if st.button("🔄 Refresh / Muat Gallery", use_container_width=True):
        if not email_input or not pass_input:
            st.error("Silakan isi Email & Password di sidebar terlebih dahulu!")
        else:
            # Kita buat session baru khusus untuk gallery fetcher
            with st.spinner("Sedang menghubungkan ke server..."):
                session_gal = requests.Session()
                session_gal.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
                })
                
                try:
                    # 1. Login Singkat
                    r_csrf = session_gal.get("https://sjinn.ai/api/auth/csrf")
                    csrf_token = r_csrf.json().get("csrfToken")
                    
                    payload = {
                        "redirect": "false", "email": email_input, "password": pass_input,
                        "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
                    }
                    r_login = session_gal.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
                    
                    if r_login.status_code != 200:
                        st.error("Gagal Login untuk mengambil Gallery. Cek password.")
                    else:
                        # 2. Ambil List Video
                        r_list = session_gal.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                        
                        if r_list.json().get("success"):
                            all_videos = r_list.json()["data"].get("list", [])
                            
                            if not all_videos:
                                st.warning("Gallery kosong.")
                            else:
                                st.success(f"Berhasil menemukan {len(all_videos)} video.")
                                
                                # Tampilkan Grid Gallery
                                gal_cols = st.columns(3)
                                for idx, vid in enumerate(all_videos):
                                    with gal_cols[idx % 3]:
                                        with st.container(border=True):
                                            # Status 1 = Sukses
                                            if vid.get("status") == 1:
                                                st.video(vid.get("output_url"))
                                                # Tampilkan prompt jika ada
                                                prompt_text = vid.get("input", {}).get("prompt", "Tanpa Prompt")
                                                st.caption(f"📝 {prompt_text}")
                                                st.link_button("Download ⬇️", vid.get("output_url"), use_container_width=True)
                                            else:
                                                st.warning(f"Status: {vid.get('status')} (Gagal/Processing)")
                        else:
                            st.error("API Error saat mengambil list.")
                            
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")
