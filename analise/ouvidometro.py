import csv
import json
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BASE_PADRAO = RAIZ / "dados" / "tratados" / "por_ano" / "*.parquet"
PAINEL = RAIZ / "painel"
CORTE = "2026-08-31"
ARQUIVO_GERADO_EM = "2026-09-01"
DIAS_PRORROGACAO = 45
MIN_ORGAO = 300
MIN_ASSUNTO = 200
JANELA_12M = ("2025-09-01", "2026-08-31")
JANELA_ANTERIOR = ("2024-09-01", "2025-08-31")
NAO_INFORMADO = ("", "Não Informado", "Não informado")

MEDIDAS = f"""
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


def conectar(base=BASE_PADRAO, corte=CORTE, dias_prorrogacao=DIAS_PRORROGACAO):
    con = duckdb.connect()
    con.execute(f"""
    create view b as select
      strptime("data registro", '%d/%m/%Y')::date as dr,
      try_strptime(nullif("data prazo resposta", ''), '%d/%m/%Y')::date as dp,
      try_strptime(nullif("data resposta", ''), '%d/%m/%Y')::date as dresp,
      try_cast(nullif("dias para resolução", '') as int) as dres,
      coalesce(nullif("tipo manifestação", ''), 'Não informado') as tipo,
      coalesce(nullif(esfera, ''), 'Não informada') as esfera,
      coalesce(nullif("uf do Órgão", ''), 'NI') as uf,
      "código do Órgão" as cod_orgao,
      "nome Órgão" as nome_orgao,
      "município do Órgão" || '/' || "uf do Órgão" as local_orgao,
      coalesce(nullif(assunto, ''), 'Não informado') as assunto,
      nullif("satisfação", '') as sat,
      nullif("demanda atendida", '') as atend
    from read_parquet('{base}')
    """)
    con.execute("create view nomes as select nome_orgao, count(distinct cod_orgao) as n from b group by 1")
    con.execute(f"""
    create view v as select b.*,
      strftime(dr, '%Y-%m') as mes,
      year(dr) as ano,
      case when b.nome_orgao is null then 'Órgão não informado'
           when b.esfera <> 'Federal' or nomes.n > 1 then b.nome_orgao || ' (' || coalesce(b.local_orgao, 'local não informado') || ')'
           else b.nome_orgao end as orgao,
      dp is not null as com_prazo,
      dp is not null and dp <= date '{corte}' as aval,
      (dresp is not null and dresp > dp) or (dresp is null and dp is not null and dp <= date '{corte}') as fora,
      dresp is null and dp is not null and dp <= date '{corte}' as pend,
      dresp is not null and dres is not null as resp,
      dp is not null and dp - dr > {dias_prorrogacao} as prorrog,
      sat is not null as sat_n,
      coalesce(sat in ('(4) Satisfeito', '(5) Muito Satisfeito'), false) as sat_pos,
      atend is not null as atend_n,
      coalesce(atend in ('Sim', 'Parcialmente Atendida'), false) as atend_pos
    from b left join nomes using (nome_orgao)
    """)
    return con


def linhas(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def total_manifestacoes(con):
    return con.execute("select count(*) from v").fetchone()[0]


def taxa_no_prazo(con, inicio, fim):
    r = con.execute(f"""
    select sum(aval::int), sum(fora::int) from v
    where dr >= date '{inicio}' and dr <= date '{fim}'
    """).fetchone()
    avaliaveis, fora = r[0] or 0, r[1] or 0
    if not avaliaveis:
        return None
    return round(100.0 * (avaliaveis - fora) / avaliaveis, 1)


def tabela_orgaos(con, inicio, fim, minimo=MIN_ORGAO):
    return linhas(con, f"""
    select cod_orgao, any_value(orgao) as orgao, any_value(esfera) as esfera, count(*) as volume,
      round(100.0 * (sum(aval::int) - sum(fora::int)) / nullif(sum(aval::int), 0), 1) as pct_no_prazo,
      round(100.0 * sum(fora::int) / nullif(sum(aval::int), 0), 1) as pct_fora,
      median(dres) as mediana_dias, round(quantile_cont(dres, 0.9), 1) as p90_dias,
      sum(pend::int) as pendentes_vencidas
    from v where dr >= date '{inicio}' and dr <= date '{fim}' and cod_orgao is not null
    group by cod_orgao having count(*) >= {int(minimo)}
    order by pct_fora desc nulls last, volume desc
    """)


def tabela_assuntos(con, inicio, fim, minimo=MIN_ASSUNTO):
    excluir = ", ".join("'" + x + "'" for x in NAO_INFORMADO)
    return linhas(con, f"""
    select assunto, count(*) as volume,
      round(100.0 * (sum(aval::int) - sum(fora::int)) / nullif(sum(aval::int), 0), 1) as pct_no_prazo,
      round(100.0 * sum(fora::int) / nullif(sum(aval::int), 0), 1) as pct_fora,
      median(dres) as mediana_dias, round(quantile_cont(dres, 0.9), 1) as p90_dias
    from v where dr >= date '{inicio}' and dr <= date '{fim}' and assunto not in ({excluir})
    group by 1 having count(*) >= {int(minimo)}
    order by pct_fora desc nulls last, volume desc
    """)


def indicadores_janela(con, inicio, fim, corte=CORTE):
    return linhas(con, f"""
    select count(*) as volume,
      round(100.0 * (sum(aval::int) - sum(fora::int)) / nullif(sum(aval::int), 0), 1) as pct_no_prazo,
      round(100.0 * sum(fora::int) / nullif(sum(aval::int), 0), 1) as pct_fora,
      median(dres) as mediana_dias, round(quantile_cont(dres, 0.9), 1) as p90_dias,
      round(avg(case when resp then dres end), 1) as tempo_medio_dias,
      sum(pend::int) as pendentes_vencidas,
      median(case when pend then date '{corte}' - dp end) as idade_mediana_pendencias,
      round(100.0 * avg(case when dresp is not null then 1 else 0 end), 1) as pct_respondidas
    from v where dr >= date '{inicio}' and dr <= date '{fim}'
    """)[0]


def resumo_12m(con, corte=CORTE):
    ini, fim = JANELA_12M
    ini_ant, fim_ant = JANELA_ANTERIOR
    filtro = f"dr >= date '{ini}' and dr <= date '{fim}'"
    return {
      "corte": corte,
      "janela_12m": [ini, fim],
      "janela_anterior": [ini_ant, fim_ant],
      "cortes": {"orgaos": MIN_ORGAO, "assuntos": MIN_ASSUNTO},
      "kpis": {"12m": indicadores_janela(con, ini, fim, corte), "ant": indicadores_janela(con, ini_ant, fim_ant, corte)},
      "total_base": linhas(con, "select count(*) as n, min(dr)::varchar as ini, max(dr)::varchar as fim from v")[0],
      "mensal": linhas(con, f"""
        select mes, count(*) as volume, sum(aval::int) as com_prazo_vencido,
          case when sum(aval::int) >= 0.9 * count(dp)
            then round(100.0 * sum(fora::int) / nullif(sum(aval::int), 0), 1) end as pct_fora,
          median(dres) as mediana_dias
        from v group by 1 order by 1"""),
      "tipos": linhas(con, f"""
        select tipo, count(*) as volume,
          round(100.0 * sum(fora::int) / nullif(sum(aval::int), 0), 1) as pct_fora, median(dres) as mediana_dias
        from v where {filtro} group by 1 order by 2 desc"""),
      "esferas": linhas(con, f"""
        with a as (
          select esfera, count(*) as volume,
            round(100.0 * (sum(aval::int) - sum(fora::int)) / nullif(sum(aval::int), 0), 1) as pct_no_prazo,
            round(100.0 * sum(fora::int) / nullif(sum(aval::int), 0), 1) as pct_fora,
            sum(pend::int) as pendentes_vencidas
          from v where {filtro} group by 1),
        p as (
          select esfera, count(*) as volume_ant,
            round(100.0 * (sum(aval::int) - sum(fora::int)) / nullif(sum(aval::int), 0), 1) as pct_no_prazo_ant
          from v where dr >= date '{ini_ant}' and dr <= date '{fim_ant}' group by 1)
        select a.esfera, a.volume, a.pct_no_prazo, a.pct_fora, a.pendentes_vencidas, p.volume_ant, p.pct_no_prazo_ant
        from a left join p using (esfera) order by a.volume desc"""),
      "orgaos": tabela_orgaos(con, ini, fim),
      "assuntos": tabela_assuntos(con, ini, fim),
      "satisfacao": linhas(con, f"""
        select case when fora then 'Fora do prazo' else 'No prazo' end as grupo, count(*) as respostas,
          round(100.0 * avg(sat_pos::int), 1) as pct_satisfeitos,
          round(100.0 * avg((sat = '(1) Muito Insatisfeito')::int), 1) as pct_muito_insatisfeitos
        from v where {filtro} and sat_n and aval group by 1 order by 1 desc"""),
      "satisfacao_cobertura": linhas(con, f"""
        select count(*) as manifestacoes, sum(sat_n::int) as com_resposta from v where {filtro}""")[0],
    }


def _colunar(con, sql, dims):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    dic = {d: sorted({r[cols.index(d)] for r in rows}, key=lambda x: (x is None, x)) for d in dims}
    idx = {d: {v: i for i, v in enumerate(dic[d])} for d in dims}
    out = {"dims": dic, "cols": {}, "linhas": len(rows)}
    for i, col in enumerate(cols):
        out["cols"][col] = [idx[col][r[i]] if col in dims else int(r[i] or 0) for r in rows]
    return out


def cubos(con, corte=CORTE):
    principal = _colunar(con, f"select mes, esfera, tipo, uf, {MEDIDAS} from v group by all", ["mes", "esfera", "tipo", "uf"])
    tipos = principal["dims"]["tipo"]
    esferas = principal["dims"]["esfera"]
    ufs = principal["dims"]["uf"]

    attr = [r for r in con.execute(
      "select cod_orgao, any_value(orgao), any_value(esfera), any_value(uf) from v group by 1").fetchall() if r[0] is not None]
    ordem = {r[0]: i for i, r in enumerate(attr)}
    rows = con.execute("""
      select cod_orgao, ano, tipo, count(*), sum(aval::int), sum(fora::int), sum(pend::int),
        sum(resp::int), sum(case when resp then dres else 0 end)
      from v where cod_orgao is not null group by all
    """).fetchall()
    orgaos = {
      "lista": [{"nome": r[1], "esfera": r[2], "uf": r[3]} for r in attr],
      "cols": {
        "o": [ordem[r[0]] for r in rows], "ano": [int(r[1]) for r in rows], "tipo": [tipos.index(r[2]) for r in rows],
        "n": [r[3] for r in rows], "av": [int(r[4] or 0) for r in rows], "fo": [int(r[5] or 0) for r in rows],
        "pe": [int(r[6] or 0) for r in rows], "re": [int(r[7] or 0) for r in rows], "sd": [int(r[8] or 0) for r in rows],
      },
    }

    assuntos = _colunar(con, """
      select assunto, ano, esfera, tipo, uf, count(*) as n, sum(aval::int) as av, sum(fora::int) as fo,
        sum(resp::int) as re, sum(case when resp then dres else 0 end) as sd
      from v group by all
    """, ["assunto", "ano", "esfera", "tipo", "uf"])
    assuntos["cols"]["esfera"] = [esferas.index(assuntos["dims"]["esfera"][i]) for i in assuntos["cols"]["esfera"]]
    assuntos["cols"]["tipo"] = [tipos.index(assuntos["dims"]["tipo"][i]) for i in assuntos["cols"]["tipo"]]
    assuntos["cols"]["uf"] = [ufs.index(assuntos["dims"]["uf"][i]) for i in assuntos["cols"]["uf"]]
    assuntos["cols"]["ano"] = [assuntos["dims"]["ano"][i] for i in assuntos["cols"]["ano"]]
    assuntos["dims"] = {"assunto": assuntos["dims"]["assunto"]}

    base = con.execute(
      "select count(*), min(dr)::varchar, max(dr)::varchar, count(distinct cod_orgao), count(distinct assunto) from v").fetchone()
    return {
      "corte": corte,
      "arquivo_gerado_em": ARQUIVO_GERADO_EM,
      "dias_prorrogacao": DIAS_PRORROGACAO,
      "cortes": {"orgaos": MIN_ORGAO, "assuntos": MIN_ASSUNTO},
      "base": {"manifestacoes": base[0], "inicio": base[1], "fim": base[2], "orgaos": base[3], "assuntos": base[4]},
      "principal": principal,
      "orgaos": orgaos,
      "assuntos": assuntos,
    }


def gravar_painel(dados, destino=PAINEL / "dados.js"):
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    Path(destino).write_text("window.OUVIDOMETRO=" + texto + ";\n", encoding="utf-8")
    return len(texto.encode("utf-8"))


def gravar_resumo(resumo, pasta=PAINEL):
    pasta = Path(pasta)
    (pasta / "indicadores.json").write_text(json.dumps(resumo, ensure_ascii=False, default=float), encoding="utf-8")
    tabelas = {"kpis": [dict(janela=k, **v) for k, v in resumo["kpis"].items()]}
    for nome in ["mensal", "tipos", "esferas", "orgaos", "assuntos", "satisfacao"]:
        tabelas[nome] = resumo[nome]
    for nome, rows in tabelas.items():
        if not rows:
            continue
        with open(pasta / f"{nome}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
