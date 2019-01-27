
""" USE CASE (Github #10 - RSilvers129)
    You have the slicer start with Windows 10 or and it watches a folder.
    You can use Netfabb, Asura, Meshmixer, B9, or some other program to lay out
    and add supports.
    You then save the STL into that folder that the slicer is monitoring.
    When it sees the file added, it pops up a GUI and you can pick layer height,
    exposure, and erode parameters. It then slices and makes a photon file, and
    then asks where to save that photon file with the GUI.
    This will do two things. One is that it will allow people to use any layout
    program and make Photon files. The other is that it will do the important
    erode function that only Formware has.
    Some nice features would be that the GUI should remember your previous
    settings at the very least, and even better if it has presets that you can
    configure and name and then just select one or add new presets.
"""


from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import sys
import os


class PhotonSlicerGui:
    args=None

    def __init__(self,inputfilepath=None):
        if getattr(sys, 'frozen', False):# frozen
            self.installpath = os.path.dirname(sys.executable)
        else: # unfrozen
            self.installpath = os.path.dirname(os.path.realpath(__file__))

        self.root = Tk()
        self.root.title("Photon OpenSlicer")
        img=PhotoImage(file=os.path.join(self.installpath,'PhotonSlicer.gif'))
        self.root.tk.call('wm','iconphoto',self.root._w,img)
        #tk.Label(self.popup, text="Slicing...").grid(row=0, column=0)

        self.mainframe = ttk.Frame(self.root, padding="3 3 12 12")
        self.mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.input = StringVar()
        self.output = StringVar()
        self.layerheight = DoubleVar()
        self.offtime = DoubleVar()
        self.bottomlayers=IntVar()
        self.bottomexposure=DoubleVar()
        self.normalexposure=DoubleVar()

        # set defaults
        self.inputpath="/"
        self.outputpath="/"
        self.layerheight.set(0.05)
        self.offtime.set(6.5)
        self.bottomlayers.set(8)
        self.bottomexposure.set(90)
        self.normalexposure.set(12)
        if inputfilepath!=None:
            self.input.set(inputfilepath)

        # read last settings if present
        try:
            fl=open(os.path.join(self.installpath,"guisettings.txt"),'r')
            self.inputpath=fl.readline().strip()
            self.outputpath=fl.readline().strip()
            self.layerheight.set(float(fl.readline().strip()))
            self.offtime.set(float(fl.readline().strip()))
            self.bottomlayers.set(int(fl.readline().strip()))
            self.bottomexposure.set(float(fl.readline().strip()))
            self.normalexposure.set(float(fl.readline().strip()))
            fl.close()
        except Exception:
            pass

        mainframe=self.mainframe

        irow=1
        ttk.Label(mainframe, text="STL/SVG/PNGs").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe,textvariable=self.input,justify=RIGHT).grid(column=2,row=irow,sticky=(W,E))
        ttk.Button(mainframe, text="Browse", command=self.browseinput).grid(column=3, row=irow, sticky=W)

        irow+=1
        ttk.Label(mainframe, text="Photon/PNGs").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe, textvariable=self.output).grid(column=2, row=irow, sticky=(W, E))
        ttk.Button(mainframe, text="Browse", command=self.browseoutput).grid(column=3, row=irow, sticky=W)

        irow+=1
        ttk.Separator(mainframe,orient=HORIZONTAL).grid(columnspan=6, row=irow, sticky=(W,E))

        irow+=1
        ttk.Label(mainframe, text="layer height").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe, textvariable=self.layerheight).grid(column=2, row=irow, sticky=(W, E))
        ttk.Label(mainframe, text="mm").grid(column=3, row=irow, sticky=W)

        irow+=1
        ttk.Label(mainframe, text="off time").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe, textvariable=self.offtime).grid(column=2, row=irow, sticky=(W, E))
        ttk.Label(mainframe, text="seconds").grid(column=3, row=irow, sticky=W)

        irow+=1
        ttk.Separator(mainframe,orient=HORIZONTAL).grid(columnspan=5, row=irow, sticky=(W,E))

        irow+=1
        ttk.Label(mainframe, text="# bottom layers").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe, textvariable=self.bottomlayers).grid(column=2, row=irow, sticky=(W, E))

        irow+=1
        ttk.Label(mainframe, text="bottom exposure").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe, textvariable=self.bottomexposure).grid(column=2, row=irow, sticky=(W, E))
        ttk.Label(mainframe, text="seconds").grid(column=3, row=irow, sticky=W)

        irow+=1
        ttk.Label(mainframe, text="normal exposure").grid(column=1, row=irow, sticky=W)
        ttk.Entry(mainframe, textvariable=self.normalexposure).grid(column=2, row=irow, sticky=(W, E))
        ttk.Label(mainframe, text="seconds").grid(column=3, row=irow, sticky=W)

        irow+=1
        ttk.Separator(mainframe,orient=HORIZONTAL).grid(columnspan=5, row=irow, sticky=(W,E))
        irow+=1
        ttk.Button(mainframe, text="Slice", command=self.setargs).grid(column=3, row=irow, sticky=W)

        for child in mainframe.winfo_children(): child.grid_configure(padx=5, pady=5)

        #feet_entry.focus()
        self.root.bind('<Return>', self.cancel)

        self.root.mainloop()


    def browseinput(self):
        self.root.filename =  filedialog.askopenfilename(initialdir = self.inputpath,title = "Open file",filetypes = (("stl files","*.stl"),("png files","*.jpg"),("svg files","*.svg")))
        if self.root.filename:
            self.input.set(self.root.filename)
            self.inputpath=os.path.dirname(self.root.filename)

    def browseoutput(self):
        self.root.filename = filedialog.asksaveasfilename(initialdir = self.outputpath,title = "Save photon file",filetypes = (("photon files","*.photon"),("all files","*.*")))
        if self.root.filename:
            self.output.set(self.root.filename)
            self.outputpath=os.path.dirname(self.root.filename)

    def setargs(self):
        # set args
        self.args=  {'input':self.input.get(),
                    'output':self.output.get(),
                    'layerheight':self.layerheight.get(),
                    'offtime':self.offtime.get(),
                    'bottomlayers':self.bottomlayers.get(),
                    'bottomexposure':self.bottomexposure.get(),
                    'normalexposure':self.normalexposure.get()
                }

        # write last settings
        fl=open(os.path.join(self.installpath,"guisettings.txt"),'w')
        fl.write(self.inputpath)
        fl.write('\n')
        fl.write(self.outputpath)
        fl.write('\n')
        fl.write(str(self.layerheight.get()))
        fl.write('\n')
        fl.write(str(self.offtime.get()))
        fl.write('\n')
        fl.write(str(self.bottomlayers.get()))
        fl.write('\n')
        fl.write(str(self.bottomexposure.get()))
        fl.write('\n')
        fl.write(str(self.normalexposure.get()))
        fl.write('\n')
        fl.close()


        self.root.destroy()

    def cancel(self):
        print ("User exited.")
        self.args=None
        self.root.destroy()

if __name__=='__main__':
    g=PhotonSlicerGui()
