from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def inicio():
    return {
        "status": "online",
        "mensagem": "Webhook Uni Explorer funcionando!"
    }


@app.post("/webhook")
async def webhook(request: Request):

    dados = await request.json()

    print("================================")
    print("DADOS RECEBIDOS DO LEADCHAT:")
    print(dados)
    print("================================")

    # Captura a última resposta enviada pelo cliente
    destino = dados.get("lastContactMessage")

    print("DESTINO IDENTIFICADO:", destino)

    return {
        "response": "SUCESSO",
        "messages": [
            {
                "text": f"Destino identificado: {destino}"
            }
        ]
    }
