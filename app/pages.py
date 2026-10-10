INSCRIPTION_HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inscription membre</title>
<style>
  :root { --bg:#f4f5fb; --card:#fff; --txt:#1c1d2b; --muted:#666a80; --accent:#3f4a8a; --err:#b3261e; --ok:#1b7a3d; --line:#cfd2e3; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14151f; --card:#1e2030; --txt:#eceefa; --muted:#a3a7c0; --accent:#8e9cf0; --err:#ff8a80; --ok:#7bd99a; --line:#3a3d57; }
  }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:var(--bg); color:var(--txt); }
  main { max-width: 440px; margin: 0 auto; padding: 24px 16px 40px; }
  .card { background:var(--card); border-radius:16px; padding:22px; box-shadow:0 2px 10px rgba(0,0,0,.08); }
  h1 { font-size:1.4rem; margin:0 0 4px; }
  p.sub { color:var(--muted); margin:0 0 18px; font-size:.95rem; }
  label { display:block; font-weight:600; margin:14px 0 6px; font-size:.95rem; }
  input, select { width:100%; padding:13px; font-size:1rem; border:1px solid var(--line); border-radius:10px; background:transparent; color:var(--txt); }
  button { width:100%; margin-top:22px; padding:14px; font-size:1.05rem; font-weight:600; border:0; border-radius:12px; background:var(--accent); color:#fff; }
  button:disabled { opacity:.6; }
  #msg { margin-top:16px; font-size:.97rem; line-height:1.4; }
  .err { color:var(--err); } .ok { color:var(--ok); }
  small { display:block; margin-top:18px; color:var(--muted); font-size:.8rem; line-height:1.4; }
</style>
</head>
<body>
<main>
  <div class="card">
    <h1>Inscription membre</h1>
    <p class="sub">Remplissez vos informations exactement comme sur votre pièce d'identité.</p>
    <form id="f" novalidate>
      <label for="prenom">Prénom</label>
      <input id="prenom" autocomplete="given-name" required>
      <label for="nom">Nom</label>
      <input id="nom" autocomplete="family-name" required>
      <label for="type">Pièce d'identité</label>
      <select id="type">
        <option value="cin">Carte d'identification nationale (CIN)</option>
        <option value="permis">Permis de conduire haïtien</option>
      </select>
      <label for="num">Numéro d'identification</label>
      <input id="num" inputmode="text" autocomplete="off" required>
      <button id="btn" type="submit">S'inscrire</button>
      <div id="msg" role="status"></div>
    </form>
    <small>Votre inscription sera examinée avant validation. Vos informations ne servent qu'à vérifier votre appartenance.</small>
  </div>
</main>
<script>
const f = document.getElementById('f'), msg = document.getElementById('msg'), btn = document.getElementById('btn');
f.addEventListener('submit', async (e) => {
  e.preventDefault();
  msg.className = ''; msg.textContent = "Envoi en cours… (jusqu'à une minute si le serveur se réveille)";
  btn.disabled = true;
  const body = {
    nom: document.getElementById('nom').value.trim(),
    prenom: document.getElementById('prenom').value.trim(),
    id_type: document.getElementById('type').value,
    id_number: document.getElementById('num').value.trim()
  };
  try {
    const r = await fetch('/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    const d = await r.json().catch(() => ({}));
    if (r.ok) {
      msg.className = 'ok'; msg.textContent = d.message || 'Inscription reçue, en attente de validation.';
      f.reset();
    } else {
      msg.className = 'err';
      msg.textContent = (typeof d.detail === 'string') ? d.detail
        : 'Vérifiez les champs : nom et prénom (2 caractères minimum), numéro (4 caractères minimum).';
    }
  } catch (err) {
    msg.className = 'err'; msg.textContent = 'Connexion impossible. Vérifiez votre réseau et réessayez.';
  }
  btn.disabled = false;
});
</script>
</body>
</html>
"""
