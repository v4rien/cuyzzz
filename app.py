import requests
import json
import time
import os
import mimetypes
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

# --- FIX IPV4 (Agar Upload Cepat) ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- KONFIGURASI AKUN ---
EMAIL = "osumar5@pdf-cutter.com"
PASSWORD = "osumar5@pdf-cutter.com"
FILE_GAMBAR = "coba.png"
PROMPT_VIDEO = "she is waving"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://sjinn.ai/login",
}

def login_sjinn(session):
    print("[Login] Memulai proses login...")
    try:
        r_csrf = session.get("https://sjinn.ai/api/auth/csrf", headers=HEADERS)
        csrf_token = r_csrf.json().get("csrfToken")
        
        payload = {
            "redirect": "false", "email": EMAIL, "password": PASSWORD,
            "csrfToken": csrf_token, "callbackUrl": "https://sjinn.ai/login", "json": "true"
        }
        h_login = HEADERS.copy()
        h_login["Content-Type"] = "application/x-www-form-urlencoded"
        
        r_login = session.post("https://sjinn.ai/api/auth/callback/credentials", data=payload, headers=h_login)
        if r_login.status_code == 200:
            print("    -> Login Sukses!")
            return True
        else:
            print(f"    [GAGAL] Login: {r_login.status_code}")
            return False
    except Exception as e:
        print(f"    Error Login: {e}")
        return False

def upload_image(session):
    print(f"\n[Upload] Mengupload '{FILE_GAMBAR}' (Hanya sekali)...")
    file_size = os.path.getsize(FILE_GAMBAR)
    mime_type, _ = mimetypes.guess_type(FILE_GAMBAR)
    if not mime_type: mime_type = "image/png"

    try:
        # 1. Minta Izin
        resp = session.post("https://sjinn.ai/api/upload_file", json={"content_type": mime_type})
        data = resp.json().get("data", {})
        signed_url = data.get("signed_url")
        file_uuid = data.get("file_name")

        # 2. Upload Fisik
        print("    -> Mengirim data ke server...", end="", flush=True)
        start = time.time()
        with open(FILE_GAMBAR, 'rb') as f:
            requests.put(signed_url, data=f, headers={"Content-Type": mime_type, "Content-Length": str(file_size)})
        print(f" [SELESAI] ({time.time() - start:.2f} detik)")
        
        return file_uuid
    except Exception as e:
        print(f"Error Upload: {e}")
        return None

def process_video_loop(session, file_uuid, loop_count):
    session.headers.update({"Referer": "https://sjinn.ai/tool-mode/sjinn-image-to-video"})
    
    for i in range(1, loop_count + 1):
        print(f"\n=== MEMPROSES VIDEO KE-{i} DARI {loop_count} ===")
        
        # 1. CREATE TASK
        try:
            payload = {
                "id": "sjinn-image-to-video",
                "input": {"image_url": file_uuid, "prompt": PROMPT_VIDEO},
                "mode": "template"
            }
            # Kita tambahkan timestamp/randomness di prompt sedikit agar server tidak menganggap spam
            # (Opsional, tapi aman)
            # payload["input"]["prompt"] += " " 
            
            resp = session.post("https://sjinn.ai/api/create_sjinn_image_to_video_task", json=payload)
            if resp.status_code == 200:
                print("    -> Task dibuat. Menunggu hasil...")
            else:
                print(f"    -> Gagal membuat task! {resp.text}")
                continue
        except Exception as e:
            print(f"    -> Error task: {e}")
            continue

        # 2. POLLING & DOWNLOAD
        berhasil = False
        for tick in range(1, 40): # Tunggu max 200 detik
            time.sleep(5)
            print(f"    ...Cek status ({tick*5} detik)...", end="\r")
            
            try:
                r_check = session.post("https://sjinn.ai/api/query_app_general_list", json={"id": "sjinn-image-to-video"})
                if r_check.json().get("success"):
                    items = r_check.json()["data"].get("list", [])
                    if items:
                        latest = items[0]
                        status = latest.get("status")
                        
                        if status == 1: # SUKSES
                            vid_url = latest.get("output_url")
                            file_name_output = f"video_ke_{i}.mp4"
                            
                            print(f"\n    [SUKSES] Video Jadi! Mendownload ke '{file_name_output}'...")
                            with open(file_name_output, 'wb') as f:
                                f.write(requests.get(vid_url).content)
                            
                            print("    -> Download selesai.")
                            berhasil = True
                            break # Keluar dari loop polling, lanjut ke video berikutnya
                            
                        elif status == 3: # GAGAL
                            print("\n    [GAGAL] Server menolak task ini.")
                            break
            except:
                pass
        
        if not berhasil:
            print("\n    [TIMEOUT] Waktu habis untuk video ini. Lanjut ke berikutnya...")
        
        # Jeda sedikit antar video agar akun aman
        time.sleep(2) 

def run_automation():
    if not os.path.exists(FILE_GAMBAR):
        print(f"File {FILE_GAMBAR} tidak ditemukan!")
        return

    # INPUT JUMLAH LOOP
    try:
        jumlah = int(input("Ingin membuat berapa video? (Masukkan Angka): "))
    except:
        jumlah = 1

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. LOGIN
    if not login_sjinn(session): return

    # 2. UPLOAD (Sekali saja)
    uuid = upload_image(session)
    if not uuid: return

    # 3. LOOPING CREATE & DOWNLOAD
    process_video_loop(session, uuid, jumlah)

    print("\n=== SEMUA PROSES SELESAI ===")

if __name__ == "__main__":
    run_automation()
