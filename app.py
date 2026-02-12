import streamlit as st
import requests
import time
import mimetypes
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

# --- CONFIG ---
# Masukkan email/pass di sini atau lebih aman pakai st.secrets nanti
DEFAULT_EMAIL = "osumar5@pdf-cutter.com"
DEFAULT_PASS = "osumar5@pdf-cutter.com" 

# --- FIX IPV4 (Agar Upload Cepat di Cloud) ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Video Generator", page_icon="🎥")
st.title("🎥 Sjinn AI Auto-Generator")
st.write("Upload gambar, bot akan otomatis login, upload, dan render video.")

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.header("Konfigurasi Akun")
    email_input = st.text_input("Email", value=DEFAULT_EMAIL)
    pass_input = st.text_input("Password", value=DEFAULT_PASS, type="password")
    
prompt_input = st.text_input("Prompt Video", value="she is waving")
uploaded_file = st.file_uploader("Pilih Gambar (.png/.jpg)", type=['png', 'jpg', 'jpeg'])

# --- FUNGSI UTAMA ---
def process_automation():
    if not uploaded_file:
        st.error("Upload gambar dulu bos!")
        return

    # Siapkan Session
    session = requests.Session()
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://sjinn.ai/login"
    }
    session.headers.update(HEADERS)

    # 1. LOGIN
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    status_text.info("🔐 Sedang Login...")
    
    try:
        # Get CSRF
        r_csrf = session.get("https://sjinn.ai/api/auth/csrf")
        csrf_token = r_csrf.json().get("csrfToken")
        
        # Login
        payload = {
            "redirect": "false", "email": email_input, "password": pass_input,
            "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
        }
        h_login = HEADERS.copy()
        h_login["Content-Type"] = "application/x-www-form-urlencoded"
        
        r_login = session.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers=h_login)
        if r_login.status_code != 200:
            st.error(f"Login Gagal! {r_login.status_code}")
            return
    except Exception as e:
        st.error(f"Error Login: {e}")
        return

    progress_bar.progress(20)
    status_text.info("📤 Mengupload Gambar...")

    # 2. UPLOAD
    try:
        # Init Upload
        mime_type = uploaded_file.type
        r_init = session.post("https://sjinn.ai/api/upload_file", json={"content_type": mime_type})
        data_up = r_init.json().get("data", {})
        signed_url = data_up.get("signed_url")
        file_uuid = data_up.get("file_name")
        
        # Upload Fisik (Streaming dari Memory Streamlit)
        # Kita reset pointer file ke 0 agar terbaca dari awal
        uploaded_file.seek(0)
        
        requests.put(
            signed_url, 
            data=uploaded_file, 
            headers={"Content-Type": mime_type, "Content-Length": str(uploaded_file.size)}
        )
    except Exception as e:
        st.error(f"Error Upload: {e}")
        return

    progress_bar.progress(50)
    status_text.info("⚙️ Membuat Task Video...")

    # 3. CREATE TASK
    try:
        session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
        payload_task = {
            "id": "sjinn-image-to-video",
            "input": {"image_url": file_uuid, "prompt": prompt_input},
            "mode": "template"
        }
        r_task = session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=payload_task)
        if r_task.status_code != 200:
            st.error("Gagal create task")
            return
    except Exception as e:
        st.error(f"Error Task: {e}")
        return

    # 4. POLLING
    status_text.info("⏳ Menunggu Rendering (Bisa 1-2 menit)...")
    
    for i in range(40):
        time.sleep(5)
        try:
            r_check = session.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
            if r_check.json().get("success"):
                items = r_check.json()["data"].get("list", [])
                if items:
                    status = items[0].get("status")
                    if status == 1: # Sukses
                        video_url = items[0].get("output_url")
                        progress_bar.progress(100)
                        status_text.success("✅ Selesai!")
                        
                        st.video(video_url)
                        st.success(f"Link Video: {video_url}")
                        return
                    elif status == 3:
                        st.error("❌ Gagal: Server menolak (Status 3)")
                        return
        except:
            pass
            
    st.warning("⚠️ Waktu habis (Timeout), coba cek manual di web.")

# Tombol Eksekusi
if st.button("MULAI GENERATE VIDEO", type="primary"):
    process_automation()
