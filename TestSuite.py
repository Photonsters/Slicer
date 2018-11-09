from Stl2Slices import *


def test_triInSlice(self):
    # points for upright tri
    p0 = (0, 0, 0)
    p1 = (0, 1, 1)
    p2 = (0, 0, 2)
    # points for upside down tri
    q0 = (0, 1, 0)
    q1 = (0, 0, 1)
    q2 = (0, 1, 2)

    # All Above
    yBottom = -2
    yTop = -1
    print("(1) All Above  : ", self.triInSlice(p0, p1, p2, yBottom, yTop))

    # All Below
    yBottom = 2
    yTop = 3
    print("(2) All Below  : ", self.triInSlice(p0, p1, p2, yBottom, yTop))

    # All Inside
    yBottom = -1
    yTop = 3
    print("(3) All Between: ", self.triInSlice(p0, p1, p2, yBottom, yTop))

    # 1 Above
    yBottom = 0
    yTop = 0.9
    print("(4) 1 Above: ", self.triInSlice(p0, p1, p2, yBottom, yTop))

    # 2 Above
    yBottom = 0
    yTop = 0.9
    print("(5) 2 Above: ", self.triInSlice(q0, q1, q2, yBottom, yTop))

    # 2 Below
    yBottom = 0.1
    yTop = 2
    print("(6) 2 Below: ", self.triInSlice(p0, p1, p2, yBottom, yTop))

    # 1 Below
    yBottom = 0.1
    yTop = 2
    print("(7) 1 Below: ", self.triInSlice(q0, q1, q2, yBottom, yTop))

    # 1 Above, 2 Below
    yBottom = 0.1
    yTop = 0.9
    print("(8) 1 Above, 2 Below: ", self.triInSlice(p0, p1, p2, yBottom, yTop))

    # 2 Above, 1 Below
    yBottom = 0.1
    yTop = 0.9
    print("(9) 2 Above, 1 Below: ", self.triInSlice(q0, q1, q2, yBottom, yTop))

    # 1 Below,1 Between, 1 Above
    yBottom = 0.1
    yTop = 0.9
    r0 = (0, 0.0, 0)
    r1 = (0, 0.5, 1)
    r2 = (0, 1.0, 0)
    print("(10) 1 Below, 1 Between, 1 Above: ", self.triInSlice(r0, r1, r2, yBottom, yTop))


#filename,sc = "STLs/pushing_elephant.stl"
#filename,sc = "STLs/ELEPHANT.stl",1
filename,sc = "STLs/pikachu_repaired.STL",1
#filename,sc = "STLs/bunny.stl",0.5
#filename = "STLs/Cube.stl"


s2p=Stl2Slices(stlfilename=filename,scale=sc,photonfilename="pikachu.photon")
#Pickachu_repaired, layerHeight 25:
# 13 secs encoded
# 9 secs saved


#s2p.test_triInSlice()
#quit()