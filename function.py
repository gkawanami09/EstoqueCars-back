def verificar_senha(senha):

    if len(senha) < 10:
        return "A senha deve ter no mínimo 10 caracteres"

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_simbolo = False
    simbolos = "!@#$%^&*()_+-=[]{}|;:,.<>?"

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
    
def enviando_email(destinatario, assunto, mensagem):
    user = 'estoquecars@gmail.com'
    senha = ''
    
    msg = MIMEText(mensagem)
    msg['Subject'] = assunto
    msg['From'] = user
    msg['To'] = destinatario
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(user, senha)
    server.send_message(msg)
    server.quit()