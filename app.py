import streamlit as st
import os
import subprocess
import re
import signal
from playwright.sync_api import sync_playwright

# ==========================================
# CẤU HÌNH GIAO DIỆN & BỘ NHỚ TẠM
# ==========================================
st.set_page_config(
    page_title="IDM M3U8 Ultimate",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 IDM M3U8 Ultimate — Tối Ưu Tối Cao")
st.caption("Bản hoàn chỉnh: Quét link ➔ Chọn link ➔ Chọn độ phân giải chuẩn ➔ Tải siêu tốc ổn định.")

# Khởi tạo bộ nhớ tạm Streamlit
if 'links_found' not in st.session_state: st.session_state.links_found = []
if 'current_pid' not in st.session_state: st.session_state.current_pid = None
if 'formats_available' not in st.session_state: st.session_state.formats_available = []
if 'last_fetched_url' not in st.session_state: st.session_state.last_fetched_url = ""

# ==========================================
# HÀM QUÉT LINK TRÌNH DUYỆT ẨN (AUTOPLAY)
# ==========================================
def scan_m3u8_links(target_url):
    danh_sach_link = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page()
        
        def handle_request(request):
            url = request.url
            if "index.m3u8" in url or ".m3u8" in url:
                if url not in danh_sach_link: 
                    danh_sach_link.append(url)

        page.on("request", handle_request)
        try:
            page.goto(target_url, timeout=0, wait_until="commit")
            page.wait_for_timeout(2000)
            page.evaluate("() => { document.querySelectorAll('video').forEach(v => { v.muted = true; v.play(); }); }")
            page.wait_for_timeout(8000)
        except: 
            pass
        finally: 
            browser.close()
    return danh_sach_link

# ==========================================
# HÀM KIỂM TRA ĐỘ PHÂN GIẢI CÓ SẴN
# ==========================================
def get_video_formats(m3u8_url):
    """Gọi yt-dlp để quét và lấy CHÍNH XÁC danh sách độ phân giải"""
    formats = []
    if not m3u8_url: return formats
    
    # Lệnh sạch không chứa --impersonate để tránh lỗi hệ thống
    command = ["yt-dlp", "-F", m3u8_url, "--no-warnings"]
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if process.returncode == 0:
            lines = process.stdout.split("\n")
            for line in lines:
                if not line or line.startswith("[") or line.startswith("ID"): 
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    format_id = parts[0]
                    # Bóc tách chính xác ký tự độ phân giải (ví dụ: 1080p, 720p hoặc 1280x720)
                    res_match = re.search(r"(\d+p|\d+x\d+)", line)
                    if res_match:
                        resolution_info = res_match.group(1)
                        display_text = f"🎬 Chất lượng: {resolution_info} (Mã luồng: {format_id})"
                        if (format_id, display_text) not in formats:
                            formats.append((format_id, display_text))
    except:
        pass
    
    # Phương án dự phòng nếu link m3u8 không chứa luồng con
    if not formats:
        formats = [
            ("best", "⭐ Bản tốt nhất có sẵn (Mặc định tự động)"),
            ("worst", "📱 Bản nhẹ nhất (Tránh giật lag khi truyền TV/iPhone)")
        ]
    return formats

# ==========================================
# GIAO DIỆN ĐIỀU KHIỂN
# ==========================================

# --- BƯỚC 1: LẤY LINK VIDEO ---
st.header("1. Lấy đường dẫn m3u8")
tabs = st.tabs(["🕵️ Quét tự động từ trang web", "🔗 Dán trực tiếp bằng tay"])

with tabs[0]:
    url_input = st.text_input("Nhập URL trang web xem phim:", placeholder="https://...")
    if st.button("🔍 Bắt đầu quét gói tin"):
        if url_input:
            with st.spinner("Đang mở trình duyệt ngầm để săn link m3u8..."):
                st.session_state.links_found = scan_m3u8_links(url_input)
            if st.session_state.links_found: 
                st.success(f"Tìm thấy {len(st.session_state.links_found)} đường dẫn video!")
            else: 
                st.error("Không tìm thấy link tự động. Hãy chuyển sang tab bên cạnh để dán tay.")
        else:
            st.warning("Vui lòng điền URL trang web trước.")

with tabs[1]:
    manual_link = st.text_input("Dán trực tiếp đường dẫn m3u8 (lấy từ F12) vào đây:")

# --- BƯỚC 2: HIỂN THỊ DANH SÁCH LINK M3U8 TÌM ĐƯỢC ---
st.markdown("---")
st.header("2. Lựa chọn nguồn Video & Độ phân giải")

final_url = ""
# Ưu tiên link dán tay, nếu không có thì lấy từ danh sách quét được
if manual_link.strip():
    final_url = manual_link.strip()
elif st.session_state.links_found:
    # Bổ sung Selectbox hiển thị các file m3u8 tìm được theo yêu cầu của bạn
    final_url = st.selectbox(
        "Danh sách file m3u8 quét được (Hãy chọn 1 file để tải):",
        options=st.session_state.links_found
    )

# --- BƯỚC 3: CHỌN ĐỘ PHÂN GIẢI RIÊNG ---
selected_format_id = "best"
if final_url:
    # Chỉ quét lại độ phân giải khi link thay đổi để tối ưu tốc độ giao diện
    if final_url != st.session_state.last_fetched_url:
        with st.spinner("⏳ Đang bóc tách danh sách độ phân giải từ Server..."):
            st.session_state.formats_available = get_video_formats(final_url)
            st.session_state.last_fetched_url = final_url
            
    if st.session_state.formats_available:
        # Bổ sung Selectbox hiển thị độ phân giải riêng biệt
        choice = st.selectbox(
            "Chọn chính xác độ phân giải mong muốn:",
            options=range(len(st.session_state.formats_available)),
            format_func=lambda x: st.session_state.formats_available[x][1]
        )
        selected_format_id = st.session_state.formats_available[choice][0]

file_name = st.text_input("Đặt tên file lưu trữ (Không cần ghi đuôi .mp4):", value="video_chuan_toc_do")

# Bộ đôi nút bấm điều khiển Tiến trình
col_btn1, col_btn2 = st.columns(2)

with col_btn2:
    if st.button("🛑 DỪNG TẢI NGAY LẬP TỨC", type="secondary"):
        if st.session_state.current_pid:
            try:
                # Bảo hiểm Linux: Diệt sạch cụm tiến trình bao gồm cả yt-dlp ngầm
                os.killpg(os.getpgid(st.session_state.current_pid), signal.SIGTERM)
                st.toast("💥 Đã hủy và dập tắt hoàn toàn tiến trình ngầm!")
                st.session_state.current_pid = None
            except: 
                st.toast("Không tìm thấy tiến trình đang chạy.")
        else:
            st.info("Hiện không có video nào đang tải.")

with col_btn1:
    if st.button("📥 Bắt đầu tải", type="primary"):
        if not final_url:
            st.error("Chưa có đường dẫn m3u8 nào để tiến hành tải!")
        elif not file_name.strip():
            st.error("Vui lòng không để trống tên file!")
        else:
            clean_url = final_url.strip().replace('\r', '').replace('\n', '')
            current_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(current_dir, f"{file_name.strip()}.mp4")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.expander("📊 Nhật ký tải thời gian thực", expanded=True):
                log_box = st.empty()
            
            # CẤU HÌNH TUYỆT ĐỐI ỔN ĐỊNH: Đã loại bỏ hoàn toàn các tham số lỗi mmap và impersonate
            command = [
                "yt-dlp",
                clean_url,
                "-f", selected_format_id,            # Ép tải chính xác độ phân giải đã chọn
                "-o", output_path,
                "--concurrent-fragments", "8",       # Đa luồng gốc đạt mốc 12-17 MB/s của bạn
                "--http-chunk-size", "10M",          # Chống băm vụn file con
                "--buffer-size", "64K",              # Tối ưu RAM đệm ghi đĩa ổn định trên Linux
                "--newline",
                "--progress-template", "[download] %(progress._percent_str)s", # Log sạch
                "--no-warnings",
                "--no-mtime",
                "--force-overwrites"
            ]
            
            try:
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace', preexec_fn=os.setsid
                )
                
                st.session_state.current_pid = process.pid
                full_log = ""
                max_pct = 0 # Khóa van một chiều chống nhảy % giật lùi
                
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None: 
                        break
                    if line:
                        if "[download]" in line or "Destination" in line:
                            full_log += line + "\n"
                            log_box.text(full_log[-1000:])
                        
                        match = re.search(r"([0-9.]+)%", line)
                        if match:
                            pct = float(match.group(1))
                            if pct > max_pct:
                                max_pct = pct
                                progress_bar.progress(int(max_pct))
                                status_text.text(f"📥 Đang tải: {int(max_pct)}% (Tốc độ tối đa ổn định)")
                
                process.wait()
                
                if process.returncode == 0 and os.path.exists(output_path):
                    progress_bar.progress(100)
                    status_text.text("✅ Tải xuống thành công hoàn toàn!")
                    st.success(f"🎉 File đã lưu tại: `{output_path}`")
                    
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="💾 Lưu file về máy tính của bạn",
                            data=f, file_name=f"{file_name.strip()}.mp4", mime="video/mp4"
                        )
                else:
                    if process.returncode == -15: 
                        status_text.text("🛑 Đã dừng tiến trình tải theo yêu cầu.")
                    else: 
                        st.error(f"❌ Thất bại với mã lỗi hệ thống: {process.returncode}")
                        
            except Exception as e: 
                st.error(f"Lỗi hệ thống: {str(e)}")
            finally: 
                st.session_state.current_pid = None


# yt-dlp "https://vip.opstream90.com/20260504/30927_2da833ec/index.m3u8" -o "test_speed.mp4" --concurrent-fragments 8 --http-chunk-size 10M --buffer-size 64K --file-access-mode mmap --impersonate chrome