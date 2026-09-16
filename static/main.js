/* ══════════════════════════════════════════════
   main.js – Voca-IA
   Test de Intereses Vocacionales y Profesionales
   ══════════════════════════════════════════════ */

// ── Estado del test ───────────────────────────
let preguntas = [];
let preguntaActual = 0;
let respuestas = [];
let seleccionActual = null;
let historialChat = [];

// ── Al cargar la página ───────────────────────
document.addEventListener('DOMContentLoaded', function() {
  if (document.getElementById('areas-grid')) {
    cargarAreas();
  }
  if (document.getElementById('test-preguntas')) {
    cargarPreguntas();
  }
  initNavbar();
  initBotonesNavbar();
  
  if (window.location.pathname.includes('chatbot')) {
    recibirMensajeDesdeURL();
  }
});

/* ════════════════════════════════════════════
   NAVBAR
   ════════════════════════════════════════════ */
function initNavbar() {
  var navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    });
  }
}

function initBotonesNavbar() {
  var links = document.querySelectorAll('.nav-link');
  links.forEach(function(link) {
    link.addEventListener('click', function(e) {
      if (this.getAttribute('href').startsWith('#')) {
        e.preventDefault();
        var id = this.getAttribute('href').replace('#', '');
        var seccion = document.getElementById(id);
        if (seccion) {
          seccion.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });
}

function toggleMenu() {
  var links = document.querySelector('.nav-links');
  if (links.style.display === 'flex') {
    links.style.display = 'none';
  } else {
    links.style.display = 'flex';
    links.style.flexDirection = 'column';
    links.style.position = 'absolute';
    links.style.top = '65px';
    links.style.left = '0';
    links.style.right = '0';
    links.style.background = 'rgba(245,237,227,0.98)';
    links.style.padding = '24px';
    links.style.borderBottom = '1px solid #e0cfc0';
    links.style.zIndex = '999';
  }
}

/* ════════════════════════════════════════════
   ÁREAS
   ════════════════════════════════════════════ */
async function cargarAreas() {
  try {
    var res = await fetch('/api/carreras');
    var datos = await res.json();
    renderAreas(datos);
  } catch (err) {
    console.error('Error cargando áreas:', err);
  }
}

function renderAreas(datos) {
  var grid = document.getElementById('areas-grid');
  if (!grid) return;
  grid.innerHTML = '';
  var claves = Object.keys(datos);
  claves.forEach(function(clave) {
    var area = datos[clave];
    var tags = area.carreras.slice(0, 3).map(function(c) {
      return '<span class="tag">' + c + '</span>';
    }).join('');
    var card = document.createElement('div');
    card.className = 'area-card';
    card.innerHTML = `
      <div class="area-card-icon">${area.icono}</div>
      <h3 class="area-card-nombre">${area.nombre}</h3>
      <p class="area-card-desc">${area.descripcion}</p>
      <div class="area-card-tags">${tags}</div>
    `;
    grid.appendChild(card);
  });
}

/* ════════════════════════════════════════════
   TEST VOCACIONAL – Respuestas binarias
   ════════════════════════════════════════════ */
async function cargarPreguntas() {
  try {
    var res = await fetch('/api/preguntas');
    preguntas = await res.json();
  } catch (err) {
    console.error('Error cargando preguntas:', err);
  }
}

function iniciarTest() {
  document.getElementById('test-inicio').classList.add('hidden');
  document.getElementById('test-preguntas').classList.remove('hidden');
  preguntaActual = 0;
  respuestas = [];
  seleccionActual = null;
  mostrarPregunta();
}

function mostrarPregunta() {
  if (preguntaActual >= preguntas.length) {
    enviarResultado();
    return;
  }

  var pregunta = preguntas[preguntaActual];
  var numDisplay = (preguntaActual + 1).toString().padStart(2, '0');
  
  document.getElementById('pregunta-numero-display').textContent = numDisplay;
  document.getElementById('pregunta-texto').textContent = pregunta.pregunta;
  document.getElementById('pregunta-num').textContent = 
    `Pregunta ${preguntaActual + 1} de ${preguntas.length}`;
  
  var progreso = ((preguntaActual) / preguntas.length) * 100;
  document.getElementById('progress-fill').style.width = progreso + '%';
  document.getElementById('progreso-pct').textContent = Math.round(progreso) + '%';

  var container = document.getElementById('opciones-container');
  container.innerHTML = '';
  
  var btnSi = document.createElement('button');
  btnSi.className = 'opcion-btn opcion-si';
  btnSi.innerHTML = '✅ Me interesa';
  btnSi.onclick = function() { seleccionarBinario(true); };
  container.appendChild(btnSi);
  
  var btnNo = document.createElement('button');
  btnNo.className = 'opcion-btn opcion-no';
  btnNo.innerHTML = '❌ No me interesa';
  btnNo.onclick = function() { seleccionarBinario(false); };
  container.appendChild(btnNo);
  
  if (respuestas[preguntaActual] !== undefined) {
    seleccionActual = respuestas[preguntaActual].me_interesa;
    if (seleccionActual === true) btnSi.classList.add('selected');
    else if (seleccionActual === false) btnNo.classList.add('selected');
  } else {
    seleccionActual = null;
  }

  document.getElementById('btn-siguiente').disabled = seleccionActual === null;
  document.getElementById('btn-anterior').disabled = preguntaActual === 0;
}

function seleccionarBinario(valor) {
  seleccionActual = valor;
  var buttons = document.querySelectorAll('.opcion-btn');
  buttons.forEach(function(btn) {
    btn.classList.remove('selected');
  });
  
  if (valor === true) {
    document.querySelector('.opcion-si').classList.add('selected');
  } else {
    document.querySelector('.opcion-no').classList.add('selected');
  }
  
  document.getElementById('btn-siguiente').disabled = false;
}

function siguientePregunta() {
  if (seleccionActual === null) return;
  
  var pregunta = preguntas[preguntaActual];
  respuestas[preguntaActual] = {
    pregunta_id: pregunta.id,
    area: pregunta.area,
    me_interesa: seleccionActual
  };
  
  preguntaActual++;
  if (preguntaActual < preguntas.length) {
    mostrarPregunta();
  } else {
    enviarResultado();
  }
}

function anteriorPregunta() {
  if (preguntaActual > 0) {
    if (seleccionActual !== null) {
      var pregunta = preguntas[preguntaActual];
      respuestas[preguntaActual] = {
        pregunta_id: pregunta.id,
        area: pregunta.area,
        me_interesa: seleccionActual
      };
    }
    preguntaActual--;
    mostrarPregunta();
  }
}

async function enviarResultado() {
  try {
    var respuestasValidas = respuestas.filter(function(r) { return r !== undefined; });
    
    var res = await fetch('/api/resultado', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ respuestas: respuestasValidas })
    });
    
    var data = await res.json();
    mostrarResultado(data);
    
  } catch (err) {
    console.error('Error enviando resultado:', err);
  }
}

function mostrarResultado(data) {
  document.getElementById('test-preguntas').classList.add('hidden');
  document.getElementById('test-resultado').classList.remove('hidden');
  
  var perfil = data.perfil_principal;
  
  document.getElementById('resultado-nombre').textContent = perfil.nombre;
  document.getElementById('resultado-desc').textContent = perfil.descripcion;
  
  var mainCard = document.getElementById('resultado-main');
  var carrerasHTML = perfil.carreras.map(function(c) {
    return `<li>${c}</li>`;
  }).join('');
  
  mainCard.innerHTML = `
    <div class="resultado-main-card">
      <span class="pct-badge">${perfil.porcentaje}% de afinidad (${perfil.puntaje}/${perfil.total})</span>
      <h4>${perfil.icono} ${perfil.nombre}</h4>
      <p>${perfil.descripcion}</p>
      <h5 style="margin-top:16px;margin-bottom:8px;">Carreras recomendadas:</h5>
      <ul class="carrera-list">${carrerasHTML}</ul>
      <h5 style="margin-top:16px;margin-bottom:8px;">Universidades:</h5>
      <ul class="carrera-list">
        ${perfil.universidades.map(u => `<li>🏫 ${u}</li>`).join('')}
      </ul>
    </div>
  `;
  
  var otrosDiv = document.getElementById('resultado-otros');
  if (data.otros_perfiles && data.otros_perfiles.length > 0) {
    var otrosHTML = '<h4 class="resultado-otros-title">Otras áreas con afinidad:</h4>';
    data.otros_perfiles.forEach(function(p) {
      otrosHTML += `
        <div class="otro-card">
          <div class="otro-card-nombre">${p.icono} ${p.nombre}</div>
          <div class="otro-card-pct">${p.porcentaje}% de afinidad (${p.puntaje}/${p.total})</div>
        </div>
      `;
    });
    otrosDiv.innerHTML = otrosHTML;
  } else {
    otrosDiv.innerHTML = '';
  }
}

function reiniciarTest() {
  document.getElementById('test-resultado').classList.add('hidden');
  document.getElementById('test-inicio').classList.remove('hidden');
  preguntaActual = 0;
  respuestas = [];
  seleccionActual = null;
}

/* ════════════════════════════════════════════
   CHATBOT
   ════════════════════════════════════════════ */
async function enviarChat() {
  const input = document.getElementById('chat-input');
  const mensaje = input.value.trim();
  
  if (!mensaje) return;
  
  agregarMensaje(mensaje, 'usuario');
  input.value = '';
  
  document.getElementById('chat-typing').classList.remove('hidden');
  
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensaje: mensaje })
    });
    
    const data = await res.json();
    
    document.getElementById('chat-typing').classList.add('hidden');
    agregarMensaje(data.respuesta, 'bot');
    
  } catch (err) {
    console.error('Error:', err);
    document.getElementById('chat-typing').classList.add('hidden');
    agregarMensaje('Lo siento, hubo un error. Intenta de nuevo.', 'bot');
  }
}

function agregarMensaje(texto, tipo) {
  const container = document.getElementById('chat-mensajes');
  const div = document.createElement('div');
  div.className = `mensaje ${tipo}`;
  
  let avatarHTML;
  if (tipo === 'usuario') {
    avatarHTML = '👤';
  } else {
    avatarHTML = '<img src="/static/logo.png" alt="IA" style="width:100%;height:100%;object-fit:contain;">';
  }
  
  div.innerHTML = `
    <div class="msg-avatar">${avatarHTML}</div>
    <div class="msg-burbuja">${texto}</div>
  `;
  
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function usarSugerencia(boton) {
  const input = document.getElementById('chat-input');
  input.value = boton.textContent;
  enviarChat();
}

function recibirMensajeDesdeURL() {
  const params = new URLSearchParams(window.location.search);
  const mensaje = params.get('mensaje');
  if (mensaje && document.getElementById('chat-input')) {
    setTimeout(function() {
      document.getElementById('chat-input').value = mensaje;
      enviarChat();
    }, 800);
  }
}

/* ════════════════════════════════════════════
   LIMPIAR CHAT (Nueva conversación)
   ════════════════════════════════════════════ */
async function limpiarChat() {
  try {
    // 1. Borra el historial en el servidor (sesión de Flask)
    await fetch('/api/chat/limpiar', { method: 'POST' });

    // 2. Borra los mensajes en pantalla y muestra el saludo inicial
    const contenedorMensajes = document.getElementById('chat-mensajes');
    if (contenedorMensajes) {
      contenedorMensajes.innerHTML = `
        <div class="mensaje bot">
          <div class="msg-avatar">
            <img src="/static/logo.png" alt="IA" style="width:100%;height:100%;object-fit:contain;">
          </div>
          <div class="msg-burbuja">
            ¡Hola! Soy tu orientador vocacional virtual de la <strong>I.E. San Luis de Gaceno</strong>.
            Estoy aquí para ayudarte a explorar carreras y resolver dudas sobre educación superior.<br/><br/>
            ¿En qué te puedo ayudar hoy?
          </div>
        </div>
      `;
    }

    // 3. Enfocar el input
    const inputChat = document.getElementById('chat-input');
    if (inputChat) inputChat.focus();

  } catch (error) {
    console.error('Error al limpiar el chat:', error);
  }
}

/* ════════════════════════════════════════════
   FORMULARIO DE CONTACTO (con correo del usuario)
   ════════════════════════════════════════════ */
async function enviarMensaje() {
  const nombre   = document.getElementById('form-nombre').value.trim();
  const correo   = document.getElementById('form-correo').value.trim();
  const grado    = document.getElementById('form-grado').value;
  const mensaje  = document.getElementById('form-mensaje').value.trim();
  const feedback = document.getElementById('form-feedback');

  if (!nombre || !correo || !grado || !mensaje) {
    feedback.textContent = ' Por favor completa todos los campos';
    feedback.style.color = '#A85A4A';
    return;
  }

  // Validación simple de correo
  if (!correo.includes('@') || !correo.split('@')[1].includes('.')) {
    feedback.textContent = ' Ingresa un correo electrónico válido';
    feedback.style.color = '#A85A4A';
    return;
  }

  feedback.textContent = ' Enviando…';
  feedback.style.color = '#6b5040';

  try {
    const res = await fetch('/api/contacto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre, correo, grado, mensaje })
    });
    const data = await res.json();

    if (data.ok) {
      feedback.textContent = ' ¡Mensaje enviado! Pronto te contactaremos.';
      feedback.style.color = '#7A8B6F';
      document.getElementById('form-nombre').value  = '';
      document.getElementById('form-correo').value  = '';
      document.getElementById('form-grado').value   = '';
      document.getElementById('form-mensaje').value = '';
      setTimeout(() => { feedback.textContent = ''; }, 6000);
    } else {
      feedback.textContent = '❌ Error: ' + (data.error || 'No se pudo enviar');
      feedback.style.color = '#A85A4A';
    }
  } catch (err) {
    console.error(err);
    feedback.textContent = '❌ Error de conexión. Intenta de nuevo.';
    feedback.style.color = '#A85A4A';
  }
}