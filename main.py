import traceback
import tkinter as tk
from tkinter import messagebox
import database
from authentification import LoginPage, RegisterPage
from dashboard import DashboardPage
from gui_helpers import ASSETS_DIR, center_window
from theme import APP_BG


class OpenLIBApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenLIB")
        self.configure(bg=APP_BG)

        # Window size: start at 1100x650 in the middle of the screen, never smaller than 950x600
        center_window(self, 1100, 650)
        self.minsize(950, 600)

        # Set window icon if the optional image assets/openlibicon.png exists
        icon_path = ASSETS_DIR / "openlibicon.png"
        if icon_path.exists():
            try:
                self.iconphoto(False, tk.PhotoImage(file=str(icon_path)))
            except Exception:
                pass

        # Create database tables if they do not exist yet
        database.init()

        # Holds current logged-in user data (a dict) or None when nobody is logged in
        self.current_user = None

        # Container for stacking screens
        container = tk.Frame(self, bg=APP_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Register all application views
        self.frames = {}
        for PageClass in (LoginPage, RegisterPage, DashboardPage):
            page_name = PageClass.__name__
            frame = PageClass(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Shortcut so that pages can ask the dashboard to change the page shown:
        #   self.controller.dashboard.show_section("Books")
        self.dashboard = self.frames["DashboardPage"]

        # When the window is closed, close the database first
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start on LoginPage
        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.on_show()
        frame.tkraise()

    def logout(self):
        self.current_user = None
        self.dashboard.clear_content()  # remove the previous user's pages from memory
        self.show_frame("LoginPage")

    def on_close(self):
        """Called when the user closes the window: closes the database, then the window."""
        database.close()
        self.destroy()

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        """
        Tkinter calls this when a button/event function crashes.
        Instead of the app silently misbehaving, show a friendly message and print the
        technical details in the console, so a developer can find the problem.
        """
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        messagebox.showerror("Unexpected error",
                             "Something went wrong, but the application is still running.\n"
                             "Please try again. If it keeps happening, tell the developers.")


if __name__ == "__main__":
    app = OpenLIBApp()
    app.mainloop()
