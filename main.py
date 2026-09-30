from machine import Pin, PWM, Timer
import sys
import select
import time
 
# ---------------- Configuración ----------------
PIN_AMARILLO = 25
PIN_AZUL = 26
PIN_ROJO = 27
FREQ_PWM = 1000          # Hz
PERIODO_LECTURA = 20     # ms, cada cuánto el timer revisa el puerto serial
 
# ---------------- LEDs con PWM ----------------
led_amarillo = PWM(Pin(PIN_AMARILLO), freq=FREQ_PWM)
led_azul = PWM(Pin(PIN_AZUL), freq=FREQ_PWM)
led_rojo = PWM(Pin(PIN_ROJO), freq=FREQ_PWM)
LEDS = [led_amarillo, led_azul, led_rojo]
 
 
def porcentaje(p):
    """Convierte un porcentaje (0-100) a duty de 16 bits (0-65535)."""
    return int(p * 65535 / 100)
 
 
def apagar_todos():
    for led in LEDS:
        led.duty_u16(0)
 
 
def encender_solo(led, p):
    """Apaga todos y enciende solo un LED con la intensidad p (%)."""
    apagar_todos()
    led.duty_u16(porcentaje(p))
 
 
# ---------------- Lectura serial por interrupción de timer ----------------
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
 
buffer = ""
comando_nuevo = None     # bandera: se llena cuando llega un comando completo
 
 
def leer_serial(t):
    """ISR del timer: lee lo que haya en el USB sin bloquear."""
    global buffer, comando_nuevo
    while poller.poll(0):
        c = sys.stdin.read(1)
        if c in ("\n", "\r"):
            if buffer:
                comando_nuevo = buffer.strip()
                buffer = ""
        else:
            buffer += c
            if len(buffer) > 32:     # protección contra basura en el puerto
                buffer = ""
 
 
timer = Timer(0)
timer.init(period=PERIODO_LECTURA, mode=Timer.PERIODIC, callback=leer_serial)
 
 
def esperar(ms):
    """Espera ms milisegundos, pero sale antes si llega un comando nuevo.
    Devuelve False si la secuencia debe interrumpirse."""
    fin = time.ticks_add(time.ticks_ms(), ms)
    while time.ticks_diff(fin, time.ticks_ms()) > 0:
        if comando_nuevo is not None:
            return False
        time.sleep_ms(5)
    return True
 
 
# ---------------- Secuencias ----------------
def secuencia_modo1():
    """Modo 1 (pulgar abajo): barrido ida y vuelta, un LED a la vez."""
    orden = [led_amarillo, led_azul, led_rojo, led_azul]
    for led in orden:
        encender_solo(led, 100)
        if not esperar(150):
            return
 
 
def secuencia_modo2():
    """Modo 2 (pulgar arriba): 'respiración', los tres LEDs suben y bajan juntos."""
    for p in list(range(0, 101, 5)) + list(range(100, -1, -5)):
        for led in LEDS:
            led.duty_u16(porcentaje(p))
        if not esperar(30):
            return
 
 
# ---------------- Procesamiento de comandos ----------------
modo = "APAGADO"
 
 
def procesar(cmd):
    global modo
    if cmd == "Closed_Fist":
        modo = "AMARILLO"
        encender_solo(led_amarillo, 30)
    elif cmd == "Victory":
        modo = "AZUL"
        encender_solo(led_azul, 70)
    elif cmd == "Open_Palm":
        modo = "ROJO"
        encender_solo(led_rojo, 100)
    elif cmd == "Thumb_Down":
        modo = "MODO1"
    elif cmd == "Thumb_Up":
        modo = "MODO2"
    else:
        return                     # gesto desconocido o "None": se mantiene el estado
    print("OK:", cmd, "->", modo)  # respuesta al PC (opcional)
 
 
# ---------------- Programa principal ----------------
apagar_todos()
print("ESP32 lista. Esperando gestos...")
 
try:
    while True:
        if comando_nuevo is not None:
            cmd = comando_nuevo
            comando_nuevo = None
            procesar(cmd)
 
        if modo == "MODO1":
            secuencia_modo1()
        elif modo == "MODO2":
            secuencia_modo2()
        else:
            time.sleep_ms(10)
 
except KeyboardInterrupt:
    timer.deinit()
    apagar_todos()
    print("Programa detenido.")
 
