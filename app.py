import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pypdf import PdfReader
from openai import AzureOpenAI

st.set_page_config(
    page_title="TI Support Hub | Dashboard & Chat Flutuante",
    page_icon="🛠️",
    layout="wide"
)

# ============================================================
# CSS: ESTILIZAÇÃO DO WIDGET FLUTUANTE (POP-UP) ESTILO WHATSAPP
# ============================================================
st.markdown("""
<style>
    /* 1. Posiciona o container do popover fixo no canto inferior direito */
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 24px !important;
        right: 28px !important;
        z-index: 999999 !important;
    }

    /* 2. Estiliza o botão flutuante de abertura (botão redondo verde WhatsApp) */
    div[data-testid="stPopover"] > button {
        background-color: #25d366 !important;
        color: white !important;
        border-radius: 50% !important;
        width: 62px !important;
        height: 62px !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
        font-size: 28px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.2s ease, background-color 0.2s ease !important;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: #20ba5a !important;
        transform: scale(1.08) !important;
    }

    /* 3. Estiliza a caixa/janela suspensa (Pop-up) */
    div[data-testid="stPopoverBody"] {
        width: 390px !important;
        max-width: 90vw !important;
        max-height: 600px !important;
        background-color: #0b141a !important;
        border: 1px solid #2a3942 !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5) !important;
        padding: 12px !important;
    }

    /* 4. Cabeçalho do contato dentro do pop-up */
    .wa-popup-header {
        background-color: #202c33;
        color: #e9edef;
        padding: 10px 14px;
        border-radius: 8px 8px 4px 4px;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        border-bottom: 1px solid #313d45;
    }
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #25d366;
        border-radius: 50%;
        display: inline-block;
    }

    /* 5. Área de rolagem das mensagens */
    .whatsapp-scroll-area {
        max-height: 320px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 6px;
        background-color: #0b141a;
        border-radius: 6px;
        margin-bottom: 12px;
    }

    /* 6. Linhas e balões de conversa */
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

    .chat-bubble {
        max-width: 84%;
        padding: 7px 11px 4px 11px;
        border-radius: 8px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13.5px;
        line-height: 1.4;
        word-wrap: break-word;
    }
    .chat-bubble.user {
        background-color: #005c4b;
        color: #e9edef;
        border-top-right-radius: 2px;
    }
    .chat-bubble.assistant {
        background-color: #202c33;
        color: #d1d7db;
        border-top-left-radius: 2px;
    }

    .msg-meta {
        font-size: 10px;
        color: rgba(233, 237, 239, 0.6);
        text-align: right;
        margin-top: 3px;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 3px;
    }
    .check-read {
        color: #53bdeb;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# INICIALIZAÇÃO DE ESTADO (SESSION STATE)
# ============================================================
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

# ============================================================
# BARRA LATERAL: PARÂMETROS AZURE & UPLOAD RAG
# ============================================================
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
        "Você é o assistente de Suporte de TI oficial via WhatsApp. "
        "Responda de forma ágil, clara e cordial. Consulte sempre a base anexada "
        "para orçamentos, procedimentos e SLAs."
    )
    persona = st.text_area("Persona da IA:", value=persona_padrao, height=90)

    arquivo_rag = st.file_uploader(
        "Upload da Base (CSV para Dashboard + Chat):",
        type=["csv", "pdf", "txt"]
    )

    if arquivo_rag is not None:
        st.session_state.conteudo_base = extrair_texto_e_dados(arquivo_rag)
        st.success(f"Carregado: {arquivo_rag.name}")
    else:
        st.session_state.conteudo_base = ""
        st.session_state.df_tabela = None

    if st.button("🚀 Conectar IA", use_container_width=True, type="primary"):
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
        if st.button("🔄 Novo Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# ============================================================
# TELA PRINCIPAL: DASHBOARD ANALÍTICO COMPLETO
# ============================================================
st.subheader("📊 Painel Analítico de Manutenção e Serviços de TI")

if st.session_state.df_tabela is not None:
    df = st.session_state.df_tabela.copy()

    # Tratamento de colunas numéricas
    colunas_valor = ["Valor_Mao_de_Obra_BRL", "Custo_Pecas_Estimado_BRL", "Valor_Total_Sugerido_BRL"]
    for col in colunas_valor:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace("R$", "", regex=False).str.strip().str.replace(",", ".").astype(float)

    # Indicadores KPI
    k1, k2, k3, k4 = st.columns(4)
    total_servicos = len(df)
    ticket_medio = df["Valor_Total_Sugerido_BRL"].mean() if "Valor_Total_Sugerido_BRL" in df.columns else 0
    sla_medio = df["SLA_Horas"].mean() if "SLA_Horas" in df.columns else 0
    remotos = len(df[df["Tipo_Atendimento"].str.contains("Remoto|Online", case=False, na=False)]) if "Tipo_Atendimento" in df.columns else 0

    k1.metric("Total de Serviços", f"{total_servicos} itens")
    k2.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
    k3.metric("SLA Médio", f"{sla_medio:.1f} h")
    k4.metric("Atendimentos Remotos", f"{remotos} itens")

    st.divider()

    # Gráficos
    g1, g2 = st.columns(2)
    with g1:
        if "Codigo_Servico" in df.columns and "Valor_Total_Sugerido_BRL" in df.columns:
            fig_bar = px.bar(
                df,
                x="Codigo_Servico",
                y="Valor_Total_Sugerido_BRL",
                color="Categoria" if "Categoria" in df.columns else None,
                hover_data=["Descricao_Servico", "Tipo_Atendimento"],
                title="Custo Total por Código de Serviço (R$)",
                template="plotly_dark"
            )
            fig_bar.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        if "Tipo_Atendimento" in df.columns:
            fig_pie = px.pie(
                df,
                names="Tipo_Atendimento",
                values="Valor_Total_Sugerido_BRL" if "Valor_Total_Sugerido_BRL" in df.columns else None,
                title="Distribuição de Valores por Tipo de Atendimento",
                hole=0.45,
                template="plotly_dark"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("🔍 Visualizar Base de Dados Completa (CSV)"):
        st.dataframe(df, use_container_width=True)

else:
    st.info("👈 Faça o upload de um arquivo **.CSV** na barra lateral para carregar automaticamente os indicadores, KPIs e gráficos.")


# ============================================================
# WIDGET POP-UP FLUTUANTE (ESTILO E-COMMERCE / WHATSAPP)
# ============================================================
# O st.popover cria o botão flutuante e a janela retrátil
with st.popover("💬", help="Abrir chat de Suporte de TI"):
    # Cabeçalho da janelinha
    st.markdown("""
    <div class="wa-popup-header">
        <div style="font-size: 22px;">🎧</div>
        <div style="flex-grow: 1;">
            <div style="font-weight: 600; font-size: 14px;">Suporte de TI Online</div>
            <div style="font-size: 11px; color: #8696a0;"><span class="status-dot"></span> online agora</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Área de histórico das mensagens
    html_chat = '<div class="whatsapp-scroll-area">'
    if len(st.session_state.messages) == 0:
        html_chat += '<div style="text-align: center; color: #8696a0; font-size: 11px; margin: auto; padding: 10px 0;">🔒 Suporte automatizado com RAG corporativo. Como podemos ajudar?</div>'
    else:
        for m in st.session_state.messages:
            papel = m["role"]
            conteudo = m["content"].replace("\n", "<br>")
            hora = m.get("time", datetime.now().strftime("%H:%M"))
            checks = '<span class="check-read">✓✓</span>' if papel == "user" else ''

            html_chat += (
                f'<div class="msg-row {papel}">'
                f'<div class="chat-bubble {papel}">'
                f'<div>{conteudo}</div>'
                f'<div class="msg-meta">{hora} {checks}</div>'
                f'</div>'
                f'</div>'
            )
    html_chat += '</div>'
    st.markdown(html_chat, unsafe_allow_html=True)

    # Formulário de Envio dentro do Pop-up
    if not st.session_state.chat_iniciado:
        st.caption("⚠️ Conecte suas credenciais na barra lateral para habilitar o envio.")
    else:
        with st.form(key="popup_chat_form", clear_on_submit=True):
            user_msg = st.text_input("Mensagem:", placeholder="Digite sua dúvida ou código de erro...", label_visibility="collapsed")
            enviar = st.form_submit_button("Enviar 📤", use_container_width=True)

            if enviar and user_msg.strip():
                hora_envio = datetime.now().strftime("%H:%M")
                st.session_state.messages.append({"role": "user", "content": user_msg, "time": hora_envio})

                # Montagem do prompt com RAG
                system_instruction = st.session_state.persona
                if st.session_state.conteudo_base:
                    system_instruction += f"\n\n[BASE RAG / CATÁLOGO]:\n{st.session_state.conteudo_base}"

                mensagens_api = [{"role": "system", "content": system_instruction}]
                for m in st.session_state.messages:
                    mensagens_api.append({"role": m["role"], "content": m["content"]})

                try:
                    endpoint_limpo = (
                        st.session_state.saved_endpoint.strip()
                        .replace("/openai/v1", "")
                        .rstrip("/")
                    )
                    client = AzureOpenAI(
                        azure_endpoint=endpoint_limpo,
                        api_key=st.session_state.saved_key.strip(),
                        api_version="2024-06-01"
                    )
                    response = client.chat.completions.create(
                        model=st.session_state.saved_model.strip(),
                        messages=mensagens_api,
                        temperature=0.2
                    )
                    resposta_ia = response.choices[0].message.content

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resposta_ia,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"Erro na conexão com Azure: {e}")
                st.error(f"Erro de conexão com o Azure OpenAI: {e}")
