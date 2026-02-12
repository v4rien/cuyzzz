import streamlit as st
import requests
import time
import mimetypes
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

# --- FIX IPV4 (Agar Upload Cepat) ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Sjinn Loop Generator", page_icon="🎥", layout="centered") 

st.title("🎥 Sjinn AI - Loop Generator")
st.write("Upload gambar sekali, generate video berkali-kali otomatis.")

# --- SIDEBAR (Konfigurasi) ---
with st.sidebar:
    st.header("Pengaturan Akun")
    # Ganti value default dengan akun Anda jika ingin
    email_input = st.text_input("Email", value="osumar5@pdf-cutter.com")
    pass_input = st.text_input("Password", value="osumar5@pdf-cutter.com", type="password")

# --- INPUT USER ---
col_input1, col_input2 = st.columns(2)
with col_input1:
    prompt_input = st.text_input("Prompt Video", value="she is waving")
with col_input2:
    loop_count = st.number_input("Jumlah Video", min_value=1, max_value=10, value=1, step=1)

uploaded_file = st.file_uploader("Pilih Gambar (.png/.jpg)", type=['png', 'jpg', 'jpeg'])

# --- FUNGSI UTAMA ---
def process_automation():
    if not uploaded_file:
        st.warning("⚠️ Harap upload gambar terlebih dahulu!")
        return

    # Siapkan Session
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://sjinn.ai/login"
    })

    # Area Log Status (Biar rapi)
    status_log = st.status("🚀 Memulai Proses...", expanded=True)

    # 1. LOGIN
    status_log.write("🔐 Sedang Login...")
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
            status_log.update(label="❌ Gagal Login!", state="error")
            st.error("Login gagal. Cek email/password.")
            return
    except Exception as e:
        status_log.update(label="❌ Error Login!", state="error")
        st.error(f"Error: {e}")
        return

    # 2. UPLOAD (Hanya Sekali)
    status_log.write("📤 Mengupload Gambar ke Server...")
    try:
        mime_type = uploaded_file.type
        r_init = session.post("https://sjinn.ai/api/upload_file", json={"content_type": mime_type})
        data_up = r_init.json().get("data", {})
        signed_url = data_up.get("signed_url")
        file_uuid = data_up.get("file_name")
        
        uploaded_file.seek(0)
        requests.put(
            signed_url, 
            data=uploaded_file, 
            headers={"Content-Type": mime_type, "Content-Length": str(uploaded_file.size)}
        )
    except Exception as e:
        status_log.update(label="❌ Gagal Upload!", state="error")
        st.error(f"Error Upload: {e}")
        return

    status_log.write("✅ Upload selesai. Memulai antrian pembuatan video...")
    status_log.update(label="⏳ Sedang Memproses Video...", state="running", expanded=True)

    # 3. LOOPING (Membuat Video Berulang)
    session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
    
    # Tempat hasil video akan muncul
    result_container = st.container()

    for i in range(1, loop_count + 1):
        status_log.write(f"⚙️ [Video {i}/{loop_count}] Mengirim perintah ke AI...")
        
        # A. Create Task
        try:
            payload_task = {
                "id": "sjinn-image-to-video",
                "input": {"image_url": file_uuid, "prompt": prompt_input},
                "mode": "template"
            }
            # Opsional: Tambah spasi random agar prompt dianggap unik tiap request
            if i > 1: payload_task["input"]["prompt"] += " " 

            r_task = session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=payload_task)
            if r_task.status_code != 200:
                st.error(f"Gagal membuat task ke-{i}")
                continue
        except:
            continue

        # B. Polling (Menunggu Hasil)
        video_found = False
        start_time = time.time()
        
        while time.time() - start_time < 200: # Timeout 200 detik
            time.sleep(5)
            try:
                r_check = session.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                if r_check.json().get("success"):
                    items = r_check.json()["data"].get("list", [])
                    if items:
                        latest = items[0]
                        status = latest.get("status")
                        
                        if status == 1: # Sukses
                            video_url = latest.get("output_url")
                            video_found = True
                            
                            # TAMPILKAN HASIL DI LAYAR
                            with result_container:
                                st.success(f"Video #{i} Selesai!")
                                # Layout kolom agar video kecil di tengah
                                c1, c2, c3 = st.columns([1, 2, 1])
                                with c2:
                                    st.video(video_url)
                                st.divider()
                            break
                        elif status == 3:
                            st.error(f"Video #{i} Gagal (Ditolak Server)")
                            break
            except:
                pass
        
        if not video_found:
            st.warning(f"Video #{i} Timeout (Waktu habis).")

    status_log.update(label="✅ Semua Proses Selesai!", state="complete", expanded=False)
    st.balloons()

# --- TOMBOL EKSEKUSI ---
if st.button("MULAI GENERATE", type="primary", use_container_width=True):
    process_automation()
