"""Exact legal-history repetition query; no null moves are supported."""
import ast

HELPER='''
@njit(cache=False, inline='always')
def threefold(hashes, hlen, halfmove):
    # A legal position cannot return after only two plies.
    if hlen < 9 or halfmove < 8:
        return False
    key = hashes[hlen - 1]
    repetitions = 1
    for i in range(hlen - 5, max(-1, hlen - halfmove - 2), -2):
        if hashes[i] == key:
            repetitions += 1
            if repetitions >= 3:
                return True
    return False
'''

def transform(source):
    old='''    repetitions = 0
    for i in range(max(0, hlen - state[3] - 1), hlen):
        repetitions += int(hashes[i] == key)
    if state[3] >= 100 or repetitions >= 3 or insufficient(board):'''
    new='''    if state[3] >= 100 or threefold(hashes, hlen, state[3]) or insufficient(board):'''
    assert source.count(old)==1
    source=source.replace(old,new)
    marker="@njit(cache=False)\ndef insufficient(board):"
    assert source.count(marker)==1
    source=source.replace(marker,HELPER+'\n'+marker)
    ast.parse(source)
    return source
