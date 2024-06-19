import simpy  # Importamos la biblioteca simpy para la simulación de eventos discretos
import random  # Importamos la biblioteca random para generar números aleatorios
import statistics  # Importamos la biblioteca statistics para cálculos estadísticos

# Parámetros de la simulación
LAMBDA_PICO = {'grande': 30, 'mediano': 40, 'pequeño': 25, 'motocicleta': 380}  # Tasas de llegada durante horas pico (en vehículos por minuto)
LAMBDA_NO_PICO = {'grande': 60, 'mediano': 70, 'pequeño': 40}  # Tasas de llegada fuera de horas pico
TIEMPOS_SERVICIO = {
    'grande': lambda: random.uniform(45, 55),  # Tiempo de servicio para vehículos grandes (uniforme entre 45 y 55 segundos)
    'mediano': lambda: random.expovariate(1 / 30),  # Tiempo de servicio para vehículos medianos (exponencial con media de 30 segundos)
    'pequeño': lambda: random.triangular(15, 20, 35),  # Tiempo de servicio para vehículos pequeños (triangular entre 15, 20 y 35 segundos)
    'motocicleta': lambda: random.expovariate(1 / 30)  # Tiempo de servicio para motocicletas (exponencial con media de 30 segundos)
}
HORAS_PICO = [(7, 9), (19, 20)]  # Intervalos de horas pico (de 7 a 9 y de 19 a 20)
TIEMPO_SIMULACION = 1440  # Tiempo total de simulación en minutos (24 horas)

# Variables de estado
tiempo_total_espera = 0  # Tiempo total de espera acumulado
total_vehiculos = 0  # Contador total de vehículos atendidos
tiempos_espera = []  # Lista para almacenar los tiempos de espera individuales

# Función para verificar si es hora pico
def es_hora_pico(hora):
    for inicio, fin in HORAS_PICO:
        if inicio <= hora < fin:
            return True
    return False

# Función para generar llegadas de vehículos
def llegada_vehiculos(entorno, cabina):
    global total_vehiculos
    while True:
        hora_actual = int(entorno.now / 60)  # Hora actual de la simulación (convertida de minutos a horas)
        if es_hora_pico(hora_actual):
            lambda_llegada = LAMBDA_PICO  # Usar tasas de llegada para horas pico
        else:
            lambda_llegada = LAMBDA_NO_PICO  # Usar tasas de llegada para fuera de horas pico

        for tipo_vehiculo in lambda_llegada.keys():
            if tipo_vehiculo == 'motocicleta' or tipo_vehiculo in LAMBDA_NO_PICO:
                tiempo_entre_llegadas = random.expovariate(1 / lambda_llegada[tipo_vehiculo])  # Tiempo entre llegadas (distribución exponencial)
                yield entorno.timeout(tiempo_entre_llegadas)  # Esperar hasta la próxima llegada
                total_vehiculos += 1  # Incrementar el contador total de vehículos
                entorno.process(vehiculo(entorno, cabina, tipo_vehiculo))  # Iniciar el proceso de atención del vehículo

# Función para modelar el comportamiento de los vehículos
def vehiculo(entorno, cabina, tipo_vehiculo):
    global tiempo_total_espera, tiempos_espera
    tiempo_llegada = entorno.now  # Tiempo de llegada del vehículo
    with cabina.request() as req:  # Solicitar una cabina de peaje
        yield req  # Esperar hasta que una cabina esté disponible
        tiempo_servicio = TIEMPOS_SERVICIO[tipo_vehiculo]()  # Obtener el tiempo de servicio del vehículo
        yield entorno.timeout(tiempo_servicio)  # Simular el tiempo de servicio
    tiempo_espera = entorno.now - tiempo_llegada  # Calcular el tiempo de espera
    tiempo_total_espera += tiempo_espera  # Sumar el tiempo de espera total
    tiempos_espera.append(tiempo_espera)  # Agregar el tiempo de espera a la lista

# Configuración de la simulación
entorno = simpy.Environment()  # Crear el entorno de simulación

# Función para manejar las cabinas
def control_cabina(entorno, cabina):
    while True:
        hora_actual = int(entorno.now / 60)  # Hora actual de la simulación
        if es_hora_pico(hora_actual):
            nueva_capacidad = 2  # Durante horas pico, la capacidad es 2
        else:
            nueva_capacidad = 1  # Fuera de horas pico, la capacidad es 1

        if cabina.capacity != nueva_capacidad:
            # Cambiar la capacidad de la cabina
            cabina = simpy.Resource(entorno, capacity=nueva_capacidad)
        
        yield entorno.timeout(60)  # Revisar cada hora

cabina = simpy.Resource(entorno, capacity=1)  # Crear el recurso de cabina
entorno.process(control_cabina(entorno, cabina))  # Iniciar el proceso de control de cabinas
entorno.process(llegada_vehiculos(entorno, cabina))  # Iniciar el proceso de llegadas de vehículos

# Ejecutar la simulación
entorno.run(until=TIEMPO_SIMULACION)  # Ejecutar la simulación por 1440 minutos (24 horas)

# Resultados de la simulación
print(f"Total de vehículos: {total_vehiculos}")  # Imprimir el total de vehículos atendidos
print(f"Tiempo promedio de espera: {statistics.mean(tiempos_espera):.2f} segundos")  # Imprimir el tiempo de espera promedio
print(f"Tiempo máximo de espera: {max(tiempos_espera):.2f} segundos")  # Imprimir el tiempo de espera máximo
print(f"Tiempo mínimo de espera: {min(tiempos_espera):.2f} segundos")  # Imprimir el tiempo de espera mínimo

# Medidas de rendimiento adicionales
superan_3_min = sum(1 for t in tiempos_espera if t > 180)  # Contar vehículos con tiempos de espera mayores a 3 minutos
porcentaje_superan_3_min = (superan_3_min / total_vehiculos) * 100  # Calcular el porcentaje de esos vehículos

print(f"Vehículos que superan 3 minutos de espera: {superan_3_min} ({porcentaje_superan_3_min:.2f}%)")  # Imprimir la cantidad y porcentaje de vehículos que esperan más de 3 minutos
