# Sistema de Fardamentos Completo

Sistema de gerenciamento de pedidos de fardamentos com controle de estoque, clientes, produtos e relatórios.

## 🆕 Novas Funcionalidades na Versão 8.0

### ✅ Status de Pedidos Aprimorado
- **Novos status**: Pendente, Em produção, Pronto para entrega, Entregue, Cancelado
- **Controle completo** do fluxo do pedido
- **Data de entrega real** registrada automaticamente

### ✅ Forma de Pagamento
- **Múltiplas opções**: Dinheiro, Cartão de Crédito, Cartão de Débito, PIX, Transferência
- **Registro no pedido** para controle financeiro

### ✅ Correção do Banco de Dados
- **Campo escola_id** adicionado na tabela produtos
- **Estrutura corrigida** para evitar erros

## Funcionalidades Principais
- 📊 Dashboard com métricas em tempo real
- 📦 Gestão completa de pedidos com status
- 👥 Cadastro simplificado de clientes
- 👕 Cadastro de produtos vinculados a escolas
- 📦 Controle de estoque automático
- 📈 Relatórios detalhados de vendas
- 🔐 Sistema de login com múltiplos usuários

## Status dos Pedidos
- 🟡 **Pendente**: Pedido recebido
- 🟠 **Em produção**: Em confecção
- 🔵 **Pronto para entrega**: Aguardando retirada/entrega
- 🟢 **Entregue**: Finalizado com sucesso
- 🔴 **Cancelado**: Pedido cancelado

## Login
- **Admin:** admin / Admin@2024!
- **Vendedor:** vendedor / Vendas@123

## Deploy no Render
1. Conecte seu repositório GitHub
2. Configure as variáveis de ambiente:
   - `DATABASE_URL`: URL do PostgreSQL
3. O deploy será automático

## Desenvolvimento Local
```bash
pip install -r requirements.txt
streamlit run app.py
