"""Walking-line adjustments on unchanged authored floors and fall barriers."""
import copy,math

def walking_paths(paths):
    result=copy.deepcopy(paths)
    for route in result:
        if route['id']=='W02':
            route['points']=[[-12,-13.416],[-13.8,-16.6],[-14.7,-17.5],[-16,-18]]
    return result

def main_ring_path(samples=1440):
    points=[]
    for i in range(samples+1):
        angle=-math.pi+math.tau*i/samples
        delta=abs(math.degrees(angle)+58.5)
        radius=18 if delta>=12.5 else 18-math.cos(delta*math.pi/25)**2
        points.append([radius*math.cos(angle),radius*math.sin(angle)])
    return dict(id='MainRing',level='L2',width=1.0,points=points,
                note='Local inward walking-line detour around the R01 stair-side enclosure; slabs remain unchanged.')
