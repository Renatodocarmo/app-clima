import streamlit as st
import requests
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from datetime import datetime
import json
import os

st.set_page_config(
    page_title="Previsão do Tempo", 
    page_icon="🌤️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

API_KEY = st.secrets["OPENWEATHER_API_KEY"]
FAVORITOS_FILE = "favoritos.json"

WEATHER_ACCENT = {
    '01d': '#FFB347', '01n': '#6C63FF',
    '02d': '#87CEEB', '02n': '#483D8B',
    '03d': '#B0C4DE', '03n': '#2F4F4F',
    '04d': '#808080', '04n': '#4A4A4A',
    '09d': '#4682B4', '09n': '#2C3E50',
    '10d': '#5B9BD5', '10n': '#1F3A5F',
    '11d': '#FF4500', '11n': '#8B0000',
    '13d': '#F0F8FF', '13n': '#708090',
    '50d': '#A9A9A9', '50n': '#696969',
}

def apply_theme(weather_code):
    accent = WEATHER_ACCENT.get(weather_code, '#FFB347')
    
    css = f"""
    <style>
    header[data-testid="stHeader"] {{
        background-color: #1a1a2e !important;
    }}
    
    .stApp {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%) !important;
    }}
    
    body {{
        background: #1a1a2e !important;
    }}
    
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 6px;
        background: {accent};
        z-index: 9999;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: #0a0a1a !important;
        border-right: 2px solid {accent} !important;
    }}
    
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    
    .stTextInput input {{
        background-color: #2a2a4a !important;
        color: white !important;
        border: 2px solid {accent} !important;
        border-radius: 10px;
    }}
    
    .stButton > button {{
        background: {accent} !important;
        color: white !important;
        font-weight: bold;
        border: none;
        border-radius: 12px;
        padding: 14px 24px;
        width: 100%;
    }}
    
    [data-testid="stMetric"] {{
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid {accent}40;
        border-radius: 16px;
        padding: 1.2rem !important;
    }}
    
    [data-testid="stMetric"] label {{
        color: rgba(255, 255, 255, 0.8) !important;
    }}
    
    [data-testid="stMetricValue"] {{
        color: white !important;
        font-size: 1.6rem !important;
    }}
    
    h1, h2, h3, h4 {{
        color: white !important;
    }}
    
    p, span, div, label {{
        color: white !important;
    }}
    
    .clock-box {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 2px solid {accent};
    }}
    
    .hour-card {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid {accent}40;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
    }}
    
    .sugestao-box {{
        background: linear-gradient(135deg, {accent}30, {accent}10);
        border: 2px solid {accent};
        border-radius: 16px;
        padding: 1.5rem;
    }}
    </style>
    
    <script>
    // JavaScript robusto que fica verificando continuamente
    function hideDeployButtons() {{
        // Esconde botões com texto Deploy/Implantar
        var allElements = document.querySelectorAll('*');
        for (var i = 0; i < allElements.length; i++) {{
            var text = allElements[i].textContent || allElements[i].innerText || '';
            if ((text.includes('Deploy') || text.includes('Implantar')) && 
                (allElements[i].tagName === 'BUTTON' || allElements[i].tagName === 'A')) {{
                allElements[i].style.display = 'none';
                allElements[i].style.visibility = 'hidden';
                allElements[i].style.opacity = '0';
                allElements[i].style.pointerEvents = 'none';
            }}
        }}
        
        // Esconde botão de 3 pontinhos
        var kebabButtons = document.querySelectorAll('[aria-label="More options"], [aria-label="Mais opções"], button[aria-label*="options"]');
        for (var i = 0; i < kebabButtons.length; i++) {{
            kebabButtons[i].style.display = 'none';
        }}
    }}
    
    // Executa imediatamente
    hideDeployButtons();
    
    // Executa a cada 500ms para pegar botões que aparecem depois
    setInterval(hideDeployButtons, 500);
    
    // Executa quando o DOM mudar
    var observer = new MutationObserver(function(mutations) {{
        hideDeployButtons();
    }});
    
    observer.observe(document.body, {{
        childList: true,
        subtree: true,
        attributes: true
    }});
    </script>
    """
    st.markdown(css, unsafe_allow_html=True)

def get_sugestao_roupa(temp, descricao, vento):
    sugestoes = []
    if temp <= 10:
        sugestoes.append("🧥 Casaco pesado")
        sugestoes.append("🧣 Cachecol e luvas")
    elif temp <= 18:
        sugestoes.append(" Casaco leve")
        sugestoes.append(" Calça comprida")
    elif temp <= 24:
        sugestoes.append(" Camiseta manga longa")
        sugestoes.append("👖 Calça ou jeans")
    elif temp <= 30:
        sugestoes.append("👕 Camiseta manga curta")
        sugestoes.append("👟 Tênis confortável")
    else:
        sugestoes.append("🎽 Roupa leve")
        sugestoes.append(" Chinelo")
        sugestoes.append(" Protetor solar!")
    
    desc_lower = descricao.lower()
    if 'chuva' in desc_lower:
        sugestoes.append("☂️ Leve guarda-chuva!")
    if vento > 7:
        sugestoes.append("💨 Vento forte")
    
    return sugestoes

def buscar_clima(cidade, units_api):
    url_atual = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY}&lang=pt_br&units={units_api}"
    url_previsao = f"http://api.openweathermap.org/data/2.5/forecast?q={cidade}&appid={API_KEY}&lang=pt_br&units={units_api}"
    
    resposta_atual = requests.get(url_atual)
    resposta_previsao = requests.get(url_previsao)
    
    if resposta_atual.status_code == 200 and resposta_previsao.status_code == 200:
        return {
            'atual': resposta_atual.json(),
            'previsao': resposta_previsao.json()
        }
    return None

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_favoritos(favoritos):
    with open(FAVORITOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(favoritos, f, ensure_ascii=False, indent=2)

if 'favoritos' not in st.session_state:
    st.session_state.favoritos = carregar_favoritos()

if 'cidade_atual' not in st.session_state:
    st.session_state.cidade_atual = "São Paulo"

if 'clima_buscado' not in st.session_state:
    st.session_state.clima_buscado = False

if 'dados_clima' not in st.session_state:
    st.session_state.dados_clima = None

with st.sidebar:
    st.header("⚙️ Configurações")
    
    agora = datetime.now()
    st.markdown(f"""
    <div class="clock-box">
        <h2 style="color: white; margin: 0;">{agora.strftime('%H:%M:%S')}</h2>
        <p style="color: rgba(255,255,255,0.7); margin: 0.5rem 0 0 0;">{agora.strftime('%d/%m/%Y')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    unidade = st.radio("Unidade:", options=["Celsius (°C)", "Fahrenheit (°F)"], index=0)
    
    if unidade == "Celsius (°C)":
        units_api = "metric"
        simbolo = "°C"
    else:
        units_api = "imperial"
        simbolo = "°F"
    
    st.divider()
    st.markdown("⭐ **Favoritas**")
    
    if st.session_state.favoritos:
        for fav in st.session_state.favoritos:
            if st.button(f"📍 {fav}", key=f"fav_{fav}", use_container_width=True):
                st.session_state.cidade_atual = fav
                dados = buscar_clima(fav, units_api)
                if dados:
                    st.session_state.dados_clima = dados
                    st.session_state.clima_buscado = True
                st.rerun()
            
            if st.button("Remover", key=f"rm_{fav}", use_container_width=True):
                st.session_state.favoritos.remove(fav)
                salvar_favoritos(st.session_state.favoritos)
                st.rerun()
    else:
        st.caption("Nenhuma favorita")
    
    st.divider()
    st.info("💡 Digite o nome da cidade!")

cidade_input = st.text_input(" Cidade:", value=st.session_state.cidade_atual)

if cidade_input != st.session_state.cidade_atual:
    st.session_state.cidade_atual = cidade_input
    st.session_state.clima_buscado = False

cidade = st.session_state.cidade_atual

url_atual = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY}&lang=pt_br&units={units_api}"
url_previsao = f"http://api.openweathermap.org/data/2.5/forecast?q={cidade}&appid={API_KEY}&lang=pt_br&units={units_api}"

if st.button("🔍 Buscar Clima", use_container_width=True):
    st.session_state.clima_buscado = True
    resposta_atual = requests.get(url_atual)
    resposta_previsao = requests.get(url_previsao)
    
    if resposta_atual.status_code == 200 and resposta_previsao.status_code == 200:
        st.session_state.dados_clima = {
            'atual': resposta_atual.json(),
            'previsao': resposta_previsao.json()
        }

if st.session_state.clima_buscado and st.session_state.dados_clima:
    dados_atual = st.session_state.dados_clima['atual']
    dados_previsao = st.session_state.dados_clima['previsao']
    
    descricao = dados_atual['weather'][0]['description'].capitalize()
    temperatura = dados_atual['main']['temp']
    sensacao = dados_atual['main']['feels_like']
    minima = dados_atual['main']['temp_min']
    maxima = dados_atual['main']['temp_max']
    umidade = dados_atual['main']['humidity']
    vento = dados_atual['wind']['speed']
    pressao = dados_atual['main']['pressure']
    visibilidade = dados_atual.get('visibility', 10000) / 1000
    icone_codigo = dados_atual['weather'][0]['icon']
    pais = dados_atual['sys']['country']
    lat = dados_atual['coord']['lat']
    lon = dados_atual['coord']['lon']
    
    nascer_sol = datetime.fromtimestamp(dados_atual['sys']['sunrise']).strftime('%H:%M')
    por_sol = datetime.fromtimestamp(dados_atual['sys']['sunset']).strftime('%H:%M')
    
    apply_theme(icone_codigo)
    url_icone = f"http://openweathermap.org/img/wn/{icone_codigo}@2x.png"
    
    if cidade not in st.session_state.favoritos:
        if st.button("⭐ Favoritar"):
            st.session_state.favoritos.append(cidade)
            salvar_favoritos(st.session_state.favoritos)
            st.success(f"✅ {cidade} adicionada!")
    else:
        if st.button("⭐ Favoritada"):
            st.session_state.favoritos.remove(cidade)
            salvar_favoritos(st.session_state.favoritos)
            st.success(f"❌ {cidade} removida!")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(url_icone, width=200)
    with col2:
        st.markdown(f"## 📍 {cidade.title()}, {pais}")
        st.markdown(f"# {temperatura:.1f}{simbolo}")
        st.markdown(f"### {descricao}")
        st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    st.divider()
    
    st.markdown("###  Sugestão do Dia")
    sugestoes = get_sugestao_roupa(temperatura, descricao, vento)
    sugestao_html = "<div class='sugestao-box'><h4>Baseado no clima:</h4>"
    for s in sugestoes:
        sugestao_html += f"<p>• {s}</p>"
    sugestao_html += "</div>"
    st.markdown(sugestao_html, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("###  Detalhes")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("️ Sensação", f"{sensacao:.1f}{simbolo}")
    with col2:
        st.metric("📉 Mínima", f"{minima:.1f}{simbolo}")
    with col3:
        st.metric("📈 Máxima", f"{maxima:.1f}{simbolo}")
    with col4:
        st.metric(" Umidade", f"{umidade}%")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("💨 Vento", f"{vento} m/s")
    with col6:
        st.metric("🌅 Nascer", nascer_sol)
    with col7:
        st.metric("🌇 Pôr", por_sol)
    with col8:
        st.metric("👁️ Visibilidade", f"{visibilidade:.1f} km")
    
    st.markdown(f"<p style='text-align: center; opacity: 0.7;'>📌 {lat:.4f}°, {lon:.4f}°</p>", unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 📈 Temperatura (24h)")
    
    horas_previsao = dados_previsao['list'][:8]
    horarios = []
    temps = []
    feels = []
    
    for item in horas_previsao:
        data_hora = datetime.fromtimestamp(item['dt'])
        horarios.append(data_hora.strftime('%H:%M'))
        temps.append(item['main']['temp'])
        feels.append(item['main']['feels_like'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=horarios, y=temps, mode='lines+markers', name='Temp', line=dict(color='#FFB347', width=3)))
    fig.add_trace(go.Scatter(x=horarios, y=feels, mode='lines+markers', name='Sensação', line=dict(color='#6C63FF', width=3, dash='dash')))
    
    fig.update_layout(
        plot_bgcolor='rgba(255,255,255,0.05)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', title='Horário'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)', title=f'Temp ({simbolo})'),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='white')),
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    st.markdown("### 🗺️ Mapa")
    
    mapa = folium.Map(location=[lat, lon], zoom_start=12, tiles='OpenStreetMap')
    folium.Marker(location=[lat, lon], popup=f"{cidade.title()}: {temperatura:.1f}{simbolo}", icon=folium.Icon(color='red')).add_to(mapa)
    st_folium(mapa, width=None, height=400)
    
    st.divider()
    st.markdown("### 📅 Previsão")
    
    previsao_por_dia = {}
    for item in dados_previsao['list']:
        data_hora = datetime.fromtimestamp(item['dt'])
        dia = data_hora.strftime('%d/%m/%Y')
        if dia not in previsao_por_dia:
            previsao_por_dia[dia] = []
        previsao_por_dia[dia].append(item)
    
    dias_disponiveis = list(previsao_por_dia.keys())
    labels_dias = []
    for i, dia in enumerate(dias_disponiveis):
        if i == 0:
            labels_dias.append("Hoje")
        elif i == 1:
            labels_dias.append("Amanhã")
        else:
            labels_dias.append(f"Dia +{i}")
    
    tabs = st.tabs(labels_dias)
    
    for tab_idx, tab in enumerate(tabs):
        dia = dias_disponiveis[tab_idx]
        previsao_dia = previsao_por_dia[dia]
        
        with tab:
            temps_dia = [item['main']['temp'] for item in previsao_dia]
            temp_max_dia = max(temps_dia)
            temp_min_dia = min(temps_dia)
            
            descricoes = [item['weather'][0]['description'] for item in previsao_dia]
            descricao_principal = max(set(descricoes), key=descricoes.count).capitalize()
            
            st.markdown(f"#### {dia} - {descricao_principal}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**📈 Máx:** {temp_max_dia:.1f}{simbolo}")
            with col2:
                st.markdown(f"**📉 Mín:** {temp_min_dia:.1f}{simbolo}")
            
            st.divider()
            
            num_horas = len(previsao_dia)
            num_colunas = 4
            
            for i in range(0, num_horas, num_colunas):
                cols = st.columns(num_colunas)
                for j in range(num_colunas):
                    idx = i + j
                    if idx < num_horas:
                        item = previsao_dia[idx]
                        data_hora = datetime.fromtimestamp(item['dt'])
                        hora = data_hora.strftime('%H:%M')
                        temp = item['main']['temp']
                        descricao_hora = item['weather'][0]['description'].capitalize()
                        icone_hora = item['weather'][0]['icon']
                        url_icone_hora = f"http://openweathermap.org/img/wn/{icone_hora}@2x.png"
                        umidade_hora = item['main']['humidity']
                        
                        with cols[j]:
                            st.markdown(f"""
                            <div class="hour-card">
                                <p>🕐 {hora}</p>
                                <img src="{url_icone_hora}" width="60">
                                <p style="font-size: 1.5rem; font-weight: bold;">{temp:.1f}{simbolo}</p>
                                <p>{descricao_hora}</p>
                                <p>💧 {umidade_hora}%</p>
                            </div>
                            """, unsafe_allow_html=True)

else:
    apply_theme('01d')
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'> Digite uma cidade e clique em Buscar!</h2>", unsafe_allow_html=True)