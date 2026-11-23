"""Company identification in news text (headline and summary) - precision first.

A news item is attached to a company only on a strong signal. If the signal is weak or ambiguous, the item stays
general market news; it is never attached to a company on a guess.

Rules
* Strong signals: the company's distinctive name ("Infosys", "Tata Consultancy Services"), a curated alias
  ("TCS", "HUL", "L&T"), or its NSE symbol written in capitals ("NTPC").
* Group or family words never match on their own: "Tata", "Reliance", "Adani", "HDFC", "Bajaj", "Mahindra",
  "ICICI", "Godrej", "Jindal" ... each needs the rest of the company name.
* Foreign parents never stand in for the Indian listed company: "Nestle", "Unilever", "Suzuki", "Vodafone",
  "Colgate", "Whirlpool" alone do not match Nestle India, HUL, Maruti, Vodafone Idea, Colgate-Palmolive (India) or
  Whirlpool of India.
* The longest name wins, and names of *other* listed entities block shorter matches inside them, so
  "Tech Mahindra" is not Mahindra & Mahindra, "HDFC Life" is not HDFC Bank, "ITC Hotels" is not ITC and
  "Bajaj Housing Finance" is not Bajaj Finance.
* Subsidiaries and brands are used only where the relationship is a matter of public record (listed below with the
  parent), and the match records that it came through the subsidiary.
* Ordinary English words that are also company names ("Titan", "Lupin") match only with a capital letter.
"""
from __future__ import annotations

import re
import threading
import time
import unicodedata
from dataclasses import dataclass

# Curated aliases for the tracked universe. Every alias is matched as a whole word/phrase, case-insensitively unless it
# is listed in CASE_SENSITIVE. The company's own legal name (minus "Limited") is always added automatically.
ALIASES: dict[str, list[str]] = {
    "AARTIIND.NS": ["Aarti Industries"],
    "ADANIENT.NS": ["Adani Enterprises"], "ADANIGREEN.NS": ["Adani Green Energy", "Adani Green"],
    "ADANIPORTS.NS": ["Adani Ports", "APSEZ"], "ADANIPOWER.NS": ["Adani Power"],
    "AMBUJACEM.NS": ["Ambuja Cements", "Ambuja Cement"], "APOLLOHOSP.NS": ["Apollo Hospitals"],
    "ASHOKLEY.NS": ["Ashok Leyland"], "ASIANPAINT.NS": ["Asian Paints"],
    "AUBANK.NS": ["AU Small Finance Bank", "AU Bank", "AU SFB"], "AUROPHARMA.NS": ["Aurobindo Pharma", "Aurobindo"],
    "AXISBANK.NS": ["Axis Bank"], "BAJAJ-AUTO.NS": ["Bajaj Auto"], "BAJAJFINSV.NS": ["Bajaj Finserv"],
    "BAJFINANCE.NS": ["Bajaj Finance"], "BANKBARODA.NS": ["Bank of Baroda"],
    "BHARTIARTL.NS": ["Bharti Airtel", "Airtel"], "BLUESTARCO.NS": ["Blue Star"],
    "BPCL.NS": ["Bharat Petroleum", "BPCL"], "BRITANNIA.NS": ["Britannia Industries", "Britannia"],
    "CANBK.NS": ["Canara Bank"], "CHAMBLFERT.NS": ["Chambal Fertilisers", "Chambal Fertilizers"],
    "CHOLAFIN.NS": ["Cholamandalam Investment", "Cholamandalam Finance", "Chola Finance"],
    "CIPLA.NS": ["Cipla"], "COALINDIA.NS": ["Coal India"], "COFORGE.NS": ["Coforge"],
    "COLPAL.NS": ["Colgate-Palmolive India", "Colgate-Palmolive (India)", "Colgate India"],
    "COROMANDEL.NS": ["Coromandel International"], "CROMPTON.NS": ["Crompton Greaves Consumer", "Crompton Consumer"],
    "DABUR.NS": ["Dabur"], "DEEPAKNTR.NS": ["Deepak Nitrite"], "DHANUKA.NS": ["Dhanuka Agritech", "Dhanuka"],
    "DIVISLAB.NS": ["Divi's Laboratories", "Divis Laboratories", "Divi's Labs", "Divis Labs", "Divi's"],
    "DIXON.NS": ["Dixon Technologies", "Dixon Tech"], "DLF.NS": ["DLF"],
    "DRREDDY.NS": ["Dr Reddy's", "Dr. Reddy's", "Dr Reddys", "Dr. Reddys", "Dr Reddy", "Dr. Reddy"],
    "EICHERMOT.NS": ["Eicher Motors", "Eicher"], "FEDERALBNK.NS": ["Federal Bank"],
    "FORTIS.NS": ["Fortis Healthcare"], "GMRAIRPORT.NS": ["GMR Airports"],
    "GODREJCP.NS": ["Godrej Consumer Products", "Godrej Consumer", "GCPL"], "GODREJPROP.NS": ["Godrej Properties"],
    "GRASIM.NS": ["Grasim Industries", "Grasim"], "HAVELLS.NS": ["Havells"],
    "HCLTECH.NS": ["HCL Technologies", "HCLTech", "HCL Tech"], "HDFCBANK.NS": ["HDFC Bank"],
    "HDFCLIFE.NS": ["HDFC Life"], "HEROMOTOCO.NS": ["Hero MotoCorp", "Hero Motocorp"],
    "HINDALCO.NS": ["Hindalco"], "HINDUNILVR.NS": ["Hindustan Unilever", "HUL"],
    "ICICIBANK.NS": ["ICICI Bank"], "ICICIGI.NS": ["ICICI Lombard"], "IDEA.NS": ["Vodafone Idea"],
    "IDFCFIRSTB.NS": ["IDFC First Bank", "IDFC First", "IDFC FIRST Bank"], "INDUSINDBK.NS": ["IndusInd Bank"],
    "INDUSTOWER.NS": ["Indus Towers"], "INFY.NS": ["Infosys"],
    "IOC.NS": ["Indian Oil Corporation", "Indian Oil", "IndianOil", "IOCL"],
    "IRB.NS": ["IRB Infrastructure", "IRB Infra"], "ITC.NS": ["ITC"],
    "JINDALSTEL.NS": ["Jindal Steel", "Jindal Steel & Power", "Jindal Steel and Power", "JSPL"],
    "JIOFIN.NS": ["Jio Financial Services", "Jio Financial", "JFSL"], "JSWSTEEL.NS": ["JSW Steel"],
    "KOTAKBANK.NS": ["Kotak Mahindra Bank", "Kotak Bank"], "LALPATHLAB.NS": ["Dr Lal PathLabs", "Dr. Lal PathLabs", "Lal PathLabs", "Lal Pathlabs"],
    "LICI.NS": ["Life Insurance Corporation of India", "Life Insurance Corporation", "LIC"],
    "LODHA.NS": ["Lodha Developers", "Macrotech Developers"],
    "LT.NS": ["Larsen & Toubro", "Larsen and Toubro", "L&T"], "LUPIN.NS": ["Lupin"],
    "M&M.NS": ["Mahindra & Mahindra", "Mahindra and Mahindra", "M&M"], "MANKIND.NS": ["Mankind Pharma"],
    "MARICO.NS": ["Marico"], "MARUTI.NS": ["Maruti Suzuki", "Maruti"], "MAXHEALTH.NS": ["Max Healthcare"],
    "MEDANTA.NS": ["Medanta"], "MPHASIS.NS": ["Mphasis"], "MUTHOOTFIN.NS": ["Muthoot Finance"],
    "NATIONALUM.NS": ["National Aluminium", "NALCO"], "NAVINFLUOR.NS": ["Navin Fluorine"],
    "NESTLEIND.NS": ["Nestle India", "Nestlé India"], "NMDC.NS": ["NMDC"], "NTPC.NS": ["NTPC"],
    "OBEROIRLTY.NS": ["Oberoi Realty"], "ONGC.NS": ["Oil and Natural Gas Corporation", "Oil & Natural Gas Corporation", "ONGC"],
    "PERSISTENT.NS": ["Persistent Systems"], "PHOENIXLTD.NS": ["Phoenix Mills"],
    "PIDILITIND.NS": ["Pidilite Industries", "Pidilite"], "PIIND.NS": ["PI Industries"],
    "PNB.NS": ["Punjab National Bank", "PNB"], "POWERGRID.NS": ["Power Grid Corporation", "Power Grid", "POWERGRID"],
    "PRESTIGE.NS": ["Prestige Estates"], "RALLIS.NS": ["Rallis India", "Rallis"],
    "RELIANCE.NS": ["Reliance Industries", "RIL"], "RPOWER.NS": ["Reliance Power"],
    "SAIL.NS": ["Steel Authority of India", "SAIL"], "SBILIFE.NS": ["SBI Life Insurance", "SBI Life"],
    "SBIN.NS": ["State Bank of India", "SBI"], "SHREECEM.NS": ["Shree Cement"], "SHRIRAMFIN.NS": ["Shriram Finance"],
    "SRF.NS": ["SRF"], "SUNPHARMA.NS": ["Sun Pharmaceutical Industries", "Sun Pharmaceutical", "Sun Pharma"],
    "TATACHEM.NS": ["Tata Chemicals"], "TATACOMM.NS": ["Tata Communications"],
    "TATACONSUM.NS": ["Tata Consumer Products", "Tata Consumer"], "TATAPOWER.NS": ["Tata Power"],
    "TATASTEEL.NS": ["Tata Steel"], "TCS.NS": ["Tata Consultancy Services", "Tata Consultancy", "TCS"],
    "TECHM.NS": ["Tech Mahindra"], "TITAN.NS": ["Titan Company", "Titan Co"],
    "TMCV.NS": ["Tata Motors Commercial Vehicles", "Tata Motors CV", "TMCV"],
    "TMPV.NS": ["Tata Motors Passenger Vehicles", "Tata Motors PV", "TMPV"],
    "TORNTPHARM.NS": ["Torrent Pharmaceuticals", "Torrent Pharma"], "TVSMOTOR.NS": ["TVS Motor"],
    "ULTRACEMCO.NS": ["UltraTech Cement", "UltraTech", "Ultratech"], "UPL.NS": ["UPL"],
    "VEDL.NS": ["Vedanta"], "VOLTAS.NS": ["Voltas"], "WHIRLPOOL.NS": ["Whirlpool of India", "Whirlpool India"],
    "WIPRO.NS": ["Wipro"], "ZYDUSLIFE.NS": ["Zydus Lifesciences", "Zydus Life"],
}

# Subsidiaries / brands whose parent relationship is public record. Matches carry reason="subsidiary".
SUBSIDIARIES: dict[str, list[str]] = {
    "RELIANCE.NS": ["Jio Platforms", "Reliance Jio", "Reliance Retail"],    # subsidiaries of Reliance Industries
    "HINDALCO.NS": ["Novelis"],                                            # wholly-owned subsidiary of Hindalco
    "EICHERMOT.NS": ["Royal Enfield"],                                     # a business of Eicher Motors
}

# Names of OTHER entities (separately listed companies, parents, funds) that contain a tracked company's alias.
# A blocker that overlaps a candidate match cancels it.
BLOCKERS = [
    "ITC Hotels", "ITC HS", "ITC-HS", "ITC (HS)", "ITC code", "ITC Infotech", "Reliance Infrastructure", "Reliance Infra", "Reliance Capital", "Reliance Communications",
    "Reliance Home Finance", "Reliance General", "Reliance Nippon", "Reliance Securities", "Tata Motors Finance",
    "Bajaj Housing Finance", "Bajaj Holdings", "Bajaj Electricals", "Bajaj Consumer", "Bajaj Hindusthan", "Bajaj Allianz",
    "HDFC AMC", "HDFC Asset Management", "HDFC Mutual Fund", "HDFC Credila", "HDFC Ergo", "HDFC ERGO",
    "ICICI Prudential", "ICICI Pru", "ICICI Securities", "SBI Card", "SBI Cards", "SBI Mutual Fund", "SBI Funds", "SBI Capital", "SBI Capital Markets", "SBICAP", "SBI Caps",
    "SBI Securities", "ICICI Securities", "Kotak Securities", "HDFC Securities", "Axis Capital", "Axis Securities", "IDBI Capital",
    "SBI General", "LIC Housing Finance", "LIC Housing", "LIC Mutual Fund", "L&T Finance", "L&T Technology Services",
    "L&T Tech", "LTIMindtree", "LTI Mindtree", "NMDC Steel", "NTPC Green", "Oil India", "PNB Housing",
    "PNB MetLife", "Airtel Africa", "Bharti Hexacom", "Vedanta Resources", "Hindustan Zinc", "Adani Wilmar", "Adani Total Gas", "Adani Energy Solutions", "Adani Transmission",
    "IRB InvIT", "IRB Infrastructure Trust", "JSW Energy", "JSW Infrastructure", "JSW Cement", "Jindal Stainless",
    "Jindal Saw", "Tata Elxsi", "Tata Technologies", "Tata Investment", "Kotak Mahindra AMC", "Kotak Mahindra Life",
    "Maruti Suzuki Toyotsu", "Godrej Industries", "Godrej Agrovet", "Mahindra Finance",
    "Mahindra & Mahindra Financial", "Mahindra Lifespace", "Mahindra Holidays", "Mahindra Logistics",
    "Sun TV", "Dixon Ticonderoga", "Titan Intech", "Canara Robeco", "Canara HSBC", "Federal Reserve", "Fed Reserve",
    "Blue Star Infotech", "Larsen Toubro Infotech", "Muthoot Microfin", "Muthoot Fincorp",
    "Shriram Properties", "Shriram Pistons", "Zydus Wellness", "Torrent Power", "Aarti Drugs", "Aarti Pharmalabs",
]

# Aliases that are also ordinary words: match only with exact capitalisation.
CASE_SENSITIVE = {"Lupin", "Eicher", "Rallis", "Dhanuka", "Marico", "Dabur",
                  "Grasim", "Cipla", "Voltas", "Airtel", "Britannia", "Aurobindo", "Vedanta", "Maruti", "Havells",
                  "Hindalco", "Pidilite", "Novelis", "Wipro", "Infosys", "Coforge", "Mphasis", "Medanta"}

# Generic words that must never become an automatic alias on their own.
_GENERIC = {"tata", "reliance", "adani", "hdfc", "icici", "bajaj", "mahindra", "godrej", "jindal", "jsw", "sbi", "lic",
            "india", "indian", "bharat", "national", "global", "power", "steel", "bank", "finance", "industries", "the",
            "max", "sun", "blue", "hero", "asian", "apollo", "axis", "federal", "coal", "oil", "life", "shree", "shriram",
            "muthoot", "oberoi", "prestige", "phoenix", "torrent", "zydus", "aarti", "kotak", "canara", "chola", "gmr",
            "irb", "hcl", "idfc", "indus", "punjab", "state", "ashok", "deepak", "crompton", "coromandel", "persistent",
            "mankind", "fortis", "titan", "jio", "tvs", "vodafone", "nestle", "unilever", "suzuki", "colgate", "whirlpool"}


# Capitalised symbols that are also ordinary words or common abbreviations in headlines.
_COMMON_UPPER = {"IDEA", "GOLD", "HOME", "CASH", "BEST", "OIL", "GAS", "USA", "CEO", "IPO", "GDP", "RBI", "SEBI", "NSE", "BSE",
                 "IOC", "ICE", "SUN", "STAR", "GOOD", "TIME", "CARE", "FACT", "MAX", "ONE", "AND", "THE", "FOR", "NEW"}


@dataclass(frozen=True)
class Match:
    symbol: str
    alias: str
    reason: str          # "name" | "alias" | "symbol" | "subsidiary"
    start: int
    end: int


def _fold(s: str) -> str:
    """Accents removed ('Nestlé' -> 'Nestle'), curly quotes straightened; length-preserving where possible."""
    if s.isascii():                     # most headlines: nothing to fold (NFKD leaves ASCII unchanged)
        return s
    s = s.replace("’", "'").replace("‘", "'").replace("�", "e")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_SUFFIX_RE = re.compile(r"\s*\b(limited|ltd\.?)\s*$", re.I)


def legal_core(name: str) -> str:
    n = _fold(name or "").strip()
    n = re.sub(r"\s*\(sample\)\s*$", "", n, flags=re.I)       # fictional demo companies: "Beta Infotech Ltd (Sample)"
    n = re.sub(r"^the\s+", "", n, flags=re.I)
    return _SUFFIX_RE.sub("", n).strip(" .,")


_TOKEN_RE = re.compile(r"[A-Za-z0-9&]+")


def _tokens(s: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(s)]


class Matcher:
    """Compiled matcher over a {symbol: legal name} map (normally the tracked companies).

    Text and names are compared as word sequences (letters, digits and '&'), so punctuation and spacing differences
    ("Dr. Reddy's" / "Dr Reddy's", "Colgate-Palmolive (India)") do not matter, and a name never matches inside a
    longer word ("ITC" is not found in "switch")."""

    def __init__(self, companies: dict[str, str]):
        entries: list[tuple[str, str, str]] = []           # (alias, symbol | "", reason)
        for sym, name in companies.items():
            if sym not in ALIASES:                  # companies tracked later: full name + capitalised NSE symbol only
                core = legal_core(name)
                words = re.findall(r"[a-z0-9]+", core.lower())
                if len(words) >= 2 and not all(w in _GENERIC for w in words):
                    entries.append((core, sym, "name"))
                base = sym.split(".")[0]
                if base.isalpha() and base.isupper() and len(base) >= 3 and base not in _COMMON_UPPER:
                    entries.append((base, sym, "symbol"))
            for a in ALIASES.get(sym, []):
                entries.append((a, sym, "symbol" if a.isupper() and a == sym.split(".")[0] else "alias"))
            for a in SUBSIDIARIES.get(sym, []):
                entries.append((a, sym, "subsidiary"))
        for b in BLOCKERS:
            entries.append((b, "", "blocker"))
        self.known = set(companies)
        # index: first word (lower case) -> candidates, longest first
        self._index: dict[str, list[tuple[tuple[str, ...], bool, str, str, str]]] = {}
        seen = set()
        for alias, sym, reason in entries:
            toks = tuple(t for t, _, _ in _tokens(_fold(alias)))
            if not toks:
                continue
            cs = alias in CASE_SENSITIVE or (alias.replace(" ", "").replace("&", "").isupper() and len(alias) <= 5)
            key = (toks if cs else tuple(t.lower() for t in toks), sym, cs)
            if key in seen:
                continue
            seen.add(key)
            self._index.setdefault(toks[0].lower(), []).append((toks if cs else tuple(t.lower() for t in toks), cs, alias, sym, reason))
        for lst in self._index.values():
            lst.sort(key=lambda e: -len(e[0]))

    def _spans(self, text: str) -> list[tuple[int, int, int, str, str, str]]:
        """(first token, last token + 1, length in chars, alias, symbol, reason) for every candidate occurrence."""
        toks = _tokens(text)
        low = [t.lower() for t, _, _ in toks]
        out = []
        for i, first in enumerate(low):
            for words, cs, alias, sym, reason in self._index.get(first, ()):
                n = len(words)
                if i + n > len(toks):
                    continue
                seq = tuple(t for t, _, _ in toks[i:i + n]) if cs else tuple(low[i:i + n])
                if seq == words:
                    out.append((i, i + n, toks[i + n - 1][2] - toks[i][1], alias, sym, reason))
        return out

    def find(self, text: str | None) -> list[Match]:
        """Companies named in `text`, in order of first appearance; overlapping names resolved longest-first and
        blocked by names of other entities."""
        if not text:
            return []
        memo = self.__dict__.setdefault("_memo", {})        # the same headlines are re-checked on every news reload
        hit = memo.get(text)
        if hit is not None:
            return list(hit)
        out = self._find(text)
        if len(memo) > 50_000:
            memo.clear()
        memo[text] = tuple(out)
        return out

    def _find(self, text: str) -> list[Match]:
        t = _fold(text)
        spans = sorted(self._spans(t), key=lambda s: (-(s[1] - s[0]), -s[2], s[0]))
        taken: list[tuple[int, int]] = []
        kept: list[Match] = []
        for start, end, _len, alias, sym, reason in spans:
            if any(start < e and end > s for s, e in taken):
                continue
            taken.append((start, end))
            if sym:                                         # blockers occupy the span but attach nothing
                kept.append(Match(sym, alias, reason, start, end))
        kept.sort(key=lambda m: (m.start, m.reason == "subsidiary"))
        out: list[Match] = []
        for m in kept:
            prev = next((o for o in out if o.symbol == m.symbol), None)
            if prev is None:
                out.append(m)
            elif prev.reason == "subsidiary" and m.reason != "subsidiary":   # a direct mention outranks a subsidiary one
                out[out.index(prev)] = Match(m.symbol, m.alias, m.reason, prev.start, prev.end)
        return out

    def symbols(self, *texts: str | None) -> list[str]:
        seen, out = set(), []
        for t in texts:
            for m in self.find(t):
                if m.symbol not in seen:
                    seen.add(m.symbol)
                    out.append(m.symbol)
        return out

    def mentions(self, symbol: str, *texts: str | None) -> Match | None:
        for t in texts:
            for m in self.find(t):
                if m.symbol == symbol:
                    return m
        return None


_CACHE: dict = {"t": 0.0, "m": None, "key": None}
_LOCK = threading.Lock()


def matcher(companies: dict[str, str] | None = None, need: str | None = None) -> Matcher:
    """Matcher over the tracked companies, rebuilt at most every 10 minutes, or at once when the company list changed
    or `need` (a symbol) is not covered yet."""
    if companies is not None:
        return Matcher(companies)
    from . import repository as repo
    with _LOCK:
        now = time.time()
        stale = _CACHE["m"] is None or now - _CACHE["t"] > 600 or (need is not None and need not in _CACHE["m"].known)
        if stale:
            comps = repo.list_companies()
            key = tuple(sorted(comps["symbol"]))
            if key != _CACHE["key"] or _CACHE["m"] is None:
                _CACHE["m"] = Matcher(dict(zip(comps["symbol"], comps["name"])))
                _CACHE["key"] = key
            _CACHE["t"] = now
        return _CACHE["m"]


def reset_cache() -> None:
    with _LOCK:
        _CACHE.update({"t": 0.0, "m": None, "key": None})
