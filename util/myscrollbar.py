from tkinter import Scrollbar

class MyScrollbar(Scrollbar):
    def __init__(self,master,command=None,*arg,**kw):
        self.command__ = command
        super(MyScrollbar,self).__init__(master,*arg,**kw)
        
        super(MyScrollbar,self).config(command=self.selfsync)
        
        
    def config(self,command=None,*arg,**kw):
        self.command_ = command
        super(MyScrollbar,self).config(*arg,**kw) 
        
    def selfsync(self,*e):    
        x1,x2=self.get()
        l = x2-x1    
        x1_new = x1; x2_new = x2   
        if e[0]=='moveto':         
            x1_new = float(e[1])
        elif e[0] == 'scroll':
            if e[2] == 'pages':
                x1_new = x1+l*int(e[1])  
            elif e[2] == 'units':
                x1_new = x1+0.01*int(e[1])
            else:
                raise Exception('unexcepted issue') 
        else:
            raise Exception('unexcepted issue')        
        x2_new = x1_new+l        
        if x1_new<0:
            x1_new=0
            x2_new=l
        if x2_new>1:
            x2_new=1
            x1_new=1-l
        self.set(x1_new,x2_new)                
        if (x1_new != x1) & (self.command__ != None):
            self.command__('moveto',x1_new,x2_new)
