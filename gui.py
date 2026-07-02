import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk
import requests
import os
import threading
import cv2

# --- Configuration
THEME_COLORS = {
    "primary": "#1E3A8A", "secondary": "#059669", "bg_gray": "#F9FAFB",
    "text_gray": "#6B7280", "white": "#FFFFFF"
}
SERVER_URL = "http://192.168.0.245:5000"
# Assumes gui.py is in a 'frontend' or similar folder, and we need to go up one level
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# --- Main Application Class
class VotingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NextGen AVM")
        self.geometry("1024x768")
        self.configure(bg=THEME_COLORS["bg_gray"])

        self.title_font = font.Font(family="Roboto", size=28, weight="bold")
        self.header_font = font.Font(family="Roboto", size=24, weight="bold")
        self.normal_font = font.Font(family="Roboto", size=16)
        self.small_font = font.Font(family="Roboto", size=12, slant="italic")

        self.current_page_name = ""
        self.cached_images = {}

        container = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        for PageClass in (WelcomePage, FingerprintPage, FacePage, CandidatePage, VotedPage):
            page = PageClass(container, self)
            self.pages[PageClass.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.poll_server_status()

    def show_page(self, page_name):
        if self.current_page_name == "FacePage":
            self.pages["FacePage"].stop_webcam()

        self.current_page_name = page_name
        page = self.pages[page_name]
        page.tkraise()

        if page_name == "FacePage":
            self.pages["FacePage"].start_webcam()

    def get_image(self, image_path, size=(200, 200)):
        if not image_path:
            return self.get_placeholder(size)

        cache_key = f"{image_path}_{size[0]}x{size[1]}"
        if cache_key in self.cached_images:
            return self.cached_images[cache_key]

        try:
            full_path = os.path.join(PROJECT_ROOT, image_path.replace("\\", "/"))
            img = Image.open(full_path).resize(size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.cached_images[cache_key] = photo
            return photo
        except Exception as e:
            print(f"Error loading image '{full_path}': {e}")
            return self.get_placeholder(size)

    def get_placeholder(self, size):
        key = f"placeholder_{size[0]}x{size[1]}"
        if key in self.cached_images:
            return self.cached_images[key]

        img = Image.new('RGB', size, color=THEME_COLORS["text_gray"])
        photo = ImageTk.PhotoImage(img)
        self.cached_images[key] = photo
        return photo

    def poll_server_status(self):
        try:
            response = requests.get(f"{SERVER_URL}/get_status", timeout=0.5)
            if response.status_code == 200:
                state = response.json()
                page_map = {
                    "welcome": "WelcomePage", "fingerprint": "FingerprintPage",
                    "face": "FacePage", "candidates": "CandidatePage", "voted": "VotedPage"
                }
                gui_page_name = page_map.get(state.get("current_page"))

                if gui_page_name and gui_page_name != self.current_page_name:
                    self.show_page(gui_page_name)
                    if gui_page_name == "CandidatePage": self.fetch_candidates()
                    if gui_page_name == "VotedPage": self.after(5000, self.reset_voting_state)

                if self.current_page_name in self.pages:
                    self.pages[self.current_page_name].update_status(state)

        except (requests.ConnectionError, requests.Timeout):
            if self.current_page_name != "WelcomePage":
                self.show_page("WelcomePage")
            self.pages["WelcomePage"].update_status({"status_message": "Cannot connect to server."})

        self.after(1000, self.poll_server_status)

    def fetch_candidates(self):
        threading.Thread(target=self._do_fetch_candidates, daemon=True).start()

    def _do_fetch_candidates(self):
        try:
            response = requests.get(f"{SERVER_URL}/candidates")
            if response.status_code == 200:
                self.pages["CandidatePage"].draw_candidates(response.json().get("candidates", []))
        except Exception as e:
            print(f"Error fetching candidates: {e}")

    def reset_voting_state(self):
        if self.current_page_name == "VotedPage":
            print("Scheduling state reset...")
            threading.Thread(target=self._do_reset_request, daemon=True).start()

    def _do_reset_request(self):
        try:
            requests.post(f"{SERVER_URL}/reset_state", timeout=2)
            print("Background reset sent.")
        except Exception as e:
            print(f"Error in background reset: {e}")


class BasePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=THEME_COLORS["bg_gray"])
        self.controller = controller

        header = tk.Frame(self, bg=THEME_COLORS["primary"])
        header.pack(side="top", fill="x")
        tk.Label(header, text="NextGen AVM", font=controller.title_font,
                 bg=THEME_COLORS["primary"], fg=THEME_COLORS["white"]).pack(pady=20, padx=40, anchor="w")

        footer = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        footer.pack(side="bottom", fill="x", pady=10)
        tk.Label(footer, text="Developed by Team NextGen AVM", font=controller.small_font,
                 bg=THEME_COLORS["bg_gray"], fg=THEME_COLORS["text_gray"]).pack()

    def update_status(self, state):
        pass


class WelcomePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        main = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        main.pack(fill="both", expand=True, padx=100, pady=50)

        tk.Label(main, text="Welcome to NextGen AVM.", font=controller.header_font,
                 bg=THEME_COLORS["bg_gray"], fg=THEME_COLORS["primary"]).pack(pady=(20, 10))

        self.nid_display = tk.Label(main, text="", font=controller.header_font,
                                    bg=THEME_COLORS["bg_gray"], fg=THEME_COLORS["text_gray"])
        self.nid_display.pack(pady=20)

        self.status = tk.Label(main, text="Please enter your NID...", font=controller.normal_font,
                               bg=THEME_COLORS["bg_gray"], fg=THEME_COLORS["text_gray"], wraplength=600)
        self.status.pack(pady=5)

    def update_status(self, state):
        message = state.get("status_message", "")
        if message.startswith("NID:"):
            self.nid_display.config(text=message)
            self.status.config(text="Please press # to submit", fg=THEME_COLORS["text_gray"])
        elif any(err in message for err in ["not found", "already voted", "failed", "Cannot connect"]):
            self.nid_display.config(text="")
            self.status.config(text=message, fg="red")
        else:
            self.nid_display.config(text="")
            self.status.config(text=message, fg=THEME_COLORS["text_gray"])


class FingerprintPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        main = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        main.pack(fill="both", expand=True, padx=100, pady=50)

        details = tk.Frame(main, bg=THEME_COLORS["white"], bd=2, relief="groove")
        details.pack(pady=20, fill="x")

        self.photo = tk.Label(details, bg=THEME_COLORS["white"])
        self.photo.pack(side="left", padx=20, pady=20)

        info = tk.Frame(details, bg=THEME_COLORS["white"])
        info.pack(side="left", padx=20, pady=20, anchor="w")

        self.name = tk.Label(info, text="Name: ", font=controller.normal_font, bg=THEME_COLORS["white"])
        self.name.pack(anchor="w")
        self.nid = tk.Label(info, text="NID: ", font=controller.normal_font, bg=THEME_COLORS["white"])
        self.nid.pack(anchor="w")

        self.status = tk.Label(main, text="Place finger on sensor.", font=controller.header_font,
                               bg=THEME_COLORS["bg_gray"], fg=THEME_COLORS["primary"], wraplength=600)
        self.status.pack(pady=30)

    def update_status(self, state):
        self.name.config(text=f"Name: {state.get('voter_name', 'N/A')}")
        self.nid.config(text=f"NID: {state.get('current_nid', 'N/A')}")
        photo_img = self.controller.get_image(state.get('voter_photo_path'), size=(150, 150))
        self.photo.config(image=photo_img)
        self.photo.image = photo_img

        message = state.get("status_message", "")
        color = "red" if any(err in message.lower() for err in ["failed", "did not match"]) else THEME_COLORS["primary"]
        self.status.config(text=message, fg=color)


class FacePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.cap = None
        self.running = False
        self.after_id = None

        main = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        main.pack(fill="both", expand=True, padx=100, pady=50)

        self.status = tk.Label(main, text="Look into the camera.", font=controller.header_font,
                               bg=THEME_COLORS["bg_gray"], fg=THEME_COLORS["primary"], wraplength=600)
        self.status.pack(pady=10)

        self.camera_label = tk.Label(main, bg="black")
        self.camera_label.pack(pady=10)

    def start_webcam(self):
        if not self.running:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Error: Cannot open webcam.")
                self.status.config(text="Error: Webcam not found.", fg="red")
                return
            self.running = True
            self.update_webcam_frame()

    def stop_webcam(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        self.camera_label.config(image='')
        print("Webcam stopped and released.")

    def update_webcam_frame(self):
        if self.running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                img = Image.fromarray(cv2image).resize((640, 480), Image.LANCZOS)
                self.photo = ImageTk.PhotoImage(image=img)
                self.camera_label.config(image=self.photo)
            self.after_id = self.after(15, self.update_webcam_frame)

    def update_status(self, state):
        message = state.get("status_message", "")
        color = "red" if "failed" in message.lower() else THEME_COLORS["primary"]
        self.status.config(text=message, fg=color)
        if "Verifying..." in message and self.running:
            print("GUI is stopping webcam to allow server access...")
            self.stop_webcam()


class CandidatePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        main = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        main.pack(fill="both", expand=True, padx=50, pady=20)

        tk.Label(main, text="Select your candidate using the buttons.",
                 font=controller.header_font,
                 bg=THEME_COLORS["bg_gray"],
                 fg=THEME_COLORS["primary"]).pack(pady=20)

        self.candidate_grid_frame = tk.Frame(main, bg=THEME_COLORS["bg_gray"])
        self.candidate_grid_frame.pack(fill="both", expand=True, pady=10)

    def draw_candidates(self, candidates):
        for w in self.candidate_grid_frame.winfo_children():
            w.destroy()

        self.candidate_grid_frame.columnconfigure((0, 1, 2), weight=1, uniform="group1")
        for i, c in enumerate(candidates):
            row, col = divmod(i, 3)
            card = tk.Frame(self.candidate_grid_frame, bg=THEME_COLORS["white"], bd=2,
                            relief="raised", padx=10, pady=10)
            card.grid(row=row, column=col, sticky="nsew", padx=15, pady=15)

            photo = self.controller.get_image(c.get('photo_path'), size=(150, 150))
            pl = tk.Label(card, image=photo, bg=THEME_COLORS["white"])
            pl.image = photo
            pl.pack(pady=10)

            tk.Label(card, text=c.get('name'), font=self.controller.normal_font,
                     bg=THEME_COLORS["white"]).pack(pady=5)

            sp = c.get('symbol_path')
            if sp:
                symbol = self.controller.get_image(sp, size=(50, 50))
                sl = tk.Label(card, image=symbol, bg=THEME_COLORS["white"])
                sl.image = symbol
                sl.pack(pady=10)


class VotedPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        main = tk.Frame(self, bg=THEME_COLORS["bg_gray"])
        main.pack(fill="both", expand=True, padx=100, pady=50)

        tk.Label(main, text="Your vote has been successfully cast.",
                 font=controller.header_font,
                 bg=THEME_COLORS["bg_gray"],
                 fg=THEME_COLORS["secondary"]).pack(pady=(50, 10))

        tk.Label(main, text="Thank you. Please exit safely.", font=controller.normal_font,
                 bg=THEME_COLORS["bg_gray"],
                 fg=THEME_COLORS["text_gray"]).pack(pady=20)


if __name__ == "__main__":
    app = VotingApp()
    app.mainloop()