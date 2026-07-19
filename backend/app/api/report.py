"""
Report API routes
Provides simulation report generation, retrieval, and conversation endpoints
"""

import os
import traceback
import threading
from flask import request, jsonify, send_file, current_app

from . import report_bp
from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..services.graph_tools import GraphToolsService
from ..services.simulation_manager import SimulationManager
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from ..utils.validation import validate_simulation_id
from ..auth.decorators import authorize_simulation_admin, require_auth

logger = get_logger('miroshark.api.report')


def _authorize_simulation_access(simulation_id, *, allow_published: bool):
    """Contrôle d'accès des endpoints rapport (US-206 — ferme l'IDOR §1.3
    du SECURITY_AUDIT_2026-05).

    Règles :
      1. Supabase non configuré (mode OSS/dev sans multitenant) → accès
         legacy inchangé.
      2. Simulation absente de ``simulation_ownership`` → legacy publique
         (même sémantique que ``is_user_authorized_to_read``).
      3. Simulation publiée + ``allow_published`` → accès public (galerie
         /explore, embeds, share cards — à ne pas casser, cf. audit).
      4. Sinon : JWT Supabase requis — super-admin OK, membre de l'org
         propriétaire OK, tout le reste 403. Sans JWT : 401.

    La livraison externe par lien signé n'emprunte PAS ces endpoints
    (blueprint dédié ``/r/<token>``, report_delivery.py) — non affectée.

    Returns:
        ``None`` si l'accès est autorisé, sinon un tuple Flask
        ``(jsonify(...), status)`` prêt à être retourné.
    """
    from ..auth import supabase_client as sbc
    from ..auth import jwt_verifier
    from ..auth.decorators import is_super_admin_email

    def _deny(code: str, message: str, status: int):
        return jsonify({
            "success": False,
            "error_code": code,
            "error": message,
        }), status

    try:
        owner = sbc.get_simulation_owner(simulation_id)
    except sbc.SupabaseConfigError:
        # Règle 1 — déploiement sans Supabase : comportement legacy.
        return None
    except Exception as exc:  # noqa: BLE001 — fail-closed (audit)
        logger.error(
            "report access check failed for sim=%s: %s",
            simulation_id, exc.__class__.__name__,
        )
        return _deny("ACCESS_CHECK_FAILED", "Authorization check failed.", 403)

    if owner is None:
        # Règle 2 — sim non trackée = legacy publique.
        return None

    if allow_published and bool(owner.get("is_published")):
        # Règle 3 — contenu volontairement public.
        return None

    # Règle 4 — JWT obligatoire.
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        return _deny(
            "AUTH_REQUIRED",
            "Authentication is required to access this report.",
            401,
        )
    try:
        claims = jwt_verifier.verify_supabase_jwt(token)
    except Exception:  # noqa: BLE001 — InvalidTokenError et variantes
        return _deny("INVALID_TOKEN", "Invalid or expired token.", 401)

    email = claims.get("email") or ""
    if is_super_admin_email(email):
        return None

    user_id = claims.get("sub") or ""
    org_id = owner.get("org_id")
    if user_id and org_id:
        try:
            role = sbc.get_user_role_in_org(user_id, str(org_id))
        except Exception:  # noqa: BLE001 — fail-closed
            role = None
        if role:
            return None

    return _deny(
        "FORBIDDEN",
        "You are not authorized to access this report.",
        403,
    )


@report_bp.before_request
def _validate_url_simulation_id():
    """Reject requests whose URL-derived simulation_id could cause path traversal."""
    from flask import request as _req
    sim_id = _req.view_args.get('simulation_id') if _req.view_args else None
    if sim_id is not None:
        try:
            validate_simulation_id(sim_id)
        except ValueError as exc:
            return jsonify({
                "success": False,
                "error_code": "INVALID_SIMULATION_ID",
                "error": str(exc)
            }), 400


# ============== Report Generation Endpoints ==============

@report_bp.route('/generate', methods=['POST'])
def generate_report():
    """
    Generate simulation analysis report (async task)

    This is a time-consuming operation. The endpoint returns task_id immediately.
    Use GET /api/report/generate/status to query progress.

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",    // Required, simulation ID
            "force_regenerate": false        // Optional, force regeneration
        }

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",
                "status": "generating",
                "message": "Report generation task started"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error_code": "MISSING_SIMULATION_ID",
                "error": "Please provide simulation_id"
            }), 400
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({
                "success": False,
                "error_code": "INVALID_SIMULATION_ID",
                "error": str(exc)
            }), 400

        denied = _authorize_simulation_access(
            simulation_id, allow_published=False,
        )
        if denied is not None:
            return denied

        force_regenerate = data.get('force_regenerate', False)

        # Get simulation info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error_code": "SIMULATION_NOT_FOUND",
                "error": f"Simulation not found: {simulation_id}"
            }), 404

        # Check if a report already exists
        if not force_regenerate:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "message": "Report already exists",
                        "already_generated": True
                    }
                })

        # Get project info
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error_code": "PROJECT_NOT_FOUND",
                "error": f"Project not found: {state.project_id}"
            }), 404

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error_code": "GRAPH_NOT_BUILT",
                "error": "Missing graph ID, please ensure the graph has been built"
            }), 400

        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Missing simulation requirement description"
            }), 400

        # Pre-generate report_id for immediate return to frontend
        import uuid
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )

        # Initialize graph_tools in Flask context BEFORE spawning thread
        # (current_app is not available inside background threads)
        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            return jsonify({
                "success": False,
                "error_code": "STORAGE_UNAVAILABLE",
                "error": "Neo4j storage not initialized"
            }), 503
        graph_tools = GraphToolsService(storage=storage)

        # Define background task
        def run_generate():
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="Initializing Report Agent..."
                )

                # Create Report Agent
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    graph_tools=graph_tools
                )

                # Progress callback
                def progress_callback(stage, progress, message):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )

                # Generate report (pass pre-generated report_id)
                report = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id
                )

                # Save report
                ReportManager.save_report(report)

                if report.status == ReportStatus.COMPLETED:
                    task_manager.complete_task(
                        task_id,
                        result={
                            "report_id": report.report_id,
                            "simulation_id": simulation_id,
                            "status": "completed"
                        }
                    )
                else:
                    task_manager.fail_task(task_id, report.error or "Report generation failed")

            except Exception as e:
                logger.error(f"Report generation failed: {str(e)}\n" + traceback.format_exc())
                task_manager.fail_task(task_id, str(e))

        # Start background thread
        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating",
                "message": "Report generation task started, query progress via /api/report/generate/status",
                "already_generated": False
            }
        })

    except Exception as e:
        logger.error(f"Failed to start report generation task: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error_code": "REPORT_GENERATION_FAILED",
            "error": "Internal server error",
        }), 500


@report_bp.route('/generate/status', methods=['POST'])
def get_generate_status():
    """
    Query report generation task progress

    Request (JSON):
        {
            "task_id": "task_xxxx",         // Optional, task_id returned by generate
            "simulation_id": "sim_xxxx"     // Optional, simulation ID
        }

    Returns:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|failed",
                "progress": 45,
                "message": "..."
            }
        }
    """
    try:
        data = request.get_json() or {}

        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        if simulation_id:
            try:
                validate_simulation_id(simulation_id)
            except ValueError as exc:
                return jsonify({
                    "success": False,
                    "error_code": "INVALID_SIMULATION_ID",
                    "error": str(exc)
                }), 400

        # If simulation_id is provided, first check if a completed report exists
        if simulation_id:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "progress": 100,
                        "message": "Report has been generated",
                        "already_completed": True
                    }
                })

        if not task_id:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Please provide task_id or simulation_id"
            }), 400

        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

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

    except Exception as e:
        logger.error(f"Failed to query task status: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


# ============== Report Retrieval Endpoints ==============

@report_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id: str):
    """
    Get report details

    Returns:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "simulation_id": "sim_xxxx",
                "status": "completed",
                "outline": {...},
                "markdown_content": "...",
                "created_at": "...",
                "completed_at": "..."
            }
        }
    """
    try:
        report = ReportManager.get_report(report_id)

        # Fallback : si l'id passé est en réalité un simulation_id (sim_xxxx),
        # on tente la résolution par simulation. Le frontend route /report/:id
        # accepte historiquement les deux formats — sans ce fallback, naviguer
        # vers /report/sim_xxx déclenche un 404 silencieux et la vue reste
        # bloquée en état GENERATING.
        if not report and isinstance(report_id, str) and report_id.startswith("sim_"):
            report = ReportManager.get_report_by_simulation(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error_code": "REPORT_NOT_FOUND",
                "error": f"Report not found: {report_id}"
            }), 404

        denied = _authorize_simulation_access(
            report.simulation_id, allow_published=True,
        )
        if denied is not None:
            return denied

        return jsonify({
            "success": True,
            "data": report.to_dict()
        })

    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


@report_bp.route('/by-simulation/<simulation_id>', methods=['GET'])
def get_report_by_simulation(simulation_id: str):
    """
    Get report by simulation ID

    Returns:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                ...
            }
        }
    """
    try:
        # Même objet que get_report par une autre clé — même garde (US-206),
        # sinon la fermeture de l'IDOR serait contournable par ce chemin.
        denied = _authorize_simulation_access(
            simulation_id, allow_published=True,
        )
        if denied is not None:
            return denied

        report = ReportManager.get_report_by_simulation(simulation_id)

        if not report:
            return jsonify({
                "success": False,
                "error_code": "REPORT_NOT_FOUND",
                "error": f"No report available for this simulation: {simulation_id}",
                "has_report": False
            }), 404

        return jsonify({
            "success": True,
            "data": report.to_dict(),
            "has_report": True
        })

    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


@report_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id: str):
    """
    Download report (Markdown format)

    Returns a Markdown file
    """
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error_code": "REPORT_NOT_FOUND",
                "error": f"Report not found: {report_id}"
            }), 404

        denied = _authorize_simulation_access(
            report.simulation_id, allow_published=True,
        )
        if denied is not None:
            return denied

        md_path = ReportManager._get_report_markdown_path(report_id)

        if not os.path.exists(md_path):
            # If MD file does not exist, generate a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(report.markdown_content)
                temp_path = f.name

            return send_file(
                temp_path,
                as_attachment=True,
                download_name=f"{report_id}.md"
            )

        return send_file(
            md_path,
            as_attachment=True,
            download_name=f"{report_id}.md"
        )

    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


@report_bp.route('/<report_id>', methods=['DELETE'])
@require_auth
def delete_report(report_id: str):
    """Delete report"""
    try:
        report = ReportManager.get_report(report_id)
        if report is None:
            return jsonify({
                "success": False,
                "error_code": "REPORT_NOT_FOUND",
                "error": f"Report not found: {report_id}"
            }), 404

        denied = authorize_simulation_admin(report.simulation_id)
        if denied is not None:
            return denied

        success = ReportManager.delete_report(report_id)

        if not success:
            return jsonify({
                "success": False,
                "error_code": "REPORT_NOT_FOUND",
                "error": f"Report not found: {report_id}"
            }), 404

        return jsonify({
            "success": True,
            "message": f"Report deleted: {report_id}"
        })

    except Exception as e:
        logger.error(f"Failed to delete report: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


# ============== Report Agent Chat Endpoints ==============

@report_bp.route('/chat', methods=['POST'])
def chat_with_report_agent():
    """
    Chat with Report Agent

    Report Agent can autonomously call retrieval tools during conversation to answer questions

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",        // Required, simulation ID
            "message": "Please explain the trend",  // Required, user message
            "chat_history": [                   // Optional, conversation history
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

    Returns:
        {
            "success": true,
            "data": {
                "response": "Agent response...",
                "tool_calls": [list of tool calls],
                "sources": [information sources]
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        message = data.get('message')
        chat_history = data.get('chat_history', [])

        if not simulation_id:
            return jsonify({
                "success": False,
                "error_code": "MISSING_SIMULATION_ID",
                "error": "Please provide simulation_id"
            }), 400
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({
                "success": False,
                "error_code": "INVALID_SIMULATION_ID",
                "error": str(exc)
            }), 400

        if not message:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Please provide message"
            }), 400

        denied = _authorize_simulation_access(
            simulation_id, allow_published=False,
        )
        if denied is not None:
            return denied

        # Get simulation and project info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error_code": "SIMULATION_NOT_FOUND",
                "error": f"Simulation not found: {simulation_id}"
            }), 404

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error_code": "PROJECT_NOT_FOUND",
                "error": f"Project not found: {state.project_id}"
            }), 404

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error_code": "GRAPH_NOT_BUILT",
                "error": "Missing graph ID"
            }), 400

        simulation_requirement = project.simulation_requirement or ""

        # Create Agent and start conversation
        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            return jsonify({
                "success": False,
                "error_code": "STORAGE_UNAVAILABLE",
                "error": "Neo4j storage not initialized"
            }), 503
        graph_tools = GraphToolsService(storage=storage)

        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
            graph_tools=graph_tools
        )

        result = agent.chat(message=message, chat_history=chat_history)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"Chat failed: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "CHAT_FAILED",
            "error": str(e)
        }), 500


# ============== Report Progress and Section Endpoints ==============

# ============== Report Status Check Endpoints ==============

@report_bp.route('/check/<simulation_id>', methods=['GET'])
def check_report_status(simulation_id: str):
    """
    Check if a simulation has a report and its status

    Used by frontend to determine whether to unlock Interview feature

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "has_report": true,
                "report_status": "completed",
                "report_id": "report_xxxx",
                "interview_unlocked": true
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None

        # Only unlock interview after report is completed
        interview_unlocked = report is not None and report.status == ReportStatus.COMPLETED

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "has_report": has_report,
                "report_status": report_status,
                "report_id": report_id,
                "interview_unlocked": interview_unlocked
            }
        })

    except Exception as e:
        logger.error(f"Failed to check report status: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


# ============== Agent Log Endpoints ==============

@report_bp.route('/<report_id>/agent-log', methods=['GET'])
def get_agent_log(report_id: str):
    """
    Get Report Agent's detailed execution log

    Retrieve each step of action during report generation in real-time, including:
    - Report start, planning start/complete
    - Each section's start, tool calls, LLM responses, completion
    - Report complete or failed

    Query parameters:
        from_line: Start reading from this line (optional, default 0, for incremental retrieval)

    Returns:
        {
            "success": true,
            "data": {
                "logs": [
                    {
                        "timestamp": "2025-12-13T...",
                        "elapsed_seconds": 12.5,
                        "report_id": "report_xxxx",
                        "action": "tool_call",
                        "stage": "generating",
                        "section_title": "Executive Summary",
                        "section_index": 1,
                        "details": {
                            "tool_name": "insight_forge",
                            "parameters": {...},
                            ...
                        }
                    },
                    ...
                ],
                "total_lines": 25,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)

        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)

        return jsonify({
            "success": True,
            "data": log_data
        })

    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


@report_bp.route('/<report_id>/agent-log/stream', methods=['GET'])
def stream_agent_log(report_id: str):
    """
    Get complete Agent log (fetch all at once)

    Returns:
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 25
            }
        }
    """
    try:
        logs = ReportManager.get_agent_log_stream(report_id)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        })

    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


# ============== Console Log Endpoints ==============

@report_bp.route('/<report_id>/console-log', methods=['GET'])
def get_console_log(report_id: str):
    """
    Get Report Agent's console output log

    Retrieve console output (INFO, WARNING, etc.) during report generation in real-time.
    This differs from the structured JSON log returned by the agent-log endpoint;
    it is plain text console-style log.

    Query parameters:
        from_line: Start reading from this line (optional, default 0, for incremental retrieval)

    Returns:
        {
            "success": true,
            "data": {
                "logs": [
                    "[19:46:14] INFO: Search complete: found 15 related facts",
                    "[19:46:14] INFO: Graph search: graph_id=xxx, query=...",
                    ...
                ],
                "total_lines": 100,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)

        log_data = ReportManager.get_console_log(report_id, from_line=from_line)

        return jsonify({
            "success": True,
            "data": log_data
        })

    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


@report_bp.route('/<report_id>/console-log/stream', methods=['GET'])
def stream_console_log(report_id: str):
    """
    Get complete console log (fetch all at once)

    Returns:
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 100
            }
        }
    """
    try:
        logs = ReportManager.get_console_log_stream(report_id)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        })

    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


# ============== Tool Call Endpoints (for debugging) ==============

@report_bp.route('/tools/search', methods=['POST'])
def search_graph_tool():
    """
    Graph search tool endpoint (for debugging)

    Request (JSON):
        {
            "graph_id": "miroshark_xxxx",
            "query": "search query",
            "limit": 10
        }
    """
    try:
        data = request.get_json() or {}

        graph_id = data.get('graph_id')
        query = data.get('query')
        limit = data.get('limit', 10)

        if not graph_id or not query:
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Please provide graph_id and query"
            }), 400

        from flask import current_app
        from ..services.graph_tools import GraphToolsService

        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            return jsonify({
                "success": False,
                "error_code": "STORAGE_UNAVAILABLE",
                "error": "Neo4j storage is not initialized"
            }), 503

        tools = GraphToolsService(storage=storage)
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": result.to_dict()
        })

    except Exception as e:
        logger.error(f"Graph search failed: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500


@report_bp.route('/tools/statistics', methods=['POST'])
def get_graph_statistics_tool():
    """
    Graph statistics tool endpoint (for debugging)

    Request (JSON):
        {
            "graph_id": "miroshark_xxxx"
        }
    """
    try:
        data = request.get_json() or {}

        graph_id = data.get('graph_id')

        if not graph_id:
            return jsonify({
                "success": False,
                "error_code": "MISSING_GRAPH_ID",
                "error": "Please provide graph_id"
            }), 400

        from flask import current_app
        from ..services.graph_tools import GraphToolsService

        storage = current_app.extensions.get('neo4j_storage')
        if not storage:
            return jsonify({
                "success": False,
                "error_code": "STORAGE_UNAVAILABLE",
                "error": "Neo4j storage is not initialized"
            }), 503

        tools = GraphToolsService(storage=storage)
        result = tools.get_graph_statistics(graph_id)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"Failed to get graph statistics: {str(e)}\n" + traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": str(e)
        }), 500
