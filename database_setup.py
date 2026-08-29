import sqlite3
from werkzeug.security import generate_password_hash

def criar_banco():
    # Conecta ao arquivo (se não existir, ele cria)
    conn = sqlite3.connect('mural.db')
    cursor = conn.cursor()

    # 1. Criar Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # 2. Criar Tabela de Mídias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS midias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            legenda TEXT,
            tempo INTEGER DEFAULT 7,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        )
    ''')

    # 3. Criar o seu usuário Super ADM (só se não existir)
    # Senha padrão: admin123 (Você poderá mudar depois)
    senha_hash = generate_password_hash('admin123')
    try:
        cursor.execute('INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)',
                       ('admin', senha_hash, 'admin'))
        print("✅ Usuário 'admin' criado com sucesso! Senha: admin123")
    except sqlite3.IntegrityError:
        print("ℹ️ Usuário admin já existe.")

    conn.commit()
    conn.close()
    print("🚀 Banco de Dados configurado!")

if __name__ == '__main__':
    criar_banco()