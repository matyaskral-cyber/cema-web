from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import json, os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cema-flask-secret-2025')

DATA_FILE = os.path.join(os.path.dirname(__file__), 'content.json')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
ALLOWED_EXT = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'cema2025')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def next_id(items):
    return max((i.get('id', 0) for i in items), default=0) + 1


# ── Static files (images) ──────────────────────
@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ── Main site ──────────────────────────────────
@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', c=data)


# ── Admin: Login ───────────────────────────────
@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin_edit'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_edit'))
        return render_template('admin/login.html', error=True)
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


# ── Admin: Main panel ─────────────────────────
@app.route('/admin/edit', methods=['GET', 'POST'])
@login_required
def admin_edit():
    data = load_data()
    saved = request.args.get('saved')
    if request.method == 'POST':
        # Save static content fields
        for key in ['meta_title', 'meta_description', 'hero_eyebrow', 'hero_nadpis',
                     'hero_text', 'hero_btn1', 'hero_btn2', 'about_nadpis', 'about_text1',
                     'about_text2', 'cta_eyebrow', 'cta_nadpis', 'cta_btn',
                     'kontakt_adresa', 'kontakt_ic', 'kontakt_dic',
                     'kontakt_hodiny_pd', 'kontakt_hodiny_vikend', 'kontakt_maps',
                     'kontakt_form_email', 'kontakt_kariera_email',
                     'footer_text', 'footer_copyright', 'footer_facebook']:
            if key in request.form:
                data[key] = request.form[key]

        # Hero stats
        stats = []
        i = 0
        while f'stat_value_{i}' in request.form:
            v = request.form[f'stat_value_{i}'].strip()
            l = request.form[f'stat_label_{i}'].strip()
            if v and l:
                stats.append({'value': v, 'label': l})
            i += 1
        if stats:
            data['hero_stats'] = stats

        # About features
        features = []
        i = 0
        while f'about_feature_{i}' in request.form:
            f_text = request.form[f'about_feature_{i}'].strip()
            if f_text:
                features.append(f_text)
            i += 1
        if features:
            data['about_features'] = features

        # Services
        sluzby = []
        i = 0
        while f'sluzba_nadpis_{i}' in request.form:
            sluzby.append({
                'cislo': request.form.get(f'sluzba_cislo_{i}', f'0{i+1}'),
                'nadpis': request.form[f'sluzba_nadpis_{i}'],
                'text': request.form.get(f'sluzba_text_{i}', ''),
                'link_text': request.form.get(f'sluzba_link_{i}', '')
            })
            i += 1
        if sluzby:
            data['sluzby'] = sluzby

        # Contact persons
        osoby = []
        i = 0
        while f'osoba_jmeno_{i}' in request.form:
            jmeno = request.form[f'osoba_jmeno_{i}'].strip()
            if jmeno:
                osoby.append({
                    'jmeno': jmeno,
                    'role': request.form.get(f'osoba_role_{i}', ''),
                    'tel': request.form.get(f'osoba_tel_{i}', ''),
                    'email': request.form.get(f'osoba_email_{i}', ''),
                    'inicialy': request.form.get(f'osoba_inicialy_{i}', '')
                })
            i += 1
        if osoby:
            data['kontakt_osoby'] = osoby

        save_data(data)
        return redirect(url_for('admin_edit', saved=1))

    return render_template('admin/edit.html', c=data, saved=saved)


# ── Admin: Upload ──────────────────────────────
@app.route('/admin/upload', methods=['POST'])
@login_required
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'ok': False, 'error': 'No filename'}), 400
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'ok': False, 'error': 'Invalid format'}), 400
    filename = secure_filename(f.filename)
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    return jsonify({'ok': True, 'path': f'images/{filename}'})


# ── Admin API: CRUD for dynamic content ────────

# Stroje
@app.route('/admin/api/stroje', methods=['GET'])
@login_required
def api_stroje_list():
    return jsonify(load_data().get('stroje', []))


@app.route('/admin/api/stroje', methods=['POST'])
@login_required
def api_stroje_save():
    data = load_data()
    item = request.json
    items = data.get('stroje', [])
    if item.get('id'):
        for i, s in enumerate(items):
            if s['id'] == item['id']:
                items[i] = item
                break
    else:
        item['id'] = next_id(items)
        items.insert(0, item)
    data['stroje'] = items
    save_data(data)
    return jsonify({'ok': True, 'id': item['id']})


@app.route('/admin/api/stroje/<int:item_id>', methods=['DELETE'])
@login_required
def api_stroje_delete(item_id):
    data = load_data()
    data['stroje'] = [s for s in data.get('stroje', []) if s['id'] != item_id]
    save_data(data)
    return jsonify({'ok': True})


# Aktuality
@app.route('/admin/api/aktuality', methods=['GET'])
@login_required
def api_aktuality_list():
    return jsonify(load_data().get('aktuality', []))


@app.route('/admin/api/aktuality', methods=['POST'])
@login_required
def api_aktuality_save():
    data = load_data()
    item = request.json
    items = data.get('aktuality', [])
    if item.get('id'):
        for i, s in enumerate(items):
            if s['id'] == item['id']:
                items[i] = item
                break
    else:
        item['id'] = next_id(items)
        items.insert(0, item)
    data['aktuality'] = items
    save_data(data)
    return jsonify({'ok': True, 'id': item['id']})


@app.route('/admin/api/aktuality/<int:item_id>', methods=['DELETE'])
@login_required
def api_aktuality_delete(item_id):
    data = load_data()
    data['aktuality'] = [s for s in data.get('aktuality', []) if s['id'] != item_id]
    save_data(data)
    return jsonify({'ok': True})


# Recenze
@app.route('/admin/api/recenze', methods=['GET'])
@login_required
def api_recenze_list():
    return jsonify(load_data().get('recenze', []))


@app.route('/admin/api/recenze', methods=['POST'])
@login_required
def api_recenze_save():
    data = load_data()
    item = request.json
    items = data.get('recenze', [])
    if item.get('id'):
        for i, s in enumerate(items):
            if s['id'] == item['id']:
                items[i] = item
                break
    else:
        item['id'] = next_id(items)
        items.insert(0, item)
    data['recenze'] = items
    save_data(data)
    return jsonify({'ok': True, 'id': item['id']})


@app.route('/admin/api/recenze/<int:item_id>', methods=['DELETE'])
@login_required
def api_recenze_delete(item_id):
    data = load_data()
    data['recenze'] = [s for s in data.get('recenze', []) if s['id'] != item_id]
    save_data(data)
    return jsonify({'ok': True})


# Kariéra
@app.route('/admin/api/kariera', methods=['GET'])
@login_required
def api_kariera_list():
    return jsonify(load_data().get('kariera', []))


@app.route('/admin/api/kariera', methods=['POST'])
@login_required
def api_kariera_save():
    data = load_data()
    item = request.json
    items = data.get('kariera', [])
    if item.get('id'):
        for i, s in enumerate(items):
            if s['id'] == item['id']:
                items[i] = item
                break
    else:
        item['id'] = next_id(items)
        items.insert(0, item)
    data['kariera'] = items
    save_data(data)
    return jsonify({'ok': True, 'id': item['id']})


@app.route('/admin/api/kariera/<int:item_id>', methods=['DELETE'])
@login_required
def api_kariera_delete(item_id):
    data = load_data()
    data['kariera'] = [s for s in data.get('kariera', []) if s['id'] != item_id]
    save_data(data)
    return jsonify({'ok': True})


# Galerie
@app.route('/admin/api/galerie', methods=['POST'])
@login_required
def api_galerie_save():
    data = load_data()
    data['galerie'] = request.json
    save_data(data)
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True, port=5051)
