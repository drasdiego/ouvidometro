import sys
import urllib.request
import zipfile
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
URL = "https://dadosabertos-download.cgu.gov.br/e-Ouv/manifestacoes-ouvidoria.zip"
ZIP = RAIZ / "manifestacoes-ouvidoria.zip"
BRUTOS = RAIZ / "dados" / "brutos"
POR_ANO = RAIZ / "dados" / "tratados" / "por_ano"
PRIMEIRO_ANO = 2015
CORTE_EXCLUSIVO = "2026-09-01"


def baixar():
    if ZIP.exists() and "--baixar" not in sys.argv:
        print(f"Usando {ZIP.name} já baixado (passe --baixar para baixar de novo).")
        return
    print(f"Baixando {URL}")
    urllib.request.urlretrieve(URL, ZIP)


def extrair():
    BRUTOS.mkdir(parents=True, exist_ok=True)
    anos = []
    with zipfile.ZipFile(ZIP) as z:
        for nome in sorted(z.namelist()):
            ano = int(nome.rsplit("_", 1)[-1].split(".")[0])
            if ano < PRIMEIRO_ANO:
                continue
            destino = BRUTOS / f"Manifestacoes_Ouvidoria_{ano}_utf8.csv"
            if not destino.exists():
                texto = z.read(nome).decode("latin-1").replace("\r\n", "\n")
                destino.write_text(texto, encoding="utf-8")
            anos.append(ano)
    return anos


def converter(anos):
    POR_ANO.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    for ano in anos:
        origem = BRUTOS / f"Manifestacoes_Ouvidoria_{ano}_utf8.csv"
        destino = POR_ANO / f"ano={ano}.parquet"
        c.execute(f"""
        copy (
          select * from read_csv('{origem}', delim=';', header=true, all_varchar=true, quote='"')
          where strptime("data registro", '%d/%m/%Y') < date '{CORTE_EXCLUSIVO}'
        ) to '{destino}' (format parquet, compression zstd)
        """)
        print(ano, "ok")


if __name__ == "__main__":
    baixar()
    converter(extrair())
