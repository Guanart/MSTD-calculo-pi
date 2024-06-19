import simpy
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
HORAS_PICO_A = [(7, 9)]  # Intervalos de horas pico en estación A (de 7 a 9)
HORAS_PICO_D = [(19, 20)]  # Intervalos de horas pico en estación D (de 19 a 20)
# TIEMPO_SIMULACION = 1440 * 7  # Tiempo total de simulación en minutos (7 días)
TIEMPO_SIMULACION = 1440 # Tiempo total de simulación en minutos (24 horas)
COSTO_CABINA_EXTRA = 100  # Costo de habilitar una cabina extra por cada 10 minutos
LIMITE_ESPERA = 3  # Tiempo de espera límite (3 minutos)

# chequear LIMITE_ESPERA

# Variables de estado
tiempo_total_espera = 0  # Tiempo total de espera acumulado
total_vehiculos = 0  # Contador total de vehículos atendidos
tiempos_espera = []  # Lista para almacenar los tiempos de espera individuales (en minutos)
eventos = []  # Lista para almacenar los eventos (llegadas y salidas de vehículos)

# Función para verificar si es hora pico en una estación
def es_hora_pico(hora, estacion: str):
    horas_pico = HORAS_PICO_A if estacion == 'A' else HORAS_PICO_D
    for inicio, fin in horas_pico:
        if inicio <= hora < fin:
            return True
    return False

# Función para generar llegadas de vehículos (infinita)
def llegada_vehiculos(entorno, estacion: str, cabinas: simpy.Resource):
    global total_vehiculos, eventos

    while True:     # Bucle infinito para simular la llegada continua de vehículos
        hora_actual = int(entorno.now / 60) % 24  # Hora actual de la simulación (convertida de minutos a horas)
        # Determinar si es hora pico, para ajustar los tiempos entre llegadas
        if estacion == 'A' and es_hora_pico(hora_actual, 'A'):
            tiempos_entre_llegadas = TIEMPOS_ENTRE_LLEGADAS_PICO  # Usar tiempos entre llegadas para horas pico en estación A
        elif estacion == 'D' and es_hora_pico(hora_actual, 'D'):
            tiempos_entre_llegadas = TIEMPOS_ENTRE_LLEGADAS_PICO  # Usar tiempos entre llegadas para horas pico en estación D
        else:
            tiempos_entre_llegadas = TIEMPOS_ENTRE_LLEGADAS_NO_PICO  # Usar tiempos entre llegadas para fuera de horas pico

        tipos_vehiculos = list(tiempos_entre_llegadas.keys())
        for tipo_vehiculo in tipos_vehiculos:
            tiempo_entre_llegadas_segundos = tiempos_entre_llegadas[tipo_vehiculo]  # Tiempo entre llegadas (en segundos)
            tiempo_entre_llegadas_minutos = tiempo_entre_llegadas_segundos / 60 # Divide por 60 para convertir a minutos el tiempo_entre_llegadas (que está en segundos)
            yield entorno.timeout(tiempo_entre_llegadas_minutos)
            print(f"Llegó vehículo tipo '{tipo_vehiculo}' a la estación {estacion} en el minuto {entorno.now}")
            total_vehiculos += 1  # Incrementar el contador total de vehículos
            eventos.append((entorno.now, 'llegada', tipo_vehiculo, estacion))  # Registra el evento de llegada
            entorno.process(atender_vehiculo(entorno, estacion, cabinas, tipo_vehiculo))  # Inicia el proceso de atención del vehículo

# Función para modelar la atención de los vehículos
def atender_vehiculo(entorno, estacion: str, cabinas: simpy.Resource, tipo_vehiculo):
    global tiempo_total_espera, tiempos_espera

    tiempo_llegada = entorno.now  # Tiempo de llegada del vehículo

    # PROBLEMA: la capacidad en hora pico no se está actualizando correctamente
    print(f"Capacidad actual de estación {estacion}: {cabinas.capacity}")

    # Se usa la keyword "with" the python, para manejar automáticamente la liberación de la cabina al finalizar el proceso (resource.release() al finalizar)
    with cabinas.request() as req:  # Solicitar una cabina de peaje (un Resource de SimPy)
        yield req  # Espera hasta que una cabina esté disponible
        tiempo_servicio_segundos = TIEMPOS_SERVICIO[tipo_vehiculo]()  # Obtener el tiempo de servicio λ del vehículo (llamando a la función lambda)
        tiempo_servicio_minutos = tiempo_servicio_segundos/60
        yield entorno.timeout(tiempo_servicio_minutos)  # Simula el tiempo de servicio (delay en Arena)

    tiempo_espera = entorno.now - tiempo_llegada    # En minutos
    tiempo_total_espera += tiempo_espera
    tiempos_espera.append(tiempo_espera)    # (no lo suma al acumulador, sino a una lista, para tener los tiempos individuales y calcular estadísticas)
    eventos.append((entorno.now, 'salida', tipo_vehiculo, estacion))  # Registra el evento de salida

# Función generadora para manejar las cabinas en una estación
def control_cabinas(entorno, estacion: str, cabinas: simpy.Resource):
    while True:
        hora_actual = int(entorno.now / 60) % 24  # Hora actual de la simulación    (% es el módulo o residuo de la división)
        print(f"\nHORA ACTUAL {hora_actual}\n")
        horas_pico = HORAS_PICO_A if estacion == 'A' else HORAS_PICO_D

        # Verifica si la hora actual está dentro de algún intervalo de horas pico.
        if any(inicio <= hora_actual < fin for inicio, fin in horas_pico):
            nueva_capacidad = 3  # Durante horas pico, la capacidad es 3
            if cabinas.capacity == 1: # Si la capacidad es 1 y es hora pico, muestra mensaje de comienzo de hora pico
                print(f"COMIENZO HORA PICO PARA ESTACIÓN {estacion}. Capacidad modificada: {nueva_capacidad}")
        else:
            nueva_capacidad = 1  # Fuera de horas pico, la capacidad es 1
            if cabinas.capacity == 3: # Si la capacidad es 3 y no es hora pico, muestra mensaje de fin de hora pico
                print(f"FIN HORA PICO PARA ESTACIÓN {estacion}. Capacidad modificada: {nueva_capacidad}")

        # Cambiar la capacidad de las cabinas
        if cabinas.capacity != nueva_capacidad:
            # PROBLEMA: LA LIBRERÍA NO PERMITE MODIFICAR LA CAPACIDAD DE UN RECURSO UNA VEZ CREADO
            # Esto hace que no pueda incrementar la capacidad de la estacion en hora pico :(
            cabinas = simpy.Resource(entorno, capacity=nueva_capacidad)

        yield entorno.timeout(60)  # Revisa o ejecuta cada hora

# Configuración de la simulación
entorno = simpy.Environment()  # Crear el entorno de simulación

# Crear los Resources e iniciar los Process de control de cabinas y llegadas de vehículos en ambas estaciones
cabinas = {'A': simpy.Resource(entorno, capacity=1), 'D': simpy.Resource(entorno, capacity=1)}
for estacion in ['A']:#, 'D']:
    # Se pasan funciones generadoras a entorno.process() para iniciar los procesos
    entorno.process(control_cabinas(entorno, estacion, cabinas[estacion]))
    entorno.process(llegada_vehiculos(entorno, estacion, cabinas[estacion]))

# Ejecutar la simulación - Se ejecuta 1 réplica de la simulación (hacer varios runs para obtener resultados más robustos)
entorno.run(until=TIEMPO_SIMULACION)  # Ejecutar la simulación por TIEMPO_SIMULACION minutos

#############################################################################################################################################################
##                                                               Resultados de la simulación                                                               ##
#############################################################################################################################################################
# print(tiempos_espera)
# print(eventos)
# exit()

print(f"Total de vehículos: {total_vehiculos}\n")  # Total de vehículos atendidos
print(f"Tiempo promedio de espera: {statistics.mean(tiempos_espera):.2f} segundos ({statistics.mean(tiempos_espera)/60/60:.2f} horas)")  # Tiempo de espera promedio (mean)
print(f"Tiempo máximo de espera: {max(tiempos_espera):.2f} segundos ({max(tiempos_espera)/60/60:.2f} horas)")
print(f"Tiempo mínimo de espera: {min(tiempos_espera):.2f} segundos")
vehiculos_superan_limite = sum(1 for t in tiempos_espera if t > LIMITE_ESPERA)  # Calcular el número de vehículos que superan el tiempo de espera límite
print(f"Vehículos que superan 3 minutos de espera: {vehiculos_superan_limite} ({vehiculos_superan_limite / total_vehiculos * 100:.2f}%)")  # Imprimir el porcentaje de vehículos que superan el tiempo de espera límite
print()

# Cálculo del costo de habilitar una cabina extra y la multa necesaria v1
# tiempo_habilitacion_extra = TIEMPO_SIMULACION / 60 / 10  # Tiempo total de habilitación de la cabina extra (en unidades de 10 minutos)
# costo_total_habilitacion = tiempo_habilitacion_extra * COSTO_CABINA_EXTRA  # Calcular el costo total de habilitar la cabina extra
# multa_necesaria = costo_total_habilitacion / vehiculos_superan_limite if vehiculos_superan_limite > 0 else 0  # Calcular la multa necesaria por vehículo que supera el tiempo de espera límite
# print(f"Costo total de habilitar una cabina extra: ${costo_total_habilitacion:.2f}")  # Imprimir el costo total de habilitar la cabina extra
# print(f"Multa necesaria por vehículo que supera 3 minutos de espera: ${multa_necesaria:.2f}")  # Imprimir la multa necesaria por vehículo que supera el tiempo de espera límite


# Cálculo del costo de habilitar una cabina extra y la multa necesaria v2 
tiempo_habilitacion_extra = sum(t - LIMITE_ESPERA for t in tiempos_espera if t > LIMITE_ESPERA)  # Calcula el tiempo total extra de espera de los vehículos que superan el límite (en MINUTOS)
bloques_10_minutos = (tiempo_habilitacion_extra // 10) + 10 # Calcula cuántos bloques de 10 minutos se necesitan para cubrir el tiempo total extra de espera. Le suma 10 para redondear hacia arriba (añadir 1 bloque de 10 minutos adicional)
costo_total_habilitacion = bloques_10_minutos * COSTO_CABINA_EXTRA  # Calcular el costo total de habilitar la cabina extra
# if vehiculos_superan_limite % 3 != 0:
#     tiempo_habilitacion_extra += 10  # Añadir 10 minutos adicionales si hay vehículos que no completan el múltiplo de 3
# costo_total_habilitacion = tiempo_habilitacion_extra * COSTO_CABINA_EXTRA  # Calcular el costo total de habilitar la cabina extra
multa_necesaria = costo_total_habilitacion / vehiculos_superan_limite if vehiculos_superan_limite > 0 else 0  # Calcular la multa necesaria (MÍNIMA) por vehículo que supera el tiempo de espera límite

print(f"Costo total de habilitar una cabina extra: ${costo_total_habilitacion:.2f}")  # Imprimir el costo total de habilitar la cabina extra
print(f"Multa necesaria MÍNIMA por vehículo que supera 3 minutos de espera: ${multa_necesaria:.2f}")  # Imprimir la multa necesaria por vehículo que supera el tiempo de espera límite

print(f"Intervalo de confianza del 95%: {statistics.stdev(tiempos_espera) / (total_vehiculos ** 0.5) * 1.96:.2f} minutos")

# Graficar los tiempos de espera de los vehículos
plt.hist(tiempos_espera, bins=50, edgecolor='black')
plt.axvline(LIMITE_ESPERA, color='red', linestyle='dashed', linewidth=1, label='Límite de 3 minutos')
plt.xlabel('Tiempo de espera (segundos)')
plt.ylabel('Número de vehículos')
plt.title('Distribución de los tiempos de espera de los vehículos')
plt.legend()
plt.show()