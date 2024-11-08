
from ophydregistry import Registry
from pandas import DataFrame

# Registry of all ophyd-style Devices and Signals.
oregistry = Registry(auto_register=False)


def get_devices(label):
    objs = oregistry.findall(label=label, allow_none=True)
    table = {"Object name": [], "PV prefix": [], "Label": []}
    for obj in objs:
        table["Object name"].append(obj.name)
        table["PV prefix"].append(obj.prefix)
        table["Label"].append(obj._ophyd_labels_)
    return DataFrame(table)
