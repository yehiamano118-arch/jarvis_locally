import customtkinter as ctk
import tkinter as tk
import threading
import datetime
import math
import time

from brain import ask_jarvis, reset_chat_history
from tts import speak, stop_speech


FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"
FONT_TITLE = (FONT_FAMILY, 17, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 9, "bold")
FONT_STATUS = (FONT_FAMILY, 9, "bold")
FONT_BODY = (FONT_FAMILY, 13)
FONT_TIME = (FONT_MONO, 9)
FONT_INPUT = (FONT_FAMILY, 13)
FONT_BTN = (FONT_FAMILY, 10, "bold")

COLOR_BG = "#0A0C0F"
COLOR_PANEL = "#12161C"
COLOR_CARD = "#171C24"
COLOR_BORDER = "#232A36"
COLOR_TEXT_PRIMARY = "#F3F4F6"
COLOR_TEXT_MUTED = "#9CA3AF"
COLOR_ACCENT = "#F59E0B"
COLOR_ACCENT_TINT = "#2A2112"
COLOR_DOCK = "#12161C"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class JarvisApp(ctk.CTk):
    """Dark, compact chat UI with a responsive vector orb and animated controls."""

    def __init__(self):
        super().__init__()

        self.title("Jarvis")
        self.geometry("960x820")
        self.minsize(720, 620)
        self.configure(fg_color=COLOR_BG)

        self.voice_enabled = True
        self.visualizer_state = "idle"
        self.anim_t = 0.0
        self.top_weight = 24
        self.bottom_weight = 76
        self._conversation_generation = 0
        self._color_animation_jobs = {}
        self._animated_colors = {}
        self._stream_jobs = {}
        self._message_labels = []
        self._suggestion_cards = []
        self._scroll_check_pending = False

        self._setup_grid_layout()
        self._build_header()
        self._build_visualizer_pane()
        self._build_draggable_splitter()
        self._build_chat_and_dock_pane()
        self._set_status("READY")
        self._animate_visualizer()
        self.bind("<Configure>", self._resize_message_wraps, add="+")

    def _setup_grid_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=self.top_weight)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=self.bottom_weight)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=48)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(14, 4))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(
            title_box,
            text="JARVIS",
            font=FONT_TITLE,
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            title_box,
            text="INTELLIGENCE",
            font=FONT_SUBTITLE,
            text_color=COLOR_ACCENT,
            fg_color=COLOR_ACCENT_TINT,
            corner_radius=8,
            padx=8,
            pady=3,
        ).pack(side="left")

        self.status_pill = ctk.CTkFrame(
            header,
            fg_color=COLOR_PANEL,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.status_pill.pack(side="left", padx=(18, 0))
        self.status_dot = ctk.CTkLabel(
            self.status_pill,
            text="●",
            font=(FONT_FAMILY, 8),
            text_color=COLOR_ACCENT,
        )
        self.status_dot.pack(side="left", padx=(9, 5), pady=5)
        self.status_label = ctk.CTkLabel(
            self.status_pill,
            text="READY",
            font=FONT_STATUS,
            text_color=COLOR_TEXT_MUTED,
        )
        self.status_label.pack(side="left", padx=(0, 10), pady=5)

        ctrl_box = ctk.CTkFrame(header, fg_color="transparent")
        ctrl_box.pack(side="right")
        self.stop_btn = self._make_header_button(
            ctrl_box, "Stop", 54, COLOR_TEXT_MUTED, self.stop_speech
        )
        self.stop_btn.pack(side="left", padx=4)
        self.clear_btn = self._make_header_button(
            ctrl_box, "Clear", 56, COLOR_TEXT_MUTED, self.clear_conversation
        )
        self.clear_btn.pack(side="left", padx=4)

    def _make_header_button(self, parent, text, width, text_color, command):
        button = ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=28,
            font=FONT_BTN,
            fg_color=COLOR_PANEL,
            hover=False,
            corner_radius=14,
            text_color=text_color,
            command=command,
        )
        self._bind_color_hover(button, COLOR_PANEL, COLOR_CARD)
        return button

    def _build_visualizer_pane(self):
        self.vis_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self.vis_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=0)
        self.canvas = tk.Canvas(
            self.vis_frame,
            bg=COLOR_BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

    def _animate_visualizer(self):
        self.anim_t += 0.04
        self.canvas.delete("orb")

        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        cx, cy = width / 2, height / 2
        base_r = min(40, max(14, min(width, height) * 0.18))

        if self.visualizer_state == "thinking":
            pulse = math.sin(self.anim_t * 4.0) * (base_r * 0.08)
            angle = (self.anim_t * 110) % 360
            self._orb_ring(cx, cy, base_r + 22 + pulse, "#3A2B15", 2)
            self.canvas.create_arc(
                cx - base_r - 12,
                cy - base_r - 12,
                cx + base_r + 12,
                cy + base_r + 12,
                start=angle,
                extent=125,
                outline=COLOR_ACCENT,
                width=3,
                style="arc",
                tags="orb",
            )
            self.canvas.create_arc(
                cx - base_r - 12,
                cy - base_r - 12,
                cx + base_r + 12,
                cy + base_r + 12,
                start=angle + 180,
                extent=100,
                outline="#D88A12",
                width=2,
                style="arc",
                tags="orb",
            )
            core_r = max(11, base_r * 0.48 + pulse * 0.25)
            self._orb_core(cx, cy, core_r, "#68420D", "#FBBF24")
        elif self.visualizer_state == "speaking":
            wave = math.sin(self.anim_t * 5.0) * (base_r * 0.10)
            self._orb_ring(cx, cy, base_r + 22 + wave, "#3A2B15", 2)
            self._orb_ring(cx, cy, base_r + 11 - wave * 0.5, "#A7650B", 2)
            self._orb_ring(cx, cy, base_r + wave * 0.3, COLOR_ACCENT, 2)
            self._orb_core(cx, cy, max(12, base_r * 0.5 + wave * 0.2), "#7A4A0B", "#FCD34D")
        else:
            breathe = math.sin(self.anim_t * 1.4) * (base_r * 0.06)
            self._orb_ring(cx, cy, base_r + 20 + breathe, "#30271A", 2)
            self._orb_ring(cx, cy, base_r + 10 + breathe * 0.6, "#8B5A12", 2)
            self._orb_ring(cx, cy, base_r + breathe * 0.25, COLOR_ACCENT, 2)
            self._orb_core(cx, cy, max(11, base_r * 0.46), "#6B450F", "#FBBF24")

        self.after(16, self._animate_visualizer)

    def _orb_ring(self, cx, cy, radius, color, width):
        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=color,
            width=width,
            tags="orb",
        )

    def _orb_core(self, cx, cy, radius, fill, highlight):
        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=fill,
            outline=COLOR_ACCENT,
            width=1,
            tags="orb",
        )
        inner = radius * 0.38
        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            fill=highlight,
            outline="",
            tags="orb",
        )

    def _build_draggable_splitter(self):
        self.splitter = ctk.CTkFrame(
            self,
            fg_color="transparent",
            height=18,
            cursor="sb_v_double_arrow",
        )
        self.splitter.grid(row=2, column=0, sticky="ew", padx=20)
        self.drag_pill = ctk.CTkFrame(
            self.splitter,
            fg_color=COLOR_BORDER,
            width=58,
            height=4,
            corner_radius=3,
            cursor="sb_v_double_arrow",
        )
        self.drag_pill.place(relx=0.5, rely=0.5, anchor="center")
        self.splitter.bind("<B1-Motion>", self._on_splitter_drag)
        self.drag_pill.bind("<B1-Motion>", self._on_splitter_drag)
        self._bind_color_hover(self.drag_pill, COLOR_BORDER, COLOR_ACCENT)

    def _on_splitter_drag(self, event):
        total_h = self.winfo_height()
        if total_h <= 0:
            return
        ratio = (event.y_root - self.winfo_rooty()) / total_h
        self.top_weight = int(max(17, min(48, ratio * 100)))
        self.bottom_weight = 100 - self.top_weight
        self.grid_rowconfigure(1, weight=self.top_weight)
        self.grid_rowconfigure(3, weight=self.bottom_weight)

    def _build_chat_and_dock_pane(self):
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(
            row=3, column=0, sticky="nsew", padx=28, pady=(0, 16)
        )

        self.content_area = ctk.CTkFrame(self.chat_container, fg_color=COLOR_BG)
        self.content_area.pack(fill="both", expand=True, pady=(2, 12))

        self.chat_scroll = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color=COLOR_BG,
            corner_radius=18,
            border_width=0,
            scrollbar_fg_color=COLOR_BG,
            scrollbar_button_color=COLOR_BORDER,
            scrollbar_button_hover_color=COLOR_TEXT_MUTED,
        )
        self.chat_scroll.pack(fill="both", expand=True)
        self.chat_scroll._scrollbar.grid_remove()
        self.chat_scroll.bind("<Configure>", self._schedule_scrollbar_check)

        self._build_empty_state()
        self.empty_state.place(relx=0.5, rely=0.5, anchor="center")

        dock = ctk.CTkFrame(
            self.chat_container,
            height=54,
            fg_color=COLOR_DOCK,
            corner_radius=27,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        dock.pack(fill="x")

        self.entry_box = ctk.CTkEntry(
            dock,
            height=42,
            placeholder_text="Message Jarvis...",
            placeholder_text_color=COLOR_TEXT_MUTED,
            font=FONT_INPUT,
            fg_color="transparent",
            border_width=0,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.entry_box.pack(side="left", fill="x", expand=True, padx=(18, 8), pady=5)
        self.entry_box.bind("<Return>", lambda event: self.send_message())
        self.entry_box.bind(
            "<FocusIn>",
            lambda event: self._animate_color(dock, "border_color", COLOR_ACCENT),
            add="+",
        )
        self.entry_box.bind(
            "<FocusOut>",
            lambda event: self._animate_color(dock, "border_color", COLOR_BORDER),
            add="+",
        )

        self.voice_btn = ctk.CTkButton(
            dock,
            text="Voice On",
            width=72,
            height=34,
            font=FONT_BTN,
            fg_color=COLOR_DOCK,
            hover=False,
            corner_radius=17,
            text_color=COLOR_TEXT_MUTED,
            command=self.toggle_voice,
        )
        self.voice_btn.pack(side="right", padx=(0, 4), pady=7)
        self._bind_color_hover(self.voice_btn, COLOR_DOCK, COLOR_CARD)

        self.send_btn = ctk.CTkButton(
            dock,
            text="↑",
            width=38,
            height=38,
            font=(FONT_FAMILY, 17, "bold"),
            fg_color=COLOR_ACCENT,
            hover=False,
            corner_radius=19,
            text_color=COLOR_BG,
            command=self.send_message,
        )
        self.send_btn.pack(side="right", padx=(0, 8), pady=7)
        self._bind_color_hover(self.send_btn, COLOR_ACCENT, "#D88A12")

    def _build_empty_state(self):
        self.empty_state = ctk.CTkFrame(self.content_area, fg_color="transparent")
        ctk.CTkLabel(
            self.empty_state,
            text="How can I help you today?",
            font=(FONT_FAMILY, 24, "bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(pady=(0, 7))
        ctk.CTkLabel(
            self.empty_state,
            text="Choose a starting point or ask me anything.",
            font=(FONT_FAMILY, 12),
            text_color=COLOR_TEXT_MUTED,
        ).pack(pady=(0, 22))

        suggestions = ctk.CTkFrame(self.empty_state, fg_color="transparent")
        suggestions.pack()
        items = (
            ("01", "Explore a topic", "Get a clear, concise explanation.",
             "Explain quantum computing in simple terms."),
            ("02", "Plan something", "Turn an idea into a practical plan.",
             "Help me plan a productive weekend."),
            ("03", "Write with me", "Draft, refine, or rewrite anything.",
             "Help me write a thoughtful thank-you note."),
            ("04", "Solve a problem", "Work through a tricky question.",
             "How can I build a consistent study habit?"),
        )
        for index, (number, title, description, prompt) in enumerate(items):
            card = ctk.CTkFrame(
                suggestions,
                width=258,
                height=86,
                fg_color=COLOR_PANEL,
                corner_radius=14,
                border_width=1,
                border_color=COLOR_BORDER,
                cursor="hand2",
            )
            card.grid(
                row=index // 2,
                column=index % 2,
                padx=6,
                pady=6,
                sticky="nsew",
            )
            card.grid_propagate(False)
            self._suggestion_cards.append(card)
            number_label = ctk.CTkLabel(
                card,
                text=number,
                font=(FONT_MONO, 10, "bold"),
                text_color=COLOR_ACCENT,
                fg_color=COLOR_ACCENT_TINT,
                corner_radius=6,
                width=29,
                height=24,
            )
            number_label.place(x=13, y=12)
            title_label = ctk.CTkLabel(
                card,
                text=title,
                font=(FONT_FAMILY, 12, "bold"),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w",
            )
            title_label.place(x=52, y=12)
            description_label = ctk.CTkLabel(
                card,
                text=description,
                font=(FONT_FAMILY, 10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            )
            description_label.place(x=52, y=37)
            self._bind_suggestion_card(card, prompt)
            for child in (number_label, title_label, description_label):
                self._bind_suggestion_card(child, prompt, card)

    def _bind_suggestion_card(self, widget, prompt, card=None):
        card = card or widget
        widget.bind(
            "<Enter>",
            lambda event, target=card: self._animate_color(
                target, "fg_color", COLOR_CARD
            ),
        )
        widget.bind(
            "<Leave>",
            lambda event, target=card: self._animate_color(
                target, "fg_color", COLOR_PANEL
            ),
        )
        widget.bind("<Button-1>", lambda event: self._use_suggestion(prompt))

    def _use_suggestion(self, prompt):
        self.entry_box.delete(0, "end")
        self.entry_box.insert(0, prompt)
        self.send_message()

    def add_user_card(self, text):
        timestamp = datetime.datetime.now().strftime("%H:%M")
        row = self._create_message_row()
        card = ctk.CTkFrame(
            row,
            fg_color=COLOR_ACCENT_TINT,
            corner_radius=16,
            border_width=1,
            border_color="#4A3516",
        )
        card.pack(anchor="e", padx=(16, 0))
        message_label = ctk.CTkLabel(
            card,
            text=text,
            font=self._message_font(text),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=self._message_wraplength(),
            justify="left",
        )
        message_label.pack(anchor="w", padx=15, pady=(10, 4))
        ctk.CTkLabel(
            card,
            text=timestamp,
            font=FONT_TIME,
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="e", padx=15, pady=(0, 8))
        self._message_labels.append(message_label)
        self._scroll_to_bottom()

    def add_jarvis_card(self, text, stream=False, generation=None):
        timestamp = datetime.datetime.now().strftime("%H:%M")
        row = self._create_message_row()
        card = ctk.CTkFrame(
            row,
            fg_color=COLOR_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(anchor="w", padx=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(8, 0))
        ctk.CTkLabel(
            header,
            text="JARVIS",
            font=FONT_BTN,
            text_color=COLOR_ACCENT,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text=timestamp,
            font=FONT_TIME,
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            header,
            text="Copy",
            width=42,
            height=20,
            font=FONT_TIME,
            fg_color="transparent",
            hover=False,
            text_color=COLOR_TEXT_MUTED,
            command=lambda: self._copy_to_clipboard(text),
        ).pack(side="right")

        body = ctk.CTkLabel(
            card,
            text="" if stream else text,
            font=self._message_font(text),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=self._message_wraplength(),
            justify="left",
        )
        body.pack(anchor="w", fill="x", padx=15, pady=(5, 12))
        self._message_labels.append(body)
        self.empty_state.place_forget()
        self._schedule_scrollbar_check()
        self._scroll_to_bottom()
        if stream:
            self._stream_text(body, text, generation, lambda: self.set_input_state(False))
        return body

    def _create_message_row(self):
        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)
        return row

    def _message_font(self, text):
        return (FONT_MONO, 12) if "```" in text else FONT_BODY

    def _message_wraplength(self):
        width = max(320, self.chat_scroll.winfo_width() - 112)
        return min(790, width)

    def _resize_message_wraps(self, event=None):
        if not self._message_labels:
            return
        wraplength = self._message_wraplength()
        for label in tuple(self._message_labels):
            if label.winfo_exists():
                label.configure(wraplength=wraplength)

    def send_message(self):
        user_input = self.entry_box.get().strip()
        if not user_input:
            return

        self._conversation_generation += 1
        generation = self._conversation_generation
        self.add_user_card(user_input)
        self.entry_box.delete(0, "end")
        self._set_status("THINKING")
        self.set_input_state(disabled=True)
        threading.Thread(
            target=self.process_ai_response,
            args=(user_input, generation),
            daemon=True,
        ).start()

    def process_ai_response(self, prompt, generation):
        response = ask_jarvis(prompt)
        if generation != self._conversation_generation:
            return

        if not self.voice_enabled:
            self.after(0, self._render_response, response, generation)
            self.after(0, self._set_idle_state, generation)
            return

        def on_audio_ready():
            if generation == self._conversation_generation:
                self.after(0, self._render_response, response, generation)
                self.after(0, self._set_speaking_state, generation)

        def on_audio_finish():
            if generation == self._conversation_generation:
                self.after(0, self._set_idle_state, generation)

        speak(response, on_start=on_audio_ready, on_finish=on_audio_finish)

    def _render_response(self, response, generation):
        if generation != self._conversation_generation:
            return
        self.add_jarvis_card(response, stream=True, generation=generation)

    def _stream_text(self, label, text, generation, on_complete):
        started = time.perf_counter()
        last_visible = -1

        def tick():
            nonlocal last_visible
            if generation != self._conversation_generation or not label.winfo_exists():
                self._stream_jobs.pop(label, None)
                return
            visible = min(len(text), int((time.perf_counter() - started) * 520))
            if visible != last_visible:
                label.configure(text=text[:visible])
                last_visible = visible
                if visible and visible % 128 < 16:
                    self._scroll_to_bottom()
            if visible >= len(text):
                self._stream_jobs.pop(label, None)
                self._scroll_to_bottom()
                on_complete()
                return
            self._stream_jobs[label] = self.after(16, tick)

        self._stream_jobs[label] = self.after(16, tick)

    def _set_speaking_state(self, generation=None):
        if generation is not None and generation != self._conversation_generation:
            return
        self._set_status("SPEAKING")

    def _set_idle_state(self, generation=None):
        if generation is not None and generation != self._conversation_generation:
            return
        self._set_status("READY")

    def _set_status(self, state):
        self.visualizer_state = state.lower()
        if state == "THINKING":
            text, color, tint = "THINKING", COLOR_ACCENT, COLOR_ACCENT_TINT
        elif state == "SPEAKING":
            text, color, tint = "SPEAKING", COLOR_ACCENT, COLOR_ACCENT_TINT
        else:
            text, color, tint = "READY", COLOR_TEXT_MUTED, COLOR_PANEL
        self.status_label.configure(text=text)
        self._animate_color(self.status_label, "text_color", color)
        self._animate_color(self.status_dot, "text_color", color)
        self._animate_color(self.status_pill, "fg_color", tint)

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        if self.voice_enabled:
            self.voice_btn.configure(text="Voice On", text_color=COLOR_ACCENT)
        else:
            self.stop_speech()
            self.voice_btn.configure(text="Voice Off", text_color=COLOR_TEXT_MUTED)

    def stop_speech(self):
        stop_speech()
        self._set_idle_state()

    def clear_conversation(self):
        self._conversation_generation += 1
        self._cancel_streams()
        self.stop_speech()
        reset_chat_history()
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()
        self._message_labels.clear()
        for card in self._suggestion_cards:
            self._cancel_color_animation(card, "fg_color")
            card.configure(fg_color=COLOR_PANEL)
            self._animated_colors[(card, "fg_color")] = COLOR_PANEL
        self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
        self.chat_scroll._parent_canvas.yview_moveto(0)
        self.set_input_state(disabled=False)
        self._schedule_scrollbar_check()

    def set_input_state(self, disabled=False):
        state = "disabled" if disabled else "normal"
        self.send_btn.configure(state=state)
        self.entry_box.configure(state=state)
        if not disabled:
            self.entry_box.focus()

    def _scroll_to_bottom(self):
        self.update_idletasks()
        self.chat_scroll._parent_canvas.yview_moveto(1.0)
        self._schedule_scrollbar_check()

    def _schedule_scrollbar_check(self, event=None):
        if self._scroll_check_pending:
            return
        self._scroll_check_pending = True
        self.after_idle(self._update_scrollbar_visibility)

    def _update_scrollbar_visibility(self):
        self._scroll_check_pending = False
        if not self.chat_scroll.winfo_children():
            self.chat_scroll._scrollbar.grid_remove()
            return
        canvas = self.chat_scroll._parent_canvas
        bounds = canvas.bbox("all")
        overflow = bounds is not None and bounds[3] - bounds[1] > canvas.winfo_height() + 2
        if overflow:
            self.chat_scroll._scrollbar.grid()
        else:
            self.chat_scroll._scrollbar.grid_remove()

    def _bind_color_hover(self, widget, base_color, hover_color):
        widget.bind(
            "<Enter>",
            lambda event: self._animate_color(widget, "fg_color", hover_color),
            add="+",
        )
        widget.bind(
            "<Leave>",
            lambda event: self._animate_color(widget, "fg_color", base_color),
            add="+",
        )

    def _animate_color(self, widget, attribute, target_color, duration=0.18):
        key = (widget, attribute)
        self._cancel_color_animation(widget, attribute)

        current = self._animated_colors.get(key)
        if current is None:
            current = self._color_value(widget.cget(attribute))
        target = self._color_value(target_color)
        start_time = time.perf_counter()
        start_rgb = self._hex_to_rgb(current)
        target_rgb = self._hex_to_rgb(target)

        def tick():
            progress = min(1.0, (time.perf_counter() - start_time) / duration)
            eased = progress * progress * (3 - 2 * progress)
            color = self._rgb_to_hex(
                tuple(
                    round(start_rgb[index] + (target_rgb[index] - start_rgb[index]) * eased)
                    for index in range(3)
                )
            )
            widget.configure(**{attribute: color})
            self._animated_colors[key] = color
            if progress >= 1:
                self._color_animation_jobs.pop(key, None)
            else:
                self._color_animation_jobs[key] = self.after(16, tick)

        tick()

    def _cancel_color_animation(self, widget, attribute):
        key = (widget, attribute)
        job = self._color_animation_jobs.pop(key, None)
        if job is not None:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass

    @staticmethod
    def _color_value(color):
        if isinstance(color, (tuple, list)):
            color = color[0]
        if color == "transparent":
            return COLOR_BG
        return color

    @staticmethod
    def _hex_to_rgb(color):
        value = color.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    def _cancel_streams(self):
        for job in self._stream_jobs.values():
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._stream_jobs.clear()

    def _copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)


if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()
