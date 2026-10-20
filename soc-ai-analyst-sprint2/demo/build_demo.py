"""
Arma la página de demo (demo/soc-demo.html) con los reportes reales del agente.

Toma cada caso de entrada y su reporte ya generado en data/reportes_sinteticos/
(correr antes `python agent/run_synthetic.py`) y los incrusta en
demo/template.html. La referencia esperada de cada caso la escribió el equipo
al diseñar el caso; no está validada por analistas.

Uso:
    python demo/build_demo.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reportes_sinteticos"

CASES = [
    {
        "key": "phishing_ecs", "title": "Phishing con robo de credenciales", "family": "Phishing",
        "input": "data/synthetic/phishing_ecs.json", "report": "phishing_ecs.json",
        "expected": [
            {"id": "T1566", "name": "Phishing"},
            {"id": "T1078", "name": "Valid Accounts (login desde otro país)"},
            {"id": "T1114.003", "name": "Email Forwarding Rule"},
        ],
    },
    {
        "key": "bruteforce_wazuh", "title": "Fuerza bruta SSH y respaldo legítimo", "family": "Fuerza bruta y movimiento lateral",
        "input": "data/synthetic/bruteforce_wazuh.json", "report": "bruteforce_wazuh.json",
        "expected": [
            {"id": "T1110", "name": "Brute Force"},
            {"id": "T1078", "name": "Valid Accounts (login exitoso tras los fallos)"},
            {"id": "T1548.003", "name": "Sudo and Sudo Caching"},
            {"id": "T1021", "name": "Remote Services", "note": "Diseñada como ambigua: coincide con un respaldo legítimo."},
        ],
    },
    {
        "key": "exfiltration", "title": "Exfiltración desde servidor de archivos", "family": "Exfiltración",
        "input": "data/synthetic/exfiltration.json", "report": "exfiltration.json",
        "expected": [
            {"id": "T1560", "name": "Archive Collected Data"},
            {"id": "T1041", "name": "Exfiltration Over C2 Channel"},
        ],
    },
    {
        "key": "pre_ransomware", "title": "Actividad previa a ransomware", "family": "Pre-ransomware",
        "input": "data/synthetic/pre_ransomware.json", "report": "pre_ransomware.json",
        "expected": [
            {"id": "T1021", "name": "Remote Services (SMB y PsExec)"},
            {"id": "T1490", "name": "Inhibit System Recovery"},
            {"id": "T1486", "name": "Data Encrypted for Impact"},
        ],
    },
    {
        "key": "benign_noise", "title": "Ruido benigno", "family": "Control negativo",
        "input": "data/synthetic/benign_noise.json", "report": "benign_noise.json",
        "expected": [],
    },
    {
        "key": "sample_case_bruteforce", "title": "Caso original del scaffold", "family": "Fuerza bruta y movimiento lateral",
        "input": "data/sample_case_bruteforce.json", "report": "sample_case_bruteforce.json",
        "expected": [
            {"id": "T1110", "name": "Brute Force"},
            {"id": "T1078", "name": "Valid Accounts (login tras los fallos)"},
            {"id": "T1021", "name": "Remote Services"},
        ],
    },
    {
        "key": "holdout_kerberoast", "title": "Caso nuevo: Kerberoasting, RDP y rclone", "family": "Caso de control no visto",
        "input": "data/holdout/kerberoast_rdp_rclone_ecs.json", "report": "holdout_kerberoast.json",
        "holdout": True,
        "expected": [
            {"id": "T1059.001", "name": "PowerShell lanzado por Office"},
            {"id": "T1558.003", "name": "Kerberoasting"},
            {"id": "T1021.001", "name": "Remote Desktop Protocol"},
            {"id": "T1567.002", "name": "Exfiltration to Cloud Storage"},
        ],
    },
]


def main() -> None:
    bundle = []
    for case in CASES:
        report = json.loads((REPORTS / case["report"]).read_text(encoding="utf-8"))
        source = json.loads((ROOT / case["input"]).read_text(encoding="utf-8"))
        mapped = {m["technique_id"].split(".")[0] for m in report["attack_mapping"]}
        expected = [
            {**e, "detected": e["id"].split(".")[0] in mapped} for e in case["expected"]
        ]
        bundle.append({
            "key": case["key"], "title": case["title"], "family": case["family"],
            "holdout": case.get("holdout", False), "description": source.get("description", ""),
            "input_path": case["input"], "alerts": source["alerts"],
            "enrichment_input": source.get("enrichment"), "expected": expected, "report": report,
        })

    data = json.dumps(bundle, ensure_ascii=False).replace("</", "<\\/")
    template = (ROOT / "demo" / "template.html").read_text(encoding="utf-8")
    out = ROOT / "demo" / "soc-demo.html"
    out.write_text(template.replace("/*__DATA__*/[]", data), encoding="utf-8")
    detected = sum(e["detected"] for c in bundle for e in c["expected"])
    total = sum(len(c["expected"]) for c in bundle)
    print(f"{out.relative_to(ROOT)}: {len(bundle)} casos, {detected}/{total} técnicas de referencia detectadas")


if __name__ == "__main__":
    main()
