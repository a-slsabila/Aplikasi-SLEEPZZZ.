import sqlite3
import datetime
import random
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFillRoundFlatButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.core.audio import SoundLoader 

# --- KONFIGURASI WINDOW ---
Window.size = (1000, 600)
Window.position = 'custom'
Window.left = 100
Window.top = 100

# --- DATABASE MANAGER (BACKEND) ---
class Database:
    def __init__(self):
        self.con = sqlite3.connect("sleepzzz_md.db")
        self.cursor = self.con.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sleep_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sleep_start TIMESTAMP,
                sleep_end TIMESTAMP,
                duration_hours REAL,
                date_logged DATE,
                day_name TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        self.con.commit()

    def register_user(self, username, password):
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            self.con.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, username, password):
        self.cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = self.cursor.fetchone()
        return user[0] if user else None

    # Helper untuk mengambil waktu mulai sesi aktif (untuk recovery)
    def get_active_sleep(self, user_id):
        self.cursor.execute("SELECT sleep_start FROM sleep_logs WHERE user_id=? AND sleep_end IS NULL", (user_id,))
        result = self.cursor.fetchone()
        if result:
            start_str = result[0]
            if isinstance(start_str, str):
                try:
                    return datetime.datetime.fromisoformat(start_str)
                except ValueError:
                    # Fallback format lama
                    return datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S.%f")
            return start_str
        return None

    def auto_start_sleep(self, user_id):
        now = datetime.datetime.now()
        day_name = now.strftime("%a")
        
        # Cek apakah sudah ada sesi yang belum selesai
        self.cursor.execute("SELECT id FROM sleep_logs WHERE user_id=? AND sleep_end IS NULL", (user_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO sleep_logs (user_id, sleep_start, date_logged, day_name) VALUES (?, ?, ?, ?)", 
                                (user_id, now, now.date(), day_name))
            self.con.commit()
            return now
        return None

    def end_sleep(self, user_id):
        now = datetime.datetime.now()
        self.cursor.execute("SELECT id, sleep_start FROM sleep_logs WHERE user_id=? AND sleep_end IS NULL ORDER BY id DESC LIMIT 1", (user_id,))
        record = self.cursor.fetchone()
        
        if record:
            log_id, start_str = record
            if isinstance(start_str, str):
                try:
                    start_time = datetime.datetime.fromisoformat(start_str)
                except ValueError:
                     start_time = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                start_time = start_str
                
            duration = (now - start_time).total_seconds() / 3600.0
            
            self.cursor.execute("UPDATE sleep_logs SET sleep_end=?, duration_hours=? WHERE id=?", (now, duration, log_id))
            self.con.commit()
            return start_time, now, duration
        return None, None, 0

    def get_week_data(self, user_id):
        self.cursor.execute("""
            SELECT day_name, duration_hours 
            FROM sleep_logs 
            WHERE user_id=? AND sleep_end IS NOT NULL 
            ORDER BY id DESC LIMIT 30
        """, (user_id,))
        return self.cursor.fetchall()

db = Database()

# --- KV DESIGN STRING (FRONTEND) ---
kv = """
# --- DEFINISI KARTU TRANSPARAN ---
<CommonCard@MDCard>:
    orientation: "vertical"
    padding: "10dp"
    spacing: "10dp"
    radius: [15, 15, 15, 15]
    elevation: 0
    md_bg_color: 0.2, 0.2, 0.3, 0.7
    line_color: 1, 1, 1, 0.2
    line_width: 1

MDScreenManager:
    LoginScreen:
    SignupScreen:
    DashboardScreen:

# --- HALAMAN LOGIN ---
<LoginScreen>:
    name: "login"
    
    Image:
        source: "login_bg.jpg"
        allow_stretch: True
        keep_ratio: False
        size_hint: 1, 1
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    MDCard:
        size_hint: None, None
        size: "320dp", "480dp"
        pos_hint: {"center_x": 0.5, "center_y": 0.5}
        elevation: 4
        padding: "20dp"
        spacing: "20dp"
        orientation: "vertical"
        radius: [20,]
        md_bg_color: 0.1, 0.1, 0.15, 0.8 

        Image:
            source: "logo_app.png"
            size_hint: None, None
            size: "100dp", "100dp"
            pos_hint: {"center_x": 0.5}

        MDLabel:
            text: "SELAMAT DATANG"
            halign: "center"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            font_style: "H5"
            bold: True
            

        MDTextField:
            id: user
            hint_text: "Username"
            mode: "round"
            icon_right: "account"
            normal_color: 1, 1, 1, 1
            color_active: 1, 1, 1, 1

        MDTextField:
            id: passw
            hint_text: "Password"
            mode: "round"
            icon_right: "key-variant"
            password: True

        MDFillRoundFlatButton:
            text: "LOGIN"
            font_size: "16sp"
            size_hint_x: 1
            on_release: root.do_login()

        MDFlatButton:
            text: "Belum punya akun? Sign Up"
            size_hint_x: 1
            theme_text_color: "Custom"
            text_color: 0.6, 0.4, 1, 1
            on_release: app.root.current = "signup"

# --- HALAMAN SIGNUP ---
<SignupScreen>:
    name: "signup"
    Image:
        source: "login_bg.jpg"
        allow_stretch: True
        keep_ratio: False
        size_hint: 1, 1
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    MDCard:
        size_hint: None, None
        size: "320dp", "450dp"
        pos_hint: {"center_x": 0.5, "center_y": 0.5}
        elevation: 0     
        padding: "25dp"
        spacing: "20dp"
        orientation: "vertical"
        radius: [20,]
        md_bg_color: 0.15, 0.15, 0.2, 0.90

        MDLabel:
            text: "SIGN UP"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Custom"
            text_color: 0.6, 0.4, 1, 1
            bold: True

        MDTextField:
            id: new_user
            hint_text: "Buat Username"
            mode: "rectangle"

        MDTextField:
            id: new_pass
            hint_text: "Buat Password"
            helper_text: "Minimal 8 karakter"
            helper_text_mode: "on_focus"
            mode: "rectangle"
            password: True

        MDFillRoundFlatButton:
            text: "DAFTAR SEKARANG"
            size_hint_x: 1
            md_bg_color: 0.6, 0.4, 1, 1
            text_color: 0, 0, 0, 1
            on_release: root.do_signup()

        MDFlatButton:
            text: "Kembali"
            size_hint_x: 1
            on_release: app.root.current = "login"

# --- HALAMAN DASHBOARD ---
<DashboardScreen>:
    name: "dashboard"
    Image:
        source: "bg_dashboard.jpg"
        allow_stretch: True
        keep_ratio: False
        size_hint: 1, 1
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    MDBoxLayout:
        id: header
        size_hint_y: None
        height: "60dp"
        padding: "10dp"
        md_bg_color: 0.2, 0.1, 0.3, 0.8
        pos_hint: {"top": 1}
        
        MDIconButton:
            icon: "account-circle"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            user_font_size: "32sp"
        
        MDLabel:
            id: welcome_label
            text: "Halo, User!"
            color: 1, 1, 1, 1
            bold: True
            font_style: "H6"

        MDFillRoundFlatButton:
            text: "LOG OUT"
            md_bg_color: 0.8, 0.2, 0.2, 1
            on_release: root.logout()

    MDGridLayout:
        cols: 2
        spacing: "15dp"
        padding: "20dp"
        size_hint_y: None
        height: root.height - header.height
        pos_hint: {"top": 1 - (header.height/root.height)}

        MDBoxLayout:
            orientation: "vertical"
            spacing: "15dp"
            size_hint_x: 0.45

            CommonCard:
                size_hint_y: 0.2
                MDLabel:
                    text: "MOTIVASI HARI INI"
                    halign: "center"
                    font_style: "Caption"
                    theme_text_color: "Hint"
                MDLabel:
                    id: motivation_label
                    text: "..."
                    halign: "center"
                    italic: True
                    font_style: "Body1"
                    theme_text_color: "Custom"
                    text_color: 1, 0.9, 0.5, 1

            CommonCard:
                size_hint_y: 0.2
                MDGridLayout:
                    cols: 2
                    MDLabel:
                        text: "TIDUR:"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 0.5, 0.8, 1, 1
                    MDLabel:
                        id: lbl_sleep
                        text: "--:--"
                        halign: "right"
                        font_style: "H6"
                        theme_text_color: "Custom"
                        text_color: 0.5, 0.8, 1, 1
                    
                    MDLabel:
                        text: "BANGUN:"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 1, 0.5, 0.5, 1
                    MDLabel:
                        id: lbl_wake
                        text: "--:--"
                        halign: "right"
                        font_style: "H6"
                        theme_text_color: "Custom"
                        text_color: 1, 0.5, 0.5, 1

            CommonCard:
                size_hint_y: 0.6
                # Music Card juga harus elevation 0
                elevation: 0
                md_bg_color: 0.2, 0.2, 0.3, 0.7
                line_color: 1, 1, 1, 0.2
                
                MDLabel:
                    text: "MUSIK PENGANTAR TIDUR"
                    halign: "center"
                    bold: True
                    size_hint_y: None
                    height: "30dp"

                MDLabel:
                    id: status_music
                    text: "Pilih lagu..."
                    halign: "center"
                    font_style: "Caption"
                    size_hint_y: None
                    height: "20dp"

                MDGridLayout:
                    cols: 2
                    spacing: "10dp"
                    padding: "5dp"
                    
                    MDRaisedButton:
                        text: "Rain"
                        size_hint_x: 1
                        md_bg_color: 0.3, 0.3, 0.5, 1
                        on_release: root.play_music("Rain Sound", "rain.mp3")
                    
                    MDRaisedButton:
                        text: "Piano"
                        size_hint_x: 1
                        md_bg_color: 0.5, 0.3, 0.5, 1
                        on_release: root.play_music("Piano Music", "piano.mp3")
                    
                    MDRaisedButton:
                        text: "Kalimba"
                        size_hint_x: 1
                        md_bg_color: 0.3, 0.5, 0.6, 1
                        on_release: root.play_music("Kalimba", "kalimba.mp3")
                    
                    MDRaisedButton:
                        text: "Xylophone"
                        size_hint_x: 1
                        md_bg_color: 0.3, 0.5, 0.3, 1
                        on_release: root.play_music("Xylophone", "xylophone.mp3")

                # Tombol Batal Tidur (Muncul saat musik main/menunggu)
                MDFillRoundFlatButton:
                    id: btn_cancel
                    text: "SAYA BELUM TIDUR (BATAL)"
                    size_hint_x: 1
                    md_bg_color: 0.8, 0.4, 0.2, 1
                    disabled: True
                    opacity: 0
                    on_release: root.cancel_sleep_mode()

                # Tombol Bangun Tidur (Muncul setelah timer habis)
                MDFillRoundFlatButton:
                    id: btn_wake
                    text: "SAYA SUDAH BANGUN"
                    size_hint_x: 1
                    md_bg_color: 1, 0.2, 0.4, 1
                    disabled: True
                    opacity: 0
                    on_release: root.im_awake()

        MDBoxLayout:
            orientation: "vertical"
            spacing: "15dp"
            size_hint_x: 0.55

            # --- KARTU REALTIME CLOCK ---
            CommonCard:
                size_hint_y: 0.2
                padding: "20dp"
                
                MDFloatLayout:
                    
                    MDIcon:
                        icon: "clock-time-four-outline"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        font_size: "48sp"
                        size_hint: None, None
                        size: "48dp", "48dp"
                        pos_hint: {"center_y": 0.5, "x": 0.05}
                    
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_size: True
                        pos_hint: {"center_x": 0.5, "center_y": 0.5}
                        spacing: "2dp"
                        
                        MDLabel:
                            id: jam_realtime
                            text: "00:00:00"
                            font_style: "H4"
                            bold: True
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            adaptive_size: True
                            pos_hint: {"center_x": 0.5}
                        
                        MDLabel:
                            id: tgl_realtime
                            text: "Senin, 01 Januari 2025"
                            theme_text_color: "Hint"
                            font_style: "Subtitle1"
                            halign: "center"
                            adaptive_size: True
                            pos_hint: {"center_x": 0.5}

            # Kartu Grafik
            CommonCard:
                size_hint_y: 0.8
                MDLabel:
                    text: "GRAFIK TIDUR MINGGUAN"
                    halign: "center"
                    bold: True
                    size_hint_y: None
                    height: "30dp"
                
                MDBoxLayout:
                    id: graph_area
                    padding: "10dp"
                    spacing: "5dp"

                MDLabel:
                    id: advice_label
                    text: ""
                    halign: "center"
                    size_hint_y: None
                    height: "40dp"
                    font_style: "H6"
                    theme_text_color: "Error"
"""

# --- LOGIKA SCREENS (LOGIC) ---

class LoginScreen(MDScreen):
    def do_login(self):
        u = self.ids.user.text
        p = self.ids.passw.text
        uid = db.login_user(u, p)
        if uid:
            self.manager.current = "dashboard"
            self.manager.get_screen("dashboard").init_user(uid, u)
            self.ids.user.text = ""
            self.ids.passw.text = ""
        else:
            toast("Login Gagal! Cek Username/Password")

class SignupScreen(MDScreen):
    def do_signup(self):
        try:
            u = self.ids.new_user.text
            p = self.ids.new_pass.text
            if not u or not p:
                toast("Isi semua kolom!")
                return
            if len(p) < 8:
                toast("Password minimal 8 karakter!")
                return
            has_letter = any(char.isalpha() for char in p)
            has_digit = any(char.isdigit() for char in p)
            if not (has_letter and has_digit):
                toast("Password harus kombinasi huruf & angka!")
                return
            if db.register_user(u, p):
                toast("Berhasil Daftar! Silakan Login")
                self.ids.new_user.text = ""
                self.ids.new_pass.text = ""
                self.manager.current = "login"
            else:
                toast("Username sudah dipakai!")
        except Exception as e:
            print(f"System Error: {e}")
            toast("Terjadi kesalahan sistem. Silakan coba lagi")

class DashboardScreen(MDScreen):
    user_id = 0
    timer_obj = None
    TIMEOUT_SECONDS = 300 
    current_sound = None 
    
    motivations = [
        "Bangun pagi adalah kunci sukses.",
        "Tidur cukup = Otak Cerdas.",
        "Hal terindah bagiku adalah tidur, lalu setidaknya aku bisa bermimpi." ,
        "Tubuhmu butuh istirahat, bukan kopi terus.",
        "Mimpi indah dimulai dari tidur nyenyak.",
        "Tidur adalah meditasi terbaik.",
        "Mimpi besar membutuhkan tubuh yang cukup istirahat"
    ]

    def on_enter(self):
        Clock.schedule_interval(self.update_clock, 1)
        self.ids.motivation_label.text = f'"{random.choice(self.motivations)}"'

    def update_clock(self, dt):
        now = datetime.datetime.now()
        hari_indo = {'Mon': 'Senin', 'Tue': 'Selasa', 'Wed': 'Rabu', 'Thu': 'Kamis', 'Fri': 'Jumat', 'Sat': 'Sabtu', 'Sun': 'Minggu'}
        bulan_indo = {'Jan': 'Januari', 'Feb': 'Februari', 'Mar': 'Maret', 'Apr': 'April', 'May': 'Mei', 'Jun': 'Juni', 
                      'Jul': 'Juli', 'Aug': 'Agustus', 'Sep': 'September', 'Oct': 'Oktober', 'Nov': 'November', 'Dec': 'Desember'}
        nama_hari = hari_indo[now.strftime("%a")]
        nama_bulan = bulan_indo[now.strftime("%b")]
        self.ids.jam_realtime.text = now.strftime("%H:%M:%S")
        self.ids.tgl_realtime.text = f"{nama_hari}, {now.day} {nama_bulan} {now.year}"

    def init_user(self, uid, name):
        self.user_id = uid
        self.ids.welcome_label.text = f"Halo, {name}"
        self.reset_ui()
        self.draw_graph()

    def reset_ui(self):
        # Matikan semua tombol saat awal
        self.ids.btn_wake.disabled = True
        self.ids.btn_wake.opacity = 0
        self.ids.btn_cancel.disabled = True
        self.ids.btn_cancel.opacity = 0
        
        self.ids.lbl_sleep.text = "--:--"
        self.ids.lbl_wake.text = "--:--"
        self.ids.status_music.text = "Pilih lagu..."
        
        if self.current_sound:
            self.current_sound.stop()
            self.current_sound = None
        if self.timer_obj:
            self.timer_obj.cancel()

    def play_music(self, song_name, filename):
        if self.current_sound:
            self.current_sound.stop()
        
        if self.timer_obj:
            self.timer_obj.cancel()
            
        # UI: Munculkan Tombol BATAL, Sembunyikan Tombol BANGUN
        self.ids.btn_cancel.disabled = False
        self.ids.btn_cancel.opacity = 1
        self.ids.btn_wake.disabled = True
        self.ids.btn_wake.opacity = 0
            
        try:
            self.current_sound = SoundLoader.load(filename)
            if self.current_sound:
                self.current_sound.play()
                self.ids.status_music.text = f"♫ Memutar {song_name}... ♫"
                
                # Simulasi lagu 5 detik (bisa diubah sesuai durasi asli)
                Clock.schedule_once(self.song_finished, 1800) 
            else:
                self.ids.status_music.text = f"File {filename} tidak ditemukan!"
                toast(f"Error: {filename} tidak ada")
        except Exception as e:
            self.ids.status_music.text = "Error memuat audio"
            print(e)

    def cancel_sleep_mode(self):
        # Jika user menekan "SAYA BELUM TIDUR"
        if self.current_sound:
            self.current_sound.stop()
        if self.timer_obj:
            self.timer_obj.cancel()
        
        self.ids.status_music.text = "Mode Tidur Dibatalkan."
        self.ids.btn_cancel.disabled = True
        self.ids.btn_cancel.opacity = 0

    def song_finished(self, dt):
        self.ids.status_music.text = "Musik Berhenti, Menunggu Tidur...."
        # Timer 30 Menit (disimulasikan 10 detik)
        self.timer_obj = Clock.schedule_once(self.detect_sleep, self.TIMEOUT_SECONDS)

    def detect_sleep(self, dt):
        # Waktu habis -> User dianggap tidur
        start = db.auto_start_sleep(self.user_id)
        
        if start:
            self.activate_sleep_ui(start)
        else:
            existing_start = db.get_active_sleep(self.user_id)
            if existing_start:
                self.activate_sleep_ui(existing_start)
                self.ids.status_music.text = "Melanjutkan tidur..."
            else:
                self.ids.status_music.text = "Error: Status tidak valid."
        
        if self.current_sound:
            self.current_sound.stop()

    def activate_sleep_ui(self, start_time):
        self.ids.status_music.text = "Mode Tidur Aktif (Zzz...)"
        self.ids.lbl_sleep.text = start_time.strftime("%H:%M")
        
        # UI Transisi: Hilangkan tombol Batal, Munculkan tombol Bangun
        self.ids.btn_cancel.disabled = True
        self.ids.btn_cancel.opacity = 0
        
        self.ids.btn_wake.disabled = False
        self.ids.btn_wake.opacity = 1
        
        self.draw_graph()

    def im_awake(self):
        start, end, dur = db.end_sleep(self.user_id)
        if end:
            self.ids.lbl_wake.text = end.strftime("%H:%M")
            self.ids.status_music.text = f"Pagi! Total: {dur:.1f} Jam"
            self.ids.btn_wake.disabled = True
            self.ids.btn_wake.opacity = 0
            self.draw_graph()
            
            if self.current_sound:
                self.current_sound.stop()

    def draw_graph(self):
        area = self.ids.graph_area
        area.clear_widgets()
        data_raw = db.get_week_data(self.user_id)
        
        days_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        indo_map = {'Mon': 'Sen', 'Tue': 'Sel', 'Wed': 'Rab', 'Thu': 'Kam', 'Fri': 'Jum', 'Sat': 'Sab', 'Sun': 'Min'}
        weekly_vals = {d: 0.0 for d in days_map}

        for d_name, dur in data_raw:
            if d_name in weekly_vals:
                weekly_vals[d_name] = dur

        total_dur = 0
        filled = 0

        for day_code in days_map:
            val = weekly_vals[day_code]
            label = indo_map[day_code]
            
            if val > 0:
                total_dur += val
                filled += 1
            
            bar_layout = MDBoxLayout(orientation='vertical', spacing="5dp")
            
            ratio = min(val / 12.0, 1.0)
            spacer_ratio = 1.0 - ratio
            
            if spacer_ratio > 0:
                bar_layout.add_widget(MDLabel(size_hint_y=spacer_ratio))
            
            color = (0.2, 0.8, 0.4, 1) if val >= 8 else (0.9, 0.3, 0.3, 1)
            if val == 0: color = (0.3, 0.3, 0.3, 0.5)

            bar = MDCard(
                size_hint_y=ratio if ratio > 0 else 0.01,
                md_bg_color=color,
                radius=[5, 5, 0, 0],
                elevation=0
            )
            bar_layout.add_widget(bar)
            
            txt = f"{label}\n{val:.1f}" if val > 0 else label
            lbl = MDLabel(
                text=txt, 
                halign="center", 
                theme_text_color="Hint", 
                font_style="Overline",
                size_hint_y=None,
                height="30dp"
            )
            bar_layout.add_widget(lbl)
            
            area.add_widget(bar_layout)

        if filled > 0:
            avg = total_dur / filled
            if avg < 8:
                self.ids.advice_label.text = "PERINGATAN: Tidurmu kurang dari 8 jam! Perbaiki pola tidur."
                self.ids.advice_label.theme_text_color = "Error"
            else:
                self.ids.advice_label.text = "Pola tidurmu sangat baik. Pertahankan!"
                self.ids.advice_label.theme_text_color = "Custom"
                self.ids.advice_label.text_color = (0.2, 0.8, 0.4, 1)
        else:
            self.ids.advice_label.text = "Belum ada data tidur."

    def logout(self):
        self.manager.current = "login"
        if self.current_sound:
            self.current_sound.stop()

class SleepzzzApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Teal"
        return Builder.load_string(kv)

if __name__ == "__main__":
    SleepzzzApp().run()