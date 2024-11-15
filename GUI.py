import os
import cv2
import platform
import numpy as np
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from datetime import datetime
from natsort import natsorted

class CameraApp:
    def __init__(self, root):
        # Store all parameters
        self.root = root
        self.root.withdraw()  # Hide the root window

        self.size_ratio = 0.3       # Initial size ratio
        self.spacing_ratio = 0.5    # Initial spacing ratio
        self.offset_ratio = 0.0     # Initial offset ratio

        # Open the camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Could not open video device")
        self.cap_fps = self.cap.get(cv2.CAP_PROP_FPS)

        # Link to display and control panel
        self.control_panel = ControlPanel(self)
        self.display_window = DisplayWindow(self)

        # Camera state
        self.preview = True  # Start in live preview mode
        self.frame_num = 0
        self.loaded_frames = []
        self.recording = False
        self.recorded_frames = []
        self.delay = int(1000/self.cap_fps)

    def run(self):
        """Start capturing and displaying images continuously."""
        self.capture_and_display()
        self.root.mainloop()

    def capture_and_display(self):
        if self.preview:
            # Live preview mode
            ret, frame = self.cap.read()
            if not ret:
                print("Warning: Failed to capture frame.")
                self.root.after(100, self.capture_and_display) # retry
                return

            # Split frame into left and right views
            square_size = min(frame.shape[0], frame.shape[1])
            left_frame = frame[:square_size, :square_size]
            right_frame = frame[-square_size:, -square_size:]

            # Save frame to recorded_frames if recording
            if self.recording:
                self.recorded_frames.append((left_frame, right_frame))

            # Display frames
            self.left_img_pil = Image.fromarray(cv2.cvtColor(left_frame, cv2.COLOR_BGR2RGB))
            self.right_img_pil = Image.fromarray(cv2.cvtColor(right_frame, cv2.COLOR_BGR2RGB))
            self.display_window.display_stereo_images(self.left_img_pil, self.right_img_pil)

        else:
            # Playback mode
            left_frame, right_frame = self.loaded_frames[self.frame_num]
            self.frame_num += 1
            if self.frame_num >= len(self.loaded_frames):
                self.frame_num = 0

            # Convert frames to PIL images for display
            left_img_pil = Image.fromarray(cv2.cvtColor(left_frame, cv2.COLOR_BGR2RGB))
            right_img_pil = Image.fromarray(cv2.cvtColor(right_frame, cv2.COLOR_BGR2RGB))
            self.display_window.display_stereo_images(left_img_pil, right_img_pil)

        # Schedule next frame based on FPS
        self.root.after(self.delay, self.capture_and_display)

    def save_image(self):
        # Get currently displayed image
        left_img_pil = self.left_img_pil
        right_img_pil = self.right_img_pil
        if not isinstance(left_img_pil, Image.Image) or not isinstance(right_img_pil, Image.Image):
            print("Error: One of the images is not a PIL.Image instance")
            return

        folder = filedialog.askdirectory(title="Select Folder to Save Image", initialdir=os.getcwd())
        if not folder:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        left_path = os.path.join(folder, f"{timestamp}_left_image.png")
        right_path = os.path.join(folder, f"{timestamp}_right_image.png")

        # Convert from PIL to OpenCV format
        left_img_cv = cv2.cvtColor(np.array(left_img_pil), cv2.COLOR_RGB2BGR)
        right_img_cv = cv2.cvtColor(np.array(right_img_pil), cv2.COLOR_RGB2BGR)
        
        # Save the images
        cv2.imwrite(left_path, left_img_cv)
        cv2.imwrite(right_path, right_img_cv)
        print(f"Saved stereo images: {left_path} and {right_path}")

    def save_recording(self):
        # Stop recording mode
        self.recording = False
        self.display_window.hide_recording_indicator()

        folder = filedialog.askdirectory(title="Select Folder to Save Video", initialdir=os.getcwd())
        if not folder:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        left_path = os.path.join(folder, f"{timestamp}_left_video.avi")
        right_path = os.path.join(folder, f"{timestamp}_right_video.avi")

        # Set up video writers
        height, width = self.recorded_frames[0][0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        left_writer = cv2.VideoWriter(left_path, fourcc, self.cap_fps, (width, height))
        right_writer = cv2.VideoWriter(right_path, fourcc, self.cap_fps, (width, height))
        
        # Write frames to video files
        for left_frame, right_frame in self.recorded_frames:
            left_writer.write(left_frame)
            right_writer.write(right_frame)
        
        # Release video writers
        left_writer.release()
        right_writer.release()
        print(f"Saved stereo videos: {left_path} and {right_path}")
    
    def load_media(self):
        folder = filedialog.askdirectory(title="Select Folder to Load Media", initialdir=os.getcwd())
        if not folder:
            return

        for filename in natsorted(os.listdir(folder)):
            if "left" in filename:
                left_path = os.path.join(folder, filename)
            elif "right" in filename:
                right_path = os.path.join(folder, filename)
        if not left_path or not right_path:
            print("Error: Could not find both left and right media files in the selected folder.")
            return
        
        # Setup for playback
        ext = left_path.split(".")[-1].lower()
        if ext in ["png", "jpg", "jpeg"]:
            # Load stereo images as a single frame with infinite FPS
            left_image = cv2.imread(left_path)
            right_image = cv2.imread(right_path)
            self.loaded_frames = [(left_image, right_image)]
            self.delay = self.delay = int(1000/self.cap_fps)
            print(f"Loaded stereo images: {left_path} and {right_path}")

        elif ext in ["avi", "mp4"]:
            # Load stereo video frames
            left_cap = cv2.VideoCapture(left_path)
            right_cap = cv2.VideoCapture(right_path)
            self.loaded_frames = []

            # Read frames from both videos and store them in loaded_frames
            while left_cap.isOpened() and right_cap.isOpened():
                ret_left, left_frame = left_cap.read()
                ret_right, right_frame = right_cap.read()
                if not (ret_left and ret_right):
                    break
                self.loaded_frames.append((left_frame, right_frame))

            # Set FPS from the video file's FPS
            self.delay = int(1000/left_cap.get(cv2.CAP_PROP_FPS))
            left_cap.release()
            right_cap.release()
            print(f"Loaded stereo videos: {left_path} and {right_path}")

        else:
            print("Error: Unsupported file format.")
            return

        # Switch to playback mode
        self.preview = False
        self.frame_num = 0                   

    def update_display_settings(self, new_size, new_spacing, new_offset):
        """Update display settings and notify display."""
        self.size_ratio = new_size
        self.spacing_ratio = new_spacing
        self.offset_ratio = new_offset
        self.display_window.update_parameters(self)

    def on_close(self):
        """Cleanly exit the application."""
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

class DisplayWindow:
    def __init__(self, app):
        self.app = app
        self.display_window = tk.Toplevel(app.root)
        self.display_window.title("Display")

        # Set to fullscreen
        if platform.system() == "Windows":
            self.display_window.state("zoomed")
        else:
            try:
                self.display_window.attributes("-fullscreen", True)
            except Exception:
                # Set the display window to maximize if fullscreen fails
                screen_width = self.display_window.winfo_screenwidth()
                screen_height = self.display_window.winfo_screenheight()
                self.display_window.geometry(f"{screen_width}x{screen_height}")
        
        # exit on close
        self.display_window.protocol("WM_DELETE_WINDOW", app.on_close)

        # Create a canvas filling the whole window
        self.canvas = tk.Canvas(self.display_window, bg="black")
        self.canvas.pack(fill="both", expand=True)

        # Bind <Configure> (resize or reposition) to update_parameters for dynamic resizing
        self.canvas.bind("<Configure>", lambda event: self.update_parameters(self.app))

        # Initial calculation of x, y, width, and height for the two displays
        self.update_parameters(app)

        # Create a dummy image to initialize left and right images on the canvas
        dummy_image = Image.new("RGB", (self.display_size, self.display_size), "black")
        dummy_img_tk = ImageTk.PhotoImage(dummy_image)
        self.left_image_id = self.canvas.create_image(self.left_x, self.y, anchor="center", image=dummy_img_tk)
        self.right_image_id = self.canvas.create_image(self.right_x, self.y, anchor="center", image=dummy_img_tk)
        
        self.recording_indicator = None

    def update_parameters(self, app):
        """Recalculate x, y, width, height for the displays based on app parameters."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        display_size = max(int(canvas_width * app.size_ratio), 1)
        center_spacing = int(canvas_width * app.spacing_ratio / 2)
        center_offset = int(canvas_width * app.offset_ratio)

        self.left_x = (canvas_width // 2) - center_spacing + center_offset
        self.right_x = (canvas_width // 2) + center_spacing + center_offset
        self.y = canvas_height // 2
        self.display_size = display_size

    def display_stereo_images(self, left_img_pil, right_img_pil):
        """Display the stereo pair of PIL images on the canvas."""
        
        # Resize both left and right images to the display size
        left_img_resized = left_img_pil.resize((self.display_size, self.display_size), Image.LANCZOS)
        right_img_resized = right_img_pil.resize((self.display_size, self.display_size), Image.LANCZOS)

        # Convert PIL images to ImageTk format for Tkinter compatibility
        left_img_tk = ImageTk.PhotoImage(left_img_resized)
        right_img_tk = ImageTk.PhotoImage(right_img_resized)

        # Update the left and right images on the canvas
        self.canvas.coords(self.left_image_id, self.left_x, self.y)
        self.canvas.coords(self.right_image_id, self.right_x, self.y)
        self.canvas.itemconfig(self.left_image_id, image=left_img_tk)
        self.canvas.itemconfig(self.right_image_id, image=right_img_tk)

        # Store references to avoid garbage collection
        self.canvas.left_image_ref = left_img_tk
        self.canvas.right_image_ref = right_img_tk
    
    def show_recording_indicator(self):
        if self.recording_indicator is None:
            self.recording_indicator = self.canvas.create_text(
                20, 20, anchor="nw", text="● Recording", fill="red", font=("Arial", 14, "bold"))

    def hide_recording_indicator(self):
        if self.recording_indicator is not None:
            self.canvas.delete(self.recording_indicator)
            self.recording_indicator = None

class ControlPanel:
    def __init__(self, app):
        self.app = app

        # Create the control panel as a Toplevel window
        self.control_panel = tk.Toplevel(app.root)
        self.control_panel.title("Control Panel")
        self.control_panel.geometry("600x600")

        # exit on close
        self.control_panel.protocol("WM_DELETE_WINDOW", app.on_close)

        # Set up a grid layout for sections
        self.control_panel.grid_rowconfigure(0, weight=1)
        self.control_panel.grid_rowconfigure(1, weight=50)
        self.control_panel.grid_rowconfigure(2, weight=1)
        self.control_panel.grid_rowconfigure(3, weight=1)
        self.control_panel.grid_columnconfigure(0, weight=1)
        self.control_panel.grid_columnconfigure(1, weight=1)

        # Camera parameters sections
        self.left_camera_frame = tk.LabelFrame(self.control_panel, text="Left Camera")
        self.left_camera_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.right_camera_frame = tk.LabelFrame(self.control_panel, text="Right Camera")
        self.right_camera_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.init_camera_controls()

        # Calibration and Analysis section
        self.calibration_frame = tk.LabelFrame(self.control_panel, text="Calibration and Analysis")
        self.calibration_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.init_calibration_analysis()

        # Save and Load section
        self.save_load_frame = tk.LabelFrame(self.control_panel, text="Save and Load")
        self.save_load_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.init_save_load()

        # Display Settings section
        self.display_settings_frame = tk.LabelFrame(self.control_panel, text="Display Settings")
        self.display_settings_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.init_display_settings()

    def init_calibration_analysis(self):
        """Initialize Calibration and Analysis section with sub-frames for each analysis."""
        # Configure layout
        self.calibration_frame.grid_rowconfigure(0, weight=1)
        self.calibration_frame.grid_columnconfigure(0, weight=1)
        self.calibration_frame.grid_columnconfigure(1, weight=1)
        self.calibration_frame.grid_columnconfigure(2, weight=1)
        
        # Checkerboard Calibration
        self.checkerboard_frame = tk.LabelFrame(self.calibration_frame, text="Checkerboard Calibration")
        self.checkerboard_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Lens Shading Calibration
        self.lens_shading_frame = tk.LabelFrame(self.calibration_frame, text="Lens Shading Calibration")
        self.lens_shading_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Color Chart Analysis
        self.color_analysis_frame = tk.LabelFrame(self.calibration_frame, text="Color Chart Analysis")
        self.color_analysis_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

    def init_camera_controls(self):
        # Create sliders for left 
        self.left_camera_frame.grid_columnconfigure(0, weight=1)
        self.left_exposure = self.create_slider(
            self.left_camera_frame, "Exposure", 1, 100, 1, 50, 
            0, 0, self.update_left_camera_setting)
        self.left_gain = self.create_slider(
            self.left_camera_frame, "Gain", 1, 10, 0.1, 1, 
            1, 0, self.update_left_camera_setting)
        self.left_white_balance = self.create_slider(
            self.left_camera_frame, "White Balance", 2800, 6500, 100, 4000, 
            2, 0, self.update_left_camera_setting)
        self.left_focus = self.create_slider(
            self.left_camera_frame, "Focus", 0, 255, 1, 128, 
            3, 0, self.update_left_camera_setting)
        self.left_denoising = self.create_slider(
            self.left_camera_frame, "Denoising Strength", 0, 1, 0.05, 0.5, 
            4, 0, self.update_left_camera_setting)

        # Create sliders for right camera
        self.right_camera_frame.grid_columnconfigure(0, weight=1)
        self.right_exposure = self.create_slider(
            self.right_camera_frame, "Exposure", 1, 100, 1, 50, 
            0, 0, self.update_right_camera_setting)
        self.right_gain = self.create_slider(
            self.right_camera_frame, "Gain", 1, 10, 0.1, 1, 
            1, 0, self.update_right_camera_setting)
        self.right_white_balance = self.create_slider(
            self.right_camera_frame, "White Balance", 2800, 6500, 100, 4000, 
            2, 0, self.update_right_camera_setting)
        self.right_focus = self.create_slider(
            self.right_camera_frame, "Focus", 0, 255, 1, 128, 
            3, 0, self.update_right_camera_setting)
        self.right_denoising = self.create_slider(
            self.right_camera_frame, "Denoising Strength", 0, 1, 0.05, 0.5, 
            4, 0, self.update_right_camera_setting)
        
    def init_save_load(self):
        self.save_load_frame.grid_columnconfigure(0, weight=1)
        self.save_load_frame.grid_columnconfigure(1, weight=1)
        self.save_load_frame.grid_columnconfigure(2, weight=1)
        self.save_load_frame.grid_columnconfigure(3, weight=1)
        self.save_load_frame.grid_columnconfigure(4, weight=1)

        # Capture Button
        self.capture_button = tk.Button(self.save_load_frame, text="Capture", command=self.capture_image)
        self.capture_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Record Button
        self.record_button = tk.Button(self.save_load_frame, text="Record", command=self.start_recording)
        self.record_button.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        # Save Recording Button
        self.save_recording_button = tk.Button(self.save_load_frame, text="Save Recording", command=self.save_recording)
        self.save_recording_button.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")

        # Load Button
        self.load_button = tk.Button(self.save_load_frame, text="Load", command=self.load_media)
        self.load_button.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        # Preview Button
        self.preview_button = tk.Button(self.save_load_frame, text="Preview", command=self.start_preview)
        self.preview_button.grid(row=0, column=4, padx=5, pady=5, sticky="nsew")

    def init_display_settings(self):
        self.display_settings_frame.grid_columnconfigure(0, weight=1)
        self.display_settings_frame.grid_columnconfigure(1, weight=1)
        self.display_settings_frame.grid_columnconfigure(2, weight=1)

        # Add sliders to the bottom row of the Display Settings section
        self.size_slider = self.create_slider(self.display_settings_frame, "Size Ratio", 
                                              0.1, 0.5, 0.05, self.app.size_ratio, 0, 0,
                                              self.update_display_settings)
        self.spacing_slider = self.create_slider(self.display_settings_frame, "Spacing Ratio", 
                                                 0.25, 0.75, 0.05, self.app.spacing_ratio, 0, 1,
                                                 self.update_display_settings)
        self.offset_slider = self.create_slider(self.display_settings_frame, "Offset Ratio", 
                                                -0.25, 0.25, 0.05, self.app.offset_ratio, 0, 2,
                                                self.update_display_settings)

    def create_slider(self, parent, label, min_val, max_val, res, initial_val, row, col, callback):
        """Create a slider within a given parent frame and place it in a specified grid."""
        slider = tk.Scale(parent, from_=min_val, to=max_val, label=label, orient="horizontal", resolution=res)
        slider.set(initial_val)
        
        # Place the slider in the specified grid
        slider.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
        
        # Bind the slider movement to update the display settings in CameraApp
        slider.bind("<Motion>", lambda event: callback())
        slider.bind("<ButtonRelease-1>", lambda event: callback())
        
        return slider

    def capture_image(self):
        self.app.save_image()

    def start_recording(self):
        self.app.recording = True
        self.app.recorded_frames = []
        self.app.display_window.show_recording_indicator()
        self.update_button_states()

    def save_recording(self):
        self.app.save_recording()
        self.update_button_states()

    def load_media(self):
        self.app.load_media()
        self.update_button_states()

    def start_preview(self):
        self.app.preview = True
        self.update_button_states()
    
    def update_button_states(self):
        """Update button states based on the current app mode."""
        if self.app.preview:
            if self.app.recording:
                self.capture_button.config(state="disabled")
                self.record_button.config(state="disabled")
                self.load_button.config(state="disabled")
                self.preview_button.config(state="disabled")
                self.save_recording_button.config(state="normal")
            else:
                self.capture_button.config(state="normal")
                self.record_button.config(state="normal")
                self.load_button.config(state="normal")
                self.preview_button.config(state="disabled")
                self.save_recording_button.config(state="disabled")
        else:
            # Playback or loaded media mode
            self.capture_button.config(state="disabled")
            self.record_button.config(state="disabled")
            self.load_button.config(state="disabled")
            self.preview_button.config(state="normal")
            self.save_recording_button.config(state="disabled")
    
    def update_display_settings(self):
        """Retrieve slider values and call app to update display settings."""
        size_ratio = self.size_slider.get()
        spacing_ratio = self.spacing_slider.get()
        offset_ratio = self.offset_slider.get()
        
        # Call the app method to update the display settings with the new values
        self.app.update_display_settings(size_ratio, spacing_ratio, offset_ratio)
    
    def update_left_camera_setting(self):
        exposure = self.left_exposure.get()
        gain = self.left_gain.get()
        white_balance = self.left_white_balance.get()
        focus = self.left_focus.get()
        denoising = self.left_denoising.get()

        # Send updated settings to the app for the left camera
        self.app.update_left_camera(exposure, gain, white_balance, focus, denoising)

    def update_right_camera_setting(self):
        exposure = self.right_exposure.get()
        gain = self.right_gain.get()
        white_balance = self.right_white_balance.get()
        focus = self.right_focus.get()
        denoising = self.right_denoising.get()

        # Send updated settings to the app for the right camera
        self.app.update_right_camera(exposure, gain, white_balance, focus, denoising)

# Main execution
root = tk.Tk()
app = CameraApp(root)
app.run()
