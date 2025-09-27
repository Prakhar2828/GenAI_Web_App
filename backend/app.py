import shutil
import os
import zipfile
import uuid
import datetime
import subprocess
import json
import requests
from flask import Flask, request, jsonify, send_file, abort, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from PyPDF2 import PdfReader
import re

app = Flask(
__name__,
static_folder='frontend/build',   # ← where we copy npm run build into
static_url_path=''                # ← serve those files at “/…”
)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    # if this matches a file in build/, serve it
    full_path = os.path.join(app.static_folder, path)
    if path and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    # otherwise serve index.html so React Router can take over
    return send_from_directory(app.static_folder, 'index.html')

UPLOAD_FOLDER = 'uploads'
SIMULATION_OUTPUT_FOLDER = 'simulation_outputs'
DEFAULT_EXE_FOLDER = 'executables'
ALLOWED_EXTENSIONS = {'txt', 'csv', 'json', 'xml', 'int', 'dat', 'out', 'exe'}
DEFAULT_EXE_NAME = 'intgrats.exe'

# Create necessary directories if they don't exist
for folder in [UPLOAD_FOLDER, SIMULATION_OUTPUT_FOLDER, DEFAULT_EXE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simulations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

##############################################################################
# MODELS
##############################################################################

class SimulationRun(db.Model):
    id = db.Column(db.String, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    input_files = db.Column(db.Text)  # JSON list of filenames (stringified)
    output_file = db.Column(db.String)
    error_file = db.Column(db.String)
    exe_used = db.Column(db.String)
    sim_metadata = db.Column(db.Text)  # Additional metadata

with app.app_context():
    db.create_all()

##############################################################################
# AUTH ENDPOINT
##############################################################################

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    # In a real application, use hashed passwords and proper auth libraries
    if username == "admin" and password == "password":
        # Generate a real token in a production app
        return jsonify({"message": "Login successful", "token": "dummy_token"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

##############################################################################
# HELPER FUNCTION
##############################################################################

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

##############################################################################
# FILE UPLOAD ENDPOINT
##############################################################################

@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('input_file')
    exe_file = request.files.get('exe')

    if not uploaded_files:
        return jsonify({"error": "No input files provided."}), 400

    saved_input_files = []
    # Use a temporary unique subfolder for this upload batch if needed
    # For simplicity, saving directly to UPLOAD_FOLDER with unique names
    upload_batch_id = str(uuid.uuid4())

    for f in uploaded_files:
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            # Prefix with UUID to avoid collisions, keep original name for reference
            unique_filename = f"{upload_batch_id}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            f.save(file_path)
            saved_input_files.append(file_path) # Store the full path
        elif f: # File was provided but not allowed
             # Clean up already saved files from this batch? Optional.
             return jsonify({"error": f"File type not allowed: {f.filename}"}), 400
        # If f is None, it's okay, just means not all potential file inputs were used

    # If an executable file is provided, save it; otherwise use the default one.
    exe_used_path = None # Path to the exe to be used for simulation
    if exe_file:
         if allowed_file(exe_file.filename) and exe_file.filename.lower().endswith('.exe'): # Ensure .exe check is case-insensitive
             exe_filename = secure_filename(exe_file.filename)
             unique_exe_filename = f"{upload_batch_id}_{exe_filename}"
             # Consider saving uploaded EXEs to a specific subfolder or UPLOAD_FOLDER
             exe_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_exe_filename)
             exe_file.save(exe_path)
             exe_used_path = exe_path
         else:
              # Clean up saved input files? Optional.
              return jsonify({"error": "Invalid or non-EXE executable file provided."}), 400
    else:
        # Use the default executable if none was uploaded
        default_exe_path = os.path.join(DEFAULT_EXE_FOLDER, DEFAULT_EXE_NAME)
        if not os.path.exists(default_exe_path):
             # Clean up saved input files? Optional.
            return jsonify({"error": f"Default executable '{DEFAULT_EXE_NAME}' not found in '{DEFAULT_EXE_FOLDER}'."}), 500
        exe_used_path = default_exe_path

    return jsonify({
        "message": "Files uploaded successfully.",
        "input_files": saved_input_files, # List of paths to saved input files
        "exe_used": exe_used_path # Path to the executable to use
        }), 200

##############################################################################
# SIMULATION ENDPOINT (Launch intgrats.exe directly or via shell)
##############################################################################

@app.route('/simulate', methods=['POST'])
def run_simulation():
    """
    Expects JSON with:
      - input_files (list of full paths to previously uploaded files)
      - exe_used (full path to the executable to use)
      - metadata (optional JSON object or string)
    One of the input files must be a master file (e.g., name contains "master" or is "INET_I.INT").
    This endpoint launches the specified intgrats.exe.
    """
    data = request.get_json()
    input_file_paths = data.get('input_files', []) # Expecting full paths from upload response
    exe_to_use = data.get('exe_used') # Expecting full path from upload response
    metadata = data.get('metadata', {}) # Can be string or dict

    if not input_file_paths or not isinstance(input_file_paths, list):
        return jsonify({"error": "Missing or invalid 'input_files' list in request."}), 400
    if not exe_to_use or not isinstance(exe_to_use, str):
        return jsonify({"error": "Missing or invalid 'exe_used' path in request."}), 400

    # Verify executable exists
    if not os.path.exists(exe_to_use):
         return jsonify({"error": f"Specified executable not found: {exe_to_use}"}), 404

    # Verify all input files exist (they should, as paths come from successful upload)
    verified_input_paths = []
    for input_path in input_file_paths:
        if not os.path.exists(input_path):
             # This indicates a server-side issue if paths came from upload response
             return jsonify({"error": f"Uploaded input file not found: {input_path}. Please try uploading again."}), 404
        verified_input_paths.append(input_path)

    # Find the master file (assuming base name contains "master" or is INET_I.INT, case-insensitive)
    # We need the *basename* for the command line argument, but the full path to locate it.
    master_file_path = None
    master_file_basename = None
    for file_path in verified_input_paths:
        basename = os.path.basename(file_path)
        # Check if filename contains "master" or is exactly "INET_I.INT" (case-insensitive)
        if "master" in basename.lower() or basename.lower() == "inet_i.int": # Updated check for .int
            master_file_path = file_path
            master_file_basename = basename # Use the original basename
            break

    # If no specific master file found by name check, maybe fall back to the first .int file? (Optional logic)
    # For now, stick to the explicit check.
    if not master_file_path:
         # This check is now redundant if the loop above checks for inet_i.int
         # inet_files = [p for p in verified_input_paths if os.path.basename(p).upper() == "INET_I.INT"] # Updated check
         # if inet_files:
         #     master_file_path = inet_files[0]
         #     master_file_basename = os.path.basename(master_file_path)
         # else:
            return jsonify({"error": "Could not find a suitable master input file (e.g., containing 'master' or named 'INET_I.INT') among uploaded files."}), 400


    # --- Simulation Execution ---
    run_id = str(uuid.uuid4())
    output_filename = f"{run_id}_output.txt"
    error_filename = f"{run_id}_error.txt"
    output_file_path = os.path.join(SIMULATION_OUTPUT_FOLDER, output_filename)
    error_file_path = os.path.join(SIMULATION_OUTPUT_FOLDER, error_filename)

    # Run from the executable's directory, passing only the master file's basename.
    exe_cwd = os.path.dirname(exe_to_use) # Directory where the executable resides
    command = [exe_to_use, master_file_basename] # Pass only the basename

    # Crucial Assumption: The executable ('intgrats.exe') when run from its directory ('exe_cwd')
    # must be able to find *all other required input files* (besides the master file passed as argument)
    # based on relative paths or internal logic, assuming they are also in 'exe_cwd'.
    # If input files are uploaded to UPLOAD_FOLDER and the exe is elsewhere, this will likely fail unless
    # files are copied to the CWD before running. Sticking to the simpler assumption for now.

    try:
        with open(output_file_path, 'w') as out_f, open(error_file_path, 'w') as err_f:
            subprocess.run(
                command,
                stdout=out_f,
                stderr=err_f,
                text=True,
                cwd=exe_cwd, # Run from the executable's directory
                check=True # Raise exception on non-zero exit code
            )

        # Record simulation run in the database.
        run_record = SimulationRun(
            id=run_id,
            input_files=json.dumps(verified_input_paths), # Store original full paths
            output_file=output_file_path,
            error_file=error_file_path,
            exe_used=exe_to_use, # Store full path used
            sim_metadata=json.dumps(metadata) if isinstance(metadata, dict) else str(metadata)
        )
        db.session.add(run_record)
        db.session.commit()

        return jsonify({"message": "Simulation completed successfully", "run_id": run_id}), 200

    except subprocess.CalledProcessError as e:
         # Read error file content if simulation failed
        error_content = ""
        if os.path.exists(error_file_path):
            try:
                 with open(error_file_path, 'r') as err_f:
                     error_content = err_f.read()
            except Exception as read_err:
                 print(f"Error reading error file {error_file_path}: {read_err}")
                 error_content = f"[Error reading error file: {read_err}]"

        # Log failed attempt
        run_record_failed = SimulationRun(
             id=run_id, input_files=json.dumps(verified_input_paths),
             output_file=output_file_path, error_file=error_file_path,
             exe_used=exe_to_use,
             sim_metadata=json.dumps({"error": "CalledProcessError", "return_code": e.returncode, "command": " ".join(command), "metadata": metadata})
        )
        db.session.add(run_record_failed)
        db.session.commit()
        return jsonify({
            "error": f"Simulation failed with exit code {e.returncode}",
            "details": error_content or str(e),
            "command_used": " ".join(command),
            "run_id": run_id
        }), 500
    except FileNotFoundError as fnf_error:
         # This might happen if exe_to_use is invalid *during* subprocess.run
         details = f"Executable not found during execution attempt. Path: {str(fnf_error)}"
         # Log attempt
         try:
             metadata_fnf = {"error": "FileNotFoundError", "details": details, "command": " ".join(command), "metadata": metadata}
             run_record_fnf = SimulationRun(
                 id=run_id, output_file=output_file_path, error_file=error_file_path,
                 input_files=json.dumps(verified_input_paths), exe_used=exe_to_use,
                 sim_metadata=json.dumps(metadata_fnf)
             )
             db.session.add(run_record_fnf)
             db.session.commit()
         except Exception as db_err: print(f"DB log error (FileNotFound): {db_err}")
         return jsonify({"error": "File Not Found Error during execution", "details": details, "run_id": run_id}), 500

    except Exception as ex:
        details = f"An unexpected error occurred during simulation execution: {str(ex)}"
        # Log general exception attempt
        try:
            run_record_ex = SimulationRun(
                 id=run_id, input_files=json.dumps(verified_input_paths),
                 output_file=output_file_path, error_file=error_file_path,
                 exe_used=exe_to_use,
                 sim_metadata=json.dumps({"error": "Other Exception", "details": str(ex), "metadata": metadata})
            )
            db.session.add(run_record_ex)
            db.session.commit()
        except Exception as db_err:
             print(f"Failed to log exception details to DB: {db_err}")

        return jsonify({"error": "Simulation failed due to an unexpected server error.", "details": details, "run_id": run_id}), 500


##############################################################################
# SAMPLE SIMULATION ENDPOINT
##############################################################################
@app.route('/run_sample', methods=['POST'])
def run_sample_simulation():
    run_id = str(uuid.uuid4()) # Generate run_id at the beginning
    output_filename = f"{run_id}_output.txt"
    error_filename = f"{run_id}_error.txt"
    output_file_path = os.path.join(SIMULATION_OUTPUT_FOLDER, output_filename)
    error_file_path = os.path.join(SIMULATION_OUTPUT_FOLDER, error_filename)

    integration_dir = None # Define scope outside try block
    exe_path = None
    # --- !!! CORRECTED FILENAME HERE !!! ---
    input_name = "INET_I.INT" # Corrected sample input name
    # --- !!! ---

    try:
        # Path to integration directory (relative to app.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        integration_dir = os.path.join(base_dir, "integration") # Assuming 'integration' is a subdir

        # Define executable name
        exe_name = "intgrats.exe" # Hardcoded sample exe name

        # Construct full paths
        exe_path = os.path.join(integration_dir, exe_name)
        input_path_in_integration_dir = os.path.join(integration_dir, input_name) # Uses corrected input_name
        input_path_relative_to_cwd = input_name # The exe expects the input file name in its CWD (uses corrected input_name)

        # Check if necessary files/dirs exist BEFORE running
        if not os.path.isdir(integration_dir):
             return jsonify({"error": f"Sample integration directory not found: {integration_dir}"}), 500
        if not os.path.exists(exe_path):
            return jsonify({"error": f"Sample executable not found: {exe_path}"}), 500
        # This check now uses the corrected input filename
        if not os.path.exists(input_path_in_integration_dir):
             return jsonify({"error": f"Sample input file '{input_name}' not found in integration directory: {integration_dir}"}), 500 # Updated error message

        # Command uses the corrected relative input name
        command = [exe_path, input_path_relative_to_cwd]

        # Run the command directly in the integration directory
        with open(output_file_path, 'w') as out_f, open(error_file_path, 'w') as err_f:
            result = subprocess.run(
                command,
                stdout=out_f,
                stderr=err_f,
                text=True,
                cwd=integration_dir,  # Important: Run from integration directory
                check=False # Don't raise exception on failure, check returncode instead
            )

        # Read the output (always attempt to read, even if run failed)
        output_content = ""
        if os.path.exists(output_file_path):
            try:
                with open(output_file_path, 'r') as out_f:
                    output_content = out_f.read()
            except Exception as read_err:
                 print(f"Error reading output file {output_file_path}: {read_err}")
                 output_content = f"[Error reading output file: {read_err}]"


        # Check return code AFTER attempting to read output/error
        if result.returncode != 0:
            error_content = ""
            if os.path.exists(error_file_path):
                try:
                     with open(error_file_path, 'r') as err_f:
                        error_content = err_f.read()
                except Exception as read_err:
                     print(f"Error reading error file {error_file_path}: {read_err}")
                     error_content = f"[Error reading error file: {read_err}]"

            # Log the failed run attempt (uses corrected input_name)
            metadata_failed = {"type": "sample_run_failed", "command": " ".join(command), "return_code": result.returncode}
            run_record_failed = SimulationRun(
                id=run_id,
                input_files=json.dumps([os.path.join("integration", input_name)]), # Log relative path used in command
                output_file=output_file_path,
                error_file=error_file_path,
                exe_used=exe_path, # Log full path used for execution
                sim_metadata=json.dumps(metadata_failed)
            )
            db.session.add(run_record_failed)
            db.session.commit()
            return jsonify({
                "error": f"Sample simulation failed with exit code {result.returncode}",
                "details": error_content,
                "command_used": " ".join(command),
                "run_id": run_id # Return run_id even on failure
            }), 500

        # Record successful run in database (uses corrected input_name)
        metadata_success = {"type": "sample_run", "command": " ".join(command)}
        run_record_success = SimulationRun(
            id=run_id,
            input_files=json.dumps([os.path.join("integration", input_name)]), # Log relative path
            output_file=output_file_path,
            error_file=error_file_path,
            exe_used=exe_path, # Log full path used
            sim_metadata=json.dumps(metadata_success)
        )
        db.session.add(run_record_success)
        db.session.commit()

        return jsonify({
            "message": "Sample simulation completed successfully",
            "output": output_content, # Include output content in success response
            "run_id": run_id
        }), 200

    except FileNotFoundError as fnf_error:
         # Specifically catch if the executable path itself is invalid *before* subprocess.run
         details = f"Executable or integration directory not found during setup. Path: {str(fnf_error)}"
         # Attempt to log (uses corrected input_name)
         try:
             metadata_fnf = {"type": "sample_run_setup_error", "error": "FileNotFoundError", "details": details}
             run_record_fnf = SimulationRun(
                 id=run_id, output_file=output_file_path, error_file=error_file_path,
                 exe_used=str(exe_path), input_files=json.dumps([os.path.join("integration", input_name)]),
                 sim_metadata=json.dumps(metadata_fnf)
             )
             db.session.add(run_record_fnf)
             db.session.commit()
         except Exception as db_err: print(f"DB log error (FileNotFound): {db_err}")
         return jsonify({"error": "File Not Found Error during setup", "details": details, "run_id": run_id}), 500

    except Exception as e:
        # General exception handler
        details = f"An unexpected error occurred: {str(e)}"
        # Attempt to log if possible (uses corrected input_name)
        try:
            metadata_exception = {"type": "sample_run_exception", "error": str(e)}
            run_record_exception = SimulationRun(
                id=run_id,
                input_files=json.dumps([os.path.join("integration", input_name)]) if integration_dir else json.dumps(["unknown"]),
                output_file=output_file_path,
                error_file=error_file_path,
                exe_used=str(exe_path) if exe_path else "unknown",
                sim_metadata=json.dumps(metadata_exception)
            )
            db.session.add(run_record_exception)
            db.session.commit()
        except Exception as db_err:
            print(f"Failed to log exception details to DB: {db_err}")

        return jsonify({
            "error": "Exception occurred during sample simulation",
            "details": details,
            "run_id": run_id # Return run_id even on failure
        }), 500


##############################################################################
# DOWNLOAD, RUNS LIST, ADMIN, & LLM ENDPOINTS
##############################################################################

@app.route('/download/<run_id>', methods=['GET'])
def download_run(run_id):
    run = SimulationRun.query.get(run_id)
    if not run:
        abort(404, description="Simulation run not found.")

    zip_filename = os.path.join(SIMULATION_OUTPUT_FOLDER, f"{run_id}_archive.zip")

    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add input files (if they still exist)
            if run.input_files:
                try:
                    input_files_list = json.loads(run.input_files)
                    if isinstance(input_files_list, list):
                         zipf.writestr(f"{run_id}_inputs_list.txt", "\n".join(input_files_list)) # Add list of inputs
                         # Add individual input files - might fail if cleaned up
                         inputs_dir_arcname = f"{run_id}_inputs"
                         for file_path in input_files_list:
                              if os.path.exists(file_path):
                                   # Add file to a subfolder within the zip
                                   zipf.write(file_path, os.path.join(inputs_dir_arcname, os.path.basename(file_path)))
                              else:
                                   print(f"Warning: Input file {file_path} for run {run_id} not found for zipping.")
                                   zipf.writestr(os.path.join(inputs_dir_arcname, os.path.basename(file_path) + ".missing.txt"), f"File not found at path: {file_path}")


                except json.JSONDecodeError:
                    zipf.writestr(f"{run_id}_inputs_list.txt", f"Error decoding input file list: {run.input_files}")
                except Exception as e:
                     print(f"Error processing input files for zip {run_id}: {e}")
                     zipf.writestr(f"{run_id}_inputs_processing_error.txt", str(e))


            # Add output file (if exists)
            if run.output_file and os.path.exists(run.output_file):
                zipf.write(run.output_file, os.path.basename(run.output_file))
            elif run.output_file:
                 zipf.writestr(os.path.basename(run.output_file) + ".missing.txt", "Output file was not found on the server.")


            # Add error file (if exists)
            if run.error_file and os.path.exists(run.error_file):
                # Only add if it has content? Optional.
                # if os.path.getsize(run.error_file) > 0:
                zipf.write(run.error_file, os.path.basename(run.error_file))
            elif run.error_file:
                 zipf.writestr(os.path.basename(run.error_file) + ".missing.txt", "Error file was not found on the server.")


            # Add metadata summary file
            meta_content = f"Run ID: {run.id}\n"
            meta_content += f"Timestamp: {run.timestamp.isoformat() if run.timestamp else 'N/A'}\n"
            meta_content += f"Executable Used: {run.exe_used or 'N/A'}\n"
            meta_content += f"Input Files Record: {run.input_files or 'N/A'}\n"
            meta_content += f"Output File Record: {run.output_file or 'N/A'}\n"
            meta_content += f"Error File Record: {run.error_file or 'N/A'}\n"
            meta_content += "\n--- Simulation Metadata ---\n"
            try:
                # Try to pretty-print if metadata is JSON
                meta_json = json.loads(run.sim_metadata) if run.sim_metadata else None
                meta_content += json.dumps(meta_json, indent=4) if meta_json else 'N/A'
            except (json.JSONDecodeError, TypeError):
                 meta_content += str(run.sim_metadata or 'N/A') # Fallback to string
            zipf.writestr(f"{run.id}_metadata_summary.txt", meta_content)

        return send_file(zip_filename, as_attachment=True, download_name=f"{run_id}_archive.zip")

    except Exception as e:
         print(f"Error creating zip file for run {run_id}: {e}")
         abort(500, description=f"Error creating download archive: {e}")


@app.route('/runs', methods=['GET'])
def list_runs():
    try:
        runs = SimulationRun.query.order_by(SimulationRun.timestamp.desc()).all()
        run_list = []
        for r in runs:
            metadata_obj = None
            try:
                 # Attempt to parse metadata JSON, fallback to string
                 metadata_obj = json.loads(r.sim_metadata) if r.sim_metadata else None
            except (json.JSONDecodeError, TypeError):
                 metadata_obj = r.sim_metadata # Keep as string if not valid JSON

            run_list.append({
                 "run_id": r.id,
                 "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                 "exe_used": os.path.basename(r.exe_used) if r.exe_used else "N/A", # Show basename for brevity
                 "metadata": metadata_obj, # Send parsed or raw metadata
                 "status": determine_run_status(r) # Helper function to guess status
            })
        return jsonify(run_list), 200
    except Exception as e:
        print(f"Error fetching runs: {e}")
        return jsonify({"error": "Failed to retrieve simulation runs."}), 500

def determine_run_status(run_record):
    """ Helper to guess run status based on metadata and file existence """
    metadata = None # Define scope
    try:
        if run_record.sim_metadata:
            # Ensure metadata is parsed as dict if possible
            if isinstance(run_record.sim_metadata, str):
                try:
                    metadata = json.loads(run_record.sim_metadata)
                except (json.JSONDecodeError, TypeError):
                    pass # Leave metadata as None if parsing fails
            elif isinstance(run_record.sim_metadata, dict):
                 metadata = run_record.sim_metadata # Already a dict

            if isinstance(metadata, dict):
                 if metadata.get("type") == "sample_run_failed" or metadata.get("error") == "CalledProcessError":
                     return "Failed (Exit Code)"
                 if metadata.get("type") == "sample_run_exception" or metadata.get("error") == "Other Exception":
                     return "Error (Exception)"
                 if metadata.get("type") == "sample_run_setup_error" or metadata.get("error") == "FileNotFoundError":
                     return "Error (Setup)"
                 if metadata.get("type") == "sample_run":
                     # Check if output file exists and has content for sample run
                     try:
                          if run_record.output_file and os.path.exists(run_record.output_file) and os.path.getsize(run_record.output_file) > 0:
                              return "Completed"
                          elif run_record.output_file and os.path.exists(run_record.output_file):
                               return "Completed (Empty Output?)"
                          else:
                               return "Completed (Output Missing?)"
                     except OSError:
                           return "Completed (Output Status Unknown)"

    except Exception as e:
         print(f"Error determining status for run {run_record.id}: {e}") # Log determination error


    # Fallback checks based purely on file existence/size
    try:
        if run_record.error_file and os.path.exists(run_record.error_file) and os.path.getsize(run_record.error_file) > 0:
             return "Failed (Error File Present)"
    except OSError: pass # Ignore file check errors

    try:
        if run_record.output_file and os.path.exists(run_record.output_file):
             # Consider a run successful if output exists, even if error file check failed
             return "Completed"
    except OSError: pass

    # If metadata suggested success but files are missing/empty, status might be misleading
    # Relying on metadata first is generally better if logging is consistent.

    return "Unknown" # Default status


@app.route('/admin/upload_exe', methods=['POST'])
def admin_upload_exe():
    # Add authentication/authorization check here for real apps
    exe_file = request.files.get('exe')
    if not exe_file:
        return jsonify({"error": "No executable file provided."}), 400

    # Use case-insensitive check for .exe
    if not exe_file.filename.lower().endswith('.exe'):
        return jsonify({"error": "File must have a .exe extension."}), 400

    exe_filename = secure_filename(DEFAULT_EXE_NAME) # Always save as the default name
    default_exe_path = os.path.join(DEFAULT_EXE_FOLDER, exe_filename)

    try:
        # Ensure the target directory exists
        os.makedirs(DEFAULT_EXE_FOLDER, exist_ok=True)
        exe_file.save(default_exe_path)
        return jsonify({"message": "Default executable updated successfully.", "default_exe_path": default_exe_path}), 200
    except Exception as e:
         print(f"Error saving default executable: {e}")
         return jsonify({"error": f"Failed to save executable: {e}"}), 500


# PROMPT TEMPLATES

def explain_input_file_prompt(file_content):
    return f"""
You are a transportation modeling assistant.

Using the Integration 2.40 User Manual, please answer the following question.

--- FILE START ---
{file_content}
--- FILE END ---

Explain this in detail, including the purpose of any numerical parameters or codes.
"""

def suggest_modifications_prompt(file_content):
    return f"""
You are helping a traffic engineer improve this simulation.

Below is the content of a traffic simulation input file. Suggest ways to modify this file to reduce traffic delay or improve flow.

--- FILE START ---
{file_content}
--- FILE END ---

List specific parameters to change, why, and what new values to try.
"""

def summarize_output_file_prompt(file_content):
    return f"""
Below is a simulation output request from a traffic model. Summarize the performance of the network.

--- FILE START ---
{file_content}
--- FILE END ---

Include:
- Number of trips
- Total delay
- Fuel and emissions
- Any safety or crash data
"""

def generate_input_file_prompt(user_input):
    # Extract parameters from user input using regex
    node_match = re.search(r'(\d+)\s*(nodes?|intersection)', user_input.lower())
    link_match = re.search(r'(\d+)\s*(links?|roads?|segment)', user_input.lower())
    time_match = re.search(r'(\d+)\s*(seconds?|minutes?|hours?|time)', user_input.lower())
    vehicle_match = re.search(r'(\d+)\s*(vehicle|car|class)', user_input.lower())
    
    # Extract values with defaults
    num_nodes = int(node_match.group(1)) if node_match else 3
    num_links = int(link_match.group(1)) if link_match else max(num_nodes - 1, 1)
    sim_time = int(time_match.group(1)) if time_match else 300
    vehicle_classes = int(vehicle_match.group(1)) if vehicle_match else 1
    
    # Convert minutes/hours to seconds if needed
    if time_match and "minute" in time_match.group(2):
        sim_time *= 60
    elif time_match and "hour" in time_match.group(2):
        sim_time *= 3600
    
    # Generate template with user parameters
    return f"""
You are a transportation simulation assistant helping to create valid INET input files for the INTEGRATION traffic simulation software.

Below are example input files that form a minimal working simulation: an INET master file (.INT) and its referenced .DAT files for nodes, links, and OD demand. Use them as patterns.

--- EXAMPLE 1: simple_master.INT ---
INET master file - format I
300 100 100 1 0
inputs\\
outputs\\
simple1.dat
simple2.dat
simple3.dat
none
none
none
none
none
simple.out
none
none
none
none
none
none
none
none
none
none
none
none
none
none
none
none
none
none
none

--- EXAMPLE 1: simple1.dat (Node Coordinates) ---
Simple Node Coordinate File
3   1.0   1.0
1   0.0   0.0   1 -1 0   zone 1
2   1.0   0.0   1 -2 0   zone 2
3   0.5   0.5   4  0  0

--- EXAMPLE 1: simple2.dat (Link Definitions) ---
Simple Link File
1   0.0  0.0
1   1   2   1.0   60   2000  1   0  40 100 0 0 0 0 0 0 0 0 0 00000 11111

--- EXAMPLE 1: simple3.dat (OD Demand) ---
Simple OD Demand File
1   0   0   1.0
1   1   2   10   1.0   0   300   1.0   0.0 0.0 0.0 0.0 0.0 1.0

---

Now generate a **new**, minimal, but valid INET master input file and its 3 corresponding `.DAT` files using the same structure and formatting. Follow these requirements:

- Simulation time: {sim_time} seconds  
- Version format: 1  
- Surveillance mode: 0  
- {num_nodes} nodes  
- {num_links} links
- {vehicle_classes} vehicle classes  
- .INT file must reference 3 input files: node, link, and OD demand  
- Name the files traffic1.int, traffic_nodes.dat, traffic_links.dat, and traffic_od.dat
- All numeric parameters must be plausible and valid
- Create a simple but realistic network with logical node positions

**Return ONLY the generated files, starting with the .INT file. Do not explain, comment, or use markdown.**

Ensure that each file path in the master file appears on its own line, exactly like in the examples above.

--- BEGIN GENERATED FILES ---
"""

# INTENT DETECTION
def determine_intent_and_prompt(user_input, file_content):
    user_input = user_input.lower()
    print(user_input)
    
    # Check for generate intent
    if "generate" in user_input or "create" in user_input:
        intent = "generate"
        print(f"Intent detected: {intent}")
        
        # Check if user already provided some parameters in their request
        has_nodes = re.search(r'(\d+)\s*(nodes?|intersection)', user_input) is not None
        has_links = re.search(r'(\d+)\s*(links?|roads?|segment)', user_input) is not None
        has_time = re.search(r'(\d+)\s*(seconds?|minutes?|hours?|time)', user_input) is not None
        has_vehicles = re.search(r'(\d+)\s*(vehicle|car|class)', user_input) is not None
        
        # If we have most parameters, go straight to generation
        if sum([has_nodes, has_links, has_time, has_vehicles]) >= 3:
            return intent, generate_input_file_prompt(user_input)
        else:
            # Otherwise, ask for more parameters
            return intent, """
You are a transportation simulation assistant helping to create INTEGRATION traffic simulation input files.

I'll help you generate input files for your simulation. Based on your request, I need a few more details:

1. How many nodes should be in your network? (e.g., 2-3 for simple, 4+ for more complex)
2. How many links do you need between these nodes?
3. What simulation time period would you like to model? (in seconds)
4. How many vehicle classes do you need?
5. Any specific origin-destination (OD) flow requirements?
6. Any specific road characteristics (speed limits, capacities)?

Please provide these parameters, and I'll generate the appropriate INET master file (.INT) and necessary .DAT files (nodes, links, OD demand) for your simulation.
"""
    elif "summarize" in user_input or ".out" in user_input:
        intent = "summarize"
        return intent, summarize_output_file_prompt(file_content)
    elif "improve" in user_input or "modify" in user_input:
        intent = "suggest"
        return intent, suggest_modifications_prompt(file_content)
    elif "explain" in user_input or ("input" in user_input and "file" in user_input):
        intent = "explain"
        return intent, explain_input_file_prompt(file_content)
    elif "run" in user_input or "simulate" in user_input or "start" in user_input:
        intent = "run"
        return intent, None
    else:
        return None, None  # fallback to default LLM reply

# Load and chunk the manuals into overlapping 1000-character sections
def load_manual_chunks():
    manual_paths = [
        os.path.join("integration", "Integration Manual 1.pdf"),
        os.path.join("integration", "Integration Manual 2.pdf")
    ]
    combined_text = ""
    for path in manual_paths:
        if os.path.exists(path):
            try:
                reader = PdfReader(path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        combined_text += text + "\n"
            except Exception as e:
                print(f"[ERROR] Failed to read manual: {path} -> {e}")
        else:
            print(f"[WARNING] Manual not found: {path}")

    # Clean up whitespace
    combined_text = re.sub(r'\s+', ' ', combined_text).strip()

    # Chunk into ~1000 characters with 100-character overlap
    chunk_size = 1000
    overlap = 100
    chunks = []
    i = 0
    while i < len(combined_text):
        chunk = combined_text[i:i + chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

# Preload at app startup
MANUAL_CHUNKS = load_manual_chunks()

# Simple keyword match scoring for relevant chunks
def find_relevant_chunks(user_input, top_k=3):
    scores = []
    keywords = set(user_input.lower().split())
    for i, chunk in enumerate(MANUAL_CHUNKS):
        chunk_words = set(chunk.lower().split())
        overlap = keywords & chunk_words
        scores.append((len(overlap), i))
    # Sort by descending score
    scores.sort(reverse=True)
    top_chunks = [MANUAL_CHUNKS[i] for _, i in scores[:top_k]]
    return "\n\n".join(top_chunks)


# SMART LLM CHAT ENDPOINT
def smart_llm_route():
    data = request.get_json()
    user_input = data.get("text", "")  # User input, may be empty
    file_content = data.get("file_content", None)  # File content
    file_name = data.get("file_name", None)  # Optional uploaded filename

    if not user_input and not file_content:
        return jsonify({"error": "No text or file content provided."}), 400

    # INTENT + PROMPT DETECTION
    result = determine_intent_and_prompt(user_input, file_content)
    if result is None:
        intent, prompt = None, None
    else:
        intent, prompt = result
    print(f"Detected intent: {intent}")
    print(f"Generated prompt: {prompt[:100]}..." if prompt else "No prompt")

    # ---------- GENERATE INTENT BRANCH ----------
    if intent == "generate":
        # Check if this is a follow-up with parameters after our initial prompt
        has_parameters = any(param in user_input.lower() for param in 
                           ["node", "link", "time", "second", "vehicle", "class"])
                           
        # If they've provided parameters in response to our prompt, generate files
        if has_parameters and "how many" not in user_input.lower():
            # Use the generate input file prompt to create files based on parameters
            generation_prompt = generate_input_file_prompt(user_input)
            
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama2:7b", "prompt": generation_prompt, "stream": False}
                )
                response_data = response.json()
                return jsonify({"response": response_data.get("response", "")}), 200
            except Exception as e:
                return jsonify({"error": "LLM file generation failed", "details": str(e)}), 500

    # ---------- RUN INTENT BRANCH ----------
    if intent == "run":
        print("Processing run intent")
        tokens = user_input.split()
        run_file_name = next((t for t in tokens if t.lower().endswith(".int")), None)
        if not run_file_name:
            #return jsonify({"error": "No .INT input file specified to run."}), 400
            return run_sample_simulation()

        candidate_dirs = [UPLOAD_FOLDER, "integration"]
        found_path = None
        for directory in candidate_dirs:
            potential_path = os.path.join(directory, run_file_name)
            if os.path.exists(potential_path):
                found_path = potential_path
                break

        if not found_path:
            return jsonify({"error": f"Input file '{run_file_name}' not found in expected directories."}), 404

        from flask import current_app
        try:
            run_data = {
                "input_files": [found_path],
                "exe_used": os.path.join(DEFAULT_EXE_FOLDER, DEFAULT_EXE_NAME),
                "metadata": {"source": "llm_triggered"}
            }
            with current_app.test_request_context(json=run_data):
                print("Running simulation")
                return run_simulation()
        except Exception as e:
            return jsonify({"error": "Simulation failed", "details": str(e)}), 500

    # ---------- DEFAULT HANDLING FOR OTHER INTENTS ----------
    # If no prompt was determined but we have file content, create a default prompt
    if prompt is None and file_content:
        prompt = f"You are a traffic simulation assistant.\n\n"
        prompt += f"The user has uploaded a file named '{file_name or 'unnamed_file'}' with the following content:\n"
        prompt += f"--- FILE CONTENT START ---\n{file_content}\n--- FILE CONTENT END ---\n\n"

        if user_input:
            prompt += f"User query: {user_input}\n\n"
            prompt += "Please analyze the file content and respond to the user's query."
        else:
            prompt += "Please provide a detailed explanation of this file's content and its purpose in traffic simulation."
    elif prompt is None:
        # Default prompt if nothing else matches
        prompt = f"You are a traffic simulation assistant. Reply to this question:\n\n{user_input}"

    # ---------- MANUAL CONTEXT ----------
    # Add manual context for non-generate intents
    if intent != "generate":
        relevant_manual_content = find_relevant_chunks(user_input or file_name or "", top_k=3)
        if relevant_manual_content:
            prompt += f"\n\n--- USER MANUAL CONTEXT ---\n{relevant_manual_content}"

    # ---------- SEND TO LLM ----------
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama2:7b", "prompt": prompt, "stream": False}
        )
        response_data = response.json()
        return jsonify({"response": response_data.get("response", "")}), 200
    except Exception as e:
        return jsonify({"error": "LLM request failed", "details": str(e)}), 500
# Register the endpoint
app.add_url_rule('/llm', view_func=smart_llm_route, methods=['POST'])


if __name__ == '__main__':
    # Make sure the 'integration' directory exists relative to this script
    integration_path_check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "integration")
    # Check for the *correct* input file name on startup
    sample_input_file_check = os.path.join(integration_path_check, "INET_I.INT") # Corrected check

    if not os.path.isdir(integration_path_check):
        print(f"WARNING: 'integration' directory not found at {integration_path_check}")
        print(f"Please create it and place 'intgrats.exe' and '{os.path.basename(sample_input_file_check)}' inside for the sample run.")
    elif not os.path.exists(sample_input_file_check):
         print(f"WARNING: Sample input file '{os.path.basename(sample_input_file_check)}' not found in {integration_path_check}")
    elif not os.path.exists(os.path.join(integration_path_check, DEFAULT_EXE_NAME)):
         print(f"WARNING: Sample executable '{DEFAULT_EXE_NAME}' not found in {integration_path_check}")


    # Ensure default executable folder exists
    if not os.path.isdir(DEFAULT_EXE_FOLDER):
        try:
            os.makedirs(DEFAULT_EXE_FOLDER)
            print(f"Created default executable folder: {DEFAULT_EXE_FOLDER}")
        except OSError as e:
            print(f"ERROR: Could not create default executable folder '{DEFAULT_EXE_FOLDER}': {e}")

    app.run(debug=True) # debug=True is convenient for development, False for production
    