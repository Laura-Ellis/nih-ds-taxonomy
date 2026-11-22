"""Country lookup for analysis D: ISO3 code, display name and World Bank region (classic 7; Pakistan in South Asia).

Keys are upper-case country names as RePORTER (`org_country`) and USAspending (`subawardee_country_name`) spell them.
"""

SSA, EAP, ECA, LAC, MENA, NA, SA = ("Sub-Saharan Africa", "East Asia & Pacific", "Europe & Central Asia",
                                    "Latin America & Caribbean", "Middle East & North Africa", "North America",
                                    "South Asia")

# ISO3: (display name, region)
COUNTRY = {
    "AGO": ("Angola", SSA), "BDI": ("Burundi", SSA), "BEN": ("Benin", SSA), "BFA": ("Burkina Faso", SSA),
    "BWA": ("Botswana", SSA), "COD": ("DR Congo", SSA), "COG": ("Congo", SSA), "CIV": ("Côte d'Ivoire", SSA),
    "CMR": ("Cameroon", SSA), "ETH": ("Ethiopia", SSA), "GAB": ("Gabon", SSA), "GHA": ("Ghana", SSA),
    "GMB": ("Gambia", SSA), "GIN": ("Guinea", SSA), "GNB": ("Guinea-Bissau", SSA), "KEN": ("Kenya", SSA),
    "LBR": ("Liberia", SSA), "LSO": ("Lesotho", SSA), "MDG": ("Madagascar", SSA), "MLI": ("Mali", SSA),
    "MOZ": ("Mozambique", SSA), "MUS": ("Mauritius", SSA), "MWI": ("Malawi", SSA), "NAM": ("Namibia", SSA),
    "NER": ("Niger", SSA), "NGA": ("Nigeria", SSA), "RWA": ("Rwanda", SSA), "SDN": ("Sudan", SSA),
    "SEN": ("Senegal", SSA), "SLE": ("Sierra Leone", SSA), "SWZ": ("Eswatini", SSA), "SYC": ("Seychelles", SSA),
    "TZA": ("Tanzania", SSA), "UGA": ("Uganda", SSA), "ZAF": ("South Africa", SSA), "ZMB": ("Zambia", SSA),
    "ZWE": ("Zimbabwe", SSA),
    "AUS": ("Australia", EAP), "MMR": ("Myanmar", EAP), "CHN": ("China", EAP), "FJI": ("Fiji", EAP),
    "HKG": ("Hong Kong", EAP), "IDN": ("Indonesia", EAP), "JPN": ("Japan", EAP), "KHM": ("Cambodia", EAP),
    "KOR": ("South Korea", EAP), "LAO": ("Laos", EAP), "MNG": ("Mongolia", EAP), "MYS": ("Malaysia", EAP),
    "NZL": ("New Zealand", EAP), "PHL": ("Philippines", EAP), "PNG": ("Papua New Guinea", EAP),
    "SGP": ("Singapore", EAP), "THA": ("Thailand", EAP), "TWN": ("Taiwan", EAP), "VNM": ("Vietnam", EAP),
    "ARM": ("Armenia", ECA), "AUT": ("Austria", ECA), "AZE": ("Azerbaijan", ECA), "BEL": ("Belgium", ECA),
    "BGR": ("Bulgaria", ECA), "CHE": ("Switzerland", ECA), "CYP": ("Cyprus", ECA), "CZE": ("Czechia", ECA),
    "DEU": ("Germany", ECA), "DNK": ("Denmark", ECA), "ESP": ("Spain", ECA), "EST": ("Estonia", ECA),
    "FIN": ("Finland", ECA), "FRA": ("France", ECA), "FRO": ("Faroe Islands", ECA), "GBR": ("United Kingdom", ECA),
    "GEO": ("Georgia", ECA), "GRC": ("Greece", ECA), "HRV": ("Croatia", ECA), "HUN": ("Hungary", ECA),
    "IRL": ("Ireland", ECA), "ISL": ("Iceland", ECA), "ITA": ("Italy", ECA), "KAZ": ("Kazakhstan", ECA),
    "KGZ": ("Kyrgyzstan", ECA), "LTU": ("Lithuania", ECA), "LVA": ("Latvia", ECA), "MDA": ("Moldova", ECA),
    "MKD": ("North Macedonia", ECA), "NLD": ("Netherlands", ECA), "NOR": ("Norway", ECA), "POL": ("Poland", ECA),
    "PRT": ("Portugal", ECA), "ROU": ("Romania", ECA), "RUS": ("Russia", ECA), "SRB": ("Serbia", ECA),
    "SVK": ("Slovakia", ECA), "SVN": ("Slovenia", ECA), "SWE": ("Sweden", ECA), "TJK": ("Tajikistan", ECA),
    "TUR": ("Türkiye", ECA), "UKR": ("Ukraine", ECA),
    "ARG": ("Argentina", LAC), "BHS": ("Bahamas", LAC), "BRB": ("Barbados", LAC), "BOL": ("Bolivia", LAC),
    "BRA": ("Brazil", LAC), "CHL": ("Chile", LAC), "COL": ("Colombia", LAC), "CRI": ("Costa Rica", LAC),
    "DOM": ("Dominican Republic", LAC), "ECU": ("Ecuador", LAC), "GTM": ("Guatemala", LAC), "GUY": ("Guyana", LAC),
    "HND": ("Honduras", LAC), "HTI": ("Haiti", LAC), "JAM": ("Jamaica", LAC), "KNA": ("St. Kitts and Nevis", LAC),
    "MEX": ("Mexico", LAC), "NIC": ("Nicaragua", LAC), "PAN": ("Panama", LAC), "PER": ("Peru", LAC),
    "PRY": ("Paraguay", LAC), "SLV": ("El Salvador", LAC), "SUR": ("Suriname", LAC),
    "TTO": ("Trinidad and Tobago", LAC), "URY": ("Uruguay", LAC), "VEN": ("Venezuela", LAC),
    "ARE": ("United Arab Emirates", MENA), "EGY": ("Egypt", MENA), "IRN": ("Iran", MENA), "ISR": ("Israel", MENA),
    "JOR": ("Jordan", MENA), "LBN": ("Lebanon", MENA), "MAR": ("Morocco", MENA), "SAU": ("Saudi Arabia", MENA),
    "TUN": ("Tunisia", MENA), "PSE": ("West Bank and Gaza", MENA),
    "CAN": ("Canada", NA), "USA": ("United States", NA),
    "BGD": ("Bangladesh", SA), "BTN": ("Bhutan", SA), "IND": ("India", SA), "LKA": ("Sri Lanka", SA),
    "NPL": ("Nepal", SA), "PAK": ("Pakistan", SA),
}

# spellings that differ from the display name
ALIAS = {
    "BURKINA": "BFA", "CONGO DEM REP": "COD", "CONGO (KINSHASA)": "COD", "CONGO (BRAZZAVILLE)": "COG",
    "COTE D'IVOIRE": "CIV", "CÔTE D’IVOIRE": "CIV", "GAMBIA, THE": "GMB", "SWAZILAND": "SWZ", "TANZANIA U REP": "TZA",
    "BURMA": "MMR", "KOREA, SOUTH": "KOR", "VIET NAM": "VNM", "CZECH REPUBLIC": "CZE", "MACEDONIA": "MKD",
    "TURKEY": "TUR", "BAHAMAS, THE": "BHS", "ST KITTS/NEVIS": "KNA", "TRINIDAD/TOBA": "TTO", "WEST BANK": "PSE",
    "UNITED STATES": "USA",
}
_BY_NAME = {name.upper(): iso for iso, (name, _) in COUNTRY.items()} | ALIAS


def iso3(name):
    """ISO3 code for a RePORTER or USAspending country name, or None."""
    if not isinstance(name, str) or not name.strip():
        return None
    return _BY_NAME.get(name.strip().upper())


def display(code):
    return COUNTRY.get(code, (code, None))[0]


def region(code):
    return COUNTRY.get(code, (None, None))[1]


# WHO regions, for public outputs (who.int/about/who-we-are/regional-offices). Taiwan, Hong Kong and the Faroe
# Islands are placed with their neighbors.
WHO_REGION = {}
for _r, _codes in {
    "African Region": "AGO BDI BEN BFA BWA COD COG CIV CMR ETH GAB GHA GMB GIN GNB KEN LBR LSO MDG MLI MOZ MUS MWI NAM "
                      "NER NGA RWA SEN SLE SWZ SYC TZA UGA ZAF ZMB ZWE",
    "Region of the Americas": "ARG BHS BRB BOL BRA CHL COL CRI DOM ECU GTM GUY HND HTI JAM KNA MEX NIC PAN PER PRY SLV "
                              "SUR TTO URY VEN CAN USA",
    "South-East Asia Region": "BGD BTN IND LKA NPL MMR THA IDN",
    "European Region": "ARM AUT AZE BEL BGR CHE CYP CZE DEU DNK ESP EST FIN FRA FRO GBR GEO GRC HRV HUN IRL ISL ISR ITA "
                       "KAZ KGZ LTU LVA MDA MKD NLD NOR POL PRT ROU RUS SRB SVK SVN SWE TJK TUR UKR",
    "Eastern Mediterranean Region": "ARE EGY IRN JOR LBN MAR SAU TUN PSE PAK SDN",
    "Western Pacific Region": "AUS CHN FJI HKG JPN KHM KOR LAO MNG MYS NZL PHL PNG SGP TWN VNM",
}.items():
    WHO_REGION.update({_c: _r for _c in _codes.split()})
assert set(WHO_REGION) == set(COUNTRY), set(COUNTRY) ^ set(WHO_REGION)


def who_region(code):
    return WHO_REGION.get(code)
