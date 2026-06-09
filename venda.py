# Importa recursos do módulo main.
from main import app, con
# Importa recursos do módulo flask.
from flask import jsonify, request, render_template
# Importa módulos usados por este arquivo.
import datetime
# Importa módulos usados por este arquivo.
import os
# Importa recursos do módulo function.
from function import gerar_pix, enviando_email
# Importa módulos usados por este arquivo.
import threading

# Define JUROS_PADRAO para uso nas próximas etapas.
JUROS_PADRAO = 4


# Antes não tínhamos a rota RegistrarRecietaVenda, ent colocamos,
# pq nela quando o usuário for pagar vai diretamente para a tabela
# do financeiro, e vai ficar registrado no banco e quando eu for salvar
# vai ter uma função no front que vai pegar esse id do pagamento do usuário
# e vai colocar na tabela.
def registrar_receita_venda(cur, id_venda, descricao, valor, data_financeiro):
    # Verifica se existe um valor válido e maior que zero antes de criar a receita.
    if valor is None or float(valor or 0) <= 0:
        # Sem valor recebido, nenhuma entrada deve ser registrada no financeiro.
        return None

    # Consulta o financeiro para evitar que a mesma receita seja cadastrada duas vezes.
    cur.execute(
        """
        SELECT ID_FINANCEIRO
        FROM FINANCEIRO
        WHERE DESCRICAO = ?
        """,
        # Usa a descrição como identificação da venda ou parcela já registrada.
        (descricao,)
    )
    # Guarda o primeiro registro financeiro encontrado pela consulta.
    financeiro_existente = cur.fetchone()

    # Verifica se a receita já existe no banco.
    if financeiro_existente:
        # Retorna o ID existente em vez de inserir uma receita duplicada.
        return financeiro_existente[0]

    # Insere uma nova entrada na tabela FINANCEIRO.
    cur.execute(
        """
        INSERT INTO FINANCEIRO(
            DESCRICAO,
            TIPO,
            DATA_FINANCEIRO,
            VALOR
        )
        VALUES (?, ?, ?, ?)
        RETURNING ID_FINANCEIRO
        """,
        # Envia descrição, tipo 0/receita, data do pagamento e valor recebido.
        (descricao, 0, data_financeiro, float(valor or 0))
    )
    # Retorna o ID da receita criada para informar quem confirmou o pagamento.
    return cur.fetchone()[0]

@app.route('/gerar_pix_venda', methods=['POST'])
# Declara a função gerar_pix_venda usada neste fluxo.
def gerar_pix_venda():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json(silent=True) or {}
        # Define valor para uso nas próximas etapas.
        valor = dados.get('valor')
        # Define chave_pix para uso nas próximas etapas.
        chave_pix = dados.get('chave_pix') or dados.get('chave_pix_empresa') or dados.get('pix_chave')
        # Define nome_recebedor_pix para uso nas próximas etapas.
        nome_recebedor_pix = dados.get('nome_recebedor_pix')
        # Define cidade_recebedor_pix para uso nas próximas etapas.
        cidade_recebedor_pix = dados.get('cidade_recebedor_pix')
        # Define txid_pix para uso nas próximas etapas.
        txid_pix = dados.get('txid') or 'VENDA'

        # Verifica esta condição antes de continuar o fluxo.
        if valor is None or str(valor).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Valor obrigatorio para gerar Pix.'}), 400

        # Inicia uma operação protegida para permitir o tratamento de erros.
        try:
            # Define valor_pix para uso nas próximas etapas.
            valor_pix = float(valor)
        except Exception:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Valor invalido para gerar Pix.'}), 400

        # Verifica esta condição antes de continuar o fluxo.
        if valor_pix <= 0:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Valor do Pix deve ser maior que zero.'}), 400

        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        # Define config_pix para uso nas próximas etapas.
        config_pix = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix and config_pix:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = config_pix[0]
        # Verifica esta condição antes de continuar o fluxo.
        if not nome_recebedor_pix and config_pix:
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = config_pix[1]
        # Verifica esta condição antes de continuar o fluxo.
        if not nome_recebedor_pix:
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')
        # Verifica esta condição antes de continuar o fluxo.
        if not cidade_recebedor_pix:
            # Define cidade_recebedor_pix para uso nas próximas etapas.
            cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')

        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400

        # Define pix_gerado para uso nas próximas etapas.
        pix_gerado = gerar_pix(
            chave=chave_pix,
            nome=nome_recebedor_pix,
            cidade=cidade_recebedor_pix,
            valor=valor_pix,
            pasta='pix',
            txid=txid_pix
        )
        # Define caminho_pix para uso nas próximas etapas.
        caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
        # Verifica esta condição antes de continuar o fluxo.
        if caminho_pix and caminho_pix[0] == '/':
            # Define caminho_pix para uso nas próximas etapas.
            caminho_pix = caminho_pix[1:]

        # Retorna o resultado desta operação.
        return jsonify({
            'pix_qrcode': f"/uploads/{caminho_pix}",
            'pix_copia_cola': pix_gerado.get('payload')
        }), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao gerar Pix: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/cadastrar_venda', methods=['POST'])
# Declara a função cadastrar_venda usada neste fluxo.
def cadastrar_venda():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = {}
        # Verifica esta condição antes de continuar o fluxo.
        if request.form:
            # Define dados para uso nas próximas etapas.
            dados = request.form.to_dict()
        else:
            # Define dados_json para uso nas próximas etapas.
            dados_json = request.get_json(silent=True)
            # Verifica esta condição antes de continuar o fluxo.
            if dados_json:
                # Define dados para uso nas próximas etapas.
                dados = dados_json
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = dados.get('id_usuario')
        # Define id_veiculo para uso nas próximas etapas.
        id_veiculo = dados.get('id_veiculo')
        # Define forma_pagamento para uso nas próximas etapas.
        forma_pagamento = dados.get('forma_pagamento')
        # Define data_venda para uso nas próximas etapas.
        data_venda = dados.get('data_venda')
        # Define valor_venda para uso nas próximas etapas.
        valor_venda = dados.get('valor_venda')
        # Define valor_recebido para uso nas próximas etapas.
        valor_recebido = dados.get('valor_recebido')
        # Define status_pagamento para uso nas próximas etapas.
        status_pagamento = dados.get('status_pagamento')
        # Define comentarios para uso nas próximas etapas.
        comentarios = dados.get('comentarios')
        # Define desconto para uso nas próximas etapas.
        desconto = dados.get('desconto', 0)
        # Define comprovante para uso nas próximas etapas.
        comprovante = request.files.get('comprovante')
        # Verifica esta condição antes de continuar o fluxo.
        if id_usuario is None or str(id_usuario).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if id_veiculo is None or str(id_veiculo).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if forma_pagamento is None or str(forma_pagamento).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if data_venda is None or str(data_venda).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if valor_venda is None or str(valor_venda).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if valor_recebido is None or str(valor_recebido).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if status_pagamento is None or str(status_pagamento).strip() == '':
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        # Define forma_pagamento para uso nas próximas etapas.
        forma_pagamento = int(forma_pagamento)
        # Define valor_venda para uso nas próximas etapas.
        valor_venda = float(valor_venda)
        # Define valor_recebido para uso nas próximas etapas.
        valor_recebido = float(valor_recebido)
        # Define desconto para uso nas próximas etapas.
        desconto = float(desconto or 0)
        # Verifica esta condição antes de continuar o fluxo.
        if desconto > 10:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Seu desconto esta muito alto, ele pode ser ate 10%'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if desconto < 0:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O desconto deve ser maior ou igual a 0'}), 400
        # Define data_venda para uso nas próximas etapas.
        data_venda = datetime.datetime.strptime(data_venda, '%d/%m/%Y %H:%M')
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT ID_VEICULO, STATUS_ESTOQUE, MODELO
            FROM VEICULO
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))
        # Define veiculo para uso nas próximas etapas.
        veiculo = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not veiculo:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Veiculo nao encontrado'}), 404
        # Define nome_veiculo_email para uso nas próximas etapas.
        nome_veiculo_email = 'Veiculo'
        # Verifica esta condição antes de continuar o fluxo.
        if veiculo[2]:
            # Define nome_veiculo_email para uso nas próximas etapas.
            nome_veiculo_email = veiculo[2]
        # Define status_estoque para uso nas próximas etapas.
        status_estoque = int(veiculo[1] or 0)
        # Verifica esta condição antes de continuar o fluxo.
        if status_estoque == 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Este veiculo ja foi vendido.'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if status_estoque not in [1, 3]:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Este veiculo nao esta disponivel para venda.'}), 400
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
        """, (id_usuario,))
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuario nao encontrado'}), 404
        # Define chave_pix para uso nas próximas etapas.
        chave_pix = None
        # Define nome_recebedor_pix para uso nas próximas etapas.
        nome_recebedor_pix = None
        # Define cidade_recebedor_pix para uso nas próximas etapas.
        cidade_recebedor_pix = None
        # Verifica esta condição antes de continuar o fluxo.
        if forma_pagamento == 0:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = dados.get('chave_pix')
            # Verifica esta condição antes de continuar o fluxo.
            if not chave_pix:
                # Define chave_pix para uso nas próximas etapas.
                chave_pix = dados.get('chave_pix_empresa')
            # Verifica esta condição antes de continuar o fluxo.
            if not chave_pix:
                # Define chave_pix para uso nas próximas etapas.
                chave_pix = dados.get('pix_chave')
            # Executa este comando no banco de dados.
            cur.execute("""
                SELECT CHAVE_PIX, NOME_EMPRESA
                FROM CONFIGURACAO
                WHERE ID_EMPRESA = 1
            """)
            # Define config_pix para uso nas próximas etapas.
            config_pix = cur.fetchone()
            # Verifica esta condição antes de continuar o fluxo.
            if not chave_pix and config_pix:
                # Define chave_pix para uso nas próximas etapas.
                chave_pix = config_pix[0]
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = dados.get('nome_recebedor_pix')
            # Verifica esta condição antes de continuar o fluxo.
            if not nome_recebedor_pix and config_pix:
                # Define nome_recebedor_pix para uso nas próximas etapas.
                nome_recebedor_pix = config_pix[1]
            # Verifica esta condição antes de continuar o fluxo.
            if not nome_recebedor_pix:
                # Define nome_recebedor_pix para uso nas próximas etapas.
                nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')

            # Define cidade_recebedor_pix para uso nas próximas etapas.
            cidade_recebedor_pix = dados.get('cidade_recebedor_pix')
            # Verifica esta condição antes de continuar o fluxo.
            if not cidade_recebedor_pix:
                # Define cidade_recebedor_pix para uso nas próximas etapas.
                cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')
            # Verifica esta condição antes de continuar o fluxo.
            if not chave_pix:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
            
            
        # Define valor_parcela para uso nas próximas etapas.
        valor_parcela = None
        # Define quantidade_parcelas para uso nas próximas etapas.
        quantidade_parcelas = None
        # Define valor_total_parcelado para uso nas próximas etapas.
        valor_total_parcelado = None
        
        
        # Verifica esta condição antes de continuar o fluxo.
        if forma_pagamento == 1:
            # Define valor_parcelado para uso nas próximas etapas.
            valor_parcelado = dados.get('valor_parcelado')
            # Define quantidade_parcelas_dados para uso nas próximas etapas.
            quantidade_parcelas_dados = dados.get('quantidade_parcelas')

            # Verifica esta condição antes de continuar o fluxo.
            if valor_parcelado is None or str(valor_parcelado).strip() == '':
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'valor_parcelado e quantidade_parcelas sao obrigatorios para pagamento parcelado'}), 400
            
            # Verifica esta condição antes de continuar o fluxo.
            if quantidade_parcelas_dados is None or str(quantidade_parcelas_dados).strip() == '':
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'valor_parcelado e quantidade_parcelas sao obrigatorios para pagamento parcelado'}), 400

            # Define valor_parcela para uso nas próximas etapas.
            valor_parcela = float(valor_parcelado)
            # Define quantidade_parcelas para uso nas próximas etapas.
            quantidade_parcelas = int(quantidade_parcelas_dados)
            # Define valor_total_parcelado para uso nas próximas etapas.
            valor_total_parcelado = valor_parcela * quantidade_parcelas
            
            
        # Verifica esta condição antes de continuar o fluxo.
        if comprovante:
            # Define nome_imagem para uso nas próximas etapas.
            nome_imagem = f'comprovante_{id_veiculo}.png'
            # Define caminho_foto para uso nas próximas etapas.
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            # Executa save nesta etapa do fluxo.
            comprovante.save(caminho_foto)
            
           
        # Define email_reserva para uso nas próximas etapas.
        email_reserva = None
        # Executa este comando no banco de dados.
        cur.execute("""
        SELECT ID_USUARIO
        FROM RESERVA_VEICULO
        WHERE ID_VEICULO = ?
                    """,
        (id_veiculo,)
        )
        
        # Define reservaU para uso nas próximas etapas.
        reservaU = cur.fetchone()
        
        # Verifica esta condição antes de continuar o fluxo.
        if reservaU:
        
            # Executa este comando no banco de dados.
            cur.execute("""
            SELECT EMAIL
            FROM USUARIO
            WHERE ID_USUARIO = ?
                        """,
            (reservaU[0],)
            )

            # Define email_usuario para uso nas próximas etapas.
            email_usuario = cur.fetchone()
            # Verifica esta condição antes de continuar o fluxo.
            if email_usuario:
                # Define email_reserva para uso nas próximas etapas.
                email_reserva = email_usuario[0]
        
            
        # Executa este comando no banco de dados.
        cur.execute("""
            INSERT INTO VENDA(
                ID_USUARIO,
                ID_VEICULO,
                FORMA_PAGAMENTO,
                DATA_VENDA,
                VALOR_VENDA,
                VALOR_RECEBIDO,
                STATUS_PAGAMENTO,
                COMENTARIOS,
                DESCONTOS
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING ID_VENDA
        """, (
            id_usuario,
            id_veiculo,
            forma_pagamento,
            data_venda,
            valor_venda,
            valor_recebido,
            status_pagamento,
            comentarios,
            desconto
        ))
        # Define id_venda para uso nas próximas etapas.
        id_venda = cur.fetchone()[0]
        # Executa este comando no banco de dados.
        cur.execute("""
            UPDATE VEICULO
            SET STATUS_ESTOQUE = 2
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))
        # Executa este comando no banco de dados.
        cur.execute("""
            DELETE
            FROM RESERVA_VEICULO
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))
        # Define pix_qrcode para uso nas próximas etapas.
        pix_qrcode = None
        # Define pix_copia_cola para uso nas próximas etapas.
        pix_copia_cola = None
        # Verifica esta condição antes de continuar o fluxo.
        if forma_pagamento == 0:
            # Define txid_pix para uso nas próximas etapas.
            txid_pix = f'VENDA{id_venda}'
            # Define pix_gerado para uso nas próximas etapas.
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_recebido,
                pasta='pix',
                txid=txid_pix
            )
            # Define caminho_pix para uso nas próximas etapas.
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            # Verifica esta condição antes de continuar o fluxo.
            if caminho_pix and caminho_pix[0] == '/':
                # Define caminho_pix para uso nas próximas etapas.
                caminho_pix = caminho_pix[1:]
            # Define pix_qrcode para uso nas próximas etapas.
            pix_qrcode = f"/uploads/{caminho_pix}"
            # Define pix_copia_cola para uso nas próximas etapas.
            pix_copia_cola = pix_gerado.get('payload')
        # Verifica esta condição antes de continuar o fluxo.
        if forma_pagamento == 1:
            # Executa este comando no banco de dados.
            cur.execute("""
                EXECUTE PROCEDURE pr_insere_parcelas(?, ?, ?, ?)
            """, (
                valor_parcela,
                quantidade_parcelas,
                valor_total_parcelado,
                id_venda
            ))

        # REGISTRAR AUTOMATICAMENTE: se a venda já for cadastrada como paga, registra sua receita automaticamente.
        if int(status_pagamento) == 0:
            # Monta a descrição usada para identificar esta venda no financeiro.
            descricao_financeiro = f'Venda de veiculo - codigo da venda: {id_venda}'
            # Cadastra a receita com o valor recebido e a data da venda.
            registrar_receita_venda(cur, id_venda, descricao_financeiro, valor_recebido, data_venda.date())
        # Confirma no banco a venda e a possível receita criada automaticamente.
        con.commit()

        # Verifica esta condição antes de continuar o fluxo.
        if email_reserva:
            # Define assunto para uso nas próximas etapas.
            assunto = "Cancelamento de reserva - Estoque Cars"
            # Define template_html para uso nas próximas etapas.
            template_html = render_template('email_reserva.html', veiculo=nome_veiculo_email)
            # Define thread para uso nas próximas etapas.
            thread = threading.Thread(target=enviando_email, args=(email_reserva, assunto, template_html))
            # Executa start nesta etapa do fluxo.
            thread.start()

        # Define resposta para uso nas próximas etapas.
        resposta = {
            'mensagem': 'Venda cadastrada com sucesso',
            'id_venda': id_venda
        }
        # Verifica esta condição antes de continuar o fluxo.
        if pix_qrcode:
            # Define valor para uso nas próximas etapas.
            resposta['pix_qrcode'] = pix_qrcode
        # Verifica esta condição antes de continuar o fluxo.
        if pix_copia_cola:
            # Define valor para uso nas próximas etapas.
            resposta['pix_copia_cola'] = pix_copia_cola
        # Retorna o resultado desta operação.
        return jsonify(resposta), 201
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao cadastrar venda: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


# REGISTRO AUTOMATICAMENTE: estas rotas confirmam o pagamento completo de uma venda.
@app.route('/confirmar_pagamento_pix_venda/<int:id_venda>', methods=['POST', 'PUT'])
@app.route('/pagar_venda_pix/<int:id_venda>', methods=['POST', 'PUT'])
@app.route('/confirmar_pagamento_venda/<int:id_venda>', methods=['POST', 'PUT'])
@app.route('/atualizar_status_pagamento_venda/<int:id_venda>', methods=['POST', 'PUT'])
def confirmar_pagamento_venda(id_venda):
    # Abre um cursor para consultar e atualizar a venda e o financeiro.
    cur = con.cursor()
    # Inicia o bloco protegido para permitir rollback caso algo falhe.
    try:
        # Consulta os dados necessários para confirmar a venda e calcular sua receita.
        cur.execute(
            """
            SELECT ID_VENDA,
                   ID_VEICULO,
                   DATA_VENDA,
                   VALOR_RECEBIDO,
                   VALOR_VENDA,
                   STATUS_PAGAMENTO
            FROM VENDA
            WHERE ID_VENDA = ?
            """,
            # Filtra a consulta usando o ID recebido pela rota.
            (id_venda,)
        )
        # Guarda a venda encontrada no banco.
        venda = cur.fetchone()

        # Verifica se o ID informado realmente pertence a uma venda.
        if not venda:
            # Retorna erro 404 quando a venda não existe.
            return jsonify({'erro': 'Venda nao encontrada.'}), 404

        # Usa primeiro o valor recebido e, como alternativa, o valor total da venda.
        valor_receita = float(venda[3] or venda[4] or 0)

        # Atualiza a venda para o código 0, que representa pagamento concluído.
        cur.execute(
            """
            UPDATE VENDA
            SET STATUS_PAGAMENTO = 0
            WHERE ID_VENDA = ?
            """,
            # Informa qual venda deve receber o status pago.
            (id_venda,)
        )

        # Monta a descrição que identifica a origem da receita no financeiro.
        descricao_financeiro = f'Venda de veiculo - codigo da venda: {id_venda}'
        # Registra automaticamente a entrada financeira após confirmar o pagamento.
        id_financeiro = registrar_receita_venda(
            # Reutiliza o cursor da mesma transação do banco.
            cur,
            # Relaciona a receita ao número da venda.
            id_venda,
            # Envia a descrição usada para localizar e evitar duplicações.
            descricao_financeiro,
            # Envia o valor que entrou no caixa.
            valor_receita,
            # Usa a data da venda ou a data atual quando ela não estiver disponível.
            venda[2] or datetime.date.today()
        )

        # Confirma juntas as alterações da venda e da receita financeira.
        con.commit()

        # Retorna ao front-end a confirmação do pagamento e da receita criada.
        return jsonify({
            # Mensagem amigável que informa o resultado da operação.
            'mensagem': 'Pagamento confirmado e receita registrada.',
            # Identifica a venda que acabou de ser confirmada.
            'id_venda': id_venda,
            # Informa o código final de pagamento concluído.
            'status_pagamento': 0,
            # Informa explicitamente que o backend já registrou a receita.
            'receita_registrada': True,
            # Envia o ID do lançamento criado ou encontrado no financeiro.
            'id_financeiro': id_financeiro
        }), 200
    # Captura qualquer erro ocorrido durante a confirmação.
    except Exception as e:
        # Desfaz alterações parciais para não deixar venda e financeiro inconsistentes.
        con.rollback()
        # Retorna o erro para o front-end.
        return jsonify({'erro': f'Erro ao confirmar pagamento da venda: {e}'}), 500
    # Executa sempre, com sucesso ou erro.
    finally:
        # Fecha o cursor usado nesta operação.
        cur.close()


@app.route('/listar_pendencias_venda', methods=['GET'])
# Declara a função listar_pendencias_venda usada neste fluxo.
def listar_pendencias_venda():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT V.ID_VEICULO,
                   V.MODELO,
                   M.MARCA,
                   V.PRECO,
                   V.STATUS_ESTOQUE,
                   RV.ID_USUARIO,
                   U.NOME,
                   RV.DATA_RESERVA
            FROM RESERVA_VEICULO RV
            INNER JOIN VEICULO V
                ON V.ID_VEICULO = RV.ID_VEICULO
            LEFT JOIN MARCA M
                ON M.ID_MARCA = V.ID_MARCA
            LEFT JOIN USUARIO U
                ON U.ID_USUARIO = RV.ID_USUARIO
            WHERE COALESCE(V.STATUS_ESTOQUE, 0) = 3
            ORDER BY RV.DATA_RESERVA DESC
            """
        )
        # Define pendencias para uso nas próximas etapas.
        pendencias = []
        # Percorre os itens necessários para executar esta etapa.
        for registro in cur.fetchall():
            # Define nome_veiculo para uso nas próximas etapas.
            nome_veiculo = ''
            # Verifica esta condição antes de continuar o fluxo.
            if registro[2]:
                # Define nome_veiculo para uso nas próximas etapas.
                nome_veiculo = str(registro[2]).strip()
            # Verifica esta condição antes de continuar o fluxo.
            if registro[1]:
                # Verifica esta condição antes de continuar o fluxo.
                if nome_veiculo:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = f'{nome_veiculo} {str(registro[1]).strip()}'
                else:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = str(registro[1]).strip()
            # Verifica esta condição antes de continuar o fluxo.
            if not nome_veiculo:
                # Verifica esta condição antes de continuar o fluxo.
                if registro[1]:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = registro[1]
                else:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = 'Veiculo'

            # Define data_reserva para uso nas próximas etapas.
            data_reserva = str(registro[7])

            # Executa append nesta etapa do fluxo.
            pendencias.append({
                'id_veiculo': registro[0],
                'modelo': registro[1],
                'marca': registro[2],
                'veiculo': nome_veiculo,
                'preco': float(registro[3] or 0),
                'status_estoque': registro[4],
                'id_usuario_reserva': registro[5],
                'nome_usuario_reserva': registro[6],
                'data_reserva': data_reserva,
                'precisa_concluir_venda': True,
                'status_venda': 'RESERVADO_PENDENTE_CONCLUSAO',
                'mensagem_venda': 'Reservado: precisa concluir a venda.'
            })
        # Retorna o resultado desta operação.
        return jsonify({'pendencias_venda': pendencias}), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao listar pendencias de venda: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()

@app.route('/listar_vendas_usuario', methods=['GET'])
# Declara a função listar_vendas_usuario usada neste fluxo.
def listar_vendas_usuario():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = request.args.get('id_usuario')
        # Verifica esta condição antes de continuar o fluxo.
        if not id_usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'id_usuario e obrigatorio'}), 400
        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT V.ID_VENDA,
                   V.ID_USUARIO,
                   V.ID_VEICULO,
                   V.FORMA_PAGAMENTO,
                   V.DATA_VENDA,
                   V.VALOR_VENDA,
                   V.VALOR_RECEBIDO,
                   V.STATUS_PAGAMENTO,
                   VE.MODELO,
                   M.MARCA,
                   P.QUANTIDADE_PARCELAS
            FROM VENDA V
            LEFT JOIN VEICULO VE
                ON VE.ID_VEICULO = V.ID_VEICULO
            LEFT JOIN MARCA M
                ON M.ID_MARCA = VE.ID_MARCA
            LEFT JOIN PARCELAMENTO P
                ON P.ID_VENDA = V.ID_VENDA
            WHERE V.ID_USUARIO = ?
            ORDER BY V.DATA_VENDA DESC
            """,
            (id_usuario,)
        )
        # Define vendas para uso nas próximas etapas.
        vendas = []
        # Percorre os itens necessários para executar esta etapa.
        for registro in cur.fetchall():
            # Define status_pagamento para uso nas próximas etapas.
            status_pagamento = registro[7]

            # Verifica esta condição antes de continuar o fluxo.
            if int(registro[3] or 0) == 1 and registro[10]:
                # Executa este comando no banco de dados.
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM PARCELAMENTO P
                    INNER JOIN ITEM_PARCELAMENTO I
                        ON I.ID_PARCELAMENTO = P.ID_PARCELAMENTO
                    WHERE P.ID_VENDA = ?
                      AND COALESCE(I.SITUACAO_PARCELA, 0) <> 1
                    """,
                    (registro[0],)
                )
                # Define parcelas_pendentes para uso nas próximas etapas.
                parcelas_pendentes = cur.fetchone()[0]

                # Verifica esta condição antes de continuar o fluxo.
                if parcelas_pendentes == 0:
                    # Define status_pagamento para uso nas próximas etapas.
                    status_pagamento = 0

            # Define nome_veiculo para uso nas próximas etapas.
            nome_veiculo = ''
            # Verifica esta condição antes de continuar o fluxo.
            if registro[9]:
                # Define nome_veiculo para uso nas próximas etapas.
                nome_veiculo = str(registro[9]).strip()
            # Verifica esta condição antes de continuar o fluxo.
            if registro[8]:
                # Verifica esta condição antes de continuar o fluxo.
                if nome_veiculo:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = f'{nome_veiculo} {str(registro[8]).strip()}'
                else:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = str(registro[8]).strip()
            # Verifica esta condição antes de continuar o fluxo.
            if not nome_veiculo:
                # Verifica esta condição antes de continuar o fluxo.
                if registro[8]:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = registro[8]
                else:
                    # Define nome_veiculo para uso nas próximas etapas.
                    nome_veiculo = 'Veiculo'

            # Define data_venda_formatada para uso nas próximas etapas.
            data_venda_formatada = str(registro[4])

            # Executa append nesta etapa do fluxo.
            vendas.append({
                'id_venda': registro[0],
                'id_usuario': registro[1],
                'id_veiculo': registro[2],
                'forma_pagamento': registro[3],
                'data_venda': data_venda_formatada,
                'valor_venda': float(registro[5] or 0),
                'valor_recebido': float(registro[6] or 0),
                'status_pagamento': status_pagamento,
                'modelo': registro[8],
                'marca': registro[9],
                'veiculo': nome_veiculo,
                'quantidade_parcelas': registro[10]
            })
        # Retorna o resultado desta operação.
        return jsonify({'vendas': vendas}), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao listar vendas do usuario {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()

@app.route('/pix_venda/<int:id_venda>', methods=['GET'])
# Declara a função pix_venda usada neste fluxo.
def pix_venda(id_venda):
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define chave_pix para uso nas próximas etapas.
        chave_pix = request.args.get('chave_pix')
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        # Define config_pix para uso nas próximas etapas.
        config_pix = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix and config_pix:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = config_pix[0]

        # Define nome_recebedor_pix para uso nas próximas etapas.
        nome_recebedor_pix = request.args.get('nome_recebedor_pix')
        # Verifica esta condição antes de continuar o fluxo.
        if not nome_recebedor_pix and config_pix:
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = config_pix[1]
        # Verifica esta condição antes de continuar o fluxo.
        if not nome_recebedor_pix:
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')

        # Define cidade_recebedor_pix para uso nas próximas etapas.
        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix')
        # Verifica esta condição antes de continuar o fluxo.
        if not cidade_recebedor_pix:
            # Define cidade_recebedor_pix para uso nas próximas etapas.
            cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')

        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT ID_VENDA,
                   FORMA_PAGAMENTO,
                   VALOR_RECEBIDO
            FROM VENDA
            WHERE ID_VENDA = ?
        """, (id_venda,))
        # Define venda para uso nas próximas etapas.
        venda = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not venda:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Venda nao encontrada.'}), 404
        # Verifica esta condição antes de continuar o fluxo.
        if int(venda[1] or 0) != 0:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Esta venda nao foi paga por Pix a vista.'}), 400
        # Define valor_recebido para uso nas próximas etapas.
        valor_recebido = float(venda[2] or 0)
        # Define txid_pix para uso nas próximas etapas.
        txid_pix = f'VENDA{id_venda}'
        # Define pix_gerado para uso nas próximas etapas.
        pix_gerado = gerar_pix(
            chave=chave_pix,
            nome=nome_recebedor_pix,
            cidade=cidade_recebedor_pix,
            valor=valor_recebido,
            pasta='pix',
            txid=txid_pix
        )
        # Define caminho_pix para uso nas próximas etapas.
        caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
        # Verifica esta condição antes de continuar o fluxo.
        if caminho_pix and caminho_pix[0] == '/':
            # Define caminho_pix para uso nas próximas etapas.
            caminho_pix = caminho_pix[1:]
        # Retorna o resultado desta operação.
        return jsonify({
            'id_venda': id_venda,
            'pix_qrcode': f"/uploads/{caminho_pix}",
            'pix_copia_cola': pix_gerado.get('payload')
        }), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao gerar Pix da venda: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()

@app.route('/listar_pix_parcelas/<int:id_venda>', methods=['GET'])
# Declara a função listar_pix_parcelas usada neste fluxo.
def listar_pix_parcelas(id_venda):
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define chave_pix para uso nas próximas etapas.
        chave_pix = request.args.get('chave_pix')
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        # Define config_pix para uso nas próximas etapas.
        config_pix = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix and config_pix:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = config_pix[0]

        # Define nome_recebedor_pix para uso nas próximas etapas.
        nome_recebedor_pix = request.args.get('nome_recebedor_pix')
        # Verifica esta condição antes de continuar o fluxo.
        if not nome_recebedor_pix and config_pix:
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = config_pix[1]
        # Verifica esta condição antes de continuar o fluxo.
        if not nome_recebedor_pix:
            # Define nome_recebedor_pix para uso nas próximas etapas.
            nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')

        # Define cidade_recebedor_pix para uso nas próximas etapas.
        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix')
        # Verifica esta condição antes de continuar o fluxo.
        if not cidade_recebedor_pix:
            # Define cidade_recebedor_pix para uso nas próximas etapas.
            cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')

        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT P.ID_PARCELAMENTO,
                   P.ID_VENDA,
                   I.ID_ITEM_PARCELAMENTO,
                   I.NUMERO_PARCELA,
                   I.VALOR_PARCELA,
                   I.DATA_VENCIMENTO,
                   I.SITUACAO_PARCELA
            FROM PARCELAMENTO P
            INNER JOIN ITEM_PARCELAMENTO I
                ON I.ID_PARCELAMENTO = P.ID_PARCELAMENTO
            WHERE P.ID_VENDA = ?
            ORDER BY I.NUMERO_PARCELA
        """, (id_venda,))
        # Define linhas para uso nas próximas etapas.
        linhas = cur.fetchall()
        # Verifica esta condição antes de continuar o fluxo.
        if not linhas:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Nenhuma parcela encontrada para esta venda.'}), 404
        # Define parcelas para uso nas próximas etapas.
        parcelas = []
        # Percorre os itens necessários para executar esta etapa.
        for linha in linhas:
            # Define id_item_parcelamento para uso nas próximas etapas.
            id_item_parcelamento = linha[2]
            # Define numero_parcela para uso nas próximas etapas.
            numero_parcela = linha[3]
            # Define valor_parcela para uso nas próximas etapas.
            valor_parcela = float(linha[4] or 0)
            # Define data_vencimento para uso nas próximas etapas.
            data_vencimento = linha[5]
            # Define situacao_parcela para uso nas próximas etapas.
            situacao_parcela = linha[6]
            # Define txid_pix para uso nas próximas etapas.
            txid_pix = f'PARC{id_item_parcelamento}'
            # Define pix_gerado para uso nas próximas etapas.
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_parcela,
                pasta='parcelas',
                txid=txid_pix
            )
            # Define caminho_pix para uso nas próximas etapas.
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            # Define data_vencimento_formatada para uso nas próximas etapas.
            data_vencimento_formatada = str(data_vencimento)
            # Define data_vencimento_texto para uso nas próximas etapas.
            data_vencimento_texto = data_vencimento_formatada.split(' ')[0]
            # Verifica esta condição antes de continuar o fluxo.
            if '-' in data_vencimento_texto:
                # Define partes_data para uso nas próximas etapas.
                partes_data = data_vencimento_texto.split('-')
                # Verifica esta condição antes de continuar o fluxo.
                if len(partes_data) == 3:
                    # Define ano para uso nas próximas etapas.
                    ano = partes_data[0]
                    # Define mes para uso nas próximas etapas.
                    mes = partes_data[1]
                    # Define dia para uso nas próximas etapas.
                    dia = partes_data[2]
                    # Define data_vencimento_formatada para uso nas próximas etapas.
                    data_vencimento_formatada = f'{dia}/{mes}/{ano}'
            # Verifica esta condição antes de continuar o fluxo.
            if caminho_pix and caminho_pix[0] == '/':
                # Define caminho_pix para uso nas próximas etapas.
                caminho_pix = caminho_pix[1:]
            # Executa append nesta etapa do fluxo.
            parcelas.append({
                'id_item_parcelamento': id_item_parcelamento,
                'numero_parcela': numero_parcela,
                'valor_parcela': valor_parcela,
                'data_vencimento': data_vencimento_formatada,
                'situacao_parcela': situacao_parcela,
                'pix_qrcode': f"/uploads/{caminho_pix}",
                'pix_copia_cola': pix_gerado.get('payload')
            })
        # Retorna o resultado desta operação.
        return jsonify({'parcelas': parcelas}), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao gerar Pix das parcelas: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()

# ITEM DA SPRINT: esta rota confirma o pagamento de uma parcela Pix e registra sua receita.
@app.route('/pagar_parcela_pix/<int:id_item_parcelamento>', methods=['POST'])
def pagar_parcela_pix(id_item_parcelamento):
    # Abre um cursor para consultar parcela, venda e financeiro na mesma transação.
    cur = con.cursor()
    # Inicia o bloco protegido para desfazer tudo caso uma etapa falhe.
    try:
        # Consulta a parcela e também recupera a venda e o veículo relacionados.
        cur.execute("""
            SELECT I.ID_PARCELAMENTO,
                   I.SITUACAO_PARCELA,
                   P.ID_VENDA,
                   I.NUMERO_PARCELA,
                   I.VALOR_PARCELA,
                   V.ID_VEICULO
            FROM ITEM_PARCELAMENTO I
            INNER JOIN PARCELAMENTO P
                ON P.ID_PARCELAMENTO = I.ID_PARCELAMENTO
            INNER JOIN VENDA V
                ON V.ID_VENDA = P.ID_VENDA
            WHERE I.ID_ITEM_PARCELAMENTO = ?
        """,
        # Filtra a consulta usando o ID da parcela recebido na URL.
        (id_item_parcelamento,))
        # Guarda os dados encontrados para a parcela.
        parcela = cur.fetchone()
        # Verifica se a parcela informada existe.
        if not parcela:
            # Retorna erro 404 quando a parcela não é encontrada.
            return jsonify({'erro': 'Parcela nao encontrada.'}), 404
        # Guarda o ID do parcelamento ao qual a parcela pertence.
        id_parcelamento = parcela[0]
        # Guarda a situação atual da parcela.
        situacao_parcela = parcela[1]
        # Guarda o ID da venda relacionada.
        id_venda = parcela[2]
        # Guarda o número visual da parcela.
        numero_parcela = parcela[3]
        # Converte o valor da parcela para número.
        valor_parcela = float(parcela[4] or 0)
        # Verifica se a parcela ainda não estava marcada como paga.
        if int(situacao_parcela or 0) != 1:
            # Atualiza somente esta parcela para a situação 1/paga.
            cur.execute("""
                UPDATE ITEM_PARCELAMENTO
                SET SITUACAO_PARCELA = 1
                WHERE ID_ITEM_PARCELAMENTO = ?
            """,
            # Informa qual parcela deve ser atualizada.
            (id_item_parcelamento,))
        # Monta uma descrição exclusiva com venda e número da parcela.
        descricao_financeiro = f'Receita automatica - Venda #{id_venda} - Parcela {numero_parcela or "-"}'
        # Registra automaticamente no financeiro o valor desta parcela paga.
        id_financeiro = registrar_receita_venda(
            # Reutiliza o cursor da operação atual.
            cur,
            # Relaciona a receita à venda correspondente.
            id_venda,
            # Usa a descrição para identificar a parcela e impedir duplicação.
            descricao_financeiro,
            # Registra somente o valor desta parcela.
            valor_parcela,
            # Registra a data em que o pagamento foi confirmado.
            datetime.date.today()
        )
        # Conta quantas parcelas desta compra ainda continuam pendentes.
        cur.execute("""
            SELECT COUNT(*)
            FROM ITEM_PARCELAMENTO
            WHERE ID_PARCELAMENTO = ?
              AND COALESCE(SITUACAO_PARCELA, 0) <> 1
        """,
        # Filtra a contagem pelo parcelamento desta compra.
        (id_parcelamento,))
        # Guarda a quantidade de parcelas ainda não pagas.
        parcelas_pendentes = cur.fetchone()[0]
        # Considera a compra quitada quando não restar nenhuma parcela pendente.
        compra_quitada = parcelas_pendentes == 0
        # Verifica se esta foi a última parcela necessária para quitar a compra.
        if compra_quitada:
            # Marca o parcelamento completo como quitado.
            cur.execute("""
                UPDATE PARCELAMENTO
                SET SITUACAO_PARCELAMENTO = 1
                WHERE ID_PARCELAMENTO = ?
            """,
            # Informa qual parcelamento deve ser atualizado.
            (id_parcelamento,))
            # Marca também a venda completa como paga.
            cur.execute("""
                UPDATE VENDA
                SET STATUS_PAGAMENTO = 0
                WHERE ID_VENDA = ?
            """,
            # Informa qual venda deve receber o status pago.
            (id_venda,))
        # Confirma juntas a parcela paga, a receita e a possível quitação da venda.
        con.commit()
        # Retorna ao front-end o resultado completo da confirmação.
        return jsonify({
            # Informa que a parcela foi atualizada.
            'mensagem': 'Parcela marcada como paga.',
            # Identifica a venda relacionada.
            'id_venda': id_venda,
            # Identifica a parcela confirmada.
            'id_item_parcelamento': id_item_parcelamento,
            # Informa que a situação final da parcela é paga.
            'situacao_parcela': 1,
            # Confirma em formato booleano que a parcela foi paga.
            'parcela_paga': True,
            # Informa se todas as parcelas da compra foram quitadas.
            'compra_quitada': compra_quitada,
            # Informa quantas parcelas continuam pendentes.
            'parcelas_pendentes': parcelas_pendentes,
            # Informa ao front-end que o próprio backend já criou a receita.
            'receita_registrada': True,
            # Envia o ID da entrada criada ou encontrada no financeiro.
            'id_financeiro': id_financeiro
        }), 200
    # Captura qualquer erro durante pagamento, receita ou quitação.
    except Exception as e:
        # Desfaz todas as alterações para manter os dados consistentes.
        con.rollback()
        # Retorna o erro ao front-end.
        return jsonify({'erro': f'Erro ao pagar parcela: {e}'}), 500
    # Executa sempre, independentemente do resultado.
    finally:
        # Fecha o cursor usado pela rota.
        cur.close()

@app.route('/configuracoes', methods=['GET'])
# Declara a função obter_configuracoes usada neste fluxo.
def obter_configuracoes():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Executa este comando no banco de dados.
        cur.execute("""
            SELECT NOME_EMPRESA, CNPJ, TELEFONE_EMPRESA, EMAIL_CONTATO, 
                   TAXA_JURO, COR_PRIMARIA, COR_SECUNDARIA, FONTE_VISUAL,
                   CHAVE_PIX
            FROM CONFIGURACAO WHERE ID_EMPRESA = 1
        """)
        # Define config para uso nas próximas etapas.
        config = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not config:
            # Retorna o resultado desta operação.
            return jsonify({'erro': ''}), 404
        # Define taxa_juro para uso nas próximas etapas.
        taxa_juro = float(config[4] or 0)
        # Verifica esta condição antes de continuar o fluxo.
        if taxa_juro <= 0:
            # Define taxa_juro para uso nas próximas etapas.
            taxa_juro = JUROS_PADRAO
        # Define dados para uso nas próximas etapas.
        dados = {
            'nome_empresa': config[0],
            'cnpj': config[1],
            'telefone_empresa': config[2],
            'email_contato': config[3],
            'taxa_juro': taxa_juro,
            'taxa_juros': taxa_juro,
            'cor_primaria': config[5] or '#FFFFFF',
            'cor_secundaria': config[6] or '#000000',
            'fonte_visual': config[7] or 'Arial',
            'chave_pix': config[8] or '',
            'chave_pix_empresa': config[8] or '',
            'pix_chave': config[8] or '',
            'logo_url': f"http://seu-servidor.com/uploads/logo_empresa.png"
        }
        # Retorna o resultado desta operação.
        return jsonify(dados), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro na configuracoes {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()

@app.route('/configuracoes', methods=['PUT'])
# Declara a função atualizar_configuracoes usada neste fluxo.
def atualizar_configuracoes():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.form
        # Define nome_empresa para uso nas próximas etapas.
        nome_empresa = dados.get('nome_empresa')
        # Define cnpj para uso nas próximas etapas.
        cnpj = dados.get('cnpj')
        # Define telefone para uso nas próximas etapas.
        telefone = dados.get('telefone_empresa')
        # Define email para uso nas próximas etapas.
        email = dados.get('email_contato')

        # Define chave_pix para uso nas próximas etapas.
        chave_pix = dados.get('chave_pix')
        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = dados.get('chave_pix_empresa')
        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = dados.get('pix_chave')
        # Verifica esta condição antes de continuar o fluxo.
        if not chave_pix:
            # Define chave_pix para uso nas próximas etapas.
            chave_pix = ''

        # Define taxa_juro_dados para uso nas próximas etapas.
        taxa_juro_dados = dados.get('taxa_juro')
        # Verifica esta condição antes de continuar o fluxo.
        if not taxa_juro_dados:
            # Define taxa_juro_dados para uso nas próximas etapas.
            taxa_juro_dados = dados.get('taxa_juros')
        # Verifica esta condição antes de continuar o fluxo.
        if not taxa_juro_dados:
            # Define taxa_juro_dados para uso nas próximas etapas.
            taxa_juro_dados = JUROS_PADRAO

        # Define taxa_juro para uso nas próximas etapas.
        taxa_juro = float(taxa_juro_dados)
        # Verifica esta condição antes de continuar o fluxo.
        if taxa_juro < 0:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'A taxa de juros nao pode ser negativa'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if taxa_juro == 0:
            # Define taxa_juro para uso nas próximas etapas.
            taxa_juro = JUROS_PADRAO
        # Define cor_primaria para uso nas próximas etapas.
        cor_primaria = dados.get('cor_primaria')
        # Define cor_secundaria para uso nas próximas etapas.
        cor_secundaria = dados.get('cor_secundaria')
        # Define fonte_visual para uso nas próximas etapas.
        fonte_visual = dados.get('fonte_visual')
        # Define logo para uso nas próximas etapas.
        logo = request.files.get('logo')
        # Verifica esta condição antes de continuar o fluxo.
        if logo:
            # Define caminho_logo para uso nas próximas etapas.
            caminho_logo = os.path.join(app.config['UPLOAD_FOLDER'], 'logo_empresa.png')
            # Executa save nesta etapa do fluxo.
            logo.save(caminho_logo)
        # Executa este comando no banco de dados.
        cur.execute("""
            UPDATE CONFIGURACAO 
            SET NOME_EMPRESA=?, CNPJ=?, TELEFONE_EMPRESA=?, EMAIL_CONTATO=?, 
                TAXA_JURO=?, COR_PRIMARIA=?, COR_SECUNDARIA=?, FONTE_VISUAL=?,
                CHAVE_PIX=?
            WHERE ID_EMPRESA = 1
        """, (
            nome_empresa,
            cnpj,
            telefone,
            email,
            taxa_juro,
            cor_primaria,
            cor_secundaria,
            fonte_visual,
            chave_pix
        ))
        # Confirma no banco todas as alterações realizadas.
        con.commit()
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Configuracoes atualizadas com sucesso!'}), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()
