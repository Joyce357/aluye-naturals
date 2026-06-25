from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ROOT / "Aluye Naturals Images"
HERO = ROOT / "Aluye Naturals Hero"
STATIC_IMAGES = ROOT / "static" / "images"


def save_webp(source: Path, destination: Path, max_width: int, quality: int = 80):
    with Image.open(source) as image:
        image = image.convert("RGB")
        if image.width > max_width:
            height = round(image.height * max_width / image.width)
            image = image.resize((max_width, height), Image.Resampling.LANCZOS)
        image.save(destination, "WEBP", quality=quality, method=6)


def main():
    product_files = [
        "photo_10_2026-06-08_18-19-49.jpg",
        "photo_1_2026-06-08_18-19-49.jpg",
        "photo_2026-06-09_11-04-04.jpg",
        "photo_2_2026-06-08_18-19-49.jpg",
        "photo_3_2026-06-05_22-40-06.jpg",
        "photo_4_2026-06-05_22-40-06.jpg",
        "photo_5_2026-06-05_22-40-06.jpg",
        "photo_6_2026-06-08_18-19-49.jpg",
        "photo_7_2026-06-08_18-19-49.jpg",
        "photo_8_2026-06-08_18-19-49.jpg",
        "photo_9_2026-06-08_18-19-49.jpg",
        "photo_2026-06-09_09-50-13.jpg",
        "photo_2026-06-09_09-50-19.jpg",
        "photo_2026-06-09_11-04-11.jpg",
        "photo_2026-06-09_11-04-16.jpg",
    ]
    for filename in product_files:
        source = PRODUCTS / filename
        save_webp(source, source.with_suffix(".webp"), max_width=640, quality=82)

    hero_files = {
        "ChatGPT Image Jun 15, 2026, 09_13_54 PM.png": "aluye-beard-hero.webp",
        "ChatGPT Image Jun 15, 2026, 09_23_15 PM (1).png": "aluye-cleanser-hero.webp",
        "ChatGPT Image Jun 15, 2026, 09_23_16 PM (2).png": "aluye-chlorophyll-hero.webp",
        "ChatGPT Image Jun 15, 2026, 09_23_17 PM (3).png": "aluye-oil-hero.webp",
        "ChatGPT Image Jun 15, 2026, 09_23_17 PM (4).png": "aluye-ritual-hero.webp",
    }
    for source, destination in hero_files.items():
        save_webp(HERO / source, HERO / destination, 1600, 80)

    STATIC_IMAGES.mkdir(parents=True, exist_ok=True)
    with Image.open(PRODUCTS / "Aluye Naturals Logo.jpg") as logo:
        logo = logo.convert("RGB")
        symbol = logo.crop((460, 40, 820, 400)).resize((192, 192), Image.Resampling.LANCZOS)
        symbol.save(STATIC_IMAGES / "favicon.png", "PNG", optimize=True)


if __name__ == "__main__":
    main()
