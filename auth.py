# auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import Database

auth_bp = Blueprint('auth', __name__, url_prefix='/api')


@auth_bp.route('/register', methods=['POST', 'OPTIONS'])
def register():
    # Dodatkowe logowanie dla diagnostyki
    print("Otrzymano żądanie rejestracji")
    print(f"Metoda: {request.method}")
    print(f"Nagłówki: {request.headers}")

    if request.method == 'OPTIONS':
        # Obsługa preflight żądania
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type, Authorization')
        return response

    if not request.is_json:
        print("Nieprawidłowy format żądania - brak JSON")
        return jsonify({"msg": "Brak JSON w żądaniu"}), 400

    data = request.get_json()
    print(f"Dane żądania: {data}")
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"msg": "Wszystkie pola są wymagane"}), 400

    db = Database()
    if db.get_user_by_username(username) or db.get_user_by_email(email):
        return jsonify({"msg": "Użytkownik o podanym username lub email już istnieje"}), 400

    hashed = generate_password_hash(password)
    user = db.register_user(username, email, hashed)
    if user:
        return jsonify({"msg": "Rejestracja przebiegła pomyślnie"}), 201

    return jsonify({"msg": "Wystąpił błąd podczas rejestracji"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"msg": "Brak username lub hasła"}), 400
    db = Database()
    user = db.get_user_by_username(username)
    if user and check_password_hash(user['password'], password):
        print(user)
        access_token = create_access_token(identity=str(user['id']))  # 🛠️ Fix tutaj
        return jsonify(access_token=access_token), 200
    return jsonify({"msg": "Niepoprawny username lub hasło"}), 401


@auth_bp.route('/lost-password', methods=['POST'])
def lost_password():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"msg": "Email jest wymagany"}), 400
    db = Database()
    user = db.get_user_by_email(email)
    if user:
        # W realnej aplikacji wysłalibyśmy link resetujący hasło
        return jsonify({"msg": "Instrukcje resetu hasła zostały wysłane na podany email"}), 200
    return jsonify({"msg": "Nie znaleziono użytkownika o podanym emailu"}), 404


@auth_bp.route('/settings', methods=['GET', 'PUT'])
@jwt_required()
def settings():
    print("test")
    user_id = get_jwt_identity()
    print(user_id)
    db = Database()
    if request.method == "GET":
        user = db.get_user_by_id(user_id)
        if user:
            user.pop('password', None)  # nie zwracamy hasła
            return jsonify(user), 200
        return jsonify({"msg": "Nie znaleziono użytkownika"}), 404
    elif request.method == "PUT":
        data = request.get_json()
        success = db.update_user_settings(user_id, data)
        if success:
            return jsonify({"msg": "Ustawienia zaktualizowane"}), 200
        else:
            return jsonify({"msg": "Nie udało się zaktualizować ustawień"}), 500
