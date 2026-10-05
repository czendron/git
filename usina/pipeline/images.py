"""Geração de imagem pela API da OpenAI (GPT Image), no mesmo padrão do tools/gpt_image.py do Papo de Gato.

- Com referências: images.edit (identidade do personagem vem da imagem, não do texto).
- Sem referências: images.generate.
- MOCK=1 (ou sem OPENAI_API_KEY e --mock): escreve um PNG placeholder, para testar o pipeline sem gastar.
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path

MODEL_DEFAULT = os.getenv("USINA_IMAGE_MODEL", "gpt-image-2.5-sunburst")
FIDELITY_MODELS = {"gpt-image-1", "gpt-image-1.5", "gpt-image-1-mini"}
SIZES = {"9:16": "1024x1536", "1:1": "1024x1024", "16:9": "1536x1024"}


class ImageError(RuntimeError):
    pass


def _placeholder_png(path: Path, label: str) -> None:
    """PNG 9:16 cinza com texto, só para modo mock."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (512, 912), (210, 205, 190))
        d = ImageDraw.Draw(img)
        d.rectangle([20, 20, 492, 892], outline=(40, 40, 40), width=4)
        y = 60
        for line in [label[i:i + 34] for i in range(0, min(len(label), 34 * 20), 34)]:
            d.text((40, y), line, fill=(20, 20, 20))
            y += 18
        img.save(path, "PNG")
    except ImportError:  # PNG 1x1 válido
        path.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="))


def generate(prompt: str, out: Path, refs: list[Path] | None = None, *, aspect: str = "9:16",
             quality: str = "high", model: str | None = None, mock: bool | None = None,
             retries: int = 2) -> Path:
    """Gera uma imagem e grava em `out`. Devolve o caminho."""
    model = model or MODEL_DEFAULT
    refs = [Path(r) for r in (refs or [])]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not prompt.strip():
        raise ImageError("prompt vazio")
    missing = [str(r) for r in refs if not r.exists()]
    if missing:
        raise ImageError(f"referência não encontrada: {', '.join(missing)}")

    if mock is None:
        mock = os.getenv("USINA_MOCK") == "1"
    if mock:
        _placeholder_png(out, f"MOCK {model} | {prompt[:600]}")
        return out

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ImageError("OPENAI_API_KEY ausente (defina no ambiente ou use USINA_MOCK=1)")
    from openai import OpenAI
    client = OpenAI(api_key=key)
    size = SIZES.get(aspect, aspect)

    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if refs:
                fhs = [open(r, "rb") for r in refs]
                try:
                    kwargs = dict(model=model, image=fhs, prompt=prompt, size=size, quality=quality)
                    if model in FIDELITY_MODELS:
                        kwargs["input_fidelity"] = "high"
                    resp = client.images.edit(**kwargs)
                finally:
                    for fh in fhs:
                        fh.close()
            else:
                resp = client.images.generate(model=model, prompt=prompt, size=size, quality=quality)
            out.write_bytes(base64.b64decode(resp.data[0].b64_json))
            return out
        except Exception as e:  # noqa: BLE001 - repassa a mensagem da API
            last = e
            msg = str(e).lower()
            # Bloqueio de moderação não melhora com retry.
            if "moderation" in msg or "safety" in msg or "content_policy" in msg:
                break
            if attempt < retries:
                time.sleep(4 * (attempt + 1))
    raise ImageError(f"{type(last).__name__}: {last}")


def generate_variants(prompt: str, outs: list[Path], refs: list[Path] | None = None, *, aspect: str = "9:16",
                      quality: str = "high", model: str | None = None, mock: bool | None = None) -> list[Path]:
    """N opções do mesmo prompt (playbook C5: "faça 4 variações e cure"). Uma chamada com n=N; se a API devolver
    menos (ou não aceitar n), completa com chamadas avulsas."""
    outs = [Path(o) for o in outs]
    if mock is None:
        mock = os.getenv("USINA_MOCK") == "1"
    if mock or len(outs) == 1:
        for i, o in enumerate(outs, 1):
            generate(f"{prompt}" if not mock else f"[variante {i}] {prompt}", o, refs, aspect=aspect, quality=quality,
                     model=model, mock=mock)
        return outs
    done: list[Path] = []
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    refs = [Path(r) for r in (refs or [])]
    if key and refs:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            m = model or MODEL_DEFAULT
            fhs = [open(r, "rb") for r in refs]
            try:
                kw = dict(model=m, image=fhs, prompt=prompt, size=SIZES.get(aspect, aspect), quality=quality, n=len(outs))
                if m in FIDELITY_MODELS:
                    kw["input_fidelity"] = "high"
                resp = client.images.edit(**kw)
            finally:
                for fh in fhs:
                    fh.close()
            for o, d in zip(outs, resp.data):
                o.parent.mkdir(parents=True, exist_ok=True)
                o.write_bytes(base64.b64decode(d.b64_json))
                done.append(o)
        except Exception as e:  # noqa: BLE001 - cai para chamadas avulsas
            msg = str(e).lower()
            if "moderation" in msg or "safety" in msg or "content_policy" in msg:
                raise ImageError(f"{type(e).__name__}: {e}")
    for o in outs[len(done):]:
        generate(prompt, o, refs, aspect=aspect, quality=quality, model=model, mock=False)
        done.append(o)
    return done
