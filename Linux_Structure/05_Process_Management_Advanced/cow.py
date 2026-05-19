#!/usr/bin/python3

# fork() を使うためのモジュール
import os

# free や ps など、外部コマンドを実行するためのモジュール
import subprocess

# 子プロセスを終了するときに使う
import sys

# mmapでメモリ領域を確保するためのモジュール
import mmap


# 確保するメモリサイズ
# 100 * 1024 * 1024 = 100MiB
ALLOC_SIZE = 100 * 1024 * 1024

# ページサイズ
# 多くのLinux x86_64環境では 4096 bytes = 4KiB
PAGE_SIZE = 4096


def access(data):
    # mmapで確保したメモリ領域に、ページ単位で書き込む関数
    #
    # 1ページにつき1バイト書き込めば、そのページは実際にアクセスされたことになる
    # これにより、デマンドページングでは物理メモリが割り当てられる
    for i in range(0, ALLOC_SIZE, PAGE_SIZE):
        data[i] = 0


def show_meminfo(msg, process):
    # メモリ状態を表示するための関数

    # どのタイミングの情報かを表示する
    print(msg)

    # システム全体のメモリ使用量を表示する
    print("freeコマンドの実行結果:")
    subprocess.run(["free", "-h"])

    # 現在のプロセスのメモリ関連情報を表示する
    print("{}のメモリ関連情報".format(process))

    # psで現在のプロセスのRSS、メジャーフォールト、マイナーフォールトを表示する
    #
    # rss:
    #   Resident Set Size
    #   実際に物理メモリ上に載っているメモリ量
    #
    # maj_flt:
    #   メジャーフォールト数
    #   ディスクI/Oを伴うページフォルト
    #
    # min_flt:
    #   マイナーフォールト数
    #   ディスクI/Oを伴わないページフォルト
    #
    # os.getpid():
    #   現在実行中のプロセスID
    subprocess.run(["ps", "-o", "rss,maj_flt,min_flt", "-p", str(os.getpid())])

    print()


# 100MiBの匿名メモリ領域をmmapで確保する
#
# -1:
#   ファイルに紐づかない匿名メモリを作る
#
# flags=mmap.MAP_PRIVATE:
#   プライベートマッピング
#
# この時点では仮想メモリ領域を確保しただけで、
# 物理メモリが全量割り当てられているとは限らない
data = mmap.mmap(-1, ALLOC_SIZE, flags=mmap.MAP_PRIVATE)

# 確保した100MiBの全ページに書き込む
#
# これにより、親プロセス側では100MiBぶんの物理メモリが実際に割り当てられる
access(data)

# fork() 前の親プロセスのメモリ状態を表示する
show_meminfo("*** 子プロセス生成前 ***", "親プロセス")


# fork() で子プロセスを作る
#
# fork() 直後、子プロセスは親プロセスのメモリ空間を引き継いだように見える
# ただし、実際に物理メモリをすぐ丸ごとコピーするわけではない
#
# Linuxでは Copy-on-Write により、親子で同じ物理ページを共有し、
# どちらかが書き込んだタイミングで初めてページをコピーする
pid = os.fork()

# fork() に失敗した場合
if pid < 0:
    print("fork()に失敗しました。", file=sys.stderr)

# pid == 0 は子プロセス側
elif pid == 0:
    # fork() 直後の子プロセスのメモリ状態を表示する
    #
    # Copy-on-Write により、子プロセスは親のメモリを持っているように見えるが、
    # 物理メモリはまだ大きくコピーされていない
    show_meminfo("*** 子プロセス生成直後 ***", "子プロセス")

    # 子プロセス側で100MiBの全ページに書き込む
    #
    # ここで親と共有していたページに書き込むため、
    # Copy-on-Write が発生する
    #
    # その結果、子プロセス用に物理ページがコピーされ、
    # RSSやマイナーフォールトが増える
    access(data)

    # 子プロセスがメモリへ書き込んだ後の状態を表示する
    show_meminfo("*** 子プロセスによるメモリアクセス後 ***", "子プロセス")

    # 子プロセスを終了する
    sys.exit(0)


# 親プロセス側
#
# 子プロセスの終了を待つ
# wait() により、子プロセスの終了ステータスも回収する
os.wait()

