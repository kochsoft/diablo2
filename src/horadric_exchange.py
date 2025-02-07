#!/usr/bin/python3
"""tkinter GUI part for the Horadric Exchange project.

Literature:
===========
[1] The grid.
  https://www.pythontutorial.net/tkinter/tkinter-grid/
  https://tkdocs.com/tutorial/grid.html
[2] Vertical Scrollbar to text area.
  https://stackoverflow.com/questions/13832720/how-to-attach-a-scrollbar-to-a-text-widget

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/02/06"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format= '[%(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

pfname_script = Path(__file__)
pfname_icon =  Path(pfname_script.parent, "logo_horadric_exchange.png")

try:
    import tkinter as tk
    from tkinter import ttk
    from idlelib.tooltip import Hovertip
except ModuleNotFoundError:
    _log.warning(f"""{pfname_script.name}: Failure to import tkinter, which is necessary for opening this GUI.
    
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

        self.width_column = 40
        self.padding_columns = 10

        self.root = None  # type: Optional[tk.Tk]
        self.icon_horadric_exchange = None  # type: Optional[tk.PhotoImage]
        self.tabControl =  None  # type: Optional[ttk.Notebook]
        self.tab1 = None  # type: Optional[ttk.Frame]
        self.tab2 = None  # type: Optional[ttk.Frame]

        self.entry_pfname1 = None  # type: Optional[tk.Entry]
        self.entry_pfname2 = None  # type: Optional[tk.Entry]
        self.ta_desc1 = None  # type: Optional[tk.Text]
        self.ta_desc2 = None  # type: Optional[tk.Text]
        self.button_commit = None  # type: Optional[tk.Button]
        self.tooltip_commit = None  # type: Optional[Hovertip]

        self.build_gui()
        if self.root:
            self.root.mainloop()
        else:
            _log.warning("No GUI available.")

    def load_1(self):
        pass

    def load_2(self):
        pass

    def build_gui(self):
        # > Main Window. ---------------------------------------------
        self.root = tk.Tk()
        self.root.title("Horadric Exchange Tool")
        self.root.geometry('1024x760')
        self.icon_horadric_exchange = tk.PhotoImage(file=str(pfname_icon))
        self.root.iconphoto(True, self.icon_horadric_exchange)
        # < Main Window. ---------------------------------------------
        # > Tabs. ----------------------------------------------------
        self.tabControl = ttk.Notebook(self.root)
        self.tab1 = ttk.Frame(self.tabControl)
        self.tab2 = ttk.Frame(self.tabControl)

        # Columns 1 and 4 (textboxes) receive weight for stretching, if the main tab resizes.
        self.tab1.columnconfigure(1, weight=1)
        self.tab1.columnconfigure(4, weight=1)
        self.tab1.rowconfigure(1, weight=1)

        self.tabControl.add(self.tab1, text="Horadric Exchange")
        self.tabControl.add(self.tab2, text="Horazon's Folly")
        self.tabControl.pack(expand=1, fill=tk.BOTH)
        # < ----------------------------------------------------------
        # > Tab 1, Horadric Exchange. --------------------------------
        tk.Label(self.tab1, text='1.:', relief=tk.RIDGE, width=10).grid(row=0, column=0)
        tk.Label(self.tab1, text='2.:', relief=tk.RIDGE, width=10).grid(row=0, column=3)

        self.entry_pfname1 = tk.Entry(self.tab1, width=self.width_column - 7, state='disabled')
        self.entry_pfname1.grid(row=0, column=1, sticky='ew')
        self.entry_pfname2 = tk.Entry(self.tab1, width=self.width_column - 7, state='disabled')
        self.entry_pfname2.grid(row=0, column=4, sticky='ew')

        tk.Button(self.tab1, text='Load .d2s', command=self.load_1, width=10, height=1, bg='#009999').grid(row=0, column=2) #, padx=(0,20)
        tk.Button(self.tab1, text='Load. d2s', command=self.load_2, width=10, height=1, bg='#009999').grid(row=0, column=5)

        self.ta_desc1 = tk.Text(self.tab1, width=self.width_column, state='disabled')
        self.ta_desc1.grid(row=1, column=0, columnspan=3, sticky='ewns')
        self.ta_desc2 = tk.Text(self.tab1, width=self.width_column, state='disabled')
        self.ta_desc2.grid(row=1, column=3, columnspan=3, sticky='ewns')

        #scrollbar1 = tk.Scrollbar(self.ta_desc1)
        #self.txt['yscrollcommand'] = scrollbar1.set

        self.button_commit = tk.Button(self.tab1, state='disabled', image=self.icon_horadric_exchange)
        self.button_commit.grid(row=2,column=0, columnspan=10, sticky='ew')
        self.tooltip_commit = Hovertip(self.button_commit, 'Load two character files and swap their Horadric Cube contents.')
        #self.tooltip_commit.text= "Huhu"
        # < ----------------------------------------------------------
        # TODO! Hier war ich.




if __name__ == '__main__':
    Horadric_GUI(sys.argv)
    print("Done.")
