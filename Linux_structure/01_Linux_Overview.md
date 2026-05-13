# Linuxの概要: システムコールとプログラム実行

## やったこと

Go、Python3、Cの小さなプログラムを使って、Linuxでプログラムが動くときの裏側を観察した。

主に見たもの:

- `strace`
- `write` システムコール
- `openat`, `read`, `mmap`
- CPU使用率の `%user` と `%system`
- `ldd` による共有ライブラリ確認
- 静的リンクと動的リンク

## Hello World と write

GoとPythonで `hello world` を出力し、`strace` で観察した。

```bash
strace -o hello.log ./hello
grep write hello.log
```

出力:

```text
write(1, "hello world\n", 12) = 12
```

大事なこと:

- 画面への出力は、最終的に `write` システムコールになる
- `1` は標準出力を表すファイルディスクリプタ
- `12` は書き込むバイト数
- `= 12` は実際に12バイト書き込めたという意味

## ファイルディスクリプタ

Linuxでは、プロセスが扱う入出力はファイルディスクリプタで表される。

基本:

```text
0: 標準入力
1: 標準出力
2: 標準エラー出力
3以降: open されたファイルなど
```

`write(1, ...)` は「標準出力に書く」という意味。

## Pythonスクリプトの実行

Pythonスクリプトを `./hello.py` として実行するには、以下が必要。

```python
#!/usr/bin/python3
```

```bash
chmod +x hello.py
```

大事なこと:

- shebang は「このファイルをどのプログラムで実行するか」を示す
- 実行権限がないと `./hello.py` として実行できない
- `sudo` しても、実行権限や実行形式の問題は解決しないことがある

## GoとPythonのstrace比較

Go版:

```text
237行
```

Python版:

```text
752行
```

どちらも最後は同じように `write` で出力していた。

違い:

- Goはコンパイル済み実行ファイル
- Pythonはインタプリタがスクリプトを読む
- Pythonは起動時にライブラリ読み込みなどが多い
- そのため `strace` のログが長くなる

## openat, read, mmap

Python実行時には、多くの共有ライブラリが読み込まれていた。

```bash
grep openat hello.py.log | head
grep read hello.py.log | head
grep mmap hello.py.log | head
```

意味:

- `openat`: ファイルを開く
- `read`: ファイルから読む
- `pread64`: 指定位置から読む
- `mmap`: ファイルやメモリ領域をプロセスの仮想メモリに割り当てる

特に `mmap` の `PROT_READ|PROT_EXEC` は、読み取り可能かつ実行可能な領域として割り当てるという意味。

## strace -T

`-T` を付けると、各システムコールにかかった時間が見える。

```bash
strace -T -o hello.log ./hello
grep write hello.log
```

出力:

```text
write(1, "hello world\n", 12) = 12 <0.000027>
```

意味:

- `<0.000027>` は `write` にかかった時間
- 0.000027秒 = 27マイクロ秒

## CPU使用率: user と system

CPU 0番だけを使って、無限ループを観察した。

```python
#!/usr/bin/python3

while True:
    pass
```

実行:

```bash
taskset -c 0 ./inf-loop.py &
sar -P 0 1 1
```

結果:

```text
%user 100.00
%system 0.00
%idle 0.00
```

意味:

- Pythonがユーザー空間で無限ループしている
- システムコールをほとんど呼ばない
- CPU 0番がユーザー空間の処理で使い切られている

## システムコールを呼ぶ無限ループ

```python
#!/usr/bin/python3

import os

while True:
    os.getppid()
```

実行:

```bash
taskset -c 0 ./syscall-inf-loop.py &
sar -P 0 1 1
```

結果:

```text
%user   65.35
%system 34.65
%idle    0.00
```

意味:

- `os.getppid()` は親プロセスIDを取得する
- 内部で `getppid` システムコールを呼ぶ
- システムコールを大量に呼ぶと `%system` が増える

大事なこと:

```text
%user   : ユーザー空間で使われたCPU時間
%system : カーネル空間で使われたCPU時間
%idle   : 何もしていなかったCPU時間
```

## taskset, sar, kill, jobs

```bash
taskset -c 0 ./inf-loop.py &
```

意味:

- `taskset`: プロセスが使うCPUを指定する
- `-c 0`: CPU 0番だけを使わせる
- `&`: バックグラウンドで実行する

```bash
sar -P 0 1 1
```

意味:

- `sar`: システム活動の統計を見る
- `-P 0`: CPU 0番を見る
- `1 1`: 1秒間隔で1回取得する

```bash
kill 338337
```

意味:

- 指定したPIDのプロセスにシグナルを送る
- デフォルトでは `SIGTERM` を送る

```bash
jobs
```

意味:

- 現在のシェルが管理しているバックグラウンドジョブを見る

## sar と Prometheus / Zabbix

PrometheusやZabbixが標準で内部的に `sar` を呼んでいるわけではない。

関係はこう考えるとよい。

```text
Linuxカーネル
  ↓
/proc/stat, /proc/meminfo, /proc/diskstats, /sys など
  ↓
sar / Prometheus node_exporter / Zabbix agent
```

大事なこと:

- `sar` はCLIでシステム統計を見る道具
- Prometheusは主に `node_exporter` でLinuxメトリクスを集める
- Zabbixは `Zabbix agent` でLinuxメトリクスを集める
- どれもLinuxカーネルが持つ統計情報を読む

## ldd と共有ライブラリ

`ldd` で、実行ファイルが必要とする共有ライブラリを確認した。

```bash
ldd /bin/echo
ldd /bin/cat
ldd /usr/bin/python3
```

`/bin/echo` や `/bin/cat` はシンプル。

```text
linux-vdso.so.1
libc.so.6
/lib64/ld-linux-x86-64.so.2
```

`/usr/bin/python3` はより多くのライブラリを使っていた。

例:

```text
libc.so.6
libpthread.so.0
libdl.so.2
libutil.so.1
libm.so.6
libexpat.so.1
libz.so.1
```

大事なこと:

- `ldd` は共有ライブラリ依存を見る
- `strace` は実行時に実際に開かれるファイルやシステムコールを見る
- Pythonはインタプリタ自体が多くのライブラリを使う

## dpkg-query

```bash
dpkg-query -W | grep ^lib
```

意味:

- `dpkg-query -W`: インストール済みパッケージを表示する
- `grep ^lib`: `lib` で始まるパッケージだけに絞る

注意:

- これは「今そのプログラムが使っているライブラリ」ではない
- システムにインストールされているlib系パッケージの一覧

## Cでpauseを見る

Cで `pause()` だけを呼ぶプログラムを作った。

```c
#include <unistd.h>

int main(void) {
    pause();
    return 0;
}
```

`pause()` は、シグナルを受け取るまでプロセスを停止する関数。

## 静的リンクと動的リンク

静的リンク:

```bash
cc -static -o pause pause.c
ls -l pause
ldd pause
```

結果:

```text
871832 bytes
動的実行ファイルではありません
```

動的リンク:

```bash
cc -o pause pause.c
ls -l pause
ldd pause
```

結果:

```text
16696 bytes
linux-vdso.so.1
libc.so.6
/lib64/ld-linux-x86-64.so.2
```

違い:

- 静的リンクは、必要なライブラリを実行ファイル内に含める
- そのためファイルサイズが大きくなる
- 動的リンクは、実行時に共有ライブラリを読み込む
- そのため実行ファイル自体は小さい

## 今日のまとめ

Linuxでは、プログラムの実行は以下の要素が組み合わさっている。

- プロセス
- システムコール
- ファイルディスクリプタ
- 共有ライブラリ
- 動的リンカ
- 仮想メモリ
- CPU時間の user / system
- カーネルが持つ統計情報

Hello Worldのような小さなプログラムでも、裏側では `execve`, `openat`, `read`, `mmap`, `write` などが動いている。

今日の一番大事な感覚:

```text
プログラムはユーザー空間で動き、
必要なときにシステムコールでカーネルに仕事を頼む。
```

