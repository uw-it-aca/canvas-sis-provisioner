# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import re


RE_WORD_BOUNDS = re.compile(r'(\s|-|\(|\)|\.|,|/|:|&|")')
RE_TITLE_ABBR = re.compile(
    r'^(?:'
    r'3d|3d4m|Acms|Aids|Anmc|Apc|Apca|Asp|Basw|'
    r'Cad|Cam|Cep|Cisb|Cma|Cophp|Cse|Csr|Css|Css3|Csss|Ct|'
    r'Dna|Dsm|Dub|Edp|Ehr|Fda|Gh|Ghc|Gis|Gix|'
    r'Hcde|Hci|Hi|Hihim|Hiv|Hmc|Hr|Html5|'
    r'Ias|Ibep|Icd|Ielts|Id|Ii|Iii|Ios|Ip|It|Iv|Ix|Jsis|'
    r'Lgbt|Lgbtq|Llm|Mpa|Mph|Msis|Msw|Mt|Napm|Otc|'
    r'Rcs|Rf|Rotc|Scca|Sql|Sti|Ta|Toefl|Tv|'
    r'Uh|Us|Uw|Uwb|Uwcr|Uweo|Uwmc|Uwt|'
    r'Va|Vamc|Vba|Vi|Vii|Viii|Wa|Wsma|Wwami|Wy|Xml'
    r')$')


def titleize(s):
    """
    Capitalizes the first letter of every word, effective only in
    ASCII region.
    """
    if s is None:
        raise TypeError('String is required')

    new_s = ''
    for word in re.split(RE_WORD_BOUNDS, str(s)):
        new_s += re.sub(
            RE_TITLE_ABBR, lambda m: m.group(0).upper(), word.capitalize())
    return new_s
