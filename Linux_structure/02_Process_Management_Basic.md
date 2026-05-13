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

