from datetime import date, datetime

import ouvidometro as ov

CORTE = date(2026, 8, 31)


def data(texto):
    return datetime.strptime(texto, "%d/%m/%Y").date() if texto else None


def no_prazo_independente(linhas, inicio, fim):
    avaliaveis = fora = 0
    for r in linhas:
        dr, dp, dresp = data(r["data registro"]), data(r["data prazo resposta"]), data(r["data resposta"])
        if not (inicio <= dr <= fim) or dp is None or dp > CORTE:
            continue
        avaliaveis += 1
        if dresp is None or dresp > dp:
            fora += 1
    return round(100.0 * (avaliaveis - fora) / avaliaveis, 1)


def test_total_bate_com_a_base_bruta(con, linhas_brutas):
    assert ov.total_manifestacoes(con) == len(linhas_brutas) == 607


def test_percentual_no_prazo_do_mes_de_referencia(con, linhas_brutas):
    esperado = no_prazo_independente(linhas_brutas, date(2026, 3, 1), date(2026, 3, 31))
    assert esperado == 50.0
    assert ov.taxa_no_prazo(con, "2026-03-01", "2026-03-31") == esperado


def test_percentual_no_prazo_de_outro_mes(con, linhas_brutas):
    esperado = no_prazo_independente(linhas_brutas, date(2026, 4, 1), date(2026, 4, 30))
    assert ov.taxa_no_prazo(con, "2026-04-01", "2026-04-30") == esperado


def test_corte_de_orgaos_em_300(con):
    assert ov.MIN_ORGAO == 300
    codigos = {r["cod_orgao"]: r for r in ov.tabela_orgaos(con, "2026-01-01", "2026-08-31")}
    assert set(codigos) == {"1"}
    assert codigos["1"]["volume"] == 300
    com_299 = {r["cod_orgao"] for r in ov.tabela_orgaos(con, "2026-01-01", "2026-08-31", minimo=299)}
    assert com_299 == {"1", "2"}


def test_corte_de_assuntos_em_200(con):
    assert ov.MIN_ASSUNTO == 200
    assuntos = {r["assunto"]: r["volume"] for r in ov.tabela_assuntos(con, "2026-01-01", "2026-08-31")}
    assert assuntos == {"Assunto X": 200}
    com_199 = {r["assunto"] for r in ov.tabela_assuntos(con, "2026-01-01", "2026-08-31", minimo=199)}
    assert com_199 == {"Assunto X", "Assunto Y"}


def test_assunto_vazio_nao_entra_no_ranking(con):
    nomes = {r["assunto"] for r in ov.tabela_assuntos(con, "2026-01-01", "2026-08-31", minimo=1)}
    assert "Não informado" not in nomes
    assert nomes == {"Assunto X", "Assunto Y", "Assunto Z"}


def test_campos_vazios_nao_quebram_o_calculo(con):
    assert ov.taxa_no_prazo(con, "2026-05-01", "2026-05-31") is None
    resumo = ov.resumo_12m(con)
    assert resumo["kpis"]["12m"]["volume"] == 607
    assert resumo["kpis"]["ant"]["volume"] == 0
    assert resumo["kpis"]["ant"]["pct_no_prazo"] is None
    esferas = {r["esfera"]: r["volume"] for r in resumo["esferas"]}
    assert esferas["Não informada"] == 5
    tipos = {r["tipo"]: r["volume"] for r in resumo["tipos"]}
    assert tipos["Não informado"] == 5


def test_prazo_ainda_nao_vencido_fica_fora_da_conta(con):
    r = con.execute("select sum(com_prazo::int), sum(aval::int), sum(fora::int), sum(pend::int) from v where mes = '2026-08'").fetchone()
    assert r == (3, 0, 0, 0)


def test_pendencias_vencidas(con, linhas_brutas):
    esperado = sum(
        1 for r in linhas_brutas
        if not r["data resposta"] and r["data prazo resposta"] and data(r["data prazo resposta"]) <= CORTE
    )
    assert esperado == 75
    assert ov.indicadores_janela(con, "2026-01-01", "2026-08-31")["pendentes_vencidas"] == esperado


def test_cubo_do_painel_soma_o_total_e_reproduz_a_taxa(con):
    dados = ov.cubos(con)
    principal = dados["principal"]
    assert sum(principal["cols"]["n"]) == 607 == dados["base"]["manifestacoes"]
    i_mar = principal["dims"]["mes"].index("2026-03")
    av = sum(a for a, m in zip(principal["cols"]["av"], principal["cols"]["mes"]) if m == i_mar)
    fo = sum(f for f, m in zip(principal["cols"]["fo"], principal["cols"]["mes"]) if m == i_mar)
    assert round(100.0 * (av - fo) / av, 1) == ov.taxa_no_prazo(con, "2026-03-01", "2026-03-31")
    assert dados["cortes"] == {"orgaos": 300, "assuntos": 200}
    assert sum(dados["orgaos"]["cols"]["n"]) == 607
    assert sum(dados["assuntos"]["cols"]["n"]) == 607


def test_orgaos_com_nome_repetido_recebem_cidade_e_uf(con):
    nomes = {r["cod_orgao"]: r["orgao"] for r in ov.tabela_orgaos(con, "2026-01-01", "2026-08-31", minimo=1)}
    assert nomes["1"] == "Órgão A"
    assert nomes["2"] == "Prefeitura Municipal (ITAJAÍ/SC)"
    assert nomes["3"] == "Prefeitura Municipal (BIGUAÇU/SC)"


def test_satisfacao_conta_so_quem_respondeu(con):
    r = ov.indicadores_janela(con, "2026-03-01", "2026-03-31")
    assert r["volume"] == 300
    s = con.execute("select sum(sat_n::int), sum(sat_pos::int), sum(atend_n::int), sum(atend_pos::int) from v").fetchone()
    assert s == (60, 30, 60, 30)
