# プロセス管理 基礎編

## 今日やったこと

`Process_Management_Basic` フォルダで、Linuxのプロセス管理の基礎を観察した。

主に見たもの:

- `pstree`
- `ps aux`
- `fork()`
- `execve()`
- `posix_spawn()`
- ELF実行ファイル
- `/proc/<pid>/maps`
- PIE / non-PIE
- プロセスの親子関係

## 作業場所

```bash
pwd
```

```text
/home/nobu/work/learning-linux-internals/Linux_structure/Process_Management_Basic
```

## pstree

```bash
pstree
pstree -p
```

意味:

- `pstree`: プロセスを親子関係のツリーで表示する
- `-p`: PIDも表示する

大事なこと:

- Linuxのプロセスは木構造になっている
- 多くのプロセスは PID 1 の `systemd` を祖先に持つ
- `pstree` 自身も、bashから起動された1つのプロセス

SSH接続の例:

```text
systemd(1)
  ↓
sshd
  ↓
sshd
  ↓
bash
  ↓
pstree
```

`{...}` で表示されるものは、主にスレッド。

## uname

```bash
uname -a
```

見た内容:

```text
Linux ubuntu 5.15.0-139-generic ... x86_64 GNU/Linux
```

意味:

- Linuxカーネルは `5.15.0-139-generic`
- Ubuntu向けカーネル
- `x86_64` は64bit x86アーキテクチャ
- `SMP` はマルチCPU/マルチコア対応

## ps aux

```bash
ps aux
```

列の意味:

- `USER`: 実行ユーザー
- `PID`: プロセスID
- `%CPU`: CPU使用率
- `%MEM`: メモリ使用率
- `VSZ`: 仮想メモリサイズ
- `RSS`: 実メモリ使用量
- `TTY`: 端末
- `STAT`: プロセス状態
- `START`: 開始時刻
- `TIME`: 累積CPU時間
- `COMMAND`: 実行コマンド

プロセス数の確認:

```bash
ps aux --noheader | wc -l
```

意味:

- `--noheader`: 見出し行を出さない
- `wc -l`: 行数を数える

注意:

- `ps` や `wc` 自身も一瞬プロセスとして存在する
- プロセス数は観測時点のスナップショット

## カーネルスレッド

`ps aux` には以下のようなものも出る。

```text
[kthreadd]
[kworker/...]
[ksoftirqd/0]
[migration/0]
[rcu_sched]
```

大事なこと:

- `[...]` で表示されるものは、主にカーネルスレッド
- ユーザーが直接起動した普通のプログラムではない
- カーネル内部の仕事をするためのスレッド

## プロセス状態 STAT

`ps aux` の `STAT` 例:

```text
S
Ss
I
I<
```

ざっくりした意味:

- `S`: sleeping。待機中
- `R`: running。実行中または実行可能
- `I`: idle kernel thread
- `<`: 高優先度
- `s`: セッションリーダー

## fork

Pythonで `fork()` を試した。

```python
#!/usr/bin/python3

import os, sys

ret = os.fork()

if ret == 0:
    print("子プロセス:pid={}, 親プロセスのpid={}".format(os.getpid(), os.getppid()))
    exit()

elif ret > 0:
    print("親プロセス:pid={}, 子プロセスのpid={}".format(os.getpid(), ret))
    exit()

sys.exit(1)
```

実行例:

```text
親プロセス:pid=5203, 子プロセスのpid=5204
子プロセス:pid=5204, 親プロセスのpid=5203
```

大事なこと:

- `fork()` は現在のプロセスを複製して子プロセスを作る
- 親プロセスには、子プロセスのPIDが返る
- 子プロセスには、`0` が返る
- `fork()` の直後から、親と子が別々に実行を続ける
- 親と子の出力順は常に保証されない

## fork と execve

Pythonで `fork()` 後に、子プロセスだけ `execve()` した。

```python
#!/usr/bin/python3
import os, sys

ret = os.fork()

if ret == 0:
    print("子プロセス:pid={}, 親プロセスのpid={}".format(os.getpid(), os.getppid()))
    os.execve("/bin/echo", ["echo", "pid={} からこんにちは".format(os.getpid())], {})
    exit()

elif ret > 0:
    print("親プロセス:pid={}, 子プロセスのpid={}".format(os.getpid(), ret))
    exit()

sys.exit(1)
```

実行例:

```text
親プロセス:pid=5242, 子プロセスのpid=5243
子プロセス:pid=5243, 親プロセスのpid=5242
pid=5243 からこんにちは
```

大事なこと:

- `fork()` はプロセスを複製する
- `execve()` は現在のプロセスの中身を別プログラムに置き換える
- `execve()` しても PID は変わらない
- 子プロセス PID 5243 は、最初 Python で、途中から `/bin/echo` になる

流れ:

```text
python3 fork-and-exec.py
  ↓ fork()
親: python3
子: python3
  ↓ 子だけ execve("/bin/echo", ...)
親: python3
子: /bin/echo
```

## execve の環境変数

```python
os.execve("/bin/echo", ["echo", "pid={} からこんにちは".format(os.getpid())], {})
```

最後の `{}` は、NULLそのものではなく、空の環境変数辞書。

意味:

```text
環境変数なしで /bin/echo を起動する
```

Cで書くとイメージは以下に近い。

```c
char *argv[] = {
    "echo",
    "pid=5243 からこんにちは",
    NULL
};

char *envp[] = {
    NULL
};

execve("/bin/echo", argv, envp);
```

親の環境変数を引き継ぎたい場合:

```python
os.execve("/bin/echo", ["echo", "hello"], os.environ)
```

## posix_spawn

Pythonで `posix_spawn()` を試した。

```python
#!/usr/bin/python3
import os

os.posix_spawn(
    "/bin/echo",
    ["echo", "echo", "posix_spawn() によって生成されました"],
    {}
)

print("echoコマンドを生成しました。")
```

実行例:

```text
echoコマンドを生成しました。
echo posix_spawn() によって生成されました
```

大事なこと:

- `posix_spawn()` は、新しいプロセスを作って指定したプログラムを実行する
- 概念的には `fork + exec` をまとめた高水準API
- 内部実装では `fork`, `vfork`, `clone`, `execve` などが使われることがある

`argv` の見方:

```python
["echo", "echo", "posix_spawn() によって生成されました"]
```

- 1つ目の `"echo"` は `argv[0]`
- 2つ目以降が `/bin/echo` に渡される表示対象の引数

## fork + execve と posix_spawn の比較

`fork()+execve()`:

```text
親プロセス
  ↓ fork()
親プロセス + 子プロセス
  ↓ 子だけ execve()
親プロセス + /bin/echo
```

`posix_spawn()`:

```text
新しいプロセスを作って、指定したプログラムを実行する
```

まとめ:

- `fork()`: プロセスを複製する
- `execve()`: プロセスの中身を別プログラムに置き換える
- `posix_spawn()`: 新しいプロセスを作って指定プログラムを実行する

## Cの pause

前回の `pause.c` をコピーして使った。

```c
#include <unistd.h>

int main(void) {
    pause();
    return 0;
}
```

意味:

- `pause()` はシグナルを受け取るまでプロセスを停止する
- 観察用にバックグラウンドで起動しやすい

## ELF 実行ファイル

`pause.c` をコンパイルした。

```bash
cc -o pause -no-pie pause.c
readelf -h pause
readelf -S pause
```

`readelf -h` で見た重要点:

```text
型: EXEC (実行可能ファイル)
エントリポイントアドレス: 0x401050
```

意味:

- ELFファイルはLinuxの実行ファイル形式
- `EXEC` は実行可能ファイル
- エントリポイントは、CPUが実行を始めるアドレス

## ELF セクション

```bash
readelf -S pause
```

重要なセクション:

- `.interp`: 動的リンカのパス
- `.text`: 機械語命令
- `.plt`: 共有ライブラリ関数呼び出し用
- `.got`, `.got.plt`: 動的リンク時のアドレス解決に関係
- `.dynamic`: 動的リンク情報
- `.dynsym`: 動的シンボル表
- `.dynstr`: 動的シンボル名
- `.rela.dyn`, `.rela.plt`: 再配置情報
- `.rodata`: 読み取り専用データ
- `.data`: 初期値ありの書き込み可能データ
- `.bss`: 初期値なしデータ

フラグ:

- `A`: メモリに割り当てられる
- `X`: 実行可能
- `W`: 書き込み可能

例:

```text
.text : AX
.data : WA
.bss  : WA
```

## /proc/<pid>/maps

`pause()` をバックグラウンドで起動して、メモリマップを見た。

```bash
./pause &
cat /proc/<pid>/maps
```

`/proc/<pid>/maps` は、そのプロセスの仮想メモリ配置を表示する。

1行の見方:

```text
アドレス範囲  権限  ファイル内オフセット  デバイス  inode  対応するファイル
```

権限:

- `r`: read。読み取り可
- `w`: write。書き込み可
- `x`: execute。実行可
- `p`: private。コピーオンライトの私有マッピング
- `s`: shared。共有マッピング

例:

```text
00401000-00402000 r-xp ... /pause
```

意味:

- `/pause` の一部が仮想メモリに配置されている
- `r-xp` なので読み取り可、実行可
- `.text` などのコード領域に対応する

## readelf と maps のつながり

`readelf -h`:

```text
エントリポイントアドレス: 0x401050
```

`readelf -S`:

```text
.text: 0x401050
```

`/proc/<pid>/maps`:

```text
00401000-00402000 r-xp ... /pause
```

大事なこと:

- エントリポイント `0x401050` は、`r-xp` の実行可能領域に入っている
- ELFファイルの `.text` が、実行時にはプロセスの仮想メモリに配置される
- 実行ファイルや共有ライブラリは、実行時にメモリへマップされる

## libc と ld-linux

`/proc/<pid>/maps` には、`pause` 本体以外も出ていた。

例:

```text
/usr/lib/x86_64-linux-gnu/libc-2.31.so
/usr/lib/x86_64-linux-gnu/ld-2.31.so
```

意味:

- `libc-2.31.so`: C標準ライブラリ
- `ld-2.31.so`: 動的リンカ

大事なこと:

- 動的リンクされた実行ファイルでは、libcや動的リンカもプロセスのメモリ空間に入る
- 共有ライブラリも `r--p`, `r-xp`, `rw-p` のように用途別に権限が分かれて配置される

## 特殊なメモリ領域

`/proc/<pid>/maps` に出ていた特殊領域:

```text
[stack]
[vvar]
[vdso]
[vsyscall]
```

意味:

- `[stack]`: スタック。関数呼び出し、ローカル変数、戻りアドレスなどに使う
- `[vvar]`: カーネルがユーザー空間に見せる読み取り用データ領域
- `[vdso]`: 一部のカーネル情報取得を高速化するための領域
- `[vsyscall]`: 古い仕組みとの互換用領域

## PIE と non-PIE

`-no-pie` あり:

```bash
cc -o pause -no-pie pause.c
```

特徴:

- ELFの型は `EXEC`
- 実行時の配置アドレスは `0x400000` 付近になりやすい

例:

```text
00400000-00401000 r--p ... /pause
00401000-00402000 r-xp ... /pause
```

`-no-pie` なし:

```bash
cc -o pause pause.c
```

特徴:

- 多くの環境では PIE として作られる
- ELFの型は `DYN` になることがある
- ASLRにより、実行時の配置アドレスがランダム化されやすい

例:

```text
5578f2d4e000-5578f2d4f000 r--p ... /pause
5578f2d4f000-5578f2d50000 r-xp ... /pause
```

大事なこと:

- PIE は Position Independent Executable
- ASLR は Address Space Layout Randomization
- PIEだと、実行ファイル本体もランダムなアドレスに配置できる
- non-PIEだと、固定的なアドレスに配置されやすい

## file

```bash
file pause
```

例:

```text
pause: ELF 64-bit LSB executable, x86-64, dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, not stripped
```

見えること:

- ELF 64bit 実行ファイル
- x86-64向け
- 動的リンクされている
- インタプリタは `/lib64/ld-linux-x86-64.so.2`
- stripされていない

## プロセス生成の全体像

今日見た大きな流れ:

```text
bash
  ↓
Pythonスクリプト起動
  ↓
fork()
  ↓
子プロセス生成
  ↓
execve()
  ↓
子プロセスの中身が /bin/echo に置き換わる
```

シェルが外部コマンドを実行するときも、基本的にはこの考え方。

```text
bash
  ↓ fork
子プロセスを作る
  ↓ exec
子プロセスを /bin/ls や /bin/echo に置き換える
```

## 今日のまとめ

今日の一番大事な理解:

```text
Linuxのプロセスは親子関係を持つ。
新しいプログラム実行は、forkで子を作り、execで中身を置き換えることで実現できる。
```

さらに、`execve()` される実行ファイルは ELF 形式で、実行時には `/proc/<pid>/maps` に見える仮想メモリ空間へ配置される。

今日のつながり:

```text
pstree / ps
  ↓
プロセスの存在と親子関係を見る

fork()
  ↓
プロセスを増やす

execve()
  ↓
プロセスの中身を別プログラムに置き換える

ELF
  ↓
execve() で読み込まれる実行ファイル形式

/proc/<pid>/maps
  ↓
実行中プロセスの仮想メモリ配置を見る
```
## プロセスの状態

```bash
ps aux
```

`ps aux` は、Linux上で動いているプロセス一覧を見る基本コマンド。

今日のテーマでは、特に `STAT` 列を見る。

`STAT` の主な意味:

- `R`: running。実行中、または実行可能
- `S`: sleeping。割り込み可能な待機状態
- `D`: uninterruptible sleep。割り込み不能な待機状態。主にI/O待ち
- `T`: stopped。停止中
- `Z`: zombie。ゾンビプロセス
- `I`: idle kernel thread。アイドル状態のカーネルスレッド

追加記号:

- `s`: セッションリーダー
- `+`: フォアグラウンドプロセスグループ
- `<`: 高優先度
- `N`: 低優先度
- `l`: マルチスレッド

例:

```text
Ss = sleeping + session leader
R+ = running + foreground process group
```

## プロセスの終了と wait

```bash
cat wait-ret.sh
```

```bash
#!/bin/bash

false &

wait $!

echo "false コマンドが終了しました:$?"
```

実行結果:

```text
false コマンドが終了しました:1
```

意味:

- `false` は終了ステータス `1` で終了するコマンド
- `&` はバックグラウンド実行
- `$!` は直前にバックグラウンド実行したプロセスのPID
- `wait $!` は、その子プロセスの終了を待つ
- `$?` は直前のコマンドの終了ステータス

大事なこと:

```text
子プロセスの終了ステータスは、親プロセスが wait で回収する。
```

親が子の終了ステータスを回収しないと、終了した子プロセスは一時的にゾンビプロセスとして残ることがある。

## ゾンビプロセスと孤児プロセス

ゾンビプロセス:

- 子プロセスが終了した
- しかし親プロセスがまだ `wait` していない
- 終了ステータスを親に渡すため、プロセステーブル上に残っている
- `ps` では `STAT` が `Z` になる

孤児プロセス:

- 子プロセスが生きている間に、親プロセスが先に終了した
- 親を失ったプロセス
- 通常は PID 1 の `systemd` などに引き取られる

大事な違い:

```text
ゾンビプロセス:
  すでに終了しているが、親に回収されていない

孤児プロセス:
  まだ動いているが、元の親がいなくなった
```

## シグナル

シグナルは、プロセスに対してイベントや命令を伝える仕組み。

今回見た主なシグナル:

- `SIGINT`: `Ctrl-C` で送られる。通常は終了
- `SIGTSTP`: `Ctrl-Z` で送られる。通常は一時停止
- `SIGTERM`: `kill` のデフォルト。通常は終了

## SIGINT を無視する

```python
#!/usr/bin/python3
import signal

signal.signal(signal.SIGINT, signal.SIG_IGN)

while True:
    pass
```

意味:

```text
SIGINT を無視する
```

通常は `Ctrl-C` を押すと `SIGINT` が送られてプロセスは終了する。

しかし、このプログラムでは `SIGINT` を無視しているため、`Ctrl-C` では止まらない。

実行例:

```text
^C^C^C
```

何回 `Ctrl-C` を押しても終了しなかった。

## Ctrl-Z と kill

`Ctrl-Z` を押すと、`SIGTSTP` が送られてプロセスは一時停止する。

```text
^Z
[1]+  停止                  ./intigore.py
```

`jobs` で停止中のジョブを確認できる。

```bash
jobs
```

```text
[1]+  停止                  ./intigore.py
```

停止中のジョブを終了する:

```bash
kill %1
```

`kill` はデフォルトで `SIGTERM` を送る。

今回のプログラムは `SIGINT` だけを無視していたため、`SIGTERM` では終了した。

## シグナルハンドラ

今回のコード:

```python
signal.signal(signal.SIGINT, signal.SIG_IGN)
```

これは独自処理を書くのではなく、`SIGINT` を無視する設定。

独自のシグナルハンドラを書く例:

```python
#!/usr/bin/python3
import signal
import time

def handler(signum, frame):
    print("SIGINTを受け取りました。でも終了しません。")

signal.signal(signal.SIGINT, handler)

while True:
    time.sleep(1)
```

流れ:

```text
Ctrl-C
  ↓
SIGINT
  ↓
handler() が呼ばれる
  ↓
プロセスは続行
```

## シェルのジョブ管理

```bash
sleep infinity &
sleep infinity &
jobs
```

実行例:

```text
[1] 7980
[2] 7981
[1]-  実行中               sleep infinity &
[2]+  実行中               sleep infinity &
```

意味:

- `&`: バックグラウンドで実行する
- `[1]`, `[2]`: bashのジョブ番号
- `7980`, `7981`: LinuxのPID
- `+`: カレントジョブ
- `-`: 前のジョブ

大事な違い:

```text
PID:
  Linuxカーネルが管理するプロセスID

ジョブ番号:
  bashが管理する番号
```

例:

```bash
kill 7980
```

PIDを指定して終了する。

```bash
kill %1
```

bashのジョブ番号を指定して終了する。

## fg と Ctrl-Z

```bash
fg 1
```

ジョブ1をフォアグラウンドに戻す。

その状態で `Ctrl-Z` を押すと、フォアグラウンドジョブに `SIGTSTP` が送られ、一時停止する。

流れ:

```text
sleep infinity &
  ↓
バックグラウンドジョブ

fg 1
  ↓
フォアグラウンドに戻す

Ctrl-Z
  ↓
SIGTSTPで停止

kill %1
  ↓
SIGTERMで終了
```

## セッション

```bash
ps ajx
```

`ps ajx` は、ジョブ制御に関係する情報を見るのに便利。

主な列:

- `PPID`: 親プロセスID
- `PID`: 自分のプロセスID
- `PGID`: プロセスグループID
- `SID`: セッションID
- `TTY`: 制御端末
- `TPGID`: その端末のフォアグラウンドプロセスグループID

例:

```text
PPID   PID   PGID   SID   TTY    TPGID STAT COMMAND
7475  7476   7476  7476   pts/0  7988  Ss   -bash
7476  7988   7988  7476   pts/0  7988  R+   ps ajx
```

意味:

- `bash` はセッションリーダー
- `ps ajx` はbashから起動された子プロセス
- `ps ajx` の `PGID` と `TPGID` が同じなので、フォアグラウンドプロセスグループにいる

大事なこと:

```text
セッション:
  ログイン単位に近いまとまり

プロセスグループ:
  ジョブ単位に近いまとまり

制御端末:
  そのセッションが操作している端末

フォアグラウンドプロセスグループ:
  今その端末から入力を受け取れるプロセスグループ
```

## プロセスグループ

```bash
ps ajx | less
```

このコマンドは1つのジョブだが、内部では2つのプロセスが動く。

```text
ps ajx
less
```

観察例:

```text
PID   PGID   SID   TTY    TPGID STAT COMMAND
7997  7997   7476  pts/0  7997  R+   ps ajx
7998  7997   7476  pts/0  7997  S+   less
```

大事なこと:

- `ps ajx` と `less` は別プロセス
- しかし同じ `PGID` に入っている
- パイプライン全体が1つのジョブとして扱われる

図:

```text
プロセスグループ 7997
  ├─ ps ajx
  └─ less
```

`TPGID = 7997` なので、このプロセスグループが端末のフォアグラウンドにいる。

`Ctrl-C` や `Ctrl-Z` は、基本的に単一PIDではなく、フォアグラウンドプロセスグループに送られる。

## デーモン

```bash
ps ajx | grep sshd
```

観察例:

```text
PPID  PID   PGID  SID   TTY  TPGID STAT COMMAND
1     768   768   768   ?    -1    Ss   sshd: /usr/sbin/sshd -D [listener]
768   7400  7400  7400  ?    -1    Ss   sshd: nobu [priv]
7400  7475  7400  7400  ?    -1    S    sshd: nobu@pts/0
```

デーモンとは:

- 端末操作のためではなく、裏で常駐してサービスを提供するプロセス
- 制御端末を持たないことが多い
- `TTY` が `?` になりやすい
- `systemd` などから起動される

例:

- `sshd`: SSH接続を受け付ける
- `cron`: 定期実行する
- `dockerd`: Dockerを管理する
- `systemd-journald`: ログを扱う

`sshd` の流れ:

```text
systemd(1)
  ↓
sshd listener
  ↓
SSH接続を受ける
  ↓
sshd: nobu [priv]
  ↓
sshd: nobu@pts/0
  ↓
bash
```

## 今日の追記まとめ

今日の大事な理解:

```text
プロセスには状態があり、ps の STAT で確認できる。
子プロセスの終了は wait で回収する。
シグナルはプロセスを終了・停止・再開させるための仕組み。
bashはジョブ番号、プロセスグループ、フォアグラウンド制御を使ってジョブを管理している。
デーモンは端末を持たず、バックグラウンドで常駐するサービスプロセス。
```

