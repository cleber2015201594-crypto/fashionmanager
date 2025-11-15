import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse as urlparse

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO AVANÇADO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def init_db():
    """Inicializa o banco de dados e cria tabelas necessárias"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    nome_completo VARCHAR(100),
                    tipo VARCHAR(20) DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT TRUE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) UNIQUE NOT NULL
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(200) NOT NULL,
                    telefone VARCHAR(20),
                    email VARCHAR(100),
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(200) NOT NULL,
                    categoria VARCHAR(100),
                    tamanho VARCHAR(10),
                    cor VARCHAR(50),
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER REFERENCES clientes(id),
                    status VARCHAR(50) DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    quantidade_total INTEGER,
                    valor_total DECIMAL(10,2),
                    observacoes TEXT
                )
            ''')
            
            # Tabela de itens do pedido
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_itens (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario DECIMAL(10,2),
                    subtotal DECIMAL(10,2)
                )
            ''')
            
            # Inserir usuários padrão se não existirem
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                cur.execute('''
                    INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                ''', (username, password_hash, nome, tipo))
            
            # Inserir escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                cur.execute('''
                    INSERT INTO escolas (nome) VALUES (%s)
                    ON CONFLICT (nome) DO NOTHING
                ''', (escola,))
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco: {str(e)}")
        finally:
            conn.close()

def get_connection():
    """Estabelece conexão com o PostgreSQL"""
    try:
        # Para Render.com - usa DATABASE_URL do environment
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Converte postgres:// para postgresql://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        else:
            # Para desenvolvimento local
            st.error("DATABASE_URL não configurada")
            return None
            
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = %s AND ativo = TRUE
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]  # sucesso, nome, tipo
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

def alterar_senha(username, senha_atual, nova_senha):
    """Altera a senha do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar senha atual
        cur.execute('SELECT password_hash FROM usuarios WHERE username = %s', (username,))
        resultado = cur.fetchone()
        
        if not resultado or not check_hashes(senha_atual, resultado[0]):
            return False, "Senha atual incorreta"
        
        # Atualizar senha
        nova_senha_hash = make_hashes(nova_senha)
        cur.execute(
            'UPDATE usuarios SET password_hash = %s WHERE username = %s',
            (nova_senha_hash, username)
        )
        conn.commit()
        return True, "Senha alterada com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_usuarios():
    """Lista todos os usuários (apenas para admin)"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, username, nome_completo, tipo, ativo, data_criacao 
            FROM usuarios 
            ORDER BY username
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []
    finally:
        conn.close()

def criar_usuario(username, password, nome_completo, tipo):
    """Cria novo usuário (apenas para admin)"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        password_hash = make_hashes(password)
        
        cur.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, tipo)
            VALUES (%s, %s, %s, %s)
        ''', (username, password_hash, nome_completo, tipo))
        
        conn.commit()
        return True, "Usuário criado com sucesso!"
        
    except psycopg2.IntegrityError:
        return False, "Username já existe"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username and password:
            sucesso, mensagem, tipo_usuario = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.nome_usuario = mensagem
                st.session_state.tipo_usuario = tipo_usuario
                st.sidebar.success(f"Bem-vindo, {mensagem}!")
                st.rerun()
            else:
                st.sidebar.error(mensagem)
        else:
            st.sidebar.error("Preencha todos os campos")

# Inicializar banco na primeira execução
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🚀 SISTEMA PRINCIPAL
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CONFIGURAÇÕES ESPECÍFICAS
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

tipos_camisetas = ["Camiseta Básica", "Camiseta Regata", "Camiseta Manga Longa"]
tipos_calcas = ["Calça Jeans", "Calça Tactel", "Calça Moletom", "Bermuda", "Short", "Short Saia"]
tipos_agasalhos = ["Blusão", "Moletom"]

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS
# =========================================

# FUNÇÕES PARA CLIENTES
def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (%s, %s, %s, %s) RETURNING id",
            (nome, telefone, email, data_cadastro)
        )
        
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM clientes ORDER BY nome
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar se tem pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = %s", (cliente_id,))
        if cur.fetchone()[0] > 0:
            return False, "Cliente possui pedidos e não pode ser excluído"
        
        cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        conn.commit()
        return True, "Cliente excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÕES PARA PRODUTOS
def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        
        conn.commit()
        return True, "Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id 
            ORDER BY p.nome
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = %s
                ORDER BY p.nome
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY p.nome
            ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE produtos SET estoque = %s WHERE id = %s", (nova_quantidade, produto_id))
        conn.commit()
        return True, "Estoque atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÕES PARA ESCOLAS
def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

# FUNÇÕES PARA PEDIDOS
def adicionar_pedido(cliente_id, itens, data_entrega, observacoes):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        cur.execute('''
            INSERT INTO pedidos (cliente_id, data_entrega_prevista, quantidade_total, valor_total, observacoes)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        ''', (cliente_id, data_entrega, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.fetchone()[0]
        
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            # Atualizar estoque
            cur.execute("UPDATE produtos SET estoque = estoque - %s WHERE id = %s", 
                       (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.data_pedido DESC
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Restaurar estoque
        cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = %s', (pedido_id,))
        itens = cur.fetchall()
        
        for produto_id, quantidade in itens:
            cur.execute("UPDATE produtos SET estoque = estoque + %s WHERE id = %s", (quantidade, produto_id))
        
        # Excluir pedido (itens serão excluídos por CASCADE)
        cur.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES PARA RELATÓRIOS
# =========================================

def gerar_relatorio_vendas():
    """Gera relatório de vendas por período"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT 
                DATE(p.data_pedido) as data,
                COUNT(*) as total_pedidos,
                SUM(p.quantidade_total) as total_itens,
                SUM(p.valor_total) as total_vendas
            FROM pedidos p
            GROUP BY DATE(p.data_pedido)
            ORDER BY data DESC
        ''')
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Data', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_produtos():
    """Gera relatório de produtos mais vendidos"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT 
                pr.nome as produto,
                pr.categoria,
                pr.tamanho,
                pr.cor,
                e.nome as escola,
                SUM(pi.quantidade) as total_vendido,
                SUM(pi.subtotal) as total_faturado
            FROM pedido_itens pi
            JOIN produtos pr ON pi.produto_id = pr.id
            LEFT JOIN escolas e ON pr.escola_id = e.id
            GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor, e.nome
            ORDER BY total_vendido DESC
        ''')
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Escola', 'Total Vendido', 'Total Faturado (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_clientes():
    """Gera relatório de clientes que mais compram"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT 
                c.nome as cliente,
                COUNT(p.id) as total_pedidos,
                SUM(p.quantidade_total) as total_itens,
                SUM(p.valor_total) as total_gasto
            FROM clientes c
            LEFT JOIN pedidos p ON c.id = p.cliente_id
            WHERE p.id IS NOT NULL
            GROUP BY c.id, c.nome
            ORDER BY total_gasto DESC
        ''')
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Cliente', 'Total Pedidos', 'Total Itens', 'Total Gasto (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Menu de gerenciamento de usuários (apenas para admin)
if st.session_state.tipo_usuario == 'admin':
    with st.sidebar.expander("👥 Gerenciar Usuários"):
        st.subheader("Novo Usuário")
        with st.form("novo_usuario"):
            novo_username = st.text_input("Username")
            nova_senha = st.text_input("Senha", type='password')
            nome_completo = st.text_input("Nome Completo")
            tipo = st.selectbox("Tipo", ["admin", "vendedor"])
            
            if st.form_submit_button("Criar Usuário"):
                if novo_username and nova_senha and nome_completo:
                    sucesso, msg = criar_usuario(novo_username, nova_senha, nome_completo, tipo)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
        
        st.subheader("Usuários do Sistema")
        usuarios = listar_usuarios()
        if usuarios:
            for usuario in usuarios:
                status = "✅ Ativo" if usuario[4] else "❌ Inativo"
                st.write(f"**{usuario[1]}** - {usuario[2]} ({usuario[3]}) - {status}")

# Menu de alteração de senha
with st.sidebar.expander("🔐 Alterar Senha"):
    with st.form("alterar_senha"):
        senha_atual = st.text_input("Senha Atual", type='password')
        nova_senha1 = st.text_input("Nova Senha", type='password')
        nova_senha2 = st.text_input("Confirmar Nova Senha", type='password')
        
        if st.form_submit_button("Alterar Senha"):
            if senha_atual and nova_senha1 and nova_senha2:
                if nova_senha1 == nova_senha2:
                    sucesso, msg = alterar_senha(st.session_state.username, senha_atual, nova_senha1)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("As novas senhas não coincidem")
            else:
                st.error("Preencha todos os campos")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.nome_usuario = None
    st.session_state.tipo_usuario = None
    st.rerun()

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Visão Geral")
elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos") 
elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
elif menu == "👕 Produtos":
    st.title("👕 Gestão de Produtos")
elif menu == "📦 Estoque":
    st.title("📦 Controle de Estoque")
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Detalhados")

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Métricas em Tempo Real")
    
    # Carregar dados
    pedidos = listar_pedidos()
    clientes = listar_clientes()
    produtos = listar_produtos()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Pedidos", len(pedidos))
    
    with col2:
        pedidos_pendentes = len([p for p in pedidos if p[2] == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        st.metric("Clientes Ativos", len(clientes))
    
    with col4:
        produtos_baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Ações Rápidas - CORRIGIDO
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

elif menu == "👥 Clientes":
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        nome = st.text_input("👤 Nome completo*")
        telefone = st.text_input("📞 Telefone")
        email = st.text_input("📧 Email")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome:
                sucesso, msg = adicionar_cliente(nome, telefone, email)
                if sucesso:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
            else:
                st.error("❌ Nome é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Data Cadastro': cliente[4]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")
    
    with tab3:
        st.header("🗑️ Excluir Cliente")
        clientes = listar_clientes()
        
        if clientes:
            cliente_selecionado = st.selectbox(
                "Selecione o cliente para excluir:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                st.warning("⚠️ Esta ação não pode ser desfeita!")
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, msg = excluir_cliente(cliente_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Listar Produtos"])
    
    with tab1:
        st.header("➕ Cadastrar Produto")
        
        nome = st.text_input("Nome do produto*")
        categoria = st.selectbox("Categoria", ["Camisetas", "Calças/Shorts", "Agasalhos"])
        tamanho = st.selectbox("Tamanho", todos_tamanhos)
        cor = st.text_input("Cor", value="Branco")
        preco = st.number_input("Preço (R$)", min_value=0.0, value=29.90)
        estoque = st.number_input("Estoque inicial", min_value=0, value=10)
        descricao = st.text_area("Descrição")
        
        # Seleção de escola para o produto
        escolas_db = listar_escolas()
        escola_selecionada = st.selectbox(
            "🏫 Escola do produto*",
            [e[1] for e in escolas_db],
            help="Selecione a escola para a qual este produto é destinado"
        )
        
        if st.button("✅ Cadastrar Produto", type="primary"):
            if nome and escola_selecionada:
                escola_id = next(e[0] for e in escolas_db if e[1] == escola_selecionada)
                sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                if sucesso:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
            else:
                st.error("❌ Nome do produto e escola são obrigatórios!")
    
    with tab2:
        st.header("📋 Produtos Cadastrados")
        
        # Filtro por escola
        escolas_db = listar_escolas()
        escola_filtro = st.selectbox(
            "Filtrar por escola:",
            ["Todas as escolas"] + [e[1] for e in escolas_db]
        )
        
        if escola_filtro == "Todas as escolas":
            produtos = listar_produtos()
        else:
            escola_id = next(e[0] for e in escolas_db if e[1] == escola_filtro)
            produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            dados = []
            for produto in produtos:
                dados.append({
                    'ID': produto[0],
                    'Nome': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Preço': f"R$ {produto[5]:.2f}",
                    'Estoque': produto[6],
                    'Descrição': produto[7] or 'N/A',
                    'Escola': produto[9] or 'N/A'
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👕 Nenhum produto cadastrado")

elif menu == "📦 Estoque":
    st.header("📊 Ajuste de Estoque")
    
    # Filtro por escola
    escolas_db = listar_escolas()
    escola_filtro = st.selectbox(
        "Filtrar por escola:",
        ["Todas as escolas"] + [e[1] for e in escolas_db]
    )
    
    if escola_filtro == "Todas as escolas":
        produtos = listar_produtos()
    else:
        escola_id = next(e[0] for e in escolas_db if e[1] == escola_filtro)
        produtos = listar_produtos_por_escola(escola_id)
    
    if produtos:
        produto_selecionado = st.selectbox(
            "Selecione o produto:",
            [f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Escola: {p[9]} - Estoque: {p[6]}" for p in produtos]
        )
        
        if produto_selecionado:
            produto_id = next(p[0] for p in produtos if f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Escola: {p[9]} - Estoque: {p[6]}" == produto_selecionado)
            produto = next(p for p in produtos if p[0] == produto_id)
            
            st.write(f"**Produto selecionado:** {produto[1]}")
            st.write(f"**Escola:** {produto[9]}")
            st.write(f"**Estoque atual:** {produto[6]} unidades")
            
            nova_quantidade = st.number_input("Nova quantidade em estoque", min_value=0, value=produto[6])
            
            if st.button("💾 Atualizar Estoque", type="primary"):
                if nova_quantidade != produto[6]:
                    sucesso, msg = atualizar_estoque(produto_id, nova_quantidade)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.info("Quantidade não foi alterada")
    else:
        st.info("👕 Nenhum produto cadastrado")

elif menu == "📦 Pedidos":
    tab1, tab2, tab3 = st.tabs(["➕ Novo Pedido", "📋 Listar Pedidos", "🗑️ Excluir Pedido"])
    
    with tab1:
        st.header("➕ Novo Pedido")
        
        # Selecionar cliente
        clientes = listar_clientes()
        if clientes:
            cliente_selecionado = st.selectbox(
                "Selecione o cliente:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                # Filtro de produtos por escola
                escolas_db = listar_escolas()
                escola_filtro = st.selectbox(
                    "🏫 Filtrar produtos por escola:",
                    ["Todas as escolas"] + [e[1] for e in escolas_db]
                )
                
                if escola_filtro == "Todas as escolas":
                    produtos = listar_produtos()
                else:
                    escola_id = next(e[0] for e in escolas_db if e[1] == escola_filtro)
                    produtos = listar_produtos_por_escola(escola_id)
                
                if produtos:
                    st.subheader("🛒 Itens do Pedido")
                    
                    # Interface para adicionar itens
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        produto_selecionado = st.selectbox(
                            "Produto:",
                            [f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Escola: {p[9]} - Estoque: {p[6]} - R$ {p[5]:.2f}" for p in produtos]
                        )
                    with col2:
                        quantidade = st.number_input("Quantidade", min_value=1, value=1)
                    with col3:
                        if st.button("➕ Adicionar Item"):
                            if 'itens_pedido' not in st.session_state:
                                st.session_state.itens_pedido = []
                            
                            produto_id = next(p[0] for p in produtos if f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Escola: {p[9]} - Estoque: {p[6]} - R$ {p[5]:.2f}" == produto_selecionado)
                            produto = next(p for p in produtos if p[0] == produto_id)
                            
                            if quantidade > produto[6]:
                                st.error("❌ Quantidade indisponível em estoque!")
                            else:
                                item = {
                                    'produto_id': produto_id,
                                    'nome': produto[1],
                                    'escola': produto[9],
                                    'quantidade': quantidade,
                                    'preco_unitario': float(produto[5]),
                                    'subtotal': float(produto[5]) * quantidade
                                }
                                st.session_state.itens_pedido.append(item)
                                st.success("✅ Item adicionado!")
                                st.rerun()
                    
                    # Mostrar itens adicionados
                    if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
                        st.subheader("📋 Itens do Pedido")
                        total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
                        
                        for i, item in enumerate(st.session_state.itens_pedido):
                            col1, col2, col3, col4, col5 = st.columns([3,1,1,1,1])
                            with col1:
                                st.write(f"**{item['nome']}**")
                                st.write(f"Escola: {item['escola']}")
                            with col2:
                                st.write(f"Qtd: {item['quantidade']}")
                            with col3:
                                st.write(f"R$ {item['preco_unitario']:.2f}")
                            with col4:
                                st.write(f"R$ {item['subtotal']:.2f}")
                            with col5:
                                if st.button("❌", key=f"del_{i}"):
                                    st.session_state.itens_pedido.pop(i)
                                    st.rerun()
                        
                        st.write(f"**Total do Pedido: R$ {total_pedido:.2f}**")
                        
                        # Data de entrega e observações
                        data_entrega = st.date_input("📅 Data de Entrega Prevista", min_value=date.today())
                        observacoes = st.text_area("Observações")
                        
                        if st.button("✅ Finalizar Pedido", type="primary"):
                            if st.session_state.itens_pedido:
                                sucesso, resultado = adicionar_pedido(
                                    cliente_id, 
                                    st.session_state.itens_pedido, 
                                    data_entrega, 
                                    observacoes
                                )
                                if sucesso:
                                    st.success(f"✅ Pedido #{resultado} criado com sucesso!")
                                    st.balloons()
                                    del st.session_state.itens_pedido
                                    st.rerun()
                                else:
                                    st.error(f"❌ Erro ao criar pedido: {resultado}")
                            else:
                                st.error("❌ Adicione pelo menos um item ao pedido!")
                    else:
                        st.info("🛒 Adicione itens ao pedido usando o botão acima")
                else:
                    st.error("❌ Nenhum produto cadastrado. Cadastre produtos primeiro.")
        else:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
    
    with tab2:
        st.header("📋 Pedidos Realizados")
        pedidos = listar_pedidos()
        
        if pedidos:
            dados = []
            for pedido in pedidos:
                status_color = {
                    'Pendente': '🟡',
                    'Entregue': '🟢',
                    'Cancelado': '🔴'
                }.get(pedido[2], '⚪')
                
                dados.append({
                    'ID': pedido[0],
                    'Cliente': pedido[8],
                    'Status': f"{status_color} {pedido[2]}",
                    'Data Pedido': pedido[3],
                    'Entrega Prevista': pedido[4],
                    'Quantidade': pedido[5],
                    'Valor Total': f"R$ {pedido[6]:.2f}",
                    'Observações': pedido[7] or 'Nenhuma'
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("📦 Nenhum pedido realizado")
    
    with tab3:
        st.header("🗑️ Excluir Pedido")
        pedidos = listar_pedidos()
        
        if pedidos:
            pedido_selecionado = st.selectbox(
                "Selecione o pedido para excluir:",
                [f"Pedido #{p[0]} - {p[8]} - R$ {p[6]:.2f}" for p in pedidos]
            )
            
            if pedido_selecionado:
                pedido_id = int(pedido_selecionado.split("#")[1].split(" -")[0])
                
                st.warning("⚠️ Esta ação não pode ser desfeita e restaurará o estoque!")
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, msg = excluir_pedido(pedido_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("📦 Nenhum pedido para excluir")

elif menu == "📈 Relatórios":
    tab1, tab2, tab3 = st.tabs(["📊 Vendas por Período", "📦 Produtos Mais Vendidos", "👥 Clientes Mais Ativos"])
    
    with tab1:
        st.header("📊 Relatório de Vendas por Período")
        relatorio_vendas = gerar_relatorio_vendas()
        
        if not relatorio_vendas.empty:
            st.dataframe(relatorio_vendas, use_container_width=True)
            
            # Gráfico de vendas
            fig = px.line(relatorio_vendas, x='Data', y='Total Vendas (R$)', 
                         title='Evolução das Vendas por Dia')
            st.plotly_chart(fig, use_container_width=True)
            
            # Métricas resumidas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Período", f"R$ {relatorio_vendas['Total Vendas (R$)'].sum():.2f}")
            with col2:
                st.metric("Média Diária", f"R$ {relatorio_vendas['Total Vendas (R$)'].mean():.2f}")
            with col3:
                st.metric("Maior Venda", f"R$ {relatorio_vendas['Total Vendas (R$)'].max():.2f}")
        else:
            st.info("📊 Nenhum dado de venda disponível")
    
    with tab2:
        st.header("📦 Produtos Mais Vendidos")
        relatorio_produtos = gerar_relatorio_produtos()
        
        if not relatorio_produtos.empty:
            st.dataframe(relatorio_produtos, use_container_width=True)
            
            # Gráfico de produtos mais vendidos
            fig = px.bar(relatorio_produtos.head(10), x='Produto', y='Total Vendido',
                        title='Top 10 Produtos Mais Vendidos')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📦 Nenhum dado de produto vendido disponível")
    
    with tab3:
        st.header("👥 Clientes Mais Ativos")
        relatorio_clientes = gerar_relatorio_clientes()
        
        if not relatorio_clientes.empty:
            st.dataframe(relatorio_clientes, use_container_width=True)
            
            # Gráfico de clientes que mais gastam
            fig = px.bar(relatorio_clientes.head(10), x='Cliente', y='Total Gasto (R$)',
                        title='Top 10 Clientes que Mais Gastam')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("👥 Nenhum dado de cliente disponível")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v8.0\n\n🗄️ **Banco de Dados PostgreSQL**")

# Botão para recarregar dados
if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()
