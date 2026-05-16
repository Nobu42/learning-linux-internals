#!/usr/bin/python3

# NumPyでデータファイルを読み込むために使う
import numpy as np

# PNG画像をJPG画像に変換するために使う
from PIL import Image

# matplotlib本体
# グラフ描画ライブラリ
import matplotlib

# 一時的に作ったPNGファイルを削除するために使う
import os

# GUI画面を使わずに画像ファイルへ描画する設定
# SSH接続先やサーバ環境では画面がないことが多いため、この指定が便利
matplotlib.use('Agg')

# 実際にグラフを描くための pyplot を読み込む
import matplotlib.pyplot as plt

# グラフ内のフォント設定
# 日本語を表示するために sans-serif 系フォントを使う
plt.rcParams['font.family'] = 'sans-serif'

# 日本語フォントとして TakaoPGothic を指定する
plt.rcParams['font.sans-serif'] = "TakaoPGothic"


def plot_sched(concurrency):
    # sched.py が出力した 0.data, 1.data, ... を読み込み、
    # タイムスライスの様子をグラフ化する関数
    #
    # concurrency は並列度
    # 例: concurrency=3 なら 0.data, 1.data, 2.data を読む

    # 新しいグラフ全体を作る
    fig = plt.figure()

    # 1行1列の領域のうち、1番目のグラフ領域を作る
    ax = fig.add_subplot(1, 1, 1)

    # 各負荷処理プロセスの data ファイルを読み込む
    for i in range(concurrency):
        # "{}.data".format(i) は、0.data, 1.data のようなファイル名になる
        #
        # dataファイルは以下の形式:
        #   経過時間[ミリ秒]    進捗[%]
        #
        # unpack=True により、1列目を x、2列目を y として読み込む
        x, y = np.loadtxt("{}.data".format(i), unpack=True)

        # 読み込んだデータを散布図として描画する
        # s=1 は点のサイズを小さくする指定
        ax.scatter(x, y, s=1)

    # グラフのタイトルを設定する
    ax.set_title("タイムスライスの可視化(並列度={})".format(concurrency))

    # x軸のラベルを設定する
    ax.set_xlabel("経過時間[ミリ秒]")

    # x軸の最小値を0にする
    ax.set_xlim(0)

    # y軸のラベルを設定する
    ax.set_ylabel("進捗[%]")

    # y軸を0%から100%までにする
    ax.set_ylim([0, 100])

    # 凡例に表示する名前を作る
    legend = []
    for i in range(concurrency):
        legend.append("負荷処理" + str(i))

    # 凡例を表示する
    ax.legend(legend)

    # まずPNGファイルとして保存する
    pngfilename = "sched-{}.png".format(concurrency)

    # 最終的に保存したいJPGファイル名
    jpgfilename = "sched-{}.jpg".format(concurrency)

    # matplotlibでPNG画像を保存する
    fig.savefig(pngfilename)

    # PillowでPNGを開き、RGB形式に変換してJPGとして保存する
    # JPGはアルファチャンネルを扱えないため、RGBに変換している
    Image.open(pngfilename).convert("RGB").save(jpgfilename)

    # 中間ファイルのPNGは不要なので削除する
    os.remove(pngfilename)


def plot_avg_tat(max_nproc):
    # cpuperf.data を読み込み、
    # プロセス数と平均ターンアラウンドタイムの関係をグラフ化する関数
    #
    # ターンアラウンドタイム:
    #   プロセス開始から終了までにかかった時間

    # 新しいグラフ全体を作る
    fig = plt.figure()

    # 1つのグラフ領域を作る
    ax = fig.add_subplot(1, 1, 1)

    # cpuperf.data を読み込む
    #
    # 想定形式:
    #   プロセス数    平均ターンアラウンドタイム    スループット
    #
    # 3列目はここでは使わないので _ に受ける
    x, y, _ = np.loadtxt("cpuperf.data", unpack=True)

    # プロセス数 x と平均ターンアラウンドタイム y を散布図にする
    ax.scatter(x, y, s=1)

    # x軸の範囲を 0 から max_nproc+1 までにする
    ax.set_xlim([0, max_nproc + 1])

    # x軸ラベル
    ax.set_xlabel("プロセス数")

    # y軸の最小値を0にする
    ax.set_ylim(0)

    # y軸ラベル
    ax.set_ylabel("平均ターンアラウンドタイム[秒]")

    # まずPNGで保存する
    # 注意: ファイル名は avg-tat のほうが自然
    pngfilename = "avg-tat.png"

    # 最終的なJPGファイル名
    jpgfilename = "avg-tat.jpg"

    # PNG保存
    fig.savefig(pngfilename)

    # PNGをJPGへ変換
    Image.open(pngfilename).convert("RGB").save(jpgfilename)

    # 中間PNGを削除
    os.remove(pngfilename)


def plot_throughput(max_nproc):
    # cpuperf.data を読み込み、
    # プロセス数とスループットの関係をグラフ化する関数
    #
    # スループット:
    #   1秒あたりに完了できたプロセス数

    # 新しいグラフ全体を作る
    fig = plt.figure()

    # 1つのグラフ領域を作る
    ax = fig.add_subplot(1, 1, 1)

    # cpuperf.data を読み込む
    #
    # 想定形式:
    #   プロセス数    平均ターンアラウンドタイム    スループット
    #
    # 2列目はここでは使わないので _ に受ける
    x, _, y = np.loadtxt("cpuperf.data", unpack=True)

    # プロセス数 x とスループット y を散布図にする
    ax.scatter(x, y, s=1)

    # x軸の範囲を 0 から max_nproc+1 までにする
    ax.set_xlim([0, max_nproc + 1])

    # x軸ラベル
    ax.set_xlabel("プロセス数")

    # y軸の最小値を0にする
    ax.set_ylim(0)

    # y軸ラベル
    ax.set_ylabel("スループット[プロセス/秒]")

    # まずPNGで保存する
    pngfilename = "throughput.png"

    # 最終的なJPGファイル名
    jpgfilename = "throughput.jpg"

    # PNG保存
    fig.savefig(pngfilename)

    # PNGをJPGへ変換
    Image.open(pngfilename).convert("RGB").save(jpgfilename)

    # 中間PNGを削除
    os.remove(pngfilename)

