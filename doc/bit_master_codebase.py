

# Dieser Code wird den Byte-Block als Bit-Feld darstellen. Little endian.
# Bedeutet: Dass die hinteren Werte zuerst kommen.
#data = b'Wir sind die lustigen Holzhackersbuam!'
#data = b'\x00\x01\x03\x07\xff\x00'
#print ('{:0{width}b}'.format(int.from_bytes(data, 'little'), width = len(data) * 8))
# >> 000000001111111100000011000000100000000100000000

# Besser mit reversed entry. Gegeben, dass das signifikanteste Bit zuerst kommt, ist das genau das, was ich will!
#print ('{:0{width}b}'.format(int.from_bytes(data[::-1], 'little'), width = len(data) * 8))

#>>> int(255*256 + 1).to_bytes(3, byteorder='little')[::-1]
#b'\x00\xff\x01'

#>>> int('1111111100000000', 2).to_bytes(4, byteorder='little')[::-1]
#b'\x00\x00\xff\x00'


def bytes2bitmap(data: bytes) -> str:
    return '{:0{width}b}'.format(int.from_bytes(data, 'little'), width = len(data) * 8)

def bitmap2bytes(bitmap: str) -> bytes:
    n = len(bitmap)
    if (n % 8) != 0:
        raise ValueError(f"Invalid bitmap length {n} not being a multiple of 8.")
    return int(bitmap,2).to_bytes(round(n/8), 'little')

def get_range_from_bitmap(bitmap: str, index_start: int, index_end: int, *, do_invert: bool = False) -> int:
    return int(bitmap[index_start:index_end][::-1] if do_invert else bitmap[index_start:index_end], 2)

def set_range_to_bitmap(bitmap: str, index_start: int, index_end: int, val: int, *, do_invert: bool = False) -> str:
    width = index_end - index_start
    rg = '{:0{width}b}'.format(val, width=width)
    if do_invert:
        rg = rg[::-1]
    return bitmap[0:index_start] + rg + bitmap[index_end:]

def get_bitrange_value_from_bytes(data: bytes, index_start: int, index_end: int, *, do_invert: bool = False):
    bm = bytes2bitmap(data)
    return get_range_from_bitmap(bm, index_start, index_end, do_invert=do_invert)

def set_bitrange_value_to_bytes(data: bytes, index_start: int, index_end: int, val: int, *, do_invert: bool = False):
    bm = bytes2bitmap(data)
    set_range_to_bitmap(bm, index_start, index_end, val, do_invert=do_invert)
    return bitmap2bytes(bm)

# > Test 1. ----------------------------------------------------------
data0 = b'\x00\x01\x03\x07\xff\x00'
bm0 = bytes2bitmap(data0)
rg0 = get_range_from_bitmap(bm0, 15,17)
bm1 = set_range_to_bitmap(bm0, 15, 19, 3)
data1 = bitmap2bytes(bm1)

val0 = get_bitrange_value_from_bytes(data0, 15, 19)
val1 = 12
data2 = set_bitrange_value_to_bytes(data0, 15, 19, val1)
print(f"{val0} => {val1}")
print(data0)
print(data1)
# < ------------------------------------------------------------------

# > Test 2. ----------------------------------------------------------
data0 = b'\x00\x0f'  #<< Little Endian! This means '256*15 == 3840'
bm0 = bytes2bitmap(data0)  #<< 00001111 00000000
get_range_from_bitmap(bm0, 0, len(bm0))  #<< 3840
rg0 = get_range_from_bitmap(bm0, 5,12)  #<< 1110000 == 64+32+16 == 112
bm1 = set_range_to_bitmap(bm0, 5, 12, 13)  #<< 0001101 == 13 leading to 00001000 11010000 == 2256
data1 = bitmap2bytes(bm1) #<< \xd0\x08. Still little Endian! 0xd0 + 256 * 0x08 == 2256
# < ------------------------------------------------------------------

