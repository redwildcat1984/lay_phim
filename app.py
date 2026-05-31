import streamlit as st
import os
import subprocess
import re
from playwright.sync_api import sync_playwright

# ==========================================
# CẤU HÌNH GIAO DIỆN
# ==========================================
st.set_page_config(
    page_title="Yt-dlp Bản Chuẩn Đa Luồng Gốc",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Tải Video M3U8 Đa Luồng Chính Chủ")
st.caption("Phiên bản rút gọn: Tải 1 link duy nhất, hiển thị log trực tiếp, dùng lõi đa luồng gốc của yt-dlp.")

# Khởi tạo bộ nhớ tạm cho link quét được
if 'links_found' not in st.session_state:
    st.session_state.links_found = []

# ==========================================
# HÀM QUÉT LINK TRÌNH DUYỆT ẨN (AUTOPLAY)
# ==========================================
def scan_m3u8_links(target_url):
    danh_sach_link = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=["--autoplay-policy=no-user-gesture-required"]
        )
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
            # Ép video tự phát ngầm
            page.evaluate("() => { document.querySelectorAll('video').forEach(v => { v.muted = true; v.play(); }); }")
            page.wait_for_timeout(8000)
        except:
            pass
        finally:
            browser.close()
    return danh_sach_link

# ==========================================
# GIAO DIỆN ỨNG DỤNG
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
                st.error("Không tìm thấy link tự động. Hãy chuyển sang tab 'Dán trực tiếp' để dán tay nhé.")
        else:
            st.warning("Vui lòng điền URL trang web trước.")

with tabs[1]:
    manual_link = st.text_input("Dán trực tiếp đường dẫn m3u8 (lấy từ F12) vào đây:")

# --- BƯỚC 2: CHỌN ĐỘ PHÂN GIẢI & CẤU HÌNH TẢI ---
st.markdown("---")
st.header("2. Cấu hình & Tải xuống")

# Xác định link cuối cùng sẽ đem đi tải
final_url = ""
if manual_link.strip():
    final_url = manual_link.strip()
elif st.session_state.links_found:
    final_url = st.selectbox("Chọn một trong các link quét được:", options=st.session_state.links_found)

# Cấu hình số luồng tải
num_threads = st.slider("Chọn số luồng tải đồng thời của yt-dlp (Mặc định là 5):", min_value=1, max_value=16, value=5)

# Đặt tên file lưu trữ
file_name = st.text_input("Đặt tên file lưu trữ (Không cần ghi đuôi .mp4):", value="video_da_tai")

# --- KÍCH HOẠT TIẾN TRÌNH TẢI ĐỒNG BỘ ---
if st.button("📥 Bắt đầu kích hoạt yt-dlp", type="primary"):
    if not final_url:
        st.error("Chưa có đường dẫn m3u8 nào để tải!")
    elif not file_name.strip():
        st.error("Vui lòng không để trống tên file!")
    else:
        # Làm sạch link và tạo đường dẫn tuyệt đối tại thư mục chứa code
        clean_url = final_url.strip().replace('\r', '').replace('\n', '')
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(current_dir, f"{file_name.strip()}.mp4")
        
        st.info(f"🚀 Hệ thống đang kích hoạt lõi đa luồng ({num_threads} luồng) để tải video...")
        
        # Tạo thanh tiến trình và ô log trống trên giao diện
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.expander("📊 Log tiến trình thời gian thực từ yt-dlp", expanded=True):
            log_box = st.empty()
            
        # CẤU HÌNH LỆNH: Gọi đa luồng gốc bằng chính lõi của yt-dlp
        command = [
            "yt-dlp",
            clean_url,
            "-o", output_path,
            "--concurrent-fragments", str(num_threads), # Ép yt-dlp tải song song nhiều mảnh cùng lúc
            "--newline",                                 # Ép in dòng mới để Streamlit đọc mượt, chống treo
            # "--no-interact",
            "--no-warnings",
            "--no-mtime",
            "--force-overwrites"
        ]
        
        # Chạy đồng bộ (Blocking), đọc và in log liên tục lên màn hình
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            full_log = ""
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    full_log += line
                    # Cập nhật khung Log trên giao diện liên tục
                    log_box.text(full_log[-2000:]) # Chỉ hiển thị 2000 ký tự cuối để giao diện mượt, không bị lag
                    
                    # Trích xuất phần trăm % tiến độ
                    match = re.search(r"\[download\]\s+([0-9.]+)%", line)
                    if match:
                        pct = float(match.group(1))
                        progress_bar.progress(int(pct))
                        status_text.text(f"📥 Đang tải: {pct}%")
            
            process.wait()
            
            # Kiểm tra kết quả cuối cùng
            if process.returncode == 0 and os.path.exists(output_path):
                progress_bar.progress(100)
                status_text.text("✅ Tải xuống thành công hoàn toàn!")
                st.success(f"🎉 File video đã được lưu tại: `{output_path}`")
                
                # Nút cho phép lưu trực tiếp về máy tính cá nhân qua trình duyệt
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="💾 Lưu file về máy tính của bạn",
                        data=f,
                        file_name=f"{file_name.strip()}.mp4",
                        mime="video/mp4"
                    )
            else:
                st.error(f"❌ yt-dlp kết thúc với lỗi (Mã phản hồi từ hệ thống: {process.returncode})")
                st.warning("Vui lòng xem chi tiết thông báo lỗi ở bảng Log phía trên để xử lý.")
                
        except Exception as e:
            st.error(f"Lỗi hệ thống khi kích hoạt câu lệnh: {str(e)}")