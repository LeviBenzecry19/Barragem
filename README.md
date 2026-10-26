# Sistema de Software e Hardware para Monitoramento da Estabilidade de Barragens

Protótipo acadêmico de um sistema integrado que coleta dados de sensores
instalados em uma barragem de terra, armazena, processa e apresenta essas
informações em um dashboard, classificando a situação em **Normal**,
**Atenção**, **Alerta** ou **Crítico**.

```
Sensores → ESP32 (IoT) → API → Banco de dados → Análise → Dashboard → Alertas
```

> ⚠️ **Aviso.** Este é um trabalho acadêmico. Os limites, pesos e parâmetros
> usados são experimentais e ilustrativos. O sistema **não substitui** a
> análise estrutural ou geotécnica de um profissional habilitado nem o Plano de
> Segurança de Barragens exigido pela Lei nº 12.334/2010.

## O que já funciona

- **API REST** que recebe leituras em JSON, valida e grava em **SQLite**.
- **Modelo de análise**: pressão hidrostática, carga piezométrica, tensão
  efetiva (σ' = σ − u), razão de poropressão e **fator de segurança** de talude
  infinito; **índice experimental de risco** ponderado e regras de alerta.
- **Modos de ruptura**, cada um combinando vários sensores e o histórico:
  galgamento (borda livre com recalque e ondas de vento, previsão por balanço
  hídrico), erosão interna (gradiente de saída, turbidez × vazão), talude de
  jusante (varredura de profundidade, γ variável, confiabilidade por Monte
  Carlo), talude de montante (rebaixamento rápido), sismo (FS pseudoestático) e
  deformações (taxas, Fukuzono). Modelos de valor esperado alertam pelo resíduo.
- **Alertas** gerados quando uma variável, um modo de ruptura ou o nível global
  sobe de nível, sem repetição enquanto o alerta anterior não for reconhecido.
- **Dashboard** web com valores atuais, níveis, limites, gráficos históricos,
  índice ao longo do tempo e lista de alertas.
- **Página de sensores** (`/sensores`), no estilo do Cisco Packet Tracer: topologia
  da estação (vista lógica, com cabos por tipo de interface e pacotes animados) e
  corte da barragem com a posição de cada sensor (vista física), explicação de cada
  sensor e formulário para digitar leituras, com prévia da classificação antes de enviar.
- **Simulador** de sensores com cinco cenários (normal, cheia, infiltração, sismo, rebaixamento).
- **Firmware ESP32** para os sensores de baixo custo, com fila de reenvio.
- **Testes automatizados** (61 testes) cobrindo fórmulas, modos de ruptura, séries temporais, regras, banco e API.

Tudo em Python com a biblioteca padrão: **não é preciso instalar pacotes**.

## Como executar

Requisito: Python 3.10 ou superior.

```bash
# 1. Iniciar o servidor (cria barragem.db automaticamente)
python -m monitor.servidor

# 2. Em outro terminal, gerar 24 h de dados de um cenário
python -m simulador.simulador --cenario infiltracao --modo historico --horas 24

# 3. Abrir o dashboard
#    http://localhost:8000
#    Sensores e entrada manual de leituras: http://localhost:8000/sensores
```

Outras opções:

```bash
# Envio contínuo, como uma estação real (uma leitura a cada 2 s)
python -m simulador.simulador --cenario cheia --modo tempo-real --intervalo 2

# Exigir chave de API para receber leituras
BARRAGEM_CHAVE_API=minha-chave python -m monitor.servidor
python -m simulador.simulador --chave-api minha-chave

# Rodar os testes
python -m unittest discover -s tests -t .
```

Para começar do zero, apague o arquivo `barragem.db`.

Os gráficos usam Chart.js carregado da internet; sem conexão, o restante do
dashboard funciona normalmente.

## Estrutura do repositório

```
monitor/                 Software de monitoramento
  config.py              Limites, pesos e parâmetros geotécnicos (metodologia)
  analise.py             Fórmulas, normalização, índice e classificação
  servico.py             Validação, avaliação e geração de alertas
  banco.py               Banco de dados SQLite
  servidor.py            API REST + dashboard
  web/                   Dashboard e página de sensores (HTML, CSS, JavaScript)
simulador/simulador.py   Gerador de dados simulados
firmware/esp32_barragem/ Firmware da estação de aquisição (ESP32)
tests/                   Testes automatizados
docs/                    Documentação do projeto
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [01 – Requisitos](docs/01-requisitos.md) | Atores, requisitos funcionais e não funcionais, regras de negócio, casos de uso |
| [02 – Variáveis e sensores](docs/02-variaveis-e-sensores.md) | O que cada variável indica, instrumento profissional × sensor do protótipo |
| [03 – Metodologia de análise](docs/03-metodologia-analise.md) | Fórmulas, limites, normalização, pesos, índice, regras de alerta, exemplo de cálculo |
| [04 – Arquitetura](docs/04-arquitetura.md) | Componentes, fluxo de dados, API |
| [05 – Banco de dados](docs/05-banco-de-dados.md) | Modelo ER, tabelas, consultas |
| [06 – Hardware](docs/06-hardware.md) | Componentes, ligações, conversões, calibração |
| [07 – Plano de testes](docs/07-plano-de-testes.md) | Testes automatizados, indicadores de avaliação, roteiro com hardware |
| [08 – Hardware necessário](docs/08-hardware-necessario.md) | Todo o hardware para a aplicação ser válida: protótipo e barragem real, especificações, energia, custos |
| [09 – Guia do projeto](docs/09-guia-do-projeto.md) | Tabela de hardware, interpretação e correlações de cada sensor, guia das 45 afirmações a referenciar e resumo do projeto |

## Variáveis monitoradas

| Variável | Indica | Equipamento | Peso no índice |
|---|---|---|---:|
| Nível do reservatório | Carga hidráulica | Sensor de nível | 15% |
| Pressão de poros | Saturação e pressão interna | Piezômetro | 25% |
| Vazão de infiltração | Comportamento da percolação | Medidor de vazão | 20% |
| Deslocamento horizontal | Movimentação do talude | Inclinômetro | 20% |
| Recalque | Movimentação vertical | Medidor de recalque | 10% |
| Chuva (24 h) | Influência das precipitações | Pluviômetro | 5% |
| Inclinação | Rotação da estrutura | Inclinômetro / acelerômetro | 5% |
| Vibração | Eventos sísmicos | Acelerômetro | alerta individual |
| Temperatura | Contexto ambiental | Termômetro | alerta individual |
| Turbidez da drenagem | Carreamento de solo (piping) | Turbidímetro | modo erosão interna |
| Vento | Ondas que reduzem a borda livre | Anemômetro | modo galgamento |
| Vazão afluente | Cheia chegando ao reservatório | Estação fluviométrica / previsão | modo galgamento |

Índice = Σ Wᵢ × nᵢ, com cada leitura normalizada de 0 a 1 e pesos somando 100%.
Detalhes e justificativa em [docs/03-metodologia-analise.md](docs/03-metodologia-analise.md).

## Equipe

| Integrante | Responsabilidade inicial |
|---|---|
| Lourenço Ferreira Fekete Othero | Desenvolvimento do software e integração do sistema |
| Igor Felix | Pesquisa de sensores e hardware |
| Maria Letícia Menezes Alves Nepomuceno | Pesquisa das variáveis e fórmulas |
| Levi Benzecry | Banco de dados, testes e documentação |

## Fontes

1. Agência Nacional de Águas e Saneamento Básico (ANA) — materiais e regulamentações sobre segurança de barragens.
2. U.S. Bureau of Reclamation — *Design Standards No. 13: Embankment Dams* (capítulos de infiltração, estabilidade e instrumentação).
3. U.S. Bureau of Reclamation — *Embankment Dam Instrumentation Manual*.
4. Brasil. Lei nº 12.334/2010 — Política Nacional de Segurança de Barragens.
