from pathlib import Path


allowed = Path("modules/models/src/gateways/openai_gateway.py").resolve()
violations = []
for root in (Path("apps"), Path("modules")):
    for path in root.rglob("*.py"):
        if path.resolve() == allowed:
            continue
        if "api.openai.com" in path.read_text(encoding="utf-8"):
            violations.append(str(path))
if violations:
    raise SystemExit("OpenAI endpoint escaped the model gateway: " + ", ".join(violations))
print("OpenAI boundary: PASS")
