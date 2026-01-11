"""Time of day"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class TimeOfDay:
    """Time of day representation"""
    date: str
    season: int
    time_number: str
    time_str: str


def number_to_spanish(num: int, all_caps: bool = True) -> str:
    mapping = {
        0: "cero",
        1: "uno",
        2: "dos",
        3: "tres",
        4: "cuatro",
        5: "cinco",
        6: "seis",
        7: "siete",
        8: "ocho",
        9: "nueve",
        10: "diez",
        11: "once",
        12: "doce",
        13: "trece",
        14: "catorce",
        15: "quince",
        16: "dieciséis",
        17: "diecisiete",
        18: "dieciocho",
        19: "diecinueve",
        20: "veinte",
        21: "veintiuno",
        22: "veintidós",
        23: "veintitrés",
        24: "veinticuatro",
        25: "veinticinco",
        26: "veintiséis",
        27: "veintisiete",
        28: "veintiocho",
        29: "veintinueve",
        30: "treinta",
        31: "treinta y uno",
        32: "treinta y dos",
        33: "treinta y tres",
        34: "treinta y cuatro",
        35: "treinta y cinco",
        36: "treinta y seis",
        37: "treinta y siete",
        38: "treinta y ocho",
        39: "treinta y nueve",
        40: "cuarenta",
        41: "cuarenta y uno",
        42: "cuarenta y dos",
        43: "cuarenta y tres",
        44: "cuarenta y cuatro",
        45: "cuarenta y cinco",
        46: "cuarenta y seis",
        47: "cuarenta y siete",
        48: "cuarenta y ocho",
        49: "cuarenta y nueve",
        50: "cincuenta",
        51: "cincuenta y uno",
        52: "cincuenta y dos",
        53: "cincuenta y tres",
        54: "cincuenta y cuatro",
        55: "cincuenta y cinco",
        56: "cincuenta y seis",
        57: "cincuenta y siete",
        58: "cincuenta y ocho",
        59: "cincuenta y nueve",
    }
    num_str = mapping.get(num, str(num))
    return num_str.upper() if all_caps else num_str

def number_to_lithuanian(num: int, all_caps: bool = True) -> str:
    mapping = {
        0: "nulis",
        1: "vienas",
        2: "du",
        3: "trys",
        4: "keturi",
        5: "penki",
        6: "šeši",
        7: "septyni",
        8: "aštuoni",
        9: "devyni",
        10: "dešimt",
        11: "vienuolika",
        12: "dvylika",
        13: "trylika",
        14: "keturiolika",
        15: "penkiolika",
        16: "šešiolika",
        17: "septyniolika",
        18: "aštuoniolika",
        19: "devyniolika",
        20: "dvidešimt",
        21: "dvidešimt vienas",
        22: "dvidešimt du",
        23: "dvidešimt trys",
        24: "dvidešimt keturi",
        25: "dvidešimt penki",
        26: "dvidešimt šeši",
        27: "dvidešimt septyni",
        28: "dvidešimt aštuoni",
        29: "dvidešimt devyni",
        30: "trisdešimt",
        31: "trisdešimt vienas",
        32: "trisdešimt du",
        33: "trisdešimt trys",
        34: "trisdešimt keturi",
        35: "trisdešimt penki",
        36: "trisdešimt šeši",
        37: "trisdešimt septyni",
        38: "trisdešimt aštuoni",
        39: "trisdešimt devyni",
        40: "keturiasdešimt",
        41: "keturiasdešimt vienas",
        42: "keturiasdešimt du",
        43: "keturiasdešimt trys",
        44: "keturiasdešimt keturi",
        45: "keturiasdešimt penki",
        46: "keturiasdešimt šeši",
        47: "keturiasdešimt septyni",
        48: "keturiasdešimt aštuoni",
        49: "keturiasdešimt devyni",
        50: "penkiasdešimt",
        51: "penkiasdešimt vienas",
        52: "penkiasdešimt du",
        53: "penkiasdešimt trys",
        54: "penkiasdešimt keturi",
        55: "penkiasdešimt penki",
        56: "penkiasdešimt šeši",
        57: "penkiasdešimt septyni",
        58: "penkiasdešimt aštuoni",
        59: "penkiasdešimt devyni",
    }
    num_str = mapping.get(num, str(num))
    return num_str.upper() if all_caps else num_str


def number_to_english(num: int, all_caps: bool = True) -> str:
    mapping = {
        0: "zero",
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
        11: "eleven",
        12: "twelve",
        13: "thirteen",
        14: "fourteen",
        15: "fifteen",
        16: "sixteen",
        17: "seventeen",
        18: "eighteen",
        19: "nineteen",
        20: "twenty",
        30: "thirty",
        40: "forty",
        50: "fifty",
    }
    if num in mapping:
        num_str = mapping[num]
    else:
        tens = (num // 10) * 10
        units = num % 10
        num_str = f"{mapping[tens]}-{mapping[units]}"

    return num_str.upper() if all_caps else num_str


def number_to_german(num: int, all_caps: bool = True) -> str:
    mapping = {
        0: "null",
        1: "eins",
        2: "zwei",
        3: "drei",
        4: "vier",
        5: "fünf",
        6: "sechs",
        7: "sieben",
        8: "acht",
        9: "neun",
        10: "zehn",
        11: "elf",
        12: "zwölf",
        13: "dreizehn",
        14: "vierzehn",
        15: "fünfzehn",
        16: "sechzehn",
        17: "siebzehn",
        18: "achtzehn",
        19: "neunzehn",
        20: "zwanzig",
        30: "dreissig",
        40: "vierzig",
        50: "fünfzig",
    }
    if num in mapping:
        num_str = mapping[num]
    else:
        tens = (num // 10) * 10
        units = num % 10
        unit_str = mapping[units]
        if units == 1:
            unit_str = "EIN"
        num_str = f"{unit_str}UND{mapping[tens]}"

    return num_str.upper() if all_caps else num_str


def get_datetime(all_caps: bool = True, language: Literal["ES", "LT", "EN", "DE"] = "ES") -> TimeOfDay:
    dt = datetime.now()
    time_number = f"{dt.hour:02}:{dt.minute:02}"

    m = dt.month
    if 3 <= m <= 5:
        season = 1
    elif 6 <= m <= 8:
        season = 2
    elif 9 <= m <= 11:
        season = 3
    else:
        season = 4

    if language == "LT":
        days_lithuanian = [
            "pirmadienis", "antradienis", "trečiadienis", "ketvirtadienis",
            "penktadienis", "šeštadienis", "sekmadienis"
        ]
        months_lithuanian = [
            "sausio", "vasario", "kovo", "balandžio",
            "gegužės", "birželio", "liepos", "rugpjūčio",
            "rugsėjo", "spalio", "lapkričio", "gruodžio"
        ]
        seasons_lithuanian = {1: "pavasaris", 2: "vasara", 3: "ruduo", 4: "žiema"}

        day_name = days_lithuanian[dt.weekday()]
        hour_str = number_to_lithuanian(dt.hour, all_caps)
        minute_str = number_to_lithuanian(dt.minute, all_caps)
        day = dt.day
        day_str = number_to_lithuanian(day, all_caps)
        month = months_lithuanian[dt.month - 1]

        date = f"{day_name.title()} {month} {day} d. {seasons_lithuanian[season]}."
        dtime = f"yra {hour_str} ir {minute_str}"
        if dt.minute == 0:
            dtime = f"yra {hour_str}."

    elif language == "EN":
        days_english = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        months_english = [
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"
        ]
        seasons_english = {1: "spring", 2: "summer", 3: "autumn", 4: "winter"}

        day_name = days_english[dt.weekday()]
        hour_str = number_to_english(dt.hour, all_caps)
        minute_str = number_to_english(dt.minute, all_caps)
        day = dt.day
        day_str = number_to_english(day, all_caps)
        month = months_english[dt.month - 1]

        date = f"{day_name}, {month} {day} ({day_str}). It is {seasons_english[season]}."
        dtime = f"It is {hour_str} {minute_str}"
        if dt.minute == 0:
            dtime = f"It is {hour_str} o'clock."

    elif language == "DE":
        days_german = [
            "Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag"
        ]
        months_german = [
            "Januar", "Februar", "März", "April",
            "Mai", "Juni", "Juli", "August",
            "September", "Oktober", "November", "Dezember"
        ]
        seasons_german = {1: "Frühling", 2: "Sommer", 3: "Herbst", 4: "Winter"}


        day_name = days_german[dt.weekday()]
        hour_str = number_to_german(dt.hour, all_caps)
        minute_str = number_to_german(dt.minute, all_caps)
        day = dt.day
        day_str = number_to_german(day, all_caps)
        month = months_german[dt.month - 1]

        date = f"{day_name}, {day} ({day_str}) {month}. Es ist {seasons_german[season]}."
        dtime = f"Es ist {hour_str} Uhr"
        if dt.minute != 0:
            dtime += f" {minute_str}"

    else:  # Default to ES
        days_spanish = [
            "lunes", "martes", "miércoles", "jueves",
            "viernes", "sábado", "domingo"
        ]

        months_spanish = [
            "enero", "febrero", "marzo", "abril",
            "mayo", "junio", "julio", "agosto",
            "septiembre", "octubre", "noviembre", "diciembre"
        ]

        day_name = days_spanish[dt.weekday()]
        hour_str = number_to_spanish(dt.hour, all_caps)
        minute_str = number_to_spanish(dt.minute, all_caps)
        day = dt.day
        day_str = number_to_spanish(day, all_caps)
        month = months_spanish[dt.month - 1]

        seasons = {1: "primavera", 2: "verano", 3: "otoño", 4: "invierno"}

        date = f"{day_name.title()} {day} ({day_str}) de {month}. Es {seasons[season]}."
        prefix = "Son las" if dt.hour != 1 else "Es la"
        dtime = f"{prefix} {hour_str} y {minute_str}"
        if dt.minute == 0:
            dtime = f"{prefix} {hour_str} en punto"

    return TimeOfDay(
        date=date.upper() if all_caps else date,
        season=season,
        time_number=time_number,
        time_str=dtime.upper() if all_caps else dtime
    )