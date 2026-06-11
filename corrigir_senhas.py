"""
Script para atualizar as senhas de teste no banco de dados.
Execute apos importar o banco_de_dados.sql.

Uso: python corrigir_senhas.py
"""

import MySQLdb
from werkzeug.security import generate_password_hash
from configuracao import Configuracao

def corrigir_senhas():
    """Gera um hash único e aplica a senha padrão nos usuários de demonstração."""

    senha_padrao = 'cardiolab123'
    senha_hash = generate_password_hash(senha_padrao, method='pbkdf2:sha256')
    
    print(f"Hash gerado: {senha_hash[:50]}...")
    
    try:
        banco = MySQLdb.connect(
            host=Configuracao.MYSQL_HOST,
            user=Configuracao.MYSQL_USER,
            passwd=Configuracao.MYSQL_PASSWORD,
            db=Configuracao.MYSQL_DB,
            charset='utf8mb4'
        )
        cursor = banco.cursor()
        
        cursor.execute("UPDATE usuarios SET senha_hash = %s", (senha_hash,))
        banco.commit()
        
        print(f"[CERTO] {cursor.rowcount} senhas atualizadas com sucesso!")
        print(f"\nCredenciais de teste:")
        print(f"  Paciente: maria@email.com / {senha_padrao}")
        print(f"  Médico:   dr.ricardo@cardiolab.com.br / {senha_padrao}")
        print(f"  Administrador: admin@cardiolab.com.br / {senha_padrao}")
        
        cursor.close()
        banco.close()
        
    except Exception as erro:
        print(f"ERRO: {erro}")
        print("Verifique as configurações do MySQL em configuracao.py")

if __name__ == '__main__':
    corrigir_senhas()


