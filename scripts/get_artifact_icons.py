import os
import requests
from urllib.parse import urljoin
import concurrent.futures

BASE_URL = "https://hellhades.com/wp-content/plugins/rsl-assets/assets/artifacts/"
PIECE_TYPES = ["Weapon", "Helmet", "Shield", "Gloves", "Chest", "Boots"]
ACCESSORY_TYPES = ["Ring", "Pendant", "Banner"]


def ensure_dir(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def download_image(url, save_path):
    """Download an image from URL and save it to path"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def download_set_icons(set_name, output_dir, is_accessory=False):
    """Download all icons for a specific set"""
    set_dir = os.path.join(output_dir, set_name)
    ensure_dir(set_dir)

    # Download set icon
    icon_url = urljoin(BASE_URL, f"icons/{set_name}.png")
    icon_path = os.path.join(set_dir, f"{set_name}_icon.png")
    if download_image(icon_url, icon_path):
        print(f"Downloaded {set_name} icon")

    # Download piece icons
    types = ACCESSORY_TYPES if is_accessory else PIECE_TYPES
    for piece in types:
        piece_url = urljoin(BASE_URL, f"{set_name}_{piece}.jpg")
        piece_path = os.path.join(set_dir, f"{set_name}_{piece}.jpg")
        if download_image(piece_url, piece_path):
            print(f"Downloaded {set_name} {piece}")


def main():
    # Regular artifact sets
    ARTIFACT_SETS = [
        "StoneSkin",
        "Supersonic",
        "Merciless",
        "Feral",
        "Stonecleaver",
        "Rebirth",
        "Speed",
        "Regeneration",
        "Savage",
        "Retaliation",
        "Reflex",
        "Cruel",
        "DivineSpeed",
        "Perception",
        "Guardian",
        "Lethal",
        "Bolster",
        "Defiant",
        "Impulse",
        "Zeal",
        "Slayer",
        "Pinpoint",
        "Accuracy",
        "Cursed",
        "Shield",
        "Relentless",
        "Stun",
        "Toxic",
        "Provoke",
        "Stalwart",
        "Immortal",
        "Resilience",
        "Untouchable",
        "Fatal",
        "Fortitude",
        "Protection",
        "Killstroke",
        "Righteous",
        "CriticalRate",
        "CritDamage",
        "Resistance",
        "Lifesteal",
        "Fury",
        "Immunity",
        "Curing",
        "DivineLife",
        "SwiftParry",
        "Deflection",
        "Bloodthirst",
        "Instinct",
        "Defense",
        "Frost",
        "Destroy",
        "Avenging",
        "DivineOffense",
        "DivineCriticalRate",
        "Affinitybreaker",
        "Frostbite",
        "Life",
        "Offense",
        "Daze",
        "Frenzy",
    ]

    # Accessory sets
    ACCESSORY_SETS = ["Refresh", "Reaction", "Revenge", "Bloodshield", "Cleansing"]

    output_dir = "artifact_icons"
    ensure_dir(output_dir)

    print("Starting download of artifact icons...")

    # Use ThreadPoolExecutor for parallel downloads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Download regular artifact sets
        futures = [
            executor.submit(download_set_icons, set_name, output_dir)
            for set_name in ARTIFACT_SETS
        ]
        # Download accessory sets
        futures.extend(
            [
                executor.submit(download_set_icons, set_name, output_dir, True)
                for set_name in ACCESSORY_SETS
            ]
        )

        # Wait for all downloads to complete
        concurrent.futures.wait(futures)

    print("Download complete!")


if __name__ == "__main__":
    main()
