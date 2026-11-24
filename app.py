import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import json
import csv

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import beam_calculations as beam


class BeamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beam Designer")
        self.geometry("1280x820")
        self.minsize(960, 650)
        self.configure(background="#f4f7fb")

        self.support = "simply-supported"
        self.span = 20.0
        self.deflection_limit = 360
        self.material = "steel"
        self.section = "W12x26"
        self.point_loads = []
        self.uniform_loads = [{
            "id": 1, "magnitude": 1.0, "start": 0.0, "end": 20.0
        }]
        self.next_load_id = 2
        self.dragging_load_id = None
        self.result = None

        self._build_menu()
        self._build_layout()
        self.refresh()

    def _build_menu(self):
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Save", command=self._save_design)
        file_menu.add_command(label="Open", command=self._open_design)
        file_menu.add_separator()
        file_menu.add_command(label="Export CSV", command=self._export_csv)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)

    def _export_csv(self, path=None):
        if path is None:
            path = filedialog.asksaveasfilename(
                title="Export Beam Results",
                defaultextension=".csv",
                filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
            )
        if not path:
            return

        if self.result is None:
            self.refresh()
        if self.result is None:
            messagebox.showerror(
                "Export Error",
                "Beam results are unavailable.",
            )
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "x-position (ft)",
                    "shear (kips)",
                    "moment (kip-ft)",
                    "deflection (in)",
                ])
                for x, shear, moment, deflection in zip(
                    self.result["x"],
                    self.result["shear"],
                    self.result["moment"],
                    self.result["deflection"],
                ):
                    writer.writerow([
                        f"{float(x):.6f}",
                        f"{float(shear):.6f}",
                        f"{float(moment):.6f}",
                        f"{float(deflection):.6f}",
                    ])
        except (OSError, csv.Error, TypeError, ValueError) as error:
            messagebox.showerror(
                "Export Error",
                f"Could not export the CSV file:\n{error}",
            )

    def _save_design(self):
        path = filedialog.asksaveasfilename(
            title="Save Beam Design",
            defaultextension=".json",
            filetypes=[("Beam design JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        design = {
            "support": self.support,
            "span": self.span,
            "material": self.material,
            "section": self.section,
            "deflection_limit": self.deflection_limit,
            "point_loads": [
                {
                    "magnitude": float(load["magnitude"]),
                    "position": float(load["position"]),
                }
                for load in self.point_loads
            ],
            "uniform_loads": [
                {
                    "magnitude": float(load["magnitude"]),
                    "start": float(load["start"]),
                    "end": float(load["end"]),
                }
                for load in self.uniform_loads
            ],
        }
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(design, file, indent=2)
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Save Error", f"Could not save the design:\n{error}")

    def _open_design(self):
        path = filedialog.askopenfilename(
            title="Open Beam Design",
            filetypes=[("Beam design JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                design = json.load(file)
            self._restore_design(design)
        except json.JSONDecodeError as error:
            messagebox.showerror(
                "Invalid File",
                f"The selected file is not valid JSON:\n{error}",
            )
        except (OSError, UnicodeDecodeError) as error:
            messagebox.showerror("Open Error", f"Could not open the design:\n{error}")
        except ValueError as error:
            messagebox.showerror("Invalid File", str(error))

    def _restore_design(self, design):
        if not isinstance(design, dict):
            raise ValueError("The design file must contain a JSON object.")

        support = design.get("support")
        if support not in ("simply-supported", "cantilever"):
            raise ValueError("Support type must be 'simply-supported' or 'cantilever'.")

        try:
            span = float(design["span"])
            deflection_limit = int(design["deflection_limit"])
            material = design["material"]
            section = design["section"]
            point_loads = design["point_loads"]
            uniform_loads = design["uniform_loads"]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"The design file is missing or has invalid data: {error}")

        if not 4 <= span <= 40:
            raise ValueError("Span must be between 4 and 40 ft.")
        if deflection_limit not in (240, 360):
            raise ValueError("Deflection limit must be 240 or 360.")
        if material not in ("steel", "lumber"):
            raise ValueError("Material must be 'steel' or 'lumber'.")
        section_table = beam.STEEL_SECTIONS if material == "steel" else beam.LUMBER_SECTIONS
        if section not in section_table:
            raise ValueError("The saved section is not valid for the selected material.")
        if not isinstance(point_loads, list) or not isinstance(uniform_loads, list):
            raise ValueError("Loads must be stored in lists.")

        restored_points = []
        for index, load in enumerate(point_loads, start=1):
            if (not isinstance(load, dict) or "magnitude" not in load
                    or "position" not in load):
                raise ValueError(f"Point load {index} is invalid.")
            try:
                magnitude = float(load["magnitude"])
                position = float(load["position"])
            except (TypeError, ValueError):
                raise ValueError(f"Point load {index} has invalid values.")
            if not 0 <= magnitude or not 0 <= position <= span:
                raise ValueError(f"Point load {index} is outside the valid range.")
            restored_points.append({
                "id": index,
                "magnitude": magnitude,
                "position": position,
            })

        restored_uniforms = []
        for index, load in enumerate(uniform_loads, start=1):
            if not isinstance(load, dict):
                raise ValueError(f"Uniform load {index} is invalid.")
            try:
                magnitude = float(load["magnitude"])
                start = float(load["start"])
                end = float(load["end"])
            except (TypeError, ValueError):
                raise ValueError(f"Uniform load {index} has invalid values.")
            if magnitude < 0:
                raise ValueError(f"Uniform load {index} has a negative magnitude.")
            if not 0 <= start <= span or not 0 <= end <= span:
                raise ValueError(f"Uniform load {index} is outside the beam.")
            if end < start:
                raise ValueError(f"Uniform load {index} has start after end.")
            restored_uniforms.append({
                "id": index,
                "magnitude": magnitude,
                "start": start,
                "end": end,
            })

        self.support = support
        self.span = span
        self.material = material
        self.section = section
        self.deflection_limit = deflection_limit
        self.point_loads = restored_points
        self.uniform_loads = restored_uniforms
        self.next_load_id = max(
            [load["id"] for load in restored_points + restored_uniforms],
            default=0,
        ) + 1

        self.support_var.set(
            "Simply supported" if support == "simply-supported" else "Cantilever"
        )
        self.span_scale.set(span)
        self.span_entry.delete(0, "end")
        self.span_entry.insert(0, f"{span:.3f}")
        self.limit_var.set(f"L/{deflection_limit}")
        self.material_var.set(
            "Steel W-shapes" if material == "steel"
            else "Douglas Fir-Larch No. 2"
        )
        sections = list(section_table)
        self.section_combo.configure(values=sections)
        self.section_var.set(section)
        self._update_header()
        self._render_load_rows()
        self.refresh()

    def _build_layout(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="white")
        style.configure("TLabel", background="#f4f7fb", foreground="#172033")
        style.configure("Card.TLabel", background="white", foreground="#172033")
        style.configure("Title.TLabel", background="#f4f7fb",
                        foreground="#172033", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", background="white",
                        foreground="#172033", font=("Segoe UI", 11, "bold"))

        header = ttk.Frame(self)
        header.pack(fill="x", padx=18, pady=(12, 8))
        ttk.Label(header, text="Beam Designer", style="Title.TLabel").pack(side="left")
        self.header_badge = ttk.Label(
            header, text="Simply supported - 20 ft", style="Card.TLabel"
        )
        self.header_badge.pack(side="right", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self.input_panel = ttk.Frame(body, style="Card.TFrame")
        self.input_panel.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.input_panel.configure(width=330)
        self.input_panel.grid_propagate(False)
        self._build_inputs()

        self.results_panel = ttk.Frame(body)
        self.results_panel.grid(row=0, column=1, sticky="nsew")
        self.results_panel.rowconfigure(0, weight=3)
        self.results_panel.rowconfigure(1, weight=1)
        self.results_panel.columnconfigure(0, weight=1)
        self._build_results()

    def _build_inputs(self):
        row = 0
        ttk.Label(self.input_panel, text="Beam", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", padx=14, pady=(12, 6)
        )
        row += 1

        support_frame = ttk.Frame(self.input_panel, style="Card.TFrame")
        support_frame.grid(row=row, column=0, sticky="ew", padx=14)
        support_frame.columnconfigure((0, 1), weight=1)
        self.support_var = tk.StringVar(value="Simply supported")
        ttk.Radiobutton(support_frame, text="Simply supported",
                        variable=self.support_var, value="Simply supported",
                        command=self._support_changed).grid(
                            row=0, column=0, sticky="ew")
        ttk.Radiobutton(support_frame, text="Cantilever",
                        variable=self.support_var, value="Cantilever",
                        command=self._support_changed).grid(
                            row=0, column=1, sticky="ew")
        row += 1

        ttk.Label(self.input_panel, text="Span (ft)", style="Card.TLabel").grid(
            row=row, column=0, sticky="w", padx=14, pady=(10, 2)
        )
        row += 1
        span_frame = ttk.Frame(self.input_panel, style="Card.TFrame")
        span_frame.grid(row=row, column=0, sticky="ew", padx=14)
        span_frame.columnconfigure(0, weight=1)
        self.span_scale = tk.Scale(span_frame, from_=4, to=40, resolution=0.5,
                                   orient="horizontal", showvalue=False,
                                   command=self._span_scale_changed,
                                   highlightthickness=0)
        self.span_scale.set(20)
        self.span_scale.grid(row=0, column=0, sticky="ew")
        self.span_entry = ttk.Entry(span_frame, width=9)
        self.span_entry.insert(0, "20.000")
        self.span_entry.grid(row=0, column=1, padx=(8, 0))
        self.span_entry.bind("<KeyRelease>", self._span_entry_changed)
        row += 1

        ttk.Label(self.input_panel, text="Deflection limit", style="Card.TLabel").grid(
            row=row, column=0, sticky="w", padx=14, pady=(10, 2)
        )
        row += 1
        self.limit_var = tk.StringVar(value="L/360")
        limit_combo = ttk.Combobox(self.input_panel, textvariable=self.limit_var,
                                   values=("L/360", "L/240"), state="readonly")
        limit_combo.grid(row=row, column=0, sticky="ew", padx=14)
        limit_combo.bind("<<ComboboxSelected>>",
                         lambda _event: self._limit_changed())
        row += 1

        ttk.Separator(self.input_panel).grid(row=row, column=0, sticky="ew",
                                             pady=10)
        row += 1
        loads_header = ttk.Frame(self.input_panel, style="Card.TFrame")
        loads_header.grid(row=row, column=0, sticky="ew", padx=14)
        loads_header.columnconfigure(0, weight=1)
        ttk.Label(loads_header, text="Loads", style="Section.TLabel").grid(
            row=0, column=0, sticky="w")
        self.load_count = ttk.Label(loads_header, text="1", style="Card.TLabel")
        self.load_count.grid(row=0, column=1, sticky="e")
        row += 1

        self.loads_container = ttk.Frame(self.input_panel, style="Card.TFrame")
        self.loads_container.grid(row=row, column=0, sticky="ew", padx=14)
        self.loads_container.columnconfigure(0, weight=1)
        row += 1

        add_frame = ttk.Frame(self.input_panel, style="Card.TFrame")
        add_frame.grid(row=row, column=0, sticky="ew", padx=14, pady=(8, 0))
        add_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(add_frame, text="+ Point load",
                   command=self._add_point_load).grid(
                       row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(add_frame, text="+ Uniform load",
                   command=self._add_uniform_load).grid(
                       row=0, column=1, sticky="ew")
        row += 1

        ttk.Separator(self.input_panel).grid(row=row, column=0, sticky="ew",
                                             pady=10)
        row += 1
        ttk.Label(self.input_panel, text="Material", style="Card.TLabel").grid(
            row=row, column=0, sticky="w", padx=14, pady=(0, 2)
        )
        row += 1
        self.material_var = tk.StringVar(value="Steel W-shapes")
        material_combo = ttk.Combobox(
            self.input_panel, textvariable=self.material_var,
            values=("Steel W-shapes", "Douglas Fir-Larch No. 2"),
            state="readonly")
        material_combo.grid(row=row, column=0, sticky="ew", padx=14)
        material_combo.bind("<<ComboboxSelected>>",
                            lambda _event: self._material_changed())
        row += 1

        ttk.Label(self.input_panel, text="Cross-section", style="Card.TLabel").grid(
            row=row, column=0, sticky="w", padx=14, pady=(8, 2)
        )
        row += 1
        self.section_var = tk.StringVar(value=self.section)
        self.section_combo = ttk.Combobox(
            self.input_panel, textvariable=self.section_var,
            values=list(beam.STEEL_SECTIONS), state="readonly")
        self.section_combo.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.section_combo.bind("<<ComboboxSelected>>",
                                lambda _event: self._section_changed())

        self._render_load_rows()

    def _build_results(self):
        beam_card = ttk.Frame(self.results_panel, style="Card.TFrame")
        beam_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        beam_card.columnconfigure(0, weight=1)
        beam_card.rowconfigure(1, weight=1)

        title_row = ttk.Frame(beam_card, style="Card.TFrame")
        title_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="Beam and diagrams",
                  style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.span_tag = ttk.Label(title_row, text="20 ft span",
                                  style="Card.TLabel")
        self.span_tag.grid(row=0, column=1, sticky="e")

        self.figure = Figure(figsize=(8.8, 6.8), dpi=100, facecolor="white")
        self.axes = self.figure.subplots(
            4, 1, sharex=True,
            gridspec_kw={"height_ratios": [1.2, 1, 1, 1], "hspace": 0.22})
        self.canvas = FigureCanvasTkAgg(self.figure, master=beam_card)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self._on_point_press)
        self.canvas.mpl_connect("button_release_event", self._on_point_release)

        self.cursor_label = ttk.Label(
            beam_card,
            text="Position: -- | Shear: -- | Moment: -- | Deflection: --",
            style="Card.TLabel")
        self.cursor_label.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 8))

        bottom = ttk.Frame(self.results_panel)
        bottom.grid(row=1, column=0, sticky="nsew")
        bottom.columnconfigure((0, 1), weight=1)

        self.bending_card = tk.Frame(bottom, bg="white", bd=1, relief="solid")
        self.bending_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.deflection_card = tk.Frame(bottom, bg="white", bd=1, relief="solid")
        self.deflection_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self._build_check_card(self.bending_card, "Bending")
        self._build_check_card(self.deflection_card, "Deflection")

        recommendation = tk.Frame(bottom, bg="white", bd=1, relief="solid")
        recommendation.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        tk.Label(recommendation, text="Section recommendation:",
                 bg="white", fg="#344054",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=12, pady=10)
        self.recommendation_text = tk.StringVar(value="Unavailable")
        tk.Label(recommendation, textvariable=self.recommendation_text,
                 bg="white", fg="#172033").pack(side="left")
        self.use_button = ttk.Button(
            recommendation, text="Use this section",
            command=self._use_recommendation)
        self.use_button.pack(side="right", padx=12, pady=8)
        self.use_button.configure(state="disabled")
        self.recommendation_section = None

    def _build_check_card(self, card, title):
        card.columnconfigure((0, 1), weight=1)
        tk.Label(card, text=title, bg="white", fg="#344054",
                 font=("Segoe UI", 11, "bold")).grid(
                     row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        status = tk.Label(card, text="--", bg="#eef1f5", fg="#667085",
                          font=("Segoe UI", 9, "bold"), padx=8, pady=3)
        status.grid(row=0, column=1, sticky="e", padx=12, pady=(10, 4))
        actual = tk.StringVar(value="Actual: --")
        allowable = tk.StringVar(value="Allowable: --")
        ratio = tk.StringVar(value="Utilization: --")
        tk.Label(card, textvariable=actual, bg="white").grid(
            row=1, column=0, sticky="w", padx=12)
        tk.Label(card, textvariable=allowable, bg="white", fg="#667085").grid(
            row=1, column=1, sticky="e", padx=12)
        tk.Label(card, textvariable=ratio, bg="white", fg="#667085").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(5, 2))
        track = tk.Frame(card, bg="#edf1f7", height=8)
        track.grid(row=3, column=0, columnspan=2, sticky="ew",
                   padx=12, pady=(0, 12))
        fill = tk.Frame(track, bg="#98a2b3", height=8)
        fill.place(x=0, y=0, relwidth=0)
        values = {"status": status, "actual": actual,
                  "allowable": allowable, "ratio": ratio,
                  "track": track, "fill": fill}
        if title == "Bending":
            self.bending_values = values
            formula = "Bending stress = |maximum moment| x 12 / Sx"
        else:
            self.deflection_values = values
            formula = "Deflection limit = span in inches / 240 or / 360"
        card.bind("<Enter>", lambda _event,
                  text=formula: self._show_formula(card, text))
        card.bind("<Leave>", lambda _event: self._hide_formula(card))

    def _show_formula(self, card, formula):
        if not hasattr(card, "_formula_label"):
            card._formula_label = tk.Label(
                card, text=formula, bg="#eff6ff", fg="#1d4ed8",
                font=("Segoe UI", 8), wraplength=300)
            card._formula_label.grid(
                row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))

    def _hide_formula(self, card):
        if hasattr(card, "_formula_label"):
            card._formula_label.destroy()
            del card._formula_label

    def _render_load_rows(self):
        for widget in self.loads_container.winfo_children():
            widget.destroy()

        row_index = 0
        for load in self.uniform_loads:
            frame = ttk.Frame(self.loads_container, style="Card.TFrame")
            frame.grid(row=row_index, column=0, sticky="ew", pady=(0, 6))
            frame.columnconfigure((0, 1, 2), weight=1)
            ttk.Label(frame, text="Uniform", style="Card.TLabel").grid(
                row=0, column=0, sticky="w")
            ttk.Button(frame, text="Remove",
                       command=lambda load_id=load["id"]:
                       self._remove_load(load_id, "uniform")).grid(
                           row=0, column=2, sticky="e")
            self._load_field(frame, 1, 0, "Magnitude (k/ft)", "magnitude",
                             load, "uniform")
            self._load_field(frame, 1, 1, "Start (ft)", "start",
                             load, "uniform")
            self._load_field(frame, 1, 2, "End (ft)", "end",
                             load, "uniform")
            row_index += 1

        for load in self.point_loads:
            frame = ttk.Frame(self.loads_container, style="Card.TFrame")
            frame.grid(row=row_index, column=0, sticky="ew", pady=(0, 6))
            frame.columnconfigure((0, 1), weight=1)
            ttk.Label(frame, text="Point", style="Card.TLabel").grid(
                row=0, column=0, sticky="w")
            ttk.Button(frame, text="Remove",
                       command=lambda load_id=load["id"]:
                       self._remove_load(load_id, "point")).grid(
                           row=0, column=1, sticky="e")
            self._load_field(frame, 1, 0, "Magnitude (k)", "magnitude",
                             load, "point")
            self._load_field(frame, 1, 1, "Position (ft)", "position",
                             load, "point")
            row_index += 1

        self.load_count.configure(
            text=str(len(self.point_loads) + len(self.uniform_loads)))

    def _load_field(self, parent, row, column, label, key, load, kind):
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=row, column=column, sticky="ew", padx=(0, 4))
        ttk.Label(frame, text=label, style="Card.TLabel").pack(anchor="w")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, f"{float(load[key]):.3f}")
        entry.pack(fill="x")
        entry.bind("<KeyRelease>",
                   lambda _event, load_id=load["id"], field=key, lk=kind:
                   self._load_entry_changed(load_id, field, lk, entry))

    def _load_entry_changed(self, load_id, key, kind, entry):
        try:
            value = float(entry.get())
        except ValueError:
            return
        collection = self.point_loads if kind == "point" else self.uniform_loads
        load = next((item for item in collection if item["id"] == load_id), None)
        if load is None:
            return
        if key in ("position", "start", "end"):
            value = max(0.0, min(self.span, value))
        else:
            value = max(0.0, value)
        load[key] = value
        self.refresh()

    def _remove_load(self, load_id, kind):
        if kind == "point":
            self.point_loads = [x for x in self.point_loads if x["id"] != load_id]
        else:
            self.uniform_loads = [x for x in self.uniform_loads if x["id"] != load_id]
        self._render_load_rows()
        self.refresh()

    def _add_point_load(self):
        position = self.span / 2 if self.support == "simply-supported" else self.span
        self.point_loads.append({
            "id": self.next_load_id, "magnitude": 1.0, "position": position
        })
        self.next_load_id += 1
        self._render_load_rows()
        self.refresh()

    def _add_uniform_load(self):
        self.uniform_loads.append({
            "id": self.next_load_id, "magnitude": 1.0,
            "start": 0.0, "end": self.span
        })
        self.next_load_id += 1
        self._render_load_rows()
        self.refresh()

    def _support_changed(self):
        self.support = ("simply-supported"
                        if self.support_var.get() == "Simply supported"
                        else "cantilever")
        self._update_header()
        self.refresh()

    def _span_scale_changed(self, value):
        self.span = float(value)
        self.span_entry.delete(0, "end")
        self.span_entry.insert(0, f"{self.span:.3f}")
        self._update_header()
        self.refresh()

    def _span_entry_changed(self, _event):
        try:
            span = float(self.span_entry.get())
        except ValueError:
            return
        if 4 <= span <= 40:
            self.span = span
            self.span_scale.set(span)
            self._update_header()
            self.refresh()

    def _limit_changed(self):
        self.deflection_limit = 360 if self.limit_var.get() == "L/360" else 240
        self.refresh()

    def _material_changed(self):
        if self.material_var.get() == "Steel W-shapes":
            self.material = "steel"
            sections = list(beam.STEEL_SECTIONS)
            self.section = "W12x26"
        else:
            self.material = "lumber"
            sections = list(beam.LUMBER_SECTIONS)
            self.section = "2x8"
        self.section_combo.configure(values=sections)
        self.section_var.set(self.section)
        self.refresh()

    def _section_changed(self):
        self.section = self.section_var.get()
        self.refresh()

    def _update_header(self):
        self.header_badge.configure(
            text=f"{self.support_var.get()} - {self.span:g} ft")

    def _use_recommendation(self):
        if self.recommendation_section:
            self.section_var.set(self.recommendation_section)
            self.section = self.recommendation_section
            self.refresh()

    def refresh(self):
        try:
            self.result = beam.calculate(
                self.support, self.span, self.point_loads,
                self.uniform_loads, self.section,
                self.material, self.deflection_limit)
        except (KeyError, ValueError, ZeroDivisionError):
            return
        self._update_checks()
        self._draw_plots()

    def _update_check_card(self, values, actual, allowable, utilization, passed):
        values["actual"].set(actual)
        values["allowable"].set(allowable)
        values["ratio"].set(f"Utilization: {utilization:.1f}%")
        color = "#b42318" if utilization > 100 else (
            "#b45309" if utilization >= 70 else "#15803d")
        values["fill"].configure(bg=color)
        self.after_idle(lambda: values["fill"].place(
            x=0, y=0, relwidth=min(1.0, utilization / 100), height=8))
        values["status"].configure(
            text="PASS" if passed else "FAIL",
            bg="#ecfdf3" if passed else "#fff1f0",
            fg="#15803d" if passed else "#b42318")

    def _update_checks(self):
        result = self.result
        bending_ratio = result["bending_stress"] / result["allowable_bending"] * 100
        deflection_ratio = result["max_deflection"] / result["allowable_deflection"] * 100
        self._update_check_card(
            self.bending_values,
            f"Actual: {result['bending_stress']:.2f} ksi",
            f"Allowable: {result['allowable_bending']:.3f} ksi",
            bending_ratio, result["bending_pass"])
        self._update_check_card(
            self.deflection_values,
            f"Actual: {result['max_deflection']:.3f} in",
            f"Allowable: {result['allowable_deflection']:.3f} in",
            deflection_ratio, result["deflection_pass"])

        recommendation = result["recommendation"]
        self.recommendation_section = recommendation
        if recommendation:
            self.recommendation_text.set(f"{recommendation} passes both checks")
            self.use_button.configure(state="normal")
        else:
            self.recommendation_text.set("No section in this material passes")
            self.use_button.configure(state="disabled")
        self.span_tag.configure(text=f"{self.span:g} ft span")

    def _draw_plots(self):
        result = self.result
        x = result["x"]
        for ax in self.axes:
            ax.clear()
        beam_ax, shear_ax, moment_ax, deflection_ax = self.axes

        beam_ax.set_xlim(0, self.span)
        beam_ax.set_ylim(-0.6, 1.6)
        beam_ax.axis("off")
        beam_ax.set_title("Beam", loc="left", fontsize=10, fontweight="bold")
        beam_y = 0.45
        beam_ax.plot([0, self.span], [beam_y, beam_y],
                     color="#344054", lw=7, solid_capstyle="round")
        if self.support == "simply-supported":
            beam_ax.plot([0, 0], [0.05, beam_y], color="#344054", lw=2)
            beam_ax.plot([0, -0.25], [0.05, -0.18], color="#344054", lw=2)
            beam_ax.plot([0, 0.25], [0.05, -0.18], color="#344054", lw=2)
            beam_ax.plot([self.span, self.span], [0.05, beam_y],
                         color="#344054", lw=2)
            beam_ax.plot([self.span - 0.25, self.span + 0.25],
                         [0.05, 0.05], color="#344054", lw=2)
        else:
            beam_ax.plot([-0.18, 0.18],
                         [beam_y - 0.38, beam_y - 0.38],
                         color="#344054", lw=3)
            beam_ax.add_patch(matplotlib.patches.Rectangle(
                (-0.18, beam_y - 0.32), 0.36, 0.64,
                facecolor="#eef2f6", edgecolor="#344054"))

        if result["reactions"]["left"] is not None:
            beam_ax.annotate(
                f"{result['reactions']['left']:.2f} k",
                xy=(0, beam_y), xytext=(0, 1.25), ha="center",
                arrowprops={"arrowstyle": "->", "color": "#15803d"},
                color="#15803d", fontsize=9, fontweight="bold")
        if result["reactions"]["right"] is not None:
            beam_ax.annotate(
                f"{result['reactions']['right']:.2f} k",
                xy=(self.span, beam_y), xytext=(self.span, 1.25), ha="center",
                arrowprops={"arrowstyle": "->", "color": "#15803d"},
                color="#15803d", fontsize=9, fontweight="bold")

        for load in self.uniform_loads:
            start = max(0.0, load["start"])
            end = min(self.span, load["end"])
            if end > start:
                positions = start + (end - start) * (
                    2 * __import__("numpy").arange(9) + 1) / 18
                for position in positions:
                    beam_ax.annotate(
                        "", xy=(position, beam_y + 0.08),
                        xytext=(position, 0.95),
                        arrowprops={"arrowstyle": "->", "color": "#2563eb"})
                beam_ax.text((start + end) / 2, 1.48,
                             f"{load['magnitude']:.2f} kip/ft",
                             ha="center", color="#2563eb",
                             fontsize=9, fontweight="bold")
        for load in self.point_loads:
            position = max(0.0, min(self.span, load["position"]))
            beam_ax.annotate(
                f"{load['magnitude']:.2f} k",
                xy=(position, beam_y), xytext=(position, 1.15), ha="center",
                arrowprops={"arrowstyle": "->", "color": "#2563eb"},
                color="#2563eb", fontsize=8)

        shear_ax.set_title("Shear (kips)", loc="left",
                           fontsize=10, fontweight="bold")
        moment_ax.set_title("Moment (kip-ft)", loc="left",
                            fontsize=10, fontweight="bold")
        deflection_ax.set_title("Deflection (in)", loc="left",
                                 fontsize=10, fontweight="bold")

        for ax, values, label, unit in (
            (shear_ax, result["shear"], "shear", "k"),
            (moment_ax, result["moment"], "moment", "kip-ft"),
            (deflection_ax, result["deflection"], "deflection", "in"),
        ):
            ax.fill_between(x, 0, values, color="#dbeafe", alpha=0.9)
            ax.plot(x, values, color="#2563eb", lw=1.8)
            ax.axhline(0, color="#98a2b3", lw=0.8)
            extreme_i = int(abs(values).argmax())
            if label == "deflection":
                text = f"{values[extreme_i]:.3f}"
            else:
                text = f"{values[extreme_i]:.2f}"
            ax.annotate(text, xy=(x[extreme_i], values[extreme_i]),
                        xytext=(0, 10), textcoords="offset points",
                        ha="center", color="#2563eb",
                        fontsize=8, fontweight="bold")
            ax.set_xlim(0, self.span)
            ax.grid(True, axis="x", color="#e4e7ec", linewidth=0.8)
            ax.tick_params(labelsize=8)
        deflection_ax.set_xlabel("Position (ft)")

        self.cursor_lines = []
        for ax in self.axes:
            self.cursor_lines.append(ax.axvline(
                0, color="#101828", lw=1, ls="--", visible=False))
        self.figure.tight_layout(pad=0.8)
        self.canvas.draw_idle()

    def _on_mouse_move(self, event):
        if self.dragging_load_id is not None:
            if event.inaxes is not None and event.xdata is not None:
                position = round(max(0.0, min(self.span, event.xdata)) * 4) / 4
                load = next((x for x in self.point_loads
                             if x["id"] == self.dragging_load_id), None)
                if load:
                    load["position"] = position
                    self._render_load_rows()
                    self.refresh()
            return

        if event.xdata is None or event.inaxes not in self.axes:
            for line in self.cursor_lines:
                line.set_visible(False)
            self.cursor_label.configure(
                text="Position: -- | Shear: -- | Moment: -- | Deflection: --")
            self.canvas.draw_idle()
            return

        position = max(0.0, min(self.span, float(event.xdata)))
        for line in self.cursor_lines:
            line.set_xdata([position, position])
            line.set_visible(True)
        x = self.result["x"]
        index = abs(x - position).argmin()
        self.cursor_label.configure(
            text=(f"Position: {position:.2f} ft | "
                  f"Shear: {self.result['shear'][index]:.2f} k | "
                  f"Moment: {self.result['moment'][index]:.2f} kip-ft | "
                  f"Deflection: {self.result['deflection'][index]:.3f} in"))
        self.canvas.draw_idle()

    def _on_point_press(self, event):
        if event.inaxes is not self.axes[0] or event.xdata is None:
            return
        nearest = None
        nearest_distance = float("inf")
        for load in self.point_loads:
            distance = abs(load["position"] - event.xdata)
            if distance < nearest_distance:
                nearest = load
                nearest_distance = distance
        if nearest and nearest_distance <= max(0.4, self.span / 60):
            self.dragging_load_id = nearest["id"]

    def _on_point_release(self, _event):
        if self.dragging_load_id is not None:
            self.dragging_load_id = None
            self._render_load_rows()
            self.refresh()


def main():
    app = BeamApp()
    app.mainloop()


if __name__ == "__main__":
    main()
