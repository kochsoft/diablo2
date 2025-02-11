#!/usr/bin/python3
"""tkinter GUI part for the Horadric Exchange project.

Literature:
===========
[1] The grid.
  https://www.pythontutorial.net/tkinter/tkinter-grid/
  https://tkdocs.com/tutorial/grid.html
[2] Vertical Scrollbar to text area.
  https://stackoverflow.com/questions/13832720/how-to-attach-a-scrollbar-to-a-text-widget
[3] Menus
  https://www.python-kurs.eu/tkinter_menus.php

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/02/06"""


import sys
import shutil
import logging
from pathlib import Path
from os.path import expanduser
from tkinter.filedialog import askopenfile

# > Config.Sys. ------------------------------------------------------
# Edit this for setting default values within the script.
default =\
{
    'pname_work': r'~/tmp',
    'pname_d2': r'~/.wine/drive_c/Program Files/Diablo II/Save'
}
# < ------------------------------------------------------------------



logging.basicConfig(level=logging.INFO, format= '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

pfname_script = Path(__file__)
pfname_icon =  Path(pfname_script.parent, "logo_horadric_exchange.png")
pfname_icon2 = Path(pfname_script.parent, "potion_of_life.png")

try:
    import tkinter as tk
    import tkinter.filedialog
    import tkinter.messagebox
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


class TextWindow:
    """A glorified text box."""
    def __init__(self, parent: tk.Tk, msg: str, img: Optional[tk.PhotoImage] = None, dim=(80,40)):
        self.root = tk.Toplevel(parent)
        self.root.wm_transient(parent)

        if img:
            panel = tk.Label(self.root, image=img)
            panel.grid(row=0, column=0)

        self.ta_content = tk.Text(self.root, width=dim[0], height=dim[1], state='normal', wrap=tk.WORD, font='Arial')
        self.ta_content.grid(row=0, column=1, sticky='ewns')
        self.ta_content.insert(0.0, msg)
        self.ta_content.config(state='disabled')

        self.button_ok = tk.Button(self.root, text='Close', command=self.close, bg='#009999')
        self.button_ok.grid(row=1, column=1, sticky='ew')

    def close(self):
        self.root.destroy()
        self.root.update()


class Horadric_GUI:
    def __init__(self):
        self.horadric_exchange = Horadric()
        self.horadric_horazon = Horadric()

        self.width_column = 40
        self.padding_columns = 10

        self.root = None  # type: Optional[tk.Tk]
        self.icon_horadric_exchange = None  # type: Optional[tk.PhotoImage]
        self.icon_potion_of_life = None  # type: Optional[tk.PhotoImage]

        self.menu = None  # type: Optional[tk.Menu]

        self.tabControl =  None  # type: Optional[ttk.Notebook]
        self.tab1 = None  # type: Optional[ttk.Frame]
        self.tab2 = None  # type: Optional[ttk.Frame]

        self.entry_pfname1 = None  # type: Optional[tk.Entry]
        self.entry_pfname2 = None  # type: Optional[tk.Entry]
        self.ta_desc1 = None  # type: Optional[tk.Text]
        self.ta_desc2 = None  # type: Optional[tk.Text]
        self.button_horadric = None  # type: Optional[tk.Button]
        self.tooltip_commit = None  # type: Optional[Hovertip]

        self.entry_pname_work = None  # type: Optional[tk.Entry]
        self.entry_pname_d2 = None  # type: Optional[tk.Entry]

        self.entry_pname_hero = None  # type: Optional[tk.Entry]
        self.ta_hero = None  # type: Optional[tk.Text]

        self.build_gui()
        if self.root:
            self.root.mainloop()
        else:
            _log.warning("No GUI available.")

    @property
    def pfname_1(self) -> str:
        return self.entry_pfname1.get() if self.entry_pfname1 else ''

    @property
    def pfname_2(self) -> str:
        return self.entry_pfname2.get() if self.entry_pfname2 else ''

    @property
    def pname_work(self) -> str:
        return self.entry_pname_work.get() if self.entry_pname_work else default['pname_work']

    @property
    def pname_d2(self) -> str:
        return self.entry_pname_d2.get() if self.entry_pname_d2 else default['pname_d2']

    def update_button_horadric(self):
        good = False  # type: bool
        if Path(self.pfname_1).is_file() and Path(self.pfname_2).is_file():
            data_1 = self.horadric_exchange.get_data_by_pfname(self.pfname_1, create_if_missing=True)
            data_2 = self.horadric_exchange.get_data_by_pfname(self.pfname_2, create_if_missing=True)
            if data_1.has_horadric_cube and data_2.has_horadric_cube:
                good = True
            else:
                tkinter.messagebox.showerror("Characters not ready.",
                    "At least one of the selected characters lacks a Horadric Cube. This makes Horadric Cube "
                    "exchange impossible. Look for such an item in the desert close to Lut Gholein.")
        self.button_horadric.config(state='normal' if good else 'disabled')

    @staticmethod
    def replace_entry_text(entry: tk.Entry, text: str):
        """Redundancy saving function, encapsulating the somewhat awkward process for replacing an Entries content."""
        entry.config(state='normal')
        entry.delete(0, tk.END)
        entry.insert(0, text)
        entry.config(state='readonly')
        entry.xview_moveto(1)
        entry.update()

    def load_1(self):
        pfname_1 = tkinter.filedialog.askopenfilename(parent=self.root, title='Select First Character File',
                    initialdir=self.pname_d2, filetypes=[("Diablo II character save-game",".d2s *.backup")])
        if pfname_1 == self.pfname_2:
            tk.messagebox.showerror("Twice the same character.", "Error: The first file name cannot match the second one.")
            return
        self.replace_entry_text(self.entry_pfname1, pfname_1)
        self.ta_insert_character_data(self.horadric_exchange, pfname_1, self.ta_desc1)
        self.update_button_horadric()

    def load_2(self):
        pfname_2 = tkinter.filedialog.askopenfilename(parent=self.root, title='Select Second Character File',
                    initialdir=self.pname_d2, filetypes=[("Diablo II character save-game",".d2s *.backup")])
        if self.pfname_1 == pfname_2:
            tk.messagebox.showerror("Twice the same character.", "The second file name cannot match the first one.")
            return
        self.replace_entry_text(self.entry_pfname2, pfname_2)
        self.ta_insert_character_data(self.horadric_exchange, pfname_2, self.ta_desc2)
        self.update_button_horadric()

    def select_pname_work(self):
        pname_work = tkinter.filedialog.askdirectory(parent=self.root, title='Select working directory for backup file storage.', initialdir=self.pname_work, mustexist=True)
        self.replace_entry_text(self.entry_pname_work, pname_work)

    def select_pname_d2(self):
        pname_d2 = tkinter.filedialog.askdirectory(parent=self.root, title="Select directory with .d2s files.", initialdir=self.pname_d2, mustexist=True)
        self.replace_entry_text(self.entry_pname_d2, pname_d2)

    def load_hero(self):
        pfname_hero = tkinter.filedialog.askopenfilename(parent=self.root, title="Select Hero Save-Game", filetypes=[("d2s save-game","*.d2s *.backup")], initialdir=self.pname_d2)
        self.replace_entry_text(self.entry_pname_hero, pfname_hero)
        self.ta_insert_character_data(self.horadric_horazon, pfname_hero, self.ta_hero)

    def pfname2pfname_backup(self, pfname) -> str:
        tm = Data.get_time()
        return str(Path(self.pname_work).joinpath(Path(tm + '_' + Path(pfname).name + '.backup').name))

    def do_horadric_exchange(self):
        data_1 = self.horadric_exchange.get_data_by_pfname(self.pfname_1)
        data_2 = self.horadric_exchange.get_data_by_pfname(self.pfname_2)
        if (not (data_1 and data_2)) or (data_1 == data_2):
            _log.error("Failure to exchange two valid candidates. This should be impossible and indicates a bug.")
            return
        self.horadric_exchange.data_all = [data_1, data_2]
        pfname_backup1 = self.pfname2pfname_backup(self.pfname_1)
        pfname_backup2 = self.pfname2pfname_backup(self.pfname_2)
        shutil.copyfile(expanduser(self.pfname_1), expanduser(pfname_backup1))
        shutil.copyfile(expanduser(self.pfname_2), expanduser(pfname_backup2))
        if self.horadric_exchange.exchange_horadric():
            tkinter.messagebox.showerror("Exchange Failed.", "Horadric Exchange has failed for unknown reasons.")
        else:
            data_1.save2disk()
            data_2.save2disk()
            self.ta_insert_character_data(self.horadric_exchange, self.pfname_1, self.ta_desc1)
            self.ta_insert_character_data(self.horadric_exchange, self.pfname_2, self.ta_desc2)
            tkinter.messagebox.showinfo("Success.", f"Horadric Exchange Succeeded! Backup files have been written into '{self.pname_work}'"
                                        f" ({pfname_backup1} and {pfname_backup2})")

    def reinstate_backup(self):
        pass

    @staticmethod
    def ta_insert_character_data(horadric: Horadric, pfname: str, ta: tk.Text):
        """Load a character's file information into the given text area.
        :param horadric: Horadric instance.
        :param pfname: pfname to a .d2s file.
        :param ta: Target text area. Will be cleared and filled with character info."""
        data = horadric.get_data_by_pfname(pfname, create_if_missing=True)
        if data:
            info = str(data)
            ta.delete(0.0, tk.END)
            ta.insert(0.0, info)
        else:
            tkinter.messagebox.showerror("File not found.", f"Failure to find file '{pfname}'.")

    def mb_settings(self):
        msg = f"""K.I.S.S.! There is no config file to this simple script program. Instead there is a
# > Config Sys ---
...
# < --------------
block at the top of the GUI file, '{Path(__file__).name}', defining the
default locations for backup and save-game files. Edit that block to
match your system and desires.

pname_d2: The directory where this script first looks for .d2s
  character save-game files. Probably should end in 'Diablo II/Save'
  
 pname_work: The directory this script uses as storage for backup files."""
        TextWindow(self.root, msg, None, (71, 13))

    def mb_about(self):
        msg = """Limited to v1.10-v1.14d of Diablo II.
        
These are pretty old versions. Sorry. However, upgrading horazons_folly.py
(which contains all the interesting stuff) to more modern versions of
.d2s save-game files should be rather straight-forward.

This program allows two single player Diablo II characters to first put items
into their respective Horadric Cubes and then have these cubes exchanged.

Thus, e.g., a Barbarian finding a powerful wand may pass it on, making
his Necromancer hero colleague happy -- and maybe even receive something
in return, that the Necromancer can make no real use of.

There is more than this, in my opinion, legit function.
But let's keep silent about what can only be described as cheating.

February 2025, Markus-H. Koch ( https://github.com/kochsoft/diablo2 )"""
        TextWindow(self.root, msg, self.icon_horadric_exchange, (70,18))

    def build_gui(self):
        # > Main Window. ---------------------------------------------
        self.root = tk.Tk()
        self.root.title("Horadric Exchange")
        self.root.geometry('1024x760')
        self.icon_horadric_exchange = tk.PhotoImage(file=str(pfname_icon))
        self.icon_potion_of_life = tk.PhotoImage(file=str(pfname_icon2))
        self.root.iconphoto(True, self.icon_horadric_exchange)
        # < ----------------------------------------------------------
        # > Menu. ----------------------------------------------------
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        menu_files = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=menu_files)
        menu_files.add_command(label="Reinstate Backup ...", command=self.reinstate_backup)
        menu_files.add_separator()
        menu_files.add_command(label="Load Character 1 ...", command=self.load_1)
        menu_files.add_command(label="Load Character 2 ...", command=self.load_2)
        menu_files.add_command(label="Load Horazon Hero ...", command=self.load_hero)
        menu_files.add_separator()
        menu_files.add_command(label="Exit", command=self.root.quit)
        menu_help = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Help", menu=menu_help)
        menu_help.add_command(label="Settings ...", command=self.mb_settings)
        menu_help.add_command(label="About ...", command=self.mb_about)
        # < ----------------------------------------------------------
        # > Tabs. ----------------------------------------------------
        self.tabControl = ttk.Notebook(self.root)
        self.tab1 = ttk.Frame(self.tabControl)
        self.tab2 = ttk.Frame(self.tabControl)

        # Columns 1 and 4 (textboxes) receive weight for stretching, if the main tab resizes.
        self.tab1.columnconfigure(1, weight=1)
        self.tab1.columnconfigure(4, weight=1)
        self.tab1.rowconfigure(1, weight=1)
        self.tab2.columnconfigure(1, weight=1)

        self.tabControl.add(self.tab1, text="Horadric Exchange")
        self.tabControl.add(self.tab2, text="Horazon's Folly")
        self.tabControl.pack(expand=1, fill=tk.BOTH)
        # < ----------------------------------------------------------
        # > Tab 1, Horadric Exchange. --------------------------------
        label_1 = tk.Label(self.tab1, text='1.:', relief=tk.RIDGE, width=12)
        label_1.grid(row=0, column=0)
        label_2 = tk.Label(self.tab1, text='2.:', relief=tk.RIDGE, width=12)
        label_2.grid(row=0, column=3)

        self.entry_pfname1 = tk.Entry(self.tab1, width=self.width_column - 7, state='readonly')
        self.entry_pfname1.grid(row=0, column=1, sticky='ew')
        self.entry_pfname2 = tk.Entry(self.tab1, width=self.width_column - 7, state='readonly')
        self.entry_pfname2.grid(row=0, column=4, sticky='ew')

        tk.Button(self.tab1, text='First .d2s', command=self.load_1, width=10, height=1, bg='#009999').grid(row=0, column=2) #, padx=(0,20)
        tk.Button(self.tab1, text='Second d2s', command=self.load_2, width=10, height=1, bg='#009999').grid(row=0, column=5)

        self.ta_desc1 = tk.Text(self.tab1, width=self.width_column, state='normal', wrap=tk.WORD)
        self.ta_desc1.grid(row=1, column=0, columnspan=3, sticky='ewns')
        self.ta_desc2 = tk.Text(self.tab1, width=self.width_column, state='normal', wrap=tk.WORD)
        self.ta_desc2.grid(row=1, column=3, columnspan=3, sticky='ewns')

        self.entry_pname_work = tk.Entry(self.tab1, width=self.width_column - 7)
        self.entry_pname_work.grid(row=2, column=1, columnspan=2, sticky='ew')
        self.entry_pname_d2 = tk.Entry(self.tab1, width=self.width_column - 7)
        self.entry_pname_d2.grid(row=3, column=1, columnspan=2, sticky='ew')
        self.replace_entry_text(self.entry_pname_work, default['pname_work'])
        self.replace_entry_text(self.entry_pname_d2, default['pname_d2'])

        tk.Button(self.tab1, text='Work Dir', command=self.select_pname_work, width=10, height=1, bg='#009999').grid(row=2, column=0)
        tk.Button(self.tab1, text='D2 Save Dir', command=self.select_pname_d2, width=10, height=1, bg='#009999').grid(row=3, column=0)

        label_wd = tk.Label(self.tab1, anchor='w', text='<- Working Dir. Where backups will be kept.', relief=tk.RIDGE, width=10)
        label_wd.grid(row=2, column=3, columnspan=3, sticky='ew')
        label_d2 = tk.Label(self.tab1, anchor='w', text='<- D2 Save-Game Dir. Where .d2s save-games will be edited.', relief=tk.RIDGE, width=10)
        label_d2.grid(row=3, column=3, columnspan=3, sticky='ew')

        self.button_horadric = tk.Button(self.tab1, state='disabled', image=self.icon_horadric_exchange, command=self.do_horadric_exchange)
        self.button_horadric.grid(row=4, column=0, columnspan=10, sticky='ew')
        self.tooltip_commit = Hovertip(self.button_horadric, 'Load two character files and swap their Horadric Cube contents.')
        #self.tooltip_commit.text= "Huhu"
        # < ----------------------------------------------------------
        # > Tab 2: Horazon's Folly. ----------------------------------
        ta_introduction = tk.Text(self.tab2, width=80, height=8, state='normal', wrap=tk.WORD)
        ta_introduction.grid(row=0, column=0, columnspan=3, sticky='ew')
        msg_horazon = """
\"Demonic magic is a quick path, but its powers are seductive and deadly.\" (Deckard Cain)

This tab grants great, quick power over the abilities of any hero.
However, using it is bound to take out the spice of the game.

Beware!"""
        ta_introduction.insert(0.0, msg_horazon)
        ta_introduction.config(state='disabled')

        tk.Button(self.tab2, text='Select Hero', command=self.load_hero, width=10, height=1, bg='#009999').grid(row=1, column=0)
        self.entry_pname_hero = tk.Entry(self.tab2, width=self.width_column - 7, state='readonly')
        self.entry_pname_hero.grid(row=1, column=1, sticky='ew')

        # There is really no reason, why the user should not write into this text area.
        self.ta_hero = tk.Text(self.tab2, state='normal', wrap=tk.WORD)
        self.ta_hero.grid(row=2, column=0, columnspan=2, sticky='ew')
        # < ----------------------------------------------------------


if __name__ == '__main__':
    Horadric_GUI()
    print("Done.")
