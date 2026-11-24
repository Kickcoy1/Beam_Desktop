# Beam Designer

Beam Designer is a Python Tkinter desktop application for student and educational beam analysis. It analyzes simply supported and cantilever beams, displays shear, moment, and deflection diagrams, and helps compare steel or lumber sections.

## Features

- Analyze simply supported and cantilever beams.
- Add, edit, remove, and drag point loads.
- Add and edit uniform loads.
- View beam loading and synchronized shear, moment, and deflection diagrams.
- Check bending stress and deflection with clear PASS or FAIL results.
- Recommend the lightest steel section or first passing lumber section.
- Save and open beam designs as JSON files.
- Export beam results as an Excel-compatible CSV file.
- Export a professional PDF calculation sheet.

## Requirements

- Python 3
- Tkinter, normally included with standard Python installations
- NumPy
- Matplotlib

## Install Dependencies

From the project directory, install NumPy and Matplotlib:

```text
python -m pip install numpy matplotlib
```

## Run the Application

From the project directory, run:

```text
python app.py
```

## Using the Application

1. Choose a simply supported or cantilever beam.
2. Set the span, deflection limit, material, and section.
3. Add point or uniform loads and edit their values and locations.
4. Review the diagrams and bending and deflection check cards.
5. Use the section recommendation button to select a passing section.
6. Use **File > Save** or **File > Open** to save or restore a design.
7. Use **File > Export CSV** or **File > Export PDF** to export results or a calculation sheet.

This application is an educational beam-design tool. It is not a substitute for professional engineering judgment or review.
