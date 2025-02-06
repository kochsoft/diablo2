"""tkinter GUI part for the Horadric Exchange project.

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/02/06"""

import tkinter as tk
from tkinter import ttk
from horazons_folly import *


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Test Window")
    tabControl = ttk.Notebook(root)
    tab1 = ttk.Frame(tabControl)
    tab2 = ttk.Frame(tabControl)
    tabControl.add(tab1, text="Horadric Exchange")
    tabControl.add(tab2, text="Horazon's Folly")
    tabControl.pack(expand=1, fill="both")
    ttk.Label(tab1, text="Wanna have Goodies!").grid(column=0, row=0, padx=30, pady=30)
    ttk.Label(tab2, text="Wanna have more Goodies!").grid(column=0, row=0, padx=30, pady=30)
    root.mainloop()

print("Done.")
