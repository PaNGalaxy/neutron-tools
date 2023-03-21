import pyfracgen as pf
from matplotlib import pyplot as plt
import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--option", type=str, required=True)
args = parser.parse_args()

xbound = (0.3602404434376143632361252444495 - 0.00000000000003,
          0.3602404434376143632361252444495 + 0.00000000000025)
ybound = (-0.6413130610648031748603750151793 - 0.00000000000006,
          -0.6413130610648031748603750151793 + 0.00000000000013)

if args.option == "mandelbrot":
    mymap = pf.images.stack_cmaps(plt.cm.gist_gray, 50)
    man = pf.mandelbrot(xbound, ybound, pf.updates.power, width=4, height=3, maxiter=5000, dpi=300)
    pf.images.image(man, cmap=mymap, gamma=0.8)
    plt.savefig("data.png")
elif args.option == "julia":
    c_vals = np.array([complex(i, 0.75) for i in np.linspace(0.05, 3.0, 100)])
    s = pf.julia_series(c_vals, (-1, 1), (-0.75, 1.25), pf.updates.magnetic_2, maxiter=100,
                        width=4, height=3, dpi=200)
    pf.images.save_animation(s, gamma=0.9, cmap=plt.cm.gist_ncar,
                             filename='data')
elif args.option == "random":
    basis = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    moves = pf.construct_moves(basis)
    M = pf.random_walk(moves, 5000000, width=4, height=3, depth=10, dpi=300,
                       tracking='temporal')
    pf.images.random_walk_image(M, cmap=plt.cm.gist_yarg, gamma=1.0)
    plt.savefig("data.png")
elif args.option == "markus":
    string = 'AAABA'
    xbound = (2.60, 4.0)
    ybound = (2.45, 4.0)
    im = pf.lyapunov(string, xbound, ybound, n_init=20, n_iter=80, dpi=300, width=4, height=3)
    pf.images.image(im, gamma=3.0, vert_exag=10000.0, cmap=plt.cm.gray)
    plt.savefig("data.png")
