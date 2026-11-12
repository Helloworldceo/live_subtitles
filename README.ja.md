# Live Subtitles for macOS（リアルタイム字幕）

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · **日本語** · [한국어](README.ko.md)

Mac で**再生中のあらゆる音声**（YouTube、映画、Zoom、ゲームなど）にリアルタイムで字幕を付けます。字幕は透明なバーに表示され、全画面の Chrome を含むすべてのアプリの上に常に表示されます。

- **完全オフライン**：音声認識は [faster-whisper](https://github.com/SYSTRAN/faster-whisper) を使って Mac 上で動きます。クラウドは使いません。
- **マイクではなくシステム音声を取り込み**：無料の [BlackHole](https://github.com/ExistentialAudio/BlackHole) ドライバーを使って、スピーカーの出力を録音します。
- **英語の字幕**のほか、**日本語・中国語など約 95 言語を英語に翻訳**して表示できます。
- **低遅延**：話している途中から文字が表示されます。

---

## 入手とインストール（手順）

必要なもの：macOS 12 以降（Apple シリコン / Intel）、空き容量 約 1.5 GB

### 手順 1：プロジェクトをダウンロード

「ターミナル」を開いて、次を実行します。

```bash
git clone https://github.com/Helloworldceo/live_subtitles.git
cd live_subtitles
```

git がない場合は、GitHub の **Code → Download ZIP** でダウンロードして解凍し、`cd` でそのフォルダに移動してください。

### 手順 2：インストーラーを実行

```bash
./install.sh                 # 通常のインストール
./install.sh --translate     # 英語への翻訳用の多言語モデルも入れる
```

インストーラーは次のことを行います。
1. Homebrew がなければインストールする
2. `portaudio`、`python@3.12`、**BlackHole 2ch** ドライバーをインストールする（途中で一度だけパスワードを聞かれます）
3. `.venv` に Python 環境を作り、`requirements.txt` のパッケージをすべて入れる
4. Whisper モデルを一度だけダウンロードする（以降はオフラインで動作します）

### 手順 3：Mac を再起動

BlackHole は再起動するまで表示されません。

### 手順 4：システム音声を BlackHole にも送る

1. **Audio MIDI 設定** を開きます（Cmd+Space で "Audio MIDI" と入力）。
2. 左下の **+** から **複数出力装置を作成** を選びます。
3. **スピーカー（またはヘッドホン）** と **BlackHole 2ch** の両方にチェックを入れます。
4. **マスター装置** をスピーカーにします。**ドリフト補正** は BlackHole だけにチェックを入れ、どちらも **48,000 Hz** に設定します。
5. **システム設定 → サウンド → 出力** で、作成した **複数出力装置** を選びます。

> 複数出力装置を使っている間は、キーボードの音量キーが効きません（macOS の仕様です）。音量はプレーヤー側で調整してください。

### 手順 5：ターミナルに許可を与える

**システム設定 → プライバシーとセキュリティ** を開きます。
- **マイク**：**ターミナル** をオンにします。許可がないと無音しか録音できません。
- **入力監視**：**ターミナル** をオンにします（Ctrl+Option のショートカットを使う場合のみ必要です）。

設定したら、ターミナルを終了して開き直してください。

### 手順 6：テストして起動

```bash
./run.sh --list-devices     # 入力デバイスに "BlackHole 2ch" があるか確認
./run.sh --test-audio       # 動画を再生するとレベルバーが動く
./run.sh                    # 字幕を開始
```

---

## 使い方

| やりたいこと | コマンド |
|---|---|
| 英語の字幕 | `./run.sh` |
| **日本語の動画 → 英語の字幕** | `./run.sh --translate --language ja --model small` |
| どの言語でも英語に（自動判定） | `./run.sh --translate --model small` |
| 日本語の字幕（翻訳しない） | `./run.sh --language ja --model small` |
| すべてのオプションを表示 | `./run.sh --help` |

## ショートカット

| キー | 動作 |
|---|---|
| **Ctrl+Option+Q** | 終了 |
| **Ctrl+Option+P** | 一時停止 / 再開 |
| **Ctrl+Option+H** | バーの表示 / 非表示 |
| **Ctrl+C**（ターミナルで） | 終了 |

## よくある問題

| 症状 | 対処 |
|---|---|
| BlackHole が見つからない | Mac を再起動するか、`sudo killall coreaudiod` を実行する |
| `--test-audio` が 0 のまま | 出力が複数出力装置になっていない、BlackHole にチェックが入っていない、またはターミナルにマイクの許可がない |
| 音が出ない | BlackHole 単体ではなく、複数出力装置を選ぶ |
| 字幕が遅れる | 小さい `--model` を使うか、`--cpu-threads 8` を追加する |

詳しいガイド（英語）は [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) にあります。
