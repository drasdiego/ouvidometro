import json
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "dados" / "tratados" / "por_ano" / "*.parquet"
SAIDA = RAIZ / "painel" / "dados.js"
CORTE = "2026-08-31"
DIAS_PRORROGACAO = 45

c = duckdb.connect()
c.execute(f"""
create view b as select
  strptime("data registro", '%d/%m/%Y')::date as dr,
  try_strptime("data prazo resposta", '%d/%m/%Y')::date as dp,
  try_strptime("data resposta", '%d/%m/%Y')::date as dresp,
  try_cast("dias para resolução" as int) as dres,
  coalesce(nullif("tipo manifestação", ''), 'Não informado') as tipo,
  coalesce(nullif(esfera, ''), 'Não informada') as esfera,
  coalesce(nullif("uf do Órgão", ''), 'NI') as uf,
  "código do Órgão" as cod_orgao,
  "nome Órgão" as nome_orgao,
  "município do Órgão" || '/' || "uf do Órgão" as local_orgao,
  coalesce(nullif(assunto, ''), 'Não informado') as assunto,
  "satisfação" as sat,
  "demanda atendida" as atend
from '{BASE}'
""")
c.execute("create view nomes as select nome_orgao, count(distinct cod_orgao) as n from b group by 1")
c.execute(f"""
create view v as select b.*,
  strftime(dr, '%Y-%m') as mes,
  year(dr) as ano,
  case when b.nome_orgao is null then 'Órgão não informado'
       when b.esfera <> 'Federal' or nomes.n > 1 then b.nome_orgao || ' (' || b.local_orgao || ')'
       else b.nome_orgao end as orgao,
  dp is not null as com_prazo,
  dp is not null and dp <= date '{CORTE}' as aval,
  (dresp is not null and dresp > dp) or (dresp is null and dp is not null and dp <= date '{CORTE}') as fora,
  dresp is null and dp is not null and dp <= date '{CORTE}' as pend,
  dresp is not null and dres is not null as resp,
  dp is not null and dp - dr > {DIAS_PRORROGACAO} as prorrog,
  sat is not null and sat <> '' as sat_n,
  sat in ('(4) Satisfeito', '(5) Muito Satisfeito') as sat_pos,
  atend is not null and atend <> '' as atend_n,
  atend in ('Sim', 'Parcialmente Atendida') as atend_pos
from b left join nomes using (nome_orgao)
""")

MEDIDAS_PRINCIPAL = f"""
  count(*) as n,
  sum(com_prazo::int) as cp,
  sum(aval::int) as av,
  sum(fora::int) as fo,
  sum(pend::int) as pe,
  sum(resp::int) as re,
  sum(case when resp then dres else 0 end) as sd,
  sum((resp and dres <= 10)::int) as r10,
  sum((resp and dres <= 30)::int) as r30,
  sum((resp and dres <= 60)::int) as r60,
  sum((pend and date '{CORTE}' - dr > 60)::int) as pe60,
  sum(prorrog::int) as pr,
  sum(sat_n::int) as sn,
  sum(sat_pos::int) as sp,
  sum((sat_n and aval)::int) as sa,
  sum((sat_pos and aval)::int) as sap,
  sum((sat_n and fora)::int) as sf,
  sum((sat_pos and fora)::int) as sfp,
  sum(atend_n::int) as an,
  sum(atend_pos::int) as ap
"""


def colunar(sql, dims):
    cur = c.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    dic = {d: sorted({r[cols.index(d)] for r in rows}, key=lambda x: (x is None, x)) for d in dims}
    idx = {d: {v: i for i, v in enumerate(dic[d])} for d in dims}
    out = {"dims": {d: dic[d] for d in dims}, "cols": {}}
    for i, col in enumerate(cols):
        if col in dims:
            out["cols"][col] = [idx[col][r[i]] for r in rows]
        else:
            out["cols"][col] = [int(r[i] or 0) for r in rows]
    out["linhas"] = len(rows)
    return out


principal = colunar(f"select mes, esfera, tipo, uf, {MEDIDAS_PRINCIPAL} from v group by all", ["mes", "esfera", "tipo", "uf"])

orgaos_attr = c.execute("""
  select cod_orgao, any_value(orgao), any_value(esfera), any_value(uf), count(*) from v group by 1
""").fetchall()
orgaos_attr = [r for r in orgaos_attr if r[0] is not None]
ordem = {r[0]: i for i, r in enumerate(orgaos_attr)}
cur = c.execute("""
  select cod_orgao, ano, tipo, count(*) as n, sum(aval::int) as av, sum(fora::int) as fo, sum(pend::int) as pe,
    sum(resp::int) as re, sum(case when resp then dres else 0 end) as sd
  from v where cod_orgao is not null group by all
""")
tipos = principal["dims"]["tipo"]
rows = cur.fetchall()
orgaos = {
  "lista": [{"nome": r[1], "esfera": r[2], "uf": r[3]} for r in orgaos_attr],
  "cols": {
    "o": [ordem[r[0]] for r in rows],
    "ano": [int(r[1]) for r in rows],
    "tipo": [tipos.index(r[2]) for r in rows],
    "n": [r[3] for r in rows], "av": [r[4] for r in rows], "fo": [r[5] for r in rows],
    "pe": [r[6] for r in rows], "re": [r[7] for r in rows], "sd": [int(r[8] or 0) for r in rows],
  },
}

esferas = principal["dims"]["esfera"]
assuntos = colunar("""
  select assunto, ano, esfera, tipo, count(*) as n, sum(aval::int) as av, sum(fora::int) as fo,
    sum(resp::int) as re, sum(case when resp then dres else 0 end) as sd
  from v group by all
""", ["assunto", "ano", "esfera", "tipo"])
assuntos["cols"]["esfera"] = [esferas.index(assuntos["dims"]["esfera"][i]) for i in assuntos["cols"]["esfera"]]
assuntos["cols"]["tipo"] = [tipos.index(assuntos["dims"]["tipo"][i]) for i in assuntos["cols"]["tipo"]]
assuntos["cols"]["ano"] = [assuntos["dims"]["ano"][i] for i in assuntos["cols"]["ano"]]
del assuntos["dims"]["esfera"], assuntos["dims"]["tipo"], assuntos["dims"]["ano"]

base = c.execute("""
  select count(*), min(dr)::varchar, max(dr)::varchar, count(distinct cod_orgao), count(distinct assunto) from v
""").fetchone()

dados = {
  "corte": CORTE,
  "arquivo_gerado_em": "2026-09-01",
  "dias_prorrogacao": DIAS_PRORROGACAO,
  "base": {"manifestacoes": base[0], "inicio": base[1], "fim": base[2], "orgaos": base[3], "assuntos": base[4]},
  "principal": principal,
  "orgaos": orgaos,
  "assuntos": assuntos,
}
texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
SAIDA.write_text("window.OUVIDOMETRO=" + texto + ";\n", encoding="utf-8")
print("linhas", principal["linhas"], len(rows), assuntos["linhas"], "tamanho_mb", round(len(texto.encode()) / 1e6, 2))
