from flask import Flask, render_template, request, jsonify, Response
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from functools import wraps
from datetime import datetime

# --- Создание Flask-приложения ---
app = Flask(__name__)

# --- Настройка базы данных (SQLite + SQLAlchemy) ---
Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    service = Column(String(50), nullable=False)
    address = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    date = Column(DateTime, nullable=False)
    rooms = Column(Integer, nullable=False)
    area = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///orders.db')
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# --- Базовая авторизация для /admin ---
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '1234'

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
        'Требуется авторизация', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- Маршруты ---

@app.route('/')
def home():
    lang = request.args.get('lang', 'ru')
    return render_template('index.html', lang=lang)

@app.route('/form')
def form():
    lang = request.args.get('lang', 'ru')
    return render_template('form.html', lang=lang)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json

    required_fields = ['service', 'date', 'time', 'rooms', 'area']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'status': 'error', 'message': f'Поле {field} обязательно'}), 400

    if not data.get('address') and not data.get('location'):
        return jsonify({'status': 'error', 'message': 'Требуется адрес или геопозиция'}), 400

    location = data.get('location')
    if location:
        lat = location.get('latitude')
        lon = location.get('longitude')
        if lat is None or lon is None:
            return jsonify({'status': 'error', 'message': 'Некорректные координаты'}), 400

    try:
        dt = datetime.strptime(f"{data['date']} {data['time']}", '%Y-%m-%d %H:%M')
        if dt < datetime.now():
            return jsonify({'status': 'error', 'message': 'Дата и время должны быть в будущем'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Неверный формат даты или времени'}), 400

    try:
        area = float(data['area'])
        if area <= 0:
            raise ValueError
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Площадь должна быть положительным числом'}), 400

    notes = data.get('notes', '').strip()

    session = SessionLocal()

    order = Order(
        user_id=data.get('user_id'),
        service=data['service'],
        address=data.get('address'),
        latitude=location.get('latitude') if location else None,
        longitude=location.get('longitude') if location else None,
        date=dt,
        rooms=int(data['rooms']),
        area=area,
        notes=notes
    )

    session.add(order)
    session.commit()
    session.close()

    return jsonify({'status': 'success', 'message': 'Заказ подтверждён'})

@app.route('/timer')
def timer():
    lang = request.args.get('lang', 'ru')
    date = request.args.get('date')
    time = request.args.get('time')
    datetime_iso = f"{date}T{time}:00"
    return render_template('timer.html', lang=lang, datetime_iso=datetime_iso)

@app.route('/admin')
@requires_auth
def admin_panel():
    session = SessionLocal()
    orders = session.query(Order).order_by(Order.created_at.desc()).all()
    session.close()
    return render_template('admin.html', orders=orders)

# --- Запуск ---
if __name__ == '__main__':
    app.run(debug=True)
