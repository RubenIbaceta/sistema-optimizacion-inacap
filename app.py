from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import sympy as sp

app = Flask(__name__)
# Configuración de la base de datos local SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==========================================
# MODELOS DE LA BASE DE DATOS (TABLAS)
# ==========================================

class Ingrediente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio_costo = db.Column(db.Float, nullable=False)

class Plato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    costo_base = db.Column(db.Float, default=0.0)
    precio_actual = db.Column(db.Float, default=0.0)

class Competencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plato_id = db.Column(db.Integer, db.ForeignKey('plato.id'), nullable=False)
    local_nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)

# Relación para facilitar las consultas entre tablas
Plato.competidores = db.relationship('Competencia', backref='plato', lazy=True)


# ==========================================
# RUTAS DE LA APLICACIÓN
# ==========================================

@app.route('/')
def inicio():
    # Página de bienvenida y explicación metodológica
    return render_template('inicio.html')

@app.route('/gestion', strict_slashes=False)
def index():
    # Módulo CRUD de Ingredientes y Platos
    ingredientes = Ingrediente.query.all()
    platos = Plato.query.all()
    return render_template('index.html', ingredientes=ingredientes, platos=platos)

@app.route('/ingrediente/nuevo', methods=['POST'])
def nuevo_ingrediente():
    nombre = request.form.get('nombre')
    precio = float(request.form.get('precio_costo'))
    
    nuevo_insumo = Ingrediente(nombre=nombre, precio_costo=precio)
    db.session.add(nuevo_insumo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/plato/nuevo', methods=['POST'])
def nuevo_plato():
    nombre = request.form.get('nombre')
    precio_inicial = float(request.form.get('precio_actual'))
    ingredientes_seleccionados = request.form.getlist('ingredientes')
    
    # Calcular automáticamente el costo base sumando los ingredientes elegidos
    costo_total = 0.0
    for ing_id in ingredientes_seleccionados:
        ing = Ingrediente.query.get(ing_id)
        if ing:
            costo_total += ing.precio_costo
            
    nuevo_p = Plato(nombre=nombre, costo_base=costo_total, precio_actual=precio_inicial)
    db.session.add(nuevo_p)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/competencia', methods=['GET', 'POST'], strict_slashes=False)
def gestion_competencia():
    if request.method == 'POST':
        plato_id = int(request.form.get('plato_id'))
        local = request.form.get('local_nombre')
        precio_comp = float(request.form.get('precio'))
        
        nueva_comp = Competencia(plato_id=plato_id, local_nombre=local, precio=precio_comp)
        db.session.add(nueva_comp)
        db.session.commit()
        return redirect(url_for('gestion_competencia'))
        
    platos = Plato.query.all()
    competencias = Competencia.query.all()
    return render_template('competencia.html', platos=platos, competencias=competencias)

@app.route('/comparativa', strict_slashes=False)
def comparativa():
    # Despliega la pantalla del gráfico de barras de Chart.js
    platos = Plato.query.all()
    return render_template('comparativa.html', platos=platos)

@app.route('/api/datos_comparativa/<int:plato_id>')
def datos_comparativa(plato_id):
    # API interna para alimentar el gráfico de barras
    plato = Plato.query.get_or_404(plato_id)
    competidores = Competencia.query.filter_by(plato_id=plato_id).all()
    
    locales = ['Nuestro Local']
    precios = [plato.precio_actual]
    
    for c in competidores:
        locales.append(c.local_nombre)
        precios.append(c.precio)
        
    return jsonify({'locales': locales, 'precios': precios})


# ==========================================
# RUTAS DE ELIMINACIÓN Y ACTUALIZACIÓN
# ==========================================

@app.route('/plato/eliminar/<int:plato_id>', methods=['POST'])
def eliminar_plato(plato_id):
    plato = Plato.query.get_or_404(plato_id)
    # Primero eliminamos sus competidores asociados para evitar errores de llave foránea
    Competencia.query.filter_by(plato_id=plato_id).delete()
    db.session.delete(plato)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/plato/actualizar/<int:plato_id>', methods=['POST'])
def actualizar_plato(plato_id):
    plato = Plato.query.get_or_404(plato_id)
    plato.nombre = request.form.get('nombre')
    plato.precio_actual = float(request.form.get('precio_actual'))
    
    # Recalcular costo base si se modificaron ingredientes
    ingredientes_seleccionados = request.form.getlist('ingredientes')
    if ingredientes_seleccionados:
        costo_total = 0.0
        for ing_id in ingredientes_seleccionados:
            ing = Ingrediente.query.get(ing_id)
            if ing:
                costo_total += ing.precio_costo
        plato.costo_base = costo_total

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/competencia/eliminar/<int:comp_id>', methods=['POST'])
def eliminar_competencia(comp_id):
    comp = Competencia.query.get_or_404(comp_id)
    db.session.delete(comp)
    db.session.commit()
    return redirect(url_for('gestion_competencia'))

@app.route('/competencia/actualizar/<int:comp_id>', methods=['POST'])
def actualizar_competencia(comp_id):
    comp = Competencia.query.get_or_404(comp_id)
    comp.local_nombre = request.form.get('local_nombre')
    comp.precio = float(request.form.get('precio'))
    db.session.commit()
    return redirect(url_for('gestion_competencia'))


# ==========================================
# MOTOR MATEMÁTICO: DERIVADAS Y OPTIMIZACIÓN
# ==========================================

@app.route('/optimizacion/<int:plato_id>')
def optimizar(plato_id):
    plato = Plato.query.get_or_404(plato_id)
    competidores = Competencia.query.filter_by(plato_id=plato_id).all()
    
    if len(competidores) < 1:
        return "<h3>Error: Para optimizar, necesitas registrar al menos el precio de 1 competidor en la pestaña 'Precios Competencia'.</h3>"
        
    precios_comp = [c.precio for c in competidores]
    precio_promedio_competencia = sum(precios_comp) / len(precios_comp)
    
    # --- MODELAMIENTO MATEMÁTICO CON SYMPY ---
    p = sp.Symbol('p')    # Variable de decisión: Precio de venta
    C = float(plato.costo_base)  # Costo base de fabricación del plato
    
    # Estimación de la Demanda lineal decreciente: Q(p) = a - b*p
    max_demanda = 200  
    b_sensibilidad = max_demanda / (precio_promedio_competencia * 1.5)
    q = max_demanda - b_sensibilidad * p
    
    # Función de Ganancia Cuadrática: G(p) = (p - C) * Q(p)
    ganancia = (p - C) * q
    
    # Aplicación de la Primera Derivada respecto al precio 'p'
    derivada_ganancia = sp.diff(ganancia, p)
    
    # Encontrar punto crítico de la cima igualando la derivada a cero: G'(p) = 0
    soluciones = sp.solve(derivada_ganancia, p)
    precio_optimo_exacto = float(soluciones[0])
    
    # --- AJUSTE DE SEGURIDAD OPERACIONAL ---
    # Si por distorsión de precios de competencia el óptimo matemático cae bajo el costo base
    if precio_optimo_exacto <= C:
        precio_optimo_exacto = C * 1.20
    
    # Calcular unidades (demanda) exactas asociadas a ese precio óptimo continuo
    unidades_optimas_exactas = float(q.subs(p, precio_optimo_exacto))
    if unidades_optimas_exactas < 0:
        unidades_optimas_exactas = 0.0
        
    # --- CÁLCULOS CONTINUOS EXACTOS (Alineado con GeoGebra) ---
    # Evaluamos las funciones originales directamente con el float exacto matemático antes de redondear
    ganancia_maxima_exacta = float(ganancia.subs(p, precio_optimo_exacto))
    ingreso_total_exacto = precio_optimo_exacto * unidades_optimas_exactas
    
    # --- REDONDEO FINAL EXCLUSIVO PARA DESPLIEGUE (Formato CLP entero) ---
    precio_optimo_redondeado = round(precio_optimo_exacto)
    unidades_optimas_redondeado = round(unidades_optimas_exactas)
    costo_base_redondeado = round(C)
    ganancia_maxima_redondeada = round(ganancia_maxima_exacta)
    ingreso_total_redondeado = round(ingreso_total_exacto)
    
    # --- CÁLCULO DE RAÍCES: Encontrar el precio límite superior ---
    raices = sp.solve(ganancia, p)
    precio_limite_perdida_exacto = float(max(raices)) if raices else precio_promedio_competencia * 2
    precio_limite_perdida = round(precio_limite_perdida_exacto)
    
    # Construcción de puntos de la parábola para graficar en la interfaz
    puntos_precio = []
    puntos_ganancia = []
    puntos_unidades = []
    
    rango_min = int(C)
    rango_max = int(precio_promedio_competencia * 2)
    paso = int((rango_max - rango_min) / 15) if (rango_max - rango_min) > 15 else 1
    
    ganancia_func = sp.lambdify(p, ganancia, 'math')
    demanda_func = sp.lambdify(p, q, 'math')
    
    for pr in range(rango_min, rango_max + paso, paso):
        puntos_precio.append(pr)
        puntos_ganancia.append(float(ganancia_func(pr)))
        puntos_unidades.append(float(demanda_func(pr)))

    return render_template('optimizacion.html', 
                           plato=plato,
                           costo_base_display=costo_base_redondeado,
                           precio_optimo=precio_optimo_redondeado, 
                           ganancia_maxima=ganancia_maxima_redondeada,
                           unidades_optimas=unidades_optimas_redondeado,
                           ingreso_total=ingreso_total_redondeado,
                           precio_limite_perdida=precio_limite_perdida,
                           puntos_precio=puntos_precio,
                           puntos_ganancia=puntos_ganancia,
                           puntos_unidades=puntos_unidades)

# ==========================================
# PRECARGA AUTOMÁTICA DE DATOS INICIALES
# ==========================================

def precargar_datos_ejemplo():
    if Ingrediente.query.first() is None:
        # A. REGISTRO DE 15 INGREDIENTES BASE
        ing = {
            'pan_copihue': Ingrediente(nombre='Pan Copihue (Unidad)', precio_costo=150),
            'pan_frika': Ingrediente(nombre='Pan Frika Grande (Unidad)', precio_costo=220),
            'vienesa': Ingrediente(nombre='Vienesa Tradicional', precio_costo=250),
            'palta': Ingrediente(nombre='Palta Molida (Porción)', precio_costo=400),
            'tomate': Ingrediente(nombre='Tomate en Cubos (Porción)', precio_costo=150),
            'salsas': Ingrediente(nombre='Salsas y Mayo', precio_costo=80),
            'churrasco': Ingrediente(nombre='Lomito/Churrasco Cerdo (150g)', precio_costo=1200),
            'queso': Ingrediente(nombre='Queso Chanco Laminado (Porción)', precio_costo=350),
            'papas': Ingrediente(nombre='Papas Fritas Congeladas (Porción)', precio_costo=500),
            'aceite': Ingrediente(nombre='Aceite para freír (Porción)', precio_costo=100),
            'carne_burguer': Ingrediente(nombre='Hamburguesa Casera (125g)', precio_costo=950),
            'huevo': Ingrediente(nombre='Huevo Grado A (Unidad)', precio_costo=130),
            'cebolla': Ingrediente(nombre='Cebolla Caramelizada (Porción)', precio_costo=120),
            'pan_molde': Ingrediente(nombre='Pan de Molde Blanco (2 rebanadas)', precio_costo=140),
            'ave': Ingrediente(nombre='Pechuga de Pollo Desmenuzada (120g)', precio_costo=850),
        }
        db.session.add_all(ing.values())
        db.session.commit()

        # B. REGISTRO DE 10 PLATOS TÍPICOS
        platos_data = [
            {'nombre': 'Completo Italiano', 'precio': 2490, 'insumos': ['pan_copihue', 'vienesa', 'palta', 'tomate', 'salsas']},
            {'nombre': 'Churrasco Italiano', 'precio': 4990, 'insumos': ['pan_frika', 'churrasco', 'palta', 'tomate', 'salsas']},
            {'nombre': 'Barros Luco', 'precio': 4500, 'insumos': ['pan_frika', 'churrasco', 'queso']},
            {'nombre': 'Hamburguesa Completa', 'precio': 3990, 'insumos': ['pan_frika', 'carne_burguer', 'tomate', 'palta', 'salsas']},
            {'nombre': 'Hamburguesa Cheddar', 'precio': 4290, 'insumos': ['pan_frika', 'carne_burguer', 'queso', 'salsas']},
            {'nombre': 'As Italiano', 'precio': 2990, 'insumos': ['pan_copihue', 'churrasco', 'palta', 'tomate', 'salsas']},
            {'nombre': 'Chorrillana Individual', 'precio': 5990, 'insumos': ['papas', 'aceite', 'churrasco', 'cebolla', 'huevo']},
            {'nombre': 'Papas Fritas Medianas', 'precio': 1990, 'insumos': ['papas', 'aceite', 'salsas']},
            {'nombre': 'Ave Mayo Especial', 'precio': 3490, 'insumos': ['pan_frika', 'ave', 'salsas']},
            {'nombre': 'Sandwich Aliado Calentito', 'precio': 2490, 'insumos': ['pan_molde', 'queso', 'salsas']}
        ]

        platos_creados = {}
        for p_info in platos_data:
            costo_acumulado = sum(ing[i_name].precio_costo for i_name in p_info['insumos'])
            nuevo_plato = Plato(nombre=p_info['nombre'], costo_base=costo_acumulado, precio_actual=p_info['precio'])
            db.session.add(nuevo_plato)
            db.session.commit()
            platos_creados[p_info['nombre']] = nuevo_plato

        # C. REGISTRO DE 9 LOCALES COMPETIDORES
        competidores = [
            'Carrito Avenida Brasil', 'Delivery App Express', 'Bajón Bellavista',
            'Picada Universitaria', 'Casino INACAP Alt', 'FoodTruck Pedro Montt',
            'Local Puerto Comida', 'Sándwich Viña Centro', 'El Rey del Completo'
        ]
        desv = [1.10, 1.25, 0.90, 0.85, 1.05, 1.15, 1.20, 1.30, 1.00]

        for i, local in enumerate(competidores):
            factor = desv[i]
            for p_name, plato_obj in platos_creados.items():
                precio_crudo = plato_obj.precio_actual * factor
                base_cien = round(precio_crudo / 100) * 100
                
                if base_cien % 1000 == 0 or base_cien % 500 == 0:
                    precio_competencia = base_cien - 10
                else:
                    precio_competencia = round(base_cien / 50) * 50
                
                nueva_comp = Competencia(plato_id=plato_obj.id, local_nombre=local, precio=float(precio_competencia))
                db.session.add(nueva_comp)
        
        db.session.commit()

# ==========================================
# INICIALIZACIÓN DE LA APLICACIÓN
# ==========================================
import os

# Ejecutar la creación de tablas e inyección de datos controlando el reloader de Flask
with app.app_context():
    db.create_all()
    # Evita que el doble parpadeo de debug=True intente escribir sobre la base duplicando registros
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        precargar_datos_ejemplo()

if __name__ == '__main__':
    app.run(debug=True)
