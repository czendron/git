"""Ferramentas de mídia com ffmpeg: inspeção, folha de contato para revisão, capa, hash e normalização para Reels."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REELS = {"width": 1080, "height": 1920, "fps": 30}


class MediaError(RuntimeError):
    pass


def _run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise MediaError(f"{' '.join(cmd[:3])}...: {r.stderr.strip()[-400:]}")
    return r.stdout


def probe(path: Path) -> dict:
    out = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    data = json.loads(out)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        raise MediaError(f"{path} não tem trilha de vídeo")
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    return {
        "duration": float(data["format"].get("duration", 0)),
        "width": int(v["width"]), "height": int(v["height"]),
        "fps": round(float(num) / float(den or 1), 2),
        "vcodec": v["codec_name"], "acodec": a["codec_name"] if a else None,
        "size_mb": round(int(data["format"].get("size", 0)) / 1e6, 2),
    }


def contact_sheet(video: Path, out: Path, n: int = 8, cols: int = 4) -> Path:
    """n frames igualmente espaçados numa grade, com o timecode em cada um: é o que o revisor de IA olha."""
    info = probe(video)
    dur = max(info["duration"], 0.1)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = (n + cols - 1) // cols
    fps = n / dur
    vf = (f"fps={fps:.5f},scale=270:-2,"
          "drawtext=text='%{pts\\:hms}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}:padding=4:margin=4")
    try:
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", vf, "-frames:v", "1", str(out)])
    except MediaError:  # ffmpeg sem drawtext/fontconfig: sem timecode
        vf = f"fps={fps:.5f},scale=270:-2,tile={cols}x{rows}:padding=4:margin=4"
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", vf, "-frames:v", "1", str(out)])
    return out


def sheet_window(video: Path, out: Path, start: float, end: float, fps: float, cols: int = 6) -> Path:
    """Folha de contato de uma janela de tempo (playbook E1: 2 fps no clipe, 6 fps no gag)."""
    dur = max(end - start, 0.1)
    n = max(1, int(round(dur * fps)))
    rows = (n + cols - 1) // cols
    out.parent.mkdir(parents=True, exist_ok=True)
    base = f"fps={fps},scale=240:-2"
    for vf in (base + ",drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,"
               f"tile={cols}x{rows}:padding=3:margin=3", base + f",tile={cols}x{rows}:padding=3:margin=3"):
        try:
            _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(video),
                  "-vf", vf, "-frames:v", "1", str(out)])
            return out
        except MediaError:
            continue
    raise MediaError("não consegui montar a folha de contato")


def detect_cuts(video: Path, threshold: float = 0.35) -> list[float]:
    """Cortes por diferença de cena (cálculo, não visão). Devolve os instantes em segundos."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True)
    import re
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    return [t for t in times if t > 0.2]


def frame_at(video: Path, t: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out)])
    return out


def last_frame(video: Path, out: Path) -> Path:
    info = probe(video)
    return frame_at(video, max(info["duration"] - 0.15, 0), out)


def ahash(image: Path) -> str:
    """Hash perceptual simples (8x8 média) para achar arquivo repetido entre páginas."""
    from PIL import Image
    im = Image.open(image).convert("L").resize((8, 8))
    px = list(im.getdata())
    avg = sum(px) / len(px)
    return "".join("1" if p > avg else "0" for p in px)


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def video_hash(video: Path, tmpdir: Path) -> str:
    """Hash do vídeo = hashes de 3 frames (25%, 50%, 75%)."""
    info = probe(video)
    parts = []
    for i, f in enumerate((0.25, 0.5, 0.75)):
        p = frame_at(video, info["duration"] * f, tmpdir / f"_h{i}.jpg")
        parts.append(ahash(p))
    return "".join(parts)


def normalize_reels(src: Path, dst: Path) -> Path:
    """Deixa o MP4 no padrão do Reels (H.264, 1080x1920, 30 fps, AAC, faststart).

    Se o arquivo já está compatível, só remuxa (preserva melhor os metadados de origem/C2PA).
    """
    info = probe(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    ok_codec = info["vcodec"] == "h264" and info["width"] <= 1080 and info["height"] <= 1920
    if ok_codec and abs(info["width"] / info["height"] - 9 / 16) < 0.01:
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0", "-c", "copy", "-map_metadata", "0",
              "-movflags", "+faststart", str(dst)])
        return dst
    w, h = REELS["width"], REELS["height"]
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={REELS['fps']}"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-map_metadata", "0", "-movflags", "+faststart"]
    if info["acodec"]:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
    else:  # Reels aceita sem áudio, mas um silêncio evita problema em alguns players
        cmd = cmd[:5] + ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"] + cmd[5:] + ["-shortest", "-c:a", "aac", "-b:a", "128k"]
    cmd.append(str(dst))
    _run(cmd)
    return dst


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
