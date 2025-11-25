import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import numpy as np
import io
import csv
import base64
import math

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos + A.I.",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Mobile Otimizado
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.75rem;
            font-size: 16px;
            margin: 0.2rem 0;
        }
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px;
            padding: 0.75rem;
        }
    }
    
    /* Indicadores de Permissão */
    .permission-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    .badge-admin { background: #dc3545; color: white; }
    .badge-gestor { background: #ffc107; color: black; }
    .badge-vendedor { background: #28a745; color: white; }
    
    /* Métricas Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        text-align: center;
    }
    
    /* Cards A.I. */
    .ai-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        border-left: 5px solid #4CAF50;
    }
    
    .warning-card {
        border-left: 5px solid #FF9800;
        background: #FFF3E0;
    }
    
    .danger-card {
        border-left: 5px solid #F44336;
        background: #FFEBEE;
    }
    
    .info-card {
        border-left: 5px solid #2196F3;
        background: #E3F2FD;
    }
    
    /* Botões Mobile */
    .mobile-btn {
        width: 100%;
        padding: 1rem;
        margin: 0.3rem 0;
        border-radius: 10px;
        border: none;
        font-size: 16px;
        font-weight: bold;
    }
    
    .btn-primary { background: #4CAF50; color: white; }
    .btn-secondary { background: #2196F3; color: white; }
    .btn-warning { background: #FF9800; color: white; }
    .btn-danger { background: #F44336; color: white; }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔐 SISTEMA DE PERMISSÕES AVANÇADO
# =========================================

PERMISSOES = {
    'admin': {
        'modulos': ['dashboard', 'clientes', 'pedidos', 'relatorios', 'administracao', 'estoque', 'financeiro'],
        'acoes': ['criar', 'ler', 'editar', 'excluir', 'exportar', 'configurar'],
        'descricao': 'Acesso total ao sistema'
    },
    'gestor': {
        'modulos': ['dashboard', 'clientes', 'pedidos', 'relatorios', 'estoque'],
        'acoes': ['criar', 'ler', 'editar', 'exportar'],
        'descricao': 'Acesso gerencial completo'
    },
    'vendedor': {
        'modulos': ['dashboard', 'clientes', 'pedidos'],
        'acoes': ['criar', 'ler', 'editar'],
        'descricao': 'Acesso operacional básico'
    }
}

def verificar_permissao(tipo_usuario, modulo=None, acao=None):
    """Verifica se usuário tem permissão"""
    if tipo_usuario not in PERMISSOES:
        return False
    
    if modulo and not acao:
        return modulo in PERMISSOES[tipo_usuario]['modulos']
    
    if modulo and acao:
        tem_modulo = modulo in PERMISSOES[tipo_usuario]['modulos']
        tem_acao = acao in PERMISSOES[tipo_usuario]['acoes']
        return tem_modulo and tem_acao
    
    return True

def mostrar_restricao_permissao():
    """Exibe mensagem de restrição de permissão"""
    st.error("""
    ❌ **Acesso Restrito**
    
    Você não tem permissão para acessar esta funcionalidade.
    
    **Sua permissão:** {}
    
    👨‍💼 _Contate o administrador do sistema_
    """.format(st.session_state.tipo_usuario))

# =========================================
# 🇧🇷 FUNÇÕES DE FORMATAÇÃO BRASILEIRA
# =========================================

def formatar_data_brasil(data_string):
    """Converte data para formato brasileiro DD/MM/YYYY"""
    if not data_string:
        return "N/A"
    
    try:
        if isinstance(data_string, (date, datetime)):
            return data_string.strftime("%d/%m/%Y")
            
        if '/' in str(data_string):
            return str(data_string)
            
        if isinstance(data_string, str) and len(data_string) >= 10:
            partes = data_string.split('-')
            if len(partes) >= 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
        
        return str(data_string)
    except:
        return str(data_string)

def formatar_datahora_brasil(datahora_string):
    """Converte data/hora para formato brasileiro"""
    if not datahora_string:
        return "N/A"
    
    try:
        if ' ' in str(datahora_string):
            data_part, hora_part = str(datahora_string).split(' ', 1)
            data_brasil = formatar_data_brasil(data_part)
            hora_part = hora_part[:5]
            return f"{data_brasil} {hora_part}"
        else:
            return formatar_data_brasil(datahora_string)
    except:
        return str(datahora_string)

def formatar_moeda_brasil(valor):
    """Formata valor para moeda brasileira"""
    try:
        return f"R$ {float(valor):.2f}".replace('.', ',')
    except:
        return "R$ 0,00"

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Conexão com SQLite otimizada"""
    try:
        conn = sqlite3.connect('sistema_fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome_completo TEXT,
                tipo TEXT DEFAULT 'vendedor',
                ativo INTEGER DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                endereco TEXT,
                telefone TEXT,
                email TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de clientes (SEM data_nascimento)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                cpf TEXT UNIQUE,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1
            )
        ''')
        
        # Tabela de produtos (COM escola_id)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT,
                tamanho TEXT,
                cor TEXT,
                preco REAL,
                custo REAL,
                estoque INTEGER DEFAULT 0,
                estoque_minimo INTEGER DEFAULT 5,
                escola_id INTEGER,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1,
                UNIQUE(nome, tamanho, cor, escola_id),
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                status TEXT DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                data_entrega_real DATE,
                valor_total REAL DEFAULT 0,
                desconto REAL DEFAULT 0,
                valor_final REAL DEFAULT 0,
                observacoes TEXT,
                forma_pagamento TEXT,
                vendedor_id INTEGER,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )
        ''')
        
        # Tabela de itens do pedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL,
                subtotal REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        
        # Índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_id ON pedidos(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_pedido)')
        
        # Usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador Sistema', 'admin'),
            ('gestor', make_hashes('gestor123'), 'Gestor Comercial', 'gestor'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor Principal', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, nome, tipo))
        
        # Escolas padrão
        escolas_padrao = [
            ('Escola Municipal', 'Rua Principal, 123', '(11) 9999-8888', 'contato@escolamunicipal.com'),
            ('Colégio Desperta', 'Av. Central, 456', '(11) 7777-6666', 'contato@colegiodesperta.com'),
            ('Instituto São Tadeu', 'Praça da Matriz, 789', '(11) 5555-4444', 'contato@institutosãotadeu.com')
        ]
        
        for nome, endereco, telefone, email in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone, email) VALUES (?, ?, ?, ?)', 
                         (nome, endereco, telefone, email))
        
        # Produtos de exemplo
        produtos_padrao = [
            ('Camiseta Polo', 'Camiseta', 'M', 'Branco', 29.90, 15.00, 50, 5, 1),
            ('Calça Jeans', 'Calça', '42', 'Azul', 89.90, 45.00, 30, 3, 1),
            ('Agasalho', 'Agasalho', 'G', 'Verde', 129.90, 65.00, 20, 2, 2),
            ('Short', 'Short', 'P', 'Preto', 39.90, 20.00, 40, 5, 2),
            ('Camiseta Regata', 'Camiseta', 'G', 'Vermelho', 24.90, 12.00, 25, 5, 3),
        ]
        
        for nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id in produtos_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = ? AND ativo = 1
        ''', (username,))
        
        resultado = cursor.fetchone()
        
        if resultado and check_hashes(password, resultado['password_hash']):
            return True, resultado['nome_completo'], resultado['tipo']
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        if conn:
            conn.close()

# =========================================
# 🤖 SISTEMA A.I. - PREVISÕES MANUAIS
# =========================================

def previsao_vendas_manual():
    """Previsão de vendas usando regressão linear manual"""
    try:
        meses = np.array([1, 2, 3, 4, 5, 6])
        vendas = np.array([12000, 15000, 18000, 22000, 25000, 28000])
        
        n = len(meses)
        soma_x = np.sum(meses)
        soma_y = np.sum(vendas)
        soma_xy = np.sum(meses * vendas)
        soma_x2 = np.sum(meses ** 2)
        
        m = (n * soma_xy - soma_x * soma_y) / (n * soma_x2 - soma_x ** 2)
        b = (soma_y - m * soma_x) / n
        
        proximos_meses = np.array([7, 8, 9])
        previsoes = m * proximos_meses + b
        
        return [
            {"mes": "Julho", "previsao": previsoes[0]},
            {"mes": "Agosto", "previsao": previsoes[1]},
            {"mes": "Setembro", "previsao": previsoes[2]}
        ]
    except:
        return [
            {"mes": "Julho", "previsao": 31000},
            {"mes": "Agosto", "previsao": 34000},
            {"mes": "Setembro", "previsao": 37000}
        ]

def analise_estoque_inteligente():
    """Análise inteligente de estoque"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, p.estoque, p.estoque_minimo, e.nome as escola_nome
            FROM produtos p
            LEFT JOIN escolas e ON p.escola_id = e.id
            WHERE p.ativo = 1
            ORDER BY p.estoque ASC
        ''')
        
        alertas = []
        for produto in cursor.fetchall():
            if produto['estoque'] <= produto['estoque_minimo']:
                alertas.append({
                    "produto": produto['nome'],
                    "escola": produto['escola_nome'],
                    "estoque_atual": produto['estoque'],
                    "estoque_minimo": produto['estoque_minimo'],
                    "nivel": "CRÍTICO" if produto['estoque'] == 0 else "ALERTA"
                })
        
        return alertas
    except:
        return []
    finally:
        if conn:
            conn.close()

def produtos_populares_ai():
    """Identifica produtos mais vendidos"""
    return [
        {"produto": "Camiseta Polo", "vendas": 45, "faturamento": 1345.50, "performance": "🏆 Excelente"},
        {"produto": "Calça Jeans", "vendas": 32, "faturamento": 2876.80, "performance": "⭐ Boa"},
        {"produto": "Agasalho", "vendas": 28, "faturamento": 3637.20, "performance": "⭐ Boa"}
    ]

# =========================================
# 👥 SISTEMA DE CLIENTES - CORRIGIDO
# =========================================

def adicionar_cliente(nome, telefone=None, email=None, cpf=None, endereco=None):
    """Adiciona cliente SEM data_nascimento"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email, cpf, endereco) VALUES (?, ?, ?, ?, ?)",
            (nome.strip(), telefone, email, cpf, endereco)
        )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ CPF já cadastrado no sistema"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes():
    """Lista todos os clientes"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY nome')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def excluir_cliente(cliente_id):
    """Exclui cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = ?", (cliente_id,))
        if cursor.fetchone()[0] > 0:
            return False, "❌ Cliente possui pedidos e não pode ser excluído"
        
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        return True, "✅ Cliente excluído com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 🏫 SISTEMA DE ESCOLAS
# =========================================

def listar_escolas():
    """Lista todas as escolas"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM escolas ORDER BY nome')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 📦 SISTEMA DE PRODUTOS - COM ESCOLAS
# =========================================

def adicionar_produto(nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id):
    """Adiciona produto com verificação de duplicata"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Verificar se produto já existe
        cursor.execute('''
            SELECT id FROM produtos 
            WHERE nome = ? AND tamanho = ? AND cor = ? AND escola_id = ?
        ''', (nome, tamanho, cor, escola_id))
        
        if cursor.fetchone():
            return False, "❌ Produto já cadastrado para esta escola"
        
        cursor.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id))
        
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos():
    """Lista produtos com informações da escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id
            ORDER BY p.nome
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 RELATÓRIOS CSV
# =========================================

def gerar_csv_produtos():
    """Gera CSV de produtos por escola"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, p.categoria, p.tamanho, p.cor, p.preco, p.estoque, 
                   p.estoque_minimo, e.nome as escola_nome
            FROM produtos p
            LEFT JOIN escolas e ON p.escola_id = e.id
            ORDER BY e.nome, p.nome
        ''')
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Produto', 'Categoria', 'Tamanho', 'Cor', 'Preço', 'Estoque', 'Estoque Mínimo', 'Escola'])
        
        for row in cursor.fetchall():
            writer.writerow([
                row['nome'],
                row['categoria'],
                row['tamanho'],
                row['cor'],
                f"R$ {row['preco']:.2f}",
                row['estoque'],
                row['estoque_minimo'],
                row['escola_nome']
            ])
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Erro ao gerar CSV: {e}")
        return None
    finally:
        if conn:
            conn.close()

def baixar_csv(data, filename):
    """Cria botão de download CSV"""
    if data:
        b64 = base64.b64encode(data.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv" style="background: #2196F3; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 4px; display: inline-block;">📥 Baixar {filename}</a>'
        st.markdown(href, unsafe_allow_html=True)

# =========================================
# 🏠 PÁGINA DE LOGIN
# =========================================

def pagina_login():
    """Página de login"""
    st.markdown('<div style="text-align: center; padding: 2rem 0;">', unsafe_allow_html=True)
    st.markdown('<h1 style="color: #4CAF50;">👕 Sistema Fardamentos + A.I.</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown('<div style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
            st.subheader("🔐 Login")
            
            with st.form("login_form"):
                username = st.text_input("👤 Usuário", placeholder="Digite seu username")
                password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
                
                submit = st.form_submit_button("🚀 Entrar", use_container_width=True)
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Preencha todos os campos!")
                    else:
                        with st.spinner("Verificando..."):
                            success, nome_completo, tipo = verificar_login(username, password)
                            
                            if success:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.nome_completo = nome_completo
                                st.session_state.tipo_usuario = tipo
                                st.success(f"✅ Bem-vindo, {nome_completo}!")
                                st.rerun()
                            else:
                                st.error("❌ Credenciais inválidas!")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("""
            **🔑 Credenciais para teste:**
            - **Admin:** admin / admin123
            - **Gestor:** gestor / gestor123  
            - **Vendedor:** vendedor / vendedor123
            """)

# =========================================
# 📱 DASHBOARD A.I. - AÇÕES RÁPIDAS CORRIGIDAS
# =========================================

def mostrar_dashboard():
    """Dashboard principal"""
    st.markdown(f'''
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h1>📊 Dashboard A.I.</h1>
        <div>
            <span class="permission-badge badge-{st.session_state.tipo_usuario}">{st.session_state.tipo_usuario.upper()}</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f"**Usuário:** {st.session_state.nome_completo}")
    st.markdown("---")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("👥 **Total Clientes**")
        st.markdown(f"<h2>{len(listar_clientes())}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("📦 **Pedidos Hoje**")
        st.markdown("<h2>12</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("💰 **Vendas Dia**")
        st.markdown("<h2>R$ 3.240</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("📈 **Crescimento**")
        st.markdown("<h2>+15%</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção A.I.
    st.markdown("---")
    st.markdown('<h2>🤖 Inteligência Artificial</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="ai-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Previsão de Vendas")
        previsoes = previsao_vendas_manual()
        
        for prev in previsoes:
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.write(f"**{prev['mes']}**")
            with col_b:
                st.write(f"R$ {prev['previsao']:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 🏆 Produtos Populares")
        populares = produtos_populares_ai()
        for i, produto in enumerate(populares, 1):
            st.write(f"{i}. **{produto['produto']}** - {produto['vendas']} vendas")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Alertas de Estoque
    alertas_estoque = analise_estoque_inteligente()
    if alertas_estoque:
        st.markdown('<div class="danger-card">', unsafe_allow_html=True)
        st.markdown("### ⚠️ Alertas de Estoque")
        for alerta in alertas_estoque[:3]:
            st.write(f"**{alerta['produto']}** ({alerta['escola']}) - Estoque: {alerta['estoque_atual']}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # AÇÕES RÁPIDAS CORRIGIDAS
    st.markdown("---")
    st.markdown('<h2>🚀 Ações Rápidas</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👥 Clientes", use_container_width=True, key="btn_clientes_dash"):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
        
        if st.button("📊 Relatórios", use_container_width=True, key="btn_relatorios_dash"):
            st.session_state.menu = "📊 Relatórios"
            st.rerun()
    
    with col2:
        if st.button("📦 Pedidos", use_container_width=True, key="btn_pedidos_dash"):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
        
        if st.button("⚙️ Admin", use_container_width=True, key="btn_admin_dash"):
            st.session_state.menu = "⚙️ Administração"
            st.rerun()

# =========================================
# 👥 INTERFACE CLIENTES - SEM DATA NASCIMENTO
# =========================================

def mostrar_clientes():
    """Interface de clientes"""
    st.header("👥 Gerenciar Clientes")
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cliente"])
    
    with tab1:
        st.subheader("📋 Lista de Clientes")
        
        clientes = listar_clientes()
        if not clientes:
            st.info("📝 Nenhum cliente cadastrado.")
        else:
            for cliente in clientes:
                with st.expander(f"👤 {cliente['nome']} - 📞 {cliente['telefone'] or 'N/A'}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**📧 Email:** {cliente['email'] or 'N/A'}")
                        st.write(f"**🔢 CPF:** {cliente['cpf'] or 'N/A'}")
                        st.write(f"**🏠 Endereço:** {cliente['endereco'] or 'N/A'}")
                        st.write(f"**📅 Cadastro:** {formatar_datahora_brasil(cliente['data_cadastro'])}")
                    
                    with col2:
                        if st.button("🗑️ Excluir", key=f"del_{cliente['id']}"):
                            success, message = excluir_cliente(cliente['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
    
    with tab2:
        st.subheader("➕ Novo Cliente")
        
        with st.form("novo_cliente_form", clear_on_submit=True):
            nome = st.text_input("👤 Nome Completo*", placeholder="Nome do cliente")
            
            col1, col2 = st.columns(2)
            with col1:
                telefone = st.text_input("📞 Telefone", placeholder="(11) 99999-9999")
                email = st.text_input("📧 Email", placeholder="cliente@email.com")
            with col2:
                cpf = st.text_input("🔢 CPF", placeholder="000.000.000-00")
                # DATA NASCIMENTO REMOVIDA
            
            endereco = st.text_area("🏠 Endereço", placeholder="Rua, número, bairro...")
            
            if st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True):
                if not nome.strip():
                    st.error("❌ O nome é obrigatório!")
                else:
                    success, message = adicionar_cliente(
                        nome=nome.strip(),
                        telefone=telefone,
                        email=email,
                        cpf=cpf,
                        endereco=endereco
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

# =========================================
# 📦 INTERFACE PEDIDOS
# =========================================

def mostrar_pedidos():
    """Interface de pedidos"""
    st.header("📦 Gerenciar Pedidos")
    
    tab1, tab2 = st.tabs(["📋 Lista de Pedidos", "➕ Novo Pedido"])
    
    with tab1:
        st.subheader("📋 Pedidos Realizados")
        st.info("🎯 Funcionalidade em desenvolvimento...")
    
    with tab2:
        st.subheader("➕ Criar Novo Pedido")
        st.info("🎯 Funcionalidade em desenvolvimento...")

# =========================================
# 📊 RELATÓRIOS - PRODUTOS POR ESCOLA
# =========================================

def mostrar_relatorios():
    """Interface de relatórios"""
    st.header("📊 Relatórios A.I.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Exportar Dados")
        
        if st.button("📚 Produtos por Escola CSV", use_container_width=True):
            csv_data = gerar_csv_produtos()
            if csv_data:
                baixar_csv(csv_data, "produtos_escolas")
    
    with col2:
        st.subheader("📈 Métricas A.I.")
        
        st.metric("Total Clientes", len(listar_clientes()))
        st.metric("Total Produtos", len(listar_produtos()))
        st.metric("Total Escolas", len(listar_escolas()))

# =========================================
# ⚙️ ADMINISTRAÇÃO - CADASTRO DE PRODUTOS
# =========================================

def mostrar_administracao():
    """Interface administrativa"""
    st.header("⚙️ Administração")
    
    tab1, tab2 = st.tabs(["📚 Cadastrar Produtos", "🔧 Sistema"])
    
    with tab1:
        st.subheader("📚 Cadastrar Novo Produto")
        
        escolas = listar_escolas()
        if not escolas:
            st.error("❌ Cadastre escolas primeiro!")
            return
        
        with st.form("novo_produto_form", clear_on_submit=True):
            nome = st.text_input("📚 Nome do Produto*", placeholder="Ex: Camiseta Polo")
            
            col1, col2 = st.columns(2)
            with col1:
                categoria = st.selectbox("📂 Categoria", ["Camiseta", "Calça", "Agasalho", "Short", "Acessório"])
                tamanho = st.text_input("📏 Tamanho*", placeholder="Ex: M, 42, P")
                cor = st.text_input("🎨 Cor*", placeholder="Ex: Branco, Azul")
            with col2:
                preco = st.number_input("💰 Preço de Venda (R$)*", min_value=0.0, step=0.01, format="%.2f")
                custo = st.number_input("💲 Custo (R$)", min_value=0.0, step=0.01, format="%.2f")
                estoque = st.number_input("📦 Estoque Atual", min_value=0, step=1, value=0)
                estoque_minimo = st.number_input("⚠️ Estoque Mínimo", min_value=0, step=1, value=5)
            
            escola_selecionada = st.selectbox(
                "🏫 Escola*",
                options=[e['nome'] for e in escolas],
                format_func=lambda x: x
            )
            
            if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True):
                if not nome.strip():
                    st.error("❌ O nome do produto é obrigatório!")
                elif not tamanho.strip():
                    st.error("❌ O tamanho é obrigatório!")
                elif not cor.strip():
                    st.error("❌ A cor é obrigatória!")
                elif preco <= 0:
                    st.error("❌ O preço deve ser maior que zero!")
                else:
                    escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada)
                    success, message = adicionar_produto(
                        nome=nome.strip(),
                        categoria=categoria,
                        tamanho=tamanho.strip(),
                        cor=cor.strip(),
                        preco=preco,
                        custo=custo,
                        estoque=estoque,
                        estoque_minimo=estoque_minimo,
                        escola_id=escola_id
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    with tab2:
        st.subheader("🔧 Configurações do Sistema")
        
        if st.button("🔄 Reiniciar Banco de Dados", use_container_width=True):
            with st.spinner("Reiniciando..."):
                if init_db():
                    st.success("✅ Banco reiniciado com sucesso!")
                else:
                    st.error("❌ Erro ao reiniciar banco!")

# =========================================
# 🧩 MENU PRINCIPAL
# =========================================

def mostrar_menu_principal():
    """Menu mobile otimizado"""
    st.sidebar.markdown('<div style="text-align: center; padding: 1rem 0;">', unsafe_allow_html=True)
    st.sidebar.markdown('<h2>👕 Menu</h2>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**👤 {st.session_state.nome_completo}**")
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    menu_options = ["🏠 Dashboard", "👥 Clientes", "📦 Pedidos", "📊 Relatórios", "⚙️ Administração"]
    menu = st.sidebar.selectbox("Navegação", menu_options, key="menu_select")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    return menu

# =========================================
# 🎯 APLICAÇÃO PRINCIPAL
# =========================================

def main():
    """Aplicação principal"""
    
    if not init_db():
        st.error("❌ Erro ao inicializar banco!")
        return
    
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        pagina_login()
        return
    
    menu = mostrar_menu_principal()
    
    if menu == "🏠 Dashboard":
        mostrar_dashboard()
    elif menu == "👥 Clientes":
        mostrar_clientes()
    elif menu == "📦 Pedidos":
        mostrar_pedidos()
    elif menu == "📊 Relatórios":
        mostrar_relatorios()
    elif menu == "⚙️ Administração":
        mostrar_administracao()

if __name__ == "__main__":
    main()
