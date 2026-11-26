#!/usr/bin/env python3
"""ukagaka-muse シェル＋ゴーストのビルドスクリプト（テンプレート同梱）。

使い方:
  作業フォルダに avatar.json を置き、そのフォルダでこのスクリプトを実行する。
  avatar.json は、現在有効なアバターの情報（avatar.get の出力）に、
  アシスタント名 "name" を加えたもの。形式は次のとおり。

    {
      "name": "<アシスタント名>",
      "image_path": "workspace/avatars/avatar-<id>-0.webp",
      "video_variants": {
        "idle": "workspace/avatars/avatar-<id>-0-attempt-<hash>.mp4",
        "connecting": "...(idle と同一ファイルの場合がある)",
        "making_something": "...",
        "milestone_level_up": "...",
        "waiting_for_subagents": "...(working と同一ファイルの場合がある)",
        "working": "..."
      }
    }

  パスは絶対パス、またはホームディレクトリからの相対パスで書く。

モード:
  build（引数なしの既定）: アバター素材からシェルを生成し、4つの nar を作る。
  base: 素材（テンプレート）自体を梱包し、template-ghost.nar と template-shell.nar を作る。
    名前は avatar.json の "name" を使う（素材の動画・静止画は読まない）。

出力（作業フォルダ）:
  build: shell-white/, shell-black/（シェルのフォルダ）,
         shell-white.nar, shell-black.nar（シェル単体）,
         ghost-white.nar, ghost-black.nar（ゴースト一式）
  base: template-ghost.nar, template-shell.nar
  部品（中身のみ・枠のみの画像）は parts-white/, parts-black/ に残す。
  シェルのフォルダや nar には入れない。

黒背景版（ダークモード）の素材は、通常版と同じフォルダにある
「<静止画のファイル名（拡張子なし）>-darkmode」という命名規則から機械的に決める。
動画については、通常版で同一ファイルを指す状態の関係（例: connecting は idle と
同一、waiting_for_subagents は working と同一）をそのまま引き継ぐ。
素材が見つからない場合は、代替で埋めずに停止して報告する。

設計方針:
- 幾何と番号割り当てはすべてこのファイルの定数に固定する。実行者の判断に依存しない。
- アニメーションのコマは「中身＋枠」の完結した画像にする（素体と同寸法・同合成）。
  枠を素体から透かす方式は幾何の一致が前提になり破綻しやすいため採らない。
- コマの採取は等間隔サンプリングに固定する。動画の再生時間を予定枚数で割り、
  その間隔でコマを取る。コマ数は常に予定枚数に固定し、動画の長さに応じて
  変わるのはサンプリング間隔（＝モーションの速度）だけである。
  素材ごとの区間選択や動き量の判定は行わない。
  同じ動画を2つのサーフェスで使う場合は、採取の位相（offset）を半周期ずらして区別する。
- アニメーションの値は、周期2.0秒に統一する。ループ・一回再生とも20コマ×100ms、
  サーフェス4 のみ 10コマ×200ms（周期は同じ、フレームレートだけ半分）。
- 1100 番台はテンプレートのシステム側（surface11 のアニメーション）が使うため、
  本体側のアニメーションには割り当てない。
- シェルは「1つのフォルダ一式」が単位である。テンプレートのシェルも、
  作成したシェルも、同じくフォルダ一式として扱う。
- nar の配置規則は梱包関数（pack_shell / pack_ghost）だけが知る。
  シェル単体はフォルダの中身をそのまま平置きし、ゴースト一式は
  ルートに install.txt・readme.txt、配下に ghost/master と shell/master を置く。
  手順の側で配置を組み立てない。
- 作成したゴーストの OnBoot は、アニメーション確認用のデモに差し替える
  （梱包用コピーの中だけ。テンプレート側の辞書は変更しない）。
- 検証までをスクリプトの責務とする。検証に落ちたら成果物を出さない。

前提: Python 3 + Pillow、ffmpeg / ffprobe が使えること。
素材（base/ghost, base/shell）は読み取りのみで、変更しない。
"""
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

from PIL import Image, ImageDraw

SIZE = 256          # 本体側の辺（px）
WAIT_MS = 100       # コマの表示間隔（10fps）
WAIT_SLOW_MS = 200  # サーフェス4用（周期は同じ2.0秒、フレームレートだけ半分）
LOOP_FRAMES = 20
RUNONCE_FRAMES = 20
QUIET_FRAMES = 10
CONTENT_DIAMETER = 234          # 中身の円の直径（枠の内側）
RING_COLOR = (0x20, 0x26, 0x2B, 255)   # 枠の暗色 #20262b
LINE_COLOR = (0xBF, 0xE9, 0xF5, 255)   # 内側の明色線 #bfe9f5
SS = 4  # 描画のスーパーサンプリング倍率

# 本体側アニメーションの番号ブロック。1100 番台はシステム側予約のため使わない。
FRAME_BLOCKS = {0: 1000, 1: 1200, 2: 1300, 3: 1400, 4: 1500, 5: 1600, 6: 1700, 8: 1800}
# システム側としてテンプレートから取り込むファイル
SYSTEM_FILES = [f"surface{i}.png" for i in range(10, 19)] + [f"surface{i}.png" for i in range(1100, 1116)]

# 作成したゴーストの OnBoot はアニメーションのデモ用に差し替える（梱包用コピーの中だけ）。
# 待機時間は各サーフェスのアニメーション長に合わせる: 本体側は全て 2000ms
# （ループ・一回再生とも 20コマ×100ms、サーフェス4 は 10コマ×200ms）、静止画は 1000ms。
# システム側サーフェス11 はテンプレートのアニメーション（16コマ×125ms = 2000ms）。
DEMO_ONBOOT = (
    "\\1\\s[11]\\_w[2000]"
    "\\0\\s[1]\\_w[2000]"
    "\\0\\s[2]\\_w[2000]"
    "\\1\\s[12]\\0\\s[3]\\_w[2000]"
    "\\1\\s[13]\\0\\s[4]\\_w[2000]"
    "\\1\\s[14]\\0\\s[5]\\_w[2000]"
    "\\1\\s[15]\\0\\s[6]\\_w[2000]"
    "\\1\\s[16]\\0\\s[7]\\_w[1000]"
    "\\1\\s[17]\\0\\s[8]\\_w[2000]"
    "\\1\\s[18]\\_w[1000]"
    "\\0\\s[0]\\1\\s[10]"
)

REQUIRED_STATES = ("idle", "making_something", "milestone_level_up", "waiting_for_subagents", "working")


# ---------- 入力（avatar.json → 素材の対応表） ----------

def resolve(path_str: str) -> pathlib.Path:
    p = pathlib.Path(path_str)
    return p if p.is_absolute() else pathlib.Path.home() / p


def glob1(directory: pathlib.Path, pattern: str) -> pathlib.Path:
    hits = sorted(directory.glob(pattern))
    if not hits:
        sys.exit(f"素材が見つかりません: {directory}/{pattern}")
    return hits[0]


def load_materials(avatar_json: pathlib.Path) -> tuple[str, dict]:
    data = json.loads(avatar_json.read_text(encoding="utf-8"))
    name = data["name"]
    still = resolve(data["image_path"])
    if not still.exists():
        sys.exit(f"静止画が見つかりません: {still}")
    light_videos = {}
    for state in REQUIRED_STATES:
        if state not in data["video_variants"]:
            sys.exit(f"avatar.json に状態 {state} の動画がありません。代替で埋めずに報告してください。")
        p = resolve(data["video_variants"][state])
        if not p.exists():
            sys.exit(f"動画が見つかりません: {p}")
        light_videos[state] = str(p)

    # 黒背景版は命名規則から機械的に作る
    stem = still.name[: -len(still.suffix)]  # 例: avatar-<id>-0
    dark_still = still.parent / f"{stem}-darkmode.webp"
    if not dark_still.exists():
        sys.exit(f"黒背景版の静止画が見つかりません: {dark_still}")
    dark_idle = glob1(still.parent, f"{stem}-darkmode-idle-attempt-*.mp4")
    dark_working = glob1(still.parent, f"{stem}-darkmode-working-attempt-*.mp4")
    dark_videos = {}
    for state in REQUIRED_STATES:
        light_path = data["video_variants"][state]
        if light_path == data["video_variants"]["idle"]:
            dark_videos[state] = str(dark_idle)
        elif light_path == data["video_variants"]["working"]:
            dark_videos[state] = str(dark_working)
        else:
            dark_videos[state] = str(glob1(still.parent, f"{stem}-darkmode-{state}-attempt-*.mp4"))

    variants = {
        "white": {"still": str(still), "videos": light_videos},
        "black": {"still": str(dark_still), "videos": dark_videos},
    }
    return name, variants


# ---------- 素材の切り出し ----------

def probe_duration(video: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


_frame_cache: dict[tuple[str, float], Image.Image] = {}


def frame_at(video: str, t: float) -> Image.Image:
    """動画の t 秒地点のコマを1枚取る。"""
    key = (video, round(t, 3))
    if key not in _frame_cache:
        out = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True, check=True,
        )
        _frame_cache[key] = Image.open(io.BytesIO(out.stdout)).convert("RGB")
    return _frame_cache[key]


def sample_video(video: str, n: int, offset: float = 0.0) -> list[Image.Image]:
    """再生時間を n で割り、その間隔で n 枚を採取する。コマ数は常に n 枚。

    offset は位相（0.5 で半周期ずらし）。動画が短い場合は間隔が狭くなる
    （＝モーションが速くなる）だけで、枚数は変わらない。
    """
    d = probe_duration(video)
    last = max(d - 0.02, 0.0)
    return [frame_at(video, min((i + offset) * d / n, last)) for i in range(n)]


# ---------- 画像の合成 ----------

def _mask(diameter: int) -> Image.Image:
    big = Image.new("L", (SIZE * SS, SIZE * SS), 0)
    d = ImageDraw.Draw(big)
    inset = (SIZE - diameter) * SS // 2
    d.ellipse([inset, inset, SIZE * SS - 1 - inset, SIZE * SS - 1 - inset], fill=255)
    m = big.resize((SIZE, SIZE), Image.LANCZOS)
    return m.point(lambda a: 255 if a >= 128 else 0)


CONTENT_MASK = _mask(CONTENT_DIAMETER)


def make_ring() -> Image.Image:
    big = SIZE * SS
    ring = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    d.ellipse([0, 0, big - 1, big - 1], fill=RING_COLOR)
    inner = 12 * SS  # 暗色リングは半径116から外側
    d.ellipse([inner, inner, big - 1 - inner, big - 1 - inner], fill=(0, 0, 0, 0))
    r0 = 13 * SS  # 明色線は半径115付近、幅2px
    d.ellipse([r0, r0, big - 1 - r0, big - 1 - r0], outline=LINE_COLOR, width=2 * SS)
    return ring.resize((SIZE, SIZE), Image.LANCZOS)


RING = make_ring()


def content_of(img: Image.Image) -> Image.Image:
    im = img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(im, (0, 0), CONTENT_MASK)
    return out


def full_surface(img: Image.Image) -> Image.Image:
    """中身＋枠の完結した窓画像。素体にもアニメーションのコマにもこれを使う。"""
    out = content_of(img)
    out.alpha_composite(RING)
    return out


# ---------- シェルの組み立て ----------

def assign_frames(videos: dict[str, str]) -> dict[int, dict]:
    """対応表: サーフェス番号 → 素材とアニメーションの割り当て。

    採取はすべて sample_video による等間隔サンプリング（枚数固定）。
    同じ動画を使うサーフェス同士は offset=0.5 で位相をずらして区別する。
    """
    mile = videos["milestone_level_up"]
    making = videos["making_something"]
    waiting = videos["waiting_for_subagents"]
    working = videos["working"]
    return {
        0: dict(src=None, frames=sample_video(videos["idle"], LOOP_FRAMES), interval="always", wait=WAIT_MS),
        1: dict(src=None, frames=sample_video(mile, RUNONCE_FRAMES), interval="runonce", wait=WAIT_MS),
        2: dict(src=None, frames=sample_video(mile, RUNONCE_FRAMES, offset=0.5), interval="runonce", wait=WAIT_MS),
        3: dict(src=None, frames=sample_video(waiting, LOOP_FRAMES, offset=0.5), interval="always", wait=WAIT_MS),
        4: dict(src=None, frames=sample_video(waiting, QUIET_FRAMES), interval="always", wait=WAIT_SLOW_MS),
        5: dict(src=None, frames=sample_video(making, LOOP_FRAMES), interval="always", wait=WAIT_MS),
        6: dict(src=None, frames=sample_video(working, LOOP_FRAMES), interval="always", wait=WAIT_MS),
        7: dict(src=frame_at(working, probe_duration(working) / 2), frames=None, interval=None, wait=None),
        8: dict(src=None, frames=sample_video(making, LOOP_FRAMES, offset=0.5), interval="always", wait=WAIT_MS),
    }


def build_shell(variant: str, mats: dict, tpl_shell: pathlib.Path, out_root: pathlib.Path, name: str) -> pathlib.Path:
    """シェルのフォルダ一式を作る。部品は parts-<variant>/ に置き、フォルダには入れない。"""
    shell_dir = out_root / f"shell-{variant}"
    if shell_dir.exists():
        shutil.rmtree(shell_dir)
    shell_dir.mkdir(parents=True)
    parts_dir = out_root / f"parts-{variant}"
    if parts_dir.exists():
        shutil.rmtree(parts_dir)
    parts_dir.mkdir(parents=True)

    plan = assign_frames(mats["videos"])

    blocks = ["charset,UTF-8\n\ndescript\n{\nversion,1\n}\n"]
    for sid in range(9):
        p = plan[sid]
        base_src = p["frames"][0] if p["frames"] else p["src"]
        full_surface(base_src).save(shell_dir / f"surface{sid}.png")
        content_of(base_src).save(parts_dir / f"content_surface{sid}.png")
        lines = [f"surface{sid}", "{", f"element0,base,surface{sid}.png,0,0"]
        if p["frames"]:
            block0 = FRAME_BLOCKS[sid]
            lines.append(f"animation0.interval,{p['interval']}")
            for i, fr in enumerate(p["frames"]):
                fid = block0 + i
                full_surface(fr).save(shell_dir / f"surface{fid}.png")
                lines.append(f"animation0.pattern{i},overlay,{fid},{p['wait']},0,0")
            if p["interval"] == "runonce":
                lines.append(f"animation0.pattern{len(p['frames'])},overlay,-1,{p['wait']},0,0")
        lines += ["collisionex0,Window,circle,128,128,127", "}\n"]
        blocks.append("\n".join(lines))

    tpl_surfaces = (tpl_shell / "surfaces.txt").read_text(encoding="utf-8")
    blocks.append(tpl_surfaces[tpl_surfaces.index("surface10") :].rstrip() + "\n")
    (shell_dir / "surfaces.txt").write_text("\n".join(blocks), encoding="utf-8")

    for fn in SYSTEM_FILES:
        shutil.copy(tpl_shell / fn, shell_dir / fn)
    RING.save(parts_dir / "frame_large.png")
    shutil.copy(shell_dir / "surface0.png", shell_dir / "thumbnail.png")
    for fn in ("descript.txt", "install.txt", "readme.txt"):
        text = (tpl_shell / fn).read_text(encoding="utf-8").replace("__ASSISTANT_NAME__", name)
        (shell_dir / fn).write_text(text, encoding="utf-8")
    return shell_dir


# ---------- 梱包（nar の配置規則はここだけが知る） ----------

def prepare_tree(src: pathlib.Path, name: str, dest: pathlib.Path, onboot_demo: bool = False) -> pathlib.Path:
    """テンプレートのコピーを作り、名前のプレイスホルダを差し替える。

    satori_license.txt は改変禁止のため対象外（プレイスホルダも含まない）。
    onboot_demo の場合、辞書の OnBoot をアニメーション確認用のデモに差し替える。
    """
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    for f in dest.rglob("*.txt"):
        if f.name == "satori_license.txt":
            continue
        t = f.read_text(encoding="utf-8")
        if "__ASSISTANT_NAME__" in t:
            f.write_text(t.replace("__ASSISTANT_NAME__", name), encoding="utf-8")
    if onboot_demo:
        dic_path = dest / "master" / "dic_muse.txt"
        dic = dic_path.read_text(encoding="utf-8")
        dic = re.sub(r"＊OnBoot\n[^\n]*", lambda m: f"＊OnBoot\n{DEMO_ONBOOT}", dic, count=1)
        dic_path.write_text(dic, encoding="utf-8")
    return dest


def pack_shell(shell_dir: pathlib.Path, out_path: pathlib.Path) -> pathlib.Path:
    """シェル単体: フォルダの中身をそのまま平置きする。サブフォルダは認めない。"""
    files = []
    for f in sorted(shell_dir.rglob("*")):
        if f.is_dir():
            sys.exit(f"シェルのフォルダにサブフォルダがあります: {f}（シェルは平置きが単位です）")
        files.append(f)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.name)
    return out_path


def pack_ghost(ghost_src: pathlib.Path, shell_dir: pathlib.Path, out_path: pathlib.Path) -> pathlib.Path:
    """ゴースト一式: ルートに install.txt・readme.txt、配下に ghost/master と shell/master。

    ghost_src は prepare_tree で用意したフォルダ（install.txt, readme.txt, master/）。
    shell_dir はシェルのフォルダ一式で、その中身が shell/master になる。
    """
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in ("install.txt", "readme.txt"):
            z.write(ghost_src / fn, fn)
        for f in sorted((ghost_src / "master").rglob("*")):
            if f.is_file():
                z.write(f, "ghost/master/" + f.relative_to(ghost_src / "master").as_posix())
        for f in sorted(shell_dir.rglob("*")):
            if f.is_file():
                z.write(f, "shell/master/" + f.relative_to(shell_dir).as_posix())
    return out_path


# ---------- 検証 ----------

def _check_texts_and_refs(texts: dict, files: set, prefix: str) -> list[str]:
    errors = []
    for n, t in texts.items():
        if "__ASSISTANT_NAME__" in t:
            errors.append(f"プレイスホルダ残存: {n}")
    surf = texts.get(prefix + "surfaces.txt")
    if surf is None:
        errors.append(f"surfaces.txt がない: {prefix}")
        return errors
    refs = set(re.findall(r"surface(\d+)\.png", surf)) | set(re.findall(r"overlay,(-?\d+),", surf))
    for r in refs:
        if r != "-1" and f"surface{r}.png" not in files:
            errors.append(f"参照先なし: surface{r}.png")
    return errors


def validate_shell_nar(nar: pathlib.Path) -> list[str]:
    """シェル単体の検証: 全ファイルが平置きで、参照が閉じていること。"""
    errors = []
    z = zipfile.ZipFile(nar)
    names = z.namelist()
    for n in names:
        if "/" in n:
            errors.append(f"サブフォルダに入っている: {n}")
    texts = {n: z.read(n).decode("utf-8") for n in names if n.endswith(".txt")}
    files = set(names)
    errors += _check_texts_and_refs(texts, files, "")
    for n in names:
        if n.endswith(".png"):
            im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
            if im.getpixel((0, 0))[3] != 0:
                errors.append(f"四隅が透明でない: {n}")
    return errors


def validate_ghost_nar(nar: pathlib.Path, tpl_shell: pathlib.Path, base_body: bool = False) -> list[str]:
    errors = []
    z = zipfile.ZipFile(nar)
    names = z.namelist()
    texts = {n: z.read(n).decode("utf-8") for n in names if n.endswith(".txt")}
    files = {n.split("/")[-1] for n in names if n.startswith("shell/master/")}
    errors += _check_texts_and_refs(texts, files, "shell/master/")
    tpl_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tpl_shell.glob("surface*.png")}
    for n in names:
        if not n.startswith("shell/master/surface"):
            continue
        fn = n.split("/")[-1]
        m = re.fullmatch(r"surface(\d+)\.png", fn)
        if not m:
            continue
        sid = int(m.group(1))
        data = z.read(n)
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        if im.getpixel((0, 0))[3] != 0:
            errors.append(f"四隅が透明でない: {fn}")
        is_system = 10 <= sid <= 18 or 1100 <= sid <= 1115
        if is_system:
            if fn in tpl_hashes and hashlib.sha256(data).hexdigest() != tpl_hashes[fn]:
                errors.append(f"システム側がテンプレートと相違: {fn}")
        elif not base_body:
            if fn in tpl_hashes and hashlib.sha256(data).hexdigest() == tpl_hashes[fn]:
                errors.append(f"本体側がテンプレートのまま: {fn}")
            if im.getpixel((128, 4)) != RING_COLOR:
                errors.append(f"枠が付いていない: {fn} (128,4)={im.getpixel((128, 4))}")
    return errors


# ---------- モード ----------

def report(tag: str, nar: pathlib.Path, errors: list[str]) -> bool:
    if errors:
        print(f"[{tag}] 検証失敗:")
        for e in errors:
            print(" -", e)
        nar.unlink()
        return False
    print(f"[{tag}] OK: {nar.name} ({nar.stat().st_size} bytes)")
    return True


def mode_build(base_dir: pathlib.Path, work: pathlib.Path) -> int:
    avatar_json = work / "avatar.json"
    if not avatar_json.exists():
        sys.exit(f"avatar.json が作業フォルダにありません: {work}")
    name, variants = load_materials(avatar_json)
    tpl_shell = base_dir / "shell"
    ok = True
    for variant, mats in variants.items():
        shell_dir = build_shell(variant, mats, tpl_shell, work, name)
        ghost_src = prepare_tree(base_dir / "ghost", name, work / f".ghost-src-{variant}", onboot_demo=True)
        ghost_nar = pack_ghost(ghost_src, shell_dir, work / f"ghost-{variant}.nar")
        shell_nar = pack_shell(shell_dir, work / f"shell-{variant}.nar")
        shutil.rmtree(ghost_src)
        ok &= report(f"ghost-{variant}", ghost_nar, validate_ghost_nar(ghost_nar, tpl_shell))
        ok &= report(f"shell-{variant}", shell_nar, validate_shell_nar(shell_nar))
    return 0 if ok else 1


def mode_base(base_dir: pathlib.Path, work: pathlib.Path) -> int:
    avatar_json = work / "avatar.json"
    if not avatar_json.exists():
        sys.exit(f"avatar.json が作業フォルダにありません: {work}（名前の取得に使います）")
    name = json.loads(avatar_json.read_text(encoding="utf-8"))["name"]
    tpl_shell = base_dir / "shell"
    ghost_src = prepare_tree(base_dir / "ghost", name, work / ".ghost-src-base", onboot_demo=True)
    shell_src = prepare_tree(tpl_shell, name, work / ".shell-src-base")
    ghost_nar = pack_ghost(ghost_src, shell_src, work / "template-ghost.nar")
    shell_nar = pack_shell(shell_src, work / "template-shell.nar")
    shutil.rmtree(ghost_src)
    shutil.rmtree(shell_src)
    ok = report("template-ghost", ghost_nar, validate_ghost_nar(ghost_nar, tpl_shell, base_body=True))
    ok &= report("template-shell", shell_nar, validate_shell_nar(shell_nar))
    return 0 if ok else 1


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    base_dir = root / "base"
    work = pathlib.Path.cwd()
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "build":
        return mode_build(base_dir, work)
    if mode == "base":
        return mode_base(base_dir, work)
    sys.exit(f"不明なモードです: {mode}（build か base）")


if __name__ == "__main__":
    sys.exit(main())
