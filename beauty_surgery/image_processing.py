import customtkinter as ctk
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import os
import math
from tkinter import filedialog, messagebox
import numpy as np
import time
import types
import json


class ImageFrame(ctk.CTkFrame):
    def __init__(self, master, app, point_update_callback, frame_update_callback=None, is_left=True, frame_adjustable=True, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.app = app
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.image = None
        self.display_image = None
        self.image_on_canvas = None
        self.aspect_ratio = 1
        self.zoom_factor = 1.0
        self.points = []
        self.point_markers = []
        self.point_input_active = False
        self.last_x = 0
        self.last_y = 0
        self.canvas_image_x = 0
        self.canvas_image_y = 0
        self.point_update_callback = point_update_callback
        self.frame_creation_callback = None
        self.is_left = is_left
        self.frame_rect = None
        self.frame_moving = False
        self.frame_resizing = False
        self.resize_edge = None
        self.frame_creation_mode = False
        self.temp_frame_rect = None
        self.frame_update_callback = frame_update_callback
        self.point_added_callback = None  # 포인트 배치되었다면 호출
        self.frame_adjustable = frame_adjustable  # 프레임 조정 가능한지?
        
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        # self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        # self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        # self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        self.original_bindings = {
            "<ButtonPress-1>": self.on_mouse_down,
            "<B1-Motion>": self.on_mouse_drag,
            "<ButtonRelease-1>": self.on_mouse_release
        }

        self.canvas.bind("<ButtonPress-1>", self.original_bindings["<ButtonPress-1>"])
        self.canvas.bind("<B1-Motion>", self.original_bindings["<B1-Motion>"])
        self.canvas.bind("<ButtonRelease-1>", self.original_bindings["<ButtonRelease-1>"])
    
    def get_zoom_factor(self):
        return self.zoom_factor
    
    def set_zoom_factor(self, zoom_factor):
        self.zoom_factor = zoom_factor
    
    def reset(self):
        # 이미지 관련 속성 초기화
        self.image = None
        self.display_image = None
        self.photo_image = None
        self.image_on_canvas = None
        self.aspect_ratio = 1
        self.zoom_factor = 1.0
        self.points = []
        self.point_markers = []
        self.point_input_active = False
        self.canvas_image_x = 0
        self.canvas_image_y = 0
        self.scale_factor = 1.0
        
        # 프레임 관련 속성 초기화
        if self.frame_rect:
            self.canvas.delete(self.frame_rect)
        self.frame_rect = None
        self.frame_moving = False
        self.frame_resizing = False
        self.resize_edge = None
        self.frame_creation_mode = False
        self.temp_frame_rect = None

        # 캔버스 초기화
        self.canvas.delete("all")
        self.canvas.configure(scrollregion=(0, 0, 0, 0))

        print(f"{'Left' if self.is_left else 'Right'} image frame reset.")
    
    def frame_to_image_coords(self):
        if not self.frame_rect:
            return None
        canvas_coords = self.canvas.coords(self.frame_rect)
        image_coords = [
            self.canvas_to_image(canvas_coords[0], canvas_coords[1]),
            self.canvas_to_image(canvas_coords[2], canvas_coords[3])
        ]
        return image_coords
    
    def on_mouse_move(self, event):
        if self.frame_rect and self.frame_adjustable:
            cursor = self.get_frame_cursor(event)
            self.canvas.config(cursor=cursor)
        else:
            self.canvas.config(cursor="")
    
    def get_frame_cursor(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        coords = self.canvas.coords(self.frame_rect)
        
        if not coords:
            return ""

        edge_threshold = 10
        
        on_left_edge = abs(x - coords[0]) < edge_threshold
        on_right_edge = abs(x - coords[2]) < edge_threshold
        on_top_edge = abs(y - coords[1]) < edge_threshold
        on_bottom_edge = abs(y - coords[3]) < edge_threshold

        if (on_left_edge and on_top_edge) or (on_right_edge and on_bottom_edge):
            return "sizing"
        elif (on_right_edge and on_top_edge) or (on_left_edge and on_bottom_edge):
            return "sizing"
        elif on_left_edge or on_right_edge:
            return "sb_h_double_arrow"
        elif on_top_edge or on_bottom_edge:
            return "sb_v_double_arrow"
        elif coords[0] < x < coords[2] and coords[1] < y < coords[3]:
            return "fleur"
        else:
            return ""
    
    def set_image(self, pil_image):
        self.image = pil_image
        self.aspect_ratio = pil_image.width / pil_image.height
        self.zoom_factor = 1.0
        self.points = []
        self.point_markers = []
        self.fit_image()

    def fit_image(self):
        if self.image:
            print(f'fit_image')
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            img_width, img_height = self.image.size
            width_ratio = canvas_width / img_width
            height_ratio = canvas_height / img_height
            self.scale_factor = min(width_ratio, height_ratio) * 0.95 * self.zoom_factor

            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)

            self.display_image = self.image.resize((new_width, new_height), Image.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(self.display_image)
            
            if self.image_on_canvas:
                self.canvas.delete(self.image_on_canvas)
            
            self.canvas_image_x = canvas_width // 2
            self.canvas_image_y = canvas_height // 2
            
            self.image_on_canvas = self.canvas.create_image(
                self.canvas_image_x, self.canvas_image_y, 
                image=self.photo_image, anchor=tk.CENTER
            )
            self.update_point_markers()
    
    def on_resize(self, event):
        self.fit_image()

    def get_zoom_factor(self):
        return self.zoom_factor
    
    def get_transformed_image_size(self):
        if self.display_image:
            return self.display_image.size
        return self.image.size if self.image else (0, 0)

    def get_scale_factor(self):
        return self.scale_factor if hasattr(self, 'scale_factor') else 1.0
    
    def on_mousewheel(self, event):
        if self.frame_rect:
            return  # Don't zoom if a frame is present
        
        if self.image:
            old_zoom = self.zoom_factor
            print(f"확인: {old_zoom}")
            if event.num == 5 or event.delta < 0:
                self.zoom_factor *= 0.9
            if event.num == 4 or event.delta > 0:
                self.zoom_factor *= 1.1
            
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
            
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            self.canvas_image_x = x - (x - self.canvas_image_x) * (self.zoom_factor / old_zoom)
            self.canvas_image_y = y - (y - self.canvas_image_y) * (self.zoom_factor / old_zoom)
            
            self.fit_image()

    def on_mouse_down(self, event):
        if self.frame_creation_mode:
            return
        
        if self.point_input_active and len(self.points) < 2:
            self.app.save_state('add_point')
            image_x, image_y = self.canvas_to_image(event.x, event.y)
            self.points.append((image_x, image_y))
            self.update_point_markers()
            self.point_update_callback()
            if self.point_added_callback:  # 콜백 호출
                self.point_added_callback()
        elif self.frame_rect:
            self.on_frame_press(event)
        else:
            self.last_x = event.x
            self.last_y = event.y
 
    def set_point_added_callback(self, callback):
        self.point_added_callback = callback
    
    def on_frame_press(self, event):
        print('on_frame_press')
        if not self.frame_adjustable:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        coords = self.canvas.coords(self.frame_rect)
        
        edge_threshold = 10
        
        on_left_edge = abs(x - coords[0]) < edge_threshold
        on_right_edge = abs(x - coords[2]) < edge_threshold
        on_top_edge = abs(y - coords[1]) < edge_threshold
        on_bottom_edge = abs(y - coords[3]) < edge_threshold
        
        if on_left_edge or on_right_edge or on_top_edge or on_bottom_edge:
            self.frame_resizing = True
            self.resize_edge = {
                "left": on_left_edge,
                "right": on_right_edge,
                "top": on_top_edge,
                "bottom": on_bottom_edge
            }
        elif coords[0] < x < coords[2] and coords[1] < y < coords[3]:
            self.frame_moving = True
        
        self.last_x = x
        self.last_y = y

    def on_mouse_drag(self, event):
        if not self.frame_adjustable and (self.frame_moving or self.frame_resizing):
            return
        if self.frame_moving:
            self.move_frame(event)
        elif self.frame_resizing:
            self.resize_frame(event)
        elif not self.point_input_active and self.image_on_canvas:
            self.move_image(event)

    def move_image(self, event):
        if self.frame_rect:
            return  # Don't move the image if a frame is present
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        
        self.canvas_image_x += dx
        self.canvas_image_y += dy
        
        self.canvas.move(self.image_on_canvas, dx, dy)
        self.update_point_markers()
        
        self.last_x = event.x
        self.last_y = event.y

    def move_frame(self, event):
        if not self.frame_rect:
            return
        if not self.frame_adjustable:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self.last_x
        dy = y - self.last_y
        
        self.canvas.move(self.frame_rect, dx, dy)
        self.last_x = x
        self.last_y = y
        
        if self.frame_update_callback:
            self.frame_update_callback((dx, dy), resize=False)
    
    def resize_frame(self, event):
        if not self.frame_rect:
            return
        if not self.frame_adjustable:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        old_coords = list(self.canvas.coords(self.frame_rect))
        new_coords = old_coords.copy()
        
        if self.resize_edge["left"]:
            new_coords[0] = min(x, new_coords[2] - 10)
        if self.resize_edge["right"]:
            new_coords[2] = max(x, new_coords[0] + 10)
        if self.resize_edge["top"]:
            new_coords[1] = min(y, new_coords[3] - 10)
        if self.resize_edge["bottom"]:
            new_coords[3] = max(y, new_coords[1] + 10)
        
        self.canvas.coords(self.frame_rect, *new_coords)
        
        if self.frame_update_callback:
            dx1 = new_coords[0] - old_coords[0]
            dy1 = new_coords[1] - old_coords[1]
            dx2 = (new_coords[2] - new_coords[0]) - (old_coords[2] - old_coords[0])
            dy2 = (new_coords[3] - new_coords[1]) - (old_coords[3] - old_coords[1])
            self.frame_update_callback((dx1, dy1, dx2, dy2), resize=True)

    def on_mouse_release(self, event):
        self.frame_moving = False
        self.frame_resizing = False
        self.resize_edge = None
        self.canvas.config(cursor="")

    def update_point_markers(self):
        for marker in self.point_markers:
            self.canvas.delete(marker)
        self.point_markers = []
        for image_x, image_y in self.points:
            canvas_x, canvas_y = self.image_to_canvas(image_x, image_y)
            marker = self.canvas.create_oval(canvas_x-5, canvas_y-5, canvas_x+5, canvas_y+5, fill='red')
            self.point_markers.append(marker)

    def set_point_input_active(self, active):
        self.point_input_active = active

    def get_point_distance_and_slope(self):
        if len(self.points) < 2:
            return None, None
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        slope = math.atan2(y2 - y1, x2 - x1)
        return distance, slope

    def canvas_to_image(self, canvas_x, canvas_y):
        image_x = (canvas_x - self.canvas_image_x) / self.scale_factor + self.image.width / 2
        image_y = (canvas_y - self.canvas_image_y) / self.scale_factor + self.image.height / 2
        return image_x, image_y

    def image_to_canvas(self, image_x, image_y):
        canvas_x = (image_x - self.image.width / 2) * self.scale_factor + self.canvas_image_x
        canvas_y = (image_y - self.image.height / 2) * self.scale_factor + self.canvas_image_y
        return canvas_x, canvas_y

    def transform_image(self, target_distance, target_slope, target_size, target_zoom_factor):
        print('ImageFrame - transform_image')
        if len(self.points) < 2 or self.image is None:
            return False

        
        current_distance, current_slope = self.get_point_distance_and_slope()
        scale_factor = (target_distance / current_distance) * (target_zoom_factor / self.zoom_factor)
        rotation_angle = target_slope - current_slope

        # Create transformation matrix
        cos_theta = math.cos(rotation_angle)
        sin_theta = math.sin(rotation_angle)
        transform_matrix = np.array([
            [cos_theta * scale_factor, -sin_theta * scale_factor],
            [sin_theta * scale_factor, cos_theta * scale_factor]
        ])
        
        rotated_image = self.display_image.rotate(-math.degrees(rotation_angle), expand=False, resample=Image.BICUBIC)
        self.transformed_image = ImageTk.PhotoImage(rotated_image)
        
        if self.image_on_canvas:
                self.canvas.delete(self.image_on_canvas)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.canvas_image_x = canvas_width // 2
        self.canvas_image_y = canvas_height // 2
        
        self.image_on_canvas = self.canvas.create_image(
            self.canvas_image_x, self.canvas_image_y, 
            image=self.transformed_image, anchor=tk.CENTER
        )
        
        self.canvas.update_idletasks()  # 화면 갱신
        
        target_width, target_height = rotated_image.size
        new_width = int(target_width * scale_factor)
        new_height = int(target_height * scale_factor)
        scaled_image = rotated_image.resize((new_width, new_height), Image.LANCZOS)
        
        old_center = np.array([self.image.width / 2, self.image.height / 2])
        new_center = np.array([scaled_image.width / 2, scaled_image.height / 2])

        print(f'변환 전 좌표: {self.points}')
        # Transform points
        new_points = []
        for x, y in self.points:
            point = np.array([x, y]) - old_center
            transformed_point = np.dot(transform_matrix, point) + new_center
            new_points.append(tuple(transformed_point))

        self.image = scaled_image
        self.points = new_points
        print(f'변환 후 좌표: {self.points}')
        
        
        self.display_image = scaled_image
        self.photo_image = ImageTk.PhotoImage(self.display_image)
        
        if self.image_on_canvas:
                self.canvas.delete(self.image_on_canvas)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.canvas_image_x = canvas_width // 2
        self.canvas_image_y = canvas_height // 2
        
        self.image_on_canvas = self.canvas.create_image(
            self.canvas_image_x, self.canvas_image_y, 
            image=self.photo_image, anchor=tk.CENTER
        )
        
        self.update_point_markers()
        return True

    def start_frame_creation(self):
        
        self.frame_creation_mode = True
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        
        self.canvas.bind("<ButtonPress-1>", self.on_frame_start)
        self.canvas.bind("<B1-Motion>", self.on_frame_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda event: self.on_frame_release(event))

    def on_frame_start(self, event):
        self.frame_start_x = self.canvas.canvasx(event.x)
        self.frame_start_y = self.canvas.canvasy(event.y)
        # Clear any existing frame
        if self.frame_rect:
            self.canvas.delete(self.frame_rect)
            self.frame_rect = None

    def on_frame_drag(self, event):
        if self.temp_frame_rect:
            self.canvas.delete(self.temp_frame_rect)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.temp_frame_rect = self.canvas.create_rectangle(
            self.frame_start_x, self.frame_start_y, x, y, outline="red", width=2
        )

    def on_frame_release(self, event):
        self.frame_creation_mode = False
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        
        # Restore original bindings
        for event_name, handler in self.original_bindings.items():
            self.canvas.bind(event_name, handler)

        # Create the final frame
        try:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            if self.temp_frame_rect:
                self.canvas.delete(self.temp_frame_rect)
            frame_coords = (self.frame_start_x, self.frame_start_y, x, y)
            self.create_frame(frame_coords)
            
            #
            point_first, point_second = (self.points)
            
            dx = self.frame_start_x - point_first[0]
            dy = self.frame_start_y - point_first[1]
            print(f'왼쪽 프레임 박스 좌표: {(self.frame_start_x, self.frame_start_y)}')
            print(f'포인트 좌표: {self.points}')
            print(f"왼쪽 프레임 차이값: {dx}, {dy}")
            print(f'왼쪽 프레임 frame_coords: {frame_coords}')
            #
            
            if self.frame_creation_callback:
                self.frame_creation_callback(frame_coords)
        except AttributeError:
            print("Error: Invalid event object received in on_frame_release")
            self.frame_start_x = None
            self.frame_start_y = None

    def create_frame(self, coords):
        if self.frame_rect:
            self.canvas.delete(self.frame_rect)
        self.frame_rect = self.canvas.create_rectangle(*coords, outline="red", width=2)
    
    def get_frame_coords(self):
        if self.frame_rect:
            return self.canvas.coords(self.frame_rect)
        return None

    def clear_frame(self):
        if self.frame_rect:
            self.canvas.delete(self.frame_rect)
            self.frame_rect = None
        self.fit_image()  # Refit the image after clearing the frame
        
    def restore_transformed_image(self):
        if self.display_image:
            self.photo_image = ImageTk.PhotoImage(self.display_image)
            
            if self.image_on_canvas:
                self.canvas.delete(self.image_on_canvas)
            
            self.image_on_canvas = self.canvas.create_image(
                self.canvas_image_x, self.canvas_image_y, 
                image=self.photo_image, anchor=tk.CENTER
            )
            
            self.canvas.update_idletasks()
    
    
    

class ImageProcessingApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("Image Processing App")
        self.geometry("1200x800")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        self.point_input_active = False
        self.left_image_loaded = False
        self.right_image_loaded = False
        self.size_fixed = False
        
        self.preset_file = "dissolve_preset.json"
        self.load_preset()
        
        buttons = [
            ("포인트 입력", lambda: self.set_point_input(True)),
            ("포인트 해제", lambda: self.set_point_input(False)),
            ("이미지 변환", self.transform_image),
            ("프레임 만들기", self.start_frame_creation),
            ("선택한 프레임 저장", self.save_selected_frame),
            ("디졸브 프리셋 및 저장", self.open_dissolve_preset),
            ("초기화", self.reset_app)
        ]
        
        for btn_text, command in buttons:
            btn = ctk.CTkButton(self.button_frame, text=btn_text, command=command)
            btn.pack(side=tk.LEFT, padx=5)
            if btn_text == "프레임 만들기":
                self.make_frame_button = btn
            elif btn_text == "이미지 변환":
                self.transform_button = btn
                
        self.history = []
        self.undo_button = ctk.CTkButton(self.button_frame, text="Undo", command=self.undo)
        self.undo_button.pack(side=tk.LEFT, padx=5)
        self.undo_button.configure(state="disabled")
                
        # 개발 중 테스트를 위한 버튼 추가
        self.test_button = ctk.CTkButton(self.button_frame, text="Load Test Images", command=self.load_test_images)
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        self.transform_button.configure(state="disabled")
        self.make_frame_button.configure(state="disabled")

        self.left_image_frame = ImageFrame(self.main_frame, self, self.update_transform_button, self.sync_right_frame, is_left=True, frame_adjustable=True)
        self.left_image_frame.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.BOTH)
        self.left_image_frame.set_point_added_callback(self.on_point_added)
        
        self.right_image_frame = ImageFrame(self.main_frame, self, self.update_transform_button, is_left=False, frame_adjustable=False)
        self.right_image_frame.pack(side=tk.RIGHT, padx=(5, 0), expand=True, fill=tk.BOTH)
        self.right_image_frame.set_point_added_callback(self.on_point_added)
        
        self.left_image_frame.drop_target_register(DND_FILES)
        self.left_image_frame.dnd_bind('<<Drop>>', self.drop_left)

        self.right_image_frame.drop_target_register(DND_FILES)
        self.right_image_frame.dnd_bind('<<Drop>>', self.drop_right)
    
    def save_state(self, action_type):
        state = {
            'action_type': action_type,
            'left_image': self.left_image_frame.image.copy() if self.left_image_frame.image else None,
            'right_image': self.right_image_frame.image.copy() if self.right_image_frame.image else None,
            'left_display_image': self.left_image_frame.display_image.copy() if self.left_image_frame.display_image else None,
            'right_display_image': self.right_image_frame.display_image.copy() if self.right_image_frame.display_image else None,
            'left_points': self.left_image_frame.points.copy(),
            'right_points': self.right_image_frame.points.copy(),
            'left_frame': self.left_image_frame.get_frame_coords(),
            'right_frame': self.right_image_frame.get_frame_coords(),
            'left_canvas_pos': (self.left_image_frame.canvas_image_x, self.left_image_frame.canvas_image_y),
            'right_canvas_pos': (self.right_image_frame.canvas_image_x, self.right_image_frame.canvas_image_y),
            'left_zoom': self.left_image_frame.zoom_factor,
            'right_zoom': self.right_image_frame.zoom_factor,
            'left_scale': self.left_image_frame.scale_factor if hasattr(self.left_image_frame, 'scale_factor') else 1.0,
            'right_scale': self.right_image_frame.scale_factor if hasattr(self.right_image_frame, 'scale_factor') else 1.0,
            'transformed': hasattr(self.right_image_frame, 'transformed_image'),
        }
        self.history.append(state)
        self.undo_button.configure(state="normal")
        
    def undo(self):
        if not self.history:
            return
        
        print('undo')
        
        state = self.history.pop()
        action_type = state['action_type']
        
        if action_type == 'frame_creation':
            self.left_image_frame.clear_frame()
            self.right_image_frame.clear_frame()
        elif action_type in ['transform', 'load_image']:
            for frame, side in [(self.left_image_frame, 'left'), (self.right_image_frame, 'right')]:
                if state[f'{side}_image']:
                    frame.image = state[f'{side}_image']
                    frame.display_image = state[f'{side}_display_image']
                    frame.points = state[f'{side}_points']
                    frame.canvas_image_x, frame.canvas_image_y = state[f'{side}_canvas_pos']
                    frame.zoom_factor = state[f'{side}_zoom']
                    frame.scale_factor = state[f'{side}_scale']
                    
                    if state[f'{side}_frame']:
                        frame.create_frame(state[f'{side}_frame'])
                    else:
                        frame.clear_frame()
                    
                    if state['transformed'] and side == 'right':
                        frame.restore_transformed_image()
                    else:
                        frame.fit_image()
                    frame.update_point_markers()
                else:
                    frame.reset()
                    if side == 'left':
                        self.left_image_loaded = False
                    else:
                        self.right_image_loaded = False
        elif action_type == 'add_point':
            for frame, side in [(self.left_image_frame, 'left'), (self.right_image_frame, 'right')]:
                frame.points = state[f'{side}_points']
                frame.update_point_markers()
        
        if state['transformed']:
            self.right_image_frame.transformed_image = True
            self.unbind_mousewheel()
        else:
            if hasattr(self.right_image_frame, 'transformed_image'):
                del self.right_image_frame.transformed_image
            self.bind_mousewheel()

        if not self.history:
            self.undo_button.configure(state="disabled")
        
        self.update_transform_button()
        self.update_make_frame_button()
    
    def on_point_added(self):
        if not self.size_fixed:
            self.resizable(False, False)
            self.size_fixed = True
        
        self.update_make_frame_button()
    
    def load_preset(self):
        if os.path.exists(self.preset_file):
            with open(self.preset_file, 'r') as f:
                self.preset = json.load(f)
        else:
            self.preset = {
                'a_duration': 2.0,
                'a_to_b_duration': 1.0,
                'b_duration': 2.0,
                'b_to_a_duration': 1.0,
                'repeat_count': 1
            }

    def save_preset(self):
        with open(self.preset_file, 'w') as f:
            json.dump(self.preset, f)
    
    def open_dissolve_preset(self):
        preset_window = ctk.CTkToplevel(self)
        preset_window.title("디졸브 프리셋 설정")
        # preset_window.geometry("300x450")  # 높이를 400으로 증가

        def update_preset(event=None):
            try:
                self.preset = {
                    'a_duration': float(a_duration.get()),
                    'a_to_b_duration': float(a_to_b_duration.get()),
                    'b_duration': float(b_duration.get()),
                    'b_to_a_duration': float(b_to_a_duration.get()),
                    'repeat_count': int(repeat_count.get())
                }
                self.save_preset()
            except ValueError:
                pass  # 유효하지 않은 입력일 경우 무시

        # 프리셋 설정을 위한 입력 필드들
        ctk.CTkLabel(preset_window, text="A 사진 유지 시간 (초):").pack(pady=5)
        a_duration = ctk.CTkEntry(preset_window)
        a_duration.insert(0, str(self.preset['a_duration']))
        a_duration.pack(pady=5)
        a_duration.bind("<KeyRelease>", update_preset)

        ctk.CTkLabel(preset_window, text="A → B 디졸브 시간 (초):").pack(pady=5)
        a_to_b_duration = ctk.CTkEntry(preset_window)
        a_to_b_duration.insert(0, str(self.preset['a_to_b_duration']))
        a_to_b_duration.pack(pady=5)
        a_to_b_duration.bind("<KeyRelease>", update_preset)

        ctk.CTkLabel(preset_window, text="B 사진 유지 시간 (초):").pack(pady=5)
        b_duration = ctk.CTkEntry(preset_window)
        b_duration.insert(0, str(self.preset['b_duration']))
        b_duration.pack(pady=5)
        b_duration.bind("<KeyRelease>", update_preset)

        ctk.CTkLabel(preset_window, text="B → A 디졸브 시간 (초):").pack(pady=5)
        b_to_a_duration = ctk.CTkEntry(preset_window)
        b_to_a_duration.insert(0, str(self.preset['b_to_a_duration']))
        b_to_a_duration.pack(pady=5)
        b_to_a_duration.bind("<KeyRelease>", update_preset)

        ctk.CTkLabel(preset_window, text="반복 횟수:").pack(pady=5)
        repeat_count = ctk.CTkEntry(preset_window)
        repeat_count.insert(0, str(self.preset['repeat_count']))
        repeat_count.pack(pady=5)
        repeat_count.bind("<KeyRelease>", update_preset)

        def create_dissolve():
            if self.left_image_frame.frame_rect and self.right_image_frame.frame_rect:
                self.generate_dissolve_video(self.preset)
                preset_window.destroy()
            else:
                messagebox.showwarning("Warning", "Please create frames on both images before generating a dissolve video.")

        create_button = ctk.CTkButton(preset_window, text="디졸브 영상 생성", command=create_dissolve)
        create_button.pack(pady=20)

        # 프레임이 없을 경우 버튼 비활성화
        if not self.left_image_frame.frame_rect or not self.right_image_frame.frame_rect:
            create_button.configure(state="disabled")

        # 팝업창 중앙에 위치
        preset_window.update_idletasks()
        width = 300
        height = 450
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        preset_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))

        preset_window.transient(self)
        preset_window.grab_set()
        self.wait_window(preset_window)

    def generate_dissolve_video(self, settings):
        # 프레임 이미지 가져오기
        left_frame = self.save_frame_image(self.left_image_frame, None)
        right_frame = self.save_frame_image(self.right_image_frame, None)

        if left_frame is None or right_frame is None:
            messagebox.showerror("Error", "Failed to get frame images.")
            return

        # 여기에 디졸브 영상 생성 로직을 구현합니다.
        # PIL, numpy, OpenCV 등을 사용하여 구현할 수 있습니다.
        # 아래는 간단한 예시 코드입니다:

        import cv2
        import numpy as np

        # 이미지를 numpy 배열로 변환
        img_a = cv2.cvtColor(np.array(left_frame), cv2.COLOR_RGB2BGR)
        img_b = cv2.cvtColor(np.array(right_frame), cv2.COLOR_RGB2BGR)

        # 비디오 설정
        fps = 30
        frame_width = img_a.shape[1]
        frame_height = img_a.shape[0]
        
        # 저장 경로 설정
        save_path = filedialog.asksaveasfilename(defaultextension=".mp4",
                                                filetypes=[("MP4 files", "*.mp4")])
        if not save_path:
            return

        out = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))

        for _ in range(settings['repeat_count']):
            # A 이미지 유지
            for _ in range(int(settings['a_duration'] * fps)):
                out.write(img_a)

            # A에서 B로 디졸브
            for i in np.linspace(0, 1, int(settings['a_to_b_duration'] * fps)):
                frame = cv2.addWeighted(img_a, 1 - i, img_b, i, 0)
                out.write(frame)

            # B 이미지 유지
            for _ in range(int(settings['b_duration'] * fps)):
                out.write(img_b)

            # B에서 A로 디졸브
            for i in np.linspace(0, 1, int(settings['b_to_a_duration'] * fps)):
                frame = cv2.addWeighted(img_b, 1 - i, img_a, i, 0)
                out.write(frame)

        out.release()
        messagebox.showinfo("Success", "Dissolve video created successfully!")
    
    def reset_app(self):
        # 왼쪽 이미지 프레임 초기화
        self.left_image_frame.reset()
        self.left_image_loaded = False

        # 오른쪽 이미지 프레임 초기화
        self.right_image_frame.reset()
        self.right_image_loaded = False
        
        # 이벤트 바인딩 재설정
        self.bind_mousewheel()
        
        # 프레임 정보 완전히 제거
        self.left_image_frame.frame_rect = None
        self.right_image_frame.frame_rect = None
        
        # 버튼 상태 초기화
        self.transform_button.configure(state="disabled")
        self.make_frame_button.configure(state="disabled")

        # 포인트 입력 상태 초기화
        self.point_input_active = False
        
        # 창 크기 고정 해제
        self.resizable(True, True)
        self.size_fixed = False
        
        print("reset_app")
    
    def sync_right_frame(self, change, resize):
        if not self.right_image_frame.frame_rect:
            return
        
        if resize:
            dx1, dy1, dx2, dy2 = change
            right_coords = self.right_image_frame.canvas.coords(self.right_image_frame.frame_rect)
            new_right_coords = [
                right_coords[0] + dx1,
                right_coords[1] + dy1,
                right_coords[2] + dx1 + dx2,
                right_coords[3] + dy1 + dy2
            ]
            self.right_image_frame.canvas.coords(self.right_image_frame.frame_rect, *new_right_coords)
        else:
            dx, dy = change
            self.right_image_frame.canvas.move(self.right_image_frame.frame_rect, dx, dy)
    
    def simulate_drop(self, file_path, is_left=True):
        # 드롭 이벤트 시뮬레이션
        event = types.SimpleNamespace()
        event.data = file_path

        if is_left:
            self.drop_left(event)
        else:
            self.drop_right(event)

    def load_test_images(self):
        # 테스트 이미지 경로 (실제 경로로 변경 필요)
        left_image_path = "견본1.png"
        right_image_path = "견본2.png"

        # 왼쪽과 오른쪽 이미지에 대해 드롭 이벤트 시뮬레이션
        self.simulate_drop(left_image_path, is_left=True)
        self.simulate_drop(right_image_path, is_left=False)
    
    def start_frame_creation(self):
        self.save_state('frame_creation')
        
        self.left_image_frame.start_frame_creation()
        self.left_image_frame.frame_creation_callback = self.on_left_frame_created

    def on_left_frame_created(self, left_frame_coords):
        left_image = self.left_image_frame
        right_image = self.right_image_frame

        # 왼쪽 프레임과 첫 번째 포인트 사이의 거리 계산 (캔버스 좌표계에서)
        left_first_point_canvas = left_image.image_to_canvas(*left_image.points[0])
        dx = left_frame_coords[0] - left_first_point_canvas[0]
        dy = left_frame_coords[1] - left_first_point_canvas[1]

        print(f"Left frame difference (canvas coords): {dx}, {dy}")

        # 오른쪽 이미지의 첫 번째 포인트 (캔버스 좌표계로 변환)
        right_first_point_canvas = right_image.image_to_canvas(*right_image.points[0])

        # 오른쪽 프레임의 좌상단 좌표 계산 (캔버스 좌표계에서)
        right_frame_top_left = (right_first_point_canvas[0] + dx, right_first_point_canvas[1] + dy)

        # 프레임 크기 계산
        frame_width = left_frame_coords[2] - left_frame_coords[0]
        frame_height = left_frame_coords[3] - left_frame_coords[1]

        # 오른쪽 프레임의 좌표 계산
        right_frame_coords = (
            right_frame_top_left[0],
            right_frame_top_left[1],
            right_frame_top_left[0] + frame_width,
            right_frame_top_left[1] + frame_height
        )

        print(f"Right frame coords (canvas): {right_frame_coords}")

        # 오른쪽 이미지에 프레임 생성
        self.right_image_frame.create_frame(right_frame_coords)
    
    def save_selected_frame(self):
        if not self.left_image_frame.frame_rect or not self.right_image_frame.frame_rect:
            messagebox.showerror("Error", "Please create frames on both images before saving.")
            return

        save_options = ctk.CTkToplevel(self)
        save_options.title("저장 옵션")
        save_options.geometry("300x150")
       
        save_mode = tk.StringVar(value="separate")
        ctk.CTkRadioButton(save_options, text="개별 저장", variable=save_mode, value="separate").pack(pady=5)
        ctk.CTkRadioButton(save_options, text="통합 저장", variable=save_mode, value="single").pack(pady=5)

        def on_save():
            save_path = filedialog.asksaveasfilename(filetypes=[("PNG files", "*.png")])
            if save_path:
                if save_mode.get() == "separate":
                    self.save_frame_image(self.left_image_frame, save_path + "_left.png")
                    self.save_frame_image(self.right_image_frame, save_path + "_right.png")
                else:
                    self.save_combined_image(save_path)
                # self.left_image_frame.clear_frame()
                # self.right_image_frame.clear_frame()
                # self.reset_app()
                
            save_options.destroy()

        def set_popup_center():
            """팝업창 위치 정중앙에 배치"""
            x = self.winfo_x() + (self.winfo_width() // 2) - (300 // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (150 // 2)
            save_options.geometry(f"300x150+{x}+{y}")
            
        ctk.CTkButton(save_options, text="저장", command=on_save).pack(pady=10)
        
        # 팝업창 최상위로 띄우기
        set_popup_center()
        save_options.transient(self)
        save_options.grab_set()
        self.wait_window(save_options)

    def save_frame_image(self, image_frame, save_path):
        if not image_frame.frame_rect:
            messagebox.showerror("Error", "No frame to save.")
            return

        # Get the frame coordinates in canvas space
        canvas_coords = image_frame.canvas.coords(image_frame.frame_rect)
        
        # Get the entire canvas as an image
        canvas_image = ImageTk.getimage(image_frame.photo_image)
        
        # Crop the image using the frame coordinates
        frame_image = canvas_image.crop((
            int(canvas_coords[0] - image_frame.canvas_image_x + canvas_image.width / 2),
            int(canvas_coords[1] - image_frame.canvas_image_y + canvas_image.height / 2),
            int(canvas_coords[2] - image_frame.canvas_image_x + canvas_image.width / 2),
            int(canvas_coords[3] - image_frame.canvas_image_y + canvas_image.height / 2)
        ))
        
        if save_path:
            frame_image.save(save_path)
        else:
            return frame_image

    def save_combined_image(self, save_path):
        left_frame = self.save_frame_image(self.left_image_frame, None)
        right_frame = self.save_frame_image(self.right_image_frame, None)

        if left_frame is None or right_frame is None:
            messagebox.showerror("Error", "Failed to save one or both frames.")
            return

        print(f"왼쪽 넓이: {left_frame.width}")
        print(f"오른쪽 넓이: {right_frame.width}")
        
        combined_width = left_frame.width + right_frame.width
        print(f"합쳐진 넓이: {combined_width}")
        
        combined_height = max(left_frame.height, right_frame.height)
        combined_image = Image.new('RGB', (combined_width, combined_height))

        combined_image.paste(left_frame, (0, 0))
        combined_image.paste(right_frame, (left_frame.width, 0))
        combined_image.save(save_path + ".png")


    def update_transform_button(self):
        if self.left_image_loaded and self.right_image_loaded:
            self.transform_button.configure(state="normal")
        else:
            self.transform_button.configure(state="disabled")

    def update_make_frame_button(self):
        if len(self.left_image_frame.points) + len(self.right_image_frame.points) == 4:
            self.make_frame_button.configure(state="normal")
        else:
            self.make_frame_button.configure(state="disabled")
    
    def transform_image(self):
        print(f'이미지 변환')
        
        self.save_state('transform')
        
        left_distance, left_slope = self.left_image_frame.get_point_distance_and_slope()
        left_image_size = self.left_image_frame.display_image.size
        left_zoom_factor = self.left_image_frame.get_zoom_factor()
        
        if left_distance is not None and left_slope is not None:
            success = self.right_image_frame.transform_image(left_distance, left_slope, left_image_size, left_zoom_factor)
            if success:
                self.update_transform_button()
                self.unbind_mousewheel()
                self.right_image_frame.transformed_image = True
                
    def set_point_input(self, is_active):
        self.left_image_frame.set_point_input_active(is_active)
        self.right_image_frame.set_point_input_active(is_active)
        status = "activated" if is_active else "deactivated"
        print(f"Point input {status}")
        self.update_transform_button()

    def drop_left(self, event):
        self.handle_drop(event, self.left_image_frame)

    def drop_right(self, event):
        self.handle_drop(event, self.right_image_frame)

    def handle_drop(self, event, frame):
        self.save_state('load_image')
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'): # Windows quirk
            file_path = file_path[1:-1]
        if os.path.isfile(file_path):
            try:
                pil_image = Image.open(file_path)
                
                if frame == self.left_image_frame:
                    self.left_image_loaded = True
                    if self.right_image_loaded and self.right_image_frame.image:
                        # Resize left image to match right image
                        pil_image = pil_image.resize(self.right_image_frame.image.size, Image.LANCZOS)
                else:  # right image frame
                    self.right_image_loaded = True
                    if self.left_image_loaded and self.left_image_frame.image:
                        # Resize right image to match left image
                        pil_image = pil_image.resize(self.left_image_frame.image.size, Image.LANCZOS)
                        # Also resize the left image to ensure it's updated
                        self.resize_left_image(pil_image.size)
                
                frame.set_image(pil_image)
                self.update_transform_button()
            except Exception as e:
                print(f"Error loading image: {e}")
                # 에러 발생 시 상태 초기화
                frame.reset()
                if frame == self.left_image_frame:
                    self.left_image_loaded = False
                else:
                    self.right_image_loaded = False

    def resize_left_image(self, new_size):
        if self.left_image_frame.image:
            resized_image = self.left_image_frame.image.resize(new_size, Image.LANCZOS)
            self.left_image_frame.set_image(resized_image)
                
    def bind_mousewheel(self):
        self.left_image_frame.canvas.bind("<MouseWheel>", self.left_image_frame.on_mousewheel)
        self.right_image_frame.canvas.bind("<MouseWheel>", self.right_image_frame.on_mousewheel)

    def unbind_mousewheel(self):
        self.left_image_frame.canvas.unbind("<MouseWheel>")
        self.right_image_frame.canvas.unbind("<MouseWheel>")
if __name__ == "__main__":
    app = ImageProcessingApp()
    app.mainloop()