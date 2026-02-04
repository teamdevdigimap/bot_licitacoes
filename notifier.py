import smtplib
import os
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def enviar_email(caminho_arquivo, destinatario):
    # Configurações (Recomendado usar .env)
    EMAIL_DE = os.environ['EMAIL_DE']
    SENHA_APP = os.environ['SENHA_APP']
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_DE
    msg['To'] = destinatario
    msg['Subject'] = f"BOT Licitações - {os.path.basename(caminho_arquivo)}"

    corpo = "Olá,\n\nSegue em anexo a lista de novas licitações encontradas e filtradas pela IA."
    msg.attach(MIMEText(corpo, 'plain'))

    # Anexo
    with open(caminho_arquivo, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(caminho_arquivo)}")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_DE, SENHA_APP)
        server.send_message(msg)
        server.quit()
        print("[NOTIFICAÇÃO] E-mail enviado com sucesso!")
    except Exception as e:
        print(f"[ERRO E-MAIL] {e}")

def enviar_whatsapp(caminho_arquivo, numero_destino):
    # Exemplo utilizando uma API de WhatsApp (Ex: Evolution API)
    API_URL_WPP = "https://sua-instancia.com/message/sendMedia/instancia_nome"
    API_KEY_WPP = "sua_api_key"

    payload = {
        "number": numero_destino,
        "caption": "Segue o relatório de licitações de hoje.",
        "media": caminho_arquivo # Algumas APIs aceitam o path ou base64
    }
    
    # Nota: O envio de arquivos via WhatsApp requer que o arquivo esteja em um servidor 
    # ou seja enviado como multipart/form-data dependendo da API escolhida.
    print(f"[NOTIFICAÇÃO] WhatsApp enviado para {numero_destino} (Simulado).")