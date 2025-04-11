from epics import caget, caput
import math

def atten(atten_value_in=None):
    # write attenuation factor to attenuator device
    # Input as attenuation value: power.first_decimal 
    # e.g. attenuation value 6.3 corresponds to attenuation factor 3e6
    if atten_value_in or str(atten_value_in) == "0":
        if str(atten_value_in) == "0":
            atten_value = 0
        else:
            atten_value = atten_value_in
    else:
        atten_factor = caget("4idPyFilter:FL1:attenuation_actual")
        power = math.floor(math.log(atten_factor,10))
        deci = 0.1*(atten_factor/(10**power))
        atten_value = power + deci
        atten_value = input(f"Attenuator value [{atten_value:.1f}]: ") or atten_value
        atten_value = float(atten_value) if isinstance(atten_value, str) else atten_value
    power =math.floor(atten_value)
    deci = 10*(atten_value-power)
    if deci < 1:
        deci = 1
    atten_factor = deci * 10**power

    caput("4idPyFilter:FL1:attenuation",atten_factor)
