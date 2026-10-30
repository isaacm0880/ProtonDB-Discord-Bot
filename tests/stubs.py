"""Minimal stand-ins for discord.py and aiohttp.

They are installed ONLY when the real libraries are not importable (for example
in a sandbox without network access). With the real libraries installed
(`pip install -r requirements.txt`) the tests run against them instead.

The stand-ins model just enough behaviour to exercise this project's own logic
(embed limits, command registration, control flow). They are NOT a substitute
for testing against live Discord.
"""
from __future__ import annotations

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

USING_STUBS = False


def install() -> bool:
    global USING_STUBS
    try:
        import discord  # noqa: F401
        import aiohttp  # noqa: F401
        return False
    except ImportError:
        pass
    if USING_STUBS:
        return True
    USING_STUBS = True
    _install_aiohttp()
    _install_discord()
    return True


# --------------------------------------------------------------------------
def _install_aiohttp() -> None:
    m = types.ModuleType("aiohttp")

    class ClientError(Exception):
        pass

    class ClientTimeout:
        def __init__(self, total=None):
            self.total = total

    class TCPConnector:
        def __init__(self, **kw):
            pass

    class ClientSession:
        def __init__(self, **kw):
            self.closed = False

        async def close(self):
            self.closed = True

    m.ClientError, m.ClientTimeout, m.TCPConnector, m.ClientSession = (
        ClientError, ClientTimeout, TCPConnector, ClientSession)
    sys.modules["aiohttp"] = m


def _install_discord() -> None:
    d = types.ModuleType("discord")

    class Colour:
        def __init__(self, value):
            self.value = value

    class _Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class Embed:
        def __init__(self, **kw):
            self.title = kw.get("title")
            self.description = kw.get("description")
            self.url = kw.get("url")
            self.colour = kw.get("colour")
            self.timestamp = kw.get("timestamp")
            self.fields: list[_Obj] = []
            self.footer = _Obj(text=None)
            self.image = _Obj(url=None)
            self.thumbnail = _Obj(url=None)

        def add_field(self, *, name, value, inline=True):
            self.fields.append(_Obj(name=name, value=value, inline=inline))
            return self

        def set_field_at(self, index, *, name, value, inline=True):
            self.fields[index] = _Obj(name=name, value=value, inline=inline)
            return self

        def remove_field(self, index):
            del self.fields[index]

        def set_footer(self, *, text=None, icon_url=None):
            self.footer = _Obj(text=text)
            return self

        def set_image(self, *, url):
            self.image = _Obj(url=url)
            return self

        def set_thumbnail(self, *, url):
            self.thumbnail = _Obj(url=url)
            return self

        def __len__(self):
            total = len(self.title or "") + len(self.description or "") + len(self.footer.text or "")
            for f in self.fields:
                total += len(f.name) + len(f.value)
            return total

    class AllowedMentions:
        @classmethod
        def none(cls):
            return cls()

    class HTTPException(Exception):
        pass

    class NotFound(HTTPException):
        pass

    class Forbidden(HTTPException):
        pass

    class Object:
        def __init__(self, id):
            self.id = id

    class Intents:
        @classmethod
        def default(cls):
            return cls()

    class _Enum:
        def __init__(self, name):
            self.name = name

    class ButtonStyle:
        secondary = _Enum("secondary")

    class InteractionType:
        autocomplete = _Enum("autocomplete")
        application_command = _Enum("application_command")

    class Interaction:
        pass

    # ---- discord.ui -----------------------------------------------------
    ui = types.ModuleType("discord.ui")

    class Item:
        pass

    class Button(Item):
        def __init__(self, *, label=None, style=None, custom_id=None, **kw):
            self.label, self.style, self.custom_id = label, style, custom_id

    class View:
        def __init__(self, *, timeout=180):
            self.timeout = timeout
            self.children: list = []

        def add_item(self, item):
            self.children.append(item)
            return self

    class DynamicItem(Item):
        template = None

        def __class_getitem__(cls, item):
            return cls

        def __init_subclass__(cls, *, template=None, **kw):
            cls.template = template

        def __init__(self, item):
            self.item = item

        @property
        def custom_id(self):
            return self.item.custom_id

    ui.Item, ui.Button, ui.View, ui.DynamicItem = Item, Button, View, DynamicItem

    # ---- discord.utils --------------------------------------------------
    utils = types.ModuleType("discord.utils")

    def escape_markdown(text, *, as_needed=False, ignore_links=True):
        for ch in ("\\", "*", "_", "~", "`", "|", ">"):
            text = text.replace(ch, "\\" + ch)
        return text

    utils.escape_markdown = escape_markdown

    # ---- discord.app_commands -------------------------------------------
    ac = types.ModuleType("discord.app_commands")

    class AppCommandError(Exception):
        pass

    class Choice:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, *, name, value):
            self.name, self.value = name, value

    class _Range:
        def __class_getitem__(cls, item):
            return item[0]

    class Command:
        def __init__(self, callback, name, description):
            self.callback, self.name, self.description = callback, name, description
            self.autocompletes = getattr(callback, "__ac__", {})
            self.descriptions = getattr(callback, "__desc__", {})

    def describe(**kw):
        def deco(fn):
            fn.__desc__ = kw
            return fn
        return deco

    def autocomplete(**kw):
        def deco(fn):
            fn.__ac__ = kw
            return fn
        return deco

    class CommandTree:
        def __init__(self):
            self.commands: dict[str, Command] = {}
            self.error_handler = None

        def command(self, *, name, description="..."):
            def deco(fn):
                cmd = Command(fn, name, description)
                self.commands[name] = cmd
                return cmd
            return deco

        def error(self, fn):
            self.error_handler = fn
            return fn

        def copy_global_to(self, *, guild):
            pass

        async def sync(self, *, guild=None):
            return list(self.commands.values())

    ac.AppCommandError, ac.Choice, ac.Range = AppCommandError, Choice, _Range
    ac.describe, ac.autocomplete, ac.CommandTree = describe, autocomplete, CommandTree

    # ---- discord.ext.commands -------------------------------------------
    ext = types.ModuleType("discord.ext")
    cmds = types.ModuleType("discord.ext.commands")

    class Bot:
        def __init__(self, command_prefix=None, intents=None, allowed_mentions=None, **kw):
            self.tree = CommandTree()
            self.user = None
            self.dynamic = []

        def event(self, fn):
            return fn

        def add_dynamic_items(self, *items):
            self.dynamic.extend(items)

        async def close(self):
            pass

    cmds.Bot = Bot
    cmds.when_mentioned = object()
    ext.commands = cmds

    d.Colour, d.Color, d.Embed, d.AllowedMentions = Colour, Colour, Embed, AllowedMentions
    d.HTTPException, d.NotFound, d.Forbidden, d.Object = HTTPException, NotFound, Forbidden, Object
    d.Intents, d.ButtonStyle, d.InteractionType, d.Interaction = Intents, ButtonStyle, InteractionType, Interaction
    d.ui, d.utils, d.app_commands, d.ext = ui, utils, ac, ext

    sys.modules.update({
        "discord": d, "discord.ui": ui, "discord.utils": utils,
        "discord.app_commands": ac, "discord.ext": ext, "discord.ext.commands": cmds,
    })


def validate_embed(embed) -> list[str]:
    """Return a list of Discord embed-limit violations (empty list = fine)."""
    problems = []
    if embed.title and len(embed.title) > 256:
        problems.append("title>256")
    if embed.description and len(embed.description) > 4096:
        problems.append("description>4096")
    if len(embed.fields) > 25:
        problems.append("fields>25")
    for f in embed.fields:
        if not f.name or len(f.name) > 256:
            problems.append(f"field name invalid: {f.name!r:.40}")
        if not f.value or len(f.value) > 1024:
            problems.append(f"field value invalid: {f.name!r:.40}")
    if embed.footer and embed.footer.text and len(embed.footer.text) > 2048:
        problems.append("footer>2048")
    if len(embed) > 6000:
        problems.append(f"total>{6000}: {len(embed)}")
    return problems
