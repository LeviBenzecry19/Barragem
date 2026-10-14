"""Regras de negócio: recebe leituras, avalia e gera alertas."""

import logging
from datetime import datetime, timezone

from . import analise, config
from .config import NIVEIS

log = logging.getLogger("monitor")


class ErroValidacao(ValueError):
    pass


def agora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalizar_instante(texto):
    if texto is None:
        return agora_iso()
    try:
        dt = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError as e:
        raise ErroValidacao(f"Instante inválido: {texto!r}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validar_pacote(pacote):
    """Valida o JSON enviado pela estação de aquisição.

    Formato esperado:
        {"estacao": "EST-01", "instante": "2026-10-14T12:00:00Z" (opcional),
         "leituras": {"nivel_reservatorio": 10.4, "pressao_poros": 18.2, ...}}
    """
    if not isinstance(pacote, dict):
        raise ErroValidacao("O corpo deve ser um objeto JSON.")
    estacao = pacote.get("estacao") or "EST-01"
    leituras = pacote.get("leituras")
    if not isinstance(leituras, dict) or not leituras:
        raise ErroValidacao("Campo 'leituras' deve ser um objeto não vazio.")
    limpas = {}
    for chave, valor in leituras.items():
        if chave not in config.VARIAVEIS:
            raise ErroValidacao(f"Variável desconhecida: {chave!r}")
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ErroValidacao(f"Valor não numérico para {chave!r}")
        if valor != valor or valor in (float("inf"), float("-inf")):
            raise ErroValidacao(f"Valor inválido para {chave!r}")
        limpas[chave] = float(valor)
    return str(estacao), normalizar_instante(pacote.get("instante")), limpas


class Monitor:
    def __init__(self, banco):
        self.banco = banco

    def registrar(self, pacote):
        estacao, instante, leituras = validar_pacote(pacote)
        anterior = self.banco.ultima_avaliacao()
        self.banco.inserir_leituras(estacao, instante, leituras)

        # A avaliação usa a última leitura conhecida de cada sensor, pois nem
        # todos os sensores precisam enviar dados no mesmo pacote.
        atuais = {k: d["valor"] for k, d in self.banco.ultimas_leituras().items()}
        resultado = analise.avaliar(atuais)
        self.banco.inserir_avaliacao(instante, resultado)
        alertas = self._gerar_alertas(instante, anterior, resultado)
        return {"instante": instante, "avaliacao": resultado, "alertas_gerados": alertas}

    def _gerar_alertas(self, instante, anterior, atual):
        """Gera um alerta quando uma variável ou o nível global sobe de nível.

        Para evitar alertas repetidos quando uma leitura oscila em torno de um
        limite, o alerta não é gerado se já existir, para a mesma origem, um
        alerta pendente (não reconhecido) de nível igual ou superior.
        """
        gerados = []
        pendentes = self.banco.niveis_pendentes()
        niveis_antes = {}
        if anterior:
            niveis_antes = {k: d["nivel"] for k, d in anterior["variaveis"].items()}
            niveis_antes["global"] = anterior["nivel"]

        for chave, dados in atual["variaveis"].items():
            antes = niveis_antes.get(chave, "Normal")
            if self._deve_alertar(dados["nivel"], antes, pendentes.get(chave)):
                var = config.VARIAVEIS[chave]
                msg = (f"{var.nome}: {str(round(dados['valor'], 3)).replace('.', ',')} {var.unidade} "
                       f"({antes} → {dados['nivel']})")
                gerados.append(self._alertar(instante, chave, dados["nivel"], antes, dados["valor"], msg))

        antes = niveis_antes.get("global", "Normal")
        if self._deve_alertar(atual["nivel"], antes, pendentes.get("global")):
            msg = f"Nível global {antes} → {atual['nivel']}. " + "; ".join(atual["motivos"])
            gerados.append(self._alertar(instante, "global", atual["nivel"], antes, atual["indice"], msg))
        return gerados

    @staticmethod
    def _deve_alertar(nivel, anterior, pendente):
        if NIVEIS.index(nivel) <= NIVEIS.index(anterior):
            return False
        return pendente is None or NIVEIS.index(nivel) > NIVEIS.index(pendente)

    def _alertar(self, instante, origem, nivel, anterior, valor, mensagem):
        alerta_id = self.banco.inserir_alerta(instante, origem, nivel, anterior, valor, mensagem)
        log.warning("ALERTA [%s] %s", nivel, mensagem)
        return {"id": alerta_id, "origem": origem, "nivel": nivel, "mensagem": mensagem}

    def estado(self):
        avaliacao = self.banco.ultima_avaliacao()
        return {
            "avaliacao": avaliacao,
            "leituras": self.banco.ultimas_leituras(),
            "sensores": self.banco.sensores(),
            "alertas_pendentes": len(self.banco.alertas(apenas_pendentes=True, limite=1000)),
            "faixas_indice": config.FAIXAS_INDICE,
            "faixas_fs": config.FAIXAS_FS,
            "geotecnia": config.GEOTECNIA,
        }
