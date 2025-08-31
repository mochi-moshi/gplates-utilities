# https://blog.mbedded.ninja/mathematics/geometry/spherical-geometry/finding-the-intersection-of-two-arcs-that-lie-on-a-sphere/


import numpy as np
from pygplates.pygplates import LatLonPoint


def is_point_on_arc(point: np.ndarray, arc_start: np.ndarray, arc_end: np.ndarray, epsilon=0.001) -> bool:
    start_dot = np.dot(arc_start, point)/(np.linalg.norm(arc_start) * np.linalg.norm(point))
    end_dot = np.dot(arc_end, point)/(np.linalg.norm(arc_end) * np.linalg.norm(point))
    if start_dot == 1.0 or end_dot == 1.0:
      return True
    
    start_end_dot = np.dot(arc_start, arc_end)/(np.linalg.norm(arc_start) * np.linalg.norm(arc_end))
    if start_end_dot == 0.0:
      return False
    
    theta_start_point = np.arccos(start_dot)
    theta_end_point = np.arccos(end_dot)
    theta_start_end = np.arccos(start_end_dot)

    return (abs(theta_start_point + theta_end_point - theta_start_end) < epsilon)

def debug_point_on_arc(point: np.ndarray, arc_start: np.ndarray, arc_end: np.ndarray, epsilon=0.001) -> bool:
    start_dot = np.dot(arc_start, point)/(np.linalg.norm(arc_start) * np.linalg.norm(point))
    end_dot = np.dot(arc_end, point)/(np.linalg.norm(arc_end) * np.linalg.norm(point))
    print(f'start_dot: {start_dot} end_dot: {end_dot}')
    if start_dot == 1.0 or end_dot == 1.0:
      return True
    
    start_end_dot = np.dot(arc_start, arc_end)/(np.linalg.norm(arc_start) * np.linalg.norm(arc_end))
    print(f'start_end_dot: {start_end_dot}')
    if start_end_dot == 0.0:
      return False
    
    theta_start_point = np.arccos(start_dot)
    theta_end_point = np.arccos(end_dot)
    theta_start_end = np.arccos(start_end_dot)
    print(f'theta_start_point: {theta_start_point} theta_end_point: {theta_end_point} theta_start_end: {theta_start_end} test: {(abs(theta_start_point + theta_end_point - theta_start_end) < epsilon)} {abs(theta_start_point + theta_end_point - theta_start_end)} < {epsilon}')

def get_arc_intersection(a1: LatLonPoint, a2: LatLonPoint, b1: LatLonPoint, b2: LatLonPoint) -> LatLonPoint | None:
    a1_lat = np.radians(a1.get_latitude()); a1_lon = np.radians(a1.get_longitude())
    a2_lat = np.radians(a2.get_latitude()); a2_lon = np.radians(a2.get_longitude())
    b1_lat = np.radians(b1.get_latitude()); b1_lon = np.radians(b1.get_longitude())
    b2_lat = np.radians(b2.get_latitude()); b2_lon = np.radians(b2.get_longitude())

    
    P_a1 = np.array([
        np.cos(a1_lat) * np.cos(a1_lon),
        np.cos(a1_lat) * np.sin(a1_lon),
        np.sin(a1_lat)
        ])
    
    P_a2 = np.array([
        np.cos(a2_lat) * np.cos(a2_lon),
        np.cos(a2_lat) * np.sin(a2_lon),
        np.sin(a2_lat)
        ])
    
    P_b1 = np.array([
        np.cos(b1_lat) * np.cos(b1_lon),
        np.cos(b1_lat) * np.sin(b1_lon),
        np.sin(b1_lat)
        ])
    
    P_b2 = np.array([
        np.cos(b2_lat) * np.cos(b2_lon),
        np.cos(b2_lat) * np.sin(b2_lon),
        np.sin(b2_lat)
        ])
    
    # Calculate Cross-Products
    N1 = np.cross(P_a1, P_a2)
    N2 = np.cross(P_b1, P_b2)

    # Calculate the Cross-Product of the Cross-Products
    L = np.cross(N1, N2)

    # Get intersection points
    I1 = L / np.linalg.norm(L)
    I2 = -I1
    
    I1_on_A = is_point_on_arc(I1, P_a1, P_a2)
    I1_on_B = is_point_on_arc(I1, P_b1, P_b2)

    I2_on_A = is_point_on_arc(I2, P_a1, P_a2)
    I2_on_B = is_point_on_arc(I2, P_b1, P_b2)

    if I1_on_A and I1_on_B:
        lat = np.arcsin(I1[2])
        lon = np.atan2(I1[1], I1[0])
        return LatLonPoint(np.degrees(lat), np.degrees(lon))
    elif I2_on_A and I2_on_B:
        lat = np.arcsin(I2[2])
        lon = np.atan2(I2[1], I2[0])
        return LatLonPoint(np.degrees(lat), np.degrees(lon))
    else:
        return None