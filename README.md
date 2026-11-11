# Ouvidômetro

Painel sobre prazo e atraso nas manifestações de ouvidoria registradas no Fala.BR, com dados abertos da Controladoria-Geral da União (CGU).

Para ver o painel, abra `painel/index.html` no navegador. Ele é interativo (filtros de período, esfera, tipo e UF, clique nas barras para filtrar, busca de órgão) e funciona sem internet e no GitHub Pages.

## O que é

O Ouvidômetro mede como os órgãos públicos respondem às manifestações dos cidadãos: quanto tempo levam, quanto fica fora do prazo e onde as pendências se acumulam. A pergunta de fundo é a de um gestor de ouvidoria: onde agir primeiro.

O painel responde a seis perguntas:

1. O prazo da lei é cumprido, e isso melhorou?
2. Quanto tempo o cidadão espera pela resposta?
3. O que está pendente com o prazo vencido?
4. Em que esfera, tipo, UF e assunto o prazo mais estoura?
5. Quais órgãos precisam de atenção primeiro?
6. A demanda foi atendida, e o atraso pesa na satisfação?

## Base legal

O painel confronta os dados com as regras de ouvidoria:

- **Decreto 9.492/2018, art. 18:** resposta conclusiva em 30 dias, prorrogável uma vez por mais 30, com justificativa. O pedido de complementação suspende o prazo.
- **Decreto 9.492/2018, art. 3º:** definições de reclamação, denúncia, elogio, sugestão e solicitação.
- **Decreto 9.492/2018, art. 16:** uso obrigatório do e-Ouv (hoje Fala.BR) pelos órgãos federais.
- **Decreto 9.492/2018, art. 23, § 2º:** comunicações de irregularidade, mesmo anônimas.
- **Lei 13.460/2017:** direitos do usuário de serviços públicos, vigência em etapas por porte do ente e medição anual da satisfação.

O próprio painel traz uma tabela que liga cada regra ao indicador que a confere e uma seção de dúvidas frequentes.

## De onde vêm os dados

Arquivo público de manifestações de ouvidoria da CGU, atualizado todo mês:
https://www.gov.br/cgu/pt-br/acesso-a-informacao/dados-abertos/arquivos/ouvidoria

O arquivo usado foi gerado em 01/09/2026 e traz um CSV por ano, de 2014 a 2026, com 26 campos: datas de registro, prazo e resposta, tipo, órgão, assunto, situação, esfera, pesquisa de satisfação e campos de perfil do manifestante. O dicionário de dados está na mesma página.

Recorte usado:

- de janeiro de 2015 a 31/08/2026, com 8.752.496 manifestações;
- 2014 ficou de fora: o sistema e-Ouv foi lançado em 08/12/2014 e o arquivo tem só 17 registros naquele ano;
- o recorte principal do painel são os últimos 12 meses completos (set/2025 a ago/2026), comparados aos 12 anteriores.

## Como reproduzir

Requer Python 3.10 ou mais novo.

```bash
pip install -r requirements.txt
python analise/preparar_dados.py --baixar
python analise/gerar_painel.py
python analise/gerar_indicadores.py
```

- `preparar_dados.py` baixa o ZIP da CGU (cerca de 190 MB), converte os CSVs de Latin-1 para UTF-8 e grava um Parquet por ano em `dados/tratados/por_ano/`.
- `gerar_painel.py` agrega a base com DuckDB por mês, esfera, tipo, UF, órgão e assunto e grava `painel/dados.js`, que alimenta os filtros do painel.
- `gerar_indicadores.py` grava um resumo dos últimos 12 meses em `painel/indicadores.json` e em CSVs, para quem quiser os números fora do painel.

Os dados brutos e tratados não vão para o repositório (veja `.gitignore`), só os indicadores agregados.

## Estrutura

```
analise/
  preparar_dados.py     download, conversão e Parquet por ano
  gerar_painel.py       dados agregados do painel interativo
  gerar_indicadores.py  resumo dos últimos 12 meses em JSON e CSV
painel/
  index.html            o painel (HTML, CSS e JavaScript)
  dados.js              dados agregados usados pelo painel
  d3.min.js             biblioteca de gráficos D3 7.9.0 (licença ISC)
  *.csv                 resumo dos últimos 12 meses
```

## Definições

- **Respondidas no prazo:** o complemento de "fora do prazo", sobre as manifestações com prazo vencido.
- **Fora do prazo:** respondida depois da data de prazo, ou sem resposta com o prazo vencido em 31/08/2026. Manifestações com prazo ainda não vencido nessa data não entram na conta. A data de prazo do arquivo já inclui as prorrogações.
- **Sem data de prazo:** fica fora da conta de prazo. Quase todas são do tipo Comunicação, que relata uma irregularidade sem pedir resposta.
- **Dias até a resposta:** mediana e percentil 90 dos dias entre registro e resposta, só das já respondidas.
- **Pendências vencidas:** sem resposta e com prazo vencido em 31/08/2026, com a idade contada a partir do prazo.
- **Órgãos:** agrupados pelo código do órgão. Nomes genéricos (como "Prefeitura Municipal") e nomes repetidos aparecem com cidade e UF. A tabela considera órgãos com pelo menos 300 manifestações no filtro escolhido; os assuntos, pelo menos 200.
- **Prazo prorrogado:** estimado por mais de 45 dias entre registro e prazo, porque a base não tem campo de prorrogação.

## Como o painel foi pensado

O desenho partiu de duas fontes: posts de gestores e analistas no LinkedIn sobre dashboards que são usados e os que ninguém abre, e as falhas mais comuns encontradas em revisões de projetos de dados publicados por outras pessoas. Daí vieram as regras do painel:

- cada seção responde a uma pergunta de decisão, e não só exibe números;
- cor de alerta para dizer onde olhar primeiro (verde abaixo da média, amarelo até o dobro, vermelho acima do dobro);
- média acompanhada da cauda: a mediana mostra o caso típico, o percentil 90 mostra quem espera demais;
- pendências com idade, e não só a contagem;
- denominador explícito em toda proporção e data de corte visível;
- ranking por taxa, com volume mínimo, para não punir quem recebe mais manifestações;
- dados reais e públicos, com o caminho para reproduzir cada número.

## Limitações

- O campo "dias de atraso" do arquivo só vem preenchido para manifestações sem resposta. Por isso o atraso foi calculado pelas datas.
- Nos meses mais recentes há mais manifestações em aberto, então a mediana e o percentil 90 de dias ficam um pouco abaixo do real.
- A pesquisa de satisfação é opcional: no período, menos de 4% das manifestações têm resposta, com peso maior de quem ficou insatisfeito.
- Os campos de perfil do manifestante (faixa etária, raça/cor, gênero) têm mais de 80% de vazios e ficaram fora.
- A base inclui estados e municípios que aderiram ao Fala.BR, e não todos os órgãos do país.

## Autor

Diego Arruda · [@drasdiegotech](https://www.instagram.com/drasdiegotech/) · [github.com/drasdiego](https://github.com/drasdiego)
