import random
import heapq
import statistics
import scipy.stats as stats
import matplotlib.pyplot as plt
from enum import Enum

# Definición de tipos de vehículo y tasas de llegada
class Vehiculo(Enum):
    GRAN_PORTE = 'Gran Porte'
    GRANDE = 'Grande'
    PEQUENO = 'Pequeño'
    MOTOCICLETA = 'Motocicleta'
    ESPECIAL = 'Especial'

# Tasas de llegada de los vehículos en hora pico y no pico (TODAS SIGUEN UNA DISTRIBUCIÓN EXPONENCIAL)
TIEMPOS_ENTRE_LLEGADAS = {
    'pico': {
        Vehiculo.GRAN_PORTE: 1/30,  # 1 cada 30 segundos
        Vehiculo.GRANDE: 1/40,      # 1 cada 40 segundos
        Vehiculo.PEQUENO: 1/25,     # 1 cada 25 segundos
        Vehiculo.MOTOCICLETA: 1/380        # 1 cada 380 segundos
    },
    'no_pico': {
        Vehiculo.GRAN_PORTE: 1/60,  # 1 cada 60 segundos
        Vehiculo.GRANDE: 1/70,      # 1 cada 70 segundos
        Vehiculo.PEQUENO: 1/40,     # 1 cada 40 segundos
        Vehiculo.MOTOCICLETA: 1/380        # 1 cada 380 segundos
    }
}

# Distribuciones del tiempo de atención usando la librería random
TIEMPOS_SERVICIO = {
    Vehiculo.GRAN_PORTE: lambda: random.uniform(45, 55),  # Distribución uniforme
    Vehiculo.GRANDE: lambda: random.expovariate(1 / 30),  # Distribución exponencial
    Vehiculo.PEQUENO: lambda: random.triangular(15, 20, 35),  # Distribución triangular
    Vehiculo.MOTOCICLETA: lambda: random.expovariate(1 / 30)     # Distribución exponencial
}

# Períodos de tiempo pico
horarios_pico_mañana = [(7, 9)]  # De 7hs a 9hs
horarios_pico_vespertino = [(19, 20)]  # De 19hs a 20hs

# Sucesos: momentos en los que se producen cambios en el sistema
class Suceso:
    def __init__(self, tiempo, tipo_suceso, tipo_vehiculo=None, tiempo_llegada=None):
        self.tiempo = tiempo
        self.tiempo_llegada = tiempo_llegada    # Usado para conocer el tiempo de llegada de los sucesos 'salida'
        self.tipo_suceso = tipo_suceso
        self.tipo_vehiculo = tipo_vehiculo
        
    # El método __lt__ permite que los objetos Suceso se ordenen en una cola de prioridad basada en el atributo "tiempo". En el contexto de una cola de prioridad (heap), esto asegura que los sucesos se procesen en el orden correcto basado en el tiempo en el que ocurren.
    def __lt__(self, otro_suceso):
        return self.tiempo < otro_suceso.tiempo

class SimulacionCabinas:
    def __init__(self, tiempo_final, horarios_pico_mañana, horarios_pico_vespertino, multa_espera):
        self.tiempo_actual = 0
        self.tiempo_final = tiempo_final
        self.horarios_pico_mañana = horarios_pico_mañana
        self.horarios_pico_vespertino = horarios_pico_vespertino
        self.cola_sucesos = []  # Cola de prioridad basada en heaps
        self.cabinas_libres = 1  # Número de cabinas disponibles inicialmente
        self.cola_vehiculos = []
        self.vehiculos_atendidos = 0    
        self.tiempos_espera = []    # (es una lista, para tener los tiempos individuales de cada vehiculo y calcular estadísticas)
        self.multa_espera_excesiva = multa_espera  # Multa por tiempo de espera excesivo (por segundo)
        self.costo_cabina_extra = 100  # Costo por habilitar una cabina extra
        self.LIMITE_ESPERA = 3 * 60  # Límite de espera de 3 minutos
        self.programar_sucesos_iniciales()

    def ejecutar(self):
        while self.tiempo_actual < self.tiempo_final:
            suceso = heapq.heappop(self.cola_sucesos)   # Extrae el primer suceso de la cola de prioridad
            self.tiempo_actual = suceso.tiempo
            self.procesar_suceso(suceso)
        print(f"Simulación finalizada: {self.vehiculos_atendidos} vehículos atendidos.")
        self.calcular_costos()

    def procesar_suceso(self, suceso):
        if suceso.tipo_suceso == 'llegada':
            self.procesar_llegada(suceso)
        elif suceso.tipo_suceso == 'salida':
            self.procesar_salida(suceso)

    def procesar_llegada(self, suceso):
        if self.cabinas_libres > 0:
            self.cabinas_libres -= 1
            tiempo_salida = self.tiempo_actual + TIEMPOS_SERVICIO[suceso.tipo_vehiculo]()
            heapq.heappush(self.cola_sucesos, Suceso(tiempo_salida, 'salida', suceso.tipo_vehiculo))
        else:
            self.cola_vehiculos.append(suceso)  # Si no hay cabinas libres, se encola
        self.proxima_llegada(suceso.tipo_vehiculo)

    def proxima_llegada(self, tipo_vehiculo):
        tasa_arribo = self.obtener_tasa_arribo(tipo_vehiculo)
        tiempo_llegada = self.tiempo_actual + random.expovariate(tasa_arribo)   # Todas las llegadas siguen una distribución exponencial
        heapq.heappush(self.cola_sucesos, Suceso(tiempo_llegada, 'llegada', tipo_vehiculo))

    def obtener_tasa_arribo(self, tipo_vehiculo):
        if self.es_hora_pico():
            return TIEMPOS_ENTRE_LLEGADAS['pico'][tipo_vehiculo]
        else:
            return TIEMPOS_ENTRE_LLEGADAS['no_pico'][tipo_vehiculo]

    def procesar_salida(self, suceso):
        self.vehiculos_atendidos += 1
        self.cabinas_libres += 1
        if self.cola_vehiculos:
            vehiculo_saliente = self.cola_vehiculos.pop(0)  # Se elimina vehiculo de la cola
            tiempo_espera = self.tiempo_actual - vehiculo_saliente.tiempo
            self.tiempos_espera.append(tiempo_espera)
            tiempo_salida = self.tiempo_actual + TIEMPOS_SERVICIO[vehiculo_saliente.tipo_vehiculo]()
            heapq.heappush(self.cola_sucesos, Suceso(tiempo_salida, 'salida', vehiculo_saliente.tipo_vehiculo, tiempo_llegada=suceso.tiempo))

    def es_hora_pico(self):
        hora_actual = (self.tiempo_actual // 3600) % 24  # Convertir tiempo actual en horas del día
        for inicio, fin in self.horarios_pico_mañana + self.horarios_pico_vespertino:
            if inicio <= hora_actual < fin:
                return True
        return False

    def programar_sucesos_iniciales(self):
        for tipo_vehiculo in TIEMPOS_ENTRE_LLEGADAS['no_pico'].keys():
            tiempo_llegada = self.tiempo_actual + random.expovariate(TIEMPOS_ENTRE_LLEGADAS['no_pico'][tipo_vehiculo])
            heapq.heappush(self.cola_sucesos, Suceso(tiempo_llegada, 'llegada', tipo_vehiculo))

    def calcular_costos(self):
        tiempo_total_espera = sum(self.tiempos_espera)
        tiempo_total_habilitacion = sum([((suceso.tiempo - suceso.tiempo_llegada) - self.LIMITE_ESPERA) for suceso in self.cola_sucesos if suceso.tipo_suceso == 'salida' and suceso.tiempo_llegada != None and (suceso.tiempo - suceso.tiempo_llegada) > self.LIMITE_ESPERA])
        multas = tiempo_total_habilitacion * self.multa_espera_excesiva
        costo_total_con_cabina_extra = (tiempo_total_habilitacion // (60*10)) * self.costo_cabina_extra

        print(f"Costo total sin cabina extra (multas): ${multas:.2f}")
        print(f"Costo total con cabina extra: ${costo_total_con_cabina_extra:.2f}")
        if costo_total_con_cabina_extra < multas:
            print("Es más económico habilitar una cabina extra.")
        else:
            print("Es más económico pagar las multas por tiempos de espera excesivos.")
        print("-----------------------------------------------------------------")

    def mostrar_grafico_espera(self, tiempos_espera):
        plt.hist(tiempos_espera, bins=50, edgecolor='black')  # 50 intervalos
        plt.axvline(self.LIMITE_ESPERA, color='red', linestyle='dashed', linewidth=1, label='Límite de 3 minutos')
        plt.xlabel('Tiempo de espera (segundos)')
        plt.ylabel('Número de vehículos')
        plt.title('Distribución de los tiempos de espera de los vehículos')
        plt.legend()
        plt.show()

    def ejecutar_n_veces(self, n):
        tiempos_promedio_espera = []    # Lista para almacenar los tiempos promedio de espera de cada simulación
        for _ in range(n):
            simulacion = SimulacionCabinas(self.tiempo_final, self.horarios_pico_mañana, self.horarios_pico_vespertino, multa_espera)
            simulacion.ejecutar()
            tiempos_promedio_espera.append(statistics.mean(simulacion.tiempos_espera))  # Almacena el promedio

        promedio_espera = statistics.mean(tiempos_promedio_espera)  # Promedio de los tiempos promedios
        intervalo_confianza = stats.t.interval(0.95, len(tiempos_promedio_espera)-1, loc=promedio_espera, scale=stats.sem(tiempos_promedio_espera))
        # Utiliza la distribución t de student para calcular el intervalo de confianza
        # Recibe como primer parámetro el nivel de confianza, el segundo es el número de grados de libertad (n-1)
        # loc son los
        # scale es el parámetro de escala, y le paso el error estándar de la media (SEM) de los tiempos promedios

        print("\nResultados de las simulaciones:")
        print(f"Tiempo promedio de espera: {promedio_espera:.2f} segundos")
        print(f"Intervalo de confianza del 95%: ({intervalo_confianza[0]:.2f}, {intervalo_confianza[1]:.2f})")
        self.mostrar_grafico_espera(tiempos_promedio_espera)

# Crear y correr la simulación
multa_espera = 1  # Multa por tiempo de espera excesivo (por segundo)
simulacion = SimulacionCabinas(24*60*60, horarios_pico_mañana, horarios_pico_vespertino, multa_espera)  # Simulación para 24 horas
simulacion.ejecutar_n_veces(150)