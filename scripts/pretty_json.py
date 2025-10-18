import sys, json
try:
    print(json.dumps(json.load(sys.stdin), ensure_ascii=False, indent=2))
except Exception:
    sys.stdout.write(sys.stdin.read())
