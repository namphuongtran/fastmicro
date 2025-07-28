#!/usr/bin/env bash

ssh-keygen -t ed25519 -C "trphuongnam@gmail.com"
cat ~/.ssh/id_ed25519.pub
git remote set-url origin git@github.com:namphuongtran/fastmicro.git