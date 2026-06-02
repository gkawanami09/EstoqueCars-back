from main import app, con
from flask import jsonify, request, render_template
import datetime
import os
from function import gerar_pix, enviando_email
import threading

JUROS_PADRAO = 4

@app.route('/gerar_pix_venda', methods=['POST'])
def gerar_pix_venda():
    cur = con.cursor()
    try:
        dados = request.get_json(silent=True) or {}
        valor = dados.get('valor')
        chave_pix = dados.get('chave_pix') or dados.get('chave_pix_empresa') or dados.get('pix_chave')
        nome_recebedor_pix = dados.get('nome_recebedor_pix')
        cidade_recebedor_pix = dados.get('cidade_recebedor_pix')
        txid_pix = dados.get('txid') or 'VENDA'

        if valor is None or str(valor).strip() == '':
            return jsonify({'erro': 'Valor obrigatorio para gerar Pix.'}), 400

        try:
            valor_pix = float(valor)
        except Exception:
            return jsonify({'erro': 'Valor invalido para gerar Pix.'}), 400

        if valor_pix <= 0:
            return jsonify({'erro': 'Valor do Pix deve ser maior que zero.'}), 400

        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        config_pix = cur.fetchone()

        if not chave_pix and config_pix:
            chave_pix = config_pix[0]
        if not nome_recebedor_pix and config_pix:
            nome_recebedor_pix = config_pix[1]
        if not nome_recebedor_pix:
            nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')
        if not cidade_recebedor_pix:
            cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')

        if not chave_pix:
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400

        pix_gerado = gerar_pix(
            chave=chave_pix,
            nome=nome_recebedor_pix,
            cidade=cidade_recebedor_pix,
            valor=valor_pix,
            pasta='pix',
            txid=txid_pix
        )
        caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
        if caminho_pix and caminho_pix[0] == '/':
            caminho_pix = caminho_pix[1:]

        return jsonify({
            'pix_qrcode': f"/uploads/{caminho_pix}",
            'pix_copia_cola': pix_gerado.get('payload')
        }), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Pix: {e}'}), 500
    finally:
        cur.close()

@app.route('/cadastrar_venda', methods=['POST'])
def cadastrar_venda():
    cur = con.cursor()
    try:
        dados = {}
        if request.form:
            dados = request.form.to_dict()
        else:
            dados_json = request.get_json(silent=True)
            if dados_json:
                dados = dados_json
        id_usuario = dados.get('id_usuario')
        id_veiculo = dados.get('id_veiculo')
        forma_pagamento = dados.get('forma_pagamento')
        data_venda = dados.get('data_venda')
        valor_venda = dados.get('valor_venda')
        valor_recebido = dados.get('valor_recebido')
        status_pagamento = dados.get('status_pagamento')
        comentarios = dados.get('comentarios')
        desconto = dados.get('desconto', 0)
        comprovante = request.files.get('comprovante')
        if id_usuario is None or str(id_usuario).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        if id_veiculo is None or str(id_veiculo).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        if forma_pagamento is None or str(forma_pagamento).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        if data_venda is None or str(data_venda).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        if valor_venda is None or str(valor_venda).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        if valor_recebido is None or str(valor_recebido).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        if status_pagamento is None or str(status_pagamento).strip() == '':
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400
        forma_pagamento = int(forma_pagamento)
        valor_venda = float(valor_venda)
        valor_recebido = float(valor_recebido)
        desconto = float(desconto or 0)
        if desconto > 10:
            return jsonify({'erro': 'Seu desconto esta muito alto, ele pode ser ate 10%'}), 400
        if desconto < 0:
            return jsonify({'erro': 'O desconto deve ser maior ou igual a 0'}), 400
        data_venda = datetime.datetime.strptime(data_venda, '%d/%m/%Y %H:%M')
        cur.execute("""
            SELECT ID_VEICULO, STATUS_ESTOQUE, MODELO
            FROM VEICULO
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))
        veiculo = cur.fetchone()
        if not veiculo:
            return jsonify({'erro': 'Veiculo nao encontrado'}), 404
        nome_veiculo_email = 'Veiculo'
        if veiculo[2]:
            nome_veiculo_email = veiculo[2]
        status_estoque = int(veiculo[1] or 0)
        if status_estoque == 2:
            return jsonify({'erro': 'Este veiculo ja foi vendido.'}), 400
        if status_estoque not in [1, 3]:
            return jsonify({'erro': 'Este veiculo nao esta disponivel para venda.'}), 400
        cur.execute("""
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
        """, (id_usuario,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({'erro': 'Usuario nao encontrado'}), 404
        chave_pix = None
        nome_recebedor_pix = None
        cidade_recebedor_pix = None
        if forma_pagamento == 0:
            chave_pix = dados.get('chave_pix')
            if not chave_pix:
                chave_pix = dados.get('chave_pix_empresa')
            if not chave_pix:
                chave_pix = dados.get('pix_chave')
            cur.execute("""
                SELECT CHAVE_PIX, NOME_EMPRESA
                FROM CONFIGURACAO
                WHERE ID_EMPRESA = 1
            """)
            config_pix = cur.fetchone()
            if not chave_pix and config_pix:
                chave_pix = config_pix[0]
            nome_recebedor_pix = dados.get('nome_recebedor_pix')
            if not nome_recebedor_pix and config_pix:
                nome_recebedor_pix = config_pix[1]
            if not nome_recebedor_pix:
                nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')

            cidade_recebedor_pix = dados.get('cidade_recebedor_pix')
            if not cidade_recebedor_pix:
                cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')
            if not chave_pix:
                return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
            
            
        valor_parcela = None
        quantidade_parcelas = None
        valor_total_parcelado = None
        
        
        if forma_pagamento == 1:
            valor_parcelado = dados.get('valor_parcelado')
            quantidade_parcelas_dados = dados.get('quantidade_parcelas')

            if valor_parcelado is None or str(valor_parcelado).strip() == '':
                return jsonify({'erro': 'valor_parcelado e quantidade_parcelas sao obrigatorios para pagamento parcelado'}), 400
            
            if quantidade_parcelas_dados is None or str(quantidade_parcelas_dados).strip() == '':
                return jsonify({'erro': 'valor_parcelado e quantidade_parcelas sao obrigatorios para pagamento parcelado'}), 400

            valor_parcela = float(valor_parcelado)
            quantidade_parcelas = int(quantidade_parcelas_dados)
            valor_total_parcelado = valor_parcela * quantidade_parcelas
            
            
        if comprovante:
            nome_imagem = f'comprovante_{id_veiculo}.png'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            comprovante.save(caminho_foto)
            
           
        email_reserva = None
        cur.execute("""
        SELECT ID_USUARIO
        FROM RESERVA_VEICULO
        WHERE ID_VEICULO = ?
                    """,
        (id_veiculo,)
        )
        
        reservaU = cur.fetchone()
        
        if reservaU:
        
            cur.execute("""
            SELECT EMAIL
            FROM USUARIO
            WHERE ID_USUARIO = ?
                        """,
            (reservaU[0],)
            )

            email_usuario = cur.fetchone()
            if email_usuario:
                email_reserva = email_usuario[0]
        
            
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
        id_venda = cur.fetchone()[0]
        cur.execute("""
            UPDATE VEICULO
            SET STATUS_ESTOQUE = 2
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))
        cur.execute("""
            DELETE
            FROM RESERVA_VEICULO
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))
        pix_qrcode = None
        pix_copia_cola = None
        if forma_pagamento == 0:
            txid_pix = f'VENDA{id_venda}'
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_recebido,
                pasta='pix',
                txid=txid_pix
            )
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            if caminho_pix and caminho_pix[0] == '/':
                caminho_pix = caminho_pix[1:]
            pix_qrcode = f"/uploads/{caminho_pix}"
            pix_copia_cola = pix_gerado.get('payload')
        if forma_pagamento == 1:
            cur.execute("""
                EXECUTE PROCEDURE pr_insere_parcelas(?, ?, ?, ?)
            """, (
                valor_parcela,
                quantidade_parcelas,
                valor_total_parcelado,
                id_venda
            ))

        if int(status_pagamento) == 0:
            descricao_financeiro = f'Venda de veiculo - codigo da venda: {id_venda}'
            cur.execute(
                """
                SELECT ID_FINANCEIRO
                FROM FINANCEIRO
                WHERE DESCRICAO = ?
                """,
                (descricao_financeiro,)
            )

            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO FINANCEIRO(
                        DESCRICAO,
                        TIPO,
                        DATA_FINANCEIRO,
                        VALOR
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (descricao_financeiro, 0, data_venda.date(), valor_recebido)
                )
        con.commit()

        if email_reserva:
            assunto = "Cancelamento de reserva - Estoque Cars"
            template_html = render_template('email_reserva.html', veiculo=nome_veiculo_email)
            thread = threading.Thread(target=enviando_email, args=(email_reserva, assunto, template_html))
            thread.start()

        resposta = {
            'mensagem': 'Venda cadastrada com sucesso',
            'id_venda': id_venda
        }
        if pix_qrcode:
            resposta['pix_qrcode'] = pix_qrcode
        if pix_copia_cola:
            resposta['pix_copia_cola'] = pix_copia_cola
        return jsonify(resposta), 201
    except Exception as e:
        return jsonify({'erro': f'Erro ao cadastrar venda: {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_pendencias_venda', methods=['GET'])
def listar_pendencias_venda():
    cur = con.cursor()
    try:
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
        pendencias = []
        for registro in cur.fetchall():
            nome_veiculo = ''
            if registro[2]:
                nome_veiculo = str(registro[2]).strip()
            if registro[1]:
                if nome_veiculo:
                    nome_veiculo = f'{nome_veiculo} {str(registro[1]).strip()}'
                else:
                    nome_veiculo = str(registro[1]).strip()
            if not nome_veiculo:
                if registro[1]:
                    nome_veiculo = registro[1]
                else:
                    nome_veiculo = 'Veiculo'

            data_reserva = str(registro[7])

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
        return jsonify({'pendencias_venda': pendencias}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar pendencias de venda: {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_vendas_usuario', methods=['GET'])
def listar_vendas_usuario():
    cur = con.cursor()
    try:
        id_usuario = request.args.get('id_usuario')
        if not id_usuario:
            return jsonify({'erro': 'id_usuario e obrigatorio'}), 400
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
        vendas = []
        for registro in cur.fetchall():
            nome_veiculo = ''
            if registro[9]:
                nome_veiculo = str(registro[9]).strip()
            if registro[8]:
                if nome_veiculo:
                    nome_veiculo = f'{nome_veiculo} {str(registro[8]).strip()}'
                else:
                    nome_veiculo = str(registro[8]).strip()
            if not nome_veiculo:
                if registro[8]:
                    nome_veiculo = registro[8]
                else:
                    nome_veiculo = 'Veiculo'

            data_venda_formatada = str(registro[4])

            vendas.append({
                'id_venda': registro[0],
                'id_usuario': registro[1],
                'id_veiculo': registro[2],
                'forma_pagamento': registro[3],
                'data_venda': data_venda_formatada,
                'valor_venda': float(registro[5] or 0),
                'valor_recebido': float(registro[6] or 0),
                'status_pagamento': registro[7],
                'modelo': registro[8],
                'marca': registro[9],
                'veiculo': nome_veiculo,
                'quantidade_parcelas': registro[10]
            })
        return jsonify({'vendas': vendas}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar vendas do usuario {e}'}), 500
    finally:
        cur.close()

@app.route('/pix_venda/<int:id_venda>', methods=['GET'])
def pix_venda(id_venda):
    cur = con.cursor()
    try:
        chave_pix = request.args.get('chave_pix')
        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        config_pix = cur.fetchone()
        if not chave_pix and config_pix:
            chave_pix = config_pix[0]

        nome_recebedor_pix = request.args.get('nome_recebedor_pix')
        if not nome_recebedor_pix and config_pix:
            nome_recebedor_pix = config_pix[1]
        if not nome_recebedor_pix:
            nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')

        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix')
        if not cidade_recebedor_pix:
            cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')

        if not chave_pix:
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
        cur.execute("""
            SELECT ID_VENDA,
                   FORMA_PAGAMENTO,
                   VALOR_RECEBIDO
            FROM VENDA
            WHERE ID_VENDA = ?
        """, (id_venda,))
        venda = cur.fetchone()
        if not venda:
            return jsonify({'erro': 'Venda nao encontrada.'}), 404
        if int(venda[1] or 0) != 0:
            return jsonify({'erro': 'Esta venda nao foi paga por Pix a vista.'}), 400
        valor_recebido = float(venda[2] or 0)
        txid_pix = f'VENDA{id_venda}'
        pix_gerado = gerar_pix(
            chave=chave_pix,
            nome=nome_recebedor_pix,
            cidade=cidade_recebedor_pix,
            valor=valor_recebido,
            pasta='pix',
            txid=txid_pix
        )
        caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
        if caminho_pix and caminho_pix[0] == '/':
            caminho_pix = caminho_pix[1:]
        return jsonify({
            'id_venda': id_venda,
            'pix_qrcode': f"/uploads/{caminho_pix}",
            'pix_copia_cola': pix_gerado.get('payload')
        }), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Pix da venda: {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_pix_parcelas/<int:id_venda>', methods=['GET'])
def listar_pix_parcelas(id_venda):
    cur = con.cursor()
    try:
        chave_pix = request.args.get('chave_pix')
        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        config_pix = cur.fetchone()
        if not chave_pix and config_pix:
            chave_pix = config_pix[0]

        nome_recebedor_pix = request.args.get('nome_recebedor_pix')
        if not nome_recebedor_pix and config_pix:
            nome_recebedor_pix = config_pix[1]
        if not nome_recebedor_pix:
            nome_recebedor_pix = app.config.get('PIX_NOME', 'ESTOQUE CARS')

        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix')
        if not cidade_recebedor_pix:
            cidade_recebedor_pix = app.config.get('PIX_CIDADE', 'SAO PAULO')

        if not chave_pix:
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
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
        linhas = cur.fetchall()
        if not linhas:
            return jsonify({'erro': 'Nenhuma parcela encontrada para esta venda.'}), 404
        parcelas = []
        for linha in linhas:
            id_item_parcelamento = linha[2]
            numero_parcela = linha[3]
            valor_parcela = float(linha[4] or 0)
            data_vencimento = linha[5]
            situacao_parcela = linha[6]
            txid_pix = f'PARC{id_item_parcelamento}'
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_parcela,
                pasta='parcelas',
                txid=txid_pix
            )
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            data_vencimento_formatada = str(data_vencimento)
            data_vencimento_texto = data_vencimento_formatada.split(' ')[0]
            if '-' in data_vencimento_texto:
                partes_data = data_vencimento_texto.split('-')
                if len(partes_data) == 3:
                    ano = partes_data[0]
                    mes = partes_data[1]
                    dia = partes_data[2]
                    data_vencimento_formatada = f'{dia}/{mes}/{ano}'
            if caminho_pix and caminho_pix[0] == '/':
                caminho_pix = caminho_pix[1:]
            parcelas.append({
                'id_item_parcelamento': id_item_parcelamento,
                'numero_parcela': numero_parcela,
                'valor_parcela': valor_parcela,
                'data_vencimento': data_vencimento_formatada,
                'situacao_parcela': situacao_parcela,
                'pix_qrcode': f"/uploads/{caminho_pix}",
                'pix_copia_cola': pix_gerado.get('payload')
            })
        return jsonify({'parcelas': parcelas}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Pix das parcelas: {e}'}), 500
    finally:
        cur.close()

@app.route('/pagar_parcela_pix/<int:id_item_parcelamento>', methods=['POST'])
def pagar_parcela_pix(id_item_parcelamento):
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT I.ID_PARCELAMENTO,
                   I.SITUACAO_PARCELA,
                   P.ID_VENDA
            FROM ITEM_PARCELAMENTO I
            INNER JOIN PARCELAMENTO P
                ON P.ID_PARCELAMENTO = I.ID_PARCELAMENTO
            WHERE I.ID_ITEM_PARCELAMENTO = ?
        """, (id_item_parcelamento,))
        parcela = cur.fetchone()
        if not parcela:
            return jsonify({'erro': 'Parcela nao encontrada.'}), 404
        id_parcelamento = parcela[0]
        situacao_parcela = parcela[1]
        id_venda = parcela[2]
        if int(situacao_parcela or 0) != 1:
            cur.execute("""
                UPDATE ITEM_PARCELAMENTO
                SET SITUACAO_PARCELA = 1
                WHERE ID_ITEM_PARCELAMENTO = ?
            """, (id_item_parcelamento,))
        cur.execute("""
            SELECT COUNT(*)
            FROM ITEM_PARCELAMENTO
            WHERE ID_PARCELAMENTO = ?
              AND COALESCE(SITUACAO_PARCELA, 0) <> 1
        """, (id_parcelamento,))
        parcelas_pendentes = cur.fetchone()[0]
        compra_quitada = parcelas_pendentes == 0
        if compra_quitada:
            cur.execute("""
                UPDATE PARCELAMENTO
                SET SITUACAO_PARCELAMENTO = 1
                WHERE ID_PARCELAMENTO = ?
            """, (id_parcelamento,))
            cur.execute("""
                UPDATE VENDA
                SET STATUS_PAGAMENTO = 0
                WHERE ID_VENDA = ?
            """, (id_venda,))
        con.commit()
        return jsonify({
            'mensagem': 'Parcela marcada como paga.',
            'id_venda': id_venda,
            'id_item_parcelamento': id_item_parcelamento,
            'situacao_parcela': 1,
            'parcela_paga': True,
            'compra_quitada': compra_quitada,
            'parcelas_pendentes': parcelas_pendentes
        }), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao pagar parcela: {e}'}), 500
    finally:
        cur.close()

@app.route('/configuracoes', methods=['GET'])
def obter_configuracoes():
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT NOME_EMPRESA, CNPJ, TELEFONE_EMPRESA, EMAIL_CONTATO, 
                   TAXA_JURO, COR_PRIMARIA, COR_SECUNDARIA, FONTE_VISUAL,
                   CHAVE_PIX
            FROM CONFIGURACAO WHERE ID_EMPRESA = 1
        """)
        config = cur.fetchone()
        if not config:
            return jsonify({'erro': ''}), 404
        taxa_juro = float(config[4] or 0)
        if taxa_juro <= 0:
            taxa_juro = JUROS_PADRAO
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
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'erro': f'Erro na configuracoes {e}'}), 500
    finally:
        cur.close()

@app.route('/configuracoes', methods=['PUT'])
def atualizar_configuracoes():
    cur = con.cursor()
    try:
        dados = request.form
        nome_empresa = dados.get('nome_empresa')
        cnpj = dados.get('cnpj')
        telefone = dados.get('telefone_empresa')
        email = dados.get('email_contato')

        chave_pix = dados.get('chave_pix')
        if not chave_pix:
            chave_pix = dados.get('chave_pix_empresa')
        if not chave_pix:
            chave_pix = dados.get('pix_chave')
        if not chave_pix:
            chave_pix = ''

        taxa_juro_dados = dados.get('taxa_juro')
        if not taxa_juro_dados:
            taxa_juro_dados = dados.get('taxa_juros')
        if not taxa_juro_dados:
            taxa_juro_dados = JUROS_PADRAO

        taxa_juro = float(taxa_juro_dados)
        if taxa_juro < 0:
            return jsonify({'erro': 'A taxa de juros nao pode ser negativa'}), 400
        if taxa_juro == 0:
            taxa_juro = JUROS_PADRAO
        cor_primaria = dados.get('cor_primaria')
        cor_secundaria = dados.get('cor_secundaria')
        fonte_visual = dados.get('fonte_visual')
        logo = request.files.get('logo')
        if logo:
            caminho_logo = os.path.join(app.config['UPLOAD_FOLDER'], 'logo_empresa.png')
            logo.save(caminho_logo)
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
        con.commit()
        return jsonify({'mensagem': 'Configuracoes atualizadas com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500
    finally:
        cur.close()
