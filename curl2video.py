#!/usr/bin/env python3
"""curl2video - download a video you can already play in your browser.

You paste the browser's "Copy as cURL" for the video's playlist (.m3u8) and
curl2video hands the same request (headers, cookies and links) to yt-dlp.
It does not break or work around any protection: it only reuses what your
browser already has. Videos protected with DRM are detected and skipped.

Run "curl2video --help" for usage. English and Spanish are supported.
"""
import glob
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

VERSION = "1.0"
CONF = os.path.join(os.path.expanduser("~"), ".config", "curl2video.conf")
# Browser headers that make no sense to repeat from another program.
SKIP_HEADERS = {"host", "authority", "content-length", "connection", "accept-encoding",
                "range", "if-range", "if-none-match", "if-modified-since", "te",
                "upgrade", "keep-alive", "proxy-connection", "transfer-encoding"}
# Only used for the checks when the pasted request has no user-agent.
DEFAULT_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
DRM_RE = re.compile(r'#EXT-X-(?:SESSION-)?KEY:[^\n]*'
                    r'(?:METHOD=SAMPLE-AES|KEYFORMAT="(?!identity")|URI="skd://)', re.I)

# --------------------------------------------------------------------- texts

MSG = {
    "intro": {
        "en": "curl2video {version} - downloads a video using your browser's session.\n",
        "es": "curl2video {version} - baja un video usando la sesión de tu navegador.\n",
    },
    "no_ytdlp": {
        "en": "yt-dlp is not installed (or not in your PATH). The README explains how to install it.",
        "es": "No encuentro yt-dlp. En el README se explica cómo instalarlo.",
    },
    "no_ffmpeg": {
        "en": "Warning: ffmpeg is not installed. The download works, but the video may not play\n"
              "everywhere. The README explains how to install it.\n",
        "es": "Aviso: no encuentro ffmpeg. La descarga funciona, pero el video podría no verse\n"
              "en todos lados. En el README se explica cómo instalarlo.\n",
    },
    "steps": {
        "en": "How to copy the request:\n"
              "  1. Open the video page in your browser, press F12 and go to the Network tab.\n"
              "  2. Type m3u8 in the filter box and play the video.\n"
              "     If nothing shows up, reload the page (F5) and play it again.\n"
              "  3. Right-click the request that ends in .m3u8 -> Copy -> Copy as cURL.\n"
              "     On Windows, pick the \"(bash)\" or \"(POSIX)\" option.\n"
              "  4. Paste it here and press Enter. (In a Linux terminal, paste with Ctrl+Shift+V.)",
        "es": "Cómo copiar el pedido:\n"
              "  1. Abre la página del video en el navegador, presiona F12 y ve a la pestaña Network (Red).\n"
              "  2. Escribe m3u8 en el filtro y reproduce el video.\n"
              "     Si no aparece nada, recarga la página (F5) y vuelve a reproducirlo.\n"
              "  3. Clic derecho sobre el pedido que termina en .m3u8 -> Copy -> Copy as cURL.\n"
              "     En Windows, elige la opción \"(bash)\" o \"(POSIX)\".\n"
              "  4. Pégalo aquí y presiona Enter. (En la terminal de Linux se pega con Ctrl+Shift+V.)",
    },
    "bad_paste": {
        "en": "That doesn't look like a \"Copy as cURL\" or a link. Run curl2video again and paste it.",
        "es": "Eso no parece un \"Copy as cURL\" ni un link. Vuelve a ejecutar curl2video y pégalo.",
    },
    "received": {
        "en": "\nGot it: a request with {n} headers from your browser.",
        "es": "\nRecibido: un pedido con {n} datos de tu navegador.",
    },
    "expires_in": {
        "en": "The link says it expires at {when} (in {left}).",
        "es": "Según el link, vence a las {when} (faltan {left}).",
    },
    "expired": {
        "en": "Careful: the link says it expired {ago} ago. I'll try anyway.",
        "es": "Ojo: según el link, venció hace {ago}. Pruebo igual.",
    },
    "playlist_check": {
        "en": "Checking the playlist: {code}",
        "es": "Revisando la lista: {code}",
    },
    "playlist_info": {
        "en": "It has {n} pieces and lasts {dur}.",
        "es": "Tiene {n} pedacitos y dura {dur}.",
    },
    "drm": {
        "en": "This video is protected with DRM, so it can't be downloaded.\n"
              "curl2video doesn't work around DRM.",
        "es": "Este video tiene DRM (protección anticopia), así que no se puede bajar.\n"
              "curl2video no saltea el DRM.",
    },
    "piece_check": {
        "en": "Testing the first piece: {code}",
        "es": "Probando el primer pedacito: {code}",
    },
    "need_piece": {
        "en": "\nThe pieces need their own permission. Copy the request of one piece too:\n"
              "  right-click a request for a piece (it usually ends in .ts, .m4s, .aac or .mp4)\n"
              "  -> Copy -> Copy as cURL (or Copy URL). Paste it here and press Enter.",
        "es": "\nLos pedacitos necesitan su propio permiso. Copia también el pedido de un pedacito:\n"
              "  clic derecho sobre el pedido de un pedacito (suele terminar en .ts, .m4s, .aac o .mp4)\n"
              "  -> Copy -> Copy as cURL (o Copy URL). Pégalo aquí y presiona Enter.",
    },
    "piece_no_query": {
        "en": "That link has no permission data (nothing after the \"?\"), so it doesn't help.",
        "es": "Ese link no trae datos de permiso (nada después del \"?\"), así que no sirve.",
    },
    "rejected": {
        "en": "\nThe server rejected the request (code {code}). Usually:\n"
              " - the request expired: reload the page, play the video and copy it again;\n"
              " - or your browser goes out through a VPN or proxy and this terminal doesn't.",
        "es": "\nEl servidor rechazó el pedido (código {code}). Lo más común:\n"
              " - el pedido venció: recarga la página, reproduce el video y cópialo de nuevo;\n"
              " - o el navegador sale por una VPN o proxy y esta terminal no.",
    },
    "no_connection": {
        "en": "\nI couldn't reach the server. Check your internet connection and try again.",
        "es": "\nNo pude conectarme al servidor. Revisa tu conexión a internet y prueba de nuevo.",
    },
    "too_many": {
        "en": "\nThe server says there are too many requests (429).\n"
              "Pause the video in your browser, wait a minute and try again.",
        "es": "\nEl servidor dice que hay demasiados pedidos (429).\n"
              "Pausa el video en el navegador, espera un minuto y prueba de nuevo.",
    },
    "try_anyway": {
        "en": "Try to download it anyway? [y/N] ",
        "es": "¿Intento bajarlo igual? [s/N] ",
    },
    "not_hls": {
        "en": "This isn't an HLS playlist (.m3u8), so I'll hand it to yt-dlp as it is.",
        "es": "Esto no es una lista HLS (.m3u8), así que se lo paso a yt-dlp tal cual.",
    },
    "ask_name": {
        "en": "\nFile name (press Enter to use \"{default}\"): ",
        "es": "\nNombre del archivo (Enter para usar \"{default}\"): ",
    },
    "already": {
        "en": "You already have it: {path}",
        "es": "Ya lo tienes: {path}",
    },
    "downloading": {
        "en": "\nDownloading. Messages like \"Live HLS streams are not supported...\", an occasional\n"
              "\"429\" or \"Sleeping ... seconds\" are normal.\n",
        "es": "\nBajando. Mensajes como \"Live HLS streams are not supported...\", algún \"429\" suelto\n"
              "o \"Sleeping ... seconds\" son normales.\n",
    },
    "not_finished": {
        "en": "\nIt didn't finish. To continue where it stopped, run curl2video again, paste a freshly\n"
              "copied request of THE SAME video and use the same name: {name}",
        "es": "\nNo terminó. Para seguir desde donde quedó, ejecuta curl2video de nuevo, pega un pedido\n"
              "recién copiado de ESE MISMO video y usa el mismo nombre: {name}",
    },
    "failed": {
        "en": "\nIt couldn't be downloaded. The error above (from yt-dlp) says why.",
        "es": "\nNo se pudo bajar. El error de arriba (de yt-dlp) dice por qué.",
    },
    "done": {
        "en": "\nDone: {path} ({mb} MB)",
        "es": "\nListo: {path} ({mb} MB)",
    },
    "complete": {
        "en": "It lasts {dur}, same as the playlist: it's complete.",
        "es": "Dura {dur}, igual que la lista: está completo.",
    },
    "mismatch": {
        "en": "Note: the file lasts {real} but the playlist said {dur}.\n"
              "This can happen with recordings that have gaps. Open it and check that it plays to the end.",
        "es": "Aviso: el archivo dura {real} y la lista decía {dur}.\n"
              "Puede pasar en grabaciones con cortes. Ábrelo y fíjate que llegue hasta el final.",
    },
    "stopped": {"en": "\nStopped.", "es": "\nCortado."},
    "no_connection_short": {"en": "no connection", "es": "sin conexión"},
    "lang_saved": {
        "en": "Language saved: English. (Change it with: curl2video --lang es)\n",
        "es": "Idioma guardado: español. (Se cambia con: curl2video --lang en)\n",
    },
    "lang_bad": {
        "en": "Unknown language. Use --lang en or --lang es.",
        "es": "Idioma desconocido. Usa --lang es o --lang en.",
    },
    "days": {"en": "{n} days", "es": "{n} días"},
    "hours": {"en": "{h} h {m} min", "es": "{h} h {m} min"},
    "minutes": {"en": "{m} min", "es": "{m} min"},
    "help": {
        "en": "curl2video {version}\n"
              "Downloads a video you can already play in your browser, by pasting the\n"
              "browser's \"Copy as cURL\". It uses yt-dlp to do the download.\n\n"
              "Usage:\n"
              "  curl2video              start (it asks you to paste the request)\n"
              "  curl2video NAME         same, saving the video as NAME\n"
              "  curl2video --lang es    switch to Spanish (it's remembered)\n"
              "  curl2video --lang en    switch to English (it's remembered)\n"
              "  curl2video --help       show this help\n\n"
              "Settings file: {conf}\n"
              "  LANG=en or es   language\n"
              "  N=3             how many pieces to download at the same time",
        "es": "curl2video {version}\n"
              "Baja un video que ya puedes ver en tu navegador, pegando el \"Copy as cURL\"\n"
              "del navegador. Usa yt-dlp para hacer la descarga.\n\n"
              "Uso:\n"
              "  curl2video              empezar (te pide que pegues el pedido)\n"
              "  curl2video NOMBRE       lo mismo, guardando el video como NOMBRE\n"
              "  curl2video --lang es    pasar a español (queda guardado)\n"
              "  curl2video --lang en    pasar a inglés (queda guardado)\n"
              "  curl2video --help       mostrar esta ayuda\n\n"
              "Archivo de configuración: {conf}\n"
              "  LANG=es o en    idioma\n"
              "  N=3             cuántos pedacitos baja a la vez",
    },
}

LANG = "en"


def t(key, **values):
    return MSG[key][LANG].format(**values)


# ------------------------------------------------------------------ settings

def read_conf():
    conf = {}
    try:
        with open(CONF, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    conf[key.strip()] = value.strip()
    except OSError:
        pass
    return conf


def save_conf(conf):
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    with open(CONF, "w", encoding="utf-8") as f:
        f.write("# curl2video settings / configuración\n"
                "# LANG: en | es\n"
                f"LANG={conf.get('LANG', '')}\n"
                "# N: pieces downloaded at the same time / pedacitos que baja a la vez\n"
                f"N={conf.get('N', '3')}\n")


def detect_language(conf):
    if conf.get("LANG") in ("en", "es"):
        return conf["LANG"]
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "").split(":")[0].lower()
        if value and value not in ("c", "posix") and not value.startswith("c."):
            return "es" if value.startswith("es") else "en"
    try:
        import locale
        name = (locale.getlocale()[0] or "").lower()
        if name.startswith(("es", "spanish")):
            return "es"
    except (ValueError, TypeError, AttributeError):
        pass
    return "en"


# ------------------------------------------------------------ pasted request

def read_paste():
    """Reads what the user pastes. A "Copy as cURL" usually comes in several lines.
    Empty lines before the paste are ignored (a stray Enter shouldn't count as an answer)."""
    lines = []
    while True:
        try:
            line = input("> " if not lines else "").rstrip()
        except EOFError:
            break
        if not lines and not line.strip():
            continue
        lines.append(line)
        if not line.endswith("\\"):
            break
    return " ".join(l[:-1].strip() if l.endswith("\\") else l.strip() for l in lines)


def parse_request(text):
    """Gets the URL and the headers out of a "Copy as cURL" (or a plain link)."""
    text = text.strip()
    plain = text.strip("'\"")
    if re.fullmatch(r"https?://\S+", plain):
        return plain, []
    try:
        parts = shlex.split(text)
    except ValueError:
        return None, []

    def undollar(s):  # browsers sometimes write $'...'
        return s[1:] if s.startswith("$") else s

    takes_value = {"-X", "--request", "-d", "--data", "--data-raw", "--data-binary",
                   "--data-urlencode", "-o", "--output", "-w", "--write-out", "-u", "--user"}
    shortcuts = {"-b": "cookie", "--cookie": "cookie", "-A": "user-agent",
                 "--user-agent": "user-agent", "-e": "referer", "--referer": "referer"}
    url, headers, i = None, [], 0
    while i < len(parts):
        part = parts[i]
        nxt = parts[i + 1] if i + 1 < len(parts) else None
        if part in ("-H", "--header") and nxt is not None:
            name, colon, value = undollar(nxt).partition(":")
            if colon and name.strip():
                headers.append((name.strip(), value.strip()))
            i += 2
        elif part in shortcuts and nxt is not None:
            headers.append((shortcuts[part], undollar(nxt)))
            i += 2
        elif part in takes_value and nxt is not None:
            i += 2
        else:
            candidate = undollar(part)
            if url is None and re.match(r"https?://", candidate):
                url = candidate
            i += 1
    if not url:
        return None, []
    return url, [(n, v) for n, v in headers if n.lower() not in SKIP_HEADERS]


def header_value(headers, name):
    for n, v in headers:
        if n.lower() == name:
            return v
    return None


def merge_headers(base, extra):
    names = {n.lower() for n, _ in base}
    return base + [(n, v) for n, v in extra if n.lower() not in names]


# ------------------------------------------------------------------- network

def fetch(url, headers, limit=None):
    """Returns (HTTP code, body). Code 0 means no connection."""
    sent = dict(headers)
    if not header_value(headers, "user-agent"):
        sent["User-Agent"] = DEFAULT_UA
    request = urllib.request.Request(url, headers=sent)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, (response.read(limit) if limit else response.read())
    except urllib.error.HTTPError as err:
        return err.code, b""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b""


def probe(url, headers):
    """Tests one piece. If the server says "wait" (429), it waits and retries."""
    code = 0
    for attempt in range(4):
        code = fetch(url, headers, limit=65536)[0]
        if code != 429:
            break
        time.sleep(3 * (attempt + 1))
    return code


def inspect_playlist(url, headers):
    """Returns (code, info). info has drm, first, count and duration, or is None."""
    current, code = url, 0
    for _ in range(3):  # a master playlist points to another playlist
        code, body = fetch(current, headers)
        if code != 200:
            return code, None
        text = body.decode("utf-8", "replace")
        if "#EXTM3U" not in text:
            return code, None
        if DRM_RE.search(text):
            return code, {"drm": True}
        entries = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        if not entries:
            return code, None
        if "#EXTINF" in text:
            duration = sum(float(x) for x in re.findall(r"#EXTINF:\s*([0-9.]+)", text))
            return code, {"drm": False, "first": urljoin(current, entries[0]),
                          "count": len(entries), "duration": duration}
        current = urljoin(current, entries[0])
    return code, None


def with_query(url, query):
    """Adds a piece's permission data to a URL (the same way yt-dlp does)."""
    parts = urlsplit(url)
    merged = parse_qs(parts.query)
    merged.update(parse_qs(query))
    return urlunsplit(parts._replace(query=urlencode(merged, doseq=True)))


def write_cookie_file(url, cookie_header):
    """Saves the browser's cookies in a temporary file for yt-dlp (host only)."""
    host = urlsplit(url).hostname or ""
    secure = "TRUE" if url.lower().startswith("https") else "FALSE"
    fd, path = tempfile.mkstemp(prefix="curl2video-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for item in cookie_header.split(";"):
            name, equals, value = item.strip().partition("=")
            if equals and name:
                f.write(f"{host}\tFALSE\t/\t{secure}\t0\t{name}\t{value}\n")
    return path


# --------------------------------------------------------------------- utils

def clock(seconds):
    seconds = int(round(seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def span(seconds):
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    if hours >= 48:
        return t("days", n=hours // 24)
    return t("hours", h=hours, m=minutes) if hours else t("minutes", m=minutes)


def link_expiry(url):
    query = urlsplit(url).query
    for key, values in parse_qs(query).items():
        if key.lower() in ("expires", "exp", "expiry", "e"):
            for value in values:
                if re.fullmatch(r"\d{10}", value):
                    return int(value)
    match = re.search(r"(?i)\bexp(?:ires)?=(\d{10})\b", query)
    return int(match.group(1)) if match else None


def show_expiry(url):
    expiry = link_expiry(url)
    if not expiry:
        return
    left = expiry - time.time()
    if left <= 0:
        print(t("expired", ago=span(-left)))
    else:
        when = time.strftime("%H:%M %d/%m", time.localtime(expiry))
        print(t("expires_in", when=when, left=span(left)))


def default_name(url):
    folders = [p for p in urlsplit(url).path.split("/") if p]
    base = "_".join(folders[-3:-1]) if len(folders) >= 3 else ""
    base = re.sub(r"[^\w.-]+", "_", base).strip("._")
    if not base or len(base) > 80:
        base = "video_" + hashlib.sha1(urlsplit(url).path.encode()).hexdigest()[:8]
    return base


def clean_name(name):
    return re.sub(r'[\\/:*?"<>|%]+', "_", name).strip().strip(".")


def ask_yes(question):
    try:
        answer = input(question).strip().lower()
    except EOFError:
        return False
    return answer in (("y", "yes") if LANG == "en" else ("s", "si", "sí", "y", "yes"))


def media_duration(path):
    if not shutil.which("ffprobe"):
        return None
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def explain(code):
    if code == 0:
        print(t("no_connection"))
    elif code == 429:
        print(t("too_many"))
    else:
        print(t("rejected", code=code))


def code_text(code):
    return str(code) if code else t("no_connection_short")


# ---------------------------------------------------------------- download

def run_ytdlp(url, headers, piece_query, name, conf):
    pieces_at_once = conf.get("N", "3")
    if not pieces_at_once.isdigit() or int(pieces_at_once) < 1:
        pieces_at_once = "3"
    command = ["yt-dlp", "-N", pieces_at_once, "--abort-on-unavailable-fragments",
               "--retry-sleep", "fragment:exp=1:20", "-o", name + ".%(ext)s"]
    cookie_path = None
    for header, value in headers:
        if header.lower() == "cookie":
            cookie_path = cookie_path or write_cookie_file(url, value)
        else:
            command += ["--add-header", f"{header}:{value}"]
    if cookie_path:
        command += ["--cookies", cookie_path]
    if piece_query:
        command += ["--extractor-args", "generic:fragment_query=" + piece_query.replace(",", "\\,")]
    try:
        return subprocess.call(command + ["--", url])
    except KeyboardInterrupt:
        return 130
    finally:
        if cookie_path:
            try:
                os.unlink(cookie_path)
            except OSError:
                pass


def main(argv):
    global LANG
    conf = read_conf()
    args = list(argv)
    if "--lang" in args:
        i = args.index("--lang")
        choice = args[i + 1].lower() if i + 1 < len(args) else ""
        del args[i:i + 2]
        if choice not in ("en", "es"):
            LANG = detect_language(conf)
            print(t("lang_bad"))
            return 1
        conf["LANG"] = LANG = choice
        save_conf(conf)
        print(t("lang_saved"))
    else:
        LANG = detect_language(conf)
    if args and args[0] in ("-h", "--help", "--ayuda"):
        print(t("help", version=VERSION, conf=CONF))
        return 0
    if args and args[0] in ("-V", "--version"):
        print(VERSION)
        return 0
    name_arg = clean_name(args[0]) if args else ""

    print(t("intro", version=VERSION))
    if not shutil.which("yt-dlp"):
        print(t("no_ytdlp"))
        return 1
    if not shutil.which("ffmpeg"):
        print(t("no_ffmpeg"))

    print(t("steps"))
    url, headers = parse_request(read_paste())
    if not url:
        print(t("bad_paste"))
        return 1
    print(t("received", n=len(headers)))
    show_expiry(url)

    info, piece_query = None, None
    if ".m3u8" in urlsplit(url).path.lower():
        code, info = inspect_playlist(url, headers)
        print(t("playlist_check", code=code_text(code)))
        if code != 200:
            explain(code)
            if code == 429 or not ask_yes(t("try_anyway")):
                return 1
        elif info and info["drm"]:
            print(t("drm"))
            return 1
        elif info:
            print(t("playlist_info", n=info["count"], dur=clock(info["duration"])))
            code = probe(info["first"], headers)
            print(t("piece_check", code=code_text(code)))
            if code in (0, 429):
                explain(code)
                return 1
            if code != 200:
                print(t("need_piece"))
                piece_url, piece_headers = parse_request(read_paste())
                piece_query = urlsplit(piece_url).query if piece_url else ""
                if not piece_query:
                    print(t("piece_no_query"))
                    if not ask_yes(t("try_anyway")):
                        return 1
                    piece_query = None
                else:
                    headers = merge_headers(headers, piece_headers)
                    code = probe(with_query(info["first"], piece_query), headers)
                    print(t("piece_check", code=code_text(code)))
                    if code != 200:
                        explain(code)
                        if code == 429 or not ask_yes(t("try_anyway")):
                            return 1
    else:
        print(t("not_hls"))

    suggested = default_name(url)
    if name_arg:
        name = name_arg
    else:
        try:
            name = clean_name(input(t("ask_name", default=suggested))) or suggested
        except EOFError:
            name = suggested
    finished = [f for f in glob.glob(glob.escape(name) + ".*")
                if not f.endswith((".part", ".ytdl")) and ".part-" not in f]
    if finished:
        print(t("already", path=os.path.abspath(finished[0])))
        return 0

    print(t("downloading"))
    result = run_ytdlp(url, headers, piece_query, name, conf)
    finished = [f for f in glob.glob(glob.escape(name) + ".*")
                if not f.endswith((".part", ".ytdl")) and ".part-" not in f]
    if result != 0 or not finished:
        started = glob.glob(glob.escape(name) + ".*.part") or glob.glob(glob.escape(name) + ".*.ytdl")
        print(t("not_finished", name=name) if started else t("failed"))
        return 1

    path = os.path.abspath(finished[0])
    megabytes = os.path.getsize(path) / 1024 / 1024
    print(t("done", path=path, mb=f"{megabytes:.0f}" if megabytes >= 10 else f"{megabytes:.1f}"))
    real = media_duration(path)
    if real and info and not info.get("drm") and info.get("duration"):
        expected = info["duration"]
        if abs(real - expected) <= max(3, expected * 0.01):
            print(t("complete", dur=clock(real)))
        else:
            print(t("mismatch", real=clock(real), dur=clock(expected)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print(t("stopped"))
        sys.exit(130)
