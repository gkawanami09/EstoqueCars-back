# Importa recursos do módulo main.
from main import app, con  # Importa a aplicacao Flask e a conexao com o banco.
# Importa recursos do módulo flask.
from flask import request, jsonify, send_from_directory, render_template  # Importa recursos para requisicoes, JSON e arquivos.
# Importa recursos do módulo validate_docbr.
from validate_docbr import RENAVAM  # Importa o validador de RENAVAM.
# Importa módulos usados por este arquivo.
import jwt  # Importa a biblioteca usada para tratar erros de token JWT.
# Importa módulos usados por este arquivo.
import os  # Importa recursos para lidar com pastas e arquivos.
# Importa módulos usados por este arquivo.
import datetime
# Importa módulos usados por este arquivo.
import threading
# Importa recursos do módulo function.
from function import enviando_email
# Define senha_secreta para uso nas próximas etapas.
senha_secreta = app.config['SECRET_KEY']


# Declara a função obter_id_usuario_token usada neste fluxo.
def obter_id_usuario_token():
    # Define token para uso nas próximas etapas.
    token = request.cookies.get('access_token')
    # Verifica esta condição antes de continuar o fluxo.
    if not token:
        # Define auth_header para uso nas próximas etapas.
        auth_header = request.headers.get('Authorization', '')
        # Verifica esta condição antes de continuar o fluxo.
        if auth_header.lower().startswith('bearer '):
            # Define token para uso nas próximas etapas.
            token = auth_header.split(' ', 1)[1].strip()

    # Verifica esta condição antes de continuar o fluxo.
    if not token:
        # Retorna o resultado desta operação.
        return None

    # Define dados para uso nas próximas etapas.
    dados = jwt.decode(token, senha_secreta, algorithms=['HS256'])
    # Retorna o resultado desta operação.
    return dados.get('id_user') or dados.get('id_usuario') or dados.get('id')


# Declara a função data_upload_veiculo usada neste fluxo.
def data_upload_veiculo(id_veiculo):
    # Define nome_imagem para uso nas próximas etapas.
    nome_imagem = f'veico_{id_veiculo}.png'
    # Define caminho_foto para uso nas próximas etapas.
    caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)

    # Verifica esta condição antes de continuar o fluxo.
    if not os.path.isfile(caminho_foto):
        # Retorna o resultado desta operação.
        return None

    # Retorna o resultado desta operação.
    return datetime.datetime.fromtimestamp(os.path.getmtime(caminho_foto)).strftime('%Y-%m-%d')


# Verifica se a pasta de upload ainda nao existe.
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    # Cria a pasta onde as imagens dos veiculos serao salvas.
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Cria o objeto usado para validar RENAVAM.
renavam_validacao = RENAVAM()

# Exemplo para gerar RENAVAM durante testes.
# novo_renavam = renavam_validacao.generate()

# Exemplo para imprimir o RENAVAM gerado.
# print(novo_renavam)


@app.route('/cadastrar_carro', methods=['POST'])
def cadastrar_carro():
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Recupera o id da categoria enviado pelo formulario.
        id_categoria = request.form.get('id_categoria')

        # Recupera o id da marca enviado pelo formulario.
        id_marca = request.form.get('id_marca')

        # Recupera o modelo do veiculo.
        modelo = request.form.get('modelo')

        # Recupera o ano de fabricacao.
        ano_fabricacao = request.form.get('ano_fabricacao')

        # Recupera o ano do modelo.
        ano_modelo = request.form.get('ano_modelo')

        # Recupera a quilometragem.
        quilometragem = request.form.get('quilometragem')

        # Recupera a cor.
        cor = request.form.get('cor')

        # Recupera o tipo de cambio.
        cambio = request.form.get('cambio')

        # Recupera o preco.
        preco = request.form.get('preco')

        # Recupera a descricao.
        descricao = request.form.get('descricao')

        # Recupera o estado de conservacao.
        estado_conservacao = request.form.get('estado_conservacao')

        # Recupera o status do documento.
        status_documento = request.form.get('status_documento')

        # Recupera o status do estoque.
        status_estoque = request.form.get('status_estoque')

        # Recupera a placa.
        placa = request.form.get('placa')

        # Recupera o RENAVAM.
        renavam = request.form.get('renavam')

        # Recupera o arquivo de foto do veiculo.
        foto_veiculo = request.files.get('foto_veiculo')

        # Verifica se os campos obrigatorios foram preenchidos.
        if not all([id_categoria, id_marca, modelo, ano_fabricacao, ano_modelo, preco, placa]):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Preencha todos os campos obrigatórios.'}), 400

        # Imprime uma marcacao simples no terminal.
        print('renavam')

        # Valida o RENAVAM informado.
        if not renavam_validacao.validate(renavam):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'RENAVAM inválido'}), 400

        # Verifica se o RENAVAM tem 11 digitos.
        if len(str(renavam)) != 11:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O RENAVAM deve conter 11 dígitos.'}), 400

        # Busca conflito de placa ou RENAVAM.
        cur.execute(  # Consulta se placa ou RENAVAM ja existem.
            """
            SELECT PLACA, -- Seleciona a placa do veiculo encontrado.
                   RENAVAM -- Seleciona o RENAVAM do veiculo encontrado.
            FROM VEICULO -- Define a tabela de veiculos.
            WHERE PLACA = ? -- Filtra pela placa informada.
               OR RENAVAM = ? -- Filtra pelo RENAVAM informado.
            """,
            (placa, renavam)
        )

        # Recupera o possivel conflito encontrado.
        conflito = cur.fetchone()

        # Verifica se existe placa ou RENAVAM ja cadastrado.
        if conflito:
            # Retorna erro quando a placa ja existe.
            if conflito[0] == placa:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Placa já cadastrada'}), 409

            # Retorna erro quando o RENAVAM ja existe.
            if conflito[1] == renavam:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'RENAVAM já cadastrado'}), 409

        # Insere o novo veiculo no banco.
        cur.execute(  # Cadastra o veiculo e retorna o id gerado.
            """
            INSERT INTO VEICULO ( -- Insere um novo registro na tabela de veiculos.
                ID_CATEGORIA, -- Informa a categoria do veiculo.
                ID_MARCA, -- Informa a marca do veiculo.
                MODELO, -- Informa o modelo do veiculo.
                ANO_FABRICACAO, -- Informa o ano de fabricacao.
                ANO_MODELO, -- Informa o ano do modelo.
                QUILOMETRAGEM, -- Informa a quilometragem.
                COR, -- Informa a cor.
                CAMBIO, -- Informa o tipo de cambio.
                PRECO, -- Informa o preco.
                DESCRICAO, -- Informa a descricao.
                ESTADO_CONSERVACAO, -- Informa o estado de conservacao.
                STATUS_DOCUMENTO, -- Informa o status do documento.
                STATUS_ESTOQUE, -- Informa o status do estoque.
                PLACA, -- Informa a placa.
                RENAVAM -- Informa o RENAVAM.
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) -- Define os valores gravados.
            RETURNING ID_VEICULO -- Retorna o id gerado pela insercao.
            """,
            (
                id_categoria, id_marca, modelo, ano_fabricacao, ano_modelo,
                quilometragem, cor, cambio, preco, descricao,
                estado_conservacao, status_documento, status_estoque, placa, renavam
            )
        )

        # Recupera o retorno da insercao.
        resultado_id = cur.fetchone()

        # Guarda o id do veiculo criado.
        id_veiculo = resultado_id[0]

        # Verifica se uma foto foi enviada.
        if foto_veiculo:
            # Define o nome padrao da imagem do veiculo.
            nome_imagem = f'veico_{id_veiculo}.png'

            # Monta o caminho completo da imagem.
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)

            # Salva a imagem enviada no caminho definido.
            foto_veiculo.save(caminho_foto)

        # Confirma o cadastro no banco.
        con.commit()

        # Retorna sucesso do cadastro.
        return jsonify({'mensagem': 'Veículo cadastrado com sucesso!'}), 201

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({"erro": "Token inválido ou adulterado."}), 401

    except Exception as e:
        # Desfaz alteracoes pendentes em caso de erro.
        con.rollback()

        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao cadastrar carro: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/editar_carro/<int:id_veiculo>', methods=['PUT'])
# Declara a função editar_carro usada neste fluxo.
def editar_carro(id_veiculo):
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Busca o veiculo antes de editar.
        cur.execute(  # Consulta se o veiculo informado existe.
            """
            SELECT ID_VEICULO -- Seleciona o id do veiculo.
            FROM VEICULO -- Define a tabela de veiculos.
            WHERE ID_VEICULO = ? -- Filtra pelo id do veiculo informado.
            """,
            (id_veiculo,)
        )

        # Retorna erro se o veiculo nao existir.
        if not cur.fetchone():
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Veículo não encontrado.'}), 404

        # Recupera o id da categoria enviado pelo formulario.
        id_categoria = request.form.get('id_categoria')

        # Recupera o id da marca enviado pelo formulario.
        id_marca = request.form.get('id_marca')

        # Recupera o modelo do veiculo.
        modelo = request.form.get('modelo')

        # Recupera o ano de fabricacao.
        ano_fabricacao = request.form.get('ano_fabricacao')

        # Recupera o ano do modelo.
        ano_modelo = request.form.get('ano_modelo')

        # Recupera a quilometragem.
        quilometragem = request.form.get('quilometragem')

        # Recupera a cor.
        cor = request.form.get('cor')

        # Recupera o tipo de cambio.
        cambio = request.form.get('cambio')

        # Recupera o preco.
        preco = request.form.get('preco')

        # Recupera a descricao.
        descricao = request.form.get('descricao')

        # Recupera o estado de conservacao.
        estado_conservacao = request.form.get('estado_conservacao')

        # Recupera o status do documento.
        status_documento = request.form.get('status_documento')

        # Recupera o status do estoque.
        status_estoque = request.form.get('status_estoque')

        # Recupera a placa.
        placa = request.form.get('placa')

        # Recupera o RENAVAM.
        renavam = request.form.get('renavam')

        # Recupera o arquivo de foto do veiculo.
        foto_veiculo = request.files.get('foto_veiculo')

        # Verifica se os campos obrigatorios foram preenchidos.
        if not all([id_categoria, id_marca, modelo, ano_fabricacao, ano_modelo, preco, placa, renavam]):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Preencha todos os campos obrigatórios.'}), 400

        # Valida o RENAVAM informado.
        if not renavam_validacao.validate(renavam):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'RENAVAM inválido'}), 400

        # Verifica se o RENAVAM tem 11 digitos.
        if len(str(renavam)) != 11:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O RENAVAM deve conter 11 dígitos.'}), 400

        # Busca conflito de placa ou RENAVAM em outro veiculo.
        cur.execute(  # Consulta placa ou RENAVAM repetidos em outro veiculo.
            """
            SELECT PLACA, -- Seleciona a placa do veiculo encontrado.
                   RENAVAM -- Seleciona o RENAVAM do veiculo encontrado.
            FROM VEICULO -- Define a tabela de veiculos.
            WHERE (PLACA = ? -- Filtra pela placa informada.
                   OR RENAVAM = ?) -- Filtra pelo RENAVAM informado.
              AND ID_VEICULO != ? -- Ignora o proprio veiculo editado.
            """,
            (placa, renavam, id_veiculo)
        )

        # Recupera o possivel conflito encontrado.
        conflito = cur.fetchone()

        # Verifica se existe conflito com outro veiculo.
        if conflito:
            # Retorna erro quando a placa ja existe em outro veiculo.
            if conflito[0] == placa:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Placa já cadastrada em outro veículo.'}), 409

            # Retorna erro quando o RENAVAM ja existe em outro veiculo.
            if conflito[1] == renavam:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'RENAVAM já cadastrado em outro veículo.'}), 409

        # Atualiza os dados do veiculo.
        cur.execute(  # Atualiza o veiculo pelo id informado.
            """
            UPDATE VEICULO -- Define a tabela que sera atualizada.
            SET ID_CATEGORIA = ?, -- Atualiza a categoria.
                ID_MARCA = ?, -- Atualiza a marca.
                MODELO = ?, -- Atualiza o modelo.
                ANO_FABRICACAO = ?, -- Atualiza o ano de fabricacao.
                ANO_MODELO = ?, -- Atualiza o ano do modelo.
                QUILOMETRAGEM = ?, -- Atualiza a quilometragem.
                COR = ?, -- Atualiza a cor.
                CAMBIO = ?, -- Atualiza o cambio.
                PRECO = ?, -- Atualiza o preco.
                DESCRICAO = ?, -- Atualiza a descricao.
                ESTADO_CONSERVACAO = ?, -- Atualiza o estado de conservacao.
                STATUS_DOCUMENTO = ?, -- Atualiza o status do documento.
                STATUS_ESTOQUE = ?, -- Atualiza o status do estoque.
                PLACA = ?, -- Atualiza a placa.
                RENAVAM = ? -- Atualiza o RENAVAM.
            WHERE ID_VEICULO = ? -- Filtra pelo id do veiculo.
            """,
            (
                id_categoria, id_marca, modelo, ano_fabricacao, ano_modelo,
                quilometragem, cor, cambio, preco, descricao,
                estado_conservacao, status_documento, status_estoque, placa, renavam,
                id_veiculo
            )
        )

        # Verifica se uma nova foto foi enviada.
        if foto_veiculo:
            # Define o nome padrao da imagem do veiculo.
            nome_imagem = f'veico_{id_veiculo}.png'

            # Monta o caminho completo da imagem.
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)

            # Salva a imagem enviada no caminho definido.
            foto_veiculo.save(caminho_foto)

        # Confirma a atualizacao no banco.
        con.commit()

        # Retorna sucesso da edicao.
        return jsonify({'mensagem': 'Veículo atualizado com sucesso!'}), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({"erro": "Token inválido ou adulterado."}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao editar carro: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()

@app.route('/reservar_carro/<int:id_veiculo>', methods=['POST'])
# Declara a função reservar_carro usada neste fluxo.
def reservar_carro(id_veiculo):
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json(silent=True) or request.form.to_dict() or {}
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = dados.get('id_usuario')

        # Verifica esta condição antes de continuar o fluxo.
        if id_usuario is None or (isinstance(id_usuario, str) and not id_usuario.strip()):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'id_usuario é obrigatório para reservar o veículo.'}), 400

        # Inicia uma operação protegida para permitir o tratamento de erros.
        try:
            # Define id_usuario para uso nas próximas etapas.
            id_usuario = int(id_usuario)
        except (TypeError, ValueError):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'id_usuario inválido.'}), 400

        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT ID_USUARIO, NOME
            FROM USUARIO
            WHERE ID_USUARIO = ?
            """,
            (id_usuario,)
        )
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Cliente não encontrado.'}), 404

        # Define nome_usuario para uso nas próximas etapas.
        nome_usuario = usuario[1]

        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT V.ID_VEICULO,
                   V.STATUS_ESTOQUE,
                   RV.ID_USUARIO,
                   V.MODELO,
                   U.EMAIL
            FROM VEICULO V
            LEFT JOIN RESERVA_VEICULO RV
              ON RV.ID_VEICULO = V.ID_VEICULO
            LEFT JOIN USUARIO U
              ON U.ID_USUARIO = RV.ID_USUARIO
            WHERE V.ID_VEICULO = ?
            """,
            (id_veiculo,)
        )
        # Define veiculo para uso nas próximas etapas.
        veiculo = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not veiculo:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Veículo não encontrado.'}), 404

        # Define status para uso nas próximas etapas.
        status = int(veiculo[1] or 0)
        # Define id_usuario_reserva para uso nas próximas etapas.
        id_usuario_reserva = veiculo[2]

        # Verifica esta condição antes de continuar o fluxo.
        if status == 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Este veículo já foi vendido.'}), 409

        # Verifica esta condição antes de continuar o fluxo.
        if id_usuario_reserva is not None:
            # Verifica esta condição antes de continuar o fluxo.
            if int(id_usuario_reserva) != id_usuario:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Este veículo já está reservado para outro cliente.'}), 409

            # Verifica esta condição antes de continuar o fluxo.
            if status != 3:
                # Executa este comando no banco de dados.
                cur.execute(
                    """
                    UPDATE VEICULO
                    SET STATUS_ESTOQUE = 3
                    WHERE ID_VEICULO = ?
                    """,
                    (id_veiculo,)
                )

            # Confirma no banco todas as alterações realizadas.
            con.commit()
            # Retorna o resultado desta operação.
            return jsonify({
                'mensagem': 'Veículo já estava reservado para este cliente.',
                'id_usuario_reserva': id_usuario,
                'nome_usuario_reserva': nome_usuario,
                'precisa_concluir_venda': True,
                'status_venda': 'RESERVADO_PENDENTE_CONCLUSAO'
            }), 200

        # Verifica esta condição antes de continuar o fluxo.
        if status != 1:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Este veículo não está disponível para reserva.'}), 409

        # Executa este comando no banco de dados.
        cur.execute(
            """
            INSERT INTO RESERVA_VEICULO (ID_VEICULO, ID_USUARIO)
            VALUES (?, ?)
            """,
            (id_veiculo, id_usuario)
        )

        # Executa este comando no banco de dados.
        cur.execute(
            """
            UPDATE VEICULO
            SET STATUS_ESTOQUE = 3
            WHERE ID_VEICULO = ?
            """,
            (id_veiculo,)
        )
        # Confirma no banco todas as alterações realizadas.
        con.commit()

        # Retorna o resultado desta operação.
        return jsonify({
            'mensagem': 'Veículo reservado com sucesso!',
            'id_usuario_reserva': id_usuario,
            'nome_usuario_reserva': nome_usuario,
            'precisa_concluir_venda': True,
            'status_venda': 'RESERVADO_PENDENTE_CONCLUSAO'
        }), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Desfaz alterações parciais após uma falha.
        con.rollback()
        # Define mensagem para uso nas próximas etapas.
        mensagem = str(e).lower()
        # Verifica esta condição antes de continuar o fluxo.
        if 'pk_reserva_veiculo' in mensagem or 'primary or unique key' in mensagem:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Este veículo acabou de ser reservado por outro cliente.'}), 409
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao reservar carro: {e}'}), 500

    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()

@app.route('/cancelar_reserva_carro/<int:id_veiculo>', methods=['DELETE'])
# Declara a função cancelar_reserva_carro usada neste fluxo.
def cancelar_reserva_carro(id_veiculo):
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json(silent=True) or request.form.to_dict() or {}
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = dados.get('id_usuario')

        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT V.ID_VEICULO,
                   V.STATUS_ESTOQUE,
                   RV.ID_USUARIO,
                   V.MODELO,
                   U.EMAIL
            FROM VEICULO V
            LEFT JOIN RESERVA_VEICULO RV
              ON RV.ID_VEICULO = V.ID_VEICULO
            LEFT JOIN USUARIO U
              ON U.ID_USUARIO = RV.ID_USUARIO
            WHERE V.ID_VEICULO = ?
            """,
            (id_veiculo,)
        )
        # Define veiculo para uso nas próximas etapas.
        veiculo = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not veiculo:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Veículo não encontrado.'}), 404

        # Define id_usuario_reserva para uso nas próximas etapas.
        id_usuario_reserva = veiculo[2]
        # Define nome_veiculo_email para uso nas próximas etapas.
        nome_veiculo_email = veiculo[3] if len(veiculo) > 3 and veiculo[3] else 'Veículo'
        # Define email_reserva para uso nas próximas etapas.
        email_reserva = veiculo[4] if len(veiculo) > 4 else None

        # Verifica esta condição antes de continuar o fluxo.
        if id_usuario_reserva is None:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Este veículo não possui reserva ativa.'}), 404

        # Verifica esta condição antes de continuar o fluxo.
        if id_usuario is not None and str(id_usuario).strip() and int(id_usuario_reserva) != int(id_usuario):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Esta reserva pertence a outro cliente.'}), 403

        # Executa este comando no banco de dados.
        cur.execute(
            """
            DELETE FROM RESERVA_VEICULO
            WHERE ID_VEICULO = ?
            """,
            (id_veiculo,)
        )

        # Executa este comando no banco de dados.
        cur.execute(
            """
            UPDATE VEICULO
            SET STATUS_ESTOQUE = 1
            WHERE ID_VEICULO = ?
              AND STATUS_ESTOQUE = 3
            """,
            (id_veiculo,)
        )

        # Confirma no banco todas as alterações realizadas.
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

        # Retorna o resultado desta operação.
        return jsonify({
            'mensagem': 'Reserva cancelada com sucesso.',
            'status_estoque': 1,
            'precisa_concluir_venda': False,
            'status_venda': 'DISPONIVEL'
        }), 200

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao cancelar reserva: {e}'}), 500

    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()



@app.route('/excluir_carro/<int:id_veiculo>', methods=['DELETE'])
# Declara a função excluir_carro usada neste fluxo.
def excluir_carro(id_veiculo):
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Guarda a data e hora atual para validar os agendamentos.
        agora = datetime.datetime.now()
        # Verifica se o veiculo existe antes de excluir.
        cur.execute(
            """
            SELECT ID_VEICULO -- Seleciona o id do veiculo.
            FROM VEICULO -- Define a tabela de veiculos.
            WHERE ID_VEICULO = ? -- Filtra pelo id do veiculo.
            """,
            (id_veiculo,)
        )
        # Retorna erro quando o veiculo nao existe.
        if not cur.fetchone():
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Veículo não encontrado.'}), 404
        # Busca vendas vinculadas para remover dependencias antes de excluir o veiculo.
        cur.execute(
            """
            SELECT ID_VENDA
            FROM VENDA
            WHERE ID_VEICULO = ?
            """,
            (id_veiculo,)
        )
        # Define ids_vendas para uso nas próximas etapas.
        ids_vendas = [linha[0] for linha in cur.fetchall()]
        # Executa este comando no banco de dados.
        cur.execute(  
            """
            SELECT ID_MANUTENCAO, DATA_MANUTENCAO -- Seleciona o id da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_VEICULO = ? -- Filtra pelo veiculo informado.
            """,
            (id_veiculo,)
        )
       
        # Define manutencoes para uso nas próximas etapas.
        manutencoes = cur.fetchall()
        
        # Percorre os itens necessários para executar esta etapa.
        for manutencao in manutencoes:
            # Verifica esta condição antes de continuar o fluxo.
            if manutencao[1] > agora:
                # Retorna o resultado desta operação.
                return jsonify({
                    'erro': 'Operação bloqueada: existe manutenção agendada no futuro para este veículo. Exclua o agendamento antes de excluir o carro.'
                }), 409
     
        # Percorre os itens necessários para executar esta etapa.
        for manutencao in manutencoes:
            # Define id_manutencao para uso nas próximas etapas.
            id_manutencao = manutencao[0]
            # Exclui os itens da manutencao.
            cur.execute(
                """
                DELETE
                FROM ITEM_MANUTENCAO
                WHERE ID_MANUTENCAO = ?
                """,
                (id_manutencao,)
            )
            # Exclui a manutencao.
            cur.execute(
                """
                DELETE
                FROM MANUTENCAO
                WHERE ID_MANUTENCAO = ?
                """,
                (id_manutencao,)
            )
        # Remove favoritos e reservas ligados ao veiculo.
        cur.execute("DELETE FROM FAVORITO WHERE ID_VEICULO = ?", (id_veiculo,))
        # Executa este comando no banco de dados.
        cur.execute("DELETE FROM RESERVA_VEICULO WHERE ID_VEICULO = ?", (id_veiculo,))

        # Remove registros financeiros e de estoque ligados as vendas do veiculo.
        for id_venda in ids_vendas:
            # Executa este comando no banco de dados.
            cur.execute(
                """
                SELECT ID_PARCELAMENTO
                FROM PARCELAMENTO
                WHERE ID_VENDA = ?
                """,
                (id_venda,)
            )
            # Define ids_parcelamentos para uso nas próximas etapas.
            ids_parcelamentos = [linha[0] for linha in cur.fetchall()]

            # Percorre os itens necessários para executar esta etapa.
            for id_parcelamento in ids_parcelamentos:
                # Executa este comando no banco de dados.
                cur.execute("DELETE FROM ITEM_PARCELAMENTO WHERE ID_PARCELAMENTO = ?", (id_parcelamento,))

            # Executa este comando no banco de dados.
            cur.execute("DELETE FROM PARCELAMENTO WHERE ID_VENDA = ?", (id_venda,))
            # Executa este comando no banco de dados.
            cur.execute("DELETE FROM MOVIMENTACAO_ESTOQUE WHERE ID_VENDA = ?", (id_venda,))
            # Executa este comando no banco de dados.
            cur.execute("DELETE FROM TRANSACOES_FINANCEIRAS WHERE ID_VENDA = ?", (id_venda,))
            # Executa este comando no banco de dados.
            cur.execute(
                """
                DELETE FROM FINANCEIRO
                WHERE DESCRICAO = ?
                """,
                (f'Venda de veiculo - codigo da venda: {id_venda}',)
            )
            # Executa este comando no banco de dados.
            cur.execute("DELETE FROM VENDA WHERE ID_VENDA = ?", (id_venda,))

        # Executa este comando no banco de dados.
        cur.execute("DELETE FROM TRANSACOES_FINANCEIRAS WHERE ID_VEICULO = ?", (id_veiculo,))
        # Exclui o veiculo do banco.
        cur.execute(  # Remove o veiculo pelo id informado.
            """
            DELETE -- Remove registros da tabela.
            FROM VEICULO -- Define a tabela de veiculos.
            WHERE ID_VEICULO = ? -- Filtra pelo id do veiculo.
            """,
            (id_veiculo,)
        )
        # Confirma a exclusao no banco.
        con.commit()
        # Define o nome padrao da imagem do veiculo.
        nome_imagem = f'veico_{id_veiculo}.png'
        # Monta o caminho completo da imagem.
        caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
        # Verifica se a imagem existe.
        if os.path.isfile(caminho_foto):
            # Remove a imagem do veiculo excluido.
            os.remove(caminho_foto)
        # Retorna sucesso da exclusao.
        return jsonify({'mensagem': 'Veículo excluído com sucesso!'}), 200
    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401
    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401
    except Exception as e:
        # Desfaz alteracoes pendentes em caso de erro.
        con.rollback()
        # Define mensagem para uso nas próximas etapas.
        mensagem = str(e).lower()
        # Verifica esta condição antes de continuar o fluxo.
        if 'fk_vendas_veiculo' in mensagem or 'foreign key' in mensagem:
            # Retorna o resultado desta operação.
            return jsonify({
                'erro': 'Este veículo já possui venda cadastrada e não pode ser excluído. Para manter o histórico financeiro, altere o status do veículo em vez de excluir.'
            }), 409
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao excluir carro {e}'}), 500
    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/listar_carro', methods=['GET'])
# Declara a função listar_carro usada neste fluxo.
def listar_carro():
    # Abre um cursor para consultar o banco.
    cur = con.cursor()

    # Recupera o filtro de categoria pela URL.
    categoria = request.args.get('categoria')

    # Recupera o filtro de marca pela URL.
    marca = request.args.get('marca')

    # Recupera o filtro de modelo pela URL.
    modelo = request.args.get('modelo')

    # Recupera o filtro de ano pela URL.
    ano = request.args.get('ano')

    # Monta a consulta base para listar veiculos.
    query = """
        SELECT V.ID_VEICULO, -- Seleciona o id do veiculo.
               V.ID_CATEGORIA, -- Seleciona o id da categoria.
               V.ID_MARCA, -- Seleciona o id da marca.
               M.MARCA, -- Seleciona o nome da marca.
               V.MODELO, -- Seleciona o modelo do veiculo.
               V.ANO_FABRICACAO, -- Seleciona o ano de fabricacao.
               V.ANO_MODELO, -- Seleciona o ano do modelo.
               V.QUILOMETRAGEM, -- Seleciona a quilometragem.
               V.COR, -- Seleciona a cor.
               V.CAMBIO, -- Seleciona o cambio.
               V.PRECO, -- Seleciona o preco.
               V.DESCRICAO, -- Seleciona a descricao.
               V.ESTADO_CONSERVACAO, -- Seleciona o estado de conservacao.
               V.STATUS_DOCUMENTO, -- Seleciona o status do documento.
               CASE -- Garante status reservado quando houver reserva ativa.
                   WHEN RV.ID_USUARIO IS NOT NULL
                        AND COALESCE(V.STATUS_ESTOQUE, 0) <> 2
                   THEN 3
                   ELSE V.STATUS_ESTOQUE
               END AS STATUS_ESTOQUE, -- Seleciona o status de estoque coerente.
               V.PLACA, -- Seleciona a placa.
               V.RENAVAM, -- Seleciona o RENAVAM.
               C.NOME, -- Seleciona o nome da categoria.
               RV.ID_USUARIO, -- Seleciona o id do cliente que reservou.
               U.NOME -- Seleciona o nome do cliente que reservou.
        FROM VEICULO V -- Define a tabela principal de veiculos.
                 INNER JOIN MARCA M ON V.ID_MARCA = M.ID_MARCA -- Junta o veiculo com sua marca.
                 INNER JOIN CATEGORIA C ON V.ID_CATEGORIA = C.ID_CATEGORIA -- Junta o veiculo com sua categoria.
                 LEFT JOIN RESERVA_VEICULO RV ON RV.ID_VEICULO = V.ID_VEICULO -- Junta reserva ativa do veiculo.
                 LEFT JOIN USUARIO U ON U.ID_USUARIO = RV.ID_USUARIO -- Junta os dados do cliente que reservou.
        WHERE 1=1 -- WHERE 1=1 e uma condicao que sempre e verdadeira e nao filtra nada.
    """

    # Cria a lista de valores usados nos filtros.
    filtros = []

    # Adiciona filtro por categoria quando informado.
    if categoria:
        # Atualiza o valor de query.
        query += """
        AND UPPER(C.NOME) = UPPER(?) -- Filtra pelo nome da categoria.
        """
        # Executa append nesta etapa do fluxo.
        filtros.append(categoria)

    # Adiciona filtro por marca quando informado.
    if marca:
        # Atualiza o valor de query.
        query += """
        AND M.MARCA LIKE ? -- Filtra por parte do nome da marca.
        """
        # Executa append nesta etapa do fluxo.
        filtros.append(f"%{marca}%")

    # Adiciona filtro por modelo quando informado.
    if modelo:
        # Atualiza o valor de query.
        query += """
        AND V.MODELO LIKE ? -- Filtra por parte do modelo.
        """
        # Executa append nesta etapa do fluxo.
        filtros.append(f"%{modelo}%")

    # Adiciona filtro por ano quando informado.
    if ano:
        # Atualiza o valor de query.
        query += """
        AND V.ANO_FABRICACAO = ? -- Filtra pelo ano de fabricacao.
        """
        # Executa append nesta etapa do fluxo.
        filtros.append(ano)

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define id_usuario_logado para uso nas próximas etapas.
        id_usuario_logado = obter_id_usuario_token()
        # Executa a consulta montada com os filtros.
        cur.execute(query, tuple(filtros))  # Busca os carros conforme os filtros informados.

        # Recupera os veiculos encontrados.
        rows = cur.fetchall()

        # Define ids_favoritos para uso nas próximas etapas.
        ids_favoritos = set()
        # Verifica esta condição antes de continuar o fluxo.
        if id_usuario_logado:
            # Executa este comando no banco de dados.
            cur.execute(
                """
                SELECT ID_VEICULO
                FROM FAVORITO
                WHERE ID_USUARIO = ?
                """,
                (id_usuario_logado,)
            )
            # Define ids_favoritos para uso nas próximas etapas.
            ids_favoritos = {linha[0] for linha in cur.fetchall()}

        # Cria a lista final de carros.
        carros = []

        # Percorre cada veiculo retornado.
        for r in rows:
            # Guarda o id do veiculo atual.
            id_veiculo = r[0]

            # Adiciona o carro formatado na lista.
            carros.append({
                "id": id_veiculo,
                "id_categoria": r[1],
                "id_marca": r[2],
                "marca": r[3],
                "nome": f"{r[3]} {r[4]}",
                "modelo": r[4],
                "ano_fabricacao": r[5],
                "ano_modelo": r[6],
                "quilometragem": r[7],
                "cor": r[8],
                "cambio": r[9],
                "preco": float(r[10]),
                "descricao": r[11],
                "estado_conservacao": r[12],
                "status_documento": r[13],
                "status_estoque": r[14],
                "placa": r[15],
                "renavam": r[16],
                "categoria": r[17],
                "id_usuario_reserva": r[18],
                "nome_usuario_reserva": r[19],
                "data_entrada": data_upload_veiculo(id_veiculo),
                "precisa_concluir_venda": r[14] == 3 and r[18] is not None,
                "status_venda": (
                    "VENDIDO"
                    if r[14] == 2
                    else "RESERVADO_PENDENTE_CONCLUSAO"
                    if (r[14] == 3 and r[18] is not None)
                    else "DISPONIVEL"
                ),
                "mensagem_venda": (
                    "Reservado: precisa concluir a venda."
                    if (r[14] == 3 and r[18] is not None)
                    else ""
                ),
                "favorito": id_veiculo in ids_favoritos,
                "imagem": f"/uploads/veico_{id_veiculo}.png"
            })

        # Retorna a lista de carros.
        return jsonify({"carros": carros}), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({"erro": f"Erro ao listar carros: {e}"}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()

@app.route('/uploads/<path:nome_arquivo>')
# Declara a função uploads usada neste fluxo.
def uploads(nome_arquivo):
    # Retorna o arquivo solicitado da pasta de uploads.
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)


@app.route('/buscar_categoria', methods=['POST'])
# Declara a função buscar_categoria usada neste fluxo.
def buscar_categoria():
    # Abre um cursor para consultar o banco.
    cur = con.cursor()

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Recupera o nome usado como filtro.
        nome = request.form.get('nome')

        # Recupera o id da categoria usado como filtro.
        id_categoria = request.form.get('id_categoria')

        # Cria a lista final de categorias.
        categorias = []

        # Busca categorias pelo nome.
        if nome:
            # Normaliza o nome para comparar em maiusculas.
            nome_formatado = nome.strip().upper()

            # Executa a busca por nome.
            cur.execute(  # Busca categorias parecidas com o nome informado.
                """
                SELECT ID_CATEGORIA, -- Seleciona o id da categoria.
                       NOME -- Seleciona o nome da categoria.
                FROM CATEGORIA -- Define a tabela de categorias.
                WHERE UPPER(NOME) LIKE ? -- Filtra pelo nome da categoria.
                """,
                (f"%{nome_formatado}%",)
            )

        # Busca categoria pelo id.
        elif id_categoria:
            # Executa este comando no banco de dados.
            cur.execute(  # Busca categoria pelo id informado.
                """
                SELECT ID_CATEGORIA, -- Seleciona o id da categoria.
                       NOME -- Seleciona o nome da categoria.
                FROM CATEGORIA -- Define a tabela de categorias.
                WHERE ID_CATEGORIA = ? -- Filtra pelo id da categoria.
                """,
                (id_categoria,)
            )

        # Busca todas as categorias quando nao ha filtro.
        else:
            # Executa este comando no banco de dados.
            cur.execute(  # Busca todas as categorias cadastradas.
                """
                SELECT ID_CATEGORIA, -- Seleciona o id da categoria.
                       NOME -- Seleciona o nome da categoria.
                FROM CATEGORIA -- Define a tabela de categorias.
                """
            )

        # Recupera as categorias encontradas.
        rows = cur.fetchall()

        # Percorre cada categoria retornada.
        for categoria in rows:
            # Adiciona a categoria formatada na lista.
            categorias.append({
                "id_categoria": categoria[0],
                "nome": categoria[1],
            })

        # Retorna erro quando nenhuma categoria foi encontrada.
        if not categorias:
            # Retorna o resultado desta operação.
            return jsonify({"erro": "Nenhuma categoria encontrada com esse filtro."}), 404

        # Retorna as categorias encontradas.
        return jsonify({"categoria": categorias}), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({"erro": f"Erro ao buscar categoria: {e}"}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/favoritar_carro/<int:id_veiculo>', methods=['POST'])
# Declara a função favoritar_carro usada neste fluxo.
def favoritar_carro(id_veiculo):
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define token para uso nas próximas etapas.
        token = request.cookies.get('access_token')
        # Verifica esta condição antes de continuar o fluxo.
        if not token:
            # Define auth_header para uso nas próximas etapas.
            auth_header = request.headers.get('Authorization', '')
            # Verifica esta condição antes de continuar o fluxo.
            if auth_header.lower().startswith('bearer '):
                # Define token para uso nas próximas etapas.
                token = auth_header.split(' ', 1)[1].strip()

        # Verifica esta condição antes de continuar o fluxo.
        if not token:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso negado. Token não encontrado.'}), 401

        # Define dados para uso nas próximas etapas.
        dados = jwt.decode(token, senha_secreta, algorithms=['HS256'])
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = dados['id_user']

        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT ID_VEICULO
            FROM VEICULO
            WHERE ID_VEICULO = ?
            """,
            (id_veiculo,)
        )
        # Define resultado para uso nas próximas etapas.
        resultado = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not resultado:
            # Retorna o resultado desta operação.
            return jsonify({"erro": "Veículo não encontrado"}), 404

        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT ID_FAVORITO
            FROM FAVORITO
            WHERE ID_USUARIO = ? AND ID_VEICULO = ?
            """,
            (id_usuario, id_veiculo)
        )
        # Define favorito para uso nas próximas etapas.
        favorito = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if favorito:
            # Executa este comando no banco de dados.
            cur.execute(
                """
                DELETE
                FROM FAVORITO
                WHERE ID_USUARIO = ? AND ID_VEICULO = ?
                """,
                (id_usuario, id_veiculo)
            )
            # Confirma no banco todas as alterações realizadas.
            con.commit()
            # Retorna o resultado desta operação.
            return jsonify({"mensagem": "Carro desfavoritado com sucesso!"}), 200

        # Executa este comando no banco de dados.
        cur.execute(
            """
            INSERT INTO FAVORITO(ID_USUARIO, ID_VEICULO)
            VALUES (?, ?)
            """,
            (id_usuario, id_veiculo)
        )
        # Confirma no banco todas as alterações realizadas.
        con.commit()
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Veículo favoritado com sucesso!'}), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({"erro": f"Erro ao favoritar: {e}"}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/listar_favoritos', methods=['GET'])
# Declara a função listar_favoritos usada neste fluxo.
def listar_favoritos():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = obter_id_usuario_token()

        # Verifica esta condição antes de continuar o fluxo.
        if not id_usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso negado. Token não encontrado.'}), 401

        # Executa este comando no banco de dados.
        cur.execute(
            """
            SELECT V.ID_VEICULO,
                   V.ID_CATEGORIA,
                   V.ID_MARCA,
                   M.MARCA,
                   V.MODELO,
                   V.ANO_FABRICACAO,
                   V.ANO_MODELO,
                   V.QUILOMETRAGEM,
                   V.COR,
                   V.CAMBIO,
                   V.PRECO,
                   V.DESCRICAO,
                   V.ESTADO_CONSERVACAO,
                   V.STATUS_DOCUMENTO,
                   V.STATUS_ESTOQUE,
                   V.PLACA,
                   V.RENAVAM,
                   C.NOME,
                   F.ID_FAVORITO
            FROM FAVORITO F
            INNER JOIN VEICULO V ON V.ID_VEICULO = F.ID_VEICULO
            INNER JOIN MARCA M ON V.ID_MARCA = M.ID_MARCA
            INNER JOIN CATEGORIA C ON V.ID_CATEGORIA = C.ID_CATEGORIA
            WHERE F.ID_USUARIO = ?
            ORDER BY F.ID_FAVORITO DESC
            """,
            (id_usuario,)
        )

        # Define favoritos para uso nas próximas etapas.
        favoritos = []
        # Percorre os itens necessários para executar esta etapa.
        for r in cur.fetchall():
            # Define id_veiculo para uso nas próximas etapas.
            id_veiculo = r[0]
            # Executa append nesta etapa do fluxo.
            favoritos.append({
                "id": id_veiculo,
                "id_veiculo": id_veiculo,
                "id_categoria": r[1],
                "id_marca": r[2],
                "marca": r[3],
                "nome": f"{r[3]} {r[4]}",
                "modelo": r[4],
                "ano_fabricacao": r[5],
                "ano_modelo": r[6],
                "quilometragem": r[7],
                "cor": r[8],
                "cambio": r[9],
                "preco": float(r[10] or 0),
                "descricao": r[11],
                "estado_conservacao": r[12],
                "status_documento": r[13],
                "status_estoque": r[14],
                "placa": r[15],
                "renavam": r[16],
                "categoria": r[17],
                "id_favorito": r[18],
                "favorito": True,
                "imagem": f"/uploads/veico_{id_veiculo}.png"
            })

        # Retorna o resultado desta operação.
        return jsonify({"favoritos": favoritos}), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({"erro": f"Erro ao listar favoritos: {e}"}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/limpar_favoritos', methods=['DELETE'])
# Declara a função limpar_favoritos usada neste fluxo.
def limpar_favoritos():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = obter_id_usuario_token()

        # Verifica esta condição antes de continuar o fluxo.
        if not id_usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso negado. Token não encontrado.'}), 401

        # Executa este comando no banco de dados.
        cur.execute(
            """
            DELETE
            FROM FAVORITO
            WHERE ID_USUARIO = ?
            """,
            (id_usuario,)
        )
        # Confirma no banco todas as alterações realizadas.
        con.commit()

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Favoritos removidos com sucesso.'}), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({"erro": f"Erro ao limpar favoritos: {e}"}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()
