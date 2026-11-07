from tkinter import *


# Create the window and give it the title "OpenLIB"
window = Tk()
window.title("OpenLIB")

# Add an icon to the app
icon = PhotoImage(file="assets/openlibicon.png")
window.iconphoto(True, icon)

# Window's dimensions
window.geometry("1200x750")
window.minsize(950, 600)

# Center the window
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

x = (screen_width - 1200) // 2
y = (screen_height - 750) // 2

window.geometry(f"1200x750+{x}+{y}")


def main():
    window.mainloop()


if __name__ == "__main__":
    main()
