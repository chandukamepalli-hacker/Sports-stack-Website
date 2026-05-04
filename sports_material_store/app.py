import base64
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, instance_relative_config=True)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "local-dev-change-this-secret-key"),
    DATABASE=str(BASE_DIR / "instance" / "sports_store.sqlite3"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    PRODUCT_UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads" / "products"),
)
Path(app.config["PRODUCT_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["700 per day", "180 per hour"],
    storage_uri="memory://",
)

SPORT_CATEGORIES = [
    "Cricket",
    "Football",
    "Badminton",
    "Basketball",
    "Tennis",
    "Gym",
    "Running",
    "Swimming",
    "Cycling",
    "Boxing",
    "Fitness",
    "Accessories",
]

PRODUCT_DUMP = [
    ("Pro Willow Cricket Bat", "Cricket", "Balanced English willow profile for powerful front-foot and back-foot shots.", 2499, 18, 4.8, ["Full size", "Anti-scuff sheet", "Light pickup"], "cricket bat sports equipment"),
    ("Tournament Leather Cricket Ball", "Cricket", "Four-piece stitched leather ball made for match practice and club games.", 429, 56, 4.6, ["156 g", "Hand stitched", "Red leather"], "cricket ball leather"),
    ("Cricket Batting Gloves Pro", "Cricket", "Padded batting gloves with split fingers and sweat-wicking lining.", 1299, 34, 4.5, ["Split finger", "Palm grip", "Right hand"], "cricket batting gloves"),
    ("Cricket Leg Guard Pads", "Cricket", "Lightweight leg pads with cane reinforcement and soft knee roll.", 1799, 22, 4.4, ["Adult size", "Triple strap", "Lightweight"], "cricket pads leg guard"),
    ("Cricket Helmet Steel Grill", "Cricket", "Protective cricket helmet with adjustable steel face grill and inner padding.", 2199, 16, 4.7, ["Steel grill", "Adjustable", "Ventilated"], "cricket helmet grill"),
    ("Cricket Wicket Stumps Set", "Cricket", "Match-practice wooden stumps with bails for turf and matting wickets.", 699, 50, 4.3, ["3 stumps", "2 bails", "Wooden"], "cricket stumps bails"),
    ("FIFA-Style Match Football", "Football", "Durable PU football with stable flight and high-grip panel texture.", 899, 32, 4.7, ["Size 5", "PU outer", "Butyl bladder"], "football soccer ball"),
    ("Football Shin Guard Pair", "Football", "Impact-resistant shin guards with breathable ankle support straps.", 349, 44, 4.4, ["Pair pack", "Adjustable strap", "Lightweight shell"], "football shin guard"),
    ("Goalkeeper Gloves Grip Pro", "Football", "Latex palm goalkeeper gloves with wrist support and confident catch grip.", 799, 24, 4.6, ["Latex palm", "Wrist strap", "Training/match"], "goalkeeper gloves football"),
    ("Football Training Cone Set", "Football", "Bright marker cones for dribbling, agility, warm-up, and academy drills.", 299, 80, 4.2, ["20 cones", "Flexible", "High visibility"], "football training cones"),
    ("Football Studs Firm Ground", "Football", "Firm-ground football boots with molded studs and ankle support.", 2499, 19, 4.6, ["FG studs", "Synthetic upper", "Grip sole"], "football boots studs"),
    ("Portable Football Goal Net", "Football", "Foldable mini goal net for backyard and academy training sessions.", 1999, 12, 4.5, ["Foldable", "Weather resistant", "Quick setup"], "portable football goal net"),
    ("Carbon Badminton Racket", "Badminton", "Fast swing racket with medium flex shaft for attacking and defensive play.", 1299, 25, 4.7, ["85 g", "Carbon frame", "Pre-strung"], "badminton racket carbon"),
    ("Feather Shuttlecock Tube", "Badminton", "Pack of 12 feather shuttles tuned for consistent speed and flight.", 699, 39, 4.5, ["12 pieces", "Feather skirt", "Speed 77"], "badminton shuttlecock tube"),
    ("Badminton Net Tournament", "Badminton", "Full-width nylon badminton net with reinforced top tape.", 899, 18, 4.4, ["Tournament width", "Nylon", "Carry pouch"], "badminton net"),
    ("Badminton Grip Tape Pack", "Badminton", "Anti-slip racket grip tape for sweat control and stronger handling.", 199, 90, 4.3, ["3 grips", "Tacky feel", "Sweat resistant"], "badminton grip tape"),
    ("Badminton Shoes Court Grip", "Badminton", "Non-marking badminton shoes with side stability and court grip.", 2299, 21, 4.6, ["Non-marking", "Cushioned", "Court sole"], "badminton shoes"),
    ("Badminton Racket Kit Bag", "Badminton", "Multi-compartment bag for rackets, shoes, shuttles, and towel.", 1199, 27, 4.4, ["2 racket slots", "Shoe pocket", "Shoulder strap"], "badminton racket bag"),
    ("Official Size Basketball", "Basketball", "Indoor and outdoor basketball with deep channels for improved control.", 1099, 21, 4.6, ["Size 7", "Rubber grip", "Indoor/outdoor"], "basketball ball"),
    ("Portable Basketball Pump", "Basketball", "Compact hand pump with needle storage for balls used across sports.", 249, 67, 4.3, ["Needle included", "Dual action", "Pocket size"], "basketball pump"),
    ("Basketball Hoop Ring Net", "Basketball", "Wall-mount hoop ring with nylon net for practice courts.", 1899, 15, 4.4, ["18 inch ring", "Wall mount", "Net included"], "basketball hoop net"),
    ("Basketball Arm Sleeve Pair", "Basketball", "Compression arm sleeves for support, warmth, and court comfort.", 399, 46, 4.2, ["Pair", "Compression", "Breathable"], "basketball arm sleeve"),
    ("Basketball Shoes High Ankle", "Basketball", "High-ankle basketball shoes with impact cushioning and lateral support.", 3499, 14, 4.7, ["High ankle", "Cushioned", "Court grip"], "basketball shoes"),
    ("Basketball Scoreboard Flip", "Basketball", "Portable flip scoreboard for local matches and coaching sessions.", 799, 23, 4.1, ["Manual flip", "Portable", "Multi-sport"], "basketball scoreboard"),
    ("Aluminium Tennis Racket", "Tennis", "Beginner-friendly racket with stable frame and comfortable grip.", 1599, 16, 4.5, ["27 inch", "Pre-strung", "Grip size G3"], "tennis racket"),
    ("Pressurized Tennis Ball Can", "Tennis", "Three pressurized balls for training, club games, and match warmups.", 379, 48, 4.4, ["3 balls", "Pressurized", "High bounce"], "tennis balls can"),
    ("Tennis Net Portable", "Tennis", "Portable tennis net suitable for beginner courts and multi-sport practice.", 2499, 11, 4.3, ["Portable", "Adjustable", "Carry bag"], "tennis net portable"),
    ("Tennis Wrist Band Pack", "Tennis", "Absorbent wrist bands for grip comfort during long rallies.", 249, 65, 4.2, ["Pair pack", "Cotton blend", "Sweat absorbent"], "tennis wrist band"),
    ("Tennis Vibration Dampener", "Tennis", "Soft dampener to reduce string vibration and improve feel.", 149, 100, 4.1, ["2 pieces", "Silicone", "Easy fit"], "tennis vibration dampener"),
    ("Tennis Racket Cover Bag", "Tennis", "Protective racket cover with zip closure and shoulder strap.", 499, 35, 4.2, ["Zip cover", "Padded", "Shoulder strap"], "tennis racket cover"),
    ("Adjustable Dumbbell Set", "Gym", "Space-saving dumbbell set for strength training at home or academy gyms.", 3199, 12, 4.8, ["20 kg set", "Spin locks", "Chrome plates"], "adjustable dumbbells gym"),
    ("Cast Iron Kettlebell", "Gym", "Compact kettlebell for swings, squats, presses, and functional training.", 1599, 24, 4.6, ["8 kg", "Cast iron", "Flat base"], "kettlebell gym"),
    ("Olympic Weight Plate Pair", "Gym", "Rubber-coated plates for barbell strength training and gym setups.", 2599, 18, 4.7, ["10 kg pair", "Rubber coated", "Olympic hole"], "gym weight plates"),
    ("Resistance Band Set", "Gym", "Multi-level resistance bands for mobility, rehab, and strength exercises.", 799, 60, 4.5, ["5 bands", "Door anchor", "Carry pouch"], "resistance bands fitness"),
    ("Push Up Board System", "Gym", "Color-coded push-up board for chest, shoulder, triceps, and back targeting.", 999, 29, 4.4, ["Foldable", "Color zones", "Anti-slip"], "push up board gym"),
    ("Weightlifting Gloves", "Gym", "Padded training gloves with wrist support and anti-slip palm.", 499, 55, 4.3, ["Wrist wrap", "Palm pad", "Breathable"], "weightlifting gloves gym"),
    ("Running Shoes Cushion Trainer", "Running", "Lightweight trainer with breathable mesh and impact cushioning.", 2299, 20, 4.7, ["Mesh upper", "EVA sole", "Road running"], "running shoes"),
    ("Running Waist Belt", "Running", "Slim running belt for phone, keys, energy gels, and cards.", 349, 52, 4.2, ["Phone pocket", "Reflective", "Adjustable"], "running waist belt"),
    ("Running Hydration Vest", "Running", "Lightweight hydration vest for long runs and trail workouts.", 1799, 17, 4.5, ["Bottle pockets", "Reflective", "Breathable mesh"], "running hydration vest"),
    ("Running Knee Support", "Running", "Compression knee support for running, workouts, and recovery.", 399, 64, 4.3, ["Compression", "Stretch fit", "Single piece"], "running knee support"),
    ("Sports Stopwatch Digital", "Running", "Digital stopwatch for sprint timing, drills, and coaching practice.", 299, 70, 4.1, ["Lap timer", "Lightweight", "Lanyard"], "sports stopwatch"),
    ("Reflective Running Jacket", "Running", "Lightweight reflective jacket for early morning and night runs.", 1499, 23, 4.4, ["Reflective", "Wind resistant", "Zip pockets"], "reflective running jacket"),
    ("Anti-Slip Yoga Mat", "Fitness", "Comfort mat with textured grip for yoga, stretching, and floor workouts.", 749, 41, 4.6, ["6 mm", "Carry strap", "Sweat resistant"], "yoga mat fitness"),
    ("Skipping Rope Speed Cable", "Fitness", "Fast-rotation rope for cardio, boxing drills, and warm-up routines.", 299, 64, 4.4, ["Adjustable", "Steel cable", "Foam handles"], "skipping rope fitness"),
    ("Foam Roller Recovery", "Fitness", "Textured foam roller for muscle recovery, mobility, and warm-ups.", 899, 33, 4.5, ["Textured", "High density", "Recovery"], "foam roller fitness"),
    ("Balance Board Trainer", "Fitness", "Core balance trainer for stability workouts and injury prevention.", 1299, 20, 4.3, ["Wood deck", "Anti-slip", "Core training"], "balance board fitness"),
    ("Pilates Ring Circle", "Fitness", "Flexible pilates ring for toning arms, thighs, and core muscles.", 599, 38, 4.2, ["Dual handles", "Lightweight", "Home workout"], "pilates ring fitness"),
    ("Agility Ladder Training", "Fitness", "Speed and agility ladder for footwork, warmups, and team training.", 649, 47, 4.4, ["12 rungs", "Carry bag", "Adjustable spacing"], "agility ladder training"),
    ("Swimming Goggles Anti Fog", "Swimming", "Anti-fog swimming goggles with adjustable straps and UV protection.", 699, 37, 4.5, ["Anti-fog", "UV protection", "Adjustable"], "swimming goggles"),
    ("Silicone Swim Cap", "Swimming", "Stretch silicone swim cap for pool training and hair protection.", 249, 85, 4.2, ["Silicone", "Stretch fit", "Reusable"], "swimming cap"),
    ("Swimming Kickboard", "Swimming", "Buoyant kickboard for stroke practice and lower-body swim drills.", 799, 28, 4.4, ["EVA foam", "Lightweight", "Training"], "swimming kickboard"),
    ("Swimming Pull Buoy", "Swimming", "Ergonomic pull buoy for upper-body stroke isolation drills.", 649, 30, 4.3, ["EVA foam", "Ergonomic", "Training"], "swimming pull buoy"),
    ("Cycling Helmet Aero", "Cycling", "Ventilated cycling helmet with adjustable dial fit and lightweight shell.", 1799, 25, 4.6, ["Dial fit", "Vented", "Lightweight"], "cycling helmet"),
    ("Cycling Gloves Padded", "Cycling", "Half-finger gloves with palm padding for road and MTB rides.", 449, 58, 4.3, ["Padded palm", "Half finger", "Grip tabs"], "cycling gloves"),
    ("Bike Bottle Cage", "Cycling", "Lightweight bottle cage for road bikes, hybrids, and MTB frames.", 299, 72, 4.1, ["Universal fit", "Lightweight", "Screws included"], "bike bottle cage"),
    ("Cycling LED Light Set", "Cycling", "Front and rear USB rechargeable lights for safer rides.", 899, 43, 4.5, ["USB charge", "Front + rear", "Water resistant"], "cycling led lights"),
    ("Boxing Gloves Training", "Boxing", "Training boxing gloves with wrist support and shock-absorbing foam.", 1499, 26, 4.6, ["12 oz", "Wrist strap", "Foam padding"], "boxing gloves"),
    ("Boxing Hand Wraps", "Boxing", "Elastic hand wraps for knuckle and wrist support during boxing training.", 249, 96, 4.3, ["Pair", "Elastic", "Thumb loop"], "boxing hand wraps"),
    ("Punching Bag Heavy", "Boxing", "Heavy punching bag for boxing, kickboxing, and fitness workouts.", 3499, 10, 4.7, ["Filled", "Hanging chain", "Durable shell"], "punching bag boxing"),
    ("Mouth Guard Sports", "Boxing", "Moldable mouth guard for boxing, football, and contact training.", 199, 78, 4.1, ["Moldable", "Case included", "Multi-sport"], "sports mouth guard"),
    ("Sports Water Bottle Steel", "Accessories", "Insulated steel bottle for training sessions and match-day hydration.", 599, 73, 4.5, ["750 ml", "Leak proof", "Insulated"], "sports water bottle"),
    ("Sports Duffel Kit Bag", "Accessories", "Large duffel bag for shoes, jersey, towel, bottle, and training gear.", 1299, 31, 4.5, ["45 L", "Shoe pocket", "Shoulder strap"], "sports duffel bag"),
    ("Microfiber Sports Towel", "Accessories", "Quick-dry microfiber towel for gym, swimming, and court sessions.", 349, 88, 4.3, ["Quick dry", "Compact", "Soft touch"], "sports towel"),
    ("Whistle Coach Metal", "Accessories", "Loud metal whistle with lanyard for coaches and referees.", 149, 120, 4.1, ["Metal", "Lanyard", "High sound"], "sports whistle coach"),
    ("First Aid Sports Kit", "Accessories", "Compact first-aid kit for sports teams, schools, and training centers.", 799, 26, 4.4, ["Bandage", "Cold pack", "Carry case"], "sports first aid kit"),
    ("Sports Sunglasses UV", "Accessories", "UV-protection sunglasses for cycling, running, cricket, and outdoor sports.", 999, 34, 4.4, ["UV protection", "Lightweight", "Outdoor"], "sports sunglasses"),
]


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or secrets.token_hex(4)


def allowed_image_filename(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def is_valid_image_url(value: str) -> bool:
    if not value:
        return False
    if not value.startswith(("http://", "https://")):
        return False
    lowered = value.lower()
    return any(token in lowered for token in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", "image", "photo"])


def delete_uploaded_image(relative_path: str) -> None:
    if not relative_path or not relative_path.startswith("uploads/products/"):
        return
    try:
        (BASE_DIR / "static" / relative_path).unlink(missing_ok=True)
    except Exception:
        pass


def save_uploaded_product_image(file_storage, slug: str):
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None
    if not allowed_image_filename(file_storage.filename):
        raise ValueError("Only PNG, JPG, JPEG, WEBP, GIF, and SVG images are allowed.")
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    unique = f"{slug}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}.{ext}"
    out_dir = Path(app.config["PRODUCT_UPLOAD_FOLDER"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / unique
    file_storage.save(out_path)
    return f"uploads/products/{unique}"


def save_data_url_image(data_url: str, slug: str, label: str = "crop"):
    if not data_url:
        return None
    match = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", data_url, re.I | re.S)
    if not match:
        raise ValueError("Cropped image data is invalid.")
    ext = "jpg" if match.group(1).lower() in {"jpeg", "jpg"} else match.group(1).lower()
    raw = base64.b64decode(match.group(2), validate=True)
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("Cropped image is too large. Please choose a smaller image.")
    unique = f"{slug}-{label}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}.{ext}"
    out_dir = Path(app.config["PRODUCT_UPLOAD_FOLDER"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / unique
    out_path.write_bytes(raw)
    return f"uploads/products/{unique}"


def resolve_product_image(
    name: str,
    category: str,
    slug: str,
    current_image: str = "",
    uploaded_file=None,
    remote_image: str = "",
    cropped_image_data: str = "",
    use_remote_as_primary: bool = False,
):
    remote_image = (remote_image or "").strip()
    uploaded_path = None
    if cropped_image_data:
        uploaded_path = save_data_url_image(cropped_image_data, slug, "primary")
    elif uploaded_file and getattr(uploaded_file, "filename", ""):
        uploaded_path = save_uploaded_product_image(uploaded_file, slug)

    if uploaded_path:
        if current_image and current_image != uploaded_path:
            delete_uploaded_image(current_image)
        current_image = uploaded_path

    if remote_image and not is_valid_image_url(remote_image):
        raise ValueError("Please provide a valid direct image URL starting with http:// or https://")

    if use_remote_as_primary and remote_image:
        if current_image and current_image != remote_image:
            delete_uploaded_image(current_image)
        current_image = remote_image

    if not current_image:
        current_image = create_product_image(name, category, slug)
    return current_image, remote_image


def online_image_url(keywords: str, lock: int) -> str:
    # Optional internet backup. The storefront uses exact local SVG product
    # images first so product name/image mismatches cannot happen.
    parts = [p for p in re.split(r"[\s,]+", keywords.lower()) if p]
    query_path = ",".join(quote_plus(p) for p in parts[:5]) or "sports,equipment"
    return f"https://loremflickr.com/900/900/{query_path}?lock={lock}"


def svg_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def wrap_svg_text(value: str, max_chars: int = 22, max_lines: int = 3):
    words = str(value).split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max_chars - 1].rstrip() + "…"
    return lines


def product_icon_svg(name: str, category: str) -> str:
    n = name.lower()
    c = category.lower()
    ball = '<circle cx="450" cy="290" r="120" fill="#f59e0b" stroke="#111827" stroke-width="10"/><path d="M330 290 H570 M450 170 V410 M365 205 C450 255 450 325 365 375 M535 205 C450 255 450 325 535 375" stroke="#111827" stroke-width="8" fill="none"/>'
    racket = '<ellipse cx="450" cy="240" rx="112" ry="142" fill="none" stroke="#111827" stroke-width="14"/><path d="M370 150 C450 240 530 330 530 330 M530 150 C450 240 370 330 370 330 M340 240 H560" stroke="#60a5fa" stroke-width="7"/><rect x="423" y="375" width="54" height="150" rx="24" fill="#92400e"/>'
    shoe = '<path d="M275 345 C390 245 500 260 625 350 C650 390 595 420 500 420 H300 C250 420 245 375 275 345Z" fill="#f8fafc" stroke="#111827" stroke-width="8"/><path d="M335 302 C430 340 520 342 582 345" stroke="#ef4444" stroke-width="13" fill="none"/><path d="M340 425 H585" stroke="#60a5fa" stroke-width="16"/>'
    glove = '<path d="M320 215 C410 170 520 190 575 285 C600 330 565 395 500 407 L385 407 C330 404 300 355 310 315Z" fill="#0f172a"/><path d="M345 260 H560" stroke="#f59e0b" stroke-width="12"/><rect x="360" y="380" width="150" height="45" rx="18" fill="#334155"/>'
    net = '<rect x="270" y="190" width="360" height="190" fill="none" stroke="#111827" stroke-width="10"/><path d="M300 195 V380 M330 195 V380 M360 195 V380 M390 195 V380 M420 195 V380 M450 195 V380 M480 195 V380 M510 195 V380 M540 195 V380 M570 195 V380 M600 195 V380 M270 235 H630 M270 280 H630 M270 325 H630" stroke="#93c5fd" stroke-width="5"/>'
    if "cricket" in c:
        if "bat" in n:
            return '<g transform="translate(345 165) rotate(18)"><rect x="-28" y="-15" width="56" height="245" rx="21" fill="#d79b48" stroke="#8b5a2b" stroke-width="8"/><rect x="-16" y="210" width="32" height="145" rx="16" fill="#263238"/><rect x="-38" y="-42" width="76" height="54" rx="18" fill="#f1c27d" stroke="#8b5a2b" stroke-width="7"/></g>'
        if "ball" in n:
            return '<circle cx="450" cy="290" r="116" fill="#b91c1c" stroke="#7f1d1d" stroke-width="12"/><path d="M374 205 C455 245 499 324 525 397" fill="none" stroke="#fff7ed" stroke-width="9" stroke-dasharray="20 16"/><path d="M527 194 C457 244 409 318 385 397" fill="none" stroke="#fff7ed" stroke-width="9" stroke-dasharray="20 16"/>'
        if "helmet" in n:
            return '<path d="M310 300 C310 190 390 130 493 140 C590 150 640 218 632 315 L585 315 C545 252 392 252 350 315 Z" fill="#111827"/><path d="M350 315 H635" stroke="#f59e0b" stroke-width="13"/><path d="M365 340 H630 M378 372 H605 M402 404 H575" stroke="#d1d5db" stroke-width="9" stroke-linecap="round"/>'
        if "pad" in n or "guard" in n:
            return '<g transform="translate(360 145)"><rect x="0" y="0" width="95" height="300" rx="44" fill="#f8fafc" stroke="#1f2937" stroke-width="8"/><rect x="130" y="0" width="95" height="300" rx="44" fill="#f8fafc" stroke="#1f2937" stroke-width="8"/><path d="M20 75 H205 M18 160 H207 M20 245 H205" stroke="#f97316" stroke-width="13" stroke-linecap="round"/></g>'
        if "stump" in n or "wicket" in n:
            return '<g stroke="#92400e" stroke-width="18" stroke-linecap="round"><path d="M390 170 V430"/><path d="M450 170 V430"/><path d="M510 170 V430"/></g><g stroke="#fbbf24" stroke-width="13" stroke-linecap="round"><path d="M372 160 H470"/><path d="M430 158 H530"/></g>'
        return glove
    if "football" in c:
        if "shin" in n:
            return '<g transform="translate(340 150)"><path d="M30 10 C110 35 130 95 118 190 L96 335 C86 390 26 385 20 330 L6 180 C-3 85 2 35 30 10Z" fill="#e0f2fe" stroke="#0369a1" stroke-width="8"/><path d="M190 10 C270 35 290 95 278 190 L256 335 C246 390 186 385 180 330 L166 180 C157 85 162 35 190 10Z" fill="#dbeafe" stroke="#1d4ed8" stroke-width="8"/></g>'
        if "glove" in n or "goalkeeper" in n:
            return glove
        if "cone" in n:
            return '<g fill="#f97316" stroke="#9a3412" stroke-width="8"><path d="M430 150 L350 420 H550 Z"/><ellipse cx="450" cy="430" rx="140" ry="32" fill="#fb923c"/></g><path d="M385 295 H515" stroke="#fff7ed" stroke-width="18"/>'
        if "stud" in n or "boot" in n:
            return shoe
        if "goal" in n or "net" in n:
            return net
        return '<circle cx="450" cy="290" r="120" fill="#f8fafc" stroke="#111827" stroke-width="10"/><path d="M450 176 L520 230 L493 315 H407 L380 230 Z" fill="#111827"/><path d="M380 230 L310 255 M520 230 L590 255 M407 315 L355 390 M493 315 L545 390" stroke="#111827" stroke-width="9"/>'
    if "badminton" in c:
        if "shuttle" in n:
            return '<ellipse cx="450" cy="390" rx="58" ry="36" fill="#f8fafc" stroke="#111827" stroke-width="7"/><path d="M395 360 L330 155 M430 355 L405 145 M470 355 L495 145 M505 360 L570 155" stroke="#e5e7eb" stroke-width="22" stroke-linecap="round"/><path d="M330 155 C405 100 500 100 570 155" fill="none" stroke="#d1d5db" stroke-width="18"/>'
        if "net" in n:
            return net
        if "shoe" in n:
            return shoe
        if "bag" in n:
            return '<rect x="300" y="205" width="300" height="230" rx="36" fill="#1d4ed8"/><path d="M375 205 C385 140 515 140 525 205" fill="none" stroke="#0f172a" stroke-width="15"/><rect x="330" y="250" width="240" height="70" rx="18" fill="#93c5fd"/>'
        return racket
    if "basketball" in c:
        if "pump" in n:
            return '<rect x="380" y="150" width="95" height="300" rx="35" fill="#2563eb"/><rect x="350" y="125" width="155" height="45" rx="20" fill="#111827"/><path d="M475 300 C590 300 595 390 520 390" stroke="#111827" stroke-width="12" fill="none"/><circle cx="520" cy="390" r="20" fill="#f59e0b"/>'
        if "hoop" in n or "ring" in n or "net" in n:
            return '<rect x="315" y="130" width="270" height="170" rx="12" fill="#f8fafc" stroke="#111827" stroke-width="10"/><ellipse cx="450" cy="330" rx="110" ry="34" fill="none" stroke="#ea580c" stroke-width="14"/><path d="M360 340 L390 470 M410 345 L425 470 M450 348 V470 M490 345 L475 470 M540 340 L510 470" stroke="#e5e7eb" stroke-width="7"/>'
        if "shoe" in n:
            return shoe
        if "sleeve" in n:
            return '<path d="M350 180 C455 145 540 190 565 315 C588 430 485 460 400 405 C330 360 280 245 350 180Z" fill="#111827"/><path d="M358 217 C442 185 518 225 530 320" stroke="#f59e0b" stroke-width="15" fill="none"/>'
        if "scoreboard" in n:
            return '<rect x="285" y="180" width="330" height="220" rx="24" fill="#111827"/><rect x="320" y="225" width="110" height="115" rx="12" fill="#fbbf24"/><rect x="470" y="225" width="110" height="115" rx="12" fill="#fbbf24"/><text x="375" y="305" text-anchor="middle" font-size="62" font-weight="900" fill="#111827">21</text><text x="525" y="305" text-anchor="middle" font-size="62" font-weight="900" fill="#111827">18</text>'
        return ball
    if "tennis" in c:
        if "ball" in n:
            return '<circle cx="450" cy="290" r="118" fill="#bef264" stroke="#65a30d" stroke-width="10"/><path d="M350 210 C440 235 480 345 550 370 M550 210 C460 235 420 345 350 370" stroke="#f8fafc" stroke-width="11" fill="none"/>'
        if "net" in n:
            return net
        if "wrist" in n:
            return '<rect x="345" y="220" width="210" height="150" rx="55" fill="#f97316"/><rect x="385" y="245" width="130" height="100" rx="40" fill="#fff7ed"/>'
        if "dampener" in n:
            return '<circle cx="415" cy="290" r="70" fill="#111827"/><circle cx="485" cy="290" r="70" fill="#111827"/><circle cx="415" cy="290" r="28" fill="#f8fafc"/><circle cx="485" cy="290" r="28" fill="#f8fafc"/>'
        if "cover" in n or "bag" in n:
            return '<path d="M355 145 H545 C590 145 625 195 600 238 L515 420 C495 455 405 455 385 420 L300 238 C275 195 310 145 355 145Z" fill="#1d4ed8"/><path d="M350 185 H550" stroke="#f8fafc" stroke-width="12"/>'
        return racket
    if "gym" in c or "fitness" in c:
        if "dumbbell" in n:
            return '<g fill="#111827"><rect x="225" y="245" width="75" height="120" rx="20"/><rect x="600" y="245" width="75" height="120" rx="20"/><rect x="305" y="280" width="290" height="50" rx="25"/><rect x="310" y="225" width="50" height="160" rx="18"/><rect x="540" y="225" width="50" height="160" rx="18"/></g>'
        if "kettlebell" in n:
            return '<path d="M372 260 C372 170 528 170 528 260" fill="none" stroke="#111827" stroke-width="36"/><path d="M330 275 C330 420 570 420 570 275 C570 220 330 220 330 275Z" fill="#334155"/>'
        if "plate" in n:
            return '<circle cx="400" cy="290" r="105" fill="#111827"/><circle cx="500" cy="290" r="105" fill="#334155"/><circle cx="400" cy="290" r="38" fill="#e5e7eb"/><circle cx="500" cy="290" r="38" fill="#e5e7eb"/>'
        if "yoga" in n or "mat" in n:
            return '<rect x="275" y="260" width="350" height="155" rx="44" fill="#8b5cf6"/><path d="M325 260 C285 260 285 415 325 415" fill="none" stroke="#c4b5fd" stroke-width="25"/>'
        if "rope" in n:
            return '<path d="M320 215 C430 120 555 190 555 310 C555 445 330 435 345 300" fill="none" stroke="#111827" stroke-width="14"/><rect x="255" y="345" width="90" height="32" rx="16" fill="#f59e0b"/><rect x="555" y="345" width="90" height="32" rx="16" fill="#f59e0b"/>'
        if "roller" in n:
            return '<rect x="315" y="230" width="270" height="140" rx="70" fill="#06b6d4"/><ellipse cx="315" cy="300" rx="45" ry="70" fill="#67e8f9"/><ellipse cx="585" cy="300" rx="45" ry="70" fill="#0891b2"/>'
        if "medicine" in n:
            return '<circle cx="450" cy="290" r="120" fill="#111827"/><path d="M345 290 H555 M450 185 V395" stroke="#f59e0b" stroke-width="24"/>'
        return glove
    if "running" in c:
        if "belt" in n:
            return '<path d="M275 285 C350 210 545 210 625 285 C565 365 340 365 275 285Z" fill="#111827"/><rect x="385" y="255" width="130" height="70" rx="22" fill="#f59e0b"/>'
        if "hydration" in n or "vest" in n:
            return '<path d="M345 165 L430 185 L450 260 L470 185 L555 165 L605 430 H500 L450 335 L400 430 H295Z" fill="#0f172a"/><circle cx="395" cy="270" r="22" fill="#60a5fa"/><circle cx="505" cy="270" r="22" fill="#60a5fa"/>'
        if "knee" in n:
            return '<rect x="350" y="165" width="200" height="280" rx="70" fill="#111827"/><ellipse cx="450" cy="305" rx="75" ry="55" fill="#334155"/>'
        if "stopwatch" in n:
            return '<circle cx="450" cy="300" r="120" fill="#f8fafc" stroke="#111827" stroke-width="13"/><rect x="420" y="125" width="60" height="50" rx="14" fill="#111827"/><path d="M450 300 L450 220 M450 300 L515 330" stroke="#ef4444" stroke-width="12" stroke-linecap="round"/>'
        if "jacket" in n:
            return '<path d="M340 165 L450 205 L560 165 L630 425 H505 L450 330 L395 425 H270Z" fill="#f97316"/><path d="M355 225 L450 330 L545 225" stroke="#f8fafc" stroke-width="14" fill="none"/>'
        return shoe
    if "swimming" in c:
        if "goggle" in n:
            return '<path d="M305 270 C350 220 430 220 455 285 C430 355 340 355 305 270Z" fill="#93c5fd" stroke="#111827" stroke-width="9"/><path d="M445 285 C470 220 550 220 595 270 C560 355 470 355 445 285Z" fill="#93c5fd" stroke="#111827" stroke-width="9"/><path d="M455 285 H445" stroke="#111827" stroke-width="12"/>'
        if "cap" in n:
            return '<path d="M315 330 C310 220 380 150 465 155 C550 160 605 235 595 330 Z" fill="#0ea5e9"/><path d="M320 330 H590" stroke="#0369a1" stroke-width="18"/>'
        if "kickboard" in n:
            return '<rect x="330" y="180" width="240" height="250" rx="80" fill="#f59e0b"/><ellipse cx="450" cy="250" rx="60" ry="30" fill="#fff7ed"/>'
        return '<path d="M335 180 C430 215 455 330 425 450 C335 420 285 310 335 180Z" fill="#22c55e"/><path d="M565 180 C470 215 445 330 475 450 C565 420 615 310 565 180Z" fill="#16a34a"/>'
    if "cycling" in c:
        if "helmet" in n:
            return '<path d="M300 310 C315 190 410 135 520 160 C600 178 650 235 625 325 H560 C535 275 395 275 345 325Z" fill="#f8fafc" stroke="#111827" stroke-width="10"/><path d="M355 230 H585" stroke="#ef4444" stroke-width="15"/>'
        if "glove" in n:
            return glove
        if "light" in n:
            return '<rect x="320" y="240" width="110" height="110" rx="28" fill="#111827"/><rect x="470" y="240" width="110" height="110" rx="28" fill="#111827"/><circle cx="375" cy="295" r="35" fill="#fef08a"/><circle cx="525" cy="295" r="35" fill="#ef4444"/>'
        return '<rect x="390" y="160" width="120" height="300" rx="44" fill="#f8fafc" stroke="#111827" stroke-width="8"/><rect x="410" y="125" width="80" height="55" rx="18" fill="#111827"/><path d="M355 245 C360 390 540 390 545 245" fill="none" stroke="#f97316" stroke-width="13"/>'
    if "boxing" in c:
        if "wrap" in n:
            return '<path d="M330 305 C340 190 560 190 570 305 C570 420 330 420 330 305Z" fill="none" stroke="#ef4444" stroke-width="36"/><path d="M385 305 C395 245 505 245 515 305" fill="none" stroke="#fecaca" stroke-width="20"/>'
        if "bag" in n or "punching" in n:
            return '<rect x="365" y="150" width="170" height="330" rx="78" fill="#111827"/><path d="M450 110 V150" stroke="#94a3b8" stroke-width="13"/><path d="M385 240 H515 M385 335 H515" stroke="#ef4444" stroke-width="13"/>'
        if "mouth" in n:
            return '<path d="M330 275 C385 215 515 215 570 275 C545 365 355 365 330 275Z" fill="#f8fafc" stroke="#111827" stroke-width="10"/><path d="M360 280 C420 315 480 315 540 280" stroke="#60a5fa" stroke-width="12" fill="none"/>'
        return '<path d="M330 165 C440 125 540 185 560 285 C585 400 450 455 355 380 C300 335 285 220 330 165Z" fill="#dc2626"/><rect x="360" y="370" width="140" height="65" rx="22" fill="#991b1b"/>'
    if "bottle" in n:
        return '<rect x="385" y="150" width="130" height="315" rx="45" fill="#64748b"/><rect x="410" y="110" width="80" height="60" rx="20" fill="#111827"/><path d="M410 245 H490" stroke="#f59e0b" stroke-width="18"/>'
    if "bag" in n or "duffel" in n:
        return '<rect x="300" y="230" width="300" height="190" rx="48" fill="#0f172a"/><path d="M370 230 C385 165 515 165 530 230" fill="none" stroke="#f59e0b" stroke-width="18"/><rect x="350" y="285" width="200" height="65" rx="20" fill="#334155"/>'
    if "towel" in n:
        return '<rect x="315" y="210" width="270" height="220" rx="30" fill="#22c55e"/><path d="M350 250 H550 M350 300 H550 M350 350 H550" stroke="#dcfce7" stroke-width="12"/>'
    if "whistle" in n:
        return '<path d="M345 255 H560 C610 255 630 325 580 360 H390 C330 360 300 300 345 255Z" fill="#f59e0b" stroke="#111827" stroke-width="9"/><circle cx="390" cy="308" r="35" fill="#fff7ed"/>'
    if "first aid" in n:
        return '<rect x="310" y="190" width="280" height="230" rx="30" fill="#f8fafc" stroke="#111827" stroke-width="9"/><path d="M450 235 V375 M385 305 H515" stroke="#ef4444" stroke-width="34"/>'
    if "sunglass" in n:
        return '<path d="M300 265 C370 225 420 245 435 305 C405 360 320 355 300 265Z" fill="#111827"/><path d="M465 305 C480 245 530 225 600 265 C580 355 495 360 465 305Z" fill="#111827"/><path d="M435 305 H465" stroke="#111827" stroke-width="12"/>'
    return ball


def create_product_image(name: str, category: str, slug: str) -> str:
    slug = slugify(slug or name)
    out_dir = BASE_DIR / "static" / "images" / "products"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.svg"
    lines = wrap_svg_text(name)
    line_svg = "".join(
        f'<text x="450" y="{612 + i * 34}" text-anchor="middle" font-size="28" font-weight="900" fill="#111827">{svg_escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 900" role="img" aria-label="{svg_escape(name)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f8fafc"/><stop offset=".52" stop-color="#eff6ff"/><stop offset="1" stop-color="#fff7ed"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="24" stdDeviation="24" flood-color="#0f172a" flood-opacity="0.24"/></filter>
  </defs>
  <rect width="900" height="900" rx="72" fill="url(#bg)"/>
  <circle cx="740" cy="130" r="128" fill="#ffedd5" opacity="0.75"/>
  <circle cx="165" cy="745" r="140" fill="#dbeafe" opacity="0.8"/>
  <g filter="url(#shadow)">{product_icon_svg(name, category)}</g>
  <rect x="282" y="60" width="336" height="54" rx="27" fill="#111827" opacity="0.92"/>
  <text x="450" y="96" text-anchor="middle" font-size="25" font-weight="900" fill="#fbbf24">{svg_escape(category)}</text>
  <rect x="130" y="578" width="640" height="136" rx="34" fill="#ffffff" opacity="0.94"/>
  {line_svg}
  <text x="450" y="760" text-anchor="middle" font-size="21" font-weight="800" fill="#64748b">Exact verified sports product image</text>
</svg>"""
    out_path.write_text(svg, encoding="utf-8")
    return f"images/products/{slug}.svg"


def create_product_360_frame(name: str, category: str, slug: str, frame: int, total: int = 6) -> str:
    slug = slugify(slug or name)
    out_dir = BASE_DIR / "static" / "images" / "products" / "gallery"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}-360-{frame}.svg"
    angle = int(round((frame - 1) * (360 / total)))
    visual_shift = int((frame - (total + 1) / 2) * 10)
    scale_x = 1 - abs(frame - (total + 1) / 2) * 0.025
    lines = wrap_svg_text(name, max_chars=20, max_lines=2)
    line_svg = "".join(
        f'<text x="450" y="{640 + i * 32}" text-anchor="middle" font-size="26" font-weight="900" fill="#111827">{svg_escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 900" role="img" aria-label="{svg_escape(name)} 360 frame {frame}">
  <defs>
    <linearGradient id="bg360" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#eef2ff"/><stop offset=".45" stop-color="#ffffff"/><stop offset="1" stop-color="#fff7ed"/>
    </linearGradient>
    <filter id="shadow360" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="26" stdDeviation="24" flood-color="#0f172a" flood-opacity="0.26"/></filter>
  </defs>
  <rect width="900" height="900" rx="72" fill="url(#bg360)"/>
  <circle cx="{190 + visual_shift}" cy="170" r="96" fill="#fef3c7" opacity=".8"/>
  <circle cx="{720 - visual_shift}" cy="735" r="128" fill="#dbeafe" opacity=".82"/>
  <g filter="url(#shadow360)" transform="translate(450 300) scale({scale_x:.2f} 1) rotate({visual_shift * .4:.1f}) translate(-450 -300)">
    {product_icon_svg(name, category)}
  </g>
  <rect x="326" y="52" width="248" height="54" rx="27" fill="#111827" opacity="0.94"/>
  <text x="450" y="88" text-anchor="middle" font-size="23" font-weight="900" fill="#fbbf24">360° VIEW {angle}°</text>
  <rect x="146" y="606" width="608" height="112" rx="30" fill="#ffffff" opacity=".94"/>
  {line_svg}
  <text x="450" y="760" text-anchor="middle" font-size="20" font-weight="800" fill="#64748b">Product angle frame {frame} of {total}</text>
</svg>"""
    out_path.write_text(svg, encoding="utf-8")
    return f"images/products/gallery/{slug}-360-{frame}.svg"


def image_path_exists(relative_path: str) -> bool:
    if not relative_path or relative_path.startswith(("http://", "https://")):
        return True
    return (BASE_DIR / "static" / relative_path).exists()


def repair_product_images(db):
    """Repair only missing generated images. Do not overwrite uploaded/admin images."""
    rows = db.execute("SELECT * FROM products").fetchall()
    for row in rows:
        image = row["image"]
        if not image or image == "images/sports-fallback.svg" or (image.startswith("images/products/") and not image_path_exists(image)):
            image = create_product_image(row["name"], row["category"], row["slug"])
            db.execute("UPDATE products SET image=? WHERE id=?", (image, row["id"]))
        ensure_product_gallery(db, row["id"], row["name"], row["category"], row["slug"], image, row["remote_image"])
    db.commit()


def relative_image_to_src(value: str) -> str:
    if value and value.startswith(("http://", "https://")):
        return value
    if value:
        return url_for("static", filename=value)
    return url_for("static", filename="images/sports-fallback.svg")


def set_primary_gallery_image(db, product_id: int, image_path: str):
    if not image_path:
        return
    now = datetime.utcnow().isoformat(timespec="seconds")
    existing = db.execute("SELECT id FROM product_images WHERE product_id=? AND is_primary=1", (product_id,)).fetchone()
    if existing:
        db.execute("UPDATE product_images SET image=?, source='primary', sort_order=0 WHERE id=?", (image_path, existing["id"]))
    else:
        db.execute(
            "INSERT INTO product_images (product_id, image, source, sort_order, is_primary, created_at) VALUES (?, ?, 'primary', 0, 1, ?)",
            (product_id, image_path, now),
        )


def add_gallery_image(db, product_id: int, image_path: str, source: str = "upload", is_primary: int = 0):
    if not image_path:
        return
    now = datetime.utcnow().isoformat(timespec="seconds")
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM product_images WHERE product_id=?", (product_id,)).fetchone()["max_order"]
    if is_primary:
        db.execute("UPDATE product_images SET is_primary=0 WHERE product_id=?", (product_id,))
        sort_order = 0
    else:
        sort_order = int(max_order) + 1
    db.execute(
        "INSERT INTO product_images (product_id, image, source, sort_order, is_primary, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (product_id, image_path, source, sort_order, 1 if is_primary else 0, now),
    )


def ensure_product_gallery(db, product_id: int, name: str, category: str, slug: str, primary_image: str, remote_image: str = ""):
    count = db.execute("SELECT COUNT(*) AS c FROM product_images WHERE product_id=?", (product_id,)).fetchone()["c"]
    if count:
        set_primary_gallery_image(db, product_id, primary_image)
        return
    set_primary_gallery_image(db, product_id, primary_image)
    if remote_image and is_valid_image_url(remote_image) and remote_image != primary_image:
        add_gallery_image(db, product_id, remote_image, "remote", 0)
    for frame in range(1, 7):
        add_gallery_image(db, product_id, create_product_360_frame(name, category, slug, frame, 6), "360", 0)


def save_gallery_uploads(db, product_id: int, slug: str, uploaded_files):
    for file_storage in uploaded_files or []:
        if file_storage and getattr(file_storage, "filename", ""):
            add_gallery_image(db, product_id, save_uploaded_product_image(file_storage, slug), "upload", 0)


def get_product_gallery(product):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM product_images WHERE product_id=? ORDER BY is_primary DESC, sort_order ASC, id ASC",
        (product["id"],),
    ).fetchall()
    if not rows:
        ensure_product_gallery(db, product["id"], product["name"], product["category"], product["slug"], product["image"], product["remote_image"])
        db.commit()
        rows = db.execute(
            "SELECT * FROM product_images WHERE product_id=? ORDER BY is_primary DESC, sort_order ASC, id ASC",
            (product["id"],),
        ).fetchall()
    gallery = []
    seen = set()
    for row in rows:
        if row["image"] in seen:
            continue
        seen.add(row["image"])
        gallery.append({
            "id": row["id"],
            "image": row["image"],
            "url": relative_image_to_src(row["image"]),
            "source": row["source"],
            "is_primary": bool(row["is_primary"]),
        })
    if not gallery:
        gallery.append({"id": 0, "image": product["image"], "url": product_image_src(product), "source": "primary", "is_primary": True})
    return gallery



def get_db():
    if "db" not in g:
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def table_columns(db, table_name):
    try:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
    except sqlite3.Error:
        return set()


def ensure_column(db, table, column_name, definition):
    if column_name not in table_columns(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}")


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS dealers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price INTEGER NOT NULL CHECK(price >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            image TEXT NOT NULL DEFAULT 'images/sports-fallback.svg',
            remote_image TEXT NOT NULL DEFAULT '',
            rating REAL NOT NULL DEFAULT 4.5,
            specs TEXT NOT NULL DEFAULT '[]',
            dealer_id INTEGER,
            dealer_name TEXT NOT NULL DEFAULT 'SportStack Warehouse',
            created_at TEXT NOT NULL,
            FOREIGN KEY (dealer_id) REFERENCES dealers(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            image TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'upload',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            total INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
        CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);
        CREATE INDEX IF NOT EXISTS idx_products_dealer ON products(dealer_id);
        CREATE INDEX IF NOT EXISTS idx_product_images_product ON product_images(product_id);
        CREATE INDEX IF NOT EXISTS idx_dealers_email ON dealers(email);
        """
    )

    # Non-destructive migrations for old versions of this project.
    ensure_column(db, "products", "remote_image", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "products", "dealer_id", "INTEGER")
    ensure_column(db, "products", "dealer_name", "TEXT NOT NULL DEFAULT 'SportStack Warehouse'")
    ensure_column(db, "dealers", "status", "TEXT NOT NULL DEFAULT 'approved'")
    db.commit()

    now = datetime.utcnow().isoformat(timespec="seconds")
    for index, (name, category, description, price, stock, rating, specs, image_keywords) in enumerate(PRODUCT_DUMP, start=1001):
        slug = slugify(name)
        exists = db.execute("SELECT id, remote_image FROM products WHERE slug=? OR name=?", (slug, name)).fetchone()
        image_url = online_image_url(image_keywords, index)
        exact_image = create_product_image(name, category, slug)
        if exists:
            if not exists["remote_image"]:
                db.execute(
                    "UPDATE products SET image=?, remote_image=?, dealer_name=COALESCE(NULLIF(dealer_name, ''), 'SportStack Warehouse') WHERE id=?",
                    (exact_image, image_url, exists["id"]),
                )
            else:
                db.execute("UPDATE products SET image=? WHERE id=?", (exact_image, exists["id"]))
            continue
        db.execute(
            """
            INSERT INTO products
                (name, slug, category, description, price, stock, image, remote_image, rating, specs, dealer_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                slug,
                category,
                description,
                price,
                stock,
                exact_image,
                image_url,
                rating,
                json.dumps(specs),
                "SportStack Warehouse",
                now,
            ),
        )
    db.commit()
    repair_product_images(db)


with app.app_context():
    init_db()


@app.before_request
def ensure_csrf_token():
    session.permanent = False
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.context_processor
def inject_globals():
    return {
        "csrf_token": session.get("csrf_token", ""),
        "cart_count": get_cart_count(),
        "categories": get_categories(),
        "rupee": lambda amount: f"₹{int(amount):,}",
        "dealer_logged_in": bool(session.get("dealer_id")),
        "dealer_name": session.get("dealer_name", ""),
        "admin_logged_in": bool(session.get("admin_logged_in")),
        "image_src": product_image_src,
        "fallback_img": url_for("static", filename="images/sports-fallback.svg"),
    }


def csrf_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            if request.accept_mimetypes.accept_json or request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Security token expired. Refresh the page and try again."}), 403
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login as admin first.", "warning")
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)

    return wrapper


def dealer_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("dealer_id"):
            flash("Please login as dealer first.", "warning")
            return redirect(url_for("dealer_login"))
        return fn(*args, **kwargs)

    return wrapper


def product_image_src(row):
    image = row["image"] if "image" in row.keys() else "images/sports-fallback.svg"
    if image and image.startswith(("http://", "https://")):
        return image
    if image and image != "images/sports-fallback.svg":
        return url_for("static", filename=image)
    remote = row["remote_image"] if "remote_image" in row.keys() else ""
    if remote and remote.startswith(("http://", "https://")):
        return remote
    return url_for("static", filename="images/sports-fallback.svg")


def get_categories():
    db = get_db()
    rows = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    result = [row["category"] for row in rows]
    for category in SPORT_CATEGORIES:
        if category not in result:
            result.append(category)
    return sorted(result)


def get_cart():
    cart = session.get("cart")
    if not isinstance(cart, dict):
        cart = {}
        session["cart"] = cart
    return cart


def get_cart_count():
    return sum(int(qty) for qty in get_cart().values())


def get_cart_items():
    cart = get_cart()
    if not cart:
        return [], 0
    product_ids = []
    for pid in cart.keys():
        try:
            product_ids.append(int(pid))
        except (TypeError, ValueError):
            continue
    if not product_ids:
        session["cart"] = {}
        return [], 0
    placeholders = ",".join("?" for _ in product_ids)
    db = get_db()
    rows = db.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids).fetchall()
    products_by_id = {str(row["id"]): row for row in rows}
    items = []
    total = 0
    changed = False
    for pid, qty in list(cart.items()):
        product = products_by_id.get(str(pid))
        if product is None:
            cart.pop(str(pid), None)
            changed = True
            continue
        safe_qty = max(1, min(int(qty), int(product["stock"]))) if product["stock"] > 0 else 0
        if safe_qty == 0:
            cart.pop(str(pid), None)
            changed = True
            continue
        if safe_qty != int(qty):
            cart[str(pid)] = safe_qty
            changed = True
        line_total = safe_qty * int(product["price"])
        total += line_total
        items.append({"product": product, "qty": safe_qty, "line_total": line_total})
    if changed:
        session.modified = True
    return items, total


def get_product_context(limit=24):
    db = get_db()
    rows = db.execute(
        "SELECT name, category, price, stock, rating, dealer_name, description FROM products ORDER BY rating DESC, stock DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return "\n".join(
        f"- {row['name']} | {row['category']} | ₹{row['price']} | stock {row['stock']} | rating {row['rating']} | dealer {row['dealer_name']} | {row['description']}"
        for row in rows
    )


def local_chatbot_reply(user_message: str):
    text = user_message.lower()
    db = get_db()
    category_map = {
        "cricket": "Cricket",
        "bat": "Cricket",
        "football": "Football",
        "soccer": "Football",
        "badminton": "Badminton",
        "shuttle": "Badminton",
        "basketball": "Basketball",
        "tennis": "Tennis",
        "gym": "Gym",
        "dumbbell": "Gym",
        "running": "Running",
        "shoe": "Running",
        "swim": "Swimming",
        "cycling": "Cycling",
        "boxing": "Boxing",
        "fitness": "Fitness",
    }
    for keyword, category in category_map.items():
        if keyword in text:
            rows = db.execute(
                "SELECT name, price, stock, rating FROM products WHERE category=? ORDER BY rating DESC, stock DESC LIMIT 6",
                (category,),
            ).fetchall()
            if rows:
                picks = "; ".join([f"{r['name']} — ₹{r['price']}, {r['stock']} in stock, {r['rating']}★" for r in rows])
                return f"For {category}, strong picks are: {picks}."
    if any(word in text for word in ["cart", "checkout", "order"]):
        items, total = get_cart_items()
        if not items:
            return "Your cart is empty. Add sports materials from the product grid, then open the cart to place a no-payment demo order."
        names = ", ".join([f"{item['qty']} × {item['product']['name']}" for item in items])
        return f"Your cart has {names}. Current total is ₹{total}. This website has no payment gateway; checkout creates a demo sports order."
    if any(word in text for word in ["dealer", "seller", "register", "sell"]):
        return "Dealers can register from Dealer → Register, login, and add only sports-material products. The system blocks non-sports categories."
    return "I can help you choose sports materials, compare stock, check cart items, and suggest products for cricket, football, badminton, basketball, tennis, gym, running, swimming, cycling, boxing, fitness, and accessories."


def unique_slug(db, name, current_id=None):
    base = slugify(name)
    candidate = base
    counter = 2
    while True:
        if current_id:
            exists = db.execute("SELECT id FROM products WHERE slug=? AND id<>?", (candidate, current_id)).fetchone()
        else:
            exists = db.execute("SELECT id FROM products WHERE slug=?", (candidate,)).fetchone()
        if not exists:
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "featured")
    dealer = request.args.get("dealer", "").strip()

    clauses = []
    params = []
    if q:
        clauses.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ? OR LOWER(dealer_name) LIKE ?)")
        like = f"%{q.lower()}%"
        params.extend([like, like, like, like])
    if category:
        clauses.append("category = ?")
        params.append(category)
    if dealer:
        clauses.append("dealer_name = ?")
        params.append(dealer)

    order_by = {
        "price_low": "price ASC",
        "price_high": "price DESC",
        "stock": "stock DESC",
        "rating": "rating DESC",
        "newest": "id DESC",
        "name": "name ASC",
    }.get(sort, "rating DESC, stock DESC")

    sql = "SELECT * FROM products"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += f" ORDER BY {order_by}"

    db = get_db()
    products = db.execute(sql, params).fetchall()
    featured = db.execute("SELECT * FROM products ORDER BY rating DESC, stock DESC LIMIT 8").fetchall()
    dealers = db.execute("SELECT DISTINCT dealer_name FROM products WHERE dealer_name <> '' ORDER BY dealer_name LIMIT 20").fetchall()
    return render_template(
        "index.html",
        products=products,
        featured=featured,
        dealers=dealers,
        selected_category=category,
        selected_dealer=dealer,
        q=q,
        sort=sort,
    )


@app.route("/product/<slug>")
def product_page(slug):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE slug=?", (slug,)).fetchone()
    if not product:
        abort(404)
    related = db.execute(
        "SELECT * FROM products WHERE category=? AND id<>? ORDER BY rating DESC, stock DESC LIMIT 8",
        (product["category"], product["id"]),
    ).fetchall()
    gallery = get_product_gallery(product)
    return render_template("product_detail.html", product=product, specs=json.loads(product["specs"]), related=related, gallery=gallery, gallery_urls=[item["url"] for item in gallery])


@app.route("/api/product/<int:product_id>")
def product_detail(product_id):
    row = get_db().execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Product not found"}), 404
    return jsonify(
        {
            "ok": True,
            "product": {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
                "category": row["category"],
                "description": row["description"],
                "price": row["price"],
                "stock": row["stock"],
                "image": product_image_src(row),
                "rating": row["rating"],
                "dealer_name": row["dealer_name"],
                "specs": json.loads(row["specs"]),
                "gallery": [item["url"] for item in get_product_gallery(row)],
            },
        }
    )


@app.post("/cart/add")
@limiter.limit("60 per minute")
@csrf_required
def cart_add():
    try:
        product_id = int(request.form.get("product_id", "0"))
        qty = max(1, int(request.form.get("qty", "1")))
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid product quantity."}), 400

    product = get_db().execute("SELECT id, name, stock FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        return jsonify({"ok": False, "error": "Product not found."}), 404
    if product["stock"] <= 0:
        return jsonify({"ok": False, "error": f"{product['name']} is out of stock."}), 409

    cart = get_cart()
    current_qty = int(cart.get(str(product_id), 0))
    new_qty = min(current_qty + qty, int(product["stock"]))
    cart[str(product_id)] = new_qty
    session.modified = True
    return jsonify({"ok": True, "message": f"{product['name']} added to cart.", "cart_count": get_cart_count()})


@app.route("/cart")
def cart_view():
    items, total = get_cart_items()
    return render_template("cart.html", items=items, total=total)


@app.post("/cart/update")
@csrf_required
def cart_update():
    try:
        product_id = int(request.form.get("product_id", "0"))
        qty = int(request.form.get("qty", "1"))
    except ValueError:
        flash("Invalid quantity.", "danger")
        return redirect(url_for("cart_view"))

    cart = get_cart()
    product = get_db().execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        cart.pop(str(product_id), None)
    elif qty <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = min(qty, int(product["stock"]))
    session.modified = True
    flash("Cart updated.", "success")
    return redirect(url_for("cart_view"))


@app.post("/cart/remove")
@csrf_required
def cart_remove():
    product_id = request.form.get("product_id", "")
    get_cart().pop(str(product_id), None)
    session.modified = True
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart_view"))


@app.post("/checkout")
@limiter.limit("12 per hour")
@csrf_required
def checkout():
    items, total = get_cart_items()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart_view"))

    customer_name = request.form.get("customer_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    if not all([customer_name, email, phone, address]):
        flash("Please fill all checkout fields.", "danger")
        return redirect(url_for("cart_view"))

    db = get_db()
    refreshed_items, refreshed_total = get_cart_items()
    for item in refreshed_items:
        stock = db.execute("SELECT stock FROM products WHERE id=?", (item["product"]["id"],)).fetchone()["stock"]
        if item["qty"] > stock:
            flash(f"Not enough stock for {item['product']['name']}.", "danger")
            return redirect(url_for("cart_view"))

    order_items = []
    for item in refreshed_items:
        product = item["product"]
        cursor = db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (item["qty"], product["id"], item["qty"]),
        )
        if cursor.rowcount != 1:
            db.rollback()
            flash(f"Stock changed for {product['name']}. Please review cart.", "danger")
            return redirect(url_for("cart_view"))
        order_items.append(
            {
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "qty": item["qty"],
                "line_total": item["line_total"],
                "dealer_name": product["dealer_name"],
            }
        )

    cursor = db.execute(
        """
        INSERT INTO orders (customer_name, email, phone, address, total, items_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_name,
            email,
            phone,
            address,
            refreshed_total,
            json.dumps(order_items),
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    session["cart"] = {}
    session.modified = True
    return render_template("order_success.html", order_id=cursor.lastrowid, total=refreshed_total, items=order_items)


@app.post("/api/chat")
@limiter.limit("30 per minute")
@csrf_required
def api_chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:1000]
    if not message:
        return jsonify({"ok": False, "error": "Type a message first."}), 400

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return jsonify({"ok": True, "reply": local_chatbot_reply(message), "mode": "local-fallback"})

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    system_prompt = (
        "You are SportBot, a concise AI shopping assistant for SportStack, a local sports-material-only ecommerce website. "
        "Never recommend non-sports products. Help with stock, dealer products, cart guidance, and product comparisons. "
        "The store has no payment gateway; checkout creates a demo order only. Available products:\n"
        + get_product_context()
    )
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "SportStack Sports Marketplace",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.45,
                "max_tokens": 320,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        reply = payload["choices"][0]["message"]["content"].strip()
        return jsonify({"ok": True, "reply": reply, "mode": "openrouter"})
    except Exception:
        return jsonify({"ok": True, "reply": local_chatbot_reply(message), "mode": "local-fallback"})


@app.route("/dealer/register", methods=["GET", "POST"])
@limiter.limit("20 per hour")
def dealer_register():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if token != session.get("csrf_token"):
            abort(403)
        business_name = request.form.get("business_name", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        if not all([business_name, owner_name, email, phone, address, password]):
            flash("Please fill all dealer registration fields.", "danger")
            return render_template("dealer_register.html")
        if len(password) < 6:
            flash("Dealer password must be at least 6 characters.", "danger")
            return render_template("dealer_register.html")
        db = get_db()
        try:
            cursor = db.execute(
                """
                INSERT INTO dealers (business_name, owner_name, email, phone, address, password_hash, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'approved', ?)
                """,
                (business_name, owner_name, email, phone, address, generate_password_hash(password), datetime.utcnow().isoformat(timespec="seconds")),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("A dealer with this email already exists. Please login.", "warning")
            return redirect(url_for("dealer_login"))
        session["dealer_id"] = cursor.lastrowid
        session["dealer_name"] = business_name
        flash("Dealer registration successful. You can now add sports products.", "success")
        return redirect(url_for("dealer_dashboard"))
    return render_template("dealer_register.html")


@app.route("/dealer/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def dealer_login():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if token != session.get("csrf_token"):
            abort(403)
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        dealer = get_db().execute("SELECT * FROM dealers WHERE email=?", (email,)).fetchone()
        if dealer and check_password_hash(dealer["password_hash"], password):
            session["dealer_id"] = dealer["id"]
            session["dealer_name"] = dealer["business_name"]
            flash("Dealer login successful.", "success")
            return redirect(url_for("dealer_dashboard"))
        flash("Invalid dealer email or password.", "danger")
    return render_template("dealer_login.html")


@app.post("/dealer/logout")
@csrf_required
def dealer_logout():
    session.pop("dealer_id", None)
    session.pop("dealer_name", None)
    flash("Dealer logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dealer/dashboard")
@dealer_required
def dealer_dashboard():
    dealer_id = session.get("dealer_id")
    db = get_db()
    dealer = db.execute("SELECT * FROM dealers WHERE id=?", (dealer_id,)).fetchone()
    if not dealer:
        session.pop("dealer_id", None)
        session.pop("dealer_name", None)
        flash("Dealer account not found. Please login again.", "warning")
        return redirect(url_for("dealer_login"))
    products = db.execute("SELECT * FROM products WHERE dealer_id=? ORDER BY id DESC", (dealer_id,)).fetchall()
    product_galleries = {product["id"]: get_product_gallery(product) for product in products}
    return render_template("dealer_dashboard.html", dealer=dealer, products=products, categories=SPORT_CATEGORIES, product_galleries=product_galleries)


@app.post("/dealer/products/add")
@dealer_required
@csrf_required
@limiter.limit("30 per hour")
def dealer_add_product():
    db = get_db()
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    price_raw = request.form.get("price", "").strip()
    stock_raw = request.form.get("stock", "").strip()
    image_keywords = request.form.get("image_keywords", "").strip()
    remote_image = request.form.get("remote_image", "").strip()
    image_file = request.files.get("image_file")
    gallery_files = request.files.getlist("gallery_images")
    cropped_image_data = request.form.get("cropped_image_data", "").strip()
    use_remote_as_primary = request.form.get("use_remote_image") == "on"
    specs_raw = request.form.get("specs", "").strip()

    if category not in SPORT_CATEGORIES:
        flash("Only sports-material categories are allowed.", "danger")
        return redirect(url_for("dealer_dashboard"))
    if not all([name, category, description, price_raw, stock_raw]):
        flash("Please fill product name, category, description, price, and stock.", "danger")
        return redirect(url_for("dealer_dashboard"))
    try:
        price = max(1, int(price_raw))
        stock = max(0, int(stock_raw))
    except ValueError:
        flash("Price and stock must be valid numbers.", "danger")
        return redirect(url_for("dealer_dashboard"))

    slug = unique_slug(db, name)
    keywords = image_keywords or f"{category} {name} sports equipment"
    try:
        exact_image, remote_image = resolve_product_image(name, category, slug, uploaded_file=image_file, remote_image=remote_image, cropped_image_data=cropped_image_data, use_remote_as_primary=use_remote_as_primary)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("dealer_dashboard"))
    if not remote_image:
        remote_image = online_image_url(keywords, secrets.randbelow(80000) + 20000)
    specs = [item.strip() for item in re.split(r"[,\n]", specs_raw) if item.strip()][:8] or ["Dealer listed", "Sports material", category]
    dealer = db.execute("SELECT business_name FROM dealers WHERE id=?", (session["dealer_id"],)).fetchone()
    try:
        db.execute(
            """
            INSERT INTO products
                (name, slug, category, description, price, stock, image, remote_image, rating, specs, dealer_id, dealer_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                slug,
                category,
                description,
                price,
                stock,
                exact_image,
                remote_image,
                4.2,
                json.dumps(specs),
                session["dealer_id"],
                dealer["business_name"],
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        product_id = db.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone()["id"]
        set_primary_gallery_image(db, product_id, exact_image)
        if remote_image and remote_image != exact_image:
            add_gallery_image(db, product_id, remote_image, "remote", 0)
        save_gallery_uploads(db, product_id, slug, gallery_files)
        db.commit()
        flash("Dealer product added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("Product name already exists. Use a more specific product name.", "danger")
    return redirect(url_for("dealer_dashboard"))


@app.post("/dealer/products/<int:product_id>/stock")
@dealer_required
@csrf_required
def dealer_update_stock(product_id):
    try:
        stock = max(0, int(request.form.get("stock", "0")))
        price = max(1, int(request.form.get("price", "1")))
    except ValueError:
        flash("Invalid price or stock.", "danger")
        return redirect(url_for("dealer_dashboard"))
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=? AND dealer_id=?", (product_id, session["dealer_id"])).fetchone()
    if not product:
        flash("Product not found for your dealer account.", "danger")
        return redirect(url_for("dealer_dashboard"))
    remote_image = request.form.get("remote_image", "").strip() or product["remote_image"]
    image_file = request.files.get("image_file")
    gallery_files = request.files.getlist("gallery_images")
    cropped_image_data = request.form.get("cropped_image_data", "").strip()
    use_remote_as_primary = request.form.get("use_remote_image") == "on"
    try:
        image, remote_image = resolve_product_image(product["name"], product["category"], product["slug"], current_image=product["image"], uploaded_file=image_file, remote_image=remote_image, cropped_image_data=cropped_image_data, use_remote_as_primary=use_remote_as_primary)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("dealer_dashboard"))
    db.execute(
        "UPDATE products SET stock=?, price=?, image=?, remote_image=? WHERE id=? AND dealer_id=?",
        (stock, price, image, remote_image, product_id, session["dealer_id"]),
    )
    set_primary_gallery_image(db, product_id, image)
    if remote_image and remote_image != image:
        add_gallery_image(db, product_id, remote_image, "remote", 0)
    save_gallery_uploads(db, product_id, product["slug"], gallery_files)
    db.commit()
    flash("Product updated.", "success")
    return redirect(url_for("dealer_dashboard"))


@app.post("/dealer/products/<int:product_id>/delete")
@dealer_required
@csrf_required
def dealer_delete_product(product_id):
    cursor = get_db().execute("DELETE FROM products WHERE id=? AND dealer_id=?", (product_id, session["dealer_id"]))
    get_db().commit()
    if cursor.rowcount:
        get_cart().pop(str(product_id), None)
        session.modified = True
        flash("Product deleted from your dealer catalog.", "info")
    else:
        flash("Product not found for your dealer account.", "danger")
    return redirect(url_for("dealer_dashboard"))




@app.post("/dealer/products/<int:product_id>/gallery/<int:image_id>/primary")
@dealer_required
@csrf_required
def dealer_gallery_primary(product_id, image_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=? AND dealer_id=?", (product_id, session["dealer_id"])).fetchone()
    image_row = db.execute("SELECT * FROM product_images WHERE id=? AND product_id=?", (image_id, product_id)).fetchone()
    if not product or not image_row:
        flash("Gallery image not found for your product.", "danger")
        return redirect(url_for("dealer_dashboard"))
    db.execute("UPDATE product_images SET is_primary=0 WHERE product_id=?", (product_id,))
    db.execute("UPDATE product_images SET is_primary=1, sort_order=0 WHERE id=?", (image_id,))
    db.execute("UPDATE products SET image=? WHERE id=?", (image_row["image"], product_id))
    db.commit()
    flash("Primary image updated.", "success")
    return redirect(url_for("dealer_dashboard"))


@app.post("/dealer/products/<int:product_id>/gallery/<int:image_id>/delete")
@dealer_required
@csrf_required
def dealer_gallery_delete(product_id, image_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=? AND dealer_id=?", (product_id, session["dealer_id"])).fetchone()
    image_row = db.execute("SELECT * FROM product_images WHERE id=? AND product_id=?", (image_id, product_id)).fetchone()
    if not product or not image_row:
        flash("Gallery image not found for your product.", "danger")
        return redirect(url_for("dealer_dashboard"))
    if image_row["is_primary"]:
        flash("Primary image cannot be deleted. Set another image as primary first.", "warning")
        return redirect(url_for("dealer_dashboard"))
    db.execute("DELETE FROM product_images WHERE id=?", (image_id,))
    delete_uploaded_image(image_row["image"])
    db.commit()
    flash("Gallery image deleted.", "info")
    return redirect(url_for("dealer_dashboard"))


@app.post("/admin/products/<int:product_id>/gallery/<int:image_id>/primary")
@admin_required
@csrf_required
def admin_gallery_primary(product_id, image_id):
    db = get_db()
    image_row = db.execute("SELECT * FROM product_images WHERE id=? AND product_id=?", (image_id, product_id)).fetchone()
    if not image_row:
        flash("Gallery image not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    db.execute("UPDATE product_images SET is_primary=0 WHERE product_id=?", (product_id,))
    db.execute("UPDATE product_images SET is_primary=1, sort_order=0 WHERE id=?", (image_id,))
    db.execute("UPDATE products SET image=? WHERE id=?", (image_row["image"], product_id))
    db.commit()
    flash("Primary image updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<int:product_id>/gallery/<int:image_id>/delete")
@admin_required
@csrf_required
def admin_gallery_delete(product_id, image_id):
    db = get_db()
    image_row = db.execute("SELECT * FROM product_images WHERE id=? AND product_id=?", (image_id, product_id)).fetchone()
    if not image_row:
        flash("Gallery image not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    if image_row["is_primary"]:
        flash("Primary image cannot be deleted. Set another image as primary first.", "warning")
        return redirect(url_for("admin_dashboard"))
    db.execute("DELETE FROM product_images WHERE id=?", (image_id,))
    delete_uploaded_image(image_row["image"])
    db.commit()
    flash("Gallery image deleted.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def admin_login():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if token != session.get("csrf_token"):
            abort(403)
        password = request.form.get("password", "")
        expected = os.getenv("ADMIN_PASSWORD", "admin123")
        if secrets.compare_digest(password, expected):
            session["admin_logged_in"] = True
            flash("Admin login successful.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Wrong admin password.", "danger")
    return render_template("admin_login.html")


@app.post("/admin/logout")
@csrf_required
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY category, name").fetchall()
    dealers = db.execute("SELECT * FROM dealers ORDER BY id DESC").fetchall()
    orders = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 30").fetchall()
    product_galleries = {product["id"]: get_product_gallery(product) for product in products}
    return render_template("admin_dashboard.html", products=products, dealers=dealers, orders=orders, product_galleries=product_galleries)


@app.post("/admin/stock")
@admin_required
@csrf_required
def admin_update_stock():
    try:
        product_id = int(request.form.get("product_id", "0"))
        stock = max(0, int(request.form.get("stock", "0")))
        price = max(1, int(request.form.get("price", "1")))
    except ValueError:
        flash("Invalid stock or price value.", "danger")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    remote_image = request.form.get("remote_image", "").strip() or product["remote_image"]
    image_file = request.files.get("image_file")
    gallery_files = request.files.getlist("gallery_images")
    cropped_image_data = request.form.get("cropped_image_data", "").strip()
    use_remote_as_primary = request.form.get("use_remote_image") == "on"
    try:
        image, remote_image = resolve_product_image(product["name"], product["category"], product["slug"], current_image=product["image"], uploaded_file=image_file, remote_image=remote_image, cropped_image_data=cropped_image_data, use_remote_as_primary=use_remote_as_primary)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin_dashboard"))
    db.execute("UPDATE products SET stock=?, price=?, image=?, remote_image=? WHERE id=?", (stock, price, image, remote_image, product_id))
    set_primary_gallery_image(db, product_id, image)
    if remote_image and remote_image != image:
        add_gallery_image(db, product_id, remote_image, "remote", 0)
    save_gallery_uploads(db, product_id, product["slug"], gallery_files)
    db.commit()
    flash("Product price/stock/image/gallery updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/dealer/<int:dealer_id>/status")
@admin_required
@csrf_required
def admin_dealer_status(dealer_id):
    status = request.form.get("status", "approved").strip()
    if status not in {"approved", "paused"}:
        status = "approved"
    get_db().execute("UPDATE dealers SET status=? WHERE id=?", (status, dealer_id))
    get_db().commit()
    flash("Dealer status updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", title="Page not found", message="The page you requested does not exist."), 404


@app.errorhandler(429)
def rate_limited(_error):
    return render_template("error.html", title="Too many requests", message="Please slow down and try again."), 429


@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", title="Server error", message="Something went wrong. Check the terminal logs."), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
