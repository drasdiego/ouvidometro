# Ouvidômetro

[![testes](https://github.com/drasdiego/ouvidometro/actions/workflows/testes.yml/badge.svg)](https://github.com/drasdiego/ouvidometro/actions/workflows/testes.yml)

## Principais achados

Recorte principal: manifestações registradas de setembro de 2025 a agosto de 2026, comparadas com as de setembro de 2024 a agosto de 2025. Os números saem dos arquivos em `painel/`, gerados por `analise/gerar_indicadores.py` a partir do arquivo da CGU de 01/09/2026.

1. **O volume cresceu 20,1% e o cumprimento do prazo caiu 0,8 ponto.** Foram 1.721.823 manifestações, contra 1.434.183 no período anterior. A parcela respondida no prazo passou de 89,0% para 88,2%. Fonte: `painel/kpis.csv`, colunas `volume` e `pct_no_prazo`.
2. **Quem recebe resposta espera menos.** A mediana do tempo de resposta caiu de 13 para 9 dias e a média, de 20,1 para 16,2 dias. Uma em cada dez respostas ainda leva mais de 36 dias. Fonte: `painel/kpis.csv`, colunas `mediana_dias`, `tempo_medio_dias` e `p90_dias`.
3. **O atraso se concentra na esfera municipal.** Os órgãos municipais responderam 66,9% no prazo (69,4% no período anterior), contra 90,3% dos federais. Eles recebem 8,6% das manifestações e respondem por 43,9% das 59.426 pendências vencidas em 31/08/2026. Fonte: `painel/esferas.csv`, colunas `volume`, `pct_no_prazo`, `pct_no_prazo_ant` e `pendentes_vencidas`.

Ressalva: o período mais recente teve menos tempo para ser respondido, então a comparação de pendências entre os dois períodos não é justa e não foi usada. A definição de cada indicador está em "Definições".

Painel sobre prazo e atraso nas manifestações de ouvidoria registradas no Fala.BR, com dados abertos da Controladoria-Geral da União (CGU). É um projeto pessoal de Diego Arruda e não é um produto oficial da CGU.

Painel no ar: https://drasdiego.github.io/ouvidometro/

Ele é interativo (filtros de período, esfera, tipo e UF, clique nas barras para filtrar, lista de órgãos) e também abre direto do arquivo `painel/index.html`, sem internet.

## Como reproduzir

Requer Python 3.10 ou mais novo.

```bash
git clone https://github.com/drasdiego/ouvidometro.git
cd ouvidometro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python analise/preparar_dados.py --baixar
python analise/gerar_painel.py
python analise/gerar_indicadores.py
pytest -v
open painel/index.html
```

- `python3 -m venv .venv` cria um ambiente isolado na pasta do projeto, e `source .venv/bin/activate` o ativa. No Windows, ative com `.venv\Scripts\activate`.
- `preparar_dados.py` baixa o ZIP da CGU (cerca de 190 MB), converte os CSVs de Latin-1 para UTF-8 e grava um Parquet por ano em `dados/tratados/por_ano/`.
- `ouvidometro.py` concentra as regras de cálculo: o que conta como no prazo, pendência, prorrogação e os cortes mínimos de volume.
- `gerar_painel.py` agrega a base com DuckDB por mês, esfera, tipo, UF, órgão e assunto e grava `painel/dados.js`, que alimenta os filtros do painel.
- `gerar_indicadores.py` grava um resumo dos últimos 12 meses em `painel/indicadores.json` e em CSVs.
- `pytest -v` roda os 14 testes. Como a base foi baixada no passo anterior, os 2 que conferem a base real também rodam; sem ela, eles são pulados (veja "Testes").
- `open` é o comando do macOS. No Linux use `xdg-open` e no Windows, `start`.

Os dados brutos e tratados não vão para o repositório (veja `.gitignore`), só os agregados. A CGU atualiza o arquivo todo mês: quem baixar depois terá registros mais novos, e os números do recorte mudam se a data de corte em `analise/ouvidometro.py` for alterada.

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

## Estrutura

```
analise/
  preparar_dados.py     download, conversão e Parquet por ano
  ouvidometro.py        regras de cálculo e agregações (DuckDB)
  gerar_painel.py       dados agregados do painel interativo
  gerar_indicadores.py  resumo dos últimos 12 meses em JSON e CSV
tests/
  test_agregacao.py     testes com base sintética, rodam em qualquer máquina
  test_base_real.py     conferência contra os CSVs da CGU, roda só com a base baixada
painel/
  index.html            o painel (HTML, CSS e JavaScript)
  dados.js              dados agregados usados pelo painel
  d3.min.js             biblioteca de gráficos D3 7.9.0 (licença ISC)
  *.csv                 resumo dos últimos 12 meses
```

## Testes

```bash
pytest -v
```

São 14 testes em pytest:

- 12 usam uma base sintética de 607 linhas, criada dentro do próprio teste, e rodam no GitHub Actions a cada push. Conferem o total contra a base bruta, o percentual no prazo de um mês contra um cálculo independente em Python puro, os cortes de 300 manifestações para órgãos e 200 para assuntos, o tratamento de campos vazios, as pendências vencidas, o prazo ainda não vencido e os dados que o painel carrega.
- 2 conferem a base real da CGU: o total do painel contra a contagem dos CSVs brutos e o percentual no prazo de março de 2025 contra um cálculo independente. Como a base não vai para o repositório, eles são pulados no GitHub Actions e rodam só em quem baixou os dados.

## Definições

- **Respondidas no prazo:** o complemento de "fora do prazo", sobre as manifestações com prazo vencido.
- **Fora do prazo:** respondida depois da data de prazo, ou sem resposta com o prazo vencido em 31/08/2026. Manifestações com prazo ainda não vencido nessa data não entram na conta. A data de prazo do arquivo já inclui as prorrogações.
- **Sem data de prazo:** fica fora da conta de prazo. Quase todas são do tipo Comunicação, que relata uma irregularidade sem pedir resposta.
- **Dias até a resposta:** mediana e percentil 90 dos dias entre registro e resposta, só das já respondidas.
- **Pendências vencidas:** sem resposta e com prazo vencido em 31/08/2026, com a idade contada a partir do prazo.
- **Órgãos:** agrupados pelo código do órgão. Nomes genéricos (como "Prefeitura Municipal") e nomes repetidos aparecem com cidade e UF. A tabela considera órgãos com pelo menos 300 manifestações no filtro escolhido; os assuntos, pelo menos 200. Os dois cortes são definidos em `analise/ouvidometro.py` e valem também para os CSVs.
- **Prazo prorrogado:** estimado por mais de 45 dias entre registro e prazo, porque a base não tem campo de prorrogação.

## Como o painel foi pensado

O desenho partiu de duas fontes: publicações de gestores e analistas em redes profissionais sobre dashboards que são usados e os que ninguém abre, e as falhas mais comuns encontradas em revisões de projetos de dados publicados por outras pessoas. Daí vieram as regras do painel:

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

## Licença

**Código:** licença MIT, no arquivo [LICENSE](LICENSE). Vale para os scripts em `analise/` e para o HTML, o CSS e o JavaScript do painel escritos para este projeto.

**Biblioteca de terceiros:** `painel/d3.min.js` é a D3 7.9.0, distribuída pelos seus autores sob a licença ISC.

**Dados:** não são de autoria deste projeto e não estão cobertos pela licença MIT. Vêm do arquivo público "Manifestações de ouvidoria" da Controladoria-Geral da União (CGU), publicado em https://www.gov.br/cgu/pt-br/acesso-a-informacao/dados-abertos/arquivos/ouvidoria. O arquivo usado foi gerado pela CGU em 01/09/2026 (data dos CSVs dentro do ZIP) e baixado em 11/11/2026. Os arquivos em `painel/` (`dados.js`, `indicadores.json` e os CSVs) são agregações desses dados feitas pelos scripts deste repositório. Ao reutilizar, cite a CGU como fonte.

## Autor

Projeto pessoal de Diego Arruda, feito por conta própria, com dados públicos.

Não é um produto oficial da Controladoria-Geral da União nem de qualquer órgão público, e não tem vínculo com nenhuma instituição. As análises e eventuais erros são de responsabilidade do autor.

Diego Arruda · [@drasdiegotech](https://www.instagram.com/drasdiegotech/) · [github.com/drasdiego](https://github.com/drasdiego)
