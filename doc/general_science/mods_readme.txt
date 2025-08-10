# TSV style file describing little endian binary extended item mod sequences
# that I understood by reading, and careful deduction.
# This list is woefully incomplete. But it does give a good overview of the
# Most common magical properties. Given these and online-available files
# like, e.g., https://github.com/WalterCouto/D2CE/blob/main/source/res/TXT/global/excel/skills.txt
# It can be easily extended to accomodate specialized wishes.
#
# Markus-Hermann Koch, https://github.com/kochsoft/diablo2/, August 9th, 2025.
#
# About codes.
# ============
# As always, all is in little endian.
#
# integer:
# --------
# number_of_bits i [(offset=0)]: Signifies an integer, potentially with an offset.
#   E.g., 11i10 stands for an 11-bit integer that holds an in-game value +10.
#   Like an armor class. An in-game armor-value of 20 would be written as 30
#   in 11 bit: (01111000000)
#
# float:
# -----
# number_of_bits f [(number_of_sub_1_digits)]: Signifies a binary floating point.
#   E.g., 21f8 stands for a 21 bit float with 8 sub-1 digits. So the smallest
#     possible value is 2^{-8}, the largest possible value is 2^13-2^{-8}.
#     Say, our character has 15.25 HP (can happen, e.g., for an Assassin).
#     That value would be: 00000010 1111000000000 (the space denotes the decimal point).