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

def verificar_senha_repetida(id_usuario, nova_senha, cur):
    #Cria uma lista vazia que vai guardar todas as senhas antigas (em formato hash)
    senhas_para_checar = []
    #Busca no banco de dados a senha ATUAL que o usuário está usando
    cur.execute("SELECT SENHA_HASH FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
    atual = cur.fetchone()# Pega apenas o primeiro resultado encontrado
    # Se encontrou a senha atual e ela não é vazia, adiciona na nossa lista
    if atual and atual[0]:
        senhas_para_checar.append(atual[0])

    #Busca no banco de dados o histórico das duas senhas mais antigas
    cur.execute("SELECT SENHA_NOVA, SENHA_NOVISSIMA FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
    antigas = cur.fetchone()
    # Se o usuário tiver um histórico de senhas salvo...
    if antigas:
        if antigas[0]: senhas_para_checar.append(antigas[0])
        if antigas[1]: senhas_para_checar.append(antigas[1])

    # 4. Fase de Verificação (A Mágica da Criptografia)
    # Vamos passar por cada hash de senha antiga que guardamos na nossa lista
    for senha_banco in senhas_para_checar:
        # O check_password_hash traduz a criptografia.
        # Ele testa se a 'nova_senha' (texto puro, ex: "12345") gera o mesmo
        # resultado do 'senha_banco' (texto criptografado).
        if check_password_hash(senha_banco, nova_senha):
            # Se bater, significa que ele já usou essa senha. Retorna True (Repetida!)
            return True
    # Se o loop terminar e não encontrar nenhuma repetição, a senha é inédita.
    # Retorna False (Não é repetida, pode prosseguir!)
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