import ouvidometro as ov

if __name__ == "__main__":
    con = ov.conectar()
    resumo = ov.resumo_12m(con)
    ov.gravar_resumo(resumo)
    print("kpis", resumo["kpis"])
    print("orgaos", len(resumo["orgaos"]), "assuntos", len(resumo["assuntos"]))
