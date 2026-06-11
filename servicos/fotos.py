from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename as nome_seguro_arquivo


EXTENSOES_FOTO_PERFIL = {"jpg", "jpeg", "png", "webp"}


def salvar_foto_perfil(arquivo, pasta_envio, usuario_id):
    """Valida, grava e devolve a URL publica da foto de perfil."""
    if not arquivo or not arquivo.filename:
        raise ValueError("Selecione uma imagem para enviar.")

    nome_original = nome_seguro_arquivo(arquivo.filename)
    extensao = nome_original.rsplit(".", 1)[-1].lower() if "." in nome_original else ""
    if extensao not in EXTENSOES_FOTO_PERFIL:
        raise ValueError("Use uma imagem JPG, PNG ou WEBP.")

    pasta_destino = Path(pasta_envio) / "fotos_perfil"
    pasta_destino.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"usuario-{usuario_id}-{uuid4().hex}.{extensao}"
    caminho_destino = pasta_destino / nome_arquivo
    arquivo.save(caminho_destino)

    return f"/static/arquivos_enviados/fotos_perfil/{nome_arquivo}"
