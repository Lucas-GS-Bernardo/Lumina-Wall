import sqlite3
from werkzeug.security import generate_password_hash

def restaurar_admin():
    # --- CONFIGURAÇÕES ---
    NOME_BANCO = 'mural.db'  # <--- Verifique se o nome está correto!
    NOVA_SENHA = 'eanig3321'         # <--- Senha temporária que você quer definir
    # ---------------------

    try:
        conn = sqlite3.connect(NOME_BANCO)
        cursor = conn.cursor()

        # Gera o hash de segurança da nova senha
        hash_senha = generate_password_hash(NOVA_SENHA)

        # Tenta atualizar o usuário com ID 1
        cursor.execute('''
            UPDATE usuarios 
            SET password = ?, reset_prio = 0 
            WHERE id = 1
        ''', (hash_senha,))

        if cursor.rowcount > 0:
            conn.commit()
            print("-----------------------------------------")
            print("✅ SUCESSO: Senha do Admin (ID 1) restaurada!")
            print(f"🔑 Nova senha temporária: {NOVA_SENHA}")
            print("-----------------------------------------")
        else:
            print("❌ ERRO: Usuário com ID 1 não foi encontrado no banco.")

    except Exception as e:
        print(f"⚠️ Ocorreu um erro: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    restaurar_admin()