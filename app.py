import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import numpy as np
import io
import csv
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import tempfile
import os

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos + A.I.",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Mobile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.75rem;
        }
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px;
            padding: 0.75rem;
        }
    }
    .admin-card { border-left: 4px solid #dc3545; }
    .gestor-card { border-left: 4px solid #ffc107; }
    .vendedor-card { border-left: 4px solid #28a745; }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .ai-insight-positive { 
        border-left: 4px solid #28a745;
        background: #f8fff9;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-insight-warning { 
        border-left: 4px solid #ffc107;
        background: #fffbf0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-insight-danger { 
        border-left: 4px solid #dc3545;
        background: #fff5f5;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .pagination-btn {
        margin: 0 0.2rem;
        padding: 0.3rem 0.6rem;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🇧🇷 FUNÇÕES DE FORMATAÇÃO BRASILEIRA
# =========================================

def formatar_data_brasil(data_string):
    """Converte data do banco (YYYY-MM-DD) para formato brasileiro (DD/MM/YYYY)"""
    if not data_string:
        return "N/A"
    
    try:
        # Se for objeto date/datetime
        if isinstance(data_string, (date, datetime)):
            return data_string.strftime("%d/%m/%Y")
            
        # Se já estiver no formato brasileiro, retorna como está
        if '/' in str(data_string):
            return str(data_string)
            
        # Converte do formato do banco para brasileiro
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
        # Para datetime completo
        if ' ' in str(datahora_string):
            data_part, hora_part = str(datahora_string).split(' ', 1)
            data_brasil = formatar_data_brasil(data_part)
            # Formatar hora (remove segundos se necessário)
            hora_part = hora_part[:5]  # Mantém apenas HH:MM
            return f"{data_brasil} {hora_part}"
        else:
            return formatar_data_brasil(datahora_string)
    except:
        return str(datahora_string)

def data_atual_brasil():
    """Retorna data atual no formato brasileiro"""
    return datetime.now().strftime("%d/%m/%Y")

def hora_atual_brasil():
    """Retorna hora atual no formato brasileiro"""
    return datetime.now().strftime("%H:%M")

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
        # Otimizações para melhor performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados com otimizações"""
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
        
        # Tabela de clientes (SEM VÍNCULO COM ESCOLA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_nascimento DATE,
                cpf TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1
            )
        ''')
        
        # Tabela de produtos
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
                FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                FOREIGN KEY (vendedor_id) REFERENCES usuarios (id)
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
        
        # Índices para melhor performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_id ON pedidos(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_pedido)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedido_itens_pedido ON pedido_itens(pedido_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedido_itens_produto ON pedido_itens(produto_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produtos_escola ON produtos(escola_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_data ON clientes(data_cadastro)')
        
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
            ('Blusa Moletom', 'Agasalho', 'M', 'Cinza', 79.90, 35.00, 35, 4, 1),
            ('Bermuda', 'Short', '38', 'Azul Marinho', 49.90, 22.00, 28, 3, 2),
        ]
        
        for nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id in produtos_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {str(e)}")
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
# 📊 FUNÇÕES DO SISTEMA - OTIMIZADAS
# =========================================

def listar_usuarios():
    """Lista todos os usuários"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, nome_completo, tipo, ativo FROM usuarios ORDER BY username')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []
    finally:
        if conn:
            conn.close()

def criar_usuario(username, password, nome_completo, tipo):
    """Cria novo usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        password_hash = make_hashes(password)
        
        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, tipo)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, nome_completo, tipo))
        
        conn.commit()
        return True, "✅ Usuário criado com sucesso!"
        
    except sqlite3.IntegrityError:
        return False, "❌ Username já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def alterar_senha_usuario(username, nova_senha):
    """Altera senha do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        nova_senha_hash = make_hashes(nova_senha)
        
        cursor.execute('''
            UPDATE usuarios SET password_hash = ? WHERE username = ?
        ''', (nova_senha_hash, username))
        
        conn.commit()
        return True, "✅ Senha alterada com sucesso!"
        
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def adicionar_escola(nome, endereco, telefone, email):
    """Adiciona nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO escolas (nome, endereco, telefone, email)
            VALUES (?, ?, ?, ?)
        ''', (nome, endereco, telefone, email))
        
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Escola já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def editar_escola(escola_id, nome, endereco, telefone, email):
    """Edita escola existente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE escolas 
            SET nome = ?, endereco = ?, telefone = ?, email = ?
            WHERE id = ?
        ''', (nome, endereco, telefone, email, escola_id))
        
        conn.commit()
        return True, "✅ Escola atualizada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Nome da escola já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def excluir_escola(escola_id):
    """Exclui escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Verificar se há produtos vinculados
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE escola_id = ?", (escola_id,))
        if cursor.fetchone()[0] > 0:
            return False, "❌ Escola possui produtos vinculados"
        
        cursor.execute("DELETE FROM escolas WHERE id = ?", (escola_id,))
        conn.commit()
        return True, "✅ Escola excluída com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def adicionar_cliente(nome, telefone, email, data_nascimento=None, cpf=None, endereco=None):
    """Adiciona cliente SEM vínculo com escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email, data_nascimento, cpf, endereco) VALUES (?, ?, ?, ?, ?, ?)",
            (nome, telefone, email, data_nascimento, cpf, endereco)
        )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes_paginado(offset=0, limit=50, busca=None):
    """Lista clientes com paginação"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if busca:
            cursor.execute('''
                SELECT * FROM clientes 
                WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
                ORDER BY nome
                LIMIT ? OFFSET ?
            ''', (f'%{busca}%', f'%{busca}%', f'%{busca}%', limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM clientes 
                ORDER BY nome
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def contar_clientes(busca=None):
    """Conta total de clientes para paginação"""
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        if busca:
            cursor.execute('''
                SELECT COUNT(*) FROM clientes 
                WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
            ''', (f'%{busca}%', f'%{busca}%', f'%{busca}%'))
        else:
            cursor.execute('SELECT COUNT(*) FROM clientes')
        return cursor.fetchone()[0]
    except Exception as e:
        st.error(f"Erro ao contar clientes: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Verificar se cliente tem pedidos
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

def editar_cliente(cliente_id, nome, telefone, email, data_nascimento=None, cpf=None, endereco=None):
    """Edita cliente existente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE clientes 
            SET nome = ?, telefone = ?, email = ?, data_nascimento = ?, cpf = ?, endereco = ?
            WHERE id = ?
        ''', (nome, telefone, email, data_nascimento, cpf, endereco, cliente_id))
        
        conn.commit()
        return True, "✅ Cliente atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def produto_existe(nome, tamanho, cor, escola_id):
    """Verifica se produto já existe"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM produtos 
            WHERE nome = ? AND tamanho = ? AND cor = ? AND escola_id = ?
        ''', (nome, tamanho, cor, escola_id))
        return cursor.fetchone() is not None
    finally:
        if conn:
            conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        # Verificar se produto já existe
        if produto_existe(nome, tamanho, cor, escola_id):
            return False, "❌ Produto já existe para esta escola"
        
        cursor = conn.cursor()
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

def listar_produtos(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if escola_id:
            cursor.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = ?
                ORDER BY p.nome
            ''', (escola_id,))
        else:
            cursor.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY p.escola_id, p.nome
            ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM escolas ORDER BY nome")
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (nova_quantidade, produto_id))
        conn.commit()
        return True, "✅ Estoque atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def adicionar_pedido(cliente_id, itens, data_entrega, observacoes, desconto=0, forma_pagamento=None, vendedor_id=None):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        valor_total = sum(item['subtotal'] for item in itens)
        valor_final = valor_total - desconto
        
        # Validar data de entrega
        if isinstance(data_entrega, date):
            data_entrega_str = data_entrega.strftime("%Y-%m-%d")
        else:
            data_entrega_str = data_entrega
        
        # Verificar estoque antes de processar
        for item in itens:
            cursor.execute("SELECT estoque FROM produtos WHERE id = ?", (item['produto_id'],))
            produto = cursor.fetchone()
            if not produto or produto['estoque'] < item['quantidade']:
                return False, f"❌ Estoque insuficiente para o produto {item['nome']}"
        
        # Inserir pedido
        cursor.execute('''
            INSERT INTO pedidos (cliente_id, data_entrega_prevista, valor_total, desconto, valor_final, observacoes, forma_pagamento, vendedor_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, data_entrega_str, valor_total, desconto, valor_final, observacoes, forma_pagamento, vendedor_id))
        
        pedido_id = cursor.lastrowid
        
        # Inserir itens do pedido
        for item in itens:
            cursor.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            # Atualizar estoque
            cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                         (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_pedidos_paginado(usuario_tipo, offset=0, limit=50, filtro_status=None, busca_cliente=None):
    """Lista pedidos com paginação"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        query = '''
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
        '''
        params = []
        
        where_conditions = []
        
        if filtro_status and filtro_status != "Todos":
            where_conditions.append("p.status = ?")
            params.append(filtro_status)
            
        if busca_cliente:
            where_conditions.append("c.nome LIKE ?")
            params.append(f'%{busca_cliente}%')
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += " ORDER BY p.data_pedido DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def contar_pedidos(filtro_status=None, busca_cliente=None):
    """Conta total de pedidos para paginação"""
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM pedidos p JOIN clientes c ON p.cliente_id = c.id"
        params = []
        
        where_conditions = []
        
        if filtro_status and filtro_status != "Todos":
            where_conditions.append("p.status = ?")
            params.append(filtro_status)
            
        if busca_cliente:
            where_conditions.append("c.nome LIKE ?")
            params.append(f'%{busca_cliente}%')
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    except Exception as e:
        st.error(f"Erro ao contar pedidos: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def atualizar_status_pedido(pedido_id, novo_status, data_entrega_real=None):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        if novo_status == 'Entregue' and data_entrega_real:
            cursor.execute('''
                UPDATE pedidos 
                SET status = ?, data_entrega_real = ? 
                WHERE id = ?
            ''', (novo_status, data_entrega_real, pedido_id))
        else:
            cursor.execute('''
                UPDATE pedidos 
                SET status = ? 
                WHERE id = ?
            ''', (novo_status, pedido_id))
        
        conn.commit()
        return True, "✅ Status do pedido atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Restaurar estoque dos itens
        cursor.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
        itens = cursor.fetchall()
        
        for item in itens:
            cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", 
                         (item['quantidade'], item['produto_id']))
        
        # Excluir itens do pedido
        cursor.execute("DELETE FROM pedido_itens WHERE pedido_id = ?", (pedido_id,))
        
        # Excluir pedido
        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "✅ Pedido excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def obter_detalhes_pedido(pedido_id):
    """Obtém detalhes completos de um pedido"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Buscar informações do pedido
        cursor.execute('''
            SELECT p.*, c.nome as cliente_nome, c.telefone, c.email, c.endereco,
                   u.nome_completo as vendedor_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN usuarios u ON p.vendedor_id = u.id
            WHERE p.id = ?
        ''', (pedido_id,))
        
        pedido = cursor.fetchone()
        
        if not pedido:
            return None
        
        # Buscar itens do pedido
        cursor.execute('''
            SELECT pi.*, pr.nome as produto_nome, pr.tamanho, pr.cor, e.nome as escola_nome
            FROM pedido_itens pi
            JOIN produtos pr ON pi.produto_id = pr.id
            LEFT JOIN escolas e ON pr.escola_id = e.id
            WHERE pi.pedido_id = ?
        ''', (pedido_id,))
        
        itens = cursor.fetchall()
        
        return {
            'pedido': dict(pedido),
            'itens': [dict(item) for item in itens]
        }
        
    except Exception as e:
        st.error(f"Erro ao buscar detalhes do pedido: {e}")
        return None
    finally:
        if conn:
            conn.close()

def exportar_pedidos_para_csv():
    """Exporta pedidos para CSV"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                p.id as pedido_id,
                c.nome as cliente,
                p.status,
                p.data_pedido,
                p.data_entrega_prevista,
                p.data_entrega_real,
                p.valor_total,
                p.desconto,
                p.valor_final,
                p.forma_pagamento,
                GROUP_CONCAT(pr.nome || ' (' || pi.quantidade || 'x)') as itens
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            JOIN pedido_itens pi ON p.id = pi.pedido_id
            JOIN produtos pr ON pi.produto_id = pr.id
            GROUP BY p.id
            ORDER BY p.data_pedido DESC
        ''')
        
        pedidos = cursor.fetchall()
        
        if not pedidos:
            return None
            
        # Criar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow(['ID', 'Cliente', 'Status', 'Data Pedido', 'Entrega Prevista', 
                        'Entrega Real', 'Valor Total', 'Desconto', 'Valor Final', 'Pagamento', 'Itens'])
        
        # Dados
        for pedido in pedidos:
            writer.writerow([
                pedido['pedido_id'],
                pedido['cliente'],
                pedido['status'],
                formatar_datahora_brasil(pedido['data_pedido']),
                formatar_data_brasil(pedido['data_entrega_prevista']),
                formatar_data_brasil(pedido['data_entrega_real']),
                f"R$ {pedido['valor_total']:.2f}",
                f"R$ {pedido['desconto']:.2f}",
                f"R$ {pedido['valor_final']:.2f}",
                pedido['forma_pagamento'] or 'N/A',
                pedido['itens']
            ])
        
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Erro ao exportar pedidos: {e}")
        return None
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 RELATÓRIOS POR ESCOLA
# =========================================

def relatorio_vendas_por_escola(data_inicio=None, data_fim=None):
    """Gera relatório de vendas por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                e.id,
                e.nome as escola_nome,
                COUNT(DISTINCT p.id) as total_pedidos,
                SUM(p.valor_final) as valor_total_vendas,
                SUM(pi.quantidade) as total_itens_vendidos,
                AVG(p.valor_final) as ticket_medio
            FROM escolas e
            LEFT JOIN produtos pr ON e.id = pr.escola_id
            LEFT JOIN pedido_itens pi ON pr.id = pi.produto_id
            LEFT JOIN pedidos p ON pi.pedido_id = p.id
        '''
        
        params = []
        
        if data_inicio and data_fim:
            query += " WHERE p.data_pedido BETWEEN ? AND ?"
            params.extend([data_inicio, data_fim])
        
        query += '''
            GROUP BY e.id
            ORDER BY valor_total_vendas DESC
        '''
        
        cursor.execute(query, params)
        return cursor.fetchall()
        
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return []
    finally:
        if conn:
            conn.close()

def relatorio_produtos_por_escola(escola_id, data_inicio=None, data_fim=None):
    """Gera relatório de produtos por escola específica"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                pr.nome,
                pr.categoria,
                pr.tamanho,
                pr.cor,
                SUM(pi.quantidade) as total_vendido,
                SUM(pi.subtotal) as valor_total,
                pr.estoque,
                pr.preco
            FROM produtos pr
            LEFT JOIN pedido_itens pi ON pr.id = pi.produto_id
            LEFT JOIN pedidos p ON pi.pedido_id = p.id
            WHERE pr.escola_id = ?
        '''
        
        params = [escola_id]
        
        if data_inicio and data_fim:
            query += " AND p.data_pedido BETWEEN ? AND ?"
            params.extend([data_inicio, data_fim])
        
        query += '''
            GROUP BY pr.id
            ORDER BY total_vendido DESC
        '''
        
        cursor.execute(query, params)
        return cursor.fetchall()
        
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return []
    finally:
        if conn:
            conn.close()

def relatorio_estoque_por_escola():
    """Gera relatório de estoque por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                e.id,
                e.nome as escola_nome,
                COUNT(pr.id) as total_produtos,
                SUM(pr.estoque) as total_estoque,
                SUM(CASE WHEN pr.estoque <= pr.estoque_minimo THEN 1 ELSE 0 END) as produtos_estoque_baixo,
                SUM(pr.estoque * pr.preco) as valor_total_estoque
            FROM escolas e
            LEFT JOIN produtos pr ON e.id = pr.escola_id
            WHERE pr.ativo = 1 OR pr.ativo IS NULL
            GROUP BY e.id
            ORDER BY valor_total_estoque DESC
        ''')
        
        return cursor.fetchall()
        
    except Exception as e:
        st.error(f"Erro ao gerar relatório de estoque: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 🧾 GERADOR DE PDF
# =========================================

def gerar_pdf_pedido(pedido_id):
    """Gera PDF do pedido"""
    detalhes = obter_detalhes_pedido(pedido_id)
    if not detalhes:
        return None
    
    try:
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilo personalizado
        estilo_titulo = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centralizado
        )
        
        estilo_normal = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Título
        titulo = Paragraph(f"PEDIDO #{pedido_id}", estilo_titulo)
        elements.append(titulo)
        elements.append(Spacer(1, 20))
        
        # Informações do pedido
        pedido = detalhes['pedido']
        info_pedido = [
            [Paragraph("<b>Data do Pedido:</b>", estilo_normal), Paragraph(formatar_datahora_brasil(pedido['data_pedido']), estilo_normal)],
            [Paragraph("<b>Status:</b>", estilo_normal), Paragraph(pedido['status'], estilo_normal)],
            [Paragraph("<b>Cliente:</b>", estilo_normal), Paragraph(pedido['cliente_nome'], estilo_normal)],
            [Paragraph("<b>Telefone:</b>", estilo_normal), Paragraph(pedido['telefone'] or 'N/A', estilo_normal)],
            [Paragraph("<b>Email:</b>", estilo_normal), Paragraph(pedido['email'] or 'N/A', estilo_normal)],
            [Paragraph("<b>Endereço:</b>", estilo_normal), Paragraph(pedido['endereco'] or 'N/A', estilo_normal)],
            [Paragraph("<b>Entrega Prevista:</b>", estilo_normal), Paragraph(formatar_data_brasil(pedido['data_entrega_prevista']), estilo_normal)],
            [Paragraph("<b>Forma de Pagamento:</b>", estilo_normal), Paragraph(pedido['forma_pagamento'] or 'N/A', estilo_normal)],
        ]
        
        if pedido['vendedor_nome']:
            info_pedido.append([Paragraph("<b>Vendedor:</b>", estilo_normal), Paragraph(pedido['vendedor_nome'], estilo_normal)])
        
        tabela_info = Table(info_pedido, colWidths=[2*inch, 4*inch])
        tabela_info.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(tabela_info)
        elements.append(Spacer(1, 20))
        
        # Itens do pedido
        elements.append(Paragraph("<b>ITENS DO PEDIDO</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        dados_itens = [['Produto', 'Escola', 'Tamanho', 'Cor', 'Qtd', 'Preço Unit.', 'Subtotal']]
        
        for item in detalhes['itens']:
            dados_itens.append([
                item['produto_nome'],
                item['escola_nome'],
                item['tamanho'],
                item['cor'],
                str(item['quantidade']),
                f"R$ {item['preco_unitario']:.2f}",
                f"R$ {item['subtotal']:.2f}"
            ])
        
        tabela_itens = Table(dados_itens, colWidths=[1.5*inch, 1.2*inch, 0.6*inch, 0.7*inch, 0.5*inch, 0.8*inch, 0.8*inch])
        tabela_itens.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(tabela_itens)
        elements.append(Spacer(1, 20))
        
        # Totais
        elementos_totais = [
            [Paragraph("<b>Valor Total:</b>", estilo_normal), Paragraph(f"R$ {pedido['valor_total']:.2f}", estilo_normal)],
            [Paragraph("<b>Desconto:</b>", estilo_normal), Paragraph(f"R$ {pedido['desconto']:.2f}", estilo_normal)],
            [Paragraph("<b>VALOR FINAL:</b>", styles['Heading2']), Paragraph(f"<b>R$ {pedido['valor_final']:.2f}</b>", styles['Heading2'])]
        ]
        
        tabela_totais = Table(elementos_totais, colWidths=[2*inch, 2*inch])
        tabela_totais.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 2), (-1, 2), 12),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 12),
        ]))
        
        elements.append(tabela_totais)
        
        # Observações
        if pedido['observacoes']:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("<b>Observações:</b>", styles['Heading2']))
            elements.append(Paragraph(pedido['observacoes'], estilo_normal))
        
        # Rodapé
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"Emitido em: {data_atual_brasil()} às {hora_atual_brasil()}", styles['Normal']))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

def criar_botao_download_pdf(pedido_id, texto="📄 Gerar PDF"):
    """Cria botão para download do PDF"""
    pdf_buffer = gerar_pdf_pedido(pedido_id)
    if pdf_buffer:
        b64 = base64.b64encode(pdf_buffer.getvalue()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="pedido_{pedido_id}.pdf" style="background-color: #4CAF50; color: white; padding: 8px 16px; text-align: center; text-decoration: none; display: inline-block; border-radius: 4px; border: none;">{texto}</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error("Erro ao gerar PDF")

# =========================================
# 🤖 SISTEMA DE A.I. E ANÁLISES
# =========================================

def gerar_metricas_avancadas():
    """Gera métricas avançadas para dashboard"""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        # Vendas por status
        cursor.execute('''
            SELECT status, COUNT(*) as quantidade, SUM(valor_total) as total
            FROM pedidos 
            GROUP BY status
        ''')
        vendas_status = cursor.fetchall()
        
        # Produtos mais vendidos
        cursor.execute('''
            SELECT pr.nome, SUM(pi.quantidade) as total_vendido
            FROM pedido_itens pi
            JOIN produtos pr ON pi.produto_id = pr.id
            GROUP BY pr.id
            ORDER BY total_vendido DESC
            LIMIT 10
        ''')
        produtos_populares = cursor.fetchall()
        
        return {
            'vendas_por_status': [dict(row) for row in vendas_status],
            'produtos_populares': [dict(row) for row in produtos_populares]
        }
        
    except Exception as e:
        st.error(f"Erro ao gerar métricas: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def previsao_vendas_simples():
    """Previsão simples de vendas usando regressão linear (sem plotly)"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Buscar dados históricos de vendas
        cursor.execute('''
            SELECT DATE(data_pedido) as data, SUM(valor_total) as total
            FROM pedidos 
            WHERE data_pedido >= date('now', '-30 days')
            GROUP BY DATE(data_pedido)
            ORDER BY data
        ''')
        
        dados = cursor.fetchall()
        
        if len(dados) < 5:
            return None
        
        # Preparar dados para o modelo
        datas = []
        totais = []
        dias_numeros = []
        
        data_minima = None
        for row in dados:
            data_str = row['data']
            total = row['total'] or 0
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
            
            if data_minima is None or data_obj < data_minima:
                data_minima = data_obj
                
            datas.append(data_obj)
            totais.append(total)
        
        # Calcular dias como números
        for data_obj in datas:
            dias = (data_obj - data_minima).days
            dias_numeros.append(dias)
        
        # Treinar modelo simples
        X = np.array(dias_numeros).reshape(-1, 1)
        y = np.array(totais)
        
        from sklearn.linear_model import LinearRegression
        modelo = LinearRegression()
        modelo.fit(X, y)
        
        # Prever próximos 7 dias
        ultimo_dia = max(dias_numeros)
        proximos_dias = np.array(range(ultimo_dia + 1, ultimo_dia + 8)).reshape(-1, 1)
        previsoes = modelo.predict(proximos_dias)
        
        # Gerar datas futuras
        ultima_data = max(datas)
        datas_futuras = [ultima_data + timedelta(days=i) for i in range(1, 8)]
        
        return {
            'datas': datas_futuras,
            'previsoes': previsoes,
            'tendencia': 'alta' if modelo.coef_[0] > 0 else 'baixa',
            'confianca': modelo.score(X, y)
        }
        
    except Exception as e:
        st.error(f"Erro na previsão: {e}")
        return None
    finally:
        if conn:
            conn.close()

def analise_estoque_otimizacao():
    """Analisa estoque e sugere otimizações"""
    produtos = listar_produtos()
    
    if not produtos:
        return []
    
    insights = []
    
    # Produtos com estoque baixo
    estoque_baixo = [p for p in produtos if p['estoque'] < p['estoque_minimo']]
    if estoque_baixo:
        insights.append({
            'tipo': 'danger',
            'titulo': '🚨 Estoque Crítico',
            'mensagem': f'{len(estoque_baixo)} produtos com estoque abaixo do mínimo',
            'detalhes': [f"{p['nome']} - {p['tamanho']} ({p['estoque']}/{p['estoque_minimo']})" for p in estoque_baixo[:3]]
        })
    
    # Produtos mais vendidos que precisam de reposição
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pr.id, pr.nome, pr.estoque, SUM(pi.quantidade) as vendidos
                FROM produtos pr
                LEFT JOIN pedido_itens pi ON pr.id = pi.produto_id
                GROUP BY pr.id
                HAVING vendidos > pr.estoque AND pr.estoque < 10
                ORDER BY vendidos DESC
                LIMIT 5
            ''')
            
            produtos_reposicao = cursor.fetchall()
            if produtos_reposicao:
                insights.append({
                    'tipo': 'warning',
                    'titulo': '📈 Produtos Populares com Estoque Baixo',
                    'mensagem': 'Estes produtos vendem bem e precisam de reposição urgente',
                    'detalhes': [f"{p['nome']} - Vendidos: {p['vendidos']}, Estoque: {p['estoque']}" for p in produtos_reposicao]
                })
        except Exception as e:
            st.error(f"Erro na análise de reposição: {e}")
        finally:
            conn.close()
    
    # Produtos com excesso de estoque
    excesso_estoque = [p for p in produtos if p['estoque'] > 100]
    if excesso_estoque:
        insights.append({
            'tipo': 'warning',
            'titulo': '📦 Excesso de Estoque',
            'mensagem': f'{len(excesso_estoque)} produtos com mais de 100 unidades em estoque',
            'detalhes': [f"{p['nome']} - {p['estoque']} unidades" for p in excesso_estoque[:3]]
        })
    
    return insights

def analise_clientes():
    """Analisa comportamento dos clientes"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Clientes que mais compram
        cursor.execute('''
            SELECT c.nome, COUNT(p.id) as total_pedidos, SUM(p.valor_total) as total_gasto
            FROM clientes c
            JOIN pedidos p ON c.id = p.cliente_id
            GROUP BY c.id
            ORDER BY total_gasto DESC
            LIMIT 5
        ''')
        
        melhores_clientes = cursor.fetchall()
        
        insights = []
        
        if melhores_clientes:
            insights.append({
                'tipo': 'positive',
                'titulo': '⭐ Clientes VIP',
                'mensagem': 'Clientes com maior valor em compras',
                'detalhes': [f"{c['nome']} - R$ {c['total_gasto']:.2f} em {c['total_pedidos']} pedidos" for c in melhores_clientes]
            })
        
        # Clientes inativos (sem pedidos nos últimos 30 dias)
        cursor.execute('''
            SELECT c.nome, MAX(p.data_pedido) as ultima_compra
            FROM clientes c
            LEFT JOIN pedidos p ON c.id = p.cliente_id
            GROUP BY c.id
            HAVING ultima_compra < date('now', '-30 days') OR ultima_compra IS NULL
            LIMIT 5
        ''')
        
        clientes_inativos = cursor.fetchall()
        
        if clientes_inativos:
            insights.append({
                'tipo': 'warning',
                'titulo': '💤 Clientes Inativos',
                'mensagem': 'Clientes sem compras há mais de 30 dias',
                'detalhes': [f"{c['nome']} - Última compra: {formatar_data_brasil(c['ultima_compra']) if c['ultima_compra'] else 'Nunca comprou'}" for c in clientes_inativos]
            })
        
        return insights
        
    except Exception as e:
        st.error(f"Erro na análise de clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def gerar_relatorio_ai():
    """Gera relatório completo com insights de A.I. (sem plotly)"""
    st.subheader("🤖 Relatório de Inteligência Artificial")
    
    with st.spinner("Analisando dados e gerando insights..."):
        
        # Métricas Avançadas
        metricas = gerar_metricas_avancadas()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_clientes = contar_clientes()
            st.metric("Total Clientes", total_clientes)
        
        with col2:
            total_pedidos = contar_pedidos()
            st.metric("Total Pedidos", total_pedidos)
        
        with col3:
            produtos = listar_produtos()
            estoque_total = sum(p['estoque'] for p in produtos)
            st.metric("Estoque Total", estoque_total)
        
        with col4:
            cursor = get_connection().cursor()
            cursor.execute("SELECT SUM(valor_final) FROM pedidos WHERE status = 'Entregue'")
            vendas_totais = cursor.fetchone()[0] or 0
            st.metric("Vendas Totais", f"R$ {vendas_totais:.2f}")
        
        st.markdown("---")
        
        # Previsão de Vendas
        st.subheader("📊 Previsão de Vendas (Próximos 7 Dias)")
        previsao = previsao_vendas_simples()
        
        if previsao:
            col1, col2 = st.columns(2)
            
            with col1:
                # Mostrar previsões em uma tabela
                st.write("**Previsões de Vendas:**")
                dados_tabela = []
                for data, previsao_valor in zip(previsao['datas'], previsao['previsoes']):
                    dados_tabela.append({
                        'Data': formatar_data_brasil(data),
                        'Previsão (R$)': f"R$ {previsao_valor:.2f}"
                    })
                
                # Exibir como tabela simples
                for item in dados_tabela:
                    st.write(f"📅 {item['Data']}: {item['Previsão (R$)']}")
            
            with col2:
                st.metric("Tendência", "📈 Alta" if previsao['tendencia'] == 'alta' else "📉 Baixa")
                st.metric("Confiança do Modelo", f"{previsao['confianca']:.1%}")
                
                st.info("💡 **Insight A.I.**: As vendas mostram tendência de **{}** para os próximos dias.".format(
                    "crescimento" if previsao['tendencia'] == 'alta' else "queda"
                ))
        else:
            st.warning("📊 Dados insuficientes para gerar previsão. Continue operando para obter insights.")
        
        st.markdown("---")
        
        # Análise de Estoque
        st.subheader("📦 Análise Inteligente de Estoque")
        insights_estoque = analise_estoque_otimizacao()
        
        if insights_estoque:
            for insight in insights_estoque:
                if insight['tipo'] == 'danger':
                    st.markdown(f'<div class="ai-insight-danger">', unsafe_allow_html=True)
                    st.error(f"**{insight['titulo']}**")
                    st.write(insight['mensagem'])
                    for detalhe in insight['detalhes']:
                        st.write(f"• {detalhe}")
                    st.markdown('</div>', unsafe_allow_html=True)
                elif insight['tipo'] == 'warning':
                    st.markdown(f'<div class="ai-insight-warning">', unsafe_allow_html=True)
                    st.warning(f"**{insight['titulo']}**")
                    st.write(insight['mensagem'])
                    for detalhe in insight['detalhes']:
                        st.write(f"• {detalhe}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="ai-insight-positive">', unsafe_allow_html=True)
                    st.success(f"**{insight['titulo']}**")
                    st.write(insight['mensagem'])
                    for detalhe in insight['detalhes']:
                        st.write(f"• {detalhe}")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.success("✅ Estoque em situação normal!")
        
        st.markdown("---")
        
        # Análise de Clientes
        st.subheader("👥 Análise Comportamental de Clientes")
        insights_clientes = analise_clientes()
        
        if insights_clientes:
            for insight in insights_clientes:
                if insight['tipo'] == 'positive':
                    st.markdown(f'<div class="ai-insight-positive">', unsafe_allow_html=True)
                    st.success(f"**{insight['titulo']}**")
                    st.write(insight['mensagem'])
                    for detalhe in insight['detalhes']:
                        st.write(f"• {detalhe}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="ai-insight-warning">', unsafe_allow_html=True)
                    st.warning(f"**{insight['titulo']}**")
                    st.write(insight['mensagem'])
                    for detalhe in insight['detalhes']:
                        st.write(f"• {detalhe}")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # Produtos Populares (sem plotly)
        if metricas and 'produtos_populares' in metricas and metricas['produtos_populares']:
            st.subheader("🏆 Produtos Mais Populares")
            
            # Mostrar como lista ordenada
            st.write("**Top 5 Produtos Mais Vendidos:**")
            for i, produto in enumerate(metricas['produtos_populares'][:5], 1):
                st.write(f"{i}. **{produto['nome']}** - {produto['total_vendido']} unidades vendidas")

# =========================================
# 🚀 INTERFACES POR TIPO DE USUÁRIO
# =========================================

def interface_admin():
    """Interface para Administrador"""
    st.header("👑 Painel do Administrador")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard", "🤖 A.I. Insights", "👥 Clientes", "👕 Produtos", "📦 Pedidos", "🏫 Escolas", "👤 Usuários", "📈 Relatórios"
    ])
    
    with tab1:
        st.subheader("📊 Visão Geral do Sistema")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_clientes = contar_clientes()
            st.metric("Total Clientes", total_clientes)
        
        with col2:
            produtos = listar_produtos()
            st.metric("Total Produtos", len(produtos))
        
        with col3:
            total_pedidos = contar_pedidos()
            st.metric("Total Pedidos", total_pedidos)
        
        with col4:
            estoque_baixo = len([p for p in produtos if p['estoque'] < p['estoque_minimo']])
            st.metric("Alerta Estoque", estoque_baixo)
        
        # Data e hora atual
        st.write(f"**📅 Data atual:** {data_atual_brasil()}")
        st.write(f"**🕒 Hora atual:** {hora_atual_brasil()}")
        
        # Métricas rápidas de A.I.
        st.subheader("🚨 Alertas Rápidos A.I.")
        insights = analise_estoque_otimizacao()
        if insights:
            for insight in insights[:2]:  # Mostra apenas os 2 primeiros alertas
                if insight['tipo'] == 'danger':
                    st.error(f"**{insight['titulo']}**: {insight['mensagem']}")
                else:
                    st.warning(f"**{insight['titulo']}**: {insight['mensagem']}")
        else:
            st.success("✅ Nenhum alerta crítico no momento")
    
    with tab2:
        gerar_relatorio_ai()
    
    with tab3:
        st.subheader("👥 Gestão de Clientes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Cliente")
            with st.form("novo_cliente_admin", clear_on_submit=True):
                nome = st.text_input("Nome completo*")
                telefone = st.text_input("Telefone*")
                email = st.text_input("Email")
                data_nascimento = st.date_input("Data de Nascimento", max_value=date.today())
                cpf = st.text_input("CPF")
                endereco = st.text_area("Endereço")
                
                if st.form_submit_button("✅ Cadastrar Cliente"):
                    if nome and telefone:
                        sucesso, msg = adicionar_cliente(nome, telefone, email, data_nascimento, cpf, endereco)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome e telefone são obrigatórios!")
        
        with col2:
            st.write("📋 Clientes Cadastrados")
            
            # Busca e paginação
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                busca_cliente = st.text_input("🔍 Buscar cliente", placeholder="Nome, telefone ou email")
            with col_filter:
                limite_clientes = st.selectbox("Itens por página", [25, 50, 100], index=1)
            
            # Paginação
            if 'pagina_clientes' not in st.session_state:
                st.session_state.pagina_clientes = 0
            
            total_clientes = contar_clientes(busca_cliente)
            total_paginas = max(1, (total_clientes + limite_clientes - 1) // limite_clientes)
            
            clientes = listar_clientes_paginado(
                offset=st.session_state.pagina_clientes * limite_clientes,
                limit=limite_clientes,
                busca=busca_cliente
            )
            
            # Controles de paginação
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("⬅️ Anterior", disabled=st.session_state.pagina_clientes == 0):
                    st.session_state.pagina_clientes -= 1
                    st.rerun()
            with col_info:
                st.write(f"Página {st.session_state.pagina_clientes + 1} de {total_paginas} ({total_clientes} clientes)")
            with col_next:
                if st.button("Próxima ➡️", disabled=st.session_state.pagina_clientes >= total_paginas - 1):
                    st.session_state.pagina_clientes += 1
                    st.rerun()
            
            for cliente in clientes:
                with st.expander(f"👤 {cliente['nome']}", expanded=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Telefone:** {cliente['telefone'] or 'N/A'}")
                        st.write(f"**Email:** {cliente['email'] or 'N/A'}")
                        if cliente['data_nascimento']:
                            st.write(f"**Nascimento:** {formatar_data_brasil(cliente['data_nascimento'])}")
                    with col_b:
                        st.write(f"**CPF:** {cliente['cpf'] or 'N/A'}")
                        st.write(f"**Endereço:** {cliente['endereco'] or 'N/A'}")
                        st.write(f"**Cadastro:** {formatar_data_brasil(cliente['data_cadastro'])}")
                    
                    col_c, col_d = st.columns(2)
                    with col_c:
                        if st.button("✏️ Editar", key=f"edit_cli_{cliente['id']}"):
                            st.session_state[f'edit_cliente_{cliente["id"]}'] = True
                        
                        if st.session_state.get(f'edit_cliente_{cliente["id"]}'):
                            with st.form(f"editar_cliente_{cliente['id']}", clear_on_submit=True):
                                novo_nome = st.text_input("Nome", value=cliente['nome'])
                                novo_telefone = st.text_input("Telefone", value=cliente['telefone'] or "")
                                novo_email = st.text_input("Email", value=cliente['email'] or "")
                                novo_cpf = st.text_input("CPF", value=cliente['cpf'] or "")
                                novo_endereco = st.text_area("Endereço", value=cliente['endereco'] or "")
                                
                                if st.form_submit_button("💾 Salvar"):
                                    sucesso, msg = editar_cliente(
                                        cliente['id'], novo_nome, novo_telefone, novo_email,
                                        cliente['data_nascimento'], novo_cpf, novo_endereco
                                    )
                                    if sucesso:
                                        st.success(msg)
                                        st.session_state[f'edit_cliente_{cliente["id"]}'] = False
                                        st.rerun()
                                    else:
                                        st.error(msg)
                    
                    with col_d:
                        if st.button("🗑️ Excluir", key=f"del_cli_{cliente['id']}"):
                            sucesso, msg = excluir_cliente(cliente['id'])
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
    
    with tab4:
        st.subheader("👕 Gestão de Produtos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Produto")
            with st.form("novo_produto_admin", clear_on_submit=True):
                nome = st.text_input("Nome do produto*")
                categoria = st.selectbox("Categoria", ["Camiseta", "Calça", "Short", "Agasalho", "Acessório", "Uniforme"])
                tamanho = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "Único", "2", "4", "6", "8", "10", "12", "14", "16"])
                cor = st.text_input("Cor*", value="Branco")
                preco = st.number_input("Preço Venda R$*", min_value=0.0, value=29.90, step=0.1)
                custo = st.number_input("Custo R$*", min_value=0.0, value=15.00, step=0.1)
                estoque = st.number_input("Estoque*", min_value=0, value=10)
                estoque_minimo = st.number_input("Estoque Mínimo*", min_value=1, value=5)
                
                escolas = listar_escolas()
                escola_id = st.selectbox("Escola*", 
                                       options=[e['id'] for e in escolas],
                                       format_func=lambda x: next(e['nome'] for e in escolas if e['id'] == x))
                
                if st.form_submit_button("✅ Cadastrar Produto"):
                    if nome and cor and escola_id:
                        sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome, cor e escola são obrigatórios!")
        
        with col2:
            st.write("📋 Produtos por Escola")
            
            escolas = listar_escolas()
            for escola in escolas:
                with st.expander(f"🏫 {escola['nome']}"):
                    produtos_escola = listar_produtos(escola['id'])
                    
                    for produto in produtos_escola:
                        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                        with col_a:
                            st.write(f"👕 **{produto['nome']}**")
                            st.write(f"{produto['tamanho']} - {produto['cor']}")
                        with col_b:
                            # Editar estoque
                            novo_estoque = st.number_input(
                                "Estoque", 
                                min_value=0, 
                                value=produto['estoque'],
                                key=f"estoque_{produto['id']}",
                                step=1
                            )
                            if novo_estoque != produto['estoque']:
                                if st.button("💾", key=f"save_estoque_{produto['id']}"):
                                    sucesso, msg = atualizar_estoque(produto['id'], novo_estoque)
                                    if sucesso:
                                        st.success("Estoque atualizado!")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with col_c:
                            margem = ((produto['preco'] - produto['custo']) / produto['custo']) * 100
                            st.write(f"R$ {produto['preco']:.2f}")
                            st.write(f"Lucro: {margem:.1f}%")
                        with col_d:
                            if produto['estoque'] <= produto['estoque_minimo']:
                                st.error("⬇️ Baixo")
                            elif produto['estoque'] <= produto['estoque_minimo'] * 2:
                                st.warning("⚠️ Atenção")
                            else:
                                st.success("✅ OK")
    
    with tab5:
        interface_pedidos('admin')
        
        # Exportação de dados
        st.subheader("📤 Exportar Dados")
        if st.button("📊 Exportar Pedidos para CSV"):
            csv_data = exportar_pedidos_para_csv()
            if csv_data:
                st.download_button(
                    label="⬇️ Baixar CSV",
                    data=csv_data,
                    file_name=f"pedidos_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.error("❌ Nenhum dado para exportar")
    
    with tab6:
        st.subheader("🏫 Gestão de Escolas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Nova Escola")
            with st.form("nova_escola", clear_on_submit=True):
                nome = st.text_input("Nome da Escola*")
                endereco = st.text_input("Endereço")
                telefone = st.text_input("Telefone")
                email = st.text_input("Email")
                
                if st.form_submit_button("✅ Cadastrar Escola"):
                    if nome:
                        sucesso, msg = adicionar_escola(nome, endereco, telefone, email)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome da escola é obrigatório")
        
        with col2:
            st.write("📋 Escolas Cadastradas")
            escolas = listar_escolas()
            
            for escola in escolas:
                with st.expander(f"🏫 {escola['nome']}"):
                    st.write(f"**Endereço:** {escola['endereco']}")
                    st.write(f"**Telefone:** {escola['telefone']}")
                    st.write(f"**Email:** {escola['email']}")
                    st.write(f"**Cadastro:** {formatar_data_brasil(escola['data_cadastro'])}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✏️ Editar", key=f"edit_esc_{escola['id']}"):
                            st.session_state.editando_escola = escola['id']
                    with col_b:
                        if st.button("🗑️ Excluir", key=f"del_esc_{escola['id']}"):
                            sucesso, msg = excluir_escola(escola['id'])
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    # Formulário de edição
                    if st.session_state.get('editando_escola') == escola['id']:
                        with st.form(f"editar_escola_{escola['id']}", clear_on_submit=True):
                            novo_nome = st.text_input("Nome", value=escola['nome'])
                            novo_endereco = st.text_input("Endereço", value=escola['endereco'] or "")
                            novo_telefone = st.text_input("Telefone", value=escola['telefone'] or "")
                            novo_email = st.text_input("Email", value=escola['email'] or "")
                            
                            col_c, col_d = st.columns(2)
                            with col_c:
                                if st.form_submit_button("💾 Salvar"):
                                    sucesso, msg = editar_escola(escola['id'], novo_nome, novo_endereco, novo_telefone, novo_email)
                                    if sucesso:
                                        st.success(msg)
                                        del st.session_state.editando_escola
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            with col_d:
                                if st.form_submit_button("❌ Cancelar"):
                                    del st.session_state.editando_escola
                                    st.rerun()
    
    with tab7:
        st.subheader("👤 Gestão de Usuários")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Usuário")
            with st.form("novo_usuario", clear_on_submit=True):
                username = st.text_input("Username*")
                password = st.text_input("Senha*", type="password")
                nome_completo = st.text_input("Nome Completo*")
                tipo = st.selectbox("Tipo", ["admin", "gestor", "vendedor"])
                
                if st.form_submit_button("✅ Criar Usuário"):
                    if username and password and nome_completo:
                        sucesso, msg = criar_usuario(username, password, nome_completo, tipo)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Todos os campos são obrigatórios")
        
        with col2:
            st.write("📋 Usuários do Sistema")
            usuarios = listar_usuarios()
            
            for usuario in usuarios:
                with st.expander(f"👤 {usuario['username']} - {usuario['tipo']}"):
                    st.write(f"**Nome:** {usuario['nome_completo']}")
                    st.write(f"**Status:** {'✅ Ativo' if usuario['ativo'] else '❌ Inativo'}")
                    
                    # Alterar senha
                    with st.form(f"alterar_senha_{usuario['id']}", clear_on_submit=True):
                        nova_senha = st.text_input("Nova Senha", type="password", key=f"pwd_{usuario['id']}")
                        if st.form_submit_button("🔐 Alterar Senha"):
                            if nova_senha:
                                sucesso, msg = alterar_senha_usuario(usuario['username'], nova_senha)
                                if sucesso:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                            else:
                                st.error("❌ Digite uma nova senha")
    
    with tab8:
        st.subheader("📈 Relatórios por Escola")
        
        tab_rel1, tab_rel2, tab_rel3 = st.tabs(["📊 Vendas por Escola", "📦 Estoque por Escola", "👕 Produtos por Escola"])
        
        with tab_rel1:
            st.subheader("📊 Relatório de Vendas por Escola")
            
            col_periodo1, col_periodo2 = st.columns(2)
            with col_periodo1:
                data_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=30))
            with col_periodo2:
                data_fim = st.date_input("Data Fim", value=date.today())
            
            if st.button("🔄 Gerar Relatório"):
                with st.spinner("Gerando relatório..."):
                    relatorio = relatorio_vendas_por_escola(data_inicio, data_fim)
                    
                    if relatorio:
                        st.success(f"📊 Relatório gerado com sucesso! ({len(relatorio)} escolas)")
                        
                        # Métricas totais
                        total_vendas = sum(r['valor_total_vendas'] or 0 for r in relatorio)
                        total_pedidos = sum(r['total_pedidos'] or 0 for r in relatorio)
                        
                        col_met1, col_met2, col_met3 = st.columns(3)
                        with col_met1:
                            st.metric("Total de Vendas", f"R$ {total_vendas:.2f}")
                        with col_met2:
                            st.metric("Total de Pedidos", total_pedidos)
                        with col_met3:
                            st.metric("Escolas no Relatório", len(relatorio))
                        
                        # Tabela de resultados
                        st.subheader("🏫 Desempenho por Escola")
                        for escola in relatorio:
                            with st.expander(f"🏫 {escola['escola_nome']} - R$ {escola['valor_total_vendas'] or 0:.2f}"):
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total de Pedidos", escola['total_pedidos'] or 0)
                                with col2:
                                    st.metric("Valor Total", f"R$ {escola['valor_total_vendas'] or 0:.2f}")
                                with col3:
                                    st.metric("Itens Vendidos", escola['total_itens_vendidos'] or 0)
                                with col4:
                                    st.metric("Ticket Médio", f"R$ {escola['ticket_medio'] or 0:.2f}")
                    else:
                        st.warning("❌ Nenhum dado encontrado para o período selecionado.")
        
        with tab_rel2:
            st.subheader("📦 Relatório de Estoque por Escola")
            
            if st.button("🔄 Gerar Relatório de Estoque"):
                with st.spinner("Gerando relatório de estoque..."):
                    relatorio = relatorio_estoque_por_escola()
                    
                    if relatorio:
                        st.success(f"📦 Relatório gerado com sucesso! ({len(relatorio)} escolas)")
                        
                        # Métricas totais
                        total_estoque = sum(r['total_estoque'] or 0 for r in relatorio)
                        total_valor_estoque = sum(r['valor_total_estoque'] or 0 for r in relatorio)
                        total_produtos_baixo = sum(r['produtos_estoque_baixo'] or 0 for r in relatorio)
                        
                        col_met1, col_met2, col_met3 = st.columns(3)
                        with col_met1:
                            st.metric("Total em Estoque", total_estoque)
                        with col_met2:
                            st.metric("Valor do Estoque", f"R$ {total_valor_estoque:.2f}")
                        with col_met3:
                            st.metric("Produtos com Estoque Baixo", total_produtos_baixo)
                        
                        # Tabela de resultados
                        st.subheader("📊 Estoque por Escola")
                        for escola in relatorio:
                            cor_status = "✅" if (escola['produtos_estoque_baixo'] or 0) == 0 else "⚠️" if (escola['produtos_estoque_baixo'] or 0) < 5 else "❌"
                            
                            with st.expander(f"{cor_status} {escola['escola_nome']} - {escola['total_estoque'] or 0} itens"):
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total Produtos", escola['total_produtos'] or 0)
                                with col2:
                                    st.metric("Total Estoque", escola['total_estoque'] or 0)
                                with col3:
                                    st.metric("Estoque Baixo", escola['produtos_estoque_baixo'] or 0)
                                with col4:
                                    st.metric("Valor Estoque", f"R$ {escola['valor_total_estoque'] or 0:.2f}")
                    else:
                        st.warning("❌ Nenhum dado encontrado.")
        
        with tab_rel3:
            st.subheader("👕 Relatório de Produtos por Escola")
            
            escolas = listar_escolas()
            escola_selecionada = st.selectbox(
                "Selecione a Escola:",
                options=[e['id'] for e in escolas],
                format_func=lambda x: next(e['nome'] for e in escolas if e['id'] == x)
            )
            
            col_periodo1, col_periodo2 = st.columns(2)
            with col_periodo1:
                data_inicio_prod = st.date_input("Data Início", value=date.today() - timedelta(days=30), key="prod_inicio")
            with col_periodo2:
                data_fim_prod = st.date_input("Data Fim", value=date.today(), key="prod_fim")
            
            if st.button("🔄 Gerar Relatório de Produtos"):
                with st.spinner("Gerando relatório de produtos..."):
                    relatorio = relatorio_produtos_por_escola(escola_selecionada, data_inicio_prod, data_fim_prod)
                    
                    if relatorio:
                        escola_nome = next(e['nome'] for e in escolas if e['id'] == escola_selecionada)
                        st.success(f"👕 Relatório gerado para {escola_nome}! ({len(relatorio)} produtos)")
                        
                        # Métricas
                        total_vendido = sum(r['total_vendido'] or 0 for r in relatorio)
                        valor_total = sum(r['valor_total'] or 0 for r in relatorio)
                        
                        col_met1, col_met2 = st.columns(2)
                        with col_met1:
                            st.metric("Total Itens Vendidos", total_vendido)
                        with col_met2:
                            st.metric("Valor Total Vendido", f"R$ {valor_total:.2f}")
                        
                        # Produtos mais vendidos
                        st.subheader("🏆 Produtos Mais Vendidos")
                        produtos_ordenados = sorted(relatorio, key=lambda x: x['total_vendido'] or 0, reverse=True)
                        
                        for i, produto in enumerate(produtos_ordenados[:10], 1):
                            with st.expander(f"{i}. {produto['nome']} - {produto['total_vendido'] or 0} vendidos"):
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.write(f"**Categoria:** {produto['categoria']}")
                                    st.write(f"**Tamanho:** {produto['tamanho']}")
                                with col2:
                                    st.write(f"**Cor:** {produto['cor']}")
                                    st.write(f"**Preço:** R$ {produto['preco']:.2f}")
                                with col3:
                                    st.write(f"**Total Vendido:** {produto['total_vendido'] or 0}")
                                    st.write(f"**Valor Total:** R$ {produto['valor_total'] or 0:.2f}")
                                with col4:
                                    st.write(f"**Estoque Atual:** {produto['estoque']}")
                                    if produto['estoque'] <= 5:
                                        st.error("Estoque Baixo")
                                    elif produto['estoque'] <= 10:
                                        st.warning("Estoque Médio")
                                    else:
                                        st.success("Estoque OK")
                    else:
                        st.warning("❌ Nenhum dado encontrado para esta escola no período selecionado.")

def interface_gestor():
    """Interface para Gestor"""
    st.header("📈 Painel do Gestor")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard", "🤖 A.I. Insights", "👥 Clientes", "👕 Produtos", "📦 Pedidos", "📈 Relatórios"
    ])
    
    with tab1:
        st.subheader("📊 Métricas Comerciais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_clientes = contar_clientes()
            st.metric("Clientes Ativos", total_clientes)
        
        with col2:
            pedidos_hoje = contar_pedidos()
            st.metric("Total Pedidos", pedidos_hoje)
        
        with col3:
            produtos = listar_produtos()
            estoque_total = sum(p['estoque'] for p in produtos)
            st.metric("Estoque Total", estoque_total)
        
        with col4:
            cursor = get_connection().cursor()
            cursor.execute("SELECT SUM(valor_final) FROM pedidos WHERE status = 'Entregue'")
            vendas_totais = cursor.fetchone()[0] or 0
            st.metric("Vendas Totais", f"R$ {vendas_totais:.2f}")
        
        # Data e hora atual
        st.write(f"**📅 Data atual:** {data_atual_brasil()}")
        st.write(f"**🕒 Hora atual:** {hora_atual_brasil()}")
        
        # Alertas A.I. rápidos
        st.subheader("🚨 Alertas Rápidos A.I.")
        insights = analise_estoque_otimizacao()
        if insights:
            for insight in insights[:2]:
                if insight['tipo'] == 'danger':
                    st.error(f"**{insight['titulo']}**: {insight['mensagem']}")
                else:
                    st.warning(f"**{insight['titulo']}**: {insight['mensagem']}")
        else:
            st.success("✅ Nenhum alerta crítico no momento")
    
    with tab2:
        gerar_relatorio_ai()
    
    with tab3:
        st.subheader("👥 Clientes")
        
        # Busca e paginação
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            busca_cliente = st.text_input("🔍 Buscar cliente", placeholder="Nome, telefone ou email", key="busca_gestor")
        with col_filter:
            limite_clientes = st.selectbox("Itens por página", [25, 50, 100], index=1, key="limite_gestor")
        
        # Paginação
        if 'pagina_clientes_gestor' not in st.session_state:
            st.session_state.pagina_clientes_gestor = 0
        
        total_clientes = contar_clientes(busca_cliente)
        total_paginas = max(1, (total_clientes + limite_clientes - 1) // limite_clientes)
        
        clientes = listar_clientes_paginado(
            offset=st.session_state.pagina_clientes_gestor * limite_clientes,
            limit=limite_clientes,
            busca=busca_cliente
        )
        
        # Controles de paginação
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️ Anterior", disabled=st.session_state.pagina_clientes_gestor == 0, key="prev_gestor"):
                st.session_state.pagina_clientes_gestor -= 1
                st.rerun()
        with col_info:
            st.write(f"Página {st.session_state.pagina_clientes_gestor + 1} de {total_paginas} ({total_clientes} clientes)")
        with col_next:
            if st.button("Próxima ➡️", disabled=st.session_state.pagina_clientes_gestor >= total_paginas - 1, key="next_gestor"):
                st.session_state.pagina_clientes_gestor += 1
                st.rerun()
        
        for cliente in clientes:
            with st.expander(f"👤 {cliente['nome']}"):
                st.write(f"**Contato:** {cliente['telefone']} | {cliente['email']}")
                if cliente['data_nascimento']:
                    st.write(f"**Nascimento:** {formatar_data_brasil(cliente['data_nascimento'])}")
                st.write(f"**Cadastro:** {formatar_data_brasil(cliente['data_cadastro'])}")
                if cliente['endereco']:
                    st.write(f"**Endereço:** {cliente['endereco']}")
    
    with tab4:
        st.subheader("👕 Produtos e Estoque")
        
        escolas = listar_escolas()
        for escola in escolas:
            with st.expander(f"🏫 {escola['nome']}"):
                produtos_escola = listar_produtos(escola['id'])
                
                for produto in produtos_escola:
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.write(f"**{produto['nome']}** - {produto['tamanho']} - {produto['cor']}")
                    with col2:
                        if produto['estoque'] < produto['estoque_minimo']:
                            st.error(f"Estoque: {produto['estoque']}")
                        elif produto['estoque'] < produto['estoque_minimo'] * 2:
                            st.warning(f"Estoque: {produto['estoque']}")
                        else:
                            st.success(f"Estoque: {produto['estoque']}")
                    with col3:
                        st.write(f"R$ {produto['preco']:.2f}")
                    with col4:
                        margem = ((produto['preco'] - produto['custo']) / produto['custo']) * 100
                        st.write(f"Lucro: {margem:.1f}%")
    
    with tab5:
        interface_pedidos('gestor')
    
    with tab6:
        st.subheader("📈 Relatórios por Escola")
        
        tab_rel1, tab_rel2 = st.tabs(["📊 Vendas por Escola", "📦 Estoque por Escola"])
        
        with tab_rel1:
            st.subheader("📊 Relatório de Vendas por Escola")
            
            col_periodo1, col_periodo2 = st.columns(2)
            with col_periodo1:
                data_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=30), key="gestor_inicio")
            with col_periodo2:
                data_fim = st.date_input("Data Fim", value=date.today(), key="gestor_fim")
            
            if st.button("🔄 Gerar Relatório", key="rel_gestor"):
                with st.spinner("Gerando relatório..."):
                    relatorio = relatorio_vendas_por_escola(data_inicio, data_fim)
                    
                    if relatorio:
                        st.success(f"📊 Relatório gerado com sucesso! ({len(relatorio)} escolas)")
                        
                        total_vendas = sum(r['valor_total_vendas'] or 0 for r in relatorio)
                        total_pedidos = sum(r['total_pedidos'] or 0 for r in relatorio)
                        
                        col_met1, col_met2, col_met3 = st.columns(3)
                        with col_met1:
                            st.metric("Total de Vendas", f"R$ {total_vendas:.2f}")
                        with col_met2:
                            st.metric("Total de Pedidos", total_pedidos)
                        with col_met3:
                            st.metric("Escolas", len(relatorio))
                        
                        for escola in relatorio:
                            with st.expander(f"🏫 {escola['escola_nome']} - R$ {escola['valor_total_vendas'] or 0:.2f}"):
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Pedidos", escola['total_pedidos'] or 0)
                                with col2:
                                    st.metric("Vendas", f"R$ {escola['valor_total_vendas'] or 0:.2f}")
                                with col3:
                                    st.metric("Itens", escola['total_itens_vendidos'] or 0)
                                with col4:
                                    st.metric("Ticket Médio", f"R$ {escola['ticket_medio'] or 0:.2f}")
                    else:
                        st.warning("❌ Nenhum dado encontrado para o período selecionado.")
        
        with tab_rel2:
            st.subheader("📦 Relatório de Estoque por Escola")
            
            if st.button("🔄 Gerar Relatório de Estoque", key="estoque_gestor"):
                with st.spinner("Gerando relatório de estoque..."):
                    relatorio = relatorio_estoque_por_escola()
                    
                    if relatorio:
                        st.success(f"📦 Relatório gerado com sucesso! ({len(relatorio)} escolas)")
                        
                        for escola in relatorio:
                            cor_status = "✅" if (escola['produtos_estoque_baixo'] or 0) == 0 else "⚠️"
                            
                            with st.expander(f"{cor_status} {escola['escola_nome']} - {escola['total_estoque'] or 0} itens"):
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Produtos", escola['total_produtos'] or 0)
                                with col2:
                                    st.metric("Estoque", escola['total_estoque'] or 0)
                                with col3:
                                    st.metric("Estoque Baixo", escola['produtos_estoque_baixo'] or 0)
                                with col4:
                                    st.metric("Valor", f"R$ {escola['valor_total_estoque'] or 0:.2f}")
                    else:
                        st.warning("❌ Nenhum dado encontrado.")

def interface_vendedor():
    """Interface para Vendedor"""
    st.header("👔 Painel do Vendedor")
    
    tab1, tab2, tab3 = st.tabs(["📦 Pedidos", "👥 Clientes", "📦 Estoque"])
    
    with tab1:
        interface_pedidos('vendedor')
    
    with tab2:
        st.subheader("👥 Clientes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Cliente")
            with st.form("novo_cliente_vendedor", clear_on_submit=True):
                nome = st.text_input("Nome completo*")
                telefone = st.text_input("Telefone*")
                email = st.text_input("Email")
                data_nascimento = st.date_input("Data de Nascimento", max_value=date.today(), key="vendedor_nasc")
                cpf = st.text_input("CPF", key="vendedor_cpf")
                endereco = st.text_area("Endereço", key="vendedor_end")
                
                if st.form_submit_button("✅ Cadastrar Cliente"):
                    if nome and telefone:
                        sucesso, msg = adicionar_cliente(nome, telefone, email, data_nascimento, cpf, endereco)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome e telefone são obrigatórios!")
        
        with col2:
            # Busca simples para vendedor
            busca_cliente = st.text_input("🔍 Buscar cliente", placeholder="Nome, telefone")
            clientes = listar_clientes_paginado(busca=busca_cliente, limit=100) if busca_cliente else listar_clientes_paginado(limit=50)
            
            for cliente in clientes[:20]:  # Limite de 20 clientes na visualização
                with st.expander(f"👤 {cliente['nome']}"):
                    st.write(f"**Telefone:** {cliente['telefone']}")
                    st.write(f"**Email:** {cliente['email'] or 'N/A'}")
                    if cliente['data_nascimento']:
                        st.write(f"**Nascimento:** {formatar_data_brasil(cliente['data_nascimento'])}")
                    st.write(f"**Cadastro:** {formatar_data_brasil(cliente['data_cadastro'])}")
    
    with tab3:
        st.subheader("📦 Estoque de Todas as Escolas")
        
        escolas = listar_escolas()
        for escola in escolas:
            with st.expander(f"🏫 {escola['nome']}"):
                produtos = listar_produtos(escola['id'])
                for produto in produtos:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{produto['nome']}** - {produto['tamanho']} - {produto['cor']}")
                    with col2:
                        if produto['estoque'] < produto['estoque_minimo']:
                            st.error(f"Estoque: {produto['estoque']}")
                        elif produto['estoque'] < produto['estoque_minimo'] * 2:
                            st.warning(f"Estoque: {produto['estoque']}")
                        else:
                            st.success(f"Estoque: {produto['estoque']}")
                    with col3:
                        st.write(f"R$ {produto['preco']:.2f}")

def interface_pedidos(tipo_usuario):
    """Interface de pedidos compartilhada"""
    st.subheader("📦 Gestão de Pedidos")
    
    tab1, tab2 = st.tabs(["➕ Novo Pedido", "📋 Meus Pedidos"])
    
    with tab1:
        # Selecionar cliente
        clientes = listar_clientes_paginado(limit=1000)  # Busca todos os clientes para seleção
        
        if not clientes:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
            return
        
        cliente_selecionado = st.selectbox(
            "👤 Selecione o cliente:",
            options=[c['id'] for c in clientes],
            format_func=lambda x: f"{next(c['nome'] for c in clientes if c['id'] == x)} - {next(c['telefone'] for c in clientes if c['id'] == x)}"
        )
        
        # Mostrar TODOS os produtos de TODAS as escolas
        st.subheader("🛒 Adicionar Itens ao Pedido")
        st.info("🎯 O cliente pode escolher produtos de qualquer escola")
        
        # Agrupar produtos por escola para melhor organização
        escolas = listar_escolas()
        
        for escola in escolas:
            with st.expander(f"🏫 {escola['nome']}", expanded=True):
                produtos_escola = listar_produtos(escola['id'])
                
                if produtos_escola:
                    for produto in produtos_escola:
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        with col1:
                            st.write(f"**{produto['nome']}**")
                            st.write(f"Tamanho: {produto['tamanho']} | Cor: {produto['cor']}")
                        with col2:
                            if produto['estoque'] <= 0:
                                st.error("Sem estoque")
                            elif produto['estoque'] < 5:
                                st.warning(f"Estoque: {produto['estoque']}")
                            else:
                                st.success(f"Estoque: {produto['estoque']}")
                        with col3:
                            st.write(f"R$ {produto['preco']:.2f}")
                        with col4:
                            # Selecionar quantidade
                            quantidade = st.number_input(
                                "Qtd", 
                                min_value=0, 
                                max_value=min(produto['estoque'], 100) if produto['estoque'] > 0 else 0,
                                value=0,
                                key=f"select_{produto['id']}",
                                step=1
                            )
                        with col5:
                            if quantidade > 0:
                                if st.button("➕ Adicionar", key=f"add_{produto['id']}"):
                                    if 'itens_pedido' not in st.session_state:
                                        st.session_state.itens_pedido = []
                                    
                                    # Verificar se produto já está no pedido
                                    for i, item in enumerate(st.session_state.itens_pedido):
                                        if item['produto_id'] == produto['id']:
                                            # Atualizar quantidade existente
                                            st.session_state.itens_pedido[i]['quantidade'] += quantidade
                                            st.session_state.itens_pedido[i]['subtotal'] = st.session_state.itens_pedido[i]['preco_unitario'] * st.session_state.itens_pedido[i]['quantidade']
                                            break
                                    else:
                                        # Adicionar novo item
                                        item = {
                                            'produto_id': produto['id'],
                                            'nome': produto['nome'],
                                            'escola': produto['escola_nome'],
                                            'quantidade': quantidade,
                                            'preco_unitario': produto['preco'],
                                            'subtotal': produto['preco'] * quantidade
                                        }
                                        st.session_state.itens_pedido.append(item)
                                    
                                    st.success(f"✅ {quantidade}x {produto['nome']} adicionado!")
                                    st.rerun()
                else:
                    st.write("📭 Nenhum produto cadastrado para esta escola")
        
        # Itens do pedido
        if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
            st.subheader("📋 Itens do Pedido")
            total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
            
            for i, item in enumerate(st.session_state.itens_pedido):
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
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
                    # Editar quantidade
                    nova_quantidade = st.number_input(
                        "Nova Qtd", 
                        min_value=1, 
                        value=item['quantidade'],
                        key=f"edit_qtd_{i}",
                        step=1
                    )
                    if nova_quantidade != item['quantidade']:
                        if st.button("🔄", key=f"update_{i}"):
                            item['quantidade'] = nova_quantidade
                            item['subtotal'] = item['preco_unitario'] * nova_quantidade
                            st.rerun()
                with col6:
                    if st.button("❌", key=f"del_{i}"):
                        st.session_state.itens_pedido.pop(i)
                        st.rerun()
            
            # Recalcular total
            total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
            st.write(f"**💰 Total do Pedido: R$ {total_pedido:.2f}**")
            
            # Finalizar pedido
            st.subheader("✅ Finalizar Pedido")
            col_data, col_desc = st.columns(2)
            with col_data:
                data_entrega = st.date_input("📅 Data de Entrega Prevista", min_value=date.today())
            with col_desc:
                desconto = st.number_input("Desconto (R$)", min_value=0.0, value=0.0, step=0.1)
            
            forma_pagamento = st.selectbox("Forma de Pagamento", 
                                         ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto", "Outro"])
            observacoes = st.text_area("Observações")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                    if st.session_state.itens_pedido:
                        # Verificar estoque para todos os itens
                        estoque_insuficiente = False
                        produtos_sem_estoque = []
                        
                        for item in st.session_state.itens_pedido:
                            produto = next((p for p in listar_produtos() if p['id'] == item['produto_id']), None)
                            if produto and item['quantidade'] > produto['estoque']:
                                produtos_sem_estoque.append(f"{produto['nome']} (estoque: {produto['estoque']})")
                                estoque_insuficiente = True
                        
                        if estoque_insuficiente:
                            st.error("❌ Estoque insuficiente para os seguintes produtos:")
                            for produto in produtos_sem_estoque:
                                st.write(f"• {produto}")
                        else:
                            vendedor_id = st.session_state.get('user_id', None)
                            sucesso, resultado = adicionar_pedido(
                                cliente_selecionado, 
                                st.session_state.itens_pedido, 
                                data_entrega, 
                                observacoes,
                                desconto,
                                forma_pagamento,
                                vendedor_id
                            )
                            if sucesso:
                                st.success(f"✅ Pedido #{resultado} criado com sucesso!")
                                st.balloons()
                                
                                # Oferecer download do PDF
                                criar_botao_download_pdf(resultado, "📄 Baixar PDF do Pedido")
                                
                                del st.session_state.itens_pedido
                                st.rerun()
                            else:
                                st.error(f"❌ Erro ao criar pedido: {resultado}")
                    else:
                        st.error("❌ Adicione itens ao pedido antes de finalizar!")
            
            with col_btn2:
                if st.button("🗑️ Limpar Pedido", use_container_width=True):
                    if 'itens_pedido' in st.session_state:
                        del st.session_state.itens_pedido
                    st.rerun()
        else:
            st.info("🛒 Adicione itens ao pedido usando os botões 'Adicionar' acima")
    
    with tab2:
        # Filtros e busca
        col_filtro, col_busca, col_limite = st.columns([2, 2, 1])
        with col_filtro:
            filtro_status = st.selectbox("Filtrar por status", 
                                       ["Todos", "Pendente", "Em produção", "Pronto para entrega", "Entregue", "Cancelado"])
        with col_busca:
            busca_cliente = st.text_input("Buscar cliente", placeholder="Nome do cliente")
        with col_limite:
            limite_pedidos = st.selectbox("Itens por página", [25, 50, 100], index=1)
        
        # Paginação
        if 'pagina_pedidos' not in st.session_state:
            st.session_state.pagina_pedidos = 0
        
        total_pedidos = contar_pedidos(
            filtro_status if filtro_status != "Todos" else None,
            busca_cliente if busca_cliente else None
        )
        total_paginas = max(1, (total_pedidos + limite_pedidos - 1) // limite_pedidos)
        
        pedidos = listar_pedidos_paginado(
            tipo_usuario,
            offset=st.session_state.pagina_pedidos * limite_pedidos,
            limit=limite_pedidos,
            filtro_status=filtro_status if filtro_status != "Todos" else None,
            busca_cliente=busca_cliente if busca_cliente else None
        )
        
        # Controles de paginação
        if total_pedidos > 0:
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("⬅️ Anterior", disabled=st.session_state.pagina_pedidos == 0, key="prev_pedidos"):
                    st.session_state.pagina_pedidos -= 1
                    st.rerun()
            with col_info:
                st.write(f"Página {st.session_state.pagina_pedidos + 1} de {total_paginas} ({total_pedidos} pedidos)")
            with col_next:
                if st.button("Próxima ➡️", disabled=st.session_state.pagina_pedidos >= total_paginas - 1, key="next_pedidos"):
                    st.session_state.pagina_pedidos += 1
                    st.rerun()
        
        if pedidos:
            for pedido in pedidos:
                status_info = {
                    'Pendente': '🟡 Pendente',
                    'Em produção': '🟠 Em produção', 
                    'Pronto para entrega': '🔵 Pronto',
                    'Entregue': '🟢 Entregue',
                    'Cancelado': '🔴 Cancelado'
                }.get(pedido['status'], f'⚪ {pedido["status"]}')
                
                with st.expander(f"{status_info} Pedido #{pedido['id']} - {pedido['cliente_nome']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Cliente:** {pedido['cliente_nome']}")
                        st.write(f"**Status:** {pedido['status']}")
                        st.write(f"**Data Pedido:** {formatar_datahora_brasil(pedido['data_pedido'])}")
                        if pedido['forma_pagamento']:
                            st.write(f"**Pagamento:** {pedido['forma_pagamento']}")
                    with col2:
                        st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                        if pedido['desconto'] > 0:
                            st.write(f"**Desconto:** R$ {pedido['desconto']:.2f}")
                        st.write(f"**Valor Final:** R$ {pedido['valor_final']:.2f}")
                        st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        if pedido['data_entrega_real']:
                            st.write(f"**Entregue em:** {formatar_data_brasil(pedido['data_entrega_real'])}")
                    
                    # Botão para gerar PDF
                    criar_botao_download_pdf(pedido['id'])
                    
                    # Ações do pedido
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        novo_status = st.selectbox(
                            "Alterar status:",
                            ["Pendente", "Em produção", "Pronto para entrega", "Entregue", "Cancelado"],
                            key=f"status_{pedido['id']}"
                        )
                        
                        if st.button("🔄 Atualizar", key=f"upd_{pedido['id']}"):
                            data_entrega = date.today() if novo_status == 'Entregue' else None
                            sucesso, msg = atualizar_status_pedido(pedido['id'], novo_status, data_entrega)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    # Admin e gestor podem excluir pedidos
                    if tipo_usuario in ['admin', 'gestor']:
                        with col2:
                            if st.button("🗑️ Excluir Pedido", key=f"del_ped_{pedido['id']}"):
                                sucesso, msg = excluir_pedido(pedido['id'])
                                if sucesso:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("📦 Nenhum pedido encontrado.")

# =========================================
# 🚀 APP PRINCIPAL
# =========================================

def main():
    # Inicialização
    if 'db_initialized' not in st.session_state:
        if init_db():
            st.session_state.db_initialized = True

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # Página de Login
    if not st.session_state.logged_in:
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1>👕 Sistema de Fardamentos + A.I.</h1>
            <p>Faça login para continuar</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
            password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if submitted:
                if username and password:
                    with st.spinner("Verificando credenciais..."):
                        sucesso, mensagem, tipo_usuario = verificar_login(username, password)
                        if sucesso:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.nome_usuario = mensagem
                            st.session_state.tipo_usuario = tipo_usuario
                            st.success(f"Bem-vindo, {mensagem}!")
                            st.rerun()
                        else:
                            st.error(mensagem)
                else:
                    st.error("Por favor, preencha todos os campos")
        st.stop()

    # Interface baseada no tipo de usuário
    st.sidebar.markdown(f"**👤 {st.session_state.nome_usuario}**")
    st.sidebar.markdown(f"**🎯 {st.session_state.tipo_usuario.upper()}**")
    
    # Data e hora atual
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**📅 {data_atual_brasil()}**")
    st.sidebar.markdown(f"**🕒 {hora_atual_brasil()}**")
    
    # Alterar própria senha
    with st.sidebar.expander("🔐 Alterar Minha Senha"):
        with st.form("alterar_minha_senha", clear_on_submit=True):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Senha", type="password")
            
            if st.form_submit_button("💾 Alterar Senha"):
                if nova_senha and confirmar_senha:
                    if nova_senha == confirmar_senha:
                        sucesso, msg = alterar_senha_usuario(st.session_state.username, nova_senha)
                        if sucesso:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Senhas não coincidem")
                else:
                    st.error("❌ Preencha todos os campos")
    
    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Redirecionar para interface correta
    if st.session_state.tipo_usuario == 'admin':
        interface_admin()
    elif st.session_state.tipo_usuario == 'gestor':
        interface_gestor()
    elif st.session_state.tipo_usuario == 'vendedor':
        interface_vendedor()
    else:
        st.error("Tipo de usuário não reconhecido")

if __name__ == "__main__":
    main()