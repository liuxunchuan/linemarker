#!python
#########################################
#version: v0
#developed by Dr. Xunchuan Liu (liuxunchuan001@gmail.com)
#initially developed: 2023.12.6
#latest modification: 2023.12.12
#Other contributors: Xiaofeng Mai
#########################################

import astropy.io.fits as fits
import numpy as np
import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
import astropy.table as t
from matplotlib.widgets import Button
from matplotlib.widgets import RectangleSelector
import matplotlib.patches as patches
from matplotlib.widgets import TextBox
from ipywidgets import widgets, interactive
import os

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import filedialog as fd 
from tkinter.messagebox import showinfo, askyesno

import util

supporting_language_switch = True
try:
    from gettext import translation
    i18n_root_dir = os.path.join(os.path.dirname(__file__), "i18n")
    supported_langdomains = [('zh','zh_CN'),('en','en')]
    default_lang = 'en'
    lang_translators = { lang: translation(domain=domain, localedir=i18n_root_dir, languages=[lang],fallback=True)
                     for lang,domain in supported_langdomains
                   } 
    lang_translators[default_lang].install()
    _ = lang_translators[default_lang].gettext
except Exception:
    supporting_language_switch = False
    
class Linemarker:
    """
    The linemarker provide a GUI to manually select the line-free (or line-emission) channels
    of a spectrum.
    Input: 
        Spectrum file:
            in the format of tsv only (e.g., path/specfile.tsv),
            the frequency is in unit of MHz,
            not necessary be continuum subtracted.
    Output: 
        Freq windows file: 
            default to be written in path/specfile_winstr.txt,
            in the format like 216988.6683~216995.9926;217078.5120~217079.9769
        Snapshot image:
            default to be saved in path/specfile_winstr.pdf           
    Control spectral panel:
        Scroll down: zoom out
        Scroll up: zoom in
        mousewheel click: reset freqency range                    
    """
    def __init__(self,master,bg='#ECECEC'):
        self.supporting_language_switch = supporting_language_switch
        self.master = master
        self.master.config(bg=bg)
        width = self.master.winfo_screenwidth()
        height = self.master.winfo_screenheight()
        dpi = width/(self.master.winfo_screenmmwidth()/25.1)
        width_app = min(int(20.*dpi), width)
        height_app = min(int(width_app*6./20), height)
        width_app_pad = (width-width_app)//2
        height_app_pad = (height-height_app)//4 
        win_geometry=('%dx%d+%d+%d'%(width_app, height_app,width_app_pad,height_app_pad))
        self.master.geometry(win_geometry)
        self.fig = plt.figure(_("select line free channel"),figsize=(width_app/dpi,height_app/dpi*2./3))
        self.ax = self.fig.add_axes([0.05,0.1,0.9,0.85])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        self.line_loaded = False
        spefile = ''#'spw0spe_test1.tsv'
        initial_winfile = 'spw0spe_test1_winstr.txt'
        
        self.line = None
        self.line_loaded = False
        self.defaultdir = './'
        if (spefile is not None) and (spefile != ''):
            try:
                self.set_data_fromfile(spefile)     
            except Exception as e:
                print(e)
                pass
         
        try:
            with open(initial_winfile) as f:
                self.mask=self.parse_winstr(f.read(),self.x)
            self.update_shadow()
        except Exception:
            pass   
        self.mask_maxhistory = 100
        self.reset_mask_history()
        if hasattr(self,'mask'):
            self.append_mask_history(self.mask)  
            
        self.canvas.mpl_connect('scroll_event', self.zoom)
        self.canvas.mpl_connect('button_press_event', self.reset_limit_listen)  
        
        self.selector = RectangleSelector(self.ax, self.draw_callback, useblit=True, 
                               button=[1, 3], # disable middle button
                               minspanx=5, minspany=5, spancoords='pixels', 
                               interactive=False)                 
       
        self.outframe = tk.Frame(master,bg=bg)
        self.outframe.pack(side=tk.LEFT)               
        self.labelText1=tk.StringVar()
        self.labelText1.set(_("Linefree frequency range"))
        self.labelDir1=tk.Label(self.outframe, textvariable=self.labelText1, height=2,bg=bg)
        self.labelDir1.pack(side=tk.TOP,pady=(20,1))                 
        self.output_box = tk.Text(self.outframe,height=12,width=80)
        #self.output_box.configure(state='disabled')
        self.output_box.pack(pady=(0,10),padx=40)    
        self.update_outputbox()  
        self.output_box.bind('<Control-KeyRelease-a>',self.select_alltext)
        
        self.fileframe = tk.Frame(master,bg=bg)
        self.fileframe.pack(side=tk.LEFT,padx=20)
        self.open_button = tk.Button(
            self.fileframe,
            text=_("Open a spectrum file"),
            command=self.select_datafile,
            height=3, width=20,
            font=("fangsong ti", 10),
            )
        self.open_button.pack(side=tk.TOP,pady=(30,1))
        self.openwin_button = tk.Button(
            self.fileframe,
            text=_('Open freq ranges file'),
            command=self.select_winfile,
            height=3, width=20,
            font=("Helvetica", 10),
            )
        self.openwin_button.pack(side=tk.TOP,pady=(10,1))   
        
        self.fitframe = tk.Frame(master,bg=bg)
        self.fitframe.pack(side=tk.LEFT,padx=20) 
        self.labelText2=tk.StringVar()
        self.labelText2.set(_("fit order"))
        self.labelDir2=tk.Label(self.fitframe, textvariable=self.labelText2, height=2, bg=bg)
        self.labelDir2.pack(side=tk.TOP,pady=(20,1))    
        self.fitorder_entry = tk.Entry(self.fitframe,width=15)
        self.fitorder_entry.pack(side=tk.TOP) 
        self.fitorder_entry.bind('<Return>',self.fitorder_return) 
        
        self.winnavi_frame = tk.Frame(self.master,bg=bg)
        self.winnavi_frame.pack(side=tk.LEFT,padx=20)  
        self.labelText3=tk.StringVar()
        self.labelText3.set(_("freq windowns navigator")) 
        self.label_winnavi=tk.Label(self.winnavi_frame, textvariable=self.labelText3, height=2, bg=bg)
        self.label_winnavi.grid(row=0,column=0,columnspan = 2)  
        self.winnavi_pre = tk.Button(self.winnavi_frame,text='<',width=8,command=lambda: self.winnavi_callback('pre'))
        self.winnavi_nex = tk.Button(self.winnavi_frame,text='>',width=8,command=lambda: self.winnavi_callback('nex'))
        self.winnavi_first = tk.Button(self.winnavi_frame,text='<<',width=8,command=lambda: self.winnavi_callback('first'))
        self.winnavi_last  = tk.Button(self.winnavi_frame,text='>>',width=8,command=lambda: self.winnavi_callback('last'))
        self.winnavi_pre.grid(row=1,column=0,padx=2)
        self.winnavi_nex.grid(row=1,column=1)   
        self.winnavi_first.grid(row=2,column=0)
        self.winnavi_last.grid(row=2,column=1)
        self.winnavi_del = tk.Button(self.winnavi_frame,text=_("delete all"),width=18+3,height=2,command=lambda: self.winnavi_callback('delete all'))
        self.winnavi_del.grid(row=3,column=0,columnspan = 2)

        self.out_switch_frame = tk.Frame(self.master,bg=bg)
        self.out_switch_frame.pack(side=tk.LEFT,padx=15) 
        switch_initial_on=True
        self.TS = util.toggleswitch.ToggleSwitch(self.out_switch_frame,orientation='vertical',width=80,height=40,initial_on=switch_initial_on)
        self.TS.bind('<<onchanged>>',self.switch_changed)
        self.TS.grid(row=0,column=0,rowspan=3)
        self.labelText5=tk.StringVar()
        self.labelText5.set(_("strict case"))
        self.label5=tk.Label(self.out_switch_frame,textvariable=self.labelText5, height=2, bg=bg,anchor="w", justify="left")
        self.label5.grid(row=0,column=1)
        self.labelText6=tk.StringVar()
        self.labelText6.set(_("loose case"))
        self.label6 = tk.Label(self.out_switch_frame,textvariable=self.labelText6, height=2, bg=bg,anchor="w", justify="left")
        self.label6.grid(row=2,column=1)
        
        #self.out_switch_label_frame = tk.Frame(self.out_switch_frame,bg=bg)
        #self.out_switch_label_frame.pack(side=tk.LEFT,padx=5) 
        
        
        self.save_frame = tk.Frame(self.master,bg=bg)
        self.save_frame.pack(side=tk.LEFT,padx=20) 
        self.save_button = tk.Button(self.save_frame,text=_("save as"),command=self.saveas,width=12,font=("Helvetica", 10))
        self.save_button.pack(side=tk.TOP,pady=(10,0))
        self.savedefalt_appendstr = '_strict_winstr.txt' if switch_initial_on else '_loose_winstr.txt'
        self.savedefault_button = tk.Button(self.save_frame,text=_("save default"),command=self.savedefault,width=12,font=("Helvetica", 10))
        self.savedefault_button.pack(side=tk.TOP,pady=(10,0))
      

        
        self.languages = ['en','zh']
        self.labelText4 = tk.StringVar()
        self.labelText4.set(self.languages[0])
        self.lang_switch = tk.OptionMenu(self.master,self.labelText4,*(self.languages))
        self.lang_switch.configure(width=5)
        self.lang_switch.pack(side=tk.LEFT,padx=(6,1))
        self.labelText4.trace("w", self.switch_language)
      
    def _require(varstrs,info=True):
        def decorator(func):
            if type(varstrs)==str:
                _varstrs = [varstrs]
            else:
                _varstrs = varstrs
            def wrapper(self,*arg,**kw):
                for varstr in _varstrs:
                    if (not hasattr(self,varstr)) or (self.__dict__[varstr] is None) or (self.__dict__[varstr] is False):
                        if info:
                            print('variable %s doest not exists or is equal to None' %varstr)
                        return
                return func(self,*arg,**kw)
            return wrapper
        return decorator
        
    def _updatecanvas(func):
        def wrapper(self,*arg,**kw):
            val = func(self,*arg,**kw)
            self.canvas.draw()
            return val
        return wrapper
        
    def _check_winavi(func):
        def wrapper(self,direction):
            assert direction in ('pre','nex','first','last','delete all')
            if len(self.mask_history)<0:
                pass 
                return  
            return func(self,direction)
        return wrapper  
                
    def select_file(self,
                    filetypes = (
                        ('tsv','*.tsv'),
                        ('csv','*.csv'),
                        ('text files', '*.txt'),
                        ('fits','*.fits'),
                        ('All files', '*'),
                        ),
                    mode='open',
                    ):
        if mode=='open':
            filename = fd.askopenfilename(
                title=_("Open a file"),
                initialdir=self.defaultdir,
                filetypes=filetypes
            )
        elif mode=='save':
            filename = fd.asksaveasfilename(
                title=_("Open a file for save"),
                initialdir=self.defaultdir,
                filetypes=filetypes
            )
        else:
            filename = ''
        
        if type(filename) != str:
            filename = ''
        #if filename != '':
        #    self.defaultdir=os.path.dirname(filename)
        return filename
        #showinfo(title='selected file',message=filename)
        
    @_require(['line_loaded','mask'],info=False)    
    def saveas(self):
        filetypes = (   ('text files', '*.txt'),
                        ('All files', '*'),
                        )
        filename = self.select_file(filetypes=filetypes,
                                    mode='save')
        if filename == '':
            return 
            
        self._save(filename)            

    def switch_changed(self,event):
        self.savedefalt_appendstr = '_strict_winstr.txt' if self.TS.is_on else '_loose_winstr.txt' 
        
    @_require(['line_loaded','mask','defaultdir','path_prefix'],info=False)
    def savedefault(self):
        filename = os.path.join(self.defaultdir,self.path_prefix+self.savedefalt_appendstr)
        overwrite = False
        if os.path.exists(filename):
            overwrite = askyesno(_("warning"),_("File '%s' exists, do you want to overwrite it?") %filename)
            if not overwrite:
                return
        self._save(filename)
        if not overwrite:
            showinfo(_("info"),_("window ranges have been saved into '%s'") %filename)   
    
    @_require(['line_loaded','mask'])            
    def _save(self,filename):
        with open(filename,'w') as f:
            print('prepare to write to %s' %filename)
            s = self.parse_mask(self.mask,self.x)
            f.write(s)
        pdffilename = os.path.splitext(filename)[0]+'.pdf'
        self._savefig(pdffilename)
            
    @_require('fig')        
    def _savefig(self,pdffilename):
            self.fig.savefig(pdffilename)
        
    def select_datafile(self):
        filename = self.select_file()
        if filename == '':
            return
        self.set_data_fromfile(filename)
      
    @_updatecanvas        
    def set_data_fromfile(self,filename):        
        data = self.getdata_from_file(filename)
        #print(filename,data)
        if data is not None:
            self.x=data[0]
            self.y=data[1]
            self.line_loaded = True
            self.line=self.update_line(self.x,self.y,self.line,color='C0')
            self.reset_limit()
            if hasattr(self,'mask'):
                del self.mask
            self.update_shadow() 
            self.reset_mask_history()
            self.remove_fitline()
            self.update_outputbox()    
            
            self.defaultdir = os.path.dirname(filename) 
            basename = os.path.basename(filename)
            self.path_prefix,self.path_ext = os.path.splitext(basename)            
            
    def getdata_from_file(self,filename):
        _, ext = os.path.splitext(filename)
        if ext == '.tsv':
            T=t.Table.read(filename,format='ascii.no_header',names=['x','y'])
            x = np.array(T['x'])*1E3
            y = np.array(T['y'])
            if x[1]<x[0]:
                x = x[::-1]
                y = y[::-1]
            return x,y
        showinfo(title='warning!',message=_("can not parse data file %s") %filename)   
        return None
     
    @_updatecanvas    
    def select_winfile(self):
        filetypes = (   ('text files', '*.txt'),
                        ('tsv','*.tsv'),
                        ('csv','*.csv'),
                        ('fits','*.fits'),
                        ('All files', '*'),
                        )
        filename = self.select_file(filetypes=filetypes)
        if filename == '':
            return
        try:
            with open(filename) as f:
                self.mask=self.parse_winstr(f.read(),self.x)
            self.update_shadow() 
            self.append_mask_history(self.mask)
            self.update_outputbox()
            self.update_fitline()            
        except Exception as e:
            showinfo(title='warning!',message=_("can not parse win file %s") %filename)
            raise e        
                
    def update_line(self,x,y,line=None,**kw):
        if line in self.ax.lines:
            try:
                self.ax.lines.remove(line)
            except Exception:
                line.remove()    
        return self.ax.plot(x,y,**kw)[0] 

    @_require('line_loaded')
    def reset_limit(self):
        #if not self.line_loaded:
        #    return
        self.ax.set_xlim(self.x.min(),self.x.max())
        dy = (self.y.max()-self.y.min())*0.02
        self.ax.set_ylim(self.y.min()-dy,self.y.max()+dy)
 
    @_updatecanvas
    def reset_limit_listen(self,event):
        if event.button == 2:  # Check if the right mouse button is pressed
            self.reset_limit() 
    
    @_updatecanvas
    def zoom(self,event):
        if event.inaxes == self.ax:
            current_xlim = self.ax.get_xlim()
            zoom_factor = 1./1.1 if event.button == 'up' else 1.1  # Adjust the zoom factor as needed

            new_xlim = (
                event.xdata - (event.xdata - current_xlim[0]) * zoom_factor,
                event.xdata + (current_xlim[1] - event.xdata) * zoom_factor
            )
            self.ax.set_xlim(new_xlim)

    def update_shadow(self,alpha=0.4,color='gray'):
        if hasattr(self,'mask_shadow') and (self.mask_shadow in self.ax.collections):
            try:
                self.ax.collections.remove(self.mask_shadow)
            except Exception:
                self.mask_shadow.remove()
        yl,yu=self.ax.get_ylim()
        if hasattr(self,'mask') and self.line_loaded:
            self.mask_shadow = self.ax.fill_between(self.x,yl,yl+(yu-yl),self.mask,color=color,alpha=alpha)
       
    @_updatecanvas  
    @_require('line_loaded')  
    def draw_callback(self,eclick, erelease):
        x1,x2= eclick.xdata, erelease.xdata
        x1,x2 = (x1,x2) if x2>x1 else (x2,x1) 
        if not hasattr(self,'mask'):
            self.mask = np.zeros_like(self.x, dtype='bool')
        if eclick.button == 1:
            self.mask = self.mask | ((self.x>x1)&(self.x<x2))
        if eclick.button == 3:
            self.mask = self.mask & ((self.x<x1)|(self.x>x2))
        self.update_shadow()  
        self.append_mask_history(self.mask)     
        self.update_outputbox()  
        self.update_fitline()
        
    def append_mask_history(self,mask):
        self.mask_history.insert(self.mask_current+1,mask)
        self.mask_current = self.mask_current+1
        if len(self.mask_history) > (self.mask_current+1):
            for i in range( len(self.mask_history) - (self.mask_current+1) ):
                 self.mask_history.pop(-1)
        if len(self.mask_history)>self.mask_maxhistory:
            self.mask_history.pop(0)
            self.mask_current = len(self.mask_history)-1     
            
    def reset_mask_history(self):
        if not hasattr(self,'mask_history'):
            self.mask_history = []
        for i in range(len(self.mask_history)):
            self.mask_history.pop(-1)
        self.mask_current = -1 
     
    @_check_winavi
    @_updatecanvas 
    @_require('mask',info=False)   
    def winnavi_callback(self,direction):  
        if direction == 'delete all':
            if askyesno(_("warning"),_("do you want to delete all windows irrevocablely?")):
                self.reset_mask_history()
                self.remove_fitline()
                del self.mask          
        elif len(self.mask_history)>1:
            if direction == 'pre':
                if self.mask_current <= 0:
                    pass
                    return
                else:
                    self.mask_current = self.mask_current-1
            if direction == 'nex':
                if self.mask_current >= (len(self.mask_history)-1):
                    pass
                    return
                else:
                    self.mask_current = self.mask_current+1
            if direction == 'first':
                self.mask_current = 0
            if direction == 'last':
                self.mask_current =  len(self.mask_history)-1
            self.mask = self.mask_history[self.mask_current]
        self.update_shadow()
        self.update_fitline()          
        
    def select_alltext(self,event):
        #self.output_box.configure(state='normal')
        #self.master.after(50,self._select_alltext,event.widget)
        event.widget.event_generate('<<SelectAll>>') 
        #self.output_box.configure(state='disabled')  
        
    def fitorder_return(self,event):
        order = event.widget.get()
        #print('order:',order)
        if order.isnumeric():
            self.fitorder = int(order)
        elif (order == '') or (order[0]=='-'):
            self.fitorder = -1
        else:
            return
        self.update_fitline()    
            

    @_updatecanvas
    @_require(['line_loaded','mask','fitorder'],info=False)            
    def update_fitline(self):
        self.remove_fitline()
        if self.fitorder<0:
            return     
        if self.mask.sum()<=self.fitorder:
                    print('the channel number is not enough for %i-order poly fitting' %(self.fitorder) )
                    return
        xfit = (self.x-self.x.min())/(self.x.max()-self.x.min())
        ppar = np.polyfit(xfit[self.mask],self.y[self.mask],self.fitorder)
        yfit = np.polyval(ppar,xfit)
        self.fitline = self.ax.plot(self.x,yfit,
                                   color='r',alpha=0.3,ls='--')[0] 
               
        
            
    @_require('fitline',info=False)
    def remove_fitline(self):
        self.fitline.remove()
        del self.fitline       
        
    @classmethod
    def parse_winstr(cls,winstr,x):
        win = np.zeros_like(x,dtype='bool')
        wins = [i.split('~') for i in winstr.strip().split(';')]
        wins = [(float(i[0]),float(i[1])) for i in wins] 
        for i in wins:
            leftdex = np.argmin(np.abs( i[0]-x )) 
            rightdex = np.argmin(np.abs( i[1]-x ))
            win[leftdex:rightdex+1] = True
            #Be carefull that 'win[(x>=i[0]) & (x<=i[1])]=True' performs not good,
            #since the frequency written to file has been truncated with limited precision.
        return win
 
    @classmethod        
    def parse_mask_edges(cls,mask):
        mask1 = np.zeros(len(mask)+2,dtype='bool')
        mask1[0]  = False
        mask1[-1] = False
        mask1[1:-1] = mask
        left_edges  = (~mask1[0:-2]) & (mask1[1:-1])
        right_edges = (mask1[1:-1]) & (~mask1[2:])
        left_edges = np.arange(len(mask))[left_edges] 
        right_edges = np.arange(len(mask))[right_edges]
        assert len(left_edges) == len(right_edges)
        return np.array([left_edges,right_edges]).T
    
    @classmethod
    def parse_mask(cls,mask,x):
        edges=cls.parse_mask_edges(mask)
        return ';'.join(['%.4f~%.4f' %(x[dex[0]],x[dex[1]]) for dex in edges])        
        
    @_require('output_box')    
    def update_outputbox(self):
        #self.output_box.configure(state='normal')
        self.output_box.delete('1.0', tk.END)
        if hasattr(self,'mask'):
            s = self.parse_mask(self.mask,self.x)
            self.output_box.insert('1.0', s)            
        #self.output_box.configure(state='disabled')
            
    def on_closing(self):
        self.master.quit()
        self.master.destroy() 
        
    @_updatecanvas    
    def configure_labels(self,lang):
        lang_translators[lang].install()
        global _
        _ = lang_translators[lang].gettext
        self.labelText1.set(_("Linefree frequency range"))
        self.labelText2.set(_("fit order"))
        self.labelText3.set(_("freq windowns navigator"))
        self.labelText5.set(_("strict case"))
        self.labelText6.set(_("loose case")) 
        self.master.title(_("Line Marker"))
        self.open_button.config(text=_("Open a spectrum file"))
        self.openwin_button.config(text=_('Open freq ranges file'))
        self.winnavi_del.config(text=_("delete all"))
        self.save_button.config(text=_("save as"))
        self.savedefault_button.config(text=_("save default"))
        
        font = ('fangsong ti',10)
        self.labelDir1.config(font=font)
        self.labelDir2.config(font=font)
        self.label_winnavi.config(font=font)
        self.label5.config(font=font)
        self.label6.config(font=font)
        self.open_button.config(font=font)
        self.openwin_button.config(font=font)
        self.winnavi_del.config(font=font)
        self.save_button.config(font=font)
        self.savedefault_button.config(font=font)
     
    @_require('supporting_language_switch')    
    def switch_language(self,*arg):
        print('switch language arg',arg)
        lang = self.labelText4.get()
        #print('switch to language %s' %lang)
        self.configure_labels(lang)
        
        
if __name__ == "__main__":
    tkroot = tk.Tk()
    print(_("Line Marker"))
    tkroot.title(_("Line Marker"))
    app = Linemarker(tkroot,bg='#ECECEC')
    tkroot.protocol('WM_DELETE_WINDOW',app.on_closing )
    tkroot.mainloop()
