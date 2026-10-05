"""Os passos de git do ciclo como código (rodada 6). O ensaio com remoto --bare e dois clones mostrou que o
texto do SKILL falhava:

1. `git add usina/.lock` rodava de dentro de `usina/` (o passo 0 faz `cd usina`): pathspec inexistente, o lock
   nunca ia para o remoto e o outro container não o enxergava.
2. O push do fim do ciclo não tinha plano B: qualquer push no meio (outro agente, o Caio, um ciclo que assumiu
   um lock vencido) deixava o commit preso no container, que morre.
3. Conflito num item da fila (dois ciclos mexeram no mesmo JSON) parava tudo num rebase pela metade.

`tick-start --git`: pull → tick-start → commit do .lock → push (push recusado: solta, puxa e tenta UMA vez).
`tick-end --git`: tick-end → commit de usina/ → push; recusado: pull (merge) → resolve → push (até 3 vezes).
`git-resolve`: resolve os conflitos de um merge em andamento com as mesmas regras (para uso à mão).

Regras de resolução (o código decide, o operador só relata):
- `.lock`: fica o lock vivo de outro ciclo; senão o meu, se vivo; senão nenhum.
- `data/*.jsonl`: união das linhas (o .gitattributes já faz isso; aqui é a rede se ele faltar).
- `data/health.json`: saldo mais recente, erros unidos por horário, maior sequência de erros.
- `data/queue/<página>/<id>.json`: fica a versão com mais jobs pagos (job_id), depois a mais avançada na
  esteira, depois a mais recente (`updated_at`). A outra vai inteira para `data/conflicts/` (no git) e o
  comando avisa se ela tinha job que a vencedora não tem (vídeo pago que pode ter se perdido).
- Qualquer outro arquivo: não resolve. Aborta o merge e empurra o commit do ciclo para um ramo
  `usina-conflito-<data>` no remoto (nada se perde com o container); o operador reporta ao Caio.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from . import lock
from .store import ALL_STATES, ROOT, StoreError

REMOTE = os.getenv("USINA_GIT_REMOTE", "origin")
CONFLICTS = ROOT / "data" / "conflicts"


class GitError(StoreError):
    pass


def git(*args: str, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[:400]}")
    return r


def top() -> Path:
    return Path(git("rev-parse", "--show-toplevel").stdout.strip())


def prefix() -> str:
    """Caminho da usina dentro do repo (ex.: 'usina/'), para traduzir os caminhos que o git devolve."""
    return git("rev-parse", "--show-prefix").stdout.strip()


def branch() -> str:
    b = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if b == "HEAD":
        raise GitError("HEAD destacado: faça checkout do ramo da usina antes do ciclo")
    return b


def remote_has_branch(br: str) -> bool:
    r = git("ls-remote", "--exit-code", "--heads", REMOTE, br, check=False)
    return r.returncode == 0


def push(br: str) -> tuple[bool, str]:
    r = git("push", "-q", "-u", REMOTE, f"HEAD:{br}", check=False)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def _merging() -> bool:
    return git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0


def _stage(path_from_top: str, n: int) -> str | None:
    r = git("show", f":{n}:{path_from_top}", check=False, cwd=top())
    return r.stdout if r.returncode == 0 else None


def _json(text: str | None):
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _job_ids(obj) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("job_id", "hf_job") and v:
                out.add(str(v))
            else:
                out |= _job_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _job_ids(v)
    return out


def _rank(item: dict) -> tuple:
    st = item.get("state")
    return (len(_job_ids(item)), ALL_STATES.index(st) if st in ALL_STATES else -1, float(item.get("updated_at") or 0))


def pick_item(mine: dict | None, theirs: dict | None) -> tuple[dict, dict | None, str]:
    """(vencedora, perdedora, de quem venceu). Pura: o teste chama direto."""
    if mine is None or theirs is None:
        return (mine if theirs is None else theirs), None, ("meu" if theirs is None else "remoto")
    if _rank(mine) >= _rank(theirs):
        return mine, theirs, "meu"
    return theirs, mine, "remoto"


def pick_lock(mine: dict | None, theirs: dict | None, now: float | None = None) -> dict | None:
    me = lock.my_owner()
    live = [d for d in (theirs, mine) if d and not lock.stale(d, now)]
    other = [d for d in live if d.get("owner") != me]
    if other:
        return other[0]
    return live[0] if live else None


def merge_health(mine: dict | None, theirs: dict | None) -> dict:
    a, b = mine or {}, theirs or {}
    out = {**b, **a}
    bals = [x.get("balance") for x in (a, b) if x.get("balance")]
    out["balance"] = max(bals, key=lambda x: float(x.get("at") or 0)) if bals else None
    errs = {json.dumps(e, sort_keys=True): e for e in (a.get("errors") or []) + (b.get("errors") or [])}
    out["errors"] = sorted(errs.values(), key=lambda e: float(e.get("at") or 0))[-50:]
    out["consecutive_errors"] = max(int(a.get("consecutive_errors") or 0), int(b.get("consecutive_errors") or 0))
    return out


def union_lines(mine: str | None, theirs: str | None) -> str:
    seen, out = set(), []
    for line in (mine or "").splitlines() + (theirs or "").splitlines():
        if line.strip() and line not in seen:
            seen.add(line)
            out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def _write(path: Path, text: str | None) -> None:
    if text is None:
        if path.exists():
            path.unlink()
        git("rm", "-q", "--cached", "--ignore-unmatch", "--", str(path.relative_to(ROOT)), check=False)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git("add", "--", str(path.relative_to(ROOT)))


def resolve(now: float | None = None) -> dict:
    """Resolve os conflitos do merge em andamento. Devolve {"resolved", "kept", "unresolved", "warnings"}."""
    pre = prefix()
    files = [f for f in git("diff", "--name-only", "--diff-filter=U", cwd=top()).stdout.splitlines() if f]
    res = {"resolved": [], "kept": [], "unresolved": [], "warnings": []}
    for f in files:
        rel = f[len(pre):] if pre and f.startswith(pre) else None
        mine_t, theirs_t = _stage(f, 2), _stage(f, 3)   # merge: 2 = meu (HEAD), 3 = o que veio do remoto
        if rel is None:
            res["unresolved"].append(f)
            continue
        path = ROOT / rel
        if rel == ".lock":
            d = pick_lock(_json(mine_t), _json(theirs_t), now)
            if d and d.get("owner") != lock.my_owner():
                res["warnings"].append(f"o lock agora é de outro ciclo ({lock.describe(d, now)}): ele assumiu enquanto "
                                       f"você rodava. Não gaste mais neste ciclo.")
            _write(path, json.dumps(d, ensure_ascii=False, indent=2) if d else None)
        elif rel.startswith("data/") and rel.endswith(".jsonl"):
            _write(path, union_lines(mine_t, theirs_t))
        elif rel == "data/health.json":
            _write(path, json.dumps(merge_health(_json(mine_t), _json(theirs_t)), ensure_ascii=False, indent=2))
        elif rel.startswith("data/queue/") and rel.endswith(".json"):
            mine, theirs = _json(mine_t), _json(theirs_t)
            if (mine_t is not None and mine is None) or (theirs_t is not None and theirs is None):
                res["unresolved"].append(f)   # JSON quebrado de um lado: não adivinho
                continue
            win, lose, who = pick_item(mine, theirs)
            _write(path, json.dumps(win, ensure_ascii=False, indent=2))
            if lose is not None:
                CONFLICTS.mkdir(parents=True, exist_ok=True)
                side = "remoto" if who == "meu" else "meu"
                keep = CONFLICTS / f"{Path(rel).parent.name}__{Path(rel).stem}__{time.strftime('%Y%m%d-%H%M%S')}-{side}.json"
                _write(keep, json.dumps(lose, ensure_ascii=False, indent=2))
                res["kept"].append(str(keep.relative_to(ROOT)))
                lost = sorted(_job_ids(lose) - _job_ids(win))
                if lost:
                    res["warnings"].append(f"{rel}: a versão guardada em {keep.relative_to(ROOT)} tem job(s) que a "
                                           f"vencedora não tem: {', '.join(lost)}. Confira no Higgsfield antes de pagar de novo.")
            res["warnings"].append(f"{rel}: conflito; ficou a versão {who} ({win.get('state')}), a outra em data/conflicts/")
        else:
            res["unresolved"].append(f)
            continue
        res["resolved"].append(rel)
    return res


def pull_merge(br: str, now: float | None = None) -> dict:
    """git pull --no-rebase com resolução automática. Conflito sem regra: aborta e levanta GitError."""
    if not remote_has_branch(br):
        return {"resolved": [], "kept": [], "unresolved": [], "warnings": [], "pulled": False}
    r = git("pull", "-q", "--no-rebase", "--no-edit", REMOTE, br, check=False)
    if r.returncode == 0:
        return {"resolved": [], "kept": [], "unresolved": [], "warnings": [], "pulled": True}
    if not _merging():
        raise GitError(f"git pull falhou: {(r.stderr or r.stdout).strip()[:400]}")
    res = resolve(now)
    if res["unresolved"]:
        git("merge", "--abort", check=False)
        res["pulled"] = False
        return res
    git("commit", "-q", "--no-edit", "-m", f"usina: merge com {REMOTE}/{br} (conflitos resolvidos pelo pipeline)")
    res["pulled"] = True
    return res


def start(owner: str | None = None, now: float | None = None) -> dict:
    """Passo 0.2 do SKILL inteiro: pull, lock, commit e push do lock (uma 2ª tentativa se o push for recusado)."""
    br = branch()
    report: dict = {"branch": br, "warnings": []}
    for attempt in (1, 2):
        res = pull_merge(br, now)
        report["warnings"] += res["warnings"]
        if res["unresolved"]:
            raise GitError(f"conflito sem regra em {', '.join(res['unresolved'])}: não comecei o ciclo. Reporte ao Caio.")
        ok, msg, d = lock.acquire(owner, now)
        if not ok:
            raise GitError(msg + ". Saia sem fazer nada (o outro ciclo termina e libera).")
        if msg:
            report["warnings"].append(msg)
        git("add", "--", ".lock")
        git("commit", "-q", "-m", "usina: lock", "--", ".lock")
        pushed, err = push(br)
        if pushed:
            report.update({"owner": d["owner"], "pushed": True, "attempts": attempt})
            return report
        # recusado: alguém empurrou antes. Desfaz só o commit do lock (o .lock volta ao do commit anterior, o resto
        # da árvore fica como está), puxa e tenta UMA vez; se quem empurrou foi outro ciclo, o acquire recusa.
        report["warnings"].append(f"push do lock recusado ({err.splitlines()[0] if err else '?'}); tentando de novo")
        git("reset", "-q", "--keep", "HEAD~1")
    raise GitError("push do lock recusado duas vezes: saia sem fazer nada e deixe o próximo ciclo tentar")


def end(message: str | None = None, owner: str | None = None, force: bool = False, now: float | None = None) -> dict:
    """Passo 4 do SKILL inteiro: solta o lock, commita usina/ e empurra; push recusado: merge, resolve, empurra."""
    br = branch()
    ok, msg = lock.release(owner, force, now)
    if not ok:
        raise GitError(msg)
    report: dict = {"branch": br, "lock": msg, "warnings": [], "kept": [], "pushed": False}
    git("add", "-A", "--", ".")
    stamp = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(now or time.time()))
    if _staged():
        git("commit", "-q", "-m", message or f"usina: tick {stamp}")
    for attempt in (1, 2, 3):
        pushed, err = push(br)
        if pushed:
            report.update({"pushed": True, "attempts": attempt})
            return report
        res = pull_merge(br, now)
        report["warnings"] += res["warnings"]
        report["kept"] += res["kept"]
        if res["unresolved"]:
            side = f"usina-conflito-{time.strftime('%Y%m%d-%H%M%S', time.gmtime(now or time.time()))}"
            r = git("push", "-q", REMOTE, f"HEAD:refs/heads/{side}", check=False)
            report.update({"unresolved": res["unresolved"], "side_branch": side if r.returncode == 0 else None})
            raise GitError(f"conflito sem regra em {', '.join(res['unresolved'])}: não empurrei para {br}. "
                           + (f"O commit do ciclo está salvo no ramo {side} do remoto. " if r.returncode == 0 else
                              "E nem o ramo de resgate subiu: NÃO feche a sessão sem reportar. ")
                           + "Reporte ao Caio; não resolva à mão.")
    raise GitError(f"push recusado 3 vezes ({err.splitlines()[0] if err else '?'}): rode `tick-end --git` de novo")


def _staged() -> bool:
    return git("diff", "--cached", "--quiet", check=False).returncode != 0
