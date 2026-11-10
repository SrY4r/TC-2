import sys
import os

import re

from flask import Flask, render_template, request

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ✅ Inicialización simple. Flask buscará 'templates' en la raíz.
app = Flask(__name__)

# --- Lógica del Analizador Léxico (AFD) ---
class AnalizadorLexico:
    def __init__(self):
        self.patrones = [
            ('TK_HEADER', r'^HDR', 'HDR'),
            ('TK_DELIM', r'^#', '#'),
            ('TK_ESTACION', r'^ST[0-9]{2}', 'ST[0-9]{2}'),
            ('TK_VAR_TEMP', r'^TMP', 'TMP'),
            ('TK_NUM_REAL', r'^-?[0-9]+\.[0-9]', '-?[0-9]+\.[0-9]'),
            ('TK_BATERIA', r'^BAT[0-9]{2,3}', 'BAT[0-9]{2,3}')
        ]

    def tokenizar(self, trama):
        trama_limpia = trama.replace(" ", "").replace("\n", "").replace("\r", "")
        tokens_detectados, posicion = [], 0
        if not trama_limpia: 
            return None, "La trama está vacía."
        while posicion < len(trama_limpia):
            match_encontrado = False
            for tipo, patron, regex_str in self.patrones:
                match = re.match(patron, trama_limpia[posicion:])
                if match:
                    lexema = match.group(0)
                    tokens_detectados.append({'lexema': lexema, 'token': tipo, 'regex': regex_str})
                    posicion += len(lexema)
                    match_encontrado = True
                    break
            if not match_encontrado: 
                return None, f"Carácter no reconocido en: '{trama_limpia[posicion:]}'"
        return tokens_detectados, "Éxito"

# --- Lógica del Analizador Sintáctico (LR) ---
class AnalizadorSintactico:
    def parsear(self, tokens):
        gramatica = ['TK_HEADER', 'TK_DELIM', 'TK_ESTACION', 'TK_DELIM', 'TK_VAR_TEMP', 'TK_NUM_REAL', 'TK_DELIM', 'TK_BATERIA']
        if len(tokens) != len(gramatica): 
            return False, "Estructura incompleta."
        for i, token in enumerate(tokens):
            if token['token'] != gramatica[i]: 
                return False, f"Error en pos {i+1}. Se esperaba '{gramatica[i]}'."
        return True, "Sintaxis válida."

# --- Ruta Principal (en la raíz) ---
@app.route('/', methods=['GET', 'POST'])
def index():
    contexto = {
        'trama_ingresada': '', 'tokens': None, 'error_lexico': None,
        'error_sintactico': None, 'mensaje_operario': None, 'tipo_alerta': None
    }
    
    if request.method == 'POST':
        try:
            trama = ""
            if 'archivo_txt' in request.files and request.files['archivo_txt'].filename != '':
                archivo = request.files['archivo_txt']
                if archivo.filename.endswith('.txt'): 
                    trama = archivo.read().decode('utf-8')
                else: 
                    contexto['error_lexico'] = "Suba un archivo .txt"
            elif 'trama_manual' in request.form: 
                trama = request.form['trama_manual']

            contexto['trama_ingresada'] = trama.strip()
            if trama.strip():
                lexer, parser = AnalizadorLexico(), AnalizadorSintactico()
                tokens, msj_lex = lexer.tokenizar(trama)
                if not tokens:
                    contexto.update(error_lexico=msj_lex, tipo_alerta='advertencia', mensaje_operario="❌ TRAMA CORRUPTA.")
                else:
                    contexto['tokens'] = tokens
                    es_valido, msj_sin = parser.parsear(tokens)
                    if not es_valido:
                        contexto.update(error_sintactico=msj_sin, tipo_alerta='advertencia', mensaje_operario="❌ ESTRUCTURA INVÁLIDA.")
                    else:
                        estacion = next(t['lexema'] for t in tokens if t['token'] == 'TK_ESTACION')
                        temp = float(next(t['lexema'] for t in tokens if t['token'] == 'TK_NUM_REAL'))
                        if temp < 0.0:
                            contexto.update(tipo_alerta='peligro', mensaje_operario=f"🚨 ¡ALERTA DE HELADA! {temp}°C en {estacion}.")
                        else:
                            contexto.update(tipo_alerta='exito', mensaje_operario=f"✅ Mensaje correcto. {temp}°C en {estacion}.")
        except Exception as e:
            contexto.update(error_lexico=f"Error interno: {str(e)}", tipo_alerta='advertencia', mensaje_operario="❌ Error de procesamiento.")
    
    return render_template('index.html', **contexto)

# Vercel necesita la variable 'app'
if __name__ == '__main__':
    app.run(debug=True)