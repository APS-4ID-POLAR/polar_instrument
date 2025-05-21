from ophyd import Device, Component


class FormattedDynamicSubDevice:
    """
    Creates a subdevice with dynamically formatted components.
    """
    def __init__(self, factory_func):
        self.factory_func = factory_func
        self._name = None

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        attr_name = f"_{self._name}_device"
        if not hasattr(instance, attr_name):
            # Build subdevice dynamically
            subdevice_class = self._build_subdevice_class(instance)
            subdevice = subdevice_class(
                '', parent=instance, name=f"{instance.name}_{self._name}"
            )
            setattr(instance, attr_name, subdevice)

        return getattr(instance, attr_name)

    def _build_subdevice_class(self, instance):
        components_dict = {}

        for comp_name, (cls, fmt_str, kwargs) in self.factory_func(
            instance
        ).items():
            formatted = fmt_str.format(**instance.__dict__)

            # Ensure default name
            if "name" not in kwargs:
                kwargs["name"] = f"{instance.name}_{self._name}_{comp_name}"

            # Wrap in Component
            components_dict[comp_name] = Component(cls, formatted, **kwargs)

        return type(
            f"_{self._name.capitalize()}SubDevice", (Device,), components_dict
        )


class InstanceFormattedComponent:
    """
    Acts like a Component that can interpolate format strings using the instance's __dict__.
    Used to dynamically build a subdevice based on instance parameters (like self.prefix1).
    """

    def __init__(self, factory_func):
        self.factory_func = factory_func
        self._name = None

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        attr_name = f"_{self._name}_device"
        if not hasattr(instance, attr_name):
            sub_cls = self._build_subdevice_class(instance)
            sub_inst = sub_cls('', parent=instance, name=f"{instance.name}_{self._name}")
            setattr(instance, attr_name, sub_inst)
        return getattr(instance, attr_name)

    def _build_subdevice_class(self, instance):
        # factory_func uses the instance to generate channel definitions
        defn = self.factory_func(instance)
        components_dict = {}

        for comp_name, (cls, fmt_str, kwargs) in defn.items():
            prefix = fmt_str.format(**vars(instance))  # instance-level string formatting
            if "name" not in kwargs:
                kwargs["name"] = f"{instance.name}_{self._name}_{comp_name}"
            components_dict[comp_name] = Component(cls, prefix, **kwargs)

        return type(
            f"_{self._name.capitalize()}SubDevice", (Device,), components_dict
        )
