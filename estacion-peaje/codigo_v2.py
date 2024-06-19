# ### Técnica de Monte Carlo
# En el programa proporcionado, la técnica de Monte Carlo se aplica de las siguientes maneras:

# 1. **Generación de llegadas de vehículos**: Utilizamos distribuciones exponenciales para modelar los tiempos entre llegadas de vehículos, lo cual refleja la naturaleza aleatoria de las llegadas.

# 2. **Tiempos de servicio**: Utilizamos diferentes distribuciones (uniforme, exponencial, triangular) para modelar el tiempo de servicio de diferentes tipos de vehículos.

# 3. **Variabilidad en horas pico y no pico**: La simulación ajusta las tasas de llegada según si la hora actual está en un periodo de alta demanda o no, añadiendo otra capa de variabilidad al modelo.

# ### Evaluación y Datos Adicionales

# Para evaluar si existen esperas medias que superen los tres minutos y determinar cuánto cobrar la multa, podemos extender el programa para calcular estos valores y realizar un análisis de sensibilidad.

# A continuación, se añade código que:
# 1. Evalúa si las esperas medias superan los tres minutos.
# 2. Calcula el costo de habilitar una cabina extra.
# 3. Determina la multa necesaria para que sea más rentable habilitar una cabina extra.

# Aquí está el código extendido:

import simpy
import random
import matplotlib.pyplot as plt
import statistics

# Parámetros de la simulación
# Tiempos entre llegadas = promedios con distribución exponencial  =>  1/λ = 1/30 segundos
TIEMPOS_ENTRE_LLEGADAS_PICO = {'grande': 30, 'mediano': 40, 'pequeño': 25, 'motocicleta': 380}  # Tiempo entre llegadas durante horas pico (en segundos)
TIEMPOS_ENTRE_LLEGADAS_NO_PICO = {'grande': 60, 'mediano': 70, 'pequeño': 40, 'motocicleta': 380}  # Tiempo entre llegadas fuera de horas pico
TIEMPOS_SERVICIO = {
    # Se usan funciones lambda, que al ser usadas, devuelven un valor aleatorio de acuerdo a la distribución de probabilidad
    'grande': lambda: random.uniform(45, 55),  # Tiempo de servicio para vehículos grandes (uniforme entre 45 y 55 segundos)
    'mediano': lambda: random.expovariate(1 / 30),  # Tiempo de servicio para vehículos medianos (exponencial con media de 30 segundos)
    'pequeño': lambda: random.triangular(15, 20, 35),  # Tiempo de servicio para vehículos pequeños (triangular entre 15, 20 (habitual) y 35 segundos)
    'motocicleta': lambda: random.expovariate(1 / 30),  # Tiempo de servicio para motocicletas (exponencial con media de 30 segundos)
    # 'especial': lambda: random.uniform(30, 40)  # Tiempo de servicio para vehículos especiales (uniforme entre 30 y 40 segundos)
}
HORAS_PICO = [(7, 9), (19, 20)]  # Intervalos de horas pico (de 7 a 9 y de 19 a 20)
TIEMPO_SIMULACION = 60 * 24 * 7  # Tiempo total de simulación en minutos (7 días en minutos)
COSTO_CABINA_EXTRA = 100  # Costo de habilitar una cabina extra por cada 10 minutos
LIMITE_ESPERA = 180  # Tiempo de espera límite (3 minutos) en segundos

# Variables de estado
tiempo_total_espera = 0  # Tiempo total de espera acumulado
total_vehiculos = 0  # Contador total de vehículos atendidos
tiempos_espera = []  # Lista para almacenar los tiempos de espera individuales de cada vehículo
eventos = []  # Lista para almacenar los eventos (llegadas y salidas de vehículos)

# Función para verificar si es hora pico
def es_hora_pico(hora):
    for inicio, fin in HORAS_PICO:
        if inicio <= hora < fin:
            return True
    return False

# Función para generar llegadas de vehículos
def llegada_vehiculos(entorno, cabinas):
    global total_vehiculos
    while True:
        hora_actual = int(entorno.now / 60) % 24  # Hora actual de la simulación (convertida de minutos a horas)
        if es_hora_pico(hora_actual):
            tiempos_entre_llegadas = TIEMPOS_ENTRE_LLEGADAS_PICO  # Usar tiempos entre llegadas para horas pico
        else:
            tiempos_entre_llegadas = TIEMPOS_ENTRE_LLEGADAS_NO_PICO  # Usar tiempos entre llegadas para fuera de horas pico

        for tipo_vehiculo in tiempos_entre_llegadas.keys():
            if tipo_vehiculo == 'motocicleta' or tipo_vehiculo in TIEMPOS_ENTRE_LLEGADAS_NO_PICO:
                tiempo_entre_llegadas = tiempos_entre_llegadas[tipo_vehiculo]  # Tiempo entre llegadas (en segundos)
                yield entorno.timeout(tiempo_entre_llegadas / 10)  # Reducir el tiempo entre llegadas para aumentar la cantidad de vehículos
                total_vehiculos += 1  # Incrementar el contador total de vehículos
                eventos.append((entorno.now, 'llegada', tipo_vehiculo))  # Registrar el evento de llegada
                entorno.process(vehiculo(entorno, cabinas, tipo_vehiculo))  # Iniciar el proceso de atención del vehículo

# Función para modelar el comportamiento de los vehículos
def vehiculo(entorno, cabinas, tipo_vehiculo):
    global tiempo_total_espera, tiempos_espera
    tiempo_llegada = entorno.now  # Tiempo de llegada del vehículo
    with cabinas.request() as req:  # Solicitar una cabina de peaje
        yield req  # Esperar hasta que una cabina esté disponible
        tiempo_servicio = TIEMPOS_SERVICIO[tipo_vehiculo]()  # Obtener el tiempo de servicio del vehículo
        yield entorno.timeout(tiempo_servicio)  # Simular el tiempo de servicio
    tiempo_espera = entorno.now - tiempo_llegada  # Calcular el tiempo de espera
    tiempo_total_espera += tiempo_espera  # Sumar el tiempo de espera total
    tiempos_espera.append(tiempo_espera)  # Agregar el tiempo de espera a la lista
    eventos.append((entorno.now, 'salida', tipo_vehiculo))  # Registrar el evento de salida

# Función para manejar las cabinas
def control_cabinas(entorno, cabinas):
    while True:
        hora_actual = int(entorno.now / 60) % 24  # Hora actual de la simulación
        if es_hora_pico(hora_actual):
            nueva_capacidad = 3  # Durante horas pico, la capacidad es 3
        else:
            nueva_capacidad = 2  # Fuera de horas pico, la capacidad es 2

        if cabinas.capacity != nueva_capacidad:
            # Cambiar la capacidad de las cabinas
            cabinas = simpy.Resource(entorno, capacity=nueva_capacidad)
        
        yield entorno.timeout(60)  # Revisar cada hora

# Configuración de la simulación
entorno = simpy.Environment()  # Crear el entorno de simulación
cabinas = simpy.Resource(entorno, capacity=2)  # Crear el recurso de cabinas con capacidad inicial de 2
entorno.process(control_cabinas(entorno, cabinas))  # Iniciar el proceso de control de cabinas
entorno.process(llegada_vehiculos(entorno, cabinas))  # Iniciar el proceso de llegadas de vehículos

# Ejecutar la simulación
entorno.run(until=TIEMPO_SIMULACION)  # Ejecutar la simulación por el tiempo indicado en el parámetro TIEMPO_SIMULACION

# Resultados de la simulación
print(f"Total de vehículos: {total_vehiculos}")  # Imprimir el total de vehículos atendidos
print(f"Tiempo promedio de espera: {statistics.mean(tiempos_espera):.2f} segundos")  # Imprimir el tiempo de espera promedio
print(f"Tiempo máximo de espera: {max(tiempos_espera):.2f} segundos")  # Imprimir el tiempo de espera máximo
print(f"Tiempo mínimo de espera: {min(tiempos_espera):.2f} segundos")  # Imprimir el tiempo de espera mínimo

# Medidas de rendimiento adicionales
superan_3_min = sum(1 for t in tiempos_espera if t > LIMITE_ESPERA)  # Contar vehículos con tiempos de espera mayores a 3 minutos
porcentaje_superan_3_min = (superan_3_min / total_vehiculos) * 100  # Calcular el porcentaje de esos vehículos
total_costo_cabina_extra = (TIEMPO_SIMULACION / 10) * COSTO_CABINA_EXTRA  # Calcular el costo total de habilitar una cabina extra durante toda la simulación

print(f"Vehículos que superan 3 minutos de espera: {superan_3_min} ({porcentaje_superan_3_min:.2f}%)")  # Imprimir la cantidad y porcentaje de vehículos que esperan más de 3 minutos
print(f"Costo total de habilitar una cabina extra: ${total_costo_cabina_extra:.2f}")  # Imprimir el costo total de habilitar una cabina extra

# Calcular la multa necesaria para que sea rentable habilitar una cabina extra
if superan_3_min > 0:
    costo_multa = total_costo_cabina_extra / superan_3_min  # Calcular la multa por vehículo
else:
    costo_multa = 0  # Si no hay vehículos que superen 3 minutos de espera, la multa es 0

print(f"Multa necesaria por vehículo que supera 3 minutos de espera: ${costo_multa:.2f}")  # Imprimir la multa necesaria

# Mostrar el histograma de tiempos de espera
plt.hist(tiempos_espera, bins=50, edgecolor='black')
plt.title("Distribución de Tiempos de Espera")
plt.xlabel("Tiempo de Espera (segundos)")
plt.ylabel("Frecuencia")
plt.axvline(LIMITE_ESPERA, color='red', linestyle='dashed', linewidth=1, label='Límite de 3 minutos')
plt.legend()
plt.show()


# ### Explicación de la Evaluación

# **1. Determinar si existen esperas medias que superen los tres minutos:**
#    - La simulación calcula los tiempos de espera de cada vehículo y almacena estos tiempos en la lista `tiempos_espera`.
#    - Luego, se verifica cuántos de estos tiempos de espera superan los 180 segundos (3 minutos) y se calcula el porcentaje de estos casos.

# **2. Costo de habilitar una cabina extra:**
#    - Se define un costo fijo de 100 $ por cada 10 minutos de habilitación de una cabina extra.
#    - El costo total de habilitar una cabina extra durante toda la simulación se calcula dividiendo el tiempo total de simulación entre 10 minutos y multiplicando por el costo por cada 10 minutos.

# **3. Determinar la multa necesaria:**
#    - Se calcula la multa por cada vehículo que exceda los tres minutos de espera dividiendo el costo total de habilitar una cabina extra entre la cantidad de vehículos que tuvieron que esperar más de tres minutos.

# Este análisis y cálculo se realizan para demostrar que habilitar una cabina extra puede ser más rentable si la multa por exceder los tres minutos de espera es suficientemente alta para cubrir los costos adicionales.