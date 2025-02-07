#!/usr/bin/python3
"""tkinter GUI part for the Horadric Exchange project.

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/02/06"""

import os
import sys
import logging
logging.basicConfig(level=logging.INFO, format= '[%(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError:
    pfname_script = os.path.basename(__file__)
    _log.warning(f"""{pfname_script}: Failure to import tkinter, which is necessary for opening this GUI.
    
You now have three options:

1.: Ensure that your python interpreter has tkinter available. This usually is not that complicated to achieve.
E.g., under Windows it should be offered as an option to pull in during basic installation of python.
Under Linux it usually is a package to install from the repository, or a plain 'python -m pip install tkinter',
to have python pull in that package itself (the repository option is preferable though).

2.: Forget the whole thing.

3.: If you are not afraid of the command line, consider using the main script, 'horazons_folly.py' directly.
Say "python horazons_folly.py --help" and you will receive a detailed manual page.
""")
    sys.exit(1)

from typing import Optional, List, Dict
from horazons_folly import *


class Horadric_GUI():
    def __init__(self, args: Optional[List[str]] = None):
        self.horadric = Horadric()
        self.root = None  # type: Optional[tk.Tk]
        self.tabControl =  None  # type: Optional[ttk.Notebook]
        self.tab1 = None  # type: Optional[ttk.Frame]
        self.tab2 = None  # type: Optional[ttk.Frame]
        self.build_gui()
        if self.root:
            self.root.mainloop()
        else:
            _log.warning("No GUI available.")

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("Test Window")
        self.tabControl = ttk.Notebook(self.root)
        self.tab1 = ttk.Frame(self.tabControl)
        self.tab2 = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab1, text="Horadric Exchange")
        self.tabControl.add(self.tab2, text="Horazon's Folly")
        self.tabControl.pack(expand=1, fill="both")
        ttk.Label(self.tab1, text="Wanna have Goodies!").grid(column=0, row=0, padx=30, pady=30)
        ttk.Label(self.tab2, text="Wanna have more Goodies!").grid(column=0, row=0, padx=30, pady=30)

        # TODO! Hier war ich.
        # root.title('Youtube to mp3')
        # pfname_icon = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/get_yt_logo.png')
        # root.iconphoto(True, tk.PhotoImage(file=pfname_icon))




if __name__ == '__main__':
    Horadric_GUI(sys.argv)
    print("Done.")
