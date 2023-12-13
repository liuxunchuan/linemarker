import tkinter as tk

class ToggleSwitch(tk.Canvas):
    """
    When class member "is_on" changed, a <<onchanged>> event will be triggered.
    class members:
        is_on: True or False
    """
    def __init__(self, parent, width=60, height=30, **kwargs):
        super().__init__(parent, width=width, height=height, bg='white', highlightthickness=0, **kwargs)
        self.parent = parent
        self.width = width
        self.height = height
        self.is_on = False
        
        # Draw the background
        self.track_on_color = 'green'
        self.track_off_color = 'grey'
        padding = 5
        radius = height - 2 * padding
        self.create_rectangle(padding + radius / 2, padding, width - (padding + radius / 2), 
                              height - padding, outline='', fill=self.track_off_color, tags='track')
        self.create_oval(padding, padding, padding + radius, height - padding, outline='', 
                        fill=self.track_off_color, tags='track')
        self.create_oval(width - (padding + radius), 
                         padding, width - padding, height - padding, outline='', 
                         fill=self.track_off_color, tags='track')
        
        # Draw the toggle circle
        self.circle_on_color = 'white'
        self.circle_off_color = 'white'
        self.circle = self.create_oval(padding*2, padding*2, height-padding*2, 
                                       height-padding*2, outline='white', 
                                       fill=self.circle_off_color, tags='circle')
        
        self.bind("<Button-1>", self.toggle)

        # self.animation_speed = 5  # Milliseconds between animation steps
        # self.animation_steps = 10  # Number of steps to move the circle

    def animate(self, direction):
        self.animation_speed = 5  # Milliseconds between animation steps, control the speed of the toggle.
        self.animation_steps = 10  # Number of steps to move the circle
        move_distance = (self.width - self.height) / self.animation_steps
        if direction == 'on':
            self.move('circle', move_distance, 0)
            current_position = self.coords('circle')
            # print(current_position)
            if current_position[2] < self.width - self.height / 2:
                self.after(self.animation_speed, self.animate, direction)
                return
            else:
                self.itemconfig('track', fill=self.track_on_color)
        elif direction == 'off':
            self.move('circle', -move_distance, 0)
            current_position = self.coords('circle')
            if current_position[0] > self.height / 2:
                self.after(self.animation_speed, self.animate, direction)
                return
            else:
                self.itemconfig('track', fill=self.track_off_color)        
        self.event_generate('<<onchanged>>')

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
    root.mainloop()
