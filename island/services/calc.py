"""Calculator, unit and currency conversion for the command bar.

    evaluate("12*7")            -> 84
    convert("5 km in mi")       -> (3.10686, "mi", "length")
    currency_query("20 usd in eur") -> (20.0, "USD", "EUR")

Expressions are parsed with ast and only numbers, + - * / // % ^ and a few
math functions are allowed: no eval(), no names, no attribute access.
Exchange rates come from the ECB via frankfurter (no API key), fetched through
curl only when a currency conversion is typed, cached for 12 hours.
"""

import ast
import math
import operator
import re
import time

from island.services import http
from island.storage import CACHE_DIR, load_json, save_json

MAX_INPUT = 200
MAX_EXPONENT = 1000
# ECB reference rates, published once a day around 16:00 CET
RATES_URLS = ("https://api.frankfurter.dev/v1/latest", "https://api.frankfurter.app/latest")  # base: EUR
RATES_PATH = CACHE_DIR / "rates.json"
RATES_MAX_AGE = 12 * 3600
RATES_RETRY = 5 * 60

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
           ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"sqrt": math.sqrt, "wurzel": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
          "asin": math.asin, "acos": math.acos, "atan": math.atan, "ln": math.log, "log": math.log10,
          "log2": math.log2, "exp": math.exp, "abs": abs, "round": round, "floor": math.floor,
          "ceil": math.ceil}
_CONSTS = {"pi": math.pi, "π": math.pi, "e": math.e, "tau": math.tau}
# A number directly followed by % (and no operand after it) is a percentage: 50*20% -> 50*(20/100)
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%(?!\s*[\d(.])")
_OPERATOR = re.compile(r"[-+*/^%()×÷]|\b(?:" + "|".join(_FUNCS) + r")\(")


class _Invalid(Exception):
    pass


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > MAX_EXPONENT or abs(left) > 1e100):
            raise _Invalid  # 9^9^9 would freeze the island
        return _BINARY[type(node.op)](left, right)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS
            and len(node.args) == 1 and not node.keywords):
        return _FUNCS[node.func.id](_eval(node.args[0]))
    raise _Invalid


def evaluate(text):
    """The value of a calculation, or None if the text isn't one (plain numbers aren't either)."""
    text = text.strip().rstrip("=").strip()
    if not text or len(text) > MAX_INPUT or not any(c.isdigit() for c in text) or not _OPERATOR.search(text):
        return None
    expr = text.lower().replace("×", "*").replace("÷", "/").replace("^", "**").replace(",", ".")
    expr = _PERCENT.sub(r"(\1/100)", expr)
    try:
        tree = ast.parse(expr, mode="eval")
        if isinstance(tree.body, (ast.Constant, ast.UnaryOp)) and isinstance(
                getattr(tree.body, "operand", tree.body), ast.Constant):
            return None  # "42", "-5": nothing to calculate
        value = _eval(tree)
    except (_Invalid, SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError, RecursionError):
        return None
    if not isinstance(value, (int, float)) or abs(value) > 1e300 or not math.isfinite(value):
        return None
    return value


def format_number(value, decimal_comma=False, digits=12):
    """84 -> '84', 0.1+0.2 -> '0.3', 1e21 -> '1e+21'; German decimal comma on request."""
    if isinstance(value, int) and abs(value) < 10 ** 15:
        text = str(value)
    else:
        text = f"{value:.{digits}g}"
        if "e" not in text and "." in text:
            text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",") if decimal_comma else text


# =============================================================================
# Units
# =============================================================================
# dimension -> {unit: factor to the base unit}; the first alias is the one shown
_UNITS = {
    "length": {  # metre
        ("mm", "millimeter", "millimetre"): 1e-3, ("cm", "zentimeter", "centimeter", "centimetre"): 1e-2,
        ("dm",): 0.1, ("m", "meter", "metre", "meters", "metres"): 1.0,
        ("km", "kilometer", "kilometre", "kilometers", "kilometres"): 1e3,
        ("in", "inch", "inches", "zoll", '"'): 0.0254, ("ft", "foot", "feet", "fuß", "fuss"): 0.3048,
        ("yd", "yard", "yards"): 0.9144, ("mi", "mile", "miles", "meile", "meilen"): 1609.344,
        ("nmi", "sm", "seemeile", "seemeilen"): 1852.0,
    },
    "mass": {  # kilogram
        ("mg", "milligramm", "milligram"): 1e-6, ("g", "gramm", "gram", "grams"): 1e-3,
        ("kg", "kilo", "kilogramm", "kilogram", "kilograms"): 1.0, ("t", "tonne", "tonnen", "tons"): 1e3,
        ("oz", "ounce", "ounces", "unze", "unzen"): 0.028349523125,
        ("lb", "lbs", "pound", "pounds"): 0.45359237, ("st", "stone"): 6.35029318,
    },
    "volume": {  # litre
        ("ml", "milliliter", "millilitre"): 1e-3, ("cl",): 1e-2, ("dl",): 0.1,
        ("l", "liter", "litre", "liters", "litres"): 1.0, ("m³", "m3", "kubikmeter"): 1e3,
        ("cup", "cups", "tasse", "tassen"): 0.2365882365, ("floz", "fl-oz"): 0.0295735295625,
        ("pt", "pint", "pints"): 0.473176473, ("qt", "quart"): 0.946352946,
        ("gal", "gallon", "gallons", "gallone", "gallonen"): 3.785411784,
    },
    "area": {  # square metre
        ("cm²", "cm2"): 1e-4, ("m²", "m2", "qm", "sqm"): 1.0, ("a", "ar"): 100.0,
        ("ha", "hektar", "hectare", "hectares"): 1e4, ("km²", "km2"): 1e6,
        ("ft²", "ft2", "sqft"): 0.09290304, ("ac", "acre", "acres"): 4046.8564224,
        ("mi²", "mi2", "sqmi"): 2589988.110336,
    },
    "time": {  # second
        ("ms",): 1e-3, ("s", "sec", "sek", "second", "seconds", "sekunde", "sekunden"): 1.0,
        ("min", "minute", "minutes", "minuten"): 60.0, ("h", "hr", "std", "hour", "hours", "stunde", "stunden"): 3600.0,
        ("d", "day", "days", "tag", "tage"): 86400.0, ("wk", "week", "weeks", "woche", "wochen"): 604800.0,
        ("y", "yr", "year", "years", "jahr", "jahre"): 31557600.0,
    },
    "data": {  # byte
        ("bit", "bits"): 0.125, ("B", "byte", "bytes"): 1.0,
        ("kB", "kb"): 1e3, ("MB",): 1e6, ("GB",): 1e9, ("TB",): 1e12,
        ("KiB",): 1024.0, ("MiB",): 1024.0 ** 2, ("GiB",): 1024.0 ** 3, ("TiB",): 1024.0 ** 4,
        ("kbit",): 125.0, ("Mbit",): 125e3, ("Gbit",): 125e6,
    },
    "speed": {  # metre per second
        ("m/s", "mps"): 1.0, ("km/h", "kmh", "kph"): 1 / 3.6, ("mph",): 0.44704,
        ("kn", "kt", "knot", "knots", "knoten"): 1852 / 3600,
    },
    "temperature": {("°C", "c", "celsius"): None, ("°F", "f", "fahrenheit"): None, ("K", "kelvin"): None},
}
UNITS = {}  # alias (lower case, as typed) -> (dimension, shown name, factor)
for _dim, _table in _UNITS.items():
    for _aliases, _factor in _table.items():
        for _alias in _aliases:
            UNITS[_alias.lower()] = (_dim, _aliases[0], _factor)

# ECB reference currencies; symbols and names map onto them
CURRENCIES = {"AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS",
              "INR", "ISK", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RON", "SEK", "SGD", "THB",
              "TRY", "USD", "ZAR"}
CURRENCY_NAMES = {"€": "EUR", "euro": "EUR", "euros": "EUR", "$": "USD", "dollar": "USD", "dollars": "USD",
                  "£": "GBP", "pfund": "GBP", "¥": "JPY", "yen": "JPY", "yuan": "CNY", "₹": "INR",
                  "franken": "CHF", "fr": "CHF", "zloty": "PLN", "zł": "PLN", "kronen": "SEK", "₺": "TRY",
                  "lira": "TRY", "real": "BRL", "rand": "ZAR", "won": "KRW", "₩": "KRW"}

_NUMBER = r"[-+]?\d+(?:[.,]\d+)?"
_INTO = r"\s+(?:in|into|to|nach|zu|=|->|→)\s+"
# "5 km in mi", "5km to mi", "$20 in eur", "20 € in $"
_CONVERSION = re.compile(rf"^\s*(?P<pre>[$€£¥₹₩₺])?\s*(?P<num>{_NUMBER})\s*(?P<src>[^\s\d][^\s]*)?{_INTO}"
                         r"(?P<dst>[^\s]+)\s*$", re.IGNORECASE)


def _number(text):
    return float(text.replace(",", "."))


def _split(text):
    """(amount, source unit, target unit) as typed, or None."""
    if len(text) > MAX_INPUT:
        return None
    m = _CONVERSION.match(text)
    if not m:
        return None
    src = m.group("pre") or m.group("src")
    if not src or (m.group("pre") and m.group("src")):
        return None
    return _number(m.group("num")), src.lower(), m.group("dst").lower()


def _to_celsius(value, unit):
    return {"°C": value, "°F": (value - 32) * 5 / 9, "K": value - 273.15}[unit]


def _from_celsius(value, unit):
    return {"°C": value, "°F": value * 9 / 5 + 32, "K": value + 273.15}[unit]


def convert(text):
    """'5 km in mi' -> (amount, source name, result, target name), or None."""
    parts = _split(text)
    if not parts:
        return None
    amount, src, dst = parts
    if src not in UNITS or dst not in UNITS:
        return None
    (dim, src_name, src_factor), (dim2, dst_name, dst_factor) = UNITS[src], UNITS[dst]
    if dim != dim2:
        return None
    if dim == "temperature":
        result = _from_celsius(_to_celsius(amount, src_name), dst_name)
    else:
        result = amount * src_factor / dst_factor
    return amount, src_name, result, dst_name


def currency_code(token):
    token = token.lower()
    if token.upper() in CURRENCIES:
        return token.upper()
    return CURRENCY_NAMES.get(token)


def currency_query(text):
    """'20 usd in eur' -> (20.0, 'USD', 'EUR'), or None."""
    parts = _split(text)
    if not parts:
        return None
    amount, src, dst = parts
    src, dst = currency_code(src), currency_code(dst)
    if not src or not dst or src == dst:
        return None
    return amount, src, dst


class Rates:
    """ECB exchange rates (base EUR), loaded from the cache or fetched when asked for."""

    def __init__(self):
        cached = load_json(RATES_PATH, {})
        self.rates = cached.get("rates") or {}
        self.date = cached.get("date", "")
        self._fetched = cached.get("fetched", 0)
        self._failed_at = 0
        self._busy = False
        self._waiting = []

    @property
    def fresh(self):
        return bool(self.rates) and time.time() - self._fetched < RATES_MAX_AGE

    def convert(self, amount, src, dst):
        if src not in self.rates or dst not in self.rates:
            return None
        return amount / self.rates[src] * self.rates[dst]

    def ensure(self, callback):
        """Fetch the rates if they are old or missing; callback(ok) on the main loop once they are in."""
        if self.fresh:
            return False
        if time.time() - self._failed_at < RATES_RETRY:
            return False  # offline: don't ask again on every key press
        self._waiting.append(callback)
        if not self._busy:
            self._busy = True
            self._fetch(RATES_URLS)
        return True

    def _fetch(self, urls):
        """Ask the first mirror; the next one only if it brings nothing usable."""
        def done(_status, data):
            if (isinstance(data, dict) and isinstance(data.get("rates"), dict)) or len(urls) == 1:
                self._done(data if isinstance(data, dict) else None)
            else:
                self._fetch(urls[1:])

        http.get_json(urls[0], done, timeout=8)

    def _done(self, data):
        self._busy = False
        ok = bool(data and isinstance(data.get("rates"), dict))
        if ok:
            self.rates = {k: float(v) for k, v in data["rates"].items() if isinstance(v, (int, float))}
            self.rates["EUR"] = 1.0
            self.date, self._fetched = str(data.get("date", "")), time.time()
            save_json(RATES_PATH, {"rates": self.rates, "date": self.date, "fetched": self._fetched})
        else:
            self._failed_at = time.time()
        waiting, self._waiting = self._waiting, []
        for callback in waiting:
            callback(ok)
