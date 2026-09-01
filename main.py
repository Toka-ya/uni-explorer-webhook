from fastapi import FastAPI, Request
from fastapi.responses import Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, quote
import re

app = FastAPI()

DOWNLOAD_URL = "https://www.uniexplorer.com.br/download/"
WEBHOOK_BASE_URL = "https://uni-explorer-webhook.onrender.com"


@app.get("/")
async def inicio():
    return {
        "status": "online",
        "mensagem": "Webhook Uni Explorer funcionando!"
    }


def normalizar(texto):
    """
    Remove diferenças de maiúsculas/minúsculas,
    acentos e caracteres especiais.
    """

    texto = unquote(texto)
    texto = texto.lower()

    substituicoes = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "õ": "o",
        "ô": "o",
        "ö": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c"
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def buscar_pdf(destino):
    """
    Consulta a página /download/ e procura
    o PDF correspondente ao destino informado.
    """

    print("================================")
    print("CONSULTANDO PAGINA DE DOWNLOADS")
    print("Destino recebido:", destino)

    try:
        resposta = requests.get(
            DOWNLOAD_URL,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resposta.raise_for_status()

    except Exception as erro:
        print("ERRO AO ACESSAR PAGINA:", erro)
        return None

    soup = BeautifulSoup(resposta.text, "html.parser")

    arquivos = []

    for link in soup.find_all("a", href=True):

        href = link.get("href")
        nome = link.get_text(" ", strip=True)

        if not nome:
            nome = unquote(href.split("/")[-1])

        if ".pdf" in nome.lower() or ".pdf" in href.lower():

            url_pdf = urljoin(DOWNLOAD_URL, href)

            arquivos.append({
                "nome": nome,
                "url": url_pdf
            })

    print("PDFs encontrados:", len(arquivos))

    if not arquivos:
        print("NENHUM PDF ENCONTRADO")
        return None

    destino_normalizado = normalizar(destino)

    print("Destino normalizado:", destino_normalizado)

    # ================================================
    # REGRAS ESPECIAIS
    # ================================================

    if destino_normalizado == "chile":
        termos_busca = [
            "chile e argentina",
            "chile argentina"
        ]
    else:
        termos_busca = [destino_normalizado]

    # ================================================
    # PRIMEIRA TENTATIVA:
    # correspondência direta
    # ================================================

    for arquivo in arquivos:

        nome_normalizado = normalizar(arquivo["nome"])

        for termo in termos_busca:

            if termo in nome_normalizado:

                print("PDF ENCONTRADO!")
                print("Nome:", arquivo["nome"])
                print("URL:", arquivo["url"])
                print("================================")

                return arquivo

    # ================================================
    # SEGUNDA TENTATIVA:
    # comparação por palavras
    # ================================================

    palavras = destino_normalizado.split()

    palavras_ignoradas = {
        "pacote",
        "uni",
        "explorer",
        "viagem",
        "para",
        "de",
        "da",
        "do",
        "e"
    }

    palavras = [
        palavra
        for palavra in palavras
        if palavra not in palavras_ignoradas
    ]

    melhor_arquivo = None
    melhor_pontuacao = 0

    for arquivo in arquivos:

        nome_normalizado = normalizar(arquivo["nome"])

        pontuacao = 0

        for palavra in palavras:

            if palavra in nome_normalizado:
                pontuacao += 1

        if pontuacao > melhor_pontuacao:

            melhor_pontuacao = pontuacao
            melhor_arquivo = arquivo

    if melhor_arquivo and melhor_pontuacao > 0:

        print("PDF ENCONTRADO POR SIMILARIDADE!")
        print("Nome:", melhor_arquivo["nome"])
        print("URL:", melhor_arquivo["url"])
        print("Pontuação:", melhor_pontuacao)
        print("================================")

        return melhor_arquivo

    print("NENHUM PDF COMPATIVEL ENCONTRADO")
    print("================================")

    return None


# ====================================================
# ROTA PRINCIPAL
# ====================================================

@app.post("/webhook")
async def webhook(request: Request):

    dados = await request.json()

    print("================================")
    print("DADOS RECEBIDOS DO LEADCHAT:")
    print(dados)
    print("================================")

    destino = dados.get("lastContactMessage")

    print("DESTINO IDENTIFICADO:", destino)

    if not destino:

        return {
            "response": "ERRO",
            "messages": [
                {
                    "text": "Não consegui identificar o destino escolhido."
                }
            ]
        }

    # Procura o PDF
    pdf = buscar_pdf(destino)

    if pdf:

        print("PDF ORIGINAL:")
        print(pdf["nome"])
        print(pdf["url"])

        # ==================================================
        # URL DO NOSSO SERVIDOR
        # ==================================================

        nome_codificado = quote(
            pdf["nome"],
            safe=""
        )

        url_pdf_webhook = (
            f"{WEBHOOK_BASE_URL}/pdf/{nome_codificado}"
        )

        print("URL DO PDF PELO WEBHOOK:")
        print(url_pdf_webhook)

        print("NOME QUE ESTAMOS ENVIANDO:")
        print(pdf["nome"])

        print("================================")

        # ==================================================
        # TESTE:
        # ARQUIVO DENTRO DO OBJETO "file"
        # ==================================================

        return {
            "response": "SUCESSO",
            "messages": [
                {
                    "text": f"Segue o material de {destino}:"
                },
                {
                    "file": {
                        "fileUrl": url_pdf_webhook,
                        "fileName": pdf["nome"]
                    }
                }
            ]
        }

    return {
        "response": "ERRO",
        "messages": [
            {
                "text": (
                    f"Destino identificado: {destino}\n\n"
                    "Não encontrei um PDF correspondente "
                    "na página de downloads."
                )
            }
        ]
    }


# ====================================================
# ROTA DINÂMICA PARA ENTREGAR O PDF
# ====================================================

@app.get("/pdf/{nome_arquivo:path}")
async def entregar_pdf(nome_arquivo: str):

    nome_arquivo = unquote(nome_arquivo)

    print("================================")
    print("SOLICITAÇÃO DE PDF")
    print("Arquivo solicitado:", nome_arquivo)

    # Segurança básica
    if not nome_arquivo.lower().endswith(".pdf"):

        return {
            "erro": "Arquivo inválido. Apenas PDFs são permitidos."
        }

    # Monta a URL original
    url_original = urljoin(
        DOWNLOAD_URL,
        quote(nome_arquivo)
    )

    print("BAIXANDO PDF ORIGINAL:")
    print(url_original)

    try:

        resposta = requests.get(
            url_original,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resposta.raise_for_status()

    except Exception as erro:

        print("ERRO AO BAIXAR PDF:")
        print(erro)

        return {
            "erro": "Não foi possível baixar o PDF.",
            "detalhes": str(erro)
        }

    print("PDF BAIXADO COM SUCESSO")
    print("Tamanho:", len(resposta.content), "bytes")
    print("Nome final:", nome_arquivo)
    print("================================")

    # ==================================================
    # ENTREGA DO PDF
    # NÃO ALTERAMOS ESTA PARTE
    # ==================================================

    return Response(
        content=resposta.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nome_arquivo}"'
            )
        }
    )


# ====================================================
# ROTA DE TESTE
# ====================================================

@app.get("/pdf-teste")
async def pdf_teste():

    url_pdf = (
        "https://www.uniexplorer.com.br/download/"
        "Pacote%20Uni%20Explorer%20-%20Machu%20Picchu%2013P.pdf"
    )

    nome_arquivo = (
        "Pacote Uni Explorer - Machu Picchu 13P.pdf"
    )

    print("================================")
    print("TESTE DE PDF")
    print("URL:", url_pdf)

    try:

        resposta = requests.get(
            url_pdf,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resposta.raise_for_status()

    except Exception as erro:

        return {
            "erro": str(erro)
        }

    return Response(
        content=resposta.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nome_arquivo}"'
            )
        }
    )
# ====================================================
# ROTA DE TESTE DE NOME DO ARQUIVO
# ====================================================

@app.get("/teste/TESTE.pdf")
async def teste_nome_arquivo():

    url_pdf = (
        "https://www.uniexplorer.com.br/download/"
        "Pacote%20Uni%20Explorer%20-%20Machu%20Picchu%2013P.pdf"
    )

    print("================================")
    print("TESTE DE NOME DE ARQUIVO")
    print("Baixando:", url_pdf)

    try:

        resposta = requests.get(
            url_pdf,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resposta.raise_for_status()

    except Exception as erro:

        print("ERRO AO BAIXAR PDF:")
        print(erro)

        return {
            "erro": str(erro)
        }

    print("PDF BAIXADO")
    print("Tamanho:", len(resposta.content))
    print("Nome pretendido: TESTE.pdf")
    print("================================")

    return Response(
        content=resposta.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="TESTE.pdf"',
            "Content-Length": str(len(resposta.content))
        }
    )
