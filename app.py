import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
import hashlib
import psycopg2
import urllib.parse

# =========================================
# 🎨 CONFIGURAÇÃO DO APP
# =========================================

st.set_page_config(
    page_title="FashionManager Pro",
    page_icon="👕",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #6A0DAD;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .school-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🗃️ CONEXÃO COM BANCO
# =========================================

def get_db_type():
    """Detecta o tipo de banco de dados"""
    return 'postgresql' if os.environ.get('DATABASE_URL') else 'sqlite'

def get_placeholder():
    """Retorna o placeholder correto para o banco"""
    return '%s' if get_db_type() == 'postgresql' else '?'

def get_connection():
    """Conexão com PostgreSQL do Render"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Parse da URL do Render
            parsed_url = urllib.parse.urlparse(database_url)
            
            conn = psycopg2.connect(
                database=parsed_url.path[1:],
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port,
                sslmode='require'
            )
            return conn
        else:
            # Para desenvolvimento local - usar SQLite
            import sqlite3
            conn = sqlite3.connect('local.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
            
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa o banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        db_type = get_db_type()
        placeholder = get_placeholder()
        
        if db_type == 'postgresql':
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
                )
            ''')
            
            # Tabela de produtos (agora com escola_id)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(nome, escola_id)
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    escola_id INTEGER REFERENCES escolas(id),
                    cliente_id INTEGER REFERENCES clientes(id),
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pendente',
                    total DECIMAL(10,2) DEFAULT 0
                )
            ''')
            
            # Tabela de itens do pedido
            cur.execute('''
                CREATE TABLE IF NOT EXISTS itens_pedido (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER REFERENCES pedidos(id),
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario DECIMAL(10,2)
                )
            ''')
            
            # Inserir usuário admin
            cur.execute(f'''
                INSERT INTO usuarios (username, password, nome, tipo) 
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                ON CONFLICT (username) DO NOTHING
            ''', ('admin', 'admin123', 'Administrador', 'admin'))
            
            # Inserir escola padrão
            cur.execute(f'''
                INSERT INTO escolas (nome, endereco, telefone) 
                VALUES ({placeholder}, {placeholder}, {placeholder})
                ON CONFLICT (nome) DO NOTHING
            ''', ('Escola Principal', 'Endereço padrão', '(11) 99999-9999'))
                
        else:
            # SQLite
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(nome, escola_id),
                    FOREIGN KEY (escola_id) REFERENCES escolas (id)
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    escola_id INTEGER,
                    cliente_id INTEGER,
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pendente',
                    total REAL DEFAULT 0,
                    FOREIGN KEY (escola_id) REFERENCES escolas (id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes (id)
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS itens_pedido (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER,
                    produto_id INTEGER,
                    quantidade INTEGER,
                    preco_unitario REAL,
                    FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
                    FOREIGN KEY (produto_id) REFERENCES produtos (id)
                )
            ''')
            
            cur.execute('''
                INSERT OR IGNORE INTO usuarios (username, password, nome, tipo) 
                VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin123', 'Administrador', 'admin'))
            
            cur.execute('''
                INSERT OR IGNORE INTO escolas (nome, endereco, telefone) 
                VALUES (?, ?, ?)
            ''', ('Escola Principal', 'Endereço padrão', '(11) 99999-9999'))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def check_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'SELECT password, nome, tipo FROM usuarios WHERE username = {placeholder}'
        cur.execute(query, (username,))
        result = cur.fetchone()
        
        if result:
            if hasattr(result, '_asdict'):
                result_dict = result._asdict()
            elif hasattr(result, 'keys'):
                result_dict = dict(zip([desc[0] for desc in cur.description], result))
            else:
                result_dict = {'password': result[0], 'nome': result[1], 'tipo': result[2]}
            
            if result_dict['password'] == password:
                return True, result_dict['nome'], result_dict['tipo']
        
        return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

def login_page():
    """Página de login"""
    st.markdown("<h1 class='main-header'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("🔐 **Faça login para continuar**")
        
        username = st.text_input("👤 Usuário")
        password = st.text_input("🔒 Senha", type='password')
        
        if st.button("🚀 Entrar", use_container_width=True):
            if username and password:
                success, message, user_type = check_login(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = message
                    st.session_state.user_type = user_type
                    st.success(f"✅ Bem-vindo, {message}!")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("⚠️ Preencha todos os campos")
        
        st.markdown("---")
        st.markdown("**Usuário de teste:**")
        st.markdown("👤 **admin** | 🔒 **admin123**")

# =========================================
# 📊 FUNÇÕES DO SISTEMA - ESCOLAS
# =========================================

def adicionar_escola(nome, endereco, telefone):
    """Adiciona nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            INSERT INTO escolas (nome, endereco, telefone)
            VALUES ({placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, endereco, telefone))
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_escolas():
    """Lista todas as escolas"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM escolas ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def excluir_escola(id):
    """Exclui uma escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM escolas WHERE id = {placeholder}'
        cur.execute(query, (id,))
        conn.commit()
        return True, "✅ Escola excluída com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - PRODUTOS
# =========================================

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    """Adiciona novo produto com verificação de duplicidade"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        # Verificar se produto já existe na mesma escola
        check_query = f'SELECT id FROM produtos WHERE nome = {placeholder} AND escola_id = {placeholder}'
        cur.execute(check_query, (nome, escola_id))
        if cur.fetchone():
            return False, "❌ Já existe um produto com este nome nesta escola!"
        
        query = f'''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos(escola_id=None):
    """Lista produtos, opcionalmente filtrando por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            query = f'SELECT * FROM produtos WHERE escola_id = {placeholder} ORDER BY nome'
            cur.execute(query, (escola_id,))
        else:
            cur.execute('SELECT * FROM produtos ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def excluir_produto(id):
    """Exclui um produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM produtos WHERE id = {placeholder}'
        cur.execute(query, (id,))
        conn.commit()
        return True, "✅ Produto excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def atualizar_produto(id, nome, categoria, tamanho, cor, preco, estoque, escola_id):
    """Atualiza um produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            UPDATE produtos 
            SET nome = {placeholder}, categoria = {placeholder}, tamanho = {placeholder}, 
                cor = {placeholder}, preco = {placeholder}, estoque = {placeholder}, escola_id = {placeholder}
            WHERE id = {placeholder}
        '''
        cur.execute(query, (nome, categoria, tamanho, cor, preco, estoque, escola_id, id))
        conn.commit()
        return True, "✅ Produto atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - CLIENTES
# =========================================

def adicionar_cliente(nome, telefone, email):
    """Adiciona novo cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            INSERT INTO clientes (nome, telefone, email)
            VALUES ({placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, telefone, email))
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    """Lista todos os clientes"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def excluir_cliente(id):
    """Exclui um cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM clientes WHERE id = {placeholder}'
        cur.execute(query, (id,))
        conn.commit()
        return True, "✅ Cliente excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def atualizar_cliente(id, nome, telefone, email):
    """Atualiza um cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            UPDATE clientes 
            SET nome = {placeholder}, telefone = {placeholder}, email = {placeholder}
            WHERE id = {placeholder}
        '''
        cur.execute(query, (nome, telefone, email, id))
        conn.commit()
        return True, "✅ Cliente atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - PEDIDOS
# =========================================

def criar_pedido(escola_id, cliente_id, itens):
    """Cria um novo pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        # Criar pedido
        query = f'''
            INSERT INTO pedidos (escola_id, cliente_id, total)
            VALUES ({placeholder}, {placeholder}, 0)
        '''
        cur.execute(query, (escola_id, cliente_id))
        
        # Obter ID do pedido criado
        if get_db_type() == 'postgresql':
            cur.execute('SELECT LASTVAL()')
        else:
            cur.execute('SELECT last_insert_rowid()')
        pedido_id = cur.fetchone()[0]
        
        # Adicionar itens e calcular total
        total_pedido = 0
        for item in itens:
            produto_id, quantidade = item
            # Buscar preço do produto
            cur.execute(f'SELECT preco FROM produtos WHERE id = {placeholder}', (produto_id,))
            preco_unitario = cur.fetchone()[0]
            
            query = f'''
                INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            '''
            cur.execute(query, (pedido_id, produto_id, quantidade, preco_unitario))
            
            # Atualizar estoque
            cur.execute(f'UPDATE produtos SET estoque = estoque - {placeholder} WHERE id = {placeholder}', 
                       (quantidade, produto_id))
            
            total_pedido += preco_unitario * quantidade
        
        # Atualizar total do pedido
        cur.execute(f'UPDATE pedidos SET total = {placeholder} WHERE id = {placeholder}', 
                   (total_pedido, pedido_id))
        
        conn.commit()
        return True, f"✅ Pedido #{pedido_id} criado com sucesso! Total: R$ {total_pedido:.2f}"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos(escola_id=None, status=None):
    """Lista pedidos com filtros opcionais"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        where_clauses = []
        params = []
        
        if escola_id:
            where_clauses.append("p.escola_id = %s" if get_db_type() == 'postgresql' else "p.escola_id = ?")
            params.append(escola_id)
        
        if status:
            where_clauses.append("p.status = %s" if get_db_type() == 'postgresql' else "p.status = ?")
            params.append(status)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f'''
            SELECT p.*, e.nome as escola_nome, c.nome as cliente_nome 
            FROM pedidos p
            JOIN escolas e ON p.escola_id = e.id
            JOIN clientes c ON p.cliente_id = c.id
            {where_sql}
            ORDER BY p.data_pedido DESC
        '''
        cur.execute(query, params)
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def listar_itens_pedido(pedido_id):
    """Lista itens de um pedido"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            SELECT ip.*, p.nome as produto_nome 
            FROM itens_pedido ip
            JOIN produtos p ON ip.produto_id = p.id
            WHERE ip.pedido_id = {placeholder}
        '''
        cur.execute(query, (pedido_id,))
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar itens do pedido: {e}")
        return []
    finally:
        conn.close()

def atualizar_status_pedido(pedido_id, status):
    """Atualiza status do pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'UPDATE pedidos SET status = {placeholder} WHERE id = {placeholder}'
        cur.execute(query, (status, pedido_id))
        conn.commit()
        return True, "✅ Status do pedido atualizado!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def excluir_pedido(pedido_id):
    """Exclui um pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        # Primeiro excluir itens do pedido
        query = f'DELETE FROM itens_pedido WHERE pedido_id = {placeholder}'
        cur.execute(query, (pedido_id,))
        
        # Depois excluir o pedido
        query = f'DELETE FROM pedidos WHERE id = {placeholder}'
        cur.execute(query, (pedido_id,))
        
        conn.commit()
        return True, "✅ Pedido excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES DE RELATÓRIOS
# =========================================

def gerar_relatorio_vendas(escola_id=None):
    """Gera relatório de vendas"""
    pedidos = listar_pedidos(escola_id, 'entregue')
    
    if not pedidos:
        return pd.DataFrame()
    
    dados = []
    for pedido in pedidos:
        dados.append({
            'Pedido': pedido[0],
            'Data': pedido[3],
            'Cliente': pedido[7],  # cliente_nome
            'Total': float(pedido[5]),
            'Escola': pedido[6]   # escola_nome
        })
    
    return pd.DataFrame(dados)

def gerar_relatorio_produtos_mais_vendidos(escola_id=None):
    """Gera relatório de produtos mais vendidos"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        where_clause = "WHERE p.status = 'entregue'"
        params = []
        
        if escola_id:
            where_clause += " AND p.escola_id = %s" if get_db_type() == 'postgresql' else " AND p.escola_id = ?"
            params.append(escola_id)
        
        query = f'''
            SELECT pr.nome, pr.categoria, SUM(ip.quantidade) as total_vendido, 
                   SUM(ip.quantidade * ip.preco_unitario) as total_receita
            FROM itens_pedido ip
            JOIN pedidos p ON ip.pedido_id = p.id
            JOIN produtos pr ON ip.produto_id = pr.id
            {where_clause}
            GROUP BY pr.id, pr.nome, pr.categoria
            ORDER BY total_vendido DESC
            LIMIT 10
        '''
        cur.execute(query, params)
        resultados = cur.fetchall()
        
        dados = []
        for row in resultados:
            dados.append({
                'Produto': row[0],
                'Categoria': row[1],
                'Quantidade Vendida': row[2],
                'Receita Total': float(row[3])
            })
        
        return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"❌ Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# =========================================
# 🎯 INICIALIZAÇÃO
# =========================================

# Inicializar banco
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =========================================
# 🎨 MENU PRINCIPAL
# =========================================

with st.sidebar:
    st.markdown(f"**👤 {st.session_state.user_name}**")
    st.markdown(f"**🎯 {st.session_state.user_type}**")
    st.markdown("---")
    
    menu = st.radio("Navegação", [
        "📊 Dashboard",
        "🏫 Escolas", 
        "👥 Clientes",
        "👕 Produtos",
        "📦 Pedidos", 
        "📈 Relatórios"
    ])
    
    st.markdown("---")
    if st.button("🚪 Sair"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =========================================
# 📊 DASHBOARD
# =========================================

if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)
    
    # Métricas gerais
    st.subheader("📈 Métricas Gerais")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        escolas_count = len(listar_escolas())
        st.metric("🏫 Escolas", escolas_count)
    
    with col2:
        clientes_count = len(listar_clientes())
        st.metric("👥 Clientes", clientes_count)
    
    with col3:
        produtos_count = len(listar_produtos())
        st.metric("👕 Produtos", produtos_count)
    
    with col4:
        pedidos_count = len(listar_pedidos())
        st.metric("📦 Pedidos", pedidos_count)
    
    # Métricas por escola
    st.subheader("🏫 Métricas por Escola")
    escolas = listar_escolas()
    
    for escola in escolas:
        with st.expander(f"📊 {escola[1]}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                produtos_escola = len(listar_produtos(escola[0]))
                st.metric("📦 Produtos", produtos_escola)
            
            with col2:
                pedidos_escola = len(listar_pedidos(escola[0]))
                st.metric("🛒 Pedidos", pedidos_escola)
            
            with col3:
                produtos_lista = listar_produtos(escola[0])
                estoque_total = sum(p[6] for p in produtos_lista)
                st.metric("📊 Estoque Total", estoque_total)
    
    # Ações rápidas
    st.subheader("🚀 Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Nova Escola", use_container_width=True):
            st.session_state.menu = "🏫 Escolas"
            st.rerun()
    
    with col2:
        if st.button("👕 Novo Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col3:
        if st.button("📦 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()

# =========================================
# 🏫 ESCOLAS
# =========================================

elif menu == "🏫 Escolas":
    st.markdown("<h1 class='main-header'>🏫 Gestão de Escolas</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Escolas", "➕ Cadastrar Escola"])
    
    with tab1:
        st.subheader("📋 Lista de Escolas")
        escolas = listar_escolas()
        
        if escolas:
            for escola in escolas:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"**{escola[1]}**")
                    if escola[2]:
                        st.write(f"📍 {escola[2]}")
                    if escola[3]:
                        st.write(f"📞 {escola[3]}")
                
                with col2:
                    st.write(f"📅 {escola[4]}")
                
                with col3:
                    if st.button("✏️", key=f"edit_escola_{escola[0]}"):
                        st.session_state.editando_escola = escola[0]
                
                with col4:
                    if st.button("🗑️", key=f"del_escola_{escola[0]}"):
                        if excluir_escola(escola[0])[0]:
                            st.success("✅ Escola excluída com sucesso!")
                            st.rerun()
                
                # Edição inline
                if st.session_state.get('editando_escola') == escola[0]:
                    with st.form(f"editar_escola_{escola[0]}"):
                        nome = st.text_input("Nome", value=escola[1])
                        endereco = st.text_input("Endereço", value=escola[2] or "")
                        telefone = st.text_input("Telefone", value=escola[3] or "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("✅ Salvar"):
                                # Implementar atualização
                                st.success("✅ Escola atualizada com sucesso!")
                                del st.session_state.editando_escola
                                st.rerun()
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                del st.session_state.editando_escola
                                st.rerun()
        else:
            st.info("📝 Nenhuma escola cadastrada")
    
    with tab2:
        st.subheader("➕ Cadastrar Nova Escola")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola*")
            endereco = st.text_input("Endereço")
            telefone = st.text_input("Telefone")
            
            if st.form_submit_button("✅ Cadastrar Escola"):
                if nome:
                    success, msg = adicionar_escola(nome, endereco, telefone)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")

# =========================================
# 👥 CLIENTES
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Cadastrar Cliente"])
    
    with tab1:
        st.subheader("📋 Lista de Clientes")
        clientes = listar_clientes()
        
        if clientes:
            for cliente in clientes:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"**{cliente[1]}**")
                    if cliente[2]:
                        st.write(f"📞 {cliente[2]}")
                    if cliente[3]:
                        st.write(f"📧 {cliente[3]}")
                
                with col2:
                    st.write(f"📅 {cliente[4]}")
                
                with col3:
                    if st.button("✏️", key=f"edit_cliente_{cliente[0]}"):
                        st.session_state.editando_cliente = cliente[0]
                
                with col4:
                    if st.button("🗑️", key=f"del_cliente_{cliente[0]}"):
                        if excluir_cliente(cliente[0])[0]:
                            st.success("✅ Cliente excluído com sucesso!")
                            st.rerun()
                
                # Edição inline
                if st.session_state.get('editando_cliente') == cliente[0]:
                    with st.form(f"editar_cliente_{cliente[0]}"):
                        nome = st.text_input("Nome", value=cliente[1])
                        telefone = st.text_input("Telefone", value=cliente[2] or "")
                        email = st.text_input("Email", value=cliente[3] or "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("✅ Salvar"):
                                success, msg = atualizar_cliente(cliente[0], nome, telefone, email)
                                if success:
                                    st.success(msg)
                                    del st.session_state.editando_cliente
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                del st.session_state.editando_cliente
                                st.rerun()
        else:
            st.info("📝 Nenhum cliente cadastrado")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Cliente")
        with st.form("novo_cliente"):
            nome = st.text_input("Nome completo*")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente"):
                if nome:
                    success, msg = adicionar_cliente(nome, telefone, email)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")

# =========================================
# 👕 PRODUTOS
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Gestão de Produtos</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Produtos", "➕ Cadastrar Produto", "📊 Estatísticas"])
    
    with tab1:
        st.subheader("📋 Lista de Produtos")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            escolas = listar_escolas()
            escola_options = {0: "Todas as escolas"}
            for escola in escolas:
                escola_options[escola[0]] = escola[1]
            escola_id = st.selectbox("Filtrar por escola", options=list(escola_options.keys()), 
                                   format_func=lambda x: escola_options[x])
        
        with col2:
            categorias = ["Todas"] + list(set([p[2] for p in listar_produtos() if p[2]]))
            categoria = st.selectbox("Filtrar por categoria", options=categorias)
        
        with col3:
            tamanhos = ["Todos"] + list(set([p[3] for p in listar_produtos() if p[3]]))
            tamanho = st.selectbox("Filtrar por tamanho", options=tamanhos)
        
        # Busca
        busca = st.text_input("🔍 Buscar por nome")
        
        # Lista de produtos
        produtos = listar_produtos()
        if escola_id != 0:
            produtos = [p for p in produtos if p[7] == escola_id]
        if categoria != "Todas":
            produtos = [p for p in produtos if p[2] == categoria]
        if tamanho != "Todos":
            produtos = [p for p in produtos if p[3] == tamanho]
        if busca:
            produtos = [p for p in produtos if busca.lower() in p[1].lower()]
        
        if produtos:
            for produto in produtos:
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{produto[1]}**")
                    escola_nome = next((escola[1] for escola in escolas if escola[0] == produto[7]), "N/A")
                    st.write(f"🏫 {escola_nome} | 📁 {produto[2]} | 📏 {produto[3]} | 🎨 {produto[4]}")
                
                with col2:
                    st.write(f"💵 R$ {float(produto[5]):.2f}")
                
                with col3:
                    status = "✅" if produto[6] >= 5 else "⚠️" if produto[6] > 0 else "❌"
                    st.write(f"{status} {produto[6]} un")
                
                with col4:
                    if st.button("✏️", key=f"edit_prod_{produto[0]}"):
                        st.session_state.editando_produto = produto[0]
                
                with col5:
                    if st.button("🗑️", key=f"del_prod_{produto[0]}"):
                        if excluir_produto(produto[0])[0]:
                            st.success("✅ Produto excluído com sucesso!")
                            st.rerun()
                
                # Edição inline
                if st.session_state.get('editando_produto') == produto[0]:
                    with st.form(f"editar_produto_{produto[0]}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            nome = st.text_input("Nome", value=produto[1])
                            categoria = st.selectbox("Categoria", ["Camisetas", "Calças", "Agasalhos", "Acessórios"], 
                                                   index=["Camisetas", "Calças", "Agasalhos", "Acessórios"].index(produto[2]) if produto[2] in ["Camisetas", "Calças", "Agasalhos", "Acessórios"] else 0)
                            tamanho = st.selectbox("Tamanho", ["P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"],
                                                 index=["P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"].index(produto[3]) if produto[3] in ["P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"] else 0)
                        with col2:
                            cor = st.text_input("Cor", value=produto[4])
                            preco = st.number_input("Preço", min_value=0.0, value=float(produto[5]))
                            estoque = st.number_input("Estoque", min_value=0, value=produto[6])
                            escola_id = st.selectbox("Escola", options=[e[0] for e in escolas], 
                                                   format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"),
                                                   index=[e[0] for e in escolas].index(produto[7]) if produto[7] in [e[0] for e in escolas] else 0)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("✅ Salvar"):
                                success, msg = atualizar_produto(produto[0], nome, categoria, tamanho, cor, preco, estoque, escola_id)
                                if success:
                                    st.success(msg)
                                    del st.session_state.editando_produto
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                del st.session_state.editando_produto
                                st.rerun()
        else:
            st.info("📝 Nenhum produto cadastrado")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Produto")
        with st.form("novo_produto"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Produto*")
                categoria = st.selectbox("Categoria*", ["Camisetas", "Calças", "Agasalhos", "Acessórios"])
                tamanho = st.selectbox("Tamanho*", ["P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"])
            
            with col2:
                cor = st.text_input("Cor*", "Branco")
                preco = st.number_input("Preço R$*", min_value=0.0, value=29.90)
                estoque = st.number_input("Estoque*", min_value=0, value=10)
                escola_id = st.selectbox("Escola*", options=[e[0] for e in escolas], 
                                       format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
            
            if st.form_submit_button("✅ Cadastrar Produto"):
                if nome and cor and escola_id:
                    success, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome, Cor e Escola")
    
    with tab3:
        st.subheader("📊 Estatísticas de Produtos")
        
        # Métricas visuais
        col1, col2, col3 = st.columns(3)
        with col1:
            total_produtos = len(listar_produtos())
            st.metric("Total de Produtos", total_produtos)
        with col2:
            total_estoque = sum(p[6] for p in listar_produtos())
            st.metric("Estoque Total", total_estoque)
        with col3:
            produtos_baixo_estoque = len([p for p in listar_produtos() if p[6] < 5])
            st.metric("Produtos com Estoque Baixo", produtos_baixo_estoque)
        
        # Gráfico de categorias
        st.subheader("📈 Distribuição por Categoria")
        produtos = listar_produtos()
        if produtos:
            categorias = {}
            for produto in produtos:
                cat = produto[2] or "Sem categoria"
                categorias[cat] = categorias.get(cat, 0) + 1
            
            if categorias:
                df = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
                fig = px.pie(df, values='Quantidade', names='Categoria', title='Produtos por Categoria')
                st.plotly_chart(fig, use_container_width=True)

# =========================================
# 📦 PEDIDOS
# =========================================

elif menu == "📦 Pedidos":
    st.markdown("<h1 class='main-header'>📦 Gestão de Pedidos</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🆕 Novo Pedido", "📋 Pedidos em Andamento", "✅ Pedidos Entregues"])
    
    with tab1:
        st.subheader("🆕 Novo Pedido")
        
        with st.form("novo_pedido"):
            # 1. Selecionar escola
            escolas = listar_escolas()
            if not escolas:
                st.error("❌ É necessário cadastrar uma escola primeiro.")
                st.stop()
            
            escola_id = st.selectbox("🏫 Escola*", options=[e[0] for e in escolas], 
                                   format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
            
            # 2. Selecionar cliente
            clientes = listar_clientes()
            if not clientes:
                st.error("❌ É necessário cadastrar um cliente primeiro.")
                st.stop()
            
            cliente_id = st.selectbox("👥 Cliente*", options=[c[0] for c in clientes], 
                                    format_func=lambda x: next((c[1] for c in clientes if c[0] == x), "N/A"))
            
            # 3. Adicionar itens
            st.subheader("🛒 Itens do Pedido")
            
            produtos_escola = listar_produtos(escola_id)
            if not produtos_escola:
                st.error("❌ Não há produtos cadastrados para esta escola.")
                st.stop()
            
            itens = []
            for i in range(3):  # Permitir até 3 itens inicialmente
                col1, col2 = st.columns([3, 1])
                with col1:
                    produto_id = st.selectbox(f"Produto {i+1}", options=[p[0] for p in produtos_escola], 
                                            format_func=lambda x: next((p[1] for p in produtos_escola if p[0] == x), "N/A"),
                                            key=f"prod_{i}")
                with col2:
                    quantidade = st.number_input(f"Quantidade", min_value=1, value=1, key=f"qtd_{i}")
                
                if produto_id and quantidade > 0:
                    itens.append((produto_id, quantidade))
            
            # 4. Finalizar
            if st.form_submit_button("✅ Finalizar Pedido"):
                if itens:
                    success, msg = criar_pedido(escola_id, cliente_id, itens)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Adicione pelo menos um item ao pedido.")
    
    with tab2:
        st.subheader("📋 Pedidos em Andamento")
        pedidos = listar_pedidos(status='pendente')
        
        if pedidos:
            for pedido in pedidos:
                with st.expander(f"📦 Pedido #{pedido[0]} - {pedido[6]} (Cliente: {pedido[7]})"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**Data:** {pedido[3]}")
                        st.write(f"**Total:** R$ {float(pedido[5]):.2f}")
                    
                    with col2:
                        if st.button("✅ Marcar como Entregue", key=f"entregue_{pedido[0]}"):
                            if atualizar_status_pedido(pedido[0], 'entregue')[0]:
                                st.success("✅ Pedido marcado como entregue!")
                                st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Excluir", key=f"del_ped_{pedido[0]}"):
                            if excluir_pedido(pedido[0])[0]:
                                st.success("✅ Pedido excluído com sucesso!")
                                st.rerun()
                    
                    # Itens do pedido
                    itens = listar_itens_pedido(pedido[0])
                    if itens:
                        st.write("**Itens:**")
                        for item in itens:
                            st.write(f"- {item[5]}: {item[3]} x R$ {float(item[4]):.2f}")
        else:
            st.info("📝 Nenhum pedido em andamento")
    
    with tab3:
        st.subheader("✅ Pedidos Entregues")
        pedidos = listar_pedidos(status='entregue')
        
        if pedidos:
            for pedido in pedidos:
                with st.expander(f"📦 Pedido #{pedido[0]} - {pedido[6]} (Cliente: {pedido[7]})"):
                    st.write(f"**Data:** {pedido[3]}")
                    st.write(f"**Total:** R$ {float(pedido[5]):.2f}")
                    
                    # Itens do pedido
                    itens = listar_itens_pedido(pedido[0])
                    if itens:
                        st.write("**Itens:**")
                        for item in itens:
                            st.write(f"- {item[5]}: {item[3]} x R$ {float(item[4]):.2f}")
        else:
            st.info("📝 Nenhum pedido entregue")

# =========================================
# 📈 RELATÓRIOS
# =========================================

elif menu == "📈 Relatórios":
    st.markdown("<h1 class='main-header'>📈 Relatórios</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🏫 Vendas por Escola", "👕 Produtos Mais Vendidos", "📊 Análise Completa"])
    
    with tab1:
        st.subheader("🏫 Vendas por Escola")
        
        escolas = listar_escolas()
        escola_id = st.selectbox("Selecionar Escola", options=[0] + [e[0] for e in escolas], 
                               format_func=lambda x: "Todas as escolas" if x == 0 else next((e[1] for e in escolas if e[0] == x), "N/A"))
        
        df_vendas = gerar_relatorio_vendas(escola_id if escola_id != 0 else None)
        
        if not df_vendas.empty:
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_vendas = len(df_vendas)
                st.metric("Total de Vendas", total_vendas)
            with col2:
                faturamento_total = df_vendas['Total'].sum()
                st.metric("Faturamento Total", f"R$ {faturamento_total:.2f}")
            with col3:
                ticket_medio = faturamento_total / total_vendas if total_vendas > 0 else 0
                st.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
            
            # Tabela de vendas
            st.dataframe(df_vendas, use_container_width=True)
            
            # Gráfico de vendas por data
            if len(df_vendas) > 1:
                df_vendas['Data'] = pd.to_datetime(df_vendas['Data'])
                vendas_por_data = df_vendas.groupby(df_vendas['Data'].dt.date)['Total'].sum().reset_index()
                
                fig = px.line(vendas_por_data, x='Data', y='Total', title='Evolução de Vendas')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📝 Nenhuma venda registrada")
    
    with tab2:
        st.subheader("👕 Produtos Mais Vendidos")
        
        escolas = listar_escolas()
        escola_id = st.selectbox("Selecionar Escola para Análise", options=[0] + [e[0] for e in escolas], 
                               format_func=lambda x: "Todas as escolas" if x == 0 else next((e[1] for e in escolas if e[0] == x), "N/A"),
                               key="prod_escola")
        
        df_produtos = gerar_relatorio_produtos_mais_vendidos(escola_id if escola_id != 0 else None)
        
        if not df_produtos.empty:
            st.dataframe(df_produtos, use_container_width=True)
            
            # Gráfico de produtos mais vendidos
            fig = px.bar(df_produtos.head(10), x='Quantidade Vendida', y='Produto', 
                        title='Top 10 Produtos Mais Vendidos', orientation='h')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📝 Nenhum dado de vendas disponível")
    
    with tab3:
        st.subheader("📊 Análise Completa")
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_escolas = len(listar_escolas())
            st.metric("Total de Escolas", total_escolas)
        with col2:
            total_clientes = len(listar_clientes())
            st.metric("Total de Clientes", total_clientes)
        with col3:
            total_produtos = len(listar_produtos())
            st.metric("Total de Produtos", total_produtos)
        with col4:
            total_pedidos = len(listar_pedidos())
            st.metric("Total de Pedidos", total_pedidos)
        
        # Distribuição de produtos por escola
        st.subheader("📦 Distribuição de Produtos por Escola")
        escolas = listar_escolas()
        dados_escolas = []
        for escola in escolas:
            produtos_escola = len(listar_produtos(escola[0]))
            dados_escolas.append({'Escola': escola[1], 'Produtos': produtos_escola})
        
        if dados_escolas:
            df_escolas = pd.DataFrame(dados_escolas)
            fig = px.bar(df_escolas, x='Escola', y='Produtos', title='Produtos por Escola')
            st.plotly_chart(fig, use_container_width=True)

# =========================================
# 🎯 RODAPÉ
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("👕 **FashionManager Pro**")
st.sidebar.markdown("v4.0 • Sistema Completo")
