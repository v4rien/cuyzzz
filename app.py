import streamlit as st
import requests
import time
import mimetypes
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

# --- FIX IPV4 (Wajib agar Upload Cepat) ---
def allowed_gai_family(): return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- 1. KONFIGURASI HALAMAN & CSS CUSTOM ---
st.set_page_config(page_title="Sjinn Studio", page_icon="✨", layout="wide")

# CSS untuk Tampilan Minimalis & Elegan
st.markdown("""
<style>
    /* Hilangkan Menu Hamburger & Footer Bawaan */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Background Utama yang Bersih */
    .stApp {
        background-color: #ffffff;
    }

    /* Styling Judul Utama */
    h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 0px;
    }
    
    /* Styling Sub-judul */
    .subtitle {
        font-family: 'Helvetica Neue', sans-serif;
        color: #666;
        text-align: center;
        margin-bottom: 30px;
        font-size: 1.1rem;
    }

    /* Styling Tombol Utama (Gradient & Shadow) */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        color: white;
    }

    /* Kartu Hasil Video */
    .video-card {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .video-card:hover {
        transform: scale(1.02);
    }
    
    /* Input Fields lebih modern */
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR (PENGATURAN TERSEMBUNYI) ---
with st.sidebar:
    st.markdown("### ⚙️ Pengaturan Akun")
    email_input = st.text_input("Email", value="osumar5@pdf-cutter.com")
    
    use_same_pass = st.toggle("Password sama dengan email?", value=True)
    if use_same_pass:
        pass_input = email_input
        st.text_input("Password", value=pass_input, type="password", disabled=True)
    else:
        pass_input = st.text_input("Password", value="", type="password")
    
    st.divider()
    st.caption("v2.0 Minimalist Edition")

# --- 3. UI UTAMA (HEADER) ---
st.markdown("<h1>Sjinn Studio ✨</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Automated AI Video Generator • Batch Processing</p>", unsafe_allow_html=True)

# Container Utama (Agar rapi di tengah)
with st.container():
    # Baris 1: Upload (Full Width tapi dibatasi margin)
    col_upload_L, col_upload_M, col_upload_R = st.columns([1, 2, 1])
    with col_upload_M:
        uploaded_file = st.file_uploader("Drop gambar Anda di sini", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")

    # Baris 2: Input Prompt & Jumlah (Berdampingan)
    if uploaded_file:
        st.write("") # Spacer
        c1, c2, c3 = st.columns([1, 2, 1]) # Biar tidak terlalu lebar
        with c2:
            prompt_input = st.text_input("Prompt / Instruksi", value="she is waving", placeholder="Contoh: she is smiling")
            
            # Slider lebih elegan daripada number input
            loop_count = st.slider("Jumlah Video", 1, 10, 2)
            
            st.write("") # Spacer
            # Tombol Eksekusi
            start_btn = st.button("MULAI GENERATE ✨", type="primary")

# --- 4. LOGIKA MESIN (BACKEND) ---
def process_batch():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://sjinn.ai/login"
    })

    # Status Container yang Minimalis
    status_container = st.empty()
    
    def update_status(msg, icon="🔄"):
        status_container.info(f"{icon} {msg}")

    # A. LOGIN
    try:
        r_csrf = session.get("https://sjinn.ai/api/auth/csrf")
        csrf_token = r_csrf.json().get("csrfToken")
        payload = {"redirect": "false", "email": email_input, "password": pass_input, "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"}
        session.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except:
        st.error("Gagal Login. Cek koneksi/akun."); return

    # B. UPLOAD
    update_status("Mengupload gambar...", "📤")
    try:
        mime = uploaded_file.type
        r_init = session.post("https://sjinn.ai/api/upload_file", json={"content_type": mime})
        d = r_init.json().get("data", {})
        url, uuid = d.get("signed_url"), d.get("file_name")
        uploaded_file.seek(0)
        requests.put(url, data=uploaded_file, headers={"Content-Type": mime, "Content-Length": str(uploaded_file.size)})
    except: st.error("Gagal Upload."); return

    # C. SEND TASKS
    session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
    
    tasks_submitted = 0
    progress_bar = st.progress(0)
    
    for i in range(1, loop_count + 1):
        update_status(f"Mengirim Task {i}/{loop_count}...", "🚀")
        try:
            p = {"id": "sjinn-image-to-video", "input": {"image_url": uuid, "prompt": prompt_input + (" "*i)}, "mode": "template"}
            if session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=p).status_code == 200:
                tasks_submitted += 1
            progress_bar.progress(int(i/loop_count*100))
            if i < loop_count: time.sleep(3)
        except: pass

    status_container.empty() # Hilangkan status text
    progress_bar.empty() # Hilangkan progress bar
    
    st.divider()
    st.markdown("<h3 style='text-align: center;'>Galeri Hasil</h3>", unsafe_allow_html=True)
    
    # D. POLLING & DISPLAY (Grid Layout)
    result_placeholder = st.empty()
    completed_ids = set()
    cols = st.columns(3) # Grid 3 Kolom Tetap
    
    start_time = time.time()
    
    while len(completed_ids) < tasks_submitted:
        if time.time() - start_time > 300: break
        time.sleep(5)
        
        try:
            r = session.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
            if r.json().get("success"):
                tasks = r.json()["data"].get("list", [])[:tasks_submitted]
                for t in tasks:
                    tid, stat, url = t.get("task_id"), t.get("status"), t.get("output_url")
                    if stat == 1 and tid not in completed_ids:
                        completed_ids.add(tid)
                        
                        # Tampilkan Card
                        with cols[(len(completed_ids)-1)%3]:
                            with st.container(border=True): # New Streamlit Container
                                st.video(url)
                                st.link_button("Download HD ⬇️", url, use_container_width=True)
        except: pass

    st.balloons()

# Trigger Tombol
if 'start_btn' in locals() and start_btn:
    if not uploaded_file:
        st.toast("⚠️ Harap upload gambar dulu!", icon="⚠️")
    else:
        process_batch()
