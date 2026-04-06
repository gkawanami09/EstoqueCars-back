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
from flask_bcrypt import generate_password_hash, check_password_hash


def gerar_codigo(tamanho=6):
    return ''.join(random.choices(string.digits, k=tamanho))

def atualizar_historico_senhas(id_usuario, nova_senha, cur):
    # Busca a senha atual do usuario
    cur.execute("SELECT SENHA_HASH FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
     # Pega o resultado da consulta (uma linha)
    atual_row = cur.fetchone()
    # Se encontrou a senha, pega o valor; senão, fica como None
    senha_atual_banco = atual_row[0] if atual_row else None

    # Busca o historico das duas ultimas senhas
    cur.execute("SELECT SENHA_NOVA, SENHA_NOVISSIMA FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
     # Pega o resultado da consulta
    historico = cur.fetchone()

    # Lista que vai armazenar todas as senhas para comparação
    # (senha atual + duas anteriores)
    senhas_para_checar = []

    # Se existe senha atual no banco, adiciona na lista
    if senha_atual_banco:
        senhas_para_checar.append(senha_atual_banco)
    if historico:
        if historico[0]:
            # Se a coluna SENHA_NOVA não for vazia, adiciona
            senhas_para_checar.append(historico[0])
        if historico[1]:
            # Se a coluna SENHA_NOVISSIMA não for vazia, adiciona
            senhas_para_checar.append(historico[1])

     # Verifica se a nova senha já foi usada anteriormente
    for senha_banco in senhas_para_checar:
         # check_password_hash compara a senha digitada com o hash salvo
        if check_password_hash(senha_banco, nova_senha):
             # Se for igual a alguma antiga, retorna True (senha repetida)
            return True

    # Atualiza o historico com a senha atual (antes de trocar pela nova)
    if senha_atual_banco:
         # Se já existe histórico
        if historico:
            cur.execute(
                "UPDATE SENHA SET SENHA_NOVISSIMA = ?, SENHA_NOVA = ? WHERE ID_USUARIO = ?",
                (historico[0], senha_atual_banco, id_usuario),
            )
        else:
            cur.execute(
                "INSERT INTO SENHA (ID_USUARIO, SENHA_NOVA) VALUES (?, ?)",
                (id_usuario, senha_atual_banco),
            )

    return False

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

    #MIMEMultipart ele e como um envelope vazio
    msg = MIMEMultipart()
    #nesse você escreve as informações por fora do envelope (Remetente, Destinatário, Assunto)
    msg['Subject'] = assunto
    msg['From'] = user
    msg['To'] = destinatario

    #o Attach ele significa Anexar ou colocar dentro
    #O (MIMEText(mensagem_html  voce pega o html criado como MIMEText e vai ser coloca dentro do envelope principal para pode ficar bonito
    msg.attach(MIMEText(mensagem_html, 'html', 'utf-8'))
    try:
        contexto = ssl.create_default_context()
        #with significa que ele abre a conexao executa o codigo  e fecha a conecao com a api do gmail
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
