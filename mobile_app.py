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
import time
import threading

# --- CẤU HÌNH SERVER ---
# Thay thế bằng URL ứng dụng Heroku của bạn (ví dụ: https://khai-security-robot-12345.herokuapp.com)
SERVER_URL = "https://TEN_APP_CUA_BAN.herokuapp.com/add_member" 

class SecurityApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Tiêu đề
        self.label_title = Label(text="ĐĂNG KÝ KHUÔN MẶT", font_size='24sp', size_hint=(1, 0.1))
        self.layout.add_widget(self.label_title)

        # Camera Preview (Sử dụng OpenCV để tương thích tốt hơn)
        self.img_camera = Image(size_hint=(1, 0.6))
        self.layout.add_widget(self.img_camera)
        
        # Ô nhập tên
        self.name_input = TextInput(hint_text="Nhập tên người thân (VD: Bo, Me)", size_hint=(1, 0.1), multiline=False)
        self.layout.add_widget(self.name_input)
        
        # Nút chụp & gửi
        self.btn_capture = Button(text="CHỤP & GỬI LÊN SERVER", size_hint=(1, 0.15), background_color=(0, 1, 0, 1), font_size='18sp')
        self.btn_capture.bind(on_press=self.capture_and_send)
        self.layout.add_widget(self.btn_capture)
        
        # Trạng thái
        self.status_label = Label(text="Sẵn sàng...", size_hint=(1, 0.1), color=(1, 1, 0, 1))
        self.layout.add_widget(self.status_label)

        # Khởi động Camera OpenCV
        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update_camera, 1.0/30.0) # Cập nhật 30 FPS
        
        return self.layout

    def update_camera(self, dt):
        ret, frame = self.capture.read()
        if ret:
            # Chuyển đổi màu từ BGR (OpenCV) sang RGB (Kivy)
            buf1 = cv2.flip(frame, 0)
            buf = buf1.tostring()
            image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.img_camera.texture = image_texture

    def capture_and_send(self, instance):
        name = self.name_input.text.strip()
        if not name:
            self.status_label.text = "⚠️ Vui lòng nhập tên trước!"
            return

        # Vô hiệu hóa nút để tránh spam
        self.btn_capture.disabled = True
        self.status_label.text = "⏳ Đang chụp ảnh và gửi..."

        # Chạy trong luồng riêng để không đơ giao diện
        threading.Thread(target=self.process_upload, args=(name,)).start()

    def process_upload(self, name):
        try:
            # 1. Lấy frame hiện tại từ Camera
            ret, frame = self.capture.read()
            if not ret:
                self.update_status("❌ Lỗi Camera!")
                return

            # 2. Lưu tạm ảnh ra file
            img_path = "temp_face.jpg"
            cv2.imwrite(img_path, frame)

            # 3. Gửi lên Server Flask
            with open(img_path, "rb") as f:
                response = requests.post(SERVER_URL, data={"name": name}, files={"image": f}, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.update_status(f"✅ Đã thêm '{name}' thành công!")
                else:
                    self.update_status(f"⚠️ Lỗi Server: {data.get('message')}")
            else:
                self.update_status(f"❌ Lỗi kết nối: {response.status_code}")

        except Exception as e:
            self.update_status(f"❌ Lỗi: {str(e)}")
        finally:
            self.enable_button()

    def update_status(self, text):
        # Cập nhật giao diện từ luồng phụ
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', text))

    def enable_button(self):
        Clock.schedule_once(lambda dt: setattr(self.btn_capture, 'disabled', False))

    def on_stop(self):
        # Giải phóng camera khi tắt app
        if self.capture:
            self.capture.release()

if __name__ == '__main__':
    SecurityApp().run()