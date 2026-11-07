import os
import tkinter as tk
import database
from login_reg import LoginPage, RegisterPage

BG_COLOR = "#0F172A"

class OpenLIBApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenLIB")
        self.geometry("800x550")
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

        # Container for stacking screens
        container = tk.Frame(self, bg=BG_COLOR)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Register all application views
        self.frames = {}
        for PageClass in (LoginPage, RegisterPage):
            page_name = PageClass.__name__
            frame = PageClass(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Start on LoginPage
        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.on_show()
        frame.tkraise()

    def logout(self):
        self.current_user = None
        self.show_frame("LoginPage")


if __name__ == "__main__":
    app = OpenLIBApp()
    app.mainloop()