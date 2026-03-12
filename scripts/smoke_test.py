import requests
import sys

API_URL = "http://localhost:8000"

def main():
    print(f"🔍 Testing health endpoint at {API_URL}...")
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
git push origin main add examples and smoke test script"
warning: in the working copy of 'examples/api/ingest_request.json', LF will be r
eplaced by CRLF the next time Git touches it
Enter passphrase for "C:/Users/ayman/.ssh/id_ed25519":
[main da821f4] feat: add examples and smoke test script
 2 files changed, 27 insertions(+)
 create mode 100644 examples/api/ingest_request.json
 create mode 100644 scripts/smoke_test.py
To https://github.com/Elmahrosa/safe-ingestion-engine.git
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs to 'https://github.com/Elmahrosa/safe-ingestion-
engine.git'
hint: Updates were rejected because the remote contains work that you do not
hint: have locally. This is usually caused by another repository pushing to
hint: the same ref. If you want to integrate the remote changes, use
hint: 'git pull' before pushing again.
hint: See the 'Note about fast-forwards' in 'git push --help' for details.

ayman@DESKTOP-TBLEEOR MINGW64 ~/safe-ingestion-engine (main)
$ git pull origin main
remote: Enumerating objects: 15, done.
remote: Counting objects: 100% (15/15), done.
remote: Compressing objects: 100% (9/9), done.
remote: Total 13 (delta 4), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (13/13), 3.45 KiB | 16.00 KiB/s, done.
From https://github.com/Elmahrosa/safe-ingestion-engine
 * branch            main       -> FETCH_HEAD
   20e2160..2e5fe96  main       -> origin/main
Auto-merging examples/api/ingest_request.json
CONFLICT (add/add): Merge conflict in examples/api/ingest_request.json
Automatic merge failed; fix conflicts and then commit the result.

ayman@DESKTOP-TBLEEOR MINGW64 ~/safe-ingestion-engine (main|MERGING)
$ git push origin main
To https://github.com/Elmahrosa/safe-ingestion-engine.git
 ! [rejected]        main -> main (non-fast-forward)
error: failed to push some refs to 'https://github.com/Elmahrosa/safe-ingestion-
engine.git'
hint: Updates were rejected because the tip of your current branch is behind
hint: its remote counterpart. If you want to integrate the remote changes,
hint: use 'git pull' before pushing again.
hint: See the 'Note about fast-forwards' in 'git push --help' for details.

ayman@DESKTOP-TBLEEOR MINGW64 ~/safe-ingestion-engine (main|MERGING)
$ cat <<EOF > Makefile
install:
    pip install -r requirements.txt

dev:
    uvicorn api.server:app --reload

test:
    pytest

lint:
    ruff .

docker:
    docker compose up

openapi:
    curl http://localhost:8000/openapi.json -o docs/openapi.json
