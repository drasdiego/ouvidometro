import csv
from datetime import date, datetime
from pathlib import Path

import pytest

import ouvidometro as ov

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos"
TRATADOS = RAIZ / "dados" / "tratados" / "por_ano"
CORTE = date(2026, 8, 31)

pytestmark = pytest.mark.skipif(
    not list(TRATADOS.glob("*.parquet")) or not list(BRUTOS.glob("*_utf8.csv")),
    reason="base real ausente: rode analise/preparar_dados.py para habilitar",
)


def data(texto):
    return datetime.strptime(texto, "%d/%m/%Y").date() if texto else None


@pytest.fixture(scope="module")
def con_real():
    return ov.conectar()


def ler(ano):
    with open(BRUTOS / f"Manifestacoes_Ouvidoria_{ano}_utf8.csv", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f, delimiter=";")


def test_total_bate_com_os_csv_brutos(con_real):
    total = 0
    for arquivo in sorted(BRUTOS.glob("*_utf8.csv")):
        ano = int(arquivo.name.split("_")[2])
        total += sum(1 for r in ler(ano) if data(r["data registro"]) <= CORTE)
    assert ov.total_manifestacoes(con_real) == total


def test_percentual_no_prazo_de_marco_de_2025(con_real):
    avaliaveis = fora = 0
    for r in ler(2025):
        dr = data(r["data registro"])
        if dr.year != 2025 or dr.month != 3:
            continue
        dp, dresp = data(r["data prazo resposta"]), data(r["data resposta"])
        if dp is None or dp > CORTE:
            continue
        avaliaveis += 1
        if dresp is None or dresp > dp:
            fora += 1
    esperado = round(100.0 * (avaliaveis - fora) / avaliaveis, 1)
    assert ov.taxa_no_prazo(con_real, "2025-03-01", "2025-03-31") == esperado
