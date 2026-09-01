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

    return {
        "response": "SUCESSO",
        "messages": [
            {
                "text": "Webhook da Uni Explorer recebeu os dados com sucesso!"
            }
        ]
    }
