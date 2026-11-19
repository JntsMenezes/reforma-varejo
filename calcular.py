"""Roda as cestas de produtos na calculadora oficial da Receita (API local)
e gera web/index.html com os resultados embutidos.

Uso: python calcular.py   (API rodando em localhost:8080)
"""
import csv
import json
import sqlite3
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
API = "http://localhost:8080/api/calculadora/observabilidade/regime-geral"
BANCO = RAIZ / "calculadora" / "calculadora" / "db" / "calculadora-pro.db"

# Cenário de alíquotas nominais usado na chamada. A página deixa o usuário mudar
# depois; o que vem da calculadora e não muda é o percentual de redução por item.
CBS, IBS_UF, IBS_MUN = 8.8, 17.7, 0.0
DATA = "2033-03-10T10:00:00-03:00"  # regime cheio, sem ICMS/PIS/COFINS/ISS


def ler_produtos():
    with open(RAIZ / "dados" / "produtos.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def item_api(i, p):
    item = {
        "numero": i,
        "cst": p["cst"],
        "cClassTrib": p["cClassTrib"],
        "baseCalculo": 100.00,  # base fixa: o resultado vira percentual
        "aliquotasNominais": {"cbs": CBS, "ibsEstadual": IBS_UF, "ibsMunicipal": IBS_MUN},
    }
    if p["nbs"]:
        item["nbs"] = p["nbs"]
    else:
        item.update(ncm=p["ncm"], quantidade=1, unidade="UN")
    return item


def chamar_api(produtos):
    corpo = {"id": "simulador-varejo", "versao": "1.0.0", "dhFatoGerador": DATA,
             "municipio": 3550308, "uf": "SP",
             "itens": [item_api(i, p) for i, p in enumerate(produtos, start=1)]}
    req = urllib.request.Request(API, data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def fundamentacao(classes):
    """Texto legal de cada cClassTrib, lido do banco oficial da calculadora."""
    con = sqlite3.connect(BANCO)
    leis = {}
    for cd in sorted(classes):
        linhas = con.execute(
            """select f.FDLG_TEXTO_CURTO, f.FDLG_TEXTO, f.FDLG_REFERENCIA_NORMATIVA, t.CLTR_DESCRICAO
               from CLASSIFICACAO_TRIBUTARIA t
               join FUNDAMENTACAO_CLASSIFICACAO fc on fc.FDCL_CLTR_ID = t.CLTR_ID
               join FUNDAMENTACAO_LEGAL f on f.FDLG_ID = fc.FDCL_FDLG_ID
               where t.CLTR_CD = ? and f.FDLG_REFERENCIA_NORMATIVA not like '%SELETIVO%'""",
            (cd,)).fetchall()
        curto, texto, ref, desc = linhas[0]
        secao = [s.strip() for s in ref.replace("\\n", "\n").split("\n") if s.strip()][-1]
        leis[cd] = {"artigo": curto, "texto": texto.replace("\\n", "\n").strip(),
                    "secao": secao, "descricao": desc}
    return leis


def montar(produtos, resposta):
    saida = []
    for p, obj in zip(produtos, resposta["objetos"]):
        if obj["estadoItem"] not in ("CALCULADO", "CALCULO_SIMULADO"):
            raise SystemExit(f"Item com erro: {p['produto']} -> {obj}")
        g = obj["tribCalc"]["IBSCBS"]["gIBSCBS"]
        saida.append({
            "ramo": p["ramo"], "produto": p["produto"], "categoria": p["categoria"],
            "ncm": p["ncm"], "nbs": p["nbs"], "cst": p["cst"], "cClassTrib": p["cClassTrib"],
            "preco": float(p["preco"]), "qtd": int(p["qtd_mes"]),
            "redCbs": float(g["gCBS"].get("gRed", {}).get("pRedAliq", 0)),
            "redIbs": float(g["gIBSUF"].get("gRed", {}).get("pRedAliq", 0)),
            "vCbs100": float(g["gCBS"]["vCBS"]), "vIbs100": float(g["vIBS"]),
            "memoria": g["gCBS"]["memoriaCalculo"],
            "estado": obj["estadoItem"],
        })
    return saida


def conferir(itens):
    """O valor da API (base 100) tem de bater com nominal x (1 - redução)."""
    for it in itens:
        esperado_cbs = round(CBS * (1 - it["redCbs"] / 100), 2)
        esperado_ibs = round((IBS_UF + IBS_MUN) * (1 - it["redIbs"] / 100), 2)
        assert abs(esperado_cbs - it["vCbs100"]) < 0.011, it
        assert abs(esperado_ibs - it["vIbs100"]) < 0.011, it


if __name__ == "__main__":
    produtos = ler_produtos()
    itens = montar(produtos, chamar_api(produtos))
    conferir(itens)
    dados = {"cenario": {"cbs": CBS, "ibs": IBS_UF + IBS_MUN, "data": DATA[:10]},
             "leis": fundamentacao({it["cClassTrib"] for it in itens}),
             "itens": itens}
    (RAIZ / "dados" / "resultado.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    modelo = (RAIZ / "web" / "modelo.html").read_text(encoding="utf-8")
    pagina = modelo.replace("/*DADOS*/null", json.dumps(dados, ensure_ascii=False))
    (RAIZ / "web" / "index.html").write_text(pagina, encoding="utf-8")
    (RAIZ / "index.html").write_text(pagina, encoding="utf-8")  # GitHub Pages serve a raiz
    ramos = {}
    for it in itens:
        ramos[it["ramo"]] = ramos.get(it["ramo"], 0) + 1
    print(f"{len(itens)} itens calculados {ramos}; conferência ok; web/index.html gerado")
