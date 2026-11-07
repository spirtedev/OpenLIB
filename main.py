import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if sys.version_info < (3, 12):
    sys.exit(f"OpenLIB needs Python 3.12 or newer (you are using "
             f"{sys.version_info.major}.{sys.version_info.minor}).")

import tkinter as tk
import database
from gui import MainFrame
from login_reg import LoginPage, RegisterPage

BG_COLOR = "#0F172A"
LOGIN_SIZE, DASHBOARD_SIZE = "800x550", "1000x620"


class OpenLIBApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenLIB")
        self.geometry(LOGIN_SIZE)
        self.configure(bg=BG_COLOR)

        # Set window icon if logo exists
        if os.path.exists("logo.png"):
            try:
                self.iconphoto(False, tk.PhotoImage(file="logo.png"))
            except Exception:
                pass

        # Create database tables if they do not exist yet
        database.init()

        # Holds current logged-in user data
        self.current_user = None
        self.dashboard = None

        # Container for stacking screens
        self.container = tk.Frame(self, bg=BG_COLOR)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Register the login and registration views
        self.frames = {}
        for PageClass in (LoginPage, RegisterPage):
            page_name = PageClass.__name__
            frame = PageClass(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Start on LoginPage
        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.on_show()
        frame.tkraise()

    def open_dashboard(self):
        """Called by LoginPage after a successful login (current_user is already set)."""
        if self.dashboard is not None:
            self.dashboard.destroy()
        self.dashboard = MainFrame(self.container, self)
        self.dashboard.grid(row=0, column=0, sticky="nsew")
        self.geometry(DASHBOARD_SIZE)
        self.minsize(860, 480)
        self.dashboard.tkraise()

    def logout(self):
        if self.dashboard is not None:
            self.dashboard.destroy()
            self.dashboard = None
        self.current_user = None
        self.minsize(1, 1)
        self.geometry(LOGIN_SIZE)
        self.show_frame("LoginPage")


if __name__ == "__main__":
    app = OpenLIBApp()
    app.mainloop()
