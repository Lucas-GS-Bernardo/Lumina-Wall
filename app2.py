from flask import Flask,make_response, render_template, request, redirect, url_for, jsonify, session, send_from_directory, send_file, flash
import os
import sqlite3
import functools
import shutil
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import time
import gc

# --- Configurações de Versão ---

VERSION = "by Lucas Godoy - v1.0.6"
EDITION = "️🔶 Jaspe 🔶"

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = "mural_escola_2026_seguro"
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'mural.db')

print("--- TESTE DE CAMINHO ---")
print(f"O Flask está procurando templates em: {app.template_folder}")
print(f"Arquivos encontrados lá: {os.listdir(app.template_folder) if os.path.exists(app.template_folder) else 'PASTA NÃO ENCONTRADA'}")
print("------------------------")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Leão de Chácara 🦁 (Versão Blindada contra Loops)


# ----- CONFIGURAÇÕES DE PASTAS -----

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
THUMB_FOLDER  = os.path.join(BASE_DIR, 'static', 'thumbnails')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMB_FOLDER'] = THUMB_FOLDER

for folder in [UPLOAD_FOLDER, THUMB_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

# --- Variáveis de Controle ---

mural_status = {
    "versao": int(time.time()), 
    "tipo": "manual"
}
houve_upload_recente = False

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'avi', 'mkv'}


def allowed_file(filename):
    return '.' in filename and \
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_version():
    return dict(current_version=f"{EDITION} {VERSION}")

# --- FUNÇÕES AUXILIARES ---

def get_db_connection():
    conn = sqlite3.connect(DB_PATH) # Usa o caminho fixo
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for('login'))
        if session.get("role") != 'admin':
            registrar_log(
            acao="❌ACESSO NEGADO",
            severidade="DANGER",
            detalhes=f"Tentativa em: {request.path}"
        )
            return "Acesso Negado", 403
        return f(*args, **kwargs)
    return decorated_function

# --- SISTEMA DE LOGS HÍBRIDO (TXT + BANCO) ---
def verificar_e_fazer_backup_mensal():
    # Agora a lista nasce sempre que a função é chamada, evitando o erro UnboundLocalError
    meses = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho", 
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    agora = datetime.now()
    if agora.day == 5:
        nome_backup = f"log_{meses[agora.month]}_{agora.year}.txt"
        if os.path.exists("historico_logs.txt") and not os.path.exists(nome_backup):
            shutil.copy("historico_logs.txt", nome_backup)

def registrar_log(acao, severidade="INFO", alvo_id=None, detalhes=None):
    try:
        verificar_e_fazer_backup_mensal()
        u_id = session.get('user_id', 0)
        u_nome = session.get('username', 'Sistema')
        
        try:
            ip = request.remote_addr
            ua = request.user_agent.string
        except:
            ip, ua = "127.0.0.1", "Local"

        # 1. Banco (Auditoria Detalhada)
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO logs (usuario_id, usuario_nome, acao, severidade, alvo_id, detalhes, ip_address, user_agent) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (u_id, u_nome, acao, severidade, alvo_id, detalhes, ip, ua))
        conn.commit()
        conn.close()

        # 2. TXT
        agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        log_line = f"[{agora}] Usuário: {u_nome}: {acao} ({severidade})\n"
        with open("historico_logs.txt", "a", encoding="utf-8") as f:
            f.write(log_line)

    except Exception as e:
        # Este print vai te mostrar se ainda houver erro de nome de variável (como o 'meses')
        print(f"Erro crítico ao registrar log: {e}")

# --- INICIALIZAÇÃO DO BANCO ---
def init_db():
    conn = get_db_connection()
    
    # 1. Configurações
    conn.execute('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, nome_escola TEXT, tempo_transicao INTEGER)')
    
    # 2. Usuários
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            email TEXT,
            ip TEXT,
            user_agent TEXT,
            reset_prio INTEGER DEFAULT 0
        )
    ''')

    # 3. Mídias (Usaremos APENAS esta para o mural)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS midias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            tipo TEXT,
            legenda TEXT,
            tempo INTEGER DEFAULT 10,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        )
    ''')

    # 4. Logs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            usuario_id INTEGER, 
            usuario_nome TEXT, 
            acao TEXT, 
            severidade TEXT, 
            alvo_id INTEGER, 
            detalhes TEXT, 
            ip_address TEXT, 
            user_agent TEXT, 
            data_hora TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    ''')

# --- MIGRAÇÕES RÁPIDAS ---
    try: conn.execute(
        'ALTER TABLE usuarios ADD COLUMN email TEXT'
        )
    except: pass

    try: conn.execute(
        'ALTER TABLE usuarios ADD COLUMN reset_prio INTEGER DEFAULT 0'
        )
    except: pass

    try: conn.execute(
        'ALTER TABLE midias ADD COLUMN ordem INTEGER DEFAULT 0'
        )
    except: pass

# --- DADOS INICIAIS ---
    if not conn.execute('SELECT 1 FROM configuracoes WHERE id = 1').fetchone():
        conn.execute('INSERT INTO configuracoes (id, nome_escola, tempo_transicao) VALUES (1, ?, ?)', 
                     ('Lumina Wall', 1500))
    
    if not conn.execute('SELECT 1 FROM usuarios WHERE username = ?', ('admin',)).fetchone():
        senha_hash = generate_password_hash("admin123")
        conn.execute('INSERT INTO usuarios (username, password, role, email, reset_prio) VALUES (?, ?, ?, ?, ?)', 
                     ('admin', senha_hash, 'admin', 'admin@escola.com', 0))
        
    conn.commit()
    conn.close()
    print("♾️ Banco de Dados rc.3 sincronizado!")

# --- ROTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já estiver logado e tentar ir para /login, joga direto pro admin
    if session.get('logged_in'):
        return redirect(url_for('admin_panel'))

    erro = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user_row = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user_row:
            user = dict(user_row)
            if check_password_hash(user['password'], password):
                session.clear() # Limpa resquícios antigos para evitar conflito
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                
                registrar_log("✅ Login realizado")
                
                if user.get('reset_prio') == 1:
                    return redirect(url_for('processar_troca_obrigatoria'))
                return redirect(url_for('admin_panel'))
        
        registrar_log("FALHA LOGIN", "WARNING", detalhes=f"User: {username}")
        erro = "Usuário ou senha incorretos"

    return render_template('login.html', erro=erro)

@app.route('/trocar_senha_obrigatoria', methods=['GET', 'POST'])
@login_required
def processar_troca_obrigatoria(): # O NOME DA FUNÇÃO DEVE SER ESTE
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao')
        user_id = session.get('user_id')

        if nova_senha == confirmacao:
            hash_senha = generate_password_hash(nova_senha)
            conn = get_db_connection()
            conn.execute('UPDATE usuarios SET password=?, reset_prio=0 WHERE id=?', (hash_senha, user_id))
            conn.commit()
            conn.close()

            registrar_log("🔐 Senha obrigatória alterada", severidade="SUCCESS", detalhes="O usuário definiu sua própria senha após o reset.")
            return redirect(url_for('admin_panel')) # Ou sua página inicial
        
        return "As senhas não coincidem", 400

    return render_template('trocar_senha_obrigatorio.html')

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_panel():
    conn = get_db_connection()
    global estado_atualizacao
    global alerta_midia_nova, pendencia_manual
    
    # Contagem de mídias atuais
    n_img = conn.execute("SELECT COUNT(*) FROM midias WHERE ativo = 1 AND filename NOT LIKE '%.mp4'").fetchone()[0]
    n_vid = conn.execute("SELECT COUNT(*) FROM midias WHERE ativo = 1 AND filename LIKE '%.mp4'").fetchone()[0]
    
    if request.method == 'POST':
        file = request.files.get('arquivo')
        legenda = request.form.get('legenda', '').strip()
        tempo_raw = request.form.get('tempo')

        # 1. Validação de segurança: Tipo de Arquivo
        if not file or not allowed_file(file.filename):
            nome_arq = file.filename if file else "Nenhum"
            registrar_log("⚠️ Tentativa de upload inválido", "WARNING", detalhes=nome_arq)
            conn.close()
            return "Erro: Tipo de arquivo não permitido!", 400

        # 2. Validação de preenchimento
        if not legenda or file.filename == '':
            conn.close()
            return "Erro: Legenda e arquivo obrigatórios!", 400

        filename = secure_filename(file.filename)
        is_video = filename.lower().endswith(('.mp4', '.mov', '.avi')) # Suporta mais extensões de vídeo

        # 3. Verificação de Limites (Imagens 5, Vídeos 2)
        #if (not is_video and n_img >= 5) or (is_video and n_vid >= 2):
            #conn.close()
            #return "Limite atingido! Remova algo antes de postar novo conteúdo.", 400

        # 4. Salvamento do arquivo
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # 5. Processamento de Miniatura (Apenas Imagem)
        if not is_video:
            try:
                img = Image.open(filepath)
                img.thumbnail((300, 300))
                img.save(os.path.join(THUMB_FOLDER, os.path.splitext(filename)[0] + ".webp"), "WEBP")
            except Exception as e:
                print(f"Erro ao gerar thumb: {e}")

    # 6. Definição do Tempo
        try:
            tempo = 0 if is_video else int(tempo_raw if tempo_raw else 10)
        except:
            tempo = 10

        # 7. Gravação no Banco (CORRIGIDO: Removido o recuo excessivo da indentação)
        conn = get_db_connection()
        conn.execute('INSERT INTO midias (filename, legenda, tempo, ativo, ordem) VALUES (?, ?, ?, ?, ?)', 
                        (filename, legenda, tempo, 1, 99))
        conn.commit()
        conn.close()
            
        global houve_upload_recente
        houve_upload_recente = True
            
        global alerta_midia_nova, pendencia_manual
        alerta_midia_nova = True
        
        registrar_log(
            "🚀 Mídia enviada",
            detalhes=f"{legenda} | Arquivo: {filename} | Tempo: {tempo}s"
        )

        return redirect(url_for('admin_panel'))

    # Se for GET (Apenas visualizando a página)
    midias = conn.execute('SELECT * FROM midias ORDER BY ordem ASC, id DESC').fetchall()
    config = conn.execute('SELECT * FROM configuracoes WHERE id = 1').fetchone()
    conn.close()
    return render_template('admin.html', arquivos=midias, config=config, n_img=n_img, n_vid=n_vid)

# --- ROTA DE LOGS SIMPLES (VISUAL ANTIGO) ---
@app.route('/logs')
@admin_required
def logs(): # Certifique-se que o nome aqui é o que você usa no url_for
    conn = get_db_connection()
    # Buscamos a ação (com ícone) e os detalhes para o visual ficar completo
    logs_data = conn.execute('''
        SELECT data_hora, usuario_nome, acao, detalhes 
        FROM logs ORDER BY id DESC LIMIT 100
    ''').fetchall()
    conn.close()
    return render_template('logs.html', logs=logs_data)

# --- ROTA DE AUDITORIA AVANÇADA (ID 1 APENAS) ---
@app.route('/auditoria')
@admin_required
def exibir_auditoria_detalhada():
    if session.get('user_id') != 1:
        return redirect(url_for('admin_panel', erro="Acesso Restrito ao Root."))
    
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs ORDER BY data_hora DESC LIMIT 500').fetchall()
    conn.close()
    return render_template('auditoria.html', logs=logs)

# --- OUTRAS ROTAS DO SISTEMA ---
@app.route('/atualizar_tempo/<nome_arquivo>', methods=['POST'])
@login_required
def atualizar_tempo(nome_arquivo):
    novo_tempo = int(request.form.get('tempo', 10))
    conn = get_db_connection()
    # 1. Primeiro buscamos a legenda da mídia para usar no log
    midia = conn.execute('SELECT legenda FROM midias WHERE filename = ?', (nome_arquivo,)).fetchone()
    if midia:
        legenda_viva = midia['legenda'] # Aqui definimos a variável que faltava
        # 2. Atualizamos o tempo
        conn.execute('UPDATE midias SET tempo = ? WHERE filename = ?', (novo_tempo, nome_arquivo))
        conn.commit()
        # 3. Agora o registrar_log vai funcionar porque 'legenda_viva' existe
        registrar_log(f"⏱️ Tempo alterado: {legenda_viva}", detalhes=f"Arquivo: {nome_arquivo} | Novo tempo: {novo_tempo}s")
    conn.close()
    return redirect(url_for('admin_panel'))
    
# app.py
@app.route('/atualizar_legenda/<nome_arquivo>', methods=['POST'])
@login_required
def atualizar_legenda(nome_arquivo):
    nova = (request.form.get('legenda') or '').strip()
    if not nova:
        return jsonify({"ok": False, "msg": "Legenda não pode ser vazia."}), 400
    if len(nova) > 50:
        return jsonify({"ok": False, "msg": "Máximo de 50 caracteres."}), 400

    conn = get_db_connection()
    conn.execute('UPDATE midias SET legenda = ? WHERE filename = ?', (nova, nome_arquivo))
    conn.commit()
    conn.close()

    registrar_log("✏️ Legenda alterada", detalhes=f"Arquivo: {nome_arquivo} → {nova}")
    return jsonify({"ok": True, "legenda": nova}), 200

@app.route('/toggle/<nome_arquivo>', methods=['POST'])
@login_required
def toggle(nome_arquivo):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT legenda, ativo, filename FROM midias WHERE filename=?',
        (nome_arquivo,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "msg": "Arquivo não encontrado"}), 404

    novo = 0 if int(row['ativo']) == 1 else 1
    conn.execute('UPDATE midias SET ativo=? WHERE filename=?', (novo, nome_arquivo))
    conn.commit()
    conn.close()

    # ✅ LOGAR AÇÃO (com legenda, arquivo e novo estado)
    estado_txt = "👀EXIBINDO" if novo == 1 else "🫣OCULTOU"
    registrar_log(
        acao=f" {estado_txt}: {row['legenda']} ",
        severidade="INFO",
        detalhes=f"Legenda: {row['legenda']} | Arquivo: {row['filename']}"
    )

    return jsonify({"ok": True, "novo_estado": novo})

@app.route('/deletar/<nome_arquivo>', methods=['POST'])
@login_required
def deletar(nome_arquivo):
    try:
        conn = get_db_connection()
        row = conn.execute(
            'SELECT filename, ativo, legenda FROM midias WHERE filename = ?',
            (nome_arquivo,)
        ).fetchone()

        if not row:
            conn.close()
            registrar_log(
                "🗑️ Solicitação de exclusão recebida",
                severidade="WARNING",
                detalhes=f"Arquivo não encontrado: {nome_arquivo}"
            )
            return jsonify({"ok": False, "msg": "Arquivo não encontrado"}), 404

        legenda = (row['legenda'] or '').strip()
        legenda_txt = f" — Legenda: {legenda}" if legenda else ""

        # Log de entrada com legenda
        registrar_log(
            "🗑️ Solicitação de exclusão recebida",
            detalhes=f"Arquivo: {row['filename']}{legenda_txt}"
        )

        is_video = row['filename'].lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
        if is_video and int(row['ativo']) == 1:
            conn.close()
            return jsonify({
                "ok": False,
                "msg": "Vídeo exibindo. Oculte e clique em ATUALIZAR NA TV antes de excluir."
            }), 400

        # 1) Apaga do banco
        conn.execute('DELETE FROM midias WHERE filename=?', (nome_arquivo,))
        conn.commit()
        conn.close()

        # 2) Apaga do disco (upload + thumb)
        up = os.path.join(app.config['UPLOAD_FOLDER'], row['filename'])
        if os.path.exists(up):
            os.remove(up)
        base = os.path.splitext(row['filename'])[0]
        th = os.path.join(app.config['THUMB_FOLDER'], f"{base}.webp")
        if os.path.exists(th):
            os.remove(th)

        # Log de sucesso com legenda
        registrar_log(
            "🗑️ Exclusão",
            detalhes=f"Arquivo: {row['filename']}{legenda_txt}"
        )

        return jsonify({"ok": True, "msg": "Arquivo excluído com sucesso."})

    except Exception as e:
        registrar_log("❌ Erro na exclusão", severidade="DANGER", detalhes=str(e))
        return jsonify({"ok": False, "msg": f"Falha ao excluir: {e}"}), 500

@app.route('/')
def mural():
    conn = get_db_connection()
    dados = conn.execute('SELECT * FROM midias WHERE ativo = 1 ORDER BY ordem ASC').fetchall()
    config_data = conn.execute('SELECT * FROM configuracoes WHERE id = 1').fetchone()
    conn.close()
    
    # Mude de 'index.html' para 'mural.html'
    return render_template('mural.html', arquivos=dados, config=config_data)
    
@app.route('/atualizar_mural', methods=['POST'])
@login_required
def atualizar_mural():
    try:
        # Aqui vai sua lógica existente para avisar as TVs 
        # (ex: socketio.emit ou atualizar um timestamp no banco)
        
        # REGISTRO DO LOG
        registrar_log(
            acao="🔄 Atualização do Mural",
            severidade="INFO",
            detalhes=f"O usuário solicitou a atualização imediata de todas as telas."
        )
        
        return jsonify({"status": "sucesso", "mensagem": "Mural atualizado!"})
    
    except Exception as e:
        registrar_log(
            acao="❌ Falha na atualização",
            severidade="DANGER",
            detalhes=str(e)
        )
        return jsonify({"status": "erro"}), 500

# --- LOGICA DE SINCRONIZAÇÃO UNIFICADA (VERSÃO v1.0.6-rc.3) ---
# Usamos apenas UM dicionário para tudo
mural_status = {
    "versao": int(time.time()),
    "tipo": "manual"
}

@app.route('/forcar_update', methods=['POST'])
@login_required
def forcar_update():
    global mural_status, houve_upload_recente
    
    # Atualiza o timestamp (ID da versão)
    mural_status["versao"] = int(time.time())
    
    if houve_upload_recente:
        mural_status["tipo"] = "nova_midia"
        detalhe = "Nova mídia enviada"
    else:
        mural_status["tipo"] = "manual"
        detalhe = "Mudança de ordem ou ocultação"
    
    houve_upload_recente = False 
    registrar_log("🔄 Atualização Solicitada", detalhes=detalhe)
    
    # Retorna a nova versão para o Admin saber que deu certo
    return jsonify({"status": "ok", "versao": mural_status["versao"]})

@app.route('/verificar_mudancas')
def verificar_mudancas():
    # IMPORTANTE: Não limpamos mais a variável aqui. 
    # Apenas entregamos a versão atual para quem perguntar.
    response = make_response(jsonify(mural_status))
    # Força o navegador (principalmente celular) a não guardar cache
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response
    
@app.route('/obter_midias')
def obter_midias():
    conn = get_db_connection()
    dados = conn.execute('SELECT * FROM midias WHERE ativo = 1 ORDER BY ordem ASC').fetchall()
    conn.close()
    
    lista_midias = []
    for d in dados:
        lista_midias.append({
            "filename": d['filename'],
            "tempo": d['tempo'] * 1000 if d['tempo'] else 7000,
            "is_video": d['filename'].lower().endswith(('.mp4', '.mov', '.avi'))
        })
    
    response = make_response(jsonify(lista_midias))
    # Permite ao navegador guardar o JSON em memória por curtos períodos
    response.headers['Cache-Control'] = 'public, max-age=5'
    return response

@app.route('/static/uploads/<path:filename>')
def custom_static_uploads(filename):
    response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename))
    # Força o navegador a fazer o cache por 1 dia (86400 segundos)
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.route('/usuarios', methods=['GET', 'POST'])
@admin_required
def gerenciar_usuarios():
    conn = get_db_connection()
    if request.method == 'POST':
        # 1. Pegamos os dados do formulário
        novo_nome = request.form.get('username') 
        senha_hash = generate_password_hash(request.form.get('password'))
        regra = request.form.get('role')
        email = request.form.get('email')

        try:
            # 2. Inserimos no banco
            cursor = conn.execute('INSERT INTO usuarios (username, password, role, email) VALUES (?, ?, ?, ?)', 
                                 (novo_nome, senha_hash, regra, email))
            novo_id = cursor.lastrowid # Pegamos o ID gerado agora
            conn.commit()

            # 3. O LOG CORRETO (Texto de criação e severidade SUCCESS)
            registrar_log(
                acao="👥 Novo usuário criado", 
                severidade="SUCCESS", 
                alvo_id=novo_id,
                detalhes=f"O usuário '{novo_nome}' foi adicionado ao sistema com ID {novo_id}."
            )
        except Exception as e:
            print(f"Erro ao criar: {e}")
            conn.rollback()

    users = conn.execute('SELECT * FROM usuarios').fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=users)

@app.route('/deletar_usuario/<int:id>')
@admin_required
def deletar_usuario(id):
    if id == 1: return redirect(url_for('gerenciar_usuarios'))
    
    conn = get_db_connection()
    # Busca o nome antes de deletar para o log não ficar vazio
    u = conn.execute('SELECT username FROM usuarios WHERE id=?', (id,)).fetchone()
    
    if u:
        conn.execute('DELETE FROM usuarios WHERE id=?', (id,))
        conn.commit()
        conn.close()
        # Log de exclusão funcionando corretamente
        registrar_log("🩻 Usuário apagado com sucesso", 
                    severidade="DANGER",  # O HTML vai ler isso e colocar a cor vermelha
                    detalhes=f"Usuário: {u['username']} | ID: {id}"
        )
    else:
        conn.close()
        
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/resetar_senha/<int:id>', methods=['POST'])
@admin_required
def resetar_senha(id):
    # Proteção para não resetar o admin principal a menos que seja ele mesmo
    if id == 1 and session.get('user_id') != 1: 
        return redirect(url_for('gerenciar_usuarios'))
    
    conn = get_db_connection()
    u = conn.execute('SELECT username FROM usuarios WHERE id = ?', (id,)).fetchone()
    
    if u:
        # 1. Atualiza a senha
        conn.execute('UPDATE usuarios SET password=?, reset_prio=1 WHERE id=?', 
                     (generate_password_hash("123456"), id))
        conn.commit()
        conn.close() # Fecha após o commit

        # 2. Prepara o nome para o log (Segurança extra)
        nome_exibicao = u['username'] if u else "Desconhecido"

        # 3. Registra o log (Corrigido: removi as aspas extras no final)
        registrar_log(
            acao="🔑 Senha resetada", 
            severidade="WARNING", 
            alvo_id=id, 
            detalhes=f"Usuário: {nome_exibicao} | ID: {id} - Senha padrão '123456' aplicada."
        )
    else:
        conn.close()
        
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/alterar_minha_senha', methods=['GET', 'POST'])
@admin_required
def alterar_minha_senha():
    # Segurança: Apenas o Administrador principal (ID 1) pode usar esta rota específica
    if session.get('user_id') != 1:
        registrar_log("⚠️ Tentativa não autorizada", "WARNING", detalhes="Usuário tentou acessar alteração de senha root")
        return redirect(url_for('gerenciar_usuarios', erro="Acesso negado."))

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar = request.form.get('confirmar_senha')

        if not nova_senha or nova_senha != confirmar:
            return render_template('trocar_senha_obrigatorio.html', erro="As senhas não coincidem.")

        if len(nova_senha) < 4:
            return render_template('trocar_senha_obrigatorio.html', erro="Senha muito curta (mínimo 4 caracteres).")

        senha_hash = generate_password_hash(nova_senha)
        conn = get_db_connection()
        conn.execute('UPDATE usuarios SET password = ?, reset_prio = 0 WHERE id = 1', (senha_hash,))
        conn.commit()
        conn.close()

        registrar_log("🔐 Senha root alterada", "CRITICAL")
        return redirect(url_for('gerenciar_usuarios', sucesso="Sua senha foi alterada com sucesso!"))

    return render_template('trocar_senha_obrigatorio.html')

@app.route('/central_downloads')
@admin_required
def central_downloads():
    # 1. Pegamos o nome do arquivo que o usuário quer baixar (se houver)
    arquivo_para_baixar = request.args.get('arquivo')

    # 2. Se não tem arquivo no pedido, apenas mostra a página com a lista
    if not arquivo_para_baixar:
        arquivos = [{"nome": "mural.db", "label": "Banco de Dados"}]
        if os.path.exists("historico_logs.txt"):
            arquivos.insert(0, {"nome": "historico_logs.txt", "label": "Histórico TXT (Legado)"})
        return render_template('downloads.html', arquivos=arquivos)

    # 3. Se chegou aqui, é porque o usuário clicou em baixar algo
    try:
        if arquivo_para_baixar in ["mural.db", "historico_logs.txt"]:
            # Definimos o ícone e severidade baseado no arquivo
            e_banco = arquivo_para_baixar == "mural.db"
            acao_txt = "🚨 BACKUP DO BANCO" if e_banco else "📄 DOWNLOAD LOG TXT"
            sev = "DANGER" if e_banco else "WARNING"

            registrar_log(
                acao=acao_txt,
                severidade=sev,
                detalhes=f"O administrador baixou o arquivo: {arquivo_para_baixar}"
            )
            
            return send_file(arquivo_para_baixar, as_attachment=True)
        else:
            return "Arquivo não permitido", 403

    except Exception as e:
        registrar_log(
            acao="❌ Falha no Download",
            severidade="WARNING",
            detalhes=f"Erro ao baixar {arquivo_para_baixar}: {str(e)}"
        )
        return f"Erro ao gerar download: {e}", 500

@app.route('/baixar_log/<path:nome_arquivo>') # Rota genérica para baixar arquivos da raiz
@admin_required
def baixar_log(nome_arquivo):
    if ".." in nome_arquivo or "/" in nome_arquivo: return "Erro", 400
    return send_file(nome_arquivo, as_attachment=True)
    
import csv
from io import StringIO
from flask import Response

@app.route('/baixar_auditoria')
@admin_required
def baixar_auditoria():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs ORDER BY id DESC').fetchall()
    conn.close()

    def generate():
        # 1. Adiciona o BOM para o Excel abrir com acentos corretos
        yield '\ufeff' 
        
        # 2. Criamos o formatador de CSV
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # 3. Cabeçalho Personalizado (O "Topo" que você pediu)
        writer.writerow([
            'DATA E HORA', 
            'NOME DO USUÁRIO', 
            'ID', 
            'AÇÃO REALIZADA', 
            'NÍVEL/SEVERIDADE', 
            'DETALHES TÉCNICOS', 
            'ENDEREÇO IP', 
            'DISPOSITIVO/NAVEGADOR'
        ])
        
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        # 4. Escreve os dados
        for log in logs:
            writer.writerow([
                log['data_hora'],
                log['usuario_nome'],
                f"ID: {log['usuario_id']}",
                log['acao'],
                log['severidade'],
                log['detalhes'] if log['detalhes'] else '---',
                log['ip_address'],
                log['user_agent']
            ])
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    # Retorna o arquivo formatado
    response = Response(generate(), mimetype='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=Auditoria_Sistema_Mural.csv"
    return response

@app.route('/backup_database')
@admin_required
def backup_database():
    return send_file("mural.db", as_attachment=True, download_name=f"backup_{datetime.now().strftime('%d%m%Y')}.db")

@app.route('/logout')
def logout():
    registrar_log("🚪 Saiu do sistema")
    session.clear()
    return redirect(url_for('login'))

@app.route('/configuracoes')
@admin_required
def configuracoes():
    conn = get_db_connection()
    c = conn.execute('SELECT * FROM configuracoes WHERE id=1').fetchone()
    conn.close()
    return render_template('configuracoes.html', config=c)

@app.route('/atualizar_configuracoes', methods=['POST'])
@admin_required
def atualizar_configuracoes():
    n = request.form.get('nome_escola')
    t = request.form.get('tempo_transicao')
    conn = get_db_connection()
    conn.execute('UPDATE configuracoes SET nome_escola=?, tempo_transicao=? WHERE id=1', (n, t))
    conn.commit()
    conn.close()
    registrar_log("⚙️Atualizou os Configurações do Mural", detalhes=f"Nome: {n} / Tempo: {t}")
    return redirect(url_for('configuracoes'))

@app.route('/templates_static/<path:filename>')
def templates_static(filename):
    # Usa a pasta de templates que você já configurou lá em cima
    return send_from_directory('templates', filename)

@app.route('/sounds/<path:filename>')
def servir_sounds(filename):
    return send_from_directory('sounds', filename)
    
@app.route('/reordenar', methods=['POST'])
@login_required
def reordenar():
    try:
        dados = request.get_json()
        nova_ordem = dados.get('ordem') # Lista de IDs vinda do SortableJS

        if nova_ordem:
            conn = get_db_connection()
            for posicao, item_id in enumerate(nova_ordem):
                conn.execute('UPDATE midias SET ordem = ? WHERE id = ?', (posicao, item_id))
            conn.commit()

            # --- ADICIONADO: Registro de Logs e Auditoria ---
            usuario_id = session.get('user_id')
            
            # Pega o nome do usuário no banco se não estiver salvo na session
            user_row = conn.execute('SELECT nome FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
            usuario_nome = user_row['nome'] if user_row else "Desconhecido"
            
            acao = "Ordem da mídia alterada"
            detalhes = f"A sequência de exibição de {len(nova_ordem)} itens foi reorganizada no mural."
            severidade = "INFO"
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            
            # Formato de data/hora padrão que você usa no sistema (ex: YYYY-MM-DD HH:MM:SS)
            from datetime import datetime
            data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Insere na tabela de logs (ajuste o nome da tabela se for diferente no seu banco, ex: 'logs' ou 'historico_logs')
            conn.execute('''
                INSERT INTO logs (data_hora, usuario_id, usuario_nome, acao, severidade, ip_address, user_agent, detalhes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data_hora, usuario_id, usuario_nome, acao, severidade, ip_address, user_agent, detalhes))
            
            conn.commit()
            # -----------------------------------------------

            conn.close()
            return jsonify({"status": "sucesso"}), 200
            
        return jsonify({"status": "erro"}), 400
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
if __name__ == '__main__':
    init_db()

    # --- CONFIGURAÇÃO DE REDE INTERNA (rodando atrás do IIS/ARR) ---
    IP_ESTATICO = "192.168.1.120"            # IP da VM Windows 10
    PORTA = 5000                             # Porta interna do app
    DOMINIO = "mural.eanig.net"              # Seu domínio

    import os
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    print("\n" + "═"*60)
    print(f"🚀 MURAL DIGITAL {VERSION} - {EDITION}")
    print(f"🔗 EXTERNO (via IIS): https://{DOMINIO}")
    print(f"🌐 PROXY LOCAL: http://127.0.0.1:{PORTA}")
    print("═"*60)
    print(f"📡 Aguardando conexões internas na porta {PORTA}...\n")

    # Servidor WSGI (waitress) escutando apenas local (IIS fica na frente)
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=PORTA, threads=10)
    except Exception as e:
        print(f"\n❌ ERRO NA PORTA {PORTA}: {e}")
        print("Tentando porta alternativa 5050...")
        serve(app, host='127.0.0.1', port=5050, threads=10)