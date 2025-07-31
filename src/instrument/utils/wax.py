from epics import caget, caput
from pyRestTable import Table
from polartools.load_data import load_catalog
from instrument.startup  import oregistry

cat = load_catalog("4id_polar")

def wm(*args):
    result = Table()
    result.labels = ("Motor","Position", "Limits")
    for arg in args:
        pos = arg.user_readback.get()
        llm = arg.low_limit_travel.get()
        hlm = arg.high_limit_travel.get()
        result.rows.append((arg.name,f"{pos:.5f}", f"[{llm:.5f},{hlm:.5f}]"))
    print("")
    print(result.reST(fmt="markdown"))

    
def wax(scan=None,motor=None,device='motor'):
    result = Table()
    devices = oregistry.findall(device)
    missed = []
    if scan:
        result.labels = ("Motor","Position")
        for arg in devices:
            try:
                name = arg.name
                if motor:
                    pos = cat[scan].baseline.read()[name]

                    if motor in pos.name:
                        result.rows.append((name,f"{pos.values[0]}"))
                else:
                    pos = cat[scan].baseline.read()[name]
                    result.rows.append((name,f"{pos.values[0]}"))
            except:
                missed.append(arg.name)
        print("")
        print(f"Motor positions from scan #{scan}")
        print("")
        print(result.reST(fmt="markdown"))
        print(f"{len(missed)} motors missed:")
        print(f"Motors missed {missed}")
    else:
        result.labels = ("Motor", "Position", "Limits")
        for arg in devices:
            try:
                pos = arg.user_readback.get()
                llm = arg.low_limit_travel.get()
                hlm = arg.high_limit_travel.get()
                name = arg.name
                if motor:
                    if motor in name:
                        result.rows.append((name,f"{pos:.5f}", f"[{llm:.5f},{hlm:.5f}]"))
                else:
                    result.rows.append((name,f"{pos:.5f}", f"[{llm:.5f},{hlm:.5f}]"))

            except:
                missed.append(arg.name)
        print("")
        print(result.reST(fmt="markdown"))
        print(f"{len(missed)} motors missed:")
        print(f"Motors missed {missed}")



def wa_scan(scan=None,motor=None):
    result = Table()
    result.labels = ("Motor","Position")
    devices = oregistry.findall('motor')
    missed = []
    if scan:
        for arg in devices:
            try:
                name = arg.name
                if motor:
                    pos = cat[scan].baseline.read()[name]
                    
                    if motor in pos.name:
                        result.rows.append((name,f"{pos.values[0]}"))
                else:
                    pos = cat[scan].baseline.read()[name]
                    result.rows.append((name,f"{pos.values[0]}"))
            except:
                missed.append(arg.name)
        print("")
        print(f"Motor positions from scan #{scan}")
        print("")
        print(result.reST(fmt="markdown"))
        print(f"{len(missed)} motors missed:")
        print(f"Motors missed {missed}")
    else:
        raise TypeError("Wrong parameters. Expected: "
                        "wapast(scan, part_of_motor_name), e.g. wa_past(1560,'huber_hp')")
    

def wa_new(motor=None):
    result = Table()
    result.labels = ("Motor", "Position", "Limits")
    devices = oregistry.findall('motor')
    missed = []
    for arg in devices:
        try:
            pos = arg.user_readback.get()
            llm = arg.low_limit_travel.get()
            hlm = arg.high_limit_travel.get()
            name = arg.name
            if motor: 
                if motor in name:
                   result.rows.append((name,f"{pos:.5f}", f"[{llm:.5f},{hlm:.5f}]"))
            else:
                result.rows.append((name,f"{pos:.5f}", f"[{llm:.5f},{hlm:.5f}]"))

        except:
            missed.append(arg.name)
    print("")
    print(result.reST(fmt="markdown"))
    print(f"{len(missed)} motors missed:")
    print(f"Motors missed {missed}")



    


