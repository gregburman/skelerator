import numpy as np
from skimage.segmentation import mark_boundaries, find_boundaries
from scipy.ndimage.filters import gaussian_filter
from skelerator import Tree, Skeleton
from mahotas import cwatershed
import h5py
from scipy.ndimage.morphology import distance_transform_edt
from scipy.ndimage.filters import maximum_filter
import matplotlib.pyplot as plt
import pickle
import pdb

def create_segmentation(shape, n_objects, points_per_skeleton, interpolation, smoothness, write_to=None):
    """
    Creates a toy segmentation containing skeletons.

    Args:

    shape: Size of the desired dataset
    
    n_objects: The number of skeleton/neurons to generate in the given volume

    points_per_skeleton: The number of potential branch points that are sampled per skeleton. 
                         Higher numbers lead to more complex shapes.

    interpolation: Method of interpolation between two sample points. Can be either linear or
                   random (constrained random walk).

    smoothness: Controls the smoothness of the initial noise map used to generate object boundaries.
    """
    shape = np.array(shape)
    if len(shape) != 3:
        raise ValueError("Provide 3D shape.")

    if np.any(shape % 2 != 0):
        raise ValueError("All shape dimensions have to be even.")

    noise = np.abs(np.random.randn(*shape))
    smoothed_noise = gaussian_filter(noise, sigma=smoothness)
    
    # Sample one tree for each object and generate its skeleton:
    seeds = np.zeros(2*shape, dtype=int)
    for i in range(n_objects):
        """
        We make the virtual volume twice as large to avoid border effects. To keep the density
        of points the same we also increase the number of points by a factor of 8 = 2**3. Such that
        on average we keep the same number of points per unit volume.
        """
        points = np.stack([np.random.randint(0, 2*shape[dim], (2**3)*points_per_skeleton) for dim in range(3)], axis=1)
        tree = Tree(points)
        skeleton = Skeleton(tree, [1,1,1], "linear")
        seeds = skeleton.draw(seeds, np.array([0,0,0]), i + 1)

   
    """
    Cut the volume to original size.
    """
    seeds = seeds[int(shape[0]/2):int(3*shape[0]/2), int(shape[1]/2):int(3*shape[1]/2), int(shape[2]/2):int(3*shape[2]/2)]

    """
    We generate an artificial segmentation by first filtering
    skeleton points that are too close to each other via a non max supression
    to avoid artifacts. A distance transform of the skeletons plus smoothed noise
    is then used to calculate a watershed transformation with the skeletons as seeds
    resulting in the final segmentation.
    """
    seeds[maximum_filter(seeds, size=4) != seeds] = 0
    seeds_dt = distance_transform_edt(seeds==0) + 5. * smoothed_noise
    segmentation = cwatershed(seeds_dt, seeds)
    boundaries = find_boundaries(segmentation)

    if write_to is not None:
        f = h5py.File(write_to, "w")
        f.create_dataset("segmentation", data=segmentation.astype(np.uint64))
        f.create_dataset("skeletons", data=seeds.astype(np.uint64))
        f.create_dataset("boundaries", data=boundaries.astype(np.uint64))
        f.create_dataset("smoothed_noise", data=smoothed_noise)
        f.create_dataset("distance_transform", data=seeds_dt)

    data = {"segmentation": segmentation, "skeletons": seeds, "raw": boundaries}
    pickle.dumps(data)
    return data
    #return segmentation, seeds, boundaries, noise, smoothed_noise, seeds_dt

if __name__ == "__main__":
    shape = np.array([100,100,100])
    n_objects = 20
    points_per_skeleton = 5
    smoothness = 2
    write_to = "./test_segmentation.h5"
    interpolation = "linear"
    data = create_segmentation(shape, n_objects, points_per_skeleton, interpolation , smoothness, write_to=write_to)
    #get_raw(segmentation)
