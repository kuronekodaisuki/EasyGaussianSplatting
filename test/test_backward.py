import matplotlib.pyplot as plt
import torch
import pygausplat as pg
import numpy as np
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from sh_coef import *
from backward_cpu import *


if __name__ == "__main__":
    gs_data = np.random.rand(4, 59)
    gs_data0 = np.array([[0.,  0.,  0.,  # xyz
                        1.,  0.,  0., 0.,  # rot
                        0.5,  0.5,  0.5,  # size
                        1.,
                        1.772484,  -1.772484,  1.772484],
                        [1.,  0.,  0.,
                        1.,  0.,  0., 0.,
                        2,  0.5,  0.5,
                        1.,
                        1.772484,  -1.772484, -1.772484],
                        [0.,  1.,  0.,
                        1.,  0.,  0., 0.,
                        0.5,  2,  0.5,
                        1.,
                        -1.772484, 1.772484, -1.772484],
                        [0.,  0.,  1.,
                        1.,  0.,  0., 0.,
                        0.5,  0.5,  2,
                        1.,
                        -1.772484, -1.772484,  1.772484]
                         ], dtype=np.float64)

    gs_data[:, :14] = gs_data0
    dtypes = [('pos', '<f8', (3,)),
              ('rot', '<f8', (4,)),
              ('scale', '<f8', (3,)),
              ('alpha', '<f8'),
              ('sh', '<f8', (48,))]
    gs = np.frombuffer(gs_data.tobytes(), dtype=dtypes)
    gs_num = gs.shape[0]

    # Camera info
    tcw = np.array([1.03796196, 0.42017467, 4.67804612])
    Rcw = np.array([[0.89699204,  0.06525223,  0.43720409],
                    [-0.04508268,  0.99739184, -0.05636552],
                    [-0.43974177,  0.03084909,  0.89759429]]).T
    twc = np.linalg.inv(Rcw) @ (-tcw)
    width = int(32)
    height = int(16)
    fx = 16
    fy = 16
    cx = width/2.
    cy = height/2.
    image_gt = np.zeros([height, width, 3])

    pws = gs['pos']
    gs_num = gs['pos'].shape[0]

    colors = np.zeros([gs_num, 3])
    us = np.zeros([gs_num, 2])
    pcs = np.zeros([gs_num, 3])
    cov3ds = np.zeros([gs_num, 6])
    cov2ds = np.zeros([gs_num, 3])
    dpc_dpws = np.zeros([gs_num, 3, 3])
    du_dpcs = np.zeros([gs_num, 2, 3])
    dcov3d_drots = np.zeros([gs_num, 6, 4])
    dcov3d_dscales = np.zeros([gs_num, 6, 3])
    dcov2d_dcov3ds = np.zeros([gs_num, 3, 6])
    dcov2d_dpcs = np.zeros([gs_num, 3, 3])
    dcolor_dshs = np.zeros([gs_num, 3, gs['sh'].shape[1]])
    dcolor_dpws = np.zeros([gs_num, 3, 3])
    for i in range(gs_num):
        pcs[i], dpc_dpws[i] = transform(pws[i], Rcw, tcw, True)
        us[i], du_dpcs[i] = project(pcs[i], fx, fy, cx, cy, True)
        cov3ds[i], dcov3d_drots[i], dcov3d_dscales[i] = compute_cov_3d(
            gs['rot'][i], gs['scale'][i], True)
        cov2ds[i], dcov2d_dcov3ds[i], dcov2d_dpcs[i] = compute_cov_2d(
            cov3ds[i], pcs[i], Rcw, fx, fy, True)
        colors[i], dcolor_dshs[i], dcolor_dpws[i] = sh2color(
            gs['sh'][i], pws[i], twc, True)

    pw_gpu = torch.from_numpy(gs['pos']).type(torch.float32).to('cuda')
    rot_gpu = torch.from_numpy(gs['rot']).type(torch.float32).to('cuda')
    scale_gpu = torch.from_numpy(gs['scale']).type(torch.float32).to('cuda')
    alpha_gpu = torch.from_numpy(gs['alpha']).type(torch.float32).to('cuda')
    sh_gpu = torch.from_numpy(gs['sh']).type(torch.float32).to('cuda')
    Rcw_gpu = torch.from_numpy(Rcw).type(torch.float32).to('cuda')
    tcw_gpu = torch.from_numpy(tcw).type(torch.float32).to('cuda')
    twc_gpu = torch.from_numpy(twc).type(torch.float32).to('cuda')

    color_gpu, dcolor_dshs_gpu, dcolor_dpws_gpu = pg.sh2Color(sh_gpu, pw_gpu, twc_gpu, True)
    print(np.max(np.abs(dcolor_dshs_gpu.cpu().numpy() - dcolor_dshs)))
    print(np.max(np.abs(dcolor_dpws_gpu.cpu().numpy() - dcolor_dpws)))