import random
import string
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from flask import request, jsonify
import threading, smtplib
import jwt, datetime
from main import app


def gerar_codigo(tamanho=6):
    return ''.join(random.choices(string.digits, k=tamanho))

def verificar_senha(senha):

    if len(senha) < 10:
        return "A senha deve ter no mínimo 10 caracteres"

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_simbolo = False
    simbolos = "!@#$%^&*()_+-=[]}{|;:,.<>?"

    for letra in senha:
        if letra.isupper():
            tem_maiuscula = True
        elif letra.islower():
            tem_minuscula = True
        elif letra.isdigit():
            tem_numero = True
        elif letra in simbolos:
            tem_simbolo = True

    if not tem_maiuscula: return "Falta uma letra maiúscula"
    if not tem_minuscula: return "Falta uma letra minúscula"
    if not tem_numero:    return "Falta um número"
    if not tem_simbolo:   return "Falta um símbolo especial"

    return None



def enviando_email(destinatario, assunto, mensagem_html):
    user = 'estoquecars@gmail.com'
    senha = 'sozzflywdrfxxntv'


    msg = MIMEMultipart()
    msg['Subject'] = assunto
    msg['From'] = user
    msg['To'] = destinatario


    msg.attach(MIMEText(mensagem_html, 'html', 'utf-8'))
    try:
        contexto = ssl.create_default_context()

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto) as server:
            server.set_debuglevel(1)
            server.login(user, senha)
            server.sendmail(user, destinatario, msg.as_string())

        print(f"E-mail enviado com sucesso para {destinatario}")

    except Exception as e:
        print(f"Erro ao enviar e-mail para {destinatario}: {e}")

senha_secreta = app.config['SECRET_KEY']
def gerar_token(id_user):
    payload = {
        'id_user' : id_user,
        'timestamp' : datetime.datetime.utcnow().isoformat(),
        'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    }
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    return token




