import json
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "dados" / "tratados" / "por_ano" / "*.parquet"
SAIDA = RAIZ / "painel" / "indicadores.json"
CORTE = "2026-08-31"
INI_12M, INI_ANT = "2025-09-01", "2024-09-01"
MIN_ORGAO, MIN_ASSUNTO = 2000, 1000

c = duckdb.connect()
c.execute(f"""
create view b as select
  strptime("data registro", '%d/%m/%Y')::date as dr,
  try_strptime("data prazo resposta", '%d/%m/%Y')::date as dp,
  try_strptime("data resposta", '%d/%m/%Y')::date as dresp,
  try_cast("dias para resolução" as int) as dres,
  "tipo manifestação" as tipo, "código do Órgão" as cod_orgao,
  "nome Órgão" as nome_orgao, "município do Órgão" || '/' || "uf do Órgão" as local_orgao, assunto, "situação" as sit, esfera,
  "satisfação" as sat
from '{BASE}'
""")
c.execute("""
create view nomes as select nome_orgao, count(distinct cod_orgao) as n from b group by 1
""")
c.execute(f"""
create view v as select b.*,
  case when b.nome_orgao is null then 'Órgão não informado' when b.esfera <> 'Federal' or nomes.n > 1 then b.nome_orgao || ' (' || b.local_orgao || ')' else b.nome_orgao end as orgao,
  dp is not null and dp <= date '{CORTE}' as avaliavel,
  (dresp is not null and dresp > dp) or (dresp is null and dp is not null and dp <= date '{CORTE}') as fora,
  dresp is null and dp is not null and dp <= date '{CORTE}' as pendente_vencida,
  case when dr >= date '{INI_12M}' then '12m' when dr >= date '{INI_ANT}' then 'ant' end as janela
from b left join nomes using (nome_orgao)
""")

def linhas(sql):
    cur = c.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def kpis(j):
    return linhas(f"""
    select count(*) as volume,
      round(100.0 * sum(fora::int) / nullif(sum(avaliavel::int), 0), 1) as pct_fora,
      median(dres) as mediana_dias, round(quantile_cont(dres, 0.9), 1) as p90_dias,
      sum(pendente_vencida::int) as pendentes_vencidas,
      median(case when pendente_vencida then date '{CORTE}' - dp end) as idade_mediana_pendencias,
      round(100.0 * avg(case when dresp is not null then 1 else 0 end), 1) as pct_respondidas
    from v where janela = '{j}'""")[0]

out = {
  "corte": CORTE, "janela_12m": [INI_12M, CORTE], "janela_anterior": [INI_ANT, "2025-08-31"],
  "kpis": {"12m": kpis("12m"), "ant": kpis("ant")},
  "total_base": linhas("select count(*) as n, min(dr)::varchar as ini, max(dr)::varchar as fim from v")[0],
  "mensal": linhas("""
    select strftime(dr, '%Y-%m') as mes, count(*) as volume, sum(avaliavel::int) as com_prazo_vencido,
      case when sum(avaliavel::int) >= 0.9 * count(dp)
        then round(100.0 * sum(fora::int) / nullif(sum(avaliavel::int), 0), 1) end as pct_fora,
      median(dres) as mediana_dias
    from v group by 1 order by 1"""),
  "base": linhas("""
    select count(*) as manifestacoes, min(dr)::varchar as inicio, max(dr)::varchar as fim,
      count(distinct cod_orgao) as orgaos, count(distinct assunto) as assuntos,
      count(distinct strftime(dr, '%Y-%m')) as meses
    from v"""),
  "tipos": linhas("""
    select tipo, count(*) as volume,
      round(100.0 * sum(fora::int) / nullif(sum(avaliavel::int), 0), 1) as pct_fora,
      median(dres) as mediana_dias
    from v where janela = '12m' group by 1 order by 2 desc"""),
  "esferas": linhas("""
    select esfera, count(*) as volume,
      round(100.0 * sum(fora::int) / nullif(sum(avaliavel::int), 0), 1) as pct_fora
    from v where janela = '12m' group by 1 order by 2 desc"""),
  "orgaos": linhas(f"""
    with a as (select cod_orgao, any_value(orgao) as orgao, any_value(esfera) as esfera, count(*) as volume, sum(avaliavel::int) as aval, sum(fora::int) as fora_n,
        median(dres) as mediana_dias, round(quantile_cont(dres, 0.9), 1) as p90_dias, sum(pendente_vencida::int) as pendentes_vencidas
      from v where janela = '12m' group by cod_orgao),
    p as (select cod_orgao, round(100.0 * sum(fora::int) / nullif(sum(avaliavel::int), 0), 1) as pct_fora_ant
      from v where janela = 'ant' group by 1 having count(*) >= {MIN_ORGAO})
    select a.cod_orgao, a.orgao, a.esfera, volume, round(100.0 * fora_n / nullif(aval, 0), 1) as pct_fora, mediana_dias, p90_dias,
      pendentes_vencidas, p.pct_fora_ant
    from a left join p using (cod_orgao) where volume >= {MIN_ORGAO} order by pct_fora desc"""),
  "assuntos": linhas(f"""
    select assunto, count(*) as volume,
      round(100.0 * sum(fora::int) / nullif(sum(avaliavel::int), 0), 1) as pct_fora,
      median(dres) as mediana_dias, round(quantile_cont(dres, 0.9), 1) as p90_dias
    from v where janela = '12m' and assunto is not null and assunto not in ('', 'Não Informado')
    group by 1 having count(*) >= {MIN_ASSUNTO} order by pct_fora desc"""),
  "satisfacao": linhas("""
    select case when fora then 'Fora do prazo' else 'No prazo' end as grupo, count(*) as respostas,
      round(100.0 * avg(case when sat in ('(4) Satisfeito', '(5) Muito Satisfeito') then 1 else 0 end), 1) as pct_satisfeitos,
      round(100.0 * avg(case when sat = '(1) Muito Insatisfeito' then 1 else 0 end), 1) as pct_muito_insatisfeitos
    from v where janela = '12m' and sat is not null and avaliavel group by 1"""),
  "satisfacao_cobertura": linhas("""
    select count(*) as manifestacoes, sum(case when sat is not null then 1 else 0 end) as com_resposta
    from v where janela = '12m'""")[0],
}
import csv
def grava(nome, rows):
    with open(RAIZ / "painel" / f"{nome}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
grava("kpis", [dict(janela=k, **v) for k, v in out["kpis"].items()])
for nome in ["mensal", "tipos", "esferas", "orgaos", "assuntos", "satisfacao"]:
    grava(nome, out[nome])
pagina = {
  "corte": CORTE,
  "kpis": [dict(janela=k, **v) for k, v in out["kpis"].items()],
  **{k: out[k] for k in ["base", "mensal", "tipos", "esferas", "orgaos", "assuntos", "satisfacao"]},
}
(RAIZ / "painel" / "dados.js").write_text(
  "window.OUVIDOMETRO = " + json.dumps(pagina, ensure_ascii=False, default=float) + ";\n", encoding="utf-8")
SAIDA.write_text(json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
print(json.dumps({k: out[k] for k in ["kpis", "total_base", "satisfacao", "satisfacao_cobertura"]}, ensure_ascii=False, default=float))
print("orgaos", len(out["orgaos"]), "assuntos", len(out["assuntos"]))
print(out["orgaos"][:5]); print(out["tipos"]); print(out["esferas"])
