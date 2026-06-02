# Importa o módulo random para gerar escolhas aleatórias e o módulo os para lidar com pastas/arquivos.
import random, os
# Importa string para acessar listas prontas de caracteres, como dígitos.
import string
# Importa smtplib para enviar e-mails por SMTP.
import smtplib
# Importa ssl para criar conexão segura com o servidor de e-mail.
import ssl
# Importa re para usar expressões regulares.
import re
# Importa unicodedata para remover acentos de textos.
import unicodedata
# Importa MIMEText para montar o corpo do e-mail em HTML.
from email.mime.text import MIMEText
# Importa MIMEMultipart para montar o e-mail completo com cabeçalhos e corpo.
from email.mime.multipart import MIMEMultipart
# Importa request para ler dados da requisição e jsonify para retornar JSON.
from flask import request, jsonify
# Importa smtplib novamente para envio de e-mail.
import smtplib
# Importa jwt para gerar tokens e datetime para trabalhar com datas e horários.
import jwt, datetime
# Importa a conexão com o banco de dados.
from main import con
# Importa a validação de RENAVAM.
from validate_docbr import RENAVAM
# Importa wraps para preservar informações de funções decoradas.
from functools import wraps
# Importa a biblioteca usada para gerar QR Code PIX.
from pixqrcode import qrcode
# Importa a aplicação Flask principal.
from main import app
# Importa funções para gerar e conferir hash de senha.
from flask_bcrypt import generate_password_hash, check_password_hash


# Define a função que gera um código numérico aleatório.
def gerar_codigo(tamanho=6):
    # Retorna uma string juntando números aleatórios com o tamanho informado.
    return ''.join(random.choices(string.digits, k=tamanho))


# Define a função que verifica e atualiza o histórico de senhas do usuário.
def atualizar_historico_senhas(id_usuario, nova_senha, cur):
    # Busca a senha atual do usuário no banco.
    cur.execute("SELECT SENHA_HASH FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
    # Pega o resultado da consulta.
    atual_row = cur.fetchone()
    # Guarda a senha atual se o usuário foi encontrado; senão, guarda None.
    senha_atual_banco = atual_row[0] if atual_row else None

    # Busca as duas últimas senhas salvas no histórico.
    cur.execute("SELECT SENHA_NOVA, SENHA_NOVISSIMA FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
    # Pega o resultado da consulta do histórico.
    historico = cur.fetchone()

    # Cria uma lista para guardar as senhas que serão comparadas.
    senhas_para_checar = []

    # Verifica se existe uma senha atual no banco.
    if senha_atual_banco:
        # Adiciona a senha atual na lista de comparação.
        senhas_para_checar.append(senha_atual_banco)

    # Verifica se existe histórico de senhas.
    if historico:
        # Verifica se a coluna SENHA_NOVA tem valor.
        if historico[0]:
            # Adiciona a senha anterior na lista de comparação.
            senhas_para_checar.append(historico[0])
        # Verifica se a coluna SENHA_NOVISSIMA tem valor.
        if historico[1]:
            # Adiciona a senha mais antiga na lista de comparação.
            senhas_para_checar.append(historico[1])

    # Percorre cada senha salva para comparar com a nova senha.
    for senha_banco in senhas_para_checar:
        # Compara a senha digitada com o hash salvo no banco.
        if check_password_hash(senha_banco, nova_senha):
            # Retorna True se a senha nova já foi usada antes.
            return True

    # Verifica se existe senha atual para mover para o histórico.
    if senha_atual_banco:
        # Verifica se o usuário já tem histórico cadastrado.
        if historico:
            # Atualiza o histórico: a senha atual vira SENHA_NOVA e a anterior vira SENHA_NOVISSIMA.
            cur.execute(
                "UPDATE SENHA SET SENHA_NOVISSIMA = ?, SENHA_NOVA = ? WHERE ID_USUARIO = ?",
                (historico[0], senha_atual_banco, id_usuario),
            )
        # Entra aqui quando o usuário ainda não tem histórico cadastrado.
        else:
            # Cria o histórico salvando a senha atual como SENHA_NOVA.
            cur.execute(
                "INSERT INTO SENHA (ID_USUARIO, SENHA_NOVA) VALUES (?, ?)",
                (id_usuario, senha_atual_banco),
            )

    # Retorna False quando a senha nova não foi encontrada no histórico.
    return False


# Comentário antigo preservado: início de uma possível função de validação de RENAVAM.
# def validacao_renavam(renavam)
# Comentário antigo preservado: validação incompleta de RENAVAM.
#     # if not renavam


# Define a função que recalcula o total de uma manutenção.
def recalcular_total_manutencao(id_manutencao, cur):
    # Busca valor cobrado e quantidade de todos os itens da manutenção.
    cur.execute(
        """SELECT VALOR_COBRADO, QUANTIDADE FROM ITEM_MANUTENCAO WHERE ID_MANUTENCAO = ?""",
        (id_manutencao,),
    )

    # Guarda todos os itens encontrados.
    itens = cur.fetchall()

    # Começa o total da manutenção em zero.
    total = 0
    # Percorre cada item da manutenção.
    for item in itens:
        # Converte o valor cobrado para número decimal.
        valor = float(item[0])
        # Converte a quantidade para número inteiro.
        quantidade = int(item[1])
        # Soma valor vezes quantidade ao total.
        total += valor * quantidade

    # Atualiza o valor total da manutenção no banco.
    cur.execute(
        """UPDATE MANUTENCAO SET VALOR_TOTAL = ? WHERE ID_MANUTENCAO = ?""",
        (total, id_manutencao),
    )
    # Retorna o total recalculado.
    return total


# Define a função que valida se a senha segue as regras mínimas.
def verificar_senha(senha):
    # Verifica se a senha tem menos de 10 caracteres.
    if len(senha) < 10:
        # Retorna a mensagem de erro para senha curta.
        return "A senha deve ter no mínimo 10 caracteres"

    # Controla se a senha tem pelo menos uma letra maiúscula.
    tem_maiuscula = False
    # Controla se a senha tem pelo menos uma letra minúscula.
    tem_minuscula = False
    # Controla se a senha tem pelo menos um número.
    tem_numero = False
    # Controla se a senha tem pelo menos um símbolo.
    tem_simbolo = False
    # Define os símbolos aceitos como caracteres especiais.
    simbolos = "!@#$%^&*()_+-=[]}{|;:,.<>?"

    # Percorre cada caractere da senha.
    for letra in senha:
        # Verifica se o caractere é uma letra maiúscula.
        if letra.isupper():
            # Marca que a senha tem letra maiúscula.
            tem_maiuscula = True
        # Verifica se o caractere é uma letra minúscula.
        elif letra.islower():
            # Marca que a senha tem letra minúscula.
            tem_minuscula = True
        # Verifica se o caractere é um número.
        elif letra.isdigit():
            # Marca que a senha tem número.
            tem_numero = True
        # Verifica se o caractere está na lista de símbolos.
        elif letra in simbolos:
            # Marca que a senha tem símbolo especial.
            tem_simbolo = True

    # Retorna erro se faltar letra maiúscula.
    if not tem_maiuscula: return "Falta uma letra maiúscula"
    # Retorna erro se faltar letra minúscula.
    if not tem_minuscula: return "Falta uma letra minúscula"
    # Retorna erro se faltar número.
    if not tem_numero:    return "Falta um número"
    # Retorna erro se faltar símbolo especial.
    if not tem_simbolo:   return "Falta um símbolo especial"

    # Retorna None quando a senha passou em todas as regras.
    return None


# Define a função responsável por enviar e-mail.
def enviando_email(destinatario, assunto, mensagem_html):
    # Define o e-mail remetente.
    user = 'estoquecars@gmail.com'
    # Define a senha de aplicativo usada para autenticar no Gmail.
    senha = 'sozzflywdrfxxntv'

    # Cria um envelope de e-mail que pode ter várias partes.
    msg = MIMEMultipart()
    # Define o assunto do e-mail.
    msg['Subject'] = assunto
    # Define o remetente do e-mail.
    msg['From'] = user
    # Define o destinatário do e-mail.
    msg['To'] = destinatario

    # Anexa o HTML da mensagem dentro do e-mail.
    msg.attach(MIMEText(mensagem_html, 'html', 'utf-8'))
    # Tenta enviar o e-mail.
    try:
        # Cria um contexto SSL padrão para conexão segura.
        contexto = ssl.create_default_context()
        # Abre a conexão segura com o servidor SMTP do Gmail.
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto) as server:
            # Ativa mensagens de debug do SMTP.
            server.set_debuglevel(1)
            # Faz login no Gmail usando remetente e senha.
            server.login(user, senha)
            # Envia o e-mail para o destinatário.
            server.sendmail(user, destinatario, msg.as_string())

        # Mostra no terminal que o e-mail foi enviado.
        print(f"E-mail enviado com sucesso para {destinatario}")

    # Captura qualquer erro no envio do e-mail.
    except Exception as e:
        # Mostra no terminal a mensagem de erro.
        print(f"Erro ao enviar e-mail para {destinatario}: {e}")


# Guarda a chave secreta configurada no Flask.
senha_secreta = app.config['SECRET_KEY']


# Define a função que gera um token JWT para o usuário.
def gerar_token(id_user):
    # Monta os dados que serão salvos dentro do token.
    payload = {
        # Salva o ID do usuário no token.
        'id_user': id_user,
        # Salva o horário de criação do token.
        'timestamp': datetime.datetime.utcnow().isoformat(),
        # Define o horário de expiração do token.
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5000)
    }
    # Gera o token JWT usando a chave secreta e o algoritmo HS256.
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    # Retorna o token gerado.
    return token


# Comentário antigo preservado: criaria um validador de RENAVAM.
# renavam_validacao = RENAVAM()
# Comentário antigo preservado: geraria um RENAVAM novo.
# novo_renavam = renavam_validacao.generate()
# Comentário antigo preservado: mostraria o RENAVAM gerado.
# print(novo_renavam)


# =========================================================
# FORMATA OS CAMPOS NO PADRÃO PIX
# =========================================================
# Define a função que monta um campo do payload PIX.
def format_field(id, value):
    # Calcula o tamanho do valor com dois dígitos.
    size = f"{len(value):02d}"

    # Retorna o campo no formato ID + TAMANHO + VALOR.
    return f"{id}{size}{value}"


# =========================================================
# GERA ASSINATURA CRC16
# =========================================================
# Define a função que calcula o CRC16 do payload PIX.
def crc16(payload):
    # Define o polinômio padrão do algoritmo CRC16.
    polinomio = 0x1021

    # Define o valor inicial do cálculo.
    resultado = 0xFFFF

    # Percorre cada caractere do payload.
    for c in payload:
        # Aplica o caractere atual no resultado.
        resultado ^= (ord(c) << 8)

        # Percorre os 8 bits do caractere.
        for _ in range(8):
            # Verifica se o bit mais significativo está ativo.
            if resultado & 0x8000:
                # Desloca o resultado e aplica o polinômio.
                resultado = (resultado << 1) ^ polinomio

            # Entra aqui quando o bit mais significativo não está ativo.
            else:
                # Apenas desloca o resultado para a esquerda.
                resultado <<= 1

            # Limita o resultado para continuar com 16 bits.
            resultado &= 0xFFFF

    # Retorna o CRC16 em hexadecimal com quatro caracteres.
    return f"{resultado:04X}"


# =========================================================
# GERA IMAGEM QR CODE
# =========================================================
# Define a função que gera a imagem do QR Code.
def gerar_qrcode(payload, nome_arquivo, pasta):
    # Monta a pasta onde a imagem será salva.
    pasta_destino = os.path.join(
        # Usa a pasta principal de uploads configurada no Flask.
        app.config['UPLOAD_FOLDER'],
        # Usa a subpasta de pagamentos.
        "pagamento",
        # Usa a pasta específica recebida por parâmetro.
        pasta
    )
    # Cria a pasta de destino se ela ainda não existir.
    os.makedirs(pasta_destino, exist_ok=True)

    # Gera o QR Code a partir do payload.
    qr = qrcode.make(payload)

    # Monta o nome do arquivo de imagem com extensão PNG.
    nome_imagem = f"{nome_arquivo}.png"
    # Monta o caminho absoluto onde a imagem será salva.
    caminho_absoluto = os.path.join(pasta_destino, nome_imagem)

    # Salva a imagem do QR Code no caminho definido.
    qr.save(caminho_absoluto)

    # Monta o caminho relativo usado pelos endpoints do sistema.
    caminho_relativo = os.path.join("pagamento", pasta, nome_imagem)

    # Retorna o caminho relativo com barras no formato de URL.
    return caminho_relativo.replace("\\", "/")


# Implementação revisada para aumentar compatibilidade com leitores bancários.
# Define uma função interna para normalizar textos usados no PIX.
def _normalize_text(value, limit):
    # Converte o valor para texto, remove espaços, coloca em maiúsculo e trata None como vazio.
    value = str(value or "").strip().upper()
    # Separa acentos das letras usando normalização Unicode.
    value = unicodedata.normalize("NFKD", value)
    # Remove os acentos separados pela normalização.
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    # Remove caracteres que não sejam letras, números ou espaço.
    value = re.sub(r"[^A-Z0-9 ]", "", value)
    # Troca vários espaços seguidos por apenas um espaço.
    value = re.sub(r"\s+", " ", value).strip()
    # Retorna o texto limitado ao tamanho máximo.
    return value[:limit]


# Define uma função interna para normalizar o TXID do PIX.
def _normalize_txid(txid):
    # Converte o TXID para texto, remove espaços e usa "***" como padrão.
    txid = str(txid or "***").strip()
    # Verifica se o TXID é o valor padrão.
    if txid == "***":
        # Retorna o valor padrão sem alterações.
        return txid
    # Remove tudo que não for letra ou número.
    txid = re.sub(r"[^A-Za-z0-9]", "", txid)
    # Limita o TXID a 25 caracteres.
    txid = txid[:25]
    # Retorna o TXID normalizado ou "***" se ficou vazio.
    return txid or "***"


# Define a função que gera o payload PIX para copiar e colar.
def gerar_payload_pix(
    # Recebe a chave PIX.
    chave,
    # Recebe o nome do recebedor.
    nome,
    # Recebe a cidade do recebedor.
    cidade,
    # Recebe o valor do pagamento.
    valor,
    # Recebe o TXID e usa "***" como padrão.
    txid="***"
):
    # Converte a chave para texto e remove espaços.
    chave = str(chave or "").strip()
    # Verifica se a chave PIX foi informada.
    if not chave:
        # Interrompe a geração quando a chave PIX está vazia.
        raise ValueError("Chave PIX inválida para gerar QR Code.")

    # Normaliza o nome e usa RECEBEDOR se o nome ficar vazio.
    nome = _normalize_text(nome, 25) or "RECEBEDOR"
    # Normaliza a cidade e usa CIDADE se a cidade ficar vazia.
    cidade = _normalize_text(cidade, 15) or "CIDADE"
    # Normaliza o TXID informado.
    txid = _normalize_txid(txid)

    # Converte o valor do PIX para número decimal.
    valor_float = float(valor)
    # Verifica se o valor é negativo.
    if valor_float < 0:
        # Interrompe a geração quando o valor é inválido.
        raise ValueError("Valor PIX inválido.")

    # Inicia o payload vazio.
    payload = ""
    # Adiciona o indicador de formato do payload.
    payload += format_field("00", "01")

    # Adiciona o campo que indica PIX estático reutilizável.
    payload += format_field("01", "11")

    # Inicia os dados da conta do recebedor.
    merchant_account = ""
    # Adiciona o domínio oficial do Banco Central para PIX.
    merchant_account += format_field("00", "br.gov.bcb.pix")
    # Adiciona a chave PIX do recebedor.
    merchant_account += format_field("01", chave)
    # Adiciona os dados da conta do recebedor ao payload.
    payload += format_field("26", merchant_account)

    # Adiciona o código de categoria do comerciante.
    payload += format_field("52", "0000")
    # Adiciona o código da moeda brasileira.
    payload += format_field("53", "986")
    # Adiciona o valor do pagamento com duas casas decimais.
    payload += format_field("54", f"{valor_float:.2f}")
    # Adiciona o país do pagamento.
    payload += format_field("58", "BR")
    # Adiciona o nome do recebedor.
    payload += format_field("59", nome)
    # Adiciona a cidade do recebedor.
    payload += format_field("60", cidade)

    # Monta o campo adicional com o TXID.
    additional = format_field("05", txid)
    # Adiciona o campo adicional ao payload.
    payload += format_field("62", additional)

    # Adiciona o identificador do campo CRC16.
    payload += "6304"
    # Calcula e adiciona o CRC16 ao final do payload.
    payload += crc16(payload)
    # Retorna o payload PIX completo.
    return payload


# Define a função que gera o PIX completo, com payload e imagem.
def gerar_pix(
    # Recebe a chave PIX.
    chave,
    # Recebe o nome do recebedor.
    nome,
    # Recebe a cidade do recebedor.
    cidade,
    # Recebe o valor do pagamento.
    valor,
    # Recebe a pasta onde a imagem será salva.
    pasta,
    # Recebe o TXID e usa "***" como padrão.
    txid="***"
):
    # Normaliza o TXID antes de usar no payload e no nome da imagem.
    txid_normalizado = _normalize_txid(txid)

    # Gera o payload PIX para copiar e colar.
    payload = gerar_payload_pix(
        # Passa a chave PIX para a função.
        chave=chave,
        # Passa o nome do recebedor para a função.
        nome=nome,
        # Passa a cidade do recebedor para a função.
        cidade=cidade,
        # Passa o valor do pagamento para a função.
        valor=valor,
        # Passa o TXID normalizado para a função.
        txid=txid_normalizado
    )

    # Gera a imagem do QR Code e guarda o caminho.
    caminho_imagem = gerar_qrcode(
        # Passa o payload que será transformado em QR Code.
        payload,
        # Usa o TXID normalizado como nome do arquivo.
        f"{txid_normalizado}",
        # Passa a pasta onde a imagem será salva.
        pasta
    )

    # Retorna os dados do PIX em formato de dicionário.
    return {
        # Retorna o caminho da imagem.
        "imagem": caminho_imagem,
        # Retorna o payload para copiar e colar.
        "payload": payload
    }


# Define a função que lê dados enviados na requisição.
def dados_requisicao():
    # Verifica se a requisição veio como formulário.
    if request.form:
        # Retorna os campos do formulário como dicionário.
        return request.form.to_dict()
    # Retorna o JSON da requisição ou um dicionário vazio.
    return request.get_json(silent=True) or {}


# Define a função que transforma o tipo financeiro em código numérico.
def normalizar_tipo(valor):
    # Converte o valor para texto minúsculo, removendo espaços.
    tipo = str(valor or "").strip().lower()

    # Verifica se o tipo representa entrada/receita.
    if tipo in ["0", "entrada", "receita", "receitas"]:
        # Retorna 0 para entrada/receita.
        return 0

    # Verifica se o tipo representa saída/despesa.
    if tipo in ["1", "saida", "saída", "despesa", "despesas"]:
        # Retorna 1 para saída/despesa.
        return 1

    # Retorna None quando o tipo não é reconhecido.
    return None


# Define a função que transforma o código do tipo em texto.
def texto_tipo(tipo):
    # Retorna entrada para código 0 e saída para qualquer outro código.
    return "entrada" if int(tipo or 0) == 0 else "saída"


# Define a função que normaliza uma data recebida.
def normalizar_data(valor):
    # Verifica se nenhuma data foi informada.
    if not valor:
        # Retorna a data atual.
        return datetime.date.today()

    # Converte a data recebida para texto e remove espaços.
    texto = str(valor).strip()

    # Percorre os formatos aceitos pelo sistema.
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        # Tenta converter o texto usando o formato atual.
        try:
            # Retorna apenas a parte da data.
            return datetime.datetime.strptime(texto, formato).date()
        # Captura erro quando o formato atual não combina.
        except ValueError:
            # Ignora o erro e tenta o próximo formato.
            pass

    # Gera erro se nenhum formato funcionou.
    raise ValueError("Data inválida.")


# Define a função que monta o dicionário de uma transação financeira.
def montar_financeiro(registro):
    # Retorna os dados financeiros formatados.
    return {
        # Define o ID principal.
        "id": registro[0],
        # Define o ID financeiro.
        "id_financeiro": registro[0],
        # Define a descrição da transação.
        "descricao": registro[1],
        # Define o tipo em texto.
        "tipo": texto_tipo(registro[2]),
        # Define o tipo em código.
        "tipo_codigo": registro[2],
        # Define a data em texto ou None.
        "data": str(registro[3]) if registro[3] else None,
        # Define a data financeira em texto ou None.
        "data_financeiro": str(registro[3]) if registro[3] else None,
        # Define o valor como número decimal.
        "valor": float(registro[4] or 0)
    }


# Define a função que monta filtros financeiros pela URL.
def filtros_financeiro():
    # Lê o tipo enviado nos parâmetros da URL.
    tipo = normalizar_tipo(request.args.get("tipo"))
    # Lê o período enviado nos parâmetros da URL.
    periodo = request.args.get("periodo")
    # Lê a data inicial enviada nos parâmetros da URL.
    data_inicio = request.args.get("data_inicio")
    # Lê a data final enviada nos parâmetros da URL.
    data_fim = request.args.get("data_fim")

    # Cria a lista de condições do WHERE.
    where = []
    # Cria a lista de parâmetros da consulta SQL.
    params = []

    # Verifica se o tipo foi reconhecido.
    if tipo is not None:
        # Adiciona o filtro por tipo.
        where.append("TIPO = ?")
        # Adiciona o valor do tipo nos parâmetros.
        params.append(tipo)

    # Verifica se foi informado um período em dias.
    if periodo:
        # Tenta converter o período para número inteiro.
        try:
            # Converte o período para dias.
            dias = int(periodo)
            # Calcula a data inicial com base na data atual menos os dias.
            data_inicio = datetime.date.today() - datetime.timedelta(days=dias)
        # Captura erro quando o período não é número.
        except ValueError:
            # Ignora o período inválido.
            pass

    # Verifica se existe data inicial.
    if data_inicio:
        # Adiciona o filtro de data mínima.
        where.append("DATA_FINANCEIRO >= ?")
        # Normaliza a data inicial e adiciona nos parâmetros.
        params.append(normalizar_data(data_inicio))

    # Verifica se existe data final.
    if data_fim:
        # Adiciona o filtro de data máxima.
        where.append("DATA_FINANCEIRO <= ?")
        # Normaliza a data final e adiciona nos parâmetros.
        params.append(normalizar_data(data_fim))

    # Inicia o trecho SQL do WHERE vazio.
    sql_where = ""
    # Verifica se existe pelo menos uma condição.
    if where:
        # Monta o WHERE juntando as condições com AND.
        sql_where = " WHERE " + " AND ".join(where)

    # Retorna o trecho WHERE e os parâmetros da consulta.
    return sql_where, params


# Define a função que adiciona dados do veículo na descrição.
def descricao_com_veiculo(cur, descricao, id_veiculo):
    # Verifica se nenhum veículo foi informado.
    if not id_veiculo:
        # Retorna a descrição original.
        return descricao

    # Busca marca, modelo e placa do veículo.
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
    # Guarda o veículo encontrado.
    veiculo = cur.fetchone()

    # Verifica se o veículo não foi encontrado.
    if not veiculo:
        # Retorna a descrição original.
        return descricao

    # Junta marca e modelo do veículo em um único texto.
    nome_veiculo = " ".join([str(valor).strip() for valor in veiculo[:2] if valor])
    # Verifica se a placa existe.
    if veiculo[2]:
        # Adiciona a placa ao nome do veículo.
        nome_veiculo = f"{nome_veiculo} - {str(veiculo[2]).strip()}" if nome_veiculo else str(veiculo[2]).strip()

    # Verifica se o nome do veículo está vazio ou já aparece na descrição.
    if not nome_veiculo or nome_veiculo.lower() in descricao.lower():
        # Retorna a descrição sem repetir o veículo.
        return descricao

    # Retorna a descrição com os dados do veículo no final.
    return f"{descricao} | Veículo: {nome_veiculo}"


# Define a função que busca o nome do veículo pelo ID.
def nome_veiculo_por_id(cur, id_veiculo):
    # Verifica se nenhum ID de veículo foi informado.
    if not id_veiculo:
        # Retorna texto vazio.
        return ""

    # Busca marca, modelo e placa do veículo.
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
    # Guarda o veículo encontrado.
    veiculo = cur.fetchone()

    # Verifica se o veículo não foi encontrado.
    if not veiculo:
        # Retorna texto vazio.
        return ""

    # Junta marca e modelo do veículo em um único texto.
    nome = " ".join([str(valor).strip() for valor in veiculo[:2] if valor])
    # Verifica se a placa existe.
    if veiculo[2]:
        # Adiciona a placa ao nome do veículo.
        nome = f"{nome} - {str(veiculo[2]).strip()}" if nome else str(veiculo[2]).strip()

    # Retorna o nome completo do veículo.
    return nome


# Define a função que tenta descobrir o veículo ligado a uma transação.
def veiculo_da_transacao(cur, descricao):
    # Converte a descrição para texto e trata None como vazio.
    texto = str(descricao or "")

    # Cria marcadores para o texto correto e versões antigas gravadas com acentuação corrompida.
    marcadores_veiculo = ["| Veículo:"]
    # Adiciona uma versão antiga do marcador, útil para registros já salvos no banco.
    marcadores_veiculo.append(marcadores_veiculo[0].encode("utf-8").decode("latin-1"))
    # Adiciona outra versão antiga gerada por dupla conversão de acentuação.
    marcadores_veiculo.append(marcadores_veiculo[1].encode("utf-8").decode("latin-1"))

    # Percorre todos os marcadores conhecidos de veículo.
    for marcador in marcadores_veiculo:
        # Verifica se a descrição contém o marcador atual.
        if marcador in texto:
            # Retorna o texto que vem depois do marcador.
            return texto.split(marcador, 1)[1].strip()

    # Procura o código da venda dentro da descrição.
    resultado = re.search(r"c[oó]digo da venda:\s*(\d+)", texto, re.IGNORECASE)
    # Verifica se nenhum código de venda foi encontrado.
    if not resultado:
        # Retorna texto vazio.
        return ""

    # Busca o veículo ligado à venda encontrada.
    cur.execute(
        """
        SELECT ID_VEICULO
        FROM VENDA
        WHERE ID_VENDA = ?
        """,
        (int(resultado.group(1)),)
    )
    # Guarda a venda encontrada.
    venda = cur.fetchone()

    # Verifica se a venda não foi encontrada.
    if not venda:
        # Retorna texto vazio.
        return ""

    # Retorna o nome do veículo ligado à venda.
    return nome_veiculo_por_id(cur, venda[0])


# Define a função que monta uma transação financeira com dados do veículo.
def montar_financeiro_com_veiculo(cur, registro):
    # Monta os dados financeiros básicos.
    transacao = montar_financeiro(registro)
    # Adiciona o veículo encontrado a partir da descrição.
    transacao["veiculo"] = veiculo_da_transacao(cur, transacao.get("descricao"))
    # Retorna a transação completa.
    return transacao
