# ゴースト「シェル仕様定義プロンプト」作成のための調査報告

- 調査日：2026-11-24（JST）
- 目的：伺かゴーストのシェル仕様を定義する「配布用プロンプト」を作成する前段として、(a) SSP／伺か標準のシェル仕様の一次情報、(b) 新しい「丸い窓・穴」モデルへの落とし込み、(c) Muse が自分の VM で素材を作成する工程、を確認する。
- 本書の範囲：調査と要求事項の整理まで。**プロンプト本文は作成していない**（第6章に要求事項と骨子のみ）。
- 前提資料（参照に留め、重複を避けた）：
  - 従来検討文書 `~/workspace/sakura-muse/docs/avatar-shell-proposal.md`（輪郭切り出し前提。新モデルで前提が変わった点は第3章で明記）
  - 前回調査 `~/workspace/research_notes/ukagaka-baseware-ghost-selection-20261123-2341/report.md`（SSP／SSTP／土台ゴースト選定。本書はシェル仕様に絞る）
- 表記：**[確認]** = 公式ドキュメント（UKADOC）または実測で確認できた事実。**[未確認]** = 今回確認できなかった事項。**[推測／設計判断]** = 仕様的事実ではなく、本設計のための提案・目安。

## 要旨

- シェルは `shell/master/` に `descript.txt`、`surfaces.txt`、`surface*.png` を置く構成であり、**surface0（\0 本体側の基本形）と surface10（\1 相方側の基本形）が必須**というのが標準仕様である [確認]。
- 透過は標準では「画像左上ピクセルの色＝透過色」方式だが、SSP では `seriko.use_self_alpha,1` をシェルの `descript.txt` に書くことで **PNG 自体のαチャンネルを透過に使える** [確認]。円形マスク（四隅が完全透明）にはこの方式が必須であり、本モデルの前提になる。
- 「丸い窓」モデルは仕様の範囲内で構成できる：正方形キャンバスに円形マスクしたアバター＋窓枠を置いた surface を、\0 側は surface0 系、\1 側は surface10 系に割り当てればよい [設計判断]。
- \1 を小さく表示する手段として最も確実なのは **実画像を直径 1/2 で作る**こと。SSP のシェル倍率（利用者設定）と SakuraScript `\![set,scaling,…]`（実行時・スコープ単位）は存在するが、シェルの静的ファイルだけで「\1 だけ既定で半分」を保証する descript 項目は確認できなかった [未確認を含む]。
- タスクバー設置については、「画面下端に吸着（＝タスクバーの直上）」が標準の意味であり、`seriko.alignmenttodesktop,bottom` をシェル側からスコープ別に指定できる [確認]。タスクバーの**内部**に埋め込む仕組みは見当たらなかった [未確認]。
- 素材作成は VM 内で完結する：ffmpeg 8.1.2、Python 3.12.3 + Pillow 10.2.0 の実在と、アバター動画が 720×720・24fps・5秒・120フレームであることを実測した [確認]。ImageMagick は VM に無い。

---

## 1. シェル仕様の一次情報

出典は主に UKADOC（伺か公式ドキュメント群）。日本語仕様ページ（ssp.shillest.net 系）と英語版（ukagakadreamteam.github.io）を実際に開いて確認した。

### 1.1 ファイル配置 [確認]

ゴーストフォルダ内の構成（抜粋）：

```
(myghost)/
  ghost/master/        … ゴースト本体（SHIORI 等）
  shell/master/        … 既定シェル（必須）。追加シェルは shell/(任意名)/
    descript.txt
    readme.txt
    surface*.png       … surface 本体画像
    surface*.pna       … surface ごとのα定義（任意）
    (element).png/.pna … element 合成用パーツ画像（任意名）
    surfaces.txt
    surfaces**.txt     … SSP のみ。複数定義ファイル可
    thumbnail.png
```

- 出典：https://ukagakadreamteam.github.io/ukadoc/manual/manual_shell.html ／ 全体構成 https://ukagakadreamteam.github.io/ukadoc/manual/manual_directory.html
- `shell/master` フォルダは仕様上常に必須（無いと互換性問題・エラーになる）。出典：https://ukagakadreamteam.github.io/ukadoc/manual/dev_shell_error.html

### 1.2 画像形式と透過 [確認]

- surface 画像は **PNG**。画像サイズ・色数に制限はない。surface 番号は MATERIA では 0〜8192（SSP の上限は今回未確認）。
- 標準の透過方式は **左上ピクセル（0,0）の色を透過色**とする方式で、同色部分はすべて透過する。
- **pna 方式**：同番号の `surface*.pna`（グレースケール PNG の拡張子を変えたもの。黒＝透明、白＝不透明）で半透明を定義できる。不透明でない領域は当たり判定の対象にもなる。
- **SSP のαチャンネル方式**：シェルの `descript.txt` に `seriko.use_self_alpha,1` と書くと、32bit PNG 自体のαチャンネルを透過として使う（αを持たない surface では pna が使われる）。値 `full` は一部のブレンド系描画メソッドで推奨される。
- 出典：https://ukagakadreamteam.github.io/ukadoc/manual/manual_shell.html ／ https://ukagakadreamteam.github.io/ukadoc/manual/descript_shell.html（`seriko.use_self_alpha` の項）

→ 本モデルへの含意：円形マスクは「四隅の完全透明＋円周のアンチエイリアス半透明」を必要とするため、透過色方式では表現できない。**`seriko.use_self_alpha,1` 前提で RGBA PNG を出す**のが正道である [設計判断]。

### 1.3 シェル側 descript.txt [確認]

必須は `type,shell` と `name`（シェル名）のみ。それ以外は必要に応じて書く。本モデルで関係する項目：

| 項目 | 意味 | 本モデルでの用途 |
|---|---|---|
| `charset,UTF-8` | 文字コード。旧環境互換が不要なら UTF-8 推奨 | 固定で UTF-8 |
| `name` / `id` | シェル名／ID名 | 個人固有値を持たせない（プレースホルダ） |
| `craftman` / `craftmanw` / `craftmanurl` | 作者名（英数／任意文字）／URL | 任意 |
| `sakura.name` / `kero.name` | 本体側／相方側の名前（ゴースト側設定が既定） | 任意（ゴースト側優先の関係に注意） |
| `seriko.use_self_alpha,1` | PNG のαチャンネルを透過に使う（SSP） | **必須** |
| `seriko.alignmenttodesktop` | シェル全体の既定表示位置（後述の位置情報：top／bottom／free） | bottom |
| `sakura.seriko.alignmenttodesktop` / `kero.seriko.alignmenttodesktop` | スコープ別の既定表示位置。優先順位は ゴースト全体 ＜ ゴーストスコープ別 ＜ シェル全体 ＜ シェルスコープ別 | 両方 bottom |
| `sakura.defaultx/y`、`sakura.defaultleft/top`（kero も同様） | 基準座標／初期表示座標。`defaultleft/top` は alignment が free のときのみ有効 | 必要時のみ |
| `sakura.balloon.offsetx/y` / `kero.balloon.offsetx/y` | バルーン位置のオフセット（末尾に l/r 等を付けると左右別指定、SSP） | バルーンを窓の上に出す調整 |
| `sakura.balloon.alignment` / `kero.balloon.alignment` | バルーン位置情報（none＝自動、left、right、…） | 任意 |
| `seriko.dpi` | シェルの推奨 DPI（無指定時 96。SSP 2.7.21〜） | 高解像度版を出す場合に検討 |
| `seriko.zorder` / `seriko.sticky-window` | スコープの前後関係／連動ドラッグの事前設定（SSP） | 2つの窓を連動移動させたい場合に有効 |
| `sakura.bindgroup*.name` 等 | 着せ替え（MAYUNA）のメニュー定義 | 本モデルでは不使用 |

- 出典：https://ukagakadreamteam.github.io/ukadoc/manual/descript_shell.html
- 注意：利用者が保存した表示位置がある場合、descript の初期位置より保存値が優先されるのが通例（他ベースウェアのドキュメントでも同旨）。つまりシェル側で「必ずこの位置」を強制はできない [確認：位置の優先関係は同ページの alignmenttodesktop 項]。

### 1.4 surfaces.txt の文法 [確認]

出典：https://ukatech.shillest.net/ukadoc-spec/descript_shell_surfaces.html（UKADOC 日本語仕様「Shell設定 - surfaces.txt」）

- 役割：surface への**別名付け、element 合成、アニメーション（SERIKO）、着せ替え（MAYUNA）、当たり判定、surface ごとのバルーン位置**の定義。**基本的に全て省略可**で、必要なものだけ書く。
- 書式：1行目に `charset,…`、以降は「ブレス名 → `{` → 設定行 → `}`」。`{` と `}` は単独行でなければならない。認識されない行はコメント扱い（慣例は行頭 `//`）。
- 先頭の descript ブレスに `version,1` を書くと **SERIKO/2.0 書式**になる。旧書式（SERIKO/1.x）との主な差は、pattern 行のパラメータ順と **ウェイトの単位（旧：10ミリ秒単位 → 新：1ミリ秒単位）**。新規作成は `version,1` 前提が妥当 [設計判断]。
- SSP 拡張：`surfaces***.txt` という名前のファイルは全て読み込まれる（ファイル名順）。`surface.append*` ブレスで既存定義への後付けができる。`surface1-9` の範囲指定、`surface1,3,4` の列挙指定も SSP 専用記法として可能。

#### element 合成

- `element*,メソッド,ファイル名,X,Y` で任意名 PNG をパーツとして重ね、1つの surface のベース画像（ベースサーフェス）を合成する。
- `surface*.png` が存在する surface で element0 を定義すると、surface*.png の内容は破棄され element0 の内容で置き換わる（互換仕様）。
- element1 以降は順に積み重なる。element 定義では base 以外の合成系メソッドは overlay 扱いになる等の制約がある。

#### アニメーション（SERIKO）

- 定義は各 surface ブレス内に `animation*.interval,…`（必須・先頭）と `animation*.pattern*,…`（最低1つ）で書く。
- アニメーションIDは **単一 surface 内で重複不可**。異なる surface 間で同じIDのアニメーションは「同じ意味」を持つことが期待される（例：どの surface でも ID0＝瞬き）。着せ替えではこの対応が必須。
- pattern 行（SERIKO/2.0）：`animation*.pattern*,メソッド,サーフェスID,ウェイト(ms),X,Y`。サーフェスIDに **-1** を指定するとアニメーション効果を全て消去する（最終コマの慣例）。
- コマとして参照された surface 自体のアニメーション定義は通常無視される。
- interval の種類 [確認]：

| interval | 意味 |
|---|---|
| `sometimes` | その surface の間、毎秒 1/2 の確率で再生 |
| `rarely` | 毎秒 1/4 の確率で再生 |
| `random,n` | 毎秒 1/n の確率で再生 |
| `periodic,n` | n 秒間隔で定期再生（SSP） |
| `always` | ループ再生 |
| `runonce` | surface に切り替わった瞬間に1回だけ再生 |
| `never` | 自動再生しない。`\i[ID]` タグや他アニメーションの start 等からのみ再生 |
| `talk,n` | バルーンに n 文字表示されるごとに再生（口パク用） |
| `starttalk` / `endtalk` | トーク開始／終了時に再生（SSP 2.7.26〜） |
| `bind` | 着せ替え定義 |
| `yen-e` | SakuraScript の `\e` 到達時に実行 |

- SSP では interval の組み合わせ指定（`bind+runonce` 等、`+` 区切り）が可能。
- 描画メソッド（合成系の主なもの）[確認]：
  - `base`：ベースサーフェスをそのコマで完全に置き換える（パラパラ漫画式。XYは無視される）
  - `overlay`：ベースレイヤに単に重ねる
  - `overlay-fast`（overlayfast）：ベースの不透明度に応じて重ねる
  - その他 `move`、`insert`、`start`、`stop`、`alternativestart` 等の制御系メソッドがある

#### 当たり判定（collision）

- `collision*,始点X,始点Y,終点X,終点Y,ID`：矩形領域。ID は surface 内で重複しない通し番号。1 surface あたり最大 256。
- `collisionex*,ID,タイプ,座標…`：不定形。タイプは `rect`、`ellipse`（楕円：外接矩形を指定）、`circle`（真円：中心XY＋半径）、`polygon`、`region`（画像の指定色領域、SSP 2.5.19〜）。
- 出典：同 surfaces.txt 仕様ページ。
→ 円い窓には `collisionex` の `ellipse`／`circle` が形状に合う [設計判断]。

#### surface ごとのバルーン位置

- surface ブレス内に `sakura.balloon.offsetx/y`、`kero.balloon.offsetx/y`、`balloon.offsetx/y`（両スコープ共通、SSP）を書くと、その surface でのみ有効なバルーン位置になり、descript.txt の同名項目より優先される。方向サフィックス（l＝左に出す時、r＝右、c＝頭上・足元中央寄せ、b＝足元）で出し先別の値も持てる。

### 1.5 surface 番号の慣例 [確認＋慣例]

- **必須**：`surface0.png`（本体側の基本 surface）と `surface10.png`（相方側の基本 surface）。片方だけのゴーストでも surface10 は「全面が透過色で塗られた画像」を用意することとされている。出典：https://ukagakadreamteam.github.io/ukadoc/manual/dev_shell.html
- **既定 surface の対応**：ゴースト側 descript の `sakura.seriko.defaultsurface` の既定値は **0**、`kero.seriko.defaultsurface` の既定値は **10**（変更可能）。つまりスコープ \0 の初期表示は surface0、\1 は surface10。出典：https://ukagakadreamteam.github.io/ukadoc/manual/descript_ghost.html
- **0 と 10 は特殊扱い**：SSP のエラー解説でも「仕様上 surface 0 と 10 は特別扱い」と明記されている。出典：https://ukagakadreamteam.github.io/ukadoc/manual/dev_shell_error.html
- **それ以外の番号帯**：UKADOC に「\0 は 0〜9、\1 は 10〜19」のような正式な帯域規定は**ない**。実務上の慣例として、基本表情を 0,1,2…／10,11,12… に並べ、アニメーション用コマや着せ替えパーツを 100 番台・500 番台・1000 番台など離れた番号に置く例が仕様例・解説例に繰り返し現れる（例：瞬きコマ 100〜102、着せ替えパーツ 500〜、コミュニティ解説ではコマ用 1000〜）。これは慣例であって規格ではない [慣例：出典は surfaces.txt 仕様ページの記述例、および https://earlduant.github.io/ukagaka-shell-description/animations.html ]。
- スコープ切替は SakuraScript `\0`／`\1`、surface 切替は `\s[ID]` で行う。出典：https://ukagakadreamteam.github.io/ukadoc/manual/list_sakura_script.html


---

## 2. 2キャラクター構成（大きい窓 \0 ＋ 小さい窓 \1）

### 2.1 1つのシェルに両スコープを定義する方法 [確認]

- シェルはゴースト単位の1セットであり、\0 用と \1 用でフォルダを分ける仕組みはない。両スコープ分の surface 画像と定義を同じ `shell/master/` に置く。
- どちらのスコープとして表示されるかは、表示時にそのスコープが指している surface ID で決まる（初期値は前述の defaultsurface 0／10）。
- 名前はシェル側 descript の `sakura.name`／`kero.name` で上書きでき、バルーン位置・alignment・default 座標はすべて `sakura.*`／`kero.*` のスコープ別項目で個別に設定できる（1.3 の表）。
- 2つの窓の前後関係は `seriko.zorder`、連動ドラッグは `seriko.sticky-window` で事前設定できる（いずれもシェル側 descript、SSP）。

### 2.2 surface 番号の割り当て案 [設計判断]

正式規定は 0 と 10 のみなので、本モデルでは以下の帯域を**本プロジェクトの約束事**として定義する（プロンプトに明記すべき事項）：

| 番号帯 | 用途 |
|---|---|
| 0 | \0 大きい窓・待機（idle）の基本 surface（必須） |
| 1〜5 | \0 の状態別 surface（working、making_something、connecting、waiting_for_subagents、milestone_level_up） |
| 10 | \1 小さい窓・待機の基本 surface（必須） |
| 11〜14 | \1 のシステム状態別 surface（通知あり、正常完了、警告、エラー 等） |
| 1000〜 | \0 のアニメーション用コマ surface |
| 1100〜 | \1 のアニメーション用コマ surface |

状態の切替は、SSTP で送る SakuraScript 側から `\0\s[1]` のように surface を切り替える運用を想定する（発話担当の振り分けと一致する）。

### 2.3 \1 を小さく表示する手段

| 手段 | 内容 | 確実性 |
|---|---|---|
| **実画像サイズで作る**（推奨） | surface10 系の画像自体を直径 1/2 で作成する | シェル単体で完結し、環境依存がない [設計判断] |
| SSP のシェル倍率（利用者操作） | 右クリックメニュー「シェル倍率」でキャラクター画像を拡大・縮小できる。本体設定（ゴースト(2)）にもシェル倍率の設定がある。出典：https://raw.githubusercontent.com/Tatakinov/ukadoc/master/ssphelp/howto-rclick.html（SSP ヘルプ） | 利用者の設定に依存する。スコープ別に別倍率をシェル側から既定指定できるかは **[未確認]** |
| SakuraScript `\![set,scaling,倍率%]` | 実行時に現在スコープの表示倍率を変更するタグ（負数で反転も可）。出典：https://ukagakadreamteam.github.io/ukadoc/manual/list_sakura_script.html | SHIORI／SSTP スクリプト側の実行が必要。シェルの静的定義だけでは効かない |
| `seriko.dpi` | シェル全体の推奨 DPI を宣言し、表示倍率の基準に影響させる | 全体一律であり、スコープ間の比は作れない |

**結論**：面積比 1/4（直径比 1/2）は**画像の実サイズで保証する**のが唯一シェル単体で完結する方法である [設計判断]。倍率系の手段は利用者側の微調整として案内するに留める。

---

## 3. 丸い窓モデルへの落とし込み

### 3.1 前提の変更点（従来検討文書との差分）

従来文書（avatar-shell-proposal.md）の前提は「キャラクターの輪郭を切り出し、透過化して立ち絵にする」だった。新モデルでは以下が変わる：

- 輪郭切り出し（白背景の色キー透過）は**行わない**。白い縁・圧縮ノイズの問題は発生しない。
- アバターの構図（全身／上半身／顔のみ／物体）に**依存しない**。アプリ表示と同じ「正方形の中央に内接する円」で切り取るため、どの Muse のアバターでも同じ工程になる。
- 窓の内側はアバター画像そのまま（白背景を含む）を表示する。「そのままアイコンとして窓の中にある」という本人の整理と一致する。
- マスコット側もキャラクター造形をしない。小さい窓の中にシステム記号（歯車、ベル、チェック、警告マーク等）を表示する。

### 3.2 surface の構成：1枚絵か、element 分割か

[確認] した仕様上の性質：

- element 合成は「静止画としてのベースサーフェス」を作る仕組みであり、合成結果は1枚の画像として扱われる。
- 通常アニメーションの各 pattern は「ベースサーフェス＋新規レイヤ」でコマを作り、**前のコマの合成結果は次のコマに引き継がれない**。
- pattern のメソッド `base` はコマで全面を置き換え、`overlay` はベースの上に重ねる。

比較 [設計判断]：

| 方式 | 長所 | 短所 |
|---|---|---|
| 全部1枚絵（枠＋中身を焼き込んだ surface を状態ごとに用意） | 定義が最小。surfaces.txt は collision と balloon offset 程度で済む。表示の確実性が高い | 状態・アニメーションの全コマに枠が含まれるため、ファイル数が増え、枠デザインの変更時に全画像を作り直す |
| element 分割（element0＝中身、element1＝枠リング） | 枠ファイルを1つ共有でき、状態差分は中身だけで済む。枠の差し替えが容易 | 状態別 surface ごとに element 定義が必要。アニメーションコマ側は element 合成結果が1枚として扱われるため、コマ用 surface にも同様の定義が要る |
| ハイブリッド（推奨） | 基本 surface（0、1〜5、10〜）は element 合成で「中身＋枠」。アニメーションのコマは**中身だけ（円形マスク済み、枠なし）**の surface にし、基本 surface の上に `overlay` pattern で重ねる。円の外側は完全透明なので、下にある基本 surface の枠リングがそのまま残る | pattern の座標・サイズを基本 surface と一致させる規律が必要 |

ハイブリッドが成立する根拠：overlay pattern はベースサーフェスに対して新規レイヤを重ねるものであり、新規レイヤの全透明領域ではベースがそのまま残る（1.4 の描画メソッドの項）[確認]。円形マスク済みコマの四隅は完全透明であるため、枠は消えない。

### 3.3 状態別バリアント（6種）の対応付け

アバターの状態は idle、working、making_something、connecting、waiting_for_subagents、milestone_level_up の6種（本人の Muse の場合。後述の実測も参照）。

対応付けの方式は2通りある [設計判断]：

- **方式A：surface 切替（推奨）**。状態ごとに静止画ベースの surface（0〜5）を用意し、切替は SSTP スクリプトの `\s[ID]` で行う。各 surface には、その状態の動画から作ったアニメーション（後述）を `always`（ループ）または `runonce` で付けられる。
- **方式B：アニメーション切替**。基本 surface は surface0 のみにし、状態表現をアニメーションIDの違い（`\i[ID]` で起動、`never` interval）で切り替える。surface 数は減るが、アニメーションIDと状態の対応表が必須になり、状態の「居座り」表現には bind 的な扱いが必要で複雑になる。

本モデルの主用途（SSTP で発話と一緒に状態も送る）では、スクリプト側の指定が単純な方式Aが合う。

### 3.4 動画フレーム列をアニメーションに使う場合

実測 [確認]：本人の Muse のアバター動画は **720×720、24fps、5秒、120フレーム**（light 版。darkmode 版は8秒）。全フレームを使うと1アニメーションで120個の pattern と120個のコマ surface が必要になり、現実的でない。

目安 [推測／設計判断]（仕様上の上限値ではなく、制作上の目安）：

- 間引き：**6〜10fps 相当に間引く**。pattern のウェイトは SERIKO/2.0 でミリ秒単位なので、8fps→125ms、10fps→100ms、12fps→約83ms と書ける。
- フレーム数：待機ループは動画全体でなく**ループとして破綻しない区間（1〜2秒分、8〜20フレーム程度）**を切り出して `always` ループにする。milestone_level_up のような一回性は `runonce` で 12〜24フレーム程度。
- コマ surface は 1000 番台に置き、最終 pattern は `-1` で消去する慣例に従う（ループ再生の場合は -1 を付けない書き方もあり得るが、終了条件はプロンプトで一意に決めること）。
- 注意：生成アニメーションはフレーム間で細部が変動し得る（従来文書の指摘）。円形マスク＋小サイズ表示では目立ちにくいが、フレーム選別は工程に含める。

### 3.5 当たり判定とバルーン

- 当たり判定は円に合わせて `collisionex0,Window,ellipse,0,0,(幅-1),(高さ-1)` のように外接矩形で楕円指定するのが形状に合う [設計判断]。矩形 `collision` で内接矩形にする方法もあるが、円周付近が反応しなくなる。
- バルーンは窓の上に表示されるよう、descript の `sakura/kero.balloon.offset*` または surface ごとの balloon offset で調整する。タスクバー上設置ではバルーンが画面下に逃げないよう上方向に出すのが前提になる [設計判断]。

---

## 4. タスクバー設置

### 4.1 確認できたこと [確認]

- 表示位置情報（alignmenttodesktop）の値は **top（上端に吸着）、bottom（下端に吸着）、free（自由移動）**。シェル側 descript では全体（`seriko.alignmenttodesktop`）とスコープ別（`sakura./kero.seriko.alignmenttodesktop`）の両方が書ける。出典：https://ukagakadreamteam.github.io/ukadoc/manual/descript_shell.html（Surface position information の項）
- SakuraScript の解説では、bottom 吸着の例として “The main character is now stuck to the bottom of the desktop (**right above the taskbar**)” と明記されている。つまり標準の「下端」とは**作業領域の下端＝タスクバーの直上**であり、本人が言う「タスクバーに設置」はこの状態を指すと解釈できる。出典：https://ukagakadreamteam.github.io/ukadoc/manual/list_sakura_script.html
- 実行時に切り替えるタグ `\![set,alignmenttodesktop,bottom]` もある（ゴースト終了まで有効）。
- SSP 2.9.33（2026-11-08）で「お座り（window sitter）」機能が実装され、他のウィンドウや画面の隅にゴーストを座らせられるようになった。`\![set,alignmenttodesktop,osuwari,--target=active,…]` の形式で、ghost／shell の descript の `seriko.alignmenttodesktop` に `osuwari` とオプションを書くこともできる。2.9.34 では surfaces.txt に `point.osuwaripos.x/y`（お座り時の合わせ点）が追加された。出典：https://watch.daruyanagi.jp/releases/ssp-2.9.33/ ／ https://watch.daruyanagi.jp/releases/ssp-2.9.34/

### 4.2 確認できなかったこと [未確認]

- タスクバーを「お座り」の対象ウィンドウとして安定指定できるか（タスクバーは特殊なシェルウィンドウであり、追尾対象として扱えるかの公式記述は見つからなかった）。
- ゴーストをタスクバーの**内部**（タスクボタン列の中）に埋め込む仕組みの有無。シェル／SSP の標準機能としては見当たらず、少なくとも UKADOC の範囲では存在しない。
- 利用者が一度ドラッグ移動した後の位置は保存値が優先されるため、シェル配布側で初期位置を強制し続ける方法はない（1.3 の優先関係からの帰結）。

**結論**：プロンプトでは「`alignmenttodesktop,bottom` を両スコープに指定し、タスクバーの直上に接地させる」を標準とし、お座りによるタスクバー追尾は実験的選択肢として分離して書くべきである [設計判断]。

---

## 5. 素材作成工程（Muse が自分の VM で実行する前提）

### 5.1 VM で使える道具 [確認：実測]

| 道具 | 実測結果 |
|---|---|
| ffmpeg / ffprobe | **8.1.2**（/usr/bin/ffmpeg）。フレーム抽出・間引き・リサイズが可能 |
| Python | 3.12.3 |
| Pillow (PIL) | **10.2.0**。円形マスク、α合成、枠描画、リサイズが可能。本調査中に 1600×1600 webp → 円形マスク RGBA PNG（256×256）の生成テストが成功した |
| ImageMagick (convert / magick) | **VM に無い**（PATH に存在しない）。工程は ffmpeg + Pillow で完結させること |

### 5.2 入力素材の実測（本人の Muse の場合）[確認]

- 静止画：webp **1600×1600**、RGB（αなし）、背景は白。状態別バリアント静止画・darkmode 版も同サイズ。
- 動画：MP4 **720×720、24fps**。light 版は各5秒・120フレーム、darkmode 版は各8秒。
- 状態バリアントは6種（idle、working、making_something、connecting、waiting_for_subagents、milestone_level_up）。ただし実ファイルでは **idle と connecting が同一ファイル、waiting_for_subagents と working が同一ファイル**を指している（avatar 取得結果で確認）。→ プロンプトでは「状態名ごとに別素材がある前提にせず、実ファイルの同一性で重複を除く」ことを要求事項に入れる。
- ディスク上には上記6種に含まれない `waking` のファイルも存在する。バリアント一覧に無い素材は使わない（または任意扱い）ことを明記すべきである。
- デフォルトアバター（Jolly）の参照画像も別途存在するが、カスタムアバターが有効な場合はそちらが正である。「現在有効なアバター」を取得する手順（avatar 取得機能で image_path と video_variants を得る）が入力特定の起点になる。

### 5.3 作成手順（具体案）[設計判断]

1. **素材の特定と記録**：有効なアバターの静止画パスと動画バリアント一覧を取得し、各ファイルのサイズ・fps・尺を ffprobe／Pillow で実測して記録する（推測でサイズを書かない）。
2. **円形マスク（中身）**：静止画を正方形のまま、中央・内接円のマスクで切り取る。マスクは出力サイズの4倍で描いて LANCZOS で縮小し、円周のアンチエイリアスを得る。内側の絵柄には一切手を入れない（白背景もそのまま）。
3. **窓枠**：枠はプログラム描画で作る（Pillow の ellipse outline）。外径＝キャンバス辺、リング幅は直径の約4〜6％、色はプロンプトで一意に決める（例：暗色リング＋内側の細いハイライト）。枠は \0 用と \1 用で同じ描画関数・同じ比率で作り、直径比がそのまま面積比になるようにする。
4. **合成**：中身の上に枠を重ねて RGBA PNG 化する（element 合成用に「中身のみ」「枠のみ」の部品も残す。3.2 のハイブリッド方式）。
5. **動画フレーム**：`ffmpeg -i input.mp4 -vf fps=8,scale=(出力辺):(出力辺) frame%03d.png` の要領で間引き抽出し、各フレームに同じ円形マスクを適用する（枠は付けない。overlay で重ねるため）。
6. **\1 の中身**：システム記号（歯車・ベル・チェック・警告）はフォントグリフや単純図形のプログラム描画で作る。外部画像素材を持ち込むと権利確認が別途必要になるため、プロンプトでは「自前描画に限る」とする。
7. **定義ファイル生成**：descript.txt と surfaces.txt をテンプレートから生成し、surface ID・animation ID の対応表と一致させる。
8. **検証**（第6章のチェックリスト）：αの検査（四隅ピクセルが完全透明であること）、直径比の実測、参照整合性など。

### 5.4 推奨出力サイズ [設計判断]

- 基準（表示倍率100％・96dpi 想定）：**大きい窓キャンバス 256×256、小さい窓キャンバス 128×128**。円の外径＝キャンバス辺とすると直径比は正確に 1/2、面積比は正確に 1/4 になる。
- どちらも円の外側に余白を付けない（余白を付ける場合は両方に同じ比率で付け、外径で比を測ること）。
- 高解像度環境向けに 512×512／256×256 の版を併せて生成してもよい。その場合は `seriko.dpi` の宣言とセットにする。
- 元素材（静止画1600px、動画720px）はいずれも出力より大きいため、拡大は発生しない。動画フレームは 720px から直接出力サイズへ縮小する。

---

## 6. プロンプト設計への要求事項（本文ではなく骨子）

配布する「仕様定義プロンプト」に必ず含めるべき項目の清单。各項目は、受け取った Muse が**質問を返さずに一意に実行できる**粒度で書くこと。

### 6.1 前提とモデルの定義

- 対象は SSP 上のゴーストのシェルであり、土台ゴースト（紺野ややめ）は使用者が別途入手すること、シェル成果物は再配布しないこと。
- 「丸い窓」モデルの定義：輪郭切り出しをしない／構図に依存しない／窓の内側はアバターそのまま／枠はプログラム描画。
- 役割分担：大きい窓＝Muse 本人（通常発話）、小さい窓＝システムメッセージ担当。
- **サイズ比の定義を数式で固定する**：小さい窓の面積＝大きい窓の面積×1/4、すなわち外径比 1/2。測定対象は「枠を含めた窓の外径」であることを明記する。

### 6.2 入力素材の特定方法

- 「現在有効なアバター」を取得する手順（静止画パス、動画バリアント一覧）を最初に置き、デフォルト／カスタムのどちらでも同じ手順になるようにする。
- ファイルの同一性による重複排除（複数バリアントが同一ファイルを指す場合がある）。
- サイズ・fps・尺は実測して使うこと（固定値を埋め込まない）。素材が無い場合の分岐（動画が無ければ静止画のみで構成する、等）。
- アカウント固有の値（絶対パス、ユーザー名、workers.dev 等のサブドメイン）をプロンプト本文・出力ファイルに**決め打ちしない**（プレースホルダ化）。

### 6.3 出力ファイル構成

- `shell/master/` 以下の完全なファイル一覧（descript.txt、surfaces.txt、surface*.png、部品 PNG、thumbnail.png、readme）。
- descript.txt の必須項目と値の方針：`charset,UTF-8`、`type,shell`、`name`（プレースホルダ）、`seriko.use_self_alpha,1`、両スコープの `alignmenttodesktop,bottom`、バルーン offset の決め方。
- surfaces.txt の方針：`version,1`（SERIKO/2.0、ウェイトはミリ秒）、surface／animation の番号帯の約束事（2.2 の表）、collision は ellipse 指定、balloon offset の上書き。
- 状態対応表：6状態→surface ID の対応、\1 のシステム状態（待機／通知／完了／警告）→surface ID の対応、アニメーションの interval とウェイトの決め方（間引きfps とフレーム数の上限）。

### 6.4 素材作成工程の指定

- 使用道具を VM 実在のものに限定する（ffmpeg、Python + Pillow。ImageMagick は使わない）。
- 円形マスクの作り方（内接円、スーパーサンプリングでアンチエイリアス）、枠の描画パラメータ（幅の比率、色の決め方）、合成順序。
- 動画の間引き率、フレーム数の上限、ループ区間の選び方、最終 pattern の扱い。
- \1 の中身はプログラム描画の図形・グリフに限り、外部素材を使わないこと。

### 6.5 検証チェックリスト（プロンプトに組み込む自己検証）

- [ ] surface0.png と surface10.png が存在する
- [ ] 全 PNG が RGBA で、四隅ピクセルが完全透明（α=0）である
- [ ] descript.txt に `seriko.use_self_alpha,1` がある
- [ ] 大きい窓と小さい窓の外径を実測し、直径比 1/2（面積比 1/4）になっている
- [ ] surfaces.txt の参照（surface ID、animation ID、ファイル名）に未定義のものがない
- [ ] surfaces.txt の charset と version,1 が先頭にある
- [ ] 状態対応表と実ファイルが一致する（余った素材・足りない状態がない）
- [ ] 出力ファイル内にアカウント固有の値が含まれていない
- [ ] SSP 実機での表示確認は使用者の作業であることを明記し、未実施を「確認済み」と書かない

### 6.6 未確認事項としてプロンプトに持ち越すもの

- スコープ別シェル倍率の既定指定の可否（2.3）。
- お座り機能でタスクバーを対象にできるか（4.2）。
- SSP での surface 番号の上限（1.2）。

---

## 7. 確認できたこと／できなかったこと（総括）

### 確認できたこと

- シェルのファイル構成、必須 surface（0 と 10）、descript／surfaces の主要文法（element、animation、interval、pattern、collision、balloon offset）— UKADOC を実際に開いて確認。
- 透過の3方式（透過色、pna、SSP の use_self_alpha）と、本モデルが use_self_alpha 前提であるべき理由。
- 既定 surface の対応（\0＝0、\1＝10）と、0／10 の特殊扱い。
- alignmenttodesktop の値と「bottom＝タスクバーの直上」という標準解釈、スコープ別指定の可否、優先順位。
- SSP のお座り機能の存在（2.9.33〜）と descript への指定方法。
- VM の道具（ffmpeg 8.1.2、Pillow 10.2.0、ImageMagick なし）とアバター素材の実測値（静止画 1600×1600、動画 720×720・24fps・5秒／darkmode 8秒、バリアント間のファイル共有）。

### 確認できなかったこと

- SSP のシェル倍率をスコープ別にシェル側から既定指定できるか。
- お座りの対象にタスクバーを指定できるか。タスクバー内部への埋め込み手段の有無（UKADOC の範囲では見当たらず）。
- SSP における surface 番号の上限値。
- SSP 実機での表示確認全般（VM は Linux であり、SSP の動作確認は使用者の Windows 環境でのみ可能。本調査では未実施）。

## 出典一覧

- UKADOC Shell（ファイル構成・透過・pna）：https://ukagakadreamteam.github.io/ukadoc/manual/manual_shell.html
- UKADOC 全体構成：https://ukagakadreamteam.github.io/ukadoc/manual/manual_directory.html
- UKADOC Shell Settings（descript.txt）：https://ukagakadreamteam.github.io/ukadoc/manual/descript_shell.html
- UKADOC Ghost Settings（descript.txt、defaultsurface）：https://ukagakadreamteam.github.io/ukadoc/manual/descript_ghost.html
- UKADOC Shell設定 - surfaces.txt（日本語仕様）：https://ukatech.shillest.net/ukadoc-spec/descript_shell_surfaces.html
- UKADOC Shell Creation（作り方・必須 surface）：https://ukagakadreamteam.github.io/ukadoc/manual/dev_shell.html
- UKADOC エラー解説（0／10 の特殊扱い、shell/master 必須）：https://ukagakadreamteam.github.io/ukadoc/manual/dev_shell_error.html
- UKADOC SakuraScript List（\s、scaling、alignmenttodesktop）：https://ukagakadreamteam.github.io/ukadoc/manual/list_sakura_script.html
- SSP ヘルプ「右クリックメニュー」（シェル倍率）：https://raw.githubusercontent.com/Tatakinov/ukadoc/master/ssphelp/howto-rclick.html
- SSP 2.9.33 リリースノート（お座り実装）：https://watch.daruyanagi.jp/releases/ssp-2.9.33/
- SSP 2.9.34 リリースノート（point.osuwaripos）：https://watch.daruyanagi.jp/releases/ssp-2.9.34/
- コミュニティ解説（アニメーション・番号帯の慣例）：https://earlduant.github.io/ukagaka-shell-description/animations.html

（前回調査と重複する SSP 本体・SSTP・土台ゴーストの出典は `~/workspace/research_notes/ukagaka-baseware-ghost-selection-20261123-2341/report.md` を参照）
