from fastapi import FastAPI, Request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re

app = FastAPI()

DOWNLOAD_URL = "https://www.uniexplorer.com.br/download/"


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

    # Procura todos os links da página
    for link in soup.find_all("a", href=True):

        href = link.get("href")
        nome = link.get_text(" ", strip=True)

        # Caso o texto do link esteja vazio,
        # usa o nome do arquivo na URL
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

    # ------------------------------------------------
    # REGRAS ESPECIAIS
    # ------------------------------------------------

    # Chile também pode representar Chile e Argentina
    if destino_normalizado == "chile":
        termos_busca = ["chile e argentina", "chile argentina"]
    else:
        termos_busca = [destino_normalizado]

    # ------------------------------------------------
    # PRIMEIRA TENTATIVA:
    # procura correspondência direta
    # ------------------------------------------------

    for arquivo in arquivos:

        nome_normalizado = normalizar(arquivo["nome"])

        for termo in termos_busca:

            if termo in nome_normalizado:

                print("PDF ENCONTRADO!")
                print("Nome:", arquivo["nome"])
                print("URL:", arquivo["url"])
                print("================================")

                return arquivo

    # ------------------------------------------------
    # SEGUNDA TENTATIVA:
    # compara palavras importantes
    # ------------------------------------------------

    palavras = destino_normalizado.split()

    # Remove palavras muito genéricas
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


@app.post("/webhook")
async def webhook(request: Request):

    dados = await request.json()

    print("================================")
    print("DADOS RECEBIDOS DO LEADCHAT:")
    print(dados)
    print("================================")

    # Captura a resposta escolhida pelo cliente
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

    return {
        "response": "SUCESSO",
        "messages": [
            {
                "text": f"Segue o material de {destino}:"
            },
            {
                "fileUrl": pdf["url"],
                "fileName": pdf["nome"]
            }
        ]
    }

    return {
        "response": "ERRO",
        "messages": [
            {
                "text": (
                    f"Destino identificado: {destino}\n\n"
                    "Não encontrei um PDF correspondente na página de downloads."
                )
            }
        ]
    }
