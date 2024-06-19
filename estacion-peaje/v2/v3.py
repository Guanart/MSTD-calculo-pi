import random
import heapq
import statistics
import scipy.stats as stats

# Definición de tipos de vehículo y tasas de llegada
class Vehiculo:
    GRAN_PORTE = 'Gran Porte'
    GRANDE = 'Grande'
    PEQUENO = 'Pequeño'
    MOTO = 'Moto'
    PRIORITARIOS = ['Ambulancia', 'Bomberos', 'Policía']

# Tasas de llegada de los vehículos en hora pico y no pico
tasas_llegada = {
    'pico': {
        Vehiculo.GRAN_PORTE: 1/30,  # 1 cada 30 segundos
        Vehiculo.GRANDE: 1/40,      # 1 cada 40 segundos
        Vehiculo.PEQUENO: 1/25,     # 1 cada 25 segundos
        Vehiculo.MOTO: 1/380        # 1 cada 380 segundos
    },
    'no_pico': {
        Vehiculo.GRAN_PORTE: 1/60,  # 1 cada 60 segundos
        Vehiculo.GRANDE: 1/70,      # 1 cada 70 segundos
        Vehiculo.PEQUENO: 1/40,     # 1 cada 40 segundos
        Vehiculo.MOTO: 1/380        # 1 cada 380 segundos
    }
}

# Distribuciones del tiempo de atención usando random
distribuciones_tiempo_atencion = {
    Vehiculo.GRAN_PORTE: lambda: random.uniform(45, 55),  # Distribución uniforme
    Vehiculo.GRANDE: lambda: random.expovariate(1 / 30),  # Distribución exponencial
    Vehiculo.PEQUENO: lambda: random.triangular(15, 20, 35),  # Distribución triangular
    Vehiculo.MOTO: lambda: random.expovariate(1 / 30)     # Distribución exponencial
}

# Períodos de tiempo pico
periodos_pico_A = [(7, 9)]  # De 7 a 9
periodos_pico_D = [(19, 20)]  # De 19 a 20

# Clase Evento
class Evento:
    def __init__(self, tiempo, tipo_evento, tipo_vehiculo=None):
        self.tiempo = tiempo
        self.tipo_evento = tipo_evento
        self.tipo_vehiculo = tipo_vehiculo
        
    def __lt__(self, otro):
        return self.tiempo < otro.tiempo

# Clase SimulacionPeaje
class SimulacionPeaje:
    def __init__(self, tiempo_final, periodos_pico_A, periodos_pico_D):
        self.tiempo_actual = 0
        self.tiempo_final = tiempo_final
        self.periodos_pico_A = periodos_pico_A
        self.periodos_pico_D = periodos_pico_D
        self.cola_eventos = []
        self.cabinas_disponibles = 1  # Número de cabinas disponibles inicialmente
        self.cola_vehiculos = []
        self.tiempos_espera = []
        self.vehiculos_atendidos = 0
        self.multa_por_espera_excesiva = 10  # Multa por tiempo de espera excesivo (por segundo)
        self.costo_por_cabina_extra = 100  # Costo por habilitar una cabina extra
        self.programar_eventos_iniciales()

    def correr(self):
        while self.tiempo_actual < self.tiempo_final and self.cola_eventos:
            evento = heapq.heappop(self.cola_eventos)
            self.tiempo_actual = evento.tiempo
            self.manejar_evento(evento)
        print(f"Simulación finalizada: {self.vehiculos_atendidos} vehículos atendidos.")
        self.evaluar_costos()

    def programar_eventos_iniciales(self):
        for tipo_vehiculo in tasas_llegada['no_pico'].keys():
            tiempo_llegada = self.tiempo_actual + random.expovariate(tasas_llegada['no_pico'][tipo_vehiculo])
            heapq.heappush(self.cola_eventos, Evento(tiempo_llegada, 'llegada', tipo_vehiculo))

    def manejar_evento(self, evento):
        if evento.tipo_evento == 'llegada':
            self.manejar_llegada(evento)
        elif evento.tipo_evento == 'salida':
            self.manejar_salida(evento)

    def manejar_llegada(self, evento):
        if self.cabinas_disponibles > 0:
            self.cabinas_disponibles -= 1
            tiempo_salida = self.tiempo_actual + distribuciones_tiempo_atencion[evento.tipo_vehiculo]()
            heapq.heappush(self.cola_eventos, Evento(tiempo_salida, 'salida', evento.tipo_vehiculo))
        else:
            self.cola_vehiculos.append(evento)
        self.programar_proxima_llegada(evento.tipo_vehiculo)

    def programar_proxima_llegada(self, tipo_vehiculo):
        tasa_llegada = self.obtener_tasa_llegada(tipo_vehiculo)
        tiempo_llegada = self.tiempo_actual + random.expovariate(tasa_llegada)
        heapq.heappush(self.cola_eventos, Evento(tiempo_llegada, 'llegada', tipo_vehiculo))

    def obtener_tasa_llegada(self, tipo_vehiculo):
        if self.es_periodo_pico():
            return tasas_llegada['pico'][tipo_vehiculo]
        else:
            return tasas_llegada['no_pico'][tipo_vehiculo]

    def manejar_salida(self, evento):
        self.vehiculos_atendidos += 1
        self.cabinas_disponibles += 1
        if self.cola_vehiculos:
            siguiente_vehiculo = self.cola_vehiculos.pop(0)
            tiempo_espera = self.tiempo_actual - siguiente_vehiculo.tiempo
            self.tiempos_espera.append(tiempo_espera)
            tiempo_salida = self.tiempo_actual + distribuciones_tiempo_atencion[siguiente_vehiculo.tipo_vehiculo]()
            heapq.heappush(self.cola_eventos, Evento(tiempo_salida, 'salida', siguiente_vehiculo.tipo_vehiculo))

    def es_periodo_pico(self):
        hora_actual = (self.tiempo_actual // 3600) % 24  # Convertir tiempo actual en horas del día
        for inicio, fin in self.periodos_pico_A + self.periodos_pico_D:
            if inicio <= hora_actual < fin:
                return True
        return False

    def evaluar_costos(self):
        tiempo_total_espera = sum(self.tiempos_espera)
        multas = tiempo_total_espera * self.multa_por_espera_excesiva
        tiempo_total_habilitacion = sum([min(self.tiempo_final - evento.tiempo, 10*60) for evento in self.cola_eventos if evento.tipo_evento == 'llegada' and self.es_periodo_pico()])
        costo_total_con_cabina_extra = (tiempo_total_habilitacion / 600) * self.costo_por_cabina_extra
        print(f"Costo total sin cabina extra (multas): {multas}")
        print(f"Costo total con cabina extra: {costo_total_con_cabina_extra}")
        if costo_total_con_cabina_extra < multas:
            print("Es más económico habilitar una cabina extra.")
        else:
            print("Es más económico pagar las multas por tiempos de espera excesivos.")

    def correr_multiples_simulaciones(self, n_simulaciones=100):
        tiempos_promedio_espera = []
        for _ in range(n_simulaciones):
            simulacion = SimulacionPeaje(self.tiempo_final, self.periodos_pico_A, self.periodos_pico_D)
            simulacion.correr()
            tiempos_promedio_espera.append(statistics.mean(simulacion.tiempos_espera))
        promedio_espera = statistics.mean(tiempos_promedio_espera)
        intervalo_confianza = stats.t.interval(0.95, len(tiempos_promedio_espera)-1, loc=promedio_espera, scale=stats.sem(tiempos_promedio_espera))
        print(f"Promedio de tiempo de espera: {promedio_espera:.2f} segundos")
        print(f"Tiempo promedio de espera: {promedio_espera:.2f} segundos ({promedio_espera/60/60:.2f} horas)")  # Tiempo de espera promedio (mean)
        print(f"Intervalo de confianza del 95%: ({intervalo_confianza[0]:.2f}, {intervalo_confianza[1]:.2f}) segundos")

# Ejecución de la simulación
tiempo_final = 24 * 3600  # 24 horas en segundos
simulacion_peaje = SimulacionPeaje(tiempo_final, periodos_pico_A, periodos_pico_D)
simulacion_peaje.correr()
simulacion_peaje.correr_multiples_simulaciones(n_simulaciones=100)
