import os
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.clock import Clock

from server import FileServer, STORAGE_DIR
import client

try:
    import qrcode
    from io import BytesIO
    from kivy.core.image import Image as CoreImage
    HAS_QR = True
except Exception:
    HAS_QR = False

try:
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE,
        Permission.INTERNET,
    ])
except Exception:
    pass


class FileTransferApp(App):
    def build(self):
        self.title = "File Transfer"
        self.server = FileServer(8000)
        ip, port = self.server.start()
        self.my_url = "http://%s:%s" % (ip, port)

        root = BoxLayout(orientation="vertical", padding=15, spacing=10)

        root.add_widget(Label(
            text="[b]عنوان هذا الجهاز:[/b]\n%s" % self.my_url,
            markup=True, size_hint_y=None, height=60
        ))

        if HAS_QR:
            root.add_widget(self.make_qr_widget(self.my_url))

        root.add_widget(Label(text="عنوان الجهاز الآخر (IP):", size_hint_y=None, height=25))
        self.target_ip = TextInput(text="", multiline=False, size_hint_y=None, height=40)
        root.add_widget(self.target_ip)

        self.target_port = TextInput(text="8000", multiline=False, size_hint_y=None, height=40)
        root.add_widget(self.target_port)

        send_btn = Button(text="اختر ملفاً وأرسله", size_hint_y=None, height=50)
        send_btn.bind(on_release=self.open_filechooser)
        root.add_widget(send_btn)

        self.status_label = Label(text="", size_hint_y=None, height=30)
        root.add_widget(self.status_label)

        root.add_widget(Label(text="الملفات المستلمة:", size_hint_y=None, height=25))
        self.files_label = Label(text="")
        root.add_widget(self.files_label)

        Clock.schedule_interval(self.refresh_files, 3)
        return root

    def make_qr_widget(self, data):
        qr = qrcode.make(data)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        core_img = CoreImage(buf, ext="png")
        return Image(texture=core_img.texture, size_hint_y=None, height=200)

    def open_filechooser(self, *args):
        chooser = FileChooserIconView(path=os.path.expanduser("~"))
        popup = Popup(title="اختر ملف", content=chooser, size_hint=(0.9, 0.9))

        def selected(instance, selection, touch):
            if selection:
                popup.dismiss()
                self.send_selected(selection[0])

        chooser.bind(on_submit=selected)
        popup.open()

    def send_selected(self, filepath):
        self.status_label.text = "جارٍ الإرسال..."

        def run():
            try:
                ip = self.target_ip.text.strip()
                port = int(self.target_port.text.strip() or "8000")
                status, resp = client.send_file(ip, port, filepath)
                msg = "تم الإرسال بنجاح" if status == 200 else ("فشل: %s" % resp)
            except Exception as e:
                msg = "خطأ: %s" % e
            Clock.schedule_once(lambda dt: setattr(self.status_label, "text", msg))

        threading.Thread(target=run, daemon=True).start()

    def refresh_files(self, dt):
        try:
            files = sorted(os.listdir(STORAGE_DIR))
            self.files_label.text = "\n".join(files) if files else "لا توجد ملفات بعد"
        except Exception:
            pass

    def on_stop(self):
        self.server.stop()


if __name__ == "__main__":
    FileTransferApp().run()
