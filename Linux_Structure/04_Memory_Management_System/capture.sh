#!/bin/bash

<<COMMENT
demand-paging.py プロセスについて、1秒ごとにメモリ関連情報を出力します。

各行の先頭には、情報を採取した時刻を表示します。
その後に続くフィールドの意味は以下の通りです。

    第1フィールド: VSZ
        プロセスが持つ仮想メモリサイズ

    第2フィールド: RSS
        実際に物理メモリ上に載っているサイズ

    第3フィールド: MAJFLT
        メジャーフォールトの数
        ディスクI/Oを伴うページフォルト

    第4フィールド: MINFLT
        マイナーフォールトの数
        ディスクI/Oを伴わないページフォルト
COMMENT

# demand-paging.py のPIDを探す
#
# pgrep:
#   条件に一致するプロセスIDを探す
#
# -f:
#   プロセス名だけでなく、コマンドライン全体を検索対象にする
#
# "demand-paging\.py":
#   demand-paging.py という文字列に一致させる
#   . は正規表現では「任意の1文字」なので、\. として普通のドット扱いにする
PID=$(pgrep -f "demand-paging\.py")

# PIDが空なら、対象プロセスが見つからなかったということ
# [ と ] の前後にはスペースが必要
if [ -z "${PID}" ]; then
    echo "demand-paging.pyプロセスが存在しませんので、$0より先に起動してください。" >&2
    exit 1
fi

# 対象プロセスが存在する間、1秒ごとに情報を表示し続ける
while true; do
    # 現在時刻を取得する
    #
    # date:
    #   現在時刻を表示
    #
    # tr -d '\n':
    #   date の末尾の改行を削除する
    DATE=$(date | tr -d '\n')

    # psで対象プロセスのメモリ関連情報を取得する
    #
    # -h:
    #   ヘッダ行を表示しない
    #
    # -o vsz,rss,maj_flt,min_flt:
    #   出力する列を指定する
    #
    # vsz:
    #   仮想メモリサイズ
    #
    # rss:
    #   実際に物理メモリに載っているサイズ
    #
    # maj_flt:
    #   メジャーフォールト数
    #
    # min_flt:
    #   マイナーフォールト数
    #
    # -p ${PID}:
    #   指定したPIDのプロセスだけを見る
    INFO=$(ps -h -o vsz,rss,maj_flt,min_flt -p "${PID}")

    # ps が失敗した場合、対象プロセスが終了した可能性が高い
    if [ $? -ne 0 ]; then
        echo "$DATE: demand-paging.pyプロセスは終了しました。" >&2
        exit 1
    fi

    # 時刻とメモリ情報を1行で表示する
    echo "${DATE}: ${INFO}"

    # 1秒待ってから次の情報を取得する
    sleep 1
done

