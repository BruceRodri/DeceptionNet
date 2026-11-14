"""POLITICAS Y REGLAS INDEPENDIENTES DEL TRANSPORTE Y DE POSTGRESQL."""
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class ReglaUmbral:
    """DEFINIR EL TIPO DE EVENTO, EL UMBRAL Y LA VENTANA DE UNA REGLA."""
    nombre: str
    tipo: str
    umbral: int
    ventana_segundos: int
    severidad: str = 'media'
    sensor: str | None = None

    def __post_init__(self):
        if self.umbral < 1 or self.ventana_segundos < 1:
            raise ValueError('EL UMBRAL Y LA VENTANA DEBEN SER POSITIVOS')

    def aplica(self, evento):
        """COMPROBAR SI UN EVENTO TIENE LOS DATOS PARA EVALUAR LA REGLA."""
        return bool(evento.sensor and evento.origen and evento.tipo == self.tipo
                    and (self.sensor is None or evento.sensor == self.sensor))

    def inicio_ventana(self, evento):
        return evento.fecha - timedelta(seconds=self.ventana_segundos)

    def alcanzada(self, cantidad):
        return cantidad >= self.umbral


class Detector:
    """SELECCIONAR LA POLITICA ADECUADA SIN CLASIFICAR COMANDOS COMO ATAQUES."""
    def __init__(self, reglas):
        self.reglas = tuple(reglas)

    def reglas_para(self, evento):
        return tuple(regla for regla in self.reglas if regla.aplica(evento))
