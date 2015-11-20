import math


def entropy(hexstring, bits=128, raw=False):
    """
    Calculate the Shannon entropy from a hexstring. If raw is True, it's
    assumed that hexstring is composed of zeros and ones.
    """
    if not raw:
        onezero = bin(int(hexstring, 16))[2:]
    else:
        onezero = hexstring
    onezero = onezero.zfill(bits)
    assert len(onezero) == bits

    length = float(bits)
    prob = [onezero.count('0') / length, onezero.count('1') / length]
    entropy = -sum([p * math.log(p, 2) for p in prob])
    return entropy


if __name__ == "__main__":
    t1 = '58e1ac7b7faf79e6ee24230f40b4a9ae'
    ent1 = entropy(t1)
    print(repr(ent1))
    assert ent1 == 0.9955927544527946

    t2 = ('1011000111000011010110001111011011111111010111101111001111'
          '0011011101110001001000010001100001111010000001011010010101'
          '00110101110')
    assert bin(int(t1, 16))[2:] == t2
    assert entropy(t2, raw=True) == ent1
