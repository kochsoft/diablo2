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
import os.path
import sys
import shutil
import logging
from pathlib import Path
from copy import deepcopy

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

colors = { 'button': '#009999', 'red'   : '#ff5050', 'green' : '#90ee90' }


try:
    import tkinter as tk
    import tkinter.filedialog
    import tkinter.messagebox
    from tkinter import ttk
    from tkinter.filedialog import askopenfile
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

        self.button_pname_work = None  # type: Optional[tk.Button]
        self.entry_pname_work = None  # type: Optional[tk.Entry]
        self.entry_pname_d2 = None  # type: Optional[tk.Entry]

        self.entry_pname_hero = None  # type: Optional[tk.Entry]
        self.ta_hero = None  # type: Optional[tk.Text]

        self.data_hero_backup = None  # type: Optional[Data]
        self.button_load_cube = None  # type: Optional[tk.Button]
        self.button_save_cube = None  # type: Optional[tk.Button]
        self.button_runic_cube = None  # type: Optional[tk.Button]
        self.button_revive_hero = None  # type: Optional[tk.Button]
        self.button_revive_mercenary = None  # type: Optional[tk.Button]
        self.button_jewelize = None  # type: Optional[tk.Button]
        self.button_forge_ring = None  # type: Optional[tk.Button]
        self.button_forge_charm = None  # type: Optional[tk.Button]
        self.button_forge_amulet = None  # type: Optional[tk.Button]
        self.button_redeem_golem = None  # type: Optional[tk.Button]
        self.button_ensure_cube = None  # type: Optional[tk.Button]
        self.button_enable_nightmare = None  # type: Optional[tk.Button]
        self.button_enable_hell = None  # type: Optional[tk.Button]
        self.button_enable_nirvana = None  # type: Optional[tk.Button]
        self.button_reset_skills = None  # type: Optional[tk.Button]
        self.button_reset_attributes = None  # type: Optional[tk.Button]
        self.button_boost_skills = None  # type: Optional[tk.Button]
        self.button_boost_attributes = None  # type: Optional[tk.Button]
        self.button_toggle_ethereal = None  # type: Optional[tk.Button]
        self.button_regrade_items = None  # type: Optional[tk.Button]
        self.button_dispel_magic = None  # type: Optional[tk.Button]
        self.button_set_sockets = None  # type: Optional[tk.Button]
        self.button_empty_sockets = None  # type: Optional[tk.Button]
        self.check_hardcore = None  # type: Optional[tk.Checkbutton]
        self.check_godmode = None  # type: Optional[tk.Checkbutton]
        self.check_wp_hop = None  # type: Optional[tk.Checkbutton]
        self.entry_runic_cube = None  # type: Optional[tk.Entry]
        self.button_revive_cows = None  # type: Optional[tk.Button]
        self.button_personalize = None  # type: Optional[tk.Button]
        self.entry_personalize = None  # type: Optional[tk.Entry]
        self.entry_boost_skills = None  # type: Optional[tk.Entry]
        self.entry_boost_attributes = None  # type: Optional[tk.Entry]
        self.entry_set_sockets = None  # type: Optional[tk.Entry]
        self.button_horazon = None  # type: Optional[tk.Button]
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

    @pname_work.setter
    def pname_work(self, pname: str):
        self.replace_entry_text(self.entry_pname_work, pname)
        if self.validate_pname_work(False):
            self.update_hero_widgets(len(self.horadric_horazon.data_all) > 0)

    @property
    def pname_d2(self) -> str:
        return self.entry_pname_d2.get() if self.entry_pname_d2 else default['pname_d2']

    def validate_pname_work(self, show_info: bool=True) -> bool:
        pname = os.path.expanduser(self.pname_work)
        pname_d2 = os.path.expanduser(self.pname_d2)
        if pname == pname_d2 or (os.path.isdir(pname) and os.access(pname, os.W_OK) and os.access(pname, os.R_OK)):
            self.button_pname_work.config(bg=colors['green'])
            return True
        self.button_pname_work.config(bg=colors['red'])
        if show_info:
            TextWindow(self.root, f"""Working directory '{self.pname_work}' cannot be opened for reading and writing.

Horadric Exchange does a lot of back-upping.
 
* d2s save-game files are back-upped with character name and timestamp.
* Activating god-mode for a character will leave a .humanity-datafile, that
  will allow a character to return to humanity later on.
* Horadric Cube contents, too can be saved to disk.

All this is done in a working directory. Its current default is given above.
And it cannot be found for writing on your system. So please select an
adequate working directory which should also not be the Diablo II Save dir.

It is encouraged to edit the 'config.sys' section close to the top of
{os.path.basename(__file__)}, setting defaults for these two directories
that fit your system.""", dim=(60,17))
        return False

    def update_button_horadric(self):
        good = False  # type: bool
        if Path(self.pfname_1).is_file() and Path(self.pfname_2).is_file():
            data_1 = self.horadric_exchange.get_data_by_pfname(self.pfname_1, create_if_missing=True)
            data_2 = self.horadric_exchange.get_data_by_pfname(self.pfname_2, create_if_missing=True)
            if self.validate_pname_work(False) and data_1.has_horadric_cube and data_2.has_horadric_cube:
                good = True
            else:
                tkinter.messagebox.showerror("Characters not ready or working directory invalid. ",
                    "Either the working directory is not selected validly, or at least one "
                    "of the selected characters lacks a Horadric Cube. This would make Horadric Cube "
                    "exchange impossible. If so, look for such an item in the desert close to Lut Gholein.")
        self.button_horadric.config(state='normal' if good else 'disabled')

    @staticmethod
    def replace_entry_text(entry: tk.Entry, text: str):
        """Redundancy saving function, encapsulating the somewhat awkward process for replacing an Entries content."""
        old_state = entry.config()['state'][4]
        entry.config(state='normal')
        entry.delete(0, tk.END)
        entry.insert(0, text)
        entry.config(state=old_state)
        entry.xview_moveto(1)
        entry.update()

    def load_1(self):
        pfname_1 = tkinter.filedialog.askopenfilename(parent=self.root, title='Select First Character File',
                    initialdir=self.pname_d2, filetypes=[("Diablo II character save-game",".d2s *.backup")])
        if not pfname_1:
            return
        if pfname_1 == self.pfname_2:
            tk.messagebox.showerror("Twice the same character.", "Error: The first file name cannot match the second one.")
            return
        self.replace_entry_text(self.entry_pfname1, pfname_1)
        self.ta_insert_character_data(self.horadric_exchange, pfname_1, self.ta_desc1)
        self.tabControl.select(self.tab1)
        self.update_button_horadric()

    def load_2(self):
        pfname_2 = tkinter.filedialog.askopenfilename(parent=self.root, title='Select Second Character File',
                    initialdir=self.pname_d2, filetypes=[("Diablo II character save-game",".d2s *.backup")])
        if not pfname_2:
            return
        if self.pfname_1 == pfname_2:
            tk.messagebox.showerror("Twice the same character.", "The second file name cannot match the first one.")
            return
        self.replace_entry_text(self.entry_pfname2, pfname_2)
        self.ta_insert_character_data(self.horadric_exchange, pfname_2, self.ta_desc2)
        self.tabControl.select(self.tab1)
        self.update_button_horadric()

    def select_pname_work(self):
        pname_work = tkinter.filedialog.askdirectory(parent=self.root, title='Select working directory for backup file storage.', initialdir=self.pname_work, mustexist=True)
        if not pname_work:
            return
        self.pname_work = pname_work

    def select_pname_d2(self):
        pname_d2 = tkinter.filedialog.askdirectory(parent=self.root, title="Select directory with .d2s files.", initialdir=self.pname_d2, mustexist=True)
        if not pname_d2:
            return
        self.replace_entry_text(self.entry_pname_d2, pname_d2)

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
        print(f"Writing backup files '{pfname_backup1}' and '{pfname_backup2}'.")
        shutil.copyfile(expanduser(self.pfname_1), expanduser(pfname_backup1))
        shutil.copyfile(expanduser(self.pfname_2), expanduser(pfname_backup2))
        if self.horadric_exchange.exchange_horadric():
            tkinter.messagebox.showerror("Exchange Failed.", "Horadric Exchange has failed for unknown reasons.")
        else:
            data_1.update_all()
            data_2.update_all()
            data_1.save2disk()
            data_2.save2disk()
            self.ta_insert_character_data(self.horadric_exchange, self.pfname_1, self.ta_desc1)
            self.ta_insert_character_data(self.horadric_exchange, self.pfname_2, self.ta_desc2)
            tkinter.messagebox.showinfo("Success.", f"Horadric Exchange Succeeded! Backup files have been written into '{self.pname_work}'"
                                        f" ({pfname_backup1} and {pfname_backup2})")

    def ta_insert_character_data(self, horadric: Horadric, pfname: str, ta: tk.Text) -> int:
        """Load a character's file information into the given text area.
        :param horadric: Horadric instance.
        :param pfname: pfname to a .d2s file.
        :param ta: Target text area. Will be cleared and filled with character info."""
        data = horadric.get_data_by_pfname(pfname, create_if_missing=True)
        if data:
            info = str(data)
            ta.delete(0.0, tk.END)
            ta.insert(0.0, info)
            self.update_hero_widgets(True)
            return 0
        else:
            tkinter.messagebox.showerror("File not found.", f"Failure to find file '{pfname}'.")
            return 1

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
But let's keep silent about what can only be described as despicable cheating.

February 2025, Markus-H. Koch ( https://github.com/kochsoft/diablo2 )"""
        TextWindow(self.root, msg, self.icon_horadric_exchange, (70,18))

    def load_backup(self):
        pfname_backup = tkinter.filedialog.askopenfilename(parent=self.root, title="Select backup file.",
                                           filetypes=[("d2s backup", "*.backup")], initialdir=self.pname_work)
        if not pfname_backup:
            return
        pfname_backup = os.path.expanduser(pfname_backup)
        fname_backup = os.path.basename(pfname_backup)

        fname_target = re.sub('^[0-9_]+', '', fname_backup)
        fname_target = re.sub('\\.backup$', '', fname_target, flags=re.IGNORECASE)
        pfname_target = os.path.expanduser(os.path.join(self.pname_d2, fname_target))
        if not os.path.isfile(pfname_target):
            _log.warning(f"Backup file '{pfname_backup}' leads to non-existing target file '{pfname_target}'.")
            tk.messagebox.showinfo("Installing Backup", f"Copying backup file '{pfname_backup}' into Diablo II save-game directory as '{pfname_target}'.")
        else:
            tk.messagebox.showinfo("Reinstating Backup", f"Copying backup file '{pfname_backup}' to replace active save-game '{pfname_target}'.")
        shutil.copyfile(pfname_backup, pfname_target)

    def verify_hero(self) -> Optional[Data]:
        if self.horadric_horazon.data_all:
            return self.horadric_horazon.data_all[0]
        else:
            tk.messagebox.showerror("No Hero", "No hero has been loaded. Unable to proceed.")
            return None

    def load_hero(self):
        pfname_hero = tkinter.filedialog.askopenfilename(parent=self.root, title="Select Hero Save-Game",
                        filetypes=[("d2s save-game","*.d2s *.backup"),("cube file", "*.cube")], initialdir=self.pname_d2)
        if not pfname_hero:
            return
        self.replace_entry_text(self.entry_pname_hero, pfname_hero)
        # >> Loading a cube for pure review. -------------------------
        if pfname_hero.lower().endswith(".cube"):
            with open(pfname_hero, 'rb') as IN:
                code = IN.read()
            n = len(code)
            items = list()  # type: List[Item]
            index0 = 0
            while index0 != n:
                index1 = code.find(b"JM", index0+2)
                index1 = index1 if index1 > 0 else n
                items.append(Item(code, index0, index1))
                index0 = index1
            info = 'Cube content.\n=============\n'
            for item in items:
                info += f"{item}\n"
            self.ta_hero.delete(0.0, tk.END)
            self.ta_hero.insert(0.0, info)
            self.horadric_horazon.data_all.clear()
            self.update_hero_widgets(False)
            self.tabControl.select(self.tab2)
        # << ---------------------------------------------------------
        # >> Loading a character. ------------------------------------
        else:
            self.horadric_horazon.data_all = [Data(pfname_hero, pname_backup=os.path.expanduser(self.pname_work))]
            self.data_hero_backup = deepcopy(self.horadric_horazon.data_all[0])
            self.data_hero_backup.pfname = self.pfname2pfname_backup(pfname_hero)
            err = self.ta_insert_character_data(self.horadric_horazon, pfname_hero, self.ta_hero)
            if err == 0:
                self.update_hero_widgets(err == 0)
                self.tabControl.select(self.tab2)
        # << ---------------------------------------------------------
    def load_cube(self):
        data = self.verify_hero()
        if not data:
            return
        pfname_in = tk.filedialog.askopenfilename(parent=self.root, title='Load Horadric Cube Contents.',
                        filetypes=[('Horadric Cube File', '*.cube')], initialdir=self.pname_work)
        if os.path.isfile(pfname_in):
            self.horadric_horazon.load_horadric(pfname_in)
            self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def save_cube(self):
        data = self.verify_hero()
        if not data:
            return
        pfname_out = tk.filedialog.asksaveasfilename(parent=self.root, title='Save Horadric Cube Contents.',
                        initialfile=Path(data.pfname).stem + '.cube',
                        confirmoverwrite=True, filetypes=[('Horadric Cube File', '*.cube')], initialdir=self.pname_work)
        if pfname_out:
            self.horadric_horazon.save_horadric(pfname_out)
            tk.messagebox.showinfo("Wrote Horadric Cube Backup.", f"Cube file written to '{pfname_out}'.")

    def reset_skills(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.reset_skills()
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def reset_attributes(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.reset_attributes()
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_jewelize(self, tpl_type_code: str = 'jew') -> bool:
        data = self.verify_hero()
        if not data:
            return False
        for item in Item(data.data).get_cube_contents():
            has_runeword = item.get_item_property(E_ItemBitProperties.IP_RUNEWORD) and \
                           item.quality in (E_Quality.EQ_NORMAL, E_Quality.EQ_SUPERIOR, E_Quality.EQ_INFERIOR)
            if has_runeword:
                return True
            # [Note: Mechanic items are, in principle, eligible. However, we cannot socket rings and the like.]
            if item.n_sockets:
                continue
            if item.type_code.lower() != tpl_type_code and item.quality in \
                    (E_Quality.EQ_RARE, E_Quality.EQ_MAGICALLY_ENHANCED, E_Quality.EQ_CRAFT, E_Quality.EQ_UNIQUE, E_Quality.EQ_SET):
                return True
        return False

    def jewelize(self, tpl: E_ItemTpl = E_ItemTpl.IT_JEWEL):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.jewelize_horadric(data, tpl)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def revive_hero(self):
        data = self.verify_hero()
        if not data:
            return
        if data.is_hardcore() and data.is_dead():
            fem = data.get_class_enum().is_female()
            res = tk.messagebox.askquestion(f"Revive {data.get_name(True)}",
                    f"{data.get_name(True)} is a hardcore character. {'She' if fem else 'He'} wants to be dead. "
                    f"Do you really want to take that away from {'her' if fem else 'him'}?",
                    icon='warning')
            if res != 'yes':
                return
        self.horadric_horazon.set_dead_self(False)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def revive_mercenary(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.set_dead_mercenary(False)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def redeem_golem(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.redeem_golem(data)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def ensure_cube(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.ensure_horadric(data)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def enable_nightmare(self):
        data = self.verify_hero()
        if not data:
            return
        data.enable_nightmare()
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def enable_hell(self):
        data = self.verify_hero()
        if not data:
            return
        data.enable_hell()
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def enable_nirvana(self):
        """Progress beyond Hell. As a gimmick, this also enables all waypoints."""
        data = self.verify_hero()
        if not data:
            return
        # Reset all quests to 0.
        # [Note: data.waypoint_map = ... below will ensure that the minimal set of quest data is applied.]
        index_quests = E_Quest.EQ_M_WARRIV.pos_byte_in_d2s(E_Progression.EP_NORMAL)
        data.data = data.data[:index_quests] + (b'\x00' * 96 * 3) + data.data[(index_quests + 3 * 96):]
        data.enable_nirvana()
        # [Note: Enabling all waypoints for a level 86 character is a nice touch, that I do want. Use-case for
        #  This option is battling Baal in Hell.]
        # [Note: First reset all waypoints. This will ensure that the next setting below will also do a quest update.]
        bm = '100000000100000000100000000100100000000'
        data.waypoint_map = {E_Progression.EP_NORMAL: bm, E_Progression.EP_NIGHTMARE: bm, E_Progression.EP_HELL: bm}
        bm = '111111111111111111111111111111111111111'
        data.waypoint_map = {E_Progression.EP_NORMAL: bm, E_Progression.EP_NIGHTMARE: bm, E_Progression.EP_HELL: bm}

        #all_done = E_Quest.get_example_completed_quests()
        #data.data = data.data[:345] + (3 * all_done) + data.data[(345+3*len(all_done)):]

        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def runic_cube(self, text_runic_cube: str):
        """Parses the string given in the runic cube textbox. Allows for runes, gems, and the small charms
        specified in d_gimmicks."""
        codes_raw = re.findall('([a-zA-Z0-9]+)', text_runic_cube)
        codes_runic = list()  # type: List[str]
        items = list()  # type: List[Item]
        for cr in codes_raw:
            if cr in d_gimmick:
                items.append(Item(d_gimmick[cr], 0, len(d_gimmick[cr])))
            else:
                codes_runic.append(cr)
        runes = list(filter(lambda x: x is not None, [E_Rune.from_name(w) for w in codes_runic]))
        if (not runes) and (not items):
            tk.messagebox.showinfo("Runic Cube", "Use a comma-separated list of rune names and gem codes to create "
                                                 "that set of items in and around your Horadric Cube. E.g., 'ral, ort, tal'.")
            return
        for rune in runes:
            items.append(Item.create_rune(rune, E_ItemStorage.IS_CUBE)) #, row, col))
        data = self.verify_hero()
        if data is None:
            return
        # self.horadric_horazon.drop_horadric(data)
        data.place_items_into_storage_maps(items)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_revive_cows(self):
        data = self.verify_hero()
        if data is None:
            return False
        for prog in [E_Progression.EP_NORMAL, E_Progression.EP_NIGHTMARE, E_Progression.EP_HELL]:
            bts = E_Quest.get_quest_block(data.data, prog)
            if E_Quest.is_cow_level_done(bts):
                return True
        return False

    def revive_cows(self):
        self.horadric_horazon.revive_cows()

    def needs_personalize(self) -> bool:
        data = self.verify_hero()
        if data is None:
            return False
        return False if (not data.has_horadric_cube) or (data.n_cube_contents_shallow == 0) else True

    def personalize(self, name: Optional[str]):
        data = self.verify_hero()
        if data is None:
            return
        if not name:
            name = None
        items = Item(data.data).get_cube_contents()
        items_new = list()  # type: List[Item]
        for item in items:
            row = item.row
            col = item.col
            bts = item.create_personalized_copy(name)
            if bts:
                item_new = Item(bts, 0, len(bts))
                item_new.row = row
                item_new.col = col
                items_new.append(item_new)
        data.drop_items(items)
        data.place_items_into_storage_maps(items_new, E_ItemStorage.IS_CUBE)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def verify_personalization_name(self, name: str):
        """Verifies if the current personalization string is valid. If it is: Turn the entries background green, else red."""
        normalized = Item.normalize_name(name)
        is_valid = (name == '') or (len(name) >= 2 and normalized == name)
        if is_valid:
            self.entry_personalize.config({'background': colors['green']})
        else:
            self.entry_personalize.config({'background': colors['red']})

    @staticmethod
    def entry2int(entry: tk.Entry, default_placeholder: int = 0, min_val: int = 0, max_val: int = 1023):
        """Verify if the entry has an int-parsable value. If not, replace by str(default_placeholder)."""
        try:
            val = int(entry.get())
            if not min_val <= val <= max_val:
                if val < min_val:
                    default_placeholder = min_val
                elif val > max_val:
                    default_placeholder = max_val
                raise ValueError(f"Value {val} out of range {min_val}..{max_val}.")
        except ValueError:
            Horadric_GUI.replace_entry_text(entry, f'{default_placeholder}')
            val = default_placeholder
        return val

    def boost_skills(self):
        val = self.entry2int(self.entry_boost_skills, 0, 0, 255)
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.boost(E_Attributes.AT_UNUSED_SKILLS, val)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def boost_attributes(self):
        val = self.entry2int(self.entry_boost_attributes, 0, 0, 1023)
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.boost(E_Attributes.AT_UNUSED_STATS, val)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_toggle_ethereal(self):
        data = self.verify_hero()
        if not data:
            return False
        for item in Item(data.data).get_cube_contents():
            if item.is_armor or item.is_weapon:
                return True
        return False

    def toggle_ethereal(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.toggle_ethereal(data)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_regrade_items(self):
        """Should the regrade items button be active?"""
        data = self.verify_hero()
        if not data:
            return False
        for item in Item(data.data).get_cube_contents():
            fam = ItemFamily.get_family_by_code(item.type_code)
            if fam and len(fam.code_names) >= 2:
                return True
        return False

    def regrade_items(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.regrade_horadric(data)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_dispel_magic(self) -> bool:
        """Does the Horadric Cube contain any magic items? (Or should the dispel-magic-button be disabled?)"""
        data = self.verify_hero()
        if not data:
            return False
        for item in Item(data.data).get_cube_contents():
            if item.is_magic:
                return True
        return False

    def dispel_magic(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.dispel_magic_horadric(data)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def set_sockets(self):
        count = self.entry2int(self.entry_set_sockets, 6, 0, 6)
        data = self.verify_hero()
        if not data:
            return
        items = Item(data.data).get_cube_contents()
        for item in items:
            data.set_sockets(item, count)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_empty_sockets(self) -> bool:
        """Does the Horadric Cube contain any items with socketed stones or runes? (Or should the empty-sockets-button be disabled?)"""
        data = self.verify_hero()
        if not data:
            return False
        for item in Item(data.data).get_cube_contents():
            if item.n_sockets_occupied:
                return True
        return False

    def empty_sockets(self):
        data = self.verify_hero()
        if not data:
            return
        self.horadric_horazon.empty_sockets_horadric(data)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def set_hardcore(self, enable: bool):
        data = self.verify_hero()
        if not data:
            return
        data.set_hardcore(enable)
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def set_godmode(self, enable: bool):
        data = self.verify_hero()
        if not data:
            return
        if enable:
            data.enable_godmode()
        else:
            err = data.disable_godmode()
            if err:
                self.check_godmode.select()
                tkinter.messagebox.showerror("Failure to Restore Humanity.",
                    f"Failure to restore humanity to {data.get_name(True)}. '{data.pfname_humanity}' was not found.")
                return
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)

    def needs_wp_hop(self) -> bool:
        """:returns True if quest of index 24 (Betrayal in Harrogath) in the currently highest active difficulty
        is anything other than b'\x00'.'"""
        data = self.verify_hero()
        if not data:
            return False
        quests = data.get_quests_simplified()[data.highest_difficulty]
        if len(quests) < 24:
            return False
        return quests[24] == '1'

    def set_wp_hop(self, enable: bool):
        data = self.verify_hero()
        if not data:
            return
        bm = (E_Waypoint.EW_HALLS_OF_PAIN.value * '.') + ('1' if enable else '0')
        data.waypoint_map = {data.highest_difficulty: bm}

    def update_hero_widgets(self, enable: bool, *, do_update: bool = True):
        """Common Horazon widget update function."""
        if not self.validate_pname_work(False):
            enable = False
        for widget in [self.button_load_cube, self.button_save_cube, self.button_reset_skills, self.button_runic_cube,
                       self.button_reset_attributes, self.button_boost_skills, self.button_boost_attributes,
                       self.check_hardcore, self.check_godmode, self.check_wp_hop, self.entry_boost_skills, self.entry_runic_cube,
                       self.button_revive_cows, self.button_personalize, self.entry_personalize,
                       self.entry_boost_attributes, self.entry_set_sockets, self.button_horazon, self.button_ensure_cube,
                       self.button_enable_nightmare, self.button_enable_hell, self.button_enable_nirvana,
                       self.button_revive_hero, self.button_revive_mercenary, self.button_jewelize,
                       self.button_forge_ring, self.button_forge_charm, self.button_forge_amulet,
                       self.button_redeem_golem, self.button_toggle_ethereal, self.button_regrade_items,
                       self.button_dispel_magic, self.button_set_sockets, self.button_empty_sockets]:
            if enable:
                widget.config(state='normal')
            else:
                widget.config(state='disabled')
        if do_update and enable and len(self.horadric_horazon.data_all):
            data = self.horadric_horazon.data_all[0]  # type: Data
            if not self.needs_jewelize('jew'):
                self.button_jewelize.config(state='disabled')
            if not data.is_dead():
                self.button_revive_hero.config(state='disabled')
            if not data.is_dead_mercenary:
                self.button_revive_mercenary.config(state='disabled')
            if not self.needs_jewelize('rin'):
                self.button_forge_ring.config(state='disabled')
            if not self.needs_jewelize('cm1'):
                self.button_forge_charm.config(state='disabled')
            if not self.needs_jewelize('amu'):
                self.button_forge_amulet.config(state='disabled')
            if not data.has_iron_golem:
                self.button_redeem_golem.config(state='disabled')
            if not self.needs_dispel_magic():
                self.button_dispel_magic.config(state='disabled')
            if not self.needs_toggle_ethereal():
                self.button_toggle_ethereal.config(state='disabled')
            if not self.needs_regrade_items():
                self.button_regrade_items.config(state='disabled')
            if not self.needs_empty_sockets():
                self.button_empty_sockets.config(state='disabled')
            if not self.needs_wp_hop():
                self.check_wp_hop.config(state='disabled')
            if not data.has_horadric_cube:
                self.button_load_cube.config(state='disabled')
                self.button_save_cube.config(state='disabled')
                self.button_runic_cube.config(state='disabled')
                self.button_ensure_cube.config(state='normal')
            else:
                self.button_ensure_cube.config(state='disabled')
            if not self.needs_revive_cows():
                self.button_revive_cows.config(state='disabled')
            if not self.needs_personalize():
                self.button_personalize.config(state='disabled')
            if data.progression >= 5:
                self.button_enable_nightmare.config(state='disabled')
            if data.progression >= 10:
                self.button_enable_hell.config(state='disabled')
            if data.progression >= 15:
                self.button_enable_nirvana.config(state='disabled')
            if len(self.entry_boost_skills.get()) == 0:
                self.entry_boost_skills.delete(0, tk.END)
                self.entry_boost_skills.insert(0, '0')
            if len(self.entry_boost_attributes.get()) == 0:
                self.entry_boost_attributes.delete(0, tk.END)
                self.entry_boost_attributes.insert(0, '0')
            if data.is_hardcore():
                self.check_hardcore.select()
            else:
                self.check_hardcore.deselect()
            if data.is_demi_god:
                self.check_godmode.select()
            else:
                self.check_godmode.deselect()
            wps = data.waypoint_map[data.highest_difficulty]
            if wps[E_Waypoint.EW_HALLS_OF_PAIN.value] == '1':
                self.check_wp_hop.select()
            else:
                self.check_wp_hop.deselect()

    def do_commit_horazon(self):
        """Save the current hero to disk. A backup has been made earlier, during self.update_hero_widgets(..)."""
        data = self.verify_hero()
        if not data:
            return
        for d in [data, self.data_hero_backup]:
            d.update_all()
            d.save2disk()
        self.ta_insert_character_data(self.horadric_horazon, data.pfname, self.ta_hero)
        tk.messagebox.showinfo("Modifications Saved.", f"Alteration of the Hero has been saved to '{data.pfname}'. "
                               f"A backup file may be found at '{self.data_hero_backup.pfname}'.")

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
        menu_files.add_command(label="Load Character 1 ...", command=self.load_1)
        menu_files.add_command(label="Load Character 2 ...", command=self.load_2)
        menu_files.add_command(label="Load Horazon Hero ...", command=self.load_hero)
        menu_files.add_separator()
        menu_files.add_command(label="Reinstate backup ...", command=self.load_backup)
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

        self.button_pname_work = tk.Button(self.tab1, text='Work Dir', command=self.select_pname_work, width=10, height=1, bg='#009999')
        self.button_pname_work.grid(row=2, column=0)
        tk.Button(self.tab1, text='D2 Save Dir', command=self.select_pname_d2, width=10, height=1, bg='#009999').grid(row=3, column=0)

        label_wd = tk.Label(self.tab1, anchor='w', text='<- Working Dir. Where backups will be kept.', relief=tk.RIDGE, width=10)
        label_wd.grid(row=2, column=3, columnspan=3, sticky='ew')
        label_d2 = tk.Label(self.tab1, anchor='w', text='<- D2 Save-Game Dir. Where .d2s save-games will be edited.', relief=tk.RIDGE, width=10)
        label_d2.grid(row=3, column=3, columnspan=3, sticky='ew')

        self.button_horadric = tk.Button(self.tab1, state='disabled', image=self.icon_horadric_exchange, command=self.do_horadric_exchange, bg='#009999')
        self.button_horadric.grid(row=4, column=0, columnspan=11, sticky='ew')
        self.tooltip_commit = Hovertip(self.button_horadric, 'Load two character files and click this button to swap their Horadric Cube contents.')
        # < ----------------------------------------------------------
        # > Tab 2: Horazon's Folly. ----------------------------------
        ta_introduction = tk.Text(self.tab2, width=80, height=6, state='normal', wrap=tk.WORD)
        ta_introduction.grid(row=0, column=0, columnspan=6, sticky='ew')
        msg_horazon = """\"Demonic magic is a quick path, but its powers are seductive and deadly.\" (Deckard Cain)

This tab grants great, quick power over the abilities of any hero.
However, using it is bound to take out the spice of the game.

Beware!"""
        ta_introduction.insert(0.0, msg_horazon)
        ta_introduction.config(state='disabled', bg='#fffaa0')

        button_load_hero = tk.Button(self.tab2, text='Select Hero', command=self.load_hero, width=10, height=1, bg='#009999')
        button_load_hero.grid(row=1, column=0)
        Hovertip(button_load_hero, 'Select .d2s hero file. Or, for review only, a .cube file.')
        self.entry_pname_hero = tk.Entry(self.tab2, width=self.width_column - 7, state='readonly')
        self.entry_pname_hero.grid(row=1, column=1, columnspan=5, sticky='ew')

        # There is really no reason, why the user should not write into this text area.
        self.ta_hero = tk.Text(self.tab2, state='normal', wrap=tk.WORD)
        self.ta_hero.grid(row=2, column=0, columnspan=6, sticky='ew')

        self.button_load_cube = tk.Button(self.tab2, text='Load Cube', command=self.load_cube, width=10, height=1, bg='#009999')
        self.button_load_cube.grid(row=3, column=0)
        Hovertip(self.button_load_cube, 'Load a .cube file as may have been created using Save Cube at an earlier occasion.')

        self.button_save_cube = tk.Button(self.tab2, text='Save Cube', command=self.save_cube, width=10, height=1, bg='#009999')
        self.button_save_cube.grid(row=3, column=1, sticky='w')
        Hovertip(self.button_save_cube, 'Save the cube contents of this character into a binary .cube file.')

        self.button_reset_skills = tk.Button(self.tab2, text='Unlearn Skills', command=self.reset_skills, width=10, height=1, bg='#009999')
        self.button_reset_skills.grid(row=4, column=0)
        Hovertip(self.button_reset_skills, 'Return all hard skill points for redistribution.')

        self.button_reset_attributes = tk.Button(self.tab2, text='Untrain Attrib.', command=self.reset_attributes, width=10, height=1, bg='#009999')
        self.button_reset_attributes.grid(row=4, column=1, sticky='w')
        Hovertip(self.button_reset_attributes, 'Return all hard attribute points for redistribution.')

        self.button_revive_hero =  tk.Button(self.tab2, text='Revive Hero', width=15, command=self.revive_hero, bg='#009999')
        self.button_revive_hero.grid(row=3, column=1, sticky='e')
        Hovertip(self.button_revive_hero, 'Will return a dead hero to life.')

        self.button_revive_mercenary =  tk.Button(self.tab2, text='Revive Mercenary', width=15, command=self.revive_mercenary, bg='#009999')
        self.button_revive_mercenary.grid(row=4, column=1, sticky='e')
        Hovertip(self.button_revive_mercenary, 'Will return a dead mercenary to life.')

        self.button_jewelize =  tk.Button(self.tab2, text='Jewelize Magic', width=15, command=self.jewelize, bg='#009999')
        self.button_jewelize.grid(row=3, column=2, sticky='we')
        Hovertip(self.button_jewelize, 'Items inside the Horadric Cube with intrinsic magic properties (magic, rare, runewords(!) or crafted) will be turned into jewels.')

        self.button_forge_ring =  tk.Button(self.tab2, text='Forge Magic Ring', width=15, command=lambda: self.jewelize(E_ItemTpl.IT_RING), bg='#009999')
        self.button_forge_ring.grid(row=4, column=2, sticky='we')
        Hovertip(self.button_forge_ring, 'Items inside the Horadric Cube with intrinsic magic properties (magic, rare, runewords(!) or crafted) will be turned into magic rings.')

        self.button_forge_charm =  tk.Button(self.tab2, text='Forge Charm', command=lambda: self.jewelize(E_ItemTpl.IT_CHARM), bg='#009999')
        self.button_forge_charm.grid(row=3, column=3, sticky='ew')
        Hovertip(self.button_forge_charm, 'Items inside the Horadric Cube with intrinsic magic properties (magic, rare, runewords(!) or crafted) will be turned into small charms.')

        self.button_forge_amulet =  tk.Button(self.tab2, text='Forge Amulet', command=lambda: self.jewelize(E_ItemTpl.IT_AMULET), bg='#009999')
        self.button_forge_amulet.grid(row=4, column=3, sticky='ew')
        Hovertip(self.button_forge_amulet, 'Items inside the Horadric Cube with intrinsic magic properties (magic, rare, runewords(!) or crafted) will be turned into magic amulets.')

        self.button_ensure_cube = tk.Button(self.tab2, text='Ensure Cube', command=self.ensure_cube, width=10, height=1, bg='#009999')
        self.button_ensure_cube.grid(row=3, column=5, sticky='ew')
        Hovertip(self.button_ensure_cube, 'If your character has no Horadric Cube. Get one into your inventory. Supplanted items will be moved into the cube.')

        self.button_enable_nightmare = tk.Button(self.tab2, text='Enable Nightmare', command=self.enable_nightmare, width=15, height=1, bg='#009999')
        self.button_enable_nightmare.grid(row=3, column=4, sticky='ew')
        Hovertip(self.button_enable_nightmare, 'If still in normal mode. Enable Nightmare, and raise your character\'s level to 38 (if necessary) and fill his stash with gold.')

        self.button_enable_hell = tk.Button(self.tab2, text='Enable Hell', command=self.enable_hell, width=10, height=1, bg='#009999')
        self.button_enable_hell.grid(row=4, column=4, sticky='ew')
        Hovertip(self.button_enable_hell, 'If still in normal or nightmare mode. Enable Hell, and raise your character\'s level to 68 (if necessary) and fill his stash with gold.')

        self.button_enable_nirvana = tk.Button(self.tab2, text='Enable Nirvana', command=self.enable_nirvana, width=15, height=1, bg='#009999')
        self.button_enable_nirvana.grid(row=4, column=5, sticky='ew')
        Hovertip(self.button_enable_nirvana, 'Beat Hell, transcend the World (enabling all waypoints, resetting most quests), raise your character\'s level to 86 (if necessary), and fill his stash with gold.')

        var_runic_cube = tk.StringVar()
        var_runic_cube.set("ort, sol, t4, t4, b4, t0, a0")
        self.entry_runic_cube = tk.Entry(self.tab2, textvariable=var_runic_cube)
        self.entry_runic_cube.grid(row=5, column=1, columnspan=2, sticky='ew')
        self.button_runic_cube = tk.Button(self.tab2, text='Runes to Cube', command=lambda: self.runic_cube(var_runic_cube.get()), width=10, height=1, bg='#009999')
        self.button_runic_cube.grid(row=5, column=0)
        Hovertip(self.button_runic_cube, 'Write a comma-separated list of rune names and/or gem codes, /^[tasredb][0-4]$/ (bone=skull), and click this. Will add these socketables to the Cube and its environment.')

        self.button_revive_cows = tk.Button(self.tab2, text='Revive Cow King', command=lambda: self.revive_cows(), width=10, height=1, bg='#009999')
        self.button_revive_cows.grid(row=5, column=3, sticky='ew')
        Hovertip(self.button_revive_cows, 'Will revive the Cow King in all difficulty levels where he died dismally for his people.')

        var_personalize = tk.StringVar()
        var_personalize.set("")
        self.entry_personalize = tk.Entry(self.tab2, textvariable=var_personalize)
        self.entry_personalize.grid(row=5, column=5, sticky='ew')
        self.entry_personalize.bind('<KeyRelease>', lambda ev: self.verify_personalization_name(var_personalize.get()))
        self.button_personalize = tk.Button(self.tab2, text='Personalize Cube:', command=lambda: self.personalize(var_personalize.get()), width=10, height=1, bg='#009999')
        self.button_personalize.grid(row=5, column=4, sticky='ew')
        Hovertip(self.button_personalize, 'Will dedicate extended items within the Horadric Cube with a name of your choosing. Or remove such a dedication.')

        var_skills = tk.StringVar()
        var_skills.set('0')
        self.entry_boost_skills = tk.Entry(self.tab2, textvariable=var_skills)
        self.entry_boost_skills.grid(row=6, column=1, columnspan=2, sticky='ew')
        self.button_boost_skills = tk.Button(self.tab2, text='Boost Skills', command=self.boost_skills, width=10, height=1, bg='#009999')
        self.button_boost_skills.grid(row=6, column=0)
        Hovertip(self.button_boost_skills, 'Set free skill points to this value.')

        var_attributes = tk.StringVar()
        var_attributes.set('0')
        self.entry_boost_attributes = tk.Entry(self.tab2, textvariable=var_attributes)
        self.entry_boost_attributes.grid(row=7, column=1, columnspan=2, sticky='ew')
        self.button_boost_attributes = tk.Button(self.tab2, text='Boost Attrib.', command=self.boost_attributes, width=10, height=1, bg='#009999')
        self.button_boost_attributes.grid(row=7, column=0)
        Hovertip(self.button_boost_attributes, 'Set free attribute points to this value.')

        self.button_toggle_ethereal = tk.Button(self.tab2, text='Toggle Ethereal', command=self.toggle_ethereal, bg='#009999')
        self.button_toggle_ethereal.grid(row=6, column=3, sticky='ew')
        Hovertip(self.button_toggle_ethereal, 'Toggles the ethereal state of items within the Horadric Cube.')

        self.button_regrade_items = tk.Button(self.tab2, text='Regrade Items', command=self.regrade_items, bg='#009999')
        self.button_regrade_items.grid(row=6, column=4, sticky='ew')
        Hovertip(self.button_regrade_items, 'Regrades items in the Horadric Cube cyclically. Normal->Elite->..->Normal.')

        self.button_dispel_magic = tk.Button(self.tab2, text='Dispel Magic', command=self.dispel_magic, bg='#009999')
        self.button_dispel_magic.grid(row=6, column=5, sticky='ew')
        Hovertip(self.button_dispel_magic, 'Dispels magic, rare, set and unique items, turning them into normal objects.')

        var_n_sockets = tk.StringVar()
        var_n_sockets.set('6')
        self.entry_set_sockets = tk.Entry(self.tab2, textvariable=var_n_sockets)
        self.entry_set_sockets.grid(row=7, column=4, sticky='ew')
        self.button_set_sockets = tk.Button(self.tab2, text='Set Sockets', command=self.set_sockets, bg='#009999')
        self.button_set_sockets.grid(row=7, column=3, sticky='ew')
        Hovertip(self.button_set_sockets, 'Within the items of the Horadric Cube, attempt to set this number of sockets ({0,..,6}).')
        self.button_empty_sockets = tk.Button(self.tab2, text='Empty Sockets', command=self.empty_sockets, bg='#009999')
        self.button_empty_sockets.grid(row=7, column=5, sticky='ew')
        Hovertip(self.button_empty_sockets, 'Remove all socketed items from the items in the Horadric Cube and return them to inventory.')

        var_hardcore = tk.IntVar()
        self.check_hardcore = tk.Checkbutton(self.tab2, text='Hardcore', variable=var_hardcore, command=lambda: self.set_hardcore(bool(var_hardcore.get())))
        self.check_hardcore.grid(row=8, column=0)
        Hovertip(self.check_hardcore, 'Enable or disable hardcore mode.')

        var_godmode = tk.IntVar()
        self.check_godmode = tk.Checkbutton(self.tab2, text='Godmode', variable=var_godmode, command=lambda: self.set_godmode(bool(var_godmode.get())))
        self.check_godmode.grid(row=8, column=1, sticky='w')
        Hovertip(self.check_godmode, 'Enable or disable god mode. Will give you powerful skills all around and high attributes. Gains made under god mode will be preserved when disabling it.')

        var_wp_hop = tk.IntVar()
        self.check_wp_hop = tk.Checkbutton(self.tab2, text="Waypoint 'Halls of Pain'", variable=var_wp_hop, command=lambda: self.set_wp_hop(bool(var_wp_hop.get())))
        self.check_wp_hop.grid(row=8, column=4, sticky='w')
        Hovertip(self.check_wp_hop, "Active if Anya is in town. Will (for highest accessible difficulty) enable or disable the 'Halls of Pain' waypoint -- and in reciprocal effect, Anya's portal to Nihlathak's Temple.")

        self.button_redeem_golem = tk.Button(self.tab2, text='Redeem Golem', command=self.redeem_golem, width=15, height=1, bg='#009999')
        self.button_redeem_golem.grid(row=8, column=5, sticky='ew') # row=3, col=4
        Hovertip(self.button_redeem_golem, 'If your character commands an iron golem, dispel that golem and, if there is space, return the item to inventory.')

        self.button_horazon = tk.Button(self.tab2, image=self.icon_potion_of_life, command=self.do_commit_horazon, bg='#009999')
        self.button_horazon.grid(row=9, column=0, columnspan=6, sticky='ew')
        Hovertip(self.button_horazon, 'All changes made above are hypothetical. Unless you click this here button that will commit them!')
        self.validate_pname_work()

        self.update_hero_widgets(False)
        # < ----------------------------------------------------------


if __name__ == '__main__':
    Horadric_GUI()
    print("Done.")
