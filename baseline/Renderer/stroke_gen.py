import cv2
import numpy as np
from scipy import interpolate

def normal(x, width):
    return (int)(x * (width - 1) + 0.5)

def spline3(x,y,point=360,deg=3):
    tck,u = interpolate.splprep([x,y],k=deg,s=0) 
    u = np.linspace(0,1,num=point,endpoint=True) 
    spline = interpolate.splev(u,tck)
    return spline[0],spline[1]

def draw(f, width=128):
    # 2*7 + 7 = 21
    # x0, y0, x1, y1, x2, y2, x3, y3, x4, y4, x5, y5, x6, y6, z0, z1, z2, z3, z4, z5, z6 = f
    pnum = 360
    xn = f[0:14:2]
    yn = f[1:14:2]
    zn = f[14:21]
    margin = int(pnum / (len(zn)-1))
    x, y = spline3(xn, yn, pnum)
    z = [0]*pnum
    for m in range(len(zn)-1):
        z[m*margin:(m+1)*margin] = np.linspace(zn[m],zn[m+1],num=margin,endpoint=True)
    canvas = np.zeros([width * 2, width * 2]).astype('float32')
    for i in range(pnum):
        fx = normal(x[i], width * 2)
        fy = normal(y[i], width * 2)
        fz = (int)(1 + z[i] * width // 3)
        cv2.circle(canvas, (fy, fx), fz, 1, -1)
    return 1 - cv2.resize(canvas, dsize=(width, width))
