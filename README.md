# About horadric_exchange.py

This is a home-brew Python 3-script for modifying Diablo v1.10-v1.14d legacy savegame files.
It is based on the information provided by Walter Couto on his excellent .d2s save-game
format analysis:

https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md

Its leading purpose is to create the ability for single player characters
to exchange items by echanging the contents of their Horadric Cubes.

As it went along the script added some cheating capabilities as well.

The script runs on vanilla python 3.13, possibly older, and has no special requirements.

However:

**MODIFYING DIABLO II .d2s FILES IS DANGEROUS TO THOSE FILES!**

The default settings of the script will create backups of the modified savegame .d2s files.

Still:

**BE SURE TO BACKUP YOUR .d2s CHARACTER FILES PRIOR TO TAMPERING.**

# About a Use Case and More

Consider the Barbarian finding the **sacred globe of divine world domination**,
that the sorceress has been looking for all these years. That brute does not
even know how to equip it to bash a zombie's head in. And there is just no way
to give it to the Sorceress.

Sad. Really sad.

No more! Using the horadric python script, the Barbarian may just put the sacred
globe into his Horadric Cube! If she is of the courteous type, the Sorceress may
put some glass perls into her own Horadric Cube as well.

Then exit the game. I trust you know how to employ the script's `--exchange_horadric`
function? It will cause the contents of both characters' Horadric Cubes to
change places by acting on their `.d2s` character files.

For this, vanilla Python 3 is needed. Required level is not quite known.
Python >=3.13 should do nicely though.

You may be pleased to read that this script has more capabilities. I have to
leave it to you, to employ the scripts `--help` function to find out more.

# Help Text (February 3rd 2025)

```
$ python horadric_exchange.py --help
usage: Horadric Exchange [-h] [--omit_backup] [--pfname_backup PFNAME_BACKUP] [--exchange_horadric] [--drop_horadric] [--save_horadric SAVE_HORADRIC] [--load_horadric LOAD_HORADRIC]
                         [--hardcore] [--softcore] [--boost_attributes BOOST_ATTRIBUTES] [--boost_skills BOOST_SKILLS] [--reset_skills] [--info]
                         pfnames [pfnames ...]

Tool script for doing small scale changes to Diablo II .d2s save game files.

Motivating example is the --exchange function. Have two characters stuff items into their Horadric cubes.
Apply this script to both their .d2s files, using the --exchange flag. Then this script will attempt to alter
both files thus, that the Horadric Cube contents of both players switch places.

positional arguments:
  pfnames               List of path and filenames to target .d2s character files.

options:
  -h, --help            show this help message and exit
  --omit_backup         Per default, target files will be backupped to .backup files. For safety. This option will disable that safety.
  --pfname_backup PFNAME_BACKUP
                        State a pfname to the backup file. Per default a timestamped name will be used. If there are multiple files to backup, the given name will be prefixed with each character's name.
  --exchange_horadric   Flag. Requires that there are precisely 2 character pfnames given. This will exchange their Horadric Cube contents.
  --drop_horadric       Flag. If given, the Horardric Cube contents of the targetted character will be removed.
  --save_horadric SAVE_HORADRIC
                        Write the items found in the Horadric Cube to disk with the given pfname. Only one character allowed.
  --load_horadric LOAD_HORADRIC
                        Drop all contents from the Horadric Cube and replace them with the horadric file content, that had been written using --save_horadric earlier.
  --hardcore            Flag. Set target characters to hard core mode.
  --softcore            Flag. Set target characters to soft core mode.
  --boost_attributes BOOST_ATTRIBUTES
                        Set this number to the given value.
  --boost_skills BOOST_SKILLS
                        Set this number to the given value.
  --reset_skills        Flag. Unlearns all skills, returning them as free skill points.
  --info                Flag. Show some statistics to each input file.

Example call:
$ python3 horadric_exchange.py conan.d2s ormaline.d2s
```

