# Beam Designer

Purpose

A beam design tool for engineers and students. The user sets up a beam, places loads on it, and picks a steel or lumber section. The app shows the shear, moment, and deflection diagrams and checks whether the beam is strong and stiff enough, updating instantly as anything changes.

Users

A civil engineering student checking a homework beam, or an engineer sizing a floor beam or deck joist.

Platform

Python desktop app using Tkinter, started with python app.py

Calculations with numpy, kept in their own module, separate from the window code

Diagrams drawn with matplotlib, embedded in the window

Inputs

Support type: Simply supported or Cantilever (fixed at the left end).

Span: 4 to 40 ft, set with a slider and a number box that stay in sync.

Loads, listed in a panel where each can be edited or removed:

Point loads: magnitude (kips, downward positive) and position (ft). A new point load starts at midspan (at the free end of a cantilever).

Uniform loads: magnitude (kips/ft) and start and end positions (ft).

"Add point load" and "Add uniform load" buttons.

Point loads can also be dragged along the beam in the drawing, snapping to 0.25 ft.

Loads that extend past the end of the beam are cut off at the end.

Material and section, from these tables:

Steel W-shapes (E = 29,000 ksi, allowable bending stress Fb = 30 ksi):

Section

Ix (in^4)

Sx (in^3)

Weight (lb/ft)

W8x10

30.8

7.81

10

W10x12

53.8

10.9

12

W12x26

204

33.4

26

W14x22

199

29.0

22

W16x26

301

38.4

26

W18x35

510

57.6

35

W21x44

843

81.6

44

W24x55

1350

114

55

Douglas Fir-Larch No. 2 lumber (E = 1,600 ksi, Fb = 0.900 ksi):

Section

Ix (in^4)

Sx (in^3)

2x8

47.63

13.14

2x10

98.93

21.39

2x12

177.98

31.64

Deflection limit: L/240 or L/360 (default L/360).

Self-weight is ignored.

Calculations

Reactions from statics.

Shear V(x) and moment M(x) along the beam, at 1 ft spacing or finer, plus exactly at every load point and load start/end.

Deflection y(x) by integrating M/EI twice with the boundary conditions for the support type (y = 0 at both supports; or y = 0 and slope = 0 at the fixed end).

Bending stress fb = |M max| x 12 / Sx (ksi). Bending check passes if fb <= Fb.

Deflection check passes if |y max| <= L/240 or L/360 (L in inches).

Lightest passing section: of the sections in the chosen material, the lightest steel section that passes both checks (if two weigh the same, the one with the larger Ix), or the first lumber size in the table that passes.

Units: kips, ft, and kip-ft on screen; inches for deflection.

Outputs

A beam drawing with the supports, load arrows (point loads as single arrows, uniform loads as a row of small arrows), and the reactions.

Three diagrams stacked under the beam and lined up with it on the same x scale: shear (kips), moment (kip-ft), and deflected shape (in). Each diagram is filled and shows its maximum value labeled at its location.

Moving the mouse over any diagram shows a vertical line across all three with the values of V, M, and y at that x.

Two check cards: Bending and Deflection. Each shows the actual value, the allowable value, a bar for the ratio (green under 70%, amber 70-100%, red over 100%), and PASS or FAIL.

A line suggesting the lightest passing section, with a button to use it.

Everything updates immediately whenever any input changes.

Look and feel

Opens with an example already loaded (20 ft simply supported W12x26 with a 1 kip/ft uniform load over the full span), so it is useful the moment it opens.

Clean and professional, like a commercial engineering desktop app: light background, white panels with soft shadows, one accent color, a modern system font, and generous spacing. No clutter.

Inputs in a panel on the left; the beam, diagrams, and checks on the right.

The window can be resized, and the layout adjusts to use the available space.

Every input has a short label with units. Hovering over a check card explains the formula used.

Validation

The three selected cases were run directly through `beam_calculations.calculate` with
recommendation calculation disabled. Values below are expected independent results
compared with actual function results; rounding is shown to the requested precision.

| Case and check | Expected | Actual | Result |
|---|---:|---:|---|
| 1: reactions (left, right), k | (10.000, 10.000) | (10.000, 10.000) | PASS |
| 1: maximum moment, kip-ft | 50.000 | 50.000 | PASS |
| 1: maximum bending stress, ksi | 17.964 | 17.964 | PASS |
| 1: maximum deflection, in | 0.6085 | 0.6085 | PASS |
| 1: bending / deflection checks | PASS / PASS | PASS / PASS | PASS |
| 2: fixed reaction, k | 5.000 | 5.000 | PASS |
| 2: fixed-end moment, kip-ft | 50.000 | 50.000 | PASS |
| 2: maximum deflection, in | 0.4868 | 0.4868 | PASS |
| 2: deflection check at L/360 | FAIL | FAIL | PASS |
| 3: reactions (left, right), k | (0.300, 0.300) | (0.300, 0.300) | PASS |
| 3: maximum moment, kip-ft | 0.900 | 0.900 | PASS |
| 3: maximum bending stress, ksi | 0.5049 | 0.5049 | PASS |
| 3: maximum deflection, in | 0.1474 | 0.1474 | PASS |
| 3: bending / deflection checks | PASS / PASS | PASS / PASS | PASS |

Case 1 also passed the symmetry check: left/right reaction error was 0.0,
maximum moment symmetry error was less than 4.1e-14 kip-ft, and maximum
deflection symmetry error was less than 1.3e-15 in.

Independent expected-value sources:

- Case 1: for a full-span uniform load, `R = wL/2 = 10 k`,
  `Mmax = wL^2/8 = 50 kip-ft`, and
  `fb = Mmax*12/Sx = 50*12/33.4 = 17.964 ksi`. The standard
  simply supported UDL deflection equation `5wL^4/(384EI)` gives
  approximately 0.6085 in after converting feet to inches.
- Case 2: `Mfixed = PL = 5*10 = 50 kip-ft` and the standard cantilever
  end-load equation `PL^3/(3EI)` gives approximately 0.4868 in.
- Case 3: the application uses Douglas Fir-Larch No. 2 `2x10` properties
  `E = 1600.0 ksi`, `Ix = 98.93 in^4`, and `Sx = 21.39 in^3`.
  Independent equations give `R = 0.05*12/2 = 0.300 k`,
  `Mmax = 0.05*12^2/8 = 0.900 kip-ft`, and
  `fb = 0.900*12/21.39 = 0.5049 ksi`; the standard UDL deflection
  equation gives approximately 0.1474 in.

The other specification cases remain additional validation targets:

Simply supported, 20 ft, W12x26, point load 10 k at 5 ft:
reactions 7.5 k (left) and 2.5 k (right); max moment 37.5 kip-ft at 5 ft; fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.

Simply supported, 30 ft, W18x35, uniform 2 kips/ft from 0 to 15 ft only:
reactions 22.5 k (left) and 7.5 k (right); max moment 126.6 kip-ft at 11.25 ft.

## Option A Desktop Features

- File menu with Save and Open options.
- Save beam designs to a file, including support type,
  span, section, deflection limit, and all loads.
- Open previously saved beam design files and restore
  all saved inputs in the application.
Export beam results to a CSV file, including x-position, shear, moment, and deflection values along the beam.

The CSV file must be compatible with Excel.

Export a PDF calculation sheet containing the beam inputs, beam and load diagram, shear diagram, moment diagram, deflection diagram, and bending and deflection checks.

Format the PDF clearly and professionally for engineering review.

Out of scope

Self-weight, shear stress, lateral-torsional buckling, load combinations, and continuous beams.

