from django.utils.timezone import (
    get_default_timezone, localtime, is_naive, make_aware)
import re


RE_WORD_BOUNDS = re.compile('(\s|-|\(|\)|\.|,|\/|:|&)')
RE_TITLE_ABBR = re.compile(
    r'\b('
    r'3d|3d4m|Aids|Asp|Basw|Cep|Cisb|Cophp|Csr|Css|Css3|'
    r'Dub|Edp|Ehr|Gis|Hcde|Hci|Hi|Hiv|Hr|Html5|'
    r'Ias|Ibep|Ielts|Ii|Iii|Ios|It|Iv|Jsis|'
    r'Mpa|Mph|Msw|Otc|Rotc|Sql|Toefl|'
    r'Us|Uw|Uwb|Uweo|Uwmc|Uwt|Vba|Wsma|Wwami|Xml'
    r')\b')


def titleize(s):
    """
    Capitalizes the first letter of every word, effective only in
    ASCII region.
    """
    if not isinstance(s, str):
        raise TypeError('String is required')

    new_s = ''
    for word in re.split(RE_WORD_BOUNDS, s):
        new_s += word.capitalize()

    new_s = re.sub(RE_TITLE_ABBR, lambda m: m.group(0).upper(), new_s)
    return new_s


def localize(dt):
    if is_naive(dt):
        return make_aware(dt, get_default_timezone())
    else:
        return localtime(dt)
