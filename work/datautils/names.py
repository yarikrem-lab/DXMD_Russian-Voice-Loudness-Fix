import re

NON_SPEAKER = {
    'vendorenticer', 'barenticer', 'enticernadanear', 'enticer', 'enticerout',
    'naturalsonlyexit', 'naturalsonlycar', 'm01_naturalsonlyexit',
    'weapondrawn', 'warning', 'keyboard', 'cbkexplosion', 'occkneel', 'occ',
    'cellenticer', 'firstenticer', 'secondenticer', 'occenticer', 'loiterenticer',
    '03enticer', '07enticer', 'visit1', 'visit2', 'visit3',
    'strip01', 'strip02', 'strip05', 'strip06',
    'femalepa', 'commannouncerfemale01', 'commannouncermale01', 'commannouncermale02',
}


def speaker_of(rel):
    p = rel.replace('\\', '/').split('/')
    stem = p[-1]
    if stem.lower().endswith('.pc_fsb'):
        stem = stem[:-7]
    if stem.lower().endswith('.wavebank'):
        stem = stem[:-9]
    toks = stem.split('_')
    if 'barks' in p:
        return p[-2]
    last = toks[-1] if toks else ''
    if last == '' or last.isdigit() or last in NON_SPEAKER:
        j = len(toks) - 2
        while j >= 0 and (toks[j] == '' or toks[j].isdigit() or toks[j] in NON_SPEAKER):
            j -= 1
        return toks[j] if j >= 0 else 'announcer'
    return last


NAMED = {
    'jen': 'Adam Jensen', 'jim': 'Jim Miller', 'jimorc': 'Jim Miller', 'mil': 'Jim Miller',
    'otar': 'Otar Botkoveli', 'koller': 'Vaclav Koller', 'delara': 'Delara Auzenne',
    'vega': 'Alex Vega', 'sarif': 'David Sarif', 'march': 'Viktor Marchenko',
    'smiley': 'Smiley', 'singh': 'Singh', 'singhcombat': 'Singh', 'mac': 'Peter MacReady',
    'chang': 'Chang', 'aria': 'Aria Argento', 'hild': 'Hilda', 'eliza': 'Eliza Cassan',
    'radich': 'Radich', 'pavlak': 'Pavlak', 'manderly': 'Manderley', 'stansfield': 'Stanfield',
    'pritchard': 'Francis Pritchard', 'chi': 'Elias Chikane', 'tib': 'Tibor Sokol',
    'dra': 'Drahomir', 'dar': 'Daria Myska', 'ruc': 'Rucker', 'ltk': 'Little K',
    'nomad': 'Nomad', 'brown': 'Brown', 'fix': 'Fix', 'mejia': 'Mejia', 'flossy': 'Flossy',
    'stenger': 'Stenger', 'saridakis': 'Saridakis', 'bladeclerk': 'Blade Clerk',
    'ludvkbrtndr': 'Ludvik', 'dtown': 'D-Town', 'oshio': 'Oshiro', 'swhittaker': 'Whitaker',
    'slaw': 'Slawomir', 'ashia': 'Ashia',
}

NONCHAR = {
    'prison': 'Announcer (Prison)', 'robdrone': 'Drone', 'robsentry': 'Sentinel Robot',
    'brchvrgrd01': 'Breach VR Guard', 'brchvrboss01': 'Breach VR Boss',
    'brchvrsnpr01': 'Breach VR Sniper', 'brchvrsnt01': 'Breach VR Sentinel',
    'brchvrogr01': 'Breach VR Ogre', 'brchvrdrn01': 'Breach VR Drone',
    'brchrmbase': 'Breach Base', 'brchrmvrsa01': 'Breach Room', 'brchrmstnr01': 'Breach Room',
    'brchrmsant01': 'Breach Room', 'brchrmpicus01': 'Breach Room', 'brchrmtrvs01': 'Breach Room',
    'fczkioskspkr': 'Kiosk Speaker', 'fmkioskspkr': 'Kiosk Speaker',
    'wrdnasstnt': 'Wardens Assistant', 'prordrecng': 'Recording', 'dlc2recng': 'Recording',
    'dlc1recng': 'Recording', 'pagarm': 'PA Announcer', 'tf29-na': 'TF29 Announcer',
    'tf29': 'TF29 Announcer', 'radhost': 'Radio Host', 'all': 'Group Line',
    'hacking': 'Hacking Interface', 'cuffed': 'Cuffed', 'poor': 'Ambient', 'amb': 'Ambient',
    'golem': 'Golem', 'silence': 'Silence', 'final3d': 'Cutscene', 'hongkong': 'Hong Kong',
    'czech': 'Czech', 'csm01': 'Cutscene', 'csm02': 'Cutscene', 'csm03': 'Cutscene',
    'm01': 'Cutscene', 'm02': 'Cutscene', 'm04': 'Cutscene', 'm05': 'Cutscene',
    'f01': 'Cutscene', 'f02': 'Cutscene', 'f03': 'Cutscene', 'paredqueen': 'Parade Queen',
    'worgate': 'Worshipper',
}

GENERIC = [
    (r'^(m|f)czciv(\d+)$', 'Civilian', True),
    (r'^(m|f)czpol(\d+)$', 'Police', True),
    (r'^(m|f)czarcgold(\d+)$', 'Elite Augmented', True),
    (r'^(m|f)czarc(\d+)$', 'Augmented', True),
    (r'^msldvali(\d+)$', 'Dvali Gangster', False),
    (r'^mrudvali(\d+)$', 'Dvali Gangster', False),
    (r'^muktv(\d+)$', 'TV Reporter', False),
    (r'^(m|f)ukciv(\d+)$', 'Civilian Utulek', True),
    (r'^(m|f)natf29civ(\d+)$', 'TF29', True),
    (r'^csmczciv(\d+)$', 'Civilian', False),
    (r'^csfczciv(\d+)$', 'Civilian', False),
    (r'^csmczpol(\d+)$', 'Police', False),
    (r'^guardem(\d+)$', 'Guard', False),
    (r'^guardef(\d+)$', 'Guard', False),
    (r'^inmateem(\d+)$', 'Inmate', False),
    (r'^(m|f)czwors(\d+)$', 'Worshipper', True),
    (r'^fczantiaug(\d+)$', 'Anti-Aug Protester', False),
    (r'^(m|f)natf29(\d+)$', 'TF29', True),
    (r'^mej(\d+)$', 'Dubai Guard', False),
    (r'^maj(\d+)$', 'Dubai Guard', False),
    (r'^almc(\d+)$', 'Blade Plaza Civilian', False),
    (r'^alfc(\d+)$', 'Blade Plaza Civilian', False),
    (r'^darciv(\d+)$', 'Civilian', False),
    (r'^kciv(\d+)$', 'Civilian', False),
    (r'^bnsciv(\d+)$', 'Civilian', False),
    (r'^ohd(\d+)$', 'NPC', False),
]


def nice_name(code):
    if code in NAMED:
        return NAMED[code]
    if code in NONCHAR:
        return NONCHAR[code]
    for pat, label, gender in GENERIC:
        m = re.match(pat, code)
        if m:
            num = m.group(2) if gender else m.group(1)
            if gender:
                g = 'M' if m.group(1) == 'm' else 'F'
                return '%s %s%s' % (label, g, num)
            return '%s %s' % (label, num)
    return code[0].upper() + code[1:] if code else code
