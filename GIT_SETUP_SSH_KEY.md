# GitHub SSH setup memo

GitHub に `git push` するとき、毎回 username/password を聞かれないように SSH 接続へ切り替える手順。

## 1. SSH key を作る

```bash
ssh-keygen -t ed25519 -C "your-email-or-label"
```

保存先を聞かれたら、今回は次の名前で作った。

```text
github_ed25519
```

この場合、秘密鍵と公開鍵はカレントディレクトリに作られる。

```text
github_ed25519
github_ed25519.pub
```

## 2. 公開鍵を GitHub に登録する

公開鍵の中身を表示する。

```bash
cat github_ed25519.pub
```

表示された次のような 1 行をコピーする。

```text
ssh-ed25519 AAAA...your-public-key... your-email-or-label
```

GitHub の SSH key 設定ページを開く。

```text
https://github.com/settings/keys
```

GitHub 画面では以下のように入力する。

```text
Title: your-device-name など、分かりやすい名前
Key type: Authentication Key
Key: cat github_ed25519.pub で表示した ssh-ed25519 から始まる 1 行
```

途中で改行を入れず、1 行のまま貼る。

## 3. 鍵を ~/.ssh に移動する

```bash
mkdir -p ~/.ssh
mv github_ed25519 ~/.ssh/
mv github_ed25519.pub ~/.ssh/
chmod 600 ~/.ssh/github_ed25519
```

## 4. SSH config を設定する

`~/.ssh/config` に GitHub 用の設定を追加する。

```bash
printf '\nHost github.com\n  HostName github.com\n  User git\n  IdentityFile ~/.ssh/github_ed25519\n  IdentitiesOnly yes\n' >> ~/.ssh/config
```

中身はこの形になる。

```sshconfig
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_ed25519
  IdentitiesOnly yes
```

## 5. Git の remote を SSH に変更する

リポジトリの中で実行する。

```bash
git remote set-url origin git@github.com:YOUR_USER/YOUR_REPO.git
```

確認する。

```bash
git remote -v
```

次のように `git@github.com:...` になっていれば OK。

```text
origin  git@github.com:YOUR_USER/YOUR_REPO.git (fetch)
origin  git@github.com:YOUR_USER/YOUR_REPO.git (push)
```

## 6. SSH 接続をテストする

```bash
ssh -T git@github.com
```

初回だけ次のような確認が出る。

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

これは `yes` で OK。

```bash
yes
```

成功すると次のような表示になる。

```text
Hi YOUR_USER! You've successfully authenticated, but GitHub does not provide shell access.
```

`shell access` がないという文は正常。GitHub は SSH ログイン用のシェルを提供していないだけ。

## 7. パスフレーズを毎回聞かれないようにする

次のように出た場合:

```text
Enter passphrase for key '/home/your-user/.ssh/github_ed25519':
```

これは GitHub のパスワードではなく、`ssh-keygen` で鍵を作ったときに入力したパスフレーズを入れる。

毎回聞かれないように SSH agent に登録する。

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/github_ed25519
```

ここで一度だけパスフレーズを入力する。

## 8. push する

```bash
git push
```

これで username/password を聞かれなければ SSH 化は完了。

## 補足: HTTPS の credential 設定を消す

HTTPS 用に設定した credential helper が邪魔な場合は消す。

```bash
git config --global --unset credential.helper
```

今回出ていた次のエラーは、`credential-osxkeychain` がその環境に存在しないため。

```text
git: 'credential-osxkeychain' はgitコマンドではありません。
```

SSH に切り替えれば、この HTTPS credential helper は使わなくてよい。
