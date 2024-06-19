import random
import matplotlib.pyplot as plt
import statistics

# Parámetros de la simulación
TIEMPOS_ENTRE_LLEGADAS_PICO = {'grande': 30, 'mediano': 40, 'pequeño': 25, 'motocicleta': 380}  # Tiempo entre llegadas durante horas pico (en segundos)
TIEMPOS_ENTRE_LLEGADAS_NO_PICO = {'grande': 60, 'mediano': 70, 'pequeño': 40, 'motocicleta': 380}  # Tiempo entre llegadas fuera de horas pico (en segundos)
TIEMPOS_SERVICIO = {
    'grande': lambda: random.uniform(45, 55),  # Tiempo de servicio para vehículos grandes (uniforme entre 45 y 55 segundos)
    'mediano': lambda: random.expovariate(1 / 30),  # Tiempo de servicio para vehículos medianos (exponencial con media de 30 segundos)
    'pequeño': lambda: random.triangular(15, 20, 35),  # Tiempo de servicio para vehículos pequeños (triangular entre 15, 20 y 35 segundos)
    'motocicleta': lambda: random.expovariate(1 / 30)  # Tiempo de servicio para motocicletas (exponencial con media de 30 segundos)
}
TIEMPO_SIMULACION = 1440  # Tiempo total de simulación en minutos (24 horas)
LIMITE_ESPERA = 3  # Tiempo de espera límite (3 minutos)

# Variables de estado
total_vehiculos = 0  # Contador total de vehículos atendidos
tiempos_espera = []  # Lista para almacenar los tiempos de espera individuales (en minutos)
eventos = []  # Lista para almacenar los eventos (llegadas y salidas de vehículos)

# Función para generar llegadas de vehículos (infinita)
def llegada_vehiculos(entorno, estacion: str, cabinas: int):
    global total_vehiculos, eventos

    while True:
        hora_actual = int(entorno.now / 60) % 24  # Hora actual de la simulación (convertida de minutos a horas)
        # Determinar si es hora pico, para ajustar los tiempos entre llegadas
        tiempos_entre_llegadas = TIEMPOS_ENTRE_LLEGADAS_PICO if es_hora_pico(hora_actual) else TIEMPOS_ENTRE_LLEGADAS_NO_PICO

        tipos_vehiculos = list(tiempos_entre_llegadas.keys())
        for tipo_vehiculo in tipos_vehiculos:
            tiempo_entre_llegadas_segundos = tiempos_entre_llegadas[tipo_vehiculo]  # Tiempo entre llegadas (en segundos)
            tiempo_entre_llegadas_minutos = tiempo_entre_llegadas_segundos / 60  # Convertir a minutos
            print(f"Llegó vehículo tipo '{tipo_vehiculo}' a la estación {estacion} en el minuto {entorno.now}")
            total_vehiculos += 1
            eventos.append((entorno.now, 'llegada', tipo_vehiculo, estacion))
            entorno.process(atender_vehiculo(entorno, estacion, cabinas, tipo_vehiculo))

        yield entorno.timeout(random.expovariate(1 / tiempo_entre_llegadas_minutos))  # Esperar tiempo entre llegadas

# Función para modelar la atención de los vehículos
def atender_vehiculo(entorno, estacion: str, cabinas: int, tipo_vehiculo: str):
    tiempo_llegada = entorno.now  # Tiempo de llegada del vehículo

    with cabinas.request() as req:
        yield req
        tiempo_servicio_segundos = TIEMPOS_SERVICIO[tipo_vehiculo]()  # Obtener tiempo de servicio
        tiempo_servicio_minutos = tiempo_servicio_segundos / 60
        yield entorno.timeout(tiempo_servicio_minutos)  # Simular tiempo de servicio

    tiempo_espera = entorno.now - tiempo_llegada  # Calcular tiempo de espera
    tiempos_espera.append(tiempo_espera)
    eventos.append((entorno.now, 'salida', tipo_vehiculo, estacion))

# Función para verificar si es hora pico
def es_hora_pico(hora: int):
    return any(inicio <= hora < fin for inicio, fin in [(7, 9), (19, 20)])  # Intervalos de horas pico

# Configuración de la simulación
entorno = simpy.Environment()
cabinas = simpy.Resource(entorno, capacity=1)

# Iniciar procesos de llegada de vehículos en ambas estaciones
for estacion in ['A', 'D']:
    entorno.process(llegada_vehiculos(entorno, estacion, cabinas))

# Ejecutar simulación
entorno.run(until=TIEMPO_SIMULACION)

# Resultados
print(f"Total de vehículos atendidos: {total_vehiculos}")
print(f"Tiempo promedio de espera: {statistics.mean(tiempos_espera):.2f} minutos")
print(f"Tiempo máximo de espera: {max(tiempos_espera):.2f} minutos")
print(f"Tiempo mínimo de espera: {min(tiempos_espera):.2f} minutos")
vehiculos_superan_limite = sum(1 for t in tiempos_espera if t > LIMITE_ESPERA)
print(f"Vehículos que superan {LIMITE_ESPERA} minutos de espera: {vehiculos_superan_limite} ({vehiculos_superan_limite / total_vehiculos * 100:.2f}%)")  # Imprimir el porcentaje de vehículos que superan el tiempo de espera límite
print()

# Graficar los tiempos de espera de los vehículos
plt.hist(tiempos_espera, bins=50, edgecolor='black')
plt.axvline(LIMITE_ESPERA, color='red', linestyle='dashed', linewidth=1, label=f'Límite de {LIMITE_ESPERA} minutos')
plt.xlabel('Tiempo de espera (minutos)')
plt.ylabel('Número de vehículos')
plt.title('Distribución de los tiempos de espera de los vehículos')
plt.legend()
plt.show()
