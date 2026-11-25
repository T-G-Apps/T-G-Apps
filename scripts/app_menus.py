"""Put the three apps' main-menu screenshots on the homepage.

Input: a folder with the phone captures from each app's
integration_test/web_screenshots_test.dart run with --dart-define=ONLY=menu
(in T-G-Apps_Local_Code), pulled from the phone:
  <KEY>_menu_<LANG>.png    the main menu in each of the 9 languages
  <KEY>_menu_buttons.json  each game button's box, as fractions of the screen
(KEY is casino, house_of_cards or boneyard; subfolders are searched too).

Output:
  images/screens/<LANG>/<KEY>_menu.jpg  300 x 549, cropped like the other
                                        screenshots
  index.html: the <!-- app-menu:KEY --> marker in each app's first card
              becomes (or the menu already there is replaced by) the menu
              screenshot with a tappable area over each game's button that
              goes to that game's section.

Usage (from the website root):
  python scripts/app_menus.py PATH_TO_CAPTURES
"""
import json
import os
import re
import sys

from PIL import Image

LANGS = ["en", "es", "fr", "de", "pt_BR", "ja", "hi", "id", "vi"]

# Crop of a 1080-wide phone capture: drop the status bar, keep the app's
# screen down to the navigation bar. Taller than the game shots (549 high)
# so a long menu in Japanese or Hindi still fits, like the 587-high House
# of Cards shots.
CROP_TOP, CROP_H, OUT_W, OUT_H = 98, 2112, 300, 587

APPS = {
    "casino": ("T-G-Apps Casino", {
        "21 / Blackjack": "twenty-one",
        "Texas Hold'em": "texas-holdem",
        "7 Card Draw": "seven-card-draw",
        "7 Card Stud": "seven-card-stud",
        "5 Card Draw": "five-card-draw",
        "Baccarat": "baccarat",
        "Let It Ride": "let-it-ride",
        "Caribbean Stud": "caribbean-stud",
    }),
    "house_of_cards": ("T-G-Apps House of Cards", {
        "Hearts": "hearts",
        "Spades": "spades",
        "Euchre": "euchre",
        "Bridge": "bridge",
        "Rummy": "rummy",
        "Cribbage": "cribbage",
        "Pinochle": "pinochle",
        "Canasta": "canasta",
    }),
    "boneyard": ("T-G-Apps Boneyard", {
        "Dice Games": "dice",
        "Dominoes": "dominoes",
        "Mahjong": "mahjong",
    }),
}


def find(root, name):
    for folder, _, files in os.walk(root):
        if name in files:
            return os.path.join(folder, name)
    return None


def crop_box(im):
    w, h = im.size
    k = w / 1080
    return (0, round(CROP_TOP * k), w, round((CROP_TOP + CROP_H) * k))


def html_escape(s):
    return (s.replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def main(captures):
    site = os.getcwd()
    page = os.path.join(site, "index.html")
    t = open(page, encoding="utf-8", newline="").read()
    for key, (app_name, jumps) in APPS.items():
        # screenshots
        size = None
        for lang in LANGS:
            src = find(captures, f"{key}_menu_{lang}.png")
            if not src:
                sys.exit(f"missing {key}_menu_{lang}.png")
            im = Image.open(src).convert("RGB")
            size = im.size
            box = crop_box(im)
            out = im.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS)
            dest = os.path.join(site, "images", "screens", lang, f"{key}_menu.jpg")
            out.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
        # buttons: screen fractions -> percentages of the cropped image, per
        # language (a button's height changes with its language's text)
        boxes = json.load(open(find(captures, f"{key}_menu_buttons.json"),
                               encoding="utf-8"))
        w, h = size
        x0, y0, x1, y1 = crop_box(Image.new("RGB", size))
        buttons = []
        for label, section in jumps.items():
            per_lang = {}
            for lang in LANGS:
                box = boxes.get(lang, {}).get(label)
                if not box:
                    sys.exit(f"{key}: no {lang} box for {label!r}")
                l, tp, r, b = box
                top = (tp * h - y0) / (y1 - y0) * 100
                bottom = (b * h - y0) / (y1 - y0) * 100
                if top < 0 or bottom > 100:
                    print(f"warning: {key} {lang} {label!r} is cut off by "
                          f"the crop ({top:.1f}%-{bottom:.1f}%)")
                per_lang[lang] = [round(top, 2), round(bottom - top, 2),
                                  round(l * 100, 2), round((r - l) * 100, 2)]
            top, height, left, width = per_lang["en"]
            buttons.append(
                f'<button type="button" class="menu-option" data-jump="{section}" '
                f'aria-label="{html_escape(label)}" '
                f"data-boxes='{json.dumps(per_lang, separators=(',', ':'))}' "
                f'style="top: {top}%; height: {height}%; left: {left}%; '
                f'width: {width}%;"></button>')
        block = (
            f'<!-- app-menu:{key} -->\n'
            f'      <div class="shots app-menu">\n'
            f'        <figure>\n'
            f'          <div class="menu-map">\n'
            f'            <img loading="lazy" decoding="async" '
            f'src="images/screens/en/{key}_menu.jpg" data-shot="{key}_menu" '
            f'width="{OUT_W}" height="{OUT_H}" alt="{html_escape(app_name)} game menu">\n'
            + "".join(f"            {b}\n" for b in buttons) +
            f'          </div>\n'
            f'          <figcaption>Game menu</figcaption>\n'
            f'        </figure>\n'
            f'      </div>\n'
            f'      <p class="menu-tip">Tap a game on the menu to see it below.</p>\n'
            f'      <!-- /app-menu:{key} -->')
        pat = re.compile(r"<!-- app-menu:" + key + r" -->(.*?<!-- /app-menu:" + key + r" -->)?", re.S)
        assert pat.search(t), f"no marker for {key}"
        t = pat.sub(lambda _: block, t, count=1)
        print(f"{key}: {len(buttons)} buttons, capture {w}x{h}")
    open(page, "w", encoding="utf-8", newline="").write(t)


if __name__ == "__main__":
    main(sys.argv[1])
