import ouvidometro as ov

if __name__ == "__main__":
    con = ov.conectar()
    dados = ov.cubos(con)
    tamanho = ov.gravar_painel(dados)
    print("manifestacoes", dados["base"]["manifestacoes"], "tamanho_mb", round(tamanho / 1e6, 2))
