# Port of https:#github.com/Formlabs/hackathon-slicer/blob/master/app/js/viewport.js
#
# Windows Error 'glutInit undefined': If glutInit not found we must use pygame

#external
import OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GL.shaders import *
'''Import the PyOpenGL convenience wrappers for the FrameBufferObject
extension(s) we're going to use.  (Requires PyOpenGL 3.0.1b2 or above).'''
from OpenGL.GL.framebufferobjects import *
import numpy
import math
import cv2

#Test if glutInit available, if not we want to use pygame
#Even if bool(glutInit) wil return True the call on glutInit might still fail
glutAvailable=False #True
try:
    glutInit()
except Exception:
    glutAvailable=False
if not glutAvailable:
    #print ("GLUT is not available.")
    try:
        import contextlib
        with contextlib.redirect_stdout(None):
            import pygame
    except ImportError:
        print ("Install pygame to use GPU slicing.")
        sys.exit()

########################################

class Printer:
    resolution = {"x": 1440, "y": 2560};
    width_mm = 1440*0.047;#25.4 * 3;

    def aspectRatio(self):
        return self.resolution['x'] / self.resolution['y']

    def pixels(self):
        return self.resolution['x'] * self.resolution['y']

    # Returns a scale ratio of OpenGL units per mm
    def getGLscale(self):
        return 2 * self.aspectRatio() / self.width_mm;

class Mat4:
    #https://open.gl/transformations
    #http://headerphile.com/uncategorized/opengl-matrix-operations/
    @staticmethod
    def Create():
        R4x4I=numpy.identity(4,dtype=numpy.float32)
        R4x4=R4x4I.transpose()
        R=R4x4.flatten()
        return R

    @staticmethod
    def Mul(M,N):
        # M is 4x4 matrix as 1 dimensional 16 long vector row after row
        # N is 4x4 matrix as 1 dimensional 16 long vector row after row
        M4x4=M.reshape([4,4])
        N4x4=N.reshape([4,4])
        M4x4I=M4x4.transpose()
        N4x4I=N4x4.transpose()
        R4x4I=numpy.dot(M4x4I,N4x4I)
        R4x4=R4x4I.transpose()
        R=R4x4.flatten()
        return R

    @staticmethod
    def MulV4(M,V):
        # M is 4x4 matrix as 1 dimensional 16 long vector row after row
        # V is 1-dim vector of length 4
        M4x4=M.reshape([4,4])
        M4x4I=M4x4.transpose()
        R4x4I=numpy.dot(M4x4I,V)
        return R4x4I

    @staticmethod
    def MulV3(M,V):
        V4=numpy.append(V,1)
        #print ("V4",V4)
        return (Mat4.MulV4(M,V4))

    @staticmethod
    def MulV3s(M,Vs):
        # M is 4x4 matrix as 1 dimensional 16 long vector row after row
        # Vs is nx3 matrix of 1-dim vectors of length 3
        #        points3n=self.mesh['verts']

        nrVs=Vs.shape[0]
        Vnx4=numpy.append(Vs,numpy.ones((nrVs,1)),axis=-1)

        Vnx4I=Vnx4.transpose()
        M4x4=M.reshape([4,4])
        M4x4I=M4x4.transpose()
        R4xnI=numpy.dot(M4x4I,Vnx4I)
        R4xn=R4xnI.transpose()
        R3xn=R4xn[:,:-1]
        return (R3xn)

    @staticmethod
    def Scale(M,V):
        # M is 4x4 matrix as 1 dimensional 16 long vector row after row
        # V should be 3 vector
        M4x4=M.reshape(4,4)
        M4x4I=M4x4.transpose()
        V4=numpy.append(V,1)
        R4x4I=M4x4I*V4
        R4x4=R4x4I.transpose()
        R=R4x4.flatten()
        return R

    @staticmethod
    def Translate(M,V):
        # M is 4x4 matrix as 1 dimensional 16 long vector row after row
        # V should be 3 vector
        N=M.copy()
        x,y,z=V[0],V[1],V[2]
        N[12] = M[0] * x + M[4] * y + M[8] * z + M[12]
        N[13] = M[1] * x + M[5] * y + M[9] * z + M[13]
        N[14] = M[2] * x + M[6] * y + M[10] * z + M[14]
        N[15] = M[3] * x + M[7] * y + M[11] * z + M[15]
        return N

    @staticmethod
    def Rotate_old(M,theta,axis):
        # This one does not to seem work correctly with axis=2 (Z)
        # axis:  0: x, 1: y,  2: z
        # theta in radians
        s=math.sin(theta)
        c=math.cos(theta)
        if axis==0:
            O=numpy.array([1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1])
        elif axis==1:
            O=numpy.array([c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1])
        elif axis==2:
            O=numpy.array([c,-s,0,0,s,c,0,0,0,0,1,0,0,0,0,1])
        else:
            return
        O4x4=O.reshape([4,4])
        O4x4I=O4x4.transpose()

        M4x4=M.reshape([4,4])
        M4x4I=M4x4.transpose()


        R4x4I=numpy.dot(M4x4I,O4x4I)
        R4x4=R4x4I.transpose()
        R=R4x4.flatten()
        return R
    @staticmethod
    def Rotate(M,theta,axis):
        # See hackathon-slicer-master/node_modules/gl-matrix/src/gl-matrix/mat4.js
        # axis:  0: x, 1: y,  2: z
        # theta in radians
        s=math.sin(theta)
        c=math.cos(theta)
        out=M.copy().astype(numpy.float32)
        if axis==0:
            a10 = M[4];
            a11 = M[5];
            a12 = M[6];
            a13 = M[7];
            a20 = M[8];
            a21 = M[9];
            a22 = M[10];
            a23 = M[11];
            out[4] = a10 * c + a20 * s;
            out[5] = a11 * c + a21 * s;
            out[6] = a12 * c + a22 * s;
            out[7] = a13 * c + a23 * s;
            out[8] = a20 * c - a10 * s;
            out[9] = a21 * c - a11 * s;
            out[10] = a22 * c - a12 * s;
            out[11] = a23 * c - a13 * s;
            return out
        elif axis==1:
            a00 = M[0];
            a01 = M[1];
            a02 = M[2];
            a03 = M[3];
            a20 = M[8];
            a21 = M[9];
            a22 = M[10];
            a23 = M[11];
            out[0] = a00 * c - a20 * s;
            out[1] = a01 * c - a21 * s;
            out[2] = a02 * c - a22 * s;
            out[3] = a03 * c - a23 * s;
            out[8] = a00 * s + a20 * c;
            out[9] = a01 * s + a21 * c;
            out[10] = a02 * s + a22 * c;
            out[11] = a03 * s + a23 * c;
            return out;
        elif axis==2:
            a00 = M[0]
            a01 = M[1]
            a02 = M[2]
            a03 = M[3]
            a10 = M[4]
            a11 = M[5]
            a12 = M[6]
            a13 = M[7]
            out[0] = a00 * c + a10 * s
            out[1] = a01 * c + a11 * s
            out[2] = a02 * c + a12 * s
            out[3] = a03 * c + a13 * s
            out[4] = a10 * c - a00 * s
            out[5] = a11 * c - a01 * s
            out[6] = a12 * c - a02 * s
            out[7] = a13 * c - a03 * s
            return out

    @staticmethod
    def RotateX(M,theta):
        return Mat4.Rotate(M,theta,0)
    @staticmethod
    def RotateY(M,theta):
        return Mat4.Rotate(M,theta,1)
    @staticmethod
    def RotateZ(M,theta):
        return Mat4.Rotate(M,theta,2)

    @staticmethod
    def test():
        M=numpy.array([0,1,2,3, 4,5,6,7, 8,9,10,11, 12,13,14,15])
        V=numpy.array([1,2,3])
        V4=numpy.array([4,5,6,1])
        VW=numpy.array([[1,2,3],[4,5,6]])
        N=numpy.array([0,10,20,30, 40,50,60,70, 80,90,100,110, 120,130,140,150])
        print("Mat4.Create",Mat4.Create())
        print("Mat4.Translate",Mat4.Translate(M,V))
        print("Mat4.Scale",Mat4.Scale(M,V))
        print("Mat4.MulV3",Mat4.MulV3(M,V))
        print("Mat4.MulV4",Mat4.MulV4(M,V4))
        print("VW",VW)
        print("Mat4.MulV3s",Mat4.MulV3s(M,VW))
        print("Mat4.RotateX",Mat4.RotateX(M,10))
        print("Mat4.RotateY",Mat4.RotateY(M,10))
        print("Mat4.RotateZ",Mat4.RotateZ(M,10))
        quit()
#Mat4.test()

class Viewport:
    printer=None
    quad = None
    base = None
    slice=None
    # Model object
    mesh = {"loaded": False}
    # window=None
    windowsize=(500,500)#(256*3,144*3)
    glutAvailable=False

    def __init__(self):
        # Get path of script/exe for local resources like iconpath and newfile.photon
        if getattr(sys, 'frozen', False):# frozen
            self.installpath = os.path.dirname(sys.executable)
        else: # unfrozen
            self.installpath = os.path.dirname(os.path.realpath(__file__))

        global glutAvailable
        # init printer specs
        self.printer=Printer()

        if glutAvailable:
            self.init_glut()
        else:
            self.init_pygame()

        # Some things that where global in npm javascript version
        self.quad=self.makeQuad()
        self.base=self.makeBase()
        self.scene={"roll": 45+math.pi/2, "pitch": 45}
        self.slice=self.makeSlice()
        self.mesh = {"loaded": False}
        glEnable(GL_DEPTH_TEST)
        self.draw()

    def init_glut(self):
        glutInit()#sys.argv)
        #glutInitContextVersion( 3, 2 )

        # Create a double-buffer RGBA window.   (Single-buffering is possible.
        # So is creating an index-mode window.)
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)

        # Create a window, setting its title
        # https://noobtuts.com/python/opengl-introduction
        glutInitWindowSize(self.windowsize[0],self.windowsize[1])
        glutInitWindowPosition(0,0)
        # self.window=
        self.glutWindowID=glutCreateWindow('python port of hackathon-slicer')

        # Set the display callback.  You can set other callbacks for keyboard and
        # mouse events.
        glutDisplayFunc(self.draw)
        #glutIdleFunc(self.draw)

    def init_pygame(self):
        import os
        os.environ['SDL_VIDEO_WINDOW_POS'] ="0,40" # coord is postion of inner drawing surface, so leave room for window bar
        pygame.display.set_mode(self.windowsize, pygame.DOUBLEBUF | pygame.OPENGL | pygame.OPENGLBLIT)
        pygame.display.set_caption('python port of hackathon-slicer')

        icon = pygame.image.load(os.path.join(self.installpath,'PhotonSlicer.gif'))
        pygame.display.set_icon(icon)

    def display(self):
        glutMainLoop()
        return

    def destroy(self):
        if glutAvailable:
            glutDestroyWindow(self.glutWindowID)
        else:
            pygame.quit()

    def buildShader(self,txt, type):
        #print ("buildShader",txt,type)
        s = glCreateShader(type)
        glShaderSource(s, txt)
        glCompileShader(s)

        #if (not glGetShaderParameter(s, GL_COMPILE_STATUS)):
        if (not glGetShaderiv(s, GL_COMPILE_STATUS)):
            raise RuntimeError ("Could not compile shader:" , glGetShaderInfoLog(s))
        return s

    def setUniforms(self,prog,modelvar,names):
        modelvar['uniform'] = {}
        for u in names:
            modelvar['uniform'][u] = glGetUniformLocation(prog, u)
        return modelvar

    def setAttribs(self,prog, modelvar,names):
        modelvar['attrib'] = {}
        for attrib in names:
            modelvar['attrib'][attrib]=glGetAttribLocation(prog,attrib)
        return modelvar

    def makeProgram(self,modelvar,vert, frag, uniforms, attribs):
        v = self.buildShader(vert, GL_VERTEX_SHADER)
        f = self.buildShader(frag, GL_FRAGMENT_SHADER)

        prog = glCreateProgram()
        glAttachShader(prog, v)
        glAttachShader(prog, f)
        glLinkProgram(prog)
        #if (not glGetProgramParameter(prog, GL_LINK_STATUS)):
        if (not glGetProgramiv(prog, GL_LINK_STATUS)):
            raise RuntimeError("Could not link program:" + glGetProgramInfoLog(prog))

        self.setUniforms(prog, modelvar, uniforms)
        self.setAttribs(prog, modelvar, attribs)

        return prog


    def viewMatrix(self):
        # We assume there is no rotation, because this port has no userinterface
        v = Mat4.Create()
        v = Mat4.Scale(v,numpy.array([1, 1, 0.5]))
        v = Mat4.RotateX(v, self.scene['pitch'])
        v = Mat4.RotateZ(v, self.scene['roll'])
        v = Mat4.Scale(v, numpy.array([1, 1, -1]))
        #v = Mat4.Scale(v, numpy.array([0.5, 0.5, -0.5]))
        return v


    def modelMatrix(self):
        # We assume there is no rotation, because this port has no userinterface
        m = Mat4.Create() #Creates a new identity mat4
        m = Mat4.RotateZ(m, self.mesh['roll'])
        m = Mat4.RotateX(m, self.mesh['pitch'])
        m = Mat4.RotateY(m, self.mesh['yaw'])

        out = Mat4.Create()
        out = Mat4.Mul(m, self.mesh['M'])
        return out


    def drawMesh(self,mesh):
        glUseProgram(self.mesh['prog'])

        glUniformMatrix4fv(self.mesh['uniform']['view'], 1, False, self.viewMatrix())
        glUniformMatrix4fv(self.mesh['uniform']['model'], 1, False, self.modelMatrix())

        glBindBuffer(GL_ARRAY_BUFFER, self.mesh['vert'])
        glEnableVertexAttribArray(self.mesh['attrib']['v'])
        glVertexAttribPointer(self.mesh['attrib']['v'], 3, GL_FLOAT, False, 0, None)

        glBindBuffer(GL_ARRAY_BUFFER, self.mesh['norm'])
        glEnableVertexAttribArray(self.mesh['attrib']['n'])
        glVertexAttribPointer(mesh['attrib']['n'], 3, GL_FLOAT, False, 0, None)

        glDrawArrays(GL_TRIANGLES, 0, self.mesh['triangles'])
        #print ("drawMesh")

    def drawBase(self,base):
        glEnable(GL_CULL_FACE)
        glCullFace(GL_FRONT)
        glUseProgram(self.base['prog'])
        glUniformMatrix4fv(self.base['uniform']['view'], 1, False, self.viewMatrix())
        if (self.mesh['loaded']):
            glUniform1f(self.base['uniform']['zmin'], self.mesh['bounds']['zmin'])
        else:
            glUniform1f(self.base['uniform']['zmin'], 0)
        glUniform1f(self.base['uniform']['aspect'], self.printer.aspectRatio())

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glBindBuffer(GL_ARRAY_BUFFER, self.base['vert'])
        glEnableVertexAttribArray(self.base['attrib']['v'])
        glVertexAttribPointer(self.base['attrib']['v'], 2, GL_FLOAT, False, 0, None)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_CULL_FACE)


    def drawQuad(self,quad):
        # Draws slice
        glUseProgram(quad['prog'])

        glDisable(GL_DEPTH_TEST)
        glUniformMatrix4fv(self.quad['uniform']['view'], 1, False, self.viewMatrix())

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D,self.slice['tex'])
        glUniform1i(self.quad['uniform']['tex'], 0)

        glBindBuffer(GL_ARRAY_BUFFER, self.quad['vert'])
        glEnableVertexAttribArray(self.quad['attrib']['v'])
        glVertexAttribPointer(self.quad['attrib']['v'], 2, GL_FLOAT, False, 0, None)

        glUniform1f(self.quad['uniform']['frac'], self.quad['frac'])
        glUniform1f(self.quad['uniform']['aspect'], self.printer.aspectRatio())
        glUniform2f(self.quad['uniform']['bounds'], self.mesh['bounds']['zmin'], self.mesh['bounds']['zmax'])

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glBindTexture(GL_TEXTURE_2D, 0)
        glEnable(GL_DEPTH_TEST)


    def draw(self):
        if self.glutAvailable:
            self.draw_glut()
        else:
            self.draw_pygame()

    def draw_glut(self):
        glClearColor(1, 1, 1, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # clear the screen

        self.drawBase(self.base)

        if (self.mesh['loaded']):
            self.drawMesh(self.mesh)
            self.drawQuad(self.quad)
            pass
        glutSwapBuffers()

    def draw_pygame(self):
        glClearColor(1, 1, 1, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # clear the screen
        self.drawBase(self.base)

        if (self.mesh['loaded']):
            self.drawMesh(self.mesh)
            self.drawQuad(self.quad)

        pygame.display.flip()
        pygame.event.pump()

    def makeQuad(self):
        quad = {}
        quad['prog'] = self.makeProgram(
            quad,
            open(os.path.join(self.installpath,'quad.vert'),'r').read(),
            open(os.path.join(self.installpath,'quad.frag'),'r').read(),
            ['view','tex','frac','aspect','bounds'], ['v'])

        quad['vert'] =  glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, quad['vert'])
        glBufferData(
            GL_ARRAY_BUFFER,
            numpy.array([-1, -1,
                         -1,  1,
                          1, -1,
                          1,  1],dtype=numpy.float32),
            GL_STATIC_DRAW)

        quad['frac'] = 0.5
        return quad


    def makeBase(self):
        base = {}
        base['prog'] = self.makeProgram(
            base,
            open(os.path.join(self.installpath,'base.vert')).read(),
            open(os.path.join(self.installpath,'base.frag')).read(),
            ['view', 'zmin', 'aspect'], ['v'])

        base['vert'] = glGenBuffers(1) #createBuffer()
        glBindBuffer(GL_ARRAY_BUFFER, base['vert'])
        glBufferData(
            GL_ARRAY_BUFFER,
            numpy.array([-1, -1,
                         -1,  1,
                          1, -1,
                          1,  1],dtype=numpy.float32),
            GL_STATIC_DRAW)

        base['frac'] = 0.5
        return base


    def makeSlice(self):
        # all these create methods are WebGL specific
        slice ={"fbo": glGenFramebuffers(1),
                     "tex": glGenTextures(1),
                     "buf": glGenRenderbuffers(1)}

        slice['prog'] = self.makeProgram(
            slice,
            open(os.path.join(self.installpath,'slice.vert'),'r').read(),
            open(os.path.join(self.installpath,'slice.frag'),'r').read(),
            ['model','bounds','frac','aspect'], ['v'])

        glBindTexture(GL_TEXTURE_2D, slice['tex'])
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                      self.printer.resolution['x'],self.printer.resolution['y'],
                      0, GL_RGBA, GL_UNSIGNED_BYTE, None) #null

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        glBindTexture(GL_TEXTURE_2D, 0)#null
        return slice


    def getMeshBounds(self):
        M = self.modelMatrix()

        points=self.mesh['verts']
        out=Mat4.MulV3s(M,points)
        x = out[:, 0]
        y = out[:, 1]
        z = out[:, 2]
        cmin = (x.min(), y.min(), z.min())
        cmax = (x.max(), y.max(), z.max())

        self.mesh['bounds'] = {}
        self.mesh['bounds']['xmin'] = cmin[0]
        self.mesh['bounds']['xmax'] = cmax[0]

        self.mesh['bounds']['ymin'] = cmin[1]
        self.mesh['bounds']['ymax'] = cmax[1]

        self.mesh['bounds']['zmin'] = cmin[2]
        self.mesh['bounds']['zmax'] = cmax[2]


    def updateScale(self):
        # Create identity transform matrix
        self.mesh['M'] = Mat4.Create()

        # Find bounds and center, then store them in matrix M
        self.getMeshBounds()

        scale = self.printer.getGLscale()

        # Store mesh transform matrix
        self.mesh['M'] = Mat4.Create()
        self.mesh['M'] = Mat4.Scale(self.mesh['M'], numpy.array([scale, scale, scale]))

        Mat4.Translate(self.mesh['M'], numpy.array([
            -(self.mesh['bounds']['xmin'] + self.mesh['bounds']['xmax']) / 2,
            -(self.mesh['bounds']['ymin'] + self.mesh['bounds']['ymax']) / 2,
            -(self.mesh['bounds']['zmin'] + self.mesh['bounds']['zmax']) / 2]))

        #print ("mesh['M']",self.mesh["M"])
        # Recalculate mesh bounds with the transform matrix
        self.getMeshBounds()


    def loadMesh(self,points,normals,cmin,cmax):
        # https://www.opengl.org/discussion_boards/showthread.php/183305-How-to-use-glDrawArrays%28%29-with-VBO-Vertex-Buffer-Object-to-display-stl-geometry
        # points = [ [x,y,z], [a,b,c],....]

        # Store model min and max bounds
        self.mesh['bounds']={}
        #print ("cmin",cmin)
        #print ("cmax",cmax)
        self.mesh['bounds']['xmin_orig']=cmin[0]
        self.mesh['bounds']['ymin_orig']=cmin[1]
        self.mesh['bounds']['zmin_orig']=cmin[2]
        self.mesh['bounds']['xmax_orig']=cmax[0]
        self.mesh['bounds']['ymax_orig']=cmax[1]
        self.mesh['bounds']['zmax_orig']=cmax[2]


        # Reset pitch and roll
        self.mesh['roll'] = 0
        self.mesh['pitch'] = 0
        self.mesh['yaw'] = 0
        # Compile shader program for mesh
        self.mesh['prog'] = self.makeProgram(
            self.mesh,
            open(os.path.join(self.installpath,'mesh.vert'),'r').read(),
            open(os.path.join(self.installpath,'mesh.frag'),'r').read(),
            ['view', 'model'], ['v', 'n'])

        # Store unique vertices
        self.mesh['verts'] = points

        # Store mesh's convex hull (as indices into vertex list)
        # only used to calc mesh bounds

        # Work out mesh scale
        self.updateScale()

        # Load vertex positions into a buffer
        #oints zijn nog niet goed...
        points_flattened = numpy.array(points.flatten(),dtype=numpy.float32)#_.flatten(stl.positions);
        self.mesh['vert'] = glGenBuffers(1)#gl.createBuffer();
        glBindBuffer(GL_ARRAY_BUFFER, self.mesh['vert'])
        glBufferData(
            GL_ARRAY_BUFFER,
            points_flattened.nbytes,
            points_flattened,
            GL_STATIC_DRAW)

        # Load normals into a second buffer
        # normals has a vector for each tri and not for each point!
        normalsPerPoint=numpy.repeat(normals,3,0)
        normals_flattened = numpy.array(normalsPerPoint.flatten(),dtype=numpy.float32)
        self.mesh['norm'] = glGenBuffers(1);
        glBindBuffer(GL_ARRAY_BUFFER, self.mesh['norm']);
        glBufferData(
            GL_ARRAY_BUFFER,
            normals_flattened.nbytes,
            numpy.array(normals_flattened,dtype=numpy.float32),
            GL_STATIC_DRAW)

        # Store the number of triangles
        self.mesh['triangles'] = len(points)#stl.positions.length;

        # Get bounds with new transform matrix applied
        self.mesh['loaded'] = True

        #print ("loaded mesh")
        self.renderSlice()


    def renderSlice(self):
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glViewport(0, 0, self.printer.resolution['x'],self.printer.resolution['y'])#printer.resolution.x, printer.resolution.y)

        # Bind the target framebuffer
        sliceFbo = self.slice['fbo'] #glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, sliceFbo)
        #glBindBuffer(GL_ARRAY_BUFFER, self.modelPtBufferIdx)

        # Attach our output texture
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
            GL_TEXTURE_2D, self.slice['tex'], 0)

        # Bind the renderbuffer to get a stencil buffer
        glBindRenderbuffer(GL_RENDERBUFFER, self.slice['buf'])
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_STENCIL,
                               self.printer.resolution['x'],self.printer.resolution['y'])
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
                                   GL_RENDERBUFFER, self.slice['buf'])

        # Clear texture
        glClearColor(0, 0, 0, 0)
        glClearStencil(0)
        glClear(GL_COLOR_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

        glUseProgram(self.slice['prog'])

        # Load model matrix
        glUniformMatrix4fv(self.slice['uniform']['model'],1, False, self.modelMatrix())

        # Load slice position and mesh bounds
        glUniform1f(self.slice['uniform']['frac'],
                    self.quad['frac'])
        glUniform1f(self.slice['uniform']['aspect'],
                    self.printer.aspectRatio())
        glUniform2f(self.slice['uniform']['bounds'],
                    self.mesh['bounds']['zmin'],
                    self.mesh['bounds']['zmax'])

        # Load mesh vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.mesh['vert'])
        glEnableVertexAttribArray(self.mesh['attrib']['v'])
        glVertexAttribPointer(self.mesh['attrib']['v'], 3, GL_FLOAT, False, 0, None)

        # Draw twice, adding and subtracting values in the stencil buffer
        # based on the handedness of faces that we encounter
        glStencilFunc(GL_ALWAYS, 0, 0xFF)
        glStencilOpSeparate(GL_BACK,  GL_KEEP, GL_KEEP, GL_INCR)
        glStencilOpSeparate(GL_FRONT, GL_KEEP, GL_KEEP, GL_KEEP)
        glDrawArrays(GL_TRIANGLES, 0, self.mesh['triangles'])

        glStencilOpSeparate(GL_BACK,  GL_KEEP, GL_KEEP, GL_KEEP)
        glStencilOpSeparate(GL_FRONT, GL_KEEP, GL_KEEP, GL_DECR)
        glDrawArrays(GL_TRIANGLES, 0, self.mesh['triangles'])

        # Clear the color bit in preparation for a redraw
        glClear(GL_COLOR_BUFFER_BIT)

        # Draw again, discarding samples if the stencil buffer != 0
        glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)#, GL_KEEP)
        glStencilFunc(GL_NOTEQUAL, 0, 0xFF)
        glDrawArrays(GL_TRIANGLES, 0, self.mesh['triangles'])

        # Load the data from the framebuffer
        data=numpy.empty([self.printer.pixels()*4],dtype=numpy.uint8) #data = new Uint8Array(printer.pixels() * 4)
        glReadPixels(0, 0,
                      self.printer.resolution['x'], self.printer.resolution['y'],
                      GL_RGBA,
                      GL_UNSIGNED_BYTE, data)

        # Restore the default framebuffer
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_STENCIL_TEST)

        glViewport(0, 0, self.windowsize[0],self.windowsize[1])

        return data

    def getSliceAt(self,frac):
        self.quad['frac'] = frac
        #print ("getSliceAt:", frac)
        #document.getElementById("slider").valueAsNumber = frac * 100
        self.draw()
        return self.renderSlice()

    def getBounds(self):
        return self.mesh['bounds']

    def hasModel(self):
        return self.mesh['loaded']
