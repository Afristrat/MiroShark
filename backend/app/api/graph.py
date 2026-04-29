"""
Graph-related API routes
Uses project context mechanism with server-side persistent state
"""

import json
import os
import traceback
import threading
from flask import request, jsonify

from flask import current_app

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get logger
logger = get_logger('miroshark.api')


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# US-039 — Context refinement constants & sanitiser
_REFINEMENT_GEO_VALUES = {"MA", "DZ", "TN", "SN", "CI", "multi"}
_REFINEMENT_TIME_VALUES = {"24h", "72h", "1w", "2w", "30d", "60d"}
_REFINEMENT_LIST_MAX = 8
_REFINEMENT_LIST_ITEM_MAX_CHARS = 60
_REFINEMENT_TENSIONS_MAX_CHARS = 200


def _sanitise_context_refinement(raw):
    """
    Validate / clip the context_refinement payload coming from the frontend.

    Returns a normalised dict with the canonical 5 keys, or None if no usable
    payload was supplied. Callers are free to write the result straight to the
    project record — defensive trimming keeps the stored shape stable.
    """
    if not isinstance(raw, dict):
        return None

    def _clean_chip_list(value):
        if not isinstance(value, list):
            return []
        cleaned = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                continue
            stripped = item.strip()
            if not stripped:
                continue
            if len(stripped) > _REFINEMENT_LIST_ITEM_MAX_CHARS:
                stripped = stripped[:_REFINEMENT_LIST_ITEM_MAX_CHARS]
            if stripped in seen:
                continue
            seen.add(stripped)
            cleaned.append(stripped)
            if len(cleaned) >= _REFINEMENT_LIST_MAX:
                break
        return cleaned

    geo = raw.get("geo_locale")
    if not isinstance(geo, str) or geo not in _REFINEMENT_GEO_VALUES:
        geo = ""

    horizon = raw.get("time_horizon")
    if not isinstance(horizon, str) or horizon not in _REFINEMENT_TIME_VALUES:
        horizon = ""

    tensions = raw.get("key_tensions")
    if isinstance(tensions, str):
        tensions = tensions.strip()[:_REFINEMENT_TENSIONS_MAX_CHARS]
    else:
        tensions = ""

    return {
        "key_actors": _clean_chip_list(raw.get("key_actors")),
        "geo_locale": geo,
        "time_horizon": horizon,
        "key_tensions": tensions,
        "expected_stakeholders": _clean_chip_list(raw.get("expected_stakeholders")),
    }


# ============== Project Management APIs ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    Get project details
    """
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error_code": "PROJECT_NOT_FOUND",
            "error": f"Project not found: {project_id}"
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict()
    })



# ============== URL Fetch API ==============

@graph_bp.route('/fetch-url', methods=['POST'])
def fetch_url():
    """
    Fetch a URL and extract readable text for use as a simulation document.

    Request (JSON):
        { "url": "https://example.com/article" }

    Returns:
        {
            "success": true,
            "data": {
                "title": "Article Title",
                "text": "Extracted plain text...",
                "url": "https://example.com/article",
                "char_count": 4200
            }
        }
    """
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()

        if not url:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "url is required"
            }), 400

        from ..utils.url_fetcher import fetch_url_text
        result = fetch_url_text(url)

        return jsonify({"success": True, "data": result})

    except ValueError as e:
        return jsonify({
            "success": False,
            "error_code": "INVALID_INPUT",
            "error": str(e)
        }), 400
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        return jsonify({
            "success": False,
            "error_code": "URL_FETCH_FAILED",
            "error": f"Failed to fetch URL: {str(e)}"
        }), 500


# ============== API 1: Upload files and generate ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    API 1: Upload files and/or URL-fetched texts, then analyze to generate ontology.

    Request format: multipart/form-data

    Parameters:
        files: Uploaded files (PDF/MD/TXT), multiple allowed (optional if url_docs provided)
        url_docs: JSON-encoded list of {title, url, text} objects fetched via /fetch-url (optional)
        simulation_requirement: Simulation requirement description (required)
        project_name: Project name (optional)
        additional_context: Additional notes (optional)

    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== Starting ontology generation ===")

        # Get parameters
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        url_docs_raw = request.form.get('url_docs', '')

        logger.debug(f"Project name: {project_name}")
        logger.debug(f"Simulation requirement: {simulation_requirement[:100]}...")

        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Please provide a simulation requirement description (simulation_requirement)"
            }), 400

        # Parse URL docs (pre-fetched via /fetch-url)
        url_docs = []
        if url_docs_raw:
            try:
                url_docs = json.loads(url_docs_raw)
            except Exception:
                logger.warning("Failed to parse url_docs field, ignoring")

        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        has_files = uploaded_files and any(f.filename for f in uploaded_files)

        if not has_files and not url_docs:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Please upload at least one document file or provide URL documents"
            }), 400

        # Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"Created project: {project.project_id}")

        # Save files and extract text
        document_texts = []
        all_text = ""

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Save file to project directory
                file_info = ProjectManager.save_file_to_project(
                    project.project_id,
                    file,
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "saved_filename": file_info["saved_filename"],
                    "size": file_info["size"]
                })

                # Extract text
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"

        # Incorporate URL-fetched documents
        for doc in url_docs:
            title = doc.get('title') or doc.get('url', 'URL Document')
            text = doc.get('text', '').strip()
            if not text:
                continue
            text = TextProcessor.preprocess_text(text)
            document_texts.append(text)
            all_text += f"\n\n=== {title} ===\n{text}"
            project.files.append({
                "filename": title,
                "size": len(text),
                "url": doc.get('url', '')
            })
            logger.info(f"Incorporated URL doc: {title} ({len(text)} chars)")

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error_code": "INVALID_INPUT",
                "error": "No documents were successfully processed, please check file formats"
            }), 400
        
        # Save extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction complete, {len(all_text)} characters total")

        # Generate ontology
        logger.info("Calling LLM to generate ontology definition...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )
        
        # Save ontology to project
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"Ontology generation complete: {entity_count} entity types, {edge_count} relationship types")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation complete === Project ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "ONTOLOGY_GENERATION_FAILED",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== API 2: Build graph ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    API 2: Build graph based on project_id

    Request (JSON):
        {
            "project_id": "proj_xxxx",  // Required, from API 1
            "graph_name": "Graph name", // Optional
            "chunk_size": 500,          // Optional, default 500
            "chunk_overlap": 50         // Optional, default 50
        }

    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "Graph build task started"
            }
        }
    """
    try:
        logger.info("=== Starting graph build ===")

        # Check Neo4j storage
        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            logger.error("Neo4j storage not initialized")
            return jsonify({
                "success": False,
                "error_code": "STORAGE_UNAVAILABLE",
                "error": "Neo4j storage is not initialized"
            }), 503

        # Parse request
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Request parameters: project_id={project_id}")

        if not project_id:
            return jsonify({
                "success": False,
                "error_code": "MISSING_PROJECT_ID",
                "error": "Please provide project_id"
            }), 400

        # Get project
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error_code": "PROJECT_NOT_FOUND",
                "error": f"Project not found: {project_id}"
            }), 404

        # US-039 — Optional context refinement payload (key actors, geo locale,
        # time horizon, tensions, expected stakeholders). Sanitised and stored
        # verbatim on the project ; never blocks the rebuild path.
        context_refinement_raw = data.get('context_refinement')
        sanitised_refinement = _sanitise_context_refinement(context_refinement_raw)
        if sanitised_refinement is not None:
            project.context_refinement = sanitised_refinement
            logger.info(
                f"[{project_id}] context_refinement updated: "
                f"actors={len(sanitised_refinement.get('key_actors', []))}, "
                f"geo={sanitised_refinement.get('geo_locale') or '-'}, "
                f"horizon={sanitised_refinement.get('time_horizon') or '-'}, "
                f"tensions_chars={len(sanitised_refinement.get('key_tensions') or '')}, "
                f"stakeholders={len(sanitised_refinement.get('expected_stakeholders', []))}"
            )

        # US-039 — refinement_only=true short-circuits the rebuild and merely
        # persists the refined context. Lets the frontend save the « Refine
        # context » form without forcing a costly graph reconstruction.
        if data.get('refinement_only'):
            ProjectManager.save_project(project)
            return jsonify({
                "success": True,
                "data": {
                    "project_id": project_id,
                    "context_refinement": project.context_refinement,
                    "message": "Context refinement saved (no rebuild triggered)"
                }
            })

        # Check project status
        force = data.get('force', False)  # Force rebuild
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error_code": "ONTOLOGY_NOT_GENERATED",
                "error": "Ontology not yet generated for this project, please call /ontology/generate first"
            }), 400

        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error_code": "GRAPH_BUILD_IN_PROGRESS",
                "error": "Graph is currently being built, please do not resubmit. To force rebuild, add force: true",
                "task_id": project.graph_build_task_id
            }), 400
        
        # If force rebuild, reset state
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # Get configuration
        graph_name = data.get('graph_name', project.name or 'MiroShark Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error_code": "EXTRACTED_TEXT_NOT_FOUND",
                "error": "Extracted text content not found"
            }), 400

        # Get ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error_code": "ONTOLOGY_NOT_FOUND",
                "error": "Ontology definition not found"
            }), 400
        
        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
        logger.info(f"Created graph build task: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Start background task
        def build_task():
            build_logger = get_logger('miroshark.build')
            try:
                build_logger.info(f"[{task_id}] Starting graph build...")
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message="Initializing graph build service..."
                )
                
                # Create graph build service
                builder = GraphBuilderService(storage=storage)
                
                # Chunking
                task_manager.update_task(
                    task_id,
                    message="Chunking text...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=chunk_size, 
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)
                
                # Create graph
                task_manager.update_task(
                    task_id,
                    message="Creating graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # Update project's graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # Set ontology
                task_manager.update_task(
                    task_id,
                    message="Setting ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # Add text (progress_callback signature is (msg, progress_ratio))
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=f"Starting to add {total_chunks} text chunks...",
                    progress=15
                )
                
                episode_uuids = builder.add_text_batches(
                    graph_id,
                    chunks,
                    max_workers=6,
                    progress_callback=add_progress_callback
                )
                
                # Wait for processing (no-op for Neo4j — synchronous)
                storage.wait_for_processing(episode_uuids)
                
                # Get graph data
                task_manager.update_task(
                    task_id,
                    message="Retrieving graph data...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # Update project status
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] Graph build complete: graph_id={graph_id}, nodes={node_count}, edges={edge_count}")
                
                # Complete
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph build complete",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # Update project status to failed
                build_logger.error(f"[{task_id}] Graph build failed: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {str(e)}",
                    error=traceback.format_exc()
                )
        
        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "Graph build task started, query progress via /task/{task_id}"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "GRAPH_BUILD_FAILED",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Task Query APIs ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    Query task status
    """
    task = TaskManager().get_task(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error_code": "TASK_NOT_FOUND",
            "error": f"Task not found: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


# ============== Graph Data APIs ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    Get graph data (nodes and edges)
    """
    try:
        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            return jsonify({
                "success": False,
                "error_code": "STORAGE_UNAVAILABLE",
                "error": "Neo4j storage is not initialized"
            }), 503

        builder = GraphBuilderService(storage=storage)
        graph_data = builder.get_graph_data(graph_id)

        return jsonify({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== US-040 — Step 1.5 « Review & refine entities » ==============

@graph_bp.route('/entities/refine', methods=['POST'])
def refine_entities():
    """Apply a user-curated diff (rename / merge / delete / add) on the
    entities of a freshly built graph, before the agent profile generation
    step kicks in. All four operations land in a single Neo4j transaction.

    Request (JSON):
        {
            "graph_id": "<uuid>",
            "renames":   [{"entity_uuid": "...", "new_name": "..."}, ...],
            "merges":    [{"src_uuid": "...", "target_uuid": "..."}, ...],
            "deletes":   [{"entity_uuid": "..."}, ...],
            "additions": [{"name": "...", "entity_type": "Person"}, ...]
        }

    Response (200):
        {
            "success": true,
            "data": {
                "graph_id": "...",
                "renames_applied":   N,
                "merges_applied":    N,
                "deletes_applied":   N,
                "additions_applied": N,
                "added_entities":    [{"uuid": "...", "name": "...",
                                        "entity_type": "..."}, ...]
            }
        }
    """
    try:
        from ..services.entity_refiner import (
            EntityRefiner,
            EntityRefineError,
            sanitise_refine_diff,
        )

        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            return jsonify({
                "success": False,
                "error": "Neo4j storage is not initialized",
                "error_code": "STORAGE_UNAVAILABLE",
            }), 503

        data = request.get_json() or {}
        graph_id = data.get('graph_id')
        if not graph_id or not isinstance(graph_id, str):
            return jsonify({
                "success": False,
                "error": "graph_id is required",
                "error_code": "MISSING_GRAPH_ID",
            }), 400

        try:
            diff = sanitise_refine_diff(data)
        except EntityRefineError as ve:
            return jsonify({
                "success": False,
                "error": str(ve),
                "error_code": "INVALID_DIFF",
            }), 400

        if diff.total_ops == 0:
            return jsonify({
                "success": True,
                "data": {
                    "graph_id": graph_id,
                    "renames_applied": 0,
                    "merges_applied": 0,
                    "deletes_applied": 0,
                    "additions_applied": 0,
                    "added_entities": [],
                    "message": "No-op — empty diff",
                }
            })

        refiner = EntityRefiner(storage=storage)
        try:
            summary = refiner.apply(graph_id, diff)
        except EntityRefineError as ve:
            # Stale UUID, malformed merge, etc. — surface as 400.
            return jsonify({
                "success": False,
                "error": str(ve),
                "error_code": "INVALID_DIFF",
            }), 400

        logger.info(
            f"[refine] {graph_id} — applied "
            f"{summary['renames_applied']} renames, "
            f"{summary['merges_applied']} merges, "
            f"{summary['deletes_applied']} deletes, "
            f"{summary['additions_applied']} additions"
        )

        return jsonify({
            "success": True,
            "data": summary,
        })

    except Exception as e:
        logger.error(f"refine_entities error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_code": "REFINE_FAILED",
            "traceback": traceback.format_exc(),
        }), 500


