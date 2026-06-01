import random, os
import string
import smtplib
import ssl
import re
import unicodedata
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import request, jsonify
import threading, smtplib
import jwt, datetime
from main import con
from validate_docbr import RENAVAM
from functools import wraps
from pixqrcode import qrcode
# Importa o wraps, que serve para nÃ£o deixar a funÃ§Ã£o perder o nome original

from main import app
from flask_bcrypt import generate_password_hash, check_password_hash


def gerar_codigo(tamanho=6):
    return ''.join(random.choices(string.digits, k=tamanho))

def atualizar_historico_senhas(id_usuario, nova_senha, cur):
    # Busca a senha atual do usuario
    cur.execute("SELECT SENHA_HASH FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
     # Pega o resultado da consulta (uma linha)
    atual_row = cur.fetchone()
    # Se encontrou a senha, pega o valor; senÃ£o, fica como None
    senha_atual_banco = atual_row[0] if atual_row else None

    # Busca o historico das duas ultimas senhas
    cur.execute("SELECT SENHA_NOVA, SENHA_NOVISSIMA FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
     # Pega o resultado da consulta
    historico = cur.fetchone()

    # Lista que vai armazenar todas as senhas para comparaÃ§Ã£o
    # (senha atual + duas anteriores)
    senhas_para_checar = []

    # Se existe senha atual no banco, adiciona na lista
    if senha_atual_banco:
        senhas_para_checar.append(senha_atual_banco)
    if historico:
        if historico[0]:
            # Se a coluna SENHA_NOVA nÃ£o for vazia, adiciona
            senhas_para_checar.append(historico[0])
        if historico[1]:
            # Se a coluna SENHA_NOVISSIMA nÃ£o for vazia, adiciona
            senhas_para_checar.append(historico[1])

     # Verifica se a nova senha jÃ¡ foi usada anteriormente
    for senha_banco in senhas_para_checar:
         # check_password_hash compara a senha digitada com o hash salvo
        if check_password_hash(senha_banco, nova_senha):
             # Se for igual a alguma antiga, retorna True (senha repetida)
            return True

    # Atualiza o historico com a senha atual (antes de trocar pela nova)
    if senha_atual_banco:
         # Se jÃ¡ existe histÃ³rico
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

#def validacao_renavam(renavam)
#    # if not renavam

def recalcular_total_manutencao(id_manutencao, cur):
    cur.execute("""SELECT VALOR_COBRADO, QUANTIDADE FROM ITEM_MANUTENCAO WHERE ID_MANUTENCAO = ?""",(id_manutencao,))

    itens = cur.fetchall()

    total = 0
    for item in itens:
        valor = float(item[0])
        quantidade = int(item[1])
        total += valor * quantidade

    cur.execute("""UPDATE MANUTENCAO SET VALOR_TOTAL = ? WHERE ID_MANUTENCAO = ?""",(total, id_manutencao))
    return total


def verificar_senha(senha):
    if len(senha) < 10:
        return "A senha deve ter no mÃ­nimo 10 caracteres"

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

    if not tem_maiuscula: return "Falta uma letra maiÃºscula"
    if not tem_minuscula: return "Falta uma letra minÃºscula"
    if not tem_numero:    return "Falta um nÃºmero"
    if not tem_simbolo:   return "Falta um sÃ­mbolo especial"

    return None


def enviando_email(destinatario, assunto, mensagem_html):
    user = 'estoquecars@gmail.com'
    senha = 'sozzflywdrfxxntv'

    #MIMEMultipart ele e como um envelope vazio
    msg = MIMEMultipart()
    #nesse vocÃª escreve as informaÃ§Ãµes por fora do envelope (Remetente, DestinatÃ¡rio, Assunto)
    msg['Subject'] = assunto
    msg['From'] = user
    msg['To'] = destinatario

    #o Attach ele significa Anexar ou colocar dentro
    #O (MIMEText(mensagem_html voce pega o html criado como MIMEText e vai ser coloca dentro do envelope principal para pode ficar bonito
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
        'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=5000)
    }
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    return token


# renavam_validacao = RENAVAM()
# novo_renavam = renavam_validacao.generate()
# print(novo_renavam)


# =========================================================
# FORMATA OS CAMPOS NO PADRÃƒO PIX
# =========================================================
def format_field(id, value):

    # pega tamanho do valor
    size = f"{len(value):02d}"

    # retorna:
    # ID + TAMANHO + VALOR
    return f"{id}{size}{value}"


# =========================================================
# GERA ASSINATURA CRC16
# =========================================================
def crc16(payload):

    # polinÃ´mio padrÃ£o
    polinomio = 0x1021

    # valor inicial
    resultado = 0xFFFF

    # percorre payload
    for c in payload:

        resultado ^= (ord(c) << 8)

        # percorre bits
        for _ in range(8):

            # verifica bit mais significativo
            if resultado & 0x8000:

                resultado = (resultado << 1) ^ polinomio

            else:

                resultado <<= 1

            # limita em 16 bits
            resultado &= 0xFFFF

    # retorna hexadecimal
    return f"{resultado:04X}"




# =========================================================
# GERA IMAGEM QR CODE
# =========================================================
def gerar_qrcode(payload, nome_arquivo, pasta):

    # cria pasta automaticamente dentro de uploads
    pasta_destino = os.path.join(
        app.config['UPLOAD_FOLDER'],
        "pagamento",
        pasta
    )
    os.makedirs(pasta_destino, exist_ok=True)

    # gera QR Code
    qr = qrcode.make(payload)

    # caminho absoluto para salvar
    nome_imagem = f"{nome_arquivo}.png"
    caminho_absoluto = os.path.join(pasta_destino, nome_imagem)

    # salva imagem
    qr.save(caminho_absoluto)

    # caminho relativo para consumo no endpoint /uploads/<path:nome_arquivo>
    caminho_relativo = os.path.join("pagamento", pasta, nome_imagem)

    # retorna caminho
    return caminho_relativo.replace("\\", "/")




# Implementacao revisada para aumentar compatibilidade com leitores bancarios.
def _normalize_text(value, limit):
    value = str(value or "").strip().upper()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^A-Z0-9 ]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def _normalize_txid(txid):
    txid = str(txid or "***").strip()
    if txid == "***":
        return txid
    txid = re.sub(r"[^A-Za-z0-9]", "", txid)
    txid = txid[:25]
    return txid or "***"


def gerar_payload_pix(
    chave,
    nome,
    cidade,
    valor,
    txid="***"
):
    chave = str(chave or "").strip()
    if not chave:
        raise ValueError("Chave PIX invalida para gerar QR Code.")

    nome = _normalize_text(nome, 25) or "RECEBEDOR"
    cidade = _normalize_text(cidade, 15) or "CIDADE"
    txid = _normalize_txid(txid)

    valor_float = float(valor)
    if valor_float < 0:
        raise ValueError("Valor PIX invalido.")

    payload = ""
    payload += format_field("00", "01")

    # Estatico reutilizavel
    payload += format_field("01", "11")

    merchant_account = ""
    merchant_account += format_field("00", "br.gov.bcb.pix")
    merchant_account += format_field("01", chave)
    payload += format_field("26", merchant_account)

    payload += format_field("52", "0000")
    payload += format_field("53", "986")
    payload += format_field("54", f"{valor_float:.2f}")
    payload += format_field("58", "BR")
    payload += format_field("59", nome)
    payload += format_field("60", cidade)

    additional = format_field("05", txid)
    payload += format_field("62", additional)

    payload += "6304"
    payload += crc16(payload)
    return payload


def gerar_pix(
    chave,
    nome,
    cidade,
    valor,
    pasta,
    txid="***"
):
    txid_normalizado = _normalize_txid(txid)

    payload = gerar_payload_pix(
        chave=chave,
        nome=nome,
        cidade=cidade,
        valor=valor,
        txid=txid_normalizado
    )

    caminho_imagem = gerar_qrcode(
        payload,
        f"{txid_normalizado}",
        pasta
    )

    return {
        "imagem": caminho_imagem,
        "payload": payload
    }
def dados_requisicao():
    if request.form:
        return request.form.to_dict()
    return request.get_json(silent=True) or {}


def normalizar_tipo(valor):
    tipo = str(valor or "").strip().lower()

    if tipo in ["0", "entrada", "receita", "receitas"]:
        return 0

    if tipo in ["1", "saida", "saída", "despesa", "despesas"]:
        return 1

    return None


def texto_tipo(tipo):
    return "entrada" if int(tipo or 0) == 0 else "saida"


def normalizar_data(valor):
    if not valor:
        return datetime.date.today()

    texto = str(valor).strip()

    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.datetime.strptime(texto, formato).date()
        except ValueError:
            pass

    raise ValueError("Data inválida.")


def montar_financeiro(registro):
    return {
        "id": registro[0],
        "id_financeiro": registro[0],
        "descricao": registro[1],
        "tipo": texto_tipo(registro[2]),
        "tipo_codigo": registro[2],
        "data": str(registro[3]) if registro[3] else None,
        "data_financeiro": str(registro[3]) if registro[3] else None,
        "valor": float(registro[4] or 0)
    }


def filtros_financeiro():
    tipo = normalizar_tipo(request.args.get("tipo"))
    periodo = request.args.get("periodo")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    where = []
    params = []

    if tipo is not None:
        where.append("TIPO = ?")
        params.append(tipo)

    if periodo:
        try:
            dias = int(periodo)
            data_inicio = datetime.date.today() - datetime.timedelta(days=dias)
        except ValueError:
            pass

    if data_inicio:
        where.append("DATA_FINANCEIRO >= ?")
        params.append(normalizar_data(data_inicio))

    if data_fim:
        where.append("DATA_FINANCEIRO <= ?")
        params.append(normalizar_data(data_fim))

    sql_where = ""
    if where:
        sql_where = " WHERE " + " AND ".join(where)

    return sql_where, params

def descricao_com_veiculo(cur, descricao, id_veiculo):
    if not id_veiculo:
        return descricao

    cur.execute(
        """
        SELECT M.MARCA,
               V.MODELO,
               V.PLACA
        FROM VEICULO V
        LEFT JOIN MARCA M
            ON M.ID_MARCA = V.ID_MARCA
        WHERE V.ID_VEICULO = ?
        """,
        (id_veiculo,)
    )
    veiculo = cur.fetchone()

    if not veiculo:
        return descricao

    nome_veiculo = " ".join([str(valor).strip() for valor in veiculo[:2] if valor])
    if veiculo[2]:
        nome_veiculo = f"{nome_veiculo} - {str(veiculo[2]).strip()}" if nome_veiculo else str(veiculo[2]).strip()

    if not nome_veiculo or nome_veiculo.lower() in descricao.lower():
        return descricao

    return f"{descricao} | Veículo: {nome_veiculo}"



def nome_veiculo_por_id(cur, id_veiculo):
    if not id_veiculo:
        return ""

    cur.execute(
        """
        SELECT M.MARCA,
               V.MODELO,
               V.PLACA
        FROM VEICULO V
        LEFT JOIN MARCA M
            ON M.ID_MARCA = V.ID_MARCA
        WHERE V.ID_VEICULO = ?
        """,
        (id_veiculo,)
    )
    veiculo = cur.fetchone()

    if not veiculo:
        return ""

    nome = " ".join([str(valor).strip() for valor in veiculo[:2] if valor])
    if veiculo[2]:
        nome = f"{nome} - {str(veiculo[2]).strip()}" if nome else str(veiculo[2]).strip()

    return nome


def veiculo_da_transacao(cur, descricao):
    texto = str(descricao or "")

    if "| Veículo:" in texto:
        return texto.split("| Veículo:", 1)[1].strip()

    if "| Veículo:" in texto:
        return texto.split("| Veículo:", 1)[1].strip()

    if "| VeÃ­culo:" in texto:
        return texto.split("| VeÃ­culo:", 1)[1].strip()

    resultado = re.search(r"codigo da venda:\s*(\d+)", texto, re.IGNORECASE)
    if not resultado:
        return ""

    cur.execute(
        """
        SELECT ID_VEICULO
        FROM VENDA
        WHERE ID_VENDA = ?
        """,
        (int(resultado.group(1)),)
    )
    venda = cur.fetchone()

    if not venda:
        return ""

    return nome_veiculo_por_id(cur, venda[0])


def montar_financeiro_com_veiculo(cur, registro):
    transacao = montar_financeiro(registro)
    transacao["veiculo"] = veiculo_da_transacao(cur, transacao.get("descricao"))
    return transacao
