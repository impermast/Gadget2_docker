#field_maker.py

import numpy as np
from unyt import unyt_quantity

def make_scalar_component(field_name, component):
    """
    Фабрика-функция, возвращающая функцию-обёртку для извлечения component-
    го столбца из записи field_name.
    """
    def _func(field, data):
        # data[(ptype, field_name)] — массив размера (N,3)
        return data[field_name][:, component]
    return _func

def make_radius(field_name):
    def _func(field, data):
        coords = data[field_name]  # shape (N,3)
        return np.sqrt((coords**2).sum(axis=1))
    return _func

def make_vel(field_name):
    def _func(field, data):
        coords = data[field_name]  # shape (N,3)
        return np.sqrt((coords**2).sum(axis=1))
    return _func

def make_theta(field_name):
    def _func(field, data):
        x,y,z = np.moveaxis(data[field_name],1,0)
        r = np.sqrt(x*x + y*y + z*z)
        eps = unyt_quantity(1e-15, r.units)
        return np.arccos( z/(r+eps) )
    return _func

def make_phi(field_name):
    def _func(field, data):
        x,y,_ = np.moveaxis(data[field_name],1,0)
        return np.arctan2(y, x)
    return _func

def make_vrad(field_pos, field_vel):
    def _func(field, data):
        x,y,z = np.moveaxis(data[field_pos],1,0)
        vx,vy,vz = np.moveaxis(data[field_vel],1,0)
        eps = unyt_quantity(1e-15, x.units)
        r = np.sqrt(x*x + y*y + z*z) + eps
        return (x*vx + y*vy + z*vz)/r
    return _func

def make_vtan(field_pos, field_vel):
    vr = make_vrad(field_pos, field_vel)
    def _func(field, data):
        total = np.sqrt((data[field_vel]**2).sum(axis=1))
        return total - vr(field, data)
    return _func

def make_angular_momentum(field_pos, field_vel):
    def _func(field, data):
        x,y,z = np.moveaxis(data[field_pos],1,0)
        vx,vy,vz = np.moveaxis(data[field_vel],1,0)
        Jx = y*vz - z*vy
        Jy = z*vx - x*vz
        Jz = x*vy - y*vx
        return np.vstack([Jx, Jy, Jz]).T
    return _func


# … (можно аналогично сделать функции для Jx, Jy, Jz, |J|, массы и т.п.) …

def register_particle_fields(ds, ptype):
    """
    Регистрирует в ds для частицы ptype
    поля: x,y,z, r, theta, phi, vx,vy,vz, vr, vt, Jx,Jy,Jz,J
    """
    parent_pos = (ptype, 'Coordinates')
    parent_vel = (ptype, 'Velocities')
	
    
    # словарь: ключ = ваше имя поля в ugrid, значение = (factory, units, sampling)
    fields = {
        f"{ptype}_x":     (make_scalar_component(parent_pos, 0), "kpc",        "particle"),
        f"{ptype}_y":     (make_scalar_component(parent_pos, 1), "kpc",        "particle"),
        f"{ptype}_z":     (make_scalar_component(parent_pos, 2), "kpc",        "particle"),
        f"{ptype}_r":     (make_radius(parent_pos),              "kpc",        "particle"),
        f"{ptype}_theta": (make_theta(parent_pos),               "",           "particle"),
        f"{ptype}_phi":   (make_phi(parent_pos),                 "",           "particle"),
        f"{ptype}_vx":    (make_scalar_component(parent_vel, 0), "km/s",       "particle"),
        f"{ptype}_vy":    (make_scalar_component(parent_vel, 1), "km/s",       "particle"),
        f"{ptype}_vz":    (make_scalar_component(parent_vel, 2), "km/s",       "particle"),
        f"{ptype}_v":   (make_radius(parent_vel),             "km/s",       "particle"),
        # f"{ptype}_v_r":   (make_vrad(parent_pos, parent_vel),    "km/s",       "particle"),
        f"{ptype}_vtan":   (make_vtan(parent_pos, parent_vel),    "km/s",       "particle"),
    }

    for fname, (func, units, sampling) in fields.items():
        ds.add_field(
            (ptype, fname),
            function=func,
            sampling_type=sampling,
            units=units
        )
        
    print(f"[yt] registered particle fields for {ptype}: {list(fields.keys())}")
