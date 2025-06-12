# Select Duplicate Objects with Tolerances in Rhino3D

This Rhino script detects and selects **duplicate geometry** within a set of selected objects using both **distance** and **angular** tolerances. It works with curves, breps (including extrusions), points, and block instances, making it especially useful for cleaning up messy models or preparing geometry for export or fabrication.

## What Does the Script Do?

The **Select Duplicates with Tolerances** tool allows you to:

* Select any number of objects in the model.
* Define a **distance tolerance** and an **angle tolerance (in degrees)**.
* Automatically search for potential duplicates using bounding box and spatial indexing.
* Perform geometry-type-specific comparison:

  * **Block instances**: Checks block name, position, and orientation.
  * **Curves**: Compares sampled point distances and tangent angles.
  * **BREPs**: Compares face points and normals.
  * **Points**: Compares Euclidean distance.
* Selects only the *duplicate* object among each pair (i.e., leaves the original unselected).

## Why Use It?

Manual duplicate detection in Rhino can be extremely time-consuming and unreliable, especially when working with:

* Imported geometry
* Geometry exploded from blocks or groups
* Converted or regenerated forms
* Slightly misaligned or rotated duplicates

This tool provides an automated, tolerance-based method to detect and clean up redundancy, improving model hygiene, file performance, and export quality.

## How to Use the Script

### Load the Script in Rhino

**Method 1**:

1. Type `_RunPythonScript` in the command line.
2. Browse to the location where you saved the script and select it.

### Method 2 Creating a Button or Alias for Easy Access (Optional)

#### Creating a Toolbar Button

1. **Right-click** on an empty area of the toolbar and select **New Button**.
2. In the **Button Editor**:

   * **Left Button Command**:

     ```plaintext
     ! _-RunPythonScript "FullPathToYourScript\select_duplicates_with_tolerances.py"
     ```

     Replace `FullPathToYourScript` with the actual file path.
   * **Tooltip and Help**: Add something like: `Find and select duplicates within tolerance`.
   * **Icon (Optional)**: Assign an icon for visual identification.

#### Creating an Alias

1. Go to **Tools > Options > Aliases**.

2. **Create a New Alias**:

   * **Alias**: e.g., `finddupes`
   * **Command Macro**:

     ```plaintext
     _-RunPythonScript "FullPathToYourScript\select_duplicates_with_tolerances.py"
     ```

3. **Use the Alias**: Type the alias (e.g., `finddupes`) into the command line and press **Enter**.

### Using the Command

1. **Select** the objects you want to check.
2. When prompted:

   * **Enter distance tolerance**: Defines positional similarity.
   * **Enter angle tolerance (in degrees)**: Defines angular similarity for tangents/normals.
3. The script will:

   * Use bounding boxes and an RTree for fast candidate lookup.
   * Compare geometry in pairs within tolerance bounds.
   * Select duplicate instances while leaving one original untouched.

The command line will print how many duplicate objects were selected.

## Technical Notes

* **Block Instances**: Compared by name, insertion point, and primary X-axis of transformation.
* **BREPs**: Compared face-by-face using sampled points and surface normals.
* **Curves**: Compared using tangents and distances at multiple domain samples.
* **Points**: Compared by direct distance.
* **Extrusions**: Automatically converted to BREPs for evaluation.
* Script skips geometry with incompatible types or unsupported forms.
* Uses `ModelAbsoluteTolerance` as a default fallback for distance if not specified.
