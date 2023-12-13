import tkinter as tk
import numpy as np

def _swap(coord,orientation):
    if orientation=='horizontal':
        return coord
    if orientation=='vertical':
        return [coord[1],coord[0],coord[3],coord[2]]

class ToggleSwitch(tk.Canvas):
    """
    When class member "is_on" changed, a <<onchanged>> event will be triggered.
    class members:
        is_on: True or False
    """
    def __init__(self, parent, width=80, height=40, padding = 3, orientation = 'horizontal', 
                 toggle_on_color = 'green', toggle_off_color = 'grey', jollystick_on_color = 'white', jollystick_off_color = 'white',
                 animation_speed = 10, animation_step = 10,
                 # myfunction,      # pass the customed function.
                 **kwargs):
        if orientation == 'horizontal':
            canvas_width, canvas_height = width, height
        elif orientation == 'vertical':
            canvas_width, canvas_height = height, width
        else:
            raise ValueError("Invalid orientation: must be 'horizontal' or 'vertical'")
        print(canvas_width, canvas_height)
        super().__init__(parent, width=canvas_width, height=canvas_height, bg='white', highlightthickness=0, **kwargs)
        self.parent = parent
        self.width = canvas_width
        self.height = canvas_height
        self.is_on = False
        self.orientation = orientation
        print(self.width, self.height)
        # Draw the background
        self.track_on_color = toggle_on_color
        self.track_off_color = toggle_off_color
        padding = padding
        
        self.circle_on_color = jollystick_on_color
        self.circle_off_color = jollystick_off_color

        self.animation_speed = animation_speed  # Milliseconds between animation steps, control the speed of the toggle.
        self.animation_steps = animation_step  # Number of steps to move the circle

        la = max(width, height)
        lb = min(width, height)
        self.oval_radius = lb - 2 * padding
        self.circle_radius = lb - 4 * padding


        self.rectangle_coord = [ padding + self.oval_radius / 2, 
                                 padding, 
                                 la - (padding + self.oval_radius / 2),
                                 lb - padding ] 
        self.oval_on_coord = [ padding,
                               padding,
                               padding+self.oval_radius,
                               padding+self.oval_radius
                             ]
        self.oval_off_coord= [la-(padding+self.oval_radius),
                              padding,
                              la-padding,
                              padding+self.oval_radius
                             ]    
        self.circle_on_coord =[2*padding,
                               2*padding,
                               2*padding+self.circle_radius,
                               2*padding+self.circle_radius
                             ]                     
        self.circle_off_coord=[la-(2*padding+self.circle_radius),
                              2*padding,
                              la-2*padding,
                              2*padding+self.circle_radius
                             ]  
                                 
        self.create_rectangle(*_swap(self.rectangle_coord,self.orientation), outline='', fill=self.track_off_color, tags='track')
        self.create_oval(*_swap(self.oval_on_coord,self.orientation), outline='', fill=self.track_off_color, tags='track')
        self.create_oval(*_swap(self.oval_off_coord,self.orientation), outline='', fill=self.track_off_color, tags='track')
        self.circle = self.create_oval(*_swap(self.circle_off_coord,self.orientation), outline='white', fill=self.circle_off_color, tags='circle')
 
        self.bind("<Button-1>", self.toggle)


    def animate(self, direction):
        if direction == 'off':
            stop_coord = self.circle_off_coord
        else:
            stop_coord = self.circle_on_coord
        start_coord = _swap(self.coords('circle'),self.orientation)
        
        animate_coords = list(np.linspace(stop_coord, start_coord, self.animation_steps+1 ) )
        animate_coords.pop()
    
        move_distance = np.abs(self.width - self.height) / self.animation_steps
        self.animate_run(animate_coords)
        self.itemconfig('track', fill=self.track_off_color if (direction=='off') else self.track_on_color)
        self.event_generate('<<onchanged>>')
        
    def animate_run(self,animate_coords):
        if len(animate_coords)>0:
            self.coords('circle',*_swap(animate_coords.pop(),self.orientation))
            self.after(self.animation_speed, self.animate_run, animate_coords)

    def toggle(self, event):
        if self.is_on:
            self.is_on = False
            self.animate('off')
        else:
            self.is_on = True
            self.animate('on')    

if __name__ == "__main__":
    root = tk.Tk()
    root.title('Toggle Switch Example')
    toggle_switch = ToggleSwitch(root)
    toggle_switch.pack(pady=50)
    toggle_switch = ToggleSwitch(root, orientation='vertical')
    toggle_switch.pack(padx=100, pady=50)    
    root.mainloop()
