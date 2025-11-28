from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import requests
import cv2
import threading
import numpy as np

# --- CẤU HÌNH KẾT NỐI ---
# Thay bằng link Heroku của bạn (bỏ dấu / ở cuối nếu có)
BASE_URL = "https://khai-security-robot-f5870f032456.herokuapp.com"

# Các đường dẫn con
UPLOAD_URL = f"{BASE_URL}/add_member"
GET_ALERT_URL = f"{BASE_URL}/get_intruder_stats"

class SecurityApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 1. Tiêu đề
        self.label_title = Label(text="ROBOT AN NINH GIA ĐÌNH", font_size='24sp', size_hint=(1, 0.1), color=(0, 1, 1, 1))
        self.layout.add_widget(self.label_title)

        # 2. Khu vực hiển thị CẢNH BÁO (Quan trọng)
        self.lbl_alert = Label(
            text="--- Hệ thống an toàn ---", 
            font_size='20sp', 
            size_hint=(1, 0.15),
            color=(0, 1, 0, 1), # Màu xanh lá
            bold=True
        )
        self.layout.add_widget(self.lbl_alert)

        # 3. Camera Preview
        self.img_camera = Image(size_hint=(1, 0.5))
        self.layout.add_widget(self.img_camera)
        
        # 4. Ô nhập tên
        self.name_input = TextInput(hint_text="Nhập tên người thân (VD: Bo, Me)", size_hint=(1, 0.1), multiline=False)
        self.layout.add_widget(self.name_input)
        
        # 5. Nút đăng ký
        self.btn_capture = Button(text="ĐĂNG KÝ KHUÔN MẶT MỚI", size_hint=(1, 0.15), background_color=(0.2, 0.6, 1, 1), font_size='18sp')
        self.btn_capture.bind(on_press=self.capture_and_send)
        self.layout.add_widget(self.btn_capture)
        
        # 6. Trạng thái upload
        self.status_label = Label(text="Sẵn sàng...", size_hint=(1, 0.05), font_size='14sp')
        self.layout.add_widget(self.status_label)

        # Khởi động Camera OpenCV
        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update_camera, 1.0/30.0)
        
        # --- QUAN TRỌNG: Tự động kiểm tra báo động mỗi 5 giây ---
        Clock.schedule_interval(self.poll_server_for_alerts, 5.0)
        
        return self.layout

    def update_camera(self, dt):
        ret, frame = self.capture.read()
        if ret:
            # Lật ảnh và chuyển sang Texture của Kivy
            buf1 = cv2.flip(frame, 0)
            buf = buf1.tobytes()
            image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.img_camera.texture = image_texture

    # --- HÀM HỎI SERVER XEM CÓ BÁO ĐỘNG KHÔNG ---
    def poll_server_for_alerts(self, dt):
        threading.Thread(target=self.check_alerts_thread).start()

    def check_alerts_thread(self):
        try:
            response = requests.get(GET_ALERT_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                total_strangers = data.get('total_strangers', 0)
                
                if total_strangers and int(total_strangers) > 0:
                    self.update_alert_ui(f"⚠️ CẢNH BÁO: CÓ {total_strangers} NGƯỜI LẠ!", is_danger=True)
                else:
                    self.update_alert_ui("✅ Nhà đang an toàn", is_danger=False)
        except:
            pass # Lỗi mạng thì bỏ qua, lần sau check tiếp

    def update_alert_ui(self, text, is_danger):
        def _update(dt):
            self.lbl_alert.text = text
            self.lbl_alert.color = (1, 0, 0, 1) if is_danger else (0, 1, 0, 1)
        Clock.schedule_once(_update)

    # --- HÀM GỬI ẢNH ĐĂNG KÝ ---
    def capture_and_send(self, instance):
        name = self.name_input.text.strip()
        if not name:
            self.status_label.text = "⚠️ Vui lòng nhập tên!"
            return

        self.btn_capture.disabled = True
        self.status_label.text = "⏳ Đang gửi lên Server..."
        threading.Thread(target=self.process_upload, args=(name,)).start()

    def process_upload(self, name):
        try:
            ret, frame = self.capture.read()
            if not ret: return

            img_path = "temp_face.jpg"
            cv2.imwrite(img_path, frame)

            with open(img_path, "rb") as f:
                response = requests.post(UPLOAD_URL, data={"name": name}, files={"image": f}, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.update_status(f"✅ Đã thêm '{name}' thành công!")
                else:
                    self.update_status(f"⚠️ Lỗi: {data.get('message')}")
            else:
                self.update_status(f"❌ Lỗi mạng: {response.status_code}")

        except Exception as e:
            self.update_status(f"❌ Lỗi: {str(e)}")
        finally:
            self.enable_button()

    def update_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', text))

    def enable_button(self):
        Clock.schedule_once(lambda dt: setattr(self.btn_capture, 'disabled', False))

    def on_stop(self):
        if self.capture: self.capture.release()

if __name__ == '__main__':
    SecurityApp().run()