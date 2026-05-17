#!/usr/bin/python3

# mmapを使って、プロセスの仮想メモリ空間に新しいメモリ領域を作る
import mmap

# 1秒ずつ待つために使う
import time

# 現在時刻つきでメッセージを表示するために使う
import datetime


# mmapで確保する仮想メモリ領域のサイズ
# 100 * 1024 * 1024 = 100MiB
ALLOC_SIZE = 100 * 1024 * 1024

# 進捗表示の単位
# 10MiBアクセスするごとにメッセージを表示する
ACCESS_UNIT = 10 * 1024 * 1024

# Linuxの一般的なページサイズ
# x86_64では多くの場合 4096 bytes = 4KiB
PAGE_SIZE = 4096


def show_message(msg):
    # 現在時刻を HH:MM:SS 形式で表示し、その後にメッセージを出す
    print("{}: {}".format(datetime.datetime.now().strftime("%H:%M:%S"), msg))


# まだmmapしていない状態
# Enter待ちにすることで、別ターミナルから free や sar などで観察しやすくする
show_message("新規メモリ領域獲得前。Enterキーを押すと100MiBの新規メモリ領域を獲得します: ")
input()

# 匿名mmapで100MiBの仮想メモリ領域を確保する
#
# -1:
#   ファイルに対応しない匿名メモリを作る
#
# ALLOC_SIZE:
#   確保するサイズ
#
# flags=mmap.MAP_PRIVATE:
#   プライベートマッピングにする
#
# 注意:
#   この時点では仮想メモリ領域を確保しただけで、
#   物理メモリが100MiB分すぐに使われるとは限らない
memregion = mmap.mmap(-1, ALLOC_SIZE, flags=mmap.MAP_PRIVATE)

# mmap後、まだ実際には全ページへアクセスしていない状態
# Enter待ちにして、mmap直後のメモリ使用量を観察できるようにする
show_message("新規メモリ領域を獲得しました。Enterキーを押すと1秒に10MiBづつ、合計100MiB新規メモリ領域にアクセスします: ")
input()

# mmapした領域にページサイズ単位でアクセスする
# 1ページにつき1バイト書き込めば、そのページが実際に使われる
for i in range(0, ALLOC_SIZE, PAGE_SIZE):
    # iバイト目に0を書き込む
    # これにより、そのページに対して書き込みアクセスが発生する
    #
    # 未割り当てのページに初めてアクセスするとページフォルトが発生し、
    # カーネルが物理メモリを割り当てる
    memregion[i] = 0

    # 10MiBごとに進捗を表示し、1秒停止する
    # これにより、別ターミナルでメモリ使用量が増える様子を観察しやすくする
    if i % ACCESS_UNIT == 0 and i != 0:
        show_message("{} MiBアクセスしました".format(i // (1024 * 1024)))
        time.sleep(1)


# 100MiB分の全ページにアクセスし終わった状態
# Enter待ちにして、アクセス後のメモリ使用量を観察できるようにする
show_message("新規獲得したメモリ領域のすべてにアクセスしました。Enterキーを押すと終了します: ")
input()

