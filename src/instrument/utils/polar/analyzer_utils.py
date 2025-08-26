import math


def calcdhkl(h, k, l, alpha, beta, gamma, symmetry, a, b, c):
    if symmetry == "cub":
        dhkl2inv = (h * h + k * k + l * l) / (a * a)
    elif symmetry == "tet":
        dhkl2inv = (h * h + k * k) / (a * a) + (l * l) / (c * c)
    elif symmetry == "ort":
        dhkl2inv = (h * h) / (a * a) + (k * k) / (b * b) + (l * l) / (c * c)
    elif symmetry == "rho":
        n = (h * h + k * k + l * l) * pow(math.sin(alpha), 2.0) + 2.0 * (
            h * k + k * l + h * l
        ) * (pow(math.cos(alpha), 2.0) - math.cos(alpha))
        d = (
            a
            * a
            * (
                1.0
                - 3.0 * pow(math.cos(alpha), 2.0)
                + 2.0 * pow(math.cos(alpha), 3.0)
            )
        )
        dhkl2inv = n / d
    elif symmetry == "hex":
        dhkl2inv = (4.0 / 3.0) * (h * h + h * k + k * k) / (a * a) + (l * l) / (
            c * c
        )
    elif symmetry == "monoclinic":
        dhkl2inv = (
            (h * h) / (a * a)
            + (k * k * pow(math.sin(beta), 2.0)) / (b * b)
            + (l * l) / (c * c)
            - (2.0 * h * l * math.cos(beta)) / (a * c)
        ) / (pow(math.sin(beta), 2.0))
    elif symmetry == "triclinic":
        V = (
            a
            * b
            * c
            * math.sqrt(
                (
                    1.0
                    - pow(math.cos(alpha), 2.0)
                    - pow(math.cos(beta), 2.0)
                    - pow(math.cos(gamma), 2.0)
                    + 2.0 * math.cos(alpha) * math.cos(beta) * math.cos(gamma)
                )
            )
        )
        n1 = (
            pow(h * b * c * math.sin(alpha), 2)
            + pow(k * a * c * math.sin(beta), 2)
            + pow(l * a * b * math.sin(gamma), 2)
        )
        n2 = (
            2
            * h
            * k
            * a
            * b
            * c
            * c
            * (math.cos(alpha) * math.cos(beta) - math.cos(gamma))
        )
        n3 = (
            2
            * k
            * l
            * a
            * a
            * b
            * c
            * (math.cos(beta) * math.cos(gamma) - math.cos(alpha))
        )
        n4 = (
            2
            * h
            * l
            * a
            * b
            * b
            * c
            * (math.cos(alpha) * math.cos(gamma) - math.cos(beta))
        )
        dhkl2inv = (n1 + n2 + n3 + n4) / (pow(V, 2.0))
    else:
        raise ValueError("Lattice system not specified for this analyzer.")
    return 1.0 / math.sqrt(dhkl2inv)


def check_structure_factor(h, k, l, spacegroupnumber, special):
    if spacegroupnumber == 225 and special == "none":
        return (h + k) % 2 == 0 and (k + l) % 2 == 0 and (h + l) % 2 == 0
    elif spacegroupnumber == 229 and special == "none":
        return (h + k + l) % 2 == 0
    elif spacegroupnumber == 227 and special == "8a":
        return ((h + k + l) % 2 != 0 and (h != 0 and k != 0 and l != 0)) or (
            (h + k + l) % 2 == 0 and (h + k + l) % 4 == 0
        )
    elif spacegroupnumber == 194 and special == "2c":
        return l % 2 == 0 or (h - k - 1) % 3 == 0 or (h - k - 2) % 3 == 0
    elif spacegroupnumber == 167 and special == "12c":
        return (-h + k + l) % 3 == 0 and l % 2 == 0
    elif spacegroupnumber == 62 and special == "4b":
        return (h + l) % 2 == 0 and k % 2 == 0
    else:
        return True
