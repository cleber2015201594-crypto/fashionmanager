import streamlit as st
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import csv
from io import StringIO
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gestão",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para conexão com PostgreSQL
def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Parse da URL do PostgreSQL
        urllib.parse.uses_netloc.append("postgres")
        url = urllib.parse.urlparse(database_url)
        
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            sslmode='require'
        )
        return conn
    else:
        # Fallback para SQLite local (desenvolvimento)
        import sqlite3
        return sqlite3.connect('gestao.db')

# Função para obter data/hora do Brasil
def get_brasil_datetime():
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    return datetime.now(tz_brasil)

# Função para formatar data no padrão BR
def format_date_br(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            return dt
    return dt.strftime("%d/%m/%Y %H:%M")

# Sistema de Autenticação
def init_db():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            
            # Tabela de usuários
            c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                         (id SERIAL PRIMARY KEY,
                          username TEXT UNIQUE,
                          password TEXT,
                          nivel TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Tabela de clientes
            c.execute('''CREATE TABLE IF NOT EXISTS clientes
                         (id SERIAL PRIMARY KEY,
                          nome TEXT NOT NULL,
                          telefone TEXT,
                          email TEXT,
                          cpf TEXT,
                          endereco TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Tabela de escolas
            c.execute('''CREATE TABLE IF NOT EXISTS escolas
                         (id SERIAL PRIMARY KEY,
                          nome TEXT,
                          telefone TEXT,
                          email TEXT,
                          endereco TEXT,
                          responsavel TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Tabela de produtos
            c.execute('''CREATE TABLE IF NOT EXISTS produtos
                         (id SERIAL PRIMARY KEY,
                          nome TEXT NOT NULL,
                          descricao TEXT,
                          preco DECIMAL(10,2),
                          custo DECIMAL(10,2),
                          estoque_minimo INTEGER,
                          tamanho TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          UNIQUE(nome, tamanho))''')
            
            # Tabela de estoque por escola
            c.execute('''CREATE TABLE IF NOT EXISTS estoque_escolas
                         (id SERIAL PRIMARY KEY,
                          escola_id INTEGER REFERENCES escolas(id),
                          produto_id INTEGER REFERENCES produtos(id),
                          quantidade INTEGER DEFAULT 0,
                          UNIQUE(escola_id, produto_id))''')
            
            # Tabela de pedidos
            c.execute('''CREATE TABLE IF NOT EXISTS pedidos
                         (id SERIAL PRIMARY KEY,
                          cliente_id INTEGER REFERENCES clientes(id),
                          escola_id INTEGER REFERENCES escolas(id),
                          status TEXT DEFAULT 'Pendente',
                          total DECIMAL(10,2),
                          desconto DECIMAL(5,2) DEFAULT 0,
                          custo_total DECIMAL(10,2),
                          lucro_total DECIMAL(10,2),
                          margem_lucro DECIMAL(5,2),
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Tabela de itens do pedido
            c.execute('''CREATE TABLE IF NOT EXISTS itens_pedido
                         (id SERIAL PRIMARY KEY,
                          pedido_id INTEGER REFERENCES pedidos(id),
                          produto_id INTEGER REFERENCES produtos(id),
                          quantidade INTEGER,
                          preco_unitario DECIMAL(10,2),
                          custo_unitario DECIMAL(10,2),
                          lucro_unitario DECIMAL(10,2),
                          margem_lucro DECIMAL(5,2))''')
            
            # Inserir usuário admin padrão se não existir
            c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
            if c.fetchone()[0] == 0:
                senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
                c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (%s, %s, %s)",
                         ('admin', senha_hash, 'admin'))
            
            conn.commit()
            c.close()
            
        else:
            # SQLite para desenvolvimento
            c = conn.cursor()
            
            c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE,
                          password TEXT,
                          nivel TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS clientes
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          nome TEXT NOT NULL,
                          telefone TEXT,
                          email TEXT,
                          cpf TEXT,
                          endereco TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS escolas
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          nome TEXT,
                          telefone TEXT,
                          email TEXT,
                          endereco TEXT,
                          responsavel TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS produtos
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          nome TEXT NOT NULL,
                          descricao TEXT,
                          preco REAL,
                          custo REAL,
                          estoque_minimo INTEGER,
                          tamanho TEXT,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          UNIQUE(nome, tamanho))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS estoque_escolas
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          escola_id INTEGER,
                          produto_id INTEGER,
                          quantidade INTEGER DEFAULT 0,
                          FOREIGN KEY(escola_id) REFERENCES escolas(id),
                          FOREIGN KEY(produto_id) REFERENCES produtos(id),
                          UNIQUE(escola_id, produto_id))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS pedidos
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          cliente_id INTEGER,
                          escola_id INTEGER,
                          status TEXT DEFAULT 'Pendente',
                          total REAL,
                          desconto REAL DEFAULT 0,
                          custo_total REAL,
                          lucro_total REAL,
                          margem_lucro REAL,
                          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                          FOREIGN KEY(escola_id) REFERENCES escolas(id))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS itens_pedido
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          pedido_id INTEGER,
                          produto_id INTEGER,
                          quantidade INTEGER,
                          preco_unitario REAL,
                          custo_unitario REAL,
                          lucro_unitario REAL,
                          margem_lucro REAL,
                          FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
                          FOREIGN KEY(produto_id) REFERENCES produtos(id))''')
            
            c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
            if c.fetchone()[0] == 0:
                senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
                c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (?, ?, ?)",
                         ('admin', senha_hash, 'admin'))
            
            conn.commit()
            
    except Exception as e:
        st.error(f"Erro ao inicializar banco de dados: {e}")
    finally:
        conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute("SELECT * FROM usuarios WHERE username=%s", (username,))
            user = c.fetchone()
        else:
            c = conn.cursor()
            c.execute("SELECT * FROM usuarios WHERE username=?", (username,))
            user = c.fetchone()
        
        if user and user[2] == hash_password(password):
            return user
        return None
    except Exception as e:
        st.error(f"Erro ao verificar login: {e}")
        return None
    finally:
        conn.close()

# Funções de Gestão de Clientes
def add_cliente(nome, telefone, email, cpf, endereco):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute('''INSERT INTO clientes (nome, telefone, email, cpf, endereco)
                         VALUES (%s, %s, %s, %s, %s)''', 
                     (nome, telefone, email, cpf, endereco))
        else:
            c = conn.cursor()
            c.execute('''INSERT INTO clientes (nome, telefone, email, cpf, endereco)
                         VALUES (?, ?, ?, ?, ?)''', 
                     (nome, telefone, email, cpf, endereco))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao cadastrar cliente: {e}")
        return False
    finally:
        conn.close()

def get_clientes():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute("SELECT * FROM clientes ORDER BY nome")
        else:
            c = conn.cursor()
            c.execute("SELECT * FROM clientes ORDER BY nome")
        
        clientes = c.fetchall()
        return clientes
    except Exception as e:
        st.error(f"Erro ao buscar clientes: {e}")
        return []
    finally:
        conn.close()

# Funções de Gestão de Escolas
def add_escola(nome, telefone, email, endereco, responsavel):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute('''INSERT INTO escolas (nome, telefone, email, endereco, responsavel)
                         VALUES (%s, %s, %s, %s, %s)''', 
                     (nome, telefone, email, endereco, responsavel))
        else:
            c = conn.cursor()
            c.execute('''INSERT INTO escolas (nome, telefone, email, endereco, responsavel)
                         VALUES (?, ?, ?, ?, ?)''', 
                     (nome, telefone, email, endereco, responsavel))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao cadastrar escola: {e}")
        return False
    finally:
        conn.close()

def get_escolas():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute("SELECT * FROM escolas ORDER BY nome")
        else:
            c = conn.cursor()
            c.execute("SELECT * FROM escolas ORDER BY nome")
        
        escolas = c.fetchall()
        return escolas
    except Exception as e:
        st.error(f"Erro ao buscar escolas: {e}")
        return []
    finally:
        conn.close()

# Funções de Gestão de Produtos
def add_produto(nome, descricao, preco, custo, estoque_minimo, tamanho):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            # Verificar se produto já existe
            c.execute("SELECT id FROM produtos WHERE nome=%s AND tamanho=%s", (nome, tamanho))
            if c.fetchone():
                return False, "Já existe um produto com este nome e tamanho"
            
            c.execute('''INSERT INTO produtos (nome, descricao, preco, custo, estoque_minimo, tamanho)
                         VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''', 
                     (nome, descricao, preco, custo, estoque_minimo, tamanho))
            produto_id = c.fetchone()[0]
        else:
            c = conn.cursor()
            c.execute("SELECT id FROM produtos WHERE nome=? AND tamanho=?", (nome, tamanho))
            if c.fetchone():
                return False, "Já existe um produto com este nome e tamanho"
            
            c.execute('''INSERT INTO produtos (nome, descricao, preco, custo, estoque_minimo, tamanho)
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                     (nome, descricao, preco, custo, estoque_minimo, tamanho))
            produto_id = c.lastrowid
        
        conn.commit()
        return True, produto_id
    except Exception as e:
        conn.rollback()
        error_msg = f"Erro ao cadastrar produto: {e}"
        st.error(error_msg)
        return False, error_msg
    finally:
        conn.close()

def get_produtos():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute("SELECT * FROM produtos ORDER BY nome, tamanho")
        else:
            c = conn.cursor()
            c.execute("SELECT * FROM produtos ORDER BY nome, tamanho")
        
        produtos = c.fetchall()
        return produtos
    except Exception as e:
        st.error(f"Erro ao buscar produtos: {e}")
        return []
    finally:
        conn.close()

# Funções de Gestão de Estoque
def vincular_produto_todas_escolas(produto_id, quantidade_inicial=0):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        escolas = get_escolas()
        if is_postgres:
            c = conn.cursor()
            for escola in escolas:
                c.execute('''INSERT INTO estoque_escolas (escola_id, produto_id, quantidade)
                             VALUES (%s, %s, %s)
                             ON CONFLICT (escola_id, produto_id) DO NOTHING''', 
                         (escola[0], produto_id, quantidade_inicial))
        else:
            c = conn.cursor()
            for escola in escolas:
                c.execute('''INSERT OR IGNORE INTO estoque_escolas (escola_id, produto_id, quantidade)
                             VALUES (?, ?, ?)''', 
                         (escola[0], produto_id, quantidade_inicial))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao vincular produto: {e}")
        return False
    finally:
        conn.close()

def get_estoque_escola(escola_id):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute('''SELECT e.id, p.nome, p.tamanho, e.quantidade, p.estoque_minimo, 
                                p.preco, p.custo, p.id as produto_id
                         FROM estoque_escolas e
                         JOIN produtos p ON e.produto_id = p.id
                         WHERE e.escola_id = %s
                         ORDER BY p.nome, p.tamanho''', (escola_id,))
        else:
            c = conn.cursor()
            c.execute('''SELECT e.id, p.nome, p.tamanho, e.quantidade, p.estoque_minimo, 
                                p.preco, p.custo, p.id as produto_id
                         FROM estoque_escolas e
                         JOIN produtos p ON e.produto_id = p.id
                         WHERE e.escola_id = ?
                         ORDER BY p.nome, p.tamanho''', (escola_id,))
        
        estoque = c.fetchall()
        return estoque
    except Exception as e:
        st.error(f"Erro ao buscar estoque: {e}")
        return []
    finally:
        conn.close()

def update_estoque_escola(escola_id, produto_id, quantidade):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute('''INSERT INTO estoque_escolas (escola_id, produto_id, quantidade)
                         VALUES (%s, %s, %s)
                         ON CONFLICT (escola_id, produto_id) 
                         DO UPDATE SET quantidade = EXCLUDED.quantidade''', 
                     (escola_id, produto_id, quantidade))
        else:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO estoque_escolas (escola_id, produto_id, quantidade)
                         VALUES (?, ?, ?)''', 
                     (escola_id, produto_id, quantidade))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar estoque: {e}")
        return False
    finally:
        conn.close()

# Funções de Gestão de Pedidos
def add_pedido(cliente_id, escola_id, itens, desconto=0):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        # Calcular totais
        total_venda = sum(item['quantidade'] * item['preco'] for item in itens)
        total_custo = sum(item['quantidade'] * item['custo'] for item in itens)
        total_com_desconto = total_venda - (total_venda * desconto / 100)
        lucro_total = total_com_desconto - total_custo
        margem_lucro = (lucro_total / total_com_desconto * 100) if total_com_desconto > 0 else 0
        
        if is_postgres:
            c = conn.cursor()
            # Inserir pedido
            c.execute('''INSERT INTO pedidos (cliente_id, escola_id, total, desconto, custo_total, lucro_total, margem_lucro)
                         VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id''', 
                     (cliente_id, escola_id, total_com_desconto, desconto, total_custo, lucro_total, margem_lucro))
            pedido_id = c.fetchone()[0]
            
            # Inserir itens e atualizar estoque
            for item in itens:
                lucro_unitario = item['preco'] - item['custo']
                margem_unitario = (lucro_unitario / item['preco'] * 100) if item['preco'] > 0 else 0
                
                c.execute('''INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, custo_unitario, lucro_unitario, margem_lucro)
                             VALUES (%s, %s, %s, %s, %s, %s, %s)''', 
                         (pedido_id, item['produto_id'], item['quantidade'], item['preco'], item['custo'], lucro_unitario, margem_unitario))
                
                # Atualizar estoque
                c.execute('''UPDATE estoque_escolas 
                             SET quantidade = quantidade - %s
                             WHERE escola_id = %s AND produto_id = %s''', 
                         (item['quantidade'], escola_id, item['produto_id']))
        else:
            c = conn.cursor()
            c.execute('''INSERT INTO pedidos (cliente_id, escola_id, total, desconto, custo_total, lucro_total, margem_lucro)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                     (cliente_id, escola_id, total_com_desconto, desconto, total_custo, lucro_total, margem_lucro))
            pedido_id = c.lastrowid
            
            for item in itens:
                lucro_unitario = item['preco'] - item['custo']
                margem_unitario = (lucro_unitario / item['preco'] * 100) if item['preco'] > 0 else 0
                
                c.execute('''INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, custo_unitario, lucro_unitario, margem_lucro)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                         (pedido_id, item['produto_id'], item['quantidade'], item['preco'], item['custo'], lucro_unitario, margem_unitario))
                
                c.execute('''UPDATE estoque_escolas 
                             SET quantidade = quantidade - ?
                             WHERE escola_id = ? AND produto_id = ?''', 
                         (item['quantidade'], escola_id, item['produto_id']))
        
        conn.commit()
        return pedido_id
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao criar pedido: {e}")
        return None
    finally:
        conn.close()

def get_pedidos():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute('''SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome 
                         FROM pedidos p
                         LEFT JOIN clientes c ON p.cliente_id = c.id
                         LEFT JOIN escolas e ON p.escola_id = e.id
                         ORDER BY p.criado_em DESC''')
        else:
            c = conn.cursor()
            c.execute('''SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome 
                         FROM pedidos p
                         LEFT JOIN clientes c ON p.cliente_id = c.id
                         LEFT JOIN escolas e ON p.escola_id = e.id
                         ORDER BY p.criado_em DESC''')
        
        pedidos = c.fetchall()
        return pedidos
    except Exception as e:
        st.error(f"Erro ao buscar pedidos: {e}")
        return []
    finally:
        conn.close()

def update_pedido_status(pedido_id, novo_status):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute("UPDATE pedidos SET status = %s WHERE id = %s", (novo_status, pedido_id))
        else:
            c = conn.cursor()
            c.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar status: {e}")
        return False
    finally:
        conn.close()

# Funções de Gestão de Usuários
def add_usuario(username, password, nivel):
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        senha_hash = hash_password(password)
        if is_postgres:
            c = conn.cursor()
            c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (%s, %s, %s)",
                     (username, senha_hash, nivel))
        else:
            c = conn.cursor()
            c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (?, ?, ?)",
                     (username, senha_hash, nivel))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao criar usuário: {e}")
        return False
    finally:
        conn.close()

def get_usuarios():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute("SELECT id, username, nivel, criado_em FROM usuarios ORDER BY username")
        else:
            c = conn.cursor()
            c.execute("SELECT id, username, nivel, criado_em FROM usuarios ORDER BY username")
        
        usuarios = c.fetchall()
        return usuarios
    except Exception as e:
        st.error(f"Erro ao buscar usuários: {e}")
        return []
    finally:
        conn.close()

# Sistema de IA
def previsao_vendas():
    # Simulação de previsão
    meses = ['Próximo Mês', '2° Mês', '3° Mês', '4° Mês', '5° Mês', '6° Mês']
    vendas = [12000, 15000, 18000, 22000, 25000, 29000]
    return meses, vendas

def alertas_estoque():
    conn = get_db_connection()
    is_postgres = 'psycopg2' in str(type(conn))
    
    try:
        if is_postgres:
            c = conn.cursor()
            c.execute('''SELECT e.escola_id, esc.nome as escola_nome, p.nome as produto_nome, p.tamanho,
                                e.quantidade, p.estoque_minimo
                         FROM estoque_escolas e
                         JOIN produtos p ON e.produto_id = p.id
                         JOIN escolas esc ON e.escola_id = esc.id
                         WHERE e.quantidade <= p.estoque_minimo''')
        else:
            c = conn.cursor()
            c.execute('''SELECT e.escola_id, esc.nome as escola_nome, p.nome as produto_nome, p.tamanho,
                                e.quantidade, p.estoque_minimo
                         FROM estoque_escolas e
                         JOIN produtos p ON e.produto_id = p.id
                         JOIN escolas esc ON e.escola_id = esc.id
                         WHERE e.quantidade <= p.estoque_minimo''')
        
        alertas = c.fetchall()
        return alertas
    except Exception as e:
        st.error(f"Erro ao buscar alertas: {e}")
        return []
    finally:
        conn.close()

# Interface Principal
def main():
    init_db()
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.user:
        show_login()
    else:
        show_main_app()

def show_login():
    st.title("🔐 Sistema de Gestão - Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            user = verify_login(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def show_main_app():
    st.sidebar.title(f"👋 Bem-vindo, {st.session_state.user[1]}")
    st.sidebar.write(f"**Nível:** {st.session_state.user[3]}")
    st.sidebar.write(f"**Data:** {format_date_br(get_brasil_datetime())}")
    
    # Menu lateral
    menu_options = ["📊 Dashboard", "👥 Gestão de Clientes", "🏫 Gestão de Escolas", 
                   "📦 Gestão de Produtos", "📦 Sistema de Pedidos", "📈 Relatórios", "🤖 Sistema A.I."]
    
    if st.session_state.user[3] == 'admin':
        menu_options.append("🔐 Administração")
    
    choice = st.sidebar.selectbox("Navegação", menu_options)
    
    if choice == "📊 Dashboard":
        show_dashboard()
    elif choice == "👥 Gestão de Clientes":
        show_client_management()
    elif choice == "🏫 Gestão de Escolas":
        show_school_management()
    elif choice == "📦 Gestão de Produtos":
        show_product_management()
    elif choice == "📦 Sistema de Pedidos":
        show_order_management()
    elif choice == "📈 Relatórios":
        show_reports()
    elif choice == "🤖 Sistema A.I.":
        show_ai_system()
    elif choice == "🔐 Administração":
        show_admin_panel()
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.user = None
        st.rerun()

def show_dashboard():
    st.title("📊 Dashboard Principal")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        clientes = get_clientes()
        st.metric("Total de Clientes", len(clientes))
    
    with col2:
        escolas = get_escolas()
        st.metric("Escolas Parceiras", len(escolas))
    
    with col3:
        pedidos = get_pedidos()
        st.metric("Pedidos Realizados", len(pedidos))
    
    with col4:
        total_vendas = sum(pedido[4] for pedido in pedidos)
        st.metric("Faturamento Total", f"R$ {total_vendas:,.2f}")

def show_client_management():
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2 = st.tabs(["Cadastrar Cliente", "Lista de Clientes"])
    
    with tab1:
        st.subheader("Novo Cliente")
        with st.form("novo_cliente"):
            nome = st.text_input("Nome Completo *")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            cpf = st.text_input("CPF (Opcional)")
            endereco = st.text_area("Endereço")
            
            if st.form_submit_button("Cadastrar Cliente"):
                if nome:
                    if add_cliente(nome, telefone, email, cpf, endereco):
                        st.success("Cliente cadastrado com sucesso!")
                    else:
                        st.error("Erro ao cadastrar cliente")
                else:
                    st.error("Nome é obrigatório")
    
    with tab2:
        st.subheader("Lista de Clientes")
        clientes = get_clientes()
        
        for cliente in clientes:
            with st.expander(f"{cliente[1]} - {cliente[4] or 'Sem CPF'}"):
                st.write(f"**Telefone:** {cliente[2]}")
                st.write(f"**Email:** {cliente[3]}")
                st.write(f"**Endereço:** {cliente[5]}")
                st.write(f"**Cadastrado em:** {format_date_br(cliente[6])}")

def show_school_management():
    st.title("🏫 Gestão de Escolas")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Escola", "Lista de Escolas", "Estoque por Escola"])
    
    with tab1:
        st.subheader("Nova Escola Parceira")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola *")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            endereco = st.text_area("Endereço")
            responsavel = st.text_input("Responsável")
            
            if st.form_submit_button("Cadastrar Escola"):
                if nome:
                    if add_escola(nome, telefone, email, endereco, responsavel):
                        st.success("Escola cadastrada com sucesso!")
                    else:
                        st.error("Erro ao cadastrar escola")
                else:
                    st.error("Nome da escola é obrigatório")
    
    with tab2:
        st.subheader("Escolas Parceiras")
        escolas = get_escolas()
        
        for escola in escolas:
            with st.expander(f"{escola[1]}"):
                st.write(f"**Telefone:** {escola[2]}")
                st.write(f"**Email:** {escola[3]}")
                st.write(f"**Endereço:** {escola[4]}")
                st.write(f"**Responsável:** {escola[5]}")
                st.write(f"**Cadastrado em:** {format_date_br(escola[6])}")
    
    with tab3:
        st.subheader("Estoque por Escola")
        escolas = get_escolas()
        produtos = get_produtos()
        
        if not escolas:
            st.warning("Nenhuma escola cadastrada. Cadastre uma escola primeiro.")
            return
            
        if not produtos:
            st.warning("Nenhum produto cadastrado. Cadastre produtos primeiro.")
            return
        
        escola_selecionada = st.selectbox("Selecione a Escola", 
                                         [f"{e[0]} - {e[1]}" for e in escolas])
        
        if escola_selecionada:
            escola_id = int(escola_selecionada.split(' - ')[0])
            escola_nome = escola_selecionada.split(' - ')[1]
            
            st.write(f"### Estoque da Escola: {escola_nome}")
            
            # Mostrar estoque atual
            estoque = get_estoque_escola(escola_id)
            
            if not estoque:
                st.info("Nenhum produto vinculado a esta escola ainda.")
            else:
                for item in estoque:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{item[1]}** - Tamanho: {item[2]}")
                    with col2:
                        st.write(f"**Estoque:** {item[3]}")
                    with col3:
                        if item[3] <= item[4]:
                            st.error(f"⚠️ Mín: {item[4]}")
                        else:
                            st.success(f"✅ Mín: {item[4]}")
            
            st.markdown("---")
            st.subheader("Ajustar Estoque")
            
            # Formulário para ajustar estoque
            produto_ajuste = st.selectbox("Selecione o Produto", 
                                         [f"{p[0]} - {p[1]} ({p[6]})" for p in produtos])
            
            if produto_ajuste:
                produto_id = int(produto_ajuste.split(' - ')[0])
                
                # Buscar quantidade atual
                estoque_atual = 0
                for item in estoque:
                    if item[7] == produto_id:
                        estoque_atual = item[3]
                        break
                
                nova_quantidade = st.number_input("Nova quantidade", 
                                                 min_value=0, 
                                                 value=estoque_atual,
                                                 key=f"ajuste_{produto_id}")
                
                if st.button("Atualizar Estoque", key=f"btn_ajuste_{produto_id}"):
                    if update_estoque_escola(escola_id, produto_id, nova_quantidade):
                        st.success(f"Estoque atualizado para {nova_quantidade}!")
                        st.rerun()

def show_product_management():
    st.title("📦 Gestão de Produtos")
    
    tab1, tab2 = st.tabs(["Cadastrar Produto", "Lista de Produtos"])
    
    with tab1:
        st.subheader("Novo Produto")
        with st.form("novo_produto"):
            nome = st.text_input("Nome do Produto *")
            descricao = st.text_area("Descrição")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                preco = st.number_input("Preço de Venda (R$)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                custo = st.number_input("Custo (R$)", min_value=0.0, value=0.0, step=0.01)
            with col3:
                estoque_minimo = st.number_input("Estoque Mínimo", min_value=0, value=5)
            with col4:
                # Tamanhos padronizados
                tamanhos = ["", "PP", "P", "M", "G", "GG", "EXG", "2", "4", "6", "8", "10", "12", "Único"]
                tamanho = st.selectbox("Tamanho *", tamanhos)
            
            # Opção para vincular automaticamente às escolas
            escolas = get_escolas()
            if escolas:
                vincular_escolas = st.checkbox("Vincular este produto a todas as escolas automaticamente", value=True)
                estoque_inicial = st.number_input("Estoque inicial nas escolas", min_value=0, value=0)
            else:
                st.warning("Cadastre escolas primeiro para vincular produtos")
                vincular_escolas = False
                estoque_inicial = 0
            
            if st.form_submit_button("Cadastrar Produto"):
                if nome and preco > 0 and tamanho:
                    sucesso, resultado = add_produto(nome, descricao, preco, custo, estoque_minimo, tamanho)
                    
                    if sucesso:
                        st.success("Produto cadastrado com sucesso!")
                        
                        # Vincular automaticamente às escolas
                        if vincular_escolas and escolas:
                            produto_id = resultado
                            if vincular_produto_todas_escolas(produto_id, estoque_inicial):
                                st.success(f"Produto vinculado automaticamente a {len(escolas)} escolas!")
                        
                        # Calcular margem
                        if preco > 0 and custo > 0:
                            margem = ((preco - custo) / preco) * 100
                            st.info(f"Margem de lucro: {margem:.1f}%")
                    else:
                        st.error(resultado)
                else:
                    st.error("Nome, preço e tamanho são obrigatórios")
    
    with tab2:
        st.subheader("Lista de Produtos")
        produtos = get_produtos()
        
        for produto in produtos:
            with st.expander(f"{produto[1]} - Tamanho: {produto[6]} - R$ {produto[3]:.2f}"):
                st.write(f"**Descrição:** {produto[2]}")
                st.write(f"**Preço:** R$ {produto[3]:.2f}")
                st.write(f"**Custo:** R$ {produto[4]:.2f}")
                st.write(f"**Estoque Mínimo:** {produto[5]}")
                
                # Calcular margem
                if produto[3] > 0 and produto[4] > 0:
                    margem = ((produto[3] - produto[4]) / produto[3]) * 100
                    lucro_unitario = produto[3] - produto[4]
                    st.write(f"**Margem:** {margem:.1f}%")
                    st.write(f"**Lucro Unitário:** R$ {lucro_unitario:.2f}")

def show_order_management():
    st.title("📦 Sistema de Pedidos")
    
    tab1, tab2 = st.tabs(["Novo Pedido", "Histórico de Pedidos"])
    
    with tab1:
        st.subheader("Criar Novo Pedido")
        
        clientes = get_clientes()
        escolas = get_escolas()
        produtos = get_produtos()
        
        if not clientes:
            st.warning("Cadastre clientes primeiro para criar pedidos")
            return
            
        if not escolas:
            st.warning("Cadastre escolas primeiro para criar pedidos")
            return
            
        if not produtos:
            st.warning("Cadastre produtos primeiro para criar pedidos")
            return
        
        with st.form("novo_pedido"):
            col1, col2 = st.columns(2)
            
            with col1:
                cliente_selecionado = st.selectbox("Cliente *", 
                                                  [f"{c[0]} - {c[1]}" for c in clientes])
                escola_selecionada = st.selectbox("Escola *", 
                                                 [f"{e[0]} - {e[1]}" for e in escolas])
                desconto = st.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=0.0)
            
            st.subheader("Itens do Pedido")
            
            itens = []
            if escola_selecionada:
                escola_id = int(escola_selecionada.split(' - ')[0])
                estoque_escola = get_estoque_escola(escola_id)
            
            for i in range(3):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    # Mostrar apenas produtos com estoque
                    produtos_com_estoque = []
                    for produto in produtos:
                        estoque_disponivel = 0
                        for item in estoque_escola:
                            if item[7] == produto[0]:
                                estoque_disponivel = item[3]
                                break
                        
                        if estoque_disponivel > 0:
                            produtos_com_estoque.append(produto)
                    
                    if produtos_com_estoque:
                        produto_opcoes = [f"{p[0]} - {p[1]} ({p[6]}) - Estoque: {next((item[3] for item in estoque_escola if item[7] == p[0]), 0)}" 
                                         for p in produtos_com_estoque]
                        produto_selecionado = st.selectbox(f"Produto {i+1}", [""] + produto_opcoes, key=f"prod_{i}")
                    else:
                        st.warning("Nenhum produto com estoque")
                        produto_selecionado = None
                
                with col2:
                    if produto_selecionado:
                        produto_id = int(produto_selecionado.split(' - ')[0])
                        estoque_disponivel = next((item[3] for item in estoque_escola if item[7] == produto_id), 0)
                        quantidade = st.number_input(f"Qtd {i+1}", min_value=1, max_value=estoque_disponivel, value=1, key=f"qtd_{i}")
                    else:
                        quantidade = 0
                
                with col3:
                    if produto_selecionado:
                        produto_info = next(p for p in produtos if p[0] == produto_id)
                        preco = st.number_input(f"Preço {i+1}", min_value=0.0, value=float(produto_info[3]), key=f"preco_{i}")
                        custo = produto_info[4]
                    else:
                        preco = 0.0
                        custo = 0.0
                
                with col4:
                    if produto_selecionado and preco > 0 and custo > 0:
                        lucro_unitario = preco - custo
                        margem = (lucro_unitario / preco * 100) if preco > 0 else 0
                        st.write(f"Margem: {margem:.1f}%")
                
                if produto_selecionado and quantidade > 0:
                    itens.append({
                        'produto_id': produto_id,
                        'quantidade': quantidade,
                        'preco': preco,
                        'custo': custo
                    })
            
            # Resumo do pedido
            if itens:
                st.subheader("Resumo do Pedido")
                total_venda = sum(item['quantidade'] * item['preco'] for item in itens)
                total_custo = sum(item['quantidade'] * item['custo'] for item in itens)
                total_com_desconto = total_venda - (total_venda * desconto / 100)
                lucro_total = total_com_desconto - total_custo
                margem_lucro = (lucro_total / total_com_desconto * 100) if total_com_desconto > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Venda", f"R$ {total_venda:.2f}")
                with col2:
                    st.metric("Total com Desconto", f"R$ {total_com_desconto:.2f}")
                with col3:
                    st.metric("Lucro Total", f"R$ {lucro_total:.2f}")
                with col4:
                    st.metric("Margem", f"{margem_lucro:.1f}%")
            
            if st.form_submit_button("Criar Pedido"):
                if not itens:
                    st.error("Adicione pelo menos um item ao pedido")
                else:
                    cliente_id = int(cliente_selecionado.split(' - ')[0])
                    escola_id = int(escola_selecionada.split(' - ')[0])
                    
                    pedido_id = add_pedido(cliente_id, escola_id, itens, desconto)
                    if pedido_id:
                        st.success(f"Pedido #{pedido_id} criado com sucesso!")
    
    with tab2:
        st.subheader("Histórico de Pedidos")
        pedidos = get_pedidos()
        
        for pedido in pedidos:
            with st.expander(f"Pedido #{pedido[0]} - {pedido[10]} - R$ {pedido[4]:.2f} - {pedido[3]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Cliente:** {pedido[10]}")
                    st.write(f"**Escola:** {pedido[11]}")
                    st.write(f"**Status:** {pedido[3]}")
                    st.write(f"**Data:** {format_date_br(pedido[9])}")
                with col2:
                    st.write(f"**Total:** R$ {pedido[4]:.2f}")
                    st.write(f"**Desconto:** {pedido[5]}%")
                    st.write(f"**Custo Total:** R$ {pedido[6]:.2f}")
                    st.write(f"**Lucro:** R$ {pedido[7]:.2f}")
                    st.write(f"**Margem:** {pedido[8]:.1f}%")
                
                # Botões para alterar status
                st.write("**Alterar Status:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Confirmar", key=f"confirm_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Confirmado")
                        st.rerun()
                with col2:
                    if st.button("🚚 Enviar", key=f"enviar_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Enviado")
                        st.rerun()
                with col3:
                    if st.button("📦 Entregue", key=f"entregue_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Entregue")
                        st.rerun()
                with col4:
                    if st.button("❌ Cancelar", key=f"cancelar_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Cancelado")
                        st.rerun()

def show_reports():
    st.title("📈 Relatórios e Análises")
    
    tab1, tab2 = st.tabs(["Exportar Dados", "Análise Financeira"])
    
    with tab1:
        st.subheader("Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Exportar Clientes CSV"):
                clientes = get_clientes()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nome', 'Telefone', 'Email', 'CPF', 'Endereço', 'Data_Criacao'])
                for cliente in clientes:
                    writer.writerow(cliente)
                st.download_button("Baixar CSV", output.getvalue(), "clientes.csv", "text/csv")
        
        with col2:
            if st.button("Exportar Pedidos CSV"):
                pedidos = get_pedidos()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Cliente_ID', 'Escola_ID', 'Status', 'Total', 'Desconto', 'Custo_Total', 'Lucro_Total', 'Margem_Lucro', 'Data', 'Cliente_Nome', 'Escola_Nome'])
                for pedido in pedidos:
                    writer.writerow(pedido)
                st.download_button("Baixar CSV", output.getvalue(), "pedidos.csv", "text/csv")
        
        with col3:
            if st.button("Exportar Produtos CSV"):
                produtos = get_produtos()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nome', 'Descricao', 'Preco', 'Custo', 'Estoque_Minimo', 'Tamanho', 'Data_Criacao'])
                for produto in produtos:
                    writer.writerow(produto)
                st.download_button("Baixar CSV", output.getvalue(), "produtos.csv", "text/csv")

def show_ai_system():
    st.title("🤖 Sistema A.I. Inteligente")
    
    tab1, tab2 = st.tabs(["📈 Previsões de Vendas", "⚠️ Alertas Automáticos"])
    
    with tab1:
        st.subheader("Previsões de Vendas")
        meses, vendas = previsao_vendas()
        
        st.write("**Previsão para os próximos 6 meses:**")
        for mes, venda in zip(meses, vendas):
            st.write(f"- **{mes}:** R$ {venda:,.2f}")
            st.progress(min(venda / 50000, 1.0))
    
    with tab2:
        st.subheader("Alertas de Estoque")
        alertas = alertas_estoque()
        
        if alertas:
            for alerta in alertas:
                st.error(f"""
                ⚠️ **ALERTA DE ESTOQUE BAIXO**
                - Escola: {alerta[1]}
                - Produto: {alerta[2]} - Tamanho: {alerta[3]}
                - Estoque atual: {alerta[4]}
                - Mínimo recomendado: {alerta[5]}
                """)
        else:
            st.success("✅ Nenhum alerta de estoque baixo no momento")

def show_admin_panel():
    if st.session_state.user[3] != 'admin':
        st.error("Acesso negado! Apenas administradores podem acessar esta área.")
        return
        
    st.title("🔐 Painel de Administração")
    
    tab1, tab2 = st.tabs(["Gerenciar Usuários", "Backup de Dados"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        
        with st.form("novo_usuario"):
            st.write("**Adicionar Novo Usuário**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                username = st.text_input("Nome de usuário")
            with col2:
                password = st.text_input("Senha", type="password")
            with col3:
                nivel = st.selectbox("Nível", ["admin", "gestor", "vendedor"])
            
            if st.form_submit_button("Criar Usuário"):
                if username and password:
                    if add_usuario(username, password, nivel):
                        st.success(f"Usuário {username} criado com sucesso!")
                    else:
                        st.error("Erro ao criar usuário")
                else:
                    st.error("Nome de usuário e senha são obrigatórios")
        
        st.subheader("Usuários do Sistema")
        usuarios = get_usuarios()
        
        for usuario in usuarios:
            with st.expander(f"{usuario[1]} - {usuario[2]}"):
                st.write(f"ID: {usuario[0]}")
                st.write(f"Nível: {usuario[2]}")
                st.write(f"Criado em: {format_date_br(usuario[3])}")

if __name__ == "__main__":
    main()
