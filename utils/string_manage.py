import difflib
import math
from fuzzywuzzy import fuzz

diff = difflib.Differ()


def similarity_word(dst_str, src_str):
    ratio = float(fuzz.token_set_ratio(dst_str, src_str)) / 100.0
    avg_len = (len(dst_str) + len(src_str)) / 2
    sub_len = math.fabs(len(dst_str) - len(src_str)) / 2
    return ratio * (avg_len - sub_len) / avg_len


def equal(str1, str2):
    str1 = str1.upper().replace(" ", "")
    str2 = str2.upper().replace(" ", "")
    return similarity_word(str1, str2) > 0.9


def find_keyword(line_text, keyword):
    if len(line_text) <= len(keyword):
        ratio = float(fuzz.token_set_ratio(line_text, keyword)) / 100.0
        max_ratio = ratio * len(line_text) / len(keyword)
        last_same_pos = 0
    else:
        max_ratio = 0
        last_same_pos = 0
        for pos in range(len(line_text) - len(keyword)):
            sub_text = line_text[pos: pos + len(keyword)]
            ratio = float(fuzz.token_set_ratio(sub_text, keyword)) / 100.0
            if max_ratio < ratio:
                max_ratio = ratio
                last_same_pos = pos

    if max_ratio > 0.9:
        return last_same_pos
    else:
        return -1
