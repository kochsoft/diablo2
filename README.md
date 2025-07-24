# About this README.md

Any good git repository should have a README.md!

And so does this one. However, there also is a **full-blown wiki page**:

https://github.com/kochsoft/diablo2/wiki

# About horadric_exchange.py

This is a home-brew Python 3-script for modifying Diablo v1.10-v1.14d legacy save-game files.
It is based on the information provided by Walter Couto on his excellent .d2s save-game
format analysis:

https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md

Its leading purpose is to create the ability for single player characters
to exchange items by exchanging the contents of their Horadric Cubes.

As it went along the script added some cheating capabilities as well.

The script runs on vanilla python 3.13, possibly older, and has no special requirements.

However:

**MODIFYING DIABLO II .d2s FILES IS DANGEROUS TO THOSE FILES!**

The default settings of the script will create backups of the modified save-game .d2s files.

Still:

**BE SURE TO BACK UP YOUR .d2s CHARACTER FILES PRIOR TO TAMPERING.**

# GUI

There is a GUI to the entire tool: **horadric_exchange.py** consider
it the main script. It is documented in detail within the wiki
that is attached to this repository.

# Help Text (March 15th 2025)

```
$ ./horazons_folly.py --help
 
usage: horazons_folly.py [-h] [--omit_backup] [--pfname_backup PFNAME_BACKUP]
                         [--exchange_horadric]
                         [--create_rune_cube [CREATE_RUNE_CUBE]]
                         [--drop_horadric] [--save_horadric SAVE_HORADRIC]
                         [--load_horadric LOAD_HORADRIC]
                         [--empty_sockets_horadric]
                         [--set_sockets_horadric SET_SOCKETS_HORADRIC]
                         [--dispel_magic] [--toggle_ethereal]
                         [--jewelize [JEWELIZE]] [--regrade_horadric]
                         [--ensure_horadric] [--hardcore] [--softcore]
                         [--revive_self] [--revive_merc] [--redeem_golem]
                         [--boost_attributes BOOST_ATTRIBUTES]
                         [--boost_skills BOOST_SKILLS] [--reset_attributes]
                         [--reset_skills] [--enable_nightmare] [--enable_hell]
                         [--enable_nirvana] [--enable_godmode]
                         [--disable_godmode] [--info] [--info_stats]
                         [--set_waypoints SET_WAYPOINTS]
                         [pfnames ...]

Tool script for doing small scale changes to Diablo II .d2s save game files.

Motivating example is the --exchange function. Have two characters stuff items into their Horadric cubes.
Apply this script to both their .d2s files, using the --exchange flag. Then this script will attempt to alter
both files thus, that the Horadric Cube contents of both players switch places.

positional arguments:
  pfnames               List of path and filenames to target .d2s character files.

options:
  -h, --help            show this help message and exit
  --omit_backup         Per default, target files will be back-upped to .backup files. For safety. This option will disable that safety.
  --pfname_backup PFNAME_BACKUP
                        State a pfname to the backup file. Per default a timestamped name will be used. If there are multiple files to backup, the given name will be prefixed with each character's name.
  --exchange_horadric   Flag. Requires that there are precisely 2 character pfnames given. This will exchange their Horadric Cube contents.
  --create_rune_cube [CREATE_RUNE_CUBE]
                        pfname, ':', then a comma separated list of up to 12 rune names and/or gem codes, /[tasredb][0-4]/. Creates a cube content with these runes and socketables.
  --drop_horadric       Flag. If given, the Horadric Cube contents of the targeted character will be removed.
  --save_horadric SAVE_HORADRIC
                        Write the items found in the Horadric Cube to disk with the given pfname. Only one character allowed.
  --load_horadric LOAD_HORADRIC
                        Drop all contents from the Horadric Cube and replace them with the horadric file content, that had been written using --save_horadric earlier.
  --empty_sockets_horadric
                        Flag. Pull all socketed items from items in the horadric cube. Try to preserve these socketables.
  --set_sockets_horadric SET_SOCKETS_HORADRIC
                        Attempt to set this many sockets to the socket-able items in the horadric cube.
  --dispel_magic        Flag. Acts on magical, rare, and crafted items within the Horadric Cube, dispelling their magic.
  --toggle_ethereal     Flag. For each item within the Horadric Cube toggle the ethereal state.
  --jewelize [JEWELIZE]
                        Will attempt to turn magic items within the Horadric Cube into jewels (if 'jew' is passed, or small charms, rings or amulets, if 'cm1', 'rin' or 'amu' is passed).
  --regrade_horadric    Flag. For each item within the Horadric Cube upgrade it (usually normal, exceptional, elite). After max grade returns to normal.
  --ensure_horadric     Flag. If the player has no Horadric Cube, one will be created in the inventory. Any item in that location will be put into the cube instead.
  --hardcore            Flag. Set target characters to hard core mode.
  --softcore            Flag. Set target characters to soft core mode.
  --revive_self         Flag. If your character is dead, this will revive him. Even if he is a hardcore character. He still may have to pick up his corpse though.
  --revive_merc         Flag. If your mercenary is dead, this will revive him.
  --redeem_golem        Flag. If there is an iron golem, dispel it and return its items into the player's inventory.
  --boost_attributes BOOST_ATTRIBUTES
                        Set this number to the given value.
  --boost_skills BOOST_SKILLS
                        Set this number to the given value.
  --reset_attributes    Flag. Returns all spent attribute points for redistribution.
  --reset_skills        Flag. Unlearns all skills, returning them as free skill points.
  --enable_nightmare    Flag. Enables entering nightmare. Fully upgrades character to level 38 and gives gold to match.
  --enable_hell         Flag. Enables entering hell and nightmare. Fully upgrades character to level 68 and gives gold to match.
  --enable_nirvana      Flag. Empowers the character to level 86 and sets him up as victor of hell. Also gives gold to match.
  --enable_godmode      Enables Demigod-mode (so far without high Mana/HP/Stamina). Creates a .humanity stat file alongside the .d2s for later return to normal mode.
  --disable_godmode     Returns to human form (retaining skill points earned in god mode). After all, who wants the stress of being super all the time?
  --info                Flag. Show some statistics to each input file.
  --info_stats          Flag. Nerd-minded. Detailed info tool on the parsing of attributes and skills.
  --set_waypoints SET_WAYPOINTS
                        Set waypoints as optional prefix /INDEX_DIFFICULTY-/ and bitmap /.{39}/ where 0/1 means off/on and everything else is ignored.

Example call:
$ python3 horazons_folly.py --info conan.d2s ormaline.d2s
```
