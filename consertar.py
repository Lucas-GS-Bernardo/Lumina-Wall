import sqlite3

conn = sqlite3.connect('mural.db')
cursor = conn.cursor()

# 1. Garante que o admin não está marcado para 'reset obrigatório'
cursor.execute("UPDATE usuarios SET reset_prio = 0 WHERE username = 'admin'")

# 2. (Opcional) Se você acha que a senha do admin mudou, force para 'admin123'
from werkzeug.security import generate_password_hash
nova_senha = generate_password_hash("admin123")
cursor.execute("UPDATE usuarios SET password = ? WHERE username = 'admin'", (nova_senha,))

conn.commit()
conn.close()
print("Acesso do admin limpo! Tente logar com 'admin' e 'admin123'")