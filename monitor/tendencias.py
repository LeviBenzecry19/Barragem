"""Séries temporais: taxas de variação, chuva antecedente, velocidade inversa
(Fukuzono) e modelos de valor esperado com resíduos.

Funções puras. Cada série é uma lista de (t, valor) em ordem crescente de t,
com t em segundos (epoch). No servidor as séries são médias horárias do banco.
Detalhes em docs/03-metodologia-analise.md.
"""

import bisect
import math

DIA = 86400.0


def regressao_linear(xs, ys):
    """Coeficientes (a, b) de y = a + b·x por mínimos quadrados, ou None se x não varia."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def minimos_quadrados(linhas, alvos, ridge=1e-6):
    """Resolve (XᵀX + λI)·β = Xᵀy por eliminação de Gauss. Retorna β ou None se singular."""
    p = len(linhas[0])
    a = [[sum(r[i] * r[j] for r in linhas) + (ridge if i == j else 0.0) for j in range(p)]
         + [sum(r[i] * y for r, y in zip(linhas, alvos))] for i in range(p)]
    for col in range(p):
        pivo = max(range(col, p), key=lambda i: abs(a[i][col]))
        if abs(a[pivo][col]) < 1e-12:
            return None
        a[col], a[pivo] = a[pivo], a[col]
        for i in range(p):
            if i != col:
                f = a[i][col] / a[col][col]
                a[i] = [x - f * y for x, y in zip(a[i], a[col])]
    return [a[i][p] / a[i][i] for i in range(p)]


def valor_proximo(serie, t, tolerancia, tempos=None):
    """Valor da série no instante mais próximo de t, se estiver a até 'tolerancia' segundos.

    'tempos' (os t da série, já extraídos) evita refazer a lista em buscas repetidas.
    """
    if not serie:
        return None
    if tempos is None:
        tempos = [p[0] for p in serie]
    i = bisect.bisect_left(tempos, t)
    candidatos = [j for j in (i - 1, i) if 0 <= j < len(serie)]
    j = min(candidatos, key=lambda j: abs(tempos[j] - t))
    return serie[j][1] if abs(tempos[j] - t) <= tolerancia else None


def taxa_diaria(serie, agora, janela_h, min_horas):
    """Inclinação da regressão linear nas últimas 'janela_h' horas, em unidades por dia."""
    pontos = [(t, v) for t, v in serie if agora - janela_h * 3600 <= t <= agora]
    if len(pontos) < 3 or pontos[-1][0] - pontos[0][0] < min_horas * 3600:
        return None
    coef = regressao_linear([t for t, _ in pontos], [v for _, v in pontos])
    return coef[1] * DIA if coef else None


def chuva_antecedente(serie_chuva_24h, agora, k, dias, tempos=None):
    """Índice de precipitação antecedente: API = Σ k^d · P(agora − d dias).

    P é a chuva de 24 h registrada mais perto de cada dia anterior (até ±6 h).
    Equivale à recursão API_t = k·API_(t−1) + P_t. Dias sem dado contam zero.
    """
    if tempos is None:
        tempos = [p[0] for p in serie_chuva_24h]
    total, usados = 0.0, 0
    for d in range(dias):
        p = valor_proximo(serie_chuva_24h, agora - d * DIA, 6 * 3600, tempos)
        if p is not None:
            total += k ** d * p
            usados += 1
    return total if usados else None


def velocidade_inversa(serie, agora, janela_h, passo_h, v_min):
    """Método da velocidade inversa (Fukuzono) aplicado ao deslocamento.

    Calcula a velocidade (mm/dia) em blocos de 'passo_h' horas. Se as últimas
    velocidades acima de v_min mostram 1/v caindo de forma linear, extrapola o
    instante em que 1/v chega a zero. Retorna {"horas", "velocidade"} ou None.
    """
    inicio = agora - janela_h * 3600
    passo = passo_h * 3600
    blocos = int(janela_h / passo_h)
    velocidades = []
    for b in range(blocos):
        t0, t1 = inicio + b * passo, inicio + (b + 1) * passo
        ultimo = b == blocos - 1   # o último bloco inclui a leitura atual (t = agora)
        bloco = [(t, v) for t, v in serie if t0 <= t < t1 or (ultimo and t == t1)]
        coef = regressao_linear([t for t, _ in bloco], [v for _, v in bloco])
        if coef:
            velocidades.append((t0 + passo / 2, coef[1] * DIA))
    recentes = []
    for t, v in reversed(velocidades):   # sequência final de velocidades acima do mínimo
        if v <= v_min:
            break
        recentes.insert(0, (t, v))
    if len(recentes) < 4:
        return None
    coef = regressao_linear([t for t, _ in recentes], [1.0 / v for _, v in recentes])
    if not coef or coef[1] >= 0:
        return None
    t_ruptura = -coef[0] / coef[1]
    return {"horas": max((t_ruptura - agora) / 3600.0, 0.0), "velocidade": recentes[-1][1]}


def modelo_esperado(series, alvo, explicativas, agora, atuais, cfg_tendencias, piso_desvio):
    """Valor esperado de 'alvo' por regressão linear nas variáveis explicativas.

    Treina com o histórico entre 'janela_modelo_dias' e 'excluir_recentes_h'
    atrás (para não aprender a anomalia recente) e compara o valor atual com o
    previsto. Explicativas especiais: "api" (chuva antecedente no instante) e
    "tempo" (dias desde o início do treino, tendência de longo prazo do HST).
    Retorna {"medido", "previsto", "desvio", "z", "pontos"} ou None.
    """
    cfg = cfg_tendencias
    fim = agora - cfg["excluir_recentes_h"] * 3600
    treino = [(t, v) for t, v in series.get(alvo, []) if agora - cfg["janela_modelo_dias"] * DIA <= t <= fim]
    if len(treino) < cfg["min_pontos_modelo"] or alvo not in atuais:
        return None
    t0 = treino[0][0]
    tempos = {nome: [p[0] for p in s] for nome, s in series.items()}

    def explicar(t, valores_atuais=None):
        linha = [1.0]
        for nome in explicativas:
            if nome == "tempo":
                x = (t - t0) / DIA
            elif nome == "api":
                x = (valores_atuais or {}).get("api")
                if x is None:
                    x = chuva_antecedente(series.get("chuva_24h", []), t, cfg["api_k"], cfg["api_dias"],
                                          tempos.get("chuva_24h"))
            elif valores_atuais is not None:
                x = valores_atuais.get(nome)
            else:
                x = valor_proximo(series.get(nome, []), t, 1800, tempos.get(nome))
            if x is None:
                return None
            linha.append(x)
        return linha

    linhas, alvos = [], []
    for t, v in treino:
        linha = explicar(t)
        if linha:
            linhas.append(linha)
            alvos.append(v)
    p = len(explicativas) + 1
    if len(linhas) < max(cfg["min_pontos_modelo"], p + 2):
        return None
    beta = minimos_quadrados(linhas, alvos)
    atual = explicar(agora, atuais)
    if beta is None or atual is None:
        return None
    residuos = [y - sum(b * x for b, x in zip(beta, linha)) for linha, y in zip(linhas, alvos)]
    desvio = max(math.sqrt(sum(r * r for r in residuos) / (len(residuos) - p)), piso_desvio)
    previsto = sum(b * x for b, x in zip(beta, atual))
    medido = atuais[alvo]
    return {"medido": medido, "previsto": previsto, "desvio": desvio,
            "z": (medido - previsto) / desvio, "pontos": len(linhas)}
