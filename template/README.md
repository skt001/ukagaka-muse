# ゴースト・テンプレート 里々ベース（template/）

- 内容：SHIORI に里々（整備班版）を用いた最小ゴーストのテンプレート一式。nar としてインストールできる形に組み立ててある。
- 成果物：`ghost.nar`（本フォルダに保存。実体は ZIP で、ルートに install.txt を含むゴースト一式。そのまま SSP にインストールして動作確認に使える）
- ソース：`ghost/` が nar の中身そのもの（バイナリを除く）。`ghost/ghost/master/satori.dll` とシェルの PNG は nar 側にのみ含まれる。

## プレイスホルダと差し替え（使用前に必須）

このテンプレートは配布用の祖であり、名前と宛先はプレイスホルダのまま入っている。**使う前に、自分の値へ差し替えること。** 差し替えは、組み立てる Muse 本人が自分の情報で行う。

- `__ASSISTANT_NAME__` … その Muse 自身のアシスタント名（install.txt の name、ゴーストの name / sakura.name、シェル名 `__ASSISTANT_NAME__-window`、readme の表題に使用）
- `__MAIL_ADDRESS__` … その Muse 自身の Muse Mail アドレス（辞書の「メールを書く」の mailto 宛先）

差し替えの手順（例）：

1. `grep -rn '__ASSISTANT_NAME__\|__MAIL_ADDRESS__' ghost/` で残っている箇所をすべて洗い出す
2. `grep -rl '__ASSISTANT_NAME__' ghost/ | xargs sed -i 's/__ASSISTANT_NAME__/<自分の名前>/g'` のように一括置換する（宛先も同様）
3. 再度 grep し、プレイスホルダが1つも残っていないことを確認してから nar を組み立てる

## 構成

```
ghost.nar
├ install.txt            … type,ghost / name,__ASSISTANT_NAME__ / directory,muse
├ readme.txt
├ ghost/master/
│  ├ descript.txt        … shiori,satori.dll、sstp.allowunspecifiedsend,1
│  ├ satori.dll          … 里々（整備班版）本体 ※nar のみに含む
│  ├ satori_license.txt  … 里々のライセンス（同梱が再配布の条件。無変更）
│  ├ satori_conf.txt     … ＊初期化のみ。＄喋り間隔は設定しない
│  └ dic_muse.txt        … 最小辞書
└ shell/master/
   ├ descript.txt
   ├ surfaces.txt
   ├ surface0.png / surface10.png / thumbnail.png  … 仮シェル ※nar のみに含む
```

## 辞書（dic_muse.txt）の内容

- `＊OnBoot` … 発話せず `\0\s[0]\1\s[10]` のサーフィス表示のみ
- `＊OnClose` … 定義しない。里々の仕様で、定義がなければ `\-` が返り無言で終了する
- `＊OnMouseDoubleClick` … 選択肢3件（muse.ai を開く／メールを書く／閉じる）
- 選択時は ID と同名の文が実行され、`\j[https://muse.ai]`、`\j[mailto:...]` を返す
- ランダムトークは、`＄喋り間隔` を設定せず、`＊OnTalk` と名前のない文を置かないことで、構造として発生しない

## 仮シェルについて

- 立ち絵は差し替え前提の仮素材。背景（単色 #d9dee2）の中央に単色の円（#7f8b93）を置いただけの構成
- \0 は 256×256、\1 は 128×128
- 本番のシェル（丸い窓モデル）へ差し替える際は、shell/master の中身を入れ替える。シェルの作り方は `docs/shell-spec-prompt.md`（仕様定義プロンプト）を参照

## 里々の入手元とライセンス

- satori.dll は、里々公式テンプレート「ポストと狛犬 V2」（ukatech/POST_and_KOMAINU_V2）の同梱物と同一ファイル（962,560 バイト）を使用
- 再配布は satori_license.txt の条件による（ライセンス文書の同梱と不変更）。本 nar はこの条件を満たす
- 本リポジトリの他の成果物（文書・辞書・設定類）のライセンスは MIT（ルートの LICENSE を参照）。里々は MIT の対象外

## 未確認事項

- 選択肢のみからなる文（OnMouseDoubleClick）の表示形式は実機未検証
- nar のファイル名は ghost.nar とした。インストール先フォルダ名は install.txt の directory,muse で決まる
