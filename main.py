import customtkinter as ctk  # Modern GUI widget library built on top of Tkinter
import tkinter as tk  # Standard Python GUI library used for high-performance canvas drawing
import threading  # Allows background network queries and TTS synthesis without freezing UI
import datetime  # Formats real-time message timestamps (e.g., 21:55)
import math  # Provides trigonometric functions (sin, cos) for smooth continuous animation
from brain import ask_jarvis, reset_chat_history  # Import AI query and conversation reset functions
from tts import speak, stop_speech  # Import speech synthesis and speech interruption functions

# ================= APPLE TYPOGRAPHY & BLUE PALETTE =================
FONT_FAMILY = "Futura"  # Clean geometric font family matching Apple aesthetic
FONT_TITLE = (FONT_FAMILY, 18, "bold")  # Top navigation title font
FONT_SUBTITLE = (FONT_FAMILY, 9, "bold")  # Pill badge subtitle font
FONT_STATUS = (FONT_FAMILY, 11, "bold")  # Central status label font
FONT_BODY = (FONT_FAMILY, 13)  # Message card text font
FONT_TIME = (FONT_FAMILY, 9)  # Small timestamp label font
FONT_INPUT = (FONT_FAMILY, 13)  # Text input field font
FONT_BTN = (FONT_FAMILY, 11, "bold")  # Action button font

COLOR_BG = "#000000"           # Pure Apple OLED Black background
COLOR_CARD_JARVIS = "#12141a"  # Frosted Dark Blue-Gray for assistant cards
COLOR_CARD_USER = "#0071e3"    # Apple Signature Blue for user cards
COLOR_CARD_BORDER = "#1c2230"  # Subtle blue-tinted divider border
COLOR_TEXT_PRIMARY = "#f5f5f7" # Apple crisp off-white text
COLOR_TEXT_MUTED = "#5b7094"   # Muted slate blue text for labels and secondary info
COLOR_DOCK = "#10131a"         # Dark floating dock container background

ctk.set_appearance_mode("Dark")  # Force dark theme mode
ctk.set_default_color_theme("blue")  # Use blue accent theme

class JarvisAppleApp(ctk.CTk):
    """
    Main application window implementing an Apple-inspired minimalist GUI
    with a central responsive audio visualizer and resizable chat pane.
    """
    def __init__(self):
        super().__init__()  # Initialize the underlying CustomTkinter root window

        self.title("Jarvis")  # Set window title
        self.geometry("880x860")  # Set default window dimensions
        self.minsize(700, 600)  # Enforce minimum window size to prevent layout breakage
        self.configure(fg_color=COLOR_BG)  # Set window background color to pure black

        self.voice_enabled = True  # Toggle flag controlling whether TTS audio is played
        self.visualizer_state = "idle"  # Visualizer animation state: 'idle', 'thinking', or 'speaking'
        self.anim_t = 0.0  # Time accumulator variable driving continuous wave math

        self.top_weight = 65  # Default top visualizer row weight (65% of screen height)
        self.bottom_weight = 35  # Default bottom chat/dock row weight (35% of screen height)

        # Build UI layout components
        self._setup_grid_layout()  # Configure resizable grid rows and columns
        self._build_header()  # Build top navigation header
        self._build_visualizer_pane()  # Build upper 65% visualizer pane
        self._build_draggable_splitter()  # Build draggable divider handle
        self._build_chat_and_dock_pane()  # Build lower 35% chat feed and input dock

        self._animate_visualizer()  # Launch 60 FPS animation loop for glowing circle

        # Display initial welcome greeting card from Jarvis
        self.add_jarvis_card("Hi, I am Jarvis, your personal AI assistant. How can I help you today?")

    # ================= GRID & SIZING =================
    def _setup_grid_layout(self):
        """Sets up the 4-row grid with dynamic weights for smooth proportional resizing."""
        self.grid_columnconfigure(0, weight=1)  # Single column that expands horizontally
        self.grid_rowconfigure(0, weight=0)                  # Row 0: Top Header (fixed height)
        self.grid_rowconfigure(1, weight=self.top_weight)    # Row 1: Visualizer Canvas (65% default)
        self.grid_rowconfigure(2, weight=0)                  # Row 2: Draggable Splitter Handle (fixed height)
        self.grid_rowconfigure(3, weight=self.bottom_weight) # Row 3: Chat Scroll and Dock (35% default)

    # ================= 1. HEADER =================
    def _build_header(self):
        """Constructs the minimalist top header containing title and quick-action controls."""
        header = ctk.CTkFrame(self, fg_color="transparent", height=42)  # Transparent header frame
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(14, 4))  # Place at top row

        title_box = ctk.CTkFrame(header, fg_color="transparent")  # Title container
        title_box.pack(side="left")  # Align to left side

        ctk.CTkLabel(
            title_box,
            text="JARVIS",  # App brand name
            font=FONT_TITLE,  # Bold Futura title font
            text_color=COLOR_TEXT_PRIMARY  # Crisp white text
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            title_box,
            text="INTELLIGENCE",  # Subtitle badge text
            font=FONT_SUBTITLE,  # Small bold font
            text_color="#38bdf8",  # Electric sky blue text
            fg_color="#0a192f",  # Deep navy badge background
            corner_radius=8,  # Rounded pill corners
            padx=8,  # Horizontal badge padding
            pady=2  # Vertical badge padding
        ).pack(side="left")

        ctrl_box = ctk.CTkFrame(header, fg_color="transparent")  # Controls container
        ctrl_box.pack(side="right")  # Align to right side

        # Voice audio toggle button (On / Off)
        self.voice_btn = ctk.CTkButton(
            ctrl_box,
            text="Voice: On",
            width=78,
            height=26,
            font=FONT_BTN,
            fg_color="#0c1726",
            hover_color="#142640",
            corner_radius=13,
            text_color=COLOR_TEXT_PRIMARY,
            command=self.toggle_voice
        )
        self.voice_btn.pack(side="left", padx=4)

        # Immediate speech stop button
        self.stop_btn = ctk.CTkButton(
            ctrl_box,
            text="Stop",
            width=54,
            height=26,
            font=FONT_BTN,
            fg_color="#0c1726",
            hover_color="#1f2d45",
            corner_radius=13,
            text_color="#60a5fa",
            command=self.stop_speech
        )
        self.stop_btn.pack(side="left", padx=4)

        # Conversation clear button
        self.clear_btn = ctk.CTkButton(
            ctrl_box,
            text="Clear",
            width=54,
            height=26,
            font=FONT_BTN,
            fg_color="#0c1726",
            hover_color="#142640",
            corner_radius=13,
            text_color=COLOR_TEXT_MUTED,
            command=self.clear_conversation
        )
        self.clear_btn.pack(side="left", padx=4)

    # ================= 2. CENTRAL VISUALIZER (65%) =================
    def _build_visualizer_pane(self):
        """Builds the upper visualizer pane containing the animated canvas and status label."""
        self.vis_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)  # Black frame container
        self.vis_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=2)  # Place in row 1

        # High-performance Tkinter Canvas for smooth circle rendering
        self.canvas = tk.Canvas(
            self.vis_frame,
            bg=COLOR_BG,  # Match pure black background
            highlightthickness=0  # Remove default canvas border
        )
        self.canvas.pack(fill="both", expand=True)  # Expand to fill entire visualizer frame

        # Text label displaying current assistant state (READY, THINKING, SPEAKING)
        self.status_label = ctk.CTkLabel(
            self.vis_frame,
            text="READY",
            font=FONT_STATUS,
            text_color=COLOR_TEXT_MUTED
        )
        self.status_label.pack(side="bottom", pady=(0, 6))  # Position at bottom of visualizer

    def _animate_visualizer(self):
        """
        Smooth 60 FPS animation loop rendering the glowing visualizer circle.
        Renders exclusively in shades of blue and scales dynamically with window size.
        """
        self.anim_t += 0.025  # Smooth continuous phase increment
        self.canvas.delete("all")  # Clear previous frame vector shapes

        # Calculate dynamic canvas center and proportional base radius
        w = max(100, self.canvas.winfo_width())  # Current canvas pixel width
        h = max(100, self.canvas.winfo_height())  # Current canvas pixel height
        cx = w / 2  # Horizontal center coordinate
        cy = h / 2  # Vertical center coordinate
        base_r = min(w, h) * 0.22  # Scale base radius dynamically with available space

        if self.visualizer_state == "idle":
            # Idle Mode: Gentle, calming breathing motion in deep blue tones
            breathe = math.sin(self.anim_t * 1.5) * (base_r * 0.08)  # Subtle sinusoidal expansion

            # Outer deep navy aura ring
            self.canvas.create_oval(cx - (base_r + 34 + breathe), cy - (base_r + 34 + breathe),
                                    cx + (base_r + 34 + breathe), cy + (base_r + 34 + breathe),
                                    outline="#061830", width=3)
            # Intermediate royal blue ring
            self.canvas.create_oval(cx - (base_r + 18 + breathe * 0.7), cy - (base_r + 18 + breathe * 0.7),
                                    cx + (base_r + 18 + breathe * 0.7), cy + (base_r + 18 + breathe * 0.7),
                                    outline="#1e40af", width=2.5)
            # Inner electric blue glowing halo
            self.canvas.create_oval(cx - (base_r + breathe * 0.4), cy - (base_r + breathe * 0.4),
                                    cx + (base_r + breathe * 0.4), cy + (base_r + breathe * 0.4),
                                    outline="#0a84ff", width=2)
            # Glowing core disk
            core_r = max(18, base_r * 0.42)
            self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                                    fill="#1d4ed8", outline="#38bdf8", width=2)
            # Bright central highlight
            self.canvas.create_oval(cx - (core_r * 0.45), cy - (core_r * 0.45),
                                    cx + (core_r * 0.45), cy + (core_r * 0.45),
                                    fill="#60a5fa", outline="#e0f2fe", width=1)

        elif self.visualizer_state == "thinking":
            # Thinking Mode: Fast orbiting arcs and pulsating energy in vibrant blues
            pulse = math.sin(self.anim_t * 4.0) * (base_r * 0.09)  # Rapid pulsation
            angle = (self.anim_t * 120) % 360  # Continuous rotation angle in degrees

            # Outer boundary ring
            self.canvas.create_oval(cx - (base_r + 36 + pulse), cy - (base_r + 36 + pulse),
                                    cx + (base_r + 36 + pulse), cy + (base_r + 36 + pulse),
                                    outline="#071a33", width=3)
            # Primary rotating sky blue arc
            self.canvas.create_arc(cx - (base_r + 20 + pulse), cy - (base_r + 20 + pulse),
                                   cx + (base_r + 20 + pulse), cy + (base_r + 20 + pulse),
                                   start=angle, extent=130, outline="#38bdf8", width=3.5, style="arc")
            # Counter-rotating electric blue arc
            self.canvas.create_arc(cx - (base_r + 20 + pulse), cy - (base_r + 20 + pulse),
                                   cx + (base_r + 20 + pulse), cy + (base_r + 20 + pulse),
                                   start=angle + 180, extent=115, outline="#0a84ff", width=3.5, style="arc")
            # Pulsating central core
            core_r = max(20, base_r * 0.45)
            self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                                    fill="#1e3a8a", outline="#60a5fa", width=2)
            self.canvas.create_oval(cx - (core_r * 0.4), cy - (core_r * 0.4),
                                    cx + (core_r * 0.4), cy + (core_r * 0.4),
                                    fill="#93c5fd", outline="#dbeafe", width=1.5)

        elif self.visualizer_state == "speaking":
            # Speaking Mode: Multi-layer acoustic soundwave harmonics reacting dynamically
            w1 = math.sin(self.anim_t * 5.0) * (base_r * 0.14)  # First wave oscillation
            w2 = math.cos(self.anim_t * 6.2) * (base_r * 0.10)  # Second harmonic wave oscillation

            # Outermost acoustic wave ring
            self.canvas.create_oval(cx - (base_r + 48 + w1), cy - (base_r + 48 + w1),
                                    cx + (base_r + 48 + w1), cy + (base_r + 48 + w1),
                                    outline="#0b2545", width=2.5)
            # Mid royal blue wave ring
            self.canvas.create_oval(cx - (base_r + 30 + w2), cy - (base_r + 30 + w2),
                                    cx + (base_r + 30 + w2), cy + (base_r + 30 + w2),
                                    outline="#1d4ed8", width=3)
            # Inner electric blue shockwave
            self.canvas.create_oval(cx - (base_r + 14 + w1 * 0.5), cy - (base_r + 14 + w1 * 0.5),
                                    cx + (base_r + 14 + w1 * 0.5), cy + (base_r + 14 + w1 * 0.5),
                                    outline="#0a84ff", width=3)
            # High-frequency sky blue wave
            self.canvas.create_oval(cx - (base_r + w2 * 0.4), cy - (base_r + w2 * 0.4),
                                    cx + (base_r + w2 * 0.4), cy + (base_r + w2 * 0.4),
                                    outline="#38bdf8", width=2)
            # Radiant speech core
            core_r = max(22, base_r * 0.48)
            self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                                    fill="#0071e3", outline="#bae6fd", width=2)
            self.canvas.create_oval(cx - (core_r * 0.35), cy - (core_r * 0.35),
                                    cx + (core_r * 0.35), cy + (core_r * 0.35),
                                    fill="#f0f9ff", outline="")

        # Schedule next animation frame at ~16ms (~60 FPS)
        self.after(16, self._animate_visualizer)

    # ================= 3. DRAGGABLE SPLITTER (DRAG UP TO EXTEND) =================
    def _build_draggable_splitter(self):
        """Constructs an Apple-style draggable divider handle to resize chat height."""
        self.splitter = ctk.CTkFrame(
            self,
            fg_color="transparent",
            height=18,
            cursor="sb_v_double_arrow"  # Vertical double-arrow cursor indicating drag ability
        )
        self.splitter.grid(row=2, column=0, sticky="ew", padx=20)  # Place between visualizer and chat

        # Minimalist rounded pill grab handle
        self.drag_pill = ctk.CTkFrame(
            self.splitter,
            fg_color="#27272a",
            width=64,
            height=5,
            corner_radius=3,
            cursor="sb_v_double_arrow"
        )
        self.drag_pill.place(relx=0.5, rely=0.5, anchor="center")  # Center handle in splitter bar

        # Bind mouse drag events to resize pane
        self.splitter.bind("<B1-Motion>", self._on_splitter_drag)
        self.drag_pill.bind("<B1-Motion>", self._on_splitter_drag)

        # Blue highlight effect on hover to signal interactivity
        self.splitter.bind("<Enter>", lambda e: self.drag_pill.configure(fg_color="#0a84ff"))
        self.splitter.bind("<Leave>", lambda e: self.drag_pill.configure(fg_color="#27272a"))
        self.drag_pill.bind("<Enter>", lambda e: self.drag_pill.configure(fg_color="#0a84ff"))
        self.drag_pill.bind("<Leave>", lambda e: self.drag_pill.configure(fg_color="#27272a"))

    def _on_splitter_drag(self, event):
        """
        Dynamically adjusts grid row weights when dragging the handle up or down.
        Dragging up extends the chat area; dragging down expands the visualizer.
        """
        total_h = self.winfo_height()  # Get full window pixel height
        if total_h <= 0:
            return  # Guard against uninitialized geometry

        mouse_y = event.y_root - self.winfo_rooty()  # Mouse Y position relative to top of window
        ratio = mouse_y / total_h  # Compute proportional split ratio

        # Clamp top weight between 20% and 82% to maintain clean usability
        top_w = int(max(20, min(82, ratio * 100)))
        bottom_w = 100 - top_w  # Remaining percentage assigned to chat pane

        self.top_weight = top_w  # Store top weight
        self.bottom_weight = bottom_w  # Store bottom weight

        # Apply updated weights to grid layout
        self.grid_rowconfigure(1, weight=self.top_weight)
        self.grid_rowconfigure(3, weight=self.bottom_weight)

    # ================= 4. CHAT AREA & DOCK =================
    def _build_chat_and_dock_pane(self):
        """Constructs the lower conversation pane containing scrollable message cards and dock."""
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")  # Container frame
        self.chat_container.grid(row=3, column=0, sticky="nsew", padx=28, pady=(2, 16))  # Place in row 3

        # Scrollable container holding user and assistant chat cards
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.chat_container,
            fg_color="#090b10",
            corner_radius=18,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.chat_scroll.pack(fill="both", expand=True, pady=(2, 10))  # Fill available container space

        # Floating Apple-style pill dock for text input
        dock = ctk.CTkFrame(
            self.chat_container,
            height=50,
            fg_color=COLOR_DOCK,
            corner_radius=25,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        dock.pack(fill="x")  # Expand horizontally

        # Prompt entry text field
        self.entry_box = ctk.CTkEntry(
            dock,
            height=40,
            placeholder_text="Message Jarvis...",
            placeholder_text_color="#435169",
            font=FONT_INPUT,
            fg_color="transparent",
            border_width=0,
            text_color=COLOR_TEXT_PRIMARY
        )
        self.entry_box.pack(side="left", fill="x", expand=True, padx=(18, 8), pady=5)
        self.entry_box.bind("<Return>", lambda event: self.send_message())  # Pressing Enter sends prompt

        # Circular Apple send button with arrow icon (↑)
        self.send_btn = ctk.CTkButton(
            dock,
            text="↑",
            width=36,
            height=36,
            font=(FONT_FAMILY, 15, "bold"),
            fg_color=COLOR_CARD_USER,
            hover_color="#0062c4",
            corner_radius=18,
            command=self.send_message
        )
        self.send_btn.pack(side="right", padx=(0, 7), pady=5)

    # ================= MESSAGE CARDS =================
    def add_user_card(self, text):
        """Renders a right-aligned blue user message card with timestamp."""
        timestamp = datetime.datetime.now().strftime("%H:%M")  # Format current time
        card = ctk.CTkFrame(
            self.chat_scroll,
            fg_color=COLOR_CARD_USER,
            corner_radius=18
        )
        card.pack(anchor="e", padx=(80, 8), pady=6)  # Align card to right

        ctk.CTkLabel(
            card,
            text=text,
            font=FONT_BODY,
            text_color="#ffffff",
            wraplength=520,  # Auto-wrap long lines
            justify="left"
        ).pack(anchor="e", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            card,
            text=timestamp,
            font=FONT_TIME,
            text_color="#c8e0ff"
        ).pack(anchor="e", padx=16, pady=(0, 6))

        self._scroll_to_bottom()  # Scroll down to latest message

    def add_jarvis_card(self, text):
        """Renders a left-aligned frosted dark assistant message card with Copy button."""
        timestamp = datetime.datetime.now().strftime("%H:%M")  # Format current time
        card = ctk.CTkFrame(
            self.chat_scroll,
            fg_color=COLOR_CARD_JARVIS,
            corner_radius=18,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        card.pack(anchor="w", padx=(8, 80), pady=6)  # Align card to left

        hdr = ctk.CTkFrame(card, fg_color="transparent")  # Header row inside card
        hdr.pack(fill="x", padx=16, pady=(8, 0))

        ctk.CTkLabel(
            hdr,
            text="Jarvis",
            font=FONT_BTN,
            text_color="#38bdf8"
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text=f"•  {timestamp}",
            font=FONT_TIME,
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left", padx=6)

        # Copy card text to clipboard
        ctk.CTkButton(
            hdr,
            text="Copy",
            width=34,
            height=16,
            font=FONT_TIME,
            fg_color="transparent",
            hover_color="#1a2233",
            text_color=COLOR_TEXT_MUTED,
            command=lambda: self._copy_to_clipboard(text)
        ).pack(side="right")

        ctk.CTkLabel(
            card,
            text=text,
            font=FONT_BODY,
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=540,  # Auto-wrap response text
            justify="left"
        ).pack(anchor="w", padx=16, pady=(4, 12))

        self._scroll_to_bottom()  # Scroll down to reveal new card

    # ================= LOGIC & THREADING =================
    def send_message(self):
        """Validates input, updates UI, switches orb to thinking state, and launches worker thread."""
        user_input = self.entry_box.get().strip()  # Retrieve and trim user input
        if not user_input:
            return  # Disallow empty submissions

        self.add_user_card(user_input)  # Display user card immediately
        self.entry_box.delete(0, "end")  # Clear input entry box

        self.visualizer_state = "thinking"  # Switch orb animation to energetic thinking state
        self.status_label.configure(text="THINKING...", text_color="#38bdf8")  # Update status text
        self.set_input_state(disabled=True)  # Temporarily disable input while generating

        # Process Ollama query and Piper TTS in background thread
        threading.Thread(target=self.process_ai_response, args=(user_input,), daemon=True).start()

    def process_ai_response(self, prompt):
        """Worker thread task: queries Ollama, synthesizes audio, and triggers synchronized UI display."""
        response = ask_jarvis(prompt)  # Query local Ollama model

        # If voice is disabled, display text immediately and return to idle state
        if not self.voice_enabled:
            self.after(0, self._render_response, response)
            self.after(0, self._set_idle_state)
            return

        # Synchronize text appearance with the exact start of audio playback
        def on_audio_ready():
            self.after(0, self._render_response, response)  # Display text card on main thread
            self.after(0, self._set_speaking_state)  # Switch orb animation to speaking state

        # Return visualizer back to idle when audio finishes playing
        def on_audio_finish():
            self.after(0, self._set_idle_state)

        # Synthesize audio and trigger callbacks
        speak(response, on_start=on_audio_ready, on_finish=on_audio_finish)

    def _render_response(self, response):
        """Safely inserts Jarvis's card onto the main UI thread and re-enables input."""
        self.add_jarvis_card(response)
        self.set_input_state(disabled=False)

    def _set_speaking_state(self):
        """Switches visualizer to speaking state and updates label."""
        self.visualizer_state = "speaking"
        self.status_label.configure(text="SPEAKING...", text_color="#60a5fa")

    def _set_idle_state(self):
        """Switches visualizer to idle state and updates label."""
        self.visualizer_state = "idle"
        self.status_label.configure(text="READY", text_color=COLOR_TEXT_MUTED)

    def toggle_voice(self):
        """Toggles TTS audio on and off."""
        self.voice_enabled = not self.voice_enabled
        if self.voice_enabled:
            self.voice_btn.configure(text="Voice: On", text_color=COLOR_TEXT_PRIMARY)
        else:
            self.stop_speech()
            self.voice_btn.configure(text="Voice: Off", text_color="#38bdf8")

    def stop_speech(self):
        """Halts active audio output and returns visualizer to idle state."""
        stop_speech()
        self._set_idle_state()

    def clear_conversation(self):
        """Purges conversation history memory and clears all UI chat cards."""
        self.stop_speech()
        reset_chat_history()  # Reset memory in brain.py
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()  # Remove all chat bubble cards
        self.add_jarvis_card("Conversation cleared. How can I assist you?")

    def set_input_state(self, disabled=False):
        """Enables or disables input widgets during request processing."""
        state = "disabled" if disabled else "normal"
        self.send_btn.configure(state=state)
        self.entry_box.configure(state=state)
        if not disabled:
            self.entry_box.focus()  # Return keyboard focus to input box

    def _scroll_to_bottom(self):
        """Scrolls the chat frame smoothly to the latest message card."""
        self.update_idletasks()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _copy_to_clipboard(self, text):
        """Copies given text to the OS clipboard."""
        self.clipboard_clear()
        self.clipboard_append(text)

if __name__ == "__main__":
    app = JarvisAppleApp()  # Instantiate main app
    app.mainloop()  # Start CustomTkinter event loop