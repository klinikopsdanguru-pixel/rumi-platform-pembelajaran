from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_ # <-- TAMBAHKAN BARIS INI
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import string
from functools import wraps

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'rumi.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'kunci_rahasia_rumi_yang_sangat_aman'
db = SQLAlchemy(app)

# --- FUNGSI BANTU ---
def generate_pairing_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not User.query.filter_by(kode_pairing=code).first():
            return code

def create_default_badges():
    # Fungsi ini memastikan lencana "Langkah Pertama" selalu ada di database.
    if Badge.query.filter_by(nama="Langkah Pertama").first() is None:
        icon_langkah = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="currentColor" width="48" height="48"><path d="M256 512c141.4 0 256-114.6 256-256S397.4 0 256 0S0 114.6 0 256S114.6 512 256 512zM159.3 388.7c-2.6 8.4-11.6 13.2-20 10.5s-13.2-11.6-10.5-20l32-96c2.3-7 8.5-12.1 15.9-13.4l96-16c8.4-1.4 16.6 2.6 20 10.5s2.6 16.6-5.8 20L184 319.3l-24.7 69.4z"/></svg>'
        badge = Badge(nama="Langkah Pertama", deskripsi="Diberikan saat berhasil menyelesaikan konten belajar pertama kali.", icon_url=icon_langkah)
        db.session.add(badge)
        db.session.commit()
        print("Lencana 'Langkah Pertama' berhasil dibuat!")

def check_and_award_badges(user):
    progress_count = user.progress.count()
    owned_badge_ids = {user_badge.badge_id for user_badge in user.badges}

    # Logika Lencana 1: "Langkah Pertama"
    badge_langkah_pertama = Badge.query.filter_by(nama="Langkah Pertama").first()
    if badge_langkah_pertama and badge_langkah_pertama.id not in owned_badge_ids:
        if progress_count == 1:
            new_user_badge = UserBadge(user_id=user.id, badge_id=badge_langkah_pertama.id)
            db.session.add(new_user_badge)
            flash(f'🎉 Selamat! Anda mendapatkan lencana baru: "{badge_langkah_pertama.nama}"', 'success')

    # Logika Lencana 2: Lencana per Materi Pokok
    completed_konten_ids = {p.konten_id for p in user.progress}
    related_materis = MateriPokok.query.join(KontenBelajar).filter(KontenBelajar.id.in_(completed_konten_ids)).distinct().all()

    for materi in related_materis:
        badge_for_materi = Badge.query.filter_by(materi_pokok_id=materi.id).first()
        if badge_for_materi and badge_for_materi.id not in owned_badge_ids:
            materi_konten_ids = {k.id for k in materi.kontens}
            if materi_konten_ids and materi_konten_ids.issubset(completed_konten_ids):
                new_user_badge = UserBadge(user_id=user.id, badge_id=badge_for_materi.id)
                db.session.add(new_user_badge)
                flash(f'🏆 Selamat! Anda mendapatkan lencana baru: "{badge_for_materi.nama}"', 'success')
    
    db.session.commit()

def generate_badge_icon(color):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512" fill="{color}" width="48" height="48"><path d="M288 0c-12.2 .1-24.2 2.1-35.5 5.9L11.2 113.2c-11.9 4-21.8 12.5-27.4 23.4S-1.5 162.3 5.4 172l152 211.2c11.3 15.8 30.1 24.8 49.3 24.8H369.3c19.2 0 38-9 49.3-24.8L570.6 172c6.9-9.7 8.9-22.4 3.3-33.3s-15.5-19.4-27.4-23.4L323.5 5.9C312.2 2.1 300.2 0 288 0zM288 64c5.3 0 10.5 .7 15.5 2.1l141.2 39.2L358.5 208H217.5L131.3 105.3 272.5 66.1C277.5 64.7 282.7 64 288 64z"/></svg>'

# --- MODEL DATABASE ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    nama_sekolah = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    peran = db.Column(db.String(10), nullable=False)
    kelas = db.Column(db.String(10))
    kode_pairing = db.Column(db.String(10), unique=True, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    tps = db.relationship('TujuanPembelajaran', backref='guru', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class TujuanPembelajaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deskripsi = db.Column(db.Text, nullable=False)
    kelas_tujuan = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    materis = db.relationship('MateriPokok', backref='tp', lazy=True, cascade="all, delete-orphan")

class MateriPokok(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    deskripsi = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    tp_id = db.Column(db.Integer, db.ForeignKey('tujuan_pembelajaran.id'), nullable=False)
    kontens = db.relationship('KontenBelajar', backref='materi', lazy=True, cascade="all, delete-orphan")
    badge = db.relationship('Badge', backref='materi', uselist=False, cascade="all, delete-orphan")

class KontenBelajar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    tipe = db.Column(db.String(50), nullable=False)
    alur = db.Column(db.String(50), nullable=False)
    sumber_url = db.Column(db.String(500), nullable=False)
    urutan = db.Column(db.Integer, default=0)
    materi_id = db.Column(db.Integer, db.ForeignKey('materi_pokok.id'), nullable=False)

class ProgressSiswa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    konten_id = db.Column(db.Integer, db.ForeignKey('konten_belajar.id'), nullable=False)
    tanggal_selesai = db.Column(db.DateTime, default=db.func.current_timestamp())
    __table_args__ = (db.UniqueConstraint('user_id', 'konten_id', name='_user_konten_uc'),)
    user = db.relationship('User', backref=db.backref('progress', lazy='dynamic', cascade="all, delete-orphan"))

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    deskripsi = db.Column(db.String(200), nullable=False)
    icon_url = db.Column(db.Text, nullable=False)
    materi_pokok_id = db.Column(db.Integer, db.ForeignKey('materi_pokok.id'), nullable=True, unique=True)

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    tanggal_dapat = db.Column(db.DateTime, default=db.func.current_timestamp())
    user = db.relationship('User', backref=db.backref('badges', lazy=True, cascade="all, delete-orphan"))
    badge = db.relationship('Badge')

class PojokBaca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    deskripsi = db.Column(db.Text, nullable=True)
    kategori = db.Column(db.String(50), nullable=True)
    url_sampul = db.Column(db.String(500), nullable=True)
    url_konten = db.Column(db.String(500), nullable=False)

class Notifikasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pengirim_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    penerima_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    konten = db.Column(db.Text, nullable=False)
    sudah_dibaca = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relasi untuk mengambil nama pengirim
    pengirim = db.relationship('User', foreign_keys=[pengirim_id])

# --- DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Anda harus masuk terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_role') != role:
                flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash('Anda harus menjadi admin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        # Query ini HANYA untuk menghitung angka di lonceng
        unread_count = Notifikasi.query.filter_by(
            penerima_id=session['user_id'], 
            sudah_dibaca=False
        ).count()

        # Query ini untuk menampilkan 5 notifikasi TERBARU di dropdown
        recent_notifs = Notifikasi.query.filter_by(
            penerima_id=session['user_id']
        ).order_by(Notifikasi.timestamp.desc()).limit(10).all()

        return dict(
            notifikasi_header=recent_notifs, # Ganti nama variabel
            jumlah_notifikasi_belum_dibaca=unread_count
        )
    return dict()

# --- ROUTING OTENTIKASI ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            session['user_id'] = user.id
            session['user_name'] = user.nama_lengkap
            session['user_role'] = user.peran
            flash(f'Selamat datang kembali, {user.nama_lengkap}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Anda telah berhasil keluar.', 'info')
    return redirect(url_for('index'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('register_student'))
        
        new_user = User(
            nama_lengkap=request.form.get('nama'), 
            nama_sekolah=request.form.get('sekolah'), 
            kelas=request.form.get('kelas'), 
            username=username, 
            peran='siswa',
            kode_pairing=generate_pairing_code()
        )
        new_user.set_password(request.form.get('password'))
        db.session.add(new_user)
        db.session.commit()
        flash('Akun siswa berhasil dibuat! Silakan masuk.', 'success')
        return redirect(url_for('login'))
    
    schools_query = db.session.query(User.nama_sekolah).filter_by(peran='guru').distinct().all()
    schools = [school[0] for school in schools_query]
    return render_template('register_student.html', schools=schools)

@app.route('/register/teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('register_teacher'))
        
        new_user = User(
            nama_lengkap=request.form.get('nama'), 
            nama_sekolah=request.form.get('sekolah'), 
            username=username, 
            peran='guru'
        )
        new_user.set_password(request.form.get('password'))
        db.session.add(new_user)
        db.session.commit()
        flash('Akun guru berhasil dibuat! Silakan masuk.', 'success')
        return redirect(url_for('login'))
    return render_template('register_teacher.html')

@app.route('/register/parent', methods=['GET', 'POST'])
def register_parent():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('register_parent'))
        
        new_user = User(
            nama_lengkap=request.form.get('nama'), 
            nama_sekolah="-", 
            username=username, 
            peran='orangtua'
        )
        new_user.set_password(request.form.get('password'))
        db.session.add(new_user)
        db.session.commit()
        flash('Akun orang tua berhasil dibuat! Silakan masuk.', 'success')
        return redirect(url_for('login'))
    return render_template('register_parent.html')

# --- ROUTING APLIKASI UTAMA ---

@app.route('/dashboard')
@login_required
def dashboard():
    # Logika untuk SISWA
    if session['user_role'] == 'siswa':
        user = User.query.get(session['user_id'])
        
        # --- LOGIKA BARU UNTUK MENGAMBIL DATA DINAMIS ---
        
        # 1. Ambil data statistik umum
        all_materis_query = MateriPokok.query.join(TujuanPembelajaran).filter(
            TujuanPembelajaran.kelas_tujuan == user.kelas, 
            MateriPokok.status == 'published'
        )
        all_materis = all_materis_query.order_by(TujuanPembelajaran.id, MateriPokok.id).all()
        
        selesai_konten_ids = {p.konten_id for p in user.progress}
        selesai_materi_count = 0
        for materi in all_materis:
            konten_ids_materi = {k.id for k in materi.kontens}
            if konten_ids_materi and konten_ids_materi.issubset(selesai_konten_ids):
                selesai_materi_count += 1
        
        jumlah_lencana = len(user.badges)

        # 2. Tentukan pelajaran saat ini
        pelajaran_saat_ini = None
        progress_bar = 0
        last_progress = user.progress.order_by(ProgressSiswa.tanggal_selesai.desc()).first()

        if last_progress:
            konten_terakhir = KontenBelajar.query.get(last_progress.konten_id)
            if konten_terakhir:
                pelajaran_saat_ini = konten_terakhir.materi
        
        # Jika tidak ada progres sama sekali, coba cari materi pertama yang belum selesai
        if not pelajaran_saat_ini and all_materis:
             for materi in all_materis:
                konten_ids_materi = {k.id for k in materi.kontens}
                if not konten_ids_materi.issubset(selesai_konten_ids):
                    pelajaran_saat_ini = materi
                    break
        
        if pelajaran_saat_ini:
            # Hitung progres bar untuk materi tersebut
            total_konten_materi = len(pelajaran_saat_ini.kontens)
            konten_selesai_di_materi = 0
            if total_konten_materi > 0:
                for konten in pelajaran_saat_ini.kontens:
                    if konten.id in selesai_konten_ids:
                        konten_selesai_di_materi += 1
                progress_bar = round((konten_selesai_di_materi / total_konten_materi) * 100)

            # --- LOGIKA BARU: JIKA SUDAH 100%, CARI MATERI BERIKUTNYA ---
            if progress_bar == 100:
                found_next = False
                for materi in all_materis:
                    konten_ids_materi = {k.id for k in materi.kontens}
                    if not konten_ids_materi.issubset(selesai_konten_ids):
                        pelajaran_saat_ini = materi
                        # Hitung ulang progress bar untuk materi baru ini
                        total_konten_materi = len(pelajaran_saat_ini.kontens)
                        konten_selesai_di_materi = 0
                        if total_konten_materi > 0:
                            for konten in pelajaran_saat_ini.kontens:
                                if konten.id in selesai_konten_ids:
                                    konten_selesai_di_materi += 1
                            progress_bar = round((konten_selesai_di_materi / total_konten_materi) * 100)
                        found_next = True
                        break
                # Jika semua materi sudah selesai
                if not found_next:
                    pass # Biarkan 'pelajaran_saat_ini' tetap materi terakhir yang selesai

        return render_template('dashboard.html',
                               total_materi=len(all_materis),
                               selesai_materi=selesai_materi_count,
                               jumlah_lencana=jumlah_lencana,
                               pelajaran_saat_ini=pelajaran_saat_ini,
                               progress_bar=progress_bar)

    # Logika untuk GURU
    elif session['user_role'] == 'guru':
        return render_template('dashboard.html')

    # Logika untuk ORANG TUA
    elif session['user_role'] == 'orangtua':
        parent = User.query.get(session['user_id'])
        if parent.student_id:
            student = User.query.get(parent.student_id)
            progress_records = ProgressSiswa.query.filter_by(user_id=student.id).all()
            selesai_konten_ids = {p.konten_id for p in progress_records}
            all_materis = MateriPokok.query.join(TujuanPembelajaran).filter(TujuanPembelajaran.kelas_tujuan == student.kelas, MateriPokok.status == 'published').all()
            
            selesai_materi_count = 0
            for materi in all_materis:
                konten_ids_materi = {k.id for k in materi.kontens}
                if konten_ids_materi and konten_ids_materi.issubset(selesai_konten_ids):
                    selesai_materi_count += 1
            
            recent_progress = ProgressSiswa.query.filter_by(user_id=student.id).order_by(ProgressSiswa.tanggal_selesai.desc()).limit(5).all()
            recent_konten_ids = [p.konten_id for p in recent_progress]
            
            aktivitas_terbaru = []
            if recent_konten_ids:
                recent_konten_obj = KontenBelajar.query.filter(KontenBelajar.id.in_(recent_konten_ids)).all()
                konten_map = {konten.id: konten for konten in recent_konten_obj}
                aktivitas_terbaru = [konten_map[kid] for kid in recent_konten_ids if kid in konten_map]

            return render_template('dashboard.html', 
                                   student=student,
                                   jumlah_konten_selesai=len(selesai_konten_ids),
                                   jumlah_materi_selesai=selesai_materi_count,
                                   total_materi_tersedia=len(all_materis),
                                   aktivitas_terbaru=aktivitas_terbaru)
        else:
            flash('Anda belum terhubung dengan akun siswa. Silakan masukkan Kode Pairing.', 'info')
            return redirect(url_for('parent_access'))
    
    # Fallback jika ada peran lain atau tidak ada logika khusus
    return render_template('dashboard.html')


@app.route('/profil')
@login_required
def profil():
    user = User.query.get(session['user_id'])
    return render_template('profil.html', user=user)

@app.route('/notifikasi/baca', methods=['POST'])
@login_required
def tandai_notifikasi_dibaca():
    notifs = Notifikasi.query.filter_by(penerima_id=session['user_id'], sudah_dibaca=False).all()
    for notif in notifs:
        notif.sudah_dibaca = True
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/parent-access', methods=['GET', 'POST'])
@login_required
@role_required('orangtua')
def parent_access():
    parent = User.query.get(session['user_id'])
    if parent.student_id:
        flash('Akun Anda sudah terhubung dengan seorang siswa.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        kode = request.form.get('unique_code')
        student = User.query.filter_by(kode_pairing=kode, peran='siswa').first()
        if student:
            parent.student_id = student.id
            student.parent_id = parent.id
            student.kode_pairing = None
            db.session.commit()
            flash('Akun berhasil terhubung dengan siswa!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Kode Pairing tidak valid atau tidak ditemukan.', 'danger')
    return render_template('parent_access.html')

# --- ROUTING GURU ---
@app.route('/studio')
@login_required
@role_required('guru')
def studio():
    tps = TujuanPembelajaran.query.filter_by(user_id=session['user_id']).order_by(TujuanPembelajaran.kelas_tujuan).all()
    return render_template('studio.html', tps=tps)

@app.route('/studio/tp/baru', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def buat_tp():
    if request.method == 'POST':
        new_tp = TujuanPembelajaran(deskripsi=request.form.get('deskripsi'), kelas_tujuan=request.form.get('kelas_tujuan'), user_id=session['user_id'])
        db.session.add(new_tp)
        db.session.commit()
        flash('Tujuan Pembelajaran baru berhasil dibuat!', 'success')
        return redirect(url_for('studio'))
    return render_template('buat_tp.html')

@app.route('/studio/tp/<int:tp_id>')
@login_required
@role_required('guru')
def detail_tp(tp_id):
    tp = TujuanPembelajaran.query.get_or_404(tp_id)
    if tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))
    return render_template('detail_tp.html', tp=tp)

@app.route('/studio/tp/<int:tp_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def edit_tp(tp_id):
    tp = TujuanPembelajaran.query.get_or_404(tp_id)
    if tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))

    if request.method == 'POST':
        tp.deskripsi = request.form.get('deskripsi')
        tp.kelas_tujuan = request.form.get('kelas_tujuan')
        db.session.commit()
        flash('Tujuan Pembelajaran berhasil diperbarui!', 'success')
        return redirect(url_for('studio'))
    return render_template('edit_tp.html', tp=tp)

@app.route('/studio/tp/<int:tp_id>/hapus', methods=['POST'])
@login_required
@role_required('guru')
def hapus_tp(tp_id):
    tp = TujuanPembelajaran.query.get_or_404(tp_id)
    if tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))

    db.session.delete(tp)
    db.session.commit()
    flash('Tujuan Pembelajaran berhasil dihapus.', 'success')
    return redirect(url_for('studio'))

@app.route('/studio/tp/<int:tp_id>/materi/baru', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def buat_materi(tp_id):
    tp = TujuanPembelajaran.query.get_or_404(tp_id)
    if tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))
    if request.method == 'POST':
        new_materi = MateriPokok(judul=request.form.get('judul'), deskripsi=request.form.get('deskripsi'), tp_id=tp.id)
        db.session.add(new_materi)
        db.session.commit()

        colors = ['#FFD700', '#C0C0C0', '#B08D57', '#03A9F4', '#4CAF50', '#F44336', '#9C27B0']
        badge_color = colors[new_materi.id % len(colors)]
        badge_icon = generate_badge_icon(badge_color)
        
        new_badge = Badge(
            nama=f"Penakluk: {new_materi.judul}",
            deskripsi=f"Diberikan saat berhasil menyelesaikan materi '{new_materi.judul}'.",
            icon_url=badge_icon,
            materi_pokok_id=new_materi.id
        )
        db.session.add(new_badge)
        db.session.commit()

        flash('Materi Pokok baru berhasil ditambahkan!', 'success')
        return redirect(url_for('detail_tp', tp_id=tp.id))
    return render_template('buat_materi.html', tp=tp)

@app.route('/studio/materi/<int:materi_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def edit_materi(materi_id):
    materi = MateriPokok.query.get_or_404(materi_id)
    if materi.tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))
    
    if request.method == 'POST':
        materi.judul = request.form['judul']
        materi.deskripsi = request.form['deskripsi']
        db.session.commit()
        flash('Materi Pokok berhasil diperbarui.', 'success')
        return redirect(url_for('detail_tp', tp_id=materi.tp_id))
    
    return render_template('edit_materi.html', materi=materi)

@app.route('/studio/materi/<int:materi_id>/hapus', methods=['POST'])
@login_required
@role_required('guru')
def hapus_materi(materi_id):
    materi = MateriPokok.query.get_or_404(materi_id)
    
    # Simpan tp_id untuk redirect sebelum materi dihapus
    tp_id = materi.tp_id

    # Otorisasi: Pastikan guru yang login adalah pemilik materi
    if materi.tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))

    # Hapus materi (ini juga akan otomatis menghapus semua konten & badge terkait berkat 'cascade')
    db.session.delete(materi)
    db.session.commit()
    
    flash('Materi Pokok berhasil dihapus.', 'success')
    return redirect(url_for('detail_tp', tp_id=tp_id))

@app.route('/studio/materi/<int:materi_id>/publish', methods=['POST'])
@login_required
@role_required('guru')
def publish_materi(materi_id):
    materi = MateriPokok.query.get_or_404(materi_id)
    if materi.tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))
    
    materi.status = 'published' if materi.status == 'draft' else 'draft'
    db.session.commit()
    flash(f'Status materi "{materi.judul}" berhasil diubah.', 'success')
    return redirect(url_for('detail_tp', tp_id=materi.tp_id))

@app.route('/studio/materi/<int:materi_id>/kelola', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def kelola_konten(materi_id):
    materi = MateriPokok.query.get_or_404(materi_id)
    if materi.tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))
        
    if request.method == 'POST':
        new_konten = KontenBelajar(
            judul=request.form.get('judul'), 
            tipe=request.form.get('tipe'), 
            alur=request.form.get('alur'), 
            sumber_url=request.form.get('sumber_url'), 
            materi_id=materi.id
        )
        db.session.add(new_konten)
        db.session.commit()
        flash('Konten baru berhasil ditambahkan!', 'success')
        return redirect(url_for('kelola_konten', materi_id=materi.id))
        
    return render_template('kelola_konten.html', materi=materi, konten_to_edit=None)

@app.route('/studio/konten/<int:konten_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def edit_konten(konten_id):
    konten = KontenBelajar.query.get_or_404(konten_id)
    materi = konten.materi
    if materi.tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))

    if request.method == 'POST':
        konten.judul = request.form['judul']
        konten.alur = request.form['alur']
        konten.tipe = request.form['tipe']
        konten.sumber_url = request.form['sumber_url']
        db.session.commit()
        flash('Konten berhasil diperbarui.', 'success')
        return redirect(url_for('kelola_konten', materi_id=materi.id))
    
    return render_template('kelola_konten.html', materi=materi, konten_to_edit=konten)

@app.route('/studio/konten/<int:konten_id>/hapus', methods=['POST'])
@login_required
@role_required('guru')
def hapus_konten(konten_id):
    konten = KontenBelajar.query.get_or_404(konten_id)
    materi_id = konten.materi_id
    if konten.materi.tp.user_id != session['user_id']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('studio'))
    
    db.session.delete(konten)
    db.session.commit()
    flash('Konten berhasil dihapus.', 'success')
    return redirect(url_for('kelola_konten', materi_id=materi_id))

@app.route('/monitoring-siswa')
@login_required
@role_required('guru')
def monitoring_siswa():
    guru = User.query.get(session['user_id'])
    
    # Ambil semua siswa dari sekolah yang sama dengan guru
    daftar_siswa = User.query.filter_by(peran='siswa', nama_sekolah=guru.nama_sekolah).order_by(User.kelas, User.nama_lengkap).all()
    
    data_progres = []
    for siswa in daftar_siswa:
        # Query semua materi yang tersedia untuk kelas siswa
        all_materis = MateriPokok.query.join(TujuanPembelajaran).filter(
            TujuanPembelajaran.kelas_tujuan == siswa.kelas,
            MateriPokok.status == 'published'
        ).all()
        
        # Hitung materi yang selesai
        selesai_konten_ids = {p.konten_id for p in siswa.progress}
        selesai_materi_count = 0
        for materi in all_materis:
            konten_ids_materi = {k.id for k in materi.kontens}
            if konten_ids_materi and konten_ids_materi.issubset(selesai_konten_ids):
                selesai_materi_count += 1
        
        data_progres.append({
            'siswa': siswa,
            'selesai_materi': selesai_materi_count,
            'total_materi': len(all_materis),
            'jumlah_lencana': len(siswa.badges)
        })

    return render_template('monitoring_siswa.html', data_progres=data_progres)

@app.route('/monitoring-siswa/<int:siswa_id>', methods=['GET', 'POST']) # Tambahkan methods
@login_required
@role_required('guru')
def detail_siswa(siswa_id):
    siswa = User.query.get_or_404(siswa_id)
    guru = User.query.get(session['user_id'])
    
    # Otorisasi: Pastikan siswa dari sekolah yang sama
    guru = User.query.get(session['user_id'])
    if siswa.nama_sekolah != guru.nama_sekolah:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('monitoring_siswa'))
    
    # --- LOGIKA BARU UNTUK MENGIRIM NOTIFIKASI (POST) ---
    if request.method == 'POST':
        konten_notif = request.form.get('konten')
        if konten_notif:
            new_notif = Notifikasi(
                pengirim_id=guru.id,
                penerima_id=siswa.id,
                konten=konten_notif
            )
            db.session.add(new_notif)
            db.session.commit()
            flash('Notifikasi berhasil dikirim!', 'success')
        else:
            flash('Isi pesan tidak boleh kosong.', 'danger')
        return redirect(url_for('detail_siswa', siswa_id=siswa_id))

    # Ambil semua materi yang tersedia untuk kelas siswa
    all_materis = MateriPokok.query.join(TujuanPembelajaran).filter(
        TujuanPembelajaran.kelas_tujuan == siswa.kelas,
        MateriPokok.status == 'published'
    ).order_by(MateriPokok.id).all()
    
    # Dapatkan ID konten yang sudah selesai
    selesai_konten_ids = {p.konten_id for p in siswa.progress}
    
    # Pisahkan materi yang sudah selesai dan yang belum
    materi_selesai = []
    materi_belum_selesai = []
    for materi in all_materis:
        konten_ids_materi = {k.id for k in materi.kontens}
        if konten_ids_materi and konten_ids_materi.issubset(selesai_konten_ids):
            materi_selesai.append(materi)
        else:
            materi_belum_selesai.append(materi)
            
    return render_template('detail_siswa.html', 
                           siswa=siswa, 
                           materi_selesai=materi_selesai,
                           materi_belum_selesai=materi_belum_selesai,
                           selesai_konten_ids=selesai_konten_ids)

# --- ROUTING POJOK BACA ---
@app.route('/pojok-baca')
@login_required
def pojok_baca():
    # Ambil kata kunci pencarian dari URL, jika ada
    search_query = request.args.get('q', '')
    
    # Mulai query dasar
    query = PojokBaca.query

    # Jika ada kata kunci, filter hasilnya
    if search_query:
        query = query.filter(PojokBaca.judul.ilike(f'%{search_query}%'))
    
    # Eksekusi query akhir
    semua_bacaan = query.order_by(PojokBaca.judul).all()
    
    return render_template('pojok_baca.html', semua_bacaan=semua_bacaan, search_query=search_query)

@app.route('/studio/pojok-baca/kelola')
@login_required
@role_required('guru')
def kelola_pojok_baca():
    semua_bacaan = PojokBaca.query.order_by(PojokBaca.judul).all()
    return render_template('kelola_pojok_baca.html', semua_bacaan=semua_bacaan)

@app.route('/studio/pojok-baca/tambah', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def tambah_bacaan():
    if request.method == 'POST':
        new_bacaan = PojokBaca(
            judul=request.form['judul'],
            deskripsi=request.form['deskripsi'],
            kategori=request.form['kategori'],
            url_sampul=request.form['url_sampul'],
            url_konten=request.form['url_konten']
        )
        db.session.add(new_bacaan)
        db.session.commit()
        flash('Materi bacaan baru berhasil ditambahkan!', 'success')
        return redirect(url_for('kelola_pojok_baca'))
    return render_template('form_pojok_baca.html', action='Tambah')

@app.route('/studio/pojok-baca/<int:bacaan_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('guru')
def edit_bacaan(bacaan_id):
    bacaan = PojokBaca.query.get_or_404(bacaan_id)
    if request.method == 'POST':
        bacaan.judul = request.form['judul']
        bacaan.deskripsi = request.form['deskripsi']
        bacaan.kategori = request.form['kategori']
        bacaan.url_sampul = request.form['url_sampul']
        bacaan.url_konten = request.form['url_konten']
        db.session.commit()
        flash('Materi bacaan berhasil diperbarui!', 'success')
        return redirect(url_for('kelola_pojok_baca'))
    return render_template('form_pojok_baca.html', action='Edit', bacaan=bacaan)

@app.route('/studio/pojok-baca/<int:bacaan_id>/hapus', methods=['POST'])
@login_required
@role_required('guru')
def hapus_bacaan(bacaan_id):
    bacaan = PojokBaca.query.get_or_404(bacaan_id)
    db.session.delete(bacaan)
    db.session.commit()
    flash('Materi bacaan berhasil dihapus.', 'success')
    return redirect(url_for('kelola_pojok_baca'))

# --- ROUTING SISWA ---
@app.route('/jalur-belajar')
@login_required
@role_required('siswa')
def jalur_belajar():
    user = User.query.get(session['user_id'])
    tps_tersedia = TujuanPembelajaran.query.filter(
        TujuanPembelajaran.kelas_tujuan == user.kelas,
        TujuanPembelajaran.materis.any(MateriPokok.status == 'published')
    ).all()
    return render_template('jalur_belajar.html', tps=tps_tersedia)

@app.route('/materi/<int:materi_id>')
@login_required
@role_required('siswa')
def materi_detail(materi_id):
    materi = MateriPokok.query.get_or_404(materi_id)
    user = User.query.get(session['user_id'])
    if materi.status != 'published' or str(materi.tp.kelas_tujuan) != user.kelas:
        flash('Materi ini tidak tersedia untuk Anda.', 'danger')
        return redirect(url_for('jalur_belajar'))
    
    progress_records = ProgressSiswa.query.filter_by(user_id=user.id).all()
    selesai_konten_ids = {p.konten_id for p in progress_records}
    konten_memahami = [k for k in materi.kontens if k.alur == 'memahami']
    konten_mengaplikasi = [k for k in materi.kontens if k.alur == 'mengaplikasi']
    konten_merefleksi = [k for k in materi.kontens if k.alur == 'merefleksi']
    
    memahami_selesai = bool(konten_memahami) and all(k.id in selesai_konten_ids for k in konten_memahami)
    mengaplikasi_selesai = bool(konten_mengaplikasi) and all(k.id in selesai_konten_ids for k in konten_mengaplikasi)
    merefleksi_selesai = bool(konten_merefleksi) and all(k.id in selesai_konten_ids for k in konten_merefleksi)

    return render_template('materi_detail.html', 
                            materi=materi, 
                            konten_memahami=konten_memahami,
                            konten_mengaplikasi=konten_mengaplikasi,
                            konten_merefleksi=konten_merefleksi,
                            selesai_konten_ids=selesai_konten_ids,
                            memahami_selesai=memahami_selesai,
                            mengaplikasi_selesai=mengaplikasi_selesai,
                            merefleksi_selesai=merefleksi_selesai)

@app.route('/konten/<int:konten_id>/selesai', methods=['POST'])
@login_required
@role_required('siswa')
def tandai_selesai(konten_id):
    user_id = session['user_id']
    existing_progress = ProgressSiswa.query.filter_by(user_id=user_id, konten_id=konten_id).first()
    
    if not existing_progress:
        new_progress = ProgressSiswa(user_id=user_id, konten_id=konten_id)
        db.session.add(new_progress)
        db.session.commit()

        user = User.query.get(user_id)
        check_and_award_badges(user)
        
    return jsonify({'status': 'ok'})


# --- ROUTING ADMIN ---
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Ambil parameter dari URL untuk filter dan pencarian
    search_query = request.args.get('q', '')
    role_filter = request.args.get('peran', '')

    # Query dasar
    query = User.query

    # Terapkan filter pencarian jika ada
    if search_query:
        query = query.filter(or_(
            User.nama_lengkap.ilike(f'%{search_query}%'),
            User.username.ilike(f'%{search_query}%')
        ))

    # Terapkan filter peran jika ada
    if role_filter:
        query = query.filter_by(peran=role_filter)

    # Eksekusi query akhir, diurutkan berdasarkan ID terbaru
    all_users = query.order_by(User.id.desc()).all()

    return render_template(
        'admin_dashboard.html', 
        all_users=all_users, 
        search_query=search_query, 
        role_filter=role_filter
    )

@app.route('/admin/user/<int:user_id>/hapus', methods=['POST'])
@login_required
@admin_required
def hapus_user(user_id):
    # Temukan pengguna yang akan dihapus
    user_to_delete = User.query.get_or_404(user_id)
    
    # Keamanan: Admin tidak bisa menghapus akunnya sendiri
    if user_to_delete.id == session['user_id']:
        flash('Anda tidak dapat menghapus akun Anda sendiri.', 'danger')
        return redirect(url_for('admin_dashboard'))

    flash(f'Pengguna "{user_to_delete.nama_lengkap}" berhasil dihapus.', 'success')
    db.session.delete(user_to_delete)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Keamanan: Admin tidak bisa mengubah perannya sendiri menjadi bukan admin
        if user_to_edit.id == session['user_id'] and request.form.get('peran') != 'admin':
            flash('Anda tidak dapat mengubah peran akun Anda sendiri.', 'danger')
            return redirect(url_for('edit_user', user_id=user_id))

        # Update data pengguna
        user_to_edit.nama_lengkap = request.form.get('nama_lengkap')
        user_to_edit.username = request.form.get('username')
        user_to_edit.peran = request.form.get('peran')
        user_to_edit.kelas = request.form.get('kelas') if request.form.get('peran') == 'siswa' else None
        
        # Logika untuk reset password
        new_password = request.form.get('password')
        if new_password:
            user_to_edit.set_password(new_password)
            flash('Password pengguna berhasil direset.', 'info')

        db.session.commit()
        flash(f'Data pengguna "{user_to_edit.nama_lengkap}" berhasil diperbarui.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_user.html', user_to_edit=user_to_edit)

@app.route('/admin/user/tambah', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_user():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('tambah_user'))

        new_user = User(
            nama_lengkap=request.form.get('nama_lengkap'),
            username=username,
            peran=request.form.get('peran'),
            nama_sekolah=request.form.get('nama_sekolah'),
            kelas=request.form.get('kelas') if request.form.get('peran') == 'siswa' else None
        )
        new_user.set_password(request.form.get('password'))
        db.session.add(new_user)
        db.session.commit()
        flash(f'Pengguna baru "{new_user.nama_lengkap}" berhasil dibuat.', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('tambah_user.html')

@app.route('/admin/backup')
@login_required
@admin_required
def backup_database():
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f'rumi_backup_{timestamp}.db'
        return send_file(
            os.path.join(base_dir, 'rumi.db'),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f"Gagal membuat backup: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    # Blok ini akan membuat tabel dan badge awal setiap kali aplikasi dijalankan.
    # Berguna untuk pengembangan, bisa dihapus atau diubah untuk produksi.
    with app.app_context():
        db.create_all()
        create_default_badges()
    app.run