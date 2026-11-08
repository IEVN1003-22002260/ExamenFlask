import unicodedata
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from database import mysql

pedidos_bp = Blueprint(
    'pedidos',
    __name__,
    url_prefix='/api/pedidos'
)

# Precios (el servidor es quien manda: recalcula subtotales y total)
TAMANOS = {'Chica': 40, 'Mediana': 80, 'Grande': 120}
INGREDIENTES = {'Jamon': 10, 'Piña': 10, 'Champiñones': 10}

# DAYOFWEEK de MySQL: 1 = domingo ... 7 = sábado
DIAS = {
    'domingo': 1, 'lunes': 2, 'martes': 3, 'miercoles': 4,
    'jueves': 5, 'viernes': 6, 'sabado': 7
}
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12
}


def normalizar(texto):
    """minúsculas y sin acentos: 'Miércoles' -> 'miercoles'"""
    texto = unicodedata.normalize('NFD', str(texto).strip().lower())
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


def validar_pedido(datos):
    """Devuelve (mensaje_error, pedido_limpio)."""
    if not isinstance(datos, dict):
        return "Se requiere un objeto JSON", None

    nombre = str(datos.get('nombre', '')).strip()
    direccion = str(datos.get('direccion', '')).strip()
    telefono = str(datos.get('telefono', '')).strip()

    if not nombre or not direccion or not telefono:
        return "Nombre, dirección y teléfono son obligatorios", None

    try:
        fecha = datetime.strptime(str(datos.get('fecha', '')), '%Y-%m-%d').date()
    except ValueError:
        return "Fecha inválida", None

    pizzas = datos.get('pizzas')
    if not isinstance(pizzas, list) or len(pizzas) == 0:
        return "El pedido debe tener al menos una pizza", None

    detalle = []
    total = 0

    for p in pizzas:
        tamano = p.get('tamano')
        if tamano not in TAMANOS:
            return "Tamaño de pizza inválido", None

        ingredientes = p.get('ingredientes', [])
        if not isinstance(ingredientes, list) or any(i not in INGREDIENTES for i in ingredientes):
            return "Ingrediente inválido", None
        ingredientes = list(dict.fromkeys(ingredientes))   # sin repetidos

        try:
            num = int(p.get('numPizzas'))
        except (TypeError, ValueError):
            return "Número de pizzas inválido", None
        if num < 1:
            return "El número de pizzas debe ser al menos 1", None

        precio_unitario = TAMANOS[tamano] + sum(INGREDIENTES[i] for i in ingredientes)
        subtotal = precio_unitario * num
        total += subtotal

        detalle.append({
            'tamano': tamano,
            'ingredientes': ', '.join(ingredientes),
            'num': num,
            'subtotal': subtotal
        })

    return None, {
        'nombre': nombre, 'direccion': direccion, 'telefono': telefono,
        'fecha': fecha, 'total': total, 'detalle': detalle
    }


def listar_ventas(condicion, parametros):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(f"""
            SELECT id, nombre, direccion, telefono, fecha, total
            FROM pedidos
            WHERE {condicion}
            ORDER BY fecha, id
        """, parametros)
        filas = cursor.fetchall()
    finally:
        cursor.close()

    ventas = [{
        "id": f[0],
        "nombre": f[1],
        "direccion": f[2],
        "telefono": f[3],
        "fecha": f[4].isoformat(),
        "total": float(f[5])
    } for f in filas]

    return ventas, sum(v["total"] for v in ventas)


# ---------- Registrar pedido (Botón Terminar) ----------
@pedidos_bp.route("/", methods=["POST"])
def registrar_pedido():
    error, pedido = validar_pedido(request.get_json(silent=True))
    if error:
        return jsonify({"mensaje": error, "exito": False}), 400

    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO pedidos (nombre, direccion, telefono, fecha, total)
            VALUES (%s, %s, %s, %s, %s)
        """, (pedido['nombre'], pedido['direccion'], pedido['telefono'],
              pedido['fecha'], pedido['total']))

        pedido_id = cursor.lastrowid

        for d in pedido['detalle']:
            cursor.execute("""
                INSERT INTO pedido_detalle
                (pedido_id, tamano, ingredientes, num_pizzas, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (pedido_id, d['tamano'], d['ingredientes'], d['num'], d['subtotal']))

        mysql.connection.commit()

        # Mensaje tipo "flash": el front lo muestra como aviso
        return jsonify({
            "mensaje": f"Pedido registrado. Total a pagar: ${pedido['total']}",
            "id": pedido_id,
            "total": pedido['total'],
            "exito": True
        }), 201

    except Exception as ex:
        mysql.connection.rollback()
        current_app.logger.error("Error al registrar pedido: %s", ex)
        return jsonify({
            "mensaje": "Error al registrar el pedido",
            "exito": False
        }), 500

    finally:
        if cursor is not None:
            cursor.close()


# ---------- Ventas por día de la semana ----------
@pedidos_bp.route("/dia/<dia>", methods=["GET"])
def ventas_por_dia(dia):
    numero = DIAS.get(normalizar(dia))
    if numero is None:
        return jsonify({
            "mensaje": "Día no válido. Usa lunes, martes, miércoles, jueves, viernes, sábado o domingo.",
            "exito": False
        }), 400

    try:
        ventas, total = listar_ventas("DAYOFWEEK(fecha) = %s", (numero,))
        return jsonify({"ventas": ventas, "total": total, "exito": True}), 200
    except Exception as ex:
        current_app.logger.error("Error en ventas por día: %s", ex)
        return jsonify({"mensaje": "Error al consultar las ventas", "exito": False}), 500


# ---------- Ventas por mes ----------
@pedidos_bp.route("/mes/<mes>", methods=["GET"])
def ventas_por_mes(mes):
    numero = MESES.get(normalizar(mes))
    if numero is None:
        return jsonify({
            "mensaje": "Mes no válido. Escribe el nombre de un mes, por ejemplo: mayo.",
            "exito": False
        }), 400

    try:
        ventas, total = listar_ventas("MONTH(fecha) = %s", (numero,))
        return jsonify({"ventas": ventas, "total": total, "exito": True}), 200
    except Exception as ex:
        current_app.logger.error("Error en ventas por mes: %s", ex)
        return jsonify({"mensaje": "Error al consultar las ventas", "exito": False}), 500


# ---------- Detalle de una venta ----------
@pedidos_bp.route("/<int:id>", methods=["GET"])
def detalle_venta(id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT id, nombre, direccion, telefono, fecha, total
            FROM pedidos WHERE id = %s
        """, (id,))
        f = cursor.fetchone()

        if f is None:
            return jsonify({"mensaje": "Pedido no encontrado", "exito": False}), 404

        cursor.execute("""
            SELECT tamano, ingredientes, num_pizzas, subtotal
            FROM pedido_detalle WHERE pedido_id = %s ORDER BY id
        """, (id,))
        filas = cursor.fetchall()

        pizzas = [{
            "tamano": d[0],
            "ingredientes": d[1].split(', ') if d[1] else [],
            "numPizzas": d[2],
            "subtotal": float(d[3])
        } for d in filas]

        return jsonify({
            "pedido": {
                "id": f[0], "nombre": f[1], "direccion": f[2],
                "telefono": f[3], "fecha": f[4].isoformat(), "total": float(f[5])
            },
            "pizzas": pizzas,
            "exito": True
        }), 200

    except Exception as ex:
        current_app.logger.error("Error al consultar detalle: %s", ex)
        return jsonify({"mensaje": "Error al consultar el detalle", "exito": False}), 500

    finally:
        if cursor is not None:
            cursor.close()