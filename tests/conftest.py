import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analise"))

import ouvidometro as ov

COLUNAS = [
    "data registro", "data prazo resposta", "data resposta", "faixa etária", "raça/cor", "gênero",
    "município manifestante", "uf do município manifestante", "município manifestação", "uf do município manifestação",
    "tipo manifestação", "código Órgão siorg", "código do Órgão", "nome Órgão", "município do Órgão", "uf do Órgão",
    "assunto", "dias para resolução", "dias de atraso", "formulário", "situação", "esfera", "serviço", "outro serviço",
    "demanda atendida", "satisfação",
]


def br(d):
    return d.strftime("%d/%m/%Y")


def linha(**campos):
    base = {c: "" for c in COLUNAS}
    base.update(campos)
    return base


def montar_linhas():
    linhas = []
    for i in range(300):
        dr = date(2026, 3, 1) + timedelta(days=i % 28)
        prazo = dr + timedelta(days=30)
        if i % 4 == 0:
            resposta, dias = br(dr + timedelta(days=40)), "40"
        elif i % 4 == 1:
            resposta, dias = "", ""
        else:
            resposta, dias = br(dr + timedelta(days=10)), "10"
        linhas.append(linha(**{
            "data registro": br(dr), "data prazo resposta": br(prazo), "data resposta": resposta,
            "dias para resolução": dias, "tipo manifestação": "Reclamação", "código do Órgão": "1",
            "nome Órgão": "Órgão A", "município do Órgão": "BRASÍLIA", "uf do Órgão": "DF", "esfera": "Federal",
            "assunto": "Assunto X" if i < 200 else "Assunto Y",
            "satisfação": "(5) Muito Satisfeito" if i % 10 == 2 else ("(1) Muito Insatisfeito" if i % 10 == 4 else ""),
            "demanda atendida": "Sim" if i % 10 == 2 else ("Não" if i % 10 == 4 else ""),
        }))
    for i in range(299):
        dr = date(2026, 4, 1) + timedelta(days=i % 28)
        prazo = dr + timedelta(days=32)
        atrasada = i % 10 == 0
        linhas.append(linha(**{
            "data registro": br(dr), "data prazo resposta": br(prazo),
            "data resposta": br(dr + timedelta(days=50 if atrasada else 5)),
            "dias para resolução": "50" if atrasada else "5", "tipo manifestação": "Solicitação",
            "código do Órgão": "2", "nome Órgão": "Prefeitura Municipal", "município do Órgão": "ITAJAÍ",
            "uf do Órgão": "SC", "esfera": "Municipal", "assunto": "Assunto Y" if i < 99 else "",
        }))
    for i in range(5):
        linhas.append(linha(**{
            "data registro": br(date(2026, 5, 10) + timedelta(days=i)), "código do Órgão": "3",
            "nome Órgão": "Prefeitura Municipal", "município do Órgão": "BIGUAÇU", "uf do Órgão": "SC",
        }))
    for i in range(3):
        linhas.append(linha(**{
            "data registro": br(date(2026, 8, 20)), "data prazo resposta": br(date(2026, 9, 21)),
            "tipo manifestação": "Denúncia", "código do Órgão": "3", "nome Órgão": "Prefeitura Municipal",
            "município do Órgão": "BIGUAÇU", "uf do Órgão": "SC", "esfera": "Municipal", "assunto": "Assunto Z",
        }))
    return linhas


@pytest.fixture(scope="session")
def linhas_brutas():
    return montar_linhas()


@pytest.fixture(scope="session")
def con(linhas_brutas, tmp_path_factory):
    pasta = tmp_path_factory.mktemp("base")
    origem = pasta / "bruto.csv"
    with open(origem, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";")
        w.writeheader()
        w.writerows(linhas_brutas)
    destino = pasta / "ano=2026.parquet"
    duckdb.connect().execute(f"""
        copy (select * from read_csv('{origem}', delim=';', header=true, all_varchar=true, quote='"'))
        to '{destino}' (format parquet)
    """)
    return ov.conectar(base=pasta / "*.parquet")
