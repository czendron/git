"""Páginas (pages/<slug>/page.yaml) e fila de vídeos (data/queue/<slug>/<id>.json).

A fila é JSON versionado no git: cada item é um vídeo, do roteiro até o post.
Estados (ordem, ata D9 storyboard-first):
  ideia -> roteiro -> storyboard -> frames -> video -> revisao -> pronto -> postado
Cada etapa de imagem/vídeo tem portões em item.gates[etapa] = {"qa": "pass|fail|pending", "caio": "approved|rejected|pending|skip"}.
Desvios: descartado, erro, pausado.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
QUEUE = ROOT / "data" / "queue"
OUT = ROOT / "out"

STATES = ["ideia", "roteiro", "storyboard", "frames", "video", "revisao", "pronto", "postado"]
OFF_STATES = ["descartado", "erro", "pausado"]
ALL_STATES = STATES + OFF_STATES


class StoreError(RuntimeError):
    pass


def rel(path) -> str:
    """Caminho para gravar no JSON da fila: relativo à raiz da usina (o repo é clonado em outras máquinas)."""
    if not path:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def local(path) -> Path | None:
    """Resolve um caminho gravado na fila (relativo, ou absoluto de outra máquina) para o arquivo local."""
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        return ROOT / p
    if p.exists():
        return p
    parts = p.parts  # absoluto legado de outra máquina: remapeia a partir de out/ ou pages/
    for anchor in ("out", "pages", "data"):
        if anchor in parts:
            i = len(parts) - 1 - parts[::-1].index(anchor)
            return ROOT.joinpath(*parts[i:])
    return p


@dataclass
class Page:
    slug: str
    data: dict
    dir: Path

    @property
    def active(self) -> bool:
        return self.data.get("status") == "ativo"

    @property
    def character(self) -> dict:
        return self.data.get("character", {})

    def ref_paths(self) -> list[Path]:
        return [self.dir / r["file"] for r in self.data.get("refs", []) if r.get("file")]

    def available_refs(self) -> list[Path]:
        return [p for p in self.ref_paths() if p.exists()]


def load_pages(include_drafts: bool = True) -> list[Page]:
    pages = []
    for f in sorted(PAGES.glob("*/page.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        slug = data.get("slug") or f.parent.name
        if slug != f.parent.name:
            raise StoreError(f"{f}: slug '{slug}' diferente da pasta '{f.parent.name}'")
        p = Page(slug=slug, data=data, dir=f.parent)
        if include_drafts or p.active:
            pages.append(p)
    return pages


def get_page(slug: str) -> Page:
    for p in load_pages():
        if p.slug == slug:
            return p
    raise StoreError(f"página '{slug}' não existe em pages/")


def slugify(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48] or "item"


@dataclass
class Item:
    page: str
    id: str
    state: str = "ideia"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    idea: dict = field(default_factory=dict)
    script: dict = field(default_factory=dict)
    storyboard: dict = field(default_factory=dict) # {"path":..,"prompt":..,"attempts":n,"higgsfield_id":..}
    frames: dict = field(default_factory=dict)     # {"start": {"path":..,"prompt":..,"higgsfield_id":..}, "end": {...}}
    motion: dict = field(default_factory=dict)     # trend: {"source_path","source_hf_id","first_frame","duration","cuts"}
    gates: dict = field(default_factory=dict)      # {"storyboard": {"qa":..,"caio":..,"notes":..}, ...}
    attempts: dict = field(default_factory=dict)   # {"storyboard": n, "frames": n, "video": n}
    cost: dict = field(default_factory=dict)       # {"usd": x, "credits": y}
    video: dict = field(default_factory=dict)      # {"provider":..,"job_id":..,"url":..,"path":..}
    post: dict = field(default_factory=dict)       # {"caption":..,"audio":..,"scheduled_for":..,"ig_media_id":..}
    history: list = field(default_factory=list)
    decisions: list = field(default_factory=list)  # ids das decisões do painel já aplicadas (idempotência)
    notes: str = ""

    @property
    def path(self) -> Path:
        return QUEUE / self.page / f"{self.id}.json"

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def set_state(self, state: str, why: str = "") -> None:
        if state not in ALL_STATES:
            raise StoreError(f"estado inválido: {state}")
        self.history.append({"at": time.time(), "from": self.state, "to": state, "why": why})
        self.state = state
        self.updated_at = time.time()

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return self.path


def new_item(page: str, title: str, idea: dict) -> Item:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = f"{stamp}-{slugify(title)}"
    item_id, n = base, 2
    while (QUEUE / page / f"{item_id}.json").exists():
        item_id, n = f"{base}-{n}", n + 1
    return Item(page=page, id=item_id, idea=idea)


def load_item(page: str, item_id: str) -> Item:
    f = QUEUE / page / f"{item_id}.json"
    if not f.exists():
        raise StoreError(f"item não existe: {page}/{item_id}")
    data = json.loads(f.read_text(encoding="utf-8"))
    return Item(**{k: v for k, v in data.items() if k in Item.__dataclass_fields__})


def list_items(page: str | None = None, state: str | None = None) -> list[Item]:
    items = []
    dirs = [QUEUE / page] if page else sorted(QUEUE.glob("*"))
    for d in dirs:
        for f in sorted(d.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            it = Item(**{k: v for k, v in data.items() if k in Item.__dataclass_fields__})
            if state is None or it.state == state:
                items.append(it)
    return items
