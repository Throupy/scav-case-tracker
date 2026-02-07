CATEGORY_MAPPING = {
    "Headphones": "Headsets",
    "Headwear": "Helmets",
    "Map": "Barter Items",
    "Face Cover": "Helmets",
    "Vis. observ. device": "Face Cover",
    "Armor": "Armors",
    "Armored equipment": "Armors",
    "Armor Plate": "Armors",
    "Chest rig": "Rigs",
    "Backpack": "Backpacks",
    "Assault rifle": "Guns",
    "Handgun": "Guns",
    "Shotgun": "Guns",
    "Sniper rifle": "Guns",
    "Magazine": "Mods",
    "SMG": "Guns",
    "Assault carbine": "Guns",
    "Marksman rifle": "Guns",
    "Machinegun": "Guns",
    "Revolver": "Guns",
    "Grenade launcher": "Guns",
    "Flashhider": "Mods",
    "Assault scope": "Mods",
    "Reflex sight": "Mods",
    "Foregrip": "Mods",
    "Receiver": "Mods",
    "Charging handle": "Mods",
    "Handguard": "Mods",
    "Mount": "Mods",
    "Stock": "Mods",
    "Ironsight": "Mods",
    "Auxiliary Mod": "Mods",
    "Scope": "Mods",
    "Bipod": "Mods",
    "Gas block": "Mods",
    "Night Vision": "Mods",
    "Compact reflex sight": "Mods",
    "Special scope": "Mods",
    "Thermal Vision": "Mods",
    "UBGL": "Mods",
    "Comb. muzzle device": "Mods",
    "Comb. tact. device": "Mods",
    "Knife": "Guns",
    "Barrel": "Mods",
    "Pistol grip": "Mods",
    "Silencer": "Suppressors",
    "Throwable weapon": "Grenades",
    "Ammo container": "Ammo",
    "Port. container": "Containers",
    "Locking container": "Containers",
    "Common container": "Containers",
    "Random Loot Container": "Containers",
    "Money": "Barter Items",
    "Battery": "Barter Items",
    "Electronics": "Barter Items",
    "Lubricant": "Barter Items",
    "Jewelry": "Barter Items",
    "Other": "Barter Items",
    "Building material": "Barter Items",
    "Stimulant": "Medical",
    "Tool": "Barter Items",
    "Fuel": "Barter Items",
    "Flashlight": "Mods",
    "Household goods": "Barter Items",
    "Flyer": "Barter Items",
    "Multitools": "Barter Items",
    "Compass": "Barter Items",
    "Info": "Barter Items",
    "Repair Kits": "Barter Items",
    "Special item": "Barter Items",
    "Arm Band": "Barter Items",
    "Spring Driven Cylinder": "Mods",
    "Cylinder Magazine": "Mods",
    "Portable Range Finder": "Barter Items",
    "Radio Transmitter": "Barter Items",
    "Cultist Amulet": "Barter Items",
    "Mark of the Unheard": "Barter Items",
    "Planting Kits": "Barter Items",
    "Mechanical Key": "Keys",
    "Keycard": "Keys",
    "Drink": "Provisions",
    "Food": "Provisions",
    "Medical item": "Medical",
    "Drug": "Medical",
    "Medikit": "Medical",
    "Medical supplies": "Medical",
    "Ammo": "Ammo",
    "Ammo packs": "Ammo",
}

SCAV_CASE_TYPES = ["₽2500", "₽15000", "₽95000", "Moonshine", "Intelligence"]

DEFAULT_TRACKED_ITEMS = [
    "Pack of sugar",
    "Bottle of Fierce Hatchling moonshine",
    "Intelligence folder",
]

CLOUDINARY_BASE_URL = "https://res.cloudinary.com/dquzibnsm/image/upload/v1739398246/"

# Error message will read 404 - Not Found, then on new line, one of:
MESSAGES_404 = [
    "Just like that last GPU you searched for.",
    "Page not found, but don’t worry, it’ll extract before you do.",
    "You didn’t bring enough rubles for this route, comrade.",
    "This page is camped by Killa. Good luck.",
    "Wrong keycard. Try again, rat.",
    "This page was found in a dead SCAV’s backpack, but now it’s gone.",
    "Page not found. Maybe it desynced?",
    "You loaded into the wrong raid. Try again.",
]

MESSAGES_403 = [
    "Nice try, but you don’t have the key for this door.",
    "Access denied. Maybe Fence doesn’t trust you enough?",
    "You need to be Level 15 to access this trader… oh wait, wrong game.",
    "Prapor says no. Try again later.",
    "This area is locked. Find a Labs keycard, then we’ll talk.",
    "Your access has been revoked… probably because you scav killed.",
    "You don’t have enough reputation to enter. Go grind some more quests.",
    "You need higher loyalty with Therapist to access this page.",
]

MESSAGES_500 = [
    "Looks like Tarkov servers are down… again.",
    "The game crashed, and now so did this page.",
    "An unexpected error occurred. Just like when your game freezes mid-raid.",
    "This page took too much damage and blacked out.",
    "Something went wrong, kind of like your last raid.",
    "Your request got head-eyes’d by a TTV chad.",
    "Our backend desynced. Please wait for a reconnect...",
    "This page hit an invisible Sturman guard. Try again.",
]

ACHIEVEMENT_CHECKS = {
    "First Case": lambda user: len(user.scav_cases) >= 1,
    "Scav Veteran": lambda user: len(user.scav_cases) >= 50,
    "Scav Elite": lambda user: len(user.scav_cases) >= 100,
    "Millionaire": lambda user: sum((case._return - case.cost) for case in user.scav_cases) >= 1_000_000,
    "Multi-Millionaire": lambda user: sum((case._return - case.cost) for case in user.scav_cases) >= 10_000_000,
    "Hoarder": lambda user: sum((case._return - case.cost) for case in user.scav_cases) >= 100_000_000,
    "Moonshine Master": lambda user: sum(1 for case in user.scav_cases if case.type == "Moonshine") > 10,
    "Intelligence Operator": lambda user: sum(1 for case in user.scav_cases if case.type == "Intelligence") > 10,
    "Moonshine Tycoon": lambda user: sum(1 for case in user.scav_cases if case.type == "Moonshine") > 50,
    "Intel Mogul": lambda user: sum(1 for case in user.scav_cases if case.type == "Intelligence") > 50,
    "Bitcoin Finder": lambda user: any(
        any(item.tarkov_item and item.tarkov_item.name == "Physical Bitcoin" for item in case.items)
        for case in user.scav_cases if case.items
    ),
    "Tech Scavenger": lambda user: any(
        any(item.tarkov_item and item.tarkov_item.name.lower() in {"graphics card", "tetriz portable game console"} 
            for item in case.items)
        for case in user.scav_cases if case.items
    ),
    "Weapon Collector": lambda user: len({
        item.tarkov_item.name for case in user.scav_cases if case.items
        for item in case.items if item.tarkov_item and item.tarkov_item.category.lower() == "guns"
    }) >= 10,
    "Keymaster": lambda user: sum(
        1 for case in user.scav_cases if case.items  # Ensure case has items
        for item in case.items 
        if item.tarkov_item and item.tarkov_item.category.lower() == "keys"
    ) >= 5,
    "Rare Loot Hunter": lambda user: any((case._return - case.cost) >= 1_000_000 for case in user.scav_cases),
    "Jackpot!": lambda user: any(
        sum(1 for item in case.items if item.tarkov_item.name == "Physical Bitcoin") >= 3
        for case in user.scav_cases
    ),
    "Nothing But Trash": lambda user: any((case._return - case.cost) <= 5000 for case in user.scav_cases),
    "Lone Survivor": lambda user: any(len(case.items) == 1 for case in user.scav_cases),
}

ACHIEVEMENT_METADATA = {
    "First Case": {"description": "Submit your first Scav Case", "icon": "first_case.png"},
    "Scav Veteran": {"description": "Submit 50 Scav Cases", "icon": "scav_veteran.png"},
    "Scav Elite": {"description": "Submit 100 Scav Cases", "icon": "scav_elite.png"},
    "Millionaire": {"description": "Earn 1,000,000 rubles total", "icon": "millionaire.png"},
    "Multi-Millionaire": {"description": "Earn 10,000,000 rubles total", "icon": "multi_millionaire.png"},
    "Hoarder": {"description": "Earn 100,000,000 rubles total", "icon": "hoarder.png"},
    "Moonshine Master": {"description": "Submit 10 Moonshine Scav Cases", "icon": "moonshine_master.png"},
    "Intelligence Operator": {"description": "Submit 10 Intelligence Scav Cases", "icon": "intelligence_operator.png"},
    "Moonshine Tycoon": {"description": "Submit 50 Moonshine Scav Cases", "icon": "moonshine_tycoon.png"},
    "Intel Mogul": {"description": "Submit 50 Intelligence Scav Cases", "icon": "intel_mogul.png"},
    "Bitcoin Finder": {"description": "Find at least 1 Bitcoin in a Scav Case", "icon": "bitcoin_finder.png"},
    "Tech Scavenger": {"description": "Find a Graphics Card or Tetriz in a Scav Case", "icon": "tech_scavenger.png"},
    "Weapon Collector": {"description": "Find 10 different weapons in Scav Cases", "icon": "weapon_collector.png"},
    "Keymaster": {"description": "Find 5 different keys in Scav Cases", "icon": "keymaster.png"},
    "Rare Loot Hunter": {"description": "Find an item worth 1,000,000+ rubles", "icon": "rare_loot_hunter.png"},
    "Jackpot!": {"description": "Find 3+ Bitcoins in a single Scav Case", "icon": "jackpot.png"},
    "Nothing But Trash": {"description": "Get an entry worth less than 5,000 rubles", "icon": "nothing_but_trash.png"},
    "Lone Survivor": {"description": "Have only one item in a Scav Case", "icon": "lone_survivor.png"},
}

LEADERBOARD_METRICS = {
    "total_profit": {
        "title": "Top profits",
        "desc": "Sum of profit across all cases",
        "column": "total_profit",
    },
    "case_count": {
        "title": "Most cases",
        "desc": "Total number of scav cases opened",
        "column": "case_count",
    },
    "avg_profit": {
        "title": "Highest average profit",
        "desc": "Average profit per case",
        "column": "avg_profit",
    },
    "most_expensive_item": {
        "title": "Most expensive item",
        "desc": "Highest single item value found",
        "column": "most_expensive_item",
    },
}
