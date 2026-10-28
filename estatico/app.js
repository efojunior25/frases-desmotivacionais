(function () {
  // Cookies: scripts de anúncio só rodam depois do "Aceitar"
  var aviso = document.getElementById('aviso-cookies');
  function guardado() { try { return localStorage.getItem('cookies'); } catch (e) { return null; } }
  function guardar(v) { try { localStorage.setItem('cookies', v); } catch (e) {} }
  function ativarAnuncios() {
    document.querySelectorAll('script[data-anuncio]').forEach(function (velho) {
      var novo = document.createElement('script');
      Array.prototype.forEach.call(velho.attributes, function (a) {
        if (a.name !== 'type' && a.name !== 'data-anuncio') novo.setAttribute(a.name, a.value);
      });
      novo.text = velho.text;
      velho.parentNode.replaceChild(novo, velho);
    });
  }
  if (guardado() === 'sim') ativarAnuncios();
  else if (guardado() === null && aviso) aviso.hidden = false;
  if (aviso) {
    document.getElementById('cookies-aceitar').addEventListener('click', function () {
      guardar('sim'); aviso.hidden = true; ativarAnuncios();
    });
    document.getElementById('cookies-recusar').addEventListener('click', function () {
      guardar('nao'); aviso.hidden = true;
    });
    document.getElementById('gerenciar-cookies').addEventListener('click', function () {
      aviso.hidden = false;
    });
  }

  // Dificulta copiar e arrastar as imagens das frases
  document.addEventListener('contextmenu', function (e) {
    if (e.target.closest('.frase-img')) e.preventDefault();
  });
  document.addEventListener('dragstart', function (e) {
    if (e.target.closest('.frase-img')) e.preventDefault();
  });

  // Compartilhamento nativo do celular (Instagram, Stories, etc.) enviando a imagem
  if (navigator.share) {
    document.querySelectorAll('.compartilhar').forEach(function (box) {
      var btn = box.querySelector('.btn-nativo');
      btn.hidden = false;
      btn.addEventListener('click', function () {
        fetch(box.dataset.img)
          .then(function (r) { return r.blob(); })
          .then(function (blob) {
            var arquivo = new File([blob], 'frase.jpg', { type: 'image/jpeg' });
            var dados = { files: [arquivo], text: box.dataset.link };
            if (navigator.canShare && navigator.canShare(dados)) return navigator.share(dados);
            return navigator.share({ title: box.dataset.titulo, url: box.dataset.link });
          })
          .catch(function () {});
      });
    });
  }

  function carregarIndice() {
    return fetch('/busca.json').then(function (r) { return r.json(); });
  }

  // Frase aleatória
  if (location.pathname === '/aleatoria/') {
    carregarIndice().then(function (lista) {
      location.replace(lista[Math.floor(Math.random() * lista.length)].u);
    });
  }

  // Busca
  if (location.pathname === '/busca/') {
    var q = new URLSearchParams(location.search).get('q') || '';
    var campo = document.getElementById('q2');
    var status = document.getElementById('busca-status');
    var ul = document.getElementById('busca-resultados');
    campo.value = q;
    var normal = function (s) { return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); };
    if (q.trim()) {
      carregarIndice().then(function (lista) {
        var termos = normal(q).split(/\s+/).filter(Boolean);
        var achadas = lista.filter(function (f) {
          var t = normal(f.t);
          return termos.every(function (x) { return t.indexOf(x) !== -1; });
        });
        status.textContent = achadas.length ? achadas.length + ' frase(s) encontrada(s).' : 'Nenhuma frase encontrada. Como tudo na vida.';
        achadas.forEach(function (f) {
          var li = document.createElement('li');
          var a = document.createElement('a');
          a.href = f.u;
          var img = document.createElement('img');
          img.className = 'frase-img';
          img.src = f.i; img.alt = f.t; img.width = 540; img.height = 540; img.loading = 'lazy';
          a.appendChild(img); li.appendChild(a); ul.appendChild(li);
        });
      });
    }
  }
})();
