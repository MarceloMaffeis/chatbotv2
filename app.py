import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pypdf import PdfReader
from openai import AzureOpenAI

st.set_page_config(
    page_title="TI Support Hub | Dashboard & WhatsApp Chat",
    page_icon="💬",
    layout="wide"
)

# ==========================================
# CSS PERSONALIZADO: ESTILO WHATSAPP
# ==========================================
st.markdown("""
<style>
    /* Fundo da área do WhatsApp */
    .whatsapp-container {
        background-color: #0b141a;
        background-image: radial-gradient(#1f2c34 1px, transparent 1px);
        background-size: 20px 20px;
        border-radius: 12px;
        padding: 20px;
        max-height: 580px;
        overflow-y: auto;
        border: 1px solid #222d34;
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 15px;
    }

    /* Cabeçalho do contato */
    .whatsapp-header {
        background-color: #202c33;
        color: #e9edef;
        padding: 10px 16px;
        border-radius: 10px 10px 0 0;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid #313d45;
    }
    .status-dot {
        height: 10px;
        width: 10px;
        background-color: #25d366;
        border-radius: 50%;
        display: inline-block;
    }

    /* Linhas de mensagem */
    .msg-row {
        display: flex;
        width: 100%;
    }
    .msg-row.user {
        justify-content: flex-end;
    }
    .msg-row.assistant {
        justify-content: flex-start;
    }

    /* Balões de fala */
    .chat-bubble {
        max-width: 75%;
        padding: 9px 14px 6px 14px;
        border-radius: 8px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 14.5px;
        line-height: 1.45;
        box-shadow: 0 1px 0.5px rgba(11,20,26,.13);
        word-wrap: break-word;
        position: relative;
    }

    /* Balão do usuário (Verde WhatsApp) */
    .chat-bubble.user {
        background-color: #005c4b;
        color: #e9edef;
        border-top-right-radius: 2px;
    }

    /* Balão da IA (Cinza chumbo WhatsApp Web Dark) */
    .chat-bubble.assistant {
        background-color: #202c33;
        color: #d1d7db;
        border-top-left-radius: 2px;
    }

    /* Metadados: hora e checks */
    .msg-meta {
        font-size: 11px;
        color: rgba(233, 237, 239, 0.6);
        text-align: right;
        margin-top: 4px;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 4px;
    }
    .check-read {
        color: #53bdeb;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# INICIALIZAÇÃO DE ESTADO
# ==========================================
if "chat_iniciado" not in st.session_state:
    st.session_state.chat_iniciado = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conteudo_base" not in st.session_state:
    st.session_state.conteudo_base = ""
if "df_tabela" not in st.session_state:
    st.session_state.df_tabela = None

def extrair_texto_e_dados(uploaded_file):
    nome = uploaded_file.name.lower()
    try:
        if nome.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            st.session_state.df_tabela = df
            return df.to_string(index=False)
        elif nome.endswith(".txt"):
            st.session_state.df_tabela = None
            return uploaded_file.read().decode("utf-8", errors="ignore")
        elif nome.endswith(".pdf"):
            st.session_state.df_tabela = None
            leitor = PdfReader(uploaded_file)
            texto = ""
            for p in leitor.pages:
                t = p.extract_text()
                if t:
                    texto += t + "\n"
            return texto
    except Exception as e:
        st.sidebar.error(f"Erro ao ler arquivo: {e}")
        return ""
    return ""

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("⚙️ Conexão & RAG")
    
    endpoint = st.text_input(
        "Endpoint Azure:",
        value=st.session_state.get("saved_endpoint", ""),
        placeholder="https://seu-recurso.services.ai.azure.com/"
    )
    api_key = st.text_input(
        "API Key:",
        value=st.session_state.get("saved_key", ""),
        type="password"
    )
    modelo = st.text_input(
        "Deployment / Modelo:",
        value=st.session_state.get("saved_model", "gpt-4.1-mini")
    )

    st.divider()

    persona_padrao = (
        "Você é o Suporte de TI oficial da empresa via WhatsApp. "
        "Responda de forma ágil, clara, cordial e profissional. "
        "Consulte sempre a base de dados anexada para passar orçamentos, procedimentos e SLAs."
    )
    persona = st.text_area("Persona da IA:", value=persona_padrao, height=100)

    arquivo_rag = st.file_uploader(
        "Upload de Base (CSV para Dashboard + Chat):",
        type=["csv", "pdf", "txt"]
    )

    if arquivo_rag is not None:
        st.session_state.conteudo_base = extrair_texto_e_dados(arquivo_rag)
        st.success(f"Carregado: {arquivo_rag.name}")
    else:
        st.session_state.conteudo_base = ""
        st.session_state.df_tabela = None

    if st.button("🚀 Iniciar / Atualizar Conexão", use_container_width=True, type="primary"):
        if not endpoint or not api_key or not modelo:
            st.error("Preencha Endpoint, API Key e Modelo.")
        else:
            st.session_state.saved_endpoint = endpoint
            st.session_state.saved_key = api_key
            st.session_state.saved_model = modelo
            st.session_state.persona = persona
            st.session_state.chat_iniciado = True
            st.rerun()

    if st.session_state.chat_iniciado:
        if st.button("🔄 Novo Chat (Limpar Conversa)", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# ==========================================
# NAVEGAÇÃO PRINCIPAL (TABS)
# ==========================================
aba_dash, aba_chat = st.tabs(["📊 Dashboard de Manutenção", "💬 Atendimento WhatsApp"])

# ------------------------------------------
# ABA 1: DASHBOARD ANALÍTICO
# ------------------------------------------
with aba_dash:
    if st.session_state.df_tabela is not None:
        df = st.session_state.df_tabela.copy()

        # Limpeza e conversão numérica das colunas de valores (se necessário)
        colunas_valor = ["Valor_Mao_de_Obra_BRL", "Custo_Pecas_Estimado_BRL", "Valor_Total_Sugerido_BRL"]
        for col in colunas_valor:
            if col in df.columns and df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace("R$", "", regex=False).str.strip().str.replace(",", ".").astype(float)

        st.subheader("Indicadores Gerais de Manutenção e Custos")

        # Métricas KPI em cartões
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_servicos = len(df)
        ticket_medio = df["Valor_Total_Sugerido_BRL"].mean() if "Valor_Total_Sugerido_BRL" in df.columns else 0
        sla_medio = df["SLA_Horas"].mean() if "SLA_Horas" in df.columns else 0
        remotos = len(df[df["Tipo_Atendimento"].str.contains("Remoto|Online", case=False, na=False)]) if "Tipo_Atendimento" in df.columns else 0

        kpi1.metric("Catálogo de Serviços", f"{total_servicos} itens")
        kpi2.metric("Ticket Médio Sugerido", f"R$ {ticket_medio:.2f}")
        kpi3.metric("SLA Médio de Atendimento", f"{sla_medio:.1f} horas")
        kpi4.metric("Atendimentos Remotos", f"{remotos} itens")

        st.divider()

        # Gráficos Analíticos
        g1, g2 = st.columns(2)

        with g1:
            if "Categoria" in df.columns and "Valor_Total_Sugerido_BRL" in df.columns:
                fig_cat = px.bar(
                    df,
                    x="Codigo_Servico",
                    y="Valor_Total_Sugerido_BRL",
                    color="Categoria",
                    hover_data=["Descricao_Servico", "Tipo_Atendimento"],
                    title="Custo Total por Serviço (Hardware vs Software)",
                    labels={"Valor_Total_Sugerido_BRL": "Valor Total (R$)", "Codigo_Servico": "Código"},
                    template="plotly_dark"
                )
                fig_cat.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_cat, use_container_width=True)

        with g2:
            if "Tipo_Atendimento" in df.columns:
                fig_pie = px.pie(
                    df,
                    names="Tipo_Atendimento",
                    values="Valor_Total_Sugerido_BRL" if "Valor_Total_Sugerido_BRL" in df.columns else None,
                    title="Distribuição da Receita por Tipo de Atendimento",
                    hole=0.45,
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("🔍 Visualizar Tabela Completa do Arquivo CSV"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info("💡 Faça o upload de um arquivo **.CSV** na barra lateral para habilitar os gráficos e indicadores.")

# ------------------------------------------
# ABA 2: CHATBOT ESTILO WHATSAPP
# ------------------------------------------
with aba_chat:
    # Cabeçalho da conversa
    st.markdown("""
    <div class="whatsapp-header">
        <div style="font-size: 26px;">🎧</div>
        <div style="flex-grow: 1;">
            <div style="font-weight: 600; font-size: 15px;">Suporte Técnico TI - HelpDesk</div>
            <div style="font-size: 12px; color: #8696a0;"><span class="status-dot"></span> online</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Renderização da Janela de Mensagens do WhatsApp
    html_chat = '<div class="whatsapp-container">'
    
    if len(st.session_state.messages) == 0:
        html_chat += """
        <div style="text-align: center; color: #8696a0; font-size: 12px; margin: auto;">
            🔒 As mensagens são protegidas com RAG corporativo e modelo Azure OpenAI.
        </div>
        """
    else:
        for m in st.session_state.messages:
            papel = m["role"]
            conteudo = m["content"].replace("\n", "<br>")
            hora = m.get("time", datetime.now().strftime("%H:%M"))
            checks = '<span class="check-read">✓✓</span>' if papel == "user" else ''

            html_chat += f"""
            <div class="msg-row {papel}">
                <div class="chat-bubble {papel}">
                    <div>{conteudo}</div>
                    <div class="msg-meta">{hora} {checks}</div>
                </div>
            </div>
            """

    html_chat += '</div>'
    st.markdown(html_chat, unsafe_allow_html=True)

    # Input do Usuário
    if not st.session_state.chat_iniciado:
        st.warning("⚠️ Conecte suas credenciais na barra lateral à esquerda para habilitar o envio.")
    else:
        if prompt := st.chat_input("Digite uma mensagem como no WhatsApp..."):
            hora_atual = datetime.now().strftime("%H:%M")
            st.session_state.messages.append({"role": "user", "content": prompt, "time": hora_atual})

            # Montagem do prompt com RAG
            instrucao = st.session_state.persona
            if st.session_state.conteudo_base:
                instrucao += f"\n\n[BASE DE CONHECIMENTO CSV/RAG]:\n{st.session_state.conteudo_base}"

            mensagens_envio = [{"role": "system", "content": instrucao}]
            for m in st.session_state.messages:
                mensagens_envio.append({"role": m["role"], "content": m["content"]})

            try:
                endpoint_sanitizado = (
                    st.session_state.saved_endpoint.strip()
                    .replace("/openai/v1", "")
                    .rstrip("/")
                )

                client = AzureOpenAI(
                    azure_endpoint=endpoint_sanitizado,
                    api_key=st.session_state.saved_key.strip(),
                    api_version="2024-06-01"
                )

                resposta = client.chat.completions.create(
                    model=st.session_state.saved_model.strip(),
                    messages=mensagens_envio,
                    temperature=0.2
                )
                conteudo_resposta = resposta.choices[0].message.content

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": conteudo_resposta,
                    "time": datetime.now().strftime("%H:%M")
                })
                st.rerun()

            except Exception as e:
                st.error(f"Erro de conexão com o Azure OpenAI: {e}")
